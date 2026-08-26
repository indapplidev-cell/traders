"""Fail-closed, side-effect-free readiness check immediately before entry."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


SCALP_CANCEL_ENTRY_PRICE_MOVED = "SCALP_CANCEL_ENTRY_PRICE_MOVED"


@dataclass(frozen=True, slots=True)
class ScalpingExecutionReadiness:
    ready: bool
    reason: str
    signal_age_ms: int
    price_drift_bps: float | None


def check_scalping_execution_readiness(
    *, decision_timestamp_ms: int, now_ms: int, decision_entry: float,
    current_price: float | None, spread_bps: float | None,
    depth_impact_bps: float | None, expected_slippage_bps: float | None,
    quantity: float | None, entry_ttl_seconds: int = 60,
    max_price_drift_bps: float = 10.0,
) -> ScalpingExecutionReadiness:
    age = int(now_ms) - int(decision_timestamp_ms)
    if age < 0:
        return ScalpingExecutionReadiness(False, "SCALP_CANCEL_FUTURE_DECISION_TIME", age, None)
    if age > int(entry_ttl_seconds) * 1_000:
        return ScalpingExecutionReadiness(False, "SCALP_CANCEL_ENTRY_TTL_EXPIRED", age, None)
    required = (current_price, spread_bps, depth_impact_bps, expected_slippage_bps, quantity)
    if any(value is None or not isfinite(float(value)) for value in required):
        return ScalpingExecutionReadiness(False, "SCALP_CANCEL_EXECUTION_INPUT_MISSING", age, None)
    if decision_entry <= 0 or current_price <= 0 or quantity <= 0:
        return ScalpingExecutionReadiness(False, "SCALP_CANCEL_EXECUTION_INPUT_INVALID", age, None)
    if spread_bps < 0 or depth_impact_bps < 0 or expected_slippage_bps < 0:
        return ScalpingExecutionReadiness(False, "SCALP_CANCEL_EXECUTION_INPUT_INVALID", age, None)
    drift = abs(float(current_price) - float(decision_entry)) / float(decision_entry) * 10_000
    if drift > max_price_drift_bps:
        return ScalpingExecutionReadiness(False, SCALP_CANCEL_ENTRY_PRICE_MOVED, age, drift)
    return ScalpingExecutionReadiness(True, "SCALP_EXECUTION_READY", age, drift)
