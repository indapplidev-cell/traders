from __future__ import annotations

from typing import Any


DIAGNOSTIC_NAME = "typeerror_downstream_analyzer_root_cause_audit"
DIAGNOSTIC_VERSION = "ml38.10.63"
EXECUTION_MODE = (
    "NO_RUN_TYPEERROR_ROOT_CAUSE_DIAGNOSTIC_NO_QUICK_QUALITY_NO_ARTIFACT_MUTATION"
)


def build_typeerror_downstream_analyzer_root_cause_audit() -> dict[str, Any]:
    """Return the read-only ML38.10.63 failure-path evidence audit."""
    suspect_file = "app/diagnostics/directional_side_walk_forward_stability.py"
    return {
        "diagnostic_name": DIAGNOSTIC_NAME,
        "diagnostic_version": DIAGNOSTIC_VERSION,
        "execution_mode": EXECUTION_MODE,
        "previous_stage_summary": {
            "previous_stage": "ML38.10.62",
            "previous_commit": "da98f6fa26cac269dee36b0510abf934bb2b0bc4",
            "previous_decision": "WRAPPER_EXECUTION_FAILED",
            "wrapper_exit_code": 1,
            "child_exit_code": 1,
            "fail_reason": "TypeError: unhashable type: 'dict'",
            "sidecar_exact_byte_valid": True,
            "sidecar_lf_only_valid": True,
            "archive_valid": True,
            "cascade_outcome_blocked": True,
        },
        "evidence_sources": {
            "external_log_path": (
                "D:\\disk_E\\game_projects\\traders\\traders-ml-run-logs\\"
                "solusdt_quick_quality_20260707_065819.log"
            ),
            "completion_marker_path": (
                "D:\\disk_E\\game_projects\\traders\\traders-ml-run-logs\\"
                "solusdt_quick_quality_20260707_065819.completion.json"
            ),
            "stage_report_path": (
                "reports/stage_ml38_10_62_real_solusdt_quick_quality_"
                "wrapper_execution_audit_report.md"
            ),
            "snapshot_path": (
                "planning/ml38_10_62_real_solusdt_quick_quality_"
                "wrapper_execution_audit_snapshot_for_chatgpt.md"
            ),
            "source_files_inspected": [
                "app/cli/commands.py",
                "app/experiments/multi_symbol_feature_regime_analyzer.py",
                suspect_file,
                "run_fv3_cached_tuning.py",
            ],
            "evidence_mode": "READ_ONLY_LOG_SOURCE_REPORT_INSPECTION",
        },
        "traceback_evidence": {
            "traceback_found": True,
            "traceback_source": "external_log",
            "exception_type": "TypeError",
            "exception_message": "unhashable type: 'dict'",
            "first_project_frame_file": "app/cli/commands.py",
            "first_project_frame_function": "multi_symbol_feature_regime_analyze_command",
            "first_project_frame_line": 4879,
            "failing_project_frame_file": suspect_file,
            "failing_project_frame_function": "_candidate_row",
            "failing_project_frame_line": 299,
            "failing_operation_summary": (
                "dict.fromkeys() hashes combined walk-forward warning entries; "
                "the first compact-pruned warning entry is a dict"
            ),
            "traceback_excerpt_line_count": 6,
            "traceback_excerpt_sanitized": True,
        },
        "source_path_evidence": {
            "suspect_file": suspect_file,
            "suspect_function": "DirectionalSideWalkForwardStabilityAnalyzer._candidate_row",
            "suspect_line_or_region": "298-303 (failing call at line 299)",
            "suspect_operation": "list(dict.fromkeys(warning_entries))",
            "suspect_payload_field": (
                "candidate_results.sample[0].walk_forward_profit_diagnostics."
                "walk_forward_stability_warnings"
            ),
            "why_dict_is_unhashable": (
                "compact pruning replaced a warning list with a metadata dict; this "
                "analyzer's _as_list wraps unknown dicts as [dict], then dict.fromkeys "
                "attempts to use that mutable dict as a key"
            ),
            "source_evidence_confidence": "HIGH",
            "code_change_applied": False,
        },
        "root_cause_classification": {
            "root_cause_status": "CONFIRMED",
            "root_cause_class": "ROOT_CAUSE_CONFIRMED_NESTED_WARNING_PAYLOAD_NOT_NORMALIZED",
            "dict_payload_origin": (
                "compact-pruned walk_forward_stability_warnings for SOLUSDT candidate "
                "lv19_h12_tts_thr065_sqmask060"
            ),
            "dict_payload_should_be_normalized_before_hashing": True,
            "likely_fix_type": (
                "decode the compact-pruned warning placeholder to its string sample "
                "before dict.fromkeys uniqueness processing"
            ),
            "requires_model_logic_change": False,
            "requires_label_gate_change": False,
        },
        "failure_phase_analysis": {
            "failure_phase": "DURING_MULTI_SYMBOL_ANALYSIS_FOR_SINGLE_SOLUSDT",
            "sidecar_export_completed_before_failure": True,
            "archive_created_before_failure": False,
            "archive_created_after_failure": True,
            "downstream_analysis_failed_after_artifact_generation": True,
            "multi_symbol_named_analyzer_called_for_single_solusdt": True,
            "failure_blocks_wrapper_success": True,
            "failure_blocks_only_downstream_analysis_report_aggregation": True,
            "failure_invalidates_cascade_outcome": True,
            "failure_invalidates_sidecar_bytes": False,
        },
        "artifact_status_context": {
            "sidecar_sets_found": 45,
            "latest_sidecar_exact_byte_valid": True,
            "latest_sidecar_lf_only_valid": True,
            "schema_ml38_10_58_valid": True,
            "summary_contract_valid": True,
            "runtime_truth_valid": True,
            "completion_evidence_valid": True,
            "archive_valid": True,
            "label_substitution_detected": False,
        },
        "fail_closed_decision_context": {
            "wrapper_child_exit_nonzero": True,
            "sidecar_valid_but_stage_failed": True,
            "cascade_outcome_allowed_now": False,
            "production_like_recompute_allowed_now": False,
            "tradable_edge_claim_allowed_now": False,
            "rerun_allowed_now": False,
        },
        "minimal_fix_plan": {
            "fix_not_applied_in_this_stage": True,
            "proposed_fix_scope": "downstream analyzer/report aggregation only",
            "proposed_fix_principle": (
                "make compact-pruned nested warning payloads hash-safe before "
                "uniqueness/grouping/sorting"
            ),
            "expected_files_to_change": [suspect_file],
            "expected_tests_to_add": [
                "synthetic compact-pruned dict warning payload regression test"
            ],
            "no_label_gate_model_changes_required": True,
            "rerun_required_after_fix": True,
            "rerun_requires_separate_approval": True,
        },
        "real_artifact_guardrail": {
            "quick_quality_rerun_during_stage": False,
            "wrapper_execute_used_during_stage": False,
            "training_or_runtime_executed_during_stage": False,
            "db_writes_during_stage": False,
            "ml_labels_writes_during_stage": False,
            "ml_predictions_writes_during_stage": False,
            "labels_builders_gates_model_logic_changed": False,
            "existing_real_artifacts_mutated": False,
            "new_real_sidecars_created": False,
            "new_zip_created": False,
            "archive_recovery_performed": False,
            "cascade_outcome_run": False,
            "production_like_recompute": False,
            "tradable_edge_confirmed": False,
        },
        "decision_gate": {
            "root_cause_diagnostic_completed": True,
            "root_cause_confirmed_or_likely": True,
            "fix_applied": False,
            "rerun_performed": False,
            "cascade_outcome_allowed_now": False,
            "production_like_recompute_allowed_now": False,
            "tradable_edge_claim_allowed_now": False,
            "decision": "TYPEERROR_ROOT_CAUSE_CONFIRMED_NO_FIX_NO_RERUN",
            "next_allowed_stage": (
                "ML38.10.64 — minimal no-run TypeError fix implementation with "
                "synthetic regression tests"
            ),
        },
        "next_step_plan": [
            "Keep cascade/outcome, production-like recompute, and edge claims blocked.",
            "Implement only the downstream compact-warning normalization in ML38.10.64.",
            "Add a synthetic regression test; rerun only with separate approval.",
        ],
        "decision": [
            "TYPEERROR_ROOT_CAUSE_CONFIRMED_NO_FIX_NO_RERUN",
            "WRAPPER_EXECUTION_REMAINS_FAILED",
            "CASCADE_OUTCOME_REMAINS_BLOCKED",
        ],
    }


typeerror_downstream_analyzer_root_cause_audit = (
    build_typeerror_downstream_analyzer_root_cause_audit()
)
