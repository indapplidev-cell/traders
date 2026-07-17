"""Direction-aware enrichment of analysis planning primitives."""

from __future__ import annotations

from typing import Any


CAUSAL_PRIMITIVES = frozenset({
    "reference_close", "confirmation_close", "current_closed_candle_close",
    "causal_support_level", "causal_resistance_level", "causal_invalidation_level",
    "causal_target_level", "nearest_opposite_level", "atr_value", "volatility_buffer",
    "setup_type", "strategy_type", "direction_hint",
})


def setup_causal_context(source: dict[str, Any], *, direction: str, setup_type: str) -> dict[str, Any]:
    result = dict(source)
    result["setup_type"] = setup_type
    result["direction_hint"] = direction
    if direction == "BULLISH":
        invalidation = result.get("causal_support_level")
        target = result.get("causal_resistance_level")
    elif direction == "BEARISH":
        invalidation = result.get("causal_resistance_level")
        target = result.get("causal_support_level")
    else:
        invalidation = target = None
    if invalidation is not None:
        result["causal_invalidation_level"] = invalidation
    if target is not None:
        result["causal_target_level"] = target
        result["nearest_opposite_level"] = target
    return result


def select_causal_primitives(source: dict[str, Any]) -> dict[str, Any]:
    return {key: source[key] for key in CAUSAL_PRIMITIVES if source.get(key) is not None}
