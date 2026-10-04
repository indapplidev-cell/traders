"""Allow two independent continuous PAPER lifecycles.

Revision ID: 0037_continuous_two_lifecycle_slots
Revises: 0036_empirical_requalification_authority
"""

from alembic import op
import sqlalchemy as sa


revision = "0037_continuous_two_lifecycle_slots"
down_revision = "0036_empirical_requalification_authority"
branch_labels = None
depends_on = None


_ACTIVE = "state NOT IN ('COMPLETED','STOPPED','FAILED_SAFE')"


def upgrade() -> None:
    op.add_column(
        "paper_first_canary_sessions",
        sa.Column("lifecycle_slot", sa.SmallInteger(), nullable=True),
    )
    op.create_check_constraint(
        "ck_paper_canary_lifecycle_slot",
        "paper_first_canary_sessions",
        "lifecycle_slot IS NULL OR lifecycle_slot BETWEEN 1 AND 2",
    )
    # The previous schema allowed at most one active row, so this update is
    # deterministic and preserves every historical command/position row.
    op.execute(sa.text(
        "UPDATE paper_first_canary_sessions SET lifecycle_slot = 1 "
        f"WHERE {_ACTIVE}"
    ))
    op.create_check_constraint(
        "ck_paper_canary_active_lifecycle_slot",
        "paper_first_canary_sessions",
        f"NOT ({_ACTIVE}) OR lifecycle_slot IS NOT NULL",
    )
    op.drop_index(
        "uq_paper_first_canary_one_active_environment",
        table_name="paper_first_canary_sessions",
    )
    op.create_index(
        "uq_paper_canary_active_lifecycle_slot",
        "paper_first_canary_sessions",
        ["environment", "lifecycle_slot"],
        unique=True,
        postgresql_where=sa.text(_ACTIVE),
    )


def downgrade() -> None:
    # A safe downgrade is possible only when no more than one lifecycle is
    # active. Refuse otherwise instead of deleting or rewriting trading data.
    bind = op.get_bind()
    active = bind.execute(sa.text(
        "SELECT count(*) FROM paper_first_canary_sessions "
        f"WHERE {_ACTIVE}"
    )).scalar_one()
    if active > 1:
        raise RuntimeError("DOWNGRADE_REQUIRES_AT_MOST_ONE_ACTIVE_LIFECYCLE")
    op.drop_index(
        "uq_paper_canary_active_lifecycle_slot",
        table_name="paper_first_canary_sessions",
    )
    op.create_index(
        "uq_paper_first_canary_one_active_environment",
        "paper_first_canary_sessions",
        ["environment"],
        unique=True,
        postgresql_where=sa.text(_ACTIVE),
    )
    op.drop_constraint(
        "ck_paper_canary_active_lifecycle_slot",
        "paper_first_canary_sessions",
        type_="check",
    )
    op.drop_constraint(
        "ck_paper_canary_lifecycle_slot",
        "paper_first_canary_sessions",
        type_="check",
    )
    op.drop_column("paper_first_canary_sessions", "lifecycle_slot")
