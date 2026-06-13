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


def test_ml36_2_critical_gap_forces_final_rejection() -> None:
    runner = LabelGridExperimentRunner()
    candidate = runner._build_candidate_result(
        label_config=_label_config(),
        quality_payload={
            "quality_status": "QUALITY_REJECTED",
            "candidate_selection": {
                "candidate_status": "CANDIDATE_ACCEPTED_FOR_RESEARCH",
                "failed_gates": None,
                "passed_gates": None,
            },
            "quality_gates_summary": {
                "failed_gates": None,
                "passed_gates": None,
            },
            "gap_quality": {
                "gap_severity": "CRITICAL",
                "gap_severity_for_training": "CRITICAL",
                "dataset_safe_for_training": False,
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
    assert "gap_quality_gate" in candidate.failed_gates
