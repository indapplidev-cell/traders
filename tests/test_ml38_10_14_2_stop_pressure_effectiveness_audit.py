from app.evaluation.profit_aware_evaluator_v2 import ProfitAwareEvaluatorV2


def test_ml38_10_14_2_entry_path_summary_splits_quality_and_stop_pressure_blocks() -> None:
    rows = [
        {
            "entry_path_filter_enabled": True,
            "entry_path_filter_blocked": True,
            "entry_path_filter_block_reason": "low_entry_quality",
            "entry_path_filter_threshold": 0.70,
            "entry_path_filter_stop_threshold": 0.45,
            "entry_path_original_predicted_label": "UP",
            "actual_label": "FLAT",
            "entry_path_quality_score": 0.30,
            "stop_pressure_risk_score": 0.20,
        },
        {
            "entry_path_filter_enabled": True,
            "entry_path_filter_blocked": True,
            "entry_path_filter_block_reason": "high_stop_pressure",
            "entry_path_filter_threshold": 0.70,
            "entry_path_filter_stop_threshold": 0.45,
            "entry_path_original_predicted_label": "DOWN",
            "actual_label": "FLAT",
            "entry_path_quality_score": 0.90,
            "stop_pressure_risk_score": 0.80,
        },
        {
            "entry_path_filter_enabled": True,
            "entry_path_filter_blocked": True,
            "entry_path_filter_block_reason": "high_stop_pressure",
            "entry_path_filter_threshold": 0.70,
            "entry_path_filter_stop_threshold": 0.45,
            "entry_path_original_predicted_label": "UP",
            "actual_label": "UP",
            "entry_path_quality_score": 0.90,
            "stop_pressure_risk_score": 0.75,
        },
        {
            "entry_path_filter_enabled": True,
            "entry_path_filter_blocked": False,
            "entry_path_filter_threshold": 0.70,
            "entry_path_filter_stop_threshold": 0.45,
            "entry_path_original_predicted_label": "UP",
            "actual_label": "UP",
            "entry_path_quality_score": 0.90,
            "stop_pressure_risk_score": 0.10,
        },
    ]

    summary = ProfitAwareEvaluatorV2._entry_path_prediction_filter_summary(rows)
    audit = summary["stop_pressure_effectiveness_audit"]

    assert summary["entry_path_filter_enabled"] is True
    assert summary["blocked_by_low_entry_quality_count"] == 1
    assert summary["blocked_by_high_stop_pressure_count"] == 2
    assert summary["removed_false_positive_count"] == 2
    assert summary["removed_true_positive_count"] == 1
    assert audit["high_stop_pressure_removed_false_positive_count"] == 1
    assert audit["high_stop_pressure_removed_true_positive_count"] == 1
    assert audit["stop_pressure_effective_for_false_positive_reduction"] is True
    assert audit["status"] == "STOP_PRESSURE_MIXED_TRUE_AND_FALSE_POSITIVE_BLOCKS"
