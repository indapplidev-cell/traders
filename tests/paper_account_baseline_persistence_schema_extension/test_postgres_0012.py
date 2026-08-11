from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
from threading import Barrier

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select, text

from app.db.paper_models import PaperAccountBaselineRecord
from app.engine_paper.accounting import (
    PaperAccountBaseline,
    PaperAccountBaselineService,
    PaperAccountIdentity,
    PaperAccountingError,
    PaperAccountingFinding,
    PaperAccountingOutcome,
    PaperAccountingReconciliationService,
)
from app.engine_paper.baseline_repository import baseline_semantically_equal
from app.engine_paper.commit_recovery import recover_uncertain_commit
from app.engine_paper.repository_results import RepositoryOutcome
from app.engine_paper.unit_of_work import PaperUnitOfWork
from app.engine_safety.paper_domain import PaperSide
from tests.paper_account_balance_trade_reporting.conftest import make_trade
from tests.paper_repository.test_atomic_lifecycle_and_concurrency import _apply_entry, _command


UTC = timezone.utc
NOW = datetime(2026, 8, 11, tzinfo=UTC)


def _baseline(amount: str = "100", suffix: str = "1") -> PaperAccountBaseline:
    return PaperAccountBaseline(
        f"baseline:{suffix}", PaperAccountIdentity("paper-primary", "session-001"),
        Decimal(amount), NOW,
    )


def test_real_pg16_migration_rehearsals_preserve_graph_and_nonpaper_data(baseline_pg_engine):
    config = Config("alembic.ini")
    command.downgrade(config, "0011_paper_close_causal_boundary_and_exit_evaluation_cursor")
    factory = __import__("sqlalchemy.orm", fromlist=["sessionmaker"]).sessionmaker(
        bind=baseline_pg_engine, autoflush=False, autocommit=False
    )
    with PaperUnitOfWork(factory) as uow:
        created, _, _, _ = _apply_entry(uow, "migration")
        assert created.outcome is RepositoryOutcome.CREATED
        assert uow.commit().successful
    tables = ("paper_execution_commands", "paper_orders", "paper_fills",
              "paper_positions", "paper_journal_entries")
    with baseline_pg_engine.connect() as connection:
        before = tuple(connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
                       for table in tables)
    assert all(count > 0 for count in before)
    command.upgrade(config, "0012_paper_account_baseline")
    with baseline_pg_engine.connect() as connection:
        after = tuple(connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
                      for table in tables)
        assert connection.execute(text("SELECT count(*) FROM paper_account_baselines")).scalar_one() == 0
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0012_paper_account_baseline"
    assert after == before
    with PaperUnitOfWork(factory) as uow:
        with pytest.raises(PaperAccountingError) as denied:
            uow.repositories.account_baselines.create_if_absent(_baseline())
        assert denied.value.finding is PaperAccountingFinding.BASELINE_AFTER_ECONOMIC_ACTIVITY_DENIED

    command.downgrade(config, "0008_engine_orchestrator_freshness_retry")
    with baseline_pg_engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO online_pipeline_runs "
            "(run_id,symbol,primary_timeframe,closed_until_ms,closed_until_utc,status,"
            "trigger_source,daemon_instance_id) VALUES "
            "('baseline-rehearsal','BTCUSDT','1m',1,:at,'COMPLETED','TEST','isolated')"
        ), {"at": NOW})
    command.upgrade(config, "0012_paper_account_baseline")
    with baseline_pg_engine.begin() as connection:
        assert connection.execute(text(
            "SELECT count(*) FROM online_pipeline_runs WHERE run_id='baseline-rehearsal'"
        )).scalar_one() == 1
        assert connection.execute(text("SELECT count(*) FROM paper_account_baselines")).scalar_one() == 0
        connection.execute(text("DELETE FROM online_pipeline_runs WHERE run_id='baseline-rehearsal'"))


def test_0012_constraints_numeric_and_destructive_downgrade_classification(baseline_pg_engine):
    inspector = inspect(baseline_pg_engine)
    columns = {column["name"]: column for column in inspector.get_columns("paper_account_baselines")}
    assert set(columns) == {"baseline_id", "account_id", "accounting_session_id",
                            "currency", "initial_balance", "initialized_at", "semantic_version"}
    assert columns["initial_balance"]["type"].precision == 38
    assert columns["initial_balance"]["type"].scale == 18
    constraints = {item["name"] for item in inspector.get_check_constraints("paper_account_baselines")}
    assert {"ck_paper_account_baseline_currency",
            "ck_paper_account_baseline_initial_balance",
            "ck_paper_account_baseline_identities"} <= constraints
    uniques = {item["name"] for item in inspector.get_unique_constraints("paper_account_baselines")}
    assert "uq_paper_account_baselines_account_session" in uniques


def test_persist_replay_conflict_and_uncertain_commit_recovery(baseline_session_factory):
    requested = _baseline()
    with PaperUnitOfWork(baseline_session_factory) as uow:
        assert uow.repositories.account_baselines.create_if_absent(requested) == requested
        assert uow.commit().successful
    with PaperUnitOfWork(baseline_session_factory) as uow:
        replay = uow.repositories.account_baselines.create_if_absent(
            _baseline("100", "different-request")
        )
        assert replay.baseline_id == requested.baseline_id
        assert uow.commit().successful
    with PaperUnitOfWork(baseline_session_factory) as uow:
        with pytest.raises(PaperAccountingError) as conflict:
            uow.repositories.account_baselines.create_if_absent(_baseline("101", "conflict"))
        assert conflict.value.finding is PaperAccountingFinding.BASELINE_IMMUTABILITY_VIOLATION
    recovered = recover_uncertain_commit(
        baseline_session_factory,
        lambda session: __import__(
            "app.engine_paper.baseline_repository", fromlist=["PaperAccountBaselineRepository"]
        ).PaperAccountBaselineRepository(session).get("paper-primary", "session-001"),
        requested,
        baseline_semantically_equal,
    )
    assert recovered.outcome is RepositoryOutcome.UNCERTAIN_COMMIT_RESOLVED_COMMITTED
    with baseline_session_factory() as session:
        assert len(tuple(session.scalars(select(PaperAccountBaselineRecord)))) == 1


@pytest.mark.parametrize("values", (("BTC", "100"), ("USDT", "0"), ("USDT", "-1"), ("USDT", "NaN")))
def test_database_constraints_deny_invalid_values(baseline_session_factory, values):
    currency, amount = values
    with baseline_session_factory() as session, session.begin():
        with pytest.raises(Exception):
            session.execute(text(
                "INSERT INTO paper_account_baselines "
                "(baseline_id,account_id,accounting_session_id,currency,initial_balance,initialized_at,semantic_version) "
                "VALUES ('bad','paper-primary','session-001',:currency,:amount,:at,'PAPER_ACCOUNTING/1.0')"
            ), {"currency": currency, "amount": amount, "at": NOW})


def test_concurrent_same_and_conflicting_initialization(baseline_session_factory):
    barrier = Barrier(2)

    def initialize(amount: str, suffix: str):
        barrier.wait()
        try:
            with PaperUnitOfWork(baseline_session_factory) as uow:
                value = PaperAccountBaselineService(
                    uow.repositories.account_baselines
                ).initialize(
                    baseline_id=f"baseline:{suffix}",
                    identity=PaperAccountIdentity("paper-primary", "session-001"),
                    initial_balance=Decimal(amount), initialized_at=NOW,
                )
                commit = uow.commit()
                return ("OK", value.initial_balance, commit.successful)
        except PaperAccountingError as error:
            return (error.finding.value, None, False)

    with ThreadPoolExecutor(max_workers=2) as pool:
        same = tuple(pool.submit(initialize, "100", str(i)) for i in range(2))
        same_results = tuple(item.result(timeout=10) for item in same)
    assert same_results == (("OK", Decimal("100"), True),) * 2
    with baseline_session_factory() as session, session.begin():
        session.execute(text("TRUNCATE paper_account_baselines"))
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        conflict = (pool.submit(initialize, "100", "winner-a"),
                    pool.submit(initialize, "101", "winner-b"))
        results = tuple(item.result(timeout=10) for item in conflict)
    assert sum(item[0] == "OK" for item in results) == 1
    assert sum(item[0] == PaperAccountingFinding.BASELINE_IMMUTABILITY_VIOLATION.value
               for item in results) == 1


def test_baseline_after_authoritative_activity_is_denied(baseline_session_factory):
    with PaperUnitOfWork(baseline_session_factory) as uow:
        denied = uow.repositories.commands.create_or_get_command(_command("activity"))
        assert denied.outcome is RepositoryOutcome.INVALID_STATE
        assert denied.reason_code == "PAPER_ACCOUNT_BASELINE_REQUIRED_BEFORE_COMMAND"


def test_full_persisted_long_short_breakeven_accounting_lifecycle(baseline_session_factory):
    requested = _baseline()
    with PaperUnitOfWork(baseline_session_factory) as uow:
        assert uow.repositories.account_baselines.create_if_absent(requested) == requested
        assert uow.commit().successful
    trades = (
        make_trade(101, side=PaperSide.LONG, entry_price=Decimal("10"),
                   exit_price=Decimal("12")),
        make_trade(102, side=PaperSide.SHORT, entry_price=Decimal("10"),
                   exit_price=Decimal("12")),
        make_trade(103, side=PaperSide.LONG, entry_price=Decimal("10"),
                   exit_price=Decimal("10"), fee_bps=Decimal("0")),
    )
    with baseline_session_factory() as session:
        repository = __import__(
            "app.engine_paper.baseline_repository", fromlist=["PaperAccountBaselineRepository"]
        ).PaperAccountBaselineRepository(session)
        result = PaperAccountingReconciliationService(
            baseline_persistence=repository
        ).reconcile_persisted(requested.identity, trades)
        persisted = repository.get("paper-primary", "session-001")
    assert result.outcome is PaperAccountingOutcome.HEALTHY
    assert result.summary is not None and len(result.reports) == 3
    assert result.reports[0].net_pnl > 0
    assert result.reports[1].net_pnl < 0
    assert result.reports[2].net_pnl == 0
    assert result.summary.total_fees == sum(
        (report.entry_fee + report.exit_fee for report in result.reports), Decimal("0")
    )
    assert result.summary.realized_net_pnl == sum(
        (report.net_pnl for report in result.reports), Decimal("0")
    )
    assert result.summary.current_balance == requested.initial_balance + result.summary.realized_net_pnl
    assert persisted == requested
