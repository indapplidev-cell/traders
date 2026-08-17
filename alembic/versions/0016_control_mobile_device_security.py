"""Add public mobile device registry and durable mutation replay claims.

Revision ID: 0016_control_mobile_device_security
Revises: 0015_trading_universe_activation
"""

from alembic import op
import sqlalchemy as sa


revision = "0016_control_mobile_device_security"
down_revision = "0015_trading_universe_activation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "control_mobile_devices",
        sa.Column("device_id", sa.String(36), primary_key=True),
        sa.Column("public_key_spki", sa.LargeBinary(512), nullable=False),
        sa.Column("public_key_fingerprint", sa.String(64), nullable=False),
        sa.Column("algorithm", sa.String(32), nullable=False),
        sa.Column("key_version", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("label", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("algorithm = 'ECDSA_P256_SHA256'", name="ck_control_mobile_device_algorithm"),
        sa.CheckConstraint("key_version >= 1", name="ck_control_mobile_device_key_version"),
        sa.CheckConstraint("octet_length(public_key_spki) BETWEEN 80 AND 512", name="ck_control_mobile_device_spki"),
        sa.CheckConstraint("length(public_key_fingerprint) = 64", name="ck_control_mobile_device_fingerprint"),
        sa.CheckConstraint(
            "(enabled AND revoked_at IS NULL) OR (NOT enabled AND revoked_at IS NOT NULL)",
            name="ck_control_mobile_device_revocation",
        ),
    )
    op.create_table(
        "control_mobile_replay_nonces",
        sa.Column("device_id", sa.String(36), nullable=False),
        sa.Column("nonce", sa.String(128), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_id", sa.String(128), nullable=False),
        sa.Column("action", sa.String(48), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("device_id", "nonce", name="pk_control_mobile_replay_nonce"),
        sa.ForeignKeyConstraint(
            ["device_id"], ["control_mobile_devices.device_id"],
            ondelete="RESTRICT", name="fk_control_mobile_replay_device",
        ),
        sa.CheckConstraint("length(nonce) BETWEEN 22 AND 128", name="ck_control_mobile_replay_nonce"),
    )
    op.create_index(
        "ix_control_mobile_replay_expires_at",
        "control_mobile_replay_nonces",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_control_mobile_replay_expires_at", table_name="control_mobile_replay_nonces")
    op.drop_table("control_mobile_replay_nonces")
    op.drop_table("control_mobile_devices")
