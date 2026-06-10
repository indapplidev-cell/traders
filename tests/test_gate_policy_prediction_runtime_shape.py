import json
from pathlib import Path

from app.gates.gate_policy_prediction_runtime_shape import (
    GatePolicyPredictionRuntimeShapeDiscoveryService,
)


def create_fake_runtime_project(root_path: Path) -> None:
    prediction_dir = root_path / "app" / "prediction"
    prediction_dir.mkdir(parents=True)

    predictor_file = prediction_dir / "predictor.py"
    predictor_file.write_text(
        """
class PredictionOutput:
    prob_up: float
    prob_down: float
    prob_flat: float
    confidence: float
    risk_score: float
    expected_move_atr: float
    tp_before_sl_probability: float
    model_version: str


class Predictor:
    def predict(self, candles):
        prediction = {
            "prob_up": 0.40,
            "prob_down": 0.30,
            "prob_flat": 0.30,
            "confidence": 0.70,
            "risk_score": 0.20,
            "expected_move_atr": 1.25,
            "tp_before_sl_probability": 0.65,
            "model_version": "demo",
        }
        return prediction
""",
        encoding="utf-8",
    )

    prediction_service_file = prediction_dir / "prediction_service.py"
    prediction_service_file.write_text(
        """
class PredictionService:
    async def predict_for_symbol(self, symbol: str, interval: str):
        return {
            "symbol": symbol,
            "interval": interval,
            "regime": "trend_up",
        }
""",
        encoding="utf-8",
    )

    api_dir = root_path / "app" / "api"
    api_dir.mkdir(parents=True)

    schemas_file = api_dir / "schemas.py"
    schemas_file.write_text(
        """
class PredictionResponse:
    prob_up: float
    prob_down: float
    prob_flat: float
    confidence: float
    model_version: str
""",
        encoding="utf-8",
    )

    tests_dir = root_path / "tests"
    tests_dir.mkdir(parents=True)

    (tests_dir / "test_predictor.py").write_text(
        """
def test_predictor_returns_probabilities():
    assert "prob_up"
""",
        encoding="utf-8",
    )

    (tests_dir / "test_prediction_service.py").write_text(
        """
def test_prediction_service_returns_model_version():
    assert "model_version"
""",
        encoding="utf-8",
    )

    (tests_dir / "test_api_predict.py").write_text(
        """
def test_api_predict_response_contains_confidence():
    assert "confidence"
""",
        encoding="utf-8",
    )


def test_prediction_runtime_shape_discovery_finds_target_files(tmp_path: Path) -> None:
    create_fake_runtime_project(tmp_path)

    service = GatePolicyPredictionRuntimeShapeDiscoveryService()
    report = service.discover(tmp_path)

    assert report.total_targets == 6
    assert report.existing_targets == 6
    assert report.missing_targets == 0
    assert report.files_with_runtime_shape_signals == 6

    assert "PredictionOutput" in report.unique_class_names
    assert "Predictor" in report.unique_class_names
    assert "PredictionService" in report.unique_class_names
    assert "PredictionResponse" in report.unique_class_names

    assert "predict" in report.unique_function_names
    assert "predict_for_symbol" in report.unique_function_names

    assert "prob_up" in report.unique_keywords
    assert "prob_down" in report.unique_keywords
    assert "prob_flat" in report.unique_keywords
    assert "confidence" in report.unique_keywords
    assert "risk_score" in report.unique_keywords
    assert "expected_move_atr" in report.unique_keywords
    assert "tp_before_sl_probability" in report.unique_keywords
    assert "model_version" in report.unique_keywords
    assert "regime" in report.unique_keywords


def test_prediction_runtime_shape_discovery_reports_missing_files(tmp_path: Path) -> None:
    service = GatePolicyPredictionRuntimeShapeDiscoveryService(
        target_paths=(
            "app/prediction/predictor.py",
            "app/prediction/missing.py",
        )
    )

    prediction_dir = tmp_path / "app" / "prediction"
    prediction_dir.mkdir(parents=True)

    (prediction_dir / "predictor.py").write_text(
        """
class Predictor:
    def predict(self):
        return {"confidence": 0.8}
""",
        encoding="utf-8",
    )

    report = service.discover(tmp_path)

    assert report.total_targets == 2
    assert report.existing_targets == 1
    assert report.missing_targets == 1

    assert report.files[0].path == "app/prediction/predictor.py"
    assert report.files[0].exists is True

    assert report.files[1].path == "app/prediction/missing.py"
    assert report.files[1].exists is False
    assert report.files[1].line_count == 0


def test_prediction_runtime_shape_file_to_dict_is_json_safe(tmp_path: Path) -> None:
    create_fake_runtime_project(tmp_path)

    service = GatePolicyPredictionRuntimeShapeDiscoveryService()
    report = service.discover(tmp_path)

    payload = report.files[0].to_dict()

    assert payload["path"] == "app/prediction/predictor.py"
    assert payload["exists"] is True
    assert "PredictionOutput" in payload["class_names"]
    assert "Predictor" in payload["class_names"]
    assert "predict" in payload["function_names"]
    assert "confidence" in payload["matched_keywords"]
    assert payload["line_count"] > 0
    assert payload["has_runtime_shape_signals"] is True

    json.dumps(payload, ensure_ascii=False)


def test_prediction_runtime_shape_report_to_dict_is_json_safe(tmp_path: Path) -> None:
    create_fake_runtime_project(tmp_path)

    service = GatePolicyPredictionRuntimeShapeDiscoveryService()
    report = service.discover(tmp_path)
    payload = report.to_dict()

    assert payload["root_path"] == str(tmp_path)
    assert payload["total_targets"] == 6
    assert payload["existing_targets"] == 6
    assert payload["missing_targets"] == 0
    assert payload["files_with_runtime_shape_signals"] == 6

    assert "PredictionOutput" in payload["unique_class_names"]
    assert "predict" in payload["unique_function_names"]
    assert "prob_up" in payload["unique_keywords"]
    assert "model_version" in payload["unique_keywords"]

    assert payload["integration_status"]["prediction_service_imported"] is False
    assert payload["integration_status"]["predictor_imported"] is False
    assert payload["integration_status"]["database_connected"] is False
    assert payload["integration_status"]["model_inference_connected"] is False
    assert payload["integration_status"]["traders_core_connected"] is False
    assert payload["integration_status"]["live_trading_connected"] is False

    json.dumps(payload, ensure_ascii=False)
