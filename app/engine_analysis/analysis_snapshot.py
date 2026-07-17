"""Stable output model for one online analysis window."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from typing import Any


class AnalysisSnapshotStatus(StrEnum):
    ANALYZED = "ANALYZED"
    SKIPPED_NOT_ENOUGH_DATA = "SKIPPED_NOT_ENOUGH_DATA"
    SKIPPED_DEGRADED_MARKET_DATA = "SKIPPED_DEGRADED_MARKET_DATA"
    SKIPPED_DUPLICATE_WINDOW = "SKIPPED_DUPLICATE_WINDOW"
    SKIPPED_INVALID_SNAPSHOT = "SKIPPED_INVALID_SNAPSHOT"
    ERROR = "ERROR"


def analysis_snapshot_id(symbol: str, timeframe: str, closed_until_ms: int) -> str:
    identity = f"{symbol.upper()}:{timeframe}:{int(closed_until_ms)}"
    digest = sha256(identity.encode("utf-8")).hexdigest()[:16]
    return f"analysis:{identity}:{digest}"


@dataclass(frozen=True, slots=True)
class AnalysisSnapshot:
    snapshot_id: str
    symbol: str
    timeframe: str
    closed_until_ms: int
    created_at_ms: int
    market_data_health: str
    degraded: bool
    enough_data: bool
    future_bars_used: bool = False
    regime: str | None = None
    confidence: float | None = None
    action: str | None = None
    impulse_phase: str | None = None
    entry_quality: str | None = None
    reason_codes: list[str] = field(default_factory=list)
    analysis_context: dict[str, Any] = field(default_factory=dict)
    human_readable_explanation: str | None = None
    status: str = AnalysisSnapshotStatus.ANALYZED.value
    skip_reason: str | None = None
    source_market_data_snapshot_id: str | None = None
    analysis_error: str | None = None

    def __post_init__(self) -> None:
        status = AnalysisSnapshotStatus(self.status)
        object.__setattr__(self, "status", status.value)
        if self.future_bars_used:
            raise ValueError("online analysis snapshots can never use future bars")
        if status is not AnalysisSnapshotStatus.ANALYZED and not self.skip_reason:
            raise ValueError("skip_reason is required for skipped and error snapshots")
        if self.confidence is not None and not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("confidence must be within [0.0, 1.0]")
        if not self.snapshot_id:
            raise ValueError("snapshot_id must not be empty")

    @classmethod
    def for_window(cls, *, symbol: str, timeframe: str, closed_until_ms: int, **values: Any) -> "AnalysisSnapshot":
        return cls(
            snapshot_id=analysis_snapshot_id(symbol, timeframe, closed_until_ms),
            symbol=symbol,
            timeframe=timeframe,
            closed_until_ms=closed_until_ms,
            **values,
        )
