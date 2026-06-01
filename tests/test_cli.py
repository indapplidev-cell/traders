from __future__ import annotations

import importlib
import sys

from typer.testing import CliRunner


def _clear_cli_modules() -> None:
    """Сбрасывает импортированные CLI-модули между тестами."""

    for module_name in ("app.cli.commands", "app.db.session", "app.db.async_session", "app.main"):
        sys.modules.pop(module_name, None)


def _clear_env(monkeypatch, tmp_path) -> None:
    """Убирает runtime-переменные, чтобы help не зависел от .env и БД."""

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
    """Проверяет, что help не тянет настройки и БД на этапе импорта."""

    _clear_env(monkeypatch, tmp_path)
    commands = importlib.import_module("app.cli.commands")
    result = CliRunner().invoke(commands.app, ["--help"])

    assert result.exit_code == 0
    assert "CLI для серверного ядра traders" in result.output


def test_load_history_help_works_without_runtime(monkeypatch, tmp_path) -> None:
    """Проверяет, что help команды load-history не требует БД и Binance."""

    _clear_env(monkeypatch, tmp_path)
    commands = importlib.import_module("app.cli.commands")
    result = CliRunner().invoke(commands.app, ["load-history", "--help"])

    assert result.exit_code == 0
    assert "загружает историю свечей" in result.output.lower()


def test_async_health_help_works_without_runtime(monkeypatch, tmp_path) -> None:
    """Проверяет, что help команды async-health не требует БД на импорте CLI."""

    _clear_env(monkeypatch, tmp_path)
    commands = importlib.import_module("app.cli.commands")
    result = CliRunner().invoke(commands.app, ["async-health", "--help"])

    assert result.exit_code == 0
    assert "async" in result.output.lower()


def test_backtest_help_works_without_runtime(monkeypatch, tmp_path) -> None:
    """Проверяет, что help новой backtest-команды не требует БД и Binance."""

    _clear_env(monkeypatch, tmp_path)
    commands = importlib.import_module("app.cli.commands")
    result = CliRunner().invoke(commands.app, ["backtest", "--help"])

    assert result.exit_code == 0
    assert "исторический backtest" in result.output.lower()


def test_paper_runner_help_works_without_runtime(monkeypatch, tmp_path) -> None:
    """Проверяет, что help runner-команды не требует доступа к БД."""

    _clear_env(monkeypatch, tmp_path)
    commands = importlib.import_module("app.cli.commands")
    result = CliRunner().invoke(commands.app, ["paper-runner", "--help"])

    assert result.exit_code == 0
    assert "paper-only runner" in result.output.lower()
