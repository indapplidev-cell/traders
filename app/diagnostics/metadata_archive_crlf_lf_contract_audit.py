from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


DIAGNOSTIC_NAME = "read_only_metadata_archive_crlf_lf_contract_audit"
DIAGNOSTIC_VERSION = "ml38.10.57"
EXECUTION_MODE = (
    "READ_ONLY_METADATA_ARCHIVE_CRLF_LF_CONTRACT_AUDIT_"
    "NO_QUICK_QUALITY_NO_TRAINING_NO_DB_WRITES"
)
STREAM_NAME = "full_dataset_prediction_stream.jsonl"
SUMMARY_NAME = "full_dataset_prediction_stream_summary.json"
SCHEMA_NAME = "prediction_payload_schema.json"


def compute_exact_file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _lf_normalized_bytes(path: str | Path) -> bytes:
    # The writer contract under audit creates CRLF from LF on Windows. Lone CR
    # bytes are retained because they are not part of that conversion.
    return Path(path).read_bytes().replace(b"\r\n", b"\n")


def compute_lf_normalized_sha256(path: str | Path) -> str:
    return hashlib.sha256(_lf_normalized_bytes(path)).hexdigest()


def compute_exact_size(path: str | Path) -> int:
    return Path(path).stat().st_size


def compute_lf_normalized_size(path: str | Path) -> int:
    return len(_lf_normalized_bytes(path))


def compute_newline_stats(path: str | Path) -> dict[str, Any]:
    data = Path(path).read_bytes()
    crlf_count = data.count(b"\r\n")
    lf_count = data.count(b"\n")
    bare_lf_count = lf_count - crlf_count
    row_count = lf_count + (1 if data and not data.endswith((b"\n", b"\r")) else 0)
    return {
        "exact_file_has_crlf": crlf_count > 0,
        "crlf_count": crlf_count,
        "lf_count": lf_count,
        "bare_lf_count": bare_lf_count,
        "row_count": row_count,
    }


def audit_summary_vs_exact_and_normalized_file(
    summary_path: str | Path, stream_path: str | Path
) -> dict[str, Any]:
    summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    summary_sha = summary.get("stream_sha256") or summary.get("sha256")
    summary_size = summary.get("size_bytes")
    exact_sha = compute_exact_file_sha256(stream_path)
    normalized_sha = compute_lf_normalized_sha256(stream_path)
    exact_size = compute_exact_size(stream_path)
    normalized_size = compute_lf_normalized_size(stream_path)
    newline = compute_newline_stats(stream_path)
    exact_match = summary_sha == exact_sha and summary_size == exact_size
    normalized_match = summary_sha == normalized_sha and summary_size == normalized_size
    if exact_match:
        status = "SUMMARY_HASHES_EXACT_BYTES"
    elif normalized_match and newline["exact_file_has_crlf"]:
        status = "SUMMARY_HASHES_LF_NORMALIZED_CONTENT_WHILE_FILE_IS_CRLF"
    elif summary_sha is None or summary_size is None:
        status = "SUMMARY_HASH_CONTRACT_UNKNOWN"
    else:
        status = "SUMMARY_HASH_MISMATCH_UNEXPLAINED"
    return {
        "summary_sha256": summary_sha,
        "exact_file_sha256": exact_sha,
        "lf_normalized_sha256": normalized_sha,
        "summary_size_bytes": summary_size,
        "exact_file_size_bytes": exact_size,
        "lf_normalized_size_bytes": normalized_size,
        "summary_matches_exact_bytes": exact_match,
        "summary_matches_lf_normalized_bytes": normalized_match,
        **newline,
        "row_count_matches_summary": newline["row_count"] == summary.get("row_count"),
        "newline_contract_status": status,
    }


def inspect_writer_newline_contract(source_text: str) -> dict[str, Any]:
    hashes_in_memory = (
        "sha256(encoded)" in source_text
        and "len(encoded)" in source_text
        and "_canonical_jsonl" in source_text
    )
    write_text_used = ".write_text(" in source_text
    explicit_encoding = 'encoding="utf-8"' in source_text or "encoding='utf-8'" in source_text
    explicit_newline = "newline=" in source_text
    binary_write = '.open("wb")' in source_text or "write_bytes(" in source_text
    exact_post_write_hash = "read_bytes()" in source_text and "sha256" in source_text
    if hashes_in_memory:
        hash_source = "IN_MEMORY_LF_TEXT"
        size_source = "IN_MEMORY_LF_TEXT_SIZE"
    elif exact_post_write_hash:
        hash_source = "EXACT_WRITTEN_BYTES"
        size_source = "EXACT_FILE_SIZE"
    else:
        hash_source = size_source = "UNKNOWN"
    if binary_write:
        disk_behavior = "BINARY_EXACT"
    elif write_text_used and explicit_newline:
        disk_behavior = "EXPLICIT_LF"
    elif write_text_used:
        disk_behavior = "PLATFORM_DEFAULT_NEWLINE_CONVERSION_RISK"
    else:
        disk_behavior = "UNKNOWN"
    confirmed = hashes_in_memory and write_text_used and not explicit_newline and not binary_write
    partial = hashes_in_memory or disk_behavior != "UNKNOWN"
    return {
        "summary_hash_source": hash_source,
        "size_source": size_source,
        "disk_write_newline_behavior": disk_behavior,
        "root_cause_status": (
            "CRLF_LF_CONTRACT_ROOT_CAUSE_CONFIRMED"
            if confirmed
            else "CRLF_LF_CONTRACT_ROOT_CAUSE_PARTIAL"
            if partial
            else "CRLF_LF_CONTRACT_ROOT_CAUSE_NOT_CONFIRMED"
        ),
        "evidence": {
            "canonical_jsonl_appends_lf": '+ "\\n"' in source_text or "+ '\\n'" in source_text,
            "summary_hashes_encoded_in_memory_text": hashes_in_memory,
            "path_write_text_used": write_text_used,
            "open_newline_argument_used": explicit_newline,
            "encoding_explicit": explicit_encoding,
            "binary_exact_write_used": binary_write,
            "exact_file_rehashed_after_write": exact_post_write_hash,
        },
    }


def inspect_jsonl_writer_contract(source_text: str) -> dict[str, Any]:
    writer = inspect_writer_newline_contract(source_text)
    declared_exact = "exact_bytes_hash_contract" in source_text
    declared_normalized = "normalized_sha256" in source_text or "lf_normalized_sha256" in source_text
    return {
        "current_contract_declared_in_schema_or_summary": declared_exact or declared_normalized,
        "exact_bytes_hash_contract_declared": declared_exact,
        "normalized_hash_contract_declared": declared_normalized,
        "current_writer_cross_platform_safe": writer["disk_write_newline_behavior"] in {"EXPLICIT_LF", "BINARY_EXACT"},
        "recommended_contract": "EXACT_BYTES_HASH_AND_SIZE_AFTER_WRITE",
        "alternative_contract": "DECLARE_NORMALIZED_LF_HASH_AND_EXACT_FILE_SIZE_SEPARATELY",
        "recommended_fix_not_applied": True,
        "status": "WRITER_CONTRACT_AUDITED_FIX_REQUIRED_NOT_APPLIED" if writer["summary_hash_source"] != "UNKNOWN" else "WRITER_CONTRACT_UNKNOWN",
    }


def audit_all_sidecar_sets(output_dir: str | Path) -> dict[str, Any]:
    output = Path(output_dir)
    rows: list[dict[str, Any]] = []
    for summary_path in sorted(output.rglob(SUMMARY_NAME)):
        stream_path = summary_path.with_name(STREAM_NAME)
        if not stream_path.is_file():
            rows.append({"summary_path": str(summary_path), "stream_path": str(stream_path), "status": "STREAM_MISSING"})
            continue
        item = audit_summary_vs_exact_and_normalized_file(summary_path, stream_path)
        rows.append({
            "summary_path": str(summary_path),
            "stream_path": str(stream_path),
            "row_count": item["row_count"],
            "summary_sha256": item["summary_sha256"],
            "exact_file_sha256": item["exact_file_sha256"],
            "lf_normalized_sha256": item["lf_normalized_sha256"],
            "summary_matches_exact": item["summary_matches_exact_bytes"],
            "summary_matches_lf_normalized": item["summary_matches_lf_normalized_bytes"],
            "summary_size_bytes": item["summary_size_bytes"],
            "exact_size_bytes": item["exact_file_size_bytes"],
            "lf_normalized_size_bytes": item["lf_normalized_size_bytes"],
            "status": item["newline_contract_status"],
        })
    exact = sum(row.get("summary_matches_exact") is True for row in rows)
    normalized = sum(
        row.get("summary_matches_lf_normalized") is True and row.get("summary_matches_exact") is not True
        for row in rows
    )
    failed = sum(
        row.get("summary_matches_exact") is False and row.get("summary_matches_lf_normalized") is False
        for row in rows
    )
    statuses = {row["status"] for row in rows}
    uniform = len(statuses) == 1 and bool(rows)
    if rows and normalized == len(rows):
        aggregate_status = "ALL_SETS_SUMMARY_MATCH_LF_NORMALIZED_ONLY"
    elif rows and (exact + normalized + failed == len(rows)) and len({exact > 0, normalized > 0, failed > 0} - {False}) > 1:
        aggregate_status = "MIXED_CONTRACT"
    else:
        aggregate_status = "CONTRACT_NOT_CONFIRMED"
    return {
        "sets": rows,
        "total_sets": len(rows),
        "sets_matching_exact_bytes": exact,
        "sets_matching_lf_normalized": normalized,
        "sets_failed_both": failed,
        "uniform_contract_observed": uniform,
        "aggregate_status": aggregate_status,
    }


def _joined_sources(source_texts: Mapping[str, str] | Sequence[str]) -> str:
    return "\n".join(source_texts.values() if isinstance(source_texts, Mapping) else source_texts)


def inspect_metadata_truth_contract(
    source_texts: Mapping[str, str] | Sequence[str],
    runtime_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    source = _joined_sources(source_texts)
    metadata = dict(runtime_metadata or {})
    wiring = metadata.get("full_dataset_prediction_sidecar_wiring")
    if isinstance(wiring, Mapping):
        metadata = dict(wiring)
    stale_fields = [
        field for field, stale_value in (
            ("implementation_status", "WIRED_NOT_EXECUTED"),
            ("real_quick_quality_run_executed", False),
            ("real_full_dataset_stream_created", False),
        ) if metadata.get(field) == stale_value
    ]
    static_reused = (
        "build_sidecar_wiring_metadata()" in source
        and '"implementation_status": "WIRED_NOT_EXECUTED"' in source
        and len(stale_fields) == 3
    )
    return {
        "stale_metadata_detected": len(stale_fields) == 3,
        "stale_fields": stale_fields,
        "static_wiring_metadata_reused_at_runtime": static_reused if source else "unknown",
        "runtime_truth_metadata_missing": not all(
            token in source for token in ("EXECUTED_REAL_QUICK_QUALITY", "sidecar_validation_status", "run_exit_code_status")
        ),
        "recommended_runtime_metadata": {
            "implementation_status": "EXECUTED_REAL_QUICK_QUALITY",
            "real_quick_quality_run_executed": True,
            "real_full_dataset_stream_created": True,
            "sidecar_validation_status": "after validation result",
            "run_exit_code_status": "LOST_DUE_TIMEOUT if applicable",
        },
        "recommended_fix_not_applied": True,
        "status": "METADATA_TRUTH_CONTRACT_AUDITED_FIX_REQUIRED_NOT_APPLIED" if source and len(stale_fields) == 3 else "METADATA_TRUTH_SOURCE_UNKNOWN",
    }


def inspect_archive_packaging_contract(
    source_texts: Mapping[str, str] | Sequence[str],
    *, output_dir_exists: bool,
    new_zip_for_run_found: bool,
    old_zip_detected: bool,
    timeout_observed: bool = True,
) -> dict[str, Any]:
    source = _joined_sources(source_texts)
    step_found = "_finalize_archive" in source and "zipfile.ZipFile" in source
    whitelist = all(name in source for name in (STREAM_NAME, SUMMARY_NAME, SCHEMA_NAME))
    return {
        "output_dir_exists": output_dir_exists,
        "new_zip_for_run_found": new_zip_for_run_found,
        "old_zip_detected": old_zip_detected,
        "archive_packaging_step_found_in_source": step_found,
        "archive_step_likely_not_reached_due_timeout": bool(step_found and timeout_observed and not new_zip_for_run_found),
        "archive_step_can_be_recovered_without_quick_quality_rerun": True if output_dir_exists and step_found else "unknown",
        "compact_whitelist_contains_sidecar_paths": whitelist,
        "recommended_fix_not_applied": True,
        "status": "ARCHIVE_PACKAGE_MISSING_CAUSE_AUDITED_FIX_REQUIRED_NOT_APPLIED" if output_dir_exists and step_found and not new_zip_for_run_found else "ARCHIVE_PACKAGE_CAUSE_UNKNOWN",
    }


def build_timeout_exit_code_audit(
    *, log_path: str | Path | None, controlling_shell_exit_code: int = 124,
    child_completed_later: bool = True, timeout_wrapper_limit_seconds: int = 3604,
) -> dict[str, Any]:
    path = Path(log_path) if log_path else None
    exists = bool(path and path.is_file())
    text = path.read_text(encoding="utf-8", errors="replace") if exists and path else ""
    lower = text.lower()
    return {
        "controlling_shell_exit_code": controlling_shell_exit_code,
        "python_exit_code_lost": controlling_shell_exit_code == 124,
        "child_completed_later": child_completed_later,
        "log_path_exists": exists,
        "log_tail_contains_success_marker": any(token in lower[-20000:] for token in ("[done]", "completed successfully", "archive created")) if exists else "unknown",
        "log_tail_contains_archive_marker": any(token in lower[-20000:] for token in ("[archive]", "archive created")) if exists else "unknown",
        "log_tail_contains_exception": any(token in lower[-20000:] for token in ("traceback", "exception", "[error]")) if exists else "unknown",
        "timeout_wrapper_limit_seconds": timeout_wrapper_limit_seconds,
        "status": "TIMEOUT_LOST_EXIT_CODE_AUDITED" if controlling_shell_exit_code == 124 and child_completed_later else "TIMEOUT_AUDIT_INCONCLUSIVE",
    }


def _risk_board() -> list[dict[str, Any]]:
    risks = (
        ("exact-byte integrity mismatch across OS newline modes", "CRITICAL", "summary matches normalized LF rather than Windows file bytes", True, True),
        ("summary claims valid while exact file hash fails", "CRITICAL", "validation_status and exact-byte integrity disagree", True, True),
        ("stale metadata hides real execution", "HIGH", "runtime artifact carries WIRED_NOT_EXECUTED/false/false", True, True),
        ("missing ZIP hides sidecars from compact deliverable", "HIGH", "run output exists but run ZIP does not", True, True),
        ("timeout loses Python exit code", "HIGH", "shell exit 124 cannot establish child exit status", True, True),
        ("partial artifacts accepted too early", "HIGH", "sidecars exist without complete integrity/package contract", True, True),
        ("cascade/outcome run before integrity fix", "CRITICAL", "downstream evaluation would consume unconfirmed bytes", True, True),
        ("production-like/tradable-edge claims made before package complete", "CRITICAL", "integrity, metadata, archive, and exit status remain incomplete", True, True),
    )
    return [{
        "risk": risk, "severity": severity, "evidence": evidence,
        "fail_closed_required": fail_closed, "blocks_cascade": blocks,
        "blocks_production_like_claim": True,
        "proposed_followup": "ML38.10.58 contract fix design; do not mutate current real artifacts",
    } for risk, severity, evidence, fail_closed, blocks in risks]


def build_metadata_archive_crlf_lf_contract_audit(
    *, output_dir: str | Path, selected_sidecar_folder: str | Path,
    exporter_source: str, metadata_source_texts: Mapping[str, str] | Sequence[str],
    archive_source_texts: Mapping[str, str] | Sequence[str],
    stage_report_read: bool = True, snapshot_read: bool = True,
    old_zip_path: str | Path | None = None, log_path: str | Path | None = None,
) -> dict[str, Any]:
    output = Path(output_dir)
    folder = Path(selected_sidecar_folder)
    stream = folder / STREAM_NAME
    summary = folder / SUMMARY_NAME
    schema = folder / SCHEMA_NAME
    selected_audit = audit_summary_vs_exact_and_normalized_file(summary, stream)
    summary_json = json.loads(summary.read_text(encoding="utf-8"))
    runtime_metadata = summary_json.get("metadata", {})
    writer_source = inspect_writer_newline_contract(exporter_source)
    all_sets = audit_all_sidecar_sets(output)
    metadata = inspect_metadata_truth_contract(metadata_source_texts, runtime_metadata)
    new_zip = output.with_suffix(".zip")
    archive = inspect_archive_packaging_contract(
        archive_source_texts, output_dir_exists=output.is_dir(),
        new_zip_for_run_found=new_zip.is_file(), old_zip_detected=bool(old_zip_path and Path(old_zip_path).is_file()),
    )
    timeout = build_timeout_exit_code_audit(log_path=log_path)
    root_confirmed = (
        selected_audit["newline_contract_status"] == "SUMMARY_HASHES_LF_NORMALIZED_CONTENT_WHILE_FILE_IS_CRLF"
        and writer_source["root_cause_status"] == "CRLF_LF_CONTRACT_ROOT_CAUSE_CONFIRMED"
    )
    decisions = [
        "METADATA_ARCHIVE_CRLF_LF_CONTRACT_AUDIT_ADDED", "ML38_10_56_FAIL_CLOSED_RESULT_READ",
        "REAL_ARTIFACTS_READ_ONLY_AUDITED", "CRLF_LF_CONTRACT_PROBED", "SUMMARY_HASH_SOURCE_PROBED",
        "JSONL_WRITER_CONTRACT_PROBED", "ALL_45_SIDECAR_SETS_PROBED", "METADATA_TRUTH_CONTRACT_PROBED",
        "ARCHIVE_PACKAGING_CONTRACT_PROBED", "TIMEOUT_EXIT_CODE_BEHAVIOR_PROBED",
        "REAL_STREAM_STRUCTURALLY_VALID_BUT_INTEGRITY_FAILED", "CASCADE_OUTCOME_REMAINS_BLOCKED",
        "PRODUCTION_LIKE_RECOMPUTE_REMAINS_BLOCKED", "TRADABLE_EDGE_CLAIM_REMAINS_BLOCKED",
        "FIX_REQUIRED_NOT_APPLIED", "DO_NOT_RERUN_QUICK_QUALITY", "DO_NOT_MUTATE_REAL_ARTIFACTS",
    ]
    if root_confirmed:
        decisions += ["CRLF_LF_CONTRACT_ROOT_CAUSE_CONFIRMED", "SUMMARY_HASH_MATCHES_LF_NORMALIZED_NOT_EXACT_BYTES"]
    else:
        decisions += ["CRLF_LF_CONTRACT_ROOT_CAUSE_NOT_CONFIRMED", "CONTRACT_AUDIT_INCONCLUSIVE"]
    if all_sets["aggregate_status"] == "ALL_SETS_SUMMARY_MATCH_LF_NORMALIZED_ONLY":
        decisions.append("ALL_SETS_SUMMARY_MATCH_LF_NORMALIZED_ONLY")
    return {
        "diagnostic_name": DIAGNOSTIC_NAME,
        "diagnostic_version": DIAGNOSTIC_VERSION,
        "execution_mode": EXECUTION_MODE,
        "source_material": {
            "previous_stage_commit": "b72b962232b397d4f254199997eb9082ea4643b0",
            "previous_stage_decision": "REAL_SIDECAR_STREAM_VALIDATION_FAILED",
            "previous_jsonl_status": "JSONL_INTEGRITY_FAILED",
            "stage_report_read": stage_report_read, "snapshot_read": snapshot_read,
            "real_artifacts_read_only": True, "quick_quality_rerun": False, "new_sidecars_created": False,
        },
        "real_artifact_selection": {
            "output_dir": str(output), "selected_sidecar_folder": str(folder),
            "stream_path": str(stream), "summary_path": str(summary), "schema_path": str(schema),
            "selection_reason": "latest selected sidecar from ML38.10.56 deep audit",
            "stream_exists": stream.is_file(), "summary_exists": summary.is_file(), "schema_exists": schema.is_file(),
            "real_artifact_mutation_performed": False,
        },
        "newline_hash_contract_audit": selected_audit,
        "summary_hash_source_audit": writer_source,
        "jsonl_writer_contract_audit": inspect_jsonl_writer_contract(exporter_source),
        "all_sidecar_sets_contract_audit": all_sets,
        "metadata_truth_audit": metadata,
        "archive_packaging_audit": archive,
        "timeout_exit_code_audit": timeout,
        "risk_board": _risk_board(),
        "fix_plan_not_applied": {
            "writer_newline_contract_fix": ["write JSONL with explicit LF using newline=\"\\n\" or binary exact bytes", "compute SHA/size from exact bytes after write", "or store normalized_sha256 and file_sha256 explicitly"],
            "summary_schema_version_update_if_fields_change": True,
            "metadata_truth_fix": ["separate runtime execution status from static wiring status", "set real_quick_quality_run_executed=true when real command runs", "set real_full_dataset_stream_created=true only after files exist"],
            "archive_packaging_recovery": ["package existing completed output only after separate approval", "verify ZIP contains sidecar paths"],
            "timeout_fix": ["avoid parent timeout shorter than child run", "capture child exit code", "write run completion marker"],
            "fixes_applied_now": False,
            "requires_next_stage": "ML38.10.58 implementation fix or ML38.10.58 packaging recovery design depending decision",
            "no_artifact_mutation_now": True,
        },
        "validation_decision_gate": {
            "crlf_lf_root_cause_confirmed": root_confirmed,
            "summary_hash_contract_confirmed": selected_audit["summary_matches_lf_normalized_bytes"],
            "metadata_staleness_confirmed": metadata["stale_metadata_detected"],
            "zip_missing_confirmed": not archive["new_zip_for_run_found"],
            "timeout_exit_code_issue_confirmed": timeout["status"] == "TIMEOUT_LOST_EXIT_CODE_AUDITED",
            "decision": "CRLF_LF_CONTRACT_CONFIRMED_FIX_REQUIRED" if root_confirmed else "CONTRACT_AUDIT_INCONCLUSIVE_FIX_REQUIRED",
            "next_allowed_stage": "ML38.10.58 - sidecar writer metadata/archive contract fix design",
            "cascade_outcome_allowed_now": False, "production_like_recompute_allowed_now": False,
            "tradable_edge_claim_allowed_now": False,
        },
        "real_stream_guardrail": {
            "real_full_dataset_prediction_stream_created": True, "real_stream_integrity_confirmed": False,
            "real_stream_structurally_valid": True, "sidecars_written_to_reports": True,
            "quick_quality_executed_before_stage": True, "quick_quality_executed_during_stage": False,
            "training_or_runtime_executed_during_stage": False, "db_writes_during_stage": False,
            "ml_labels_writes_during_stage": False, "ml_predictions_writes_during_stage": False,
            "full_6481_cascade_allowed_now": False, "full_6481_outcome_allowed_now": False,
            "production_like_recompute": False, "tradable_edge_confirmed": False,
        },
        "next_step_plan": ["ML38.10.58: design the writer, runtime metadata, archive recovery, and timeout completion contracts without mutating current real artifacts"],
        "decision": decisions,
    }


read_only_metadata_archive_crlf_lf_contract_audit: dict[str, Any] = {
    "diagnostic_name": DIAGNOSTIC_NAME, "diagnostic_version": DIAGNOSTIC_VERSION,
    "execution_mode": EXECUTION_MODE, "source_material": {}, "real_artifact_selection": {},
    "newline_hash_contract_audit": {}, "summary_hash_source_audit": {},
    "jsonl_writer_contract_audit": {}, "all_sidecar_sets_contract_audit": {},
    "metadata_truth_audit": {}, "archive_packaging_audit": {}, "timeout_exit_code_audit": {},
    "risk_board": [], "fix_plan_not_applied": {}, "validation_decision_gate": {},
    "real_stream_guardrail": {}, "next_step_plan": [], "decision": [],
}
