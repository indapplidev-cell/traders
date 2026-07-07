from __future__ import annotations

from typing import Any


DIAGNOSTIC_NAME = "solusdt_quick_quality_execution_harness_readiness"
DIAGNOSTIC_VERSION = "ml38.10.61"
EXECUTION_MODE = (
    "NO_RUN_EXECUTION_HARNESS_DRY_RUN_NO_QUICK_QUALITY_NO_TRAINING_NO_DB_WRITES"
)
ALLOWED_COMMAND = (
    "python run_fv3_cached_tuning.py --quick-quality --quick-quality-symbol SOLUSDT"
)
EXTERNAL_LOG_DIR = r"D:\disk_E\game_projects\traders\traders-ml-run-logs"


def build_solusdt_quick_quality_execution_harness_readiness() -> dict[str, Any]:
    """Return the deterministic ML38.10.61 no-run harness design."""
    return {
        "diagnostic_name": DIAGNOSTIC_NAME,
        "diagnostic_version": DIAGNOSTIC_VERSION,
        "execution_mode": EXECUTION_MODE,
        "previous_stage_summary": {
            "previous_stage": "ML38.10.60",
            "previous_commit": "cd0e5937d6f7340cfd08642f7642c23390b1e63f",
            "previous_decision": "REAL_QUICK_QUALITY_RERUN_READINESS_PLAN_CREATED_NO_RUN",
            "future_command_prepared_not_executed": True,
            "separate_user_approval_required": True,
        },
        "wrapper_contract": {
            "wrapper_file": "run_solusdt_quick_quality_once.py",
            "default_mode": "dry-run",
            "execute_requires_explicit_flags": True,
            "allowed_command": ALLOWED_COMMAND,
            "allowed_symbol": "SOLUSDT",
            "allowed_interval": "15m",
            "btc_allowed": False,
            "eth_allowed": False,
            "multisymbol_allowed": False,
            "clean_allowed": False,
            "fast_allowed": False,
            "sequence_allowed": False,
            "cascade_outcome_allowed": False,
        },
        "dry_run_behavior": {
            "dry_run_does_not_spawn_subprocess": True,
            "dry_run_prints_command": True,
            "dry_run_prints_log_paths": True,
            "dry_run_prints_safety_constraints": True,
            "dry_run_reports_not_executed": True,
        },
        "execute_mode_safety": {
            "real_execute_not_used_in_this_stage": True,
            "clean_git_required_before_execute": True,
            "no_short_parent_timeout": True,
            "progress_interval_minutes": 20,
            "completion_marker_required": True,
            "external_log_required": True,
            "fake_exit_code_forbidden": True,
        },
        "external_logging_contract": {
            "external_log_dir": EXTERNAL_LOG_DIR,
            "log_inside_repo_reports_allowed": False,
            "timestamped_log_required": True,
            "stdout_stderr_capture_required": True,
            "start_end_timestamps_required": True,
            "completion_marker_json_required": True,
        },
        "exit_code_contract": {
            "child_process_exit_code_captured": True,
            "wrapper_returns_child_exit_code_on_execute": True,
            "unknown_exit_code_policy": "fail-closed",
            "timeout_loss_prevented_by_no_short_parent_timeout": True,
        },
        "command_scope_guardrail": {
            "only_solusdt_quick_quality_command_allowed": True,
            "command_injection_disallowed": True,
            "user_custom_symbols_disallowed": True,
            "btc_eth_multisymbol_disallowed": True,
            "clean_fast_sequence_disallowed": True,
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
            "no_run_harness_created": True,
            "dry_run_validated": True,
            "real_quick_quality_executed": False,
            "separate_user_approval_required_for_execute": True,
            "newly_generated_exact_byte_valid_real_sidecar_available": False,
            "cascade_outcome_allowed_now": False,
            "production_like_recompute_allowed_now": False,
            "tradable_edge_claim_allowed_now": False,
            "decision": "SOLUSDT_QUICK_QUALITY_EXECUTION_HARNESS_READY_NO_RUN",
            "next_allowed_stage": (
                "ML38.10.62 — separately approved real SOLUSDT quick-quality "
                "execution using wrapper"
            ),
        },
        "next_step_plan": [
            "Keep ML38.10.61 no-run and request separate approval for execution.",
            "After approval, invoke the wrapper with both explicit execute flags.",
            "Validate durable completion evidence before any later artifact claims.",
        ],
        "decision": ["SOLUSDT_QUICK_QUALITY_EXECUTION_HARNESS_READY_NO_RUN"],
    }


solusdt_quick_quality_execution_harness_readiness = (
    build_solusdt_quick_quality_execution_harness_readiness()
)
