"""Database settings scoped to market-data synchronization."""

from dataclasses import dataclass
import os

from app.config.settings import get_settings


@dataclass(frozen=True, slots=True)
class MarketDataDatabaseSettings:
    database_url: str

    @classmethod
    def from_environment(cls) -> "MarketDataDatabaseSettings":
        return cls(os.getenv("MARKET_DATA_DATABASE_URL", get_settings().database_url))
