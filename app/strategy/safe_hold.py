"""Стратегия-заглушка, которая всегда возвращает HOLD."""

from __future__ import annotations

from app.strategy.base_strategy import BaseStrategy, StrategyDecision
from app.strategy.strategy_context import StrategyContext


class SafeHoldStrategy(BaseStrategy):
    """Безопасная paper-only стратегия без торгового сигнала."""

    name = "safe_hold"
    version = "1.0"

    def decide(self, context: StrategyContext) -> StrategyDecision:
        regime = str(context.market_regime or "UNKNOWN").strip().upper() or "UNKNOWN"
        reason = "Стратегия safe_hold всегда возвращает HOLD и не открывает позицию."

        return StrategyDecision(
            strategy_name=self.name,
            strategy_version=self.version,
            symbol=context.symbol,
            interval=context.interval,
            action="HOLD",
            reason=reason,
            confidence=1.0,
            metadata={"market_regime": regime},
        )
