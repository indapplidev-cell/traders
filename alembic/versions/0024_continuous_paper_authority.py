"""Add durable continuous PAPER authority and budget state.

Revision ID: 0024_continuous_paper_authority
Revises: 0023_scalping_v2_journal_causality
"""

from alembic import op
import sqlalchemy as sa


revision = "0024_continuous_paper_authority"
down_revision = "0023_scalping_v2_journal_causality"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "paper_first_canary_sessions",
        sa.Column("authority_mode", sa.String(length=32), nullable=False, server_default="FIRST_CANARY_HISTORICAL"),
    )
    op.add_column(
        "paper_first_canary_sessions",
        sa.Column("continuous_cycle_number", sa.BigInteger(), nullable=True),
    )
    op.create_check_constraint(
        "ck_paper_canary_authority_mode",
        "paper_first_canary_sessions",
        "authority_mode IN ('FIRST_CANARY_HISTORICAL','CONTINUOUS')",
    )
    op.create_unique_constraint(
        "uq_paper_continuous_cycle_number",
        "paper_first_canary_sessions",
        ["continuous_cycle_number"],
    )
    op.create_table(
        "paper_continuous_control",
        sa.Column("environment", sa.String(length=32), primary_key=True),
        sa.Column("control_mode", sa.String(length=32), nullable=False),
        sa.Column("control_state", sa.String(length=32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("mode_version", sa.Integer(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activation_source", sa.String(length=128), nullable=True),
        sa.Column("activation_reason", sa.String(length=80), nullable=True),
        sa.Column("trading_day_timezone", sa.String(length=16), nullable=False),
        sa.Column("budget_day", sa.Date(), nullable=False),
        sa.Column("daily_command_budget", sa.Integer(), nullable=False),
        sa.Column("daily_realized_loss_budget", sa.Numeric(38, 18), nullable=False),
        sa.Column("daily_risk_budget_bps", sa.Numeric(20, 10), nullable=False),
        sa.Column("max_consecutive_losses", sa.Integer(), nullable=True),
        sa.Column("commands_used", sa.Integer(), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(38, 18), nullable=False),
        sa.Column("realized_loss", sa.Numeric(38, 18), nullable=False),
        sa.Column("risk_used_bps", sa.Numeric(20, 10), nullable=False),
        sa.Column("loss_streak", sa.Integer(), nullable=False),
        sa.Column("pause_reason", sa.String(length=80), nullable=True),
        sa.Column("last_successful_reconciliation", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_command_id", sa.String(length=128), nullable=True),
        sa.Column("last_position_id", sa.String(length=128), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint("environment = 'PRODUCTION'", name="ck_paper_continuous_environment"),
        sa.CheckConstraint("control_mode = 'CONTINUOUS'", name="ck_paper_continuous_mode"),
        sa.CheckConstraint("control_state IN ('DISABLED','CONTINUOUS_ARMED','PAUSED_BY_RISK','EMERGENCY_STOPPED')", name="ck_paper_continuous_state"),
        sa.CheckConstraint("trading_day_timezone = 'UTC'", name="ck_paper_continuous_timezone"),
        sa.CheckConstraint("generation >= 1 AND mode_version >= 1 AND version >= 0", name="ck_paper_continuous_versions"),
        sa.CheckConstraint("daily_command_budget >= 1 AND commands_used >= 0", name="ck_paper_continuous_command_budget"),
        sa.CheckConstraint("daily_realized_loss_budget >= 0 AND realized_loss >= 0", name="ck_paper_continuous_loss_budget"),
        sa.CheckConstraint("daily_risk_budget_bps > 0 AND risk_used_bps >= 0", name="ck_paper_continuous_risk_budget"),
        sa.CheckConstraint("loss_streak >= 0", name="ck_paper_continuous_loss_streak"),
        sa.CheckConstraint("max_consecutive_losses IS NULL OR max_consecutive_losses >= 1", name="ck_paper_continuous_loss_streak_limit"),
        sa.CheckConstraint("enabled = (control_state = 'CONTINUOUS_ARMED')", name="ck_paper_continuous_enabled_state"),
    )
    op.create_table(
        "paper_continuous_control_events",
        sa.Column("event_id", sa.String(length=128), primary_key=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("control_state", sa.String(length=32), nullable=False),
        sa.Column("reason_code", sa.String(length=80), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.CheckConstraint("length(trim(event_type)) BETWEEN 1 AND 64", name="ck_paper_continuous_event_type"),
        sa.CheckConstraint("generation >= 1", name="ck_paper_continuous_event_generation"),
    )
    op.create_index("ix_paper_continuous_events_occurred", "paper_continuous_control_events", ["occurred_at"])


def downgrade() -> None:
    raise RuntimeError("0024 continuous PAPER authority is forward-only")
