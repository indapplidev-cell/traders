from __future__ import annotations

from app.training.metrics import TrainingMetrics


def test_trade_two_stage_metrics_report_trade_and_direction_quality() -> None:
    metrics = TrainingMetrics().compute(
        direction_probabilities=[
            [0.80, 0.10, 0.10],
            [0.20, 0.70, 0.10],
            [0.90, 0.05, 0.05],
            [0.10, 0.80, 0.10],
        ],
        direction_targets=[0, 1, 2, 2],
        tp_sl_probabilities=[0.8, 0.8, 0.1, 0.1],
        tp_sl_targets=[True, True, None, None],
        expected_move_predictions=[1.0, 1.0, 0.0, 0.0],
        expected_move_targets=[1.0, 1.0, 0.0, 0.0],
        opportunity_probabilities=[0.90, 0.80, 0.20, 0.70],
        opportunity_targets=[1, 1, 0, 0],
        training_objective="trade_two_stage",
    )

    assert metrics["trade_row_ratio"] == 0.5
    assert metrics["no_trade_row_ratio"] == 0.5
    assert metrics["direction_trade_rows"] == 2
    assert metrics["direction_accuracy_on_trade_rows"] == 1.0
    assert metrics["opportunity_recall"] == 1.0
    assert metrics["opportunity_precision"] == 2 / 3
    assert metrics["opportunity_false_positive_rate"] == 0.5
    assert "two_stage_confusion_matrix" in metrics
