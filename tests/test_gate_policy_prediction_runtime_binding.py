import json

from app.gates.gate_policy_prediction_runtime_binding import (
    PredictionServiceGatePolicyRuntimeBinding,
    bind_prediction_payload_to_gate_policy,
)


SAMPLE_PAYLOAD = {
    "prob_up": 0.61,
    "prob_down": 0.21,
    "prob_flat": 0.18,
    "confidence": 0.72,
    "tp_before_sl_probability": 0.64,
    "risk_score": 0.31,
    "expected_move_atr": 1.45,
    "regime": "trend_up",
    "model_version": "sample_model_v1",
    "symbol": "BTCUSDT",
    "interval": "15m",
}


def test_binding_accepts_valid_payload_and_builds_gate_policy_decision() -> None:
    result = bind_prediction_payload_to_gate_policy(SAMPLE_PAYLOAD)
    payload = result.to_dict()

    assert payload["is_valid"] is True
    assert payload["direction"] == "LONG"
    assert payload["gate_policy_payload"]["direction"] == "LONG"
    assert payload["gate_policy_decision"]["decision"] == "ALLOW_LONG"
    assert payload["gate_policy_decision"]["allowed"] is True


def test_binding_marks_invalid_payload_as_safe_reject() -> None:
    result = bind_prediction_payload_to_gate_policy(
        {
            "prob_up": 0.61,
            "prob_down": "bad",
            "prob_flat": 0.18,
            "confidence": 0.72,
            "tp_before_sl_probability": 0.64,
            "regime": "trend_up",
        }
    )
    payload = result.to_dict()

    assert payload["is_valid"] is False
    assert payload["direction"] == "NONE"
    assert payload["gate_policy_payload"] is None
    assert payload["gate_policy_decision"]["allowed"] is False
    assert payload["gate_policy_decision"]["decision"] == "BLOCK"


def test_binding_turns_tied_probabilities_into_none_direction() -> None:
    result = bind_prediction_payload_to_gate_policy(
        {
            **SAMPLE_PAYLOAD,
            "prob_up": 0.40,
            "prob_down": 0.40,
            "prob_flat": 0.20,
        }
    )
    payload = result.to_dict()

    assert payload["is_valid"] is True
    assert payload["direction"] == "NONE"
    assert payload["gate_policy_payload"]["direction"] == "NONE"
    assert payload["gate_policy_decision"]["allowed"] is False
    assert payload["gate_policy_decision"]["decision"] == "BLOCK"


def test_binding_preserves_metadata_and_safe_integration_status() -> None:
    result = bind_prediction_payload_to_gate_policy(SAMPLE_PAYLOAD)
    payload = result.to_dict()

    assert payload["prediction_payload"]["model_version"] == "sample_model_v1"
    assert payload["prediction_payload"]["symbol"] == "BTCUSDT"
    assert payload["prediction_payload"]["interval"] == "15m"

    assert payload["integration_status"] == {
        "prediction_service_bound": False,
        "runtime_adapter_used": True,
        "gate_policy_service_used": True,
        "database_connected": False,
        "traders_core_connected": False,
        "live_trading_connected": False,
        "orders_enabled": False,
    }

    json.dumps(payload, ensure_ascii=False)


def test_binding_supports_prediction_service_request_mode_without_real_inference() -> None:
    binding = PredictionServiceGatePolicyRuntimeBinding(
        prediction_service=FakePredictionService()
    )

    result = binding.bind_from_service_request(
        {
            "symbol": "BTCUSDT",
            "interval": "15m",
            "horizon_candles": 8,
            "candles": [],
            "context": {"market_regime": "trend_up"},
        }
    )
    payload = result.to_dict()

    assert payload["is_valid"] is True
    assert payload["direction"] == "LONG"
    assert payload["prediction_payload"]["regime"] == "trend_up"
    assert payload["integration_status"]["prediction_service_bound"] is True
    assert payload["gate_policy_decision"]["decision"] == "ALLOW_LONG"


class FakePredictionService:
    def predict(self, payload):
        return {
            "ml_available": True,
            "symbol": payload["symbol"],
            "interval": payload["interval"],
            "direction": "UP",
            "prob_up": 0.68,
            "prob_down": 0.15,
            "prob_flat": 0.17,
            "tp_before_sl_probability": 0.67,
            "expected_move_atr": 1.23,
            "risk_score": 0.22,
            "confidence": 0.68,
            "model_version": "service_model_v1",
        }
