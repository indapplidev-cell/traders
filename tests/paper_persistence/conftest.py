from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine, create_engine, inspect, text
from sqlalchemy.engine import make_url

from app.config.settings import get_settings


PAPER_TABLES = {
    "paper_simulation_policies",
    "paper_execution_commands",
    "paper_orders",
    "paper_order_events",
    "paper_fills",
    "paper_positions",
    "paper_exit_decisions",
    "paper_journal_entries",
}


@dataclass(frozen=True)
class MigrationCycle:
    baseline_revision: str
    upgraded_revision: str
    paper_tables_after_upgrade: frozenset[str]
    paper_tables_after_downgrade: frozenset[str]
    preexisting_schema_unchanged: bool
    reupgraded_revision: str


def _required_isolated_url() -> str:
    raw = os.environ.get("PAPER_TEST_DATABASE_URL")
    if not raw:
        pytest.fail("PAPER_TEST_DATABASE_URL is required for PostgreSQL persistence tests")
    url = make_url(raw)
    if url.get_backend_name() != "postgresql":
        pytest.fail("PAPER_TEST_DATABASE_URL must use PostgreSQL")
    if url.host not in {"127.0.0.1", "localhost", "::1"}:
        pytest.fail("PAPER_TEST_DATABASE_URL must be loopback-only")
    if not (url.database or "").startswith("paper_test_"):
        pytest.fail("PAPER_TEST_DATABASE_URL must name a task-owned paper_test_ database")
    return raw


def _revision(engine: Engine) -> str:
    with engine.connect() as connection:
        return connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()


def _nonpaper_schema_signature(engine: Engine) -> tuple[tuple[object, ...], ...]:
    query = text(
        """
        SELECT kind, object_name, definition
        FROM (
            SELECT
                'column'::text AS kind,
                c.table_name || '.' || c.column_name AS object_name,
                concat_ws(
                    '|',
                    c.ordinal_position::text,
                    c.data_type,
                    coalesce(c.udt_name, ''),
                    c.is_nullable,
                    coalesce(c.column_default, ''),
                    coalesce(c.numeric_precision::text, ''),
                    coalesce(c.numeric_scale::text, '')
                ) AS definition
            FROM information_schema.columns c
            WHERE c.table_schema = 'public'
              AND c.table_name NOT LIKE 'paper\\_%' ESCAPE '\\'
            UNION ALL
            SELECT
                'constraint',
                cls.relname || '.' || con.conname,
                pg_get_constraintdef(con.oid, true)
            FROM pg_constraint con
            JOIN pg_class cls ON cls.oid = con.conrelid
            JOIN pg_namespace ns ON ns.oid = cls.relnamespace
            WHERE ns.nspname = 'public'
              AND cls.relname NOT LIKE 'paper\\_%' ESCAPE '\\'
            UNION ALL
            SELECT
                'index',
                tab.relname || '.' || idx.relname,
                pg_get_indexdef(idx.oid)
            FROM pg_index ix
            JOIN pg_class tab ON tab.oid = ix.indrelid
            JOIN pg_class idx ON idx.oid = ix.indexrelid
            JOIN pg_namespace ns ON ns.oid = tab.relnamespace
            WHERE ns.nspname = 'public'
              AND tab.relname NOT LIKE 'paper\\_%' ESCAPE '\\'
        ) signature
        ORDER BY kind, object_name, definition
        """
    )
    with engine.connect() as connection:
        return tuple(tuple(row) for row in connection.execute(query))


@pytest.fixture(scope="session")
def postgres_engine_and_cycle() -> Iterator[tuple[Engine, MigrationCycle]]:
    test_url = _required_isolated_url()
    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = test_url
    get_settings.cache_clear()

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", test_url.replace("%", "%%"))
    engine = create_engine(test_url, hide_parameters=True)

    command.downgrade(config, "0008_engine_orchestrator_freshness_retry")
    command.upgrade(config, "0008_engine_orchestrator_freshness_retry")
    baseline_revision = _revision(engine)
    baseline_signature = _nonpaper_schema_signature(engine)

    command.upgrade(config, "0009_paper_trading_persistence_foundation")
    upgraded_revision = _revision(engine)
    upgraded_tables = frozenset(inspect(engine).get_table_names()) & PAPER_TABLES

    command.downgrade(config, "0008_engine_orchestrator_freshness_retry")
    downgraded_tables = frozenset(inspect(engine).get_table_names()) & PAPER_TABLES
    unchanged = baseline_signature == _nonpaper_schema_signature(engine)

    command.upgrade(config, "0009_paper_trading_persistence_foundation")
    reupgraded_revision = _revision(engine)
    cycle = MigrationCycle(
        baseline_revision=baseline_revision,
        upgraded_revision=upgraded_revision,
        paper_tables_after_upgrade=upgraded_tables,
        paper_tables_after_downgrade=downgraded_tables,
        preexisting_schema_unchanged=unchanged,
        reupgraded_revision=reupgraded_revision,
    )
    try:
        yield engine, cycle
    finally:
        engine.dispose()
        get_settings.cache_clear()
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url


@pytest.fixture
def pg_connection(
    postgres_engine_and_cycle: tuple[Engine, MigrationCycle],
) -> Iterator[Connection]:
    engine, _ = postgres_engine_and_cycle
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            yield connection
        finally:
            if transaction.is_active:
                transaction.rollback()
