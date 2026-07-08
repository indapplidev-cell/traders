from app.diagnostics.post_field_contract_rerun_readiness import (
    post_field_contract_rerun_readiness as diagnostic,
)


def test_identity_and_previous_stage_evidence() -> None:
    assert diagnostic["diagnostic_name"] == "post_field_contract_rerun_readiness"
    assert diagnostic["diagnostic_version"] == "ml38.10.70"
    assert diagnostic["execution_mode"] == "READINESS_NO_RUN_NO_WRAPPER_NO_QUICK_QUALITY"
    previous = diagnostic["previous_stage_summary"]
    assert previous["previous_stage"] == "ML38.10.69"
    assert previous["previous_decision"] == "SIDECAR_FIELD_CONTRACT_IMPLEMENTED_TESTED_NO_REAL_RUN"
    assert previous["previous_full_pytest"].startswith("1160 passed")


def test_ml38_10_69_field_contract_is_complete_and_layers_are_separate() -> None:
    evidence = diagnostic["ml38_10_69_contract_evidence"]
    assert evidence["field_contract_version"] == "ml38.10.69"
    assert evidence["raw_probabilities_present_in_future_sidecar_contract"] is True
    assert evidence["calibrated_probabilities_present_in_future_sidecar_contract"] is True
    assert evidence["actual_label_present_in_future_sidecar_contract"] is True
    assert evidence["actual_label_source"] == "source_row.direction_label"
    assert evidence["row_alignment_key_present"] is True
    assert evidence["prediction_layers_present"] is True
    assert evidence["prediction_layers"] == ["raw", "calibrated", "sidecar_selected"]
    assert evidence["downstream_policy_available_in_writer"] is False
    assert evidence["downstream_policy_not_conflated_with_sidecar_argmax"] is True


def test_static_probe_fix_preserves_prediction_source() -> None:
    evidence = diagnostic["static_probe_fix_evidence"]
    assert evidence["ml38_10_55_probe_updated"] is True
    assert evidence["actual_label_export_allowed_by_field_contract"] is True
    assert evidence["actual_label_used_for_prediction"] is False
    assert evidence["label_substitution_detected"] is False
    assert evidence["prediction_label_source"] == "probability_argmax"


def test_wrapper_and_future_scope_require_separate_approval() -> None:
    wrapper = diagnostic["wrapper_readiness"]
    assert wrapper["wrapper_file_present"] is True
    assert wrapper["wrapper_requires_execute_flag"] is True
    assert wrapper["wrapper_requires_i_understand_flag"] is True
    assert wrapper["wrapper_targets_solusdt_quick_quality_only"] is True
    assert wrapper["wrapper_run_during_readiness"] is False
    assert wrapper["quick_quality_run_during_readiness"] is False
    scope = diagnostic["expected_next_real_run_scope"]
    assert scope["next_real_run_requires_separate_user_approval"] is True
    assert scope["allowed_scope_after_approval"] == "one SOLUSDT quick-quality wrapper run only"
    assert scope["actual_real_run_authorized_now"] is False


def test_h08_and_dirty_worktree_are_assessed_without_mutation() -> None:
    h08 = diagnostic["h08_risk_assessment"]
    assert h08["h08_known_issue_present"] is True
    assert h08["h08_candidate_boundary_total"] == 6485
    assert h08["h08_expected_global_denominator"] == 6481
    assert h08["h08_fix_applied"] is False
    assert h08["h08_blocks_readiness"] is False
    dirty = diagnostic["dirty_worktree_policy"]
    assert dirty["worktree_dirty_expected"] is True
    assert dirty["commit_required_before_real_run"] == "USER_DECISION"
    assert dirty["unexpected_runtime_artifacts_detected"] is False
    assert diagnostic["readiness_gate"]["h08_assessed"] is True


def test_readiness_and_decision_gates_are_no_run() -> None:
    gate = diagnostic["readiness_gate"]
    assert gate["real_run_not_executed"] is True
    assert gate["next_run_requires_separate_approval"] is True
    assert gate["ready_for_separately_approved_rerun"] is True
    decision = diagnostic["decision_gate"]
    assert decision["real_run_authorized_now"] is False
    assert decision["decision"] == "READY_FOR_SEPARATELY_APPROVED_SOLUSDT_QUICK_QUALITY_RERUN"


def test_guardrails_exclude_runtime_writes_and_policy_changes() -> None:
    guardrails = diagnostic["guardrails"]
    for key in (
        "training_run_during_readiness", "wrapper_execute_used_during_readiness",
        "quick_quality_rerun_during_readiness", "run_fv3_cached_tuning_used_during_readiness",
        "db_writes_during_readiness", "ml_labels_writes_during_readiness",
        "ml_predictions_writes_during_readiness", "existing_real_artifacts_mutated",
        "new_real_sidecars_created", "new_zip_created", "cascade_outcome_run",
        "production_like_recompute", "tradable_edge_confirmed", "commit_performed",
        "planning_update_performed", "snapshot_performed",
    ):
        assert guardrails[key] is False
