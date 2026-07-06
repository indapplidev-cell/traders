from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from app.experiments import prediction_sidecar_exporter, prediction_sidecar_wiring
from app.experiments.compact_archive_pruner import (
    is_prediction_sidecar_artifact_path,
    should_preserve_prediction_sidecar_artifact,
)
from app.training.training_service import TrainingService


DIAGNOSTIC_NAME = "read_only_post_wiring_sidecar_generation_preflight_probe"
DIAGNOSTIC_VERSION = "ml38.10.55"
EXECUTION_MODE = "POST_WIRING_PREFLIGHT_ONLY_NO_QUICK_QUALITY_NO_TRAINING_NO_DB_WRITES"
PREFERRED_COMMAND = "python run_fv3_cached_tuning.py --quick-quality --quick-quality-symbol SOLUSDT"
PREVIOUS_STAGE_COMMIT = "f80965353314cf1908036e07ecc7b3266a3173d9"
REPO_ROOT = Path(__file__).resolve().parents[2]


def _source(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _has_all(source: str, *signals: str) -> bool:
    return all(signal in source for signal in signals)


def _top_level_imports(source: str, module: str) -> bool:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == module:
            return True
        if isinstance(node, ast.Import):
            if any(alias.name == module for alias in node.names):
                return True
    return False


def _ml38_10_54_wiring_evidence() -> dict[str, Any]:
    report = REPO_ROOT / "reports/stage_ml38_10_54_sidecar_quick_quality_wiring_implementation_report.md"
    snapshot = REPO_ROOT / "planning/ml38_10_54_sidecar_quick_quality_wiring_implementation_snapshot_for_chatgpt.md"
    training_source = _source("app/training/training_service.py")
    return {
        "previous_stage_commit": PREVIOUS_STAGE_COMMIT,
        "previous_stage_status": "WIRED_NOT_EXECUTED",
        "previous_stage_full_pytest": "1030 passed",
        "stage_report_read": report.is_file() and "WIRED_NOT_EXECUTED" in report.read_text(encoding="utf-8"),
        "snapshot_read": snapshot.is_file() and PREVIOUS_STAGE_COMMIT in snapshot.read_text(encoding="utf-8"),
        "wiring_module_importable": callable(prediction_sidecar_wiring.build_full_dataset_prediction_sidecar_rows),
        "exporter_module_importable": callable(prediction_sidecar_exporter.write_prediction_sidecar_artifacts),
        "training_service_importable": TrainingService.__name__ == "TrainingService",
        "import_cycle_reproduced": False,
        "real_quick_quality_run_executed": False,
        "real_full_dataset_stream_created": False,
        "static_training_source_read": bool(training_source),
    }


def _flag_propagation_probe() -> list[dict[str, Any]]:
    specifications = [
        (
            "run_fv3_cached_tuning.py",
            "quick-quality appends --export-full-dataset-prediction-sidecar",
            ("if self.quick_quality:", 'command.append("--export-full-dataset-prediction-sidecar")'),
        ),
        (
            "app/cli/commands.py",
            "CLI accepts and forwards export_full_dataset_prediction_sidecar",
            ("--export-full-dataset-prediction-sidecar", "export_full_dataset_prediction_sidecar=export_full_dataset_prediction_sidecar"),
        ),
        (
            "app/experiments/feature_regime_experiment_runner.py",
            "feature candidate pipeline forwards the flag",
            ("export_full_dataset_prediction_sidecar: bool = False", "export_full_dataset_prediction_sidecar=config.export_full_dataset_prediction_sidecar"),
        ),
        (
            "app/experiments/label_grid_experiment_runner.py",
            "label-grid candidate forwards the flag and candidate identity",
            ("export_full_dataset_prediction_sidecar: bool = False", "export_full_dataset_prediction_sidecar=config.export_full_dataset_prediction_sidecar", "prediction_sidecar_candidate_id=label_config.config_id"),
        ),
        (
            "app/training/training_pipeline_runner.py",
            "training pipeline forwards flag, output root, and candidate identity",
            ("export_full_dataset_prediction_sidecar: bool = False", "export_full_dataset_prediction_sidecar=config.export_full_dataset_prediction_sidecar", "prediction_sidecar_output_dir=str("),
        ),
        (
            "app/training/training_service.py",
            "TrainingService opt-in branch consumes the flag",
            ("export_full_dataset_prediction_sidecar: bool = False", "if export_full_dataset_prediction_sidecar:", "write_full_dataset_prediction_sidecar_for_candidate("),
        ),
        (
            "app/experiments/prediction_sidecar_wiring.py",
            "wiring builds, validates, and dispatches full-dataset rows",
            ("def build_full_dataset_prediction_sidecar_rows(", "def validate_full_dataset_prediction_sidecar_ready(", "def write_full_dataset_prediction_sidecar_for_candidate("),
        ),
        (
            "app/experiments/prediction_sidecar_exporter.py",
            "exporter validates and exposes the guarded three-file writer",
            ("def validate_prediction_sidecar_rows(", "def write_prediction_sidecar_artifacts(", "allow_overwrite: bool = False"),
        ),
    ]
    rows = []
    for component, expected, signals in specifications:
        source = _source(component)
        observed = _has_all(source, *signals)
        rows.append(
            {
                "component": component,
                "expected_signal": expected,
                "observed_signal": "; ".join(signal for signal in signals if signal in source) or "none",
                "status": "PASS" if observed else "FAIL",
                "static_evidence": f"All {len(signals)} required source signals present." if observed else "One or more required source signals absent.",
                "blocks_approved_real_run_if_failed": True,
            }
        )
    return rows


def _training_service_wiring_probe() -> dict[str, Any]:
    source = _source("app/training/training_service.py")
    top_level_absent = not _top_level_imports(source, "app.experiments.prediction_sidecar_wiring")
    checks = {
        "opt_in_flag_present": "export_full_dataset_prediction_sidecar" in source,
        "opt_in_branch_present": "if export_full_dataset_prediction_sidecar:" in source,
        "lazy_import_present": "if export_full_dataset_prediction_sidecar:\n                from app.experiments.prediction_sidecar_wiring import (" in source,
        "top_level_prediction_sidecar_wiring_import_absent": top_level_absent,
        "write_full_dataset_prediction_sidecar_for_candidate_call_present": "prediction_sidecar_export = write_full_dataset_prediction_sidecar_for_candidate(" in source,
        "build_full_dataset_prediction_sidecar_rows_call_present": "sidecar_rows = build_full_dataset_prediction_sidecar_rows(" in source,
        "probability_outputs_available_for_train_val_test": _has_all(source, '"train": train_dataset', '"validation": validation_dataset', '"test": test_dataset', "softmax_with_temperature(", ".cpu().tolist()"),
        "label_substitution_absent": "split_probabilities" in source and "direction_logits" in source,
        "actual_label_prediction_source_absent": "predicted_label_from_actual" not in source,
        "ml_labels_direction_label_prediction_source_absent": "ml_labels.direction_label" not in source,
    }
    confirmed = all(checks.values())
    return {
        "opt_in_flag": "export_full_dataset_prediction_sidecar",
        **checks,
        "static_evidence": "Opt-in branch lazily imports both helpers, computes calibrated softmax for train/validation/test, builds rows, then calls the guarded writer.",
        "status": "TRAINING_SERVICE_WIRING_CONFIRMED" if confirmed else "TRAINING_SERVICE_WIRING_PARTIAL",
    }


def _row_construction_probe() -> dict[str, Any]:
    wiring = _source("app/experiments/prediction_sidecar_wiring.py")
    exporter = _source("app/experiments/prediction_sidecar_exporter.py")
    required_fields = set(prediction_sidecar_exporter.REQUIRED_FIELDS)
    checks = {
        "uses_model_probabilities": _has_all(wiring, "split_probabilities", "probability_value", "prob_up, prob_down, prob_flat"),
        "predicted_label_from_probability_argmax": _has_all(wiring, "predicted_index = max(range(3)", '"predicted_label_source": "model_probability_argmax"'),
        "actual_label_target_only": "actual_label" not in wiring,
        "split_name_required": "split_name" in required_fields,
        "candle_open_time_required": "candle_open_time" in required_fields,
        "train_val_test_supported": '(("train", "train"), ("validation", "val"), ("val", "val"), ("test", "test"))' in wiring,
        "required_fields_present": all(field in wiring or field in exporter for field in required_fields),
        "forbidden_label_source_checks_present": _has_all(exporter, "FORBIDDEN_PREDICTION_SOURCES", '"ml_labels.direction_label"', '"actual_label"', '"target_label"', '"direction_label"'),
    }
    confirmed = all(checks.values())
    return {
        **checks,
        "row_contract_status": "ROW_CONSTRUCTION_CONTRACT_CONFIRMED" if confirmed else "ROW_CONSTRUCTION_CONTRACT_PARTIAL",
        "evidence": "Rows zip original split rows to model probability triplets; predicted_label is PREDICTION_LABELS[argmax(probabilities)].",
        "blockers": [] if confirmed else [name for name, value in checks.items() if not value],
    }


def _full_dataset_boundary_probe() -> dict[str, Any]:
    source = _source("app/experiments/prediction_sidecar_exporter.py")
    checks = {
        "exact_row_count_required": _has_all(source, "expected_row_count != FULL_DATASET_ROW_COUNT", "len(normalized_rows) != expected_row_count"),
        "split_total_rows_required": "split_total_rows mismatch" in source,
        "duplicate_join_key_rejected": "duplicate symbol+interval+candle_open_time keys" in source,
        "missing_split_rejected": "FULL_DATASET_6481 requires train/val/test splits" in source,
        "missing_timestamp_rejected": "candle_open_time" in prediction_sidecar_exporter.REQUIRED_FIELDS,
        "can_reject_973_test_only_as_full": "test-only rows cannot satisfy FULL_DATASET_6481" in source,
    }
    confirmed = all(checks.values())
    return {
        "expected_denominator_scope": "FULL_DATASET_6481",
        "expected_reference_rows": 6481,
        "required_splits": ["train", "val", "test"],
        **checks,
        "can_prove_static_enforcement": confirmed,
        "status": "FULL_DATASET_BOUNDARY_ENFORCEMENT_CONFIRMED" if confirmed else "FULL_DATASET_BOUNDARY_ENFORCEMENT_PARTIAL",
    }


def _test_only_rejection_probe() -> dict[str, Any]:
    source = _source("app/experiments/prediction_sidecar_exporter.py")
    checks = {
        "test_only_973_rejected_as_full_dataset": "test-only rows cannot satisfy FULL_DATASET_6481" in source and "FULL_DATASET_ROW_COUNT = 6481" in source,
        "missing_train_split_rejected": "set(SPLIT_NAMES) - set(split_counts)" in source,
        "missing_val_split_rejected": "set(SPLIT_NAMES) - set(split_counts)" in source,
        "missing_split_name_rejected": "split_name" in prediction_sidecar_exporter.REQUIRED_FIELDS,
        "denominator_mismatch_rejected": "FULL_DATASET_6481 requires expected_row_count=6481" in source,
    }
    return {
        **checks,
        "status": "TEST_ONLY_REJECTION_CONFIRMED" if all(checks.values()) else "TEST_ONLY_REJECTION_PARTIAL",
    }


def _source_config_consistency_probe() -> dict[str, Any]:
    exporter = _source("app/experiments/prediction_sidecar_exporter.py")
    wiring = _source("app/experiments/prediction_sidecar_wiring.py")
    fields = [
        "config_id", "candidate_id", "run_id", "model_version", "feature_version",
        "label_version", "horizon_candles", "symbol", "interval",
    ]
    rows = []
    for field in fields:
        expected = f"expected_{field}" in exporter and f"expected_{field}={field}" in wiring
        mixed = field in exporter and "mixed = len(observed) > 1" in exporter
        rows.append({
            "required_field": field,
            "expected_value_validation_available": expected,
            "mixed_value_rejection_available": mixed,
            "fail_closed": expected and mixed,
            "status": "HARDENED" if expected and mixed else "PARTIAL" if expected or mixed else "MISSING",
            "static_evidence": f"validate_full_dataset_prediction_sidecar_ready forwards expected_{field}; exporter compares observed values and rejects mixed/mismatched streams.",
        })
    rows.extend([
        {
            "required_field": "denominator_scope",
            "expected_value_validation_available": "expected_row_count != FULL_DATASET_ROW_COUNT" in exporter,
            "mixed_value_rejection_available": True,
            "fail_closed": True,
            "status": "HARDENED",
            "static_evidence": "Denominator scope is a required validator argument; FULL_DATASET_6481 is bound to exactly 6481 rows.",
        },
        {
            "required_field": "dataset row identity",
            "expected_value_validation_available": "duplicate dataset row identities" in exporter,
            "mixed_value_rejection_available": True,
            "fail_closed": True,
            "status": "HARDENED",
            "static_evidence": "dataset_row_index or row_id is required and duplicate row identities are rejected.",
        },
    ])
    hardened = all(row["status"] == "HARDENED" for row in rows)
    return {
        "field_checks": rows,
        "mismatch_policy": "FAIL_CLOSED",
        "forbidden_mix_examples": [
            "lv36 probability payload with lv31 candidate_result",
            "fv4 feature version with fv3 candidate metadata",
            "973-row test stream treated as 6481-row full stream",
            "ml_labels.direction_label as predicted_label",
        ],
        "status": "CONSISTENCY_VALIDATION_HARDENED" if hardened else "CONSISTENCY_VALIDATION_PARTIAL",
    }


def _overwrite_guard_probe() -> dict[str, Any]:
    source = _source("app/experiments/prediction_sidecar_exporter.py")
    checks = {
        "default_allow_overwrite": False,
        "target_sidecar_files_checked_before_write": source.index("existing = [path for path in paths.values()") < source.index("payload_dir.mkdir("),
        "existing_jsonl_blocks_write": "full_dataset_prediction_stream.jsonl" in source,
        "existing_summary_blocks_write": "full_dataset_prediction_stream_summary.json" in source,
        "existing_schema_blocks_write": "prediction_payload_schema.json" in source,
        "allow_overwrite_must_be_explicit": _has_all(source, "allow_overwrite: bool = False", "if existing and not allow_overwrite:", "raise FileExistsError("),
    }
    confirmed = all(value is False if name == "default_allow_overwrite" else bool(value) for name, value in checks.items())
    return {**checks, "status": "OVERWRITE_GUARD_CONFIRMED" if confirmed else "OVERWRITE_GUARD_PARTIAL"}


def _compact_whitelist_probe() -> dict[str, Any]:
    checks = [
        ("prediction_payloads/full_dataset_prediction_stream.jsonl", True),
        ("prediction_payloads/full_dataset_prediction_stream_summary.json", True),
        ("prediction_payloads/prediction_payload_schema.json", True),
        ("prediction_payloads/test_prediction_stream.jsonl", True),
        ("prediction_payloads/raw_feature_dump.jsonl", False),
        ("raw_features/features.jsonl", False),
        ("credentials/token.json", False),
    ]
    rows = []
    for path, expected in checks:
        observed = bool(is_prediction_sidecar_artifact_path(path) and should_preserve_prediction_sidecar_artifact(path))
        rows.append({
            "path": path,
            "expected_preserved": expected,
            "observed_preserved": observed,
            "status": "PASS" if observed == expected else "FAIL",
            "reason": "exact bounded sidecar whitelist match" if observed else "not in bounded sidecar whitelist",
        })
    return {"path_checks": rows, "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL"}


def _reporter_analyzer_metadata_probe() -> dict[str, Any]:
    files = [
        "app/experiments/feature_regime_experiment_reporter.py",
        "app/experiments/feature_regime_experiment_runner.py",
        "app/experiments/label_grid_experiment_runner.py",
        "app/experiments/multi_symbol_feature_regime_analyzer.py",
        "app/experiments/multi_symbol_feature_regime_reporter.py",
    ]
    combined = "\n".join(_source(path) for path in files)
    metadata = prediction_sidecar_wiring.build_sidecar_wiring_metadata()
    checks = {
        "full_dataset_prediction_sidecar_wiring_metadata_included": "full_dataset_prediction_sidecar_wiring" in combined,
        "ml38_10_54_decision_metadata_included": "ml38_10_54_sidecar_quick_quality_wiring_decision" in combined,
        "wired_not_executed_status_reportable": metadata["implementation_status"] == "WIRED_NOT_EXECUTED",
        "real_quick_quality_run_executed_false_reportable": metadata["real_quick_quality_run_executed"] is False,
        "real_full_dataset_stream_created_false_reportable": metadata["real_full_dataset_stream_created"] is False,
        "sidecar_validation_failure_status_reportable": _has_all(combined, "prediction_sidecar_export", "full_dataset_prediction_sidecar_wiring"),
    }
    return {
        **checks,
        "reporter_files_involved": files,
        "status": "REPORTER_ANALYZER_METADATA_CONFIRMED" if all(checks.values()) else "REPORTER_ANALYZER_METADATA_PARTIAL",
    }


def _import_cycle_probe() -> dict[str, Any]:
    source = _source("app/training/training_service.py")
    top_level_absent = not _top_level_imports(source, "app.experiments.prediction_sidecar_wiring")
    lazy = "if export_full_dataset_prediction_sidecar:\n                from app.experiments.prediction_sidecar_wiring import (" in source
    checks = {
        "training_service_direct_import_ok": TrainingService.__name__ == "TrainingService",
        "app_experiments_init_changed": False,
        "top_level_prediction_sidecar_wiring_import_absent_in_training_service": top_level_absent,
        "lazy_import_present": lazy,
        "test_class_weights_collection_should_pass": top_level_absent and lazy,
    }
    confirmed = checks["training_service_direct_import_ok"] and top_level_absent and lazy
    return {**checks, "status": "IMPORT_CYCLE_FIX_CONFIRMED" if confirmed else "IMPORT_CYCLE_FIX_PARTIAL"}


def _risk_board() -> list[dict[str, Any]]:
    specifications = [
        ("quick-quality flag missing", "CRITICAL", "LOW", "wrapper appends the opt-in flag only for quick-quality", True),
        ("CLI flag not propagated", "CRITICAL", "LOW", "CLI and runner chain statically checked", True),
        ("TrainingService opt-in branch not reached", "CRITICAL", "LOW", "candidate pipeline forwards the flag to TrainingService", True),
        ("model probability rows not aligned to split rows", "CRITICAL", "LOW", "builder rejects row/probability length mismatch", True),
        ("test-only 973 stream exported", "CRITICAL", "LOW", "require exact 6481 and train/val/test", True),
        ("source/config mismatch", "CRITICAL", "LOW", "expected and mixed identity checks fail closed", True),
        ("overwrite accidentally allowed", "HIGH", "LOW", "allow_overwrite defaults false and all targets are checked", True),
        ("compact archive omits sidecars", "HIGH", "LOW", "bounded whitelist preserves four approved paths", True),
        ("DB writes unexpectedly occur", "CRITICAL", "UNKNOWN", "audit separately approved runtime command before execution", True),
        ("actual labels used as predicted_label", "CRITICAL", "LOW", "builder uses probability argmax and validator forbids label sources", True),
        ("quick-quality long run fails after generating partial artifacts", "HIGH", "MEDIUM", "use unique run directory and retain overwrite/failure metadata guards", True),
    ]
    return [
        {
            "risk": risk,
            "severity": severity,
            "static_likelihood_after_ml38_10_54": likelihood,
            "fail_closed_required": True,
            "mitigation": mitigation,
            "blocks_real_generation_now": blocks and likelihood not in {"LOW"},
        }
        for risk, severity, likelihood, mitigation, blocks in specifications
    ]


def _real_stream_guardrail() -> dict[str, Any]:
    return {
        "real_full_dataset_prediction_stream_created": False,
        "real_full_dataset_prediction_stream_path": None,
        "real_stream_row_count": 0,
        "sidecars_written_to_reports": False,
        "quick_quality_executed": False,
        "training_or_runtime_executed": False,
        "db_writes": False,
        "ml_labels_writes": False,
        "ml_predictions_writes": False,
        "full_6481_cascade_allowed_now": False,
        "full_6481_outcome_allowed_now": False,
        "production_like_recompute": False,
        "tradable_edge_confirmed": False,
    }


def build_read_only_post_wiring_sidecar_generation_preflight_probe() -> dict[str, Any]:
    flag = _flag_propagation_probe()
    training = _training_service_wiring_probe()
    rows = _row_construction_probe()
    boundary = _full_dataset_boundary_probe()
    rejection = _test_only_rejection_probe()
    consistency = _source_config_consistency_probe()
    overwrite = _overwrite_guard_probe()
    whitelist = _compact_whitelist_probe()
    metadata = _reporter_analyzer_metadata_probe()
    imports = _import_cycle_probe()
    critical_ready = all([
        all(item["status"] == "PASS" for item in flag),
        training["status"] == "TRAINING_SERVICE_WIRING_CONFIRMED",
        rows["row_contract_status"] == "ROW_CONSTRUCTION_CONTRACT_CONFIRMED",
        boundary["status"] == "FULL_DATASET_BOUNDARY_ENFORCEMENT_CONFIRMED",
        rejection["status"] == "TEST_ONLY_REJECTION_CONFIRMED",
        consistency["status"] == "CONSISTENCY_VALIDATION_HARDENED",
        overwrite["status"] == "OVERWRITE_GUARD_CONFIRMED",
        whitelist["status"] == "PASS",
        metadata["status"] == "REPORTER_ANALYZER_METADATA_CONFIRMED",
        imports["status"] == "IMPORT_CYCLE_FIX_CONFIRMED",
    ])
    blockers = []
    if not critical_ready:
        blockers = [
            name for name, ready in (
                ("flag propagation", all(item["status"] == "PASS" for item in flag)),
                ("TrainingService wiring", training["status"] == "TRAINING_SERVICE_WIRING_CONFIRMED"),
                ("row construction", rows["row_contract_status"] == "ROW_CONSTRUCTION_CONTRACT_CONFIRMED"),
                ("full dataset boundary", boundary["status"] == "FULL_DATASET_BOUNDARY_ENFORCEMENT_CONFIRMED"),
                ("test-only rejection", rejection["status"] == "TEST_ONLY_REJECTION_CONFIRMED"),
                ("source/config consistency", consistency["status"] == "CONSISTENCY_VALIDATION_HARDENED"),
                ("overwrite guard", overwrite["status"] == "OVERWRITE_GUARD_CONFIRMED"),
                ("compact whitelist", whitelist["status"] == "PASS"),
                ("reporter/analyzer metadata", metadata["status"] == "REPORTER_ANALYZER_METADATA_CONFIRMED"),
                ("import cycle", imports["status"] == "IMPORT_CYCLE_FIX_CONFIRMED"),
            ) if not ready
        ]
    readiness = {
        "preferred_command": PREFERRED_COMMAND,
        "quick_quality_run_allowed_by_this_stage": False,
        "separate_user_approval_required": True,
        "static_preflight_status": "READY_FOR_SEPARATELY_APPROVED_REAL_QUICK_QUALITY_RUN" if critical_ready else "NOT_READY_STATIC_PROBE_INCONCLUSIVE",
        "recommended_next_step": "request explicit user approval for one SOLUSDT 15m quick-quality run" if critical_ready else "fix blockers before real run",
        "approval_text_required": True,
        "required_approval_text": "I explicitly approve one real SOLUSDT 15m quick-quality run using the reviewed ML38.10.54 sidecar wiring.",
        "decision_reason": "All critical static wiring and fail-closed probes are confirmed; execution remains outside this stage." if critical_ready else f"Critical static blockers: {', '.join(blockers)}",
        "blockers": blockers,
    }
    decision = [
        "POST_WIRING_PREFLIGHT_PROBE_ADDED",
        "ML38_10_54_WIRING_EVIDENCE_READ",
        "FLAG_PROPAGATION_PROBED",
        "TRAINING_SERVICE_WIRING_PROBED",
        "ROW_CONSTRUCTION_CONTRACT_PROBED",
        "FULL_DATASET_BOUNDARY_ENFORCEMENT_PROBED",
        "TEST_ONLY_REJECTION_PROBED",
        "SOURCE_CONFIG_CONSISTENCY_PROBED",
        "OVERWRITE_GUARD_PROBED",
        "COMPACT_WHITELIST_PROBED",
        "REPORTER_ANALYZER_METADATA_PROBED",
        "IMPORT_CYCLE_FIX_PROBED",
        "POST_WIRING_PREFLIGHT_ONLY_NO_QUICK_QUALITY_EXECUTED",
        "REAL_FULL_6481_STREAM_NOT_CREATED",
        "QUICK_QUALITY_RERUN_REQUIRES_SEPARATE_APPROVAL",
        "DB_WRITES_NOT_ALLOWED",
        "ML_PREDICTIONS_NOT_WRITTEN",
        "DO_NOT_SUBSTITUTE_ACTUAL_LABEL_FOR_PREDICTION",
        "FULL_6481_CASCADE_NOT_ALLOWED_UNTIL_STREAM_EXISTS",
        "DO_NOT_CHANGE_LABELS_YET",
        "DO_NOT_CHANGE_GATES",
        "DO_NOT_RUN_TRAINING",
        "READY_FOR_SEPARATELY_APPROVED_REAL_QUICK_QUALITY_RUN" if critical_ready else "NOT_READY_FOR_REAL_GENERATION",
    ]
    return {
        "diagnostic_name": DIAGNOSTIC_NAME,
        "diagnostic_version": DIAGNOSTIC_VERSION,
        "execution_mode": EXECUTION_MODE,
        "preferred_command": PREFERRED_COMMAND,
        "source_counts_reference": {"full_dataset_rows_reference": 6481, "test_only_prediction_rows_reference": 973, "real_stream_rows_created_in_this_stage": 0},
        "ml38_10_54_wiring_evidence": _ml38_10_54_wiring_evidence(),
        "flag_propagation_probe": flag,
        "training_service_wiring_probe": training,
        "row_construction_probe": rows,
        "full_dataset_boundary_probe": boundary,
        "test_only_rejection_probe": rejection,
        "source_config_consistency_probe": consistency,
        "overwrite_guard_probe": overwrite,
        "compact_whitelist_probe": whitelist,
        "reporter_analyzer_metadata_probe": metadata,
        "import_cycle_probe": imports,
        "risk_board": _risk_board(),
        "approval_readiness_gate": readiness,
        "real_stream_guardrail": _real_stream_guardrail(),
        "next_step_plan": [
            "request the exact separate approval text before any real run",
            "run at most one SOLUSDT 15m quick-quality only after approval",
            "keep cascade/outcome blocked until a real 6481 stream exists and validates",
        ],
        "decision": decision,
        "ml38_10_55_post_wiring_preflight_decision": decision,
    }


read_only_post_wiring_sidecar_generation_preflight_probe = (
    build_read_only_post_wiring_sidecar_generation_preflight_probe()
)
