from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class MarketRegime(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    FLAT = "FLAT"
    UNKNOWN = "UNKNOWN"


class DirectionalBias(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    UNKNOWN = "UNKNOWN"


class TrendStrength(str, Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    NONE = "NONE"
    UNKNOWN = "UNKNOWN"


class TradeSignal(str, Enum):
    NOT_EVALUATED = "NOT_EVALUATED"


@dataclass(frozen=True)
class MarketAnalysisResult:
    symbol: str
    interval: str
    market_regime: MarketRegime
    directional_bias: DirectionalBias
    confidence: float
    trend_strength: TrendStrength
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    trade_signal: TradeSignal = TradeSignal.NOT_EVALUATED
    safe_for_runtime_trading: bool = False

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")

        if self.trade_signal != TradeSignal.NOT_EVALUATED:
            raise ValueError("BOOK-L1 Market Reader must not produce trading signals")

        if self.safe_for_runtime_trading:
            raise ValueError("BOOK-L1 Market Reader must not approve runtime trading")

        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))

    def to_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "market_regime": self.market_regime.value,
            "directional_bias": self.directional_bias.value,
            "confidence": self.confidence,
            "trend_strength": self.trend_strength.value,
            "reason_codes": list(self.reason_codes),
            "trade_signal": self.trade_signal.value,
            "safe_for_runtime_trading": self.safe_for_runtime_trading,
        }
