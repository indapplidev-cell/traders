from decimal import Decimal

from app.engine_market_data.candle import Candle
from app.engine_market_data.timeframe import timeframe_to_milliseconds


def candle(symbol, timeframe, open_ms):
    return Candle(symbol, timeframe, open_ms, open_ms + timeframe_to_milliseconds(timeframe) - 1,
                  Decimal("1"), Decimal("2"), Decimal("1"), Decimal("2"), Decimal("3"),
                  is_closed=True, source="rest")


class FakeRepository:
    def __init__(self, values=()):
        self.values = {(c.symbol, c.timeframe, c.open_time_ms): c for c in values}
        self.writes = 0

    def get_latest_closed_candle(self, symbol, timeframe):
        rows = [c for (s, t, _), c in self.values.items() if s == symbol and t == timeframe]
        return max(rows, key=lambda c: c.open_time_ms) if rows else None

    def find_missing_open_times(self, symbol, timeframe, expected):
        return [value for value in expected if (symbol, timeframe, value) not in self.values]

    def upsert_candles(self, candles):
        self.writes += 1
        for value in candles:
            self.values[value.identity] = value
        return len(candles)


class FakeRest:
    def __init__(self, now_ms, source=None):
        self.now_ms = now_ms
        self.source = source or {}
        self.calls = []

    def fetch_server_time_ms(self):
        return self.now_ms

    def fetch_klines(self, *, symbol, timeframe, start_time_ms, end_time_ms, limit):
        self.calls.append((symbol, timeframe, start_time_ms, end_time_ms, limit))
        step = timeframe_to_milliseconds(timeframe)
        return [self.source.get((symbol, timeframe, value), candle(symbol, timeframe, value))
                for value in range(start_time_ms, end_time_ms + 1, step)][:limit]
