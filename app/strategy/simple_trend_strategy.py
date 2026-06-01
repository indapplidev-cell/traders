"""Простая трендовая стратегия MVP-уровня."""

from typing import Sequence

from app.db.models import Candle
from app.market.indicator_service import IndicatorSnapshot
from app.strategy.base_strategy import BaseStrategy
from app.strategy.trade_decision import DecisionType, MarketRegime, TradeDecision


class SimpleTrendStrategy(BaseStrategy):
    """Минимальная стратегия для первого этапа.

    Логика намеренно простая: она должна быть читаемой, тестируемой
    и безопасной для paper trading, а не максимально прибыльной.
    """

    def evaluate(
        self,
        *,
        symbol: str,
        interval: str,
        candles: Sequence[Candle],
        indicator_snapshot: IndicatorSnapshot,
        market_regime: MarketRegime,
    ) -> TradeDecision:
        """Формирует BUY / SELL / HOLD по заданным правилам."""

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
                reason="Рынок бычий, цена выше EMA20, EMA20 выше EMA50, RSI не перегрет, объём выше средней.",
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
                reason="Есть сигнал на выход: цена ниже EMA50, либо RSI слишком высокий, либо рынок медвежий.",
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

