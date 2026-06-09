from app.gates.gate_policy_adapter import (
    GatePolicyAdapterConfig,
    GatePolicyEvaluationAdapter,
)
from app.gates.gate_policy_models import GateDirection


def test_gate_policy_adapter_builds_input_from_primary_keys() -> None:
    adapter = GatePolicyEvaluationAdapter()

    gate_input = adapter.from_mapping(
        {
            "regime": "trend_up",
            "direction": "LONG",
            "confidence": 0.81,
            "tp_before_sl_probability": 0.64,
            "risk_score": 0.22,
            "expected_move_atr": 1.4,
            "model_total_r": 10.5,
            "baseline_total_r": 4.0,
            "model_profit_factor": 1.34,
            "baseline_profit_factor": 1.02,
            "sample_count": 120,
        }
    )

    assert gate_input.regime == "trend_up"
    assert gate_input.direction == GateDirection.LONG
    assert gate_input.confidence == 0.81
    assert gate_input.tp_before_sl_probability == 0.64
    assert gate_input.risk_score == 0.22
    assert gate_input.expected_move_atr == 1.4
    assert gate_input.model_total_r == 10.5
    assert gate_input.baseline_total_r == 4.0
    assert gate_input.model_profit_factor == 1.34
    assert gate_input.baseline_profit_factor == 1.02
    assert gate_input.sample_count == 120
    assert gate_input.metadata["regime"] == "trend_up"


def test_gate_policy_adapter_supports_alias_keys() -> None:
    adapter = GatePolicyEvaluationAdapter()

    gate_input = adapter.from_mapping(
        {
            "market_regime": "trend_down",
            "predicted_direction": "DOWN",
            "model_confidence": "0.77",
            "tp_before_sl_prob": "0.61",
            "model_risk_score": "0.33",
            "expected_atr_move": "1.8",
            "ml_total_r": "9.0",
            "baseline_r": "5.0",
            "ml_profit_factor": "1.21",
            "baseline_profit_factor": "1.03",
            "samples": "88",
        }
    )

    assert gate_input.regime == "trend_down"
    assert gate_input.direction == GateDirection.SHORT
    assert gate_input.confidence == 0.77
    assert gate_input.tp_before_sl_probability == 0.61
    assert gate_input.risk_score == 0.33
    assert gate_input.expected_move_atr == 1.8
    assert gate_input.model_total_r == 9.0
    assert gate_input.baseline_total_r == 5.0
    assert gate_input.model_profit_factor == 1.21
    assert gate_input.baseline_profit_factor == 1.03
    assert gate_input.sample_count == 88


def test_gate_policy_adapter_uses_safe_defaults_for_missing_values() -> None:
    adapter = GatePolicyEvaluationAdapter()

    gate_input = adapter.from_mapping({})

    assert gate_input.regime == "unknown"
    assert gate_input.direction == GateDirection.NONE
    assert gate_input.confidence == 0.0
    assert gate_input.tp_before_sl_probability == 0.0
    assert gate_input.risk_score is None
    assert gate_input.expected_move_atr is None
    assert gate_input.model_total_r is None
    assert gate_input.baseline_total_r is None
    assert gate_input.model_profit_factor is None
    assert gate_input.baseline_profit_factor is None
    assert gate_input.sample_count is None
    assert gate_input.metadata == {}


def test_gate_policy_adapter_uses_custom_defaults() -> None:
    adapter = GatePolicyEvaluationAdapter(
        GatePolicyAdapterConfig(
            default_regime="range",
            default_direction=GateDirection.FLAT,
            default_confidence=0.10,
            default_tp_before_sl_probability=0.20,
        )
    )

    gate_input = adapter.from_mapping({})

    assert gate_input.regime == "range"
    assert gate_input.direction == GateDirection.FLAT
    assert gate_input.confidence == 0.10
    assert gate_input.tp_before_sl_probability == 0.20


def test_gate_policy_adapter_handles_invalid_numeric_values_safely() -> None:
    adapter = GatePolicyEvaluationAdapter()

    gate_input = adapter.from_mapping(
        {
            "regime": "trend_up",
            "direction": "LONG",
            "confidence": "bad",
            "tp_before_sl_probability": "bad",
            "risk_score": "bad",
            "expected_move_atr": "bad",
            "sample_count": "bad",
        }
    )

    assert gate_input.regime == "trend_up"
    assert gate_input.direction == GateDirection.LONG
    assert gate_input.confidence == 0.0
    assert gate_input.tp_before_sl_probability == 0.0
    assert gate_input.risk_score is None
    assert gate_input.expected_move_atr is None
    assert gate_input.sample_count is None


def test_gate_policy_adapter_builds_many_inputs() -> None:
    adapter = GatePolicyEvaluationAdapter()

    inputs = adapter.from_mappings(
        [
            {
                "regime": "trend_up",
                "direction": "BUY",
                "confidence": 0.80,
                "tp_before_sl_probability": 0.70,
            },
            {
                "regime": "trend_down",
                "direction": "SELL",
                "confidence": 0.75,
                "tp_before_sl_probability": 0.65,
            },
        ]
    )

    assert len(inputs) == 2
    assert inputs[0].direction == GateDirection.LONG
    assert inputs[1].direction == GateDirection.SHORT
