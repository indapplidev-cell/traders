from app.training.training_pipeline_runner import LongHistoryTrainingPipelineRunner, TrainingPipelineConfig


def test_training_pipeline_quality_extensions_are_present_in_report_payload(tmp_path) -> None:
    result = LongHistoryTrainingPipelineRunner().run(
        TrainingPipelineConfig(
            symbol="BTCUSDT",
            interval="15m",
            start_date="2025-01-01",
            run_id="ml27_quality_extensions_case",
            dry_run=True,
            output_dir=tmp_path,
        )
    )

    payload = result.to_dict()

    assert "gap_quality_summary" in payload
    assert "anti_collapse_summary" in payload
    assert "candidate_selection_summary" in payload
    assert "label_config_summary" in payload
    assert "quality_gates_summary" in payload
    assert "quality_summary" in payload
    assert "model_summary" in payload
