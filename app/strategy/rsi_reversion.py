"""RSI mean reversion стратегия для paper-only sandbox."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from app.strategy.base_strategy import BaseStrategy, StrategyDecision
from app.strategy.strategy_context import StrategyContext


class RsiReversionStrategy(BaseStrategy):
    """Сигнал на возврат к среднему по RSI14."""

    name = "rsi_reversion"
    version = "1.0"

    def decide(self, context: StrategyContext) -> StrategyDecision:
        rsi_14 = self._read_decimal(context, "rsi_14")
        if rsi_14 is None:
            return self._hold(context, "Недостаточно данных для rsi_reversion: нужен rsi_14.")

        if rsi_14 < Decimal("25"):
            action = "BUY"
            confidence = 0.80
            threshold = "rsi_14 < 25"
        elif rsi_14 < Decimal("30"):
            action = "BUY"
            confidence = 0.70
            threshold = "rsi_14 < 30"
        elif rsi_14 > Decimal("75"):
            action = "SELL"
            confidence = 0.80
            threshold = "rsi_14 > 75"
        elif rsi_14 > Decimal("70"):
            action = "SELL"
            confidence = 0.70
            threshold = "rsi_14 > 70"
        else:
            return self._hold(
                context,
                f"rsi_reversion: rsi14={rsi_14}, экстремумов нет, решение HOLD.",
                metadata={"rsi_14": str(rsi_14), "threshold": "inside-range"},
            )

        return StrategyDecision(
            strategy_name=self.name,
            strategy_version=self.version,
            symbol=context.symbol,
            interval=context.interval,
            action=action,
            reason=f"rsi_reversion: rsi14={rsi_14}, threshold={threshold}, decision={action}.",
            confidence=confidence,
            metadata={"rsi_14": str(rsi_14), "threshold": threshold},
        )

    @staticmethod
    def _read_decimal(context: StrategyContext, key: str) -> Decimal | None:
        value = context.indicators.get(key)
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None

    def _hold(
        self,
        context: StrategyContext,
        reason: str,
        metadata: dict[str, str] | None = None,
    ) -> StrategyDecision:
        return StrategyDecision(
            strategy_name=self.name,
            strategy_version=self.version,
            symbol=context.symbol,
            interval=context.interval,
            action="HOLD",
            reason=reason,
            confidence=0.55,
            metadata=metadata or {},
        )
