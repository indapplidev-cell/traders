from __future__ import annotations

import importlib
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from typer.testing import CliRunner

from app.db.base import Base
from app.db.models import BacktestSession, Candle, RunnerSession
from app.db.session import get_engine, session_scope


def load_commands_module():
    for module_name in (
        "app.cli.commands",
        "app.db.session",
        "app.db.async_session",
        "app.backtest.backtest_runner",
        "app.analytics.backtest_performance",
        "app.analytics.session_comparison",
        "app.runtime.strategy_runtime",
        "app.runtime.paper_runner",
    ):
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


def test_backtest_history_empty_db_does_not_fail(configured_env) -> None:
    _ = configured_env
    Base.metadata.create_all(get_engine())
    commands = load_commands_module()

    result = CliRunner().invoke(commands.app, ["backtest-history", "--limit", "10"])

    assert result.exit_code == 0
    assert "No backtest sessions found." in result.output


def test_backtest_performance_missing_session_returns_error(configured_env) -> None:
    _ = configured_env
    Base.metadata.create_all(get_engine())
    commands = load_commands_module()

    result = CliRunner().invoke(commands.app, ["backtest-performance", "--session-id", "999"])

    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_backtest_run_performance_history_and_compare_work(configured_env) -> None:
    _ = configured_env
    seed_flat_candles()
    commands = load_commands_module()
    runner = CliRunner()

    run_result = runner.invoke(
        commands.app,
        [
            "backtest-run",
            "--strategy",
            "simple_trend",
            "--symbol",
            "BTCUSDT",
            "--interval",
            "15m",
            "--candles",
            "300",
            "--initial-cash",
            "1000",
        ],
    )
    assert run_result.exit_code == 0
    assert "session id" in run_result.output.lower()

    with session_scope() as session:
        backtest_session_id = session.execute(select(BacktestSession.id).order_by(BacktestSession.id.desc())).scalar_one()

    performance_result = runner.invoke(
        commands.app,
        ["backtest-performance", "--session-id", str(backtest_session_id)],
    )
    assert performance_result.exit_code == 0
    assert "backtest performance" in performance_result.output.lower()

    history_result = runner.invoke(commands.app, ["backtest-history", "--limit", "10"])
    assert history_result.exit_code == 0
    assert "backtest history" in history_result.output.lower()

    runner_start_result = runner.invoke(
        commands.app,
        [
            "runner-start",
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
    assert runner_start_result.exit_code == 0

    with session_scope() as session:
        runner_session_id = session.execute(select(RunnerSession.id).order_by(RunnerSession.id.desc())).scalar_one()

    compare_result = runner.invoke(
        commands.app,
        [
            "session-compare",
            "--left-type",
            "runner",
            "--left-id",
            str(runner_session_id),
            "--right-type",
            "backtest",
            "--right-id",
            str(backtest_session_id),
        ],
    )
    assert compare_result.exit_code == 0
    assert "session comparison" in compare_result.output.lower()
