"""Готовый контекст, который runtime передаёт стратегии."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from app.config.settings import Settings
from app.db.models import Candle


@dataclass(slots=True)
class StrategyContext:
    """Контекст одного tick без прямых зависимостей на инфраструктуру."""

    symbol: str
    interval: str
    candles: Sequence[Candle]
    indicators: dict[str, Any]
    market_regime: str | None
    open_positions: Sequence[Any]
    portfolio_state: dict[str, Any]
    last_decisions: Sequence[Any]
    settings: Settings
