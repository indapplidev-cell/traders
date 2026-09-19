"""Persist authoritative Scalping v2 1m hold revalidation decisions.

Revision ID: 0032_scalping_hold_lifecycle
Revises: 0031_scalping_parameter_sets
"""

from alembic import op
import sqlalchemy as sa


revision = "0032_scalping_hold_lifecycle"
down_revision = "0031_scalping_parameter_sets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scalping_position_hold_decisions",
        sa.Column("position_id", sa.String(128), nullable=False),
        sa.Column("evaluation_closed_until_ms", sa.BigInteger(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("holding_seconds", sa.BigInteger(), nullable=False),
        sa.Column("validity", sa.String(24), nullable=False),
        sa.Column("lifecycle_state", sa.String(32), nullable=False),
        sa.Column("exit_reason", sa.String(80), nullable=True),
        sa.Column("extension_count", sa.Integer(), nullable=False),
        sa.Column("extension_until_ms", sa.BigInteger(), nullable=True),
        sa.Column("thesis", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("policy_version", sa.String(64), nullable=False),
        sa.Column("config_hash", sa.String(64), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.CheckConstraint("holding_seconds >= 0", name="ck_scalping_hold_holding"),
        sa.CheckConstraint("extension_count >= 0", name="ck_scalping_hold_extensions"),
        sa.CheckConstraint(
            "validity IN ('VALID','INVALIDATED','REVERSED','STALE','DATA_UNAVAILABLE','ERROR')",
            name="ck_scalping_hold_validity",
        ),
        sa.CheckConstraint(
            "lifecycle_state IN ('FRESH','AT_RISK','STALE','EXTENSION_ALLOWED','EXTENSION_EXHAUSTED','FORCE_EXIT')",
            name="ck_scalping_hold_state",
        ),
        sa.CheckConstraint(
            "(lifecycle_state = 'FORCE_EXIT') = (exit_reason IS NOT NULL)",
            name="ck_scalping_hold_exit_complete",
        ),
        sa.ForeignKeyConstraint(
            ["position_id"], ["paper_positions.position_id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("position_id", "evaluation_closed_until_ms"),
    )
    op.create_index(
        "ix_scalping_hold_position_evaluation",
        "scalping_position_hold_decisions",
        ["position_id", "evaluation_closed_until_ms"],
    )
    op.execute(
        """
        DO $grants$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'traders_paper_runtime') THEN
                GRANT SELECT, INSERT, UPDATE ON TABLE
                    scalping_position_hold_decisions TO traders_paper_runtime;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'traders_readonly_api') THEN
                GRANT SELECT ON TABLE scalping_position_hold_decisions TO traders_readonly_api;
            END IF;
        END
        $grants$;
        """
    )


def downgrade() -> None:
    raise RuntimeError("0032 Scalping hold lifecycle is forward-only")
