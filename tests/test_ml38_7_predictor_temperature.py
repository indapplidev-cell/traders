from types import SimpleNamespace

import torch

from app.prediction.predictor import PredictionRuntime
from app.prediction.predictor import Predictor


def test_predictor_uses_runtime_direction_temperature() -> None:
    predictor = Predictor(
        model_registry_repository=object(),
        prediction_repository=FakePredictionRepository(),
        artifact_storage=object(),
        model_loader=object(),
    )
    runtime = PredictionRuntime(
        model_row=SimpleNamespace(model_version="mv1"),
        model=FakeModel(),
        scaler={"mean": [0.0], "std": [1.0]},
        feature_columns=["x"],
        direction_temperature=0.5,
    )
    feature_record = SimpleNamespace(
        candle_open_time=None,
        features_json={"x": 1.0},
    )

    response = predictor._predict_feature_record(
        symbol="BTCUSDT",
        interval="15m",
        horizon_candles=8,
        feature_record=feature_record,
        runtime=runtime,
    )

    assert response["direction_temperature"] == 0.5
    assert response["probability_source"] == "temperature_scaled"
    assert response["confidence"] > 0.34


def test_logged_prediction_payload_keeps_temperature_metadata_inside_response_payload_only() -> None:
    prediction_repository = FakePredictionRepository()
    predictor = Predictor(
        model_registry_repository=object(),
        prediction_repository=prediction_repository,
        artifact_storage=object(),
        model_loader=object(),
    )
    runtime = PredictionRuntime(
        model_row=SimpleNamespace(model_version="mv1"),
        model=FakeModel(),
        scaler={"mean": [0.0], "std": [1.0]},
        feature_columns=["x"],
        direction_temperature=0.5,
    )
    feature_record = SimpleNamespace(
        candle_open_time=None,
        features_json={"x": 1.0},
    )

    response = predictor.predict_from_feature_record(
        symbol="BTCUSDT",
        interval="15m",
        horizon_candles=8,
        feature_record=feature_record,
        runtime=runtime,
        log_prediction=True,
    )

    assert response["direction_temperature"] == 0.5
    assert response["probability_source"] == "temperature_scaled"

    assert prediction_repository.created_payloads
    payload = prediction_repository.created_payloads[0]

    assert "direction_temperature" not in payload
    assert "probability_source" not in payload
    assert payload["response_payload"]["direction_temperature"] == 0.5
    assert payload["response_payload"]["probability_source"] == "temperature_scaled"


class FakeModel(torch.nn.Module):
    def eval(self):
        return self

    def forward(self, features):
        return {
            "direction_logits": torch.tensor([[0.20, 0.18, 0.17]], dtype=torch.float32),
            "tp_sl_logits": torch.tensor([0.0], dtype=torch.float32),
            "expected_move_atr": torch.tensor([1.0], dtype=torch.float32),
            "risk_score": torch.tensor([0.5], dtype=torch.float32),
        }


class FakePredictionRepository:
    def __init__(self) -> None:
        self.created_payloads = []

    def create(self, payload):
        self.created_payloads.append(payload)
        return payload
