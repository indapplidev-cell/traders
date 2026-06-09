from fastapi.testclient import TestClient

from app.api.main import app
from app.api import routes_models, routes_predict, routes_replay


def test_predict_endpoint_returns_fallback_contract(monkeypatch) -> None:
    monkeypatch.setattr(routes_predict, "get_prediction_service", lambda session: FakePredictionService())
    monkeypatch.setattr(routes_models, "get_model_registry", lambda session: FakeModelRegistry())
    monkeypatch.setattr(routes_replay, "get_replay_service", lambda session: FakeReplayService())
    client = TestClient(app)

    response = client.post(
        "/predict",
        json={
            "symbol": "BTCUSDT",
            "interval": "15m",
            "horizon_candles": 8,
            "candles": [
                {
                    "open_time": "2026-06-08T10:00:00Z",
                    "open": "70000.0",
                    "high": "70100.0",
                    "low": "69850.0",
                    "close": "70050.0",
                    "volume": "123.45",
                }
            ],
            "context": {"market_regime": "TREND_UP"},
        },
    )

    assert response.status_code == 200
    assert response.json() == {"ml_available": False, "reason": "not_enough_candles", "symbol": None, "interval": None, "horizon_candles": None, "direction": None, "prob_up": None, "prob_down": None, "prob_flat": None, "tp_before_sl_probability": None, "expected_move_atr": None, "risk_score": None, "confidence": None, "model_version": None}


def test_models_and_replay_endpoints(monkeypatch) -> None:
    monkeypatch.setattr(routes_predict, "get_prediction_service", lambda session: FakePredictionService())
    monkeypatch.setattr(routes_models, "get_model_registry", lambda session: FakeModelRegistry())
    monkeypatch.setattr(routes_replay, "get_replay_service", lambda session: FakeReplayService())
    client = TestClient(app)

    models_response = client.get("/models")
    activate_response = client.post("/models/activate", json={"model_version": "mv1"})
    replay_response = client.get("/replay/sessions")

    assert models_response.status_code == 200
    assert activate_response.status_code == 200
    assert replay_response.status_code == 200


class FakePredictionService:
    def predict(self, payload):
        return {"ml_available": False, "reason": "not_enough_candles"}


class FakeModelRegistry:
    def list_models(self):
        return [
            {
                "model_version": "mv1",
                "model_name": "candle_mlp",
                "symbol": "BTCUSDT",
                "interval": "15m",
                "horizon_candles": 8,
                "feature_version": "fv1",
                "label_version": "lv1",
                "accuracy": 0.4,
                "brier_score": 0.6,
                "is_active": True,
                "artifact_path": "artifacts/models/mv1",
                "created_at": None,
            }
        ]

    def activate(self, model_version: str):
        return {"model_version": model_version, "activated": True, "warning": None}


class FakeReplayService:
    def list_sessions(self):
        return [
            {
                "session_id": "s1",
                "model_version": "mv1",
                "symbol": "BTCUSDT",
                "interval": "15m",
                "start_at": "2025-01-01T00:00:00+00:00",
                "end_at": "2025-01-02T00:00:00+00:00",
                "status": "completed",
                "metrics_json": {"accuracy": 0.5},
                "created_at": None,
            }
        ]
