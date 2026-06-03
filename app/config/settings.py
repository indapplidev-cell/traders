"""Centralized application settings."""

from __future__ import annotations

from decimal import Decimal
from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ALLOWED_BINANCE_INTERVALS = {
    "1m",
    "3m",
    "5m",
    "15m",
    "30m",
    "1h",
    "2h",
    "4h",
    "6h",
    "8h",
    "12h",
    "1d",
    "3d",
    "1w",
    "1M",
}


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="local", alias="APP_ENV")
    database_url: str = Field(alias="DATABASE_URL")
    async_database_url: str | None = Field(default=None, alias="ASYNC_DATABASE_URL")

    binance_public_rest_url: str = Field(alias="BINANCE_PUBLIC_REST_URL")

    default_symbol: str = Field(default="BTCUSDT", alias="DEFAULT_SYMBOL")
    default_interval: str = Field(default="15m", alias="DEFAULT_INTERVAL")
    default_candle_limit: int = Field(default=300, alias="DEFAULT_CANDLE_LIMIT")

    strategy_default_name: str = Field(default="simple_trend", alias="STRATEGY_DEFAULT_NAME")
    strategy_min_confidence: Decimal = Field(default=Decimal("0.55"), alias="STRATEGY_MIN_CONFIDENCE")
    strategy_loop_sleep_seconds: Decimal = Field(default=Decimal("60"), alias="STRATEGY_LOOP_SLEEP_SECONDS")
    strategy_max_ticks: int = Field(default=10, alias="STRATEGY_MAX_TICKS")
    strategy_default_candle_limit: int = Field(default=300, alias="STRATEGY_DEFAULT_CANDLE_LIMIT")

    paper_initial_balance_usdt: Decimal = Field(
        default=Decimal("1000"),
        alias="PAPER_INITIAL_BALANCE_USDT",
    )
    paper_position_size_fraction: Decimal = Field(
        default=Decimal("0.01"),
        validation_alias=AliasChoices("PAPER_POSITION_SIZE_FRACTION", "PAPER_RISK_PER_TRADE"),
        alias="PAPER_POSITION_SIZE_FRACTION",
    )
    paper_max_open_positions: int = Field(default=1, alias="PAPER_MAX_OPEN_POSITIONS")

    @field_validator("paper_position_size_fraction")
    @classmethod
    def validate_paper_position_size_fraction(cls, value: Decimal) -> Decimal:
        if value <= 0 or value > 1:
            raise ValueError("PAPER_POSITION_SIZE_FRACTION must be in range 0 < value <= 1.")
        return value

    @field_validator("default_candle_limit")
    @classmethod
    def validate_default_candle_limit(cls, value: int) -> int:
        if value < 250:
            raise ValueError("DEFAULT_CANDLE_LIMIT must not be less than 250.")
        return value

    @field_validator("strategy_default_name")
    @classmethod
    def validate_strategy_default_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("STRATEGY_DEFAULT_NAME must not be empty.")
        return normalized

    @field_validator("strategy_min_confidence")
    @classmethod
    def validate_strategy_min_confidence(cls, value: Decimal) -> Decimal:
        if value < 0 or value > 1:
            raise ValueError("STRATEGY_MIN_CONFIDENCE must be in range 0 <= value <= 1.")
        return value

    @field_validator("strategy_loop_sleep_seconds")
    @classmethod
    def validate_strategy_loop_sleep_seconds(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("STRATEGY_LOOP_SLEEP_SECONDS must be >= 0.")
        return value

    @field_validator("strategy_max_ticks")
    @classmethod
    def validate_strategy_max_ticks(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("STRATEGY_MAX_TICKS must be > 0.")
        return value

    @field_validator("strategy_default_candle_limit")
    @classmethod
    def validate_strategy_default_candle_limit(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("STRATEGY_DEFAULT_CANDLE_LIMIT must be > 0.")
        return value

    @field_validator("default_symbol")
    @classmethod
    def validate_default_symbol(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("DEFAULT_SYMBOL must not be empty.")
        return normalized

    @field_validator("default_interval")
    @classmethod
    def validate_default_interval(cls, value: str) -> str:
        normalized = value.strip()
        if normalized not in ALLOWED_BINANCE_INTERVALS:
            raise ValueError(
                "DEFAULT_INTERVAL must be one of the supported Binance intervals: "
                + ", ".join(sorted(ALLOWED_BINANCE_INTERVALS))
                + "."
            )
        return normalized

    @field_validator("async_database_url")
    @classmethod
    def validate_async_database_url(cls, value: str | None) -> str | None:
        if value is None:
            return value

        normalized = value.strip()
        if not normalized.startswith("postgresql+asyncpg://"):
            raise ValueError("ASYNC_DATABASE_URL must start with postgresql+asyncpg://")
        return normalized


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cache settings for the lifetime of the process."""

    return Settings()
