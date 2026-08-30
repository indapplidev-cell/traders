from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ServiceRecord:
    name: str
    status: str
    observed_at: datetime
    message: str | None = None


@dataclass(frozen=True, slots=True)
class HealthRecord:
    status: str
    observed_at: datetime
    services: tuple[ServiceRecord, ...]
    timing_state: str = "UNKNOWN"
    reason_code: str = "UNKNOWN"
    operational: bool = False
    ready: bool = False
    acceptance_blocking: bool = True


@dataclass(frozen=True, slots=True)
class MarketRecord:
    symbol: str
    status: str
    updated_at: datetime
    timeframe: str = "15m"
    latest_price: Decimal | None = None
    closed_until_ms: int | None = None
    regime: str | None = None
    setup_status: str = "UNKNOWN"
    risk_status: str | None = None
    strategy_status: str | None = None
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    close: Decimal | None = None
    volume: Decimal | None = None
    has_gaps: bool | None = None
    enough_data: bool | None = None
    future_bars_used: bool = False


@dataclass(frozen=True, slots=True)
class AnalysisRecord:
    analysis_id: str
    symbol: str
    timeframe: str
    closed_until_ms: int
    status: str
    market_data_status: str
    updated_at: datetime
    regime: str | None = None
    direction: str = "UNKNOWN"
    confidence: float | None = None
    impulse_phase: str | None = None
    entry_quality: str | None = None
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SetupRecord:
    setup_id: str
    symbol: str
    timeframe: str
    closed_until_ms: int
    status: str
    setup_type: str
    direction: str
    quality: str
    updated_at: datetime
    quality_score: float | None = None
    confirmation_state: str = "NOT_APPLICABLE"
    reason_codes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    invalidation_reasons: tuple[str, ...] = ()
    strategy_status: str | None = None
    risk_status: str | None = None
    paper_status: str | None = None
    hypothetical_entry: Decimal | None = None
    hypothetical_stop: Decimal | None = None
    hypothetical_target: Decimal | None = None
    planned_rr: Decimal | None = None
    executable: bool = False
    cursor_identifier: str | None = None


@dataclass(frozen=True, slots=True)
class IncidentRecord:
    incident_id: str
    status: str
    severity: str
    source: str
    title: str
    opened_at: datetime
    updated_at: datetime
    symbol: str | None = None
    resolved_at: datetime | None = None
    safe_description: str = "An operational condition was recorded."
    reason_code: str | None = None
    timeframe: str | None = None
    closed_until_ms: int | None = None


@dataclass(frozen=True, slots=True)
class RunRecord:
    run_id: str
    symbol: str
    primary_timeframe: str
    closed_until_ms: int
    status: str
    attempt_count: int
    result_count: int


@dataclass(frozen=True, slots=True)
class TradingUniverseSymbolReadinessRecord:
    symbol: str
    ready_timeframes: tuple[str, ...]
    history_ready: bool
    analysis_ready: bool
    setup_ready: bool
    strategy_compatible: bool
    risk_compatible: bool


@dataclass(frozen=True, slots=True)
class CursorPosition:
    updated_at: datetime
    identifier: str


@dataclass(frozen=True, slots=True)
class SetupQuery:
    limit: int
    cursor: CursorPosition | None = None
    symbol: str | None = None
    status: str | None = None
    from_at: datetime | None = None
    to_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class IncidentQuery:
    limit: int
    cursor: CursorPosition | None = None
    symbol: str | None = None
    status: str | None = None
    severity: str | None = None
    from_at: datetime | None = None
    to_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class RecordPage:
    items: tuple[object, ...] = field(default_factory=tuple)
    has_more: bool = False


@dataclass(frozen=True, slots=True)
class PaperPositionQuery:
    limit: int
    cursor: CursorPosition | None = None
    state: str | None = None
    symbol: str | None = None


@dataclass(frozen=True, slots=True)
class PaperTradeQuery:
    limit: int
    cursor: CursorPosition | None = None
    symbol: str | None = None
    side: str | None = None
    exit_reason: str | None = None
    from_at: datetime | None = None
    to_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class PaperListQuery:
    limit: int
    cursor: CursorPosition | None = None
    symbol: str | None = None


@dataclass(frozen=True, slots=True)
class PaperOrderRecordView:
    order_id: str
    command_id: str
    symbol: str
    side: str
    order_role: str
    order_type: str
    state: str
    requested_quantity: Decimal
    filled_quantity: Decimal
    average_fill_price: Decimal | None
    reason_code: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class PaperFillRecordView:
    fill_id: str
    order_id: str
    symbol: str
    side: str
    fill_role: str
    quantity: Decimal
    price: Decimal
    fee_amount: Decimal
    fee_asset: str
    filled_at: datetime


@dataclass(frozen=True, slots=True)
class PaperJournalRecordView:
    event_id: str
    entity_type: str
    entity_id: str
    event_type: str
    state_version: int
    reason_code: str
    causation_id: str
    correlation_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class PaperPositionRecordView:
    position: object
    entry_time: datetime
    updated_at: datetime
    command_id: str | None = None
    exit_reason: str | None = None
    entry_order_id: str | None = None
    entry_fill_id: str | None = None
    close_order_id: str | None = None
    close_fill_id: str | None = None
    exit_cursor_status: str | None = None
    exit_decision: str | None = None
    lifecycle_events: tuple[dict[str, str], ...] = ()
