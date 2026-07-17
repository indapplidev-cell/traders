"""Pure validation rules for execution intents and their source contracts."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from app.engine_execution.approval_policy import ApprovalResult, evaluate_approval_pair
from app.engine_execution.enums import ExecutionMode, ExecutionOrderType, ExecutionReasonCode as R, ExecutionSide


def value(source: object, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(source, dict) and name in source:
            return source[name]
        if hasattr(source, name):
            return getattr(source, name)
    return default


def side_value(raw: Any) -> str | None:
    normalized = str(getattr(raw, "value", raw) or "").upper()
    return {"BUY": "BUY", "LONG": "BUY", "BULLISH": "BUY",
            "SELL": "SELL", "SHORT": "SELL", "BEARISH": "SELL"}.get(normalized)


def decimal_value(raw: Any) -> Decimal | None:
    if raw is None or isinstance(raw, bool):
        return None
    try:
        result = raw if isinstance(raw, Decimal) else Decimal(str(raw))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return result if result.is_finite() else None


def validate_sources(strategy: object, risk: object, context: object,
                     source_window: object) -> tuple[list[str], ApprovalResult]:
    """Validate source gates in their contractually significant order."""
    reasons: list[str] = []
    close_ms = value(source_window, "closed_until_ms", "source_window_close_ms", "close_ms")
    timeframe = value(source_window, "timeframe", "source_timeframe")
    if source_window is None or close_ms is None or not timeframe:
        reasons.append(R.MISSING_SOURCE_WINDOW.value)
    else:
        is_closed = value(source_window, "is_closed", "closed", default=None)
        if is_closed is not True:
            reasons.append(R.SOURCE_WINDOW_NOT_CLOSED.value)

    approval = evaluate_approval_pair(
        value(strategy, "decision_status", "status"),
        value(risk, "risk_status", "status"),
    )
    reasons.extend(approval.reason_codes)

    strategy_id = value(strategy, "decision_id", "strategy_decision_id")
    risk_strategy_id = value(risk, "source_strategy_decision_id", "strategy_decision_id")
    setup_ids = [value(strategy, "source_setup_id", "setup_id"),
                 value(risk, "source_setup_id", "setup_id"), value(context, "setup_id", "source_setup_id")]
    risk_id = value(risk, "risk_decision_id", "decision_id")
    context_risk_id = value(context, "risk_decision_id", "source_risk_decision_id", default=risk_id)
    if (not strategy_id or not risk_id or strategy_id != risk_strategy_id
            or risk_id != context_risk_id or not all(setup_ids) or len(set(setup_ids)) != 1):
        reasons.append(R.CONTRACT_MISMATCH.value)
    if source_window is not None and close_ms is not None and timeframe:
        identities = [(value(item, "closed_until_ms", "source_window_close_ms"),
                       value(item, "timeframe", "source_timeframe")) for item in (strategy, risk)]
        if any(item_close != close_ms or item_tf != timeframe for item_close, item_tf in identities):
            reasons.append(R.CONTRACT_MISMATCH.value)

    symbols = [str(value(item, "symbol", default="")).upper() for item in (strategy, risk, context)]
    if not all(symbols) or len(set(symbols)) != 1:
        reasons.append(R.SYMBOL_MISMATCH.value)
    sides = [side_value(value(item, "side", "direction_hint", "paper_direction"))
             for item in (strategy, risk, context)]
    if not all(sides) or len(set(sides)) != 1:
        reasons.append(R.SIDE_MISMATCH.value)

    return list(dict.fromkeys(reasons)), approval


def validate_trade_values(context: object) -> list[str]:
    reasons: list[str] = []
    quantity = decimal_value(value(context, "quantity"))
    if quantity is None or quantity <= 0:
        reasons.append(R.INVALID_QUANTITY.value)
    reference = decimal_value(value(context, "reference_price", "entry_price",
                                    "entry", "hypothetical_entry_reference"))
    stop = decimal_value(value(context, "stop_price", "stop", "hypothetical_stop_level"))
    target = decimal_value(value(context, "target_price", "target", "hypothetical_target_level"))
    limit_raw = value(context, "limit_price")
    limit_price = decimal_value(limit_raw) if limit_raw is not None else None
    if reference is None or reference <= 0 or stop is None or stop <= 0 or target is None or target <= 0:
        reasons.append(R.INVALID_PRICE.value)
    if limit_raw is not None and (limit_price is None or limit_price <= 0):
        reasons.append(R.INVALID_PRICE.value)
    try:
        order_type = ExecutionOrderType(value(context, "order_type", default="MARKET_INTENT"))
        if order_type is ExecutionOrderType.LIMIT_INTENT and limit_price is None:
            reasons.append(R.INVALID_PRICE.value)
    except ValueError:
        reasons.append(R.UNSUPPORTED_ORDER_TYPE.value)
    side = side_value(value(context, "side", "direction_hint", "paper_direction"))
    if reference is not None and stop is not None:
        if (side == ExecutionSide.BUY.value and stop >= reference) or (side == ExecutionSide.SELL.value and stop <= reference):
            reasons.append(R.INVALID_STOP_PLACEMENT.value)
    if reference is not None and target is not None:
        if (side == ExecutionSide.BUY.value and target <= reference) or (side == ExecutionSide.SELL.value and target >= reference):
            reasons.append(R.INVALID_TARGET_PLACEMENT.value)
    return list(dict.fromkeys(reasons))


def validate_intent_contract(intent: object) -> tuple[str, ...]:
    reasons: list[str] = []
    if not value(intent, "idempotency_key"):
        reasons.append(R.MISSING_IDEMPOTENCY_KEY.value)
    if value(intent, "execution_mode") == ExecutionMode.LIVE:
        reasons.append(R.LIVE_EXECUTION_DISABLED.value)
    if value(intent, "status") not in {"READY", getattr(value(intent, "status"), "value", None)}:
        reasons.append(R.CONTRACT_MISMATCH.value)
    return tuple(dict.fromkeys(reasons))
