"""Persist empirical authority generations and recovery campaigns.

Revision ID: 0036_empirical_requalification_authority
Revises: 0035_scalping_v2_ingestion_policy_contract
"""

from alembic import op
import sqlalchemy as sa


revision = "0036_empirical_requalification_authority"
down_revision = "0035_scalping_v2_ingestion_policy_contract"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "empirical_authority_generations",
        sa.Column("authority_generation_id", sa.String(128), primary_key=True),
        sa.Column("authority_population_id", sa.String(128), nullable=False),
        sa.Column("authority_policy_version", sa.String(64), nullable=False),
        sa.Column("observation_set_fingerprint", sa.String(64), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("wins", sa.Integer(), nullable=False),
        sa.Column("losses", sa.Integer(), nullable=False),
        sa.Column("win_rate", sa.Numeric(20, 10), nullable=False),
        sa.Column("average_win_net_bps", sa.Numeric(38, 18), nullable=False),
        sa.Column("average_loss_net_bps", sa.Numeric(38, 18), nullable=False),
        sa.Column("empirical_ev_net_bps", sa.Numeric(38, 18), nullable=False),
        sa.Column("expected_ev_r", sa.Numeric(38, 18), nullable=False),
        sa.Column("break_even_win_rate", sa.Numeric(20, 10), nullable=False),
        sa.Column("required_dynamic_rr", sa.Numeric(38, 18), nullable=False),
        sa.Column("bucket_level", sa.String(40), nullable=False),
        sa.Column("bucket_key", sa.String(512), nullable=False),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("recovery_campaign_id", sa.String(128)),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("superseded_at", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.CheckConstraint("sample_count = 20", name="ck_empirical_authority_sample_20"),
        sa.CheckConstraint("wins >= 0 AND losses >= 0 AND wins + losses = sample_count", name="ck_empirical_authority_counts"),
        sa.UniqueConstraint("authority_population_id", "observation_set_fingerprint", name="uq_empirical_authority_population_window"),
    )
    op.create_index(
        "uq_empirical_authority_one_active", "empirical_authority_generations",
        ["authority_population_id"], unique=True, postgresql_where=sa.text("is_active"),
    )
    op.create_index(
        "ix_empirical_authority_population_activated", "empirical_authority_generations",
        ["authority_population_id", "activated_at"],
    )
    op.create_table(
        "empirical_recovery_campaigns",
        sa.Column("recovery_campaign_id", sa.String(128), primary_key=True),
        sa.Column("authority_population_id", sa.String(128), nullable=False),
        sa.Column("state", sa.String(40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("v2_closed_probe_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("distinct_symbol_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("positive_confirmation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latest_window_fingerprint", sa.String(64)),
        sa.Column("latest_window_ev_net_bps", sa.Numeric(38, 18)),
        sa.Column("latest_window_expected_ev_r", sa.Numeric(38, 18)),
        sa.Column("latest_evaluated_closed_at", sa.DateTime(timezone=True)),
        sa.Column("requalified_at", sa.DateTime(timezone=True)),
        sa.Column("active_authority_generation_id", sa.String(128)),
        sa.Column("initial_authority_generation_id", sa.String(128), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "state IN ('ESTABLISHED_NEGATIVE','EXPLORATION_RECOVERY_ACTIVE','REQUALIFICATION_PENDING','REQUALIFIED_ACTIVE')",
            name="ck_empirical_recovery_state",
        ),
        sa.CheckConstraint("v2_closed_probe_count >= 0", name="ck_empirical_recovery_probe_count"),
        sa.CheckConstraint("distinct_symbol_count >= 0", name="ck_empirical_recovery_symbol_count"),
        sa.CheckConstraint("positive_confirmation_count BETWEEN 0 AND 2", name="ck_empirical_recovery_confirmations"),
    )
    op.create_index(
        "ix_empirical_recovery_population_started", "empirical_recovery_campaigns",
        ["authority_population_id", "started_at"],
    )
    op.create_table(
        "empirical_recovery_evaluations",
        sa.Column("evaluation_id", sa.String(128), primary_key=True),
        sa.Column("recovery_campaign_id", sa.String(128), nullable=False),
        sa.Column("trigger_position_id", sa.String(128), nullable=False),
        sa.Column("trigger_closed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_fingerprint", sa.String(64), nullable=False),
        sa.Column("window_sample_count", sa.Integer(), nullable=False),
        sa.Column("window_ev_net_bps", sa.Numeric(38, 18)),
        sa.Column("window_expected_ev_r", sa.Numeric(38, 18)),
        sa.Column("new_v2_probe_count", sa.Integer(), nullable=False),
        sa.Column("distinct_symbol_count", sa.Integer(), nullable=False),
        sa.Column("predicate_passed", sa.Boolean(), nullable=False),
        sa.Column("positive_confirmation_count", sa.Integer(), nullable=False),
        sa.Column("promoted_authority_generation_id", sa.String(128)),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("window_sample_count BETWEEN 0 AND 20", name="ck_empirical_recovery_window_count"),
        sa.CheckConstraint("positive_confirmation_count BETWEEN 0 AND 2", name="ck_empirical_recovery_evaluation_confirmations"),
        sa.UniqueConstraint("recovery_campaign_id", "trigger_position_id", name="uq_empirical_recovery_probe_evaluation"),
    )
    op.create_index(
        "ix_empirical_recovery_evaluation_campaign", "empirical_recovery_evaluations",
        ["recovery_campaign_id", "trigger_closed_at"],
    )


def downgrade() -> None:
    op.drop_table("empirical_recovery_evaluations")
    op.drop_table("empirical_recovery_campaigns")
    op.drop_index("uq_empirical_authority_one_active", table_name="empirical_authority_generations")
    op.drop_table("empirical_authority_generations")
