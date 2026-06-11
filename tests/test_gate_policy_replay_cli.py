import json
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from app.cli.commands import (
    build_gate_policy_replay_evaluate_preview_payload,
    cli,
)


def test_build_gate_policy_replay_evaluate_preview_payload() -> None:
    payload = build_gate_policy_replay_evaluate_preview_payload()

    assert payload["evaluator_name"] == "gate_policy_replay_evaluator"
    assert payload["evaluator_version"] == "ml23.1"
    assert payload["total_records"] == 5
    assert payload["valid_records"] == 4
    assert payload["invalid_records"] == 1
    assert payload["direction_counts"] == {
        "LONG": 1,
        "SHORT": 1,
        "FLAT": 1,
        "NONE": 2,
    }
    assert payload["integration_status"]["orders_enabled"] is False
    assert payload["integration_status"]["live_trading_connected"] is False
    assert payload["integration_status"]["traders_core_connected"] is False
    assert payload["integration_status"]["database_writes"] is False


def test_gate_policy_replay_evaluate_preview_cli_outputs_json() -> None:
    runner = CliRunner()

    result = runner.invoke(cli, ["gate-policy-replay-evaluate-preview"])

    assert result.exit_code == 0

    payload = json.loads(result.stdout)

    assert payload["evaluator_name"] == "gate_policy_replay_evaluator"
    assert payload["total_records"] == 5
    assert payload["direction_counts"]["NONE"] == 2


def test_gate_policy_replay_evaluate_export_cli_writes_json(tmp_path: Path) -> None:
    runner = CliRunner()
    output_path = tmp_path / "gate_policy_replay_evaluation_summary.json"

    result = runner.invoke(
        cli,
        [
            "gate-policy-replay-evaluate-export",
            "--output-path",
            str(output_path),
        ],
    )

    assert result.exit_code == 0

    command_payload = json.loads(result.stdout)
    file_payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert command_payload["status"] == "ok"
    assert command_payload["total_records"] == 5
    assert command_payload["orders_enabled"] is False
    assert command_payload["live_trading_connected"] is False
    assert command_payload["traders_core_connected"] is False
    assert command_payload["database_writes"] is False

    assert file_payload["total_records"] == 5
    assert file_payload["direction_counts"] == {
        "LONG": 1,
        "SHORT": 1,
        "FLAT": 1,
        "NONE": 2,
    }
    assert file_payload["orders_enabled"] is False
    assert file_payload["live_trading_connected"] is False
    assert file_payload["traders_core_connected"] is False
    assert file_payload["database_writes"] is False


def test_gate_policy_replay_evaluate_export_artifact_is_not_tracked_by_git() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    result = subprocess.run(
        [
            "git",
            "ls-files",
            "--error-unmatch",
            "reports/gate_policy_replay_evaluation_summary.json",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
