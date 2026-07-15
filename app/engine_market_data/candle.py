"""Strict normalized candle model."""

from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from typing import Any

from app.engine_market_data.errors import CandleValidationError
from app.engine_market_data.market_symbol import normalize_market_symbol
from app.engine_market_data.timeframe import is_aligned_to_timeframe, timeframe_to_milliseconds


def _decimal(value: Decimal | float | int | str, field: str) -> Decimal:
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise CandleValidationError(f"{field} must be numeric") from exc
    if not result.is_finite():
        raise CandleValidationError(f"{field} must be finite")
    return result


@dataclass(frozen=True, slots=True)
class Candle:
    symbol: str
    timeframe: str
    open_time_ms: int
    close_time_ms: int
    open: Decimal | float
    high: Decimal | float
    low: Decimal | float
    close: Decimal | float
    volume: Decimal | float
    quote_volume: Decimal | float | None = None
    trades_count: int | None = None
    is_closed: bool = False
    source: str = "unknown"
    received_at_ms: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", normalize_market_symbol(self.symbol))
        timeframe_to_milliseconds(self.timeframe)
        if not isinstance(self.open_time_ms, int) or isinstance(self.open_time_ms, bool):
            raise CandleValidationError("open_time_ms must be an integer")
        if not isinstance(self.close_time_ms, int) or isinstance(self.close_time_ms, bool):
            raise CandleValidationError("close_time_ms must be an integer")
        if self.open_time_ms < 0 or self.close_time_ms < self.open_time_ms:
            raise CandleValidationError("candle timestamps are invalid")
        if not is_aligned_to_timeframe(self.open_time_ms, self.timeframe):
            raise CandleValidationError("open_time_ms is not timeframe-aligned")
        expected_close = self.open_time_ms + timeframe_to_milliseconds(self.timeframe) - 1
        if self.close_time_ms != expected_close:
            raise CandleValidationError("close_time_ms does not match the timeframe")

        for field in ("open", "high", "low", "close", "volume"):
            object.__setattr__(self, field, _decimal(getattr(self, field), field))
        if self.quote_volume is not None:
            object.__setattr__(self, "quote_volume", _decimal(self.quote_volume, "quote_volume"))
        if self.high < max(self.open, self.close, self.low):
            raise CandleValidationError("high must be >= open, close and low")
        if self.low > min(self.open, self.close, self.high):
            raise CandleValidationError("low must be <= open, close and high")
        if self.volume < 0 or (self.quote_volume is not None and self.quote_volume < 0):
            raise CandleValidationError("volumes must be non-negative")
        if self.trades_count is not None and (not isinstance(self.trades_count, int) or self.trades_count < 0):
            raise CandleValidationError("trades_count must be a non-negative integer or None")
        if not isinstance(self.is_closed, bool):
            raise CandleValidationError("is_closed must be boolean")
        if not isinstance(self.source, str) or not self.source.strip():
            raise CandleValidationError("source must be non-empty")
        if self.received_at_ms is not None and (
            not isinstance(self.received_at_ms, int) or self.received_at_ms < 0
        ):
            raise CandleValidationError("received_at_ms must be a non-negative integer or None")

    @property
    def identity(self) -> tuple[str, str, int]:
        return self.symbol, self.timeframe, self.open_time_ms

    def as_closed(self) -> "Candle":
        return replace(self, is_closed=True)

    def market_values(self) -> tuple[Any, ...]:
        return (
            self.open_time_ms, self.close_time_ms, self.open, self.high, self.low,
            self.close, self.volume, self.quote_volume, self.trades_count, self.is_closed,
        )
