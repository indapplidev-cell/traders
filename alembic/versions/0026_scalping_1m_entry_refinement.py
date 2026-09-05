"""Persist Scalping v2 1m entry-refinement causality.

Revision ID: 0026_scalping_1m_entry_refinement
Revises: 0025_paper_budget_policy
"""

from alembic import op
import sqlalchemy as sa


revision = "0026_scalping_1m_entry_refinement"
down_revision = "0025_paper_budget_policy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    table = "paper_plan_execution_outcomes"
    for column in (
        sa.Column("refinement_identity", sa.String(length=128), nullable=True),
        sa.Column("refinement_mode", sa.String(length=16), nullable=True),
        sa.Column("refinement_state", sa.String(length=32), nullable=True),
        sa.Column("refinement_reason", sa.String(length=80), nullable=True),
        sa.Column("refinement_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refinement_finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refinement_valid_from_ms", sa.BigInteger(), nullable=True),
        sa.Column("refinement_valid_until_ms", sa.BigInteger(), nullable=True),
        sa.Column("refinement_details", sa.JSON(), nullable=True),
    ):
        op.add_column(table, column)
    op.create_unique_constraint(
        "uq_plan_outcome_refinement_identity", table, ["refinement_identity"]
    )
    op.create_check_constraint(
        "ck_plan_outcome_refinement_mode", table,
        "refinement_mode IS NULL OR refinement_mode IN ('OFF','SHADOW','AUTHORITATIVE')",
    )
    op.create_check_constraint(
        "ck_plan_outcome_refinement_state", table,
        "refinement_state IS NULL OR refinement_state IN "
        "('NOT_REACHED','WAITING_FOR_1M','READY_TO_ENTER','REJECTED_1M',"
        "'EXPIRED_1M','BYPASSED','FAILED')",
    )
    op.create_check_constraint(
        "ck_plan_outcome_refinement_approval_bound", table,
        "refinement_valid_until_ms IS NULL OR "
        "refinement_valid_until_ms <= approval_valid_until_ms",
    )


def downgrade() -> None:
    raise RuntimeError("0026 Scalping entry refinement is forward-only")
