"""Базовый интерфейс стратегии."""

from abc import ABC, abstractmethod
from typing import Sequence

from app.db.models import Candle
from app.market.indicator_service import IndicatorSnapshot
from app.strategy.trade_decision import MarketRegime, TradeDecision


class BaseStrategy(ABC):
    """Интерфейс стратегии.

    Важное правило архитектуры: стратегия только анализирует рынок и
    формирует решение. Реальное или paper-исполнение в этот слой не входит.
    """

    @abstractmethod
    def evaluate(
        self,
        *,
        symbol: str,
        interval: str,
        candles: Sequence[Candle],
        indicator_snapshot: IndicatorSnapshot,
        market_regime: MarketRegime,
    ) -> TradeDecision:
        """Возвращает торговое решение по входным данным."""

