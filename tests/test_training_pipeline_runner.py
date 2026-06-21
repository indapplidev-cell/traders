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


def test_training_pipeline_runner_real_mode_uses_wired_stage_handlers(tmp_path, monkeypatch) -> None:
    def completed(message: str, data: dict) -> dict:
        return {"status": "COMPLETED", "message": message, "data": data}

    monkeypatch.setattr(
        LongHistoryTrainingPipelineRunner,
        "_load_candles_real",
        lambda self, config, stage_payloads: completed("candles", {"loaded": 100}),
    )
    monkeypatch.setattr(
        LongHistoryTrainingPipelineRunner,
        "_check_candle_gaps_real",
        lambda self, config, stage_payloads: completed("gaps", {"gap_count": 0}),
    )
    monkeypatch.setattr(
        LongHistoryTrainingPipelineRunner,
        "_build_features_real",
        lambda self, config, stage_payloads: completed("features", {"feature_version": "fv1"}),
    )
    monkeypatch.setattr(
        LongHistoryTrainingPipelineRunner,
        "_build_labels_real",
        lambda self, config, stage_payloads: completed(
            "labels",
            {"label_version": "lv1", "horizon_candles": 8},
        ),
    )
    monkeypatch.setattr(
        LongHistoryTrainingPipelineRunner,
        "_build_dataset_real",
        lambda self, config, stage_payloads: completed(
            "dataset",
            {
                "dataset_rows": 1000,
                "train_rows": 700,
                "validation_rows": 150,
                "test_rows": 150,
            },
        ),
    )
    monkeypatch.setattr(
        LongHistoryTrainingPipelineRunner,
        "_train_model_real",
        lambda self, config, stage_payloads: completed(
            "train",
            {
                "model_version": "ml_test_v1",
                "training_run_id": "train_ml_test_v1",
                "test_metrics": {"accuracy": 0.55},
                "model_accuracy": 0.55,
                "dataset_summary": {
                    "dataset_rows": 1000,
                    "train_rows": 700,
                    "validation_rows": 150,
                    "test_rows": 150,
                },
                "dataset_rows": 1000,
                "train_rows": 700,
                "validation_rows": 150,
                "val_rows": 150,
                "test_rows": 150,
                "real_training_executed": True,
            },
        ),
    )
    monkeypatch.setattr(
        LongHistoryTrainingPipelineRunner,
        "_probability_diagnostics_real",
        lambda self, config, stage_payloads: completed(
            "probability",
            {"collapse_detected": False, "predicted_direction_ratios": {"UP": 0.4}},
        ),
    )
    monkeypatch.setattr(
        LongHistoryTrainingPipelineRunner,
        "_baseline_compare_real",
        lambda self, config, stage_payloads: completed(
            "baseline",
            {"baseline_accuracy": 0.45, "baseline_results": [{"accuracy": 0.45}]},
        ),
    )
    monkeypatch.setattr(
        LongHistoryTrainingPipelineRunner,
        "_calibration_diagnostics_real",
        lambda self, config, stage_payloads: completed(
            "calibration",
            {"calibration_status": "ACCEPTABLE", "expected_calibration_error": 0.05, "brier_score": 0.6},
        ),
    )
    monkeypatch.setattr(
        LongHistoryTrainingPipelineRunner,
        "_profit_aware_evaluation_real",
        lambda self, config, stage_payloads: completed(
            "profit",
            {"profit_aware_status": "ACCEPTABLE", "summary": {"total_r": 0.0, "profit_factor": 1.0}},
        ),
    )
    monkeypatch.setattr(
        LongHistoryTrainingPipelineRunner,
        "_walk_forward_evaluation_real",
        lambda self, config, stage_payloads: completed(
            "walk",
            {"walk_forward_status": "NEEDS_MORE_DATA", "summary": {"fold_count": 1, "total_test_signal_count": 5}},
        ),
    )
    monkeypatch.setattr(
        LongHistoryTrainingPipelineRunner,
        "_gate_policy_replay_sample",
        lambda self, config, stage_payloads: completed(
            "gate",
            {"gate_policy_replay_status": "SAMPLE_ONLY", "total_records": 5, "valid_records": 4},
        ),
    )
    monkeypatch.setattr(
        LongHistoryTrainingPipelineRunner,
        "_quality_validation_real",
        lambda self, config, stage_payloads: completed(
            "quality",
            {"quality_status": "NEEDS_MORE_DATA", "approved_for_traders_core_integration": False},
        ),
    )

    runner = LongHistoryTrainingPipelineRunner()
    result = runner.run(
        TrainingPipelineConfig(
            symbol="BTCUSDT",
            interval="15m",
            start_date="2025-01-01",
            run_id="real_mode_case",
            output_dir=tmp_path,
        )
    )

    assert result.status == "COMPLETED"
    assert len(result.stage_results) == len(LongHistoryTrainingPipelineRunner.STAGES)
    assert result.model_summary["model_version"] == "ml_test_v1"
    assert all(item.status == "COMPLETED" for item in result.stage_results)
    assert all(item.data.get("reason") != "direct_real_execution_not_wired" for item in result.stage_results)

def test_training_pipeline_runner_skip_candle_load_does_not_call_loader(tmp_path, monkeypatch) -> None:
    def completed(message: str, data: dict) -> dict:
        return {"status": "COMPLETED", "message": message, "data": data}

    def fail_load_candles(self, config, stage_payloads):
        raise AssertionError("load_candles must be skipped in cached training mode")

    monkeypatch.setattr(
        LongHistoryTrainingPipelineRunner,
        "_load_candles_real",
        fail_load_candles,
    )
    monkeypatch.setattr(
        LongHistoryTrainingPipelineRunner,
        "_check_candle_gaps_real",
        lambda self, config, stage_payloads: completed(
            "gaps",
            {
                "gap_count": 29,
                "real_gap_count": 0,
                "real_missing_open_times": [],
                "trailing_incomplete_range_detected": True,
            },
        ),
    )
    monkeypatch.setattr(
        LongHistoryTrainingPipelineRunner,
        "_build_features_real",
        lambda self, config, stage_payloads: completed("features", {"feature_version": "fv3_candle_ta_context"}),
    )
    monkeypatch.setattr(
        LongHistoryTrainingPipelineRunner,
        "_build_labels_real",
        lambda self, config, stage_payloads: completed(
            "labels",
            {"label_version": "lv2_h08_thr03_tp10_sl10", "horizon_candles": 8, "direction_counts": {"UP": 1}},
        ),
    )
    monkeypatch.setattr(
        LongHistoryTrainingPipelineRunner,
        "_build_dataset_real",
        lambda self, config, stage_payloads: completed(
            "dataset",
            {"dataset_rows": 1000, "train_rows": 700, "validation_rows": 150, "test_rows": 150},
        ),
    )
    monkeypatch.setattr(
        LongHistoryTrainingPipelineRunner,
        "_train_model_real",
        lambda self, config, stage_payloads: completed(
            "train",
            {
                "model_version": "ml_test_cached",
                "training_run_id": "train_ml_test_cached",
                "test_metrics": {"accuracy": 0.55},
                "model_accuracy": 0.55,
                "dataset_rows": 1000,
                "train_rows": 700,
                "validation_rows": 150,
                "val_rows": 150,
                "test_rows": 150,
                "real_training_executed": True,
            },
        ),
    )
    monkeypatch.setattr(
        LongHistoryTrainingPipelineRunner,
        "_probability_diagnostics_real",
        lambda self, config, stage_payloads: completed(
            "probability",
            {"collapse_detected": False, "predicted_direction_ratios": {"UP": 0.4}},
        ),
    )
    monkeypatch.setattr(
        LongHistoryTrainingPipelineRunner,
        "_baseline_compare_real",
        lambda self, config, stage_payloads: completed(
            "baseline",
            {"baseline_accuracy": 0.45, "baseline_results": [{"accuracy": 0.45}]},
        ),
    )
    monkeypatch.setattr(
        LongHistoryTrainingPipelineRunner,
        "_calibration_diagnostics_real",
        lambda self, config, stage_payloads: completed("calibration", {"calibration_status": "OK"}),
    )
    monkeypatch.setattr(
        LongHistoryTrainingPipelineRunner,
        "_profit_aware_evaluation_real",
        lambda self, config, stage_payloads: completed("profit", {"summary": {"total_r": 1.0, "profit_factor": 1.2}}),
    )
    monkeypatch.setattr(
        LongHistoryTrainingPipelineRunner,
        "_walk_forward_evaluation_real",
        lambda self, config, stage_payloads: completed("walk", {"summary": {"fold_count": 1, "global_total_r": 1.0, "global_profit_factor": 1.1}}),
    )
    monkeypatch.setattr(
        LongHistoryTrainingPipelineRunner,
        "_quality_validation_real",
        lambda self, config, stage_payloads: completed(
            "quality",
            {
                "quality_status": "QUALITY_REJECTED",
                "approved_for_traders_core_integration": False,
                "candidate_selection": {"candidate_status": "REJECTED", "failed_gates": []},
                "gap_quality": {"dataset_safe_for_training": True},
                "anti_collapse": {},
                "quality_gates_summary": {},
                "label_config": {},
            },
        ),
    )

    runner = LongHistoryTrainingPipelineRunner()
    result = runner.run(
        TrainingPipelineConfig(
            symbol="BTCUSDT",
            interval="15m",
            start_date="2025-01-01",
            run_id="cached_skip_case",
            feature_version="fv3_candle_ta_context",
            output_dir=tmp_path,
            skip_candle_load=True,
        )
    )

    load_stage = next(item for item in result.stage_results if item.stage == "load_candles")
    assert load_stage.status == "SKIPPED"
    assert load_stage.data["skip_candle_load"] is True
    assert load_stage.data["candle_source"] == "postgresql_db_cache"
