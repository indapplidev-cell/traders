from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config.settings import Settings


def build_settings(monkeypatch, **overrides) -> Settings:
    """Собирает валидный набор env-переменных и позволяет точечно его ломать."""

    values = {
        "APP_ENV": "test",
        "DATABASE_URL": "sqlite+pysqlite:///settings.sqlite3",
        "ASYNC_DATABASE_URL": "postgresql+asyncpg://traders:traders@localhost:5432/traders",
        "BINANCE_PUBLIC_REST_URL": "https://api.binance.com",
        "DEFAULT_SYMBOL": "BTCUSDT",
        "DEFAULT_INTERVAL": "15m",
        "DEFAULT_CANDLE_LIMIT": "300",
        "STRATEGY_DEFAULT_NAME": "simple_trend",
        "STRATEGY_MIN_CONFIDENCE": "0.55",
        "STRATEGY_LOOP_SLEEP_SECONDS": "60",
        "STRATEGY_MAX_TICKS": "10",
        "STRATEGY_DEFAULT_CANDLE_LIMIT": "300",
        "PAPER_INITIAL_BALANCE_USDT": "1000",
        "PAPER_POSITION_SIZE_FRACTION": "0.01",
        "PAPER_MAX_OPEN_POSITIONS": "1",
    }
    values.update(overrides)
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    return Settings()


def test_valid_paper_position_size_fraction_passes(monkeypatch) -> None:
    settings = build_settings(monkeypatch, PAPER_POSITION_SIZE_FRACTION="0.25")
    assert str(settings.paper_position_size_fraction) == "0.25"


@pytest.mark.parametrize("value", ["0", "-0.1", "1.1"])
def test_invalid_paper_position_size_fraction_fails(monkeypatch, value: str) -> None:
    with pytest.raises(ValidationError):
        build_settings(monkeypatch, PAPER_POSITION_SIZE_FRACTION=value)


def test_default_candle_limit_below_minimum_fails(monkeypatch) -> None:
    with pytest.raises(ValidationError):
        build_settings(monkeypatch, DEFAULT_CANDLE_LIMIT="249")


def test_invalid_default_interval_fails(monkeypatch) -> None:
    with pytest.raises(ValidationError):
        build_settings(monkeypatch, DEFAULT_INTERVAL="7m")


@pytest.mark.parametrize("value", ["", "   "])
def test_empty_default_symbol_fails(monkeypatch, value: str) -> None:
    with pytest.raises(ValidationError):
        build_settings(monkeypatch, DEFAULT_SYMBOL=value)


def test_invalid_async_database_url_fails(monkeypatch) -> None:
    with pytest.raises(ValidationError):
        build_settings(monkeypatch, ASYNC_DATABASE_URL="postgresql+psycopg://traders:traders@localhost:5432/traders")
