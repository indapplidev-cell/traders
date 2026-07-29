"""Pure deterministic PAPER position state machine."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal

from app.engine_execution.paper_models import PaperExecutionCommand, PaperFill, PaperOrder
from app.engine_journal.paper_events import PaperDomainEvent
from app.engine_position.paper_accounting import gross_realized_pnl, net_realized_pnl
from app.engine_position.paper_models import PaperPosition
from app.engine_safety.paper_domain import (
    PaperEventType,
    PaperOrderState,
    PaperPositionState,
    PaperReasonCode,
    fail,
    require_identity,
    require_enum,
    require_utc,
)


@dataclass(frozen=True, slots=True)
class PaperPositionTransition:
    previous_position: PaperPosition | None
    position: PaperPosition
    events: tuple[PaperDomainEvent, ...]
    applied: bool
    reason_code: PaperReasonCode


def _event(
    *,
    event_id: str,
    event_type: PaperEventType,
    occurred_at: datetime,
    position: PaperPosition,
    causation_id: str,
    reason_code: PaperReasonCode,
) -> PaperDomainEvent:
    return PaperDomainEvent(
        event_id=event_id,
        event_type=event_type,
        occurred_at=occurred_at,
        aggregate_type="paper_position",
        aggregate_id=position.position_id,
        correlation_id=position.entry_order_id,
        causation_id=causation_id,
        reason_code=reason_code,
        aggregate_version=position.version,
    )


def apply_entry_fill(
    existing_position: PaperPosition | None,
    command: PaperExecutionCommand,
    order: PaperOrder,
    fill: PaperFill,
    *,
    position_id: str,
    event_id: str,
) -> PaperPositionTransition:
    if existing_position is not None:
        if existing_position.entry_fill_id == fill.fill_id:
            return PaperPositionTransition(
                existing_position,
                existing_position,
                (),
                False,
                PaperReasonCode.PAPER_POSITION_DUPLICATE_FILL,
            )
        fail(
            PaperReasonCode.PAPER_POSITION_INVALID_TRANSITION,
            "position already exists for a different fill",
            "existing_position",
        )
    if (
        order.state is not PaperOrderState.FILLED
        or order.applied_fill_id != fill.fill_id
        or order.order_id != fill.order_id
        or command.command_id != order.command_id
        or command.symbol != fill.symbol
        or command.side is not fill.side
    ):
        fail(
            PaperReasonCode.PAPER_POSITION_INVALID_TRANSITION,
            "entry causal graph mismatch",
            "fill",
        )
    if fill.quantity != command.requested_quantity:
        fail(
            PaperReasonCode.PAPER_FILL_PARTIAL_UNSUPPORTED,
            "partial entry fill is unsupported",
            "fill.quantity",
        )
    position = PaperPosition(
        position_id=require_identity(position_id, "position_id"),
        mode=command.mode,
        symbol=command.symbol,
        side=command.side,
        state=PaperPositionState.OPEN,
        entry_order_id=order.order_id,
        entry_fill_id=fill.fill_id,
        entry_quantity=fill.quantity,
        remaining_quantity=fill.quantity,
        average_entry_price=fill.price,
        average_exit_price=None,
        entry_fees=fill.fee_amount,
        exit_fees=Decimal("0"),
        realized_pnl=-fill.fee_amount,
        unrealized_pnl=Decimal("0"),
        stop_price=command.stop_price,
        target_price=command.target_price,
        opened_at=fill.filled_at,
        closed_at=None,
        last_mark_price=fill.price,
        last_mark_closed_until_ms=fill.source_closed_until_ms,
        version=0,
        reason_code=PaperReasonCode.PAPER_POSITION_OPENED,
    )
    event = _event(
        event_id=event_id,
        event_type=PaperEventType.PAPER_POSITION_OPENED,
        occurred_at=fill.filled_at,
        position=position,
        causation_id=fill.fill_id,
        reason_code=PaperReasonCode.PAPER_POSITION_OPENED,
    )
    return PaperPositionTransition(None, position, (event,), True, position.reason_code)


def begin_closing(
    position: PaperPosition,
    *,
    expected_version: int,
    exit_decision_id: str,
    occurred_at: datetime,
) -> PaperPositionTransition:
    require_utc(occurred_at, "occurred_at")
    require_identity(exit_decision_id, "exit_decision_id")
    _require_version(position, expected_version)
    if position.state is PaperPositionState.CLOSED:
        fail(
            PaperReasonCode.PAPER_POSITION_ALREADY_CLOSED,
            "closed position cannot reopen",
            "state",
        )
    if position.state is not PaperPositionState.OPEN:
        fail(
            PaperReasonCode.PAPER_POSITION_INVALID_TRANSITION,
            "only open position can begin closing",
            "state",
        )
    state = replace(
        position,
        state=PaperPositionState.CLOSING,
        version=position.version + 1,
        reason_code=PaperReasonCode.PAPER_POSITION_CLOSING,
    )
    return PaperPositionTransition(
        position,
        state,
        (),
        True,
        PaperReasonCode.PAPER_POSITION_CLOSING,
    )


def apply_close_fill(
    position: PaperPosition,
    fill: PaperFill,
    *,
    expected_version: int,
    event_id: str,
) -> PaperPositionTransition:
    if position.state is PaperPositionState.CLOSED and position.exit_fill_id == fill.fill_id:
        return PaperPositionTransition(
            position,
            position,
            (),
            False,
            PaperReasonCode.PAPER_POSITION_DUPLICATE_FILL,
        )
    _require_version(position, expected_version)
    if position.state is PaperPositionState.CLOSED:
        fail(
            PaperReasonCode.PAPER_POSITION_ALREADY_CLOSED,
            "closed position cannot accept a fill",
            "state",
        )
    if position.state is not PaperPositionState.CLOSING:
        fail(
            PaperReasonCode.PAPER_POSITION_INVALID_TRANSITION,
            "position must be closing",
            "state",
        )
    if fill.symbol != position.symbol or fill.side is not position.side:
        fail(
            PaperReasonCode.PAPER_FILL_INVALID,
            "close fill does not match position",
            "fill",
        )
    if fill.quantity != position.remaining_quantity:
        fail(
            PaperReasonCode.PAPER_FILL_PARTIAL_UNSUPPORTED,
            "partial close is unsupported",
            "fill.quantity",
        )
    if fill.filled_at < position.opened_at:
        fail(
            PaperReasonCode.PAPER_INPUT_TIME_INVALID,
            "close fill predates position",
            "fill.filled_at",
        )
    gross = gross_realized_pnl(
        position.side,
        position.average_entry_price,
        fill.price,
        fill.quantity,
    )
    net = net_realized_pnl(gross, position.entry_fees, fill.fee_amount)
    state = replace(
        position,
        state=PaperPositionState.CLOSED,
        remaining_quantity=Decimal("0"),
        average_exit_price=fill.price,
        exit_fees=fill.fee_amount,
        realized_pnl=net,
        unrealized_pnl=Decimal("0"),
        closed_at=fill.filled_at,
        last_mark_price=fill.price,
        last_mark_closed_until_ms=fill.source_closed_until_ms,
        version=position.version + 1,
        reason_code=PaperReasonCode.PAPER_POSITION_CLOSED,
        exit_fill_id=fill.fill_id,
    )
    event = _event(
        event_id=event_id,
        event_type=PaperEventType.PAPER_POSITION_CLOSED,
        occurred_at=fill.filled_at,
        position=state,
        causation_id=fill.fill_id,
        reason_code=PaperReasonCode.PAPER_POSITION_CLOSED,
    )
    return PaperPositionTransition(
        position,
        state,
        (event,),
        True,
        PaperReasonCode.PAPER_POSITION_CLOSED,
    )


def fail_position(
    position: PaperPosition,
    *,
    expected_version: int,
    occurred_at: datetime,
    event_id: str,
    reason_code: PaperReasonCode = PaperReasonCode.PAPER_INTERNAL_INVARIANT_VIOLATION,
) -> PaperPositionTransition:
    require_utc(occurred_at, "occurred_at")
    _require_version(position, expected_version)
    if position.state is PaperPositionState.CLOSED:
        fail(
            PaperReasonCode.PAPER_POSITION_ALREADY_CLOSED,
            "closed position is immutable",
            "state",
        )
    if position.state is PaperPositionState.FAILED:
        fail(
            PaperReasonCode.PAPER_POSITION_INVALID_TRANSITION,
            "failed position is terminal",
            "state",
        )
    selected = require_enum(
        reason_code,
        PaperReasonCode,
        PaperReasonCode.PAPER_INTERNAL_INVARIANT_VIOLATION,
        "reason_code",
    )
    state = replace(
        position,
        state=PaperPositionState.FAILED,
        version=position.version + 1,
        reason_code=selected,
    )
    event = _event(
        event_id=event_id,
        event_type=PaperEventType.PAPER_EXECUTION_FAILED,
        occurred_at=occurred_at,
        position=state,
        causation_id=position.position_id,
        reason_code=selected,
    )
    return PaperPositionTransition(position, state, (event,), True, selected)


def _require_version(position: PaperPosition, expected_version: int) -> None:
    if expected_version != position.version:
        fail(
            PaperReasonCode.PAPER_POSITION_VERSION_CONFLICT,
            "stale position version",
            "expected_version",
        )
