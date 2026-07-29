from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from alembic import command as alembic_command
from alembic.config import Config
from sqlalchemy import create_engine, delete, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.db.paper_models import (
    PaperExecutionCommandRecord,
    PaperExitDecisionRecord,
    PaperFillRecord,
    PaperJournalEntryRecord,
    PaperOrderEventRecord,
    PaperOrderRecord,
    PaperPositionRecord,
    PaperSimulationPolicyRecord,
)
from app.config.settings import get_settings
from app.engine_paper.command_ingestion_service import (
    PaperCommandIngestionOutcome,
    PaperCommandIngestionService,
)
from app.engine_paper.order_execution_service import PaperEntryExecutionRequest
from app.engine_paper.fill_simulator import PaperFillRole
from app.engine_paper.repository_results import RepositoryOutcome, result
from app.engine_paper.unit_of_work import PaperUnitOfWork
from app.engine_safety.paper_domain import PaperOrderState
from tests.paper_command_ingestion_retry.conftest import (
    APPROVED_AT,
    CREATED_AT,
    CLOSED,
    Q,
    make_chain,
    make_policy,
    make_request,
)


@pytest.fixture(scope="session")
def ingestion_engine():
    raw = os.environ.get("PAPER_TEST_DATABASE_URL")
    if not raw:
        pytest.fail("PAPER_TEST_DATABASE_URL is required")
    url = make_url(raw)
    if (
        url.get_backend_name() != "postgresql"
        or url.host not in {"127.0.0.1", "localhost", "::1"}
        or not (url.database or "").startswith("paper_test_")
    ):
        pytest.fail("task-owned loopback PostgreSQL is required")
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", raw.replace("%", "%%"))
    engine = create_engine(raw, hide_parameters=True)
    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = raw
    get_settings.cache_clear()
    alembic_command.upgrade(
        config,
        "0010_paper_final_approval_and_order_transition_event_vocabulary",
    )
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one() == (
            "0010_paper_final_approval_and_order_transition_event_vocabulary"
        )
    try:
        yield engine
    finally:
        engine.dispose()
        get_settings.cache_clear()
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url


@pytest.fixture
def ingestion_factory(ingestion_engine):
    factory = sessionmaker(bind=ingestion_engine, autoflush=False, autocommit=False)
    with ingestion_engine.begin() as connection:
        for model in (
            PaperJournalEntryRecord,
            PaperExitDecisionRecord,
            PaperPositionRecord,
            PaperFillRecord,
            PaperOrderEventRecord,
            PaperOrderRecord,
            PaperExecutionCommandRecord,
            PaperSimulationPolicyRecord,
        ):
            connection.execute(delete(model))
    yield factory


def seed_policy(factory, *, fingerprint="config:ingestion:v1", **changes):
    policy = make_policy()
    values = {
        "policy_id": policy.simulation_policy_id,
        "policy_version": 1,
        "status": "ACTIVE",
        "price_source": policy.price_source.value,
        "timeframe": policy.timeframe,
        "latency_candles": policy.latency_candles,
        "slippage_bps": policy.slippage_bps,
        "fee_bps": policy.fee_bps,
        "partial_fill_enabled": policy.partial_fill_enabled,
        "future_data_allowed": policy.future_data_allowed,
        "intrabar_conflict_policy": policy.intrabar_conflict_policy.value,
        "configuration_fingerprint": fingerprint,
        "created_at": CREATED_AT,
        "retired_at": None,
    }
    values.update(changes)
    with factory.begin() as session:
        session.add(PaperSimulationPolicyRecord(**values))


def service(factory, *, uow_type=PaperUnitOfWork, recovery_factory=None):
    return PaperCommandIngestionService(
        lambda: uow_type(factory),
        recovery_factory or factory,
    )


def counts(factory):
    with factory() as session:
        return {
            "policy": session.scalar(select(func.count()).select_from(PaperSimulationPolicyRecord)),
            "command": session.scalar(select(func.count()).select_from(PaperExecutionCommandRecord)),
            "order": session.scalar(select(func.count()).select_from(PaperOrderRecord)),
            "event": session.scalar(select(func.count()).select_from(PaperOrderEventRecord)),
            "journal": session.scalar(select(func.count()).select_from(PaperJournalEntryRecord)),
            "fill": session.scalar(select(func.count()).select_from(PaperFillRecord)),
            "position": session.scalar(select(func.count()).select_from(PaperPositionRecord)),
        }


def test_real_postgres_creates_exact_atomic_open_graph(ingestion_factory):
    seed_policy(ingestion_factory)
    request = make_request()
    outcome = service(ingestion_factory).ingest_and_create_entry_order(request)
    assert outcome.outcome is PaperCommandIngestionOutcome.COMMAND_AND_ORDER_CREATED
    assert outcome.order_state is PaperOrderState.OPEN
    assert outcome.order_version == 2
    assert counts(ingestion_factory) == {
        "policy": 1,
        "command": 1,
        "order": 1,
        "event": 3,
        "journal": 4,
        "fill": 0,
        "position": 0,
    }
    with ingestion_factory() as session:
        order = session.get(PaperOrderRecord, request.order_id)
        assert order.order_role == "ENTRY"
        assert order.order_type == "MARKET_SIMULATED"
        assert order.state == "OPEN"
        assert order.version == 2
        assert order.filled_quantity == 0
        assert order.average_fill_price is None
        assert order.total_fees == 0


def test_exact_replay_has_zero_mutation_and_zero_version_increment(ingestion_factory):
    seed_policy(ingestion_factory)
    request = make_request()
    first = service(ingestion_factory).ingest_and_create_entry_order(request)
    before = counts(ingestion_factory)
    second = service(ingestion_factory).ingest_and_create_entry_order(request)
    after = counts(ingestion_factory)
    assert first.outcome is PaperCommandIngestionOutcome.COMMAND_AND_ORDER_CREATED
    assert second.outcome is PaperCommandIngestionOutcome.COMMAND_AND_ORDER_ALREADY_EXIST
    assert before == after
    with ingestion_factory() as session:
        assert session.get(PaperOrderRecord, request.order_id).version == 2


@pytest.mark.parametrize(
    ("field", "value"),
        [
            ("status", "RETIRED"),
            ("latency_candles", 2),
        ("slippage_bps", 3),
        ("fee_bps", 11),
        ("configuration_fingerprint", "config:other"),
    ],
)
def test_policy_mismatch_has_zero_graph_mutation(ingestion_factory, field, value):
    changes = {field: value}
    if field == "status":
        changes["retired_at"] = CREATED_AT
    seed_policy(ingestion_factory, **changes)
    outcome = service(ingestion_factory).ingest_and_create_entry_order(make_request())
    assert outcome.outcome is PaperCommandIngestionOutcome.POLICY_MISMATCH
    assert counts(ingestion_factory)["command"] == 0


def test_policy_not_found_has_zero_graph_mutation(ingestion_factory):
    outcome = service(ingestion_factory).ingest_and_create_entry_order(make_request())
    assert outcome.outcome is PaperCommandIngestionOutcome.POLICY_NOT_FOUND
    assert counts(ingestion_factory)["command"] == 0


class FaultingUow(PaperUnitOfWork):
    stage = ""

    def __enter__(self):
        entered = super().__enter__()

        def inject(current):
            if current == self.stage:
                raise RuntimeError("bounded injected fault")

        self.repositories.fault_injector = inject
        return entered


@pytest.mark.parametrize(
    "stage",
    [
        "ingestion_after_command",
        "ingestion_after_order_created",
        "ingestion_after_order_validated",
        "ingestion_after_order_opened",
    ],
)
def test_fault_at_every_persistence_boundary_rolls_back_all(
    ingestion_factory, stage
):
    seed_policy(ingestion_factory)
    FaultingUow.stage = stage
    outcome = service(
        ingestion_factory, uow_type=FaultingUow
    ).ingest_and_create_entry_order(make_request())
    assert outcome.outcome is PaperCommandIngestionOutcome.INTERNAL_INVARIANT_FAILURE
    assert counts(ingestion_factory) == {
        "policy": 1,
        "command": 0,
        "order": 0,
        "event": 0,
        "journal": 0,
        "fill": 0,
        "position": 0,
    }


def test_existing_command_without_order_is_not_repaired(ingestion_factory):
    seed_policy(ingestion_factory)
    request = make_request()
    expected = service(ingestion_factory)._build_expected(request)
    with PaperUnitOfWork(ingestion_factory) as uow:
        assert uow.repositories.commands.create_or_get_command(
            expected.command, event_id=request.command_event_id
        ).outcome is RepositoryOutcome.CREATED
        assert uow.commit().outcome is RepositoryOutcome.UPDATED
    before = counts(ingestion_factory)
    outcome = service(ingestion_factory).ingest_and_create_entry_order(request)
    assert outcome.outcome is PaperCommandIngestionOutcome.EXISTING_GRAPH_INCONSISTENT
    assert counts(ingestion_factory) == before


def test_missing_opened_journal_is_not_repaired(ingestion_factory):
    seed_policy(ingestion_factory)
    request = make_request()
    assert service(ingestion_factory).ingest_and_create_entry_order(
        request
    ).successful
    with ingestion_factory.begin() as session:
        session.execute(
            delete(PaperJournalEntryRecord).where(
                PaperJournalEntryRecord.journal_entry_id
                == request.order_opened_event_id
            )
        )
    before = counts(ingestion_factory)
    outcome = service(ingestion_factory).ingest_and_create_entry_order(request)
    assert outcome.outcome is PaperCommandIngestionOutcome.EXISTING_GRAPH_INCONSISTENT
    assert counts(ingestion_factory) == before


def test_identical_concurrency_commits_one_graph(ingestion_factory):
    seed_policy(ingestion_factory)
    request = make_request()
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(
            pool.map(
                lambda _: service(ingestion_factory).ingest_and_create_entry_order(
                    request
                ),
                range(2),
            )
        )
    assert sorted(item.outcome.value for item in outcomes) == sorted(
        [
            PaperCommandIngestionOutcome.COMMAND_AND_ORDER_CREATED.value,
            PaperCommandIngestionOutcome.COMMAND_AND_ORDER_ALREADY_EXIST.value,
        ]
    )
    assert counts(ingestion_factory)["command"] == 1
    assert counts(ingestion_factory)["event"] == 3


def test_conflicting_concurrency_commits_one_graph(ingestion_factory):
    seed_policy(ingestion_factory)
    first = make_request(identity_suffix="first")
    second_chain = make_chain(approved_at=APPROVED_AT + timedelta(microseconds=1))
    second = make_request(
        chain=second_chain,
        identity_suffix="second",
        created_at=CREATED_AT + timedelta(microseconds=1),
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(
            pool.map(
                lambda request: service(
                    ingestion_factory
                ).ingest_and_create_entry_order(request),
                (first, second),
            )
        )
    assert {item.outcome for item in outcomes} == {
        PaperCommandIngestionOutcome.COMMAND_AND_ORDER_CREATED,
        PaperCommandIngestionOutcome.IDEMPOTENCY_CONFLICT,
    }
    assert counts(ingestion_factory)["command"] == 1
    assert counts(ingestion_factory)["order"] == 1


class CommittedButUncertainUow(PaperUnitOfWork):
    def commit(self):
        committed = super().commit()
        assert committed.outcome is RepositoryOutcome.UPDATED
        return result(
            RepositoryOutcome.UNCERTAIN_COMMIT_UNRESOLVED,
            reason_code="PAPER_DB_COMMIT_OUTCOME_UNKNOWN",
        )


class RolledBackUncertainUow(PaperUnitOfWork):
    def commit(self):
        self.rollback()
        return result(
            RepositoryOutcome.UNCERTAIN_COMMIT_UNRESOLVED,
            reason_code="PAPER_DB_COMMIT_OUTCOME_UNKNOWN",
        )


def test_uncertain_commit_matching_graph_uses_fresh_sessions(ingestion_factory):
    seed_policy(ingestion_factory)
    calls = []

    def fresh():
        calls.append(object())
        return ingestion_factory()

    outcome = service(
        ingestion_factory,
        uow_type=CommittedButUncertainUow,
        recovery_factory=fresh,
    ).ingest_and_create_entry_order(make_request())
    assert outcome.outcome is (
        PaperCommandIngestionOutcome.UNCERTAIN_COMMIT_RESOLVED_COMMITTED
    )
    assert len(calls) == 1


def test_uncertain_commit_absent_is_resolved_without_blind_replay(ingestion_factory):
    seed_policy(ingestion_factory)
    outcome = service(
        ingestion_factory,
        uow_type=RolledBackUncertainUow,
    ).ingest_and_create_entry_order(make_request())
    assert outcome.outcome is (
        PaperCommandIngestionOutcome.UNCERTAIN_COMMIT_RESOLVED_NOT_COMMITTED
    )
    assert counts(ingestion_factory)["command"] == 0


def test_uncertain_commit_lookup_unavailable_is_bounded_to_three(ingestion_factory):
    seed_policy(ingestion_factory)
    calls = []

    def unavailable():
        calls.append(object())
        raise RuntimeError("lookup unavailable")

    outcome = service(
        ingestion_factory,
        uow_type=RolledBackUncertainUow,
        recovery_factory=unavailable,
    ).ingest_and_create_entry_order(make_request())
    assert outcome.outcome is PaperCommandIngestionOutcome.UNCERTAIN_COMMIT_UNRESOLVED
    assert len(calls) == 3
    assert counts(ingestion_factory)["command"] == 0


def test_created_graph_has_order_execution_request_shape_without_execution(
    ingestion_factory,
):
    seed_policy(ingestion_factory)
    request = make_request()
    outcome = service(ingestion_factory).ingest_and_create_entry_order(request)
    assert outcome.successful
    execution_request = PaperEntryExecutionRequest(
        command_id=request.command_id,
        order_id=request.order_id,
        expected_order_version=2,
        fill_role=PaperFillRole.ENTRY,
        candidate_candles=(),
        market_snapshot_closed_until_ms=CLOSED,
        simulation_policy=request.simulation_policy,
        price_quantum=Q,
        fee_quantum=Q,
        quote_asset="USDT",
        fill_id="fill:future:entry",
        order_event_id="event:future:fill-order",
        position_event_id="event:future:open-position",
        journal_entry_ids=(
            "journal:future:fill-order",
            "journal:future:open-position",
        ),
        correlation_id=request.command_id,
        causation_id=request.order_id,
        operation_at=CREATED_AT,
        position_id="position:future:entry",
    )
    assert execution_request.expected_order_version == 2
    assert counts(ingestion_factory)["fill"] == 0
    assert counts(ingestion_factory)["position"] == 0
