"""SQLAlchemy 2.x engine and session helpers."""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.engine_market_data.db.settings import MarketDataDatabaseSettings


def create_market_data_engine(database_url: str | None = None, **kwargs: object) -> Engine:
    url = database_url or MarketDataDatabaseSettings.from_environment().database_url
    return create_engine(url, pool_pre_ping=True, **kwargs)


def create_market_data_session_factory(
    database_url: str | None = None, *, engine: Engine | None = None,
) -> sessionmaker[Session]:
    bind = engine or create_market_data_engine(database_url)
    return sessionmaker(bind=bind, expire_on_commit=False)
