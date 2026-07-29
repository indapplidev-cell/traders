from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from app.config.settings import get_settings


REVISION = "0010_paper_final_approval_and_order_transition_event_vocabulary"
BASELINE = "0009_paper_trading_persistence_foundation"
NOW = datetime(2026, 7, 29, 8, 0, tzinfo=timezone.utc)


def _isolated_url() -> str:
    raw = os.environ.get("PAPER_TEST_DATABASE_URL")
    if not raw:
        pytest.fail("PAPER_TEST_DATABASE_URL is required for migration 0010 tests")
    url = make_url(raw)
    if (
        url.get_backend_name() != "postgresql"
        or url.host not in {"127.0.0.1", "localhost", "::1"}
        or not (url.database or "").startswith("paper_test_")
    ):
        pytest.fail("isolated loopback paper_test_ PostgreSQL is required")
    return raw


def _journal_values(suffix: str, event_type: str) -> dict[str, object]:
    return {
        "journal_entry_id": f"migration-event:{suffix}",
        "event_type": event_type,
        "occurred_at": NOW,
        "aggregate_type": "paper_order",
        "aggregate_id": "migration-order:1",
        "aggregate_version": 1,
        "correlation_id": "migration-command:1",
        "causation_id": "migration-order:1",
        "idempotency_key": f"migration-idempotency:{suffix}",
        "reason_code": (
            "PAPER_ORDER_VALIDATED"
            if event_type == "PAPER_ORDER_VALIDATED"
            else "PAPER_ORDER_OPENED"
            if event_type == "PAPER_ORDER_OPENED"
            else "PAPER_ORDER_CREATED"
        ),
        "command_id": None,
        "order_id": None,
        "fill_id": None,
        "position_id": None,
        "exit_decision_id": None,
    }


def _insert(connection, suffix: str, event_type: str) -> None:
    connection.execute(
        text(
            """
            INSERT INTO paper_journal_entries (
                journal_entry_id, event_type, occurred_at, aggregate_type,
                aggregate_id, aggregate_version, correlation_id, causation_id,
                idempotency_key, reason_code, command_id, order_id, fill_id,
                position_id, exit_decision_id
            ) VALUES (
                :journal_entry_id, :event_type, :occurred_at, :aggregate_type,
                :aggregate_id, :aggregate_version, :correlation_id, :causation_id,
                :idempotency_key, :reason_code, :command_id, :order_id, :fill_id,
                :position_id, :exit_decision_id
            )
            """
        ),
        _journal_values(suffix, event_type),
    )


def _assert_rejected(connection, suffix: str, event_type: str) -> None:
    savepoint = connection.begin_nested()
    try:
        with pytest.raises(IntegrityError):
            _insert(connection, suffix, event_type)
    finally:
        savepoint.rollback()


def test_migration_0009_upgrade_downgrade_reupgrade_event_constraints():
    raw = _isolated_url()
    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = raw
    get_settings.cache_clear()
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", raw.replace("%", "%%"))
    engine = create_engine(raw, hide_parameters=True)
    try:
        with engine.connect() as connection:
            version_table = connection.execute(
                text("SELECT to_regclass('public.alembic_version')")
            ).scalar_one()
            current = (
                connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one()
                if version_table is not None
                else None
            )
        if current is None:
            command.upgrade(config, BASELINE)
        elif current != BASELINE:
            command.downgrade(config, BASELINE)
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM paper_journal_entries"))
            connection.execute(text("DELETE FROM paper_order_events"))
            _insert(connection, "old-at-0009", "PAPER_ORDER_CREATED")
            _assert_rejected(connection, "validated-at-0009", "PAPER_ORDER_VALIDATED")
            connection.execute(
                text(
                    "DELETE FROM paper_journal_entries "
                    "WHERE journal_entry_id = 'migration-event:old-at-0009'"
                )
            )

        command.upgrade(config, REVISION)
        with engine.begin() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            assert revision == REVISION
            _insert(connection, "old-at-0010", "PAPER_ORDER_CREATED")
            _insert(connection, "validated-at-0010", "PAPER_ORDER_VALIDATED")
            _insert(connection, "opened-at-0010", "PAPER_ORDER_OPENED")
            _assert_rejected(connection, "unknown-at-0010", "UNKNOWN")

        command.downgrade(config, BASELINE)
        with engine.begin() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            assert revision == BASELINE
            assert connection.execute(
                text(
                    "SELECT count(*) FROM paper_journal_entries "
                    "WHERE event_type IN "
                    "('PAPER_ORDER_VALIDATED','PAPER_ORDER_OPENED')"
                )
            ).scalar_one() == 2
            _insert(connection, "old-after-downgrade", "PAPER_ORDER_CREATED")
            _assert_rejected(
                connection,
                "validated-after-downgrade",
                "PAPER_ORDER_VALIDATED",
            )
            _assert_rejected(
                connection,
                "opened-after-downgrade",
                "PAPER_ORDER_OPENED",
            )
            connection.execute(
                text(
                    "DELETE FROM paper_journal_entries "
                    "WHERE journal_entry_id LIKE 'migration-event:%'"
                )
            )

        command.upgrade(config, REVISION)
        with engine.begin() as connection:
            assert connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one() == REVISION
            _insert(connection, "validated-after-reupgrade", "PAPER_ORDER_VALIDATED")
            connection.execute(
                text(
                    "DELETE FROM paper_journal_entries "
                    "WHERE journal_entry_id = 'migration-event:validated-after-reupgrade'"
                )
            )
    finally:
        engine.dispose()
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
        get_settings.cache_clear()


def test_migration_0010_is_constraint_only_and_0009_is_unchanged():
    root = Path(__file__).parents[2]
    source = (
        root
        / "alembic/versions/0010_paper_final_approval_and_order_transition_event_vocabulary.py"
    ).read_text(encoding="utf-8")
    assert "op.drop_constraint" in source
    assert "op.create_check_constraint" in source
    for forbidden in (
        "op.create_table",
        "op.drop_table",
        "op.add_column",
        "op.drop_column",
        "op.execute",
        "UPDATE ",
        "INSERT ",
        "DELETE ",
    ):
        assert forbidden not in source
