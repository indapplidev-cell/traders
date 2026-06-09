from app.training.metrics import LABEL_TO_INDEX, TrainingMetrics


def test_training_metrics_compute_expected_values() -> None:
    metrics = TrainingMetrics()
    result = metrics.compute(
        direction_probabilities=[
            [0.8, 0.1, 0.1],
            [0.2, 0.7, 0.1],
            [0.2, 0.2, 0.6],
        ],
        direction_targets=[
            LABEL_TO_INDEX["UP"],
            LABEL_TO_INDEX["DOWN"],
            LABEL_TO_INDEX["FLAT"],
        ],
        tp_sl_probabilities=[0.8, 0.2, 0.7],
        tp_sl_targets=[True, False, None],
        expected_move_predictions=[1.0, -0.5, 0.2],
        expected_move_targets=[0.9, -0.2, 0.0],
    )

    assert result["accuracy"] == 1.0
    assert result["precision_up"] == 1.0
    assert result["precision_down"] == 1.0
    assert result["tp_before_sl_accuracy"] == 1.0
    assert result["average_expected_move_error"] > 0.0
