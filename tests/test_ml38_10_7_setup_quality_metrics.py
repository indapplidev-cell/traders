from __future__ import annotations

from app.training.metrics import TrainingMetrics


def test_trade_two_stage_metrics_include_setup_quality_bucket_diagnostics() -> None:
    metrics = TrainingMetrics().compute(
        direction_probabilities=[
            [0.90, 0.10, 0.0],
            [0.80, 0.20, 0.0],
            [0.70, 0.30, 0.0],
            [0.60, 0.40, 0.0],
        ],
        direction_targets=[0, 0, 0, 0],
        tp_sl_probabilities=[0.0, 0.0, 0.0, 0.0],
        tp_sl_targets=[None, None, None, None],
        expected_move_predictions=[0.0, 0.0, 0.0, 0.0],
        expected_move_targets=[0.0, 0.0, 0.0, 0.0],
        opportunity_probabilities=[0.80, 0.70, 0.60, 0.20],
        opportunity_targets=[1, 0, 1, 0],
        opportunity_probability_threshold=0.65,
        setup_quality_scores=[0.65, 0.70, 0.35, 0.0],
        setup_quality_min_threshold=0.60,
        training_objective="trade_two_stage",
    )

    good_bucket = metrics["setup_quality_bucket_metrics"]["good_0_60_0_75"]
    assert good_bucket["row_count"] == 2
    assert good_bucket["precision"] == 0.5
    assert good_bucket["recall"] == 1.0
    assert good_bucket["false_positive_rate"] == 1.0

    filter_summary = metrics["setup_quality_filter_summary"]
    assert filter_summary["setup_quality_min_threshold"] == 0.60
    assert filter_summary["rows_below_threshold"] == 2
    assert filter_summary["rows_at_or_above_threshold"] == 2
    assert filter_summary["predicted_trade_rate_below_threshold"] == 0.0
    assert filter_summary["predicted_trade_rate_at_or_above_threshold"] == 1.0
