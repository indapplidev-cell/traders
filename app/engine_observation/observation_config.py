from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

UTC = timezone.utc


def parse_utc(value: str | datetime) -> datetime:
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError("observation timestamps must be explicitly UTC")
    return parsed.astimezone(UTC)


def floor_boundary(value: datetime, minutes: int = 15) -> datetime:
    value = parse_utc(value)
    seconds = minutes * 60
    return datetime.fromtimestamp(int(value.timestamp()) // seconds * seconds, tz=UTC)


@dataclass(frozen=True, slots=True)
class ObservationThresholds:
    missing_warning_ratio: float = 0.0
    missing_fail_ratio: float = 0.01
    freshness_warning_ratio: float = 0.01
    freshness_fail_ratio: float = 0.05
    completion_warning_ratio: float = 0.99
    latency_warning_ms: int = 300_000
    latency_fail_ms: int = 900_000
    reclaim_interval_seconds: int = 300
    error_message_max_length: int = 4_000


@dataclass(frozen=True, slots=True)
class ObservationConfig:
    symbols: tuple[str, ...] = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
    primary_timeframe: str = "15m"
    start_utc: datetime | None = None
    end_utc: datetime | None = None
    last_hours: float | None = 24.0
    minimum_window_hours: float = 24.0
    output_dir: Path = Path("reports/engine_observation/online_pipeline_observation_01")
    report_json: str = "ONLINE_PIPELINE_OBSERVATION_01_SUMMARY.json"
    report_md: str = "ONLINE_PIPELINE_OBSERVATION_01_REPORT.md"
    fail_on_warning: bool = False
    thresholds: ObservationThresholds = ObservationThresholds()

    def __post_init__(self) -> None:
        symbols = tuple(dict.fromkeys(item.strip().upper() for item in self.symbols if item.strip()))
        if not symbols:
            raise ValueError("at least one symbol is required")
        if self.primary_timeframe != "15m":
            raise ValueError("ONLINE-PIPELINE-OBSERVATION-01 supports primary timeframe 15m")
        explicit = self.start_utc is not None or self.end_utc is not None
        if explicit and (self.start_utc is None or self.end_utc is None):
            raise ValueError("start_utc and end_utc must be supplied together")
        if explicit and self.last_hours is not None:
            raise ValueError("explicit interval and last_hours are mutually exclusive")
        if not explicit and (self.last_hours is None or self.last_hours <= 0):
            raise ValueError("last_hours must be positive")
        if self.minimum_window_hours <= 0:
            raise ValueError("minimum_window_hours must be positive")
        if explicit:
            start, end = parse_utc(self.start_utc), parse_utc(self.end_utc)
            if start >= end:
                raise ValueError("start_utc must precede end_utc")
            if start != floor_boundary(start) or end != floor_boundary(end):
                raise ValueError("explicit interval endpoints must be closed 15m boundaries")
            object.__setattr__(self, "start_utc", start)
            object.__setattr__(self, "end_utc", end)
        object.__setattr__(self, "symbols", symbols)
        object.__setattr__(self, "output_dir", Path(self.output_dir))

    def interval(self, now: datetime | None = None) -> tuple[datetime, datetime]:
        if self.start_utc is not None:
            return self.start_utc, self.end_utc  # type: ignore[return-value]
        end = floor_boundary(now or datetime.now(UTC))
        return end - timedelta(hours=float(self.last_hours)), end
