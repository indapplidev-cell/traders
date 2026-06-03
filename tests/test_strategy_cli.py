from __future__ import annotations

import importlib
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from typer.testing import CliRunner

from app.db.base import Base
from app.db.models import Candle, TradeDecisionRecord
from app.db.session import get_engine, session_scope
from app.runtime.strategy_runtime import RuntimeTickResult
from app.strategy.base_strategy import StrategyDecision


def load_commands_module():
    for module_name in ("app.cli.commands", "app.db.session", "app.db.async_session"):
        sys.modules.pop(module_name, None)
    return importlib.import_module("app.cli.commands")


def seed_flat_candles() -> None:
    Base.metadata.create_all(get_engine())
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    candles: list[Candle] = []
    for index in range(300):
        open_time = now - timedelta(minutes=15 * (300 - index))
        candles.append(
            Candle(
                symbol="BTCUSDT",
                interval="15m",
                open_time=open_time,
                open=Decimal("100"),
                high=Decimal("101"),
                low=Decimal("99"),
                close=Decimal("100"),
                volume=Decimal("10"),
                close_time=open_time + timedelta(minutes=15),
            )
        )

    with session_scope() as session:
        session.add_all(candles)


def build_tick_result(message: str) -> RuntimeTickResult:
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
        execution_message=message,
        decision_id=1,
        candles_used=300,
        market_regime="SIDEWAYS",
        portfolio_snapshot={"balance_usdt": "1000"},
    )


def test_strategy_list_shows_simple_trend(configured_env) -> None:
    _ = configured_env
    commands = load_commands_module()

    result = CliRunner().invoke(commands.app, ["strategy-list"])

    assert result.exit_code == 0
    assert "simple_trend" in result.output


def test_strategy_run_creates_journal_row(configured_env) -> None:
    _ = configured_env
    seed_flat_candles()
    commands = load_commands_module()

    result = CliRunner().invoke(
        commands.app,
        ["strategy-run", "--strategy", "simple_trend", "--symbol", "BTCUSDT", "--interval", "15m"],
    )

    assert result.exit_code == 0
    assert "strategy action" in result.output.lower()
    with session_scope() as session:
        record = session.execute(select(TradeDecisionRecord)).scalar_one()

    assert record.strategy_name == "simple_trend"
    assert record.interval == "15m"


def test_strategy_loop_prints_each_tick_and_stops(configured_env, monkeypatch) -> None:
    _ = configured_env
    commands = load_commands_module()

    class FakeRuntime:
        def run_loop(self, strategy_name: str, symbol: str, interval: str, ticks: int, sleep_seconds: float):
            assert strategy_name == "simple_trend"
            assert symbol == "BTCUSDT"
            assert interval == "15m"
            assert ticks == 3
            assert sleep_seconds == 0
            return [
                build_tick_result("tick 1"),
                build_tick_result("tick 2"),
                build_tick_result("tick 3"),
            ]

    monkeypatch.setattr(commands, "get_strategy_runtime", lambda: FakeRuntime())

    result = CliRunner().invoke(
        commands.app,
        [
            "strategy-loop",
            "--strategy",
            "simple_trend",
            "--symbol",
            "BTCUSDT",
            "--interval",
            "15m",
            "--ticks",
            "3",
            "--sleep-seconds",
            "0",
        ],
    )

    assert result.exit_code == 0
    assert result.output.count("Strategy loop tick") == 3
