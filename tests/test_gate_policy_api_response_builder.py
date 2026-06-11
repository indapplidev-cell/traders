from app.api.gate_policy_response_builder import (
    build_gate_policy_api_block_from_prediction_payload,
    build_safe_gate_policy_api_block_from_error,
)


def test_builder_returns_valid_gate_policy_block_for_valid_prediction_payload() -> None:
    payload = build_gate_policy_api_block_from_prediction_payload(
        {
            "ml_available": True,
            "symbol": "BTCUSDT",
            "interval": "15m",
            "direction": "UP",
            "prob_up": 0.61,
            "prob_down": 0.21,
            "prob_flat": 0.18,
            "confidence": 0.72,
            "tp_before_sl_probability": 0.64,
            "risk_score": 0.31,
            "expected_move_atr": 1.45,
            "model_version": "model_v1",
        },
        request_payload={
            "symbol": "BTCUSDT",
            "interval": "15m",
            "horizon_candles": 8,
            "candles": [],
            "context": {"market_regime": "trend_up"},
        },
    )

    assert payload["enabled"] is True
    assert payload["source"] == "ml21_runtime_binding"
    assert payload["is_valid"] is True
    assert payload["direction"] == "LONG"
    assert payload["gate_policy_payload"] is not None
    assert sorted(payload["gate_policy_payload"].keys()) == [
        "confidence",
        "direction",
        "expected_move_atr",
        "interval",
        "model_version",
        "regime",
        "risk_score",
        "symbol",
        "tp_before_sl_probability",
    ]
    assert payload["integration_status"]["orders_enabled"] is False
    assert payload["integration_status"]["traders_core_connected"] is False
    assert payload["integration_status"]["live_trading_connected"] is False


def test_builder_returns_invalid_gate_policy_block_for_invalid_prediction_payload() -> None:
    payload = build_gate_policy_api_block_from_prediction_payload(
        {
            "ml_available": False,
            "reason": "not_enough_candles",
        },
        request_payload={
            "symbol": "BTCUSDT",
            "interval": "15m",
            "horizon_candles": 8,
            "candles": [],
            "context": {"market_regime": "trend_up"},
        },
    )

    assert payload["enabled"] is True
    assert payload["is_valid"] is False
    assert payload["direction"] == "NONE"
    assert payload["issues"]
    assert payload["integration_status"]["orders_enabled"] is False
    assert payload["integration_status"]["traders_core_connected"] is False
    assert payload["integration_status"]["live_trading_connected"] is False


def test_builder_returns_safe_error_block() -> None:
    payload = build_safe_gate_policy_api_block_from_error(
        RuntimeError("binding exploded")
    )

    assert payload["enabled"] is True
    assert payload["is_valid"] is False
    assert payload["direction"] == "NONE"
    assert payload["gate_policy_payload"] is None
    assert payload["gate_policy_decision"] is None
    assert payload["issues"][0]["code"] == "gate_policy_binding_error"
    assert payload["integration_status"]["gate_policy_service_used"] is False
    assert payload["integration_status"]["orders_enabled"] is False
