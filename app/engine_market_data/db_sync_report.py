"""Audit model for a database synchronization run."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4


class SyncStatus(StrEnum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    NOOP_ALREADY_SYNCED = "NOOP_ALREADY_SYNCED"
    DEGRADED = "DEGRADED"
    ERROR = "ERROR"


@dataclass(slots=True)
class SyncReport:
    symbol: str
    boundary_timeframe: str | None = None
    target_timeframes: list[str] = field(default_factory=list)
    boundary_open_time_ms: int | None = None
    boundary_close_time_ms: int | None = None
    sync_id: str = field(default_factory=lambda: str(uuid4()))
    started_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at_utc: datetime | None = None
    status: str = SyncStatus.SUCCESS
    tasks_total: int = 0
    tasks_success: int = 0
    tasks_failed: int = 0
    expected_candles: int = 0
    existing_candles: int = 0
    missing_before: int = 0
    downloaded_candles: int = 0
    upserted_candles: int = 0
    missing_after: int = 0
    rest_calls: int = 0
    used_websocket_existing_data: bool = False
    used_rest_recovery: bool = False
    future_bars_used: bool = False
    health_status: str = "OK"
    errors: list[str] = field(default_factory=list)

    def finish(self) -> "SyncReport":
        self.finished_at_utc = datetime.now(timezone.utc)
        if self.errors and self.tasks_success == 0: self.status = SyncStatus.ERROR
        elif self.missing_after: self.status = SyncStatus.PARTIAL if self.tasks_success else SyncStatus.DEGRADED
        elif self.missing_before == 0: self.status = SyncStatus.NOOP_ALREADY_SYNCED
        else: self.status = SyncStatus.SUCCESS
        self.health_status = "OK" if self.missing_after == 0 and not self.errors else "DEGRADED"
        if self.future_bars_used: raise ValueError("database synchronization cannot use future bars")
        return self
