"""Build a local position from an acknowledged execution contract."""
from __future__ import annotations
from datetime import datetime
from hashlib import sha256
from typing import Any
from app.engine_execution import ExecutionAcknowledgement, ExecutionIntent, ExecutionMode
from app.engine_position.enums import PositionFillAction, PositionReasonCode as R, PositionStatus
from app.engine_position.events import PositionFillEvent
from app.engine_position.exceptions import PositionContractError
from app.engine_position.idempotency import build_position_key
from app.engine_position.models import Position
from app.engine_position.serialization import canonical_json
from app.engine_position.validator import side_from_execution, validate_execution_contract


def build_position_from_execution(intent: ExecutionIntent | None,
                                  acknowledgement: ExecutionAcknowledgement | None,
                                  *, current_timestamp: datetime,
                                  initial_fill: PositionFillEvent | None = None,
                                  synthetic_local_fill: bool = False) -> Position:
    reasons = validate_execution_contract(intent, acknowledgement)
    if reasons:
        raise PositionContractError(*reasons)
    assert intent is not None and acknowledgement is not None
    key = build_position_key(execution_intent_id=intent.execution_intent_id,
                             execution_idempotency_key=intent.idempotency_key,
                             symbol=intent.symbol, mode=intent.execution_mode.value,
                             source_timeframe=intent.source_timeframe,
                             source_window_close_ms=intent.source_window_close_ms,
                             setup_id=intent.setup_id, strategy_decision_id=intent.strategy_decision_id,
                             risk_decision_id=intent.risk_decision_id)
    position_id = key
    acknowledgement_identity = {
        "execution_intent_id": acknowledgement.execution_intent_id,
        "idempotency_key": acknowledgement.idempotency_key,
        "mode": acknowledgement.mode.value,
        "status": acknowledgement.status.value,
    }
    ack_id = "ack:v1:" + sha256(
        canonical_json(acknowledgement_identity).encode("utf-8")
    ).hexdigest()
    metadata: dict[str, Any] = {
        "last_source_window_close_ms": intent.source_window_close_ms,
        "requested_initial_quantity": str(intent.quantity),
    }
    position = Position(
        position_id=position_id, position_key=key, execution_intent_id=intent.execution_intent_id,
        execution_acknowledgement_id=ack_id, execution_idempotency_key=intent.idempotency_key,
        mode=intent.execution_mode, symbol=intent.symbol, side=side_from_execution(intent.side),
        status=PositionStatus.PENDING_OPEN, opened_at_utc=None, updated_at_utc=current_timestamp,
        closed_at_utc=None, source_timeframe=intent.source_timeframe,
        source_window_close_ms=intent.source_window_close_ms, setup_id=intent.setup_id,
        strategy_decision_id=intent.strategy_decision_id, risk_decision_id=intent.risk_decision_id,
        initial_quantity=intent.quantity, open_quantity=intent.quantity, closed_quantity=0,
        average_entry_price=intent.limit_price or intent.reference_price,
        last_mark_price=intent.limit_price or intent.reference_price,
        stop_price=intent.stop_price, target_price=intent.target_price,
        reason_codes=(R.POSITION_PENDING_OPEN.value,), warnings=intent.warnings, metadata=metadata)
    if synthetic_local_fill:
        if intent.execution_mode is not ExecutionMode.DRY_RUN:
            raise PositionContractError(R.EXECUTION_CONTRACT_MISMATCH.value)
        initial_fill = PositionFillEvent(event_id=f"local-fill:{key.split(':')[-1]}", position_id=position_id,
                                         occurred_at_utc=current_timestamp, source="LOCAL_DRY_RUN",
                                         fill_quantity=intent.quantity,
                                         fill_price=intent.limit_price or intent.reference_price,
                                         fee="0", action=PositionFillAction.OPEN,
                                         metadata={"fill_source": "LOCAL_DRY_RUN"})
    if initial_fill is not None:
        from app.engine_position.lifecycle import reduce_event
        result = reduce_event(position, initial_fill)
        if not result.applied:
            raise PositionContractError(*result.reason_codes)
        position = result.position
    return position


class PositionBuilder:
    def build(self, intent: ExecutionIntent | None, acknowledgement: ExecutionAcknowledgement | None,
              *, current_timestamp: datetime, initial_fill: PositionFillEvent | None = None,
              synthetic_local_fill: bool = False) -> Position:
        return build_position_from_execution(intent, acknowledgement, current_timestamp=current_timestamp,
                                             initial_fill=initial_fill,
                                             synthetic_local_fill=synthetic_local_fill)
