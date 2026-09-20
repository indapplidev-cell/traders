"""Allow the versioned twenty-symbol Scalping universe.

Revision ID: 0034_scalping_universe_v3
Revises: 0033_net_pnl_protection
"""

from alembic import op
import sqlalchemy as sa


revision = "0034_scalping_universe_v3"
down_revision = "0033_net_pnl_protection"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_trading_universe_runtime_active_version",
        "trading_universe_runtime_state",
        type_="check",
    )
    op.drop_constraint(
        "ck_trading_universe_runtime_previous_version",
        "trading_universe_runtime_state",
        type_="check",
    )
    op.create_check_constraint(
        "ck_trading_universe_runtime_active_version",
        "trading_universe_runtime_state",
        "active_version_id IN ('trading-universe-v1','trading-universe-v2','trading-universe-v3')",
    )
    op.create_check_constraint(
        "ck_trading_universe_runtime_previous_version",
        "trading_universe_runtime_state",
        "previous_version_id IS NULL OR previous_version_id IN ('trading-universe-v1','trading-universe-v2','trading-universe-v3')",
    )
    op.create_table(
        "trading_universe_symbol_preflight",
        sa.Column("environment", sa.String(32), nullable=False),
        sa.Column("universe_version_id", sa.String(64), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("configured", sa.Boolean(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("reason", sa.String(64), nullable=True),
        sa.Column("one_minute_fresh", sa.Boolean(), nullable=False),
        sa.Column("five_minute_fresh", sa.Boolean(), nullable=False),
        sa.Column("commission_authority", sa.String(64), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("authority_details", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("environment", "universe_version_id", "symbol", name="pk_trading_universe_symbol_preflight"),
        sa.CheckConstraint("environment = 'PRODUCTION'", name="ck_trading_universe_preflight_environment"),
        sa.CheckConstraint("status IN ('PASS','SYMBOL_FAIL_CLOSED')", name="ck_trading_universe_preflight_status"),
        sa.CheckConstraint("configured = true", name="ck_trading_universe_preflight_configured"),
        sa.CheckConstraint("active = (status = 'PASS')", name="ck_trading_universe_preflight_active_status"),
    )
    op.create_index(
        "ix_trading_universe_preflight_active",
        "trading_universe_symbol_preflight",
        ["universe_version_id", "active"],
    )


def downgrade() -> None:
    raise RuntimeError("0034 Scalping universe v3 activation is forward-only")
