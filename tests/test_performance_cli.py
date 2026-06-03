from __future__ import annotations

import importlib
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from typer.testing import CliRunner

from app.db.base import Base
from app.db.models import Candle, RunnerSession
from app.db.session import get_engine, session_scope


def load_commands_module():
    for module_name in (
        "app.cli.commands",
        "app.db.session",
        "app.db.async_session",
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


def test_performance_history_empty_db_does_not_fail(configured_env) -> None:
    _ = configured_env
    Base.metadata.create_all(get_engine())
    commands = load_commands_module()
    result = CliRunner().invoke(commands.app, ["performance-history", "--limit", "10"])

    assert result.exit_code == 0
    assert "performance history" in result.output.lower()


def test_performance_session_missing_session_returns_error(configured_env) -> None:
    _ = configured_env
    Base.metadata.create_all(get_engine())
    commands = load_commands_module()
    result = CliRunner().invoke(commands.app, ["performance-session", "--session-id", "999"])

    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_portfolio_analytics_empty_db_returns_unavailable(configured_env) -> None:
    _ = configured_env
    Base.metadata.create_all(get_engine())
    commands = load_commands_module()
    result = CliRunner().invoke(commands.app, ["portfolio-analytics", "--symbol", "BTCUSDT"])

    assert result.exit_code == 0
    assert "UNAVAILABLE" in result.output or "N/A" in result.output


def test_performance_cli_with_runner_session(configured_env) -> None:
    _ = configured_env
    seed_flat_candles()
    commands = load_commands_module()
    runner = CliRunner()

    start_result = runner.invoke(
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
    assert start_result.exit_code == 0
    assert "session id" in start_result.output.lower()

    with session_scope() as session:
        session_id = session.execute(select(RunnerSession.id).order_by(RunnerSession.id.desc())).scalar_one()

    performance_result = runner.invoke(commands.app, ["performance-session", "--session-id", str(session_id)])
    assert performance_result.exit_code == 0
    assert "performance session" in performance_result.output.lower()
    assert str(session_id) in performance_result.output

    history_result = runner.invoke(commands.app, ["performance-history", "--limit", "10"])
    assert history_result.exit_code == 0
    assert "performance history" in history_result.output.lower()

    compare_result = runner.invoke(
        commands.app,
        ["performance-compare", "--strategy", "simple_trend", "--symbol", "BTCUSDT", "--limit", "10"],
    )
    assert compare_result.exit_code == 0
    assert "performance compare" in compare_result.output.lower()
