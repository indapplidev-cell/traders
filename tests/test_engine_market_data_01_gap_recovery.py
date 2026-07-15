from app.engine_market_data.candle import Candle
from app.engine_market_data.candle_store import CandleStore
from app.engine_market_data.gap_recovery import GapRecovery


def make(open_time: int, *, closed: bool = True) -> Candle:
    return Candle("BTCUSDT", "1m", open_time, open_time + 59_999, 10, 12, 9, 11, 5, None, None, closed, "rest")


class FakeRest:
    def __init__(self, result: list[Candle] | Exception) -> None:
        self.result = result
        self.calls: list[dict] = []

    def fetch_klines(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_recovery_requests_only_exact_missing_interval() -> None:
    rest = FakeRest([make(60_000), make(120_000)])
    store = CandleStore()
    report = GapRecovery(rest, store).recover("BTCUSDT", "1m", [60_000, 120_000])
    assert report.success is True and report.recovered_count == 2
    assert rest.calls == [{
        "symbol": "BTCUSDT", "timeframe": "1m", "start_time_ms": 60_000,
        "end_time_ms": 179_999, "limit": 2,
    }]


def test_failed_recovery_degrades_without_synthetic_candles() -> None:
    rest = FakeRest(RuntimeError("offline"))
    store = CandleStore()
    report = GapRecovery(rest, store).recover("BTCUSDT", "1m", [60_000])
    assert report.success is False
    assert report.unrecovered_open_times == [60_000]
    assert store.count("BTCUSDT", "1m") == 0
    assert store.health.status == "DEGRADED"


def test_unclosed_rest_result_is_not_accepted() -> None:
    store = CandleStore()
    report = GapRecovery(FakeRest([make(60_000, closed=False)]), store).recover("BTCUSDT", "1m", [60_000])
    assert report.recovered_count == 0
    assert store.count("BTCUSDT", "1m") == 0
