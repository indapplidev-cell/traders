"""Persist the immutable PAPER account/session opening balance.

Revision ID: 0012_paper_account_baseline
Revises: 0011_paper_close_causal_boundary_and_exit_evaluation_cursor
"""

from alembic import op
import sqlalchemy as sa


revision = "0012_paper_account_baseline"
down_revision = "0011_paper_close_causal_boundary_and_exit_evaluation_cursor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_account_baselines",
        sa.Column("baseline_id", sa.String(128), nullable=False),
        sa.Column("account_id", sa.String(128), nullable=False),
        sa.Column("accounting_session_id", sa.String(128), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("initial_balance", sa.Numeric(38, 18), nullable=False),
        sa.Column("initialized_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("semantic_version", sa.String(128), nullable=False),
        sa.PrimaryKeyConstraint("baseline_id", name="pk_paper_account_baselines"),
        sa.UniqueConstraint(
            "account_id",
            "accounting_session_id",
            name="uq_paper_account_baselines_account_session",
        ),
        sa.CheckConstraint(
            "length(trim(baseline_id)) BETWEEN 1 AND 128 AND "
            "length(trim(account_id)) BETWEEN 1 AND 128 AND "
            "length(trim(accounting_session_id)) BETWEEN 1 AND 128 AND "
            "length(trim(semantic_version)) BETWEEN 1 AND 128",
            name="ck_paper_account_baseline_identities",
        ),
        sa.CheckConstraint(
            "currency = 'USDT'", name="ck_paper_account_baseline_currency"
        ),
        sa.CheckConstraint(
            "initial_balance NOT IN (CAST('NaN' AS NUMERIC), "
            "CAST('Infinity' AS NUMERIC), CAST('-Infinity' AS NUMERIC)) "
            "AND initial_balance > 0",
            name="ck_paper_account_baseline_initial_balance",
        ),
    )


def downgrade() -> None:
    # Destructive by design: operators must use forward remediation or PITR.
    op.drop_table("paper_account_baselines")
