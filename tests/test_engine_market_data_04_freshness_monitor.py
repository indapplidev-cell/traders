from app.engine_market_data.freshness_monitor import FreshnessMonitor
from tests.engine_market_data_04_helpers import FakeRepository, candle


def test_ok_and_stale():
    boundary = 600_000
    expected = boundary - 60_000
    ok = FreshnessMonitor(FakeRepository([candle("BTCUSDT", "1m", expected)])).snapshot("BTCUSDT", "1m", boundary + 11_000)
    stale = FreshnessMonitor(FakeRepository()).snapshot("BTCUSDT", "1m", boundary + 11_000, missing_count=1)
    assert ok.status == "OK"
    assert stale.status == "STALE"
