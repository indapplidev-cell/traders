from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

from app.diagnostics.metadata_archive_crlf_lf_contract_audit import (
    EXECUTION_MODE,
    audit_all_sidecar_sets,
    audit_summary_vs_exact_and_normalized_file,
    build_metadata_archive_crlf_lf_contract_audit,
    build_timeout_exit_code_audit,
    compute_exact_file_sha256,
    compute_lf_normalized_sha256,
    compute_lf_normalized_size,
    compute_newline_stats,
    inspect_archive_packaging_contract,
    inspect_metadata_truth_contract,
    inspect_writer_newline_contract,
    read_only_metadata_archive_crlf_lf_contract_audit,
)


WRITER_SOURCE = '''
def _canonical_jsonl(rows):
    return "".join(str(row) + "\\n" for row in rows)
def write(path, rows):
    encoded = _canonical_jsonl(rows).encode("utf-8")
    summary = {"sha256": sha256(encoded).hexdigest(), "size_bytes": len(encoded)}
    path.write_text(_canonical_jsonl(rows), encoding="utf-8")
'''
METADATA_SOURCE = '''
def build_sidecar_wiring_metadata():
    return {"implementation_status": "WIRED_NOT_EXECUTED",
            "real_quick_quality_run_executed": False,
            "real_full_dataset_stream_created": False}
metadata["full_dataset_prediction_sidecar_wiring"] = build_sidecar_wiring_metadata()
'''
ARCHIVE_SOURCE = '''
def _finalize_archive():
    zipfile.ZipFile("run.zip", "w")
PREDICTION_SIDECAR_WHITELIST_PATHS = (
 "full_dataset_prediction_stream.jsonl",
 "full_dataset_prediction_stream_summary.json",
 "prediction_payload_schema.json")
'''


def _sidecar(tmp_path: Path, name: str = "candidate") -> Path:
    folder = tmp_path / name / "prediction_payloads"
    folder.mkdir(parents=True)
    lf = b'{"row":1}\n{"row":2}\n'
    stream = folder / "full_dataset_prediction_stream.jsonl"
    stream.write_bytes(lf.replace(b"\n", b"\r\n"))
    summary = {
        "row_count": 2,
        "sha256": hashlib.sha256(lf).hexdigest(),
        "size_bytes": len(lf),
        "metadata": {"full_dataset_prediction_sidecar_wiring": {
            "implementation_status": "WIRED_NOT_EXECUTED",
            "real_quick_quality_run_executed": False,
            "real_full_dataset_stream_created": False,
        }},
    }
    (folder / "full_dataset_prediction_stream_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (folder / "prediction_payload_schema.json").write_text("{}", encoding="utf-8")
    return folder


def test_audit_block_and_execution_mode_exist() -> None:
    assert read_only_metadata_archive_crlf_lf_contract_audit["diagnostic_name"] == "read_only_metadata_archive_crlf_lf_contract_audit"
    assert read_only_metadata_archive_crlf_lf_contract_audit["execution_mode"] == EXECUTION_MODE


def test_crlf_exact_and_normalized_hash_size_contract(tmp_path: Path) -> None:
    folder = _sidecar(tmp_path)
    stream = folder / "full_dataset_prediction_stream.jsonl"
    summary = folder / "full_dataset_prediction_stream_summary.json"
    audit = audit_summary_vs_exact_and_normalized_file(summary, stream)
    assert compute_exact_file_sha256(stream) != compute_lf_normalized_sha256(stream)
    assert audit["summary_matches_exact_bytes"] is False
    assert audit["summary_matches_lf_normalized_bytes"] is True
    assert audit["exact_file_size_bytes"] != compute_lf_normalized_size(stream)
    assert audit["lf_normalized_size_bytes"] == audit["summary_size_bytes"]
    assert audit["newline_contract_status"] == "SUMMARY_HASHES_LF_NORMALIZED_CONTENT_WHILE_FILE_IS_CRLF"


def test_newline_stats_count_crlf_rows(tmp_path: Path) -> None:
    stream = _sidecar(tmp_path) / "full_dataset_prediction_stream.jsonl"
    stats = compute_newline_stats(stream)
    assert stats == {"exact_file_has_crlf": True, "crlf_count": 2, "lf_count": 2, "bare_lf_count": 0, "row_count": 2}


def test_writer_source_and_fix_contract_are_represented() -> None:
    audit = inspect_writer_newline_contract(WRITER_SOURCE)
    assert audit["summary_hash_source"] == "IN_MEMORY_LF_TEXT"
    assert audit["size_source"] == "IN_MEMORY_LF_TEXT_SIZE"
    assert audit["disk_write_newline_behavior"] == "PLATFORM_DEFAULT_NEWLINE_CONVERSION_RISK"
    assert audit["root_cause_status"] == "CRLF_LF_CONTRACT_ROOT_CAUSE_CONFIRMED"


def test_all_sidecars_can_be_uniform_lf_normalized_only(tmp_path: Path) -> None:
    _sidecar(tmp_path, "one")
    _sidecar(tmp_path, "two")
    audit = audit_all_sidecar_sets(tmp_path)
    assert audit["total_sets"] == 2
    assert audit["sets_matching_exact_bytes"] == 0
    assert audit["sets_matching_lf_normalized"] == 2
    assert audit["sets_failed_both"] == 0
    assert audit["uniform_contract_observed"] is True
    assert audit["aggregate_status"] == "ALL_SETS_SUMMARY_MATCH_LF_NORMALIZED_ONLY"


def test_metadata_archive_and_timeout_contracts(tmp_path: Path) -> None:
    metadata = inspect_metadata_truth_contract([METADATA_SOURCE], {
        "implementation_status": "WIRED_NOT_EXECUTED",
        "real_quick_quality_run_executed": False,
        "real_full_dataset_stream_created": False,
    })
    assert metadata["stale_metadata_detected"] is True
    assert metadata["static_wiring_metadata_reused_at_runtime"] is True
    archive = inspect_archive_packaging_contract(
        [ARCHIVE_SOURCE], output_dir_exists=True, new_zip_for_run_found=False, old_zip_detected=True
    )
    assert archive["new_zip_for_run_found"] is False
    assert archive["compact_whitelist_contains_sidecar_paths"] is True
    log = tmp_path / "run.log"
    log.write_text("child output stopped before archive", encoding="utf-8")
    timeout = build_timeout_exit_code_audit(log_path=log)
    assert timeout["controlling_shell_exit_code"] == 124
    assert timeout["python_exit_code_lost"] is True
    assert timeout["status"] == "TIMEOUT_LOST_EXIT_CODE_AUDITED"


def test_complete_synthetic_audit_blocks_downstream_claims(tmp_path: Path) -> None:
    folder = _sidecar(tmp_path)
    old_zip = tmp_path / "old.zip"
    old_zip.write_bytes(b"old")
    log = tmp_path / "run.log"
    log.write_text("launch", encoding="utf-8")
    audit = build_metadata_archive_crlf_lf_contract_audit(
        output_dir=tmp_path, selected_sidecar_folder=folder,
        exporter_source=WRITER_SOURCE, metadata_source_texts=[METADATA_SOURCE],
        archive_source_texts=[ARCHIVE_SOURCE], old_zip_path=old_zip, log_path=log,
    )
    assert audit["jsonl_writer_contract_audit"]["recommended_fix_not_applied"] is True
    assert audit["jsonl_writer_contract_audit"]["status"] == "WRITER_CONTRACT_AUDITED_FIX_REQUIRED_NOT_APPLIED"
    gate = audit["validation_decision_gate"]
    assert gate["decision"] == "CRLF_LF_CONTRACT_CONFIRMED_FIX_REQUIRED"
    assert gate["cascade_outcome_allowed_now"] is False
    assert gate["production_like_recompute_allowed_now"] is False
    assert gate["tradable_edge_claim_allowed_now"] is False


def test_tests_only_write_under_tmp_path_and_never_launch_runtime() -> None:
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    calls = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert "subprocess" not in imports
    assert "run_fv3_cached_tuning" not in calls
    forbidden_runtime_flag = "quick" + "-quality"
    forbidden_reports_path = "Path(" + chr(34) + "reports"
    assert forbidden_runtime_flag not in source
    assert forbidden_reports_path not in source
