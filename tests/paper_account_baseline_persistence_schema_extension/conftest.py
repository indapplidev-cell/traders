from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.config.settings import get_settings


@pytest.fixture(scope="session")
def baseline_pg_engine() -> Iterator[Engine]:
    raw = os.environ.get("BASELINE_TEST_DATABASE_URL")
    if not raw:
        pytest.fail("BASELINE_TEST_DATABASE_URL is required")
    url = make_url(raw)
    if (url.get_backend_name() != "postgresql"
            or url.host not in {"127.0.0.1", "localhost", "::1"}
            or not (url.database or "").startswith("paper_test_baseline_")):
        pytest.fail("task-owned loopback paper_test_baseline_ PostgreSQL is required")
    # This process-local value is the task-owned isolated target, never a
    # protected production binding.
    os.environ["DATABASE_URL"] = raw
    get_settings.cache_clear()
    config = Config("alembic.ini")
    engine = create_engine(raw, hide_parameters=True)
    with engine.connect() as connection:
        version_table = connection.execute(
            text("SELECT to_regclass('public.alembic_version')")
        ).scalar_one()
    if version_table is not None:
        command.downgrade(config, "0008_engine_orchestrator_freshness_retry")
    else:
        command.upgrade(config, "0008_engine_orchestrator_freshness_retry")
    command.upgrade(config, "0012_paper_account_baseline")
    try:
        yield engine
    finally:
        engine.dispose()
        get_settings.cache_clear()
        os.environ.pop("DATABASE_URL", None)


@pytest.fixture
def baseline_session_factory(baseline_pg_engine: Engine) -> Iterator[sessionmaker]:
    with baseline_pg_engine.begin() as connection:
        connection.execute(text(
            "TRUNCATE paper_account_baselines, paper_exit_evaluation_cursors, "
            "paper_journal_entries, paper_exit_decisions, paper_positions, "
            "paper_fills, paper_order_events, paper_orders, "
            "paper_execution_commands, paper_simulation_policies "
            "RESTART IDENTITY CASCADE"
        ))
    yield sessionmaker(bind=baseline_pg_engine, autoflush=False, autocommit=False)
