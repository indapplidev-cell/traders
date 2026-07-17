"""Deterministic adapter from approved upstream decisions to a safe intent."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable

from app.engine_execution.enums import (
    ExecutionIntentStatus, ExecutionMode, ExecutionOrderType, ExecutionReasonCode as R, ExecutionSide,
)
from app.engine_execution.idempotency import InMemoryIdempotencyRegistry, build_idempotency_key
from app.engine_execution.models import ExecutionIntent
from app.engine_execution.validator import decimal_value, side_value, validate_sources, validate_trade_values, value


class ExecutionIntentBuilder:
    def __init__(self, registry: InMemoryIdempotencyRegistry | None = None,
                 clock: Callable[[], datetime] | None = None) -> None:
        self.registry = registry or InMemoryIdempotencyRegistry()
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def build(self, strategy_decision: object, risk_decision: object, setup_context: object,
              execution_mode: ExecutionMode | str, source_window: object) -> ExecutionIntent:
        mode = ExecutionMode(execution_mode)
        if mode is ExecutionMode.LIVE:
            return self._live_disabled(strategy_decision, risk_decision, setup_context, source_window)
        reasons, approval = validate_sources(
            strategy_decision, risk_decision, setup_context, source_window,
        )
        reasons.extend(validate_trade_values(setup_context))
        reasons = list(dict.fromkeys(reasons))

        symbol = str(value(setup_context, "symbol", default=value(strategy_decision, "symbol", default=""))).upper()
        side = side_value(value(setup_context, "side", "direction_hint", "paper_direction")) or ExecutionSide.BUY.value
        strategy_id = str(value(strategy_decision, "decision_id", "strategy_decision_id", default=""))
        risk_id = str(value(risk_decision, "risk_decision_id", "decision_id", default=""))
        setup_id = str(value(setup_context, "setup_id", "source_setup_id", default=""))
        close_ms = _safe_int(value(
            source_window, "closed_until_ms", "source_window_close_ms", "close_ms", default=0,
        ))
        timeframe = str(value(source_window, "timeframe", "source_timeframe", default=""))
        key = build_idempotency_key(
            symbol=symbol, source_timeframe=timeframe, source_closed_until_ms=close_ms,
            setup_id=setup_id, strategy_decision_id=strategy_id,
            risk_decision_id=risk_id, execution_mode=mode,
        )
        if not key:
            reasons.append(R.MISSING_IDEMPOTENCY_KEY.value)

        if reasons:
            status = ExecutionIntentStatus.REJECTED
        elif not self.registry.register(key):
            status = ExecutionIntentStatus.DUPLICATE
            reasons = [R.DUPLICATE_EXECUTION_INTENT.value]
        else:
            status = ExecutionIntentStatus.READY
            reasons = [R.EXECUTION_INTENT_READY.value]

        reference = decimal_value(value(setup_context, "reference_price", "entry_price", "entry",
                                        "hypothetical_entry_reference")) or Decimal("0")
        stop = decimal_value(value(setup_context, "stop_price", "stop", "hypothetical_stop_level")) or Decimal("0")
        target = decimal_value(value(setup_context, "target_price", "target", "hypothetical_target_level")) or Decimal("0")
        quantity = decimal_value(value(setup_context, "quantity")) or Decimal("0")
        limit_price = decimal_value(value(setup_context, "limit_price"))
        try:
            order_type = ExecutionOrderType(value(setup_context, "order_type", default="MARKET_INTENT"))
        except ValueError:
            order_type = ExecutionOrderType.MARKET_INTENT
        execution_id = f"intent:{key.split(':')[-1]}" if key else "intent:invalid"
        metadata = dict(value(setup_context, "metadata", default={}) or {})
        if approval.scope is not None:
            metadata["approval_scope"] = approval.scope.value
        return ExecutionIntent(
            execution_intent_id=execution_id, idempotency_key=key, created_at_utc=self.clock(),
            symbol=symbol, side=ExecutionSide(side), execution_mode=mode, order_type=order_type,
            quantity=quantity, reference_price=reference, limit_price=limit_price,
            stop_price=stop, target_price=target,
            time_in_force=value(setup_context, "time_in_force"),
            reduce_only=bool(value(setup_context, "reduce_only", default=False)),
            strategy_decision_id=strategy_id, risk_decision_id=risk_id, setup_id=setup_id,
            source_window_close_ms=close_ms, source_timeframe=timeframe, status=status,
            reason_codes=tuple(dict.fromkeys(reasons)),
            warnings=tuple(value(setup_context, "warnings", default=()) or ()),
            metadata=metadata,
        )

    def _live_disabled(self, strategy: object, risk: object, context: object,
                       source_window: object) -> ExecutionIntent:
        """First safety gate: produce no validation side effects beyond LIVE denial."""
        symbol = str(value(context, "symbol", default=value(strategy, "symbol", default=""))).upper()
        side = side_value(value(context, "side", "direction_hint", "paper_direction")) or "BUY"
        strategy_id = str(value(strategy, "decision_id", "strategy_decision_id", default=""))
        risk_id = str(value(risk, "risk_decision_id", "decision_id", default=""))
        setup_id = str(value(context, "setup_id", "source_setup_id", default=""))
        close_ms = _safe_int(value(
            source_window, "closed_until_ms", "source_window_close_ms", "close_ms", default=0,
        ))
        timeframe = str(value(source_window, "timeframe", "source_timeframe", default=""))
        key = build_idempotency_key(
            symbol=symbol, source_timeframe=timeframe, source_closed_until_ms=close_ms,
            setup_id=setup_id, strategy_decision_id=strategy_id,
            risk_decision_id=risk_id, execution_mode=ExecutionMode.LIVE,
        )
        return ExecutionIntent(
            execution_intent_id=f"intent:{key.split(':')[-1]}" if key else "intent:disabled",
            idempotency_key=key, created_at_utc=self.clock(), symbol=symbol,
            side=ExecutionSide(side), execution_mode=ExecutionMode.LIVE,
            order_type=ExecutionOrderType.MARKET_INTENT, quantity=Decimal("0"),
            reference_price=Decimal("0"), limit_price=None, stop_price=Decimal("0"),
            target_price=Decimal("0"), time_in_force=None, reduce_only=False,
            strategy_decision_id=strategy_id, risk_decision_id=risk_id, setup_id=setup_id,
            source_window_close_ms=close_ms, source_timeframe=timeframe,
            status=ExecutionIntentStatus.DISABLED,
            reason_codes=(R.LIVE_EXECUTION_DISABLED.value,), metadata={},
        )


def build_execution_intent(strategy_decision: object, risk_decision: object, setup_context: object,
                           execution_mode: ExecutionMode | str, source_window: object,
                           registry: InMemoryIdempotencyRegistry | None = None) -> ExecutionIntent:
    return ExecutionIntentBuilder(registry=registry).build(
        strategy_decision, risk_decision, setup_context, execution_mode, source_window,
    )


def _safe_int(raw: object) -> int:
    try:
        return int(raw or 0)
    except (TypeError, ValueError, OverflowError):
        return 0
