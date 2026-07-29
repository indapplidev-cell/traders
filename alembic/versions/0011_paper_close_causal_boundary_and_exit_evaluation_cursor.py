"""Add the dedicated PAPER exit-evaluation cursor.

Revision ID: 0011_paper_close_causal_boundary_and_exit_evaluation_cursor
Revises: 0010_paper_final_approval_and_order_transition_event_vocabulary
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_paper_close_causal_boundary_and_exit_evaluation_cursor"
down_revision = "0010_paper_final_approval_and_order_transition_event_vocabulary"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_exit_evaluation_cursors",
        sa.Column("cursor_id", sa.String(128), nullable=False),
        sa.Column("contract_version", sa.String(128), nullable=False),
        sa.Column("position_id", sa.String(128), nullable=False),
        sa.Column("mode", sa.String(8), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("last_evaluated_closed_until_ms", sa.BigInteger(), nullable=False),
        sa.Column("position_opened_closed_until_ms", sa.BigInteger(), nullable=False),
        sa.Column("evaluation_policy_id", sa.String(128), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(128), nullable=False),
        sa.Column("causation_id", sa.String(128), nullable=False),
        sa.Column("last_advance_idempotency_key", sa.String(128)),
        sa.Column("last_advance_from_closed_until_ms", sa.BigInteger()),
        sa.Column("last_advance_to_closed_until_ms", sa.BigInteger()),
        sa.Column("last_advance_expected_version", sa.BigInteger()),
        sa.Column("last_window_identity", sa.String(128)),
        sa.ForeignKeyConstraint(
            ["position_id"],
            ["paper_positions.position_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("cursor_id"),
        sa.UniqueConstraint(
            "position_id", name="uq_paper_exit_evaluation_cursor_position"
        ),
        sa.CheckConstraint("mode = 'PAPER'", name="ck_paper_exit_cursor_mode"),
        sa.CheckConstraint(
            "length(trim(cursor_id)) BETWEEN 1 AND 128 AND "
            "length(trim(contract_version)) BETWEEN 1 AND 128 AND "
            "length(trim(symbol)) BETWEEN 2 AND 32 AND "
            "length(trim(evaluation_policy_id)) BETWEEN 1 AND 128 AND "
            "length(trim(correlation_id)) BETWEEN 1 AND 128 AND "
            "length(trim(causation_id)) BETWEEN 1 AND 128",
            name="ck_paper_exit_cursor_identities",
        ),
        sa.CheckConstraint(
            "last_evaluated_closed_until_ms >= position_opened_closed_until_ms "
            "AND position_opened_closed_until_ms >= 0 "
            "AND mod(last_evaluated_closed_until_ms, 60000) = 0 "
            "AND mod(position_opened_closed_until_ms, 60000) = 0",
            name="ck_paper_exit_cursor_boundaries",
        ),
        sa.CheckConstraint("version >= 0", name="ck_paper_exit_cursor_version"),
        sa.CheckConstraint(
            "updated_at >= created_at", name="ck_paper_exit_cursor_timestamps"
        ),
        sa.CheckConstraint(
            "(last_advance_idempotency_key IS NULL "
            "AND last_advance_from_closed_until_ms IS NULL "
            "AND last_advance_to_closed_until_ms IS NULL "
            "AND last_advance_expected_version IS NULL "
            "AND last_window_identity IS NULL) OR "
            "(last_advance_idempotency_key IS NOT NULL "
            "AND length(trim(last_advance_idempotency_key)) BETWEEN 1 AND 128 "
            "AND last_advance_from_closed_until_ms IS NOT NULL "
            "AND last_advance_to_closed_until_ms IS NOT NULL "
            "AND last_advance_expected_version IS NOT NULL "
            "AND last_window_identity IS NOT NULL "
            "AND length(trim(last_window_identity)) BETWEEN 1 AND 128 "
            "AND last_advance_from_closed_until_ms >= 0 "
            "AND last_advance_to_closed_until_ms > "
            "last_advance_from_closed_until_ms "
            "AND last_advance_to_closed_until_ms = "
            "last_evaluated_closed_until_ms "
            "AND last_advance_expected_version + 1 = version)",
            name="ck_paper_exit_cursor_last_advance",
        ),
    )
    op.create_index(
        "ix_paper_exit_evaluation_cursors_updated_at",
        "paper_exit_evaluation_cursors",
        ["updated_at", "position_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_paper_exit_evaluation_cursors_updated_at",
        table_name="paper_exit_evaluation_cursors",
    )
    op.drop_table("paper_exit_evaluation_cursors")
