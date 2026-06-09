from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import get_settings

_ENGINE_CACHE: dict[str, Engine] = {}


def reset_engine_cache() -> None:
    for engine in _ENGINE_CACHE.values():
        engine.dispose()
    _ENGINE_CACHE.clear()


def get_engine(database_url: str | None = None) -> Engine:
    url = database_url or get_settings().database_url
    if url not in _ENGINE_CACHE:
        engine_kwargs = {"pool_pre_ping": True}
        if url.startswith("sqlite"):
            engine_kwargs["connect_args"] = {"check_same_thread": False}
        _ENGINE_CACHE[url] = create_engine(url, **engine_kwargs)
    return _ENGINE_CACHE[url]


def get_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(database_url), autoflush=False, autocommit=False)


def get_session(database_url: str | None = None) -> Session:
    return get_session_factory(database_url)()


def db_session_dependency() -> Iterator[Session]:
    session = get_session()
    try:
        yield session
    finally:
        session.close()
