import json

from app.training.training_pipeline_logger import TrainingPipelineLogger


def test_training_pipeline_logger_creates_files_and_writes_events(tmp_path) -> None:
    logger = TrainingPipelineLogger(run_id="20260611_213045_BTCUSDT_15m", output_dir=tmp_path)

    assert logger.paths.run_dir.exists()

    logger.pipeline_started(message="pipeline started", data={"symbol": "BTCUSDT"})
    logger.stage_started(stage="build_features", message="Building features")
    logger.stage_completed(
        stage="build_features",
        status="COMPLETED",
        message="Features built",
        duration_seconds=1.25,
        data={"rows": 100},
    )
    logger.pipeline_completed(
        status="COMPLETED",
        message="pipeline completed",
        duration_seconds=2.50,
        data={"quality_status": "NEEDS_MORE_DATA"},
    )

    assert logger.paths.log_path.exists()
    assert logger.paths.events_path.exists()

    lines = logger.paths.events_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 4

    payloads = [json.loads(line) for line in lines]

    assert payloads[0]["event"] == "pipeline_started"
    assert payloads[1]["event"] == "stage_started"
    assert payloads[2]["event"] == "stage_completed"
    assert payloads[3]["event"] == "pipeline_completed"

    for payload in payloads:
        assert payload["run_id"] == "20260611_213045_BTCUSDT_15m"
        assert payload["stage"]
        assert payload["status"]
        assert payload["timestamp"]


def test_training_pipeline_logger_human_log_is_readable(tmp_path) -> None:
    logger = TrainingPipelineLogger(run_id="test_run", output_dir=tmp_path)

    logger.stage_started(stage="train_model", message="Training model")
    logger.stage_failed(
        stage="train_model",
        message="Training failed",
        duration_seconds=0.42,
        data={"error": "boom"},
    )

    text = logger.paths.log_path.read_text(encoding="utf-8")

    assert "[INFO] [train_model]" in text
    assert "[ERROR] [train_model]" in text
    assert "event=stage_started" in text
    assert "event=stage_failed" in text
