"""Add durable retry lifecycle for transient freshness boundaries.

Revision ID: 0008_engine_orchestrator_freshness_retry
Revises: 0007_engine_orchestrator_online_pipeline
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_engine_orchestrator_freshness_retry"
down_revision = "0007_engine_orchestrator_online_pipeline"
branch_labels = None
depends_on = None


STATUS_CHECK = (
    "status IN ('PENDING','RESERVED','CHECKING_FRESHNESS',"
    "'WAITING_FOR_REQUIRED_BOUNDARY','READY_TO_RUN','RUNNING','COMPLETED',"
    "'SKIPPED_DUPLICATE_WINDOW','SKIPPED_FRESHNESS_NOT_OK',"
    "'SKIPPED_FRESHNESS_TIMEOUT','SKIPPED_NOT_ENOUGH_DATA','MODULE_ERROR','ERROR')"
)


def upgrade() -> None:
    op.add_column("online_pipeline_runs", sa.Column("freshness_attempt_count", sa.Integer(), server_default="0", nullable=False))
    op.add_column("online_pipeline_runs", sa.Column("first_freshness_checked_at", sa.DateTime(timezone=True)))
    op.add_column("online_pipeline_runs", sa.Column("last_freshness_checked_at", sa.DateTime(timezone=True)))
    op.add_column("online_pipeline_runs", sa.Column("first_wait_at", sa.DateTime(timezone=True)))
    op.add_column("online_pipeline_runs", sa.Column("next_retry_at", sa.DateTime(timezone=True)))
    op.add_column("online_pipeline_runs", sa.Column("freshness_deadline_at", sa.DateTime(timezone=True)))
    op.add_column("online_pipeline_runs", sa.Column("freshness_claimed_at", sa.DateTime(timezone=True)))
    op.add_column("online_pipeline_runs", sa.Column("waiting_reason_code", sa.String(100)))
    op.add_column("online_pipeline_runs", sa.Column("waiting_timeframes", sa.JSON()))
    op.add_column("online_pipeline_runs", sa.Column("last_freshness_payload", sa.JSON()))
    op.add_column("online_pipeline_runs", sa.Column("freshness_recovered_at", sa.DateTime(timezone=True)))
    op.drop_constraint("ck_online_pipeline_run_status", "online_pipeline_runs", type_="check")
    op.create_check_constraint("ck_online_pipeline_run_status", "online_pipeline_runs", STATUS_CHECK)
    op.create_index(
        "ix_online_pipeline_runs_status_next_retry",
        "online_pipeline_runs",
        ["status", "next_retry_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_online_pipeline_runs_status_next_retry", table_name="online_pipeline_runs")
    op.drop_constraint("ck_online_pipeline_run_status", "online_pipeline_runs", type_="check")
    op.execute(
        "UPDATE online_pipeline_runs SET status = 'PENDING' "
        "WHERE status IN ('RESERVED','CHECKING_FRESHNESS','WAITING_FOR_REQUIRED_BOUNDARY','READY_TO_RUN')"
    )
    op.execute(
        "UPDATE online_pipeline_runs SET status = 'SKIPPED_FRESHNESS_NOT_OK' "
        "WHERE status = 'SKIPPED_FRESHNESS_TIMEOUT'"
    )
    op.create_check_constraint(
        "ck_online_pipeline_run_status",
        "online_pipeline_runs",
        "status IN ('PENDING','RUNNING','COMPLETED','SKIPPED_DUPLICATE_WINDOW',"
        "'SKIPPED_FRESHNESS_NOT_OK','SKIPPED_NOT_ENOUGH_DATA','MODULE_ERROR','ERROR')",
    )
    for column in (
        "freshness_recovered_at", "last_freshness_payload", "waiting_timeframes",
        "waiting_reason_code", "freshness_claimed_at", "freshness_deadline_at",
        "next_retry_at", "first_wait_at", "last_freshness_checked_at",
        "first_freshness_checked_at", "freshness_attempt_count",
    ):
        op.drop_column("online_pipeline_runs", column)
