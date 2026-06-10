import json

from app.gates.gate_policy_prediction_runtime_shape import (
    PredictionRuntimeShapeFile,
    PredictionRuntimeShapeReport,
)
from app.gates.gate_policy_prediction_runtime_shape_reporter import (
    GatePolicyPredictionRuntimeShapeReporter,
)


def build_runtime_shape_report() -> PredictionRuntimeShapeReport:
    return PredictionRuntimeShapeReport(
        root_path=".",
        target_paths=(
            "app/prediction/predictor.py",
            "app/prediction/prediction_service.py",
            "app/api/schemas.py",
        ),
        files=(
            PredictionRuntimeShapeFile(
                path="app/prediction/predictor.py",
                exists=True,
                class_names=("PredictionRuntime", "Predictor"),
                function_names=(
                    "__init__",
                    "predict",
                    "prepare_runtime",
                    "predict_from_feature_record",
                ),
                matched_keywords=(
                    "prob_up",
                    "prob_down",
                    "prob_flat",
                    "confidence",
                    "risk_score",
                    "expected_move_atr",
                    "tp_before_sl_probability",
                    "model_version",
                    "prediction",
                    "predictor",
                    "symbol",
                    "interval",
                    "candle",
                    "candles",
                    "model",
                ),
                line_count=200,
            ),
            PredictionRuntimeShapeFile(
                path="app/prediction/prediction_service.py",
                exists=True,
                class_names=("PredictionService",),
                function_names=("__init__", "predict"),
                matched_keywords=(
                    "model_version",
                    "prediction",
                    "predictor",
                ),
                line_count=80,
            ),
            PredictionRuntimeShapeFile(
                path="app/api/schemas.py",
                exists=True,
                class_names=(
                    "PredictionCandleInput",
                    "PredictionContextInput",
                    "PredictionRequest",
                    "PredictionResponse",
                ),
                function_names=(),
                matched_keywords=(
                    "prob_up",
                    "prob_down",
                    "prob_flat",
                    "confidence",
                    "risk_score",
                    "expected_move_atr",
                    "tp_before_sl_probability",
                    "model_version",
                ),
                line_count=120,
            ),
        ),
    )


def test_prediction_runtime_shape_reporter_converts_file_to_dict() -> None:
    reporter = GatePolicyPredictionRuntimeShapeReporter()

    payload = reporter.file_to_dict(
        PredictionRuntimeShapeFile(
            path="app/prediction/predictor.py",
            exists=True,
            class_names=("Predictor",),
            function_names=("predict",),
            matched_keywords=("confidence", "model_version"),
            line_count=100,
        )
    )

    assert payload["path"] == "app/prediction/predictor.py"
    assert payload["exists"] is True
    assert payload["class_names"] == ["Predictor"]
    assert payload["function_names"] == ["predict"]
    assert payload["matched_keywords"] == ["confidence", "model_version"]
    assert payload["line_count"] == 100
    assert payload["has_runtime_shape_signals"] is True


def test_prediction_runtime_shape_reporter_builds_full_report_dict() -> None:
    reporter = GatePolicyPredictionRuntimeShapeReporter()
    report = build_runtime_shape_report()

    payload = reporter.report_to_dict(report)

    assert payload["root_path"] == "."
    assert payload["target_paths"] == [
        "app/prediction/predictor.py",
        "app/prediction/prediction_service.py",
        "app/api/schemas.py",
    ]
    assert payload["total_targets"] == 3
    assert payload["existing_targets"] == 3
    assert payload["missing_targets"] == 0
    assert payload["files_with_runtime_shape_signals"] == 3
    assert payload["shown_files"] == 3
    assert payload["files_truncated"] is False

    assert "Predictor" in payload["unique_class_names"]
    assert "PredictionService" in payload["unique_class_names"]
    assert "PredictionResponse" in payload["unique_class_names"]

    assert "predict" in payload["unique_function_names"]
    assert "prepare_runtime" in payload["unique_function_names"]

    assert "prob_up" in payload["unique_keywords"]
    assert "confidence" in payload["unique_keywords"]
    assert "model_version" in payload["unique_keywords"]

    assert payload["class_name_counts"]["Predictor"] == 1
    assert payload["function_name_counts"]["predict"] == 2
    assert payload["keyword_counts"]["model_version"] == 3
    assert payload["keyword_counts"]["confidence"] == 2
    assert payload["keyword_counts"]["prob_up"] == 2

    assert payload["files"][0]["path"] == "app/prediction/predictor.py"

    assert payload["integration_status"]["prediction_service_imported"] is False
    assert payload["integration_status"]["predictor_imported"] is False
    assert payload["integration_status"]["database_connected"] is False
    assert payload["integration_status"]["model_inference_connected"] is False
    assert payload["integration_status"]["traders_core_connected"] is False
    assert payload["integration_status"]["live_trading_connected"] is False


def test_prediction_runtime_shape_reporter_limits_files() -> None:
    reporter = GatePolicyPredictionRuntimeShapeReporter()
    report = build_runtime_shape_report()

    payload = reporter.report_to_dict(report, max_files=2)

    assert payload["total_targets"] == 3
    assert payload["shown_files"] == 2
    assert payload["files_truncated"] is True
    assert len(payload["files"]) == 2


def test_prediction_runtime_shape_reporter_builds_summary_dict() -> None:
    reporter = GatePolicyPredictionRuntimeShapeReporter()
    report = build_runtime_shape_report()

    payload = reporter.summary_to_dict(report)

    assert payload["root_path"] == "."
    assert payload["total_targets"] == 3
    assert payload["existing_targets"] == 3
    assert payload["missing_targets"] == 0
    assert payload["files_with_runtime_shape_signals"] == 3

    assert "files" not in payload
    assert "shown_files" not in payload
    assert "files_truncated" not in payload

    assert payload["class_name_counts"]["PredictionRuntime"] == 1
    assert payload["function_name_counts"]["predict"] == 2
    assert payload["keyword_counts"]["model_version"] == 3


def test_prediction_runtime_shape_reporter_converts_report_to_json() -> None:
    reporter = GatePolicyPredictionRuntimeShapeReporter()
    report = build_runtime_shape_report()

    json_payload = reporter.report_to_json(report, max_files=1)
    payload = json.loads(json_payload)

    assert payload["total_targets"] == 3
    assert payload["shown_files"] == 1
    assert payload["files_truncated"] is True
    assert payload["files"][0]["path"] == "app/prediction/predictor.py"


def test_prediction_runtime_shape_reporter_converts_summary_to_json() -> None:
    reporter = GatePolicyPredictionRuntimeShapeReporter()
    report = build_runtime_shape_report()

    json_payload = reporter.summary_to_json(report)
    payload = json.loads(json_payload)

    assert payload["total_targets"] == 3
    assert payload["existing_targets"] == 3
    assert payload["keyword_counts"]["confidence"] == 2
    assert "files" not in payload


def test_prediction_runtime_shape_reporter_supports_compact_json() -> None:
    reporter = GatePolicyPredictionRuntimeShapeReporter()
    report = build_runtime_shape_report()

    json_payload = reporter.report_to_json(report, indent=None)

    assert "\n" not in json_payload

    payload = json.loads(json_payload)

    assert payload["total_targets"] == 3
    assert payload["shown_files"] == 3
