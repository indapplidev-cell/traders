from app.diagnostics.typeerror_downstream_analyzer_root_cause_audit import (
    typeerror_downstream_analyzer_root_cause_audit as audit,
)


def test_diagnostic_identity_and_previous_failure() -> None:
    assert audit["diagnostic_name"] == "typeerror_downstream_analyzer_root_cause_audit"
    assert audit["execution_mode"] == (
        "NO_RUN_TYPEERROR_ROOT_CAUSE_DIAGNOSTIC_NO_QUICK_QUALITY_NO_ARTIFACT_MUTATION"
    )
    previous = audit["previous_stage_summary"]
    assert previous["previous_stage"] == "ML38.10.62"
    assert previous["previous_decision"] == "WRAPPER_EXECUTION_FAILED"


def test_traceback_and_source_path_are_specific() -> None:
    traceback = audit["traceback_evidence"]
    assert traceback["exception_type"] == "TypeError"
    assert "unhashable type: 'dict'" in traceback["exception_message"]
    assert traceback["traceback_found"] is True
    source = audit["source_path_evidence"]
    assert source["suspect_file"]
    assert source["suspect_function"]
    assert source["source_evidence_confidence"] == "HIGH"
    assert audit["evidence_sources"]["evidence_mode"] == (
        "READ_ONLY_LOG_SOURCE_REPORT_INSPECTION"
    )


def test_root_cause_phase_and_artifact_context() -> None:
    root = audit["root_cause_classification"]
    assert root["root_cause_status"] in {"CONFIRMED", "LIKELY", "INCOMPLETE"}
    assert root["root_cause_class"] == (
        "ROOT_CAUSE_CONFIRMED_NESTED_WARNING_PAYLOAD_NOT_NORMALIZED"
    )
    assert audit["failure_phase_analysis"]["failure_phase"]
    assert audit["artifact_status_context"]["latest_sidecar_exact_byte_valid"] is True
    assert audit["artifact_status_context"]["archive_valid"] is True


def test_decision_and_real_artifact_guardrails_are_fail_closed() -> None:
    gate = audit["decision_gate"]
    assert gate["fix_applied"] is False
    assert gate["rerun_performed"] is False
    assert gate["cascade_outcome_allowed_now"] is False
    assert gate["production_like_recompute_allowed_now"] is False
    assert gate["tradable_edge_claim_allowed_now"] is False
    guard = audit["real_artifact_guardrail"]
    assert guard["quick_quality_rerun_during_stage"] is False
    assert guard["existing_real_artifacts_mutated"] is False
