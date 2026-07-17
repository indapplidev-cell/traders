"""Create online closed-candle orchestrator run and result tables.

Revision ID: 0007_engine_orchestrator_online_pipeline
Revises: 0006_engine_market_data_sync_state
"""

from alembic import op
import sqlalchemy as sa

revision = "0007_engine_orchestrator_online_pipeline"
down_revision = "0006_engine_market_data_sync_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "online_pipeline_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(80), nullable=False),
        sa.Column("symbol", sa.String(50), nullable=False),
        sa.Column("primary_timeframe", sa.String(8), nullable=False),
        sa.Column("closed_until_ms", sa.BigInteger(), nullable=False),
        sa.Column("closed_until_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("duration_ms", sa.BigInteger()),
        sa.Column("trigger_source", sa.String(50), nullable=False),
        sa.Column("daemon_instance_id", sa.String(100), nullable=False),
        sa.Column("market_data_freshness_status", sa.String(40)),
        sa.Column("analysis_status", sa.String(60)),
        sa.Column("setup_status", sa.String(60)),
        sa.Column("strategy_status", sa.String(60)),
        sa.Column("risk_status", sa.String(60)),
        sa.Column("paper_status", sa.String(60)),
        sa.Column("final_result", sa.String(40)),
        sa.Column("final_reason", sa.Text()),
        sa.Column("error_code", sa.String(100)),
        sa.Column("error_message", sa.Text()),
        sa.Column("future_bars_used", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_trade_signal", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_executable", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("order_approved", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("execution_approved", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("position_opened", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("position_size_approved", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('PENDING','RUNNING','COMPLETED','SKIPPED_DUPLICATE_WINDOW','SKIPPED_FRESHNESS_NOT_OK','SKIPPED_NOT_ENOUGH_DATA','MODULE_ERROR','ERROR')", name="ck_online_pipeline_run_status"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", name="uq_online_pipeline_runs_run_id"),
        sa.UniqueConstraint("symbol", "primary_timeframe", "closed_until_ms", name="uq_online_pipeline_window"),
    )
    op.create_index("ix_online_pipeline_runs_status", "online_pipeline_runs", ["status"])
    op.create_index("ix_online_pipeline_runs_closed_until", "online_pipeline_runs", ["closed_until_ms"])
    op.create_table(
        "online_pipeline_results",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(80), nullable=False),
        sa.Column("symbol", sa.String(50), nullable=False),
        sa.Column("primary_timeframe", sa.String(8), nullable=False),
        sa.Column("closed_until_ms", sa.BigInteger(), nullable=False),
        sa.Column("market_data_payload_json", sa.JSON(), nullable=False),
        sa.Column("analysis_payload_json", sa.JSON(), nullable=False),
        sa.Column("setup_payload_json", sa.JSON(), nullable=False),
        sa.Column("strategy_payload_json", sa.JSON(), nullable=False),
        sa.Column("risk_payload_json", sa.JSON(), nullable=False),
        sa.Column("paper_payload_json", sa.JSON(), nullable=False),
        sa.Column("module_reasons_json", sa.JSON(), nullable=False),
        sa.Column("module_warnings_json", sa.JSON(), nullable=False),
        sa.Column("safety_counters_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["online_pipeline_runs.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", name="uq_online_pipeline_results_run_id"),
    )


def downgrade() -> None:
    op.drop_table("online_pipeline_results")
    op.drop_index("ix_online_pipeline_runs_closed_until", table_name="online_pipeline_runs")
    op.drop_index("ix_online_pipeline_runs_status", table_name="online_pipeline_runs")
    op.drop_table("online_pipeline_runs")
