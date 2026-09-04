"""Version continuous PAPER budget policy and disable virtual-money limits.

Revision ID: 0025_paper_budget_policy
Revises: 0024_continuous_paper_authority
"""

from alembic import op
import sqlalchemy as sa


revision = "0025_paper_budget_policy"
down_revision = "0024_continuous_paper_authority"
branch_labels = None
depends_on = None


POLICY_VERSION = "scalping-v2-continuous-paper-statistics-v2"
POLICY_SOURCE = "USER_AUTHORIZED_VIRTUAL_PAPER_STATISTICS_POLICY"
ENFORCEMENT_MODE = "PAPER_STATISTICS_ONLY"


def upgrade() -> None:
    op.add_column(
        "paper_continuous_control",
        sa.Column("budget_policy_version", sa.String(length=80), nullable=False,
                  server_default=POLICY_VERSION),
    )
    op.add_column(
        "paper_continuous_control",
        sa.Column("budget_policy_source", sa.String(length=128), nullable=False,
                  server_default=POLICY_SOURCE),
    )
    op.add_column(
        "paper_continuous_control",
        sa.Column("budget_enforcement_mode", sa.String(length=32), nullable=False,
                  server_default=ENFORCEMENT_MODE),
    )
    for name, unit in (
        ("daily_command_budget_unit", "trade_count"),
        ("daily_risk_budget_unit", "equity_basis_points"),
        ("daily_realized_loss_budget_unit", "USDT"),
        ("loss_streak_unit", "closed_trade_count"),
    ):
        op.add_column(
            "paper_continuous_control",
            sa.Column(name, sa.String(length=32), nullable=False, server_default=unit),
        )
    op.add_column(
        "paper_continuous_control",
        sa.Column("budget_reset_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "UPDATE paper_continuous_control "
        "SET budget_reset_at = (budget_day + INTERVAL '1 day') AT TIME ZONE 'UTC'"
    )
    op.alter_column("paper_continuous_control", "budget_reset_at", nullable=False)
    op.create_check_constraint(
        "ck_paper_continuous_budget_enforcement_mode",
        "paper_continuous_control",
        "budget_enforcement_mode IN ('PAPER_STATISTICS_ONLY','REAL_MONEY_LIMITED')",
    )
    # The old 10 commands / 50 bps / 0.5 USDT constants were not part of the
    # Scalping v2 policy.  Preserve their counters for statistics, but remove
    # their authority to pause virtual-money PAPER execution.
    op.execute(
        "UPDATE paper_continuous_control SET control_state = 'CONTINUOUS_ARMED', "
        "enabled = TRUE, pause_reason = NULL, version = version + 1 "
        "WHERE control_state = 'PAUSED_BY_RISK' AND pause_reason IN "
        "('DAILY_COMMAND_BUDGET_EXHAUSTED','DAILY_LOSS_BUDGET_EXHAUSTED',"
        "'DAILY_RISK_BUDGET_EXHAUSTED','MAX_CONSECUTIVE_LOSSES_REACHED')"
    )
    for column in (
        "budget_policy_version", "budget_policy_source", "budget_enforcement_mode",
        "daily_command_budget_unit", "daily_risk_budget_unit",
        "daily_realized_loss_budget_unit", "loss_streak_unit",
    ):
        op.alter_column("paper_continuous_control", column, server_default=None)


def downgrade() -> None:
    raise RuntimeError("0025 PAPER budget policy is forward-only")
