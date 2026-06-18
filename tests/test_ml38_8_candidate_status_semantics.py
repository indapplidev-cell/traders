from types import SimpleNamespace

from app.experiments.label_grid_experiment_runner import LabelGridExperimentRunner
from app.labels.label_quality_grid import LabelQualityGridConfig


def _label_config() -> LabelQualityGridConfig:
    return LabelQualityGridConfig(
        config_id="lv4_h06_thr035_tp12_sl08_cp",
        label_version="lv4_h06_thr035_tp12_sl08_cp",
        horizon=6,
        threshold=0.35,
        take_profit_atr=1.2,
        stop_loss_atr=0.8,
        flat_threshold=0.35,
        description="ML38.8 status semantics regression",
        risk_note="test",
    )


def test_ml38_8_quality_rejected_payload_is_rejected_not_failed() -> None:
    runner = LabelGridExperimentRunner()
    quality_payload = {
        "quality_status": "QUALITY_REJECTED",
        "model_version": "mv_ml38_8_status_test",
        "training_run_id": "run_ml38_8_status_test",
        "dataset_rows": 4000,
        "train_rows": 2800,
        "validation_rows": 600,
        "test_rows": 600,
        "model_accuracy": 0.33,
        "baseline_accuracy": 0.34,
        "accuracy_edge": -0.01,
        "candidate_selection": {
            "candidate_status": "CANDIDATE_REJECTED",
            "failed_gates": [],
            "passed_gates": ["gap_quality_gate"],
        },
        "quality_gates_summary": {
            "failed_gates": [],
            "passed_gates": ["gap_quality_gate"],
        },
        "gap_quality": {
            "gap_severity": "OK",
            "gap_severity_for_training": "OK",
            "dataset_safe_for_training": True,
            "effective_gap_count_for_training": 0,
        },
        "probability_diagnostics": {
            "actual_direction_counts": {"UP": 100, "DOWN": 100, "FLAT": 100},
            "predicted_direction_counts": {"UP": 120, "DOWN": 90, "FLAT": 90},
        },
        "regime_label_builder_status": {
            "regime_label_builder_status": "built",
            "regime_label_builder_used_in_training": True,
            "regime_specific_training_applied": True,
            "missing_requirements": [],
            "warnings": [],
        },
    }
    pipeline_result = SimpleNamespace(
        gap_quality_summary=quality_payload["gap_quality"],
        quality_summary=quality_payload,
        stage_results=(
            SimpleNamespace(stage="build_dataset", status="COMPLETED", data={"dataset_rows": 4000}),
            SimpleNamespace(
                stage="build_labels",
                status="COMPLETED",
                data={
                    "direction_counts": {"UP": 100, "DOWN": 100, "FLAT": 100},
                    "regime_label_builder_status": quality_payload["regime_label_builder_status"],
                },
            ),
            SimpleNamespace(
                stage="train_model",
                status="COMPLETED",
                data={"model_version": "mv_ml38_8_status_test", "training_run_id": "run_ml38_8_status_test"},
            ),
            SimpleNamespace(stage="probability_diagnostics", status="COMPLETED", data=quality_payload["probability_diagnostics"]),
            SimpleNamespace(stage="model_quality_validation", status="FAILED", data=quality_payload),
        ),
    )

    candidate = runner._build_failed_pipeline_candidate_result(
        config=SimpleNamespace(feature_version="fv3_candle_ta_context"),
        label_config=_label_config(),
        pipeline_result=pipeline_result,
    )

    assert candidate.status == "COMPLETED"
    assert candidate.candidate_status == "REJECTED"
    assert candidate.raw_candidate_status == "CANDIDATE_REJECTED"
    assert candidate.quality_status == "QUALITY_REJECTED"
    assert candidate.model_quality_validation_status == "COMPLETED"
    assert candidate.model_version == "mv_ml38_8_status_test"
    assert candidate.training_run_id == "run_ml38_8_status_test"
    assert candidate.failed_gates == ()
    assert "gap_quality_gate" in candidate.passed_gates


def test_ml38_8_empty_failed_pipeline_still_remains_failed() -> None:
    runner = LabelGridExperimentRunner()
    pipeline_result = SimpleNamespace(
        gap_quality_summary={},
        quality_summary={},
        stage_results=(
            SimpleNamespace(stage="model_quality_validation", status="FAILED", data={}),
        ),
    )

    candidate = runner._build_failed_pipeline_candidate_result(
        config=SimpleNamespace(feature_version="fv3_candle_ta_context"),
        label_config=_label_config(),
        pipeline_result=pipeline_result,
    )

    assert candidate.status == "FAILED"
    assert candidate.candidate_status == "FAILED"
    assert candidate.raw_candidate_status == "FAILED"
