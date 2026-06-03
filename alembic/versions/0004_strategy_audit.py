"""add strategy audit fields"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0004_strategy_audit"
down_revision: str | None = "0003_runner_state"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Adds runtime strategy metadata to trade_decisions."""

    op.add_column("trade_decisions", sa.Column("strategy_name", sa.String(length=64), nullable=True))
    op.add_column("trade_decisions", sa.Column("strategy_version", sa.String(length=32), nullable=True))
    op.add_column("trade_decisions", sa.Column("confidence", sa.Numeric(6, 4), nullable=True))

    op.execute("UPDATE trade_decisions SET strategy_name = 'legacy'")
    op.execute("UPDATE trade_decisions SET strategy_version = 'legacy'")
    op.execute("UPDATE trade_decisions SET confidence = 1.0")

    op.alter_column("trade_decisions", "strategy_name", existing_type=sa.String(length=64), nullable=False)
    op.alter_column("trade_decisions", "strategy_version", existing_type=sa.String(length=32), nullable=False)
    op.alter_column("trade_decisions", "confidence", existing_type=sa.Numeric(6, 4), nullable=False)


def downgrade() -> None:
    """Removes runtime strategy metadata from trade_decisions."""

    op.drop_column("trade_decisions", "confidence")
    op.drop_column("trade_decisions", "strategy_version")
    op.drop_column("trade_decisions", "strategy_name")
