from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from app.experiments.prediction_sidecar_exporter import (
    BYTE_SIZE_CONTRACT,
    HASH_CONTRACT,
    LINE_ENDING_CONTRACT,
    SIDECAR_SCHEMA_VERSION,
    WRITER_CONTRACT_VERSION,
    build_archive_status_metadata,
    validate_prediction_sidecar_file_contract,
    write_prediction_sidecar_artifacts,
)


DIAGNOSTIC_NAME = "post_fix_sidecar_fixture_validation"
DIAGNOSTIC_VERSION = "ml38.10.59"
EXECUTION_MODE = (
    "SYNTHETIC_TMP_PATH_FIXTURE_VALIDATION_NO_QUICK_QUALITY_NO_TRAINING_NO_DB_WRITES"
)


def build_synthetic_prediction_rows() -> list[dict[str, Any]]:
    """Return three explicit model-output fixtures with no actual-label fields."""
    probabilities = (
        ("UP", 0.80, 0.10, 0.10),
        ("DOWN", 0.15, 0.75, 0.10),
        ("FLAT", 0.20, 0.20, 0.60),
    )
    splits = ("train", "val", "test")
    rows: list[dict[str, Any]] = []
    for index, (predicted_label, prob_up, prob_down, prob_flat) in enumerate(probabilities):
        rows.append(
            {
                "symbol": "FIXTUREUSDT",
                "interval": "15m",
                "candle_open_time": f"2026-01-01T00:{index:02d}:00+00:00",
                "dataset_row_index": index,
                "split_name": splits[index],
                "split_row_index": 0,
                "split_total_rows": 1,
                "feature_version": "fixture_feature_v1",
                "label_version": "fixture_label_v1",
                "horizon_candles": 12,
                "config_id": "fixture_config_ml38_10_59",
                "model_name": "synthetic_fixture_model",
                "model_version": "fixture_model_v1",
                "run_id": "fixture_run_ml38_10_59",
                "candidate_id": "fixture_candidate_ml38_10_59",
                "predicted_label": predicted_label,
                "prediction_source_stage": "synthetic_model_probability_argmax",
                "predicted_label_source": "model_probability_argmax",
                "prob_up": prob_up,
                "prob_down": prob_down,
                "prob_flat": prob_flat,
                "confidence": max(prob_up, prob_down, prob_flat),
            }
        )
    return rows


def create_tmp_sidecar_fixture(output_dir: str | Path) -> dict[str, Any]:
    """Generate sidecars only below the caller-owned fixture directory."""
    output_path = Path(output_dir)
    if not output_path.is_dir():
        raise ValueError("fixture output_dir must be an existing temporary directory")
    rows = build_synthetic_prediction_rows()
    return write_prediction_sidecar_artifacts(
        output_path,
        rows,
        metadata={
            "config_id": "fixture_config_ml38_10_59",
            "model_version": "fixture_model_v1",
            "feature_version": "fixture_feature_v1",
            "label_version": "fixture_label_v1",
            "candidate_id": "fixture_candidate_ml38_10_59",
            "run_id": "fixture_run_ml38_10_59",
            "symbol": "FIXTUREUSDT",
            "interval": "15m",
            "horizon_candles": 12,
            "real_quick_quality_run_executed": None,
            "archive_expected": None,
            "fixture_only": True,
        },
        expected_row_count=len(rows),
        denominator_scope="SYNTHETIC_FIXTURE_ROWS_3",
        require_field_contract=False,
    )


def compute_exact_sha256(path: str | Path) -> str:
    return sha256(Path(path).read_bytes()).hexdigest()


def compute_exact_size(path: str | Path) -> int:
    return len(Path(path).read_bytes())


def count_line_endings(path: str | Path) -> dict[str, Any]:
    exact = Path(path).read_bytes()
    crlf_count = exact.count(b"\r\n")
    lf_count = exact.count(b"\n")
    return {
        "crlf_count": crlf_count,
        "bare_lf_count": lf_count - crlf_count,
        "generated_stream_has_crlf": crlf_count > 0,
        "generated_stream_has_bare_lf": lf_count > crlf_count,
        "stray_cr_count": exact.replace(b"\r\n", b"").count(b"\r"),
    }


def validate_fixture_exact_byte_contract(
    summary_path: str | Path, stream_path: str | Path
) -> dict[str, Any]:
    summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    exact = Path(stream_path).read_bytes()
    file_contract = validate_prediction_sidecar_file_contract(stream_path, summary)
    normalized_hash = sha256(exact.replace(b"\r\n", b"\n")).hexdigest()
    return {
        **file_contract,
        "summary_sha256": summary.get("sha256"),
        "summary_size_bytes": summary.get("size_bytes"),
        "lf_normalized_sha256": normalized_hash,
        "lf_normalized_equals_exact": normalized_hash == file_contract["exact_file_sha256"],
        "contract_fields": {
            "hash_contract": summary.get("hash_contract"),
            "line_ending_contract": summary.get("line_ending_contract"),
            "byte_size_contract": summary.get("byte_size_contract"),
            "writer_contract_version": summary.get("writer_contract_version"),
        },
    }


def build_legacy_normalized_only_fixture(tmp_path: str | Path) -> dict[str, str]:
    root = Path(tmp_path)
    if not root.is_dir():
        raise ValueError("legacy fixture root must be an existing temporary directory")
    stream_path = root / "legacy_normalized_only.jsonl"
    summary_path = root / "legacy_normalized_only_summary.json"
    exact = b'{"fixture":1}\r\n{"fixture":2}\r\n'
    normalized = exact.replace(b"\r\n", b"\n")
    stream_path.write_bytes(exact)
    summary_path.write_bytes(
        (
            json.dumps(
                {"sha256": sha256(normalized).hexdigest(), "size_bytes": len(normalized)},
                indent=2,
            )
            + "\n"
        ).encode("utf-8")
    )
    return {"stream_path": str(stream_path), "summary_path": str(summary_path)}


def validate_legacy_normalized_only_fails_closed(
    summary_path: str | Path, stream_path: str | Path
) -> dict[str, Any]:
    before_hash = compute_exact_sha256(stream_path)
    before_size = compute_exact_size(stream_path)
    summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    contract = validate_prediction_sidecar_file_contract(stream_path, summary)
    after_hash = compute_exact_sha256(stream_path)
    after_size = compute_exact_size(stream_path)
    return {
        **contract,
        "exact_sha256_before_validation": before_hash,
        "exact_sha256_after_validation": after_hash,
        "exact_size_before_validation": before_size,
        "exact_size_after_validation": after_size,
        "fixture_mutated_during_validation": (before_hash, before_size)
        != (after_hash, after_size),
    }


def build_post_fix_sidecar_fixture_validation(tmp_path: str | Path) -> dict[str, Any]:
    root = Path(tmp_path)
    fixture_root = root / "post_fix_fixture"
    legacy_root = root / "legacy_fixture"
    fixture_root.mkdir()
    legacy_root.mkdir()

    result = create_tmp_sidecar_fixture(fixture_root)
    paths = {name: Path(value) for name, value in result["paths"].items()}
    summary = json.loads(paths["summary_path"].read_text(encoding="utf-8"))
    schema = json.loads(paths["schema_path"].read_text(encoding="utf-8"))
    exact_validation = validate_fixture_exact_byte_contract(
        paths["summary_path"], paths["stream_path"]
    )
    endings = count_line_endings(paths["stream_path"])
    runtime_truth = summary["metadata"]["sidecar_runtime_truth"]
    archive = runtime_truth["archive"]
    completion = runtime_truth["completion"]

    legacy_paths = build_legacy_normalized_only_fixture(legacy_root)
    legacy = validate_legacy_normalized_only_fails_closed(
        legacy_paths["summary_path"], legacy_paths["stream_path"]
    )

    contract_fields_valid = exact_validation["contract_fields"] == {
        "hash_contract": HASH_CONTRACT,
        "line_ending_contract": LINE_ENDING_CONTRACT,
        "byte_size_contract": BYTE_SIZE_CONTRACT,
        "writer_contract_version": WRITER_CONTRACT_VERSION,
    }
    checks = {
        "writer_status_valid": result["validation"]["status"] == "PREDICTION_SIDECAR_VALID",
        "all_fixture_files_exist": all(path.is_file() for path in paths.values()),
        "row_count_valid": summary["row_count"] == len(build_synthetic_prediction_rows()),
        "lf_only": not endings["generated_stream_has_crlf"]
        and endings["generated_stream_has_bare_lf"]
        and endings["stray_cr_count"] == 0,
        "exact_hash_and_size_valid": exact_validation["summary_matches_exact_bytes"],
        "normalized_hash_equals_exact": exact_validation["lf_normalized_equals_exact"],
        "contract_fields_valid": contract_fields_valid,
        "schema_version_valid": schema.get("schema_version") == SIDECAR_SCHEMA_VERSION,
        "runtime_truth_valid": runtime_truth.get("export_completed") is True
        and runtime_truth.get("real_full_dataset_stream_created") is True
        and runtime_truth.get("real_quick_quality_run_executed") is None,
        "archive_truthful": archive.get("archive_status") in {"NOT_REQUESTED", "MISSING", "UNKNOWN"}
        and archive.get("sidecar_retention_confirmed") is False,
        "completion_truthful": completion.get("python_exit_code") is None
        and completion.get("controlling_shell_exit_code") is None
        and completion.get("run_exit_code_status") == "UNKNOWN_OR_EXTERNAL",
        "legacy_fails_closed": legacy["status"] == "PREDICTION_SIDECAR_EXACT_BYTES_INVALID"
        and "SUMMARY_HASH_MATCHES_LF_NORMALIZED_NOT_EXACT_BYTES" in legacy["errors"],
        "legacy_not_mutated": legacy["fixture_mutated_during_validation"] is False,
    }
    passed = all(checks.values())
    return {
        "diagnostic_name": DIAGNOSTIC_NAME,
        "diagnostic_version": DIAGNOSTIC_VERSION,
        "execution_mode": EXECUTION_MODE,
        "previous_stage_contract": {
            "stage": "ML38.10.58",
            "status": "SIDECAR_WRITER_METADATA_ARCHIVE_CONTRACT_FIXED_NOT_EXECUTED",
            "writer_contract_version": WRITER_CONTRACT_VERSION,
        },
        "fixture_generation": {
            "fixture_only": True,
            "generated_stream_exists": paths["stream_path"].is_file(),
            "generated_summary_exists": paths["summary_path"].is_file(),
            "generated_schema_exists": paths["schema_path"].is_file(),
            "generated_row_count": summary["row_count"],
            "validation_status": result["validation"]["status"],
        },
        "exact_byte_integrity_validation": exact_validation,
        "line_ending_validation": endings,
        "summary_contract_validation": {
            **exact_validation["contract_fields"],
            "fields_valid": contract_fields_valid,
        },
        "schema_contract_validation": {
            "schema_version": schema.get("schema_version"),
            "schema_version_valid": checks["schema_version_valid"],
        },
        "runtime_truth_validation": {
            "sidecar_runtime_truth_exists": True,
            "runtime_truth": runtime_truth,
            "unknown_facts_use_null_not_false": checks["runtime_truth_valid"]
            and completion.get("timeout_detected") is None
            and completion.get("child_completed_later") is None,
        },
        "archive_contract_validation": {
            "fixture_archive": archive,
            "supported_status_examples": {
                status: build_archive_status_metadata(archive_expected=expected)
                for status, expected in (("NOT_REQUESTED", False), ("MISSING", True), ("UNKNOWN", None))
            },
            "retention_not_falsely_confirmed": archive.get("sidecar_retention_confirmed") is False,
        },
        "completion_contract_validation": {
            "completion": completion,
            "fake_exit_code_zero_present": completion.get("python_exit_code") == 0
            or completion.get("controlling_shell_exit_code") == 0,
        },
        "legacy_normalized_only_validation": legacy,
        "real_artifact_guardrail": {
            "temporary_directory_only": True,
            "real_artifacts_read": False,
            "real_artifacts_written_or_mutated": False,
            "new_real_sidecars_created": False,
            "zip_created": False,
            "quick_quality_run": False,
            "training_or_runtime_run": False,
            "db_writes": False,
        },
        "validation_decision_gate": {
            "checks": checks,
            "future_writer_contract_validated_on_fixture": passed,
            "newly_generated_exact_byte_valid_real_sidecar_available": False,
            "cascade_outcome_allowed_now": False,
            "production_like_recompute_allowed_now": False,
            "tradable_edge_claim_allowed_now": False,
            "next_allowed_stage": (
                "ML38.10.60 — separately approved real SOLUSDT quick-quality re-run or "
                "no-run package/metadata validation plan"
            ),
        },
        "next_step_plan": [
            "Require separate approval before any real quick-quality execution.",
            "Keep full 6481 cascade/outcome blocked until a valid real artifact exists.",
        ],
        "decision": [
            "POST_FIX_FIXTURE_VALIDATION_PASSED_NO_REAL_RUN"
            if passed
            else "POST_FIX_FIXTURE_VALIDATION_FAILED_NO_REAL_RUN"
        ],
    }


with TemporaryDirectory(prefix="ml38_10_59_fixture_") as _fixture_tmp:
    post_fix_sidecar_fixture_validation = build_post_fix_sidecar_fixture_validation(
        Path(_fixture_tmp)
    )
