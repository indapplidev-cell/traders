import json

from app.gates.gate_policy_prediction_runtime_binding import (
    bind_prediction_payload_to_gate_policy,
)
from app.gates.gate_policy_prediction_runtime_binding_reporter import (
    GatePolicyPredictionRuntimeBindingReporter,
)


def test_runtime_binding_reporter_summary_contains_capabilities() -> None:
    reporter = GatePolicyPredictionRuntimeBindingReporter()

    payload = reporter.summary_to_dict()

    assert payload["binding_name"] == "gate_policy_prediction_runtime_binding"
    assert payload["binding_version"] == "ml21.1"
    assert payload["uses_prediction_service"] is True
    assert payload["uses_runtime_adapter"] is True
    assert payload["uses_gate_policy_service"] is True
    assert payload["supports_payload_mode"] is True
    assert payload["supports_service_result_mode"] is True
    assert payload["database_connected"] is False
    assert payload["traders_core_connected"] is False
    assert payload["live_trading_connected"] is False
    assert payload["orders_enabled"] is False


def test_runtime_binding_reporter_serializes_result_and_json() -> None:
    reporter = GatePolicyPredictionRuntimeBindingReporter()
    result = bind_prediction_payload_to_gate_policy(
        {
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
    )

    payload = reporter.result_to_dict(result)
    full_report = reporter.full_report_to_dict(result)

    assert payload["binding_name"] == "gate_policy_prediction_runtime_binding"
    assert payload["binding_version"] == "ml21.1"
    assert payload["gate_policy_decision"]["decision"] == "ALLOW_LONG"
    assert full_report["summary"]["supports_service_result_mode"] is True
    assert full_report["result"]["direction"] == "LONG"

    json.loads(reporter.summary_to_json())
    json.loads(reporter.full_report_to_json(result))
    json.loads(reporter.result_to_json(result))
