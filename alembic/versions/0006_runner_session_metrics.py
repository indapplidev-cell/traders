"""add runner session metrics snapshot table"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0006_runner_metrics"
down_revision = "0005_runner_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runner_session_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("runner_session_id", sa.Integer(), nullable=False),
        sa.Column("ticks_requested", sa.Integer(), nullable=False),
        sa.Column("ticks_completed", sa.Integer(), nullable=False),
        sa.Column("audit_ticks_count", sa.Integer(), nullable=False),
        sa.Column("error_ticks_count", sa.Integer(), nullable=False),
        sa.Column("success_rate", sa.Float(), nullable=False),
        sa.Column("strategy_buy_count", sa.Integer(), nullable=False),
        sa.Column("strategy_sell_count", sa.Integer(), nullable=False),
        sa.Column("strategy_hold_count", sa.Integer(), nullable=False),
        sa.Column("final_buy_count", sa.Integer(), nullable=False),
        sa.Column("final_sell_count", sa.Integer(), nullable=False),
        sa.Column("final_hold_count", sa.Integer(), nullable=False),
        sa.Column("risk_approved_count", sa.Integer(), nullable=False),
        sa.Column("risk_rejected_count", sa.Integer(), nullable=False),
        sa.Column("risk_rejection_rate", sa.Float(), nullable=False),
        sa.Column("execution_executed_count", sa.Integer(), nullable=False),
        sa.Column("execution_skipped_count", sa.Integer(), nullable=False),
        sa.Column("average_confidence", sa.Numeric(24, 10), nullable=True),
        sa.Column("min_confidence", sa.Numeric(24, 10), nullable=True),
        sa.Column("max_confidence", sa.Numeric(24, 10), nullable=True),
        sa.Column("candles_used_min", sa.Integer(), nullable=True),
        sa.Column("candles_used_max", sa.Integer(), nullable=True),
        sa.Column("candles_used_average", sa.Float(), nullable=True),
        sa.Column("realized_pnl", sa.Numeric(24, 10), nullable=True),
        sa.Column("unrealized_pnl", sa.Numeric(24, 10), nullable=True),
        sa.Column("total_pnl", sa.Numeric(24, 10), nullable=True),
        sa.Column("return_pct", sa.Numeric(24, 10), nullable=True),
        sa.Column("data_quality", sa.String(length=32), nullable=False),
        sa.Column("unavailable_reason", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["runner_session_id"], ["runner_sessions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("runner_session_id", name="uq_runner_session_metrics_runner_session_id"),
    )
    op.create_index(
        "ix_runner_session_metrics_runner_session_id",
        "runner_session_metrics",
        ["runner_session_id"],
        unique=False,
    )
    op.create_index(
        "ix_runner_session_metrics_created_at",
        "runner_session_metrics",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_runner_session_metrics_data_quality",
        "runner_session_metrics",
        ["data_quality"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_runner_session_metrics_data_quality", table_name="runner_session_metrics")
    op.drop_index("ix_runner_session_metrics_created_at", table_name="runner_session_metrics")
    op.drop_index("ix_runner_session_metrics_runner_session_id", table_name="runner_session_metrics")
    op.drop_table("runner_session_metrics")
