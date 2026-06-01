"""Создание SQLAlchemy engine и сессий."""

from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import get_settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Лениво создаёт SQLAlchemy engine.

    Это важно для CLI: простые команды вроде `--help` не должны падать
    только потому, что переменные окружения или база ещё не подготовлены.
    """

    settings = get_settings()
    # Используется синхронный engine, потому что CLI-команды короткоживущие,
    # а требования этапа сосредоточены на корректности бизнес-логики и хранения данных.
    return create_engine(settings.database_url, future=True)


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    """Лениво создаёт фабрику SQLAlchemy-сессий."""

    return sessionmaker(
        bind=get_engine(),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


@contextmanager
def session_scope() -> Iterator[Session]:
    """Открывает транзакционную сессию с автоматическим commit/rollback.

    Такой контекст упрощает работу сервисов и исключает тихое забывание
    `rollback`, если внутри возникло исключение.
    """

    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
