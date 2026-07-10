from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class CandleBar:
    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    @classmethod
    def from_candle(cls, candle: Any) -> "CandleBar":
        open_time = _read_field(candle, "open_time")
        if not isinstance(open_time, datetime):
            raise ValueError("candle open_time must be a datetime")

        bar = cls(
            open_time=open_time,
            open=_to_finite_float(_read_field(candle, "open"), "open"),
            high=_to_finite_float(_read_field(candle, "high"), "high"),
            low=_to_finite_float(_read_field(candle, "low"), "low"),
            close=_to_finite_float(_read_field(candle, "close"), "close"),
            volume=_to_finite_float(_read_field(candle, "volume"), "volume"),
        )
        bar._validate()
        return bar

    def _validate(self) -> None:
        for field_name in ("open", "high", "low", "close"):
            if getattr(self, field_name) <= 0.0:
                raise ValueError(f"candle {field_name} must be positive")

        if self.volume < 0.0:
            raise ValueError("candle volume must be non-negative")

        if self.high < self.low:
            raise ValueError("candle high must be greater than or equal to low")

        if not self.low <= self.open <= self.high:
            raise ValueError("candle open must be inside high/low range")

        if not self.low <= self.close <= self.high:
            raise ValueError("candle close must be inside high/low range")


@dataclass(frozen=True)
class CandleWindow:
    symbol: str
    interval: str
    candles: tuple[CandleBar, ...]

    @classmethod
    def from_candles(
        cls,
        *,
        symbol: str,
        interval: str,
        candles: Sequence[Any],
        min_size: int = 1,
    ) -> "CandleWindow":
        if min_size <= 0:
            raise ValueError("min_size must be positive")

        normalized = tuple(CandleBar.from_candle(candle) for candle in candles)
        if len(normalized) < min_size:
            raise ValueError(f"not enough candles: expected at least {min_size}, got {len(normalized)}")

        window = cls(symbol=symbol, interval=interval, candles=normalized)
        window._validate_chronological_order()
        return window

    @property
    def size(self) -> int:
        return len(self.candles)

    @property
    def first_open_time(self) -> datetime:
        return self.candles[0].open_time

    @property
    def last_open_time(self) -> datetime:
        return self.candles[-1].open_time

    @property
    def latest(self) -> CandleBar:
        return self.candles[-1]

    @property
    def opens(self) -> tuple[float, ...]:
        return tuple(candle.open for candle in self.candles)

    @property
    def highs(self) -> tuple[float, ...]:
        return tuple(candle.high for candle in self.candles)

    @property
    def lows(self) -> tuple[float, ...]:
        return tuple(candle.low for candle in self.candles)

    @property
    def closes(self) -> tuple[float, ...]:
        return tuple(candle.close for candle in self.candles)

    @property
    def volumes(self) -> tuple[float, ...]:
        return tuple(candle.volume for candle in self.candles)

    def _validate_chronological_order(self) -> None:
        for previous, current in zip(self.candles, self.candles[1:]):
            if current.open_time <= previous.open_time:
                raise ValueError("candles must be ordered by strictly increasing open_time")


def _read_field(candle: Any, field_name: str) -> Any:
    if isinstance(candle, Mapping):
        if field_name not in candle:
            raise ValueError(f"candle is missing field: {field_name}")
        return candle[field_name]

    if not hasattr(candle, field_name):
        raise ValueError(f"candle is missing field: {field_name}")
    return getattr(candle, field_name)


def _to_finite_float(value: Any, field_name: str) -> float:
    try:
        numeric_value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"candle {field_name} must be numeric") from exc

    if not math.isfinite(numeric_value):
        raise ValueError(f"candle {field_name} must be finite")

    return numeric_value
