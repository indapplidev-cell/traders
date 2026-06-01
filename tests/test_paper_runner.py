from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.db.base import Base
from app.db.models import Candle
from app.db.session import get_engine
from app.execution.paper_runner_service import PaperRunnerService
from app.market.analysis_service import AnalysisResult
from app.market.indicator_service import IndicatorSnapshot
from app.strategy.trade_decision import DecisionType, MarketRegime, TradeDecision


class FakeCandleService:
    """Тестовый сервис, который не ходит в Binance."""

    async def fetch_and_store_candles(self, symbol: str, interval: str, limit: int) -> int:
        _ = (symbol, interval, limit)
        return 0


class FakeAnalysisService:
    """Всегда возвращает одну и ту же закрытую свечу для runner-теста."""

    def __init__(self, candle: Candle) -> None:
        self.candle = candle

    def load_and_analyze(self, session, symbol: str, interval: str, limit: int) -> AnalysisResult:
        _ = (session, symbol, interval, limit)
        return AnalysisResult(
            candles=[self.candle],
            latest_candle=self.candle,
            indicator_snapshot=IndicatorSnapshot(
                ema_20=Decimal("100"),
                ema_50=Decimal("99"),
                ema_200=Decimal("95"),
                rsi_14=Decimal("60"),
                atr_14=Decimal("10"),
                volume_sma_20=Decimal("10"),
                last_close=self.candle.close,
                last_volume=self.candle.volume,
            ),
            market_regime=MarketRegime.BULL,
            strategy_decision=TradeDecision.build(
                symbol=symbol,
                interval=interval,
                decision=DecisionType.HOLD,
                reason="Ничего не делаем.",
                regime=MarketRegime.BULL,
                price=self.candle.close,
                created_at=self.candle.close_time,
            ),
        )


def test_runner_does_not_process_same_candle_twice(configured_env) -> None:
    """Проверяет, что runner помнит последнюю обработанную свечу."""

    Base.metadata.create_all(get_engine())
    now = datetime.now(UTC)
    candle = Candle(
        symbol="BTCUSDT",
        interval="15m",
        open_time=now - timedelta(minutes=15),
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100"),
        volume=Decimal("10"),
        close_time=now,
    )
    service = PaperRunnerService(
        candle_service=FakeCandleService(),
        analysis_service=FakeAnalysisService(candle),
    )

    first = __import__("asyncio").run(service.run_once(symbol="BTCUSDT", interval="15m"))
    second = __import__("asyncio").run(service.run_once(symbol="BTCUSDT", interval="15m"))

    assert first.processed is True
    assert second.processed is False
