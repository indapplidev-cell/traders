from __future__ import annotations

import ast
from pathlib import Path

from app.diagnostics.post_wiring_sidecar_generation_preflight_probe import (
    PREFERRED_COMMAND,
    read_only_post_wiring_sidecar_generation_preflight_probe as PROBE,
)


def test_post_wiring_probe_identity_and_non_execution_contract() -> None:
    assert PROBE["diagnostic_name"] == "read_only_post_wiring_sidecar_generation_preflight_probe"
    assert PROBE["diagnostic_version"] == "ml38.10.55"
    assert PROBE["execution_mode"] == "POST_WIRING_PREFLIGHT_ONLY_NO_QUICK_QUALITY_NO_TRAINING_NO_DB_WRITES"
    assert PROBE["preferred_command"] == PREFERRED_COMMAND
    assert PROBE["approval_readiness_gate"]["quick_quality_run_allowed_by_this_stage"] is False


def test_flag_propagation_covers_entire_reviewed_chain() -> None:
    expected = {
        "run_fv3_cached_tuning.py",
        "app/cli/commands.py",
        "app/experiments/feature_regime_experiment_runner.py",
        "app/experiments/label_grid_experiment_runner.py",
        "app/training/training_pipeline_runner.py",
        "app/training/training_service.py",
        "app/experiments/prediction_sidecar_wiring.py",
        "app/experiments/prediction_sidecar_exporter.py",
    }
    rows = PROBE["flag_propagation_probe"]
    assert {row["component"] for row in rows} == expected
    assert all(row["status"] == "PASS" for row in rows)
    assert all(row["blocks_approved_real_run_if_failed"] for row in rows)


def test_training_service_wiring_confirms_opt_in_and_lazy_import() -> None:
    probe = PROBE["training_service_wiring_probe"]
    assert probe["opt_in_flag"] == "export_full_dataset_prediction_sidecar"
    assert probe["opt_in_flag_present"] is True
    assert probe["opt_in_branch_present"] is True
    assert probe["lazy_import_present"] is True
    assert probe["top_level_prediction_sidecar_wiring_import_absent"] is True
    assert probe["build_full_dataset_prediction_sidecar_rows_call_present"] is True
    assert probe["write_full_dataset_prediction_sidecar_for_candidate_call_present"] is True
    assert probe["probability_outputs_available_for_train_val_test"] is True
    assert probe["status"] == "TRAINING_SERVICE_WIRING_CONFIRMED"


def test_row_construction_uses_probability_argmax_without_label_substitution() -> None:
    probe = PROBE["row_construction_probe"]
    assert probe["uses_model_probabilities"] is True
    assert probe["predicted_label_from_probability_argmax"] is True
    assert probe["actual_label_target_only"] is True
    assert probe["forbidden_label_source_checks_present"] is True
    assert probe["row_contract_status"] == "ROW_CONSTRUCTION_CONTRACT_CONFIRMED"
    assert probe["blockers"] == []


def test_full_dataset_boundary_is_enforced_or_exact_blockers_are_reported() -> None:
    probe = PROBE["full_dataset_boundary_probe"]
    assert probe["expected_denominator_scope"] == "FULL_DATASET_6481"
    assert probe["expected_reference_rows"] == 6481
    assert probe["required_splits"] == ["train", "val", "test"]
    if probe["can_prove_static_enforcement"]:
        assert probe["status"] == "FULL_DATASET_BOUNDARY_ENFORCEMENT_CONFIRMED"
    else:
        assert PROBE["approval_readiness_gate"]["blockers"]


def test_test_only_973_stream_is_statically_rejected() -> None:
    probe = PROBE["test_only_rejection_probe"]
    assert probe["test_only_973_rejected_as_full_dataset"] is True
    assert probe["missing_train_split_rejected"] is True
    assert probe["missing_val_split_rejected"] is True
    assert probe["missing_split_name_rejected"] is True
    assert probe["denominator_mismatch_rejected"] is True
    assert probe["status"] == "TEST_ONLY_REJECTION_CONFIRMED"


def test_source_config_consistency_is_fail_closed() -> None:
    probe = PROBE["source_config_consistency_probe"]
    assert probe["mismatch_policy"] == "FAIL_CLOSED"
    assert probe["status"] == "CONSISTENCY_VALIDATION_HARDENED"
    assert all(row["fail_closed"] for row in probe["field_checks"])
    assert all(row["status"] == "HARDENED" for row in probe["field_checks"])


def test_overwrite_guard_is_confirmed() -> None:
    probe = PROBE["overwrite_guard_probe"]
    assert probe["default_allow_overwrite"] is False
    assert probe["target_sidecar_files_checked_before_write"] is True
    assert probe["existing_jsonl_blocks_write"] is True
    assert probe["existing_summary_blocks_write"] is True
    assert probe["existing_schema_blocks_write"] is True
    assert probe["allow_overwrite_must_be_explicit"] is True
    assert probe["status"] == "OVERWRITE_GUARD_CONFIRMED"


def test_compact_whitelist_has_only_approved_paths() -> None:
    probe = PROBE["compact_whitelist_probe"]
    assert probe["status"] == "PASS"
    assert all(row["status"] == "PASS" for row in probe["path_checks"])
    observed = {row["path"]: row["observed_preserved"] for row in probe["path_checks"]}
    assert observed["prediction_payloads/full_dataset_prediction_stream.jsonl"] is True
    assert observed["prediction_payloads/raw_feature_dump.jsonl"] is False
    assert observed["raw_features/features.jsonl"] is False
    assert observed["credentials/token.json"] is False


def test_reporter_metadata_and_import_cycle_fix_are_confirmed() -> None:
    metadata = PROBE["reporter_analyzer_metadata_probe"]
    imports = PROBE["import_cycle_probe"]
    assert metadata["status"] == "REPORTER_ANALYZER_METADATA_CONFIRMED"
    assert metadata["wired_not_executed_status_reportable"] is True
    assert metadata["real_quick_quality_run_executed_false_reportable"] is True
    assert metadata["real_full_dataset_stream_created_false_reportable"] is True
    assert imports["training_service_direct_import_ok"] is True
    assert imports["top_level_prediction_sidecar_wiring_import_absent_in_training_service"] is True
    assert imports["lazy_import_present"] is True
    assert imports["status"] == "IMPORT_CYCLE_FIX_CONFIRMED"


def test_real_stream_guardrail_and_decisions_record_no_execution() -> None:
    guardrail = PROBE["real_stream_guardrail"]
    assert guardrail["real_full_dataset_prediction_stream_created"] is False
    assert guardrail["real_stream_row_count"] == 0
    assert guardrail["sidecars_written_to_reports"] is False
    assert guardrail["quick_quality_executed"] is False
    assert guardrail["training_or_runtime_executed"] is False
    assert guardrail["db_writes"] is False
    assert guardrail["ml_labels_writes"] is False
    assert guardrail["ml_predictions_writes"] is False
    decisions = PROBE["decision"]
    assert "POST_WIRING_PREFLIGHT_ONLY_NO_QUICK_QUALITY_EXECUTED" in decisions
    assert "REAL_FULL_6481_STREAM_NOT_CREATED" in decisions
    assert "FULL_6481_CASCADE_NOT_ALLOWED_UNTIL_STREAM_EXISTS" in decisions


def test_readiness_decision_is_ready_or_fail_closed_with_blockers() -> None:
    gate = PROBE["approval_readiness_gate"]
    if gate["static_preflight_status"] == "READY_FOR_SEPARATELY_APPROVED_REAL_QUICK_QUALITY_RUN":
        assert "READY_FOR_SEPARATELY_APPROVED_REAL_QUICK_QUALITY_RUN" in PROBE["decision"]
        assert gate["blockers"] == []
        assert gate["separate_user_approval_required"] is True
    else:
        assert "NOT_READY_FOR_REAL_GENERATION" in PROBE["decision"]
        assert gate["blockers"]


def test_probe_test_is_static_and_does_not_write_report_sidecars() -> None:
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "subprocess" not in imports
    assert "write_full_dataset_prediction_sidecar_for_candidate" not in called_names
    assert "write_prediction_sidecar_artifacts" not in called_names
    assert not Path("reports/prediction_payloads/full_dataset_prediction_stream.jsonl").exists()
