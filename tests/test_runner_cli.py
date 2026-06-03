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


def test_runner_start_history_and_ticks_work(configured_env) -> None:
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
    assert "ticks completed" in start_result.output.lower()
    with session_scope() as session:
        session_id = session.execute(select(RunnerSession.id).order_by(RunnerSession.id.desc())).scalar_one()

    history_result = runner.invoke(commands.app, ["runner-history", "--limit", "10"])
    assert history_result.exit_code == 0
    assert "Runner history" in history_result.output
    assert str(session_id) in history_result.output

    ticks_result = runner.invoke(commands.app, ["runner-ticks", "--session-id", str(session_id)])
    assert ticks_result.exit_code == 0
    assert "Runner ticks session" in ticks_result.output
    assert "1" in ticks_result.output
    assert "2" in ticks_result.output
    assert "3" in ticks_result.output


def test_runner_start_rejects_zero_ticks(configured_env) -> None:
    _ = configured_env
    commands = load_commands_module()

    result = CliRunner().invoke(
        commands.app,
        ["runner-start", "--strategy", "simple_trend", "--symbol", "BTCUSDT", "--interval", "15m", "--ticks", "0"],
    )

    assert result.exit_code == 1
    assert "ticks must be > 0" in result.output


def test_runner_start_rejects_ticks_above_limit(configured_env) -> None:
    _ = configured_env
    commands = load_commands_module()

    result = CliRunner().invoke(
        commands.app,
        ["runner-start", "--strategy", "simple_trend", "--symbol", "BTCUSDT", "--interval", "15m", "--ticks", "11"],
    )

    assert result.exit_code == 1
    assert "STRATEGY_MAX_TICKS" in result.output
