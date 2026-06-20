from __future__ import annotations

from app.diagnostics.two_stage_trade_diagnostics import TwoStageTradeDiagnostics


def test_two_stage_quality_gate_passes_for_balanced_masked_candidate() -> None:
    diagnostics = TwoStageTradeDiagnostics().evaluate_metrics(
        {
            "trade_row_ratio": 0.0586,
            "actual_trade_rate": 0.0586,
            "predicted_trade_rate": 0.1089,
            "predicted_to_actual_trade_rate_ratio": 1.86,
            "opportunity_precision": 0.3113,
            "opportunity_recall": 0.5789,
            "opportunity_f1": 0.4049,
            "opportunity_false_positive_rate": 0.0797,
            "direction_accuracy_on_trade_rows": 1.0,
            "direction_trade_rows": 65,
            "setup_quality_bucket_metrics_after_mask": {
                "missing_or_zero": {"row_count": 748, "false_positive_count": 0},
            },
        }
    )

    assert diagnostics["two_stage_quality_gate_passed"] is True
    assert diagnostics["anti_undertrading_gate_passed"] is True
    assert diagnostics["status"] == "TWO_STAGE_PROMISING"


def test_two_stage_quality_gate_rejects_precision_trap_undertrading() -> None:
    diagnostics = TwoStageTradeDiagnostics().evaluate_metrics(
        {
            "trade_row_ratio": 0.0703,
            "actual_trade_rate": 0.0703,
            "predicted_trade_rate": 0.0017,
            "predicted_to_actual_trade_rate_ratio": 0.02,
            "opportunity_precision": 1.0,
            "opportunity_recall": 0.0233,
            "opportunity_f1": 0.0455,
            "opportunity_false_positive_rate": 0.0,
            "direction_accuracy_on_trade_rows": 1.0,
            "direction_trade_rows": 1,
            "setup_quality_bucket_metrics_after_mask": {
                "missing_or_zero": {"row_count": 700, "false_positive_count": 0},
            },
        }
    )

    assert diagnostics["two_stage_quality_gate_passed"] is False
    assert diagnostics["anti_undertrading_gate_passed"] is False
    assert diagnostics["status"] == "TWO_STAGE_UNDERTRADING"
    assert "predicted_trade_rate_below_gate" in diagnostics["warnings"]
