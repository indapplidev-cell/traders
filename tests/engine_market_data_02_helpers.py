from app.engine_market_data.candle import Candle


def candle(timeframe: str, open_ms: int, *, closed: bool = True, source: str = "rest") -> Candle:
    durations = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}
    return Candle("BTCUSDT", timeframe, open_ms, open_ms + durations[timeframe] - 1,
                  10, 12, 9, 11, 5, 55, 7, closed, source)


class MemoryRepository:
    def __init__(self, candles=()): self.rows = {item.identity: item for item in candles}
    def find_missing_open_times(self, symbol, timeframe, expected):
        return [value for value in expected if (symbol.upper(), timeframe, value) not in self.rows]
    def upsert_candles(self, candles):
        for item in candles: self.rows[item.identity] = item
        return len(candles)
    def get_candles(self, symbol, timeframe, limit=None, **kwargs):
        rows = sorted((c for c in self.rows.values() if c.symbol == symbol.upper() and c.timeframe == timeframe and c.is_closed), key=lambda c: c.open_time_ms)
        return rows[-limit:] if limit is not None else rows
    def count(self, symbol, timeframe): return len(self.get_candles(symbol, timeframe))


class Rest:
    def __init__(self, available=(), now_ms=86_400_002_000): self.available = list(available); self.now_ms = now_ms; self.calls = []
    def fetch_server_time_ms(self): return self.now_ms
    def fetch_klines(self, **kwargs):
        self.calls.append(kwargs)
        return [c for c in self.available if c.timeframe == kwargs["timeframe"] and kwargs["start_time_ms"] <= c.open_time_ms <= kwargs["end_time_ms"]]
