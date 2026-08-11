from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="session")
def reporting_pg_engine() -> Iterator[Engine]:
    raw = os.environ.get("PAPER_REPORTING_TEST_DATABASE_URL")
    if not raw:
        pytest.skip("task-owned PAPER_REPORTING_TEST_DATABASE_URL is not configured")
    url = make_url(raw)
    if url.get_backend_name() != "postgresql" or url.host not in {"127.0.0.1", "localhost", "::1"} or not (url.database or "").startswith("paper_reporting_test_"):
        pytest.fail("a task-owned loopback paper_reporting_test_ PostgreSQL is required")
    import app.config.settings as settings
    original = settings.get_settings
    settings.get_settings = lambda: SimpleNamespace(database_url=raw)
    engine = create_engine(raw, hide_parameters=True)
    config = Config("alembic.ini")
    with engine.connect() as connection:
        exists = connection.execute(text("SELECT to_regclass('public.alembic_version')")).scalar_one()
    if exists is None:
        command.upgrade(config, "0008_engine_orchestrator_freshness_retry")
    else:
        command.downgrade(config, "0008_engine_orchestrator_freshness_retry")
    try:
        yield engine
    finally:
        engine.dispose()
        settings.get_settings = original


@pytest.fixture
def reporting_sessions(reporting_pg_engine):
    return sessionmaker(bind=reporting_pg_engine, autoflush=False, expire_on_commit=False)
