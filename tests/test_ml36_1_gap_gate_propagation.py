from app.experiments.label_grid_experiment_runner import LabelGridExperimentRunner
from app.labels.label_quality_grid import LabelQualityGridConfig


def test_ml36_1_critical_gap_rejects_candidate_and_marks_gap_gate_failed() -> None:
    runner = LabelGridExperimentRunner()
    label_config = LabelQualityGridConfig(
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
    candidate = runner._build_candidate_result(
        label_config=label_config,
        quality_payload={
            "quality_status": "QUALITY_APPROVED",
            "model_version": "mv",
            "training_run_id": "run",
            "dataset_rows": 2400,
            "train_rows": 1600,
            "val_rows": 400,
            "test_rows": 400,
            "model_accuracy": 0.44,
            "baseline_accuracy": 0.40,
            "accuracy_edge": 0.04,
            "gap_quality": {
                "gap_severity": "CRITICAL",
                "gap_severity_for_training": "CRITICAL",
                "gap_count": 3,
                "effective_gap_count_for_training": 3,
                "dataset_safe_for_training": False,
            },
            "anti_collapse": {
                "actual_distribution": {"UP": 0.34, "DOWN": 0.33, "FLAT": 0.33},
                "predicted_distribution": {"UP": 0.34, "DOWN": 0.33, "FLAT": 0.33},
            },
            "candidate_selection": {
                "candidate_status": "CANDIDATE_ACCEPTED_FOR_RESEARCH",
                "failed_gates": [],
                "passed_gates": [
                    "baseline_edge_gate",
                    "collapse_gate",
                    "profit_aware_gate",
                    "walk_forward_gate",
                    "gap_quality_gate",
                ],
            },
            "quality_gates_summary": {"failed_gates": [], "passed_gates": []},
            "regime_label_builder_status": {
                "regime_label_builder_status": "built",
                "regime_label_builder_used_in_training": True,
                "regime_specific_training_applied": True,
                "missing_requirements": [],
                "warnings": [],
            },
        },
        class_distribution={"UP": 100, "DOWN": 80, "FLAT": 60},
        gate_policy_summary={},
    )

    assert candidate.candidate_status == "REJECTED"
    assert "gap_quality_gate" in candidate.failed_gates
    assert candidate.gap_severity_for_training == "CRITICAL"
    assert candidate.gap_training_safe is False

