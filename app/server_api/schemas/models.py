from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


UtcTimestamp = Annotated[str, StringConstraints(pattern=r"Z$")]
DecimalString = Annotated[str, StringConstraints(pattern=r"^-?(0|[1-9][0-9]*)(\.[0-9]+)?$")]
Symbol = Annotated[str, StringConstraints(pattern=r"^[A-Z0-9]{5,20}$")]
SafeIdentifier = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,127}$")]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class HealthState(StrEnum):
    UNKNOWN = "UNKNOWN"
    OK = "OK"
    STALE = "STALE"
    DEGRADED = "DEGRADED"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    ERROR = "ERROR"
    OFFLINE = "OFFLINE"


class Direction(StrEnum):
    UNKNOWN = "UNKNOWN"
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    NONE = "NONE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class AnalysisStatus(StrEnum):
    UNKNOWN = "UNKNOWN"
    ANALYZED = "ANALYZED"
    SKIPPED_NOT_ENOUGH_DATA = "SKIPPED_NOT_ENOUGH_DATA"
    SKIPPED_DEGRADED_MARKET_DATA = "SKIPPED_DEGRADED_MARKET_DATA"
    SKIPPED_DUPLICATE_WINDOW = "SKIPPED_DUPLICATE_WINDOW"
    SKIPPED_INVALID_SNAPSHOT = "SKIPPED_INVALID_SNAPSHOT"
    ERROR = "ERROR"


class SetupStatus(StrEnum):
    UNKNOWN = "UNKNOWN"
    SETUP_CANDIDATE = "SETUP_CANDIDATE"
    NO_SETUP = "NO_SETUP"
    WAIT_FOR_CONFIRMATION = "WAIT_FOR_CONFIRMATION"
    SETUP_INVALID = "SETUP_INVALID"
    ERROR = "ERROR"


class IncidentStatus(StrEnum):
    UNKNOWN = "UNKNOWN"
    OPEN = "OPEN"
    UPDATED = "UPDATED"
    RESOLVED = "RESOLVED"


class Severity(StrEnum):
    UNKNOWN = "UNKNOWN"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class PipelineStatus(StrEnum):
    UNKNOWN = "UNKNOWN"
    PENDING = "PENDING"
    WAITING_FOR_REQUIRED_BOUNDARY = "WAITING_FOR_REQUIRED_BOUNDARY"
    READY_TO_RUN = "READY_TO_RUN"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
    MODULE_ERROR = "MODULE_ERROR"
    ERROR = "ERROR"


class ServiceSnapshot(ContractModel):
    name: str
    status: HealthState
    observed_at: UtcTimestamp
    message: str | None = None


class HealthSnapshot(ContractModel):
    status: HealthState
    observed_at: UtcTimestamp
    services: list[ServiceSnapshot]
    timing_state: str
    reason_code: str
    operational: bool
    ready: bool
    acceptance_blocking: bool


class MarketSummary(ContractModel):
    symbol: Symbol
    status: HealthState
    latest_price: DecimalString | None
    closed_until: UtcTimestamp | None
    closed_until_ms: int | None = Field(ge=0)
    regime: str | None
    setup_status: SetupStatus
    risk_status: str | None
    strategy_status: str | None = None
    analysis_status: AnalysisStatus | None = None
    analysis_direction: Direction | None = None
    analysis_phase: str | None = None
    updated_at: UtcTimestamp


class MarketDetail(ContractModel):
    summary: MarketSummary
    timeframe: str
    open: DecimalString | None
    high: DecimalString | None
    low: DecimalString | None
    close: DecimalString | None
    volume: DecimalString | None
    has_gaps: bool | None
    enough_data: bool | None
    future_bars_used: Literal[False] = False


class AnalysisSnapshot(ContractModel):
    analysis_id: str
    symbol: Symbol
    timeframe: str
    closed_until: UtcTimestamp
    closed_until_ms: int = Field(ge=0)
    status: AnalysisStatus
    market_data_status: HealthState
    regime: str | None
    direction: Direction
    confidence: float | None = Field(ge=0, le=1)
    impulse_phase: str | None
    entry_quality: str | None
    reason_codes: list[str]
    updated_at: UtcTimestamp


class SetupSummary(ContractModel):
    setup_id: str
    symbol: Symbol
    timeframe: str
    closed_until: UtcTimestamp
    closed_until_ms: int = Field(ge=0)
    status: SetupStatus
    setup_type: str
    direction: Direction
    quality: str
    quality_score: float | None = Field(ge=0, le=1)
    updated_at: UtcTimestamp


class SetupDetail(ContractModel):
    summary: SetupSummary
    confirmation_state: str
    reason_codes: list[str]
    warnings: list[str]
    invalidation_reasons: list[str]
    strategy_status: str | None
    risk_status: str | None
    paper_status: str | None
    hypothetical_entry: DecimalString | None
    hypothetical_stop: DecimalString | None
    hypothetical_target: DecimalString | None
    planned_rr: DecimalString | None
    executable: Literal[False] = False


class IncidentSummary(ContractModel):
    incident_id: str
    status: IncidentStatus
    severity: Severity
    source: str
    title: str
    symbol: Symbol | None
    opened_at: UtcTimestamp
    updated_at: UtcTimestamp
    resolved_at: UtcTimestamp | None


class IncidentDetail(ContractModel):
    summary: IncidentSummary
    safe_description: str
    reason_code: str | None
    timeframe: str | None
    closed_until: UtcTimestamp | None
    closed_until_ms: int | None = Field(ge=0)


class PipelineRunSummary(ContractModel):
    run_id: str
    symbol: Symbol
    primary_timeframe: str
    closed_until: UtcTimestamp
    closed_until_ms: int = Field(ge=0)
    status: PipelineStatus
    attempt_count: int = Field(ge=0)
    result_count: int = Field(ge=0)


class DashboardSnapshot(ContractModel):
    status: HealthState
    observed_at: UtcTimestamp
    markets: list[MarketSummary]
    recent_runs: list[PipelineRunSummary]
    active_incident_count: int = Field(ge=0)


class TradingUniverseSymbolStatus(ContractModel):
    symbol: Symbol
    universe_version: str
    market_data_ready: bool
    ready_streams: int = Field(ge=0, le=6)
    total_streams: Literal[6] = 6
    history_ready: bool
    analysis_ready: bool
    setup_ready: bool
    strategy_compatible: bool
    risk_compatible: bool
    trading_activation_state: Literal["ACTIVE", "PREPARED_NOT_ACTIVE"]


class TradingUniverseSnapshot(ContractModel):
    active_universe_version: str
    prepared_universe_version: str
    active_symbols: list[Symbol]
    prepared_symbols: list[Symbol]
    active_symbol_count: int = Field(ge=0, le=10)
    target_symbol_count: Literal[10] = 10
    ready_market_data_streams: int = Field(ge=0, le=60)
    target_market_data_streams: Literal[60] = 60
    symbols: list[TradingUniverseSymbolStatus]


class PageInfo(ContractModel):
    limit: int = Field(ge=1, le=100)
    next_cursor: str | None


class SetupPage(BaseModel):
    items: list[SetupSummary]
    page: PageInfo


class IncidentPage(BaseModel):
    items: list[IncidentSummary]
    page: PageInfo


class MarketList(BaseModel):
    items: list[MarketSummary]


class Error(ContractModel):
    code: str
    message: str
    details: dict[str, Any]


class ErrorEnvelope(ContractModel):
    api_version: Literal["v1"] = "v1"
    error: Error
    request_id: str | None = None


class HealthEnvelopeObject(BaseModel):
    api_version: Literal["v1"] = "v1"
    generated_at: UtcTimestamp
    data: HealthSnapshot


HealthEnvelope = HealthEnvelopeObject


class DashboardEnvelope(BaseModel):
    api_version: Literal["v1"] = "v1"
    generated_at: UtcTimestamp
    data: DashboardSnapshot


class TradingUniverseEnvelope(BaseModel):
    api_version: Literal["v1"] = "v1"
    generated_at: UtcTimestamp
    data: TradingUniverseSnapshot


class FunnelCandidateStatus(ContractModel):
    symbol: Symbol
    source_run_id: str
    candidate_id: str | None
    direction: str | None
    current_stage: str
    stage_status: str
    source_reason_code: str | None
    source_reason_detail_safe: str | None
    ui_reason_category: str
    final_approval_id: str | None
    eligible: bool
    execution_eligible: bool = False
    selector_rank: int | None = Field(default=None, ge=1)
    selected_winner: bool
    updated_at_ms: int = Field(ge=0)
    stage_trace: dict[str, str]
    downstream_stage_trace: dict[str, str] = Field(default_factory=dict)
    downstream_current_stage: str | None = None
    terminal_reason_code: str | None = None
    downstream_detail: dict[str, Any] = Field(default_factory=dict)
    risk_score: Any | None = None
    strategy_score: Any | None = None
    planned_risk_reward: Any | None = None


class FunnelEligibleCompetitor(ContractModel):
    rank: int = Field(ge=1)
    symbol: Symbol
    candidate_id: str
    final_approval_id: str


class FunnelCycle(ContractModel):
    boundary_close_ms: int = Field(ge=0)
    boundary_start_ms: int = Field(ge=0)
    symbols_expected: int = Field(ge=1, le=10)
    symbols_seen: int = Field(ge=0, le=10)
    symbols_processed: int = Field(ge=0, le=10)
    cycle_complete: bool
    stage_counts: dict[str, int]
    downstream_stage_counts: dict[str, int | None] = Field(default_factory=dict)
    stage_rejected_count: dict[str, int] = Field(default_factory=dict)
    dominant_rejection_reason: dict[str, str | None] = Field(default_factory=dict)
    items: list[FunnelCandidateStatus]
    eligible_competitors: list[FunnelEligibleCompetitor]
    winner_symbol: Symbol | None
    winner_candidate_id: str | None
    latest_pipeline_update_ms: int = Field(ge=0)


class FunnelRollingSummary(ContractModel):
    window_ms: int = Field(gt=0)
    boundary_count: int = Field(ge=0)
    completed_cycle_count: int = Field(ge=0)
    stage_counts: dict[str, int]
    downstream_stage_counts: dict[str, int | None] = Field(default_factory=dict)
    stage_rejected_count: dict[str, int] = Field(default_factory=dict)
    dominant_rejection_reason: dict[str, str | None] = Field(default_factory=dict)


class TradingFunnelSnapshot(ContractModel):
    projection_version: Literal["trading-funnel-v1"]
    trade_profile_id: Literal["trade-15m-v1", "trade-5m-v1"] = "trade-15m-v1"
    trade_mode: Literal["TRADE_15M", "SCALPING"] = "TRADE_15M"
    display_i18n_key: str = "trading.profile.trade_15m.title"
    primary_timeframe: Literal["15m", "5m"] = "15m"
    entry_timeframes: list[str] = Field(default_factory=lambda: ["15m"])
    context_timeframes: list[str] = Field(default_factory=lambda: ["1h", "4h"])
    trigger_timeframe: Literal["15m", "5m"] = "15m"
    profile_mode: Literal["PRODUCTION_SEARCH", "SHADOW_SEARCH"] = "PRODUCTION_SEARCH"
    decision_timeframe: Literal["15m", "5m"]
    universe_id: str
    selection_policy_version: Literal["eligible-approval-ranking-v1"]
    count_unit: dict[str, Literal["SYMBOL"]]
    downstream_stage_order: list[str] = Field(default_factory=list)
    downstream_count_unit: dict[str, Literal["SYMBOL"]] = Field(default_factory=dict)
    current_cycle: FunnelCycle | None
    last_completed_cycle: FunnelCycle | None
    detail_candidates: list[FunnelCandidateStatus] = Field(default_factory=list)
    rolling_1h: FunnelRollingSummary
    rolling_4h: FunnelRollingSummary
    projection_generated_at_ms: int = Field(ge=0)
    latest_pipeline_update_ms: int | None = Field(default=None, ge=0)
    age_ms: int | None = Field(default=None, ge=0)
    freshness_state: Literal["CURRENT", "STALE", "NOT_AVAILABLE"]
    query_time_horizon_ms: int = Field(gt=0)
    expected_1h_cycle_count: Literal[4, 12] = 4
    expected_4h_cycle_count: Literal[16, 48] = 16
    paper_command_creation_enabled: bool = True
    position_opening_enabled: bool = True
    profile_metrics: dict[str, Any] = Field(default_factory=dict)
    profile_health: dict[str, Any] = Field(default_factory=dict)


class TradingFunnelEnvelope(BaseModel):
    api_version: Literal["v1"] = "v1"
    generated_at: UtcTimestamp
    data: TradingFunnelSnapshot


class MarketListEnvelope(BaseModel):
    api_version: Literal["v1"] = "v1"
    generated_at: UtcTimestamp
    data: MarketList


class MarketDetailEnvelope(BaseModel):
    api_version: Literal["v1"] = "v1"
    generated_at: UtcTimestamp
    data: MarketDetail


class AnalysisEnvelope(BaseModel):
    api_version: Literal["v1"] = "v1"
    generated_at: UtcTimestamp
    data: AnalysisSnapshot


class AnalysisList(BaseModel):
    items: list[AnalysisSnapshot]
    active_symbol_count: int = Field(ge=0, le=10)
    active_symbols: list[Symbol]


class AnalysisListEnvelope(BaseModel):
    api_version: Literal["v1"] = "v1"
    generated_at: UtcTimestamp
    data: AnalysisList


class SetupPageEnvelope(BaseModel):
    api_version: Literal["v1"] = "v1"
    generated_at: UtcTimestamp
    data: SetupPage


class SetupDetailEnvelope(BaseModel):
    api_version: Literal["v1"] = "v1"
    generated_at: UtcTimestamp
    data: SetupDetail


class IncidentPageEnvelope(BaseModel):
    api_version: Literal["v1"] = "v1"
    generated_at: UtcTimestamp
    data: IncidentPage


class IncidentDetailEnvelope(BaseModel):
    api_version: Literal["v1"] = "v1"
    generated_at: UtcTimestamp
    data: IncidentDetail
