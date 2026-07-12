"""Book-based trend and market state reading engine.

engine_trend is a clean BOOK-L1 core that reads candles for a selected period
and classifies market state as UP, DOWN, FLAT, or UNKNOWN.

It must not produce trading signals.
"""

from app.market_reader.engine_trend.schemas import (
    BookEvidence,
    BookSource,
    ConfidenceDecomposition,
    EngineTrendCandle,
    EngineTrendEvidence,
    EngineTrendRegime,
    EngineTrendResult,
    EngineTrendSafety,
    TradeSignal,
)
from app.market_reader.engine_trend.candle_morphology import (
    CandleDirection,
    CandleMorphology,
    analyze_candle_morphology,
    analyze_candle_window_morphology,
)
from app.market_reader.engine_trend.nison_candlestick_context import (
    NisonCandleContext,
    NisonWindowContext,
    analyze_nison_candle_context,
    analyze_nison_window_context,
)
from app.market_reader.engine_trend.nison_pattern_catalog import (
    CATALOG_DESCRIPTIONS,
    analyze_nison_pattern_catalog,
)
from app.market_reader.engine_trend.altunina_trend_context import (
    ALTUNINA_CORRECTION_LIMIT,
    FIBONACCI_PULLBACK_LEVELS,
    AltuninaStructureDirection,
    AltuninaTrendContext,
    ImpulseCorrectionSummary,
    PriceLeg,
    PriceLegDirection,
    SwingPoint,
    SwingPointType,
    TrendDurationClass,
    TrendDurationSummary,
    TrendHierarchyRole,
    TrendLineSummary,
    analyze_altunina_trend_context,
    analyze_impulse_correction,
    build_trend_line,
    build_price_legs,
    classify_trend_duration,
    classify_structure_direction,
    detect_swing_points,
    normalize_swing_points,
)

__all__ = [
    "BookEvidence",
    "BookSource",
    "ConfidenceDecomposition",
    "EngineTrendCandle",
    "EngineTrendEvidence",
    "EngineTrendRegime",
    "EngineTrendResult",
    "EngineTrendSafety",
    "TradeSignal",
    "CandleDirection",
    "CandleMorphology",
    "NisonCandleContext",
    "NisonWindowContext",
    "analyze_candle_morphology",
    "analyze_candle_window_morphology",
    "analyze_nison_candle_context",
    "analyze_nison_window_context",
    "CATALOG_DESCRIPTIONS",
    "analyze_nison_pattern_catalog",
    "ALTUNINA_CORRECTION_LIMIT",
    "FIBONACCI_PULLBACK_LEVELS",
    "AltuninaStructureDirection",
    "AltuninaTrendContext",
    "ImpulseCorrectionSummary",
    "PriceLeg",
    "PriceLegDirection",
    "SwingPoint",
    "SwingPointType",
    "TrendDurationClass",
    "TrendDurationSummary",
    "TrendHierarchyRole",
    "TrendLineSummary",
    "analyze_altunina_trend_context",
    "analyze_impulse_correction",
    "build_trend_line",
    "build_price_legs",
    "classify_trend_duration",
    "classify_structure_direction",
    "detect_swing_points",
    "normalize_swing_points",
]
