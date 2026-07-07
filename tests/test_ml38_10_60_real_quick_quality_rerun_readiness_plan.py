from app.diagnostics.real_quick_quality_rerun_readiness_plan import (
    APPROVED_COMMAND,
    EXECUTION_MODE,
    build_real_quick_quality_rerun_readiness_plan,
    real_quick_quality_rerun_readiness_plan,
)


def test_diagnostic_identity_command_and_scope() -> None:
    plan = build_real_quick_quality_rerun_readiness_plan()
    assert plan["diagnostic_name"] == "real_quick_quality_rerun_readiness_plan"
    assert plan["execution_mode"] == EXECUTION_MODE
    assert plan["approved_command_template"]["command"] == APPROVED_COMMAND
    assert APPROVED_COMMAND == (
        "python run_fv3_cached_tuning.py --quick-quality --quick-quality-symbol SOLUSDT"
    )
    scope = plan["rerun_scope"]
    assert scope["rerun_approved_now"] is False
    assert scope["allowed_symbol_when_approved"] == "SOLUSDT"
    assert scope["allowed_interval_when_approved"] == "15m"
    assert scope["btc_allowed"] is False
    assert scope["eth_allowed"] is False
    assert scope["multisymbol_allowed"] is False
    assert scope["fast_debug_required_before_rerun"] is False
    assert scope["clean_required_before_rerun"] is False
    assert not any(word in APPROVED_COMMAND for word in ("--fast-debug", "clean_traders_ml", "run_clean_fast_quick_sequence"))


def test_external_runbook_preserves_completion_evidence() -> None:
    plan = real_quick_quality_rerun_readiness_plan
    command = plan["approved_command_template"]
    runbook = plan["execution_runbook"]
    timeout = plan["timeout_exit_code_capture_plan"]
    assert "reports" not in command["external_log_dir"].lower()
    assert not command["external_log_dir"].startswith(command["working_directory"] + "\\")
    assert command["no_parent_timeout_shorter_than_expected_runtime"] is True
    assert runbook["no_parent_timeout_shorter_than_expected_runtime"] is True
    assert runbook["capture_process_exit_code"] is True
    assert runbook["write_completion_marker"] is True
    assert runbook["write_start_end_timestamps"] is True
    assert timeout["python_exit_code_must_be_captured"] is True
    assert timeout["unknown_exit_code_policy"] == "fail-closed"


def test_post_run_contract_metadata_archive_and_label_checks() -> None:
    plan = real_quick_quality_rerun_readiness_plan
    sidecar = plan["post_run_sidecar_validation_plan"]
    assert sidecar["validate_exact_sha_size"] is True
    assert sidecar["validate_lf_only"] is True
    assert sidecar["validate_schema_ml38_10_58"] is True
    assert sidecar["validate_contract_fields"] is True
    assert set(sidecar["required_contract_fields"]) == {
        "hash_contract", "line_ending_contract", "byte_size_contract", "writer_contract_version"
    }
    metadata = plan["metadata_truth_validation_plan"]
    assert metadata["validate_sidecar_runtime_truth_present"] is True
    assert metadata["stale_wired_not_executed_false_false_must_fail"] is True
    labels = plan["label_substitution_guardrail"]
    assert labels["forbid_actual_label_as_predicted_label"] is True
    assert labels["forbid_ml_labels_direction_label_as_prediction_source"] is True
    assert labels["predicted_label_must_come_from_model_prob_argmax"] is True
    archive = plan["archive_zip_validation_plan"]
    assert archive["no_false_retention_confirmation"] is True


def test_no_run_guardrail_and_fail_closed_gate() -> None:
    plan = real_quick_quality_rerun_readiness_plan
    guardrail = plan["real_artifact_guardrail"]
    assert guardrail["quick_quality_executed_during_stage"] is False
    assert guardrail["training_or_runtime_executed_during_stage"] is False
    assert guardrail["new_real_sidecars_created"] is False
    assert guardrail["new_zip_created"] is False
    gate = plan["decision_gate"]
    assert gate["separate_user_approval_required_for_rerun"] is True
    assert gate["cascade_outcome_allowed_now"] is False
    assert gate["production_like_recompute_allowed_now"] is False
    assert gate["tradable_edge_claim_allowed_now"] is False
    assert gate["decision"] == "REAL_QUICK_QUALITY_RERUN_READINESS_PLAN_CREATED_NO_RUN"
