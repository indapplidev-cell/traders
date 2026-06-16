from app.training.training_pipeline_runner import LongHistoryTrainingPipelineRunner, TrainingPipelineConfig


def test_long_history_runner_has_resolved_datetime_range_method() -> None:
    runner = LongHistoryTrainingPipelineRunner()
    config = TrainingPipelineConfig(
        symbol="BTCUSDT",
        interval="15m",
        start_date="2026-05-01",
        end_date="2026-06-15",
    )

    start_at, end_at = runner._resolved_datetime_range(config)

    assert start_at.isoformat() == "2026-05-01T00:00:00+00:00"
    assert end_at.isoformat() == "2026-06-16T00:00:00+00:00"
