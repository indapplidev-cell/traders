"""Durable causal opportunity and outcome diagnostic integration.

Revision ID: 0027_scalping_profitability_integration
Revises: 0026_scalping_1m_entry_refinement
"""

from alembic import op
import sqlalchemy as sa


revision = "0027_scalping_profitability_integration"
down_revision = "0026_scalping_1m_entry_refinement"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scalping_opportunities",
        sa.Column("causal_opportunity_id", sa.String(128), primary_key=True),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("causal_parent_id", sa.String(128)),
        sa.Column("reset_reason", sa.String(160)),
        sa.Column("reset_evidence", sa.String(512)),
        sa.Column("paper_plan_id", sa.String(512)),
        sa.Column("command_id", sa.String(128), unique=True),
        sa.Column("position_id", sa.String(128), unique=True),
        sa.Column("observation_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("state IN ('RESET_AVAILABLE','RESERVED','COMMAND_CREATED','EXECUTED')", name="ck_scalping_opportunity_state"),
        sa.CheckConstraint("length(trim(causal_opportunity_id)) BETWEEN 1 AND 128", name="ck_scalping_opportunity_id"),
    )
    op.create_index("ix_scalping_opportunity_state", "scalping_opportunities", ["state"])
    op.create_table(
        "scalping_outcome_diagnostics",
        sa.Column("position_id", sa.String(128), primary_key=True),
        sa.Column("mae", sa.Numeric(38, 18), nullable=False),
        sa.Column("mfe", sa.Numeric(38, 18), nullable=False),
        sa.Column("time_to_mae_ms", sa.BigInteger(), nullable=False),
        sa.Column("time_to_mfe_ms", sa.BigInteger(), nullable=False),
        sa.Column("planned_stop_distance", sa.Numeric(38, 18), nullable=False),
        sa.Column("actual_stop_slippage", sa.Numeric(38, 18)),
        sa.Column("planned_target_distance", sa.Numeric(38, 18), nullable=False),
        sa.Column("target_reached_after_stop", sa.Boolean(), nullable=False),
        sa.Column("max_favorable_before_stop", sa.Numeric(38, 18), nullable=False),
        sa.Column("max_adverse_before_target", sa.Numeric(38, 18), nullable=False),
        sa.Column("holding_time_ms", sa.BigInteger(), nullable=False),
        sa.Column("diagnostic_version", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    raise RuntimeError("0027 Scalping profitability integration is forward-only")
