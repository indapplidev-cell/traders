"""Сервис чтения свечей и построения торгового анализа."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Candle
from app.market.indicator_service import IndicatorService, IndicatorSnapshot
from app.market.regime_detector import RegimeDetector
from app.strategy.simple_trend_strategy import SimpleTrendStrategy
from app.strategy.trade_decision import MarketRegime, TradeDecision


@dataclass(slots=True)
class AnalysisResult:
    """Результат полного анализа рынка на одной закрытой свече."""

    candles: list[Candle]
    latest_candle: Candle
    indicator_snapshot: IndicatorSnapshot
    market_regime: MarketRegime
    strategy_decision: TradeDecision


class MarketAnalysisService:
    """Изолирует рыночный анализ от CLI-команд."""

    def __init__(
        self,
        indicator_service: IndicatorService | None = None,
        regime_detector: RegimeDetector | None = None,
        strategy: SimpleTrendStrategy | None = None,
    ) -> None:
        self.indicator_service = indicator_service or IndicatorService()
        self.regime_detector = regime_detector or RegimeDetector()
        self.strategy = strategy or SimpleTrendStrategy()

    def load_candles(self, session: Session, symbol: str, interval: str, limit: int) -> list[Candle]:
        """Читает свечи из БД в хронологическом порядке."""

        rows = session.execute(
            select(Candle)
            .where(Candle.symbol == symbol.upper(), Candle.interval == interval)
            .order_by(Candle.open_time.desc())
            .limit(limit)
        ).scalars().all()
        return list(reversed(rows))

    def analyze(
        self,
        *,
        symbol: str,
        interval: str,
        candles: Sequence[Candle],
    ) -> AnalysisResult:
        """Строит индикаторы, режим и решение стратегии по заданным свечам."""

        candle_list = list(candles)
        if not candle_list:
            raise ValueError("В базе нет свечей для анализа. Сначала загрузите данные командой fetch-candles.")

        snapshot = self.indicator_service.calculate(candle_list)
        regime = self.regime_detector.detect(snapshot)
        decision = self.strategy.evaluate(
            symbol=symbol.upper(),
            interval=interval,
            candles=candle_list,
            indicator_snapshot=snapshot,
            market_regime=regime,
        )
        return AnalysisResult(
            candles=candle_list,
            latest_candle=candle_list[-1],
            indicator_snapshot=snapshot,
            market_regime=regime,
            strategy_decision=decision,
        )

    def load_candles_since(self, session: Session, symbol: str, interval: str, since: datetime) -> list[Candle]:
        """Читает все свечи начиная с указанного времени в хронологическом порядке."""

        return (
            session.execute(
                select(Candle)
                .where(
                    Candle.symbol == symbol.upper(),
                    Candle.interval == interval,
                    Candle.open_time >= since,
                )
                .order_by(Candle.open_time.asc())
            )
            .scalars()
            .all()
        )

    def load_and_analyze(self, session: Session, symbol: str, interval: str, limit: int) -> AnalysisResult:
        """Читает свечи из БД и сразу строит анализ."""

        candles = self.load_candles(session=session, symbol=symbol, interval=interval, limit=limit)
        return self.analyze(symbol=symbol, interval=interval, candles=candles)
