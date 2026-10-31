"""Separate PAPER economics and activate the 1000 USDT accounting session.

Revision ID: 0039_paper_accounting_session_v2
Revises: 0038_plan_outcome_pre_selector_terminal
"""

from alembic import op
import sqlalchemy as sa


revision = "0039_paper_accounting_session_v2"
down_revision = "0038_plan_outcome_pre_selector_terminal"
branch_labels = None
depends_on = None


OLD_SESSION = "TRADERS_PAPER_SESSION_01"
NEW_SESSION = "TRADERS_PAPER_SESSION_02"
SESSION_TABLES = (
    "paper_first_canary_sessions",
    "paper_continuous_control_events",
    "paper_execution_commands",
    "paper_plan_execution_outcomes",
    "paper_orders",
    "paper_order_events",
    "paper_fills",
    "paper_positions",
    "paper_exit_evaluation_cursors",
    "paper_exit_decisions",
    "paper_journal_entries",
)


def upgrade() -> None:
    bind = op.get_bind()
    open_positions = bind.execute(sa.text(
        "SELECT count(*) FROM paper_positions WHERE state IN ('OPEN','CLOSING')"
    )).scalar_one()
    if open_positions:
        raise RuntimeError("SESSION_ROTATION_REQUIRES_ZERO_OPEN_POSITIONS")

    # Historical commands that outlived their entry window cannot cross the
    # accounting boundary. They remain durable and are terminally classified.
    bind.execute(sa.text(
        "UPDATE paper_execution_commands SET processing_status='FAILED' "
        "WHERE processing_status IN ('PENDING','PROCESSING') "
        "AND valid_until_ms < (extract(epoch FROM clock_timestamp()) * 1000)::bigint"
    ))
    remaining = bind.execute(sa.text(
        "SELECT count(*) FROM paper_execution_commands "
        "WHERE processing_status IN ('PENDING','PROCESSING')"
    )).scalar_one()
    if remaining:
        raise RuntimeError("SESSION_ROTATION_REQUIRES_ZERO_ACTIVE_COMMANDS")

    for table in SESSION_TABLES:
        op.add_column(
            table,
            sa.Column(
                "accounting_session_id",
                sa.String(length=128),
                nullable=False,
                server_default=OLD_SESSION,
            ),
        )
        op.create_check_constraint(
            f"ck_{table}_accounting_session",
            table,
            "length(trim(accounting_session_id)) BETWEEN 1 AND 128",
        )
        op.alter_column(
            table,
            "accounting_session_id",
            existing_type=sa.String(length=128),
            nullable=False,
            server_default=NEW_SESSION,
        )
        op.create_index(
            f"ix_{table}_accounting_session",
            table,
            ["accounting_session_id"],
        )

    # Copy identity and semantic version from the immutable v1 baseline. No
    # historical balance or PnL row is rewritten.
    bind.execute(sa.text(
        "INSERT INTO paper_account_baselines "
        "(baseline_id,account_id,accounting_session_id,currency,initial_balance,initialized_at,semantic_version) "
        "SELECT 'baseline:production-paper-v2',account_id,CAST(:new_session AS varchar(128)),currency,1000.00,clock_timestamp(),semantic_version "
        "FROM paper_account_baselines WHERE accounting_session_id=:old_session "
        "AND NOT EXISTS (SELECT 1 FROM paper_account_baselines WHERE accounting_session_id=:new_session)"
    ), {"old_session": OLD_SESSION, "new_session": NEW_SESSION})
    row = bind.execute(sa.text(
        "SELECT baseline_id,initial_balance FROM paper_account_baselines "
        "WHERE accounting_session_id=:new_session"
    ), {"new_session": NEW_SESSION}).one_or_none()
    if row is None or row[0] != "baseline:production-paper-v2" or row[1] != 1000:
        raise RuntimeError("SESSION_V2_BASELINE_POSTCONDITION_FAILED")


def downgrade() -> None:
    bind = op.get_bind()
    for table in SESSION_TABLES:
        count = bind.execute(sa.text(
            f"SELECT count(*) FROM {table} WHERE accounting_session_id=:session"
        ), {"session": NEW_SESSION}).scalar_one()
        if count:
            raise RuntimeError("DOWNGRADE_REQUIRES_ZERO_SESSION_V2_ECONOMIC_ROWS")
    bind.execute(sa.text(
        "DELETE FROM paper_account_baselines WHERE accounting_session_id=:session "
        "AND baseline_id='baseline:production-paper-v2' AND initial_balance=1000.00"
    ), {"session": NEW_SESSION})
    for table in reversed(SESSION_TABLES):
        op.drop_index(f"ix_{table}_accounting_session", table_name=table)
        op.drop_constraint(
            f"ck_{table}_accounting_session", table, type_="check"
        )
        op.drop_column(table, "accounting_session_id")
