from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy import select

from app.db.models import RunnerSession, RuntimeTick
from app.runtime.paper_runner import PaperRunner
from app.runtime.strategy_runtime import RuntimeTickResult
from app.strategy.base_strategy import StrategyDecision


def _build_runtime_result(index: int) -> RuntimeTickResult:
    return RuntimeTickResult(
        strategy_decision=StrategyDecision(
            strategy_name="simple_trend",
            strategy_version="1.0",
            symbol="BTCUSDT",
            interval="15m",
            action="SELL" if index % 2 else "HOLD",
            reason=f"tick {index}",
            confidence=0.7,
            metadata={},
        ),
        final_action="HOLD",
        risk_approved=False,
        risk_reason="blocked",
        execution_action="SKIPPED",
        execution_message="blocked",
        decision_id=100 + index,
        candles_used=300,
        market_regime="BEAR",
        portfolio_snapshot={"balance_usdt": "1000"},
    )


class SuccessRuntime:
    def __init__(self) -> None:
        self.settings = SimpleNamespace(strategy_max_ticks=10)
        self.calls = 0

    def run_tick(self, strategy_name: str, symbol: str, interval: str) -> RuntimeTickResult:
        _ = (strategy_name, symbol, interval)
        self.calls += 1
        return _build_runtime_result(self.calls)


class FailingRuntime(SuccessRuntime):
    def run_tick(self, strategy_name: str, symbol: str, interval: str) -> RuntimeTickResult:
        self.calls += 1
        if self.calls == 2:
            raise RuntimeError("boom on tick 2")
        return _build_runtime_result(self.calls)


def test_runtime_tick_audit_stores_tick_fields(sqlite_session) -> None:
    _ = sqlite_session
    runner = PaperRunner(runtime=SuccessRuntime())

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
    assert session_row.status == "STOPPED"
    assert session_row.ticks_completed == 3
    assert len(tick_rows) == 3
    assert tick_rows[0].strategy_action == "SELL"
    assert tick_rows[0].final_action == "HOLD"
    assert tick_rows[0].risk_approved is False
    assert tick_rows[0].risk_reason == "blocked"
    assert tick_rows[0].execution_action == "SKIPPED"
    assert tick_rows[0].journal_id == 101
    assert tick_rows[0].market_regime == "BEAR"
    assert tick_rows[0].candles_used == 300


def test_runtime_tick_audit_marks_failed_session_and_error_row(sqlite_session) -> None:
    _ = sqlite_session
    runner = PaperRunner(runtime=FailingRuntime())

    result = runner.start(
        strategy_name="simple_trend",
        symbol="BTCUSDT",
        interval="15m",
        ticks=3,
        sleep_seconds=0,
    )

    session_row = sqlite_session.execute(select(RunnerSession)).scalar_one()
    tick_rows = sqlite_session.execute(select(RuntimeTick).order_by(RuntimeTick.tick_number.asc())).scalars().all()

    assert result.status == "FAILED"
    assert result.ticks_completed == 1
    assert result.last_error == "boom on tick 2"
    assert session_row.status == "FAILED"
    assert session_row.ticks_completed == 1
    assert session_row.last_error == "boom on tick 2"
    assert session_row.stopped_at is not None
    assert len(tick_rows) == 2
    assert tick_rows[1].tick_number == 2
    assert tick_rows[1].execution_action == "ERROR"
    assert tick_rows[1].error == "boom on tick 2"
