from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, delete, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.db.paper_models import (
    PaperExecutionCommandRecord,
    PaperExitEvaluationCursorRecord,
    PaperExitDecisionRecord,
    PaperFillRecord,
    PaperJournalEntryRecord,
    PaperOrderEventRecord,
    PaperOrderRecord,
    PaperPositionRecord,
)
from app.config.settings import get_settings

@pytest.fixture(scope="session")
def repository_postgres_engine() -> Iterator[Engine]:
    raw = os.environ.get("PAPER_TEST_DATABASE_URL")
    if not raw:
        pytest.fail("PAPER_TEST_DATABASE_URL is required")
    url = make_url(raw)
    if (
        url.get_backend_name() != "postgresql"
        or url.host not in {"127.0.0.1", "localhost", "::1"}
        or not (url.database or "").startswith("paper_test_")
    ):
        pytest.fail("isolated loopback paper_test_ PostgreSQL is required")
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", raw.replace("%", "%%"))
    engine = create_engine(raw, hide_parameters=True)
    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = raw
    get_settings.cache_clear()
    with engine.connect() as connection:
        revision = connection.execute(
            text("SELECT to_regclass('public.alembic_version')")
        ).scalar_one()
    if revision is None:
        command.upgrade(
            config,
            "0011_paper_close_causal_boundary_and_exit_evaluation_cursor",
        )
    else:
        command.upgrade(
            config,
            "0011_paper_close_causal_boundary_and_exit_evaluation_cursor",
        )
    yield engine
    engine.dispose()
    get_settings.cache_clear()
    if previous_database_url is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = previous_database_url


@pytest.fixture
def paper_session_factory(repository_postgres_engine) -> Iterator[sessionmaker]:
    engine: Engine = repository_postgres_engine
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with engine.begin() as connection:
        for model in (
            PaperJournalEntryRecord,
            PaperExitEvaluationCursorRecord,
            PaperExitDecisionRecord,
            PaperPositionRecord,
            PaperFillRecord,
            PaperOrderEventRecord,
            PaperOrderRecord,
            PaperExecutionCommandRecord,
        ):
            connection.execute(delete(model))
    yield factory
    engine.dispose()
