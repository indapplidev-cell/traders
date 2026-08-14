from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.db.paper_models import PaperFirstCanarySessionRecord
from app.engine_paper.first_canary_correlation import (
    CanaryCorrelationError,
    PaperFirstCanaryRepository,
    PaperFirstCanaryState,
    SqlAlchemyPaperFirstCanaryStore,
)
from app.engine_paper.repository_results import RepositoryOutcome
from app.engine_paper.unit_of_work import PaperUnitOfWork
from app.engine_execution.paper_idempotency import (
    exit_decision_idempotency_key,
    fill_idempotency_key,
)
from app.engine_execution.paper_state_machine import fill_order
from app.engine_exit.paper_exit import create_exit_decision
from app.engine_position.paper_state_machine import apply_close_fill, apply_entry_fill
from app.engine_safety.paper_domain import (
    PaperExitCause,
    PaperPositionState,
    PaperReasonCode,
    PaperSide,
)
from app.engine_safety.paper_production_control import PaperProductionSafetyControl
from app.operator_control.config import PaperOperatorControlConfig, PaperOperatorControlOperationMode
from app.operator_control.schemas import PaperOperatorArmFirstCanaryRequest, PaperOperatorStartFirstCanaryRequest
from app.operator_control.service import PaperOperatorArmReadiness, PaperOperatorControlService
from app.server_api.repositories.sqlalchemy_read import SqlAlchemyReadAdapter
from app.server_api.services.paper_reporting import PaperReadonlyReportingService
from tests.paper_domain.conftest import make_command
from tests.paper_domain.conftest import make_fill
from tests.paper_repository.test_atomic_lifecycle_and_concurrency import (
    _command,
    _cursor,
    _open_order,
)


NOW = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)


def _store(factory):
    return SqlAlchemyPaperFirstCanaryStore(factory)


def _reserve(store, request_id="arm-request-0001", symbols=("BTCUSDT",)):
    return store.reserve_arm(
        request_id=request_id,
        fingerprint=f"fingerprint-{request_id}",
        expected_generation=1,
        allowed_symbols=symbols,
        now=NOW,
    )


def test_empty_exact_lookup_and_durable_arm_restart(canary_sessions) -> None:
    first_store = _store(canary_sessions)
    assert first_store.current() is None
    assert first_store.get(str(uuid4())) is None
    reserved = _reserve(first_store)
    assert reserved.state is PaperFirstCanaryState.RESERVED
    armed = first_store.complete_arm(
        reserved.canary_id, "00000000-0000-4000-8000-000000000111", 2, NOW
    )
    assert armed.state is PaperFirstCanaryState.ARMED

    restarted_store = _store(canary_sessions)
    recovered = restarted_store.get(armed.canary_id)
    assert recovered == armed
    assert restarted_store.get_by_arm_request("arm-request-0001") == armed
    assert _reserve(restarted_store).canary_id == armed.canary_id


def test_active_uniqueness_and_request_conflict(canary_sessions) -> None:
    store = _store(canary_sessions)
    first = _reserve(store)
    with pytest.raises(CanaryCorrelationError, match="CANARY_ALREADY_ACTIVE"):
        _reserve(store, "arm-request-0002")
    with pytest.raises(CanaryCorrelationError, match="REQUEST_ID_CONFLICT"):
        store.reserve_arm(
            request_id="arm-request-0001", fingerprint="different", expected_generation=1,
            allowed_symbols=("BTCUSDT",), now=NOW,
        )
    assert store.current().canary_id == first.canary_id


class NoApprovalExecutor:
    def preflight(self, **_kwargs):
        return ("NO_ELIGIBLE_APPROVAL",)

    def start_bounded_canary(self, **_kwargs):
        raise AssertionError("no-trade path must not start the worker")

    def status(self):
        raise AssertionError("durable store owns status")


def _control_service(tmp_path: Path, factory, executor=None):
    control = PaperProductionSafetyControl(tmp_path, acl_checker=lambda _path: True)
    if not control.state_path.exists():
        control.initialize_disabled(acknowledge=True)
    config = PaperOperatorControlConfig(
        enabled=True,
        operation_mode=PaperOperatorControlOperationMode.ISOLATED_CONTROL_ROOT,
    )
    return control, PaperOperatorControlService(
        config=config, control=control, readiness=PaperOperatorArmReadiness.isolated_ready,
        executor=executor or NoApprovalExecutor(), canary_store=_store(factory),
    )


def test_uncertain_arm_and_start_are_exactly_recoverable_after_service_restart(canary_sessions, tmp_path) -> None:
    control, service = _control_service(tmp_path / "control", canary_sessions)
    arm_request = PaperOperatorArmFirstCanaryRequest(
        request_id="uncertain-arm-0001", expected_generation=1, environment="PRODUCTION",
        mode="PAPER", max_new_commands=1, max_open_positions=1,
        allowed_symbols=("BTCUSDT",), operator_acknowledgement=True,
        paper_acknowledgement=True, live_forbidden_acknowledgement=True,
    )
    arm = service.arm_first_canary(arm_request)
    assert arm.canary_id and arm.arming_transition_id

    # The response is treated as lost. A new service object recovers by exact ID/request.
    _, restarted = _control_service(tmp_path / "control", canary_sessions)
    status = restarted.canary_status(canary_id=arm.canary_id)
    assert status.canary_id == arm.canary_id
    assert status.arming_transition_id == arm.arming_transition_id
    assert restarted.canary_status(arm_request_id=arm_request.request_id).canary_id == arm.canary_id

    start_request = PaperOperatorStartFirstCanaryRequest(
        request_id="uncertain-start-0001", expected_generation=arm.generation_after,
        canary_id=arm.canary_id, arming_transition_id=arm.arming_transition_id,
        canary_acknowledgement=True,
    )
    start = restarted.start_first_canary(start_request)
    assert start.canary_id == arm.canary_id
    assert start.executed is False

    _, restarted_again = _control_service(tmp_path / "control", canary_sessions)
    recovered = restarted_again.canary_status(canary_id=arm.canary_id)
    assert recovered.state.value == "WAITING_FOR_ELIGIBLE_APPROVAL"
    assert recovered.availability_code == "NO_ELIGIBLE_APPROVAL"
    assert recovered.command_count == recovered.position_count == 0
    replay = restarted_again.start_first_canary(start_request)
    assert replay.canary_id == arm.canary_id
    assert replay.executed is False


def test_command_link_is_same_uow_idempotent_and_budget_fail_closed(canary_sessions) -> None:
    store = _store(canary_sessions)
    reserved = _reserve(store)
    armed = store.complete_arm(
        reserved.canary_id, "00000000-0000-4000-8000-000000000222", 2, NOW
    )
    store.reserve_start(armed.canary_id, "start-request-0001", "start-fingerprint", armed.arming_transition_id, 2)
    store.mark_started(armed.canary_id, no_approval=False, now=NOW)

    command = make_command(symbol="BTCUSDT")
    with PaperUnitOfWork(canary_sessions) as uow:
        result = uow.repositories.commands.create_or_get_command(
            command, canary_id=armed.canary_id
        )
        assert result.outcome is RepositoryOutcome.CREATED
        assert uow.commit().successful
    linked = store.get(armed.canary_id)
    assert linked.command_count == 1
    assert linked.command_id == command.command_id

    with PaperUnitOfWork(canary_sessions) as uow:
        replay = uow.repositories.commands.create_or_get_command(
            command, canary_id=armed.canary_id
        )
        assert replay.outcome is RepositoryOutcome.EXISTING_IDEMPOTENT

    with canary_sessions() as session:
        repo = PaperFirstCanaryRepository(session)
        failed = repo.link_command(armed.canary_id, "different-command", "BTCUSDT")
        assert failed.state is PaperFirstCanaryState.FAILED_SAFE
        assert failed.terminal_reason == "FIRST_CANARY_COMMAND_BUDGET_VIOLATION"
        session.commit()
    assert store.get(armed.canary_id).command_id == command.command_id


def test_symbol_violation_is_fail_safe_without_replacement(canary_sessions) -> None:
    store = _store(canary_sessions)
    session = _reserve(store, symbols=("BTCUSDT",))
    with canary_sessions() as db:
        failed = PaperFirstCanaryRepository(db).link_command(
            session.canary_id, "outside-command", "ETHUSDT"
        )
        assert failed.state is PaperFirstCanaryState.FAILED_SAFE
        assert failed.command_id is None
        assert failed.finding_codes == ("FIRST_CANARY_SYMBOL_SCOPE_VIOLATION",)
        db.commit()


def test_position_link_is_derived_from_exact_command_in_same_uow(canary_sessions) -> None:
    store = _store(canary_sessions)
    reserved = _reserve(store)
    armed = store.complete_arm(
        reserved.canary_id, "00000000-0000-4000-8000-000000000333", 2, NOW
    )
    store.reserve_start(armed.canary_id, "start-request-0001", "start-fingerprint", armed.arming_transition_id, 2)
    store.mark_started(armed.canary_id, no_approval=False, now=NOW)
    command = _command("canary")
    with PaperUnitOfWork(canary_sessions) as uow:
        assert uow.repositories.commands.create_or_get_command(
            command, canary_id=armed.canary_id
        ).outcome is RepositoryOutcome.CREATED
        order = _open_order(uow, command, "canary")
        fill = make_fill(
            fill_id="fill:canary:entry", order_id=order.order_id,
            idempotency_key=fill_idempotency_key(order.order_id, "ENTRY"),
            source_closed_until_ms=60_000,
        )
        order_change = fill_order(
            order, fill, expected_version=2, event_id="event:canary:entry-fill"
        )
        position_change = apply_entry_fill(
            None, command, order_change.order, fill,
            position_id="position:canary", event_id="event:canary:position-open",
        )
        result = uow.repositories.apply_entry_fill_and_open_position(
            order.order_id, 2, fill, position_change.position,
            _cursor(fill, position_change.position), order_change.events[0],
            position_change.events[0], (order_change.events[0], position_change.events[0]),
        )
        assert result.outcome is RepositoryOutcome.CREATED
        assert uow.commit().successful
    linked = store.get(armed.canary_id)
    assert linked.command_id == command.command_id
    assert linked.position_id == "position:canary"
    assert linked.position_count == 1
    assert linked.state is PaperFirstCanaryState.POSITION_OPEN


@pytest.mark.parametrize("side", [PaperSide.LONG, PaperSide.SHORT])
def test_full_long_short_closed_report_reconciliation_and_terminal_correlation(canary_sessions, side) -> None:
    store = _store(canary_sessions)
    reserved = _reserve(store)
    armed = store.complete_arm(
        reserved.canary_id, "00000000-0000-4000-8000-000000000444", 2, NOW
    )
    store.reserve_start(armed.canary_id, "start-request-0001", "start-fingerprint", armed.arming_transition_id, 2)
    store.mark_started(armed.canary_id, no_approval=False, now=NOW)
    command = make_command(side=side, command_id=f"command:{side.value.lower()}")

    with PaperUnitOfWork(canary_sessions) as uow:
        assert uow.repositories.commands.create_or_get_command(
            command, canary_id=armed.canary_id
        ).outcome is RepositoryOutcome.CREATED
        entry_order = _open_order(uow, command, f"{side.value.lower()}:entry")
        entry_fill = make_fill(
            fill_id=f"fill:{side.value.lower()}:entry", order_id=entry_order.order_id,
            idempotency_key=fill_idempotency_key(entry_order.order_id, "ENTRY"),
            symbol=command.symbol, side=side, source_closed_until_ms=60_000,
        )
        entry_order_change = fill_order(
            entry_order, entry_fill, expected_version=2,
            event_id=f"event:{side.value.lower()}:entry-fill",
        )
        position_change = apply_entry_fill(
            None, command, entry_order_change.order, entry_fill,
            position_id=f"position:{side.value.lower()}",
            event_id=f"event:{side.value.lower()}:position-open",
        )
        opened = uow.repositories.apply_entry_fill_and_open_position(
            entry_order.order_id, 2, entry_fill, position_change.position,
            _cursor(entry_fill, position_change.position), entry_order_change.events[0],
            position_change.events[0],
            (entry_order_change.events[0], position_change.events[0]),
        )
        assert opened.outcome is RepositoryOutcome.CREATED
        position = opened.value.position

        close_order = _open_order(uow, command, f"{side.value.lower()}:exit", role="EXIT")
        decision, exit_event = create_exit_decision(
            position,
            exit_decision_id=f"exit:{side.value.lower()}",
            idempotency_key=exit_decision_idempotency_key(
                position.position_id, position.version, PaperExitCause.STOP_LOSS
            ),
            expected_position_version=0,
            cause=PaperExitCause.STOP_LOSS,
            decision_price=Decimal("90") if side is PaperSide.LONG else Decimal("110"),
            source_closed_until_ms=120_000,
            decided_at=NOW,
            reason_code=PaperReasonCode.PAPER_EXIT_STOP_LOSS_TRIGGERED,
            event_id=f"event:{side.value.lower()}:exit",
        )
        assert uow.repositories.exits.create_or_get_exit_decision(
            position.position_id, 0, decision, exit_event, exit_event
        ).outcome is RepositoryOutcome.CREATED
        close_fill = make_fill(
            fill_id=f"fill:{side.value.lower()}:exit", order_id=close_order.order_id,
            idempotency_key=fill_idempotency_key(close_order.order_id, "EXIT"),
            symbol=command.symbol, side=side,
            price=Decimal("90") if side is PaperSide.LONG else Decimal("110"),
            source_closed_until_ms=120_000,
        )
        close_order_change = fill_order(
            close_order, close_fill, expected_version=2,
            event_id=f"event:{side.value.lower()}:close-order",
        )
        closing = replace(
            position, state=PaperPositionState.CLOSING, version=1,
            reason_code=PaperReasonCode.PAPER_POSITION_CLOSING,
        )
        closed_change = apply_close_fill(
            closing, close_fill, expected_version=1,
            event_id=f"event:{side.value.lower()}:position-closed",
        )
        closed = uow.repositories.apply_close_fill_and_close_position(
            decision.exit_decision_id, position.position_id, 1,
            close_order.order_id, 2, close_fill,
            (close_order_change.events[0], closed_change.events[0]),
            (close_order_change.events[0], closed_change.events[0]),
        )
        assert closed.outcome is RepositoryOutcome.UPDATED
        assert uow.commit().successful

    reporting = PaperReadonlyReportingService(SqlAlchemyReadAdapter(canary_sessions))
    report = reporting.trade_report(f"position:{side.value.lower()}")
    assert report.position_id == f"position:{side.value.lower()}"
    assert report.side == side.value
    reconciliation = reporting.reconciliation()
    assert reconciliation.paper_reconciliation.status == "HEALTHY"
    assert reconciliation.accounting_reconciliation.status == "HEALTHY"

    pending = store.refresh_terminal(
        armed.canary_id, control_state="ARMED", control_generation=2,
        report_available=True, paper_reconciliation_status="HEALTHY",
        accounting_reconciliation_status="HEALTHY", checked_at=NOW,
    )
    assert pending.state is PaperFirstCanaryState.RECONCILIATION_PENDING
    completed = store.refresh_terminal(
        armed.canary_id, control_state="DISABLED", control_generation=3,
        report_available=True, paper_reconciliation_status="HEALTHY",
        accounting_reconciliation_status="HEALTHY", checked_at=NOW,
    )
    assert completed.state is PaperFirstCanaryState.COMPLETED
    assert completed.position_id == report.position_id
    assert completed.trade_report_available is True


def test_corrupt_counter_fails_closed_on_status(canary_sessions) -> None:
    store = _store(canary_sessions)
    reserved = _reserve(store)
    with canary_sessions() as session:
        row = session.get(PaperFirstCanarySessionRecord, reserved.canary_id)
        row.command_count = 1
        # Disable DB check only for the transaction-local corruption probe by
        # invoking the mapper before flush; status must refuse to guess.
        with session.no_autoflush:
            with pytest.raises(CanaryCorrelationError, match="CANARY_CORRELATION_UNAVAILABLE"):
                PaperFirstCanaryRepository(session).get(reserved.canary_id)
        session.rollback()


def test_exact_pk_lookup_is_bounded(canary_sessions) -> None:
    store = _store(canary_sessions)
    row = _reserve(store)
    for _ in range(10):
        assert store.get(row.canary_id).canary_id == row.canary_id
    with canary_sessions() as session:
        assert session.scalar(select(func.count()).select_from(PaperFirstCanarySessionRecord)) == 1
