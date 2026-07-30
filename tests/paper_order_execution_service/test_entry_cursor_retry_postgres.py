from __future__ import annotations

from sqlalchemy import delete, func, select

from app.db.paper_models import (
    PaperExitEvaluationCursorRecord,
    PaperJournalEntryRecord,
    PaperOrderEventRecord,
    PaperPositionRecord,
    PaperSimulationPolicyRecord,
)
from app.engine_paper.exit_evaluation_service import (
    PaperExitEvaluationService,
    PaperExitServiceOutcome,
)
from app.engine_paper.order_execution_service import PaperOrderExecutionOutcome
from app.engine_paper.repositories import PaperRepositories
from app.engine_paper.unit_of_work import PaperUnitOfWork
from app.engine_safety import PaperPositionState
from tests.paper_exit_evaluation_retry.conftest import make_request

from .conftest import make_policy
from .test_postgres_service_integration import (
    _entry_request,
    _seed_open_order,
    _service,
)


def test_retry_postgres_preexisting_open_position_without_cursor_fails_closed(
    paper_session_factory,
):
    command, order = _seed_open_order(
        paper_session_factory, suffix="retry-partial-missing-cursor"
    )
    request = _entry_request(
        command, order, suffix="retry-partial-missing-cursor"
    )
    created = _service(paper_session_factory).execute_entry(request)
    assert created.outcome is PaperOrderExecutionOutcome.ENTRY_EXECUTED

    with paper_session_factory.begin() as session:
        session.execute(
            delete(PaperExitEvaluationCursorRecord).where(
                PaperExitEvaluationCursorRecord.position_id
                == request.position_id
            )
        )

    replay = _service(paper_session_factory).execute_entry(request)

    assert (
        replay.outcome
        is PaperOrderExecutionOutcome.EXISTING_ENTRY_GRAPH_INCONSISTENT
    )
    with paper_session_factory() as session:
        assert session.scalar(
            select(func.count()).select_from(PaperExitEvaluationCursorRecord)
        ) == 0
        position = session.get(PaperPositionRecord, request.position_id)
        assert position.state == "OPEN"


def test_retry_postgres_cursor_policy_conflict_is_typed_and_graph_is_unchanged(
    paper_session_factory,
):
    command, order = _seed_open_order(
        paper_session_factory, suffix="retry-policy-conflict"
    )
    request = _entry_request(command, order, suffix="retry-policy-conflict")
    created = _service(paper_session_factory).execute_entry(request)
    assert created.outcome is PaperOrderExecutionOutcome.ENTRY_EXECUTED

    with paper_session_factory.begin() as session:
        row = session.scalar(
            select(PaperExitEvaluationCursorRecord).where(
                PaperExitEvaluationCursorRecord.position_id
                == request.position_id
            )
        )
        row.evaluation_policy_id = "STOP_FIRST_CONSERVATIVE_CONFLICT"

    replay = _service(paper_session_factory).execute_entry(request)

    assert replay.outcome is PaperOrderExecutionOutcome.IDEMPOTENCY_CONFLICT
    with paper_session_factory() as session:
        assert session.scalar(
            select(func.count()).select_from(PaperExitEvaluationCursorRecord)
        ) == 1
        assert session.scalar(
            select(func.count()).select_from(PaperOrderEventRecord)
        ) == 4
        assert session.scalar(
            select(func.count()).select_from(PaperJournalEntryRecord)
        ) == 6


def test_retry_postgres_fresh_entry_is_immediately_exit_evaluator_compatible(
    paper_session_factory,
):
    command, order = _seed_open_order(
        paper_session_factory, suffix="retry-exit-compatible"
    )
    request = _entry_request(command, order, suffix="retry-exit-compatible")
    created = _service(paper_session_factory).execute_entry(request)
    assert created.outcome is PaperOrderExecutionOutcome.ENTRY_EXECUTED

    policy = make_policy()
    with paper_session_factory.begin() as session:
        if session.get(
            PaperSimulationPolicyRecord,
            (policy.simulation_policy_id, 1),
        ) is None:
            session.add(
                PaperSimulationPolicyRecord(
                    policy_id=policy.simulation_policy_id,
                    policy_version=1,
                    status="ACTIVE",
                    price_source=policy.price_source.value,
                    timeframe=policy.timeframe,
                    latency_candles=policy.latency_candles,
                    slippage_bps=policy.slippage_bps,
                    fee_bps=policy.fee_bps,
                    partial_fill_enabled=policy.partial_fill_enabled,
                    future_data_allowed=policy.future_data_allowed,
                    intrabar_conflict_policy=policy.intrabar_conflict_policy.value,
                    configuration_fingerprint=command.configuration_fingerprint,
                    created_at=command.created_at,
                    retired_at=None,
                )
            )

    with paper_session_factory() as session:
        graph = PaperRepositories(session).commands.get_command_graph(
            command.command_id
        ).value
        position = next(
            item for item in graph.positions if item.position_id == request.position_id
        )
        cursor = next(
            item for item in graph.cursors if item.position_id == request.position_id
        )

    exit_request = make_request(
        {"command": command, "position": position},
        cursor,
    )
    actual = PaperExitEvaluationService(
        lambda: PaperUnitOfWork(paper_session_factory),
        paper_session_factory,
    ).evaluate(exit_request)

    assert (
        actual.outcome
        is PaperExitServiceOutcome.NO_EXIT_TRIGGER_CURSOR_ADVANCED
    )
    assert actual.cursor_id == cursor.cursor_id
    assert actual.cursor_version == 1
    with paper_session_factory() as session:
        stored_position = session.get(PaperPositionRecord, request.position_id)
        stored_cursor = session.get(
            PaperExitEvaluationCursorRecord, cursor.cursor_id
        )
        assert stored_position.state == PaperPositionState.OPEN.value
        assert stored_cursor.version == 1
        assert (
            stored_cursor.last_evaluated_closed_until_ms
            == cursor.last_evaluated_closed_until_ms + 60_000
        )
