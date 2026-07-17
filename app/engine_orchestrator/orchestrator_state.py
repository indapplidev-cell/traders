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
