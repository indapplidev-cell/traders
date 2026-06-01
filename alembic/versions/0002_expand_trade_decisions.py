"""expand trade decisions"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0002_expand_trade_decisions"
down_revision: str | None = "0001_init"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Расширяет журнал trade_decisions для хранения полной истории шага."""

    op.alter_column(
        "trade_decisions",
        "decision",
        new_column_name="strategy_decision",
        existing_type=sa.String(length=16),
        existing_nullable=False,
    )
    op.alter_column(
        "trade_decisions",
        "reason",
        new_column_name="strategy_reason",
        existing_type=sa.String(length=512),
        existing_nullable=False,
    )

    op.add_column("trade_decisions", sa.Column("final_decision", sa.String(length=16), nullable=True))
    op.add_column("trade_decisions", sa.Column("final_reason", sa.String(length=512), nullable=True))
    op.add_column("trade_decisions", sa.Column("risk_approved", sa.Boolean(), nullable=True))
    op.add_column("trade_decisions", sa.Column("risk_reason", sa.String(length=512), nullable=True))
    op.add_column("trade_decisions", sa.Column("execution_action", sa.String(length=16), nullable=True))
    op.add_column("trade_decisions", sa.Column("execution_message", sa.String(length=1024), nullable=True))

    op.execute("UPDATE trade_decisions SET final_decision = strategy_decision")
    op.execute("UPDATE trade_decisions SET final_reason = strategy_reason")
    op.execute("UPDATE trade_decisions SET risk_approved = TRUE")
    op.execute(
        "UPDATE trade_decisions SET risk_reason = 'Историческая запись до расширения журнала.'"
    )
    op.execute("UPDATE trade_decisions SET execution_action = 'UNKNOWN'")
    op.execute(
        "UPDATE trade_decisions SET execution_message = 'Историческая запись до расширения журнала.'"
    )

    op.alter_column("trade_decisions", "final_decision", existing_type=sa.String(length=16), nullable=False)
    op.alter_column("trade_decisions", "final_reason", existing_type=sa.String(length=512), nullable=False)
    op.alter_column("trade_decisions", "risk_approved", existing_type=sa.Boolean(), nullable=False)
    op.alter_column("trade_decisions", "risk_reason", existing_type=sa.String(length=512), nullable=False)
    op.alter_column("trade_decisions", "execution_action", existing_type=sa.String(length=16), nullable=False)
    op.alter_column(
        "trade_decisions",
        "execution_message",
        existing_type=sa.String(length=1024),
        nullable=False,
    )


def downgrade() -> None:
    """Возвращает старую упрощённую схему журнала."""

    op.drop_column("trade_decisions", "execution_message")
    op.drop_column("trade_decisions", "execution_action")
    op.drop_column("trade_decisions", "risk_reason")
    op.drop_column("trade_decisions", "risk_approved")
    op.drop_column("trade_decisions", "final_reason")
    op.drop_column("trade_decisions", "final_decision")

    op.alter_column(
        "trade_decisions",
        "strategy_reason",
        new_column_name="reason",
        existing_type=sa.String(length=512),
        existing_nullable=False,
    )
    op.alter_column(
        "trade_decisions",
        "strategy_decision",
        new_column_name="decision",
        existing_type=sa.String(length=16),
        existing_nullable=False,
    )
