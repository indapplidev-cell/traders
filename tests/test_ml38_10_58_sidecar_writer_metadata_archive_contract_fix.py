from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from app.diagnostics.sidecar_writer_metadata_archive_contract_fix import (
    sidecar_writer_metadata_archive_contract_fix_plan,
)
from app.diagnostics.real_quick_quality_sidecar_validation_audit import (
    MODEL_SOURCE_STAGE,
    validate_sidecar_summary_contract,
)
from app.experiments.prediction_sidecar_exporter import (
    build_archive_status_metadata,
    build_timeout_exit_code_metadata,
    validate_prediction_sidecar_file_contract,
    write_prediction_sidecar_artifacts,
)


def _row(index: int, total: int = 3) -> dict:
    splits = ("train", "val", "test")
    return {
        "symbol": "SYNTHUSDT", "interval": "15m", "candle_open_time": f"2026-01-01T00:{index:02d}:00+00:00",
        "dataset_row_index": index, "split_name": splits[index], "split_row_index": 0,
        "split_total_rows": 1, "feature_version": "fv-test", "label_version": "lv-test",
        "horizon_candles": 12, "config_id": "cfg-test", "model_name": "synthetic",
        "model_version": "model-test", "run_id": "run-test", "candidate_id": "candidate-test",
        "predicted_label": "UP", "prediction_source_stage": "synthetic_model_probability_argmax",
        "predicted_label_source": "model_probability_argmax", "prob_up": 0.8,
        "prob_down": 0.1, "prob_flat": 0.1, "confidence": 0.8,
    }


def _write(tmp_path: Path) -> dict:
    return write_prediction_sidecar_artifacts(
        tmp_path, [_row(i) for i in range(3)],
        metadata={"config_id": "cfg-test", "model_version": "model-test", "feature_version": "fv-test", "label_version": "lv-test"},
        expected_row_count=3, denominator_scope="SYNTHETIC_TEST_ROWS",
    )


def test_future_writer_uses_lf_exact_bytes_and_summary_contract(tmp_path: Path) -> None:
    result = _write(tmp_path)
    stream = Path(result["paths"]["stream_path"])
    exact = stream.read_bytes()
    summary = json.loads(Path(result["paths"]["summary_path"]).read_text(encoding="utf-8"))
    assert b"\r\n" not in exact and exact.endswith(b"\n")
    assert summary["sha256"] == sha256(exact).hexdigest()
    assert summary["size_bytes"] == stream.stat().st_size == len(exact)
    assert summary["hash_contract"] == "EXACT_BYTES_AFTER_WRITE"
    assert summary["line_ending_contract"] == "LF"
    assert summary["byte_size_contract"] == "EXACT_BYTES_AFTER_WRITE"
    assert summary["writer_contract_version"] == "ml38.10.58"
    assert result["schema"]["schema_version"] == "ml38.10.58"
    assert result["schema"]["summary_contract"]["hash_contract"] == "EXACT_BYTES_AFTER_WRITE"


def test_runtime_truth_is_separate_and_unknown_facts_are_not_false(tmp_path: Path) -> None:
    summary = _write(tmp_path)["summary"]
    assert summary["metadata"]["sidecar_runtime_truth"]["runtime_execution_status"] == "EXECUTED"
    runtime = summary["metadata"]["sidecar_runtime_truth"]
    assert runtime["real_full_dataset_stream_created"] is True
    assert runtime["real_quick_quality_run_executed"] is None
    assert runtime["completion"]["timeout_detected"] is None
    assert runtime["completion"]["python_exit_code"] is None
    assert runtime["archive"]["archive_status"] == "UNKNOWN"
    assert runtime["archive"]["archive_contains_sidecars"] == "unknown"
    assert runtime["archive"]["sidecar_retention_confirmed"] is False


def test_schema_reporter_accepts_new_version_only_with_exact_contract(tmp_path: Path) -> None:
    summary = _write(tmp_path)["summary"]
    summary["denominator_scope"] = "FULL_DATASET_3"
    summary["metadata"].update({
        "prediction_source_stage": MODEL_SOURCE_STAGE,
        "symbol": "SOLUSDT", "interval": "15m", "horizon_candles": 12,
        "feature_version": "fv4_book_setup_context",
        "label_version": "lv36_h12_metric_relax_suppress_short_exit45",
    })
    audit = validate_sidecar_summary_contract(
        summary, expected_row_count=3,
        expected_split_counts={"train": 1, "val": 1, "test": 1},
    )
    assert audit["schema_version_valid"] is True
    summary.pop("hash_contract")
    assert validate_sidecar_summary_contract(
        summary, expected_row_count=3,
        expected_split_counts={"train": 1, "val": 1, "test": 1},
    )["schema_version_valid"] is False


def test_legacy_normalized_only_mismatch_fails_closed_without_mutation(tmp_path: Path) -> None:
    stream = tmp_path / "legacy.jsonl"
    exact = b'{"a":1}\r\n{"a":2}\r\n'
    stream.write_bytes(exact)
    before = stream.read_bytes()
    normalized = exact.replace(b"\r\n", b"\n")
    audit = validate_prediction_sidecar_file_contract(
        stream, {"sha256": sha256(normalized).hexdigest(), "size_bytes": len(normalized)}
    )
    assert audit["status"] == "PREDICTION_SIDECAR_EXACT_BYTES_INVALID"
    assert audit["summary_matches_lf_normalized_not_exact_bytes"] is True
    assert "SUMMARY_HASH_MATCHES_LF_NORMALIZED_NOT_EXACT_BYTES" in audit["errors"]
    assert stream.read_bytes() == before


def test_archive_and_timeout_contracts_represent_missing_lost_and_unknown() -> None:
    missing = build_archive_status_metadata(archive_expected=True)
    unknown = build_archive_status_metadata()
    completion = build_timeout_exit_code_metadata()
    assert missing["archive_status"] == "MISSING" and missing["archive_created"] is False
    assert unknown["archive_status"] == "UNKNOWN" and unknown["archive_created"] is None
    assert completion["run_exit_code_status"] == "UNKNOWN_OR_EXTERNAL"
    assert completion["controlling_shell_exit_code"] is None
    lost = {**completion, "timeout_detected": True, "run_exit_code_status": "LOST_DUE_TIMEOUT"}
    assert lost["python_exit_code"] is None


def test_diagnostic_plan_preserves_stage_guardrails() -> None:
    plan = sidecar_writer_metadata_archive_contract_fix_plan
    assert plan["writer_contract_fix"]["status"] == "IMPLEMENTED"
    assert plan["legacy_artifact_policy"]["mutate_legacy_artifacts"] is False
    assert plan["real_artifact_guardrail"]["archive_recovery_performed"] is False
    assert plan["validation_decision_gate"]["full_6481_cascade_outcome_allowed"] is False
