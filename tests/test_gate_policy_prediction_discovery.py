import json
from pathlib import Path

from app.gates.gate_policy_prediction_discovery import (
    GatePolicyPredictionDiscoveryService,
)


def test_gate_policy_prediction_discovery_finds_files_by_name_and_content(
    tmp_path: Path,
) -> None:
    app_dir = tmp_path / "app" / "prediction"
    app_dir.mkdir(parents=True)

    prediction_file = app_dir / "prediction_service.py"
    prediction_file.write_text(
        """
prob_up = 0.40
prob_down = 0.30
prob_flat = 0.30
confidence = 0.70
risk_score = 0.20
expected_move_atr = 1.25
model_version = "demo"
""",
        encoding="utf-8",
    )

    service = GatePolicyPredictionDiscoveryService()
    report = service.discover(tmp_path)

    assert report.total_files == 1
    assert report.files_with_content_matches == 1

    discovered = report.files[0]

    assert discovered.path == "app/prediction/prediction_service.py"
    assert "prediction" in discovered.matched_name_keywords
    assert "prob_up" in discovered.matched_content_keywords
    assert "prob_down" in discovered.matched_content_keywords
    assert "prob_flat" in discovered.matched_content_keywords
    assert "confidence" in discovered.matched_content_keywords
    assert "risk_score" in discovered.matched_content_keywords
    assert "expected_move_atr" in discovered.matched_content_keywords
    assert "model_version" in discovered.matched_content_keywords


def test_gate_policy_prediction_discovery_finds_test_files_by_content(
    tmp_path: Path,
) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir(parents=True)

    test_file = tests_dir / "test_anything.py"
    test_file.write_text(
        """
def test_profit_aware_prediction_payload():
    payload = {
        "total_r": 1.5,
        "profit_factor": 1.2,
        "baseline": "ema",
        "regime": "trend_up",
    }
""",
        encoding="utf-8",
    )

    service = GatePolicyPredictionDiscoveryService()
    report = service.discover(tmp_path)

    assert report.total_files == 1

    discovered = report.files[0]

    assert discovered.path == "tests/test_anything.py"
    assert discovered.matched_name_keywords == ()
    assert "total_r" in discovered.matched_content_keywords
    assert "profit_factor" in discovered.matched_content_keywords
    assert "baseline" in discovered.matched_content_keywords
    assert "regime" in discovered.matched_content_keywords


def test_gate_policy_prediction_discovery_ignores_unrelated_files(tmp_path: Path) -> None:
    app_dir = tmp_path / "app" / "misc"
    app_dir.mkdir(parents=True)

    unrelated_file = app_dir / "helpers.py"
    unrelated_file.write_text(
        """
def add(left: int, right: int) -> int:
    return left + right
""",
        encoding="utf-8",
    )

    service = GatePolicyPredictionDiscoveryService()
    report = service.discover(tmp_path)

    assert report.total_files == 0
    assert report.files == ()
    assert report.unique_content_keywords == ()


def test_gate_policy_prediction_discovery_report_to_dict_is_json_safe(
    tmp_path: Path,
) -> None:
    app_dir = tmp_path / "app"
    app_dir.mkdir(parents=True)

    predictor_file = app_dir / "predictor.py"
    predictor_file.write_text(
        """
prediction = {
    "confidence": 0.8,
    "tp_before_sl_probability": 0.65,
}
""",
        encoding="utf-8",
    )

    service = GatePolicyPredictionDiscoveryService()
    report = service.discover(tmp_path)
    payload = report.to_dict()

    assert payload["root_path"] == str(tmp_path)
    assert payload["scan_dirs"] == ["app", "tests"]
    assert payload["total_files"] == 1
    assert payload["files_with_content_matches"] == 1
    assert payload["files"][0]["path"] == "app/predictor.py"
    assert payload["integration_status"]["database_connected"] is False
    assert payload["integration_status"]["model_inference_connected"] is False
    assert payload["integration_status"]["traders_core_connected"] is False
    assert payload["integration_status"]["live_trading_connected"] is False

    json.dumps(payload, ensure_ascii=False)
