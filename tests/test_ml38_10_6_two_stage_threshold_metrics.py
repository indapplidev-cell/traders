from __future__ import annotations

from app.training.metrics import TrainingMetrics


def test_trade_two_stage_metrics_respect_opportunity_threshold() -> None:
    low_threshold_metrics = TrainingMetrics().compute(
        direction_probabilities=[
            [0.80, 0.10, 0.10],
            [0.20, 0.70, 0.10],
            [0.70, 0.20, 0.10],
            [0.15, 0.75, 0.10],
        ],
        direction_targets=[2, 2, 0, 1],
        tp_sl_probabilities=[0.8, 0.8, 0.8, 0.2],
        tp_sl_targets=[True, True, True, None],
        expected_move_predictions=[1.0, 1.0, 1.0, 0.0],
        expected_move_targets=[1.0, 1.0, 1.0, 0.0],
        opportunity_probabilities=[0.52, 0.58, 0.66, 0.72],
        opportunity_targets=[0, 0, 1, 1],
        opportunity_probability_threshold=0.50,
        training_objective="trade_two_stage",
    )
    high_threshold_metrics = TrainingMetrics().compute(
        direction_probabilities=[
            [0.80, 0.10, 0.10],
            [0.20, 0.70, 0.10],
            [0.70, 0.20, 0.10],
            [0.15, 0.75, 0.10],
        ],
        direction_targets=[2, 2, 0, 1],
        tp_sl_probabilities=[0.8, 0.8, 0.8, 0.2],
        tp_sl_targets=[True, True, True, None],
        expected_move_predictions=[1.0, 1.0, 1.0, 0.0],
        expected_move_targets=[1.0, 1.0, 1.0, 0.0],
        opportunity_probabilities=[0.52, 0.58, 0.66, 0.72],
        opportunity_targets=[0, 0, 1, 1],
        opportunity_probability_threshold=0.65,
        training_objective="trade_two_stage",
    )

    assert low_threshold_metrics["predicted_trade_rate"] > high_threshold_metrics["predicted_trade_rate"]
    assert high_threshold_metrics["opportunity_precision"] >= low_threshold_metrics["opportunity_precision"]
    assert "predicted_to_actual_trade_rate_ratio" in high_threshold_metrics
    assert high_threshold_metrics["opportunity_probability_threshold"] == 0.65
