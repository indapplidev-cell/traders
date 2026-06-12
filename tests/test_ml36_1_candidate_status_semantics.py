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


def test_ml36_1_completed_candidate_never_ends_with_unknown_status() -> None:
    runner = LabelGridExperimentRunner()
    candidate = runner._build_candidate_result(
        label_config=_label_config(),
        quality_payload={
            "quality_status": "QUALITY_REJECTED",
            "candidate_selection": {
                "candidate_status": None,
                "failed_gates": ["collapse_gate"],
                "passed_gates": ["baseline_edge_gate"],
            },
            "quality_gates_summary": {
                "failed_gates": ["collapse_gate"],
                "passed_gates": ["baseline_edge_gate"],
            },
            "gap_quality": {
                "gap_severity": "OK",
                "gap_severity_for_training": "OK",
                "dataset_safe_for_training": True,
            },
            "anti_collapse": {
                "actual_distribution": {"UP": 0.4, "DOWN": 0.3, "FLAT": 0.3},
                "predicted_distribution": {"UP": 0.9, "DOWN": 0.05, "FLAT": 0.05},
            },
            "regime_label_builder_status": {
                "regime_label_builder_status": "built",
                "regime_label_builder_used_in_training": True,
                "regime_specific_training_applied": True,
                "missing_requirements": [],
                "warnings": [],
            },
        },
        class_distribution={},
        gate_policy_summary={},
    )

    assert candidate.candidate_status == "REJECTED"


def test_ml36_1_failed_pipeline_candidate_uses_failed_status() -> None:
    runner = LabelGridExperimentRunner()
    pipeline_result = SimpleNamespace(
        gap_quality_summary={},
        stage_results=(
            SimpleNamespace(stage="model_quality_validation", status="FAILED", data={}),
        ),
    )

    candidate = runner._build_failed_pipeline_candidate_result(
        config=SimpleNamespace(feature_version="fv2"),
        label_config=_label_config(),
        pipeline_result=pipeline_result,
    )

    assert candidate.status == "FAILED"
    assert candidate.candidate_status == "FAILED"
    assert candidate.raw_candidate_status == "FAILED"

