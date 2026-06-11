import json

from app.evaluation.gate_policy_replay_evaluator import (
    GatePolicyReplayEvaluator,
)


def test_gate_policy_replay_evaluator_counts_records_and_directions() -> None:
    evaluator = GatePolicyReplayEvaluator()

    summary = evaluator.evaluate(_sample_payloads())
    payload = summary.to_dict()

    assert payload["total_records"] == 5
    assert payload["valid_records"] == 4
    assert payload["invalid_records"] == 1
    assert payload["direction_counts"] == {
        "LONG": 1,
        "SHORT": 1,
        "FLAT": 1,
        "NONE": 2,
    }
    assert payload["gate_policy_allowed_count"] == 2
    assert payload["gate_policy_blocked_count"] == 3
    assert payload["gate_policy_none_count"] == 2
    assert payload["integration_status"] == {
        "runtime_binding_used": True,
        "gate_policy_used": True,
        "prediction_service_required": False,
        "database_connected": False,
        "database_writes": False,
        "traders_core_connected": False,
        "live_trading_connected": False,
        "orders_enabled": False,
    }


def test_gate_policy_replay_evaluator_records_and_issue_counts_are_safe() -> None:
    evaluator = GatePolicyReplayEvaluator()

    summary = evaluator.evaluate(_sample_payloads())
    payload = summary.to_dict()

    assert payload["records"][0]["direction"] == "LONG"
    assert payload["records"][1]["direction"] == "SHORT"
    assert payload["records"][2]["direction"] == "FLAT"
    assert payload["records"][3]["direction"] == "NONE"
    assert payload["records"][4]["is_valid"] is False
    assert payload["records"][4]["issue_count"] > 0
    assert payload["records"][4]["gate_policy_decision"]["allowed"] is False
    assert payload["records"][3]["gate_policy_decision"]["allowed"] is False
    assert payload["issue_counts"]["missing_required_numeric_field"] >= 1
    assert "missing_required_numeric_field" in payload["top_issue_codes"]

    json.dumps(payload, ensure_ascii=False)


def _sample_payloads() -> list[dict[str, object]]:
    return [
        {
            "timestamp": "2026-06-11T12:00:00Z",
            "symbol": "BTCUSDT",
            "interval": "15m",
            "model_version": "sample_model_v1",
            "prob_up": 0.61,
            "prob_down": 0.21,
            "prob_flat": 0.18,
            "confidence": 0.72,
            "tp_before_sl_probability": 0.64,
            "risk_score": 0.31,
            "expected_move_atr": 1.45,
            "regime": "trend_up",
        },
        {
            "timestamp": "2026-06-11T12:15:00Z",
            "symbol": "BTCUSDT",
            "interval": "15m",
            "model_version": "sample_model_v1",
            "prob_up": 0.15,
            "prob_down": 0.67,
            "prob_flat": 0.18,
            "confidence": 0.67,
            "tp_before_sl_probability": 0.63,
            "risk_score": 0.25,
            "expected_move_atr": 1.20,
            "regime": "trend_down",
        },
        {
            "timestamp": "2026-06-11T12:30:00Z",
            "symbol": "BTCUSDT",
            "interval": "15m",
            "model_version": "sample_model_v1",
            "prob_up": 0.20,
            "prob_down": 0.18,
            "prob_flat": 0.62,
            "confidence": 0.62,
            "tp_before_sl_probability": 0.59,
            "risk_score": 0.20,
            "expected_move_atr": 0.60,
            "regime": "trend_up",
        },
        {
            "timestamp": "2026-06-11T12:45:00Z",
            "symbol": "BTCUSDT",
            "interval": "15m",
            "model_version": "sample_model_v1",
            "prob_up": 0.40,
            "prob_down": 0.40,
            "prob_flat": 0.20,
            "confidence": 0.40,
            "tp_before_sl_probability": 0.50,
            "risk_score": 0.40,
            "expected_move_atr": 0.80,
            "regime": "trend_up",
        },
        {
            "timestamp": "2026-06-11T13:00:00Z",
            "symbol": "BTCUSDT",
            "interval": "15m",
            "model_version": "sample_model_v1",
            "prob_up": 0.55,
            "prob_flat": 0.45,
            "confidence": 0.55,
            "tp_before_sl_probability": 0.58,
            "regime": "trend_up",
        },
    ]
