from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db.models import Candle, PaperPosition, TradeDecisionRecord
from app.runtime.strategy_runtime import RuntimeTickResult, StrategyRuntime
from app.strategy.base_strategy import StrategyDecision


def seed_flat_candles(session, *, count: int = 300, symbol: str = "BTCUSDT", interval: str = "15m") -> None:
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    candles: list[Candle] = []
    for index in range(count):
        open_time = now - timedelta(minutes=15 * (count - index))
        candles.append(
            Candle(
                symbol=symbol,
                interval=interval,
                open_time=open_time,
                open=Decimal("100"),
                high=Decimal("101"),
                low=Decimal("99"),
                close=Decimal("100"),
                volume=Decimal("10"),
                close_time=open_time + timedelta(minutes=15),
            )
        )
    session.add_all(candles)
    session.commit()


class FailingCandleService:
    async def fetch_and_store_candles(self, *, symbol: str, interval: str, limit: int) -> int:
        _ = (symbol, interval, limit)
        raise AssertionError("Runtime should not fetch candles when DB already has enough rows.")


def build_tick_result() -> RuntimeTickResult:
    return RuntimeTickResult(
        strategy_decision=StrategyDecision(
            strategy_name="simple_trend",
            strategy_version="1.0",
            symbol="BTCUSDT",
            interval="15m",
            action="HOLD",
            reason="stub",
            confidence=0.5,
            metadata={},
        ),
        final_action="HOLD",
        risk_approved=True,
        risk_reason="ok",
        execution_action="HOLD",
        execution_message="stub",
        decision_id=1,
        candles_used=300,
        market_regime="SIDEWAYS",
        portfolio_snapshot={"balance_usdt": "1000"},
    )


def test_runtime_works_after_db_candle_roundtrip(sqlite_session) -> None:
    seed_flat_candles(sqlite_session)

    runtime = StrategyRuntime(candle_service=FailingCandleService())
    result = runtime.run_tick("simple_trend", "BTCUSDT", "15m", candle_limit=300)

    record = sqlite_session.execute(select(TradeDecisionRecord)).scalar_one()
    open_positions = sqlite_session.execute(select(PaperPosition).where(PaperPosition.status == "OPEN")).scalars().all()

    assert result.strategy_decision.strategy_name == "simple_trend"
    assert result.candles_used == 300
    assert result.final_action == "HOLD"
    assert result.execution_action == "HOLD"
    assert record.strategy_name == "simple_trend"
    assert record.strategy_version == "1.0"
    assert str(record.confidence) == "0.5000"
    assert open_positions == []


def test_runtime_loop_stops_after_exact_ticks(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = StrategyRuntime()
    calls: list[tuple[str, str, str]] = []

    def fake_run_tick(strategy_name: str, symbol: str, interval: str, candle_limit: int | None = None) -> RuntimeTickResult:
        _ = candle_limit
        calls.append((strategy_name, symbol, interval))
        return build_tick_result()

    monkeypatch.setattr(runtime, "run_tick", fake_run_tick)

    results = runtime.run_loop("simple_trend", "BTCUSDT", "15m", ticks=3, sleep_seconds=0)

    assert len(results) == 3
    assert calls == [("simple_trend", "BTCUSDT", "15m")] * 3


def test_runtime_loop_rejects_non_positive_ticks() -> None:
    with pytest.raises(ValueError, match="ticks must be > 0"):
        StrategyRuntime().run_loop("simple_trend", "BTCUSDT", "15m", ticks=0, sleep_seconds=0)


def test_runtime_loop_rejects_ticks_above_settings_limit() -> None:
    with pytest.raises(ValueError, match="STRATEGY_MAX_TICKS"):
        StrategyRuntime().run_loop("simple_trend", "BTCUSDT", "15m", ticks=11, sleep_seconds=0)
