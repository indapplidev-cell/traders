"""Create separate closed-candle tables for market-data timeframes.

Revision ID: 0005_engine_market_data_mtf
Revises: 0004_opportunity_labels
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_engine_market_data_mtf"
down_revision = "0004_opportunity_labels"
branch_labels = None
depends_on = None

TABLES = ("candles_1m", "candles_5m", "candles_15m", "candles_1h", "candles_4h", "candles_1d")


def _create_candle_table(table: str) -> None:
    op.create_table(table,
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=50), nullable=False),
        sa.Column("open_time_ms", sa.BigInteger(), nullable=False),
        sa.Column("close_time_ms", sa.BigInteger(), nullable=False),
        sa.Column("open_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("close_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(38, 18), nullable=False),
        sa.Column("high", sa.Numeric(38, 18), nullable=False),
        sa.Column("low", sa.Numeric(38, 18), nullable=False),
        sa.Column("close", sa.Numeric(38, 18), nullable=False),
        sa.Column("volume", sa.Numeric(38, 18), nullable=False),
        sa.Column("quote_volume", sa.Numeric(38, 18), nullable=True),
        sa.Column("trades_count", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("is_closed", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("ingested_at_utc", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("data_checksum", sa.String(length=64), nullable=True),
        sa.CheckConstraint("is_closed = true", name=f"ck_{table}_closed"),
        sa.CheckConstraint("volume >= 0", name=f"ck_{table}_volume"),
        sa.CheckConstraint("high >= open", name=f"ck_{table}_high_open"),
        sa.CheckConstraint("high >= close", name=f"ck_{table}_high_close"),
        sa.CheckConstraint("high >= low", name=f"ck_{table}_high_low"),
        sa.CheckConstraint("low <= open", name=f"ck_{table}_low_open"),
        sa.CheckConstraint("low <= close", name=f"ck_{table}_low_close"),
        sa.CheckConstraint("low <= high", name=f"ck_{table}_low_high"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "open_time_ms", name=f"uq_{table}_symbol_open_ms"),
    )
    op.create_index(f"ix_{table}_symbol_open_ms", table, ["symbol", "open_time_ms"])
    op.create_index(f"ix_{table}_symbol_close_ms", table, ["symbol", "close_time_ms"])
    op.create_index(f"ix_{table}_symbol_open_utc", table, ["symbol", "open_time_utc"])


def upgrade() -> None:
    for table in TABLES:
        _create_candle_table(table)


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)
