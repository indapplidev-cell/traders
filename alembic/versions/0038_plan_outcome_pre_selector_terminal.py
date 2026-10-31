"""Represent terminal PAPER plans that never produced a selector candidate.

Revision ID: 0038_plan_outcome_pre_selector_terminal
Revises: 0037_continuous_two_lifecycle_slots
"""

from alembic import op
import sqlalchemy as sa


revision = "0038_plan_outcome_pre_selector_terminal"
down_revision = "0037_continuous_two_lifecycle_slots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_plan_outcome_approval", "paper_plan_execution_outcomes", type_="check"
    )
    op.drop_constraint(
        "ck_plan_outcome_candidate", "paper_plan_execution_outcomes", type_="check"
    )
    op.alter_column(
        "paper_plan_execution_outcomes", "final_approval_id",
        existing_type=sa.String(length=128), nullable=True,
    )
    op.alter_column(
        "paper_plan_execution_outcomes", "candidate_id",
        existing_type=sa.String(length=128), nullable=True,
    )
    op.create_check_constraint(
        "ck_plan_outcome_approval", "paper_plan_execution_outcomes",
        "final_approval_id IS NULL OR length(trim(final_approval_id)) BETWEEN 1 AND 128",
    )
    op.create_check_constraint(
        "ck_plan_outcome_candidate", "paper_plan_execution_outcomes",
        "candidate_id IS NULL OR length(trim(candidate_id)) BETWEEN 1 AND 128",
    )


def downgrade() -> None:
    bind = op.get_bind()
    incomplete = bind.execute(sa.text(
        "SELECT count(*) FROM paper_plan_execution_outcomes "
        "WHERE final_approval_id IS NULL OR candidate_id IS NULL"
    )).scalar_one()
    if incomplete:
        raise RuntimeError(
            "DOWNGRADE_REQUIRES_NO_PRE_SELECTOR_TERMINAL_OUTCOMES"
        )
    op.drop_constraint(
        "ck_plan_outcome_candidate", "paper_plan_execution_outcomes", type_="check"
    )
    op.drop_constraint(
        "ck_plan_outcome_approval", "paper_plan_execution_outcomes", type_="check"
    )
    op.alter_column(
        "paper_plan_execution_outcomes", "candidate_id",
        existing_type=sa.String(length=128), nullable=False,
    )
    op.alter_column(
        "paper_plan_execution_outcomes", "final_approval_id",
        existing_type=sa.String(length=128), nullable=False,
    )
    op.create_check_constraint(
        "ck_plan_outcome_candidate", "paper_plan_execution_outcomes",
        "length(trim(candidate_id)) BETWEEN 1 AND 128",
    )
    op.create_check_constraint(
        "ck_plan_outcome_approval", "paper_plan_execution_outcomes",
        "length(trim(final_approval_id)) BETWEEN 1 AND 128",
    )
