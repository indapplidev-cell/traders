from app.diagnostics.real_solusdt_quick_quality_wrapper_execution_audit import (
    EXPECTED_COMMAND,
    real_solusdt_quick_quality_wrapper_execution_audit as audit,
)


def test_identity_and_wrapper_execution_evidence() -> None:
    assert audit["diagnostic_name"] == "real_solusdt_quick_quality_wrapper_execution_audit"
    assert audit["diagnostic_version"] == "ml38.10.62"
    assert audit["execution_mode"] == (
        "REAL_SOLUSDT_QUICK_QUALITY_EXECUTED_USING_WRAPPER_NO_CASCADE_NO_OUTCOME"
    )
    evidence = audit["wrapper_execution_evidence"]
    assert evidence["wrapper_used"] is True
    assert evidence["wrapper_execute_used"] is True
    assert evidence["direct_run_fv3_cached_tuning_used"] is False
    assert evidence["command_expected"] == EXPECTED_COMMAND
    assert EXPECTED_COMMAND == (
        "python run_fv3_cached_tuning.py --quick-quality --quick-quality-symbol SOLUSDT"
    )
    assert evidence["wrapper_exit_code"] == evidence["child_exit_code"] == 1
    for key in ("external_log_path", "completion_marker_path", "elapsed_seconds"):
        assert evidence[key]


def test_scope_is_solusdt_only_without_forbidden_modes() -> None:
    scope = audit["scope_validation"]
    assert scope["solusdt_only"] is True
    assert scope["interval_15m"] is True
    for key in (
        "btc_detected", "eth_detected", "multisymbol_detected", "clean_detected",
        "fast_debug_detected", "sequence_detected", "cascade_outcome_detected",
    ):
        assert scope[key] is False


def test_sidecar_contract_fields_and_validations() -> None:
    assert audit["sidecar_discovery"]["sidecar_sets_found"] == 45
    exact = audit["exact_byte_validation"]
    for key in (
        "exact_sha256", "summary_sha256", "exact_size_bytes", "summary_size_bytes",
        "exact_sha256_matches_summary", "exact_size_matches_summary", "status",
    ):
        assert key in exact
    assert exact["status"] == "EXACT_BYTE_VALID"
    line = audit["line_ending_validation"]
    assert line["lf_only"] is True and line["status"] == "LF_ONLY_VALID"
    schema = audit["schema_contract_validation"]
    assert schema["schema_version"] == schema["schema_version_expected"] == "ml38.10.58"
    assert schema["required_fields_present"] is True
    summary = audit["summary_contract_validation"]
    for key in ("hash_contract", "line_ending_contract", "byte_size_contract", "writer_contract_version"):
        assert summary[key]


def test_runtime_completion_archive_and_label_guardrails() -> None:
    runtime = audit["runtime_truth_validation"]
    for key in ("sidecar_runtime_truth_present", "export_requested", "export_completed", "real_full_dataset_stream_created"):
        assert runtime[key] is True
    assert runtime["unknown_facts_not_false"] is True
    assert runtime["stale_wired_not_executed_detected"] is True
    completion = audit["completion_evidence_validation"]
    assert completion["status"] == "COMPLETION_EVIDENCE_VALID"
    archive = audit["archive_zip_validation"]
    assert archive["zip_found"] is True and archive["zip_contains_sidecars"] is True
    labels = audit["label_substitution_guardrail"]
    assert labels["actual_label_used_as_predicted_label"] is False
    assert labels["ml_labels_direction_label_used_as_prediction_source"] is False
    assert labels["prediction_source_model_softmax_argmax"] is True


def test_failure_decision_keeps_all_later_claims_blocked() -> None:
    gate = audit["decision_gate"]
    assert gate["decision"] == "WRAPPER_EXECUTION_FAILED"
    assert gate["wrapper_exit_code_zero"] is False
    assert gate["child_exit_code_zero"] is False
    assert gate["cascade_outcome_allowed_now"] is False
    assert gate["production_like_recompute_allowed_now"] is False
    assert gate["tradable_edge_claim_allowed_now"] is False
