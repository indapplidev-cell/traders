"""Shared structural context used by all book-based interpretation layers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.engine_analysis.altunina_trend_context import (
    AltuninaTrendContext,
    SwingPoint,
    analyze_altunina_trend_context,
    detect_swing_points,
    detect_volatility_aware_swing_points,
)
from app.engine_analysis.analysis_contract import (
    AnalysisReadiness,
    AnalysisWindowConfig,
    ResolvedAnalysisWindow,
    resolve_analysis_window,
)
from app.engine_analysis.nison_candlestick_context import (
    NisonWindowContext,
    analyze_nison_window_context,
)
from app.engine_analysis.schemas import EngineAnalysisCandle
from app.engine_analysis.technical_indicator_context import (
    TechnicalIndicatorContext,
    analyze_technical_indicators,
)
from app.engine_analysis.schwager_range_context import (
    SchwagerRangeContext,
    analyze_schwager_range_context,
)


@dataclass(frozen=True)
class VolumeContext:
    """Small, descriptive volume layer shared by confirmation rules."""

    available: bool
    positive_volume_count: int
    average_volume: float
    recent_average_volume: float
    recent_to_baseline_ratio: float
    breakout_volume_ratio: float | None

    def to_dict(self) -> dict[str, object]:
        return {
            "available": self.available,
            "positive_volume_count": self.positive_volume_count,
            "average_volume": self.average_volume,
            "recent_average_volume": self.recent_average_volume,
            "recent_to_baseline_ratio": self.recent_to_baseline_ratio,
            "breakout_volume_ratio": self.breakout_volume_ratio,
        }


@dataclass(frozen=True)
class UnifiedMarketContext:
    """One market map consumed by Nison, Altunina, and Schwager semantics."""

    candle_count: int
    candles: tuple[EngineAnalysisCandle, ...]
    raw_swing_points: tuple[SwingPoint, ...]
    structural_swing_points: tuple[SwingPoint, ...]
    timestamp_to_index: dict[str, int]
    nison_context: NisonWindowContext
    altunina_context: AltuninaTrendContext
    schwager_context: SchwagerRangeContext
    volume_context: VolumeContext
    indicator_context: TechnicalIndicatorContext
    analysis_window: ResolvedAnalysisWindow

    def to_dict(self) -> dict[str, Any]:
        return {
            "candle_count": self.candle_count,
            "raw_swing_points": [item.to_dict() for item in self.raw_swing_points],
            "structural_swing_points": [
                item.to_dict() for item in self.structural_swing_points
            ],
            "timestamp_to_index": dict(self.timestamp_to_index),
            "nison_context": self.nison_context.to_dict(),
            "altunina_context": self.altunina_context.to_dict(),
            "schwager_context": self.schwager_context.to_dict(),
            "volume_context": self.volume_context.to_dict(),
            "indicator_context": self.indicator_context.to_dict(),
            "analysis_window": self.analysis_window.to_dict(),
        }


def _average(values: tuple[float, ...] | list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _volume_context(
    candles: tuple[EngineAnalysisCandle, ...],
    schwager: SchwagerRangeContext,
) -> VolumeContext:
    volumes = tuple(float(item.volume) for item in candles)
    positive_count = sum(value > 0.0 for value in volumes)
    available = positive_count > 0
    average = _average(volumes) if available else 0.0
    recent_size = min(3, len(volumes))
    recent = _average(volumes[-recent_size:]) if available and recent_size else 0.0
    baseline_values = volumes[:-recent_size] if len(volumes) > recent_size else volumes
    baseline = _average(baseline_values) if available else 0.0
    recent_ratio = recent / baseline if baseline > 0.0 else 0.0

    breakout_index = schwager.breakout_context.breakout_index
    breakout_ratio: float | None = None
    if available and breakout_index is not None:
        prior = volumes[max(0, breakout_index - 20):breakout_index]
        prior_average = _average(prior)
        if prior_average > 0.0:
            breakout_ratio = volumes[breakout_index] / prior_average

    return VolumeContext(
        available=available,
        positive_volume_count=positive_count,
        average_volume=average,
        recent_average_volume=recent,
        recent_to_baseline_ratio=recent_ratio,
        breakout_volume_ratio=breakout_ratio,
    )


def build_unified_market_context(
    candles: tuple[EngineAnalysisCandle, ...] | list[EngineAnalysisCandle],
    config: AnalysisWindowConfig | None = None,
) -> UnifiedMarketContext:
    """Build all book contexts from one shared, normalized structural map."""

    all_items = tuple(candles)
    # Calls without a contract are low-level book-rule evaluations. Public
    # facades pass the production contract explicitly.
    production_contract = config is not None
    contract = config or AnalysisWindowConfig(minimum_candles=8)
    resolved = resolve_analysis_window(len(all_items), contract)
    items = all_items[resolved.context_start_index:]
    # Re-resolve indexes against the sliced context exported to consumers.
    resolved = resolve_analysis_window(len(items), contract)
    raw_swings = detect_swing_points(items)
    structural_candidates = (
        detect_volatility_aware_swing_points(items)
        if production_contract and resolved.readiness is AnalysisReadiness.FULL
        else raw_swings
    )
    altunina = analyze_altunina_trend_context(items, structural_candidates)
    # Schwager levels deliberately use the same normalized structural pivots
    # that define the Altunina trend and price-leg map.
    schwager = analyze_schwager_range_context(items, altunina.swing_points)
    nison = analyze_nison_window_context(items)
    return UnifiedMarketContext(
        candle_count=len(items),
        candles=items,
        raw_swing_points=raw_swings,
        structural_swing_points=altunina.swing_points,
        timestamp_to_index={item.timestamp: index for index, item in enumerate(items)},
        nison_context=nison,
        altunina_context=altunina,
        schwager_context=schwager,
        volume_context=_volume_context(items, schwager),
        indicator_context=analyze_technical_indicators(items),
        analysis_window=resolved,
    )
