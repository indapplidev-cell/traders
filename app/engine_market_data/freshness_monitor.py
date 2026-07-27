"""Boundary-aware closed-candle freshness calculation and JSON health reports."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
import json
from pathlib import Path

from app.engine_market_data.continuous_sync_config import FRESHNESS_ALLOWANCE_MS
from app.engine_market_data.continuous_sync_state import ContinuousSyncStatus
from app.engine_market_data.timeframe import timeframe_to_milliseconds


STATUS_PRIORITY = {"OK": 0, "STALE": 1, "GAP_DETECTED": 2, "RECOVERING": 3,
                   "DEGRADED": 4, "DISCONNECTED": 5, "ERROR": 6,
                   "NOT_CONFIGURED": 4}
HEALTH_REPORT_SCHEMA_VERSION = "MARKET_DATA_HEALTH/2.0"


class BoundaryTimingState(StrEnum):
    CURRENT = "CURRENT"
    WITHIN_GRACE = "WITHIN_GRACE"
    DEADLINE_EXPIRED = "DEADLINE_EXPIRED"


class HealthReasonCode(StrEnum):
    HEALTHY_CURRENT = "HEALTHY_CURRENT"
    BOUNDARY_WITHIN_GRACE = "BOUNDARY_WITHIN_GRACE"
    RECOVERY_AFTER_DEADLINE = "RECOVERY_AFTER_DEADLINE"
    REAL_GAP_RECOVERY = "REAL_GAP_RECOVERY"
    RETRY_BACKOFF_ACTIVE = "RETRY_BACKOFF_ACTIVE"
    RETRY_DEADLINE_EXPIRED = "RETRY_DEADLINE_EXPIRED"
    RUNTIME_NO_PROGRESS = "RUNTIME_NO_PROGRESS"
    ACTIVE_EXCHANGE_ERROR = "ACTIVE_EXCHANGE_ERROR"
    ACTIVE_DATABASE_ERROR = "ACTIVE_DATABASE_ERROR"
    STALE_CACHED_ERROR = "STALE_CACHED_ERROR"
    UNKNOWN_HEALTH_STATE = "UNKNOWN_HEALTH_STATE"


def utc_from_ms(value: int | None) -> str | None:
    if value is None:
        return None
    return (
        datetime.fromtimestamp(value / 1000, timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def latest_expected_closed_open_time_ms(timeframe: str, now_ms: int) -> int:
    duration = timeframe_to_milliseconds(timeframe)
    if now_ms < duration:
        raise ValueError("no closed candle exists yet")
    return now_ms - now_ms % duration - duration


def close_boundary_ms(open_time_ms: int, timeframe: str) -> int:
    return open_time_ms + timeframe_to_milliseconds(timeframe)


@dataclass(frozen=True, slots=True)
class FreshnessSnapshot:
    symbol: str
    timeframe: str
    expected_open_time_ms: int
    stored_open_time_ms: int | None
    freshness_lag_ms: int
    freshness_lag_candles: int
    status: str
    missing_count: int
    last_success_at: str | None = None
    last_error: str | None = None
    operational: bool = False
    ready: bool = False
    acceptance_blocking: bool = True
    reason_code: str = HealthReasonCode.UNKNOWN_HEALTH_STATE
    timing_state: str = BoundaryTimingState.DEADLINE_EXPIRED
    pair: str | None = None
    expected_boundary_utc: str | None = None
    deadline_utc: str | None = None
    observed_at_utc: str | None = None
    seconds_since_boundary: float = 0.0
    seconds_until_deadline: float = 0.0
    latest_closed_candle_utc: str | None = None
    heartbeat_progressing: bool = False
    scheduler_due: bool = False
    recovery_active: bool = False
    recovery_progressing: bool = False
    gap_count: int = 0
    active_error: bool = False
    cached_error_stale: bool = False
    clock_skew_seconds: float = 0.0
    deadline_expired: bool = False


@dataclass(slots=True)
class MarketDataFreshnessReport:
    generated_at: str
    daemon_instance_id: str
    overall_status: str
    snapshots: list[FreshnessSnapshot] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    timeframes: list[str] = field(default_factory=list)
    dry_run: bool = False
    schema_version: str = HEALTH_REPORT_SCHEMA_VERSION
    operational: bool = False
    ready: bool = False
    acceptance_blocking: bool = True
    reason_code: str = HealthReasonCode.UNKNOWN_HEALTH_STATE
    within_grace_count: int = 0
    deadline_expired_count: int = 0

    def to_dict(self) -> dict[str, object]:
        return {**asdict(self), "snapshots": [asdict(value) for value in self.snapshots]}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    def write_json(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(self.to_json() + "\n", encoding="utf-8")
        temporary.replace(target)


class FreshnessMonitor:
    def __init__(self, repository: object, *, allowances_ms: dict[str, int] | None = None) -> None:
        self.repository = repository
        self.allowances_ms = allowances_ms or FRESHNESS_ALLOWANCE_MS

    def snapshot(self, symbol: str, timeframe: str, now_ms: int, *, missing_count: int = 0,
                 status_override: str | None = None, last_success_at: str | None = None,
                 last_error: str | None = None, heartbeat_progressing: bool = True,
                 recovery_active: bool = False, recovery_progressing: bool = False,
                 cached_error_stale: bool = False, clock_skew_seconds: float = 0.0,
                 active_error_reason_code: str | None = None) -> FreshnessSnapshot:
        expected = latest_expected_closed_open_time_ms(timeframe, now_ms)
        latest = self.repository.get_latest_closed_candle(symbol, timeframe)
        stored = latest.open_time_ms if latest is not None else None
        duration = timeframe_to_milliseconds(timeframe)
        expected_boundary = close_boundary_ms(expected, timeframe)
        deadline = expected_boundary + self.allowances_ms[timeframe]
        lag_candles = max(0, (expected - stored) // duration) if stored is not None else max(1, missing_count)
        lag_ms = lag_candles * duration
        active_error = bool(last_error and not cached_error_stale) or status_override in {
            str(ContinuousSyncStatus.ERROR),
            str(ContinuousSyncStatus.DISCONNECTED),
        }
        real_gap = (
            lag_candles > 1
            or missing_count > 1
            or status_override == str(ContinuousSyncStatus.GAP_DETECTED)
        )
        missing_latest = stored != expected
        deadline_expired = missing_latest and now_ms > deadline
        scheduler_due = missing_latest and now_ms >= deadline

        if active_error:
            status = status_override if status_override in {
                str(ContinuousSyncStatus.ERROR),
                str(ContinuousSyncStatus.DISCONNECTED),
                str(ContinuousSyncStatus.DEGRADED),
            } else str(ContinuousSyncStatus.ERROR)
            reason = active_error_reason_code or HealthReasonCode.ACTIVE_EXCHANGE_ERROR
            operational = ready = False
        elif status_override == str(ContinuousSyncStatus.DEGRADED):
            status = str(ContinuousSyncStatus.DEGRADED)
            reason = (
                HealthReasonCode.REAL_GAP_RECOVERY
                if real_gap else HealthReasonCode.RUNTIME_NO_PROGRESS
            )
            operational = ready = False
        elif real_gap:
            status = (
                str(ContinuousSyncStatus.RECOVERING)
                if heartbeat_progressing or recovery_progressing
                else str(ContinuousSyncStatus.DEGRADED)
            )
            reason = (
                HealthReasonCode.REAL_GAP_RECOVERY
                if status == str(ContinuousSyncStatus.RECOVERING)
                else HealthReasonCode.RUNTIME_NO_PROGRESS
            )
            recovery_active = True
            recovery_progressing = heartbeat_progressing or recovery_progressing
            operational = ready = False
        elif not missing_latest:
            status = str(ContinuousSyncStatus.OK)
            reason = HealthReasonCode.HEALTHY_CURRENT
            operational = ready = True
        elif not deadline_expired and heartbeat_progressing:
            # The deadline is inclusive. At the exact deadline the scheduler is
            # due, but the service is still within its configured contract.
            status = str(ContinuousSyncStatus.OK)
            reason = HealthReasonCode.BOUNDARY_WITHIN_GRACE
            operational = ready = True
        elif not heartbeat_progressing:
            status = str(ContinuousSyncStatus.DEGRADED)
            reason = HealthReasonCode.RUNTIME_NO_PROGRESS
            operational = ready = False
        else:
            status = str(ContinuousSyncStatus.RECOVERING)
            reason = HealthReasonCode.RECOVERY_AFTER_DEADLINE
            recovery_active = True
            recovery_progressing = True
            operational = ready = False

        timing_state = (
            BoundaryTimingState.CURRENT
            if not missing_latest
            else BoundaryTimingState.DEADLINE_EXPIRED
            if deadline_expired
            else BoundaryTimingState.WITHIN_GRACE
        )
        return FreshnessSnapshot(
            symbol=symbol,
            timeframe=timeframe,
            expected_open_time_ms=expected,
            stored_open_time_ms=stored,
            freshness_lag_ms=lag_ms,
            freshness_lag_candles=lag_candles,
            status=str(status),
            missing_count=missing_count,
            last_success_at=last_success_at,
            last_error=last_error,
            operational=operational,
            ready=ready,
            acceptance_blocking=not (operational and ready),
            reason_code=str(reason),
            timing_state=str(timing_state),
            pair=symbol,
            expected_boundary_utc=utc_from_ms(expected_boundary),
            deadline_utc=utc_from_ms(deadline),
            observed_at_utc=utc_from_ms(now_ms),
            seconds_since_boundary=round((now_ms - expected_boundary) / 1000, 3),
            seconds_until_deadline=round((deadline - now_ms) / 1000, 3),
            latest_closed_candle_utc=(
                utc_from_ms(close_boundary_ms(stored, timeframe))
                if stored is not None else None
            ),
            heartbeat_progressing=heartbeat_progressing,
            scheduler_due=scheduler_due,
            recovery_active=recovery_active,
            recovery_progressing=recovery_progressing,
            gap_count=max(0, missing_count if real_gap else lag_candles - 1),
            active_error=active_error,
            cached_error_stale=cached_error_stale,
            clock_skew_seconds=round(clock_skew_seconds, 3),
            deadline_expired=deadline_expired,
        )

    @staticmethod
    def report(snapshots: list[FreshnessSnapshot], daemon_instance_id: str, *,
               generated_at: datetime | None = None, symbols: list[str] | None = None,
               timeframes: list[str] | None = None, dry_run: bool = False) -> MarketDataFreshnessReport:
        overall = max((value.status for value in snapshots), key=lambda value: STATUS_PRIORITY.get(value, 6), default="OK")
        timestamp = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        operational = bool(snapshots) and all(value.operational for value in snapshots)
        ready = bool(snapshots) and all(value.ready for value in snapshots)
        within_grace = sum(
            value.reason_code == HealthReasonCode.BOUNDARY_WITHIN_GRACE
            for value in snapshots
        )
        deadline_expired = sum(value.deadline_expired for value in snapshots)
        if overall == str(ContinuousSyncStatus.OK) and within_grace:
            reason = HealthReasonCode.BOUNDARY_WITHIN_GRACE
        elif overall == str(ContinuousSyncStatus.OK):
            reason = HealthReasonCode.HEALTHY_CURRENT
        else:
            reason = next(
                (
                    value.reason_code
                    for value in snapshots
                    if value.status == overall
                ),
                HealthReasonCode.UNKNOWN_HEALTH_STATE,
            )
        return MarketDataFreshnessReport(timestamp, daemon_instance_id, overall, snapshots,
                                         symbols or sorted({s.symbol for s in snapshots}),
                                         timeframes or list(dict.fromkeys(s.timeframe for s in snapshots)),
                                         dry_run, HEALTH_REPORT_SCHEMA_VERSION, operational, ready,
                                         not (operational and ready), str(reason), within_grace,
                                         deadline_expired)
