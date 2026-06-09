import json

from app.gates.gate_policy_diagnostics import GatePolicyDiagnosticsService
from app.gates.gate_policy_models import (
    GatePolicyInput,
)
from app.gates.gate_policy_reporter import GatePolicyReporter
from app.gates.gate_policy_service import GatePolicyService


def test_gate_policy_reporter_converts_result_to_dict() -> None:
    service = GatePolicyService()
    reporter = GatePolicyReporter()

    result = service.evaluate(
        GatePolicyInput(
            regime="trend_up",
            direction="LONG",
            confidence=0.80,
            tp_before_sl_probability=0.70,
            risk_score=0.30,
            sample_count=50,
        )
    )

    payload = reporter.result_to_dict(result)

    assert payload["decision"] == "ALLOW_LONG"
    assert payload["allowed"] is True
    assert payload["regime"] == "trend_up"
    assert payload["direction"] == "LONG"
    assert payload["reasons"] == ["signal_passed_gate_policy"]
    assert payload["thresholds"]["min_confidence"] == 0.60
    assert payload["thresholds"]["min_tp_before_sl_probability"] == 0.55


def test_gate_policy_reporter_converts_diagnostics_report_to_dict() -> None:
    diagnostics = GatePolicyDiagnosticsService()
    reporter = GatePolicyReporter()

    report = diagnostics.build_report(
        (
            GatePolicyInput(
                regime="trend_up",
                direction="LONG",
                confidence=0.80,
                tp_before_sl_probability=0.70,
            ),
            GatePolicyInput(
                regime="range",
                direction="LONG",
                confidence=0.80,
                tp_before_sl_probability=0.70,
            ),
            GatePolicyInput(
                regime="trend_down",
                direction="SHORT",
                confidence=0.80,
                tp_before_sl_probability=0.70,
            ),
        )
    )

    payload = reporter.report_to_dict(report)

    assert payload["total"] == 3
    assert payload["allowed_total"] == 2
    assert payload["blocked_total"] == 1
    assert payload["decision_counts"]["ALLOW_LONG"] == 1
    assert payload["decision_counts"]["ALLOW_SHORT"] == 1
    assert payload["decision_counts"]["BAD_REGIME"] == 1
    assert payload["regime_counts"]["range"] == 1
    assert payload["direction_counts"]["LONG"] == 2
    assert payload["reason_counts"]["regime_is_not_trusted"] == 1


def test_gate_policy_reporter_converts_diagnostics_report_to_json() -> None:
    diagnostics = GatePolicyDiagnosticsService()
    reporter = GatePolicyReporter()

    report = diagnostics.build_report(
        (
            GatePolicyInput(
                regime="trend_up",
                direction="LONG",
                confidence=0.80,
                tp_before_sl_probability=0.70,
            ),
            GatePolicyInput(
                regime="trend_up",
                direction="LONG",
                confidence=0.40,
                tp_before_sl_probability=0.70,
            ),
        )
    )

    json_payload = reporter.report_to_json(report)
    payload = json.loads(json_payload)

    assert payload["total"] == 2
    assert payload["allowed_total"] == 1
    assert payload["blocked_total"] == 1
    assert payload["decision_counts"]["ALLOW_LONG"] == 1
    assert payload["decision_counts"]["LOW_CONFIDENCE"] == 1
    assert payload["reason_counts"]["confidence_below_threshold"] == 1


def test_gate_policy_reporter_supports_compact_json() -> None:
    diagnostics = GatePolicyDiagnosticsService()
    reporter = GatePolicyReporter()

    report = diagnostics.build_report(())

    json_payload = reporter.report_to_json(report, indent=None)

    assert "\n" not in json_payload

    payload = json.loads(json_payload)

    assert payload["total"] == 0
    assert payload["allowed_total"] == 0
    assert payload["blocked_total"] == 0
