"""Database settings scoped to market-data synchronization."""

from dataclasses import dataclass
import os

from app.config.settings import get_settings


@dataclass(frozen=True, slots=True)
class MarketDataDatabaseSettings:
    database_url: str

    @classmethod
    def from_environment(cls) -> "MarketDataDatabaseSettings":
        database_url = os.getenv("MARKET_DATA_DATABASE_URL")
        if database_url:
            return cls(database_url)
        return cls(get_settings().require_database_url())
