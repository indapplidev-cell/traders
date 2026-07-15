"""Closed-candle freshness calculation and JSON health reports."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path

from app.engine_market_data.continuous_sync_config import FRESHNESS_ALLOWANCE_MS
from app.engine_market_data.continuous_sync_state import ContinuousSyncStatus
from app.engine_market_data.timeframe import timeframe_to_milliseconds


STATUS_PRIORITY = {"OK": 0, "STALE": 1, "GAP_DETECTED": 2, "RECOVERING": 3,
                   "DEGRADED": 4, "DISCONNECTED": 5, "ERROR": 6,
                   "NOT_CONFIGURED": 4}


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


@dataclass(slots=True)
class MarketDataFreshnessReport:
    generated_at: str
    daemon_instance_id: str
    overall_status: str
    snapshots: list[FreshnessSnapshot] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    timeframes: list[str] = field(default_factory=list)
    dry_run: bool = False

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
                 last_error: str | None = None) -> FreshnessSnapshot:
        expected = latest_expected_closed_open_time_ms(timeframe, now_ms)
        latest = self.repository.get_latest_closed_candle(symbol, timeframe)
        stored = latest.open_time_ms if latest is not None else None
        duration = timeframe_to_milliseconds(timeframe)
        lag_candles = max(0, (expected - stored) // duration) if stored is not None else max(1, missing_count)
        lag_ms = lag_candles * duration
        if status_override:
            status = status_override
        elif stored == expected:
            status = ContinuousSyncStatus.OK
        elif now_ms - (expected + duration) <= self.allowances_ms[timeframe]:
            status = ContinuousSyncStatus.RECOVERING
        else:
            status = ContinuousSyncStatus.STALE
        return FreshnessSnapshot(symbol, timeframe, expected, stored, lag_ms, lag_candles,
                                 str(status), missing_count, last_success_at, last_error)

    @staticmethod
    def report(snapshots: list[FreshnessSnapshot], daemon_instance_id: str, *,
               generated_at: datetime | None = None, symbols: list[str] | None = None,
               timeframes: list[str] | None = None, dry_run: bool = False) -> MarketDataFreshnessReport:
        overall = max((value.status for value in snapshots), key=lambda value: STATUS_PRIORITY.get(value, 6), default="OK")
        timestamp = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        return MarketDataFreshnessReport(timestamp, daemon_instance_id, overall, snapshots,
                                         symbols or sorted({s.symbol for s in snapshots}),
                                         timeframes or list(dict.fromkeys(s.timeframe for s in snapshots)), dry_run)
