"""Persist PAPER plan selector and execution terminal outcomes.

Revision ID: 0020_paper_plan_execution_outcomes
Revises: 0019_first_class_15m_domain
"""

from alembic import op
import sqlalchemy as sa


revision = "0020_paper_plan_execution_outcomes"
down_revision = "0019_first_class_15m_domain"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_plan_execution_outcomes",
        sa.Column("pipeline_run_id", sa.String(128), primary_key=True),
        sa.Column("paper_plan_id", sa.String(512), nullable=False),
        sa.Column("final_approval_id", sa.String(128), nullable=False),
        sa.Column("candidate_id", sa.String(128), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("trade_profile_id", sa.String(64), nullable=False),
        sa.Column("universe_id", sa.String(128), nullable=False),
        sa.Column("boundary_closed_at_ms", sa.BigInteger(), nullable=False),
        sa.Column("plan_created_at_ms", sa.BigInteger(), nullable=False),
        sa.Column("approval_valid_until_ms", sa.BigInteger(), nullable=False),
        sa.Column("selector_state", sa.String(40), nullable=False),
        sa.Column("selector_reason", sa.String(160)),
        sa.Column("selector_rank", sa.Integer()),
        sa.Column("selected_winner", sa.Boolean(), nullable=False),
        sa.Column("lifecycle_state", sa.String(40), nullable=False),
        sa.Column("terminal_reason", sa.String(160)),
        sa.Column("command_id", sa.String(128)),
        sa.Column("control_generation", sa.Integer(), nullable=False),
        sa.Column("runtime_enabled", sa.Boolean(), nullable=False),
        sa.Column("daemon_enabled", sa.Boolean(), nullable=False),
        sa.Column("scheduler_enabled", sa.Boolean(), nullable=False),
        sa.Column("mutation_enabled", sa.Boolean(), nullable=False),
        sa.Column("live_enabled", sa.Boolean(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("terminal_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("length(trim(pipeline_run_id)) BETWEEN 1 AND 128", name="ck_plan_outcome_run"),
        sa.CheckConstraint("length(trim(paper_plan_id)) BETWEEN 1 AND 512", name="ck_plan_outcome_plan"),
        sa.CheckConstraint("length(trim(final_approval_id)) BETWEEN 1 AND 128", name="ck_plan_outcome_approval"),
        sa.CheckConstraint("length(trim(candidate_id)) BETWEEN 1 AND 128", name="ck_plan_outcome_candidate"),
        sa.CheckConstraint("length(trim(symbol)) BETWEEN 2 AND 32", name="ck_plan_outcome_symbol"),
        sa.CheckConstraint("boundary_closed_at_ms >= 0", name="ck_plan_outcome_boundary"),
        sa.CheckConstraint("plan_created_at_ms >= boundary_closed_at_ms", name="ck_plan_outcome_created"),
        sa.CheckConstraint("approval_valid_until_ms >= boundary_closed_at_ms", name="ck_plan_outcome_validity"),
        sa.CheckConstraint("lifecycle_state IN ('PLAN_OBSERVED','NOT_SELECTED','BLOCKED_BY_POLICY','COMMAND_CREATED','EXECUTION_FAILED','EXPIRED_BEFORE_EXECUTION')", name="ck_plan_outcome_state"),
        sa.CheckConstraint("selector_rank IS NULL OR selector_rank >= 1", name="ck_plan_outcome_rank"),
        sa.CheckConstraint("attempt_count >= 0", name="ck_plan_outcome_attempts"),
        sa.CheckConstraint("live_enabled = false", name="ck_plan_outcome_live_disabled"),
        sa.UniqueConstraint("paper_plan_id", name="uq_paper_plan_execution_outcome_plan"),
    )
    op.create_index("ix_plan_outcome_profile_boundary", "paper_plan_execution_outcomes", ["trade_profile_id", "boundary_closed_at_ms"])
    op.create_index("ix_plan_outcome_terminal", "paper_plan_execution_outcomes", ["lifecycle_state", "approval_valid_until_ms"])


def downgrade() -> None:
    raise RuntimeError("0020 paper plan execution outcomes is forward-only")
