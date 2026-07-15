from app.engine_market_data.continuous_sync_config import ContinuousSyncConfig
from app.engine_market_data.continuous_sync_daemon import ContinuousSyncDaemon
from tests.engine_market_data_04_helpers import FakeRepository, FakeRest


def test_once_catches_up_and_exits():
    now = 600_001
    daemon = ContinuousSyncDaemon(ContinuousSyncConfig(symbols=["BTCUSDT"], timeframes=["1m"],
        warmup=True, continuous=False, gap_check=False, warmup_depths={"1m": 2},
        gap_check_windows={"1m": 2}, freshness_allowance_ms={"1m": 10_000}),
        FakeRepository(), FakeRest(now), clock_ms=lambda: now)
    assert daemon.run().overall_status == "OK"
