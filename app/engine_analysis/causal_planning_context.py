"""Closed-window price primitives for downstream paper research planning."""

from __future__ import annotations

from typing import Any

from app.engine_analysis.market_hypothesis import MarketHypothesisResult
from app.engine_analysis.schwager_range_context import ZoneType
from app.engine_analysis.unified_market_context import UnifiedMarketContext


def build_causal_planning_context(
    context: UnifiedMarketContext,
    hypotheses: MarketHypothesisResult,
    *,
    timeframe: str = "5m",
) -> dict[str, Any]:
    """Extract primitives using only candles and confirmed structure in this context."""
    if not context.candles:
        return {}
    reference = float(context.candles[-1].close)
    dominant = hypotheses.dominant_hypothesis
    confirmation_index = dominant.confirmation_index if dominant is not None else None
    confirmation = (
        float(context.candles[confirmation_index].close)
        if confirmation_index is not None and 0 <= confirmation_index < len(context.candles)
        else reference
    )

    level_reference = confirmation
    local_source_type = "LOCAL_5M" if timeframe == "5m" else timeframe.upper()
    supports: list[tuple[float, str, str]] = []
    resistances: list[tuple[float, str, str]] = []
    for zone in context.schwager_context.zones:
        price = float(zone.mid_price)
        role = zone.current_zone_type or zone.positional_zone_type or zone.zone_type
        if role is ZoneType.SUPPORT and price < level_reference:
            supports.append((price, local_source_type, "schwager_support_zone"))
        elif role is ZoneType.RESISTANCE and price > level_reference:
            resistances.append((price, local_source_type, "schwager_resistance_zone"))
    # Structural pivots are confirmed by the existing swing detector before this
    # boundary. They are a causal fallback when repeated-touch zones are absent.
    for swing in context.structural_swing_points:
        price = float(swing.price)
        if swing.point_type.value == "LOW" and price < level_reference:
            supports.append((
                price, "STRUCTURAL" if timeframe == "5m" else local_source_type,
                "confirmed_structural_swing_low",
            ))
        elif swing.point_type.value == "HIGH" and price > level_reference:
            resistances.append((
                price, "STRUCTURAL" if timeframe == "5m" else local_source_type,
                "confirmed_structural_swing_high",
            ))

    support = max(supports, default=(None, None, None), key=lambda item: item[0])
    resistance = min(resistances, default=(None, None, None), key=lambda item: item[0])

    def candidates(values: list[tuple[float, str, str]], *, reverse: bool) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        seen: set[tuple[float, str, str]] = set()
        for price, source_type, detail in sorted(values, key=lambda item: item[0], reverse=reverse):
            identity = (round(price, 12), source_type, timeframe)
            if identity in seen:
                continue
            seen.add(identity)
            result.append({
                "price": price,
                "source_type": source_type,
                "timeframe": timeframe,
                "source_detail": detail,
                "validated": True,
                "future_safe": True,
                "still_relevant": True,
            })
        return result
    atr = context.indicator_context.atr_14
    result: dict[str, Any] = {
        "reference_close": reference,
        "confirmation_close": confirmation,
        "current_closed_candle_close": reference,
        "atr_value": float(atr) if atr is not None and atr > 0 else None,
        "volatility_buffer": float(atr) if atr is not None and atr > 0 else None,
        "causal_support_level": support[0],
        "causal_resistance_level": resistance[0],
        "causal_support_candidates": candidates(supports, reverse=True),
        "causal_resistance_candidates": candidates(resistances, reverse=False),
        "causal_primitive_sources": {
            "reference_close": "last_closed_candle",
            "confirmation_close": ("dominant_hypothesis_confirmation_close"
                                   if confirmation_index is not None else "last_closed_candle"),
            "causal_support_level": support[2],
            "causal_resistance_level": resistance[2],
            "atr_value": "technical_indicators.atr_14" if atr is not None else None,
            "volatility_buffer": "technical_indicators.atr_14_1x" if atr is not None else None,
        },
        "causal_boundary_only": True,
    }
    return {key: value for key, value in result.items() if value is not None}
