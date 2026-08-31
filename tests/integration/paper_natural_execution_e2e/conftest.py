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


EXPECTED_HEAD = "0019_first_class_15m_domain"


@pytest.fixture(scope="session")
def natural_e2e_engine() -> Iterator[Engine]:
    raw = os.environ.get("PAPER_NATURAL_E2E_DATABASE_URL")
    if not raw:
        pytest.skip("PAPER_NATURAL_E2E_DATABASE_URL is not configured")
    url = make_url(raw)
    if (
        url.get_backend_name() != "postgresql"
        or url.host not in {"127.0.0.1", "localhost", "::1"}
        or not (url.database or "").startswith("paper_test_")
        or not (url.username or "").startswith("paper_test_")
    ):
        pytest.fail(
            "task-owned loopback paper_test_ PostgreSQL and test-only principal are required"
        )

    engine = create_engine(raw, hide_parameters=True)
    with engine.connect() as connection:
        database, principal, server_major = connection.execute(
            text(
                "SELECT current_database(), current_user, "
                "current_setting('server_version_num')::int / 10000"
            )
        ).one()
        role = connection.execute(
            text(
                "SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication, "
                "rolbypassrls FROM pg_roles WHERE rolname = current_user"
            )
        ).one()
    if (
        database != url.database
        or principal != url.username
        or server_major != 16
        or any(role)
    ):
        pytest.fail("isolated PostgreSQL 16 test identity is not production-safe")

    config = Config("alembic.ini")
    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = raw
    get_settings.cache_clear()
    command.upgrade(config, "head")
    with engine.connect() as connection:
        revisions = tuple(
            connection.execute(text("SELECT version_num FROM alembic_version"))
        )
    if revisions != ((EXPECTED_HEAD,),):
        pytest.fail(f"expected exactly one Alembic head {EXPECTED_HEAD!r}")
    try:
        yield engine
    finally:
        engine.dispose()
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
        get_settings.cache_clear()


@pytest.fixture
def natural_e2e_sessions(natural_e2e_engine: Engine) -> sessionmaker:
    tables = (
        "paper_first_canary_sessions",
        "paper_account_baselines",
        "paper_exit_evaluation_cursors",
        "paper_journal_entries",
        "paper_exit_decisions",
        "paper_positions",
        "paper_fills",
        "paper_order_events",
        "paper_orders",
        "paper_execution_commands",
        "paper_simulation_policies",
        "online_pipeline_results",
        "online_pipeline_runs",
        "market_data_sync_state",
        "candles_1m",
        "candles_5m",
        "candles_15m",
        "candles_1h",
    )
    # The session fixture has already proved the exact task-owned database and
    # test-only principal before this isolated-only destructive cleanup.
    with natural_e2e_engine.begin() as connection:
        connection.execute(
            text("TRUNCATE " + ", ".join(tables) + " RESTART IDENTITY CASCADE")
        )
    return sessionmaker(
        bind=natural_e2e_engine,
        autoflush=False,
        expire_on_commit=False,
    )
