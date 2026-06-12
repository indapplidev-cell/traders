from app.evaluation.model_candidate_selector import ModelCandidateSelector


def test_candidate_selector_uses_training_safe_gap_fields_for_trailing_only_gaps() -> None:
    payload = ModelCandidateSelector().select(
        model_version="mv_gap_safe",
        quality_status="QUALITY_APPROVED",
        gap_quality={
            "gap_severity": "HIGH",
            "gap_severity_for_training": "OK",
            "effective_gap_count_for_training": 0,
            "dataset_safe_for_training": True,
        },
        anti_collapse={"collapse_detected": False, "collapse_type": "NONE"},
        calibration_status="ACCEPTABLE",
        profit_aware_summary={"gate_results": [{"resolved_signal_count": 120, "total_r": 25.0, "profit_factor": 1.2}]},
        walk_forward_summary={"summary": {"fold_count": 8, "global_total_r": 12.0, "global_profit_factor": 1.15, "total_test_signal_count": 220}},
        gate_policy_replay_summary={"gate_policy_replay_status": "ACCEPTABLE"},
        model_accuracy=0.42,
        baseline_accuracy=0.40,
        accuracy_edge=0.02,
    )

    assert "gap_quality_gate" in payload["passed_gates"]


def test_candidate_selector_still_fails_real_historical_high_gap() -> None:
    payload = ModelCandidateSelector().select(
        model_version="mv_gap_bad",
        quality_status="QUALITY_REJECTED",
        gap_quality={
            "gap_severity": "HIGH",
            "gap_severity_for_training": "HIGH",
            "effective_gap_count_for_training": 20,
            "dataset_safe_for_training": False,
        },
        anti_collapse={"collapse_detected": False, "collapse_type": "NONE"},
        calibration_status="ACCEPTABLE",
        profit_aware_summary={"gate_results": [{"resolved_signal_count": 120, "total_r": 25.0, "profit_factor": 1.2}]},
        walk_forward_summary={"summary": {"fold_count": 8, "global_total_r": 12.0, "global_profit_factor": 1.15, "total_test_signal_count": 220}},
        gate_policy_replay_summary={"gate_policy_replay_status": "ACCEPTABLE"},
        model_accuracy=0.42,
        baseline_accuracy=0.40,
        accuracy_edge=0.02,
    )

    assert "gap_quality_gate" in payload["failed_gates"]
