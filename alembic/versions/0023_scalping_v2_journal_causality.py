"""Reconcile Scalping v2 fill-to-position journal causality.

Revision ID: 0023_scalping_v2_journal_causality
Revises: 0022_scalping_v2_paper_simulation_policy
"""

from alembic import op


revision = "0023_scalping_v2_journal_causality"
down_revision = "0022_scalping_v2_paper_simulation_policy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE paper_journal_entries AS journal
        SET causation_id = journal.fill_id
        FROM paper_execution_commands AS command,
             online_pipeline_runs AS pipeline
        WHERE journal.command_id = command.command_id
          AND command.pipeline_run_id = pipeline.run_id
          AND pipeline.trade_profile_id = 'trade-5m-v2'
          AND journal.event_type IN ('PAPER_POSITION_OPENED', 'PAPER_POSITION_CLOSED')
          AND journal.fill_id IS NOT NULL
          AND journal.causation_id <> journal.fill_id
        """
    )


def downgrade() -> None:
    raise RuntimeError("0023 Scalping v2 journal causality repair is forward-only")
