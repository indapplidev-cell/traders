"""Централизованная конфигурация приложения."""

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
    """Настройки приложения.

    Все значения вынесены в переменные окружения, чтобы не хранить
    инфраструктурные параметры и риск-настройки прямо в коде.
    """

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

    paper_initial_balance_usdt: Decimal = Field(
        default=Decimal("1000"),
        alias="PAPER_INITIAL_BALANCE_USDT",
    )
    # Новое имя отражает фактическую семантику: пока это не настоящий риск
    # на сделку, а просто доля баланса, выделяемая под размер paper-позиции.
    paper_position_size_fraction: Decimal = Field(
        default=Decimal("0.01"),
        validation_alias=AliasChoices("PAPER_POSITION_SIZE_FRACTION", "PAPER_RISK_PER_TRADE"),
        alias="PAPER_POSITION_SIZE_FRACTION",
    )
    paper_max_open_positions: int = Field(
        default=1,
        alias="PAPER_MAX_OPEN_POSITIONS",
    )

    @field_validator("paper_position_size_fraction")
    @classmethod
    def validate_paper_position_size_fraction(cls, value: Decimal) -> Decimal:
        """Гарантирует корректную долю баланса для paper-позиции."""

        if value <= 0 or value > 1:
            raise ValueError("PAPER_POSITION_SIZE_FRACTION должен быть в диапазоне 0 < value <= 1.")
        return value

    @field_validator("default_candle_limit")
    @classmethod
    def validate_default_candle_limit(cls, value: int) -> int:
        """Не даёт задать слишком маленький лимит свечей для индикаторов."""

        if value < 250:
            raise ValueError("DEFAULT_CANDLE_LIMIT должен быть не меньше 250.")
        return value

    @field_validator("default_symbol")
    @classmethod
    def validate_default_symbol(cls, value: str) -> str:
        """Запрещает пустой символ по умолчанию."""

        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("DEFAULT_SYMBOL не должен быть пустым.")
        return normalized

    @field_validator("default_interval")
    @classmethod
    def validate_default_interval(cls, value: str) -> str:
        """Проверяет, что interval входит в список поддерживаемых Binance значений."""

        normalized = value.strip()
        if normalized not in ALLOWED_BINANCE_INTERVALS:
            raise ValueError(
                "DEFAULT_INTERVAL должен быть одним из допустимых Binance interval: "
                + ", ".join(sorted(ALLOWED_BINANCE_INTERVALS))
                + "."
            )
        return normalized

    @field_validator("async_database_url")
    @classmethod
    def validate_async_database_url(cls, value: str | None) -> str | None:
        """Проверяет, что явный async URL использует драйвер asyncpg."""

        if value is None:
            return value

        normalized = value.strip()
        if not normalized.startswith("postgresql+asyncpg://"):
            raise ValueError("ASYNC_DATABASE_URL должен начинаться с postgresql+asyncpg://")
        return normalized


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Кеширует настройки на время жизни процесса.

    Для CLI-команд этого достаточно: каждая команда живёт недолго,
    а постоянное повторное чтение `.env` здесь не даёт пользы.
    """

    return Settings()
