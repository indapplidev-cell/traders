from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, replace
from decimal import Decimal
import inspect
from pathlib import Path

import pytest

from app.engine_execution.paper_idempotency import (
    PAPER_IDEMPOTENCY_VERSION,
    command_idempotency_key,
    exit_decision_idempotency_key,
    fill_idempotency_key,
    journal_event_idempotency_key,
    order_idempotency_key,
    position_application_key,
)
from app.engine_execution.paper_models import PaperExecutionCommand, PaperFill, PaperOrder
from app.engine_execution.paper_state_machine import (
    command_created_event,
    create_paper_order,
    fill_order,
    transition_order,
)
from app.engine_exit import (
    PAPER_INTRABAR_CONFLICT_POLICY,
    PaperExitDecision,
    create_exit_decision,
    resolve_intrabar_exit,
)
from app.engine_journal import PaperDomainEvent
from app.engine_position import (
    PaperPosition,
    apply_close_fill,
    apply_entry_fill,
    begin_closing,
    fail_position,
    gross_realized_pnl,
    net_realized_pnl,
    return_percentage,
    risk_multiple,
    total_fees,
    unrealized_pnl,
)
from app.engine_safety import (
    PaperDomainError,
    PaperEventType,
    PaperExitCause,
    PaperOrderState,
    PaperPositionState,
    PaperReasonCode,
    PaperSide,
)
from tests.paper_domain.conftest import NOW, make_command, make_created_order, make_fill


def make_entry_graph(*, side=PaperSide.LONG):
    command = make_command(side=side)
    order = make_created_order(command)
    order = transition_order(
        order, PaperOrderState.VALIDATED, expected_version=0, occurred_at=NOW
    ).order
    order = transition_order(
        order, PaperOrderState.OPEN, expected_version=1, occurred_at=NOW
    ).order
    fill = make_fill(
        side=side,
        price=Decimal("100"),
        idempotency_key=fill_idempotency_key(order.order_id, "ENTRY"),
    )
    order = fill_order(order, fill, expected_version=2, event_id="event:entry-filled").order
    position = apply_entry_fill(
        None,
        command,
        order,
        fill,
        position_id="position:1",
        event_id="event:position-opened",
    ).position
    return command, order, fill, position


def test_entry_fill_opens_position_and_emits_event():
    command, order, fill, _ = make_entry_graph()
    result = apply_entry_fill(
        None,
        command,
        order,
        fill,
        position_id="position:2",
        event_id="event:open-2",
    )
    assert result.position.state is PaperPositionState.OPEN
    assert result.position.version == 0
    assert result.position.remaining_quantity == fill.quantity
    assert result.events[0].event_type is PaperEventType.PAPER_POSITION_OPENED


def test_duplicate_entry_fill_is_idempotent():
    command, order, fill, position = make_entry_graph()
    replay = apply_entry_fill(
        position,
        command,
        order,
        fill,
        position_id=position.position_id,
        event_id="event:replay",
    )
    assert replay.applied is False
    assert replay.position is position
    assert replay.reason_code is PaperReasonCode.PAPER_POSITION_DUPLICATE_FILL


def test_different_entry_fill_cannot_mutate_existing_position():
    command, order, fill, position = make_entry_graph()
    with pytest.raises(PaperDomainError):
        apply_entry_fill(
            position,
            command,
            order,
            replace(fill, fill_id="fill:other"),
            position_id=position.position_id,
            event_id="event:other",
        )


def test_open_to_closing_increments_version(position_factory):
    position = position_factory()
    result = begin_closing(
        position,
        expected_version=0,
        exit_decision_id="exit:1",
        occurred_at=NOW,
    )
    assert result.position.state is PaperPositionState.CLOSING
    assert result.position.version == 1
    assert position.state is PaperPositionState.OPEN


def test_closing_to_closed_applies_full_fill(position_factory, fill_factory):
    position = begin_closing(
        position_factory(),
        expected_version=0,
        exit_decision_id="exit:1",
        occurred_at=NOW,
    ).position
    fill = fill_factory(
        fill_id="fill:close",
        order_id="order:close",
        idempotency_key=fill_idempotency_key("order:close", "CLOSE"),
        price=Decimal("110"),
    )
    result = apply_close_fill(position, fill, expected_version=1, event_id="event:closed")
    assert result.position.state is PaperPositionState.CLOSED
    assert result.position.remaining_quantity == 0
    assert result.position.version == 2
    assert result.position.realized_pnl == Decimal("19.6")
    assert result.events[0].event_type is PaperEventType.PAPER_POSITION_CLOSED


def test_partial_close_is_rejected(position_factory, fill_factory):
    position = begin_closing(
        position_factory(),
        expected_version=0,
        exit_decision_id="exit:1",
        occurred_at=NOW,
    ).position
    with pytest.raises(PaperDomainError) as error:
        apply_close_fill(
            position,
            fill_factory(
                fill_id="fill:close",
                order_id="order:close",
                quantity=Decimal("1"),
            ),
            expected_version=1,
            event_id="event:partial-close",
        )
    assert error.value.reason_code is PaperReasonCode.PAPER_FILL_PARTIAL_UNSUPPORTED


def test_duplicate_close_fill_is_idempotent(position_factory, fill_factory):
    closing = begin_closing(
        position_factory(),
        expected_version=0,
        exit_decision_id="exit:1",
        occurred_at=NOW,
    ).position
    fill = fill_factory(fill_id="fill:close", order_id="order:close")
    closed = apply_close_fill(closing, fill, expected_version=1, event_id="event:closed").position
    replay = apply_close_fill(closed, fill, expected_version=2, event_id="event:replay")
    assert replay.applied is False
    assert replay.position is closed


def test_closed_position_cannot_reopen(position_factory, fill_factory):
    closing = begin_closing(
        position_factory(),
        expected_version=0,
        exit_decision_id="exit:1",
        occurred_at=NOW,
    ).position
    closed = apply_close_fill(
        closing,
        fill_factory(fill_id="fill:close", order_id="order:close"),
        expected_version=1,
        event_id="event:closed",
    ).position
    with pytest.raises(PaperDomainError) as error:
        begin_closing(closed, expected_version=2, exit_decision_id="exit:2", occurred_at=NOW)
    assert error.value.reason_code is PaperReasonCode.PAPER_POSITION_ALREADY_CLOSED


@pytest.mark.parametrize("operation", ["closing", "close", "failure"])
def test_stale_position_version_rejected(position_factory, fill_factory, operation):
    position = position_factory()
    with pytest.raises(PaperDomainError) as error:
        if operation == "closing":
            begin_closing(position, expected_version=9, exit_decision_id="exit:1", occurred_at=NOW)
        elif operation == "close":
            closing = begin_closing(
                position, expected_version=0, exit_decision_id="exit:1", occurred_at=NOW
            ).position
            apply_close_fill(
                closing,
                fill_factory(fill_id="fill:close", order_id="order:close"),
                expected_version=9,
                event_id="event:close",
            )
        else:
            fail_position(position, expected_version=9, occurred_at=NOW, event_id="event:fail")
    assert error.value.reason_code is PaperReasonCode.PAPER_POSITION_VERSION_CONFLICT


def test_negative_remaining_quantity_is_impossible(position_factory):
    with pytest.raises(PaperDomainError) as error:
        replace(position_factory(), remaining_quantity=Decimal("-1"))
    assert error.value.reason_code is PaperReasonCode.PAPER_POSITION_NEGATIVE_REMAINDER


def test_remaining_cannot_exceed_entry(position_factory):
    with pytest.raises(PaperDomainError):
        replace(position_factory(), remaining_quantity=Decimal("3"))


@pytest.mark.parametrize("state", [PaperPositionState.OPEN, PaperPositionState.CLOSING])
def test_explicit_safe_failure_path(position_factory, state):
    position = position_factory()
    if state is PaperPositionState.CLOSING:
        position = begin_closing(
            position, expected_version=0, exit_decision_id="exit:1", occurred_at=NOW
        ).position
    result = fail_position(
        position,
        expected_version=position.version,
        occurred_at=NOW,
        event_id="event:fail",
    )
    assert result.position.state is PaperPositionState.FAILED
    assert result.position.version == position.version + 1
    assert result.events[0].event_type is PaperEventType.PAPER_EXECUTION_FAILED


def test_position_is_frozen(position_factory):
    position = position_factory()
    with pytest.raises(FrozenInstanceError):
        position.remaining_quantity = Decimal("0")


@pytest.mark.parametrize(
    ("side", "exit_price", "expected"),
    [
        (PaperSide.LONG, Decimal("110"), Decimal("20")),
        (PaperSide.LONG, Decimal("90"), Decimal("-20")),
        (PaperSide.SHORT, Decimal("90"), Decimal("20")),
        (PaperSide.SHORT, Decimal("110"), Decimal("-20")),
        (PaperSide.LONG, Decimal("100"), Decimal("0")),
    ],
)
def test_realized_pnl_cases(side, exit_price, expected):
    assert gross_realized_pnl(side, Decimal("100"), exit_price, Decimal("2")) == expected


def test_fees_turn_break_even_into_net_loss():
    assert net_realized_pnl(Decimal("0"), Decimal("0.2"), Decimal("0.2")) == Decimal("-0.4")


@pytest.mark.parametrize(
    ("side", "mark", "expected"),
    [
        (PaperSide.LONG, Decimal("105"), Decimal("10")),
        (PaperSide.SHORT, Decimal("105"), Decimal("-10")),
        (PaperSide.LONG, Decimal("95"), Decimal("-10")),
        (PaperSide.SHORT, Decimal("95"), Decimal("10")),
    ],
)
def test_unrealized_pnl_cases(side, mark, expected):
    assert unrealized_pnl(side, Decimal("100"), mark, Decimal("2")) == expected


def test_total_fees():
    assert total_fees(Decimal("0.2"), Decimal("0.3")) == Decimal("0.5")


def test_return_percentage():
    assert return_percentage(Decimal("20"), Decimal("100"), Decimal("2")) == Decimal("10.0")


def test_risk_multiple():
    assert risk_multiple(Decimal("20"), Decimal("10")) == Decimal("2")


@pytest.mark.parametrize("risk", [Decimal("0"), Decimal("-1"), Decimal("NaN"), 1.0])
def test_invalid_initial_risk_rejected(risk):
    with pytest.raises(PaperDomainError):
        risk_multiple(Decimal("1"), risk)


@pytest.mark.parametrize(
    "call",
    [
        lambda: gross_realized_pnl(PaperSide.LONG, Decimal("NaN"), Decimal("1"), Decimal("1")),
        lambda: gross_realized_pnl(PaperSide.LONG, Decimal("1"), Decimal("Infinity"), Decimal("1")),
        lambda: gross_realized_pnl(PaperSide.LONG, Decimal("1"), Decimal("2"), 1.0),
        lambda: net_realized_pnl(1.0, Decimal("0"), Decimal("0")),
        lambda: total_fees(Decimal("-1"), Decimal("0")),
        lambda: return_percentage(Decimal("1"), Decimal("0"), Decimal("1")),
    ],
)
def test_accounting_rejects_float_nonfinite_and_invalid_bounds(call):
    with pytest.raises(PaperDomainError):
        call()


@pytest.mark.parametrize(
    ("side", "high", "low", "cause"),
    [
        (PaperSide.LONG, Decimal("110"), Decimal("89"), PaperExitCause.STOP_LOSS),
        (PaperSide.LONG, Decimal("121"), Decimal("95"), PaperExitCause.TAKE_PROFIT),
        (PaperSide.LONG, Decimal("121"), Decimal("89"), PaperExitCause.STOP_LOSS),
        (PaperSide.LONG, Decimal("110"), Decimal("95"), None),
        (PaperSide.SHORT, Decimal("121"), Decimal("95"), PaperExitCause.STOP_LOSS),
        (PaperSide.SHORT, Decimal("110"), Decimal("89"), PaperExitCause.TAKE_PROFIT),
        (PaperSide.SHORT, Decimal("121"), Decimal("89"), PaperExitCause.STOP_LOSS),
        (PaperSide.SHORT, Decimal("110"), Decimal("95"), None),
    ],
)
def test_intrabar_resolver(position_factory, side, high, low, cause):
    resolution = resolve_intrabar_exit(
        position_factory(side=side),
        high_price=high,
        low_price=low,
    )
    assert resolution.cause is cause


def test_stop_first_policy_is_explicit(position_factory):
    result = resolve_intrabar_exit(
        position_factory(),
        high_price=Decimal("121"),
        low_price=Decimal("89"),
    )
    assert PAPER_INTRABAR_CONFLICT_POLICY == "STOP_FIRST_CONSERVATIVE"
    assert result.reason_code is PaperReasonCode.PAPER_EXIT_STOP_FIRST_CONFLICT


@pytest.mark.parametrize(
    ("cause", "reason"),
    [
        (PaperExitCause.STOP_LOSS, PaperReasonCode.PAPER_EXIT_STOP_LOSS_TRIGGERED),
        (PaperExitCause.TAKE_PROFIT, PaperReasonCode.PAPER_EXIT_TAKE_PROFIT_TRIGGERED),
        (PaperExitCause.SYSTEM_SAFETY_EXIT, PaperReasonCode.PAPER_EXIT_SYSTEM_SAFETY_TRIGGERED),
    ],
)
def test_all_exit_causes_create_typed_decision(position_factory, cause, reason):
    position = position_factory()
    decision, event = create_exit_decision(
        position,
        exit_decision_id=f"exit:{cause.value.lower()}",
        idempotency_key=exit_decision_idempotency_key(position.position_id, position.version, cause),
        expected_position_version=position.version,
        cause=cause,
        decision_price=Decimal("90"),
        source_closed_until_ms=2_000,
        decided_at=NOW,
        reason_code=reason,
        event_id=f"event:{cause.value.lower()}",
    )
    assert decision.requested_close_quantity == position.remaining_quantity
    assert event.event_type is PaperEventType.PAPER_EXIT_TRIGGERED


def test_exit_decision_rejects_stale_version(position_factory):
    position = position_factory()
    with pytest.raises(PaperDomainError) as error:
        create_exit_decision(
            position,
            exit_decision_id="exit:1",
            idempotency_key="paper:exit:v1:key",
            expected_position_version=9,
            cause=PaperExitCause.STOP_LOSS,
            decision_price=Decimal("90"),
            source_closed_until_ms=2_000,
            decided_at=NOW,
            reason_code=PaperReasonCode.PAPER_EXIT_STOP_LOSS_TRIGGERED,
            event_id="event:exit",
        )
    assert error.value.reason_code is PaperReasonCode.PAPER_EXIT_VERSION_CONFLICT


def test_exit_decision_rejects_future_data(position_factory):
    position = position_factory()
    with pytest.raises(PaperDomainError) as error:
        create_exit_decision(
            position,
            exit_decision_id="exit:1",
            idempotency_key="paper:exit:v1:key",
            expected_position_version=0,
            cause=PaperExitCause.STOP_LOSS,
            decision_price=Decimal("90"),
            source_closed_until_ms=2_000,
            decided_at=NOW,
            reason_code=PaperReasonCode.PAPER_EXIT_STOP_LOSS_TRIGGERED,
            event_id="event:exit",
            future_bars_used=True,
        )
    assert error.value.reason_code is PaperReasonCode.PAPER_SAFETY_FUTURE_DATA_DETECTED


def test_exit_decision_is_frozen(position_factory):
    position = position_factory()
    decision, _ = create_exit_decision(
        position,
        exit_decision_id="exit:1",
        idempotency_key="paper:exit:v1:key",
        expected_position_version=0,
        cause=PaperExitCause.STOP_LOSS,
        decision_price=Decimal("90"),
        source_closed_until_ms=2_000,
        decided_at=NOW,
        reason_code=PaperReasonCode.PAPER_EXIT_STOP_LOSS_TRIGGERED,
        event_id="event:exit",
    )
    with pytest.raises(FrozenInstanceError):
        decision.cause = PaperExitCause.TAKE_PROFIT


def test_all_idempotency_keys_are_versioned_and_bounded():
    keys = [
        command_idempotency_key(
            pipeline_run_id="run:1",
            analysis_result_id="analysis:1",
            setup_id="setup:1",
            strategy_decision_id="strategy:1",
            risk_decision_id="risk:1",
            symbol="BTCUSDT",
            side=PaperSide.LONG,
            closed_until_ms=1_000,
            configuration_fingerprint="config:v1",
        ),
        order_idempotency_key("command:1", "ENTRY"),
        fill_idempotency_key("order:1", "ENTRY"),
        position_application_key("fill:1"),
        exit_decision_idempotency_key("position:1", 0, PaperExitCause.STOP_LOSS),
        journal_event_idempotency_key(
            aggregate_type="paper_order",
            aggregate_id="order:1",
            causation_id="fill:1",
            event_type=PaperEventType.PAPER_ORDER_FILLED,
        ),
    ]
    assert PAPER_IDEMPOTENCY_VERSION == "v1"
    assert all(":v1:" in key and len(key) < 128 for key in keys)


@pytest.mark.parametrize(
    "builder",
    [
        lambda: order_idempotency_key("", "ENTRY"),
        lambda: fill_idempotency_key("order:1", ""),
        lambda: position_application_key(" "),
        lambda: exit_decision_idempotency_key("position:1", -1, PaperExitCause.STOP_LOSS),
        lambda: journal_event_idempotency_key(
            aggregate_type="", aggregate_id="order:1", causation_id="fill:1",
            event_type=PaperEventType.PAPER_ORDER_FILLED,
        ),
    ],
)
def test_blank_or_invalid_idempotency_inputs_rejected(builder):
    with pytest.raises(PaperDomainError) as error:
        builder()
    assert error.value.reason_code in {
        PaperReasonCode.PAPER_INPUT_IDENTITY_INVALID,
        PaperReasonCode.PAPER_IDEMPOTENCY_KEY_INVALID,
    }


def test_same_causal_inputs_produce_same_key():
    first = fill_idempotency_key("order:1", "ENTRY")
    second = fill_idempotency_key("order:1", "ENTRY")
    assert first == second


@pytest.mark.parametrize(
    ("first", "second"),
    [
        (order_idempotency_key("command:1", "ENTRY"), order_idempotency_key("command:2", "ENTRY")),
        (fill_idempotency_key("order:1", "ENTRY"), fill_idempotency_key("order:1", "CLOSE")),
        (
            exit_decision_idempotency_key("position:1", 0, PaperExitCause.STOP_LOSS),
            exit_decision_idempotency_key("position:1", 1, PaperExitCause.STOP_LOSS),
        ),
        (
            exit_decision_idempotency_key("position:1", 0, PaperExitCause.STOP_LOSS),
            exit_decision_idempotency_key("position:1", 0, PaperExitCause.TAKE_PROFIT),
        ),
    ],
)
def test_material_causal_change_changes_key(first, second):
    assert first != second


def test_idempotency_api_has_no_secret_inputs():
    names = set(inspect.signature(command_idempotency_key).parameters)
    assert not any(fragment in name.lower() for name in names for fragment in ("secret", "password", "credential", "token"))


def test_domain_event_retains_correlation_and_causation():
    event = PaperDomainEvent(
        event_id="event:1",
        event_type=PaperEventType.PAPER_SAFETY_BLOCKED,
        occurred_at=NOW,
        aggregate_type="paper_command",
        aggregate_id="command:1",
        correlation_id="correlation:1",
        causation_id="analysis:1",
        reason_code=PaperReasonCode.PAPER_SAFETY_SOURCE_STALE,
        aggregate_version=0,
    )
    assert event.correlation_id == "correlation:1"
    assert event.causation_id == "analysis:1"
    with pytest.raises(FrozenInstanceError):
        event.aggregate_version = 1


def test_command_event_mapping(command_factory):
    event = command_created_event(command_factory(), event_id="event:command", occurred_at=NOW)
    assert event.event_type is PaperEventType.PAPER_COMMAND_CREATED


def test_paper_domain_has_no_transport_persistence_or_wall_clock_imports():
    paths = [
        Path("app/engine_safety/paper_domain.py"),
        Path("app/engine_execution/paper_models.py"),
        Path("app/engine_execution/paper_state_machine.py"),
        Path("app/engine_execution/paper_idempotency.py"),
        Path("app/engine_position/paper_models.py"),
        Path("app/engine_position/paper_state_machine.py"),
        Path("app/engine_position/paper_accounting.py"),
        Path("app/engine_exit/paper_exit.py"),
        Path("app/engine_journal/paper_events.py"),
    ]
    forbidden = {"requests", "httpx", "socket", "sqlalchemy", "subprocess", "binance", "ccxt"}
    for path in paths:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        assert imports.isdisjoint(forbidden), path
        assert "datetime.now" not in source
        assert "datetime.utcnow" not in source
        assert "uuid4" not in source
        assert "random." not in source


def test_no_float_annotations_in_paper_economic_contracts():
    economic_models = (
        PaperExecutionCommand,
        PaperOrder,
        PaperFill,
        PaperPosition,
        PaperExitDecision,
    )
    for model in economic_models:
        annotations = {field.name: str(field.type) for field in fields(model)}
        assert all("float" not in annotation for annotation in annotations.values())
