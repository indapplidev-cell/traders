from app.engine_orchestrator.closed_window_detector import ClosedWindowDetector
from tests.engine_orchestrator_01_helpers import BOUNDARY, CandleRepo
from types import SimpleNamespace


class Store:
    def has_window(self, symbol, timeframe, boundary, **_kwargs):
        return False


def test_detects_exclusive_closed_boundary():
    windows = ClosedWindowDetector(CandleRepo(), Store()).get_unprocessed_closed_windows("BTCUSDT")
    assert [item.closed_until_ms for item in windows] == [BOUNDARY]


def test_batch_detection_uses_one_universe_load_and_one_existing_key_read():
    class BatchCandles:
        def __init__(self):
            self.calls = 0

        def get_recent_candles_for_symbols(self, symbols, timeframe, *, limit_per_symbol):
            self.calls += 1
            assert timeframe == "5m" and limit_per_symbol == 4
            return {
                symbol: [SimpleNamespace(close_time_ms=BOUNDARY - 1, is_closed=True)]
                for symbol in symbols
            }

    class BatchStore:
        def __init__(self):
            self.calls = 0

        def existing_window_keys(self, windows, *, trade_profile_id):
            self.calls += 1
            assert trade_profile_id == "trade-5m-v2"
            return {("ETHUSDT", "5m", BOUNDARY)}

    candles, store = BatchCandles(), BatchStore()
    detector = ClosedWindowDetector(
        candles, store, trade_profile_id="trade-5m-v2",
    )

    result = detector.get_unprocessed_closed_windows_many(("BTCUSDT", "ETHUSDT"))

    assert [item.closed_until_ms for item in result["BTCUSDT"]] == [BOUNDARY]
    assert result["ETHUSDT"] == []
    assert candles.calls == store.calls == 1
