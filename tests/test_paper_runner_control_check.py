"""Tests for Stage 8 paper runner control check."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "paper_runner_control_check.py"


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("paper_runner_control_check", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)

    # dataclass + postponed annotations require the module to exist in sys.modules
    # before exec_module(), otherwise dataclasses cannot resolve cls.__module__.
    sys.modules[spec.name] = module

    spec.loader.exec_module(module)
    return module


def test_extract_session_id_from_ascii_table() -> None:
    module = load_module()

    output = """
Runner session result
+--------------------------------+
| field           | value        |
|-----------------+--------------|
| session id      | 20           |
| status          | STOPPED      |
+--------------------------------+
"""

    assert module.extract_session_id(output) == 20


def test_extract_session_id_from_colon_text() -> None:
    module = load_module()

    assert module.extract_session_id("session id: 42") == 42


def test_extract_session_id_raises_for_missing_id() -> None:
    module = load_module()

    try:
        module.extract_session_id("no session here")
    except RuntimeError as exc:
        assert "Cannot extract runner session id" in str(exc)
    else:
        raise AssertionError("RuntimeError was not raised")


def test_assert_contains_success() -> None:
    module = load_module()

    result = module.assert_contains("sample", "paper-runner is disabled for Stage 8", "Stage 8")

    assert result.ok is True
    assert result.name == "sample"
    assert "FOUND" in result.details


def test_assert_contains_failure() -> None:
    module = load_module()

    result = module.assert_contains("sample", "abc", "missing")

    assert result.ok is False
    assert result.name == "sample"
    assert "NOT FOUND" in result.details


def test_private_binance_env_guard_blocks_private_keys(monkeypatch) -> None:
    module = load_module()

    monkeypatch.setenv("BINANCE_API_KEY", "secret")

    result = module.require_no_private_binance_env()

    assert result.ok is False
    assert "BINANCE_API_KEY" in result.details


def test_private_binance_env_guard_allows_absent_private_keys(monkeypatch) -> None:
    module = load_module()

    monkeypatch.delenv("BINANCE_API_KEY", raising=False)
    monkeypatch.delenv("BINANCE_API_SECRET", raising=False)
    monkeypatch.delenv("BINANCE_SECRET_KEY", raising=False)

    result = module.require_no_private_binance_env()

    assert result.ok is True
    assert "private Binance env is absent" in result.details


def test_run_command_success(monkeypatch) -> None:
    module = load_module()

    class FakeCompletedProcess:
        returncode = 0
        stdout = "OK"

    def fake_run(*args: object, **kwargs: object) -> FakeCompletedProcess:
        return FakeCompletedProcess()

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = module.run_command(["python", "--version"])

    assert result.ok is True
    assert result.details == "OK"


def test_run_command_expected_failure(monkeypatch) -> None:
    module = load_module()

    class FakeCompletedProcess:
        returncode = 1
        stdout = "ERROR"

    def fake_run(*args: object, **kwargs: object) -> FakeCompletedProcess:
        return FakeCompletedProcess()

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = module.run_command(["python", "bad.py"], expect_success=False)

    assert result.ok is True
    assert result.details == "ERROR"
