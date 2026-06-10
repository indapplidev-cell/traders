import json
from pathlib import Path

from typer.testing import CliRunner

from app.cli.commands import (
    build_gate_policy_prediction_runtime_shape_summary_payload,
    cli,
)


def create_fake_runtime_shape_project(root_path: Path) -> None:
    prediction_dir = root_path / "app" / "prediction"
    prediction_dir.mkdir(parents=True)

    predictor_file = prediction_dir / "predictor.py"
    predictor_file.write_text(
        '''
class PredictionRuntime:
    pass


class Predictor:
    def predict(self, candles):
        return {
            "prob_up": 0.40,
            "prob_down": 0.30,
            "prob_flat": 0.30,
            "confidence": 0.70,
            "risk_score": 0.20,
            "expected_move_atr": 1.25,
            "tp_before_sl_probability": 0.65,
            "model_version": "demo",
        }

    def prepare_runtime(self):
        return PredictionRuntime()
''',
        encoding="utf-8",
    )

    prediction_service_file = prediction_dir / "prediction_service.py"
    prediction_service_file.write_text(
        '''
class PredictionService:
    async def predict(self, symbol: str, interval: str):
        return {
            "symbol": symbol,
            "interval": interval,
            "regime": "trend_up",
        }
''',
        encoding="utf-8",
    )

    api_dir = root_path / "app" / "api"
    api_dir.mkdir(parents=True)

    schemas_file = api_dir / "schemas.py"
    schemas_file.write_text(
        '''
class PredictionCandleInput:
    pass


class PredictionRequest:
    pass


class PredictionResponse:
    prob_up: float
    prob_down: float
    prob_flat: float
    confidence: float
    model_version: str
''',
        encoding="utf-8",
    )

    tests_dir = root_path / "tests"
    tests_dir.mkdir(parents=True)

    (tests_dir / "test_predictor.py").write_text(
        '''
def test_predictor_returns_probabilities():
    assert "prob_up"
''',
        encoding="utf-8",
    )

    (tests_dir / "test_prediction_service.py").write_text(
        '''
def test_prediction_service_returns_prediction():
    assert "prediction"
''',
        encoding="utf-8",
    )

    (tests_dir / "test_api_predict.py").write_text(
        '''
def test_api_predict_response_contains_confidence():
    assert "confidence"
''',
        encoding="utf-8",
    )


def test_build_gate_policy_prediction_runtime_shape_summary_payload(
    tmp_path: Path,
) -> None:
    create_fake_runtime_shape_project(tmp_path)

    payload = build_gate_policy_prediction_runtime_shape_summary_payload(tmp_path)

    assert payload["root_path"] == str(tmp_path)
    assert payload["total_targets"] == 6
    assert payload["existing_targets"] == 6
    assert payload["missing_targets"] == 0
    assert payload["files_with_runtime_shape_signals"] == 6

    assert "PredictionRuntime" in payload["unique_class_names"]
    assert "Predictor" in payload["unique_class_names"]
    assert "PredictionService" in payload["unique_class_names"]
    assert "PredictionResponse" in payload["unique_class_names"]

    assert "predict" in payload["unique_function_names"]
    assert "prepare_runtime" in payload["unique_function_names"]

    assert "prob_up" in payload["unique_keywords"]
    assert "prob_down" in payload["unique_keywords"]
    assert "prob_flat" in payload["unique_keywords"]
    assert "confidence" in payload["unique_keywords"]
    assert "risk_score" in payload["unique_keywords"]
    assert "expected_move_atr" in payload["unique_keywords"]
    assert "tp_before_sl_probability" in payload["unique_keywords"]
    assert "model_version" in payload["unique_keywords"]
    assert "prediction" in payload["unique_keywords"]
    assert "regime" in payload["unique_keywords"]

    assert payload["keyword_counts"]["confidence"] >= 2
    assert payload["keyword_counts"]["model_version"] >= 2

    assert "files" not in payload
    assert "shown_files" not in payload
    assert "files_truncated" not in payload

    assert payload["integration_status"]["prediction_service_imported"] is False
    assert payload["integration_status"]["predictor_imported"] is False
    assert payload["integration_status"]["database_connected"] is False
    assert payload["integration_status"]["model_inference_connected"] is False
    assert payload["integration_status"]["traders_core_connected"] is False
    assert payload["integration_status"]["live_trading_connected"] is False


def test_gate_policy_prediction_runtime_shape_summary_cli_outputs_json(
    tmp_path: Path,
) -> None:
    create_fake_runtime_shape_project(tmp_path)

    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "gate-policy-prediction-runtime-shape-summary",
            "--root-path",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0

    payload = json.loads(result.stdout)

    assert payload["root_path"] == str(tmp_path)
    assert payload["total_targets"] == 6
    assert payload["existing_targets"] == 6
    assert payload["missing_targets"] == 0
    assert payload["files_with_runtime_shape_signals"] == 6

    assert "PredictionRuntime" in payload["unique_class_names"]
    assert "Predictor" in payload["unique_class_names"]
    assert "PredictionService" in payload["unique_class_names"]

    assert "predict" in payload["unique_function_names"]

    assert "prob_up" in payload["unique_keywords"]
    assert "confidence" in payload["unique_keywords"]
    assert "model_version" in payload["unique_keywords"]

    assert "files" not in payload

    assert payload["integration_status"]["prediction_service_imported"] is False
    assert payload["integration_status"]["predictor_imported"] is False
