from app.training.training_pipeline_runner import LongHistoryTrainingPipelineRunner


def test_ml38_8_training_pipeline_uses_direction_separation_objective() -> None:
    runner = LongHistoryTrainingPipelineRunner()

    assert runner.DEFAULT_DIRECTION_LOSS_NAME == "focal"
    assert runner.DEFAULT_DIRECTION_LOSS_WEIGHT > 1.0
    assert runner.DEFAULT_TP_SL_LOSS_WEIGHT < 1.0
    assert runner.DEFAULT_MOVE_LOSS_WEIGHT < 1.0
    assert runner.DEFAULT_RISK_LOSS_WEIGHT < 1.0
    assert runner.DEFAULT_DIRECTION_LOGIT_GAP_WEIGHT > 0.0
    assert runner.DEFAULT_LABEL_NOISE_HARDENING_ENABLED is True
