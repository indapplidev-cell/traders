"""Persist atomic trading-universe activation and canary universe lineage.

Revision ID: 0015_trading_universe_activation
Revises: 0014_paper_canary_selection_policy
"""

from alembic import op
import sqlalchemy as sa


revision = "0015_trading_universe_activation"
down_revision = "0014_paper_canary_selection_policy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "paper_first_canary_sessions",
        sa.Column("universe_version_id", sa.String(64), nullable=True),
    )
    op.execute(
        "UPDATE paper_first_canary_sessions SET universe_version_id = 'trading-universe-v1' "
        "WHERE universe_version_id IS NULL"
    )
    op.alter_column("paper_first_canary_sessions", "universe_version_id", nullable=False)
    op.create_check_constraint(
        "ck_paper_first_canary_universe_version",
        "paper_first_canary_sessions",
        "universe_version_id IN ('trading-universe-v1','trading-universe-v2')",
    )
    op.create_table(
        "trading_universe_runtime_state",
        sa.Column("environment", sa.String(32), primary_key=True),
        sa.Column("active_version_id", sa.String(64), nullable=False),
        sa.Column("previous_version_id", sa.String(64), nullable=True),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activation_reason", sa.String(80), nullable=False),
        sa.Column("runtime_revision", sa.String(64), nullable=False),
        sa.CheckConstraint("environment = 'PRODUCTION'", name="ck_trading_universe_runtime_environment"),
        sa.CheckConstraint(
            "active_version_id IN ('trading-universe-v1','trading-universe-v2')",
            name="ck_trading_universe_runtime_active_version",
        ),
        sa.CheckConstraint(
            "previous_version_id IS NULL OR previous_version_id IN ('trading-universe-v1','trading-universe-v2')",
            name="ck_trading_universe_runtime_previous_version",
        ),
        sa.CheckConstraint("generation >= 1", name="ck_trading_universe_runtime_generation"),
    )
    op.execute(
        "INSERT INTO trading_universe_runtime_state "
        "(environment, active_version_id, previous_version_id, generation, activated_at, activation_reason, runtime_revision) "
        "VALUES ('PRODUCTION','trading-universe-v1',NULL,1,now(),'INITIAL_V1_BASELINE','0015')"
    )


def downgrade() -> None:
    op.drop_table("trading_universe_runtime_state")
    op.drop_constraint(
        "ck_paper_first_canary_universe_version",
        "paper_first_canary_sessions",
        type_="check",
    )
    op.drop_column("paper_first_canary_sessions", "universe_version_id")
