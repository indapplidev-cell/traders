"""Extend PAPER order transition event vocabulary.

Revision ID: 0010_paper_final_approval_and_order_transition_event_vocabulary
Revises: 0009_paper_trading_persistence_foundation
"""

from alembic import op


revision = "0010_paper_final_approval_and_order_transition_event_vocabulary"
down_revision = "0009_paper_trading_persistence_foundation"
branch_labels = None
depends_on = None


OLD_EVENT_TYPES = (
    "PAPER_COMMAND_CREATED",
    "PAPER_COMMAND_REJECTED",
    "PAPER_ORDER_CREATED",
    "PAPER_ORDER_FILLED",
    "PAPER_POSITION_OPENED",
    "PAPER_EXIT_TRIGGERED",
    "PAPER_POSITION_CLOSED",
    "PAPER_EXECUTION_FAILED",
    "PAPER_SAFETY_BLOCKED",
)
NEW_EVENT_TYPES = OLD_EVENT_TYPES + (
    "PAPER_ORDER_VALIDATED",
    "PAPER_ORDER_OPENED",
)


def _values(values: tuple[str, ...]) -> str:
    return ",".join(f"'{value}'" for value in values)


def _replace(
    name: str,
    table: str,
    values: tuple[str, ...],
    *,
    not_valid: bool = False,
) -> None:
    op.drop_constraint(name, table, type_="check")
    op.create_check_constraint(
        name,
        table,
        f"event_type IN ({_values(values)})",
        postgresql_not_valid=not_valid,
    )


def upgrade() -> None:
    _replace("ck_paper_order_event_type", "paper_order_events", NEW_EVENT_TYPES)
    _replace("ck_paper_journal_event_type", "paper_journal_entries", NEW_EVENT_TYPES)


def downgrade() -> None:
    # PostgreSQL NOT VALID preserves any already-recorded 0010 events while
    # enforcing the restored 0009 vocabulary for every subsequent write.
    _replace(
        "ck_paper_journal_event_type",
        "paper_journal_entries",
        OLD_EVENT_TYPES,
        not_valid=True,
    )
    _replace(
        "ck_paper_order_event_type",
        "paper_order_events",
        OLD_EVENT_TYPES,
        not_valid=True,
    )
