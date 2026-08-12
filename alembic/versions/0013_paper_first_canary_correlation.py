"""Add durable authoritative first-canary correlation.

Revision ID: 0013_paper_first_canary_correlation
Revises: 0012_paper_account_baseline
"""

from alembic import op
import sqlalchemy as sa


revision = "0013_paper_first_canary_correlation"
down_revision = "0012_paper_account_baseline"
branch_labels = None
depends_on = None


_STATES = (
    "RESERVED", "ARMED", "ARMED_WAITING", "NO_ELIGIBLE_APPROVAL", "RUNNING",
    "POSITION_OPEN", "POSITION_CLOSING", "POSITION_CLOSED",
    "RECONCILIATION_PENDING", "COMPLETED", "STOPPED", "FAILED_SAFE",
)


def upgrade() -> None:
    states = ",".join(f"'{value}'" for value in _STATES)
    op.create_table(
        "paper_first_canary_sessions",
        sa.Column("canary_id", sa.String(36), nullable=False),
        sa.Column("environment", sa.String(32), nullable=False),
        sa.Column("mode", sa.String(8), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("armed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("arm_request_id", sa.String(128), nullable=False),
        sa.Column("arm_request_fingerprint", sa.String(64), nullable=False),
        sa.Column("arming_transition_id", sa.String(128), nullable=True),
        sa.Column("arming_generation", sa.Integer(), nullable=True),
        sa.Column("start_request_id", sa.String(128), nullable=True),
        sa.Column("start_request_fingerprint", sa.String(64), nullable=True),
        sa.Column("current_control_generation", sa.Integer(), nullable=False),
        sa.Column("max_new_commands", sa.Integer(), nullable=False),
        sa.Column("max_open_positions", sa.Integer(), nullable=False),
        sa.Column("allowed_symbols", sa.JSON(), nullable=False),
        sa.Column("approval_id", sa.String(128), nullable=True),
        sa.Column("command_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("command_id", sa.String(128), nullable=True),
        sa.Column("position_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("position_id", sa.String(128), nullable=True),
        sa.Column("trade_report_available", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("paper_reconciliation_status", sa.String(32), nullable=False),
        sa.Column("accounting_reconciliation_status", sa.String(32), nullable=False),
        sa.Column("reconciliation_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("terminal_reason", sa.String(80), nullable=True),
        sa.Column("finding_codes", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("canary_id", name="pk_paper_first_canary_sessions"),
        sa.UniqueConstraint("arm_request_id", name="uq_paper_first_canary_arm_request"),
        sa.UniqueConstraint("arming_transition_id", name="uq_paper_first_canary_arm_transition"),
        sa.UniqueConstraint("start_request_id", name="uq_paper_first_canary_start_request"),
        sa.UniqueConstraint("command_id", name="uq_paper_first_canary_command"),
        sa.UniqueConstraint("position_id", name="uq_paper_first_canary_position"),
        sa.ForeignKeyConstraint(["command_id"], ["paper_execution_commands.command_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["position_id"], ["paper_positions.position_id"], ondelete="RESTRICT"),
        sa.CheckConstraint("environment = 'PRODUCTION'", name="ck_paper_first_canary_environment"),
        sa.CheckConstraint("mode = 'PAPER'", name="ck_paper_first_canary_mode"),
        sa.CheckConstraint(f"state IN ({states})", name="ck_paper_first_canary_state"),
        sa.CheckConstraint("max_new_commands = 1", name="ck_paper_first_canary_command_budget"),
        sa.CheckConstraint("max_open_positions = 1", name="ck_paper_first_canary_position_budget"),
        sa.CheckConstraint("command_count BETWEEN 0 AND 1", name="ck_paper_first_canary_command_count"),
        sa.CheckConstraint("position_count BETWEEN 0 AND 1", name="ck_paper_first_canary_position_count"),
        sa.CheckConstraint("(command_count = 0 AND command_id IS NULL) OR (command_count = 1 AND command_id IS NOT NULL)", name="ck_paper_first_canary_command_link"),
        sa.CheckConstraint("(position_count = 0 AND position_id IS NULL) OR (position_count = 1 AND position_id IS NOT NULL)", name="ck_paper_first_canary_position_link"),
        sa.CheckConstraint("version >= 0", name="ck_paper_first_canary_version"),
    )
    op.create_index(
        "uq_paper_first_canary_one_active_environment",
        "paper_first_canary_sessions",
        ["environment"],
        unique=True,
        postgresql_where=sa.text("state NOT IN ('COMPLETED','STOPPED','FAILED_SAFE')"),
    )


def downgrade() -> None:
    # Destructive by design: production recovery uses forward remediation/PITR.
    op.drop_index("uq_paper_first_canary_one_active_environment", table_name="paper_first_canary_sessions")
    op.drop_table("paper_first_canary_sessions")
