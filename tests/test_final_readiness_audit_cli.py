import json
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from app.cli.commands import build_final_readiness_audit_preview_payload, cli


def test_build_final_readiness_audit_preview_payload() -> None:
    payload = build_final_readiness_audit_preview_payload()

    assert payload["audit_name"] == "traders_ml_final_standalone_readiness_audit"
    assert payload["audit_version"] == "ml24"
    assert payload["status"] == "READY_STANDALONE"
    assert payload["standalone_ml_service_ready"] is True
    assert payload["traders_core_connected"] is False
    assert payload["live_trading_connected"] is False
    assert payload["orders_enabled"] is False


def test_final_readiness_audit_preview_cli_outputs_json() -> None:
    runner = CliRunner()

    result = runner.invoke(cli, ["final-readiness-audit-preview"])

    assert result.exit_code == 0

    payload = json.loads(result.stdout)

    assert payload["audit_name"] == "traders_ml_final_standalone_readiness_audit"
    assert payload["status"] == "READY_STANDALONE"
    assert payload["ready_component_count"] > 0


def test_final_readiness_audit_export_cli_writes_json(tmp_path: Path) -> None:
    runner = CliRunner()
    output_path = tmp_path / "final_standalone_readiness_audit.json"

    result = runner.invoke(
        cli,
        [
            "final-readiness-audit-export",
            "--output-path",
            str(output_path),
        ],
    )

    assert result.exit_code == 0

    command_payload = json.loads(result.stdout)
    file_payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert command_payload["status"] == "ok"
    assert command_payload["audit_name"] == "traders_ml_final_standalone_readiness_audit"
    assert command_payload["readiness_status"] == "READY_STANDALONE"
    assert command_payload["orders_enabled"] is False
    assert command_payload["live_trading_connected"] is False
    assert command_payload["traders_core_connected"] is False

    assert file_payload["audit_name"] == "traders_ml_final_standalone_readiness_audit"
    assert file_payload["status"] == "READY_STANDALONE"
    assert file_payload["safety_boundaries"]["orders_enabled"] is False
    assert file_payload["safety_boundaries"]["live_trading_connected"] is False
    assert file_payload["safety_boundaries"]["traders_core_connected"] is False


def test_final_readiness_audit_export_artifact_is_not_tracked_by_git() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    result = subprocess.run(
        [
            "git",
            "ls-files",
            "--error-unmatch",
            "reports/final_standalone_readiness_audit.json",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
