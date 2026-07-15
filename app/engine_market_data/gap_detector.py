"""Causal continuity checks between normalized closed candles."""

from dataclasses import dataclass
from collections.abc import Iterable

from app.engine_market_data.candle import Candle
from app.engine_market_data.timeframe import timeframe_to_milliseconds


@dataclass(frozen=True, slots=True)
class Gap:
    symbol: str
    timeframe: str
    previous_open_time_ms: int
    current_open_time_ms: int
    missing_open_times: tuple[int, ...]

    @property
    def missing_count(self) -> int:
        return len(self.missing_open_times)


def detect_gap(previous_candle: Candle, current_candle: Candle) -> Gap | None:
    if not previous_candle.is_closed or not current_candle.is_closed:
        raise ValueError("Gap detection requires closed candles")
    if (previous_candle.symbol, previous_candle.timeframe) != (current_candle.symbol, current_candle.timeframe):
        raise ValueError("Candles must have the same symbol and timeframe")
    if current_candle.open_time_ms <= previous_candle.open_time_ms:
        return None
    step = timeframe_to_milliseconds(current_candle.timeframe)
    missing = tuple(range(previous_candle.open_time_ms + step, current_candle.open_time_ms, step))
    if not missing:
        return None
    return Gap(
        symbol=current_candle.symbol, timeframe=current_candle.timeframe,
        previous_open_time_ms=previous_candle.open_time_ms,
        current_open_time_ms=current_candle.open_time_ms,
        missing_open_times=missing,
    )


def find_missing_open_times(existing_candles: Iterable[Candle], timeframe: str | None = None) -> list[int]:
    candles = sorted(existing_candles, key=lambda candle: candle.open_time_ms)
    if len(candles) < 2:
        return []
    selected_timeframe = timeframe or candles[0].timeframe
    if any(not candle.is_closed for candle in candles):
        raise ValueError("Gap detection requires closed candles")
    if any(candle.timeframe != selected_timeframe for candle in candles):
        raise ValueError("Mixed timeframes are not allowed")
    if any(candle.symbol != candles[0].symbol for candle in candles):
        raise ValueError("Mixed symbols are not allowed")
    step = timeframe_to_milliseconds(selected_timeframe)
    actual = {candle.open_time_ms for candle in candles}
    return [value for value in range(candles[0].open_time_ms, candles[-1].open_time_ms, step) if value not in actual]


class GapDetector:
    detect_gap = staticmethod(detect_gap)
    find_missing_open_times = staticmethod(find_missing_open_times)
