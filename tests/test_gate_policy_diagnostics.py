from app.gates.gate_policy_diagnostics import GatePolicyDiagnosticsService
from app.gates.gate_policy_models import GatePolicyDecision, GatePolicyInput


def test_gate_policy_diagnostics_evaluates_many_signals_in_order() -> None:
    service = GatePolicyDiagnosticsService()

    results = service.evaluate_many(
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

    assert len(results) == 3
    assert results[0].decision == GatePolicyDecision.ALLOW_LONG
    assert results[1].decision == GatePolicyDecision.BAD_REGIME
    assert results[2].decision == GatePolicyDecision.ALLOW_SHORT


def test_gate_policy_diagnostics_builds_aggregate_report() -> None:
    service = GatePolicyDiagnosticsService()

    report = service.build_report(
        (
            GatePolicyInput(
                regime="trend_up",
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
            GatePolicyInput(
                regime="range",
                direction="LONG",
                confidence=0.80,
                tp_before_sl_probability=0.70,
            ),
            GatePolicyInput(
                regime="trend_up",
                direction="LONG",
                confidence=0.50,
                tp_before_sl_probability=0.70,
            ),
            GatePolicyInput(
                regime="trend_up",
                direction="FLAT",
                confidence=0.90,
                tp_before_sl_probability=0.80,
            ),
        )
    )

    assert report.total == 5
    assert report.allowed_total == 2
    assert report.blocked_total == 3

    assert report.decision_counts["ALLOW_LONG"] == 1
    assert report.decision_counts["ALLOW_SHORT"] == 1
    assert report.decision_counts["BAD_REGIME"] == 1
    assert report.decision_counts["LOW_CONFIDENCE"] == 1
    assert report.decision_counts["BLOCK"] == 1

    assert report.regime_counts["trend_up"] == 3
    assert report.regime_counts["trend_down"] == 1
    assert report.regime_counts["range"] == 1

    assert report.direction_counts["LONG"] == 3
    assert report.direction_counts["SHORT"] == 1
    assert report.direction_counts["FLAT"] == 1

    assert report.reason_counts["signal_passed_gate_policy"] == 2
    assert report.reason_counts["regime_is_not_trusted"] == 1
    assert report.reason_counts["confidence_below_threshold"] == 1
    assert report.reason_counts["direction_is_not_tradeable"] == 1


def test_gate_policy_diagnostics_handles_empty_signal_list() -> None:
    service = GatePolicyDiagnosticsService()

    report = service.build_report(())

    assert report.total == 0
    assert report.allowed_total == 0
    assert report.blocked_total == 0
    assert report.decision_counts == {}
    assert report.regime_counts == {}
    assert report.direction_counts == {}
    assert report.reason_counts == {}
