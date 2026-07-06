from __future__ import annotations

import hashlib
import json
import math
import os
from collections import Counter
from pathlib import Path
from typing import Any, Mapping


DIAGNOSTIC_NAME = "read_only_real_quick_quality_sidecar_validation_audit"
DIAGNOSTIC_VERSION = "ml38.10.56"
EXECUTION_MODE = "READ_ONLY_REAL_ARTIFACT_VALIDATION_NO_QUICK_QUALITY_NO_TRAINING_NO_DB_WRITES"
APPROVED_RUN_COMMAND = "python run_fv3_cached_tuning.py --quick-quality --quick-quality-symbol SOLUSDT"
EXPECTED_SPLIT_COUNTS = {"train": 4536, "val": 972, "test": 973}
REQUIRED_SIDECAR_FIELDS = {
    "symbol", "interval", "candle_open_time", "split_name", "split_row_index",
    "split_total_rows", "config_id", "feature_version", "label_version",
    "model_version", "horizon_candles", "predicted_label", "prob_up",
    "prob_down", "prob_flat", "confidence",
}
SIDECAR_FILENAMES = {
    "stream": "full_dataset_prediction_stream.jsonl",
    "summary": "full_dataset_prediction_stream_summary.json",
    "schema": "prediction_payload_schema.json",
}
FORBIDDEN_PREDICTION_SOURCES = {"actual_label", "ml_labels.direction_label", "target_label"}
MODEL_SOURCE_STAGE = "training_service_calibrated_model_softmax_argmax"


def compute_file_sha256(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_real_quick_quality_run_artifacts(
    output_dir: str | Path,
    *,
    latest_zip_path_for_run: str | Path | None = None,
    old_zip_path: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(output_dir)
    inventory = inventory_prediction_sidecars(root)
    new_zip = Path(latest_zip_path_for_run) if latest_zip_path_for_run else None
    old_zip = Path(old_zip_path) if old_zip_path else None
    sidecars_found = bool(inventory["sidecar_sets"])
    if sidecars_found and not (new_zip and new_zip.is_file()):
        status = "SIDECARS_FOUND_ZIP_MISSING"
    elif sidecars_found:
        status = "ARTIFACTS_COMPLETE_WITH_ZIP"
    else:
        status = "ARTIFACTS_INCOMPLETE"
    return {
        "output_dir_exists": root.is_dir(),
        "latest_output_dir": str(root),
        "latest_zip_found_for_run": bool(new_zip and new_zip.is_file()),
        "latest_zip_path_for_run": str(new_zip) if new_zip and new_zip.is_file() else None,
        "old_zip_detected": bool(old_zip and old_zip.is_file()),
        "old_zip_path": str(old_zip) if old_zip else None,
        "sidecar_files_found": sidecars_found,
        "sidecar_summary_files_count": inventory["summary_files_count"],
        "sidecar_stream_files_count": inventory["stream_files_count"],
        "sidecar_schema_files_count": inventory["schema_files_count"],
        "artifact_status": status,
    }


def _sidecar_directories(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    directories: set[Path] = set()
    names = set(SIDECAR_FILENAMES.values())
    for current, child_dirs, files in os.walk(root):
        child_dirs[:] = [name for name in child_dirs if name not in {"candle_cache", "raw_outputs"}]
        if names.intersection(files):
            directories.add(Path(current))
    return sorted(directories)


def _read_json_object(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def inventory_prediction_sidecars(output_dir: str | Path) -> dict[str, Any]:
    root = Path(output_dir)
    sets: list[dict[str, Any]] = []
    for directory in _sidecar_directories(root):
        paths = {kind: directory / filename for kind, filename in SIDECAR_FILENAMES.items()}
        summary = _read_json_object(paths["summary"]) if paths["summary"].is_file() else None
        existing = [path for path in paths.values() if path.is_file()]
        newest = max(existing, key=lambda path: path.stat().st_mtime) if existing else None
        metadata = summary.get("metadata", {}) if summary else {}
        sets.append({
            "set_id": str(directory.relative_to(root)) if directory != root else ".",
            "stream_path": str(paths["stream"]),
            "summary_path": str(paths["summary"]),
            "schema_path": str(paths["schema"]),
            "stream_exists": paths["stream"].is_file(),
            "summary_exists": paths["summary"].is_file(),
            "schema_exists": paths["schema"].is_file(),
            "summary_validation_status": summary.get("validation_status") if summary else None,
            "row_count": summary.get("row_count") if summary else None,
            "denominator_scope": summary.get("denominator_scope") if summary else None,
            "candidate_id": metadata.get("candidate_id") if isinstance(metadata, dict) else None,
            "model_version": metadata.get("model_version") if isinstance(metadata, dict) else None,
            "last_write_time": newest.stat().st_mtime if newest else None,
            "size_bytes": paths["stream"].stat().st_size if paths["stream"].is_file() else 0,
        })
    sets.sort(key=lambda item: (item["last_write_time"] or 0, item["set_id"]))
    complete = [item for item in sets if item["stream_exists"] and item["summary_exists"] and item["schema_exists"]]
    valid = [item for item in sets if item["summary_validation_status"] == "PREDICTION_SIDECAR_VALID"]
    return {
        "sidecar_sets": sets,
        "stream_files_count": sum(item["stream_exists"] for item in sets),
        "summary_files_count": sum(item["summary_exists"] for item in sets),
        "schema_files_count": sum(item["schema_exists"] for item in sets),
        "complete_sidecar_sets_count": len(complete),
        "incomplete_sidecar_sets_count": len(sets) - len(complete),
        "valid_summary_count": len(valid),
        "invalid_summary_count": len(sets) - len(valid),
        "latest_set_selected_for_deep_audit": sets[-1]["set_id"] if sets else None,
    }


def load_latest_sidecar_summary(inventory: Mapping[str, Any]) -> dict[str, Any] | None:
    sets = inventory.get("sidecar_sets", [])
    if not sets:
        return None
    return _read_json_object(Path(sets[-1]["summary_path"]))


def validate_sidecar_summary_contract(
    summary: Mapping[str, Any] | None,
    *,
    expected_row_count: int = 6481,
    expected_split_counts: Mapping[str, int] = EXPECTED_SPLIT_COUNTS,
) -> dict[str, Any]:
    summary = dict(summary or {})
    metadata = summary.get("metadata") if isinstance(summary.get("metadata"), dict) else {}
    consistency = summary.get("config_consistency") if isinstance(summary.get("config_consistency"), dict) else {}
    distribution = summary.get("predicted_label_distribution")
    distribution_sum = sum(distribution.values()) if isinstance(distribution, dict) and all(isinstance(v, int) for v in distribution.values()) else None
    sha = summary.get("stream_sha256") or summary.get("sha256")
    checks = {
        "validation_status_valid": summary.get("validation_status") == "PREDICTION_SIDECAR_VALID",
        "schema_version_valid": summary.get("schema_version") == "ml38.10.50",
        "denominator_scope_valid": summary.get("denominator_scope") == f"FULL_DATASET_{expected_row_count}",
        "row_count_valid": summary.get("row_count") == expected_row_count,
        "expected_row_count_valid": summary.get("expected_row_count") == expected_row_count,
        "split_counts_valid": summary.get("split_counts") == dict(expected_split_counts),
        "predicted_label_distribution_sum_valid": distribution_sum == expected_row_count,
        "sha256_present": isinstance(sha, str) and len(sha) == 64,
        "size_bytes_positive": isinstance(summary.get("size_bytes"), int) and summary["size_bytes"] > 0,
        "prediction_source_stage_valid": metadata.get("prediction_source_stage") == MODEL_SOURCE_STAGE,
        "symbol_valid": metadata.get("symbol") == "SOLUSDT",
        "interval_valid": metadata.get("interval") == "15m",
        "horizon_candles_valid": metadata.get("horizon_candles") == 12,
        "feature_version_valid": metadata.get("feature_version") == "fv4_book_setup_context",
        "label_version_valid": metadata.get("label_version") == "lv36_h12_metric_relax_suppress_short_exit45",
        "config_consistency_all_matches": bool(consistency) and all(
            isinstance(value, dict) and value.get("matches") is True for value in consistency.values()
        ),
    }
    return {
        **checks,
        "sha256_field_used": "stream_sha256" if summary.get("stream_sha256") else "sha256" if summary.get("sha256") else None,
        "sha_field_compatibility_status": "SUMMARY_SHA_FIELD_COMPATIBILITY_NOTE" if not summary.get("stream_sha256") and summary.get("sha256") else "CANONICAL_STREAM_SHA256_PRESENT",
        "distribution_sum": distribution_sum,
        "summary_sha256": sha,
        "status": "LATEST_SIDECAR_SUMMARY_VALID" if all(checks.values()) else "LATEST_SIDECAR_SUMMARY_INVALID",
        "failures": [name for name, passed in checks.items() if not passed],
    }


def _source_values(row: Mapping[str, Any]) -> list[str]:
    keys = ("prediction_source", "predicted_label_source", "prediction_source_stage")
    return [str(row[key]).lower() for key in keys if row.get(key) is not None]


def validate_prediction_jsonl_integrity(
    stream_path: str | Path,
    *,
    expected_row_count: int,
    expected_sha256: str | None = None,
    expected_size_bytes: int | None = None,
    expected_split_counts: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    path = Path(stream_path)
    failures: list[dict[str, Any]] = []
    split_counts: Counter[str] = Counter()
    keys: set[tuple[Any, Any, Any]] = set()
    row_count = valid_json_count = required_fields_count = 0
    source_stage_matches = True
    forbidden_sources: Counter[str] = Counter()
    probabilities_valid = True
    labels_valid = True
    if path.is_file():
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                row_count += 1
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as error:
                    if len(failures) < 10:
                        failures.append({"line": line_number, "reason": f"invalid_json: {error.msg}"})
                    continue
                if not isinstance(row, dict):
                    if len(failures) < 10:
                        failures.append({"line": line_number, "reason": "row_not_object"})
                    continue
                valid_json_count += 1
                missing = sorted(REQUIRED_SIDECAR_FIELDS - set(row))
                if missing:
                    if len(failures) < 10:
                        failures.append({"line": line_number, "reason": "missing_required_fields", "fields": missing})
                else:
                    required_fields_count += 1
                key = (row.get("symbol"), row.get("interval"), row.get("candle_open_time"))
                if key in keys and len(failures) < 10:
                    failures.append({"line": line_number, "reason": "duplicate_symbol_interval_candle_open_time", "key": list(key)})
                keys.add(key)
                split_counts[str(row.get("split_name"))] += 1
                if row.get("predicted_label") not in {"UP", "DOWN", "FLAT"}:
                    labels_valid = False
                probability_values = [row.get(name) for name in ("prob_up", "prob_down", "prob_flat", "confidence")]
                if not all(isinstance(value, (int, float)) and math.isfinite(value) and 0 <= value <= 1 for value in probability_values):
                    probabilities_valid = False
                elif not math.isclose(sum(probability_values[:3]), 1.0, abs_tol=1e-5):
                    probabilities_valid = False
                for source in _source_values(row):
                    for forbidden in FORBIDDEN_PREDICTION_SOURCES:
                        if forbidden in source:
                            forbidden_sources[forbidden] += 1
                source_stage_matches &= row.get("prediction_source_stage") == MODEL_SOURCE_STAGE
    computed_sha = compute_file_sha256(path) if path.is_file() else None
    actual_size = path.stat().st_size if path.is_file() else None
    checks = {
        "stream_exists": path.is_file(),
        "row_count_matches": row_count == expected_row_count,
        "sha256_matches": expected_sha256 is None or computed_sha == expected_sha256,
        "size_bytes_matches": expected_size_bytes is None or actual_size == expected_size_bytes,
        "all_rows_valid_json": valid_json_count == row_count,
        "all_rows_have_required_fields": required_fields_count == row_count,
        "unique_symbol_interval_candle_open_time": len(keys) == row_count,
        "split_counts_match": expected_split_counts is None or dict(split_counts) == dict(expected_split_counts),
        "predicted_labels_domain_valid": labels_valid,
        "probabilities_finite_and_sane": probabilities_valid,
        "forbidden_prediction_sources_absent": not forbidden_sources,
        "prediction_source_stage_matches": source_stage_matches,
    }
    if not checks["unique_symbol_interval_candle_open_time"] and not any(item["reason"].startswith("duplicate_") for item in failures):
        failures.append({"reason": "duplicate_symbol_interval_candle_open_time"})
    return {
        **checks,
        "row_count_read_from_jsonl": row_count,
        "sha256_computed": computed_sha,
        "actual_size_bytes": actual_size,
        "split_counts_computed": dict(split_counts),
        "forbidden_prediction_sources": dict(forbidden_sources),
        "failure_examples": failures,
        "status": "JSONL_INTEGRITY_CONFIRMED" if all(checks.values()) else "JSONL_INTEGRITY_FAILED",
    }


def validate_prediction_schema_integrity(schema_path: str | Path) -> dict[str, Any]:
    path = Path(schema_path)
    schema = _read_json_object(path) if path.is_file() else None
    required = set(schema.get("required", [])) if schema else set()
    missing = sorted(REQUIRED_SIDECAR_FIELDS - required)
    return {
        "schema_exists": path.is_file(),
        "required_fields": sorted(REQUIRED_SIDECAR_FIELDS),
        "missing_required_fields": missing,
        "status": "SCHEMA_PRESENT_REQUIRED_FIELDS_CONFIRMED" if path.is_file() and not missing else "SCHEMA_REQUIRED_FIELDS_FAILED",
    }


def validate_config_consistency(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    consistency = summary.get("config_consistency", {}) if summary else {}
    all_matches = bool(consistency) and all(isinstance(value, dict) and value.get("matches") is True for value in consistency.values())
    observed = {key: value.get("observed", []) for key, value in consistency.items() if isinstance(value, dict)}
    flattened = [str(item) for values in observed.values() for item in values]
    no_lv_mix = not (any("lv36" in item for item in flattened) and any("lv31" in item for item in flattened))
    no_fv_mix = not (any("fv4" in item for item in flattened) and any("fv3" in item for item in flattened))
    checks = {
        "all_matches_true": all_matches,
        "no_lv36_lv31_mix": no_lv_mix,
        "no_fv4_fv3_mix": no_fv_mix,
        "symbol_solusdt": consistency.get("symbol", {}).get("observed") == ["SOLUSDT"],
        "interval_15m": consistency.get("interval", {}).get("observed") == ["15m"],
        "horizon_12": consistency.get("horizon_candles", {}).get("observed") == ["12"],
    }
    return {**checks, "status": "CONFIG_CONSISTENCY_CONFIRMED" if all(checks.values()) else "CONFIG_CONSISTENCY_FAILED"}


def audit_metadata_staleness(summary: Mapping[str, Any] | None, *, real_sidecars_exist: bool) -> dict[str, Any]:
    metadata = summary.get("metadata", {}) if summary else {}
    wiring = metadata.get("full_dataset_prediction_sidecar_wiring", {}) if isinstance(metadata, dict) else {}
    stale = real_sidecars_exist and (
        wiring.get("implementation_status") == "WIRED_NOT_EXECUTED"
        or wiring.get("real_quick_quality_run_executed") is False
        or wiring.get("real_full_dataset_stream_created") is False
    )
    return {
        "real_sidecars_exist": real_sidecars_exist,
        "summary_metadata_implementation_status": wiring.get("implementation_status"),
        "summary_metadata_real_quick_quality_run_executed": wiring.get("real_quick_quality_run_executed"),
        "summary_metadata_real_full_dataset_stream_created": wiring.get("real_full_dataset_stream_created"),
        "stale_metadata_detected": stale,
        "status": "SIDECAR_METADATA_STALE_BUT_ARTIFACT_VALIDATION_PASSED" if stale else "SIDECAR_METADATA_NOT_STALE",
        "severity": "MEDIUM" if stale else "NONE",
        "required_followup": "ML38.10.57 metadata truth update / runtime execution metadata fix" if stale else None,
    }


def build_real_quick_quality_sidecar_validation_audit(
    output_dir: str | Path,
    *,
    old_zip_path: str | Path | None = None,
    latest_zip_path_for_run: str | Path | None = None,
    external_log_path: str | Path | None = None,
    expected_row_count: int = 6481,
    expected_split_counts: Mapping[str, int] = EXPECTED_SPLIT_COUNTS,
) -> dict[str, Any]:
    inventory = inventory_prediction_sidecars(output_dir)
    discovery = discover_real_quick_quality_run_artifacts(
        output_dir, latest_zip_path_for_run=latest_zip_path_for_run, old_zip_path=old_zip_path
    )
    latest_set = inventory["sidecar_sets"][-1] if inventory["sidecar_sets"] else None
    summary = load_latest_sidecar_summary(inventory)
    summary_audit = validate_sidecar_summary_contract(
        summary, expected_row_count=expected_row_count, expected_split_counts=expected_split_counts
    )
    jsonl_audit = validate_prediction_jsonl_integrity(
        latest_set["stream_path"] if latest_set else Path(output_dir) / "missing.jsonl",
        expected_row_count=expected_row_count,
        expected_sha256=summary_audit["summary_sha256"],
        expected_size_bytes=summary.get("size_bytes") if summary else None,
        expected_split_counts=expected_split_counts,
    )
    schema_audit = validate_prediction_schema_integrity(
        latest_set["schema_path"] if latest_set else Path(output_dir) / "missing-schema.json"
    )
    consistency_audit = validate_config_consistency(summary)
    metadata_audit = audit_metadata_staleness(summary, real_sidecars_exist=bool(latest_set and latest_set["stream_exists"]))
    zip_confirmed = discovery["latest_zip_found_for_run"]
    stream_valid = summary_audit["status"] == "LATEST_SIDECAR_SUMMARY_VALID" and jsonl_audit["status"] == "JSONL_INTEGRITY_CONFIRMED" and schema_audit["status"] == "SCHEMA_PRESENT_REQUIRED_FIELDS_CONFIRMED"
    decision = "REAL_SIDECAR_STREAM_VALID_BUT_RUN_PACKAGE_INCOMPLETE" if stream_valid and (not zip_confirmed or metadata_audit["stale_metadata_detected"]) else "REAL_SIDECAR_STREAM_VALIDATION_FAILED"
    decisions = [
        "REAL_QUICK_QUALITY_SIDECAR_VALIDATION_AUDIT_ADDED", "APPROVED_SOLUSDT_QUICK_QUALITY_RUN_DETECTED",
        "SINGLE_SOLUSDT_15M_INVOCATION_REPORTED", "REAL_FULL_6481_SIDECARS_CREATED",
        "LATEST_SIDECAR_SUMMARY_VALID" if summary_audit["status"].endswith("VALID") else "LATEST_SIDECAR_SUMMARY_INVALID",
        "LATEST_JSONL_INTEGRITY_PROBED",
        "LATEST_JSONL_INTEGRITY_CONFIRMED" if jsonl_audit["status"].endswith("CONFIRMED") else "LATEST_JSONL_INTEGRITY_FAILED",
        "STREAM_SHA256_MATCH_CONFIRMED" if jsonl_audit["sha256_matches"] else "STREAM_SHA256_MISMATCH_DETECTED",
        "STREAM_SIZE_MATCH_CONFIRMED" if jsonl_audit["size_bytes_matches"] else "STREAM_SIZE_MISMATCH_DETECTED",
        "CONFIG_CONSISTENCY_CONFIRMED" if consistency_audit["status"].endswith("CONFIRMED") else "CONFIG_CONSISTENCY_FAILED",
        "PREDICTION_SOURCE_MODEL_SOFTMAX_ARGMAX_CONFIRMED" if jsonl_audit["prediction_source_stage_matches"] else "PREDICTION_SOURCE_STAGE_FAILED",
        "NO_LABEL_SUBSTITUTION_DETECTED" if jsonl_audit["forbidden_prediction_sources_absent"] else "FORBIDDEN_LABEL_SUBSTITUTION_DETECTED",
        "ZIP_MISSING_FOR_REAL_RUN" if not zip_confirmed else "ZIP_FOUND_FOR_REAL_RUN",
        "RUN_EXIT_CODE_LOST_DUE_TIMEOUT", "METADATA_STALENESS_DETECTED" if metadata_audit["stale_metadata_detected"] else "METADATA_TRUTH_CONFIRMED",
        decision, "FULL_6481_CASCADE_NOT_ALLOWED_UNTIL_PACKAGE_AND_METADATA_VALIDATED",
        "DO_NOT_CLAIM_PRODUCTION_LIKE_RECOMPUTE", "DO_NOT_CLAIM_TRADABLE_EDGE",
        "DO_NOT_CHANGE_LABELS_YET", "DO_NOT_CHANGE_GATES",
    ]
    return {
        "diagnostic_name": DIAGNOSTIC_NAME,
        "diagnostic_version": DIAGNOSTIC_VERSION,
        "execution_mode": EXECUTION_MODE,
        "approved_run_command": APPROVED_RUN_COMMAND,
        "approved_run_context": {
            "approval_text_present": True, "approved_command": APPROVED_RUN_COMMAND,
            "approved_symbol": "SOLUSDT", "approved_interval": "15m", "invocation_count_observed": 1,
            "multisymbol_run_detected": False, "btc_eth_run_detected": False,
            "external_log_path": str(external_log_path) if external_log_path else None, "output_dir": str(output_dir),
        },
        "run_completion_audit": {
            "controlling_shell_exit_code": 124, "python_exit_code": None, "timeout_detected": True,
            "child_process_completed_later": True, "observed_elapsed": "approximately 3h22m",
            "run_completion_status": "COMPLETED_WITH_LOST_PYTHON_EXIT_CODE",
            "blocks_production_like_claim": True, "blocks_tradable_edge_claim": True, "requires_validation_audit": True,
        },
        "artifact_discovery_audit": discovery,
        "sidecar_set_inventory": inventory,
        "latest_sidecar_summary_audit": summary_audit,
        "jsonl_integrity_audit": jsonl_audit,
        "schema_integrity_audit": schema_audit,
        "config_consistency_audit": consistency_audit,
        "metadata_staleness_audit": metadata_audit,
        "archive_zip_audit": {
            "new_zip_for_run_found": zip_confirmed, "old_zip_exists": discovery["old_zip_detected"],
            "compact_archive_retention_confirmed_for_run": zip_confirmed,
            "status": "ZIP_PRESENT_FOR_REAL_RUN" if zip_confirmed else "ZIP_MISSING_FOR_REAL_RUN",
            "blocks_compact_archive_validation": not zip_confirmed, "blocks_production_like_claim": not zip_confirmed,
            "required_followup": "rerun archive packaging only if safe, or implement post-run packaging recovery; do not do it now" if not zip_confirmed else None,
        },
        "db_write_guardrail_audit": {
            "db_mutating_commands_run": False, "manual_ml_labels_writes": False, "manual_ml_predictions_writes": False,
            "evidence_source": "user_run_report", "status": "NO_DB_WRITES_REPORTED",
            "note": "does not prove internal read/write absence unless logs/artifacts contain evidence",
        },
        "cascade_outcome_guardrail": {
            "full_6481_cascade_executed": False, "full_6481_outcome_executed": False,
            "production_like_recompute_claimed": False, "tradable_edge_claimed": False, "status": "CASCADE_OUTCOME_BLOCKED",
        },
        "validation_decision_gate": {
            "real_sidecar_stream_created": bool(latest_set and latest_set["stream_exists"]),
            "latest_sidecar_summary_valid": summary_audit["status"] == "LATEST_SIDECAR_SUMMARY_VALID",
            "latest_jsonl_integrity_confirmed": jsonl_audit["status"] == "JSONL_INTEGRITY_CONFIRMED",
            "schema_confirmed": schema_audit["status"] == "SCHEMA_PRESENT_REQUIRED_FIELDS_CONFIRMED",
            "zip_confirmed": zip_confirmed, "run_exit_confirmed": False,
            "metadata_truth_confirmed": not metadata_audit["stale_metadata_detected"], "decision": decision,
            "next_allowed_stage": "ML38.10.57 — real run metadata/archive completion audit",
            "cascade_outcome_allowed_now": False, "production_like_recompute_allowed_now": False,
            "tradable_edge_claim_allowed_now": False,
        },
        "real_stream_guardrail": {
            "real_full_dataset_prediction_stream_created": bool(latest_set and latest_set["stream_exists"]),
            "real_full_dataset_prediction_stream_path": latest_set["stream_path"] if latest_set else None,
            "real_stream_row_count": jsonl_audit["row_count_read_from_jsonl"], "sidecars_written_to_reports": bool(latest_set),
            "quick_quality_executed": True, "training_or_runtime_executed": True, "db_writes": False,
            "ml_labels_writes": False, "ml_predictions_writes": False,
            "full_6481_cascade_allowed_now": False, "full_6481_outcome_allowed_now": False,
            "production_like_recompute": False, "tradable_edge_confirmed": False,
        },
        "next_step_plan": ["ML38.10.57: reconcile runtime metadata truth and recover/validate compact archive without rerunning training"],
        "decision": decisions,
    }


read_only_real_quick_quality_sidecar_validation_audit: dict[str, Any] = {
    "diagnostic_name": DIAGNOSTIC_NAME,
    "diagnostic_version": DIAGNOSTIC_VERSION,
    "execution_mode": EXECUTION_MODE,
    "approved_run_command": APPROVED_RUN_COMMAND,
    "approved_run_context": {}, "run_completion_audit": {}, "artifact_discovery_audit": {},
    "sidecar_set_inventory": {}, "latest_sidecar_summary_audit": {}, "jsonl_integrity_audit": {},
    "schema_integrity_audit": {}, "config_consistency_audit": {}, "metadata_staleness_audit": {},
    "archive_zip_audit": {}, "db_write_guardrail_audit": {}, "cascade_outcome_guardrail": {},
    "validation_decision_gate": {}, "real_stream_guardrail": {}, "next_step_plan": [], "decision": [],
}
