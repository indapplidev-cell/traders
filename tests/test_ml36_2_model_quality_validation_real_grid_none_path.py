from app.training.training_pipeline_runner import (
    LongHistoryTrainingPipelineRunner,
    TrainingPipelineConfig,
)


def test_ml36_2_model_quality_validation_real_grid_none_path() -> None:
    runner = LongHistoryTrainingPipelineRunner()
    payload = runner._quality_validation_real(
        TrainingPipelineConfig(
            symbol="BTCUSDT",
            interval="15m",
            start_date="2025-01-01",
            end_date="2025-06-01",
            feature_version="fv2",
        ),
        {
            "train_model": {
                "model_version": "candle_mlp_fv2",
                "training_run_id": "run_btc",
                "dataset_rows": 2048,
                "train_rows": 1400,
                "validation_rows": 320,
                "test_rows": 328,
                "model_accuracy": 0.54,
                "sample_mode": False,
                "real_training_executed": True,
            },
            "baseline_compare": {
                "baselines": {
                    "majority_class": {
                        "test": {
                            "accuracy": 0.50,
                        }
                    }
                }
            },
            "probability_diagnostics": None,
            "calibration_diagnostics": None,
            "profit_aware_evaluation": None,
            "walk_forward_evaluation": None,
            "gate_policy_replay_evaluation": None,
            "check_candle_gaps": {
                "gap_count": 0,
                "missing_open_times": None,
                "real_missing_open_times": None,
                "trailing_incomplete_open_times": None,
                "trailing_incomplete_range_detected": None,
            },
            "build_labels": {
                "regime_label_builder_status": {
                    "regime_label_builder_status": "built",
                    "regime_label_builder_used_in_training": True,
                    "regime_specific_training_applied": True,
                    "missing_requirements": [],
                    "warnings": [],
                }
            },
        },
    )

    report = payload["data"]

    assert payload["status"] == "COMPLETED"
    assert "NoneType" not in payload["message"]
    assert report["candidate_selection"]["candidate_status"] not in {"UNKNOWN", "", None}
    assert "probability_diagnostics_not_provided" in report["warnings"]
