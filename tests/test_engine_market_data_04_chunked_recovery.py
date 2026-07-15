from app.engine_market_data.continuous_sync_config import ContinuousSyncConfig
from app.engine_market_data.continuous_sync_daemon import ContinuousSyncDaemon
from app.engine_market_data.db.candle_repository import (
    CandleRepository, MAX_LOOKUP_BATCH_SIZE, MAX_UPSERT_BATCH_SIZE,
)
from tests.engine_market_data_04_helpers import FakeRepository, FakeRest, candle


def config(**overrides):
    values = dict(
        symbols=["BTCUSDT"], timeframes=["1m"], warmup=False, continuous=False,
        gap_check=False, warmup_depths={"1m": 10}, gap_check_windows={"1m": 10},
        freshness_allowance_ms={"1m": 10_000}, max_rest_batch_size=1000,
    )
    values.update(overrides)
    return ContinuousSyncConfig(**values)


class BoundedRepository(FakeRepository):
    def __init__(self):
        super().__init__()
        self.batch_sizes = []

    def upsert_candles(self, candles):
        self.batch_sizes.append(len(candles))
        assert len(candles) <= 1000
        return super().upsert_candles(candles)


def test_recovery_writes_each_rest_batch_without_accumulating_all_candles():
    expected = list(range(0, 2500 * 60_000, 60_000))
    now = expected[-1] + 60_001
    repository = BoundedRepository()
    daemon = ContinuousSyncDaemon(config(), repository, FakeRest(now), clock_ms=lambda: now)

    result = daemon.sync_expected("BTCUSDT", "1m", expected, expected[-1], now)

    assert result.error is None
    assert result.rest_calls == 3
    assert result.inserted_count == 2500
    assert repository.batch_sizes == [1000, 1000, 500]


def test_repository_defensively_chunks_oversized_single_timeframe_upsert():
    repository = CandleRepository(None)  # _upsert_batch is replaced; no DB session is used.
    batch_sizes = []
    repository._upsert_batch = lambda values: batch_sizes.append(len(values)) or len(values)
    candles = [candle("BTCUSDT", "1m", value * 60_000) for value in range(2501)]

    assert repository.upsert_candles(candles) == 2501
    assert batch_sizes == [MAX_UPSERT_BATCH_SIZE, MAX_UPSERT_BATCH_SIZE, 501]


def test_repository_chunks_large_missing_time_lookup_below_protocol_limit():
    repository = CandleRepository(None)
    batch_sizes = []
    repository._find_existing_open_times_batch = lambda _model, _symbol, values: (
        batch_sizes.append(len(values)) or set(values[::2]))
    expected = list(range(0, (2 * MAX_LOOKUP_BATCH_SIZE + 1) * 60_000, 60_000))

    missing = repository.find_missing_open_times("BTCUSDT", "1m", expected)

    assert batch_sizes == [MAX_LOOKUP_BATCH_SIZE, MAX_LOOKUP_BATCH_SIZE, 1]
    assert missing
    assert set(missing) < set(expected)


class FailOnceRepository(FakeRepository):
    def __init__(self):
        super().__init__()
        self.fail = True

    def upsert_candles(self, candles):
        if self.fail:
            self.fail = False
            raise RuntimeError("recovery write failed")
        return super().upsert_candles(candles)


def test_later_narrow_gap_check_cannot_mask_prior_recovery_error_as_ok():
    now = 180_001
    repository = FailOnceRepository()
    daemon = ContinuousSyncDaemon(config(), repository, FakeRest(now), clock_ms=lambda: now)

    failed = daemon.sync_expected("BTCUSDT", "1m", [0, 60_000, 120_000], 120_000, now)
    recovered_latest = daemon.sync_expected("BTCUSDT", "1m", [120_000], 120_000, now)
    health = daemon.build_health_report(now)

    assert failed.error == "recovery write failed"
    assert recovered_latest.error is None
    assert health.overall_status == "DEGRADED"
    assert health.snapshots[0].status == "DEGRADED"
    assert health.snapshots[0].last_error == "recovery write failed"
