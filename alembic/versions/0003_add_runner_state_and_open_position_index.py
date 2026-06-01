"""add runner state and open position index"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0003_add_runner_state_and_open_position_index"
down_revision: str | None = "0002_expand_trade_decisions"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Добавляет partial index и состояние paper-runner."""

    # DB-level защита нужна для реальной защиты от гонок записи.
    # Проверка в Python полезна, но только уникальный индекс БД гарантирует,
    # что по одному symbol нельзя одновременно держать две OPEN-позиции.
    op.create_index(
        "uq_paper_positions_one_open_per_symbol",
        "paper_positions",
        ["symbol"],
        unique=True,
        postgresql_where=sa.text("status = 'OPEN'"),
        sqlite_where=sa.text("status = 'OPEN'"),
    )

    op.create_table(
        "paper_runner_state",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("interval", sa.String(length=16), nullable=False),
        sa.Column("last_processed_open_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("symbol", "interval", name="uq_paper_runner_state_symbol_interval"),
    )
    op.create_index("ix_paper_runner_state_symbol", "paper_runner_state", ["symbol"])
    op.create_index("ix_paper_runner_state_interval", "paper_runner_state", ["interval"])


def downgrade() -> None:
    """Удаляет таблицу состояния runner и partial index."""

    op.drop_index("ix_paper_runner_state_interval", table_name="paper_runner_state")
    op.drop_index("ix_paper_runner_state_symbol", table_name="paper_runner_state")
    op.drop_table("paper_runner_state")
    op.drop_index("uq_paper_positions_one_open_per_symbol", table_name="paper_positions")
