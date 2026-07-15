from app.engine_market_data.continuous_sync_config import ContinuousSyncConfig
from app.engine_market_data.continuous_sync_daemon import ContinuousSyncDaemon
from tests.engine_market_data_04_helpers import FakeRepository, FakeRest, candle


def test_downtime_missing_tail_is_fetched_and_fresh():
    now = 360_001
    repo = FakeRepository([candle("BTCUSDT", "1m", 120_000)])
    rest = FakeRest(now)
    config = ContinuousSyncConfig(symbols=["BTCUSDT"], timeframes=["1m"], continuous=False,
        gap_check=False, warmup_depths={"1m": 10}, gap_check_windows={"1m": 10},
        freshness_allowance_ms={"1m": 10_000})
    daemon = ContinuousSyncDaemon(config, repo, rest, clock_ms=lambda: now)
    assert daemon.run().overall_status == "OK"
    assert rest.calls[0][2] == 180_000
