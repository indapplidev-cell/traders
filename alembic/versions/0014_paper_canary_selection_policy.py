"""Bind each PAPER canary to an immutable approval-selection policy.

Revision ID: 0014_paper_canary_selection_policy
Revises: 0013_paper_first_canary_correlation
"""

from alembic import op
import sqlalchemy as sa


revision = "0014_paper_canary_selection_policy"
down_revision = "0013_paper_first_canary_correlation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing canaries retain their original exactly-one behavior. New rows
    # explicitly supplied by the repository bind the deterministic v1 policy.
    op.add_column(
        "paper_first_canary_sessions",
        sa.Column(
            "selection_policy_version", sa.String(64), nullable=False,
            server_default="exactly-one-eligible-v1",
        ),
    )
    op.create_check_constraint(
        "ck_paper_first_canary_selection_policy",
        "paper_first_canary_sessions",
        "selection_policy_version IN ('exactly-one-eligible-v1','eligible-approval-ranking-v1')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_paper_first_canary_selection_policy",
        "paper_first_canary_sessions",
        type_="check",
    )
    op.drop_column("paper_first_canary_sessions", "selection_policy_version")
