"""add runner sessions and runtime tick audit tables"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0005_runner_audit"
down_revision = "0004_strategy_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runner_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("strategy_name", sa.String(length=64), nullable=False),
        sa.Column("strategy_version", sa.String(length=32), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("interval", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ticks_requested", sa.Integer(), nullable=False),
        sa.Column("ticks_completed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_runner_sessions_created_at", "runner_sessions", ["created_at"], unique=False)
    op.create_index("ix_runner_sessions_status", "runner_sessions", ["status"], unique=False)
    op.create_index("ix_runner_sessions_strategy_name", "runner_sessions", ["strategy_name"], unique=False)
    op.create_index("ix_runner_sessions_symbol", "runner_sessions", ["symbol"], unique=False)

    op.create_table(
        "runtime_ticks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("runner_session_id", sa.Integer(), nullable=False),
        sa.Column("tick_number", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("interval", sa.String(length=16), nullable=False),
        sa.Column("strategy_action", sa.String(length=16), nullable=False),
        sa.Column("final_action", sa.String(length=16), nullable=False),
        sa.Column("risk_approved", sa.Boolean(), nullable=False),
        sa.Column("risk_reason", sa.String(length=512), nullable=True),
        sa.Column("execution_action", sa.String(length=16), nullable=False),
        sa.Column("journal_id", sa.Integer(), nullable=True),
        sa.Column("market_regime", sa.String(length=16), nullable=True),
        sa.Column("candles_used", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["runner_session_id"], ["runner_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("runner_session_id", "tick_number", name="uq_runtime_ticks_session_tick"),
    )
    op.create_index("ix_runtime_ticks_created_at", "runtime_ticks", ["created_at"], unique=False)
    op.create_index("ix_runtime_ticks_runner_session_id", "runtime_ticks", ["runner_session_id"], unique=False)
    op.create_index("ix_runtime_ticks_symbol", "runtime_ticks", ["symbol"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_runtime_ticks_symbol", table_name="runtime_ticks")
    op.drop_index("ix_runtime_ticks_runner_session_id", table_name="runtime_ticks")
    op.drop_index("ix_runtime_ticks_created_at", table_name="runtime_ticks")
    op.drop_table("runtime_ticks")

    op.drop_index("ix_runner_sessions_symbol", table_name="runner_sessions")
    op.drop_index("ix_runner_sessions_strategy_name", table_name="runner_sessions")
    op.drop_index("ix_runner_sessions_status", table_name="runner_sessions")
    op.drop_index("ix_runner_sessions_created_at", table_name="runner_sessions")
    op.drop_table("runner_sessions")
