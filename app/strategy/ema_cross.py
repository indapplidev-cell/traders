"""EMA crossover стратегия для paper-only sandbox."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from app.strategy.base_strategy import BaseStrategy, StrategyDecision
from app.strategy.strategy_context import StrategyContext


class EmaCrossStrategy(BaseStrategy):
    """Сигнал по пересечению EMA20 и EMA50."""

    name = "ema_cross"
    version = "1.0"

    def decide(self, context: StrategyContext) -> StrategyDecision:
        ema_20 = self._read_decimal(context, "ema_20")
        ema_50 = self._read_decimal(context, "ema_50")
        last_close = self._read_decimal(context, "last_close")

        if ema_20 is None or ema_50 is None or last_close is None or last_close <= 0:
            return self._hold(
                context,
                "Недостаточно данных для ema_cross: нужны ema_20, ema_50 и положительный last_close.",
            )

        spread = ema_20 - ema_50
        spread_ratio = abs(spread) / last_close

        if spread_ratio < Decimal("0.001"):
            return self._hold(
                context,
                (
                    "ema_cross: спред EMA20/EMA50 слишком мал "
                    f"(ema20={ema_20}, ema50={ema_50}, spread={spread}, ratio={spread_ratio:.6f})."
                ),
                metadata={
                    "ema_20": str(ema_20),
                    "ema_50": str(ema_50),
                    "spread": str(spread),
                    "spread_ratio": str(spread_ratio),
                },
            )

        if ema_20 > ema_50:
            action = "BUY"
        elif ema_20 < ema_50:
            action = "SELL"
        else:
            return self._hold(
                context,
                (
                    "ema_cross: EMA20 равна EMA50, сигнал отсутствует "
                    f"(ema20={ema_20}, ema50={ema_50}, spread={spread})."
                ),
                metadata={
                    "ema_20": str(ema_20),
                    "ema_50": str(ema_50),
                    "spread": str(spread),
                    "spread_ratio": str(spread_ratio),
                },
            )

        confidence = 0.65
        if spread_ratio > Decimal("0.010"):
            confidence = 0.85
        elif spread_ratio > Decimal("0.005"):
            confidence = 0.75

        return StrategyDecision(
            strategy_name=self.name,
            strategy_version=self.version,
            symbol=context.symbol,
            interval=context.interval,
            action=action,
            reason=(
                "ema_cross: "
                f"ema20={ema_20}, ema50={ema_50}, spread={spread}, ratio={spread_ratio:.6f}, decision={action}."
            ),
            confidence=confidence,
            metadata={
                "ema_20": str(ema_20),
                "ema_50": str(ema_50),
                "spread": str(spread),
                "spread_ratio": str(spread_ratio),
            },
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
