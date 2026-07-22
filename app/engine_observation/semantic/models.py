from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.engine_observation.observer_reliability import CollectorStatus
from .contracts import AcceptanceImpact, Severity, WindowState


@dataclass(frozen=True, slots=True)
class ExpectedWindow:
    symbol: str
    timeframe: str
    closed_until_ms: int
    due: bool

    @property
    def key(self) -> tuple[str, str, int]:
        return self.symbol, self.timeframe, self.closed_until_ms


@dataclass(frozen=True, slots=True)
class RunSnapshot:
    run_id: str
    symbol: str
    primary_timeframe: str
    closed_until_ms: int
    status: str
    reason_code: str | None = None
    freshness_attempt_count: int = 0
    first_wait_at: datetime | None = None
    last_freshness_checked_at: datetime | None = None
    freshness_deadline_at: datetime | None = None
    waiting_timeframes: tuple[str, ...] = ()
    freshness_reasons: tuple[str, ...] = ()
    readiness_classification: str | None = None
    market_data_freshness_status: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    updated_at: datetime | None = None
    raw_diagnostics: Any = None
    future_bars_used: bool = False
    execution_approved: bool = False
    position_opened: bool = False

    @property
    def window_key(self) -> tuple[str, str, int]:
        return self.symbol, self.primary_timeframe, self.closed_until_ms


@dataclass(frozen=True, slots=True)
class ResultSnapshot:
    result_id: str
    run_id: str
    created_at: datetime
    result_type: str | None
    payload_hash: str


@dataclass(frozen=True, slots=True)
class CandleSnapshot:
    symbol: str
    timeframe: str
    open_time_ms: int
    close_time_ms: int
    is_closed: bool

    @property
    def key(self) -> tuple[str, str, int]:
        return self.symbol, self.timeframe, self.open_time_ms


@dataclass(frozen=True, slots=True)
class SemanticCollection:
    database_now: datetime | None
    runs: tuple[RunSnapshot, ...] = ()
    results: tuple[ResultSnapshot, ...] = ()
    candles: tuple[CandleSnapshot, ...] = ()
    run_status: CollectorStatus = CollectorStatus.UNAVAILABLE
    result_status: CollectorStatus = CollectorStatus.UNAVAILABLE
    candle_status: CollectorStatus = CollectorStatus.UNAVAILABLE
    query_durations_ms: dict[str, int] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)

    @property
    def complete(self) -> bool:
        return all(value == CollectorStatus.SUCCESS for value in (self.run_status, self.result_status, self.candle_status))


@dataclass(frozen=True, slots=True)
class Finding:
    incident_type: str
    severity: Severity
    acceptance_impact: AcceptanceImpact
    symbol: str | None = None
    timeframe: str | None = None
    closed_until_ms: int | None = None
    run_id: str | None = None
    reason_code: str | None = None
    stable_sub_key: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class WindowVerdict:
    key: tuple[str, str, int]
    state: WindowState
    run_id: str | None
    diagnostic_hash: str
    evidence: dict[str, Any] = field(default_factory=dict)
