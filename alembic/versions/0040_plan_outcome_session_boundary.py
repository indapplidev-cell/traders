"""Keep reconciled plan outcomes inside their accounting-session boundary.

Revision ID: 0040_plan_outcome_session_boundary
Revises: 0039_paper_accounting_session_v2
"""

from alembic import op
import sqlalchemy as sa


revision = "0040_plan_outcome_session_boundary"
down_revision = "0039_paper_accounting_session_v2"
branch_labels = None
depends_on = None


OLD_SESSION = "TRADERS_PAPER_SESSION_01"
NEW_SESSION = "TRADERS_PAPER_SESSION_02"
MARKER = "0040_plan_outcome_session_boundary"


def upgrade() -> None:
    bind = op.get_bind()
    unsafe = bind.execute(sa.text(
        "SELECT count(*) FROM paper_plan_execution_outcomes o "
        "JOIN online_pipeline_runs r ON r.run_id=o.pipeline_run_id "
        "JOIN paper_account_baselines b ON b.accounting_session_id=:new_session "
        "WHERE o.accounting_session_id=:new_session "
        "AND r.finished_at < b.initialized_at AND o.command_id IS NOT NULL"
    ), {"new_session": NEW_SESSION}).scalar_one()
    if unsafe:
        raise RuntimeError("SESSION_BOUNDARY_REPAIR_REQUIRES_ZERO_LINKED_COMMANDS")

    bind.execute(sa.text(
        "UPDATE paper_plan_execution_outcomes o SET "
        "accounting_session_id=:old_session, "
        "refinement_details=(coalesce(o.refinement_details::jsonb,'{}'::jsonb) "
        "|| jsonb_build_object('session_boundary_reclassified_by',:marker))::json "
        "FROM online_pipeline_runs r, paper_account_baselines b "
        "WHERE r.run_id=o.pipeline_run_id "
        "AND b.accounting_session_id=:new_session "
        "AND o.accounting_session_id=:new_session "
        "AND r.finished_at < b.initialized_at"
    ), {
        "old_session": OLD_SESSION,
        "new_session": NEW_SESSION,
        "marker": MARKER,
    })


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text(
        "UPDATE paper_plan_execution_outcomes SET "
        "accounting_session_id=:new_session, "
        "refinement_details=(refinement_details::jsonb "
        "- 'session_boundary_reclassified_by')::json "
        "WHERE accounting_session_id=:old_session "
        "AND refinement_details::jsonb->>'session_boundary_reclassified_by'=:marker"
    ), {
        "old_session": OLD_SESSION,
        "new_session": NEW_SESSION,
        "marker": MARKER,
    })
