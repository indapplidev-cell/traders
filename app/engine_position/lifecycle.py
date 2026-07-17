"""Deterministic event reducer and high-level lifecycle service."""
from __future__ import annotations
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from typing import Any
from app.engine_position.builder import PositionBuilder
from app.engine_position.enums import PositionFillAction, PositionReasonCode as R, PositionStatus
from app.engine_position.events import (PositionCancelEvent, PositionCloseEvent, PositionEvent,
                                        PositionFillEvent, PositionMarkEvent)
from app.engine_position.models import Position, PositionTransitionResult, TERMINAL_STATUSES
from app.engine_position.pnl import net_realized_pnl, realized_pnl, unrealized_pnl
from app.engine_position.serialization import thaw


def _result(position: Position, event: PositionEvent, applied: bool, reasons: tuple[str, ...],
            new_position: Position | None = None) -> PositionTransitionResult:
    state = new_position or position
    return PositionTransitionResult(position_id=position.position_id, event_id=event.event_id,
                                    previous_status=position.status, new_status=state.status,
                                    applied=applied, occurred_at_utc=event.occurred_at_utc,
                                    reason_codes=reasons, warnings=(), position=state, metadata={})


def reduce_event(position: Position, event: PositionEvent) -> PositionTransitionResult:
    if event.position_id != position.position_id:
        return _result(position, event, False, (R.POSITION_ID_MISMATCH.value,))
    if event.event_id in position.applied_event_ids:
        return _result(position, event, False, (R.DUPLICATE_POSITION_EVENT.value,))
    if position.status in TERMINAL_STATUSES:
        return _result(position, event, False, (R.POSITION_ALREADY_TERMINAL.value,))
    if event.occurred_at_utc < position.updated_at_utc:
        return _result(position, event, False, (R.OUT_OF_ORDER_POSITION_EVENT.value,))
    if position.opened_at_utc is not None and event.occurred_at_utc < position.opened_at_utc:
        return _result(position, event, False, (R.OUT_OF_ORDER_POSITION_EVENT.value,))
    ids = (*position.applied_event_ids, event.event_id)
    if isinstance(event, PositionFillEvent):
        if event.action is PositionFillAction.CLOSE:
            close_event = PositionCloseEvent(event_id=event.event_id, position_id=event.position_id,
                                             occurred_at_utc=event.occurred_at_utc, source=event.source,
                                             reason_codes=event.reason_codes, metadata=event.metadata,
                                             close_quantity=event.fill_quantity, close_price=event.fill_price,
                                             fee=event.fee, close_reason="FILL_CLOSE")
            return _apply_close(position, close_event)
        if event.action is not PositionFillAction.OPEN:
            return _result(position, event, False, (R.UNSUPPORTED_FILL_ACTION.value,))
        if position.status is not PositionStatus.PENDING_OPEN:
            return _result(position, event, False, (R.INVALID_POSITION_TRANSITION.value,))
        if event.fill_quantity <= 0 or event.fill_quantity > position.initial_quantity:
            return _result(position, event, False, (R.INVALID_OPEN_QUANTITY.value,))
        if event.fill_quantity < position.initial_quantity:
            return _result(position, event, False, (R.PARTIAL_OPEN_FILL_UNSUPPORTED.value,))
        if event.fill_price <= 0:
            return _result(position, event, False, (R.INVALID_ENTRY_PRICE.value,))
        if event.fee < 0:
            return _result(position, event, False, (R.INVALID_FEE.value,))
        state = replace(position, status=PositionStatus.OPEN, opened_at_utc=event.occurred_at_utc,
                        updated_at_utc=event.occurred_at_utc,
                        open_quantity=position.initial_quantity, closed_quantity=Decimal("0"),
                        average_entry_price=event.fill_price, last_mark_price=event.fill_price,
                        fees_paid=event.fee, net_realized_pnl=-event.fee,
                        applied_event_ids=ids, reason_codes=(R.POSITION_OPENED.value,),
                        metadata={**thaw(position.metadata), **thaw(event.metadata)})
        return _result(position, event, True, (R.POSITION_OPENED.value,), state)
    if isinstance(event, PositionMarkEvent):
        if position.status not in {PositionStatus.OPEN, PositionStatus.PARTIALLY_CLOSED}:
            return _result(position, event, False, (R.INVALID_POSITION_TRANSITION.value,))
        if event.mark_price <= 0:
            return _result(position, event, False, (R.INVALID_MARK_PRICE.value,))
        boundary = int(position.metadata.get("last_source_window_close_ms", position.source_window_close_ms))
        if (not event.source_timeframe or event.source_timeframe != position.source_timeframe or
                event.source_window_close_ms <= 0):
            return _result(position, event, False, (R.SOURCE_WINDOW_NOT_CLOSED.value,))
        if event.source_window_close_ms < boundary:
            return _result(position, event, False, (R.OUT_OF_ORDER_POSITION_EVENT.value,))
        metadata = thaw(position.metadata); metadata["last_source_window_close_ms"] = event.source_window_close_ms
        state = replace(position, updated_at_utc=event.occurred_at_utc, last_mark_price=event.mark_price,
                        unrealized_pnl=unrealized_pnl(position.side, position.average_entry_price,
                                                    event.mark_price, position.open_quantity),
                        applied_event_ids=ids, metadata=metadata)
        return _result(position, event, True, (R.POSITION_READY.value,), state)
    if isinstance(event, PositionCloseEvent):
        return _apply_close(position, event)
    if isinstance(event, PositionCancelEvent):
        if position.status is not PositionStatus.PENDING_OPEN:
            return _result(position, event, False, (R.INVALID_POSITION_TRANSITION.value,))
        state = replace(position, status=PositionStatus.CANCELLED, updated_at_utc=event.occurred_at_utc,
                        close_reason="CANCELLED_LOCALLY", applied_event_ids=ids,
                        reason_codes=(R.POSITION_CANCELLED.value,))
        return _result(position, event, True, (R.POSITION_CANCELLED.value,), state)
    return _result(position, event, False, (R.INVALID_POSITION_TRANSITION.value,))


def _apply_close(position: Position, event: PositionCloseEvent) -> PositionTransitionResult:
    if position.status not in {PositionStatus.OPEN, PositionStatus.PARTIALLY_CLOSED}:
        return _result(position, event, False, (R.INVALID_POSITION_TRANSITION.value,))
    if event.close_quantity <= 0 or event.close_quantity > position.open_quantity:
        return _result(position, event, False, (R.INVALID_CLOSE_QUANTITY.value,))
    if event.close_price <= 0:
        return _result(position, event, False, (R.INVALID_CLOSE_PRICE.value,))
    if event.fee < 0:
        return _result(position, event, False, (R.INVALID_FEE.value,))
    open_q = position.open_quantity - event.close_quantity
    closed_q = position.closed_quantity + event.close_quantity
    gross = position.gross_realized_pnl + realized_pnl(position.side, position.average_entry_price,
                                                       event.close_price, event.close_quantity)
    fees = position.fees_paid + event.fee
    closed = open_q == 0
    status = PositionStatus.CLOSED if closed else PositionStatus.PARTIALLY_CLOSED
    reason = R.POSITION_CLOSED.value if closed else R.POSITION_PARTIALLY_CLOSED.value
    state = replace(position, status=status, updated_at_utc=event.occurred_at_utc,
                    closed_at_utc=event.occurred_at_utc if closed else None,
                    open_quantity=open_q, closed_quantity=closed_q, last_mark_price=event.close_price,
                    gross_realized_pnl=gross, fees_paid=fees, net_realized_pnl=net_realized_pnl(gross, fees),
                    unrealized_pnl=Decimal("0") if closed else unrealized_pnl(
                        position.side, position.average_entry_price, event.close_price, open_q),
                    close_reason=event.close_reason if closed else None,
                    applied_event_ids=(*position.applied_event_ids, event.event_id), reason_codes=(reason,))
    return _result(position, event, True, (reason,), state)


class PositionLifecycleService:
    def __init__(self, store: Any, builder: PositionBuilder | None = None) -> None:
        self.store = store; self.builder = builder or PositionBuilder()

    def create_position(self, intent: Any, acknowledgement: Any, *, current_timestamp: datetime,
                        initial_fill: PositionFillEvent | None = None,
                        synthetic_local_fill: bool = False) -> Position:
        position = self.builder.build(intent, acknowledgement, current_timestamp=current_timestamp,
                                      initial_fill=initial_fill, synthetic_local_fill=synthetic_local_fill)
        self.store.create(position); return self.store.get(position.position_id)

    def apply_fill(self, position_id: str, event: PositionFillEvent) -> PositionTransitionResult:
        return self.store.apply_event(position_id, event)
    def apply_mark(self, position_id: str, event: PositionMarkEvent) -> PositionTransitionResult:
        return self.store.apply_event(position_id, event)
    def partial_close(self, position_id: str, event: PositionCloseEvent) -> PositionTransitionResult:
        return self.store.apply_event(position_id, event)
    def close(self, position_id: str, event: PositionCloseEvent) -> PositionTransitionResult:
        return self.store.apply_event(position_id, event)
    def cancel(self, position_id: str, event: PositionCancelEvent) -> PositionTransitionResult:
        return self.store.apply_event(position_id, event)
    def get_position(self, position_id: str) -> Position | None:
        return self.store.get(position_id)
