from __future__ import annotations

from typing import Any


DIAGNOSTIC_NAME = "real_quick_quality_rerun_readiness_plan"
DIAGNOSTIC_VERSION = "ml38.10.60"
EXECUTION_MODE = "NO_RUN_RERUN_READINESS_PLAN_NO_QUICK_QUALITY_NO_TRAINING_NO_DB_WRITES"
APPROVED_COMMAND = (
    "python run_fv3_cached_tuning.py --quick-quality --quick-quality-symbol SOLUSDT"
)
REPO_ROOT = r"D:\disk_E\game_projects\traders\traders-ml"
EXTERNAL_LOG_DIR = r"D:\disk_E\game_projects\traders\traders-ml-run-logs"


def build_real_quick_quality_rerun_readiness_plan() -> dict[str, Any]:
    """Build the deterministic ML38.10.60 design; execute and inspect nothing."""
    return {
        "diagnostic_name": DIAGNOSTIC_NAME,
        "diagnostic_version": DIAGNOSTIC_VERSION,
        "execution_mode": EXECUTION_MODE,
        "previous_stage_summary": {
            "previous_stage": "ML38.10.59",
            "previous_commit": "fbaed537e279e65e6377eec38b54105ddc34dc5a",
            "previous_decision": "POST_FIX_FIXTURE_VALIDATION_PASSED_NO_REAL_RUN",
            "fixture_exact_byte_valid": True,
            "fixture_lf_only": True,
            "real_exact_byte_valid_sidecar_available": False,
            "existing_real_sidecars_status": "legacy/fail-closed",
            "cascade_outcome_allowed_before_rerun": False,
        },
        "rerun_scope": {
            "rerun_required_for_real_validation": True,
            "rerun_approved_now": False,
            "allowed_symbol_when_approved": "SOLUSDT",
            "allowed_interval_when_approved": "15m",
            "btc_allowed": False,
            "eth_allowed": False,
            "multisymbol_allowed": False,
            "cascade_outcome_allowed": False,
            "production_like_recompute": False,
            "tradable_edge": False,
            "quick_quality_allowed_without_separate_approval": False,
            "fast_debug_required_before_rerun": False,
            "clean_required_before_rerun": False,
        },
        "approved_command_template": {
            "command": APPROVED_COMMAND,
            "working_directory": REPO_ROOT,
            "expected_runtime_note": "may take multiple hours",
            "no_parent_timeout_shorter_than_expected_runtime": True,
            "external_log_dir": EXTERNAL_LOG_DIR,
            "output_detection": (
                "latest reports/feature_regime_experiments/"
                "quick_quality_fv3_cached_fresh_tuning_solusdt_15m_*"
            ),
        },
        "execution_runbook": {
            "preflight_git_status_clean_required": True,
            "activate_venv": True,
            "run_single_command_only": True,
            "no_clean_fast_sequence": True,
            "no_parent_timeout_shorter_than_expected_runtime": True,
            "print_elapsed_every_minutes": 20,
            "write_external_log": True,
            "write_start_end_timestamps": True,
            "capture_process_exit_code": True,
            "write_completion_marker": True,
            "do_not_commit_runtime_artifacts": True,
            "ordered_steps": [
                "Obtain separate user approval for ML38.10.61.",
                "Require a clean git status and activate the project virtual environment.",
                "Create a timestamped external run directory below the external log directory.",
                "Record UTC and local start timestamps before launching the one approved command.",
                "Launch the Python process directly and retain its process handle without a short parent timeout.",
                "Append stdout and stderr to the external log and report elapsed time every 20 minutes.",
                "Wait for the Python process, capture its actual exit code, and record timeout state explicitly.",
                "Record UTC and local end timestamps, elapsed duration, and a completion marker externally.",
                "Do not commit generated runtime artifacts; begin validation only after completion evidence is durable.",
            ],
        },
        "timeout_exit_code_capture_plan": {
            "controlling_shell_exit_code_must_be_captured": True,
            "python_exit_code_must_be_captured": True,
            "timeout_detected_must_be_recorded": True,
            "child_completed_later_must_not_hide_exit_code": True,
            "fake_zero_exit_code_forbidden": True,
            "unknown_exit_code_policy": "fail-closed",
        },
        "post_run_sidecar_validation_plan": {
            "discover_new_output_dir_after_start_time": True,
            "discover_sidecar_sets": True,
            "select_latest_new_sidecar": True,
            "validate_exact_sha_size": True,
            "validate_lf_only": True,
            "validate_schema_ml38_10_58": True,
            "validate_contract_fields": True,
            "required_contract_fields": [
                "hash_contract",
                "line_ending_contract",
                "byte_size_contract",
                "writer_contract_version",
            ],
            "validate_row_count_6481_or_expected_full_dataset_count": True,
            "validate_splits_train_val_test": True,
            "validate_probabilities_finite": True,
            "validate_prediction_source_model_softmax_argmax": True,
            "validate_no_actual_label_substitution": True,
            "validate_no_direction_label_source": True,
            "validate_symbol_solusdt_only": True,
            "validate_no_btc_eth_multisymbol": True,
        },
        "metadata_truth_validation_plan": {
            "validate_sidecar_runtime_truth_present": True,
            "validate_export_requested_completed_truthful": True,
            "validate_real_full_dataset_stream_created_truthful": True,
            "validate_real_quick_quality_run_executed_truthful_or_unknown": True,
            "validate_unknown_not_false": True,
            "validate_run_exit_code_status": True,
            "stale_wired_not_executed_false_false_must_fail": True,
        },
        "archive_zip_validation_plan": {
            "validate_archive_status_field_present": True,
            "if_zip_created_validate_contains_sidecars": True,
            "if_zip_missing_status_must_be_missing_or_not_requested_or_unknown": True,
            "zip_missing_blocks_archive_validation_not_sidecar_byte_validation": True,
            "no_false_retention_confirmation": True,
            "archive_recovery_not_in_this_stage": True,
        },
        "label_substitution_guardrail": {
            "forbid_actual_label_as_predicted_label": True,
            "forbid_ml_labels_direction_label_as_prediction_source": True,
            "predicted_label_must_come_from_model_prob_argmax": True,
            "label_substitution_blocks_acceptance": True,
        },
        "real_artifact_guardrail": {
            "quick_quality_executed_during_stage": False,
            "training_or_runtime_executed_during_stage": False,
            "db_writes_during_stage": False,
            "ml_labels_writes_during_stage": False,
            "ml_predictions_writes_during_stage": False,
            "existing_real_artifacts_mutated": False,
            "new_real_sidecars_created": False,
            "new_zip_created": False,
            "archive_recovery_performed": False,
            "full_6481_cascade_allowed_now": False,
            "full_6481_outcome_allowed_now": False,
            "production_like_recompute": False,
            "tradable_edge_confirmed": False,
        },
        "decision_gate": {
            "readiness_plan_created": True,
            "real_rerun_executed": False,
            "separate_user_approval_required_for_rerun": True,
            "newly_generated_exact_byte_valid_real_sidecar_available": False,
            "invalid_exact_byte_sidecar_blocks_cascade_outcome": True,
            "stale_or_false_metadata_blocks_cascade_outcome": True,
            "lost_exit_code_blocks_production_like_and_tradable_edge_claims": True,
            "missing_zip_blocks_archive_validation_only": True,
            "valid_sidecar_still_requires_separate_cascade_outcome_stage": True,
            "cascade_outcome_allowed_now": False,
            "production_like_recompute_allowed_now": False,
            "tradable_edge_claim_allowed_now": False,
            "decision": "REAL_QUICK_QUALITY_RERUN_READINESS_PLAN_CREATED_NO_RUN",
            "next_allowed_stage": (
                "ML38.10.61 — separately approved real SOLUSDT quick-quality run "
                "using fixed writer contract"
            ),
        },
        "next_step_plan": [
            "Request separate approval before executing the exact SOLUSDT command.",
            "If approved, execute only under ML38.10.61 with durable external completion evidence.",
            "Validate newly created artifacts fail-closed before proposing any later cascade/outcome stage.",
        ],
        "decision": ["REAL_QUICK_QUALITY_RERUN_READINESS_PLAN_CREATED_NO_RUN"],
    }


real_quick_quality_rerun_readiness_plan = (
    build_real_quick_quality_rerun_readiness_plan()
)
