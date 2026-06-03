from __future__ import annotations

import importlib
import sys

from typer.testing import CliRunner


def _clear_cli_modules() -> None:
    """Clear imported CLI modules between tests."""

    for module_name in ("app.cli.commands", "app.db.session", "app.db.async_session", "app.main"):
        sys.modules.pop(module_name, None)


def _clear_env(monkeypatch, tmp_path) -> None:
    """Remove runtime variables so CLI help stays independent from .env and DB."""

    for key in (
        "APP_ENV",
        "DATABASE_URL",
        "ASYNC_DATABASE_URL",
        "BINANCE_PUBLIC_REST_URL",
        "DEFAULT_SYMBOL",
        "DEFAULT_INTERVAL",
        "DEFAULT_CANDLE_LIMIT",
        "PAPER_INITIAL_BALANCE_USDT",
        "PAPER_POSITION_SIZE_FRACTION",
        "PAPER_RISK_PER_TRADE",
        "PAPER_MAX_OPEN_POSITIONS",
    ):
        monkeypatch.delenv(key, raising=False)

    monkeypatch.chdir(tmp_path)
    _clear_cli_modules()


def test_cli_help_does_not_require_env(monkeypatch, tmp_path) -> None:
    _clear_env(monkeypatch, tmp_path)
    commands = importlib.import_module("app.cli.commands")
    result = CliRunner().invoke(commands.app, ["--help"])

    assert result.exit_code == 0
    assert "CLI for the traders server runtime" in result.output


def test_load_history_help_works_without_runtime(monkeypatch, tmp_path) -> None:
    _clear_env(monkeypatch, tmp_path)
    commands = importlib.import_module("app.cli.commands")
    result = CliRunner().invoke(commands.app, ["load-history", "--help"])

    assert result.exit_code == 0
    assert "load historical binance candles" in result.output.lower()


def test_async_health_help_works_without_runtime(monkeypatch, tmp_path) -> None:
    _clear_env(monkeypatch, tmp_path)
    commands = importlib.import_module("app.cli.commands")
    result = CliRunner().invoke(commands.app, ["async-health", "--help"])

    assert result.exit_code == 0
    assert "async" in result.output.lower()


def test_backtest_help_works_without_runtime(monkeypatch, tmp_path) -> None:
    _clear_env(monkeypatch, tmp_path)
    commands = importlib.import_module("app.cli.commands")
    result = CliRunner().invoke(commands.app, ["backtest", "--help"])

    assert result.exit_code == 0
    assert "historical backtest" in result.output.lower()


def test_paper_runner_help_works_without_runtime(monkeypatch, tmp_path) -> None:
    _clear_env(monkeypatch, tmp_path)
    commands = importlib.import_module("app.cli.commands")
    result = CliRunner().invoke(commands.app, ["paper-runner", "--help"])

    assert result.exit_code == 0
    assert "paper-only runner" in result.output.lower()


def test_cli_error_text_falls_back_to_ascii_for_cp1251(monkeypatch, tmp_path) -> None:
    _clear_env(monkeypatch, tmp_path)
    commands = importlib.import_module("app.cli.commands")

    class _FakeStream:
        encoding = "cp1251"

    assert commands._supports_unicode_stream(_FakeStream()) is False
    assert commands._safe_output_text("bad \u2807 output", _FakeStream()) == "bad \\u2807 output"
