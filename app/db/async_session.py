"""Асинхронная SQLAlchemy-связка для будущих long-running сервисов."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config.settings import get_settings


def get_async_database_url() -> str:
    """Возвращает async URL для PostgreSQL.

    В production лучше задавать `ASYNC_DATABASE_URL` явно. Если он не задан,
    пытаемся безопасно преобразовать sync `DATABASE_URL`.
    """

    settings = get_settings()
    if settings.async_database_url:
        return settings.async_database_url

    database_url = settings.database_url
    if database_url.startswith("postgresql+psycopg://"):
        return database_url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    raise ValueError("Асинхронная БД поддерживает только PostgreSQL URL.")


@lru_cache(maxsize=1)
def get_async_engine() -> AsyncEngine:
    """Лениво создаёт async engine.

    Engine не создаётся на импорте, чтобы `CLI --help` не зависел от `.env`
    и реальной доступности PostgreSQL.
    """

    return create_async_engine(
        get_async_database_url(),
        pool_pre_ping=True,
        future=True,
    )


@lru_cache(maxsize=1)
def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """Лениво создаёт фабрику async-сессий."""

    return async_sessionmaker(
        bind=get_async_engine(),
        expire_on_commit=False,
        class_=AsyncSession,
    )


@asynccontextmanager
async def async_session_scope() -> AsyncIterator[AsyncSession]:
    """Открывает async-сессию с commit/rollback логикой."""

    session_factory = get_async_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
