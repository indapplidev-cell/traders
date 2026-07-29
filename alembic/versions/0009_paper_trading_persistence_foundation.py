"""Create the normalized PAPER persistence foundation.

Revision ID: 0009_paper_trading_persistence_foundation
Revises: 0008_engine_orchestrator_freshness_retry
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_paper_trading_persistence_foundation"
down_revision = "0008_engine_orchestrator_freshness_retry"
branch_labels = None
depends_on = None


PAPER_REASON_CODES = (
    "PAPER_CONFIG_MODE_MISSING_OFF",
    "PAPER_CONFIG_MODE_OFF",
    "PAPER_CONFIG_MODE_UNKNOWN",
    "PAPER_CONFIG_LIVE_DISABLED",
    "PAPER_CONFIG_POLICY_MISSING",
    "PAPER_INPUT_SYMBOL_INVALID",
    "PAPER_INPUT_SIDE_INVALID",
    "PAPER_INPUT_QUANTITY_INVALID",
    "PAPER_INPUT_NOTIONAL_INVALID",
    "PAPER_INPUT_PRICE_INVALID",
    "PAPER_INPUT_STOP_TARGET_INVALID",
    "PAPER_INPUT_IDENTITY_INVALID",
    "PAPER_INPUT_VALIDITY_INVALID",
    "PAPER_INPUT_TIME_INVALID",
    "PAPER_INPUT_STRATEGY_MISSING",
    "PAPER_INPUT_RISK_MISSING",
    "PAPER_SAFETY_SOURCE_STALE",
    "PAPER_SAFETY_HEALTH_DEGRADED",
    "PAPER_SAFETY_HEALTH_UNKNOWN",
    "PAPER_SAFETY_FUTURE_DATA_DETECTED",
    "PAPER_RISK_APPROVAL_MISSING",
    "PAPER_RISK_NOT_APPROVED",
    "PAPER_ORDER_CREATED",
    "PAPER_ORDER_VALIDATED",
    "PAPER_ORDER_OPENED",
    "PAPER_ORDER_FILLED",
    "PAPER_ORDER_REJECTED",
    "PAPER_ORDER_FAILED",
    "PAPER_ORDER_INVALID_TRANSITION",
    "PAPER_ORDER_TERMINAL",
    "PAPER_ORDER_TYPE_UNSUPPORTED",
    "PAPER_FILL_DUPLICATE",
    "PAPER_FILL_PARTIAL_UNSUPPORTED",
    "PAPER_FILL_INVALID",
    "PAPER_FILL_FUTURE_DATA",
    "PAPER_POSITION_OPENED",
    "PAPER_POSITION_CLOSING",
    "PAPER_POSITION_CLOSED",
    "PAPER_POSITION_INVALID_TRANSITION",
    "PAPER_POSITION_ALREADY_CLOSED",
    "PAPER_POSITION_VERSION_CONFLICT",
    "PAPER_POSITION_NEGATIVE_REMAINDER",
    "PAPER_POSITION_DUPLICATE_FILL",
    "PAPER_EXIT_CAUSE_UNSUPPORTED",
    "PAPER_EXIT_STOP_FIRST_CONFLICT",
    "PAPER_EXIT_STOP_LOSS_TRIGGERED",
    "PAPER_EXIT_TAKE_PROFIT_TRIGGERED",
    "PAPER_EXIT_SYSTEM_SAFETY_TRIGGERED",
    "PAPER_EXIT_NO_TRIGGER",
    "PAPER_EXIT_VERSION_CONFLICT",
    "PAPER_IDEMPOTENCY_KEY_INVALID",
    "PAPER_IDEMPOTENCY_COMMAND_REPLAY",
    "PAPER_IDEMPOTENCY_FILL_REPLAY",
    "PAPER_IDEMPOTENCY_JOURNAL_REPLAY",
    "PAPER_INTERNAL_INVARIANT_VIOLATION",
)
PAPER_EVENT_TYPES = (
    "PAPER_COMMAND_CREATED",
    "PAPER_COMMAND_REJECTED",
    "PAPER_ORDER_CREATED",
    "PAPER_ORDER_FILLED",
    "PAPER_POSITION_OPENED",
    "PAPER_EXIT_TRIGGERED",
    "PAPER_POSITION_CLOSED",
    "PAPER_EXECUTION_FAILED",
    "PAPER_SAFETY_BLOCKED",
)
PAPER_ORDER_STATES = ("CREATED", "VALIDATED", "OPEN", "FILLED", "REJECTED", "FAILED")


def _values(values: tuple[str, ...]) -> str:
    return ",".join(f"'{value}'" for value in values)


def _finite(column: str) -> str:
    return (
        f"{column} NOT IN (CAST('NaN' AS NUMERIC), "
        "CAST('Infinity' AS NUMERIC), CAST('-Infinity' AS NUMERIC))"
    )


def upgrade() -> None:
    op.create_table(
        "paper_simulation_policies",
        sa.Column("policy_id", sa.String(128), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("price_source", sa.String(48), nullable=False),
        sa.Column("timeframe", sa.String(8), nullable=False),
        sa.Column("latency_candles", sa.Integer(), nullable=False),
        sa.Column("slippage_bps", sa.Numeric(20, 10), nullable=False),
        sa.Column("fee_bps", sa.Numeric(20, 10), nullable=False),
        sa.Column("partial_fill_enabled", sa.Boolean(), nullable=False),
        sa.Column("future_data_allowed", sa.Boolean(), nullable=False),
        sa.Column("intrabar_conflict_policy", sa.String(40), nullable=False),
        sa.Column("configuration_fingerprint", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retired_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint(
            "policy_id",
            "policy_version",
            name="pk_paper_simulation_policies",
        ),
        sa.CheckConstraint(
            "length(trim(policy_id)) BETWEEN 1 AND 128",
            name="ck_paper_policy_id",
        ),
        sa.CheckConstraint("policy_version >= 1", name="ck_paper_policy_version"),
        sa.CheckConstraint("status IN ('ACTIVE','RETIRED')", name="ck_paper_policy_status"),
        sa.CheckConstraint(
            "price_source IN ('NEXT_ELIGIBLE_CLOSED_1M_OPEN')",
            name="ck_paper_policy_price_source",
        ),
        sa.CheckConstraint("timeframe IN ('1m')", name="ck_paper_policy_timeframe"),
        sa.CheckConstraint("latency_candles >= 0", name="ck_paper_policy_latency"),
        sa.CheckConstraint(
            f"{_finite('slippage_bps')} AND slippage_bps >= 0",
            name="ck_paper_policy_slippage",
        ),
        sa.CheckConstraint(
            f"{_finite('fee_bps')} AND fee_bps >= 0",
            name="ck_paper_policy_fee",
        ),
        sa.CheckConstraint(
            "partial_fill_enabled = false",
            name="ck_paper_policy_no_partial_fill",
        ),
        sa.CheckConstraint(
            "future_data_allowed = false",
            name="ck_paper_policy_no_future",
        ),
        sa.CheckConstraint(
            "intrabar_conflict_policy IN ('STOP_FIRST_CONSERVATIVE')",
            name="ck_paper_policy_conflict",
        ),
        sa.CheckConstraint(
            "length(trim(configuration_fingerprint)) BETWEEN 1 AND 128",
            name="ck_paper_policy_fingerprint",
        ),
        sa.CheckConstraint(
            "(status = 'ACTIVE' AND retired_at IS NULL) OR "
            "(status = 'RETIRED' AND retired_at IS NOT NULL)",
            name="ck_paper_policy_retirement",
        ),
    )

    op.create_table(
        "paper_execution_commands",
        sa.Column("command_id", sa.String(128), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("mode", sa.String(8), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("order_type", sa.String(24), nullable=False),
        sa.Column("requested_quantity", sa.Numeric(38, 18), nullable=False),
        sa.Column("requested_notional", sa.Numeric(38, 18)),
        sa.Column("entry_reference_price", sa.Numeric(38, 18), nullable=False),
        sa.Column("stop_price", sa.Numeric(38, 18), nullable=False),
        sa.Column("target_price", sa.Numeric(38, 18), nullable=False),
        sa.Column("strategy_decision_id", sa.String(128), nullable=False),
        sa.Column("risk_decision_id", sa.String(128), nullable=False),
        sa.Column("setup_id", sa.String(128), nullable=False),
        sa.Column("pipeline_run_id", sa.String(128), nullable=False),
        sa.Column("analysis_result_id", sa.String(128), nullable=False),
        sa.Column("closed_until_ms", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until_ms", sa.BigInteger(), nullable=False),
        sa.Column("configuration_fingerprint", sa.String(128), nullable=False),
        sa.Column("simulation_policy_id", sa.String(128), nullable=False),
        sa.Column("fee_policy_id", sa.String(128), nullable=False),
        sa.Column("slippage_policy_id", sa.String(128), nullable=False),
        sa.Column("latency_policy_id", sa.String(128), nullable=False),
        sa.Column("final_paper_approval", sa.Boolean(), nullable=False),
        sa.Column("input_health_status", sa.String(24), nullable=False),
        sa.Column("future_bars_used", sa.Boolean(), nullable=False),
        sa.Column(
            "processing_status",
            sa.String(16),
            server_default=sa.text("'PENDING'"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("command_id"),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_paper_commands_idempotency_key",
        ),
        sa.CheckConstraint(
            "length(trim(idempotency_key)) BETWEEN 1 AND 128",
            name="ck_paper_command_idem",
        ),
        sa.CheckConstraint("mode = 'PAPER'", name="ck_paper_command_mode"),
        sa.CheckConstraint("side IN ('LONG','SHORT')", name="ck_paper_command_side"),
        sa.CheckConstraint(
            "order_type IN ('MARKET_SIMULATED')",
            name="ck_paper_command_order_type",
        ),
        sa.CheckConstraint(
            "length(trim(symbol)) BETWEEN 2 AND 32",
            name="ck_paper_command_symbol",
        ),
        sa.CheckConstraint(
            f"{_finite('requested_quantity')} AND requested_quantity > 0",
            name="ck_paper_command_quantity",
        ),
        sa.CheckConstraint(
            f"requested_notional IS NULL OR ({_finite('requested_notional')} "
            "AND requested_notional > 0)",
            name="ck_paper_command_notional",
        ),
        sa.CheckConstraint(
            "requested_notional IS NULL OR "
            "requested_notional = requested_quantity * entry_reference_price",
            name="ck_paper_command_notional_consistency",
        ),
        sa.CheckConstraint(
            " AND ".join(
                f"{_finite(name)} AND {name} > 0"
                for name in ("entry_reference_price", "stop_price", "target_price")
            ),
            name="ck_paper_command_prices",
        ),
        sa.CheckConstraint(
            "(side = 'LONG' AND stop_price < entry_reference_price "
            "AND entry_reference_price < target_price) OR "
            "(side = 'SHORT' AND target_price < entry_reference_price "
            "AND entry_reference_price < stop_price)",
            name="ck_paper_command_geometry",
        ),
        sa.CheckConstraint(
            "closed_until_ms >= 0",
            name="ck_paper_command_closed_until",
        ),
        sa.CheckConstraint(
            "valid_until_ms >= closed_until_ms",
            name="ck_paper_command_valid_until",
        ),
        sa.CheckConstraint(
            "final_paper_approval = true",
            name="ck_paper_command_approval",
        ),
        sa.CheckConstraint(
            "future_bars_used = false",
            name="ck_paper_command_no_future",
        ),
        sa.CheckConstraint(
            "input_health_status IN ('HEALTHY','CURRENT','WITHIN_GRACE')",
            name="ck_paper_command_health",
        ),
        sa.CheckConstraint(
            "processing_status IN ('PENDING','PROCESSING','COMPLETED','FAILED')",
            name="ck_paper_command_processing",
        ),
        sa.CheckConstraint(
            "length(trim(strategy_decision_id)) BETWEEN 1 AND 128 AND "
            "length(trim(risk_decision_id)) BETWEEN 1 AND 128 AND "
            "length(trim(setup_id)) BETWEEN 1 AND 128 AND "
            "length(trim(pipeline_run_id)) BETWEEN 1 AND 128 AND "
            "length(trim(analysis_result_id)) BETWEEN 1 AND 128",
            name="ck_paper_command_causal_ids",
        ),
        sa.CheckConstraint(
            "length(trim(configuration_fingerprint)) BETWEEN 1 AND 128 AND "
            "length(trim(simulation_policy_id)) BETWEEN 1 AND 128 AND "
            "length(trim(fee_policy_id)) BETWEEN 1 AND 128 AND "
            "length(trim(slippage_policy_id)) BETWEEN 1 AND 128 AND "
            "length(trim(latency_policy_id)) BETWEEN 1 AND 128",
            name="ck_paper_command_policy_ids",
        ),
    )
    op.create_index(
        "ix_paper_commands_processing_created",
        "paper_execution_commands",
        ["processing_status", "created_at"],
    )
    op.create_index(
        "ix_paper_commands_pipeline_run_id",
        "paper_execution_commands",
        ["pipeline_run_id"],
    )
    op.create_index(
        "ix_paper_commands_analysis_result_id",
        "paper_execution_commands",
        ["analysis_result_id"],
    )

    op.create_table(
        "paper_orders",
        sa.Column("order_id", sa.String(128), nullable=False),
        sa.Column("command_id", sa.String(128), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("order_role", sa.String(8), nullable=False),
        sa.Column("mode", sa.String(8), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("order_type", sa.String(24), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("requested_quantity", sa.Numeric(38, 18), nullable=False),
        sa.Column("filled_quantity", sa.Numeric(38, 18), nullable=False),
        sa.Column("average_fill_price", sa.Numeric(38, 18)),
        sa.Column("total_fees", sa.Numeric(38, 18), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("reason_code", sa.String(80), nullable=False),
        sa.Column("applied_fill_id", sa.String(128)),
        sa.ForeignKeyConstraint(
            ["command_id"],
            ["paper_execution_commands.command_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("order_id"),
        sa.UniqueConstraint("idempotency_key", name="uq_paper_orders_idempotency_key"),
        sa.UniqueConstraint(
            "command_id",
            "order_role",
            name="uq_paper_orders_command_role",
        ),
        sa.CheckConstraint(
            "length(trim(idempotency_key)) BETWEEN 1 AND 128",
            name="ck_paper_order_idem",
        ),
        sa.CheckConstraint("order_role IN ('ENTRY','EXIT')", name="ck_paper_order_role"),
        sa.CheckConstraint("mode = 'PAPER'", name="ck_paper_order_mode"),
        sa.CheckConstraint("side IN ('LONG','SHORT')", name="ck_paper_order_side"),
        sa.CheckConstraint(
            "order_type IN ('MARKET_SIMULATED')",
            name="ck_paper_order_order_type",
        ),
        sa.CheckConstraint(
            f"state IN ({_values(PAPER_ORDER_STATES)})",
            name="ck_paper_order_state",
        ),
        sa.CheckConstraint(
            f"{_finite('requested_quantity')} AND requested_quantity > 0 AND "
            f"{_finite('filled_quantity')} AND filled_quantity >= 0 AND "
            "filled_quantity <= requested_quantity",
            name="ck_paper_order_quantities",
        ),
        sa.CheckConstraint(
            f"{_finite('total_fees')} AND total_fees >= 0",
            name="ck_paper_order_fees",
        ),
        sa.CheckConstraint(
            f"average_fill_price IS NULL OR ({_finite('average_fill_price')} "
            "AND average_fill_price > 0)",
            name="ck_paper_order_average_price",
        ),
        sa.CheckConstraint(
            "(state = 'FILLED' AND filled_quantity = requested_quantity "
            "AND average_fill_price IS NOT NULL AND average_fill_price > 0 "
            "AND applied_fill_id IS NOT NULL) OR "
            "(state <> 'FILLED' AND filled_quantity = 0 "
            "AND average_fill_price IS NULL AND total_fees = 0 "
            "AND applied_fill_id IS NULL)",
            name="ck_paper_order_state_accounting",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_paper_order_timestamps",
        ),
        sa.CheckConstraint("version >= 0", name="ck_paper_order_version"),
        sa.CheckConstraint(
            f"reason_code IN ({_values(PAPER_REASON_CODES)})",
            name="ck_paper_order_reason",
        ),
    )
    op.create_index(
        "ix_paper_orders_state_created_at",
        "paper_orders",
        ["state", "created_at"],
    )

    op.create_table(
        "paper_order_events",
        sa.Column("order_event_id", sa.String(128), nullable=False),
        sa.Column("order_id", sa.String(128), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("from_state", sa.String(16)),
        sa.Column("to_state", sa.String(16), nullable=False),
        sa.Column("aggregate_version", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("correlation_id", sa.String(128), nullable=False),
        sa.Column("causation_id", sa.String(128), nullable=False),
        sa.Column("reason_code", sa.String(80), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["paper_orders.order_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("order_event_id"),
        sa.UniqueConstraint("idempotency_key", name="uq_paper_order_events_idem"),
        sa.UniqueConstraint(
            "order_id",
            "aggregate_version",
            name="uq_paper_order_events_order_version",
        ),
        sa.CheckConstraint(
            f"event_type IN ({_values(PAPER_EVENT_TYPES)})",
            name="ck_paper_order_event_type",
        ),
        sa.CheckConstraint(
            f"from_state IS NULL OR from_state IN ({_values(PAPER_ORDER_STATES)})",
            name="ck_paper_order_event_from_state",
        ),
        sa.CheckConstraint(
            f"to_state IN ({_values(PAPER_ORDER_STATES)})",
            name="ck_paper_order_event_to_state",
        ),
        sa.CheckConstraint(
            "aggregate_version >= 0",
            name="ck_paper_order_event_version",
        ),
        sa.CheckConstraint(
            "length(trim(idempotency_key)) BETWEEN 1 AND 128 AND "
            "length(trim(correlation_id)) BETWEEN 1 AND 128 AND "
            "length(trim(causation_id)) BETWEEN 1 AND 128",
            name="ck_paper_order_event_causal_ids",
        ),
        sa.CheckConstraint(
            f"reason_code IN ({_values(PAPER_REASON_CODES)})",
            name="ck_paper_order_event_reason",
        ),
    )

    op.create_table(
        "paper_fills",
        sa.Column("fill_id", sa.String(128), nullable=False),
        sa.Column("order_id", sa.String(128), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("fill_role", sa.String(8), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("quantity", sa.Numeric(38, 18), nullable=False),
        sa.Column("price", sa.Numeric(38, 18), nullable=False),
        sa.Column("fee_amount", sa.Numeric(38, 18), nullable=False),
        sa.Column("fee_asset", sa.String(32), nullable=False),
        sa.Column("filled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_closed_until_ms", sa.BigInteger(), nullable=False),
        sa.Column("simulation_policy_id", sa.String(128), nullable=False),
        sa.Column("slippage_policy_id", sa.String(128), nullable=False),
        sa.Column("fee_policy_id", sa.String(128), nullable=False),
        sa.Column("latency_policy_id", sa.String(128), nullable=False),
        sa.Column("future_bars_used", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["paper_orders.order_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("fill_id"),
        sa.UniqueConstraint("idempotency_key", name="uq_paper_fills_idempotency_key"),
        sa.UniqueConstraint("order_id", "fill_role", name="uq_paper_fills_order_role"),
        sa.CheckConstraint(
            "length(trim(idempotency_key)) BETWEEN 1 AND 128",
            name="ck_paper_fill_idem",
        ),
        sa.CheckConstraint("fill_role IN ('ENTRY','EXIT')", name="ck_paper_fill_role"),
        sa.CheckConstraint("side IN ('LONG','SHORT')", name="ck_paper_fill_side"),
        sa.CheckConstraint(
            f"{_finite('quantity')} AND quantity > 0",
            name="ck_paper_fill_quantity",
        ),
        sa.CheckConstraint(
            f"{_finite('price')} AND price > 0",
            name="ck_paper_fill_price",
        ),
        sa.CheckConstraint(
            f"{_finite('fee_amount')} AND fee_amount >= 0",
            name="ck_paper_fill_fee",
        ),
        sa.CheckConstraint(
            "length(trim(fee_asset)) BETWEEN 2 AND 32",
            name="ck_paper_fill_asset",
        ),
        sa.CheckConstraint(
            "source_closed_until_ms >= 0",
            name="ck_paper_fill_boundary",
        ),
        sa.CheckConstraint(
            "future_bars_used = false",
            name="ck_paper_fill_no_future",
        ),
        sa.CheckConstraint(
            "length(trim(simulation_policy_id)) BETWEEN 1 AND 128 AND "
            "length(trim(slippage_policy_id)) BETWEEN 1 AND 128 AND "
            "length(trim(fee_policy_id)) BETWEEN 1 AND 128 AND "
            "length(trim(latency_policy_id)) BETWEEN 1 AND 128",
            name="ck_paper_fill_policy_ids",
        ),
    )

    op.create_table(
        "paper_positions",
        sa.Column("position_id", sa.String(128), nullable=False),
        sa.Column("mode", sa.String(8), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("entry_order_id", sa.String(128), nullable=False),
        sa.Column("entry_fill_id", sa.String(128), nullable=False),
        sa.Column("entry_quantity", sa.Numeric(38, 18), nullable=False),
        sa.Column("remaining_quantity", sa.Numeric(38, 18), nullable=False),
        sa.Column("average_entry_price", sa.Numeric(38, 18), nullable=False),
        sa.Column("average_exit_price", sa.Numeric(38, 18)),
        sa.Column("entry_fees", sa.Numeric(38, 18), nullable=False),
        sa.Column("exit_fees", sa.Numeric(38, 18), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(38, 18), nullable=False),
        sa.Column("unrealized_pnl", sa.Numeric(38, 18), nullable=False),
        sa.Column("stop_price", sa.Numeric(38, 18), nullable=False),
        sa.Column("target_price", sa.Numeric(38, 18), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("last_mark_price", sa.Numeric(38, 18), nullable=False),
        sa.Column("last_mark_closed_until_ms", sa.BigInteger(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("reason_code", sa.String(80), nullable=False),
        sa.Column("exit_fill_id", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["entry_order_id"],
            ["paper_orders.order_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["entry_fill_id"],
            ["paper_fills.fill_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("position_id"),
        sa.CheckConstraint("mode = 'PAPER'", name="ck_paper_position_mode"),
        sa.CheckConstraint("side IN ('LONG','SHORT')", name="ck_paper_position_side"),
        sa.CheckConstraint(
            "state IN ('OPEN','CLOSING','CLOSED','FAILED')",
            name="ck_paper_position_state",
        ),
        sa.CheckConstraint(
            f"{_finite('entry_quantity')} AND entry_quantity > 0 AND "
            f"{_finite('remaining_quantity')} AND remaining_quantity >= 0 "
            "AND remaining_quantity <= entry_quantity",
            name="ck_paper_position_quantities",
        ),
        sa.CheckConstraint(
            f"{_finite('average_entry_price')} AND average_entry_price > 0 AND "
            f"(average_exit_price IS NULL OR ({_finite('average_exit_price')} "
            "AND average_exit_price > 0))",
            name="ck_paper_position_average_prices",
        ),
        sa.CheckConstraint(
            f"{_finite('entry_fees')} AND entry_fees >= 0 AND "
            f"{_finite('exit_fees')} AND exit_fees >= 0",
            name="ck_paper_position_fees",
        ),
        sa.CheckConstraint(
            f"{_finite('realized_pnl')} AND {_finite('unrealized_pnl')}",
            name="ck_paper_position_pnl",
        ),
        sa.CheckConstraint(
            f"{_finite('stop_price')} AND stop_price > 0 AND "
            f"{_finite('target_price')} AND target_price > 0 AND "
            f"{_finite('last_mark_price')} AND last_mark_price > 0",
            name="ck_paper_position_prices",
        ),
        sa.CheckConstraint(
            "(side = 'LONG' AND stop_price < average_entry_price "
            "AND average_entry_price < target_price) OR "
            "(side = 'SHORT' AND target_price < average_entry_price "
            "AND average_entry_price < stop_price)",
            name="ck_paper_position_geometry",
        ),
        sa.CheckConstraint(
            "last_mark_closed_until_ms >= 0",
            name="ck_paper_position_boundary",
        ),
        sa.CheckConstraint("version >= 0", name="ck_paper_position_version"),
        sa.CheckConstraint(
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
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_paper_position_timestamps",
        ),
        sa.CheckConstraint(
            f"reason_code IN ({_values(PAPER_REASON_CODES)})",
            name="ck_paper_position_reason",
        ),
    )
    op.create_index(
        "uq_paper_positions_active_mode_symbol",
        "paper_positions",
        ["mode", "symbol"],
        unique=True,
        postgresql_where=sa.text("state IN ('OPEN','CLOSING')"),
    )
    op.create_index(
        "ix_paper_positions_state_symbol",
        "paper_positions",
        ["state", "symbol"],
    )
    op.create_index(
        "ix_paper_positions_updated_at",
        "paper_positions",
        ["updated_at"],
    )

    op.create_table(
        "paper_exit_decisions",
        sa.Column("exit_decision_id", sa.String(128), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("position_id", sa.String(128), nullable=False),
        sa.Column("position_version", sa.Integer(), nullable=False),
        sa.Column("cause", sa.String(24), nullable=False),
        sa.Column("decision_price", sa.Numeric(38, 18), nullable=False),
        sa.Column("requested_close_quantity", sa.Numeric(38, 18), nullable=False),
        sa.Column("source_closed_until_ms", sa.BigInteger(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason_code", sa.String(80), nullable=False),
        sa.ForeignKeyConstraint(
            ["position_id"],
            ["paper_positions.position_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("exit_decision_id"),
        sa.UniqueConstraint("idempotency_key", name="uq_paper_exit_decisions_idem"),
        sa.UniqueConstraint(
            "position_id",
            "position_version",
            "cause",
            name="uq_paper_exit_position_version_cause",
        ),
        sa.CheckConstraint(
            "length(trim(idempotency_key)) BETWEEN 1 AND 128",
            name="ck_paper_exit_idem",
        ),
        sa.CheckConstraint(
            "cause IN ('STOP_LOSS','TAKE_PROFIT','SYSTEM_SAFETY_EXIT')",
            name="ck_paper_exit_cause",
        ),
        sa.CheckConstraint(
            "position_version >= 0",
            name="ck_paper_exit_position_version",
        ),
        sa.CheckConstraint(
            f"{_finite('decision_price')} AND decision_price > 0",
            name="ck_paper_exit_price",
        ),
        sa.CheckConstraint(
            f"{_finite('requested_close_quantity')} "
            "AND requested_close_quantity > 0",
            name="ck_paper_exit_quantity",
        ),
        sa.CheckConstraint(
            "source_closed_until_ms >= 0",
            name="ck_paper_exit_boundary",
        ),
        sa.CheckConstraint(
            f"reason_code IN ({_values(PAPER_REASON_CODES)})",
            name="ck_paper_exit_reason",
        ),
    )

    op.create_table(
        "paper_journal_entries",
        sa.Column("journal_entry_id", sa.String(128), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("aggregate_type", sa.String(24), nullable=False),
        sa.Column("aggregate_id", sa.String(128), nullable=False),
        sa.Column("aggregate_version", sa.Integer(), nullable=False),
        sa.Column("correlation_id", sa.String(128), nullable=False),
        sa.Column("causation_id", sa.String(128), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("reason_code", sa.String(80), nullable=False),
        sa.Column("command_id", sa.String(128)),
        sa.Column("order_id", sa.String(128)),
        sa.Column("fill_id", sa.String(128)),
        sa.Column("position_id", sa.String(128)),
        sa.Column("exit_decision_id", sa.String(128)),
        sa.ForeignKeyConstraint(
            ["command_id"],
            ["paper_execution_commands.command_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["paper_orders.order_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["fill_id"],
            ["paper_fills.fill_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["position_id"],
            ["paper_positions.position_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["exit_decision_id"],
            ["paper_exit_decisions.exit_decision_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("journal_entry_id"),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_paper_journal_idempotency_key",
        ),
        sa.CheckConstraint(
            f"event_type IN ({_values(PAPER_EVENT_TYPES)})",
            name="ck_paper_journal_event_type",
        ),
        sa.CheckConstraint(
            "aggregate_type IN "
            "('paper_command','paper_order','paper_fill','paper_position','paper_exit')",
            name="ck_paper_journal_aggregate_type",
        ),
        sa.CheckConstraint(
            "aggregate_version >= 0",
            name="ck_paper_journal_version",
        ),
        sa.CheckConstraint(
            "length(trim(aggregate_id)) BETWEEN 1 AND 128 AND "
            "length(trim(correlation_id)) BETWEEN 1 AND 128 AND "
            "length(trim(causation_id)) BETWEEN 1 AND 128 AND "
            "length(trim(idempotency_key)) BETWEEN 1 AND 128",
            name="ck_paper_journal_causal_ids",
        ),
        sa.CheckConstraint(
            f"reason_code IN ({_values(PAPER_REASON_CODES)})",
            name="ck_paper_journal_reason",
        ),
    )
    op.create_index(
        "ix_paper_journal_occurred_at",
        "paper_journal_entries",
        ["occurred_at"],
    )
    op.create_index(
        "ix_paper_journal_aggregate",
        "paper_journal_entries",
        ["aggregate_type", "aggregate_id"],
    )
    op.create_index(
        "ix_paper_journal_correlation_id",
        "paper_journal_entries",
        ["correlation_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_paper_journal_correlation_id",
        table_name="paper_journal_entries",
    )
    op.drop_index(
        "ix_paper_journal_aggregate",
        table_name="paper_journal_entries",
    )
    op.drop_index(
        "ix_paper_journal_occurred_at",
        table_name="paper_journal_entries",
    )
    op.drop_table("paper_journal_entries")
    op.drop_table("paper_exit_decisions")
    op.drop_index("ix_paper_positions_updated_at", table_name="paper_positions")
    op.drop_index("ix_paper_positions_state_symbol", table_name="paper_positions")
    op.drop_index(
        "uq_paper_positions_active_mode_symbol",
        table_name="paper_positions",
    )
    op.drop_table("paper_positions")
    op.drop_table("paper_fills")
    op.drop_table("paper_order_events")
    op.drop_index("ix_paper_orders_state_created_at", table_name="paper_orders")
    op.drop_table("paper_orders")
    op.drop_index(
        "ix_paper_commands_analysis_result_id",
        table_name="paper_execution_commands",
    )
    op.drop_index(
        "ix_paper_commands_pipeline_run_id",
        table_name="paper_execution_commands",
    )
    op.drop_index(
        "ix_paper_commands_processing_created",
        table_name="paper_execution_commands",
    )
    op.drop_table("paper_execution_commands")
    op.drop_table("paper_simulation_policies")
