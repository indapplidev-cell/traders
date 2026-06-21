from app.evaluation.signal_gate_evaluator import SignalGateEvaluator
from app.evaluation.profit_aware_evaluator_v2 import ProfitAwareEvaluatorV2


def test_ml38_10_14_1_signal_gate_skips_entry_path_blocked_rows() -> None:
    evaluator = SignalGateEvaluator()
    rows = [
        {
            "predicted_label": "UP",
            "actual_label": "UP",
            "prob_up": 0.70,
            "prob_down": 0.20,
            "prob_flat": 0.10,
            "confidence": 0.70,
            "entry_path_filter_blocked": True,
        },
        {
            "predicted_label": "UP",
            "actual_label": "UP",
            "prob_up": 0.70,
            "prob_down": 0.20,
            "prob_flat": 0.10,
            "confidence": 0.70,
            "entry_path_filter_blocked": False,
        },
    ]

    selection = evaluator.select_signals(rows, gate_type="max_prob", threshold=0.50)

    assert selection["signal_count"] == 1
    assert selection["skipped_entry_path_filter_count"] == 1


def test_ml38_10_14_1_profit_summary_reports_entry_path_prediction_filter() -> None:
    predictions = [
        {"entry_path_filter_enabled": True, "entry_path_filter_blocked": True, "entry_path_original_predicted_label": "UP", "entry_path_quality_score": 0.30, "stop_pressure_risk_score": 0.80},
        {"entry_path_filter_enabled": True, "entry_path_filter_blocked": False, "entry_path_original_predicted_label": "DOWN", "entry_path_quality_score": 0.80, "stop_pressure_risk_score": 0.20},
    ]

    summary = ProfitAwareEvaluatorV2._entry_path_prediction_filter_summary(predictions)

    assert summary["entry_path_filter_enabled"] is True
    assert summary["total_prediction_rows"] == 2
    assert summary["blocked_prediction_rows"] == 1
    assert summary["blocked_prediction_rate"] == 0.5
    assert summary["blocked_original_label_counts"]["UP"] == 1
