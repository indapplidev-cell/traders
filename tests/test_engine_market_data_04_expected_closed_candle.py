from datetime import datetime, timezone
from app.engine_market_data.freshness_monitor import latest_expected_closed_open_time_ms


def test_all_expected_boundaries_and_15m_example():
    boundary = int(datetime(2026, 7, 15, 15, 30, tzinfo=timezone.utc).timestamp() * 1000)
    assert latest_expected_closed_open_time_ms("15m", boundary) == boundary - 900_000
    for timeframe in ("1m", "5m", "15m", "1h", "4h", "1d"):
        assert latest_expected_closed_open_time_ms(timeframe, boundary) < boundary
