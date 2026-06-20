from __future__ import annotations

from app.training.metrics import TrainingMetrics


def test_trade_two_stage_metrics_apply_setup_quality_decision_mask_and_preserve_raw_metrics() -> None:
    disabled_metrics = TrainingMetrics().compute(
        direction_probabilities=[
            [0.90, 0.10, 0.0],
            [0.85, 0.15, 0.0],
            [0.80, 0.20, 0.0],
            [0.75, 0.25, 0.0],
            [0.20, 0.80, 0.0],
        ],
        direction_targets=[2, 0, 0, 2, 2],
        tp_sl_probabilities=[0.0] * 5,
        tp_sl_targets=[None] * 5,
        expected_move_predictions=[0.0] * 5,
        expected_move_targets=[0.0] * 5,
        opportunity_probabilities=[0.90, 0.88, 0.80, 0.75, 0.10],
        opportunity_targets=[0, 1, 1, 0, 0],
        opportunity_probability_threshold=0.65,
        setup_quality_scores=[0.0, 0.85, 0.70, 0.30, 0.90],
        setup_quality_min_threshold=0.60,
        training_objective="trade_two_stage",
    )

    enabled_metrics = TrainingMetrics().compute(
        direction_probabilities=[
            [0.90, 0.10, 0.0],
            [0.85, 0.15, 0.0],
            [0.80, 0.20, 0.0],
            [0.75, 0.25, 0.0],
            [0.20, 0.80, 0.0],
        ],
        direction_targets=[2, 0, 0, 2, 2],
        tp_sl_probabilities=[0.0] * 5,
        tp_sl_targets=[None] * 5,
        expected_move_predictions=[0.0] * 5,
        expected_move_targets=[0.0] * 5,
        opportunity_probabilities=[0.90, 0.88, 0.80, 0.75, 0.10],
        opportunity_targets=[0, 1, 1, 0, 0],
        opportunity_probability_threshold=0.65,
        setup_quality_scores=[0.0, 0.85, 0.70, 0.30, 0.90],
        setup_quality_min_threshold=0.60,
        setup_quality_decision_mask_enabled=True,
        setup_quality_decision_mask_min_threshold=0.60,
        training_objective="trade_two_stage",
    )

    assert disabled_metrics["predicted_trade_rate"] == 0.8
    assert disabled_metrics["setup_quality_bucket_metrics"]["missing_or_zero"]["false_positive_count"] == 1

    assert enabled_metrics["setup_quality_decision_mask_enabled"] is True
    assert enabled_metrics["setup_quality_decision_mask_min_threshold"] == 0.60
    assert enabled_metrics["predicted_trade_rate"] == 0.4
    assert enabled_metrics["raw_predicted_trade_rate"] == 0.8
    assert enabled_metrics["masked_predicted_trade_rate"] == 0.4
    assert enabled_metrics["raw_opportunity_precision"] == 0.5
    assert enabled_metrics["opportunity_precision"] == 1.0
    assert enabled_metrics["raw_opportunity_recall"] == 1.0
    assert enabled_metrics["opportunity_recall"] == 1.0
    assert enabled_metrics["setup_quality_masked_row_count"] == 2
    assert enabled_metrics["setup_quality_forced_no_trade_count"] == 2
    assert enabled_metrics["setup_quality_mask_false_positive_removed_count"] == 2
    assert enabled_metrics["setup_quality_mask_trade_prediction_removed_count"] == 2
    assert enabled_metrics["setup_quality_bucket_metrics_raw"]["missing_or_zero"]["false_positive_count"] == 1
    assert enabled_metrics["setup_quality_bucket_metrics_after_mask"]["missing_or_zero"]["false_positive_count"] == 0
    assert enabled_metrics["setup_quality_bucket_metrics_after_mask"]["missing_or_zero"]["predicted_trade_count"] == 0
