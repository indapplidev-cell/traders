from fastapi.testclient import TestClient

from app.api import routes_models, routes_predict, routes_replay
from app.api.main import app


def test_predict_endpoint_adds_gate_policy_block_and_preserves_prediction_fields(monkeypatch) -> None:
    monkeypatch.setattr(
        routes_predict,
        "get_prediction_service",
        lambda session: FakePredictionService(),
    )
    monkeypatch.setattr(
        routes_models,
        "get_model_registry",
        lambda session: FakeModelRegistry(),
    )
    monkeypatch.setattr(
        routes_replay,
        "get_replay_service",
        lambda session: FakeReplayService(),
    )
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
            "context": {"market_regime": "trend_up"},
        },
    )

    payload = response.json()

    assert response.status_code == 200
    assert payload["ml_available"] is True
    assert payload["prob_up"] == 0.61
    assert payload["prob_down"] == 0.21
    assert payload["prob_flat"] == 0.18
    assert payload["confidence"] == 0.72
    assert payload["risk_score"] == 0.31
    assert payload["tp_before_sl_probability"] == 0.64
    assert payload["expected_move_atr"] == 1.45
    assert payload["model_version"] == "model_v1"

    gate_policy = payload["gate_policy"]
    assert gate_policy["enabled"] is True
    assert gate_policy["source"] == "ml21_runtime_binding"
    assert gate_policy["is_valid"] is True
    assert gate_policy["direction"] == "LONG"
    assert gate_policy["gate_policy_payload"]["direction"] == "LONG"
    assert gate_policy["integration_status"]["prediction_service_bound"] is True
    assert gate_policy["integration_status"]["orders_enabled"] is False
    assert gate_policy["integration_status"]["traders_core_connected"] is False
    assert gate_policy["integration_status"]["live_trading_connected"] is False


def test_predict_endpoint_returns_safe_invalid_gate_policy_block(monkeypatch) -> None:
    monkeypatch.setattr(
        routes_predict,
        "get_prediction_service",
        lambda session: FallbackPredictionService(),
    )
    monkeypatch.setattr(
        routes_models,
        "get_model_registry",
        lambda session: FakeModelRegistry(),
    )
    monkeypatch.setattr(
        routes_replay,
        "get_replay_service",
        lambda session: FakeReplayService(),
    )
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
            "context": {"market_regime": "trend_up"},
        },
    )

    payload = response.json()
    gate_policy = payload["gate_policy"]

    assert response.status_code == 200
    assert payload["ml_available"] is False
    assert payload["reason"] == "not_enough_candles"
    assert gate_policy["enabled"] is True
    assert gate_policy["is_valid"] is False
    assert gate_policy["direction"] == "NONE"
    assert gate_policy["issues"]
    assert gate_policy["integration_status"]["orders_enabled"] is False
    assert gate_policy["integration_status"]["traders_core_connected"] is False
    assert gate_policy["integration_status"]["live_trading_connected"] is False


class FakePredictionService:
    def predict(self, payload):
        return {
            "ml_available": True,
            "symbol": payload["symbol"],
            "interval": payload["interval"],
            "horizon_candles": payload["horizon_candles"],
            "direction": "UP",
            "prob_up": 0.61,
            "prob_down": 0.21,
            "prob_flat": 0.18,
            "tp_before_sl_probability": 0.64,
            "expected_move_atr": 1.45,
            "risk_score": 0.31,
            "confidence": 0.72,
            "model_version": "model_v1",
        }


class FallbackPredictionService:
    def predict(self, payload):
        return {
            "ml_available": False,
            "reason": "not_enough_candles",
        }


class FakeModelRegistry:
    def list_models(self):
        return []

    def activate(self, model_version: str):
        return {"model_version": model_version, "activated": True, "warning": None}


class FakeReplayService:
    def list_sessions(self):
        return []
