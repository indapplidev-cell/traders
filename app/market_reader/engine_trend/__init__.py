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
]
