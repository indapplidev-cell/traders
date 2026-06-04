"""0007_backtest_metrics

Revision ID: 0007_backtest_metrics
Revises: 0006_runner_metrics
Create Date: 2026-06-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0007_backtest_metrics"
down_revision = "0006_runner_metrics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create backtest_sessions and backtest_session_metrics tables."""
    # Create backtest_sessions table
    op.create_table(
        "backtest_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("strategy_name", sa.String(64), nullable=False),
        sa.Column("strategy_version", sa.String(32), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("interval", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("candles_requested", sa.Integer(), nullable=True),
        sa.Column("candles_used", sa.Integer(), nullable=True),
        sa.Column("initial_cash", sa.Numeric(24, 10), nullable=True),
        sa.Column("final_equity", sa.Numeric(24, 10), nullable=True),
        sa.Column("last_error", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indices for backtest_sessions
    op.create_index("ix_backtest_sessions_strategy_name", "backtest_sessions", ["strategy_name"])
    op.create_index("ix_backtest_sessions_symbol", "backtest_sessions", ["symbol"])
    op.create_index("ix_backtest_sessions_status", "backtest_sessions", ["status"])
    op.create_index("ix_backtest_sessions_created_at", "backtest_sessions", ["created_at"])

    # Create backtest_session_metrics table
    op.create_table(
        "backtest_session_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("backtest_session_id", sa.Integer(), nullable=False),
        sa.Column("candles_used", sa.Integer(), nullable=True),
        sa.Column("strategy_buy_count", sa.Integer(), nullable=True),
        sa.Column("strategy_sell_count", sa.Integer(), nullable=True),
        sa.Column("strategy_hold_count", sa.Integer(), nullable=True),
        sa.Column("executed_buy_count", sa.Integer(), nullable=True),
        sa.Column("executed_sell_count", sa.Integer(), nullable=True),
        sa.Column("skipped_count", sa.Integer(), nullable=True),
        sa.Column("total_trades", sa.Integer(), nullable=True),
        sa.Column("winning_trades", sa.Integer(), nullable=True),
        sa.Column("losing_trades", sa.Integer(), nullable=True),
        sa.Column("win_rate", sa.Numeric(6, 4), nullable=True),
        sa.Column("initial_cash", sa.Numeric(24, 10), nullable=True),
        sa.Column("final_equity", sa.Numeric(24, 10), nullable=True),
        sa.Column("realized_pnl", sa.Numeric(24, 10), nullable=True),
        sa.Column("unrealized_pnl", sa.Numeric(24, 10), nullable=True),
        sa.Column("total_pnl", sa.Numeric(24, 10), nullable=True),
        sa.Column("return_pct", sa.Numeric(24, 10), nullable=True),
        sa.Column("max_drawdown", sa.Numeric(24, 10), nullable=True),
        sa.Column("average_confidence", sa.Numeric(24, 10), nullable=True),
        sa.Column("min_confidence", sa.Numeric(24, 10), nullable=True),
        sa.Column("max_confidence", sa.Numeric(24, 10), nullable=True),
        sa.Column("data_quality", sa.String(32), nullable=False),
        sa.Column("unavailable_reason", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["backtest_session_id"], ["backtest_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("backtest_session_id", name="uq_backtest_session_metrics_backtest_session_id"),
    )

    # Create indices for backtest_session_metrics
    op.create_index("ix_backtest_session_metrics_backtest_session_id", "backtest_session_metrics", ["backtest_session_id"])
    op.create_index("ix_backtest_session_metrics_created_at", "backtest_session_metrics", ["created_at"])
    op.create_index("ix_backtest_session_metrics_data_quality", "backtest_session_metrics", ["data_quality"])


def downgrade() -> None:
    """Drop backtest_session_metrics and backtest_sessions tables."""
    # Drop indices for backtest_session_metrics
    op.drop_index("ix_backtest_session_metrics_data_quality", table_name="backtest_session_metrics")
    op.drop_index("ix_backtest_session_metrics_created_at", table_name="backtest_session_metrics")
    op.drop_index("ix_backtest_session_metrics_backtest_session_id", table_name="backtest_session_metrics")

    # Drop backtest_session_metrics table
    op.drop_table("backtest_session_metrics")

    # Drop indices for backtest_sessions
    op.drop_index("ix_backtest_sessions_created_at", table_name="backtest_sessions")
    op.drop_index("ix_backtest_sessions_status", table_name="backtest_sessions")
    op.drop_index("ix_backtest_sessions_symbol", table_name="backtest_sessions")
    op.drop_index("ix_backtest_sessions_strategy_name", table_name="backtest_sessions")

    # Drop backtest_sessions table
    op.drop_table("backtest_sessions")
