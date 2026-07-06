from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

from app.diagnostics.real_quick_quality_sidecar_validation_audit import (
    APPROVED_RUN_COMMAND,
    EXECUTION_MODE,
    MODEL_SOURCE_STAGE,
    REQUIRED_SIDECAR_FIELDS,
    audit_metadata_staleness,
    build_real_quick_quality_sidecar_validation_audit,
    discover_real_quick_quality_run_artifacts,
    read_only_real_quick_quality_sidecar_validation_audit,
    validate_config_consistency,
    validate_prediction_jsonl_integrity,
    validate_prediction_schema_integrity,
    validate_sidecar_summary_contract,
)


SPLITS = {"train": 1, "val": 1, "test": 1}


def _rows() -> list[dict]:
    rows = []
    for index, split in enumerate(SPLITS):
        rows.append({
            "symbol": "SOLUSDT", "interval": "15m", "candle_open_time": f"2026-01-01T0{index}:00:00+00:00",
            "split_name": split, "split_row_index": 0, "split_total_rows": 1,
            "config_id": "lv36_candidate", "feature_version": "fv4_book_setup_context",
            "label_version": "lv36_h12_metric_relax_suppress_short_exit45", "model_version": "model-lv36",
            "horizon_candles": 12, "predicted_label": ("UP", "DOWN", "FLAT")[index],
            "predicted_label_source": "model_probability_argmax", "prediction_source_stage": MODEL_SOURCE_STAGE,
            "prob_up": 0.4, "prob_down": 0.3, "prob_flat": 0.3, "confidence": 0.4,
        })
    return rows


def _consistency() -> dict:
    values = {
        "config_id": "lv36_candidate", "model_version": "model-lv36",
        "feature_version": "fv4_book_setup_context", "label_version": "lv36_h12_metric_relax_suppress_short_exit45",
        "candidate_id": "lv36_candidate", "run_id": "run", "symbol": "SOLUSDT", "interval": "15m",
        "horizon_candles": "12", "model_name": "candle_mlp",
    }
    return {key: {"expected": value, "observed": [value], "matches": True} for key, value in values.items()}


def _summary(sha: str = "a" * 64) -> dict:
    return {
        "schema_version": "ml38.10.50", "relative_path": "prediction_payloads/full_dataset_prediction_stream.jsonl",
        "denominator_scope": "FULL_DATASET_3", "row_count": 3, "expected_row_count": 3,
        "split_counts": SPLITS, "predicted_label_distribution": {"UP": 1, "DOWN": 1, "FLAT": 1},
        "sha256": sha, "size_bytes": 100, "validation_status": "PREDICTION_SIDECAR_VALID",
        "config_consistency": _consistency(),
        "metadata": {
            "candidate_id": "lv36_candidate", "model_version": "model-lv36",
            "feature_version": "fv4_book_setup_context", "label_version": "lv36_h12_metric_relax_suppress_short_exit45",
            "horizon_candles": 12, "symbol": "SOLUSDT", "interval": "15m",
            "prediction_source_stage": MODEL_SOURCE_STAGE,
            "full_dataset_prediction_sidecar_wiring": {
                "implementation_status": "WIRED_NOT_EXECUTED", "real_quick_quality_run_executed": False,
                "real_full_dataset_stream_created": False,
            },
        },
    }


def _write_fixture(tmp_path: Path) -> Path:
    payloads = tmp_path / "candidate" / "prediction_payloads"
    payloads.mkdir(parents=True)
    stream = payloads / "full_dataset_prediction_stream.jsonl"
    stream.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in _rows()), encoding="utf-8")
    summary = _summary(hashlib.sha256(stream.read_bytes()).hexdigest())
    summary["size_bytes"] = stream.stat().st_size
    (payloads / "full_dataset_prediction_stream_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    schema = {"required": sorted(REQUIRED_SIDECAR_FIELDS)}
    (payloads / "prediction_payload_schema.json").write_text(json.dumps(schema), encoding="utf-8")
    return payloads


def test_audit_block_and_execution_contract_exist() -> None:
    assert read_only_real_quick_quality_sidecar_validation_audit["diagnostic_name"] == "read_only_real_quick_quality_sidecar_validation_audit"
    assert read_only_real_quick_quality_sidecar_validation_audit["execution_mode"] == EXECUTION_MODE
    assert read_only_real_quick_quality_sidecar_validation_audit["approved_run_command"] == APPROVED_RUN_COMMAND


def test_summary_accepts_legacy_sha_field_and_enforces_boundary() -> None:
    audit = validate_sidecar_summary_contract(_summary(), expected_row_count=3, expected_split_counts=SPLITS)
    assert audit["status"] == "LATEST_SIDECAR_SUMMARY_VALID"
    assert audit["sha_field_compatibility_status"] == "SUMMARY_SHA_FIELD_COMPATIBILITY_NOTE"
    invalid = _summary()
    invalid["row_count"] = 2
    assert validate_sidecar_summary_contract(invalid, expected_row_count=3, expected_split_counts=SPLITS)["status"] == "LATEST_SIDECAR_SUMMARY_INVALID"
    invalid = _summary()
    invalid["denominator_scope"] = "TEST_ONLY_3"
    assert validate_sidecar_summary_contract(invalid, expected_row_count=3, expected_split_counts=SPLITS)["status"] == "LATEST_SIDECAR_SUMMARY_INVALID"


def test_jsonl_integrity_verifies_count_hash_and_splits(tmp_path: Path) -> None:
    payloads = _write_fixture(tmp_path)
    stream = payloads / "full_dataset_prediction_stream.jsonl"
    audit = validate_prediction_jsonl_integrity(
        stream, expected_row_count=3, expected_sha256=hashlib.sha256(stream.read_bytes()).hexdigest(), expected_split_counts=SPLITS
    )
    assert audit["status"] == "JSONL_INTEGRITY_CONFIRMED"
    assert audit["row_count_read_from_jsonl"] == 3
    assert audit["split_counts_computed"] == SPLITS


def test_jsonl_integrity_rejects_duplicate_and_forbidden_source(tmp_path: Path) -> None:
    rows = _rows()
    rows[1]["candle_open_time"] = rows[0]["candle_open_time"]
    rows[1]["prediction_source"] = "ml_labels.direction_label"
    path = tmp_path / "stream.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    audit = validate_prediction_jsonl_integrity(path, expected_row_count=3, expected_split_counts=SPLITS)
    assert audit["status"] == "JSONL_INTEGRITY_FAILED"
    assert audit["unique_symbol_interval_candle_open_time"] is False
    assert audit["forbidden_prediction_sources_absent"] is False


def test_schema_config_and_metadata_checks(tmp_path: Path) -> None:
    payloads = _write_fixture(tmp_path)
    assert validate_prediction_schema_integrity(payloads / "prediction_payload_schema.json")["status"] == "SCHEMA_PRESENT_REQUIRED_FIELDS_CONFIRMED"
    summary = _summary()
    assert validate_config_consistency(summary)["status"] == "CONFIG_CONSISTENCY_CONFIRMED"
    stale = audit_metadata_staleness(summary, real_sidecars_exist=True)
    assert stale["stale_metadata_detected"] is True
    assert stale["severity"] == "MEDIUM"


def test_discovery_and_decision_gate_capture_incomplete_package(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    discovery = discover_real_quick_quality_run_artifacts(tmp_path)
    assert discovery["artifact_status"] == "SIDECARS_FOUND_ZIP_MISSING"
    audit = build_real_quick_quality_sidecar_validation_audit(
        tmp_path, expected_row_count=3, expected_split_counts=SPLITS
    )
    assert audit["run_completion_audit"]["controlling_shell_exit_code"] == 124
    assert audit["run_completion_audit"]["python_exit_code"] is None
    assert audit["validation_decision_gate"]["decision"] == "REAL_SIDECAR_STREAM_VALID_BUT_RUN_PACKAGE_INCOMPLETE"
    assert audit["validation_decision_gate"]["zip_confirmed"] is False
    assert audit["validation_decision_gate"]["cascade_outcome_allowed_now"] is False
    assert audit["cascade_outcome_guardrail"]["status"] == "CASCADE_OUTCOME_BLOCKED"


def test_tests_are_synthetic_and_do_not_invoke_quick_quality_or_write_reports() -> None:
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    called = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    assert "subprocess" not in imports
    assert "run_fv3_cached_tuning" not in called
    assert ".write_text(" in source
    forbidden_report_constructor = "Path(" + chr(34) + "reports"
    assert forbidden_report_constructor not in source
