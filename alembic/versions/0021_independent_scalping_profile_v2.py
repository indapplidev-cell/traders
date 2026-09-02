"""Add the independent versioned Scalping v2 persistence identity.

Revision ID: 0021_independent_scalping_profile_v2
Revises: 0020_paper_plan_execution_outcomes
"""

from alembic import op


revision = "0021_independent_scalping_profile_v2"
down_revision = "0020_paper_plan_execution_outcomes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_online_pipeline_trade_profile", "online_pipeline_runs", type_="check"
    )
    op.create_check_constraint(
        "ck_online_pipeline_trade_profile",
        "online_pipeline_runs",
        "(trade_profile_id = 'trade-15m-v1' AND primary_timeframe = '15m' "
        "AND profile_mode = 'PRODUCTION_SEARCH') OR "
        "(trade_profile_id IN ('trade-5m-v1', 'trade-5m-v2') "
        "AND primary_timeframe = '5m' "
        "AND profile_mode IN ('SHADOW_SEARCH', 'PRODUCTION_SEARCH'))",
    )


def downgrade() -> None:
    raise RuntimeError("0021 independent Scalping identity is forward-only")
