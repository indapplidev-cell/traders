from app.diagnostics.model_quality_post_fix_solusdt_triage import (
    model_quality_post_fix_solusdt_triage as triage,
)


def test_identity_and_previous_stage_contract() -> None:
    assert triage["diagnostic_name"] == "model_quality_post_fix_solusdt_triage"
    assert triage["diagnostic_version"] == "ml38.10.66"
    assert triage["execution_mode"] == (
        "READ_ONLY_POST_FIX_SOLUSDT_QUALITY_TRIAGE_NO_TRAINING_NO_RERUN"
    )
    previous = triage["previous_stage_summary"]
    assert previous["previous_stage"] == "ML38.10.65"
    assert previous["previous_decision"] == (
        "POST_FIX_SOLUSDT_QUICK_QUALITY_RERUN_PASSED"
    )
    assert previous["wrapper_exit_code"] == 0
    assert previous["child_exit_code"] == 0
    assert previous["typeerror_repeated"] is False


def test_candidate_and_sidecar_counts_are_exact() -> None:
    status = triage["candidate_status_summary"]
    assert status["total_candidates"] == 46
    assert status["rejected_candidates"] == 45
    assert status["failed_candidates"] == 1
    assert status["unknown_candidates"] == 0
    sidecar = triage["sidecar_context"]
    assert sidecar["sidecar_sets_valid"] == 45
    assert sidecar["latest_sidecar_sha256"] == (
        "5ef2a0492f33686e5885fe9d2128bf223df8d4b7c0f0939fd3486f0d8100f3c4"
    )


def test_failed_candidate_is_not_the_fixed_typeerror() -> None:
    failed = triage["failed_candidate_analysis"]
    assert failed["failed_candidate_found"] is True
    assert failed["failed_phase"] == "train_model"
    assert failed["failed_is_typeerror_repeat"] is False
    assert failed["failed_is_sidecar_export_failure"] is True
    assert "6485" in failed["failed_reason"]
    assert "6481" in failed["failed_reason"]


def test_guardrails_and_decision_are_fail_closed() -> None:
    guardrails = triage["guardrails"]
    assert guardrails["quick_quality_rerun_during_stage"] is False
    assert guardrails["training_or_runtime_executed_during_stage"] is False
    assert guardrails["existing_real_artifacts_mutated"] is False
    assert guardrails["new_real_sidecars_created"] is False
    assert guardrails["new_zip_created"] is False
    gate = triage["decision_gate"]
    assert gate["cascade_outcome_allowed_now"] is False
    assert gate["production_like_recompute_allowed_now"] is False
    assert gate["tradable_edge_claim_allowed_now"] is False


def test_next_action_uses_allowed_enum() -> None:
    allowed = {
        "LABEL_THRESHOLD_TUNING",
        "CANDIDATE_GATE_TUNING",
        "WALK_FORWARD_STABILITY_TUNING",
        "CALIBRATION_TUNING",
        "FEATURE_CONTEXT_TUNING",
        "FAILURE_FIX_FIRST",
        "MULTI_SYMBOL_CONFIRMATION",
        "UNKNOWN_NEEDS_MANUAL_REVIEW",
    }
    action = triage["next_training_quality_action"]
    assert action
    assert action["action_type"] in allowed
    assert action["recommended_stage"] == "ML38.10.67"
    assert action["still_blocks_cascade_outcome"] is True
    assert action["still_blocks_tradable_edge_claim"] is True
