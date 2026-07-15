from app.engine_market_data.continuous_sync_config import ContinuousSyncConfig
from app.engine_market_data.continuous_sync_daemon import ContinuousSyncDaemon
from tests.engine_market_data_04_helpers import FakeRepository, FakeRest


def test_dry_run_does_not_fetch_or_write():
    now = 600_001
    repo, rest = FakeRepository(), FakeRest(now)
    config = ContinuousSyncConfig(symbols=["BTCUSDT"], timeframes=["1m"], warmup=True,
        continuous=False, gap_check=False, dry_run=True, warmup_depths={"1m": 2},
        gap_check_windows={"1m": 2}, freshness_allowance_ms={"1m": 10_000})
    ContinuousSyncDaemon(config, repo, rest, clock_ms=lambda: now).run()
    assert repo.writes == 0 and rest.calls == []
