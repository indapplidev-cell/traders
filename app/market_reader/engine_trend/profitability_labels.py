"""Deterministic offline profitability labels for ENGINE-TREND-21 setup plans.

This module is deliberately not imported by the market-reader runtime.  It accepts
an already-created, causal setup plan and evaluates only candles strictly after the
entry candle.  It has no exchange, execution, order, or strategy dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import math
from typing import Any, Mapping, Sequence


class LabelStatus(StrEnum):
    TP_BEFORE_SL = "TP_BEFORE_SL"
    SL_BEFORE_TP = "SL_BEFORE_TP"
    NEITHER_EXPIRED = "NEITHER_EXPIRED"
    AMBIGUOUS_INTRACANDLE = "AMBIGUOUS_INTRACANDLE"
    INSUFFICIENT_FUTURE_DATA = "INSUFFICIENT_FUTURE_DATA"
    INVALID_SETUP_PLAN = "INVALID_SETUP_PLAN"
    NO_TRADE_SKIPPED = "NO_TRADE_SKIPPED"


@dataclass(frozen=True)
class AuditCostAssumptions:
    """Deterministic audit assumptions; never sourced from a trading API."""

    fee_bps_per_side: float = 10.0
    slippage_bps_per_side: float = 2.0

    @property
    def round_trip_cost_bps(self) -> float:
        return 2.0 * (self.fee_bps_per_side + self.slippage_bps_per_side)


DEFAULT_AUDIT_COSTS = AuditCostAssumptions()
NO_TRADE_STATUSES = frozenset({"NO_TRADE", "WAIT_CONFIRMATION", "INVALIDATED"})
ALLOWED_DIRECTIONS = frozenset({"LONG", "SHORT"})
BLOCKED_SETUP_TYPES = frozenset({"SHORT_TREND_ONLY_CONTINUATION_CANDIDATE"})


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _finite_positive(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) and number > 0.0 else None


def _base_result(
    setup_plan: Mapping[str, Any],
    costs: AuditCostAssumptions,
) -> dict[str, Any]:
    entry = setup_plan.get("entry") if isinstance(setup_plan.get("entry"), Mapping) else {}
    stop = setup_plan.get("stop") if isinstance(setup_plan.get("stop"), Mapping) else {}
    return {
        "schema_version": "1.0.0-audit",
        "case_id": str(setup_plan.get("case_id") or setup_plan.get("setup_id") or "UNKNOWN_CASE"),
        "label_status": None,
        "direction": setup_plan.get("direction") if setup_plan.get("direction") in {"LONG", "SHORT", "NONE"} else "NONE",
        "entry_time": entry.get("timestamp") or entry.get("confirmation_candle_time"),
        "entry_price": entry.get("price"),
        "stop_price": stop.get("price"),
        "target_price": None,
        "exit_time": None,
        "exit_price": None,
        "exit_reason": "NONE",
        "risk_abs": None,
        "reward_abs": None,
        "realized_return_abs": None,
        "rr_planned": None,
        "mfe_abs": None,
        "mfe_pct": None,
        "mfe_r": None,
        "mae_abs": None,
        "mae_pct": None,
        "mae_r": None,
        "bars_to_outcome": None,
        "bars_to_tp": None,
        "bars_to_sl": None,
        "bars_to_max_favorable": None,
        "bars_to_max_adverse": None,
        "bars_to_expiry": None,
        "gross_return_pct": None,
        "fee_bps_per_side": costs.fee_bps_per_side,
        "slippage_bps_per_side": costs.slippage_bps_per_side,
        "round_trip_cost_bps": costs.round_trip_cost_bps,
        "net_return_pct": None,
        "ambiguity_flags": [],
        "validation_errors": [],
        "data_quality": "PASS",
        "target_results": [],
        "audit_only": True,
    }


def _invalid(result: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    result["label_status"] = LabelStatus.INVALID_SETUP_PLAN.value
    result["validation_errors"] = errors
    result["data_quality"] = "FAIL"
    return result


def _validated_candles(
    candles: Sequence[Mapping[str, Any]], entry_time: datetime
) -> tuple[list[dict[str, Any]], list[str]]:
    future: list[dict[str, Any]] = []
    errors: list[str] = []
    seen: set[datetime] = set()
    for index, candle in enumerate(candles):
        timestamp = _parse_time(candle.get("timestamp"))
        high = _finite_positive(candle.get("high"))
        low = _finite_positive(candle.get("low"))
        close = _finite_positive(candle.get("close"))
        if timestamp is None or high is None or low is None or close is None or low > high or not (low <= close <= high):
            errors.append(f"INVALID_CANDLE_{index}")
            continue
        if timestamp <= entry_time:
            continue
        if timestamp in seen:
            errors.append(f"DUPLICATE_FUTURE_CANDLE_{index}")
            continue
        seen.add(timestamp)
        future.append({"timestamp": timestamp, "high": high, "low": low, "close": close})
    future.sort(key=lambda row: row["timestamp"])
    return future, errors


def _target_label(
    *,
    direction: str,
    entry_price: float,
    stop_price: float,
    target: Mapping[str, Any],
    candles: Sequence[Mapping[str, Any]],
    expiry: int,
    costs: AuditCostAssumptions,
) -> dict[str, Any]:
    target_price = float(target["price"])
    risk = entry_price - stop_price if direction == "LONG" else stop_price - entry_price
    reward = target_price - entry_price if direction == "LONG" else entry_price - target_price
    observed = list(candles[:expiry])

    status: str | None = None
    outcome_index: int | None = None
    tp_index: int | None = None
    sl_index: int | None = None
    ambiguity_flags: list[str] = []
    for index, candle in enumerate(observed, start=1):
        if direction == "LONG":
            tp_hit = candle["high"] >= target_price
            sl_hit = candle["low"] <= stop_price
        else:
            tp_hit = candle["low"] <= target_price
            sl_hit = candle["high"] >= stop_price
        if tp_hit and tp_index is None:
            tp_index = index
        if sl_hit and sl_index is None:
            sl_index = index
        if tp_hit and sl_hit:
            status = LabelStatus.AMBIGUOUS_INTRACANDLE.value
            outcome_index = index
            ambiguity_flags = ["TARGET_AND_STOP_TOUCHED_SAME_CANDLE"]
            break
        if tp_hit:
            status = LabelStatus.TP_BEFORE_SL.value
            outcome_index = index
            break
        if sl_hit:
            status = LabelStatus.SL_BEFORE_TP.value
            outcome_index = index
            break

    if status is None:
        if len(candles) < expiry:
            status = LabelStatus.INSUFFICIENT_FUTURE_DATA.value
        else:
            status = LabelStatus.NEITHER_EXPIRED.value
            outcome_index = expiry

    metric_bars = observed[:outcome_index] if outcome_index is not None else observed
    favorable = [
        (candle["high"] - entry_price if direction == "LONG" else entry_price - candle["low"])
        for candle in metric_bars
    ]
    adverse = [
        (entry_price - candle["low"] if direction == "LONG" else candle["high"] - entry_price)
        for candle in metric_bars
    ]
    mfe_abs = max(0.0, max(favorable)) if favorable else None
    mae_abs = max(0.0, max(adverse)) if adverse else None
    max_favorable_bar = favorable.index(max(favorable)) + 1 if favorable else None
    max_adverse_bar = adverse.index(max(adverse)) + 1 if adverse else None

    exit_price: float | None = None
    exit_reason = "NONE"
    if status == LabelStatus.TP_BEFORE_SL.value:
        exit_price, exit_reason = target_price, "TARGET"
    elif status == LabelStatus.SL_BEFORE_TP.value:
        exit_price, exit_reason = stop_price, "STOP"
    elif status == LabelStatus.NEITHER_EXPIRED.value:
        exit_price, exit_reason = observed[expiry - 1]["close"], "EXPIRY"

    realized_abs: float | None = None
    gross_pct: float | None = None
    net_pct: float | None = None
    if exit_price is not None:
        realized_abs = exit_price - entry_price if direction == "LONG" else entry_price - exit_price
        gross_pct = realized_abs / entry_price * 100.0
        net_pct = gross_pct - costs.round_trip_cost_bps / 100.0

    return {
        "target_id": str(target.get("target_id") or "T1"),
        "label_status": status,
        "target_price": target_price,
        "exit_time": _iso_utc(metric_bars[-1]["timestamp"]) if outcome_index is not None and metric_bars else None,
        "exit_price": exit_price,
        "exit_reason": exit_reason,
        "risk_abs": risk,
        "reward_abs": reward,
        "realized_return_abs": realized_abs,
        "rr_planned": reward / risk,
        "mfe_abs": mfe_abs,
        "mfe_pct": mfe_abs / entry_price * 100.0 if mfe_abs is not None else None,
        "mfe_r": mfe_abs / risk if mfe_abs is not None else None,
        "mae_abs": mae_abs,
        "mae_pct": mae_abs / entry_price * 100.0 if mae_abs is not None else None,
        "mae_r": mae_abs / risk if mae_abs is not None else None,
        "bars_to_outcome": outcome_index,
        "bars_to_tp": tp_index,
        "bars_to_sl": sl_index,
        "bars_to_max_favorable": max_favorable_bar,
        "bars_to_max_adverse": max_adverse_bar,
        "bars_to_expiry": expiry if status == LabelStatus.NEITHER_EXPIRED.value else None,
        "gross_return_pct": gross_pct,
        "net_return_pct": net_pct,
        "ambiguity_flags": ambiguity_flags,
        "data_quality": "AMBIGUOUS" if ambiguity_flags else ("INCOMPLETE" if status == LabelStatus.INSUFFICIENT_FUTURE_DATA.value else "PASS"),
    }


def build_profitability_label(
    setup_plan: Mapping[str, Any],
    future_candles: Sequence[Mapping[str, Any]],
    *,
    costs: AuditCostAssumptions = DEFAULT_AUDIT_COSTS,
) -> dict[str, Any]:
    """Evaluate an immutable setup plan against strictly post-entry OHLC candles."""

    result = _base_result(setup_plan, costs)
    status = setup_plan.get("status")
    if status in NO_TRADE_STATUSES:
        result["label_status"] = LabelStatus.NO_TRADE_SKIPPED.value
        result["exit_reason"] = "NOT_A_TRADE"
        result["data_quality"] = "NOT_APPLICABLE"
        return result

    errors: list[str] = []
    if status != "TRADE_CANDIDATE":
        errors.append("STATUS_NOT_TRADE_CANDIDATE")
    direction = setup_plan.get("direction")
    if direction not in ALLOWED_DIRECTIONS:
        errors.append("DIRECTION_MUST_BE_LONG_OR_SHORT")
    if setup_plan.get("setup_type") == "NO_TRADE_CONTRACT":
        errors.append("NO_TRADE_CONTRACT_CANNOT_BE_TRADE_CANDIDATE")
    if setup_plan.get("setup_type") in BLOCKED_SETUP_TYPES:
        errors.append("SETUP_CONTRACT_BLOCKED_ENGINE_TREND_20B")
    if setup_plan.get("source_regime") == "UNKNOWN":
        errors.append("UNKNOWN_REGIME_CANNOT_BE_TRADE_CANDIDATE")
    if setup_plan.get("evidence_origin") == "INDICATOR_ONLY":
        errors.append("INDICATOR_ONLY_EVIDENCE_CANNOT_ORIGINATE_SETUP")
    entry = setup_plan.get("entry") if isinstance(setup_plan.get("entry"), Mapping) else {}
    stop = setup_plan.get("stop") if isinstance(setup_plan.get("stop"), Mapping) else {}
    entry_price = _finite_positive(entry.get("price"))
    stop_price = _finite_positive(stop.get("price"))
    entry_time = _parse_time(entry.get("timestamp") or entry.get("confirmation_candle_time"))
    if entry_price is None:
        errors.append("MISSING_OR_INVALID_ENTRY_PRICE")
    if entry_time is None:
        errors.append("MISSING_OR_INVALID_ENTRY_TIME")
    if stop_price is None:
        errors.append("MISSING_OR_INVALID_STOP_PRICE")
    raw_targets = setup_plan.get("targets")
    if not isinstance(raw_targets, Sequence) or isinstance(raw_targets, (str, bytes)) or not raw_targets:
        errors.append("MISSING_TARGET")
        raw_targets = []
    expiry = setup_plan.get("expires_after_candles")
    if isinstance(expiry, bool) or not isinstance(expiry, int) or expiry < 1:
        errors.append("INVALID_EXPIRY")

    targets: list[dict[str, Any]] = []
    target_ids: set[str] = set()
    for index, target in enumerate(raw_targets):
        if not isinstance(target, Mapping):
            errors.append(f"INVALID_TARGET_{index}")
            continue
        price = _finite_positive(target.get("price"))
        target_id = str(target.get("target_id") or f"T{index + 1}")
        if price is None or target_id in target_ids:
            errors.append(f"INVALID_TARGET_{index}")
            continue
        target_ids.add(target_id)
        targets.append({**target, "price": price, "target_id": target_id})

    if entry_price is not None and stop_price is not None and direction in ALLOWED_DIRECTIONS:
        risk = entry_price - stop_price if direction == "LONG" else stop_price - entry_price
        if risk <= 0.0:
            errors.append("NON_POSITIVE_RISK")
        for index, target in enumerate(targets):
            reward = target["price"] - entry_price if direction == "LONG" else entry_price - target["price"]
            if reward <= 0.0:
                errors.append(f"NON_POSITIVE_REWARD_{index}")
    if errors:
        return _invalid(result, errors)

    assert entry_time is not None and entry_price is not None and stop_price is not None
    future, candle_errors = _validated_candles(future_candles, entry_time)
    if candle_errors:
        return _invalid(result, candle_errors)

    target_results = [
        _target_label(
            direction=direction,
            entry_price=entry_price,
            stop_price=stop_price,
            target=target,
            candles=future,
            expiry=expiry,
            costs=costs,
        )
        for target in targets
    ]
    primary_index = next((i for i, target in enumerate(targets) if target["target_id"] == "T1"), 0)
    primary = target_results[primary_index]
    result.update({key: value for key, value in primary.items() if key != "target_id"})
    result["target_results"] = target_results
    return result


__all__ = [
    "AuditCostAssumptions",
    "DEFAULT_AUDIT_COSTS",
    "LabelStatus",
    "build_profitability_label",
]
