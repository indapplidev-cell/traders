from __future__ import annotations

from typing import Any

from app.experiments.prediction_sidecar_exporter import (
    BYTE_SIZE_CONTRACT,
    HASH_CONTRACT,
    LINE_ENDING_CONTRACT,
    WRITER_CONTRACT_VERSION,
    build_archive_status_metadata,
    build_timeout_exit_code_metadata,
)


EXECUTION_MODE = "CODE_CONTRACT_FIX_NO_QUICK_QUALITY_NO_TRAINING_NO_DB_WRITES"


def build_sidecar_writer_metadata_archive_contract_fix_plan() -> dict[str, Any]:
    return {
        "diagnostic_name": "sidecar_writer_metadata_archive_contract_fix_plan",
        "diagnostic_version": "ml38.10.58",
        "execution_mode": EXECUTION_MODE,
        "previous_stage_findings": {
            "decision": "CRLF_LF_CONTRACT_CONFIRMED_FIX_REQUIRED",
            "root_cause_confirmed": True,
            "summary_hashed_lf_normalized_in_memory_content": True,
            "real_files_observed_as_crlf": True,
        },
        "writer_contract_fix": {
            "status": "IMPLEMENTED",
            "hash_contract": HASH_CONTRACT,
            "line_ending_contract": LINE_ENDING_CONTRACT,
            "byte_size_contract": BYTE_SIZE_CONTRACT,
            "writer_contract_version": WRITER_CONTRACT_VERSION,
            "exact_bytes_rehashed_after_write": True,
        },
        "summary_schema_contract": {
            "schema_version": "ml38.10.58",
            "backward_compatible_sha256_and_size_bytes_retained": True,
            "new_contract_fields_declared": True,
        },
        "metadata_truth_contract": {
            "static_wiring_separate_from_runtime_truth": True,
            "unknown_facts_use_null_or_unknown_status": True,
            "successful_write_sets_stream_created_true": True,
        },
        "archive_contract": build_archive_status_metadata(archive_expected=None),
        "timeout_exit_code_contract": build_timeout_exit_code_metadata(),
        "backward_compatibility": {
            "sha256_field_retained": True,
            "size_bytes_field_retained": True,
        },
        "legacy_artifact_policy": {
            "mutate_legacy_artifacts": False,
            "normalized_only_artifacts_exact_byte_valid": False,
            "diagnostic": "SUMMARY_HASH_MATCHES_LF_NORMALIZED_NOT_EXACT_BYTES",
        },
        "tests_contract": {
            "synthetic_tmp_path_only": True,
            "targeted_tests_only": True,
        },
        "real_artifact_guardrail": {
            "quick_quality_rerun": False,
            "archive_recovery_performed": False,
            "existing_real_artifacts_mutated": False,
            "new_real_sidecars_created": False,
            "db_writes": False,
        },
        "validation_decision_gate": {
            "future_contract_fix_implemented": True,
            "full_6481_cascade_outcome_allowed": False,
            "production_like_recompute_allowed": False,
            "tradable_edge_claim_allowed": False,
        },
        "decision": [
            "EXACT_BYTES_AFTER_WRITE_IMPLEMENTED",
            "STATIC_WIRING_SEPARATED_FROM_RUNTIME_TRUTH",
            "LEGACY_ARTIFACTS_NOT_MUTATED",
            "ARCHIVE_RECOVERY_NOT_PERFORMED",
            "QUICK_QUALITY_NOT_RERUN",
            "CASCADE_OUTCOME_REMAINS_BLOCKED",
        ],
    }


sidecar_writer_metadata_archive_contract_fix_plan = (
    build_sidecar_writer_metadata_archive_contract_fix_plan()
)
