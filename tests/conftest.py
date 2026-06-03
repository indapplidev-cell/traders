from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import get_settings
from app.db.async_session import get_async_engine, get_async_session_factory
from app.db.base import Base
from app.db.session import get_engine, get_session_factory


def _clear_caches() -> None:
    """Сбрасывает кеш настроек и ленивых фабрик между тестами."""

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    get_async_engine.cache_clear()
    get_async_session_factory.cache_clear()


@pytest.fixture
def configured_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> str:
    """Готовит изолированное окружение и файловую SQLite-БД для тестов."""

    database_url = f"sqlite+pysqlite:///{tmp_path / 'test.sqlite3'}"
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.delenv("ASYNC_DATABASE_URL", raising=False)
    monkeypatch.setenv("BINANCE_PUBLIC_REST_URL", "https://api.binance.com")
    monkeypatch.setenv("DEFAULT_SYMBOL", "BTCUSDT")
    monkeypatch.setenv("DEFAULT_INTERVAL", "15m")
    monkeypatch.setenv("DEFAULT_CANDLE_LIMIT", "300")
    monkeypatch.setenv("STRATEGY_DEFAULT_NAME", "simple_trend")
    monkeypatch.setenv("STRATEGY_MIN_CONFIDENCE", "0.55")
    monkeypatch.setenv("STRATEGY_LOOP_SLEEP_SECONDS", "0")
    monkeypatch.setenv("STRATEGY_MAX_TICKS", "10")
    monkeypatch.setenv("STRATEGY_DEFAULT_CANDLE_LIMIT", "300")
    monkeypatch.setenv("PAPER_INITIAL_BALANCE_USDT", "1000")
    monkeypatch.setenv("PAPER_POSITION_SIZE_FRACTION", "0.01")
    monkeypatch.setenv("PAPER_MAX_OPEN_POSITIONS", "1")
    monkeypatch.chdir(tmp_path)
    _clear_caches()
    yield database_url
    _clear_caches()


@pytest.fixture
def sqlite_session(configured_env: str) -> Session:
    """Создаёт изолированную SQLAlchemy-сессию с текущими моделями."""

    engine = create_engine(configured_env, future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
        session.commit()
    finally:
        session.close()
        engine.dispose()
