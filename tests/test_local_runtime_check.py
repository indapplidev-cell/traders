from __future__ import annotations

import subprocess
import sys
from types import SimpleNamespace

import pytest

from scripts import local_runtime_check as runtime_check


def make_args(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "symbol": "BTCUSDT",
        "interval": "15m",
        "days": 7,
        "ticks": 3,
        "sleep_seconds": 0,
        "strategy": "simple_trend",
        "initial_cash": "1000",
        "fresh_db": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_step_result_ok_returns_true_for_zero_code() -> None:
    result = runtime_check.StepResult(
        title="ok",
        command=["python", "--version"],
        returncode=0,
        stdout="",
        stderr="",
    )

    assert result.ok is True


def test_step_result_ok_returns_false_for_non_zero_code() -> None:
    result = runtime_check.StepResult(
        title="fail",
        command=["python", "--bad"],
        returncode=1,
        stdout="",
        stderr="error",
    )

    assert result.ok is False


def test_build_python_command_uses_current_executable() -> None:
    command = runtime_check.build_python_command(["-m", "app.cli.commands", "health"])

    assert command[0] == sys.executable
    assert command[1:] == ["-m", "app.cli.commands", "health"]


def test_build_cli_command_uses_app_cli_commands_module() -> None:
    command = runtime_check.build_cli_command(["health"])

    assert command == [
        sys.executable,
        "-m",
        "app.cli.commands",
        "health",
    ]


def test_build_alembic_command_uses_python_module_invocation() -> None:
    command = runtime_check.build_alembic_command(["current"])

    assert command == [
        sys.executable,
        "-m",
        "alembic",
        "current",
    ]


def test_build_demo_command_contains_expected_arguments() -> None:
    args = make_args(
        symbol="ETHUSDT",
        interval="1h",
        days=14,
        ticks=5,
        sleep_seconds=0,
        strategy="simple_trend",
        initial_cash="2000",
    )

    command = runtime_check.build_demo_command(args)

    assert command[0] == sys.executable
    assert str(runtime_check.PROJECT_ROOT / "scripts" / "demo_traders_pipeline.py") in command
    assert "--symbol" in command
    assert "ETHUSDT" in command
    assert "--interval" in command
    assert "1h" in command
    assert "--days" in command
    assert "14" in command
    assert "--ticks" in command
    assert "5" in command
    assert "--initial-cash" in command
    assert "2000" in command


def test_build_docker_commands_without_fresh_db_has_no_destructive_down() -> None:
    commands = runtime_check.build_docker_commands(fresh_db=False)

    command_lines = [" ".join(spec.command) for spec in commands]

    assert "docker compose down -v" not in command_lines
    assert "docker compose up -d postgres" in command_lines


def test_build_docker_commands_with_fresh_db_contains_destructive_down() -> None:
    commands = runtime_check.build_docker_commands(fresh_db=True)

    destructive_specs = [spec for spec in commands if spec.destructive]
    command_lines = [" ".join(spec.command) for spec in destructive_specs]

    assert command_lines == ["docker compose down -v"]


def test_build_runtime_command_specs_contains_demo_pipeline() -> None:
    args = make_args(fresh_db=False)

    specs = runtime_check.build_runtime_command_specs(args)
    titles = [spec.title for spec in specs]

    assert "Demo pipeline" in titles


def test_build_runtime_command_specs_order_without_fresh_db() -> None:
    args = make_args(fresh_db=False)

    titles = [spec.title for spec in runtime_check.build_runtime_command_specs(args)]

    assert titles == [
        "Docker compose config",
        "Docker compose up postgres",
        "Docker compose ps",
        "Docker inspect postgres",
        "Python settings",
        "Health",
        "Async health",
        "Alembic upgrade head",
        "Alembic current",
        "Demo pipeline",
    ]


def test_build_runtime_command_specs_order_with_fresh_db() -> None:
    args = make_args(fresh_db=True)

    titles = [spec.title for spec in runtime_check.build_runtime_command_specs(args)]

    assert titles == [
        "Docker compose config",
        "Fresh DB: docker compose down -v",
        "Docker compose up postgres",
        "Docker compose ps",
        "Docker inspect postgres",
        "Python settings",
        "Health",
        "Async health",
        "Alembic upgrade head",
        "Alembic current",
        "Demo pipeline",
    ]


def test_mask_url_hides_password() -> None:
    value = "postgresql+psycopg://traders:local_dev_password@127.0.0.1:5432/traders"

    masked = runtime_check.mask_url(value)

    assert masked == "postgresql+psycopg://traders:***@127.0.0.1:5432/traders"
    assert "local_dev_password" not in masked


def test_detect_forbidden_env_returns_only_present_forbidden_names(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in runtime_check.FORBIDDEN_SECRET_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setenv("BINANCE_API_KEY", "secret-key")
    monkeypatch.setenv("BINANCE_SECRET_KEY", "secret-value")

    found = runtime_check.detect_forbidden_env()

    assert found == ["BINANCE_API_KEY", "BINANCE_SECRET_KEY"]


def test_mask_sensitive_text_hides_forbidden_secret_env_value(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in runtime_check.FORBIDDEN_SECRET_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setenv("BINANCE_API_KEY", "super-secret-token")

    masked = runtime_check.mask_sensitive_text("token=super-secret-token")

    assert "super-secret-token" not in masked
    assert "token=***" in masked


def test_mask_sensitive_text_hides_database_password_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://traders:local_dev_password@127.0.0.1:5432/traders",
    )

    masked = runtime_check.mask_sensitive_text(
        "DATABASE_URL=postgresql+psycopg://traders:local_dev_password@127.0.0.1:5432/traders"
    )

    assert "local_dev_password" not in masked
    assert "traders:***@" in masked


def test_run_command_step_marks_missing_expected_text_as_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    completed = subprocess.CompletedProcess(
        args=["demo"],
        returncode=0,
        stdout="Статус: ОШИБКА",
        stderr="",
    )

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return completed

    monkeypatch.setattr(runtime_check.subprocess, "run", fake_run)

    result = runtime_check.run_command_step(
        1,
        1,
        runtime_check.CommandSpec(
            title="Demo pipeline",
            command=["demo"],
            expected_text=("Статус: УСПЕХ",),
        ),
    )

    captured = capsys.readouterr()

    assert result.ok is False
    assert result.returncode == 1
    assert "Ожидаемый текст не найден" in result.stderr
    assert "Статус: ОШИБКА" in captured.out


def test_run_command_step_does_not_leak_sensitive_env_value(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("BINANCE_API_KEY", "secret-token")

    completed = subprocess.CompletedProcess(
        args=["fake"],
        returncode=1,
        stdout="stdout secret-token",
        stderr="stderr secret-token",
    )

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return completed

    monkeypatch.setattr(runtime_check.subprocess, "run", fake_run)

    result = runtime_check.run_command_step(
        1,
        1,
        runtime_check.CommandSpec(title="fake", command=["fake"]),
    )

    captured = capsys.readouterr()

    assert result.ok is False
    assert "secret-token" not in captured.out
    assert "stdout ***" in captured.out
    assert "stderr ***" in captured.out


def test_check_safety_guard_fails_when_forbidden_env_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in runtime_check.FORBIDDEN_SECRET_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setenv("BINANCE_PRIVATE_SECRET", "secret")

    with pytest.raises(RuntimeError) as exc_info:
        runtime_check.check_safety_guard()

    assert "BINANCE_PRIVATE_SECRET: найдена запрещённая переменная" in str(exc_info.value)
    assert "secret" not in str(exc_info.value)


def test_check_safety_guard_passes_without_forbidden_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in runtime_check.FORBIDDEN_SECRET_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)

    result = runtime_check.check_safety_guard()

    assert "Запрещённые Binance private env переменные: не найдены" in result
    assert "Live trading" not in result
