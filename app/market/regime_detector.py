"""Определение рыночного режима."""

from decimal import Decimal

from app.market.indicator_service import IndicatorSnapshot
from app.strategy.trade_decision import MarketRegime


class RegimeDetector:
    """Определяет грубый режим рынка.

    Это намеренно простая MVP-логика. Она не претендует на полноту,
    не гарантирует прибыль и служит только базовым фильтром режима.
    """

    VOLATILE_ATR_RATIO = Decimal("0.03")
    SIDEWAYS_EMA_DISTANCE_RATIO = Decimal("0.003")

    def detect(self, snapshot: IndicatorSnapshot) -> MarketRegime:
        """Возвращает режим рынка на основе индикаторов."""

        if snapshot.last_close <= 0:
            return MarketRegime.UNKNOWN

        atr_ratio = snapshot.atr_14 / snapshot.last_close
        ema_distance_ratio = abs(snapshot.ema_20 - snapshot.ema_50) / snapshot.last_close

        if atr_ratio >= self.VOLATILE_ATR_RATIO:
            return MarketRegime.VOLATILE

        if (
            snapshot.last_close > snapshot.ema_200
            and snapshot.ema_50 > snapshot.ema_200
            and Decimal("45") <= snapshot.rsi_14 <= Decimal("75")
        ):
            return MarketRegime.BULL

        if (
            snapshot.last_close < snapshot.ema_200
            and snapshot.ema_50 < snapshot.ema_200
            and snapshot.rsi_14 < Decimal("55")
        ):
            return MarketRegime.BEAR

        if ema_distance_ratio <= self.SIDEWAYS_EMA_DISTANCE_RATIO and Decimal("40") <= snapshot.rsi_14 <= Decimal("60"):
            return MarketRegime.SIDEWAYS

        return MarketRegime.UNKNOWN

