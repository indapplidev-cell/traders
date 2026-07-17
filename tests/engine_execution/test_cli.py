from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts" / "engine_execution_dry_run.py"


def run_cli(tmp_path, payload, mode, *, raw=False, path=None):
    source = path or tmp_path / "intent.json"
    if path is None:
        source.write_text(payload if raw else json.dumps(payload), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(CLI), str(source), "--mode", mode], cwd=ROOT,
        text=True, capture_output=True, check=False,
    )


@pytest.mark.parametrize("mode", ["PAPER", "DRY_RUN"])
def test_cli_safe_modes_return_ready_json(tmp_path, approved_payload, mode):
    result = run_cli(tmp_path, approved_payload, mode)
    output = json.loads(result.stdout)
    assert result.returncode == 0
    assert output["intent"]["status"] == "READY"
    assert output["intent"]["execution_mode"] == mode
    assert "Traceback" not in result.stderr


def test_cli_live_returns_nonzero_disabled_json(tmp_path, approved_payload):
    result = run_cli(tmp_path, approved_payload, "LIVE")
    assert result.returncode != 0
    assert json.loads(result.stdout)["reason_codes"] == ["LIVE_EXECUTION_DISABLED"]
    assert result.stderr == ""


def test_cli_invalid_mode_is_safe_json_error(tmp_path, approved_payload):
    result = run_cli(tmp_path, approved_payload, "UNKNOWN")
    assert result.returncode != 0
    assert json.loads(result.stdout)["reason_codes"] == ["CONTRACT_MISMATCH"]
    assert "unsupported execution mode" in result.stderr
    assert "Traceback" not in result.stderr


def test_cli_invalid_json_is_safe_json_error(tmp_path):
    result = run_cli(tmp_path, "{not-json", "DRY_RUN", raw=True)
    assert result.returncode != 0
    assert json.loads(result.stdout)["status"] == "REJECTED"
    assert "invalid JSON" in result.stderr
    assert "Traceback" not in result.stderr


def test_cli_missing_file_is_safe_json_error(tmp_path):
    result = run_cli(tmp_path, {}, "DRY_RUN", path=tmp_path / "missing.json")
    assert result.returncode != 0
    assert json.loads(result.stdout)["status"] == "REJECTED"
    assert "Traceback" not in result.stderr


def test_cli_missing_required_field_is_safe_json_error(tmp_path, payload_copy):
    payload = payload_copy()
    del payload["risk_decision"]
    result = run_cli(tmp_path, payload, "DRY_RUN")
    assert result.returncode != 0
    assert json.loads(result.stdout)["status"] == "REJECTED"
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), float("-inf")])
def test_cli_non_finite_prices_are_rejected(tmp_path, payload_copy, invalid):
    payload = payload_copy()
    payload["setup_context"]["reference_price"] = invalid
    result = run_cli(tmp_path, payload, "DRY_RUN")
    output = json.loads(result.stdout)
    assert result.returncode != 0
    assert "INVALID_PRICE" in output["intent"]["reason_codes"]
    assert "Traceback" not in result.stderr
