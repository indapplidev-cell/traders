from __future__ import annotations

from pathlib import Path

from app.diagnostics.post_fix_sidecar_fixture_validation import (
    EXECUTION_MODE,
    build_legacy_normalized_only_fixture,
    build_post_fix_sidecar_fixture_validation,
    build_synthetic_prediction_rows,
    compute_exact_sha256,
    count_line_endings,
    post_fix_sidecar_fixture_validation,
    validate_legacy_normalized_only_fails_closed,
)


def test_diagnostic_block_and_fixture_contract(tmp_path: Path) -> None:
    diagnostic = build_post_fix_sidecar_fixture_validation(tmp_path)
    assert diagnostic["diagnostic_name"] == "post_fix_sidecar_fixture_validation"
    assert diagnostic["execution_mode"] == EXECUTION_MODE
    generation = diagnostic["fixture_generation"]
    assert generation["generated_stream_exists"] is True
    assert generation["generated_summary_exists"] is True
    assert generation["generated_schema_exists"] is True
    assert generation["generated_row_count"] == 3
    assert generation["validation_status"] == "PREDICTION_SIDECAR_VALID"
    assert diagnostic["decision"] == ["POST_FIX_FIXTURE_VALIDATION_PASSED_NO_REAL_RUN"]


def test_lf_only_exact_byte_integrity_and_summary_fields(tmp_path: Path) -> None:
    diagnostic = build_post_fix_sidecar_fixture_validation(tmp_path)
    endings = diagnostic["line_ending_validation"]
    exact = diagnostic["exact_byte_integrity_validation"]
    assert endings["generated_stream_has_crlf"] is False
    assert endings["generated_stream_has_bare_lf"] is True
    assert endings["stray_cr_count"] == 0
    assert exact["exact_file_sha256"] == exact["summary_sha256"]
    assert exact["exact_file_size_bytes"] == exact["summary_size_bytes"]
    assert exact["lf_normalized_sha256"] == exact["exact_file_sha256"]
    assert diagnostic["summary_contract_validation"] == {
        "hash_contract": "EXACT_BYTES_AFTER_WRITE",
        "line_ending_contract": "LF",
        "byte_size_contract": "EXACT_BYTES_AFTER_WRITE",
        "writer_contract_version": "ml38.10.69",
        "fields_valid": True,
    }
    assert diagnostic["schema_contract_validation"]["schema_version"] == "ml38.10.69"


def test_runtime_archive_and_completion_truth(tmp_path: Path) -> None:
    diagnostic = build_post_fix_sidecar_fixture_validation(tmp_path)
    runtime = diagnostic["runtime_truth_validation"]
    assert runtime["sidecar_runtime_truth_exists"] is True
    assert runtime["unknown_facts_use_null_not_false"] is True
    assert runtime["runtime_truth"]["real_full_dataset_stream_created"] is True
    assert runtime["runtime_truth"]["export_completed"] is True
    assert runtime["runtime_truth"]["real_quick_quality_run_executed"] is None
    archive = diagnostic["archive_contract_validation"]
    assert set(archive["supported_status_examples"]) == {"NOT_REQUESTED", "MISSING", "UNKNOWN"}
    assert all(
        item["sidecar_retention_confirmed"] is False
        for item in archive["supported_status_examples"].values()
    )
    completion = diagnostic["completion_contract_validation"]
    assert completion["fake_exit_code_zero_present"] is False
    assert completion["completion"]["python_exit_code"] is None
    assert completion["completion"]["controlling_shell_exit_code"] is None


def test_legacy_normalized_only_fails_closed_without_mutation(tmp_path: Path) -> None:
    paths = build_legacy_normalized_only_fixture(tmp_path)
    before = compute_exact_sha256(paths["stream_path"])
    endings = count_line_endings(paths["stream_path"])
    validation = validate_legacy_normalized_only_fails_closed(
        paths["summary_path"], paths["stream_path"]
    )
    assert endings["generated_stream_has_crlf"] is True
    assert validation["status"] == "PREDICTION_SIDECAR_EXACT_BYTES_INVALID"
    assert validation["summary_matches_lf_normalized_not_exact_bytes"] is True
    assert "SUMMARY_HASH_MATCHES_LF_NORMALIZED_NOT_EXACT_BYTES" in validation["errors"]
    assert validation["fixture_mutated_during_validation"] is False
    assert compute_exact_sha256(paths["stream_path"]) == before


def test_rows_are_synthetic_predictions_without_actual_labels() -> None:
    rows = build_synthetic_prediction_rows()
    assert {row["symbol"] for row in rows} == {"FIXTUREUSDT"}
    assert {row["split_name"] for row in rows} == {"train", "val", "test"}
    assert {row["predicted_label"] for row in rows} == {"UP", "DOWN", "FLAT"}
    assert all("actual_label" not in row and "direction_label" not in row for row in rows)
    assert all(row["predicted_label_source"] == "model_probability_argmax" for row in rows)


def test_guardrails_and_import_time_block() -> None:
    diagnostic = post_fix_sidecar_fixture_validation
    guardrail = diagnostic["real_artifact_guardrail"]
    assert guardrail["temporary_directory_only"] is True
    assert guardrail["real_artifacts_read"] is False
    assert guardrail["real_artifacts_written_or_mutated"] is False
    assert guardrail["quick_quality_run"] is False
    assert guardrail["training_or_runtime_run"] is False
    assert guardrail["db_writes"] is False
    gate = diagnostic["validation_decision_gate"]
    assert gate["future_writer_contract_validated_on_fixture"] is True
    assert gate["newly_generated_exact_byte_valid_real_sidecar_available"] is False
    assert gate["cascade_outcome_allowed_now"] is False
    assert gate["production_like_recompute_allowed_now"] is False
    assert gate["tradable_edge_claim_allowed_now"] is False
