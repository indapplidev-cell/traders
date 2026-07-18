"""Mutable daemon-only counters; durable window state lives in PostgreSQL."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class OrchestratorState:
    cycles: int = 0
    detected_windows: int = 0
    completed_windows: int = 0
    skipped_windows: int = 0
    duplicate_windows: int = 0
    error_windows: int = 0
    last_error: str | None = None
    last_processed: dict[str, dict[str, Any]] = field(default_factory=dict)
    safety_totals: dict[str, int] = field(default_factory=dict)
    waiting_windows: int = 0
    waiting_by_timeframe: dict[str, int] = field(default_factory=dict)
    waiting_by_symbol: dict[str, int] = field(default_factory=dict)
    oldest_wait_age_seconds: float = 0
    next_retry_at: str | None = None
    freshness_retry_attempts_total: int = 0
    freshness_recovered_total: int = 0
    freshness_timeouts_total: int = 0
    last_freshness_recovery_at: str | None = None
    last_freshness_timeout_at: str | None = None
