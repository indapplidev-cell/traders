"""Add first-class online trade-profile provenance.

Revision ID: 0017_parallel_trade_profiles
Revises: 0016_control_mobile_device_security
"""

from alembic import op
import sqlalchemy as sa


revision = "0017_parallel_trade_profiles"
down_revision = "0016_control_mobile_device_security"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("online_pipeline_runs", sa.Column(
        "trade_profile_id", sa.String(32), nullable=False,
        server_default=sa.text("'trade-15m-v1'"),
    ))
    op.add_column("online_pipeline_runs", sa.Column(
        "profile_mode", sa.String(32), nullable=False,
        server_default=sa.text("'PRODUCTION_SEARCH'"),
    ))
    op.add_column("online_pipeline_results", sa.Column(
        "trade_profile_id", sa.String(32), nullable=False,
        server_default=sa.text("'trade-15m-v1'"),
    ))
    op.add_column("online_pipeline_results", sa.Column(
        "profile_mode", sa.String(32), nullable=False,
        server_default=sa.text("'PRODUCTION_SEARCH'"),
    ))
    op.drop_constraint("uq_online_pipeline_window", "online_pipeline_runs", type_="unique")
    op.create_unique_constraint(
        "uq_online_pipeline_profile_window", "online_pipeline_runs",
        ["trade_profile_id", "symbol", "primary_timeframe", "closed_until_ms"],
    )
    op.create_index(
        "ix_online_pipeline_profile_boundary", "online_pipeline_runs",
        ["trade_profile_id", "closed_until_ms"],
    )
    op.create_check_constraint(
        "ck_online_pipeline_trade_profile", "online_pipeline_runs",
        "(trade_profile_id = 'trade-15m-v1' AND primary_timeframe = '15m' AND profile_mode = 'PRODUCTION_SEARCH') OR "
        "(trade_profile_id = 'trade-5m-v1' AND primary_timeframe = '5m' AND profile_mode = 'SHADOW_SEARCH')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_online_pipeline_trade_profile", "online_pipeline_runs", type_="check")
    op.drop_index("ix_online_pipeline_profile_boundary", table_name="online_pipeline_runs")
    op.drop_constraint("uq_online_pipeline_profile_window", "online_pipeline_runs", type_="unique")
    op.create_unique_constraint(
        "uq_online_pipeline_window", "online_pipeline_runs",
        ["symbol", "primary_timeframe", "closed_until_ms"],
    )
    op.drop_column("online_pipeline_results", "profile_mode")
    op.drop_column("online_pipeline_results", "trade_profile_id")
    op.drop_column("online_pipeline_runs", "profile_mode")
    op.drop_column("online_pipeline_runs", "trade_profile_id")
