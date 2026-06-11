import json

from app.training.training_pipeline_reporter import TrainingPipelineReporter
from app.training.training_pipeline_runner import (
    LongHistoryTrainingPipelineRunner,
    TrainingPipelineConfig,
)


def test_training_pipeline_reporter_compact_summary_contains_counts_and_paths(tmp_path) -> None:
    runner = LongHistoryTrainingPipelineRunner()
    reporter = TrainingPipelineReporter()
    result = runner.run(
        TrainingPipelineConfig(
            symbol="BTCUSDT",
            interval="15m",
            start_date="2025-01-01",
            run_id="reporter_case",
            dry_run=True,
            output_dir=tmp_path,
        )
    )

    payload = reporter.compact_summary_to_dict(result)

    assert payload["run_id"] == "reporter_case"
    assert payload["status"] == "DRY_RUN_COMPLETED"
    assert payload["stage_count"] == len(result.stage_results)
    assert payload["log_path"]
    assert payload["events_path"]


def test_training_pipeline_reporter_writes_json_and_markdown(tmp_path) -> None:
    runner = LongHistoryTrainingPipelineRunner()
    reporter = TrainingPipelineReporter()
    result = runner.run(
        TrainingPipelineConfig(
            symbol="BTCUSDT",
            interval="15m",
            start_date="2025-01-01",
            run_id="report_files_case",
            dry_run=True,
            output_dir=tmp_path,
        )
    )

    json_path = reporter.write_json_report(result)
    markdown_path = reporter.write_markdown_report(result)

    assert json_path.exists()
    assert markdown_path.exists()
    json.loads(json_path.read_text(encoding="utf-8"))

    text = markdown_path.read_text(encoding="utf-8")
    assert "training_pipeline.log" in text
    assert "training_pipeline_events.jsonl" in text
    assert "no live trading" in text
    assert "no orders" in text
    assert "no traders-core integration" in text
