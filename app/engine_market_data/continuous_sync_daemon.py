"""Persistent closed-candle PostgreSQL synchronizer.

This runtime intentionally imports only standard library and engine_market_data.
It never invokes analysis or trading stages.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import random
import signal
import socket
import threading
import time
from typing import Callable, Sequence
from uuid import uuid4

from app.engine_market_data.continuous_sync_config import (
    ContinuousSyncConfig, GAP_CHECK_INTERVAL_MS,
)
from app.engine_market_data.continuous_sync_state import ContinuousSyncStatus, SyncStateUpdate
from app.engine_market_data.exchange_time_sync import ExchangeTimeSync
from app.engine_market_data.freshness_monitor import (
    FreshnessMonitor, FreshnessSnapshot, MarketDataFreshnessReport,
    close_boundary_ms, latest_expected_closed_open_time_ms,
)
from app.engine_market_data.historical_backfill_planner import (
    BackfillRange, group_missing_open_times_into_ranges, split_backfill_range,
)
from app.engine_market_data.timeframe import timeframe_to_milliseconds


logger = logging.getLogger(__name__)

MAX_OPERATIONAL_ERROR_LENGTH = 4000


def _operational_error_text(error: BaseException) -> str:
    value = str(error)
    if len(value) <= MAX_OPERATIONAL_ERROR_LENGTH:
        return value
    return value[:MAX_OPERATIONAL_ERROR_LENGTH] + "... <truncated>"


@dataclass(frozen=True, slots=True)
class DueSyncTask:
    symbol: str
    timeframe: str
    expected_open_time_ms: int


class ContinuousBoundaryScheduler:
    """Emit each symbol/timeframe after its UTC close-boundary allowance."""

    def __init__(self, symbols: Sequence[str], timeframes: Sequence[str], allowances_ms: dict[str, int]) -> None:
        self.symbols = tuple(symbols)
        self.timeframes = tuple(timeframes)
        self.allowances_ms = allowances_ms
        self._emitted: set[tuple[str, str, int]] = set()

    def get_due_tasks(self, now_ms: int) -> list[DueSyncTask]:
        tasks: list[DueSyncTask] = []
        for timeframe in self.timeframes:
            eligible_now = now_ms - self.allowances_ms[timeframe]
            try:
                expected = latest_expected_closed_open_time_ms(timeframe, eligible_now)
            except ValueError:
                continue
            for symbol in self.symbols:
                key = (symbol, timeframe, expected)
                if key not in self._emitted:
                    self._emitted.add(key)
                    tasks.append(DueSyncTask(symbol, timeframe, expected))
        return tasks


class WarmupPlanner:
    def __init__(self, depths: dict[str, int]) -> None:
        self.depths = depths

    def expected_open_times(self, timeframe: str, expected_latest_open_time_ms: int,
                            latest_stored_open_time_ms: int | None) -> list[int]:
        duration = timeframe_to_milliseconds(timeframe)
        if latest_stored_open_time_ms is None:
            start = expected_latest_open_time_ms - (self.depths[timeframe] - 1) * duration
        else:
            start = latest_stored_open_time_ms + duration
        if start < 0 or start > expected_latest_open_time_ms:
            return []
        return list(range(start, expected_latest_open_time_ms + duration, duration))


@dataclass(slots=True)
class PairSyncResult:
    symbol: str
    timeframe: str
    expected_open_time_ms: int
    missing_before: int = 0
    missing_after: int = 0
    inserted_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    rest_calls: int = 0
    error: str | None = None


class ContinuousSyncDaemon:
    def __init__(self, config: ContinuousSyncConfig, repository: object, rest_client: object,
                 *, state_repository: object | None = None,
                 clock_ms: Callable[[], int] = lambda: int(time.time() * 1000),
                 sleep: Callable[[float], None] = time.sleep,
                 random_uniform: Callable[[float, float], float] = random.uniform) -> None:
        self.config = config
        self.repository = repository
        self.rest_client = rest_client
        self.state_repository = state_repository
        self.clock_ms = clock_ms
        self.sleep = sleep
        self.random_uniform = random_uniform
        self.daemon_instance_id = config.daemon_instance_id or f"market-data-sync-{socket.gethostname()}-{uuid4().hex[:8]}"
        self.time_sync = ExchangeTimeSync(rest_client, clock_ms=clock_ms)
        self.scheduler = ContinuousBoundaryScheduler(config.symbols, config.timeframes,
                                                     config.freshness_allowance_ms)
        self.warmup_planner = WarmupPlanner(config.warmup_depths)
        self.freshness_monitor = FreshnessMonitor(repository, allowances_ms=config.freshness_allowance_ms)
        self._stop_event = threading.Event()
        self._last_gap_check_ms = {timeframe: 0 for timeframe in config.timeframes}
        self._last_health_report_ms = 0
        self._pair_status: dict[tuple[str, str], str] = {}
        self._pair_errors: dict[tuple[str, str], str] = {}
        self._pair_missing: dict[tuple[str, str], int] = {}
        self._last_success: dict[tuple[str, str], str] = {}

    def request_stop(self, *_args: object) -> None:
        self._stop_event.set()

    def install_signal_handlers(self) -> None:
        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGINT, self.request_stop)
            signal.signal(signal.SIGTERM, self.request_stop)

    def exchange_now_ms(self) -> int:
        return self.time_sync.now_ms_exchange_adjusted()

    def startup_warmup(self, now_ms: int | None = None) -> list[PairSyncResult]:
        now = self.exchange_now_ms() if now_ms is None else now_ms
        results: list[PairSyncResult] = []
        for symbol in self.config.symbols:
            for timeframe in self.config.timeframes:
                expected = latest_expected_closed_open_time_ms(timeframe, now)
                try:
                    latest = self.repository.get_latest_closed_candle(symbol, timeframe)
                    latest_open = latest.open_time_ms if latest is not None else None
                    candidates = self.warmup_planner.expected_open_times(timeframe, expected, latest_open)
                    results.append(self.sync_expected(symbol, timeframe, candidates, expected, now))
                except Exception as exc:
                    result = PairSyncResult(symbol, timeframe, expected, failed_count=1,
                                            missing_after=1, error=str(exc))
                    key = (symbol, timeframe)
                    self._pair_status[key] = str(ContinuousSyncStatus.ERROR)
                    self._pair_errors[key] = str(exc)
                    self._pair_missing[key] = 1
                    results.append(result)
                    logger.exception("startup warmup planning failed for %s %s", symbol, timeframe)
        return results

    def sync_latest(self, now_ms: int | None = None) -> list[PairSyncResult]:
        now = self.exchange_now_ms() if now_ms is None else now_ms
        return [self.sync_expected(symbol, timeframe, [latest_expected_closed_open_time_ms(timeframe, now)],
                                   latest_expected_closed_open_time_ms(timeframe, now), now)
                for symbol in self.config.symbols for timeframe in self.config.timeframes]

    def sync_expected(self, symbol: str, timeframe: str, expected_open_times: Sequence[int],
                      expected_latest_open_time_ms: int, now_ms: int) -> PairSyncResult:
        expected = sorted(set(expected_open_times))
        result = PairSyncResult(symbol, timeframe, expected_latest_open_time_ms)
        key = (symbol, timeframe)
        attempted_at = datetime.now(timezone.utc)
        try:
            missing = self.repository.find_missing_open_times(symbol, timeframe, expected)
            result.missing_before = len(missing)
            result.skipped_count = len(expected) - len(missing)
            self._pair_missing[key] = len(missing)
            if missing:
                self._pair_status[key] = str(ContinuousSyncStatus.GAP_DETECTED)
                self._persist_state(symbol, timeframe, expected_latest_open_time_ms, now_ms,
                                    status=ContinuousSyncStatus.GAP_DETECTED, missing=len(missing),
                                    attempted_at=attempted_at)
            if missing and not self.config.dry_run:
                self._pair_status[key] = str(ContinuousSyncStatus.RECOVERING)
                self._persist_state(symbol, timeframe, expected_latest_open_time_ms, now_ms,
                                    status=ContinuousSyncStatus.RECOVERING, missing=len(missing),
                                    recovering=len(missing), attempted_at=attempted_at)
                exact = set(missing)
                for missing_range in group_missing_open_times_into_ranges(missing, timeframe, symbol):
                    for batch in split_backfill_range(missing_range, self.config.max_rest_batch_size):
                        candles = self.rest_client.fetch_klines(
                            symbol=symbol, timeframe=timeframe,
                            start_time_ms=batch.start_time_ms,
                            end_time_ms=batch.end_time_ms + timeframe_to_milliseconds(timeframe) - 1,
                            limit=batch.expected_count,
                        )
                        result.rest_calls += 1
                        unique = {
                            candle.open_time_ms: candle for candle in candles
                            if candle.is_closed and candle.open_time_ms in exact
                            and candle.close_time_ms < now_ms
                        }
                        if unique:
                            result.inserted_count += int(
                                self.repository.upsert_candles(list(unique.values())))
            if self.config.dry_run:
                result.missing_after = len(missing)
                self._pair_status[key] = str(ContinuousSyncStatus.GAP_DETECTED if missing else ContinuousSyncStatus.OK)
            else:
                after = self.repository.find_missing_open_times(symbol, timeframe, expected)
                result.missing_after = len(after)
                result.failed_count = len(after)
                self._pair_missing[key] = len(after)
                has_prior_error = key in self._pair_errors
                self._pair_status[key] = str(
                    ContinuousSyncStatus.DEGRADED
                    if after or has_prior_error else ContinuousSyncStatus.OK)
                if not after and not has_prior_error:
                    self._last_success[key] = attempted_at.isoformat().replace("+00:00", "Z")
                sticky_error = RuntimeError(self._pair_errors[key]) if has_prior_error else None
            self._persist_state(symbol, timeframe, expected_latest_open_time_ms, now_ms,
                                status=self._pair_status[key], missing=result.missing_after,
                                attempted_at=attempted_at, result=result,
                                error=(sticky_error if not self.config.dry_run else None))
        except Exception as exc:
            error_text = _operational_error_text(exc)
            result.error = error_text
            result.failed_count = max(1, len(expected))
            result.missing_after = result.failed_count
            self._pair_status[key] = str(ContinuousSyncStatus.ERROR)
            self._pair_errors[key] = error_text
            self._pair_missing[key] = result.missing_after
            self._persist_state(symbol, timeframe, expected_latest_open_time_ms, now_ms,
                                status=ContinuousSyncStatus.ERROR, missing=result.missing_after,
                                attempted_at=attempted_at, result=result, error=exc)
            logger.exception("market-data sync failed for %s %s", symbol, timeframe)
        return result

    def run_gap_checks(self, now_ms: int | None = None, *, force: bool = False) -> list[PairSyncResult]:
        now = self.exchange_now_ms() if now_ms is None else now_ms
        results: list[PairSyncResult] = []
        for timeframe in self.config.timeframes:
            if not force and now - self._last_gap_check_ms[timeframe] < GAP_CHECK_INTERVAL_MS[timeframe]:
                continue
            self._last_gap_check_ms[timeframe] = now
            duration = timeframe_to_milliseconds(timeframe)
            latest = latest_expected_closed_open_time_ms(timeframe, now)
            count = self.config.gap_check_windows[timeframe]
            expected = list(range(max(0, latest - (count - 1) * duration), latest + duration, duration))
            for symbol in self.config.symbols:
                results.append(self.sync_expected(symbol, timeframe, expected, latest, now))
        return results

    def build_health_report(self, now_ms: int | None = None) -> MarketDataFreshnessReport:
        now = self.exchange_now_ms() if now_ms is None else now_ms
        snapshots: list[FreshnessSnapshot] = []
        for symbol in self.config.symbols:
            for timeframe in self.config.timeframes:
                key = (symbol, timeframe)
                override = self._pair_status.get(key)
                if override == "OK":
                    override = None
                try:
                    snapshots.append(self.freshness_monitor.snapshot(
                        symbol, timeframe, now, missing_count=self._pair_missing.get(key, 0),
                        status_override=override, last_success_at=self._last_success.get(key),
                        last_error=self._pair_errors.get(key),
                    ))
                except Exception as exc:
                    self._pair_errors[key] = str(exc)
                    snapshots.append(FreshnessSnapshot(
                        symbol, timeframe, latest_expected_closed_open_time_ms(timeframe, now),
                        None, 0, max(1, self._pair_missing.get(key, 1)), "ERROR",
                        max(1, self._pair_missing.get(key, 1)), self._last_success.get(key), str(exc)))
        return self.freshness_monitor.report(snapshots, self.daemon_instance_id,
                                             symbols=list(self.config.symbols),
                                             timeframes=list(self.config.timeframes),
                                             dry_run=self.config.dry_run)

    def write_health_report(self, now_ms: int | None = None) -> MarketDataFreshnessReport:
        report = self.build_health_report(now_ms)
        if self.config.health_report_path:
            report.write_json(self.config.health_report_path)
        return report

    def run(self) -> MarketDataFreshnessReport:
        self.install_signal_handlers()
        try:
            self.time_sync.sync()
        except Exception as exc:
            logger.warning("Binance time sync failed, retry loop will continue: %s", exc)
            for key in ((s, t) for s in self.config.symbols for t in self.config.timeframes):
                self._pair_status[key] = str(ContinuousSyncStatus.DISCONNECTED)
                self._pair_errors[key] = _operational_error_text(exc)
        if self.config.warmup:
            self.startup_warmup()
            if self.config.gap_check:
                self.run_gap_checks(force=True)
        elif not self.config.continuous:
            self.sync_latest()
        if not self.config.continuous:
            return self.write_health_report()

        cycles = 0
        backoff = self.config.backoff_initial_seconds
        while not self._stop_event.is_set():
            try:
                now = self.exchange_now_ms()
                for task in self.scheduler.get_due_tasks(now):
                    self.sync_expected(task.symbol, task.timeframe, [task.expected_open_time_ms],
                                       task.expected_open_time_ms, now)
                if self.config.gap_check:
                    self.run_gap_checks(now)
                if now - self._last_health_report_ms >= self.config.health_report_interval_seconds * 1000:
                    self.write_health_report(now)
                    self._last_health_report_ms = now
                backoff = self.config.backoff_initial_seconds
            except Exception:
                logger.exception("continuous market-data cycle failed")
                delay = min(backoff, self.config.backoff_max_seconds)
                self._stop_event.wait(self.random_uniform(delay * 0.8, delay * 1.2))
                backoff = min(backoff * 2, self.config.backoff_max_seconds)
            cycles += 1
            if self.config.stop_after_cycles is not None and cycles >= self.config.stop_after_cycles:
                break
            self._stop_event.wait(self.config.poll_interval_seconds)
        return self.write_health_report()

    def _persist_state(self, symbol: str, timeframe: str, expected: int, now_ms: int, *,
                       status: str, missing: int, attempted_at: datetime,
                       recovering: int = 0, result: PairSyncResult | None = None,
                       error: Exception | None = None) -> None:
        if self.state_repository is None or self.config.dry_run:
            return
        try:
            duration = timeframe_to_milliseconds(timeframe)
            latest = self.repository.get_latest_closed_candle(symbol, timeframe)
            stored = latest.open_time_ms if latest else None
            lag_candles = max(0, (expected - stored) // duration) if stored is not None else max(1, missing)
            update = SyncStateUpdate(
                symbol=symbol, timeframe=timeframe, daemon_instance_id=self.daemon_instance_id,
                status=str(status), last_expected_open_time_ms=expected,
                last_expected_close_boundary_ms=close_boundary_ms(expected, timeframe),
                last_stored_open_time_ms=stored,
                last_stored_close_boundary_ms=(close_boundary_ms(stored, timeframe) if stored is not None else None),
                freshness_lag_ms=lag_candles * duration, freshness_lag_candles=lag_candles,
                missing_count=missing, recovering_count=recovering, last_attempt_at=attempted_at,
                last_success_at=(attempted_at if str(status) == "OK" else None),
                last_error_at=(attempted_at if error else None),
                last_error_code=(type(error).__name__ if error else None),
                last_error_message=(str(error) if error else None),
                last_inserted_count=result.inserted_count if result else 0,
                last_updated_count=result.updated_count if result else 0,
                last_skipped_count=result.skipped_count if result else 0,
                last_failed_count=result.failed_count if result else 0,
            )
            self.state_repository.upsert(update)
        except Exception:
            logger.exception("could not persist sync state for %s %s", symbol, timeframe)


def simulate_downtime_missing_open_times(timeframe: str, expected_latest_open_time_ms: int,
                                         latest_stored_open_time_ms: int | None,
                                         warmup_depth: int) -> list[int]:
    """Pure helper used by restart/downtime recovery tests; it never changes clocks."""
    return WarmupPlanner({timeframe: warmup_depth}).expected_open_times(
        timeframe, expected_latest_open_time_ms, latest_stored_open_time_ms)
