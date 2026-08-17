"""SQLAlchemy persistence records for the immutable PAPER domain foundation."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    LargeBinary,
    Numeric,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.engine_safety.paper_domain import (
    ExecutionMode,
    PaperEventType,
    PaperExitCause,
    PaperInputHealthStatus,
    PaperOrderState,
    PaperOrderType,
    PaperPositionState,
    PaperReasonCode,
    PaperSide,
)


IDENTITY_LENGTH = 128
SYMBOL_LENGTH = 32
REASON_CODE_LENGTH = 80
PRICE_PRECISION = 38
PRICE_SCALE = 18
QUANTITY_PRECISION = 38
QUANTITY_SCALE = 18
MONEY_PRECISION = 38
MONEY_SCALE = 18
RATIO_PRECISION = 20
RATIO_SCALE = 10

LOGICAL_FOREIGN_KEY_ONLY = frozenset(
    {
        "paper_execution_commands.strategy_decision_id",
        "paper_execution_commands.risk_decision_id",
        "paper_execution_commands.setup_id",
        "paper_execution_commands.pipeline_run_id",
        "paper_execution_commands.analysis_result_id",
        "paper_execution_commands.simulation_policy_id",
        "paper_execution_commands.fee_policy_id",
        "paper_execution_commands.slippage_policy_id",
        "paper_execution_commands.latency_policy_id",
        "paper_orders.applied_fill_id",
        "paper_fills.simulation_policy_id",
        "paper_fills.slippage_policy_id",
        "paper_fills.fee_policy_id",
        "paper_fills.latency_policy_id",
        "paper_positions.exit_fill_id",
    }
)

POLICY_STATUSES = ("ACTIVE", "RETIRED")
POLICY_PRICE_SOURCES = ("NEXT_ELIGIBLE_CLOSED_1M_OPEN",)
POLICY_TIMEFRAMES = ("1m",)
INTRABAR_CONFLICT_POLICIES = ("STOP_FIRST_CONSERVATIVE",)
ORDER_ROLES = ("ENTRY", "EXIT")
FILL_ROLES = ("ENTRY", "EXIT")
PROCESSING_STATUSES = ("PENDING", "PROCESSING", "COMPLETED", "FAILED")
FIRST_CANARY_STATES = (
    "RESERVED",
    "ARMED",
    "ARMED_WAITING",
    "NO_ELIGIBLE_APPROVAL",
    "RUNNING",
    "POSITION_OPEN",
    "POSITION_CLOSING",
    "POSITION_CLOSED",
    "RECONCILIATION_PENDING",
    "COMPLETED",
    "STOPPED",
    "FAILED_SAFE",
)
AGGREGATE_TYPES = (
    "paper_command",
    "paper_order",
    "paper_fill",
    "paper_position",
    "paper_exit",
)


def _values(values: tuple[str, ...]) -> str:
    return ",".join(f"'{value}'" for value in values)


def _finite(column: str) -> str:
    return (
        f"{column} NOT IN (CAST('NaN' AS NUMERIC), "
        "CAST('Infinity' AS NUMERIC), CAST('-Infinity' AS NUMERIC))"
    )


class PaperAccountBaselineRecord(Base):
    __tablename__ = "paper_account_baselines"
    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "accounting_session_id",
            name="uq_paper_account_baselines_account_session",
        ),
        CheckConstraint(
            "length(trim(baseline_id)) BETWEEN 1 AND 128 AND "
            "length(trim(account_id)) BETWEEN 1 AND 128 AND "
            "length(trim(accounting_session_id)) BETWEEN 1 AND 128 AND "
            "length(trim(semantic_version)) BETWEEN 1 AND 128",
            name="ck_paper_account_baseline_identities",
        ),
        CheckConstraint(
            "currency = 'USDT'", name="ck_paper_account_baseline_currency"
        ),
        CheckConstraint(
            f"{_finite('initial_balance')} AND initial_balance > 0",
            name="ck_paper_account_baseline_initial_balance",
        ),
    )

    baseline_id: Mapped[str] = mapped_column(
        String(IDENTITY_LENGTH), primary_key=True
    )
    account_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    accounting_session_id: Mapped[str] = mapped_column(
        String(IDENTITY_LENGTH), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    initial_balance: Mapped[Decimal] = mapped_column(
        Numeric(MONEY_PRECISION, MONEY_SCALE), nullable=False
    )
    initialized_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    semantic_version: Mapped[str] = mapped_column(
        String(IDENTITY_LENGTH), nullable=False
    )


class PaperFirstCanarySessionRecord(Base):
    """One durable, bounded first-canary causal identity."""

    __tablename__ = "paper_first_canary_sessions"
    __table_args__ = (
        UniqueConstraint("arm_request_id", name="uq_paper_first_canary_arm_request"),
        UniqueConstraint("arming_transition_id", name="uq_paper_first_canary_arm_transition"),
        UniqueConstraint("start_request_id", name="uq_paper_first_canary_start_request"),
        UniqueConstraint("command_id", name="uq_paper_first_canary_command"),
        UniqueConstraint("position_id", name="uq_paper_first_canary_position"),
        CheckConstraint("environment = 'PRODUCTION'", name="ck_paper_first_canary_environment"),
        CheckConstraint("mode = 'PAPER'", name="ck_paper_first_canary_mode"),
        CheckConstraint(
            f"state IN ({_values(FIRST_CANARY_STATES)})",
            name="ck_paper_first_canary_state",
        ),
        CheckConstraint("max_new_commands = 1", name="ck_paper_first_canary_command_budget"),
        CheckConstraint("max_open_positions = 1", name="ck_paper_first_canary_position_budget"),
        CheckConstraint("command_count BETWEEN 0 AND 1", name="ck_paper_first_canary_command_count"),
        CheckConstraint("position_count BETWEEN 0 AND 1", name="ck_paper_first_canary_position_count"),
        CheckConstraint(
            "selection_policy_version IN ('exactly-one-eligible-v1','eligible-approval-ranking-v1')",
            name="ck_paper_first_canary_selection_policy",
        ),
        CheckConstraint(
            "universe_version_id IN ('trading-universe-v1','trading-universe-v2')",
            name="ck_paper_first_canary_universe_version",
        ),
        CheckConstraint(
            "(command_count = 0 AND command_id IS NULL) OR (command_count = 1 AND command_id IS NOT NULL)",
            name="ck_paper_first_canary_command_link",
        ),
        CheckConstraint(
            "(position_count = 0 AND position_id IS NULL) OR (position_count = 1 AND position_id IS NOT NULL)",
            name="ck_paper_first_canary_position_link",
        ),
        CheckConstraint("version >= 0", name="ck_paper_first_canary_version"),
        Index(
            "uq_paper_first_canary_one_active_environment",
            "environment",
            unique=True,
            postgresql_where=text(
                "state NOT IN ('COMPLETED','STOPPED','FAILED_SAFE')"
            ),
        ),
    )

    canary_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    environment: Mapped[str] = mapped_column(String(32), nullable=False)
    mode: Mapped[str] = mapped_column(String(8), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    armed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    arm_request_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    arm_request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    arming_transition_id: Mapped[str | None] = mapped_column(String(IDENTITY_LENGTH))
    arming_generation: Mapped[int | None] = mapped_column(Integer)
    start_request_id: Mapped[str | None] = mapped_column(String(IDENTITY_LENGTH))
    start_request_fingerprint: Mapped[str | None] = mapped_column(String(64))
    current_control_generation: Mapped[int] = mapped_column(Integer, nullable=False)
    max_new_commands: Mapped[int] = mapped_column(Integer, nullable=False)
    max_open_positions: Mapped[int] = mapped_column(Integer, nullable=False)
    allowed_symbols: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    universe_version_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="trading-universe-v1"
    )
    selection_policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    approval_id: Mapped[str | None] = mapped_column(String(IDENTITY_LENGTH))
    command_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    command_id: Mapped[str | None] = mapped_column(
        String(IDENTITY_LENGTH), ForeignKey("paper_execution_commands.command_id", ondelete="RESTRICT")
    )
    position_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    position_id: Mapped[str | None] = mapped_column(
        String(IDENTITY_LENGTH), ForeignKey("paper_positions.position_id", ondelete="RESTRICT")
    )
    trade_report_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    paper_reconciliation_status: Mapped[str] = mapped_column(String(32), nullable=False)
    accounting_reconciliation_status: Mapped[str] = mapped_column(String(32), nullable=False)
    reconciliation_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    terminal_reason: Mapped[str | None] = mapped_column(String(REASON_CODE_LENGTH))
    finding_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class TradingUniverseRuntimeStateRecord(Base):
    """Singleton production activation state; updates are transactional and audited."""

    __tablename__ = "trading_universe_runtime_state"
    __table_args__ = (
        CheckConstraint("environment = 'PRODUCTION'", name="ck_trading_universe_runtime_environment"),
        CheckConstraint(
            "active_version_id IN ('trading-universe-v1','trading-universe-v2')",
            name="ck_trading_universe_runtime_active_version",
        ),
        CheckConstraint(
            "previous_version_id IS NULL OR previous_version_id IN ('trading-universe-v1','trading-universe-v2')",
            name="ck_trading_universe_runtime_previous_version",
        ),
        CheckConstraint("generation >= 1", name="ck_trading_universe_runtime_generation"),
    )

    environment: Mapped[str] = mapped_column(String(32), primary_key=True)
    active_version_id: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_version_id: Mapped[str | None] = mapped_column(String(64))
    generation: Mapped[int] = mapped_column(Integer, nullable=False)
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    activation_reason: Mapped[str] = mapped_column(String(REASON_CODE_LENGTH), nullable=False)
    runtime_revision: Mapped[str] = mapped_column(String(64), nullable=False)


EXECUTION_MODES = tuple(item.value for item in ExecutionMode)
PAPER_SIDES = tuple(item.value for item in PaperSide)
PAPER_ORDER_TYPES = tuple(item.value for item in PaperOrderType)
PAPER_ORDER_STATES = tuple(item.value for item in PaperOrderState)
PAPER_POSITION_STATES = tuple(item.value for item in PaperPositionState)
PAPER_EXIT_CAUSES = tuple(item.value for item in PaperExitCause)
PAPER_EVENT_TYPES = tuple(item.value for item in PaperEventType)
PAPER_HEALTH_STATUSES = tuple(item.value for item in PaperInputHealthStatus)
PAPER_REASON_CODES = tuple(item.value for item in PaperReasonCode)


class PaperSimulationPolicyRecord(Base):
    __tablename__ = "paper_simulation_policies"
    __table_args__ = (
        PrimaryKeyConstraint("policy_id", "policy_version", name="pk_paper_simulation_policies"),
        CheckConstraint("length(trim(policy_id)) BETWEEN 1 AND 128", name="ck_paper_policy_id"),
        CheckConstraint("policy_version >= 1", name="ck_paper_policy_version"),
        CheckConstraint(f"status IN ({_values(POLICY_STATUSES)})", name="ck_paper_policy_status"),
        CheckConstraint(
            f"price_source IN ({_values(POLICY_PRICE_SOURCES)})",
            name="ck_paper_policy_price_source",
        ),
        CheckConstraint(
            f"timeframe IN ({_values(POLICY_TIMEFRAMES)})",
            name="ck_paper_policy_timeframe",
        ),
        CheckConstraint("latency_candles >= 0", name="ck_paper_policy_latency"),
        CheckConstraint(
            f"{_finite('slippage_bps')} AND slippage_bps >= 0",
            name="ck_paper_policy_slippage",
        ),
        CheckConstraint(
            f"{_finite('fee_bps')} AND fee_bps >= 0",
            name="ck_paper_policy_fee",
        ),
        CheckConstraint("partial_fill_enabled = false", name="ck_paper_policy_no_partial_fill"),
        CheckConstraint("future_data_allowed = false", name="ck_paper_policy_no_future"),
        CheckConstraint(
            f"intrabar_conflict_policy IN ({_values(INTRABAR_CONFLICT_POLICIES)})",
            name="ck_paper_policy_conflict",
        ),
        CheckConstraint(
            "length(trim(configuration_fingerprint)) BETWEEN 1 AND 128",
            name="ck_paper_policy_fingerprint",
        ),
        CheckConstraint(
            "(status = 'ACTIVE' AND retired_at IS NULL) OR "
            "(status = 'RETIRED' AND retired_at IS NOT NULL)",
            name="ck_paper_policy_retirement",
        ),
    )

    policy_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    price_source: Mapped[str] = mapped_column(String(48), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    latency_candles: Mapped[int] = mapped_column(Integer, nullable=False)
    slippage_bps: Mapped[Decimal] = mapped_column(Numeric(RATIO_PRECISION, RATIO_SCALE), nullable=False)
    fee_bps: Mapped[Decimal] = mapped_column(Numeric(RATIO_PRECISION, RATIO_SCALE), nullable=False)
    partial_fill_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    future_data_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    intrabar_conflict_policy: Mapped[str] = mapped_column(String(40), nullable=False)
    configuration_fingerprint: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PaperExecutionCommandRecord(Base):
    __tablename__ = "paper_execution_commands"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_paper_commands_idempotency_key"),
        CheckConstraint("length(trim(idempotency_key)) BETWEEN 1 AND 128", name="ck_paper_command_idem"),
        CheckConstraint("mode = 'PAPER'", name="ck_paper_command_mode"),
        CheckConstraint(f"side IN ({_values(PAPER_SIDES)})", name="ck_paper_command_side"),
        CheckConstraint(
            f"order_type IN ({_values(PAPER_ORDER_TYPES)})",
            name="ck_paper_command_order_type",
        ),
        CheckConstraint("length(trim(symbol)) BETWEEN 2 AND 32", name="ck_paper_command_symbol"),
        CheckConstraint(
            f"{_finite('requested_quantity')} AND requested_quantity > 0",
            name="ck_paper_command_quantity",
        ),
        CheckConstraint(
            f"requested_notional IS NULL OR ({_finite('requested_notional')} AND requested_notional > 0)",
            name="ck_paper_command_notional",
        ),
        CheckConstraint(
            "requested_notional IS NULL OR "
            "requested_notional = requested_quantity * entry_reference_price",
            name="ck_paper_command_notional_consistency",
        ),
        CheckConstraint(
            " AND ".join(
                f"{_finite(name)} AND {name} > 0"
                for name in ("entry_reference_price", "stop_price", "target_price")
            ),
            name="ck_paper_command_prices",
        ),
        CheckConstraint(
            "(side = 'LONG' AND stop_price < entry_reference_price "
            "AND entry_reference_price < target_price) OR "
            "(side = 'SHORT' AND target_price < entry_reference_price "
            "AND entry_reference_price < stop_price)",
            name="ck_paper_command_geometry",
        ),
        CheckConstraint("closed_until_ms >= 0", name="ck_paper_command_closed_until"),
        CheckConstraint(
            "valid_until_ms >= closed_until_ms",
            name="ck_paper_command_valid_until",
        ),
        CheckConstraint("final_paper_approval = true", name="ck_paper_command_approval"),
        CheckConstraint("future_bars_used = false", name="ck_paper_command_no_future"),
        CheckConstraint(
            f"input_health_status IN ({_values(PAPER_HEALTH_STATUSES)})",
            name="ck_paper_command_health",
        ),
        CheckConstraint(
            f"processing_status IN ({_values(PROCESSING_STATUSES)})",
            name="ck_paper_command_processing",
        ),
        CheckConstraint(
            "length(trim(strategy_decision_id)) BETWEEN 1 AND 128 AND "
            "length(trim(risk_decision_id)) BETWEEN 1 AND 128 AND "
            "length(trim(setup_id)) BETWEEN 1 AND 128 AND "
            "length(trim(pipeline_run_id)) BETWEEN 1 AND 128 AND "
            "length(trim(analysis_result_id)) BETWEEN 1 AND 128",
            name="ck_paper_command_causal_ids",
        ),
        CheckConstraint(
            "length(trim(configuration_fingerprint)) BETWEEN 1 AND 128 AND "
            "length(trim(simulation_policy_id)) BETWEEN 1 AND 128 AND "
            "length(trim(fee_policy_id)) BETWEEN 1 AND 128 AND "
            "length(trim(slippage_policy_id)) BETWEEN 1 AND 128 AND "
            "length(trim(latency_policy_id)) BETWEEN 1 AND 128",
            name="ck_paper_command_policy_ids",
        ),
        Index(
            "ix_paper_commands_processing_created",
            "processing_status",
            "created_at",
        ),
        Index("ix_paper_commands_pipeline_run_id", "pipeline_run_id"),
        Index("ix_paper_commands_analysis_result_id", "analysis_result_id"),
    )

    command_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    mode: Mapped[str] = mapped_column(String(8), nullable=False)
    symbol: Mapped[str] = mapped_column(String(SYMBOL_LENGTH), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    order_type: Mapped[str] = mapped_column(String(24), nullable=False)
    requested_quantity: Mapped[Decimal] = mapped_column(
        Numeric(QUANTITY_PRECISION, QUANTITY_SCALE), nullable=False
    )
    requested_notional: Mapped[Decimal | None] = mapped_column(Numeric(MONEY_PRECISION, MONEY_SCALE))
    entry_reference_price: Mapped[Decimal] = mapped_column(
        Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=False
    )
    stop_price: Mapped[Decimal] = mapped_column(Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=False)
    target_price: Mapped[Decimal] = mapped_column(Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=False)
    strategy_decision_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    risk_decision_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    setup_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    pipeline_run_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    analysis_result_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    closed_until_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    configuration_fingerprint: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    simulation_policy_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    fee_policy_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    slippage_policy_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    latency_policy_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    final_paper_approval: Mapped[bool] = mapped_column(Boolean, nullable=False)
    input_health_status: Mapped[str] = mapped_column(String(24), nullable=False)
    future_bars_used: Mapped[bool] = mapped_column(Boolean, nullable=False)
    processing_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="PENDING", server_default=text("'PENDING'")
    )


class PaperOrderRecord(Base):
    __tablename__ = "paper_orders"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_paper_orders_idempotency_key"),
        UniqueConstraint("command_id", "order_role", name="uq_paper_orders_command_role"),
        CheckConstraint("length(trim(idempotency_key)) BETWEEN 1 AND 128", name="ck_paper_order_idem"),
        CheckConstraint(f"order_role IN ({_values(ORDER_ROLES)})", name="ck_paper_order_role"),
        CheckConstraint("mode = 'PAPER'", name="ck_paper_order_mode"),
        CheckConstraint(f"side IN ({_values(PAPER_SIDES)})", name="ck_paper_order_side"),
        CheckConstraint(
            f"order_type IN ({_values(PAPER_ORDER_TYPES)})",
            name="ck_paper_order_order_type",
        ),
        CheckConstraint(
            f"state IN ({_values(PAPER_ORDER_STATES)})",
            name="ck_paper_order_state",
        ),
        CheckConstraint(
            f"{_finite('requested_quantity')} AND requested_quantity > 0 AND "
            f"{_finite('filled_quantity')} AND filled_quantity >= 0 AND "
            "filled_quantity <= requested_quantity",
            name="ck_paper_order_quantities",
        ),
        CheckConstraint(
            f"{_finite('total_fees')} AND total_fees >= 0",
            name="ck_paper_order_fees",
        ),
        CheckConstraint(
            f"average_fill_price IS NULL OR ({_finite('average_fill_price')} "
            "AND average_fill_price > 0)",
            name="ck_paper_order_average_price",
        ),
        CheckConstraint(
            "(state = 'FILLED' AND filled_quantity = requested_quantity "
            "AND average_fill_price IS NOT NULL AND average_fill_price > 0 "
            "AND applied_fill_id IS NOT NULL) OR "
            "(state <> 'FILLED' AND filled_quantity = 0 "
            "AND average_fill_price IS NULL AND total_fees = 0 "
            "AND applied_fill_id IS NULL)",
            name="ck_paper_order_state_accounting",
        ),
        CheckConstraint("updated_at >= created_at", name="ck_paper_order_timestamps"),
        CheckConstraint("version >= 0", name="ck_paper_order_version"),
        CheckConstraint(
            f"reason_code IN ({_values(PAPER_REASON_CODES)})",
            name="ck_paper_order_reason",
        ),
        Index("ix_paper_orders_state_created_at", "state", "created_at"),
    )

    order_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), primary_key=True)
    command_id: Mapped[str] = mapped_column(
        String(IDENTITY_LENGTH),
        ForeignKey("paper_execution_commands.command_id", ondelete="RESTRICT"),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    order_role: Mapped[str] = mapped_column(String(8), nullable=False)
    mode: Mapped[str] = mapped_column(String(8), nullable=False)
    symbol: Mapped[str] = mapped_column(String(SYMBOL_LENGTH), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    order_type: Mapped[str] = mapped_column(String(24), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    requested_quantity: Mapped[Decimal] = mapped_column(
        Numeric(QUANTITY_PRECISION, QUANTITY_SCALE), nullable=False
    )
    filled_quantity: Mapped[Decimal] = mapped_column(
        Numeric(QUANTITY_PRECISION, QUANTITY_SCALE), nullable=False
    )
    average_fill_price: Mapped[Decimal | None] = mapped_column(Numeric(PRICE_PRECISION, PRICE_SCALE))
    total_fees: Mapped[Decimal] = mapped_column(Numeric(MONEY_PRECISION, MONEY_SCALE), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    reason_code: Mapped[str] = mapped_column(String(REASON_CODE_LENGTH), nullable=False)
    applied_fill_id: Mapped[str | None] = mapped_column(String(IDENTITY_LENGTH))


class PaperOrderEventRecord(Base):
    __tablename__ = "paper_order_events"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_paper_order_events_idem"),
        UniqueConstraint(
            "order_id",
            "aggregate_version",
            name="uq_paper_order_events_order_version",
        ),
        CheckConstraint(
            f"event_type IN ({_values(PAPER_EVENT_TYPES)})",
            name="ck_paper_order_event_type",
        ),
        CheckConstraint(
            f"from_state IS NULL OR from_state IN ({_values(PAPER_ORDER_STATES)})",
            name="ck_paper_order_event_from_state",
        ),
        CheckConstraint(
            f"to_state IN ({_values(PAPER_ORDER_STATES)})",
            name="ck_paper_order_event_to_state",
        ),
        CheckConstraint("aggregate_version >= 0", name="ck_paper_order_event_version"),
        CheckConstraint(
            "length(trim(idempotency_key)) BETWEEN 1 AND 128 AND "
            "length(trim(correlation_id)) BETWEEN 1 AND 128 AND "
            "length(trim(causation_id)) BETWEEN 1 AND 128",
            name="ck_paper_order_event_causal_ids",
        ),
        CheckConstraint(
            f"reason_code IN ({_values(PAPER_REASON_CODES)})",
            name="ck_paper_order_event_reason",
        ),
    )

    order_event_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), primary_key=True)
    order_id: Mapped[str] = mapped_column(
        String(IDENTITY_LENGTH),
        ForeignKey("paper_orders.order_id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    from_state: Mapped[str | None] = mapped_column(String(16))
    to_state: Mapped[str] = mapped_column(String(16), nullable=False)
    aggregate_version: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    causation_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(REASON_CODE_LENGTH), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PaperFillRecord(Base):
    __tablename__ = "paper_fills"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_paper_fills_idempotency_key"),
        UniqueConstraint("order_id", "fill_role", name="uq_paper_fills_order_role"),
        CheckConstraint("length(trim(idempotency_key)) BETWEEN 1 AND 128", name="ck_paper_fill_idem"),
        CheckConstraint(f"fill_role IN ({_values(FILL_ROLES)})", name="ck_paper_fill_role"),
        CheckConstraint(f"side IN ({_values(PAPER_SIDES)})", name="ck_paper_fill_side"),
        CheckConstraint(
            f"{_finite('quantity')} AND quantity > 0",
            name="ck_paper_fill_quantity",
        ),
        CheckConstraint(
            f"{_finite('price')} AND price > 0",
            name="ck_paper_fill_price",
        ),
        CheckConstraint(
            f"{_finite('fee_amount')} AND fee_amount >= 0",
            name="ck_paper_fill_fee",
        ),
        CheckConstraint("length(trim(fee_asset)) BETWEEN 2 AND 32", name="ck_paper_fill_asset"),
        CheckConstraint("source_closed_until_ms >= 0", name="ck_paper_fill_boundary"),
        CheckConstraint("future_bars_used = false", name="ck_paper_fill_no_future"),
        CheckConstraint(
            "length(trim(simulation_policy_id)) BETWEEN 1 AND 128 AND "
            "length(trim(slippage_policy_id)) BETWEEN 1 AND 128 AND "
            "length(trim(fee_policy_id)) BETWEEN 1 AND 128 AND "
            "length(trim(latency_policy_id)) BETWEEN 1 AND 128",
            name="ck_paper_fill_policy_ids",
        ),
    )

    fill_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), primary_key=True)
    order_id: Mapped[str] = mapped_column(
        String(IDENTITY_LENGTH),
        ForeignKey("paper_orders.order_id", ondelete="RESTRICT"),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    fill_role: Mapped[str] = mapped_column(String(8), nullable=False)
    symbol: Mapped[str] = mapped_column(String(SYMBOL_LENGTH), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(QUANTITY_PRECISION, QUANTITY_SCALE), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=False)
    fee_amount: Mapped[Decimal] = mapped_column(Numeric(MONEY_PRECISION, MONEY_SCALE), nullable=False)
    fee_asset: Mapped[str] = mapped_column(String(SYMBOL_LENGTH), nullable=False)
    filled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_closed_until_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    simulation_policy_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    slippage_policy_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    fee_policy_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    latency_policy_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    future_bars_used: Mapped[bool] = mapped_column(Boolean, nullable=False)


class PaperPositionRecord(Base):
    __tablename__ = "paper_positions"
    __table_args__ = (
        CheckConstraint("mode = 'PAPER'", name="ck_paper_position_mode"),
        CheckConstraint(f"side IN ({_values(PAPER_SIDES)})", name="ck_paper_position_side"),
        CheckConstraint(
            f"state IN ({_values(PAPER_POSITION_STATES)})",
            name="ck_paper_position_state",
        ),
        CheckConstraint(
            f"{_finite('entry_quantity')} AND entry_quantity > 0 AND "
            f"{_finite('remaining_quantity')} AND remaining_quantity >= 0 "
            "AND remaining_quantity <= entry_quantity",
            name="ck_paper_position_quantities",
        ),
        CheckConstraint(
            f"{_finite('average_entry_price')} AND average_entry_price > 0 AND "
            f"(average_exit_price IS NULL OR ({_finite('average_exit_price')} "
            "AND average_exit_price > 0))",
            name="ck_paper_position_average_prices",
        ),
        CheckConstraint(
            f"{_finite('entry_fees')} AND entry_fees >= 0 AND "
            f"{_finite('exit_fees')} AND exit_fees >= 0",
            name="ck_paper_position_fees",
        ),
        CheckConstraint(
            f"{_finite('realized_pnl')} AND {_finite('unrealized_pnl')}",
            name="ck_paper_position_pnl",
        ),
        CheckConstraint(
            f"{_finite('stop_price')} AND stop_price > 0 AND "
            f"{_finite('target_price')} AND target_price > 0 AND "
            f"{_finite('last_mark_price')} AND last_mark_price > 0",
            name="ck_paper_position_prices",
        ),
        CheckConstraint(
            "(side = 'LONG' AND stop_price < average_entry_price "
            "AND average_entry_price < target_price) OR "
            "(side = 'SHORT' AND target_price < average_entry_price "
            "AND average_entry_price < stop_price)",
            name="ck_paper_position_geometry",
        ),
        CheckConstraint("last_mark_closed_until_ms >= 0", name="ck_paper_position_boundary"),
        CheckConstraint("version >= 0", name="ck_paper_position_version"),
        CheckConstraint(
            "(state = 'OPEN' AND remaining_quantity > 0 AND closed_at IS NULL "
            "AND average_exit_price IS NULL AND exit_fill_id IS NULL) OR "
            "(state = 'CLOSING' AND remaining_quantity > 0 AND closed_at IS NULL "
            "AND average_exit_price IS NULL AND exit_fill_id IS NULL) OR "
            "(state = 'CLOSED' AND remaining_quantity = 0 AND closed_at IS NOT NULL "
            "AND closed_at >= opened_at AND average_exit_price IS NOT NULL "
            "AND average_exit_price > 0 "
            "AND exit_fill_id IS NOT NULL AND unrealized_pnl = 0) OR "
            "(state = 'FAILED')",
            name="ck_paper_position_state_accounting",
        ),
        CheckConstraint("updated_at >= created_at", name="ck_paper_position_timestamps"),
        CheckConstraint(
            f"reason_code IN ({_values(PAPER_REASON_CODES)})",
            name="ck_paper_position_reason",
        ),
        Index(
            "uq_paper_positions_active_mode_symbol",
            "mode",
            "symbol",
            unique=True,
            postgresql_where=text("state IN ('OPEN','CLOSING')"),
            sqlite_where=text("state IN ('OPEN','CLOSING')"),
        ),
        Index("ix_paper_positions_state_symbol", "state", "symbol"),
        Index("ix_paper_positions_updated_at", "updated_at"),
    )

    position_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), primary_key=True)
    mode: Mapped[str] = mapped_column(String(8), nullable=False)
    symbol: Mapped[str] = mapped_column(String(SYMBOL_LENGTH), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    entry_order_id: Mapped[str] = mapped_column(
        String(IDENTITY_LENGTH),
        ForeignKey("paper_orders.order_id", ondelete="RESTRICT"),
        nullable=False,
    )
    entry_fill_id: Mapped[str] = mapped_column(
        String(IDENTITY_LENGTH),
        ForeignKey("paper_fills.fill_id", ondelete="RESTRICT"),
        nullable=False,
    )
    entry_quantity: Mapped[Decimal] = mapped_column(
        Numeric(QUANTITY_PRECISION, QUANTITY_SCALE), nullable=False
    )
    remaining_quantity: Mapped[Decimal] = mapped_column(
        Numeric(QUANTITY_PRECISION, QUANTITY_SCALE), nullable=False
    )
    average_entry_price: Mapped[Decimal] = mapped_column(
        Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=False
    )
    average_exit_price: Mapped[Decimal | None] = mapped_column(Numeric(PRICE_PRECISION, PRICE_SCALE))
    entry_fees: Mapped[Decimal] = mapped_column(Numeric(MONEY_PRECISION, MONEY_SCALE), nullable=False)
    exit_fees: Mapped[Decimal] = mapped_column(Numeric(MONEY_PRECISION, MONEY_SCALE), nullable=False)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(MONEY_PRECISION, MONEY_SCALE), nullable=False)
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(MONEY_PRECISION, MONEY_SCALE), nullable=False)
    stop_price: Mapped[Decimal] = mapped_column(Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=False)
    target_price: Mapped[Decimal] = mapped_column(Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_mark_price: Mapped[Decimal] = mapped_column(
        Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=False
    )
    last_mark_closed_until_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    reason_code: Mapped[str] = mapped_column(String(REASON_CODE_LENGTH), nullable=False)
    exit_fill_id: Mapped[str | None] = mapped_column(String(IDENTITY_LENGTH))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PaperExitEvaluationCursorRecord(Base):
    __tablename__ = "paper_exit_evaluation_cursors"
    __table_args__ = (
        UniqueConstraint(
            "position_id", name="uq_paper_exit_evaluation_cursor_position"
        ),
        CheckConstraint("mode = 'PAPER'", name="ck_paper_exit_cursor_mode"),
        CheckConstraint(
            "length(trim(cursor_id)) BETWEEN 1 AND 128 AND "
            "length(trim(contract_version)) BETWEEN 1 AND 128 AND "
            "length(trim(symbol)) BETWEEN 2 AND 32 AND "
            "length(trim(evaluation_policy_id)) BETWEEN 1 AND 128 AND "
            "length(trim(correlation_id)) BETWEEN 1 AND 128 AND "
            "length(trim(causation_id)) BETWEEN 1 AND 128",
            name="ck_paper_exit_cursor_identities",
        ),
        CheckConstraint(
            "last_evaluated_closed_until_ms >= position_opened_closed_until_ms "
            "AND position_opened_closed_until_ms >= 0 "
            "AND mod(last_evaluated_closed_until_ms, 60000) = 0 "
            "AND mod(position_opened_closed_until_ms, 60000) = 0",
            name="ck_paper_exit_cursor_boundaries",
        ),
        CheckConstraint("version >= 0", name="ck_paper_exit_cursor_version"),
        CheckConstraint(
            "updated_at >= created_at", name="ck_paper_exit_cursor_timestamps"
        ),
        CheckConstraint(
            "(last_advance_idempotency_key IS NULL "
            "AND last_advance_from_closed_until_ms IS NULL "
            "AND last_advance_to_closed_until_ms IS NULL "
            "AND last_advance_expected_version IS NULL "
            "AND last_window_identity IS NULL) OR "
            "(last_advance_idempotency_key IS NOT NULL "
            "AND length(trim(last_advance_idempotency_key)) BETWEEN 1 AND 128 "
            "AND last_advance_from_closed_until_ms IS NOT NULL "
            "AND last_advance_to_closed_until_ms IS NOT NULL "
            "AND last_advance_expected_version IS NOT NULL "
            "AND last_window_identity IS NOT NULL "
            "AND length(trim(last_window_identity)) BETWEEN 1 AND 128 "
            "AND last_advance_from_closed_until_ms >= 0 "
            "AND last_advance_to_closed_until_ms > "
            "last_advance_from_closed_until_ms "
            "AND last_advance_to_closed_until_ms = "
            "last_evaluated_closed_until_ms "
            "AND last_advance_expected_version + 1 = version)",
            name="ck_paper_exit_cursor_last_advance",
        ),
        Index(
            "ix_paper_exit_evaluation_cursors_updated_at",
            "updated_at",
            "position_id",
        ),
    )

    cursor_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), primary_key=True)
    contract_version: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    position_id: Mapped[str] = mapped_column(
        String(IDENTITY_LENGTH),
        ForeignKey("paper_positions.position_id", ondelete="RESTRICT"),
        nullable=False,
    )
    mode: Mapped[str] = mapped_column(String(8), nullable=False)
    symbol: Mapped[str] = mapped_column(String(SYMBOL_LENGTH), nullable=False)
    last_evaluated_closed_until_ms: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )
    position_opened_closed_until_ms: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )
    evaluation_policy_id: Mapped[str] = mapped_column(
        String(IDENTITY_LENGTH), nullable=False
    )
    version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    causation_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    last_advance_idempotency_key: Mapped[str | None] = mapped_column(
        String(IDENTITY_LENGTH)
    )
    last_advance_from_closed_until_ms: Mapped[int | None] = mapped_column(BigInteger)
    last_advance_to_closed_until_ms: Mapped[int | None] = mapped_column(BigInteger)
    last_advance_expected_version: Mapped[int | None] = mapped_column(BigInteger)
    last_window_identity: Mapped[str | None] = mapped_column(String(IDENTITY_LENGTH))


class PaperExitDecisionRecord(Base):
    __tablename__ = "paper_exit_decisions"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_paper_exit_decisions_idem"),
        UniqueConstraint(
            "position_id",
            "position_version",
            "cause",
            name="uq_paper_exit_position_version_cause",
        ),
        CheckConstraint("length(trim(idempotency_key)) BETWEEN 1 AND 128", name="ck_paper_exit_idem"),
        CheckConstraint(
            f"cause IN ({_values(PAPER_EXIT_CAUSES)})",
            name="ck_paper_exit_cause",
        ),
        CheckConstraint("position_version >= 0", name="ck_paper_exit_position_version"),
        CheckConstraint(
            f"{_finite('decision_price')} AND decision_price > 0",
            name="ck_paper_exit_price",
        ),
        CheckConstraint(
            f"{_finite('requested_close_quantity')} AND requested_close_quantity > 0",
            name="ck_paper_exit_quantity",
        ),
        CheckConstraint("source_closed_until_ms >= 0", name="ck_paper_exit_boundary"),
        CheckConstraint(
            f"reason_code IN ({_values(PAPER_REASON_CODES)})",
            name="ck_paper_exit_reason",
        ),
    )

    exit_decision_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    position_id: Mapped[str] = mapped_column(
        String(IDENTITY_LENGTH),
        ForeignKey("paper_positions.position_id", ondelete="RESTRICT"),
        nullable=False,
    )
    position_version: Mapped[int] = mapped_column(Integer, nullable=False)
    cause: Mapped[str] = mapped_column(String(24), nullable=False)
    decision_price: Mapped[Decimal] = mapped_column(Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=False)
    requested_close_quantity: Mapped[Decimal] = mapped_column(
        Numeric(QUANTITY_PRECISION, QUANTITY_SCALE), nullable=False
    )
    source_closed_until_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(REASON_CODE_LENGTH), nullable=False)


class PaperJournalEntryRecord(Base):
    __tablename__ = "paper_journal_entries"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_paper_journal_idempotency_key"),
        CheckConstraint(
            f"event_type IN ({_values(PAPER_EVENT_TYPES)})",
            name="ck_paper_journal_event_type",
        ),
        CheckConstraint(
            f"aggregate_type IN ({_values(AGGREGATE_TYPES)})",
            name="ck_paper_journal_aggregate_type",
        ),
        CheckConstraint("aggregate_version >= 0", name="ck_paper_journal_version"),
        CheckConstraint(
            "length(trim(aggregate_id)) BETWEEN 1 AND 128 AND "
            "length(trim(correlation_id)) BETWEEN 1 AND 128 AND "
            "length(trim(causation_id)) BETWEEN 1 AND 128 AND "
            "length(trim(idempotency_key)) BETWEEN 1 AND 128",
            name="ck_paper_journal_causal_ids",
        ),
        CheckConstraint(
            f"reason_code IN ({_values(PAPER_REASON_CODES)})",
            name="ck_paper_journal_reason",
        ),
        Index("ix_paper_journal_occurred_at", "occurred_at"),
        Index(
            "ix_paper_journal_aggregate",
            "aggregate_type",
            "aggregate_id",
        ),
        Index("ix_paper_journal_correlation_id", "correlation_id"),
    )

    journal_entry_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(24), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    aggregate_version: Mapped[int] = mapped_column(Integer, nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    causation_id: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(IDENTITY_LENGTH), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(REASON_CODE_LENGTH), nullable=False)
    command_id: Mapped[str | None] = mapped_column(
        String(IDENTITY_LENGTH),
        ForeignKey("paper_execution_commands.command_id", ondelete="RESTRICT"),
    )
    order_id: Mapped[str | None] = mapped_column(
        String(IDENTITY_LENGTH),
        ForeignKey("paper_orders.order_id", ondelete="RESTRICT"),
    )
    fill_id: Mapped[str | None] = mapped_column(
        String(IDENTITY_LENGTH),
        ForeignKey("paper_fills.fill_id", ondelete="RESTRICT"),
    )
    position_id: Mapped[str | None] = mapped_column(
        String(IDENTITY_LENGTH),
        ForeignKey("paper_positions.position_id", ondelete="RESTRICT"),
    )
    exit_decision_id: Mapped[str | None] = mapped_column(
        String(IDENTITY_LENGTH),
        ForeignKey("paper_exit_decisions.exit_decision_id", ondelete="RESTRICT"),
    )


class ControlMobileDeviceRecord(Base):
    """Public device identity only; Android private keys never reach the server."""

    __tablename__ = "control_mobile_devices"
    __table_args__ = (
        CheckConstraint("algorithm = 'ECDSA_P256_SHA256'", name="ck_control_mobile_device_algorithm"),
        CheckConstraint("key_version >= 1", name="ck_control_mobile_device_key_version"),
        CheckConstraint("octet_length(public_key_spki) BETWEEN 80 AND 512", name="ck_control_mobile_device_spki"),
        CheckConstraint("length(public_key_fingerprint) = 64", name="ck_control_mobile_device_fingerprint"),
        CheckConstraint(
            "(enabled AND revoked_at IS NULL) OR (NOT enabled AND revoked_at IS NOT NULL)",
            name="ck_control_mobile_device_revocation",
        ),
    )

    device_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    public_key_spki: Mapped[bytes] = mapped_column(LargeBinary(512), nullable=False)
    public_key_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(32), nullable=False)
    key_version: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    label: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ControlMobileReplayNonceRecord(Base):
    """Durable device-scoped claim made before a Control mutation."""

    __tablename__ = "control_mobile_replay_nonces"
    __table_args__ = (
        PrimaryKeyConstraint("device_id", "nonce", name="pk_control_mobile_replay_nonce"),
        ForeignKeyConstraint(
            ["device_id"], ["control_mobile_devices.device_id"], ondelete="RESTRICT",
            name="fk_control_mobile_replay_device",
        ),
        CheckConstraint("length(nonce) BETWEEN 22 AND 128", name="ck_control_mobile_replay_nonce"),
        Index("ix_control_mobile_replay_expires_at", "expires_at"),
    )

    device_id: Mapped[str] = mapped_column(String(36), nullable=False)
    nonce: Mapped[str] = mapped_column(String(128), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str | None] = mapped_column(String(48))
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
