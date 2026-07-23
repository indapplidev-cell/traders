import json
from datetime import datetime

import pytest

from app.engine_market_data.continuous_sync_config import ContinuousSyncConfig
from app.engine_market_data.continuous_sync_daemon import ContinuousSyncDaemon
from app.engine_market_data.timeframe import timeframe_to_milliseconds
from tests.engine_market_data_04_helpers import FakeRepository, FakeRest, candle


TIMEFRAMES = ("1m", "5m", "15m", "1h", "4h", "1d")


class RecordingStateRepository:
    def __init__(self):
        self.updates = []

    def upsert(self, update):
        self.updates.append(update)


class FailingRest(FakeRest):
    def fetch_klines(self, **kwargs):
        raise RuntimeError("transient upstream failure")


def daemon_for(timeframes, repository, rest, state_repository=None):
    return ContinuousSyncDaemon(
        ContinuousSyncConfig(
            symbols=["BTCUSDT", "ETHUSDT"],
            timeframes=list(timeframes),
            warmup=False,
            continuous=False,
            gap_check=False,
        ),
        repository,
        rest,
        state_repository=state_repository,
    )


@pytest.mark.parametrize("timeframe", TIMEFRAMES)
def test_transient_error_then_no_gap_success_clears_only_recovered_pair(timeframe):
    duration = timeframe_to_milliseconds(timeframe)
    expected = duration
    now = expected + duration
    repository = FakeRepository()
    state = RecordingStateRepository()
    daemon = daemon_for((timeframe,), repository, FailingRest(now), state)

    failed = daemon.sync_expected("BTCUSDT", timeframe, [expected], expected, now)
    assert failed.error == "transient upstream failure"
    assert daemon._pair_errors[("BTCUSDT", timeframe)] == "transient upstream failure"

    other_key = ("ETHUSDT", timeframe)
    daemon._pair_errors[other_key] = "unrelated current failure"
    daemon._pair_status[other_key] = "ERROR"
    daemon.rest_client = FakeRest(now)
    recovered = daemon.sync_expected("BTCUSDT", timeframe, [expected], expected, now)

    assert recovered.missing_after == 0
    assert ("BTCUSDT", timeframe) not in daemon._pair_errors
    assert daemon._pair_errors[other_key] == "unrelated current failure"
    snapshot = next(value for value in daemon.build_health_report(now).snapshots
                    if value.symbol == "BTCUSDT" and value.timeframe == timeframe)
    assert snapshot.status == "OK"
    assert snapshot.last_error is None
    assert snapshot.last_success_at is not None
    datetime.fromisoformat(snapshot.last_success_at.replace("Z", "+00:00"))
    assert state.updates[-1].status == "OK"
    assert state.updates[-1].last_success_at is not None
    assert state.updates[-1].last_error_at is None


def test_current_exception_after_success_remains_blocking():
    timeframe = "1h"
    duration = timeframe_to_milliseconds(timeframe)
    expected, now = duration, duration * 2
    repository = FakeRepository([candle("BTCUSDT", timeframe, expected)])
    daemon = daemon_for((timeframe,), repository, FakeRest(now))
    daemon.sync_expected("BTCUSDT", timeframe, [expected], expected, now)
    first_success = daemon._last_success[("BTCUSDT", timeframe)]

    repository.values.clear()
    daemon.rest_client = FailingRest(now)
    failed = daemon.sync_expected("BTCUSDT", timeframe, [expected], expected, now)

    assert failed.error == "transient upstream failure"
    assert daemon._pair_status[("BTCUSDT", timeframe)] == "ERROR"
    assert daemon._pair_errors[("BTCUSDT", timeframe)] == "transient upstream failure"
    assert daemon._last_success[("BTCUSDT", timeframe)] == first_success
    assert daemon.build_health_report(now).overall_status == "ERROR"


def test_current_gap_does_not_clear_prior_error_or_publish_ok():
    timeframe = "1h"
    duration = timeframe_to_milliseconds(timeframe)
    expected, now = duration, duration * 2
    repository = FakeRepository()
    daemon = daemon_for((timeframe,), repository, FakeRest(now))
    key = ("BTCUSDT", timeframe)
    daemon._pair_errors[key] = "not recovered yet"
    daemon.rest_client.source[("BTCUSDT", timeframe, expected)] = candle("OTHER", timeframe, expected)

    result = daemon.sync_expected("BTCUSDT", timeframe, [expected], expected, now)

    assert result.missing_after == 1
    assert daemon._pair_errors[key] == "not recovered yet"
    assert daemon._pair_status[key] == "DEGRADED"
    snapshot = next(value for value in daemon.build_health_report(now).snapshots
                    if value.symbol == "BTCUSDT")
    assert snapshot.status == "DEGRADED"
    assert snapshot.last_success_at is None


def test_fail_recover_fail_recover_and_repeated_success_is_stable():
    timeframe = "15m"
    duration = timeframe_to_milliseconds(timeframe)
    expected, now = duration, duration * 2
    repository = FakeRepository()
    daemon = daemon_for((timeframe,), repository, FailingRest(now))
    key = ("BTCUSDT", timeframe)

    daemon.sync_expected("BTCUSDT", timeframe, [expected], expected, now)
    daemon.rest_client = FakeRest(now)
    daemon.sync_expected("BTCUSDT", timeframe, [expected], expected, now)
    first_recovery = daemon._last_success[key]
    repository.values.clear()
    daemon.rest_client = FailingRest(now)
    daemon.sync_expected("BTCUSDT", timeframe, [expected], expected, now)
    daemon.rest_client = FakeRest(now)
    daemon.sync_expected("BTCUSDT", timeframe, [expected], expected, now)
    second_recovery = daemon._last_success[key]
    daemon.sync_expected("BTCUSDT", timeframe, [expected], expected, now)

    assert key not in daemon._pair_errors
    assert daemon._pair_status[key] == "OK"
    assert first_recovery <= second_recovery <= daemon._last_success[key]
    payload = json.loads(daemon.build_health_report(now).to_json())
    snapshot = next(value for value in payload["snapshots"] if value["symbol"] == "BTCUSDT")
    assert snapshot["status"] == "OK"
    assert snapshot["last_error"] is None


def test_narrow_success_cannot_clear_error_until_failed_scope_has_no_gaps():
    timeframe = "1m"
    expected = [0, 60_000, 120_000]
    now = 180_001
    repository = FakeRepository()
    daemon = daemon_for((timeframe,), repository, FailingRest(now))
    key = ("BTCUSDT", timeframe)

    daemon.sync_expected("BTCUSDT", timeframe, expected, expected[-1], now)
    daemon.rest_client = FakeRest(now)
    narrow = daemon.sync_expected("BTCUSDT", timeframe, [expected[-1]], expected[-1], now)

    assert narrow.missing_after == 2
    assert daemon._pair_status[key] == "DEGRADED"
    assert key in daemon._pair_errors

    full = daemon.sync_expected("BTCUSDT", timeframe, expected, expected[-1], now)
    assert full.missing_after == 0
    assert key not in daemon._pair_errors
    assert key not in daemon._pair_unresolved_expected
    assert daemon._pair_status[key] == "OK"


def test_narrow_success_cannot_mask_previous_current_gap():
    timeframe = "1m"
    now = 180_001
    repository = FakeRepository()
    rest = FakeRest(now)
    rest.source[("BTCUSDT", timeframe, 0)] = candle("OTHER", timeframe, 0)
    daemon = daemon_for((timeframe,), repository, rest)
    key = ("BTCUSDT", timeframe)

    gap = daemon.sync_expected("BTCUSDT", timeframe, [0, 60_000], 60_000, now)
    narrow = daemon.sync_expected("BTCUSDT", timeframe, [60_000], 60_000, now)

    assert gap.missing_after == 1
    assert narrow.missing_after == 1
    assert daemon._pair_status[key] == "DEGRADED"
    assert daemon._pair_unresolved_expected[key] == {0}
