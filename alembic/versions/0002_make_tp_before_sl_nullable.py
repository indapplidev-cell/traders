"""Make tp_before_sl nullable for ML labels.

Revision ID: 0002_make_tp_before_sl_nullable
Revises: 0001_ml_foundation
Create Date: 2026-06-08
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_make_tp_before_sl_nullable"
down_revision = "0001_ml_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("ml_labels", "tp_before_sl", existing_type=sa.Boolean(), nullable=True)


def downgrade() -> None:
    op.alter_column("ml_labels", "tp_before_sl", existing_type=sa.Boolean(), nullable=False)
