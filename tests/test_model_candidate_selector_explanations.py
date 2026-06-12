from app.evaluation.model_candidate_selector import ModelCandidateSelector


def test_model_candidate_selector_exposes_failed_gate_explanations_and_thresholds() -> None:
    payload = ModelCandidateSelector().select(
        model_version="mv_explain",
        quality_status="QUALITY_REJECTED",
        gap_quality={"gap_severity": "HIGH", "dataset_safe_for_training": False},
        anti_collapse={
            "collapse_detected": False,
            "collapse_type": "NONE",
            "predicted_distribution": {"UP": 0.82, "DOWN": 0.08, "FLAT": 0.10},
            "actual_distribution": {"UP": 0.35, "DOWN": 0.42, "FLAT": 0.23},
        },
        calibration_status="ACCEPTABLE",
        profit_aware_summary={"gate_results": [{"resolved_signal_count": 12, "total_r": -1.0, "profit_factor": 0.97}]},
        walk_forward_summary={"summary": {"fold_count": 8, "global_total_r": -2.0, "global_profit_factor": 0.99, "total_test_signal_count": 240}},
        gate_policy_replay_summary={"gate_policy_replay_status": "SAMPLE_ONLY"},
        model_accuracy=0.374,
        baseline_accuracy=0.370,
        accuracy_edge=0.004,
    )

    assert payload["candidate_status"] == "CANDIDATE_REJECTED"
    assert payload["thresholds"]["min_accuracy_edge"] == 0.005
    assert payload["failed_gate_explanations"]["baseline_edge_gate"].startswith("baseline_edge_gate failed")
    assert payload["failed_gate_explanations"]["collapse_gate"] == (
        "collapse_gate failed because max_predicted_class_share > threshold"
    )
    assert payload["failed_gate_explanations"]["gap_quality_gate"].startswith("gap_quality_gate failed")


def test_model_candidate_selector_detects_low_down_share_explanation() -> None:
    payload = ModelCandidateSelector().select(
        model_version="mv_down_share",
        quality_status="QUALITY_REJECTED",
        gap_quality={"gap_severity": "OK", "dataset_safe_for_training": True},
        anti_collapse={
            "collapse_detected": False,
            "collapse_type": "NONE",
            "predicted_distribution": {"UP": 0.60, "DOWN": 0.10, "FLAT": 0.30},
            "actual_distribution": {"UP": 0.30, "DOWN": 0.40, "FLAT": 0.30},
        },
        calibration_status="ACCEPTABLE",
        profit_aware_summary={"gate_results": [{"resolved_signal_count": 30, "total_r": 3.0, "profit_factor": 1.10}]},
        walk_forward_summary={"summary": {"fold_count": 8, "global_total_r": 4.0, "global_profit_factor": 1.03, "total_test_signal_count": 280}},
        gate_policy_replay_summary={"gate_policy_replay_status": "ACCEPTABLE"},
        model_accuracy=0.410,
        baseline_accuracy=0.401,
        accuracy_edge=0.009,
    )

    assert payload["failed_gate_explanations"]["collapse_gate"] == (
        "collapse_gate failed because DOWN prediction share is too small for the actual DOWN share"
    )
