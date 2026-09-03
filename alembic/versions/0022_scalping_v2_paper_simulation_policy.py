"""Seed the isolated Scalping v2 PAPER fill simulation policy.

Revision ID: 0022_scalping_v2_paper_simulation_policy
Revises: 0021_independent_scalping_profile_v2
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone


revision = "0022_scalping_v2_paper_simulation_policy"
down_revision = "0021_independent_scalping_profile_v2"
branch_labels = None
depends_on = None


SCALPING_V2_POLICY_ID = "simulation:scalping-v2:foundation:v1"
SCALPING_V2_APPROVAL_CONFIGURATION = (
    "paper:approval-config:v1:"
    "786f1844ab428829064402a0cb84bda7c2df7b9062fdb31c0504430f1260df5d"
)


def upgrade() -> None:
    policy = sa.table(
        "paper_simulation_policies",
        sa.column("policy_id", sa.String),
        sa.column("policy_version", sa.Integer),
        sa.column("status", sa.String),
        sa.column("price_source", sa.String),
        sa.column("timeframe", sa.String),
        sa.column("latency_candles", sa.Integer),
        sa.column("slippage_bps", sa.Numeric),
        sa.column("fee_bps", sa.Numeric),
        sa.column("partial_fill_enabled", sa.Boolean),
        sa.column("future_data_allowed", sa.Boolean),
        sa.column("intrabar_conflict_policy", sa.String),
        sa.column("configuration_fingerprint", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("retired_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(policy, [{
        "policy_id": SCALPING_V2_POLICY_ID,
        "policy_version": 1,
        "status": "ACTIVE",
        "price_source": "NEXT_ELIGIBLE_CLOSED_1M_OPEN",
        "timeframe": "1m",
        "latency_candles": 1,
        "slippage_bps": 2,
        "fee_bps": 10,
        "partial_fill_enabled": False,
        "future_data_allowed": False,
        "intrabar_conflict_policy": "STOP_FIRST_CONSERVATIVE",
        "configuration_fingerprint": SCALPING_V2_APPROVAL_CONFIGURATION,
        "created_at": datetime.now(timezone.utc),
        "retired_at": None,
    }])


def downgrade() -> None:
    raise RuntimeError("0022 Scalping v2 PAPER execution policy is forward-only")
