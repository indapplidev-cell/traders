from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.backtest.backtest_engine import BacktestEngine
from app.db.models import Candle
from app.market.analysis_service import AnalysisResult
from app.market.indicator_service import IndicatorCalculationError, IndicatorSnapshot
from app.strategy.trade_decision import DecisionType, MarketRegime, TradeDecision


def build_backtest_candles(
    count: int = 205,
    *,
    breakout_index: int = 200,
    breakout_low: Decimal | None = None,
    breakout_high: Decimal | None = None,
) -> list[Candle]:
    """Генерирует свечи для детерминированного backtest."""

    start = datetime.now(UTC) - timedelta(minutes=count * 15)
    candles: list[Candle] = []
    for index in range(count):
        close = Decimal("100")
        low = Decimal("99")
        high = Decimal("101")
        if index == breakout_index and breakout_low is not None:
            low = breakout_low
        if index == breakout_index and breakout_high is not None:
            high = breakout_high
        candles.append(
            Candle(
                symbol="BTCUSDT",
                interval="15m",
                open_time=start + timedelta(minutes=index * 15),
                open=close,
                high=high,
                low=low,
                close=close,
                volume=Decimal("20"),
                close_time=start + timedelta(minutes=index * 15 + 14),
            )
        )
    return candles


@dataclass
class FakeAnalysisService:
    """Возвращает предсказуемые сигналы для проверки backtest-движка."""

    decisions: list[DecisionType]
    window_lengths: list[int]
    atr_14: Decimal = Decimal("10")

    def analyze(self, *, symbol: str, interval: str, candles: list[Candle]) -> AnalysisResult:
        self.window_lengths.append(len(candles))
        step = len(self.window_lengths) - 1
        latest = candles[-1]
        decision = self.decisions[min(step, len(self.decisions) - 1)]
        return AnalysisResult(
            candles=candles,
            latest_candle=latest,
            indicator_snapshot=IndicatorSnapshot(
                ema_20=Decimal("100"),
                ema_50=Decimal("99"),
                ema_200=Decimal("95"),
                rsi_14=Decimal("60"),
                atr_14=self.atr_14,
                volume_sma_20=Decimal("10"),
                last_close=latest.close,
                last_volume=latest.volume,
            ),
            market_regime=MarketRegime.BULL,
            strategy_decision=TradeDecision.build(
                symbol=symbol,
                interval=interval,
                decision=decision,
                reason=f"Тестовый сигнал {decision.value}.",
                regime=MarketRegime.BULL,
                price=latest.close,
                created_at=latest.close_time,
            ),
        )


def test_backtest_uses_only_past_and_current_candles(configured_env) -> None:
    """Проверяет, что backtest не передаёт анализу будущие свечи."""

    analysis = FakeAnalysisService(
        decisions=[DecisionType.BUY, DecisionType.HOLD, DecisionType.HOLD, DecisionType.HOLD, DecisionType.HOLD, DecisionType.HOLD],
        window_lengths=[],
    )
    candles = build_backtest_candles()

    BacktestEngine(analysis_service=analysis).run(symbol="BTCUSDT", interval="15m", candles=candles)

    assert analysis.window_lengths[0] == 200
    assert analysis.window_lengths[-1] == len(candles)
    assert analysis.window_lengths == sorted(analysis.window_lengths)


def test_backtest_returns_total_trades_final_balance_and_winrate(configured_env) -> None:
    """Проверяет основные итоговые метрики backtest."""

    analysis = FakeAnalysisService(
        decisions=[DecisionType.BUY, DecisionType.HOLD, DecisionType.HOLD, DecisionType.HOLD, DecisionType.HOLD, DecisionType.HOLD],
        window_lengths=[],
    )
    candles = build_backtest_candles(breakout_index=200, breakout_high=Decimal("121"))

    result = BacktestEngine(analysis_service=analysis).run(symbol="BTCUSDT", interval="15m", candles=candles)

    assert result.total_trades == 1
    assert result.final_balance > result.initial_balance
    assert result.winrate_pct == Decimal("100")
    assert result.max_drawdown_pct >= Decimal("0")


def test_backtest_stop_loss_is_triggered(configured_env) -> None:
    """Проверяет закрытие LONG по stop-loss."""

    analysis = FakeAnalysisService(
        decisions=[DecisionType.BUY, DecisionType.HOLD, DecisionType.HOLD, DecisionType.HOLD, DecisionType.HOLD, DecisionType.HOLD],
        window_lengths=[],
    )
    candles = build_backtest_candles(breakout_index=200, breakout_low=Decimal("84"))

    result = BacktestEngine(analysis_service=analysis).run(symbol="BTCUSDT", interval="15m", candles=candles)

    assert result.trades[-1].exit_action == "STOP_LOSS"


def test_backtest_take_profit_is_triggered(configured_env) -> None:
    """Проверяет закрытие LONG по take-profit."""

    analysis = FakeAnalysisService(
        decisions=[DecisionType.BUY, DecisionType.HOLD, DecisionType.HOLD, DecisionType.HOLD, DecisionType.HOLD, DecisionType.HOLD],
        window_lengths=[],
    )
    candles = build_backtest_candles(breakout_index=200, breakout_high=Decimal("121"))

    result = BacktestEngine(analysis_service=analysis).run(symbol="BTCUSDT", interval="15m", candles=candles)

    assert result.trades[-1].exit_action == "TAKE_PROFIT"


def test_backtest_prefers_stop_loss_if_both_levels_hit(configured_env) -> None:
    """Проверяет консервативное правило SL-first при одновременном касании SL и TP."""

    analysis = FakeAnalysisService(
        decisions=[DecisionType.BUY, DecisionType.HOLD, DecisionType.HOLD, DecisionType.HOLD, DecisionType.HOLD, DecisionType.HOLD],
        window_lengths=[],
    )
    candles = build_backtest_candles(breakout_index=200, breakout_low=Decimal("84"), breakout_high=Decimal("121"))

    result = BacktestEngine(analysis_service=analysis).run(symbol="BTCUSDT", interval="15m", candles=candles)

    assert result.trades[-1].exit_action == "STOP_LOSS"


def test_backtest_raises_clear_error_when_candles_are_insufficient(configured_env) -> None:
    """Проверяет понятную ошибку при нехватке свечей."""

    analysis = FakeAnalysisService(decisions=[DecisionType.HOLD], window_lengths=[])
    with pytest.raises(IndicatorCalculationError):
        BacktestEngine(analysis_service=analysis).run(
            symbol="BTCUSDT",
            interval="15m",
            candles=build_backtest_candles(count=100),
        )


def test_backtest_buy_without_atr_does_not_open_position(configured_env) -> None:
    """Проверяет, что BUY без ATR14 не открывает позицию и не ломает backtest."""

    analysis = FakeAnalysisService(
        decisions=[DecisionType.BUY, DecisionType.HOLD, DecisionType.HOLD, DecisionType.HOLD, DecisionType.HOLD, DecisionType.HOLD],
        window_lengths=[],
        atr_14=Decimal("0"),
    )
    candles = build_backtest_candles()

    result = BacktestEngine(analysis_service=analysis).run(symbol="BTCUSDT", interval="15m", candles=candles)

    assert result.total_trades == 0
    assert result.final_balance == result.initial_balance


def test_backtest_can_load_history_from_db_by_days(sqlite_session) -> None:
    """Проверяет отдельный DB-режим backtest по истории за последние N дней."""

    candles = build_backtest_candles()
    sqlite_session.add_all(candles)
    sqlite_session.flush()

    result = BacktestEngine().load_candles_from_db(
        session=sqlite_session,
        symbol="BTCUSDT",
        interval="15m",
        days=30,
    )

    assert len(result) == len(candles)
    assert result[0].open_time <= result[-1].open_time
