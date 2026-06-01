from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from typer.testing import CliRunner

from app.cli import commands
from app.db.models import PaperPosition, TradeDecisionRecord
from app.db.session import get_engine, session_scope
from app.execution.paper_execution_engine import PaperExecutionEngine
from app.execution.paper_step_service import PaperStepService
from app.execution.position_manager import PositionManager
from app.market.analysis_service import AnalysisResult
from app.market.indicator_service import IndicatorSnapshot
from app.strategy.trade_decision import DecisionType, MarketRegime, TradeDecision


def build_decision(decision: DecisionType, reason: str) -> TradeDecision:
    """Создаёт тестовое торговое решение."""

    return TradeDecision.build(
        symbol="BTCUSDT",
        interval="15m",
        decision=decision,
        reason=reason,
        regime=MarketRegime.BULL if decision == DecisionType.BUY else MarketRegime.BEAR,
        price=Decimal("100"),
    )


def build_snapshot(atr_14: Decimal = Decimal("10")) -> IndicatorSnapshot:
    """Создаёт снимок индикаторов для тестов paper-step."""

    return IndicatorSnapshot(
        ema_20=Decimal("100"),
        ema_50=Decimal("99"),
        ema_200=Decimal("95"),
        rsi_14=Decimal("60"),
        atr_14=atr_14,
        volume_sma_20=Decimal("10"),
        last_close=Decimal("100"),
        last_volume=Decimal("12"),
    )


def test_paper_step_journals_strategy_and_final_decisions_separately(configured_env) -> None:
    """Проверяет CLI-поток paper-step и корректный аудит при риск-отклонении."""

    from app.db.base import Base

    Base.metadata.create_all(get_engine())

    async def fake_fetch_and_store_candles(self, symbol: str, interval: str, limit: int) -> int:
        _ = (self, symbol, interval, limit)
        return 0

    fake_candle_time = build_decision(DecisionType.HOLD, "stub").created_at
    fake_analysis = AnalysisResult(
        candles=[],
        latest_candle=SimpleNamespace(
            close_time=fake_candle_time,
            open_time=fake_candle_time,
            interval="15m",
            low=Decimal("99"),
            high=Decimal("101"),
        ),
        indicator_snapshot=build_snapshot(),
        market_regime=MarketRegime.BEAR,
        strategy_decision=build_decision(DecisionType.SELL, "Стратегия хочет закрыть позицию."),
    )

    original_fetch = commands.CandleService.fetch_and_store_candles
    original_analysis = commands.analysis_service.load_and_analyze

    commands.CandleService.fetch_and_store_candles = fake_fetch_and_store_candles
    commands.analysis_service.load_and_analyze = lambda session, symbol, interval, limit: fake_analysis
    try:
        result = CliRunner().invoke(commands.app, ["paper-step", "--symbol", "BTCUSDT", "--interval", "15m"])
    finally:
        commands.CandleService.fetch_and_store_candles = original_fetch
        commands.analysis_service.load_and_analyze = original_analysis

    assert result.exit_code == 0
    assert "strategy decision" in result.output
    assert "final decision" in result.output

    with session_scope() as session:
        record = session.execute(select(TradeDecisionRecord)).scalar_one()

    assert record.strategy_decision == "SELL"
    assert record.final_decision == "HOLD"
    assert record.risk_approved is False
    assert record.execution_action == "SKIPPED"


def test_buy_does_not_create_second_open_position_for_same_symbol(sqlite_session) -> None:
    """Проверяет, что повторный BUY по тому же символу не открывает вторую позицию."""

    service = PaperStepService(sqlite_session)

    first_result = service.process(
        build_decision(DecisionType.BUY, "Первый вход в позицию."),
        indicator_snapshot=build_snapshot(),
    )
    second_result = service.process(
        build_decision(DecisionType.BUY, "Повторный вход по тому же символу."),
        indicator_snapshot=build_snapshot(),
    )

    open_positions = sqlite_session.execute(
        select(PaperPosition).where(PaperPosition.symbol == "BTCUSDT", PaperPosition.status == "OPEN")
    ).scalars().all()

    assert first_result.risk_approved is True
    assert second_result.strategy_decision.decision == DecisionType.BUY
    assert second_result.final_decision.decision == DecisionType.HOLD
    assert second_result.risk_approved is False
    assert len(open_positions) == 1


def test_risk_manager_rejects_sell_without_open_position_and_journal_keeps_sell(sqlite_session) -> None:
    """Проверяет, что исходный SELL не теряется при риск-отклонении."""

    result = PaperStepService(sqlite_session).process(build_decision(DecisionType.SELL, "Выход по сигналу стратегии."))
    record = sqlite_session.execute(select(TradeDecisionRecord)).scalar_one()

    assert result.strategy_decision.decision == DecisionType.SELL
    assert result.final_decision.decision == DecisionType.HOLD
    assert result.risk_approved is False
    assert record.strategy_decision == "SELL"
    assert record.final_decision == "HOLD"
    assert "открытая позиция отсутствует" in record.risk_reason.lower()


def test_execution_error_is_journaled_without_losing_signal(sqlite_session, monkeypatch: pytest.MonkeyPatch) -> None:
    """Проверяет, что ошибка исполнения сохраняется в audit-записи."""

    def broken_execute(self, decision, *, indicator_snapshot=None):
        _ = (self, decision, indicator_snapshot)
        raise ValueError("Сломанное исполнение для теста.")

    monkeypatch.setattr(PaperExecutionEngine, "execute", broken_execute)

    result = PaperStepService(sqlite_session).process(
        build_decision(DecisionType.BUY, "Пробуем открыть позицию."),
        indicator_snapshot=build_snapshot(),
    )

    record = sqlite_session.execute(select(TradeDecisionRecord)).scalar_one()
    assert result.has_execution_error is True
    assert record.strategy_decision == "BUY"
    assert record.final_decision == "HOLD"
    assert record.execution_action == "ERROR"
    assert "сломанное исполнение" in record.execution_message.lower()


def test_runner_state_persists_last_processed_open_time(sqlite_session) -> None:
    """Проверяет сохранение состояния последней обработанной свечи."""

    manager = PositionManager(sqlite_session)
    state = manager.get_or_create_runner_state(symbol="BTCUSDT", interval="15m")
    assert state.last_processed_open_time is None

    state.last_processed_open_time = build_decision(DecisionType.HOLD, "x").created_at
    sqlite_session.flush()

    same_state = manager.get_or_create_runner_state(symbol="BTCUSDT", interval="15m")
    assert same_state.last_processed_open_time == state.last_processed_open_time


def test_buy_without_atr_is_rejected_with_clear_error(sqlite_session) -> None:
    """Проверяет понятный отказ BUY без ATR14."""

    result = PaperStepService(sqlite_session).process(
        build_decision(DecisionType.BUY, "Пробуем открыть позицию без ATR."),
        indicator_snapshot=build_snapshot(atr_14=Decimal("0")),
    )
    record = sqlite_session.execute(select(TradeDecisionRecord)).scalar_one()

    assert result.has_execution_error is True
    assert record.execution_action == "ERROR"
    assert "atr14" in record.execution_message.lower()


def test_open_position_can_be_closed_by_stop_loss_on_next_step(sqlite_session) -> None:
    """Проверяет автоматическое закрытие позиции по stop-loss на следующем шаге."""

    service = PaperStepService(sqlite_session)
    service.process(
        build_decision(DecisionType.BUY, "Открываем позицию."),
        indicator_snapshot=build_snapshot(),
    )

    stop_candle = SimpleNamespace(
        symbol="BTCUSDT",
        interval="15m",
        open_time=build_decision(DecisionType.HOLD, "x").created_at,
        close_time=build_decision(DecisionType.HOLD, "x").created_at,
        low=Decimal("84"),
        high=Decimal("101"),
    )
    result = service.process(
        build_decision(DecisionType.HOLD, "Стратегия сама не закрывает позицию."),
        indicator_snapshot=build_snapshot(),
        latest_candle=stop_candle,
    )

    open_positions = sqlite_session.execute(
        select(PaperPosition).where(PaperPosition.symbol == "BTCUSDT", PaperPosition.status == "OPEN")
    ).scalars().all()

    assert result.final_decision.decision == DecisionType.SELL
    assert result.execution_action == "STOP_LOSS"
    assert len(open_positions) == 0
