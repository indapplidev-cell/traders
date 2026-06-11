import json
import subprocess
import sys
from pathlib import Path

from typer.testing import CliRunner

from app.cli.commands import (
    build_gate_policy_runtime_binding_preview_payload,
    cli,
)


def test_build_gate_policy_runtime_binding_preview_payload() -> None:
    payload = build_gate_policy_runtime_binding_preview_payload()

    assert payload["binding_name"] == "gate_policy_prediction_runtime_binding"
    assert payload["binding_version"] == "ml21.1"
    assert payload["is_valid"] is True
    assert payload["direction"] == "LONG"
    assert payload["gate_policy_payload"]["direction"] == "LONG"
    assert payload["gate_policy_decision"]["decision"] == "ALLOW_LONG"
    assert payload["integration_status"]["database_connected"] is False
    assert payload["integration_status"]["traders_core_connected"] is False
    assert payload["integration_status"]["live_trading_connected"] is False
    assert payload["integration_status"]["orders_enabled"] is False


def test_gate_policy_runtime_binding_preview_cli_outputs_json() -> None:
    runner = CliRunner()

    result = runner.invoke(cli, ["gate-policy-runtime-binding-preview"])

    assert result.exit_code == 0

    payload = json.loads(result.stdout)

    assert payload["binding_name"] == "gate_policy_prediction_runtime_binding"
    assert payload["binding_version"] == "ml21.1"
    assert payload["direction"] == "LONG"
    assert payload["gate_policy_decision"]["decision"] == "ALLOW_LONG"


def test_gate_policy_runtime_binding_export_cli_creates_json_file(tmp_path: Path) -> None:
    runner = CliRunner()
    output_path = tmp_path / "gate_policy_runtime_binding_summary.json"

    result = runner.invoke(
        cli,
        [
            "gate-policy-runtime-binding-export",
            "--output-path",
            str(output_path),
        ],
    )

    assert result.exit_code == 0

    command_payload = json.loads(result.stdout)
    file_payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert command_payload["status"] == "ok"
    assert command_payload["sample_direction"] == "LONG"
    assert command_payload["sample_is_valid"] is True
    assert file_payload["binding_name"] == "gate_policy_prediction_runtime_binding"
    assert file_payload["sample_result"]["direction"] == "LONG"


def test_gate_policy_runtime_binding_export_artifact_is_not_tracked_by_git() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    result = subprocess.run(
        [
            "git",
            "ls-files",
            "--error-unmatch",
            "reports/gate_policy_runtime_binding_summary.json",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0


def test_gate_policy_runtime_binding_preview_real_module_command_outputs_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.cli.commands",
            "gate-policy-runtime-binding-preview",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)

    assert payload["binding_name"] == "gate_policy_prediction_runtime_binding"
    assert payload["binding_version"] == "ml21.1"
    assert payload["gate_policy_decision"]["decision"] == "ALLOW_LONG"
