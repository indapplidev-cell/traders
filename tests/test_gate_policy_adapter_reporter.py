import json
from decimal import Decimal

from app.gates.gate_policy_adapter_diagnostics import (
    GatePolicyAdapterDiagnosticsService,
)
from app.gates.gate_policy_adapter_reporter import GatePolicyAdapterReporter
from app.gates.gate_policy_models import GatePolicyInput


def test_gate_policy_adapter_reporter_converts_input_to_dict() -> None:
    reporter = GatePolicyAdapterReporter()

    payload = reporter.input_to_dict(
        GatePolicyInput(
            regime="trend_up",
            direction="LONG",
            confidence=0.80,
            tp_before_sl_probability=0.70,
            risk_score=0.20,
            expected_move_atr=1.5,
            model_total_r=10.0,
            baseline_total_r=5.0,
            model_profit_factor=1.30,
            baseline_profit_factor=1.05,
            sample_count=100,
            metadata={"source": "unit_test"},
        )
    )

    assert payload["regime"] == "trend_up"
    assert payload["direction"] == "LONG"
    assert payload["confidence"] == 0.80
    assert payload["tp_before_sl_probability"] == 0.70
    assert payload["risk_score"] == 0.20
    assert payload["expected_move_atr"] == 1.5
    assert payload["model_total_r"] == 10.0
    assert payload["baseline_total_r"] == 5.0
    assert payload["model_profit_factor"] == 1.30
    assert payload["baseline_profit_factor"] == 1.05
    assert payload["sample_count"] == 100
    assert payload["metadata"]["source"] == "unit_test"


def test_gate_policy_adapter_reporter_converts_adapter_result_to_dict() -> None:
    diagnostics = GatePolicyAdapterDiagnosticsService()
    reporter = GatePolicyAdapterReporter()

    result = diagnostics.evaluate_payloads(
        (
            {
                "regime": "trend_up",
                "direction": "LONG",
                "confidence": 0.80,
                "tp_before_sl_probability": 0.70,
            },
            {
                "regime": "range",
                "direction": "LONG",
                "confidence": 0.90,
                "tp_before_sl_probability": 0.80,
            },
        )
    )

    payload = reporter.adapter_result_to_dict(result)

    assert payload["input_count"] == 2
    assert payload["result_count"] == 2

    assert payload["report"]["total"] == 2
    assert payload["report"]["allowed_total"] == 1
    assert payload["report"]["blocked_total"] == 1

    assert payload["inputs"][0]["regime"] == "trend_up"
    assert payload["inputs"][1]["regime"] == "range"

    assert payload["results"][0]["decision"] == "ALLOW_LONG"
    assert payload["results"][1]["decision"] == "BAD_REGIME"

    assert payload["decision_sequence"] == ["ALLOW_LONG", "BAD_REGIME"]
    assert payload["allowed_sequence"] == [True, False]


def test_gate_policy_adapter_reporter_converts_adapter_result_to_json() -> None:
    diagnostics = GatePolicyAdapterDiagnosticsService()
    reporter = GatePolicyAdapterReporter()

    result = diagnostics.evaluate_payloads(
        (
            {
                "market_regime": "trend_down",
                "predicted_direction": "DOWN",
                "model_confidence": "0.81",
                "tp_before_sl_prob": "0.66",
            },
        )
    )

    json_payload = reporter.adapter_result_to_json(result)
    payload = json.loads(json_payload)

    assert payload["input_count"] == 1
    assert payload["result_count"] == 1
    assert payload["report"]["total"] == 1
    assert payload["report"]["allowed_total"] == 1
    assert payload["decision_sequence"] == ["ALLOW_SHORT"]
    assert payload["inputs"][0]["direction"] == "SHORT"


def test_gate_policy_adapter_reporter_supports_compact_json() -> None:
    diagnostics = GatePolicyAdapterDiagnosticsService()
    reporter = GatePolicyAdapterReporter()

    result = diagnostics.evaluate_payloads(())

    json_payload = reporter.adapter_result_to_json(result, indent=None)

    assert "\n" not in json_payload

    payload = json.loads(json_payload)

    assert payload["input_count"] == 0
    assert payload["result_count"] == 0
    assert payload["report"]["total"] == 0
    assert payload["decision_sequence"] == []


def test_gate_policy_adapter_reporter_makes_metadata_json_safe() -> None:
    reporter = GatePolicyAdapterReporter()

    payload = reporter.input_to_dict(
        GatePolicyInput(
            regime="trend_up",
            direction="LONG",
            confidence=0.80,
            tp_before_sl_probability=0.70,
            metadata={
                "decimal_value": Decimal("1.23"),
                "nested": {
                    "items": (Decimal("2.34"), "ok"),
                },
            },
        )
    )

    assert payload["metadata"]["decimal_value"] == "1.23"
    assert payload["metadata"]["nested"]["items"] == ["2.34", "ok"]

    json.dumps(payload, ensure_ascii=False)
