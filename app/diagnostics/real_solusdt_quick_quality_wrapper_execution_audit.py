from __future__ import annotations

from typing import Any


DIAGNOSTIC_NAME = "real_solusdt_quick_quality_wrapper_execution_audit"
DIAGNOSTIC_VERSION = "ml38.10.62"
EXECUTION_MODE = (
    "REAL_SOLUSDT_QUICK_QUALITY_EXECUTED_USING_WRAPPER_NO_CASCADE_NO_OUTCOME"
)
EXPECTED_COMMAND = (
    "python run_fv3_cached_tuning.py --quick-quality --quick-quality-symbol SOLUSDT"
)
OUTPUT_DIR = (
    "reports/feature_regime_experiments/"
    "quick_quality_fv3_cached_fresh_tuning_solusdt_15m_20260707_035826"
)
SIDECAR_ROOT = (
    OUTPUT_DIR
    + "/per_symbol_experiments/fv3_cached_fresh_tuning_solusdt_15m_20260707_035826/"
    "label_grid_runtime/fv3_cached_fresh_tuning_solusdt_15m_20260707_035826_label_grid/"
    "pipeline_runs/fv3_cached_fresh_tuning_solusdt_15m_20260707_035826_label_grid_"
    "lv36_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_metric_relax_"
    "exit45_probe/prediction_payloads"
)


def build_real_solusdt_quick_quality_wrapper_execution_audit() -> dict[str, Any]:
    """Return the immutable evidence audit for the one approved ML38.10.62 run."""
    stream = SIDECAR_ROOT + "/full_dataset_prediction_stream.jsonl"
    summary = SIDECAR_ROOT + "/full_dataset_prediction_stream_summary.json"
    schema = SIDECAR_ROOT + "/prediction_payload_schema.json"
    return {
        "diagnostic_name": DIAGNOSTIC_NAME,
        "diagnostic_version": DIAGNOSTIC_VERSION,
        "execution_mode": EXECUTION_MODE,
        "previous_stage_summary": {
            "previous_stage": "ML38.10.61",
            "previous_commit": "2bb6addca3c979d8a8b3364035db5b370df11cd6",
            "previous_decision": "SOLUSDT_QUICK_QUALITY_EXECUTION_HARNESS_READY_NO_RUN",
            "wrapper_file": "run_solusdt_quick_quality_once.py",
            "wrapper_default_dry_run_validated": True,
        },
        "wrapper_execution_evidence": {
            "wrapper_used": True,
            "wrapper_execute_used": True,
            "direct_run_fv3_cached_tuning_used": False,
            "command_expected": EXPECTED_COMMAND,
            "command_executed_from_marker_or_log": EXPECTED_COMMAND,
            "wrapper_exit_code": 1,
            "child_exit_code": 1,
            "exit_code_known": True,
            "exit_code_status": "EXIT_CODE_NONZERO",
            "external_log_path": (
                "D:\\disk_E\\game_projects\\traders\\traders-ml-run-logs\\"
                "solusdt_quick_quality_20260707_065819.log"
            ),
            "completion_marker_path": (
                "D:\\disk_E\\game_projects\\traders\\traders-ml-run-logs\\"
                "solusdt_quick_quality_20260707_065819.completion.json"
            ),
            "run_start_local": "2026-07-07T06:58:19.531649+03:00",
            "run_end_local": "2026-07-07T10:40:14.575345+03:00",
            "elapsed_seconds": 13315.047,
            "completion_marker_present": True,
            "failure": "TypeError: unhashable type: 'dict' in multi-symbol analysis",
        },
        "scope_validation": {
            "solusdt_only": True,
            "interval_15m": True,
            "btc_detected": False,
            "eth_detected": False,
            "multisymbol_detected": False,
            "clean_detected": False,
            "fast_debug_detected": False,
            "sequence_detected": False,
            "cascade_outcome_detected": False,
        },
        "output_dir_validation": {
            "output_dir_found": True,
            "output_dir_path": OUTPUT_DIR,
            "output_dir_created_after_run_start": True,
            "output_dir_symbol_scope_valid": True,
        },
        "sidecar_discovery": {
            "sidecar_sets_found": 45,
            "latest_sidecar_stream_path": stream,
            "latest_sidecar_summary_path": summary,
            "latest_sidecar_schema_path": schema,
            "latest_sidecar_selected": True,
        },
        "exact_byte_validation": {
            "stream_file_exists": True,
            "summary_file_exists": True,
            "exact_sha256": "e38b71d1cf862991c57a99479692a6e084d51f44fed7bc9c0778b945d3e1c337",
            "summary_sha256": "e38b71d1cf862991c57a99479692a6e084d51f44fed7bc9c0778b945d3e1c337",
            "exact_size_bytes": 6973344,
            "summary_size_bytes": 6973344,
            "exact_sha256_matches_summary": True,
            "exact_size_matches_summary": True,
            "status": "EXACT_BYTE_VALID",
        },
        "line_ending_validation": {
            "lf_only": True,
            "crlf_count": 0,
            "bare_lf_count": 6481,
            "stray_cr_count": 0,
            "status": "LF_ONLY_VALID",
        },
        "schema_contract_validation": {
            "schema_file_exists": True,
            "schema_version": "ml38.10.58",
            "schema_version_expected": "ml38.10.58",
            "schema_version_valid": True,
            "required_fields_present": True,
        },
        "summary_contract_validation": {
            "hash_contract": "EXACT_BYTES_AFTER_WRITE",
            "line_ending_contract": "LF",
            "byte_size_contract": "EXACT_BYTES_AFTER_WRITE",
            "writer_contract_version": "ml38.10.58",
            "contract_fields_valid": True,
        },
        "runtime_truth_validation": {
            "sidecar_runtime_truth_present": True,
            "export_requested": True,
            "export_completed": True,
            "real_full_dataset_stream_created": True,
            "real_quick_quality_run_executed": None,
            "unknown_facts_not_false": True,
            "stale_wired_not_executed_detected": True,
            "stale_false_false_metadata_detected": True,
            "status": "RUNTIME_TRUTH_VALID",
        },
        "completion_evidence_validation": {
            "completion_marker_present": True,
            "external_log_present": True,
            "wrapper_exit_code_known": True,
            "child_exit_code_known": True,
            "fake_zero_detected": False,
            "short_timeout_loss_detected": False,
            "status": "COMPLETION_EVIDENCE_VALID",
        },
        "archive_zip_validation": {
            "archive_status": "CREATED_BY_WRAPPER_AFTER_COMPACT_PRUNE",
            "zip_found": True,
            "zip_contains_sidecars": True,
            "false_retention_confirmation_detected": False,
            "status": "ARCHIVE_VALID",
            "zip_path": OUTPUT_DIR + ".zip",
            "zip_size_bytes": 24985558,
            "sidecar_entries": 135,
        },
        "label_substitution_guardrail": {
            "actual_label_used_as_predicted_label": False,
            "ml_labels_direction_label_used_as_prediction_source": False,
            "prediction_source_model_softmax_argmax": True,
            "status": "NO_LABEL_SUBSTITUTION_DETECTED",
        },
        "real_artifact_guardrail": {
            "quick_quality_executed_during_stage": True,
            "wrapper_execute_used_during_stage": True,
            "training_or_runtime_executed_during_stage": True,
            "db_manual_writes_during_stage": False,
            "ml_labels_manual_writes_during_stage": False,
            "ml_predictions_manual_writes_during_stage": False,
            "labels_builders_gates_model_logic_changed": False,
            "existing_real_artifacts_mutated": False,
            "new_real_sidecars_created": True,
            "new_zip_created": True,
            "archive_recovery_performed": False,
            "full_6481_cascade_allowed_now": False,
            "full_6481_outcome_allowed_now": False,
            "production_like_recompute": False,
            "tradable_edge_confirmed": False,
        },
        "decision_gate": {
            "real_run_executed_with_wrapper": True,
            "wrapper_exit_code_zero": False,
            "child_exit_code_zero": False,
            "completion_evidence_valid": True,
            "newly_generated_exact_byte_valid_real_sidecar_available": True,
            "runtime_truth_valid": True,
            "label_substitution_absent": True,
            "archive_validation_status": "ARCHIVE_VALID",
            "cascade_outcome_allowed_now": False,
            "production_like_recompute_allowed_now": False,
            "tradable_edge_claim_allowed_now": False,
            "decision": "WRAPPER_EXECUTION_FAILED",
        },
        "next_step_plan": [
            "Keep cascade/outcome blocked.",
            "Do not rerun or repair without a separately approved stage.",
            "Investigate the unhashable warning payload only after separate approval.",
        ],
        "decision": [
            "REAL_SOLUSDT_QUICK_QUALITY_WRAPPER_EXECUTION_FAILED",
            "WRAPPER_EXECUTION_FAILED",
            "REAL_SOLUSDT_QUICK_QUALITY_EXECUTION_AUDIT_FAILED_CASCADE_BLOCKED",
        ],
    }


real_solusdt_quick_quality_wrapper_execution_audit = (
    build_real_solusdt_quick_quality_wrapper_execution_audit()
)
