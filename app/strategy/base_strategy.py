"""Базовый контракт стратегии и её нормализованное решение."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

from app.strategy.strategy_context import StrategyContext


StrategyAction = Literal["BUY", "SELL", "HOLD"]


@dataclass(slots=True)
class StrategyDecision:
    """Нормализованное решение стратегии без привязки к исполнению."""

    strategy_name: str
    strategy_version: str
    symbol: str
    interval: str
    action: StrategyAction
    reason: str
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.symbol = self.symbol.strip().upper()
        self.interval = self.interval.strip()
        self.reason = self.reason.strip()
        if not self.reason:
            raise ValueError("reason не должен быть пустым")
        if self.action not in {"BUY", "SELL", "HOLD"}:
            raise ValueError("action должен быть одним из BUY/SELL/HOLD")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence должен быть в диапазоне от 0.0 до 1.0")
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata должен быть dict[str, Any]")


class BaseStrategy(ABC):
    """Базовый интерфейс стратегии.

    Стратегия получает уже собранный контекст и возвращает только решение.
    Она не должна сама ходить в БД, Binance или слой исполнения.
    """

    name: str
    version: str

    @abstractmethod
    def decide(self, context: StrategyContext) -> StrategyDecision:
        """Возвращает нормализованное решение стратегии для одного tick."""
