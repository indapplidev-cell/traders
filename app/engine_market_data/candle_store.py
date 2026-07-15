"""Thread-safe runtime candle store with closed-only read methods."""

from threading import RLock

from app.engine_market_data.candle import Candle
from app.engine_market_data.errors import DuplicateCandleConflict
from app.engine_market_data.market_data_health import MarketDataHealth
from app.engine_market_data.market_symbol import normalize_market_symbol
from app.engine_market_data.timeframe import timeframe_to_milliseconds


class CandleStore:
    def __init__(self, health: MarketDataHealth | None = None) -> None:
        self._candles: dict[tuple[str, str, int], Candle] = {}
        self._raw: dict[tuple[str, str, int], Candle] = {}
        self._lock = RLock()
        self.health = health or MarketDataHealth()

    def upsert_candle(self, candle: Candle) -> None:
        with self._lock:
            existing = self._candles.get(candle.identity) or self._raw.get(candle.identity)
            if existing is not None:
                if existing.is_closed and not candle.is_closed:
                    return
                if existing.is_closed and candle.is_closed:
                    if existing.market_values() == candle.market_values():
                        return
                    self.health.degraded("duplicate conflict")
                    raise DuplicateCandleConflict(f"Conflicting candle: {candle.identity}")
            if candle.is_closed:
                self._raw.pop(candle.identity, None)
                self._candles[candle.identity] = candle
            else:
                self._raw[candle.identity] = candle

    def get_candles(
        self,
        symbol: str,
        timeframe: str,
        start_time_ms: int | None = None,
        end_time_ms: int | None = None,
        limit: int | None = None,
    ) -> list[Candle]:
        key_symbol = normalize_market_symbol(symbol)
        timeframe_to_milliseconds(timeframe)
        with self._lock:
            result = sorted(
                (
                    candle for (stored_symbol, stored_timeframe, _), candle in self._candles.items()
                    if stored_symbol == key_symbol
                    and stored_timeframe == timeframe
                    and (start_time_ms is None or candle.open_time_ms >= start_time_ms)
                    and (end_time_ms is None or candle.open_time_ms <= end_time_ms)
                ),
                key=lambda candle: candle.open_time_ms,
            )
        if limit is not None:
            if limit < 0:
                raise ValueError("limit must be non-negative")
            result = result[-limit:] if limit else []
        return result

    def get_latest_closed_candle(self, symbol: str, timeframe: str) -> Candle | None:
        candles = self.get_candles(symbol, timeframe, limit=1)
        return candles[-1] if candles else None

    def get_raw_candle(self, symbol: str, timeframe: str, open_time_ms: int) -> Candle | None:
        key = (normalize_market_symbol(symbol), timeframe, open_time_ms)
        with self._lock:
            return self._raw.get(key)

    def has_candle(self, symbol: str, timeframe: str, open_time_ms: int) -> bool:
        key = (normalize_market_symbol(symbol), timeframe, open_time_ms)
        with self._lock:
            return key in self._candles

    def count(self, symbol: str, timeframe: str) -> int:
        return len(self.get_candles(symbol, timeframe))
