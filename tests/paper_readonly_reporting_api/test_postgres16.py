from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from threading import Event, Thread

from alembic import command
from alembic.config import Config
from sqlalchemy import event, text

from app.engine_paper.accounting import PaperAccountBaseline, PaperAccountIdentity
from app.engine_execution.paper_idempotency import exit_decision_idempotency_key, fill_idempotency_key
from app.engine_execution.paper_state_machine import fill_order
from app.engine_exit.paper_exit import create_exit_decision
from app.engine_paper.unit_of_work import PaperUnitOfWork
from app.engine_paper.repository_results import RepositoryOutcome
from app.engine_position.paper_state_machine import apply_close_fill
from app.engine_safety.paper_domain import PaperExitCause, PaperReasonCode
from app.server_api.errors import ApiError
from app.server_api.repositories.sqlalchemy_read import SqlAlchemyReadAdapter
from app.server_api.services.paper_reporting import PaperReadonlyReportingService
from tests.paper_domain.conftest import make_fill
from tests.paper_repository.test_atomic_lifecycle_and_concurrency import _apply_entry, _open_order, _prepare_close


NOW = datetime(2026, 8, 11, tzinfo=timezone.utc)


def test_real_pg16_0008_gate_and_0012_full_reporting_lifecycle(reporting_pg_engine, reporting_sessions):
    adapter = SqlAlchemyReadAdapter(reporting_sessions)
    observed = []
    event.listen(reporting_pg_engine, "before_cursor_execute", lambda _c, _u, statement, *_a: observed.append(statement.lower()))
    assert adapter.schema_revision() == "0008_engine_orchestrator_freshness_retry"
    service = PaperReadonlyReportingService(adapter)
    assert service.readiness().status == "PAPER_SCHEMA_NOT_DEPLOYED"
    assert not [statement for statement in observed if "paper_" in statement]

    command.upgrade(Config("alembic.ini"), "0013_paper_first_canary_correlation")
    with reporting_pg_engine.begin() as connection:
        connection.execute(text("TRUNCATE paper_account_baselines, paper_exit_evaluation_cursors, paper_journal_entries, paper_exit_decisions, paper_positions, paper_fills, paper_order_events, paper_orders, paper_execution_commands, paper_simulation_policies RESTART IDENTITY CASCADE"))
    baseline = PaperAccountBaseline("baseline:reporting", PaperAccountIdentity("paper-primary", "session-001"), Decimal("100"), NOW)
    with PaperUnitOfWork(reporting_sessions) as uow:
        uow.repositories.account_baselines.create_if_absent(baseline)
        decision, order, fill, order_event, position_event = _prepare_close(uow)
        result = uow.repositories.apply_close_fill_and_close_position(
            decision.exit_decision_id, decision.position_id, 1, order.order_id, 2,
            fill, (order_event, position_event), (order_event, position_event),
        )
        assert result.successful and uow.commit().successful

    assert adapter.schema_revision() == "0013_paper_first_canary_correlation"
    observed.clear()
    account = service.account()
    account_queries = len(observed)
    assert account.initial_balance == "100" and account.closed_trade_count == 1
    observed.clear()
    positions = service.positions(limit=50, cursor=None, state=None, symbol=None)
    positions_queries = len(observed)
    assert len(positions.items) == 1 and positions.items[0].state == "CLOSED"
    observed.clear()
    trades = service.trades(limit=50, cursor=None, symbol=None, side=None, exit_reason=None, from_value=None, to_value=None)
    trades_queries = len(observed)
    assert len(trades.items) == 1
    observed.clear()
    report = service.trade_report(positions.items[0].position_id)
    report_queries = len(observed)
    assert report.net_pnl == positions.items[0].realized_pnl
    assert service.reconciliation().overall_status == "HEALTHY"
    assert account_queries <= 12
    assert positions_queries <= 6
    assert trades_queries <= 8
    assert report_queries <= 12


def test_real_pg16_atomic_close_report_race_is_never_partial(reporting_pg_engine, reporting_sessions):
    with reporting_pg_engine.begin() as connection:
        connection.execute(text("TRUNCATE paper_account_baselines, paper_exit_evaluation_cursors, paper_journal_entries, paper_exit_decisions, paper_positions, paper_fills, paper_order_events, paper_orders, paper_execution_commands, paper_simulation_policies RESTART IDENTITY CASCADE"))
    baseline = PaperAccountBaseline("baseline:race", PaperAccountIdentity("paper-primary", "session-001"), Decimal("100"), NOW)
    with PaperUnitOfWork(reporting_sessions) as uow:
        uow.repositories.account_baselines.create_if_absent(baseline)
        opened, command_value, _, position = _apply_entry(uow, "race")
        assert opened.successful and uow.commit().successful

    prepared, release = Event(), Event()
    outcome = {}

    def close_writer():
        with PaperUnitOfWork(reporting_sessions) as uow:
            current = uow.repositories.positions.get_position(position.position_id)
            close_order = _open_order(uow, command_value, "race-close", role="EXIT")
            decision, exit_event = create_exit_decision(
                current, exit_decision_id="exit:race",
                idempotency_key=exit_decision_idempotency_key(current.position_id, current.version, PaperExitCause.STOP_LOSS),
                expected_position_version=0, cause=PaperExitCause.STOP_LOSS,
                decision_price=Decimal("90"), source_closed_until_ms=1120, decided_at=NOW,
                reason_code=PaperReasonCode.PAPER_EXIT_STOP_LOSS_TRIGGERED, event_id="event:exit:race",
            )
            created = uow.repositories.exits.create_or_get_exit_decision(current.position_id, 0, decision, exit_event, exit_event)
            assert created.outcome is RepositoryOutcome.CREATED
            close_fill = make_fill(fill_id="fill:race:close", order_id=close_order.order_id,
                idempotency_key=fill_idempotency_key(close_order.order_id, "EXIT"), price=Decimal("90"), source_closed_until_ms=1120)
            order_change = fill_order(close_order, close_fill, expected_version=2, event_id="event:race:close-order")
            closing = uow.repositories.positions.get_position(current.position_id)
            position_change = apply_close_fill(closing, close_fill, expected_version=1, event_id="event:race:position-closed")
            applied = uow.repositories.apply_close_fill_and_close_position(
                decision.exit_decision_id, decision.position_id, 1, close_order.order_id, 2, close_fill,
                (order_change.events[0], position_change.events[0]),
                (order_change.events[0], position_change.events[0]),
            )
            assert applied.successful
            prepared.set()
            assert release.wait(10)
            outcome["commit"] = uow.commit().successful

    thread = Thread(target=close_writer)
    thread.start()
    assert prepared.wait(10)
    service = PaperReadonlyReportingService(SqlAlchemyReadAdapter(reporting_sessions))
    try:
        service.trade_report(position.position_id)
        before = "COMPLETE"
    except ApiError as error:
        before = error.code
    release.set()
    thread.join(10)
    assert not thread.is_alive() and outcome == {"commit": True}
    after = service.trade_report(position.position_id)
    assert before == "FINAL_REPORT_NOT_AVAILABLE"
    assert after.position_id == position.position_id and after.total_fees is not None
