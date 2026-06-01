"""init"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0001_init"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Создаёт стартовую схему БД для проекта."""

    op.create_table(
        "candles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("interval", sa.String(length=16), nullable=False),
        sa.Column("open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(24, 10), nullable=False),
        sa.Column("high", sa.Numeric(24, 10), nullable=False),
        sa.Column("low", sa.Numeric(24, 10), nullable=False),
        sa.Column("close", sa.Numeric(24, 10), nullable=False),
        sa.Column("volume", sa.Numeric(24, 10), nullable=False),
        sa.Column("close_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("symbol", "interval", "open_time", name="uq_candles_symbol_interval_open_time"),
    )
    op.create_index("ix_candles_symbol", "candles", ["symbol"])
    op.create_index("ix_candles_interval", "candles", ["interval"])
    op.create_index("ix_candles_open_time", "candles", ["open_time"])

    op.create_table(
        "paper_accounts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("currency", sa.String(length=16), nullable=False),
        sa.Column("balance", sa.Numeric(24, 10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("currency"),
    )
    op.create_index("ix_paper_accounts_currency", "paper_accounts", ["currency"], unique=True)

    op.create_table(
        "paper_positions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("side", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("entry_price", sa.Numeric(24, 10), nullable=False),
        sa.Column("quantity", sa.Numeric(24, 10), nullable=False),
        sa.Column("stop_loss", sa.Numeric(24, 10), nullable=True),
        sa.Column("take_profit", sa.Numeric(24, 10), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("close_price", sa.Numeric(24, 10), nullable=True),
        sa.Column("realized_pnl", sa.Numeric(24, 10), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_paper_positions_symbol", "paper_positions", ["symbol"])
    op.create_index("ix_paper_positions_status", "paper_positions", ["status"])

    op.create_table(
        "trade_decisions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("interval", sa.String(length=16), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=512), nullable=False),
        sa.Column("regime", sa.String(length=16), nullable=False),
        sa.Column("price", sa.Numeric(24, 10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_trade_decisions_symbol", "trade_decisions", ["symbol"])
    op.create_index("ix_trade_decisions_interval", "trade_decisions", ["interval"])


def downgrade() -> None:
    """Удаляет стартовую схему БД."""

    op.drop_index("ix_trade_decisions_interval", table_name="trade_decisions")
    op.drop_index("ix_trade_decisions_symbol", table_name="trade_decisions")
    op.drop_table("trade_decisions")

    op.drop_index("ix_paper_positions_status", table_name="paper_positions")
    op.drop_index("ix_paper_positions_symbol", table_name="paper_positions")
    op.drop_table("paper_positions")

    op.drop_index("ix_paper_accounts_currency", table_name="paper_accounts")
    op.drop_table("paper_accounts")

    op.drop_index("ix_candles_open_time", table_name="candles")
    op.drop_index("ix_candles_interval", table_name="candles")
    op.drop_index("ix_candles_symbol", table_name="candles")
    op.drop_table("candles")

