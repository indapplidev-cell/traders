"""Add opportunity fields to ML labels.

Revision ID: 0004_opportunity_labels
Revises: 0003_constraints_indexes
Create Date: 2026-06-19
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_opportunity_labels"
down_revision = "0003_constraints_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ml_labels",
        sa.Column("opportunity_label", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "ml_labels",
        sa.Column("opportunity_direction", sa.String(length=20), nullable=False, server_default="NONE"),
    )
    op.add_column(
        "ml_labels",
        sa.Column("opportunity_reason", sa.String(length=100), nullable=False, server_default="no_setup"),
    )
    op.add_column(
        "ml_labels",
        sa.Column("opportunity_score", sa.Numeric(10, 6), nullable=False, server_default="0"),
    )
    op.add_column(
        "ml_labels",
        sa.Column("setup_type", sa.String(length=100), nullable=False, server_default="no_setup"),
    )
    op.add_column(
        "ml_labels",
        sa.Column("setup_quality_score", sa.Numeric(10, 6), nullable=False, server_default="0"),
    )
    op.add_column(
        "ml_labels",
        sa.Column("setup_invalidation_distance_atr", sa.Numeric(10, 6), nullable=False, server_default="0"),
    )
    op.add_column(
        "ml_labels",
        sa.Column("setup_expected_move_atr", sa.Numeric(10, 6), nullable=False, server_default="0"),
    )
    op.add_column(
        "ml_labels",
        sa.Column("label_ambiguity_score", sa.Numeric(10, 6), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("ml_labels", "label_ambiguity_score")
    op.drop_column("ml_labels", "setup_expected_move_atr")
    op.drop_column("ml_labels", "setup_invalidation_distance_atr")
    op.drop_column("ml_labels", "setup_quality_score")
    op.drop_column("ml_labels", "setup_type")
    op.drop_column("ml_labels", "opportunity_score")
    op.drop_column("ml_labels", "opportunity_reason")
    op.drop_column("ml_labels", "opportunity_direction")
    op.drop_column("ml_labels", "opportunity_label")
