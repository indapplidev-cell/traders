"""Version the Scalping v2 PAPER ingestion policy contract.

Revision ID: 0035_scalping_v2_ingestion_policy_contract
Revises: 0034_scalping_universe_v3
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "0035_scalping_v2_ingestion_policy_contract"
down_revision = "0034_scalping_universe_v3"
branch_labels = None
depends_on = None


_POLICIES = (
    (
        "simulation:scalping-v2:foundation:v1",
        "paper:simulation-contract:v2:481bce6ffde60807a19b574038ea15eb269bf369e3c490985c8bcd9fb373b7eb",
    ),
    (
        "simulation:scalping-v2:1m-entry-refinement:v1",
        "paper:simulation-contract:v2:53ca25fa221eea985ffc67140dd496c566a3c5146458675c01c085141573d3c8",
    ),
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
    created_at = datetime.now(timezone.utc)
    op.bulk_insert(policy, [{
        "policy_id": policy_id,
        "policy_version": 2,
        "status": "ACTIVE",
        "price_source": "NEXT_ELIGIBLE_CLOSED_1M_OPEN",
        "timeframe": "1m",
        "latency_candles": 1,
        "slippage_bps": 2,
        "fee_bps": 10,
        "partial_fill_enabled": False,
        "future_data_allowed": False,
        "intrabar_conflict_policy": "STOP_FIRST_CONSERVATIVE",
        "configuration_fingerprint": fingerprint,
        "created_at": created_at,
        "retired_at": None,
    } for policy_id, fingerprint in _POLICIES])


def downgrade() -> None:
    raise RuntimeError("0035 Scalping v2 ingestion policy contract is forward-only")
