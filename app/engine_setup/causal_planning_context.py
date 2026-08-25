"""Direction-aware enrichment of analysis planning primitives."""

from __future__ import annotations

from typing import Any


CAUSAL_PRIMITIVES = frozenset({
    "reference_close", "confirmation_close", "current_closed_candle_close",
    "causal_support_level", "causal_resistance_level", "causal_invalidation_level",
    "causal_target_level", "nearest_opposite_level", "atr_value", "volatility_buffer",
    "causal_target_candidates", "causal_support_candidates",
    "causal_resistance_candidates", "higher_timeframe_target_candidates",
    "setup_type", "strategy_type", "direction_hint",
})


def setup_causal_context(source: dict[str, Any], *, direction: str, setup_type: str) -> dict[str, Any]:
    result = dict(source)
    result["setup_type"] = setup_type
    result["direction_hint"] = direction
    if direction == "BULLISH":
        invalidation = result.get("causal_support_level")
        target = result.get("causal_resistance_level")
        side = "resistance"
    elif direction == "BEARISH":
        invalidation = result.get("causal_resistance_level")
        target = result.get("causal_support_level")
        side = "support"
    else:
        invalidation = target = None
        side = None
    if invalidation is not None:
        result["causal_invalidation_level"] = invalidation
    if target is not None:
        result["causal_target_level"] = target
        result["nearest_opposite_level"] = target
    local_key = f"causal_{side}_candidates" if side else None
    local = result.get(local_key, []) if local_key else []
    higher = result.get("higher_timeframe_target_candidates", [])
    local_items = local if isinstance(local, list) else []
    higher_items = higher if isinstance(higher, list) else []
    result["causal_target_candidates"] = [
        dict(item)
        for item in (*local_items, *higher_items)
        if isinstance(item, dict) and (item.get("side") in {None, side})
    ]
    return result


def select_causal_primitives(source: dict[str, Any]) -> dict[str, Any]:
    return {key: source[key] for key in CAUSAL_PRIMITIVES if source.get(key) is not None}
