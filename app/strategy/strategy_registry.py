"""Лёгкий реестр стратегий без зависимостей на CLI и БД."""

from __future__ import annotations

from app.strategy.base_strategy import BaseStrategy
from app.strategy.breakout_volume import BreakoutVolumeStrategy
from app.strategy.ema_cross import EmaCrossStrategy
from app.strategy.rsi_reversion import RsiReversionStrategy
from app.strategy.safe_hold import SafeHoldStrategy
from app.strategy.simple_trend_strategy import SimpleTrendStrategy


class StrategyRegistry:
    """Хранит доступные стратегии по имени."""

    def __init__(self) -> None:
        self._strategies: dict[str, BaseStrategy] = {}

    def list_strategies(self) -> list[str]:
        return sorted(self._strategies)

    def get_strategy(self, name: str) -> BaseStrategy:
        normalized = name.strip()
        strategy = self._strategies.get(normalized)
        if strategy is None:
            raise ValueError(f"Unknown strategy: {name}")
        return strategy

    def register_strategy(self, strategy: BaseStrategy) -> None:
        self._strategies[strategy.name] = strategy


default_registry = StrategyRegistry()
default_registry.register_strategy(SimpleTrendStrategy())
default_registry.register_strategy(SafeHoldStrategy())
default_registry.register_strategy(EmaCrossStrategy())
default_registry.register_strategy(RsiReversionStrategy())
default_registry.register_strategy(BreakoutVolumeStrategy())


def list_strategies() -> list[str]:
    return default_registry.list_strategies()


def get_strategy(name: str) -> BaseStrategy:
    return default_registry.get_strategy(name)


def register_strategy(strategy: BaseStrategy) -> None:
    default_registry.register_strategy(strategy)
