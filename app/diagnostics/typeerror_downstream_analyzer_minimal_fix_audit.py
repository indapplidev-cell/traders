from __future__ import annotations

from typing import Any


def build_typeerror_downstream_analyzer_minimal_fix_audit() -> dict[str, Any]:
    return {
        "diagnostic_name": "typeerror_downstream_analyzer_minimal_fix_audit",
        "diagnostic_version": "ml38.10.64",
        "execution_mode": "NO_RUN_TYPEERROR_MINIMAL_FIX_SYNTHETIC_TESTS_NO_QUICK_QUALITY",
        "previous_stage_summary": {
            "previous_stage": "ML38.10.63",
            "previous_commit": "f6a8785ce578cc62983810899a750857117a9bf9",
            "previous_decision": "TYPEERROR_ROOT_CAUSE_CONFIRMED_NO_FIX_NO_RERUN",
            "root_cause": (
                "compact-pruned dict from walk_forward_stability_warnings reaches "
                "dict.fromkeys"
            ),
            "suspect_file": "app/diagnostics/directional_side_walk_forward_stability.py",
            "suspect_function": (
                "DirectionalSideWalkForwardStabilityAnalyzer._candidate_row"
            ),
        },
        "fix_scope": {
            "fix_applied": True,
            "fix_scope": "downstream analyzer/report aggregation only",
            "labels_changed": False,
            "gates_changed": False,
            "model_logic_changed": False,
            "wrapper_rerun": False,
            "quick_quality_rerun": False,
            "real_artifacts_mutated": False,
        },
        "implementation_summary": {
            "fixed_file": "app/diagnostics/directional_side_walk_forward_stability.py",
            "fixed_function": "DirectionalSideWalkForwardStabilityAnalyzer._candidate_row",
            "helper_added_or_updated": True,
            "helper_purpose": (
                "normalize nested warning payload before hash-based uniqueness"
            ),
            "failing_operation_protected": "dict.fromkeys",
            "compact_pruned_dict_supported": True,
            "ordering_preserved": True,
            "duplicates_deduplicated": True,
        },
        "regression_test_summary": {
            "synthetic_compact_dict_payload_tested": True,
            "duplicate_dict_payload_tested": True,
            "string_warning_behavior_preserved": True,
            "mixed_warning_payload_tested": True,
            "real_artifacts_used": False,
            "db_required": False,
        },
        "artifact_guardrail": {
            "wrapper_execute_used_during_stage": False,
            "quick_quality_rerun_during_stage": False,
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
            "minimal_fix_implemented": True,
            "synthetic_regression_tests_added": True,
            "root_cause_path_covered_by_test": True,
            "rerun_performed": False,
            "cascade_outcome_allowed_now": False,
            "production_like_recompute_allowed_now": False,
            "tradable_edge_claim_allowed_now": False,
            "decision": "TYPEERROR_MINIMAL_FIX_IMPLEMENTED_NO_RERUN_SYNTHETIC_TESTED",
            "next_allowed_stage": (
                "ML38.10.65 — no-run post-fix validation audit, or separately "
                "approved wrapper rerun planning"
            ),
        },
        "next_step_plan": [
            "Keep cascade/outcome and production-like recompute blocked.",
            "Proceed only to ML38.10.65 or separately approved wrapper rerun planning.",
        ],
        "decision": [
            "TYPEERROR_MINIMAL_FIX_IMPLEMENTED_NO_RERUN_SYNTHETIC_TESTED"
        ],
    }


typeerror_downstream_analyzer_minimal_fix_audit = (
    build_typeerror_downstream_analyzer_minimal_fix_audit()
)
