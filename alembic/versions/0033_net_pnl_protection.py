"""Add authoritative Scalping net-PnL protection evidence.

Revision ID: 0033_net_pnl_protection
Revises: 0032_scalping_hold_lifecycle
"""

from alembic import op
import sqlalchemy as sa


revision = "0033_net_pnl_protection"
down_revision = "0032_scalping_hold_lifecycle"
branch_labels = None
depends_on = None


_REASON_CONSTRAINTS = (
    ("paper_orders", "ck_paper_order_reason"),
    ("paper_order_events", "ck_paper_order_event_reason"),
    ("paper_positions", "ck_paper_position_reason"),
    ("paper_exit_decisions", "ck_paper_exit_reason"),
    ("paper_journal_entries", "ck_paper_journal_reason"),
)

_REASONS = (
    "'PAPER_CONFIG_MODE_MISSING_OFF','PAPER_CONFIG_MODE_OFF','PAPER_CONFIG_MODE_UNKNOWN',"
    "'PAPER_CONFIG_LIVE_DISABLED','PAPER_CONFIG_POLICY_MISSING','PAPER_INPUT_SYMBOL_INVALID',"
    "'PAPER_INPUT_SIDE_INVALID','PAPER_INPUT_QUANTITY_INVALID','PAPER_INPUT_NOTIONAL_INVALID',"
    "'PAPER_INPUT_PRICE_INVALID','PAPER_INPUT_STOP_TARGET_INVALID','PAPER_INPUT_IDENTITY_INVALID',"
    "'PAPER_INPUT_VALIDITY_INVALID','PAPER_INPUT_TIME_INVALID','PAPER_INPUT_STRATEGY_MISSING',"
    "'PAPER_INPUT_RISK_MISSING','PAPER_SAFETY_SOURCE_STALE','PAPER_SAFETY_HEALTH_DEGRADED',"
    "'PAPER_SAFETY_HEALTH_UNKNOWN','PAPER_SAFETY_FUTURE_DATA_DETECTED','PAPER_RISK_APPROVAL_MISSING',"
    "'PAPER_RISK_NOT_APPROVED','PAPER_ORDER_CREATED','PAPER_ORDER_VALIDATED','PAPER_ORDER_OPENED',"
    "'PAPER_ORDER_FILLED','PAPER_ORDER_REJECTED','PAPER_ORDER_FAILED','PAPER_ORDER_INVALID_TRANSITION',"
    "'PAPER_ORDER_TERMINAL','PAPER_ORDER_TYPE_UNSUPPORTED','PAPER_FILL_DUPLICATE',"
    "'PAPER_FILL_PARTIAL_UNSUPPORTED','PAPER_FILL_INVALID','PAPER_FILL_FUTURE_DATA',"
    "'PAPER_POSITION_OPENED','PAPER_POSITION_CLOSING','PAPER_POSITION_CLOSED',"
    "'PAPER_POSITION_INVALID_TRANSITION','PAPER_POSITION_ALREADY_CLOSED',"
    "'PAPER_POSITION_VERSION_CONFLICT','PAPER_POSITION_NEGATIVE_REMAINDER',"
    "'PAPER_POSITION_DUPLICATE_FILL','PAPER_EXIT_CAUSE_UNSUPPORTED','PAPER_EXIT_STOP_FIRST_CONFLICT',"
    "'PAPER_EXIT_STOP_LOSS_TRIGGERED','PAPER_EXIT_TAKE_PROFIT_TRIGGERED',"
    "'PAPER_EXIT_SYSTEM_SAFETY_TRIGGERED','PAPER_EXIT_NET_PNL_PROTECTION_TRIGGERED',"
    "'PAPER_EXIT_OPERATOR_RECOVERY_CLOSE_AFTER_MISSED_STOP','PAPER_EXIT_NO_TRIGGER',"
    "'PAPER_EXIT_VERSION_CONFLICT','PAPER_IDEMPOTENCY_KEY_INVALID',"
    "'PAPER_IDEMPOTENCY_COMMAND_REPLAY','PAPER_IDEMPOTENCY_FILL_REPLAY',"
    "'PAPER_IDEMPOTENCY_JOURNAL_REPLAY','PAPER_INTERNAL_INVARIANT_VIOLATION'"
)


def upgrade() -> None:
    table = "scalping_position_hold_decisions"
    op.add_column(table, sa.Column(
        "soft_timeout_seconds", sa.BigInteger(), nullable=False, server_default="600"
    ))
    op.add_column(table, sa.Column(
        "hard_timeout_seconds", sa.BigInteger(), nullable=False, server_default="1200"
    ))
    op.add_column(table, sa.Column("net_exit_pnl_current", sa.Numeric(38, 18)))
    op.add_column(table, sa.Column("net_exit_pnl_currency", sa.String(16)))
    op.add_column(table, sa.Column("net_exit_pnl_quantized", sa.Numeric(38, 18)))
    op.add_column(table, sa.Column(
        "net_pnl_protection_window_active", sa.Boolean(), nullable=False,
        server_default=sa.false(),
    ))
    op.add_column(table, sa.Column(
        "net_pnl_protection_triggered", sa.Boolean(), nullable=False,
        server_default=sa.false(),
    ))
    op.add_column(table, sa.Column("net_pnl_protection_triggered_at", sa.DateTime(timezone=True)))
    op.add_column(table, sa.Column("net_pnl_protection_1m_boundary", sa.BigInteger()))
    op.add_column(table, sa.Column("exit_candidate_reason", sa.String(80)))
    op.add_column(table, sa.Column("exit_decision_reason", sa.String(80)))
    op.add_column(table, sa.Column("exit_decision_at", sa.DateTime(timezone=True)))
    op.add_column(table, sa.Column("exit_fill_at", sa.DateTime(timezone=True)))
    op.drop_constraint("ck_scalping_hold_state", table, type_="check")
    op.drop_constraint("ck_scalping_hold_exit_complete", table, type_="check")
    op.create_check_constraint(
        "ck_scalping_hold_state", table,
        "lifecycle_state IN ('FRESH','AT_RISK','STALE','EXTENSION_ALLOWED',"
        "'EXTENSION_EXHAUSTED','NET_PNL_PROTECTION_ACTIVE',"
        "'NET_PNL_PROTECTION_TRIGGERED','FORCE_EXIT')",
    )
    op.create_check_constraint(
        "ck_scalping_hold_exit_complete", table,
        "(lifecycle_state IN ('FORCE_EXIT','NET_PNL_PROTECTION_TRIGGERED')) "
        "= (exit_reason IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_scalping_hold_net_pnl_trigger", table,
        "(NOT net_pnl_protection_triggered) OR "
        "(net_pnl_protection_window_active AND net_exit_pnl_quantized > 0 "
        "AND net_pnl_protection_triggered_at IS NOT NULL "
        "AND net_pnl_protection_1m_boundary = evaluation_closed_until_ms "
        "AND exit_decision_reason = 'NET_PNL_PROTECTION')",
    )

    op.drop_constraint("ck_paper_exit_cause", "paper_exit_decisions", type_="check")
    op.create_check_constraint(
        "ck_paper_exit_cause", "paper_exit_decisions",
        "cause IN ('STOP_LOSS','TAKE_PROFIT','SYSTEM_SAFETY_EXIT',"
        "'NET_PNL_PROTECTION','OPERATOR_RECOVERY_CLOSE')",
    )
    for reason_table, constraint in _REASON_CONSTRAINTS:
        op.drop_constraint(constraint, reason_table, type_="check")
        op.create_check_constraint(
            constraint, reason_table, f"reason_code IN ({_REASONS})"
        )


def downgrade() -> None:
    raise RuntimeError("0033 net PnL protection is forward-only")
