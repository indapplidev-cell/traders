from app.evaluation.model_candidate_selector import ModelCandidateSelector


def test_model_candidate_selector_rejects_bad_candidate() -> None:
    payload = ModelCandidateSelector().select(
        model_version="mv_bad",
        quality_status="QUALITY_REJECTED",
        gap_quality={"gap_severity": "HIGH", "dataset_safe_for_training": False},
        anti_collapse={"collapse_detected": True, "collapse_type": "MIXED_COLLAPSE", "directional_bias_detected": True},
        calibration_status="ACCEPTABLE",
        profit_aware_summary={"gate_results": [{"resolved_signal_count": 50, "total_r": -10.0, "profit_factor": 0.9}]},
        walk_forward_summary={"summary": {"fold_count": 10, "global_total_r": -5.0, "global_profit_factor": 0.95, "total_test_signal_count": 400}},
        gate_policy_replay_summary={"gate_policy_replay_status": "SAMPLE_ONLY"},
        model_accuracy=0.372,
        baseline_accuracy=0.370,
        accuracy_edge=0.002,
    )

    assert payload["candidate_status"] == "CANDIDATE_REJECTED"
    assert payload["approved_for_live_trading"] is False
    assert payload["approved_for_auto_activation"] is False
    assert "collapse_gate" in payload["failed_gates"]


def test_model_candidate_selector_accepts_research_candidate() -> None:
    payload = ModelCandidateSelector().select(
        model_version="mv_good",
        quality_status="QUALITY_APPROVED",
        gap_quality={"gap_severity": "OK", "dataset_safe_for_training": True},
        anti_collapse={"collapse_detected": False, "collapse_type": "NONE"},
        calibration_status="ACCEPTABLE",
        profit_aware_summary={"gate_results": [{"resolved_signal_count": 120, "total_r": 25.0, "profit_factor": 1.2}]},
        walk_forward_summary={"summary": {"fold_count": 8, "global_total_r": 12.0, "global_profit_factor": 1.15, "total_test_signal_count": 220}},
        gate_policy_replay_summary={"gate_policy_replay_status": "ACCEPTABLE"},
        model_accuracy=0.42,
        baseline_accuracy=0.40,
        accuracy_edge=0.02,
    )

    assert payload["candidate_status"] == "CANDIDATE_ACCEPTED_FOR_RESEARCH"
    assert payload["approved_for_live_trading"] is False
    assert payload["approved_for_auto_activation"] is False
