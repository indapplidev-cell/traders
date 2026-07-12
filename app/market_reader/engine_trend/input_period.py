"""Input period contract for engine_trend."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.market_reader.engine_trend.schemas import EngineTrendCandle


@dataclass(frozen=True)
class EngineTrendInputPeriod:
    """Candles selected for one market-reading period."""

    symbol: str
    interval: str
    candles: tuple[EngineTrendCandle, ...]

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError("symbol must not be empty")
        if not self.interval:
            raise ValueError("interval must not be empty")
        if not self.candles:
            raise ValueError("candles must not be empty")

    @property
    def period_start(self) -> str:
        return self.candles[0].timestamp

    @property
    def period_end(self) -> str:
        return self.candles[-1].timestamp

    @property
    def candle_count(self) -> int:
        return len(self.candles)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "candle_count": self.candle_count,
            "candles": [candle.to_dict() for candle in self.candles],
        }
