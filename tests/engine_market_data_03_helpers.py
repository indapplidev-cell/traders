from app.engine_market_data.candle import Candle


DURATIONS = {"1m": 60_000, "5m": 300_000, "15m": 900_000,
             "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}


def candle(open_ms, timeframe="1m", *, closed=True, symbol="BTCUSDT"):
    duration = DURATIONS[timeframe]
    return Candle(symbol, timeframe, open_ms, open_ms + duration - 1,
                  10, 12, 9, 11, 5, 55, 7, closed, "rest")


class MemoryRepository:
    def __init__(self, rows=()):
        self.rows = {row.identity: row for row in rows}
        self.upsert_calls = 0

    def find_missing_open_times(self, symbol, timeframe, expected_open_times):
        return [value for value in expected_open_times
                if (symbol.upper(), timeframe, value) not in self.rows]

    def upsert_candles(self, rows):
        self.upsert_calls += 1
        for row in rows:
            self.rows[row.identity] = row
        return len(rows)

    def get_candles(self, symbol, timeframe, start_time_ms=None, end_time_ms=None, **kwargs):
        rows = [row for row in self.rows.values()
                if row.symbol == symbol.upper() and row.timeframe == timeframe]
        if start_time_ms is not None:
            rows = [row for row in rows if row.open_time_ms >= start_time_ms]
        if end_time_ms is not None:
            rows = [row for row in rows if row.open_time_ms <= end_time_ms]
        return sorted(rows, key=lambda row: row.open_time_ms)


class RestClient:
    def __init__(self, rows=(), now_ms=600_001):
        self.rows = list(rows)
        self.now_ms = now_ms
        self.kline_calls = []

    def fetch_server_time_ms(self):
        return self.now_ms

    def fetch_klines(self, **kwargs):
        self.kline_calls.append(kwargs)
        return [row for row in self.rows
                if row.symbol == kwargs["symbol"] and row.timeframe == kwargs["timeframe"]
                and kwargs["start_time_ms"] <= row.open_time_ms <= kwargs["end_time_ms"]]

