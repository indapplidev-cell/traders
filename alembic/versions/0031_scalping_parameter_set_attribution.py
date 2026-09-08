"""Persist immutable Scalping v2 parameter-set attribution.

Revision ID: 0031_scalping_parameter_sets
Revises: 0030_paper_recovery_close
"""

import sqlalchemy as sa
from alembic import op


revision = "0031_scalping_parameter_sets"
down_revision = "0030_paper_recovery_close"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for name, column in (
        ("parameter_set_id", sa.String(128)),
        ("parameter_set_label", sa.String(160)),
        ("parameter_set_version", sa.String(128)),
        ("resolved_config_hash", sa.String(64)),
        ("activation_cycle_boundary_ms", sa.BigInteger()),
        ("activation_revision", sa.String(128)),
    ):
        op.add_column("scalping_opportunities", sa.Column(name, column, nullable=True))
    op.create_index(
        "ix_scalping_opportunity_parameter_set",
        "scalping_opportunities",
        ["parameter_set_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_scalping_opportunity_parameter_set",
        table_name="scalping_opportunities",
    )
    for name in (
        "activation_revision", "activation_cycle_boundary_ms",
        "resolved_config_hash", "parameter_set_version",
        "parameter_set_label", "parameter_set_id",
    ):
        op.drop_column("scalping_opportunities", name)
