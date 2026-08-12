from __future__ import annotations

from collections.abc import Iterator
import os
from types import SimpleNamespace

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url


@pytest.fixture(scope="session")
def source_contract_pg_engine() -> Iterator[Engine]:
    raw = os.environ.get("SOURCE_CONTRACT_TEST_PG_URL")
    if not raw:
        pytest.fail("SOURCE_CONTRACT_TEST_PG_URL is required")
    url = make_url(raw)
    if (url.get_backend_name() != "postgresql"
            or url.host not in {"127.0.0.1", "localhost", "::1"}
            or not (url.database or "").startswith("paper_source_contract_")):
        pytest.fail("task-owned loopback paper_source_contract_ PostgreSQL 16 is required")
    engine = create_engine(raw, hide_parameters=True)
    with engine.connect() as connection:
        assert connection.execute(text("SHOW server_version_num")).scalar_one().startswith("16")
    import app.config.settings as settings
    original = settings.get_settings
    settings.get_settings = lambda: SimpleNamespace(database_url=raw)
    config = Config("alembic.ini")
    try:
        with engine.connect() as connection:
            exists = connection.execute(text("SELECT to_regclass('public.alembic_version')")).scalar_one()
        if exists is not None:
            command.downgrade(config, "0008_engine_orchestrator_freshness_retry")
        else:
            command.upgrade(config, "0008_engine_orchestrator_freshness_retry")
        yield engine
    finally:
        engine.dispose()
        settings.get_settings = original
