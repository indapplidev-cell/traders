from app.engine_orchestrator.closed_window_detector import ClosedWindowDetector
from tests.engine_orchestrator_01_helpers import BOUNDARY, CandleRepo


class Store:
    def has_window(self, symbol, timeframe, boundary):
        return False


def test_detects_exclusive_closed_boundary():
    windows = ClosedWindowDetector(CandleRepo(), Store()).get_unprocessed_closed_windows("BTCUSDT")
    assert [item.closed_until_ms for item in windows] == [BOUNDARY]
