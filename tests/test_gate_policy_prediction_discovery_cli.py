import json
from pathlib import Path

from typer.testing import CliRunner

from app.cli.commands import (
    build_gate_policy_prediction_discovery_summary_payload,
    cli,
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


def test_build_gate_policy_prediction_discovery_summary_payload(tmp_path: Path) -> None:
    create_fake_prediction_project(tmp_path)

    payload = build_gate_policy_prediction_discovery_summary_payload(tmp_path)

    assert payload["root_path"] == str(tmp_path)
    assert payload["scan_dirs"] == ["app", "tests"]
    assert payload["total_files"] == 3
    assert payload["files_with_content_matches"] == 3

    assert "predict" in payload["unique_name_keywords"]
    assert "prediction" in payload["unique_name_keywords"]
    assert "profit" in payload["unique_name_keywords"]
    assert "evaluator" in payload["unique_name_keywords"]

    assert "prob_up" in payload["unique_content_keywords"]
    assert "prob_down" in payload["unique_content_keywords"]
    assert "prob_flat" in payload["unique_content_keywords"]
    assert "confidence" in payload["unique_content_keywords"]
    assert "risk_score" in payload["unique_content_keywords"]
    assert "expected_move_atr" in payload["unique_content_keywords"]
    assert "model_version" in payload["unique_content_keywords"]
    assert "profit_factor" in payload["unique_content_keywords"]
    assert "total_r" in payload["unique_content_keywords"]
    assert "baseline" in payload["unique_content_keywords"]
    assert "regime" in payload["unique_content_keywords"]

    assert "files" not in payload

    assert payload["integration_status"]["database_connected"] is False
    assert payload["integration_status"]["model_inference_connected"] is False
    assert payload["integration_status"]["traders_core_connected"] is False
    assert payload["integration_status"]["live_trading_connected"] is False


def test_gate_policy_prediction_discovery_summary_cli_outputs_json(
    tmp_path: Path,
) -> None:
    create_fake_prediction_project(tmp_path)

    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "gate-policy-prediction-discovery-summary",
            "--root-path",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0

    payload = json.loads(result.stdout)

    assert payload["root_path"] == str(tmp_path)
    assert payload["scan_dirs"] == ["app", "tests"]
    assert payload["total_files"] == 3
    assert payload["files_with_content_matches"] == 3

    assert "predict" in payload["unique_name_keywords"]
    assert "prediction" in payload["unique_name_keywords"]

    assert "prob_up" in payload["unique_content_keywords"]
    assert "confidence" in payload["unique_content_keywords"]
    assert "profit_factor" in payload["unique_content_keywords"]
    assert "total_r" in payload["unique_content_keywords"]

    assert payload["content_keyword_counts"]["prediction"] >= 1
    assert payload["content_keyword_counts"]["confidence"] == 1
    assert payload["content_keyword_counts"]["model_version"] == 1

    assert "files" not in payload

    assert payload["integration_status"]["database_connected"] is False
    assert payload["integration_status"]["traders_core_connected"] is False
