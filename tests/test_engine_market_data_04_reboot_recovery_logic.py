from app.engine_market_data.continuous_sync_daemon import simulate_downtime_missing_open_times


def test_restart_warmup_uses_persisted_latest_open():
    assert simulate_downtime_missing_open_times("1m", 300_000, 120_000, 10) == [180_000, 240_000, 300_000]
