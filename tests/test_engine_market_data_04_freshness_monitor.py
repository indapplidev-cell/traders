from app.engine_market_data.freshness_monitor import FreshnessMonitor
from tests.engine_market_data_04_helpers import FakeRepository, candle


def test_ok_and_recovering_after_deadline():
    boundary = 600_000
    expected = boundary - 60_000
    ok = FreshnessMonitor(FakeRepository([candle("BTCUSDT", "1m", expected)])).snapshot("BTCUSDT", "1m", boundary + 11_000)
    recovering = FreshnessMonitor(FakeRepository()).snapshot(
        "BTCUSDT", "1m", boundary + 11_000, missing_count=1,
    )
    assert ok.status == "OK"
    assert recovering.status == "RECOVERING"
    assert recovering.operational is False
