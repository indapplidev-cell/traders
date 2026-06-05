"""Breakout стратегия с подтверждением объёмом для paper-only sandbox."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from app.strategy.base_strategy import BaseStrategy, StrategyDecision
from app.strategy.strategy_context import StrategyContext


class BreakoutVolumeStrategy(BaseStrategy):
    """Сигнал breakout при подтверждении тренда объёмом."""

    name = "breakout_volume"
    version = "1.0"

    def decide(self, context: StrategyContext) -> StrategyDecision:
        last_close = self._read_decimal(context, "last_close")
        last_volume = self._read_decimal(context, "last_volume")
        volume_sma_20 = self._read_decimal(context, "volume_sma_20")
        ema_20 = self._read_decimal(context, "ema_20")
        ema_50 = self._read_decimal(context, "ema_50")

        if (
            last_close is None
            or last_volume is None
            or volume_sma_20 is None
            or ema_20 is None
            or ema_50 is None
            or volume_sma_20 <= 0
        ):
            return self._hold(
                context,
                "Недостаточно данных для breakout_volume: нужны close, volume, volume_sma_20, ema_20 и ema_50.",
            )

        volume_ratio = last_volume / volume_sma_20
        trend = "flat"

        if last_volume <= volume_sma_20:
            return self._hold(
                context,
                (
                    "breakout_volume: объём не подтверждает движение "
                    f"(close={last_close}, volume={last_volume}, volume_sma_20={volume_sma_20}, "
                    f"volume_ratio={volume_ratio:.6f}, trend={trend}, decision=HOLD)."
                ),
                metadata={
                    "last_close": str(last_close),
                    "last_volume": str(last_volume),
                    "volume_sma_20": str(volume_sma_20),
                    "volume_ratio": str(volume_ratio),
                    "ema_20": str(ema_20),
                    "ema_50": str(ema_50),
                },
            )

        if last_close > ema_20 and ema_20 > ema_50:
            action = "BUY"
            trend = "bullish"
        elif last_close < ema_20 and ema_20 < ema_50:
            action = "SELL"
            trend = "bearish"
        else:
            return self._hold(
                context,
                (
                    "breakout_volume: объём выше среднего, но направление EMA не подтверждено "
                    f"(close={last_close}, volume={last_volume}, volume_sma_20={volume_sma_20}, "
                    f"volume_ratio={volume_ratio:.6f}, trend={trend}, decision=HOLD)."
                ),
                metadata={
                    "last_close": str(last_close),
                    "last_volume": str(last_volume),
                    "volume_sma_20": str(volume_sma_20),
                    "volume_ratio": str(volume_ratio),
                    "ema_20": str(ema_20),
                    "ema_50": str(ema_50),
                },
            )

        confidence = 0.65
        if volume_ratio >= Decimal("2.0"):
            confidence = 0.85
        elif volume_ratio >= Decimal("1.5"):
            confidence = 0.75

        return StrategyDecision(
            strategy_name=self.name,
            strategy_version=self.version,
            symbol=context.symbol,
            interval=context.interval,
            action=action,
            reason=(
                "breakout_volume: "
                f"close={last_close}, volume={last_volume}, volume_sma_20={volume_sma_20}, "
                f"volume_ratio={volume_ratio:.6f}, trend={trend}, decision={action}."
            ),
            confidence=confidence,
            metadata={
                "last_close": str(last_close),
                "last_volume": str(last_volume),
                "volume_sma_20": str(volume_sma_20),
                "volume_ratio": str(volume_ratio),
                "ema_20": str(ema_20),
                "ema_50": str(ema_50),
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
