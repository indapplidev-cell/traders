from app.training.training_pipeline_runner import LongHistoryTrainingPipelineRunner


def test_ml38_9_training_defaults_are_flat_bias_aware() -> None:
    assert LongHistoryTrainingPipelineRunner.DEFAULT_DIRECTION_LOSS_WEIGHT >= 3.0
    assert LongHistoryTrainingPipelineRunner.DEFAULT_TP_SL_LOSS_WEIGHT <= 0.10
    assert LongHistoryTrainingPipelineRunner.DEFAULT_MOVE_LOSS_WEIGHT <= 0.10
    assert LongHistoryTrainingPipelineRunner.DEFAULT_RISK_LOSS_WEIGHT <= 0.10
    assert LongHistoryTrainingPipelineRunner.DEFAULT_DIRECTION_DISTRIBUTION_LOSS_WEIGHT > 0
    assert LongHistoryTrainingPipelineRunner.DEFAULT_FLAT_PROBABILITY_FLOOR_WEIGHT > 0
    assert LongHistoryTrainingPipelineRunner.DEFAULT_FLAT_PROBABILITY_FLOOR_TARGET >= 0.18
