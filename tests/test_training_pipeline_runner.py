import json

from app.training import training_pipeline_runner as runner_module
from app.training.training_pipeline_runner import (
    LongHistoryTrainingPipelineRunner,
    TrainingPipelineConfig,
)


def test_training_pipeline_runner_dry_run_completes_without_db(tmp_path, monkeypatch) -> None:
    def fail_get_session():
        raise AssertionError("dry_run should not access DB")

    monkeypatch.setattr(runner_module, "get_session", fail_get_session)

    runner = LongHistoryTrainingPipelineRunner()
    result = runner.run(
        TrainingPipelineConfig(
            symbol="BTCUSDT",
            interval="15m",
            start_date="2025-01-01",
            run_id="dry_run_case",
            dry_run=True,
            output_dir=tmp_path,
        )
    )

    payload = result.to_dict()

    assert result.status == "DRY_RUN_COMPLETED"
    assert result.quality_summary["quality_status"] == "NEEDS_MORE_DATA"
    assert len(result.stage_results) == len(LongHistoryTrainingPipelineRunner.STAGES)
    assert result.safety["approved_for_live_trading"] is False
    assert result.safety["approved_for_auto_activation"] is False
    assert result.safety["orders_enabled"] is False
    assert result.safety["traders_core_connected"] is False
    assert payload["log_path"]
    assert payload["events_path"]
    assert payload["json_report_path"]
    assert payload["markdown_report_path"]
    json.dumps(payload, ensure_ascii=False, sort_keys=True)


def test_training_pipeline_runner_sample_mode_returns_needs_more_data(tmp_path) -> None:
    runner = LongHistoryTrainingPipelineRunner()
    result = runner.run(
        TrainingPipelineConfig(
            symbol="BTCUSDT",
            interval="15m",
            start_date="2025-01-01",
            run_id="sample_mode_case",
            sample_mode=True,
            output_dir=tmp_path,
        )
    )

    assert result.status == "SAMPLE_COMPLETED"
    assert result.quality_summary["quality_status"] == "NEEDS_MORE_DATA"
    assert {item.stage for item in result.stage_results} == set(
        LongHistoryTrainingPipelineRunner.STAGES
    )


def test_training_pipeline_runner_failed_stage_produces_failed_pipeline(tmp_path) -> None:
    def fail_build_dataset(config, stage_payloads):
        raise RuntimeError("forced failure")

    runner = LongHistoryTrainingPipelineRunner(
        stage_handlers={"build_dataset": fail_build_dataset}
    )
    result = runner.run(
        TrainingPipelineConfig(
            symbol="BTCUSDT",
            interval="15m",
            start_date="2025-01-01",
            run_id="failed_case",
            dry_run=True,
            output_dir=tmp_path,
        )
    )

    assert result.status == "FAILED"
    assert any(
        item.stage == "build_dataset" and item.status == "FAILED"
        for item in result.stage_results
    )
