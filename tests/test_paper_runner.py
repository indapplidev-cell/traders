from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.db.base import Base
from app.db.models import Candle, RunnerSession, RuntimeTick
from app.db.session import get_engine
from app.execution.paper_runner_service import PaperRunnerService
from app.market.analysis_service import AnalysisResult
from app.market.indicator_service import IndicatorSnapshot
from app.runtime.paper_runner import PaperRunner
from app.runtime.strategy_runtime import RuntimeTickResult
from app.strategy.base_strategy import StrategyDecision
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


def _build_runtime_result(index: int = 1) -> RuntimeTickResult:
    return RuntimeTickResult(
        strategy_decision=StrategyDecision(
            strategy_name="simple_trend",
            strategy_version="1.0",
            symbol="BTCUSDT",
            interval="15m",
            action="HOLD",
            reason=f"tick {index}",
            confidence=0.5,
            metadata={},
        ),
        final_action="HOLD",
        risk_approved=True,
        risk_reason="ok",
        execution_action="HOLD",
        execution_message="skipped",
        decision_id=index,
        candles_used=300,
        market_regime="SIDEWAYS",
        portfolio_snapshot={"balance_usdt": "1000"},
    )


class FakeRuntime:
    def __init__(self) -> None:
        self.settings = SimpleNamespace(strategy_max_ticks=10)
        self.calls = 0

    def run_tick(self, strategy_name: str, symbol: str, interval: str) -> RuntimeTickResult:
        _ = (strategy_name, symbol, interval)
        self.calls += 1
        return _build_runtime_result(self.calls)


def test_paper_runner_start_creates_session_and_ticks(sqlite_session) -> None:
    _ = sqlite_session
    runner = PaperRunner(runtime=FakeRuntime())

    result = runner.start(
        strategy_name="simple_trend",
        symbol="BTCUSDT",
        interval="15m",
        ticks=3,
        sleep_seconds=0,
    )

    session_row = sqlite_session.execute(select(RunnerSession)).scalar_one()
    tick_rows = sqlite_session.execute(select(RuntimeTick).order_by(RuntimeTick.tick_number.asc())).scalars().all()

    assert result.status == "STOPPED"
    assert result.ticks_requested == 3
    assert result.ticks_completed == 3
    assert session_row.status == "STOPPED"
    assert session_row.ticks_completed == 3
    assert [item.tick_number for item in tick_rows] == [1, 2, 3]
    assert all(item.runner_session_id == session_row.id for item in tick_rows)


@pytest.mark.parametrize("ticks", [0, -1, 11])
def test_paper_runner_rejects_invalid_ticks(sqlite_session, ticks: int) -> None:
    _ = sqlite_session
    runner = PaperRunner(runtime=FakeRuntime())

    with pytest.raises(ValueError):
        runner.start(
            strategy_name="simple_trend",
            symbol="BTCUSDT",
            interval="15m",
            ticks=ticks,
            sleep_seconds=0,
        )


def test_paper_runner_rejects_negative_sleep(sqlite_session) -> None:
    _ = sqlite_session
    runner = PaperRunner(runtime=FakeRuntime())

    with pytest.raises(ValueError, match="sleep_seconds must be >= 0"):
        runner.start(
            strategy_name="simple_trend",
            symbol="BTCUSDT",
            interval="15m",
            ticks=1,
            sleep_seconds=-1,
        )
