import threading
import time

import pytest

from app.engine_market_data.continuous_sync_config import ContinuousSyncConfig
from app.engine_market_data.continuous_sync_daemon import (
    ContinuousBoundaryScheduler,
    ContinuousSyncDaemon,
    DueSyncTask,
)
from app.engine_market_data.errors import (
    CandleValidationError,
    PublicMarketDataError,
    UnsupportedTimeframeError,
)
from app.engine_market_data.failed_boundary_retry import (
    FailedBoundaryErrorClassification,
    FailedBoundaryRetryStatus,
    classify_failed_boundary_error,
)
from app.engine_market_data.timeframe import timeframe_to_milliseconds
from tests.engine_market_data_04_helpers import FakeRepository, FakeRest


TIMEFRAMES = ("1m", "5m", "15m", "1h", "4h", "1d")


class FailThenSucceedRest(FakeRest):
    def __init__(self, now_ms, failures, *, message="connection reset"):
        super().__init__(now_ms)
        self.failures = failures
        self.message = message

    def fetch_klines(self, **kwargs):
        self.calls.append((
            kwargs["symbol"],
            kwargs["timeframe"],
            kwargs["start_time_ms"],
            kwargs["end_time_ms"],
            kwargs["limit"],
        ))
        if self.failures > 0:
            self.failures -= 1
            try:
                raise OSError(self.message)
            except OSError as cause:
                raise PublicMarketDataError(
                    "Binance public REST request failed") from cause
        return FakeRest.fetch_klines(self, **kwargs)


class SelectiveFailureRest(FakeRest):
    def fetch_klines(self, **kwargs):
        if kwargs["symbol"] == "BTCUSDT":
            self.calls.append((
                kwargs["symbol"],
                kwargs["timeframe"],
                kwargs["start_time_ms"],
                kwargs["end_time_ms"],
                kwargs["limit"],
            ))
            try:
                raise OSError("temporary DNS failure")
            except OSError as cause:
                raise PublicMarketDataError(
                    "Binance public REST request failed") from cause
        return super().fetch_klines(**kwargs)


def config(timeframes=("1h",), symbols=("BTCUSDT",), **changes):
    values = dict(
        symbols=list(symbols),
        timeframes=list(timeframes),
        warmup=False,
        continuous=True,
        gap_check=False,
        warmup_depths={timeframe: 3 for timeframe in timeframes},
        gap_check_windows={timeframe: 3 for timeframe in timeframes},
        freshness_allowance_ms={timeframe: 1_000 for timeframe in timeframes},
        poll_interval_seconds=0.01,
        health_report_interval_seconds=60,
    )
    values.update(changes)
    return ContinuousSyncConfig(**values)


def boundary(timeframe):
    duration = timeframe_to_milliseconds(timeframe)
    expected = duration
    return duration, expected, expected + duration


def schedule_once(daemon, timeframe="1h", symbol="BTCUSDT"):
    _, expected, now = boundary(timeframe)
    result = daemon.sync_scheduled_boundary(
        DueSyncTask(symbol, timeframe, expected), now)
    return expected, now, result


def test_terminal_rest_failure_schedules_exactly_one_prompt_retry():
    _, expected, now = boundary("1h")
    daemon = ContinuousSyncDaemon(
        config(), FakeRepository(), FailThenSucceedRest(now, failures=1))

    _, _, result = schedule_once(daemon)
    record = next(iter(daemon._failed_boundary_retries.values()))

    assert result.error_classification == "RETRYABLE_TRANSIENT"
    assert record.identity == ("BTCUSDT", "1h", expected + 3_600_000)
    assert record.expected_open_times == (expected,)
    assert record.next_retry_at_ms == now + 5_000
    assert record.prompt_retry_attempt_count == 0
    assert record.status == FailedBoundaryRetryStatus.RETRY_SCHEDULED
    assert daemon.prompt_retry_metrics.scheduled == 1


@pytest.mark.parametrize("timeframe", TIMEFRAMES)
def test_prompt_retry_is_generic_and_recovers_exact_closed_boundary(timeframe):
    _, _, now = boundary(timeframe)
    repository = FakeRepository()
    rest = FailThenSucceedRest(now, failures=1)
    daemon = ContinuousSyncDaemon(
        config((timeframe,)), repository, rest)

    expected, _, failed = schedule_once(daemon, timeframe)
    results = daemon.run_prompt_retries(now + 5_000)

    assert failed.missing_after == 1
    assert results[0].missing_after == 0
    assert (daemon.config.symbols[0], timeframe, expected) in repository.values
    assert daemon._failed_boundary_retries == {}
    assert daemon.prompt_retry_metrics.recovered == 1
    assert daemon.build_health_report(now + 5_000).overall_status == "OK"


def test_repeated_transient_failure_uses_bounded_deterministic_backoff():
    _, _, now = boundary("1h")
    daemon = ContinuousSyncDaemon(
        config(), FakeRepository(), FailThenSucceedRest(now, failures=2))
    schedule_once(daemon)

    first = next(iter(daemon._failed_boundary_retries.values()))
    daemon.run_prompt_retries(first.next_retry_at_ms)
    after_first = next(iter(daemon._failed_boundary_retries.values()))
    assert after_first.prompt_retry_attempt_count == 1
    assert after_first.next_retry_at_ms == now + 15_000

    daemon.run_prompt_retries(after_first.next_retry_at_ms)
    assert daemon._failed_boundary_retries == {}
    assert daemon.prompt_retry_metrics.executed == 2
    assert daemon.prompt_retry_metrics.recovered == 1


def test_persistent_outage_stops_at_local_policy_without_tight_loop():
    _, _, now = boundary("1h")
    daemon = ContinuousSyncDaemon(
        config(), FakeRepository(), FailThenSucceedRest(now, failures=99))
    schedule_once(daemon)
    due_times = []
    while True:
        record = next(iter(daemon._failed_boundary_retries.values()))
        if record.next_retry_at_ms is None:
            break
        due_times.append(record.next_retry_at_ms)
        daemon.run_prompt_retries(record.next_retry_at_ms)

    record = next(iter(daemon._failed_boundary_retries.values()))
    executed = daemon.prompt_retry_metrics.executed
    daemon.run_prompt_retries(now + 1_000_000)

    assert [value - now for value in due_times] == [5_000, 15_000, 35_000, 75_000]
    assert record.prompt_retry_attempt_count == 4
    assert record.status == FailedBoundaryRetryStatus.TERMINAL_FOR_LOCAL_POLICY
    assert record.next_retry_at_ms is None
    assert daemon.prompt_retry_metrics.executed == executed
    assert daemon.build_health_report(now + 180_000).overall_status == "ERROR"


def test_scheduler_duplicate_event_has_one_logical_owner():
    duration, _, now = boundary("1h")
    scheduler = ContinuousBoundaryScheduler(["BTCUSDT"], ["1h"], {"1h": 1_000})
    due = duration * 3 + 1_000
    first = scheduler.get_due_tasks(due)
    second = scheduler.get_due_tasks(due)
    daemon = ContinuousSyncDaemon(
        config(), FakeRepository(), FailThenSucceedRest(now, failures=99))

    daemon.sync_scheduled_boundary(first[0], due)
    assert second == []
    assert len(daemon._failed_boundary_retries) == 1


def test_ordinary_scheduler_success_supersedes_pending_retry_without_duplicate_write():
    _, _, now = boundary("1h")
    repository = FakeRepository()
    rest = FailThenSucceedRest(now, failures=1)
    daemon = ContinuousSyncDaemon(config(), repository, rest)
    expected, _, _ = schedule_once(daemon)

    ordinary = daemon.sync_expected(
        "BTCUSDT", "1h", [expected], expected, now + 1_000)
    prompt = daemon.run_prompt_retries(now + 5_000)

    assert ordinary.missing_after == 0
    assert prompt == []
    assert daemon._failed_boundary_retries == {}
    assert repository.writes == 1


def test_gap_recovery_success_supersedes_pending_retry():
    _, _, now = boundary("1h")
    repository = FakeRepository()
    rest = FailThenSucceedRest(now, failures=1)
    daemon = ContinuousSyncDaemon(
        config(gap_check=True), repository, rest)
    schedule_once(daemon)

    recovered = daemon.run_gap_checks(now + 1_000, force=True)

    assert recovered[0].missing_after == 0
    assert daemon._failed_boundary_retries == {}
    assert daemon.run_prompt_retries(now + 5_000) == []


def test_symbols_and_timeframes_own_independent_retry_state():
    timeframes = ("1m", "1h")
    symbols = ("BTCUSDT", "ETHUSDT")
    now = 7_200_000
    daemon = ContinuousSyncDaemon(
        config(timeframes, symbols), FakeRepository(),
        SelectiveFailureRest(now))

    btc = daemon.sync_scheduled_boundary(
        DueSyncTask("BTCUSDT", "1h", 3_600_000), now)
    eth = daemon.sync_scheduled_boundary(
        DueSyncTask("ETHUSDT", "1h", 3_600_000), now)
    minute = daemon.sync_scheduled_boundary(
        DueSyncTask("BTCUSDT", "1m", 7_140_000), now)

    assert btc.missing_after == 1 and eth.missing_after == 0
    assert minute.missing_after == 1
    assert set(daemon._failed_boundary_retries) == {
        ("BTCUSDT", "1h", 7_200_000),
        ("BTCUSDT", "1m", 7_200_000),
    }
    assert ("ETHUSDT", "1h") not in daemon._pair_errors


def test_newer_boundary_does_not_cancel_or_duplicate_retry_for_older_gap():
    duration = timeframe_to_milliseconds("1h")
    now = duration * 3
    repository = FakeRepository()
    rest = FailThenSucceedRest(now, failures=1)
    daemon = ContinuousSyncDaemon(config(), repository, rest)
    older = duration
    newer = duration * 2

    daemon.sync_scheduled_boundary(
        DueSyncTask("BTCUSDT", "1h", older), duration * 2)
    daemon.sync_scheduled_boundary(
        DueSyncTask("BTCUSDT", "1h", newer), now)

    assert set(daemon._failed_boundary_retries) == {
        ("BTCUSDT", "1h", duration * 2),
    }
    assert ("BTCUSDT", "1h", newer) in repository.values
    assert ("BTCUSDT", "1h", older) not in repository.values


def test_scheduler_and_retry_never_select_future_or_unclosed_boundary():
    scheduler = ContinuousBoundaryScheduler(
        ["BTCUSDT"], list(TIMEFRAMES),
        {timeframe: 1_000 for timeframe in TIMEFRAMES},
    )
    now = 3 * 86_400_000 + 1_000

    tasks = scheduler.get_due_tasks(now)

    assert tasks
    assert all(
        task.expected_open_time_ms + timeframe_to_milliseconds(task.timeframe)
        <= now
        for task in tasks
    )


def test_shutdown_cancels_pending_retry_and_interrupts_daemon_wait():
    _, _, now = boundary("1h")
    daemon = ContinuousSyncDaemon(
        config(), FakeRepository(), FailThenSucceedRest(now, failures=99),
        clock_ms=lambda: now)
    schedule_once(daemon)
    thread = threading.Thread(target=daemon.run, daemon=True)
    thread.start()
    time.sleep(0.03)
    daemon.request_stop()
    thread.join(timeout=1)

    assert not thread.is_alive()
    assert not daemon._retry_in_flight
    assert all(
        record.status == FailedBoundaryRetryStatus.CANCELLED_ON_SHUTDOWN
        for record in daemon._failed_boundary_retries.values()
    )


def test_restart_startup_reconciliation_recovers_lost_in_memory_retry():
    duration = timeframe_to_milliseconds("1h")
    now = duration * 10
    expected = now - duration
    repository = FakeRepository()
    failed = ContinuousSyncDaemon(
        config(), repository, FailThenSucceedRest(now, failures=99))
    failed.sync_scheduled_boundary(
        DueSyncTask("BTCUSDT", "1h", expected), now)
    assert failed._failed_boundary_retries

    restarted = ContinuousSyncDaemon(
        config(warmup=True), repository, FakeRest(now))
    results = restarted.startup_warmup(now)

    assert results[0].missing_after == 0
    assert ("BTCUSDT", "1h", expected) in repository.values
    assert restarted._failed_boundary_retries == {}


def test_failed_startup_reconciliation_registers_prompt_retry():
    now = timeframe_to_milliseconds("1h") * 10
    daemon = ContinuousSyncDaemon(
        config(warmup=True), FakeRepository(),
        FailThenSucceedRest(now, failures=1))

    failed = daemon.startup_warmup(now)
    record = next(iter(daemon._failed_boundary_retries.values()))
    recovered = daemon.run_prompt_retries(record.next_retry_at_ms)

    assert failed[0].missing_after > 0
    assert recovered[0].missing_after == 0
    assert daemon._failed_boundary_retries == {}


@pytest.mark.parametrize(
    ("error", "classification"),
    [
        (TimeoutError("timeout"),
         FailedBoundaryErrorClassification.RETRYABLE_TRANSIENT),
        (OSError("connection reset"),
         FailedBoundaryErrorClassification.RETRYABLE_TRANSIENT),
        (PublicMarketDataError("Temporary Binance HTTP status 429"),
         FailedBoundaryErrorClassification.RETRYABLE_RATE_LIMITED),
        (PublicMarketDataError("Temporary Binance HTTP status 503"),
         FailedBoundaryErrorClassification.RETRYABLE_TRANSIENT),
        (UnsupportedTimeframeError("bad timeframe"),
         FailedBoundaryErrorClassification.NON_RETRYABLE_INPUT),
        (CandleValidationError("future candle"),
         FailedBoundaryErrorClassification.NON_RETRYABLE_DATA_VALIDATION),
        (TypeError("programming error"),
         FailedBoundaryErrorClassification.NON_RETRYABLE_PROGRAMMING),
    ],
)
def test_error_classification(error, classification):
    assert classify_failed_boundary_error(error) == classification


def test_non_rate_limited_http_4xx_is_non_retryable_input():
    class Response:
        status_code = 401

    error = RuntimeError("authentication/private endpoint rejected")
    error.response = Response()

    assert classify_failed_boundary_error(error) == (
        FailedBoundaryErrorClassification.NON_RETRYABLE_INPUT)


def test_non_retryable_failure_is_visible_and_not_looped():
    class InvalidRest(FakeRest):
        def fetch_klines(self, **kwargs):
            raise CandleValidationError("future/unclosed candle response")

    _, _, now = boundary("1h")
    daemon = ContinuousSyncDaemon(
        config(), FakeRepository(), InvalidRest(now))
    schedule_once(daemon)
    record = next(iter(daemon._failed_boundary_retries.values()))

    assert record.error_classification == (
        FailedBoundaryErrorClassification.NON_RETRYABLE_DATA_VALIDATION)
    assert record.status == FailedBoundaryRetryStatus.TERMINAL_FOR_LOCAL_POLICY
    assert record.next_retry_at_ms is None
    assert daemon.build_health_report(now).overall_status == "ERROR"
