"""Persist Scalping v2 stale-position SHADOW lifecycle diagnostics.

Revision ID: 0029_stale_position_shadow
Revises: 0028_scalping_profitability_grants
"""

from alembic import op
import sqlalchemy as sa


revision = "0029_stale_position_shadow"
down_revision = "0028_scalping_profitability_grants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scalping_stale_position_shadow_diagnostics",
        sa.Column("position_id", sa.String(128), nullable=False),
        sa.Column("evaluation_closed_until_ms", sa.BigInteger(), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("policy_version", sa.String(64), nullable=False),
        sa.Column("config_hash", sa.String(64), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_price", sa.Numeric(38, 18), nullable=False),
        sa.Column("holding_seconds", sa.BigInteger(), nullable=False),
        sa.Column("soft_timeout_reached", sa.Boolean(), nullable=False),
        sa.Column("hard_timeout_reached", sa.Boolean(), nullable=False),
        sa.Column("target_progress", sa.Numeric(20, 10), nullable=False),
        sa.Column("mfe_bps", sa.Numeric(20, 10), nullable=False),
        sa.Column("mae_bps", sa.Numeric(20, 10), nullable=False),
        sa.Column("current_gross_pnl", sa.Numeric(38, 18), nullable=False),
        sa.Column("estimated_net_exit_pnl", sa.Numeric(38, 18), nullable=False),
        sa.Column("remaining_target_distance", sa.Numeric(38, 18), nullable=False),
        sa.Column("remaining_ev_r", sa.Numeric(20, 10), nullable=True),
        sa.Column("setup_valid", sa.Boolean(), nullable=True),
        sa.Column("momentum_valid", sa.Boolean(), nullable=True),
        sa.Column("entry_fee_incurred", sa.Numeric(38, 18), nullable=False),
        sa.Column("expected_exit_commission", sa.Numeric(38, 18), nullable=False),
        sa.Column("spread_cost", sa.Numeric(38, 18), nullable=False),
        sa.Column("slippage_cost", sa.Numeric(38, 18), nullable=False),
        sa.Column("adverse_exit_reserve", sa.Numeric(38, 18), nullable=False),
        sa.Column("net_break_even_price", sa.Numeric(38, 18), nullable=False),
        sa.Column("break_even_activation_reason", sa.String(80), nullable=True),
        sa.Column("extension_count", sa.Integer(), nullable=False),
        sa.Column("shadow_decision", sa.String(48), nullable=False),
        sa.Column("decision_reason", sa.String(80), nullable=True),
        sa.Column("shadow_exit_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("shadow_exit_price", sa.Numeric(38, 18), nullable=True),
        sa.Column("shadow_exit_reason", sa.String(80), nullable=True),
        sa.Column("shadow_gross_pnl", sa.Numeric(38, 18), nullable=True),
        sa.Column("shadow_fees", sa.Numeric(38, 18), nullable=True),
        sa.Column("shadow_net_pnl", sa.Numeric(38, 18), nullable=True),
        sa.Column("position_capacity_seconds_consumed", sa.BigInteger(), nullable=False),
        sa.Column("later_rejected_candidates", sa.Integer(), nullable=True),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("mode = 'SHADOW'", name="ck_stale_shadow_mode"),
        sa.CheckConstraint("holding_seconds >= 0", name="ck_stale_shadow_holding"),
        sa.CheckConstraint("extension_count >= 0", name="ck_stale_shadow_extensions"),
        sa.CheckConstraint(
            "shadow_exit_reason IS NULL OR shadow_exit_time IS NOT NULL",
            name="ck_stale_shadow_exit_complete",
        ),
        sa.ForeignKeyConstraint(
            ["position_id"], ["paper_positions.position_id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("position_id", "evaluation_closed_until_ms"),
    )
    op.create_index(
        "ix_stale_shadow_position_evaluation",
        "scalping_stale_position_shadow_diagnostics",
        ["position_id", "evaluation_closed_until_ms"],
    )
    op.execute(
        """
        DO $grants$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'traders_paper_runtime') THEN
                GRANT SELECT, INSERT, UPDATE ON TABLE
                    scalping_stale_position_shadow_diagnostics TO traders_paper_runtime;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'traders_readonly_api') THEN
                GRANT SELECT ON TABLE scalping_stale_position_shadow_diagnostics
                    TO traders_readonly_api;
            END IF;
        END
        $grants$;
        """
    )


def downgrade() -> None:
    raise RuntimeError("0029 stale-position SHADOW diagnostics are forward-only")
