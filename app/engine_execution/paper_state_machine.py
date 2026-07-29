"""Pure deterministic PAPER order state machine."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from types import MappingProxyType

from app.engine_execution.paper_models import PaperExecutionCommand, PaperFill, PaperOrder
from app.engine_execution.paper_idempotency import order_transition_event_id
from app.engine_journal.paper_events import PaperDomainEvent
from app.engine_safety.paper_domain import (
    PaperEventType,
    PaperOrderState,
    PaperReasonCode,
    fail,
    require_identity,
    require_enum,
    require_utc,
)


_ALLOWED_TRANSITIONS = frozenset(
    {
        (PaperOrderState.CREATED, PaperOrderState.VALIDATED),
        (PaperOrderState.CREATED, PaperOrderState.REJECTED),
        (PaperOrderState.CREATED, PaperOrderState.FAILED),
        (PaperOrderState.VALIDATED, PaperOrderState.OPEN),
        (PaperOrderState.VALIDATED, PaperOrderState.REJECTED),
        (PaperOrderState.VALIDATED, PaperOrderState.FAILED),
        (PaperOrderState.OPEN, PaperOrderState.FILLED),
        (PaperOrderState.OPEN, PaperOrderState.FAILED),
    }
)
_TERMINAL_STATES = frozenset(
    {PaperOrderState.FILLED, PaperOrderState.REJECTED, PaperOrderState.FAILED}
)

ORDER_TRANSITION_EVENT_TYPES = MappingProxyType({
    (PaperOrderState.CREATED, PaperOrderState.VALIDATED):
        PaperEventType.PAPER_ORDER_VALIDATED,
    (PaperOrderState.CREATED, PaperOrderState.REJECTED):
        PaperEventType.PAPER_COMMAND_REJECTED,
    (PaperOrderState.CREATED, PaperOrderState.FAILED):
        PaperEventType.PAPER_EXECUTION_FAILED,
    (PaperOrderState.VALIDATED, PaperOrderState.OPEN):
        PaperEventType.PAPER_ORDER_OPENED,
    (PaperOrderState.VALIDATED, PaperOrderState.REJECTED):
        PaperEventType.PAPER_COMMAND_REJECTED,
    (PaperOrderState.VALIDATED, PaperOrderState.FAILED):
        PaperEventType.PAPER_EXECUTION_FAILED,
    (PaperOrderState.OPEN, PaperOrderState.FILLED):
        PaperEventType.PAPER_ORDER_FILLED,
    (PaperOrderState.OPEN, PaperOrderState.FAILED):
        PaperEventType.PAPER_EXECUTION_FAILED,
})


@dataclass(frozen=True, slots=True)
class PaperOrderTransition:
    previous_order: PaperOrder | None
    order: PaperOrder
    events: tuple[PaperDomainEvent, ...]
    applied: bool
    reason_code: PaperReasonCode


def _event(
    *,
    event_id: str,
    event_type: PaperEventType,
    occurred_at: datetime,
    order: PaperOrder,
    correlation_id: str,
    causation_id: str,
    reason_code: PaperReasonCode,
) -> PaperDomainEvent:
    return PaperDomainEvent(
        event_id=event_id,
        event_type=event_type,
        occurred_at=occurred_at,
        aggregate_type="paper_order",
        aggregate_id=order.order_id,
        correlation_id=correlation_id,
        causation_id=causation_id,
        reason_code=reason_code,
        aggregate_version=order.version,
    )


def command_created_event(
    command: PaperExecutionCommand,
    *,
    event_id: str,
    occurred_at: datetime,
) -> PaperDomainEvent:
    return PaperDomainEvent(
        event_id=event_id,
        event_type=PaperEventType.PAPER_COMMAND_CREATED,
        occurred_at=occurred_at,
        aggregate_type="paper_command",
        aggregate_id=command.command_id,
        correlation_id=command.command_id,
        causation_id=command.analysis_result_id,
        reason_code=PaperReasonCode.PAPER_ORDER_CREATED,
        aggregate_version=0,
    )


def create_paper_order(
    command: PaperExecutionCommand,
    *,
    order_id: str,
    idempotency_key: str,
    occurred_at: datetime,
    event_id: str,
) -> PaperOrderTransition:
    require_utc(occurred_at, "occurred_at")
    order = PaperOrder(
        order_id=order_id,
        command_id=command.command_id,
        idempotency_key=idempotency_key,
        symbol=command.symbol,
        side=command.side,
        order_type=command.order_type,
        state=PaperOrderState.CREATED,
        requested_quantity=command.requested_quantity,
        filled_quantity=command.requested_quantity * 0,
        average_fill_price=None,
        total_fees=command.requested_quantity * 0,
        created_at=occurred_at,
        updated_at=occurred_at,
        version=0,
        reason_code=PaperReasonCode.PAPER_ORDER_CREATED,
    )
    event = _event(
        event_id=event_id,
        event_type=PaperEventType.PAPER_ORDER_CREATED,
        occurred_at=occurred_at,
        order=order,
        correlation_id=command.command_id,
        causation_id=command.command_id,
        reason_code=PaperReasonCode.PAPER_ORDER_CREATED,
    )
    return PaperOrderTransition(None, order, (event,), True, PaperReasonCode.PAPER_ORDER_CREATED)


def transition_order(
    order: PaperOrder,
    target_state: PaperOrderState,
    *,
    expected_version: int,
    occurred_at: datetime,
    event_id: str | None = None,
    reason_code: PaperReasonCode | None = None,
) -> PaperOrderTransition:
    target = require_enum(
        target_state,
        PaperOrderState,
        PaperReasonCode.PAPER_ORDER_INVALID_TRANSITION,
        "target_state",
    )
    require_utc(occurred_at, "occurred_at")
    if occurred_at < order.updated_at:
        fail(
            PaperReasonCode.PAPER_INPUT_TIME_INVALID,
            "order transition timestamp regressed",
            "occurred_at",
        )
    if expected_version != order.version:
        fail(
            PaperReasonCode.PAPER_ORDER_INVALID_TRANSITION,
            "stale order version",
            "expected_version",
        )
    if order.state in _TERMINAL_STATES:
        fail(PaperReasonCode.PAPER_ORDER_TERMINAL, "terminal order cannot transition", "state")
    if target is PaperOrderState.FILLED or (order.state, target) not in _ALLOWED_TRANSITIONS:
        fail(
            PaperReasonCode.PAPER_ORDER_INVALID_TRANSITION,
            "invalid order transition",
            "state",
        )
    default_reason = {
        PaperOrderState.VALIDATED: PaperReasonCode.PAPER_ORDER_VALIDATED,
        PaperOrderState.OPEN: PaperReasonCode.PAPER_ORDER_OPENED,
        PaperOrderState.REJECTED: PaperReasonCode.PAPER_ORDER_REJECTED,
        PaperOrderState.FAILED: PaperReasonCode.PAPER_ORDER_FAILED,
    }[target]
    selected_reason = require_enum(
        reason_code or default_reason,
        PaperReasonCode,
        PaperReasonCode.PAPER_INTERNAL_INVARIANT_VIOLATION,
        "reason_code",
    )
    new_order = replace(
        order,
        state=target,
        updated_at=occurred_at,
        version=order.version + 1,
        reason_code=selected_reason,
    )
    canonical_event_id = (
        require_identity(event_id, "event_id")
        if event_id is not None
        else order_transition_event_id(
            order_id=order.order_id,
            from_state=order.state,
            to_state=target,
            aggregate_version=new_order.version,
        )
    )
    event = _event(
        event_id=canonical_event_id,
        event_type=ORDER_TRANSITION_EVENT_TYPES[(order.state, target)],
        occurred_at=occurred_at,
        order=new_order,
        correlation_id=order.command_id,
        causation_id=order.order_id,
        reason_code=selected_reason,
    )
    return PaperOrderTransition(order, new_order, (event,), True, selected_reason)


def fill_order(
    order: PaperOrder,
    fill: PaperFill,
    *,
    expected_version: int,
    event_id: str,
) -> PaperOrderTransition:
    if order.state is PaperOrderState.FILLED and order.applied_fill_id == fill.fill_id:
        return PaperOrderTransition(
            order,
            order,
            (),
            False,
            PaperReasonCode.PAPER_FILL_DUPLICATE,
        )
    if expected_version != order.version:
        fail(
            PaperReasonCode.PAPER_ORDER_INVALID_TRANSITION,
            "stale order version",
            "expected_version",
        )
    if order.state in _TERMINAL_STATES:
        fail(PaperReasonCode.PAPER_ORDER_TERMINAL, "terminal order cannot fill", "state")
    if order.state is not PaperOrderState.OPEN:
        fail(
            PaperReasonCode.PAPER_ORDER_INVALID_TRANSITION,
            "only open order can fill",
            "state",
        )
    if fill.order_id != order.order_id or fill.symbol != order.symbol or fill.side is not order.side:
        fail(
            PaperReasonCode.PAPER_FILL_INVALID,
            "fill does not match order",
            "fill.order_id",
        )
    if fill.quantity != order.requested_quantity:
        fail(
            PaperReasonCode.PAPER_FILL_PARTIAL_UNSUPPORTED,
            "partial fills are unsupported",
            "fill.quantity",
        )
    if fill.filled_at < order.updated_at:
        fail(
            PaperReasonCode.PAPER_INPUT_TIME_INVALID,
            "fill timestamp regressed",
            "fill.filled_at",
        )
    new_order = replace(
        order,
        state=PaperOrderState.FILLED,
        filled_quantity=fill.quantity,
        average_fill_price=fill.price,
        total_fees=fill.fee_amount,
        updated_at=fill.filled_at,
        version=order.version + 1,
        reason_code=PaperReasonCode.PAPER_ORDER_FILLED,
        applied_fill_id=fill.fill_id,
    )
    event = _event(
        event_id=event_id,
        event_type=PaperEventType.PAPER_ORDER_FILLED,
        occurred_at=fill.filled_at,
        order=new_order,
        correlation_id=order.command_id,
        causation_id=fill.fill_id,
        reason_code=PaperReasonCode.PAPER_ORDER_FILLED,
    )
    return PaperOrderTransition(
        order,
        new_order,
        (event,),
        True,
        PaperReasonCode.PAPER_ORDER_FILLED,
    )
