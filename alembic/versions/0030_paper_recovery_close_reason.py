"""Add the explicit operator recovery PAPER exit cause.

Revision ID: 0030_paper_recovery_close
Revises: 0029_stale_position_shadow
"""

from alembic import op


revision = "0030_paper_recovery_close"
down_revision = "0029_stale_position_shadow"
branch_labels = None
depends_on = None


_REASON_CONSTRAINTS = (
    ("paper_orders", "ck_paper_order_reason"),
    ("paper_order_events", "ck_paper_order_event_reason"),
    ("paper_positions", "ck_paper_position_reason"),
    ("paper_exit_decisions", "ck_paper_exit_reason"),
    ("paper_journal_entries", "ck_paper_journal_reason"),
)


def upgrade() -> None:
    op.drop_constraint("ck_paper_exit_cause", "paper_exit_decisions", type_="check")
    op.create_check_constraint(
        "ck_paper_exit_cause",
        "paper_exit_decisions",
        "cause IN ('STOP_LOSS','TAKE_PROFIT','SYSTEM_SAFETY_EXIT','OPERATOR_RECOVERY_CLOSE')",
    )
    for table, constraint in _REASON_CONSTRAINTS:
        op.drop_constraint(constraint, table, type_="check")
        op.create_check_constraint(
            constraint,
            table,
            "reason_code IN ("
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
            "'PAPER_EXIT_SYSTEM_SAFETY_TRIGGERED','PAPER_EXIT_OPERATOR_RECOVERY_CLOSE_AFTER_MISSED_STOP',"
            "'PAPER_EXIT_NO_TRIGGER','PAPER_EXIT_VERSION_CONFLICT','PAPER_IDEMPOTENCY_KEY_INVALID',"
            "'PAPER_IDEMPOTENCY_COMMAND_REPLAY','PAPER_IDEMPOTENCY_FILL_REPLAY',"
            "'PAPER_IDEMPOTENCY_JOURNAL_REPLAY','PAPER_INTERNAL_INVARIANT_VIOLATION')",
        )


def downgrade() -> None:
    raise RuntimeError("0030 PAPER recovery close reason is forward-only")
