import json

from app.gates.gate_policy_prediction_discovery import (
    PredictionDiscoveryFile,
    PredictionServiceDiscoveryReport,
)
from app.gates.gate_policy_prediction_discovery_reporter import (
    GatePolicyPredictionDiscoveryReporter,
)


def build_discovery_report() -> PredictionServiceDiscoveryReport:
    return PredictionServiceDiscoveryReport(
        root_path=".",
        scan_dirs=("app", "tests"),
        files=(
            PredictionDiscoveryFile(
                path="app/prediction/predictor.py",
                matched_name_keywords=("predict", "prediction"),
                matched_content_keywords=(
                    "prob_up",
                    "prob_down",
                    "prob_flat",
                    "confidence",
                    "risk_score",
                    "expected_move_atr",
                    "model_version",
                ),
            ),
            PredictionDiscoveryFile(
                path="app/evaluation/profit_aware_evaluator.py",
                matched_name_keywords=("profit", "evaluator", "evaluation"),
                matched_content_keywords=(
                    "confidence",
                    "prediction",
                    "profit_factor",
                    "total_r",
                ),
            ),
            PredictionDiscoveryFile(
                path="tests/test_prediction_service.py",
                matched_name_keywords=("predict", "prediction"),
                matched_content_keywords=(
                    "model_version",
                    "prediction",
                    "predictor",
                ),
            ),
        ),
    )


def test_gate_policy_prediction_discovery_reporter_converts_file_to_dict() -> None:
    reporter = GatePolicyPredictionDiscoveryReporter()

    payload = reporter.file_to_dict(
        PredictionDiscoveryFile(
            path="app/prediction/predictor.py",
            matched_name_keywords=("predict", "prediction"),
            matched_content_keywords=("prob_up", "confidence"),
        )
    )

    assert payload["path"] == "app/prediction/predictor.py"
    assert payload["matched_name_keywords"] == ["predict", "prediction"]
    assert payload["matched_content_keywords"] == ["prob_up", "confidence"]
    assert payload["has_content_matches"] is True


def test_gate_policy_prediction_discovery_reporter_builds_full_report_dict() -> None:
    reporter = GatePolicyPredictionDiscoveryReporter()
    report = build_discovery_report()

    payload = reporter.report_to_dict(report)

    assert payload["root_path"] == "."
    assert payload["scan_dirs"] == ["app", "tests"]
    assert payload["total_files"] == 3
    assert payload["files_with_content_matches"] == 3
    assert payload["shown_files"] == 3
    assert payload["files_truncated"] is False

    assert payload["unique_name_keywords"] == [
        "evaluation",
        "evaluator",
        "predict",
        "prediction",
        "profit",
    ]

    assert "prob_up" in payload["unique_content_keywords"]
    assert "confidence" in payload["unique_content_keywords"]
    assert "profit_factor" in payload["unique_content_keywords"]

    assert payload["name_keyword_counts"]["predict"] == 2
    assert payload["name_keyword_counts"]["prediction"] == 2
    assert payload["name_keyword_counts"]["profit"] == 1

    assert payload["content_keyword_counts"]["confidence"] == 2
    assert payload["content_keyword_counts"]["model_version"] == 2
    assert payload["content_keyword_counts"]["prediction"] == 2
    assert payload["content_keyword_counts"]["prob_up"] == 1

    assert payload["files"][0]["path"] == "app/prediction/predictor.py"

    assert payload["integration_status"]["database_connected"] is False
    assert payload["integration_status"]["model_inference_connected"] is False
    assert payload["integration_status"]["traders_core_connected"] is False
    assert payload["integration_status"]["live_trading_connected"] is False


def test_gate_policy_prediction_discovery_reporter_limits_files() -> None:
    reporter = GatePolicyPredictionDiscoveryReporter()
    report = build_discovery_report()

    payload = reporter.report_to_dict(report, max_files=2)

    assert payload["total_files"] == 3
    assert payload["shown_files"] == 2
    assert payload["files_truncated"] is True
    assert len(payload["files"]) == 2


def test_gate_policy_prediction_discovery_reporter_builds_summary_dict() -> None:
    reporter = GatePolicyPredictionDiscoveryReporter()
    report = build_discovery_report()

    payload = reporter.summary_to_dict(report)

    assert payload["root_path"] == "."
    assert payload["scan_dirs"] == ["app", "tests"]
    assert payload["total_files"] == 3
    assert payload["files_with_content_matches"] == 3

    assert "files" not in payload
    assert "shown_files" not in payload
    assert "files_truncated" not in payload

    assert payload["content_keyword_counts"]["confidence"] == 2
    assert payload["content_keyword_counts"]["model_version"] == 2
    assert payload["name_keyword_counts"]["predict"] == 2


def test_gate_policy_prediction_discovery_reporter_converts_report_to_json() -> None:
    reporter = GatePolicyPredictionDiscoveryReporter()
    report = build_discovery_report()

    json_payload = reporter.report_to_json(report, max_files=1)
    payload = json.loads(json_payload)

    assert payload["total_files"] == 3
    assert payload["shown_files"] == 1
    assert payload["files_truncated"] is True
    assert payload["files"][0]["path"] == "app/prediction/predictor.py"


def test_gate_policy_prediction_discovery_reporter_converts_summary_to_json() -> None:
    reporter = GatePolicyPredictionDiscoveryReporter()
    report = build_discovery_report()

    json_payload = reporter.summary_to_json(report)
    payload = json.loads(json_payload)

    assert payload["total_files"] == 3
    assert payload["files_with_content_matches"] == 3
    assert payload["content_keyword_counts"]["confidence"] == 2
    assert "files" not in payload


def test_gate_policy_prediction_discovery_reporter_supports_compact_json() -> None:
    reporter = GatePolicyPredictionDiscoveryReporter()
    report = build_discovery_report()

    json_payload = reporter.report_to_json(report, indent=None)

    assert "\n" not in json_payload

    payload = json.loads(json_payload)

    assert payload["total_files"] == 3
    assert payload["shown_files"] == 3
