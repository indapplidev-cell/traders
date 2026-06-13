from types import SimpleNamespace

from app.experiments.label_grid_experiment_runner import LabelGridExperimentRunner
from app.labels.label_quality_grid import LabelQualityGridConfig


def _label_config() -> LabelQualityGridConfig:
    return LabelQualityGridConfig(
        config_id="lv2_h12_thr05_tp15_sl10",
        label_version="lv2_h12_thr05_tp15_sl10",
        horizon=12,
        threshold=0.5,
        take_profit_atr=1.5,
        stop_loss_atr=1.0,
        flat_threshold=0.5,
        description="test",
        risk_note="test",
    )


def test_ml36_2_known_quality_rejection_is_not_reported_as_failed() -> None:
    runner = LabelGridExperimentRunner()
    pipeline_result = SimpleNamespace(
        gap_quality_summary={
            "gap_severity": "CRITICAL",
            "gap_severity_for_training": "CRITICAL",
            "dataset_safe_for_training": False,
            "effective_gap_count_for_training": 12,
        },
        stage_results=(
            SimpleNamespace(stage="build_dataset", status="COMPLETED", data={"dataset_rows": 1500}),
            SimpleNamespace(
                stage="build_labels",
                status="COMPLETED",
                data={
                    "direction_counts": {"UP": 10, "DOWN": 8, "FLAT": 6},
                    "regime_label_builder_status": {
                        "regime_label_builder_status": "built",
                        "regime_label_builder_used_in_training": True,
                        "regime_specific_training_applied": True,
                        "missing_requirements": [],
                        "warnings": [],
                    },
                },
            ),
            SimpleNamespace(stage="model_quality_validation", status="FAILED", data={"error": "old_none_bug"}),
        ),
    )

    candidate = runner._build_failed_pipeline_candidate_result(
        config=SimpleNamespace(feature_version="fv2"),
        label_config=_label_config(),
        pipeline_result=pipeline_result,
    )

    assert candidate.status == "COMPLETED"
    assert candidate.candidate_status == "REJECTED"
    assert candidate.raw_candidate_status == "CANDIDATE_REJECTED"
    assert "gap_quality_gate" in candidate.failed_gates
