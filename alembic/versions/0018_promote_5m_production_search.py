"""Allow the 5m trade profile to produce executable approvals.

Revision ID: 0018_promote_5m_production_search
Revises: 0017_parallel_trade_profiles
"""

from alembic import op


revision = "0018_promote_5m_production_search"
down_revision = "0017_parallel_trade_profiles"
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
        "(trade_profile_id = 'trade-5m-v1' AND primary_timeframe = '5m' "
        "AND profile_mode IN ('SHADOW_SEARCH', 'PRODUCTION_SEARCH'))",
    )


def downgrade() -> None:
    op.execute(
        "UPDATE online_pipeline_runs SET profile_mode = 'SHADOW_SEARCH' "
        "WHERE trade_profile_id = 'trade-5m-v1' AND profile_mode = 'PRODUCTION_SEARCH'"
    )
    op.execute(
        "UPDATE online_pipeline_results SET profile_mode = 'SHADOW_SEARCH' "
        "WHERE trade_profile_id = 'trade-5m-v1' AND profile_mode = 'PRODUCTION_SEARCH'"
    )
    op.drop_constraint(
        "ck_online_pipeline_trade_profile", "online_pipeline_runs", type_="check"
    )
    op.create_check_constraint(
        "ck_online_pipeline_trade_profile",
        "online_pipeline_runs",
        "(trade_profile_id = 'trade-15m-v1' AND primary_timeframe = '15m' "
        "AND profile_mode = 'PRODUCTION_SEARCH') OR "
        "(trade_profile_id = 'trade-5m-v1' AND primary_timeframe = '5m' "
        "AND profile_mode = 'SHADOW_SEARCH')",
    )
