from pathlib import Path


def test_stage_ml26_training_pipeline_report_exists_and_documents_scope() -> None:
    report_path = Path("reports/stage_ml26_long_history_training_pipeline_runner_report.md")

    assert report_path.exists()

    text = report_path.read_text(encoding="utf-8")

    required_phrases = [
        "Stage ML26",
        "Long-history Training Pipeline Runner",
        "train-quality-pipeline",
        "training_pipeline.log",
        "training_pipeline_events.jsonl",
        "training_pipeline_report.json",
        "dry-run",
        "sample mode",
        "no auto activation",
        "no live",
        "no orders",
        "no traders-core",
        "ML27",
    ]

    for phrase in required_phrases:
        assert phrase in text
