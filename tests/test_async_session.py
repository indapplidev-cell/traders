from __future__ import annotations

import pytest

from app.config.settings import get_settings
from app.db.async_session import get_async_database_url


def test_async_database_url_uses_explicit_value(monkeypatch, configured_env) -> None:
    """Проверяет приоритет явно заданного ASYNC_DATABASE_URL."""

    _ = configured_env
    monkeypatch.setenv("ASYNC_DATABASE_URL", "postgresql+asyncpg://user:pass@127.0.0.1:5432/traders")
    get_settings.cache_clear()

    assert get_async_database_url() == "postgresql+asyncpg://user:pass@127.0.0.1:5432/traders"


def test_async_database_url_converts_sync_postgres_url(monkeypatch, configured_env) -> None:
    """Проверяет преобразование sync PostgreSQL URL в async URL."""

    _ = configured_env
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@127.0.0.1:5432/traders")
    monkeypatch.delenv("ASYNC_DATABASE_URL", raising=False)
    get_settings.cache_clear()

    assert get_async_database_url() == "postgresql+asyncpg://user:pass@127.0.0.1:5432/traders"


def test_async_database_url_rejects_non_postgres(monkeypatch, configured_env) -> None:
    """Проверяет понятную ошибку для неподдерживаемого sync URL."""

    _ = configured_env
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///async.sqlite3")
    monkeypatch.delenv("ASYNC_DATABASE_URL", raising=False)
    get_settings.cache_clear()

    with pytest.raises(ValueError):
        get_async_database_url()
