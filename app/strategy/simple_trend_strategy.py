"""Простая трендовая стратегия MVP-уровня."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Sequence

from app.db.models import Candle
from app.market.indicator_service import IndicatorSnapshot
from app.strategy.base_strategy import BaseStrategy, StrategyDecision
from app.strategy.strategy_context import StrategyContext
from app.strategy.trade_decision import DecisionType, MarketRegime, TradeDecision


class SimpleTrendStrategy(BaseStrategy):
    """Минимальная стратегия для первого безопасного paper-runtime слоя."""

    name = "simple_trend"
    version = "1.0"

    def decide(self, context: StrategyContext) -> StrategyDecision:
        """Возвращает StrategyDecision по заранее собранному контексту."""

        snapshot = self._coerce_snapshot(context.indicators)
        market_regime = self._coerce_regime(context.market_regime)
        legacy_decision = self.evaluate(
            symbol=context.symbol,
            interval=context.interval,
            candles=context.candles,
            indicator_snapshot=snapshot,
            market_regime=market_regime,
        )

        return StrategyDecision(
            strategy_name=self.name,
            strategy_version=self.version,
            symbol=legacy_decision.symbol,
            interval=legacy_decision.interval,
            action=legacy_decision.decision.value,
            reason=legacy_decision.reason,
            confidence=self._estimate_confidence(legacy_decision, snapshot, market_regime),
            metadata={
                "price": str(legacy_decision.price),
                "market_regime": legacy_decision.regime.value,
            },
        )

    def evaluate(
        self,
        *,
        symbol: str,
        interval: str,
        candles: Sequence[Candle],
        indicator_snapshot: IndicatorSnapshot,
        market_regime: MarketRegime,
    ) -> TradeDecision:
        """Сохраняет backward-compatible контракт Stage 1/2."""

        _ = candles
        close = indicator_snapshot.last_close

        if (
            market_regime == MarketRegime.BULL
            and close > indicator_snapshot.ema_20
            and indicator_snapshot.ema_20 > indicator_snapshot.ema_50
            and indicator_snapshot.rsi_14 <= 70
            and indicator_snapshot.last_volume > indicator_snapshot.volume_sma_20
        ):
            return TradeDecision.build(
                symbol=symbol,
                interval=interval,
                decision=DecisionType.BUY,
                reason=(
                    "Рынок бычий, цена выше EMA20, EMA20 выше EMA50, "
                    "RSI не перегрет, объём выше средней."
                ),
                regime=market_regime,
                price=close,
            )

        if (
            close < indicator_snapshot.ema_50
            or indicator_snapshot.rsi_14 > 75
            or market_regime == MarketRegime.BEAR
        ):
            return TradeDecision.build(
                symbol=symbol,
                interval=interval,
                decision=DecisionType.SELL,
                reason=(
                    "Есть сигнал на выход: цена ниже EMA50, либо RSI слишком высокий, "
                    "либо рынок медвежий."
                ),
                regime=market_regime,
                price=close,
            )

        return TradeDecision.build(
            symbol=symbol,
            interval=interval,
            decision=DecisionType.HOLD,
            reason="Условия для входа или выхода не выполнены.",
            regime=market_regime,
            price=close,
        )

    @staticmethod
    def _coerce_snapshot(indicators: dict[str, Any]) -> IndicatorSnapshot:
        """Поддерживает контекст как с готовым snapshot, так и с плоским dict."""

        snapshot = indicators.get("snapshot")
        if isinstance(snapshot, IndicatorSnapshot):
            return snapshot

        return IndicatorSnapshot(
            ema_20=Decimal(str(indicators["ema_20"])),
            ema_50=Decimal(str(indicators["ema_50"])),
            ema_200=Decimal(str(indicators["ema_200"])),
            rsi_14=Decimal(str(indicators["rsi_14"])),
            atr_14=Decimal(str(indicators["atr_14"])),
            volume_sma_20=Decimal(str(indicators["volume_sma_20"])),
            last_close=Decimal(str(indicators["last_close"])),
            last_volume=Decimal(str(indicators["last_volume"])),
        )

    @staticmethod
    def _coerce_regime(value: str | MarketRegime | None) -> MarketRegime:
        if isinstance(value, MarketRegime):
            return value
        if value is None:
            return MarketRegime.UNKNOWN
        return MarketRegime(str(value).upper())

    @staticmethod
    def _estimate_confidence(
        decision: TradeDecision,
        snapshot: IndicatorSnapshot,
        market_regime: MarketRegime,
    ) -> float:
        """Оценивает уверенность без внедрения сложной математики в MVP."""

        if decision.decision == DecisionType.HOLD:
            return 0.5

        confidence = Decimal("0.55")
        if market_regime == MarketRegime.BULL and decision.decision == DecisionType.BUY:
            confidence += Decimal("0.15")
        if market_regime == MarketRegime.BEAR and decision.decision == DecisionType.SELL:
            confidence += Decimal("0.15")
        if snapshot.last_volume > snapshot.volume_sma_20:
            confidence += Decimal("0.10")
        if snapshot.rsi_14 < 70 and decision.decision == DecisionType.BUY:
            confidence += Decimal("0.05")
        if snapshot.rsi_14 > 60 and decision.decision == DecisionType.SELL:
            confidence += Decimal("0.05")
        return float(min(confidence, Decimal("0.99")))
