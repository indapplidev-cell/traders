from __future__ import annotations

from app.diagnostics.two_stage_trade_diagnostics import TwoStageTradeDiagnostics


def test_two_stage_diagnostics_flags_precision_and_trade_rate_gate_failures() -> None:
    diagnostics = TwoStageTradeDiagnostics().evaluate_metrics(
        {
            "trade_row_ratio": 0.10,
            "predicted_trade_rate": 0.40,
            "predicted_to_actual_trade_rate_ratio": 4.0,
            "opportunity_precision": 0.10,
            "opportunity_recall": 0.60,
            "opportunity_f1": 0.17,
            "opportunity_false_positive_rate": 0.30,
            "direction_accuracy_on_trade_rows": 0.50,
            "direction_trade_rows": 12,
        },
        min_precision=0.25,
        max_predicted_trade_rate=0.15,
        max_predicted_to_actual_trade_rate_ratio=3.0,
        max_false_positive_rate=0.25,
    )

    assert "opportunity_precision_below_gate" in diagnostics["warnings"]
    assert "predicted_trade_rate_above_gate" in diagnostics["warnings"]
    assert diagnostics["precision_control_passed"] is False


def test_two_stage_diagnostics_pass_precision_control_when_metrics_are_normal() -> None:
    diagnostics = TwoStageTradeDiagnostics().evaluate_metrics(
        {
            "trade_row_ratio": 0.10,
            "predicted_trade_rate": 0.10,
            "predicted_to_actual_trade_rate_ratio": 1.00,
            "opportunity_precision": 0.40,
            "opportunity_recall": 0.60,
            "opportunity_f1": 0.48,
            "opportunity_false_positive_rate": 0.10,
            "direction_accuracy_on_trade_rows": 0.55,
            "direction_trade_rows": 12,
        },
        min_precision=0.25,
        min_recall=0.50,
        max_predicted_trade_rate=0.15,
        max_predicted_to_actual_trade_rate_ratio=3.0,
        max_false_positive_rate=0.25,
    )

    assert diagnostics["precision_control_passed"] is True
