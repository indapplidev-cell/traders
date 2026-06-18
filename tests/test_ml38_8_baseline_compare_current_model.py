from app.training.training_pipeline_runner import (
    COMPLETED,
    LongHistoryTrainingPipelineRunner,
    TrainingPipelineConfig,
)


def test_ml38_8_baseline_compare_uses_current_training_model_only(monkeypatch, tmp_path) -> None:
    captured: dict = {}

    class FakeDiagnosticsService:
        def compare_models(self, **kwargs):
            captured.update(kwargs)
            return {
                "best_baseline": {
                    "name": "majority_class",
                    "test_metrics": {"accuracy": 0.42, "brier_score": 0.7},
                },
                "baseline_results": {
                    "majority_class": {"test": {"accuracy": 0.42, "brier_score": 0.7}},
                },
                "model_results": [
                    {
                        "model_version": "mv_current_ml38_8",
                        "accuracy": 0.33,
                        "brier_score": 0.8,
                    }
                ],
                "best_model": {
                    "model_version": "mv_current_ml38_8",
                    "accuracy": 0.33,
                    "brier_score": 0.8,
                },
                "is_best_model_better_than_best_baseline": False,
            }

    runner = LongHistoryTrainingPipelineRunner()
    monkeypatch.setattr(
        runner,
        "_with_diagnostics_service",
        lambda callback: callback(FakeDiagnosticsService()),
    )

    result = runner._baseline_compare_real(
        TrainingPipelineConfig(
            symbol="BTCUSDT",
            interval="15m",
            start_date="2026-05-01",
            end_date="2026-06-15",
            run_id="ml38_8_baseline_compare_current_model_test",
            feature_version="fv3_candle_ta_context",
            output_dir=tmp_path,
        ),
        stage_payloads={
            "train_model": {
                "model_version": "mv_current_ml38_8",
            }
        },
    )

    assert result["status"] == COMPLETED
    assert result["data"]["candidate_model_version"] == "mv_current_ml38_8"
    assert result["data"]["baseline_accuracy"] == 0.42
    assert captured["model_versions"] == ["mv_current_ml38_8"]
    assert captured["skip_incompatible_models"] is False
