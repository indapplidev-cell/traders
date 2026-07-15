"""Create operational market-data synchronization state.

Revision ID: 0006_engine_market_data_sync_state
Revises: 0005_engine_market_data_mtf
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_engine_market_data_sync_state"
down_revision = "0005_engine_market_data_mtf"
branch_labels = None
depends_on = None

ALEMBIC_VERSION_LENGTH = 64


def upgrade() -> None:
    # Alembic creates version_num as VARCHAR(32) by default.  This revision id is
    # 34 characters, so PostgreSQL would otherwise roll the whole migration back
    # when Alembic records the new head after upgrade() returns.
    op.alter_column(
        "alembic_version",
        "version_num",
        existing_type=sa.String(length=32),
        type_=sa.String(length=ALEMBIC_VERSION_LENGTH),
        existing_nullable=False,
    )
    op.create_table(
        "market_data_sync_state",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(50), nullable=False),
        sa.Column("timeframe", sa.String(8), nullable=False),
        sa.Column("last_expected_open_time_ms", sa.BigInteger()),
        sa.Column("last_expected_close_boundary_ms", sa.BigInteger()),
        sa.Column("last_stored_open_time_ms", sa.BigInteger()),
        sa.Column("last_stored_close_boundary_ms", sa.BigInteger()),
        sa.Column("freshness_lag_ms", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("freshness_lag_candles", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("missing_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("recovering_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("last_error_at", sa.DateTime(timezone=True)),
        sa.Column("last_error_code", sa.String(100)),
        sa.Column("last_error_message", sa.Text()),
        sa.Column("last_inserted_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_updated_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_skipped_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_failed_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("daemon_instance_id", sa.String(100), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('OK','STALE','GAP_DETECTED','RECOVERING','DEGRADED','DISCONNECTED','ERROR','NOT_CONFIGURED')",
                           name="ck_market_data_sync_state_status"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "timeframe", name="uq_market_data_sync_state_symbol_timeframe"),
    )
    op.create_index("ix_market_data_sync_state_status", "market_data_sync_state", ["status"])
    op.create_index("ix_market_data_sync_state_updated_at", "market_data_sync_state", ["updated_at"])


def downgrade() -> None:
    op.drop_table("market_data_sync_state")
    # Keep version_num widened.  Alembic records the down_revision only after
    # downgrade() returns, so shrinking it here would fail while the 34-character
    # current revision is still stored.  VARCHAR(64) is backward-compatible.
