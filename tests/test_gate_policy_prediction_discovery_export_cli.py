import json
from pathlib import Path

from typer.testing import CliRunner

from app.cli.commands import (
    cli,
    export_gate_policy_prediction_discovery_summary_report,
)


def create_fake_prediction_project(root_path: Path) -> None:
    app_prediction_dir = root_path / "app" / "prediction"
    app_prediction_dir.mkdir(parents=True)

    predictor_file = app_prediction_dir / "predictor.py"
    predictor_file.write_text(
        """
prediction = {
    "prob_up": 0.40,
    "prob_down": 0.30,
    "prob_flat": 0.30,
    "confidence": 0.70,
    "risk_score": 0.20,
    "expected_move_atr": 1.25,
    "model_version": "demo",
}
""",
        encoding="utf-8",
    )

    app_evaluation_dir = root_path / "app" / "evaluation"
    app_evaluation_dir.mkdir(parents=True)

    evaluator_file = app_evaluation_dir / "profit_aware_evaluator.py"
    evaluator_file.write_text(
        """
payload = {
    "prediction": "LONG",
    "profit_factor": 1.2,
    "total_r": 3.5,
    "baseline": "ema",
    "regime": "trend_up",
}
""",
        encoding="utf-8",
    )

    tests_dir = root_path / "tests"
    tests_dir.mkdir(parents=True)

    test_file = tests_dir / "test_prediction_service.py"
    test_file.write_text(
        """
def test_prediction_payload():
    assert "predictor"
""",
        encoding="utf-8",
    )


def test_export_gate_policy_prediction_discovery_summary_report_writes_json_file(
    tmp_path: Path,
) -> None:
    project_path = tmp_path / "project"
    project_path.mkdir()
    create_fake_prediction_project(project_path)

    output_path = tmp_path / "gate_policy_prediction_discovery_summary.json"

    summary = export_gate_policy_prediction_discovery_summary_report(
        root_path=project_path,
        output_path=output_path,
    )

    assert summary["status"] == "ok"
    assert summary["output_path"] == str(output_path)
    assert summary["root_path"] == str(project_path)
    assert summary["total_files"] == 3
    assert summary["files_with_content_matches"] == 3
    assert summary["unique_name_keyword_count"] >= 4
    assert summary["unique_content_keyword_count"] >= 10

    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["root_path"] == str(project_path)
    assert payload["scan_dirs"] == ["app", "tests"]
    assert payload["total_files"] == 3
    assert payload["files_with_content_matches"] == 3

    assert "prob_up" in payload["unique_content_keywords"]
    assert "confidence" in payload["unique_content_keywords"]
    assert "profit_factor" in payload["unique_content_keywords"]
    assert "total_r" in payload["unique_content_keywords"]

    assert "files" not in payload
    assert "shown_files" not in payload
    assert "files_truncated" not in payload

    assert payload["integration_status"]["database_connected"] is False
    assert payload["integration_status"]["model_inference_connected"] is False
    assert payload["integration_status"]["traders_core_connected"] is False
    assert payload["integration_status"]["live_trading_connected"] is False


def test_gate_policy_prediction_discovery_export_cli_writes_json_file(
    tmp_path: Path,
) -> None:
    project_path = tmp_path / "project"
    project_path.mkdir()
    create_fake_prediction_project(project_path)

    output_path = tmp_path / "cli_gate_policy_prediction_discovery_summary.json"

    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "gate-policy-prediction-discovery-export",
            "--root-path",
            str(project_path),
            "--output-path",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert output_path.exists()

    command_payload = json.loads(result.stdout)
    file_payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert command_payload["status"] == "ok"
    assert command_payload["output_path"] == str(output_path)
    assert command_payload["root_path"] == str(project_path)
    assert command_payload["total_files"] == 3
    assert command_payload["files_with_content_matches"] == 3
    assert command_payload["unique_name_keyword_count"] >= 4
    assert command_payload["unique_content_keyword_count"] >= 10

    assert file_payload["root_path"] == str(project_path)
    assert file_payload["scan_dirs"] == ["app", "tests"]
    assert file_payload["total_files"] == 3
    assert file_payload["files_with_content_matches"] == 3

    assert "prob_up" in file_payload["unique_content_keywords"]
    assert "prob_down" in file_payload["unique_content_keywords"]
    assert "prob_flat" in file_payload["unique_content_keywords"]
    assert "confidence" in file_payload["unique_content_keywords"]
    assert "model_version" in file_payload["unique_content_keywords"]

    assert "files" not in file_payload
