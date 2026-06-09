from app.gates.gate_policy_adapter_diagnostics import (
    GatePolicyAdapterDiagnosticsService,
)
from app.gates.gate_policy_models import GateDirection, GatePolicyDecision


def test_gate_policy_adapter_diagnostics_evaluates_raw_payloads() -> None:
    service = GatePolicyAdapterDiagnosticsService()

    result = service.evaluate_payloads(
        (
            {
                "regime": "trend_up",
                "direction": "LONG",
                "confidence": 0.80,
                "tp_before_sl_probability": 0.70,
                "risk_score": 0.30,
                "sample_count": 80,
            },
            {
                "regime": "trend_down",
                "direction": "SHORT",
                "confidence": 0.78,
                "tp_before_sl_probability": 0.68,
                "risk_score": 0.28,
                "sample_count": 75,
            },
            {
                "regime": "range",
                "direction": "LONG",
                "confidence": 0.85,
                "tp_before_sl_probability": 0.75,
                "risk_score": 0.25,
                "sample_count": 90,
            },
        )
    )

    assert len(result.inputs) == 3
    assert len(result.results) == 3

    assert result.inputs[0].direction == GateDirection.LONG
    assert result.inputs[1].direction == GateDirection.SHORT
    assert result.inputs[2].regime == "range"

    assert result.results[0].decision == GatePolicyDecision.ALLOW_LONG
    assert result.results[1].decision == GatePolicyDecision.ALLOW_SHORT
    assert result.results[2].decision == GatePolicyDecision.BAD_REGIME

    assert result.report.total == 3
    assert result.report.allowed_total == 2
    assert result.report.blocked_total == 1


def test_gate_policy_adapter_diagnostics_supports_alias_payloads() -> None:
    service = GatePolicyAdapterDiagnosticsService()

    result = service.evaluate_payloads(
        (
            {
                "market_regime": "trend_up",
                "predicted_direction": "UP",
                "model_confidence": "0.81",
                "tp_before_sl_prob": "0.66",
                "model_risk_score": "0.20",
                "samples": "100",
            },
            {
                "market_regime": "trend_down",
                "predicted_direction": "DOWN",
                "model_confidence": "0.79",
                "tp_before_sl_prob": "0.63",
                "model_risk_score": "0.22",
                "samples": "100",
            },
        )
    )

    assert result.report.total == 2
    assert result.report.allowed_total == 2
    assert result.report.blocked_total == 0

    assert result.report.decision_counts["ALLOW_LONG"] == 1
    assert result.report.decision_counts["ALLOW_SHORT"] == 1

    assert result.inputs[0].direction == GateDirection.LONG
    assert result.inputs[1].direction == GateDirection.SHORT


def test_gate_policy_adapter_diagnostics_blocks_bad_or_incomplete_payloads() -> None:
    service = GatePolicyAdapterDiagnosticsService()

    result = service.evaluate_payloads(
        (
            {
                "regime": "unknown",
                "direction": "LONG",
                "confidence": 0.90,
                "tp_before_sl_probability": 0.80,
            },
            {
                "regime": "trend_up",
                "direction": "LONG",
                "confidence": 0.30,
                "tp_before_sl_probability": 0.80,
            },
            {},
        )
    )

    assert result.report.total == 3
    assert result.report.allowed_total == 0
    assert result.report.blocked_total == 3

    assert result.report.decision_counts["BAD_REGIME"] == 1
    assert result.report.decision_counts["LOW_CONFIDENCE"] == 1
    assert result.report.decision_counts["BLOCK"] == 1

    assert result.report.reason_counts["regime_is_not_trusted"] == 1
    assert result.report.reason_counts["confidence_below_threshold"] == 1
    assert result.report.reason_counts["direction_is_not_tradeable"] == 1


def test_gate_policy_adapter_diagnostics_handles_empty_payloads() -> None:
    service = GatePolicyAdapterDiagnosticsService()

    result = service.evaluate_payloads(())

    assert result.inputs == ()
    assert result.results == ()
    assert result.report.total == 0
    assert result.report.allowed_total == 0
    assert result.report.blocked_total == 0
    assert result.report.decision_counts == {}
    assert result.report.reason_counts == {}
