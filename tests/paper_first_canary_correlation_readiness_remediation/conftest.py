from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
import os
from types import SimpleNamespace

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="session")
def canary_pg_engine() -> Iterator[Engine]:
    raw = os.environ.get("CANARY_REMEDIATION_TEST_PG_URL")
    if not raw:
        pytest.fail("CANARY_REMEDIATION_TEST_PG_URL is required")
    url = make_url(raw)
    if (
        url.get_backend_name() != "postgresql"
        or url.host not in {"127.0.0.1", "localhost", "::1"}
        or not (url.database or "").startswith("paper_canary_remediation_")
    ):
        pytest.fail("task-owned loopback paper_canary_remediation_ PostgreSQL 16 is required")
    engine = create_engine(raw, hide_parameters=True)
    with engine.connect() as connection:
        assert connection.execute(text("SHOW server_version_num")).scalar_one().startswith("16")

    import app.config.settings as settings
    original = settings.get_settings
    settings.get_settings = lambda: SimpleNamespace(database_url=raw)
    config = Config("alembic.ini")
    try:
        with engine.connect() as connection:
            version_table = connection.execute(
                text("SELECT to_regclass('public.alembic_version')")
            ).scalar_one()
        if version_table is not None:
            command.downgrade(config, "0008_engine_orchestrator_freshness_retry")
        else:
            command.upgrade(config, "0008_engine_orchestrator_freshness_retry")
        command.upgrade(config, "0012_paper_account_baseline")
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO paper_account_baselines "
                "(baseline_id,account_id,accounting_session_id,currency,initial_balance,initialized_at,semantic_version) "
                "VALUES ('baseline:canary','paper-primary','session-001','USDT',100,:now,'PAPER_ACCOUNTING/1.0')"
            ), {"now": datetime(2026, 8, 12, tzinfo=timezone.utc)})
        command.upgrade(config, "0014_paper_canary_selection_policy")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0014_paper_canary_selection_policy"
            assert connection.execute(text("SELECT count(*) FROM paper_account_baselines")).scalar_one() == 1
            assert connection.execute(text("SELECT count(*) FROM paper_first_canary_sessions")).scalar_one() == 0
        yield engine
    finally:
        engine.dispose()
        settings.get_settings = original


@pytest.fixture
def canary_sessions(canary_pg_engine: Engine):
    with canary_pg_engine.begin() as connection:
        connection.execute(text(
            "TRUNCATE paper_first_canary_sessions, paper_exit_evaluation_cursors, "
            "paper_journal_entries, paper_exit_decisions, paper_positions, paper_fills, "
            "paper_order_events, paper_orders, paper_execution_commands, paper_simulation_policies "
            "RESTART IDENTITY CASCADE"
        ))
    return sessionmaker(bind=canary_pg_engine, autoflush=False, expire_on_commit=False)
