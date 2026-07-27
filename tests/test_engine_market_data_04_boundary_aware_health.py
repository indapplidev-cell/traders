import json
from datetime import datetime, timezone

import pytest

from app.engine_market_data.continuous_sync_config import (
    FRESHNESS_ALLOWANCE_MS,
    ContinuousSyncConfig,
)
from app.engine_market_data.continuous_sync_daemon import ContinuousSyncDaemon
from app.engine_market_data.exchange_time_sync import ExchangeTimeSync
from app.engine_market_data.freshness_monitor import (
    HEALTH_REPORT_SCHEMA_VERSION,
    BoundaryTimingState,
    FreshnessMonitor,
    HealthReasonCode,
)
from app.engine_market_data.operational.prod_smoke import (
    health_payload_operational,
    validate_health_payload,
)
from app.engine_market_data.timeframe import timeframe_to_milliseconds
from tests.engine_market_data_04_helpers import FakeRepository, FakeRest, candle


UTC = timezone.utc
TIMEFRAMES = ("1m", "5m", "15m", "1h", "4h", "1d")


def boundary_case(timeframe: str):
    duration = timeframe_to_milliseconds(timeframe)
    boundary = duration * 10
    latest_expected = boundary - duration
    previously_current = boundary - 2 * duration
    repository = FakeRepository([
        candle("BTCUSDT", timeframe, previously_current),
    ])
    return duration, boundary, latest_expected, repository


@pytest.mark.parametrize("timeframe", TIMEFRAMES)
def test_before_boundary_is_current_for_every_configured_timeframe(timeframe):
    _duration, boundary, _expected, repository = boundary_case(timeframe)
    snapshot = FreshnessMonitor(repository).snapshot(
        "BTCUSDT", timeframe, boundary - 1,
    )
    assert snapshot.status == "OK"
    assert snapshot.reason_code == HealthReasonCode.HEALTHY_CURRENT
    assert snapshot.timing_state == BoundaryTimingState.CURRENT
    assert snapshot.operational is snapshot.ready is True
    assert snapshot.acceptance_blocking is False


@pytest.mark.parametrize("timeframe", TIMEFRAMES)
@pytest.mark.parametrize("offset", [0, 1])
def test_exact_boundary_and_inside_grace_are_operational(timeframe, offset):
    _duration, boundary, _expected, repository = boundary_case(timeframe)
    allowance = FRESHNESS_ALLOWANCE_MS[timeframe]
    now = boundary if offset == 0 else boundary + allowance - 1
    snapshot = FreshnessMonitor(repository).snapshot(
        "BTCUSDT", timeframe, now, heartbeat_progressing=True,
    )
    assert snapshot.status == "OK"
    assert snapshot.reason_code == HealthReasonCode.BOUNDARY_WITHIN_GRACE
    assert snapshot.timing_state == BoundaryTimingState.WITHIN_GRACE
    assert snapshot.operational is snapshot.ready is True
    assert snapshot.acceptance_blocking is False
    assert snapshot.deadline_expired is False
    assert snapshot.gap_count == 0
    assert snapshot.active_error is False


@pytest.mark.parametrize("timeframe", TIMEFRAMES)
def test_exact_deadline_is_inclusive_and_one_millisecond_after_is_recovering(timeframe):
    _duration, boundary, _expected, repository = boundary_case(timeframe)
    deadline = boundary + FRESHNESS_ALLOWANCE_MS[timeframe]
    exact = FreshnessMonitor(repository).snapshot(
        "BTCUSDT", timeframe, deadline, heartbeat_progressing=True,
    )
    after = FreshnessMonitor(repository).snapshot(
        "BTCUSDT", timeframe, deadline + 1, heartbeat_progressing=True,
    )
    assert exact.status == "OK"
    assert exact.reason_code == HealthReasonCode.BOUNDARY_WITHIN_GRACE
    assert exact.scheduler_due is True
    assert exact.seconds_until_deadline == 0
    assert after.status == "RECOVERING"
    assert after.reason_code == HealthReasonCode.RECOVERY_AFTER_DEADLINE
    assert after.operational is after.ready is False
    assert after.acceptance_blocking is True


@pytest.mark.parametrize("timeframe", TIMEFRAMES)
def test_successful_sync_inside_or_after_grace_is_current(timeframe):
    _duration, boundary, expected, repository = boundary_case(timeframe)
    repository.upsert_candles([candle("BTCUSDT", timeframe, expected)])
    monitor = FreshnessMonitor(repository)
    for now in (
        boundary + FRESHNESS_ALLOWANCE_MS[timeframe] - 1,
        boundary + FRESHNESS_ALLOWANCE_MS[timeframe] + 1,
    ):
        snapshot = monitor.snapshot("BTCUSDT", timeframe, now)
        assert snapshot.status == "OK"
        assert snapshot.reason_code == HealthReasonCode.HEALTHY_CURRENT
        assert snapshot.timing_state == BoundaryTimingState.CURRENT


@pytest.mark.parametrize("timeframe", TIMEFRAMES)
def test_no_progress_real_gap_and_active_error_remain_blocking(timeframe):
    duration, boundary, _expected, repository = boundary_case(timeframe)
    deadline = boundary + FRESHNESS_ALLOWANCE_MS[timeframe]
    monitor = FreshnessMonitor(repository)
    stalled = monitor.snapshot(
        "BTCUSDT", timeframe, deadline + 1, heartbeat_progressing=False,
    )
    assert stalled.status == "DEGRADED"
    assert stalled.reason_code == HealthReasonCode.RUNTIME_NO_PROGRESS
    assert stalled.acceptance_blocking is True

    gap_repository = FakeRepository([
        candle("BTCUSDT", timeframe, boundary - 3 * duration),
    ])
    gap = FreshnessMonitor(gap_repository).snapshot(
        "BTCUSDT", timeframe, boundary + 1, missing_count=2,
        status_override="GAP_DETECTED", heartbeat_progressing=True,
        recovery_active=True, recovery_progressing=True,
    )
    assert gap.status == "RECOVERING"
    assert gap.reason_code == HealthReasonCode.REAL_GAP_RECOVERY
    assert gap.gap_count == 2
    assert gap.acceptance_blocking is True

    error = monitor.snapshot(
        "BTCUSDT", timeframe, boundary + 1, status_override="ERROR",
        last_error="exchange unavailable", heartbeat_progressing=True,
    )
    assert error.status == "ERROR"
    assert error.reason_code == HealthReasonCode.ACTIVE_EXCHANGE_ERROR
    assert error.active_error is True
    assert error.acceptance_blocking is True


@pytest.mark.parametrize("timeframe", TIMEFRAMES)
def test_stale_cached_error_after_success_does_not_block(timeframe):
    _duration, boundary, expected, repository = boundary_case(timeframe)
    repository.upsert_candles([candle("BTCUSDT", timeframe, expected)])
    snapshot = FreshnessMonitor(repository).snapshot(
        "BTCUSDT", timeframe, boundary + 1,
        last_error="old transient error", cached_error_stale=True,
    )
    assert snapshot.status == "OK"
    assert snapshot.reason_code == HealthReasonCode.HEALTHY_CURRENT
    assert snapshot.cached_error_stale is True
    assert snapshot.active_error is False
    assert snapshot.acceptance_blocking is False


@pytest.mark.parametrize("drift_ms", [-2_000, 2_000])
def test_exchange_adjusted_clock_skew_does_not_prematurely_expire_grace(drift_ms):
    timeframe = "1m"
    duration, boundary, _expected, repository = boundary_case(timeframe)
    canonical_now = boundary + 1
    local_now = canonical_now - drift_ms
    rest = FakeRest(canonical_now)
    sync = ExchangeTimeSync(
        rest, max_drift_ms=5_000, clock_ms=lambda: local_now,
    )
    result = sync.sync()
    assert result.drift_ms == drift_ms
    snapshot = FreshnessMonitor(repository).snapshot(
        "BTCUSDT", timeframe, sync.now_ms_exchange_adjusted(),
        clock_skew_seconds=sync.drift_ms / 1000,
    )
    assert snapshot.expected_open_time_ms == boundary - duration
    assert snapshot.status == "OK"
    assert snapshot.reason_code == HealthReasonCode.BOUNDARY_WITHIN_GRACE
    assert snapshot.clock_skew_seconds == drift_ms / 1000


def test_three_pair_hourly_incident_regression_transitions():
    timeframe = "1h"
    duration = timeframe_to_milliseconds(timeframe)
    boundary = duration * 10
    expected = boundary - duration
    prior = boundary - 2 * duration
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    repository = FakeRepository([
        candle(symbol, timeframe, prior) for symbol in symbols
    ])
    daemon = ContinuousSyncDaemon(
        ContinuousSyncConfig(
            symbols=symbols,
            timeframes=[timeframe],
            warmup=False,
            continuous=True,
            gap_check=False,
        ),
        repository,
        FakeRest(boundary),
    )

    within = daemon.build_health_report(
        boundary + 30_000, heartbeat_progressing=True,
    )
    assert within.overall_status == "OK"
    assert within.reason_code == HealthReasonCode.BOUNDARY_WITHIN_GRACE
    assert within.within_grace_count == 3
    assert within.operational is within.ready is True
    assert within.acceptance_blocking is False

    expired = daemon.build_health_report(
        boundary + FRESHNESS_ALLOWANCE_MS[timeframe] + 1,
        heartbeat_progressing=True,
    )
    assert expired.overall_status == "RECOVERING"
    assert expired.reason_code == HealthReasonCode.RECOVERY_AFTER_DEADLINE
    assert expired.deadline_expired_count == 3
    assert expired.acceptance_blocking is True

    repository.upsert_candles([
        candle(symbol, timeframe, expected) for symbol in symbols
    ])
    current = daemon.build_health_report(
        boundary + FRESHNESS_ALLOWANCE_MS[timeframe] + 2,
        heartbeat_progressing=True,
    )
    assert current.overall_status == "OK"
    assert current.reason_code == HealthReasonCode.HEALTHY_CURRENT
    assert current.within_grace_count == 0
    assert current.operational is current.ready is True


def test_report_atomic_write_and_old_new_reader_compatibility(tmp_path):
    timeframe = "1m"
    _duration, boundary, _expected, repository = boundary_case(timeframe)
    snapshot = FreshnessMonitor(repository).snapshot(
        "BTCUSDT", timeframe, boundary + 1,
    )
    report = FreshnessMonitor.report(
        [snapshot],
        "test-daemon",
        generated_at=datetime.fromtimestamp((boundary + 1) / 1000, UTC),
    )
    target = tmp_path / "health.json"
    report.write_json(target)
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert not target.with_suffix(".json.tmp").exists()
    assert payload["schema_version"] == HEALTH_REPORT_SCHEMA_VERSION
    assert payload["overall_status"] == "OK"
    assert payload["operational"] is payload["ready"] is True
    assert validate_health_payload(payload) == []
    assert health_payload_operational(payload) is True

    old_payload = {
        "generated_at": "2026-07-27T00:00:00Z",
        "daemon_instance_id": "old",
        "overall_status": "OK",
        "snapshots": [{
            "symbol": "BTCUSDT",
            "timeframe": "1m",
            "expected_open_time_ms": 0,
            "stored_open_time_ms": 0,
            "freshness_lag_candles": 0,
            "status": "OK",
            "missing_count": 0,
            "last_success_at": "2026-07-27T00:00:00Z",
        }],
    }
    assert validate_health_payload(old_payload) == []
    assert health_payload_operational(old_payload) is True
    assert health_payload_operational({"overall_status": "UNKNOWN_NEW_STATE"}) is False


def test_multi_timeframe_overlap_has_no_false_unhealthy():
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    snapshots = []
    for timeframe in TIMEFRAMES:
        duration = timeframe_to_milliseconds(timeframe)
        boundary = 86_400_000 * 10
        expected = boundary - duration
        prior = expected - duration
        repository = FakeRepository([
            candle(symbol, timeframe, prior) for symbol in symbols
        ])
        monitor = FreshnessMonitor(repository)
        snapshots.extend(
            monitor.snapshot(
                symbol, timeframe, boundary + 1,
                heartbeat_progressing=True,
            )
            for symbol in symbols
        )
    report = FreshnessMonitor.report(snapshots, "simulation")
    assert report.overall_status == "OK"
    assert report.within_grace_count == len(symbols) * len(TIMEFRAMES)
    assert report.operational is report.ready is True
    assert report.acceptance_blocking is False


def test_database_health_read_error_is_explicit_and_blocking():
    class FailingRepository(FakeRepository):
        def get_latest_closed_candle(self, symbol, timeframe):
            raise RuntimeError("database read unavailable")

    boundary = 600_000
    daemon = ContinuousSyncDaemon(
        ContinuousSyncConfig(
            symbols=["BTCUSDT"],
            timeframes=["1m"],
            warmup=False,
            continuous=True,
            gap_check=False,
        ),
        FailingRepository(),
        FakeRest(boundary),
    )
    report = daemon.build_health_report(
        boundary + 1, heartbeat_progressing=True,
    )
    snapshot = report.snapshots[0]
    assert snapshot.status == "ERROR"
    assert snapshot.reason_code == HealthReasonCode.ACTIVE_DATABASE_ERROR
    assert snapshot.active_error is True
    assert snapshot.acceptance_blocking is True
    assert report.operational is report.ready is False
