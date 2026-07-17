"""Validation of the execution-to-position boundary."""
from __future__ import annotations
from decimal import Decimal
from app.engine_execution import (ExecutionAcknowledgementStatus, ExecutionIntentStatus,
                                  ExecutionMode, ExecutionSide)
from app.engine_position.enums import PositionReasonCode as R, PositionSide


def side_from_execution(side: ExecutionSide) -> PositionSide:
    if side is ExecutionSide.BUY:
        return PositionSide.LONG
    if side is ExecutionSide.SELL:
        return PositionSide.SHORT
    raise ValueError(R.SIDE_MISMATCH.value)


def validate_execution_contract(intent: object, acknowledgement: object) -> tuple[str, ...]:
    # LIVE is deliberately the first and isolated safety gate.
    if intent is not None and getattr(intent, "execution_mode", None) is ExecutionMode.LIVE:
        return (R.LIVE_POSITION_MANAGEMENT_DISABLED.value,)
    if intent is None or acknowledgement is None:
        return (R.EXECUTION_CONTRACT_MISMATCH.value,)
    reasons: list[str] = []
    if intent.status is not ExecutionIntentStatus.READY:
        reasons.append(R.EXECUTION_INTENT_NOT_READY.value)
    if acknowledgement.status is not ExecutionAcknowledgementStatus.ACKNOWLEDGED:
        reasons.append(R.EXECUTION_ACK_NOT_ACKNOWLEDGED.value)
    if acknowledgement.execution_intent_id != intent.execution_intent_id:
        reasons.append(R.EXECUTION_CONTRACT_MISMATCH.value)
    if acknowledgement.idempotency_key != intent.idempotency_key:
        reasons.append(R.EXECUTION_CONTRACT_MISMATCH.value)
    if acknowledgement.mode is not intent.execution_mode:
        reasons.append(R.MODE_MISMATCH.value)
    if intent.execution_mode not in {ExecutionMode.PAPER, ExecutionMode.DRY_RUN}:
        reasons.append(R.EXECUTION_CONTRACT_MISMATCH.value)
    if not str(intent.symbol).strip():
        reasons.append(R.SYMBOL_MISMATCH.value)
    ack_symbol = acknowledgement.metadata.get("symbol")
    if ack_symbol is not None and str(ack_symbol).upper() != intent.symbol:
        reasons.append(R.SYMBOL_MISMATCH.value)
    ack_side = acknowledgement.metadata.get("side")
    if ack_side is not None and str(ack_side) != intent.side.value:
        reasons.append(R.SIDE_MISMATCH.value)
    if not intent.quantity.is_finite() or intent.quantity <= 0:
        reasons.append(R.INVALID_INITIAL_QUANTITY.value)
    entry_valid = intent.reference_price.is_finite() and intent.reference_price > 0
    if not entry_valid:
        reasons.append(R.INVALID_ENTRY_PRICE.value)
    if not intent.source_timeframe or intent.source_window_close_ms <= 0:
        reasons.append(R.MISSING_SOURCE_WINDOW.value)
    if intent.metadata.get("source_window_is_closed") is False:
        reasons.append(R.SOURCE_WINDOW_NOT_CLOSED.value)
    if intent.side is ExecutionSide.BUY and entry_valid:
        if intent.stop_price is None or not intent.stop_price.is_finite() or intent.stop_price >= intent.reference_price:
            reasons.append(R.INVALID_STOP_PLACEMENT.value)
        if intent.target_price is None or not intent.target_price.is_finite() or intent.target_price <= intent.reference_price:
            reasons.append(R.INVALID_TARGET_PLACEMENT.value)
    elif intent.side is ExecutionSide.SELL and entry_valid:
        if intent.stop_price is None or not intent.stop_price.is_finite() or intent.stop_price <= intent.reference_price:
            reasons.append(R.INVALID_STOP_PLACEMENT.value)
        if intent.target_price is None or not intent.target_price.is_finite() or intent.target_price >= intent.reference_price:
            reasons.append(R.INVALID_TARGET_PLACEMENT.value)
    else:
        reasons.append(R.SIDE_MISMATCH.value)
    return tuple(dict.fromkeys(reasons))
