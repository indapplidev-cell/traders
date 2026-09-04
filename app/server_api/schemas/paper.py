from __future__ import annotations

from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field

from app.server_api.schemas.models import DecimalString, SafeIdentifier, Symbol, UtcTimestamp


T = TypeVar("T")


class PaperEnvelope(BaseModel, Generic[T]):
    api_version: Literal["v1"] = "v1"
    paper_reporting_api_version: Literal[1] = 1
    generated_at: UtcTimestamp
    data: T


class PaperBudgetMetricSemantics(BaseModel):
    unit: str
    source: str
    window: str
    reset_boundary: str
    updated_at: UtcTimestamp


class PaperReadiness(BaseModel):
    environment: str
    mode: Literal["PAPER"] = "PAPER"
    paper_schema_expected: Literal[
        "0024_continuous_paper_authority"
    ] = "0024_continuous_paper_authority"
    paper_schema_ready: bool
    status: str
    paper_runtime_enabled: bool
    paper_daemon_enabled: bool
    paper_scheduler_enabled: bool
    paper_control_state: str
    paper_control_effective_state: str
    paper_control_generation: int | None = Field(ge=0)
    paper_control_health: str
    paper_canary_id: str | None = None
    paper_canary_status: str | None = None
    live_allowed: Literal[False] = False
    account_baseline_persistence_ready: bool
    account_baseline_exists: bool | None
    account_baseline_valid: bool | None
    accounting_reconciliation_status: str
    paper_reconciliation_status: str
    market_data_adapter_ready: bool | None
    approval_source_adapter_ready: bool | None
    wal_ready: bool | None
    pitr_ready: bool | None
    pitr_lineage_valid: bool | None = None
    pitr_lineage_start: UtcTimestamp | None = None
    pitr_lineage_end: UtcTimestamp | None = None
    pitr_contiguous_duration_seconds: int | None = Field(default=None, ge=0)
    pitr_physical_gap: bool | None = None
    canary_command_limit: int | None = Field(default=None, ge=0)
    canary_command_count: int | None = Field(default=None, ge=0)
    canary_command_remaining: int | None = Field(default=None, ge=0)
    canary_command_budget_exhausted: bool | None = None
    canary_open_position_limit: int | None = Field(default=None, ge=0)
    canary_open_position_count: int | None = Field(default=None, ge=0)
    canary_open_position_remaining: int | None = Field(default=None, ge=0)
    canary_open_position_budget_exhausted: bool | None = None
    canary_closed_trade_count: int | None = Field(default=None, ge=0)
    current_approval_availability: str
    current_mutation_ready: bool = False
    current_mutation_denial_reasons: list[str]
    authority_mode: str = "FIRST_CANARY_HISTORICAL"
    control_mode_version: int | None = Field(default=None, ge=1)
    budget_day: str | None = None
    daily_command_budget: int | None = Field(default=None, ge=1)
    commands_used_today: int | None = Field(default=None, ge=0)
    daily_realized_loss_budget: DecimalString | None = None
    realized_pnl_today: DecimalString | None = None
    realized_loss_today: DecimalString | None = None
    daily_risk_budget_bps: DecimalString | None = None
    risk_used_today_bps: DecimalString | None = None
    max_consecutive_losses: int | None = Field(default=None, ge=1)
    loss_streak: int | None = Field(default=None, ge=0)
    risk_pause_reason: str | None = None
    budget_semantics: dict[str, PaperBudgetMetricSemantics] = Field(default_factory=dict)


class PaperAccount(BaseModel):
    account_id: SafeIdentifier
    accounting_session_id: SafeIdentifier
    currency: str
    baseline_id: SafeIdentifier
    initial_balance: DecimalString
    initialized_at: UtcTimestamp
    baseline_semantic_version: str
    current_balance: DecimalString
    realized_gross_pnl: DecimalString
    total_fees: DecimalString
    realized_net_pnl: DecimalString
    return_percent: DecimalString
    closed_trade_count: int = Field(ge=0)
    winning_trade_count: int = Field(ge=0)
    losing_trade_count: int = Field(ge=0)
    breakeven_trade_count: int = Field(ge=0)
    win_rate_percent: DecimalString
    gross_profit: DecimalString
    gross_loss: DecimalString
    profit_factor: DecimalString | None
    average_net_pnl: DecimalString | None
    average_win: DecimalString | None
    average_loss: DecimalString | None
    largest_win: DecimalString | None
    largest_loss: DecimalString | None
    accounting_reconciliation_status: str
    unrealized_pnl: DecimalString | None = None
    global_open_position_count: int | None = Field(default=None, ge=0)
    scalping_v2_performance: dict[str, Any] = Field(default_factory=dict)


class PaperPositionItem(BaseModel):
    position_id: SafeIdentifier
    command_id: SafeIdentifier | None = None
    symbol: Symbol
    side: str
    state: str
    quantity: DecimalString
    entry_price: DecimalString
    entry_time: UtcTimestamp
    stop_price: DecimalString
    target_price: DecimalString
    exit_reason: str | None
    closed_at: UtcTimestamp | None
    realized_pnl: DecimalString | None


class PaperPositionDetail(PaperPositionItem):
    entry_order_id: SafeIdentifier | None
    entry_fill_id: SafeIdentifier | None
    close_order_id: SafeIdentifier | None
    close_fill_id: SafeIdentifier | None
    exit_cursor_status: str | None
    exit_decision: str | None
    lifecycle_events: list[dict[str, str]]


class PaperTradeItem(BaseModel):
    position_id: SafeIdentifier
    trade_id: SafeIdentifier
    symbol: Symbol
    side: str
    entry_time: UtcTimestamp
    exit_time: UtcTimestamp
    exit_reason: str
    capital_used: DecimalString
    entry_notional: DecimalString
    exit_notional: DecimalString
    total_fees: DecimalString
    net_pnl: DecimalString
    roi_percent: DecimalString
    balance_before: DecimalString
    balance_after: DecimalString


class PaperTradeReport(PaperTradeItem):
    accounting_session_id: SafeIdentifier
    currency: str
    quantity: DecimalString
    entry_price: DecimalString
    exit_price: DecimalString
    entry_fee: DecimalString
    exit_fee: DecimalString
    gross_pnl: DecimalString
    report_semantic_id: SafeIdentifier


class PaperList(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None
    has_more: bool


class PaperReconciliationSection(BaseModel):
    status: str
    findings: list[str]
    rows_scanned: int = Field(ge=0)


class PaperReconciliation(BaseModel):
    overall_status: str
    paper_reconciliation: PaperReconciliationSection
    accounting_reconciliation: PaperReconciliationSection


class PaperExecutionLifecycle(BaseModel):
    source_run_id: SafeIdentifier
    symbol: Symbol
    trade_profile_id: str
    boundary_closed_at_ms: int = Field(ge=0)
    candidate_id: SafeIdentifier
    approval_id: SafeIdentifier
    plan_id: str = Field(min_length=1, max_length=512)
    approval_valid_until_ms: int = Field(ge=0)
    selector_state: str
    selector_rank: int | None = Field(default=None, ge=1)
    selected_at: UtcTimestamp
    scheduler_last_observed_at: UtcTimestamp
    policy_evaluated_at: UtcTimestamp | None = None
    policy_generation: int | None = Field(default=None, ge=1)
    policy_reason_source: Literal["READONLY_PAPER_READINESS_CURRENT_SNAPSHOT"] | None = None
    policy_source_timestamp: UtcTimestamp | None = None
    lifecycle_state: str
    command_status: str
    command_id: SafeIdentifier | None = None
    position_status: str
    position_id: SafeIdentifier | None = None
    terminal_reason: str | None = None
    attempt_count: int = Field(ge=0)


class PaperRuntimeStatus(BaseModel):
    mode: Literal["PAPER"] = "PAPER"
    runtime_enabled: bool
    daemon_enabled: bool
    scheduler_enabled: bool
    dry_run: bool
    mutation_enabled: bool
    live_allowed: Literal[False] = False
    worker_running: bool | None
    operator_runner_running: bool | None
    current_execution: PaperExecutionLifecycle | None = None


class PaperControlStatus(BaseModel):
    state: str
    effective_state: str
    generation: int | None = Field(ge=0)
    health: str
    emergency_stop_available: bool
    audit_health: str
    state_audit_reconciliation: str
    canary_id: str | None = None
    canary_status: str | None = None
    canary_command_limit: int | None = Field(default=None, ge=0)
    canary_command_count: int | None = Field(default=None, ge=0)
    canary_command_remaining: int | None = Field(default=None, ge=0)
    canary_command_budget_exhausted: bool | None = None
    canary_open_position_limit: int | None = Field(default=None, ge=0)
    canary_open_position_count: int | None = Field(default=None, ge=0)
    canary_open_position_remaining: int | None = Field(default=None, ge=0)
    canary_open_position_budget_exhausted: bool | None = None
    canary_closed_trade_count: int | None = Field(default=None, ge=0)
    authority_mode: str = "FIRST_CANARY_HISTORICAL"
    control_mode_version: int | None = Field(default=None, ge=1)
    budget_day: str | None = None
    daily_command_budget: int | None = Field(default=None, ge=1)
    commands_used_today: int | None = Field(default=None, ge=0)
    daily_realized_loss_budget: DecimalString | None = None
    realized_pnl_today: DecimalString | None = None
    realized_loss_today: DecimalString | None = None
    daily_risk_budget_bps: DecimalString | None = None
    risk_used_today_bps: DecimalString | None = None
    max_consecutive_losses: int | None = Field(default=None, ge=1)
    loss_streak: int | None = Field(default=None, ge=0)
    risk_pause_reason: str | None = None
    budget_semantics: dict[str, PaperBudgetMetricSemantics] = Field(default_factory=dict)


class PaperOrderItem(BaseModel):
    order_id: SafeIdentifier
    command_id: SafeIdentifier
    symbol: Symbol
    side: str
    role: str
    order_type: str
    state: str
    quantity: DecimalString
    filled_quantity: DecimalString
    average_fill_price: DecimalString | None
    reason_code: str
    created_at: UtcTimestamp
    updated_at: UtcTimestamp


class PaperFillItem(BaseModel):
    fill_id: SafeIdentifier
    order_id: SafeIdentifier
    symbol: Symbol
    side: str
    role: str
    quantity: DecimalString
    price: DecimalString
    fee: DecimalString
    fee_asset: str
    timestamp: UtcTimestamp


class PaperJournalItem(BaseModel):
    event_id: SafeIdentifier
    entity_type: str
    entity_id: SafeIdentifier
    event_type: str
    state_version: int = Field(ge=0)
    reason_code: str
    causation_id: SafeIdentifier
    correlation_id: SafeIdentifier
    timestamp: UtcTimestamp


class TradingCriterion(BaseModel):
    key: str = Field(min_length=1, max_length=96)
    category: str = Field(min_length=1, max_length=96)
    classification: Literal[
        "FIXED_THRESHOLD", "DYNAMIC_RULE", "DERIVED_VALUE", "BOOLEAN_GATE",
        "ENUM_ALLOWLIST", "NOT_CONFIGURED_AS_FIXED_THRESHOLD", "NOT_APPLICABLE",
    ]
    value: Any = None
    unit: str | None = Field(default=None, max_length=48)
    source_component: str = Field(min_length=1, max_length=200)


class TradingCriteriaProvenance(BaseModel):
    projection: Literal["EFFECTIVE_CURRENT_SERVER_POLICY"]
    policy_versions: dict[str, str]


class TradingCriteriaSnapshot(BaseModel):
    title_key: Literal["current_server_trading_criteria"]
    environment: Literal["PRODUCTION"]
    mode: Literal["PAPER"]
    versioned_trading_policy_present: bool
    canary_bound_policy_snapshot_available: bool
    groups: dict[str, list[TradingCriterion]]
    provenance: TradingCriteriaProvenance
