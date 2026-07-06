from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.diagnostics.sidecar_exporter_fixture_audit import (
    build_read_only_sidecar_exporter_fixture_audit,
)


def _audit(tmp_path: Path) -> dict:
    return build_read_only_sidecar_exporter_fixture_audit(tmp_path)


def test_fixture_audit_writes_only_three_artifacts_to_tmp_path(tmp_path: Path) -> None:
    reports_stream = Path("reports/prediction_payloads/full_dataset_prediction_stream.jsonl")
    reports_before = reports_stream.exists()
    audit = _audit(tmp_path)
    written = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*") if path.is_file())

    assert written == [
        "prediction_payloads/full_dataset_prediction_stream.jsonl",
        "prediction_payloads/full_dataset_prediction_stream_summary.json",
        "prediction_payloads/prediction_payload_schema.json",
    ]
    assert reports_stream.exists() is reports_before
    assert all(row["created_in_temp_dir"] for row in audit["fixture_sidecar_artifact_board"])


def test_non_temp_and_reports_output_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="system temp"):
        build_read_only_sidecar_exporter_fixture_audit(Path.cwd() / "fixture-output")
    with pytest.raises(ValueError, match="reports"):
        build_read_only_sidecar_exporter_fixture_audit(tmp_path / "reports")


def test_valid_fixture_and_artifact_board(tmp_path: Path) -> None:
    audit = _audit(tmp_path)
    validation = {row["check_name"]: row for row in audit["fixture_validator_result_board"]}
    artifacts = {row["artifact_name"]: row for row in audit["fixture_sidecar_artifact_board"]}

    assert validation["valid_fixture_stream"]["observed_status"] == "PREDICTION_SIDECAR_VALID"
    assert validation["valid_fixture_stream"]["passed"] is True
    assert set(artifacts) == {
        "full_dataset_prediction_stream.jsonl",
        "full_dataset_prediction_stream_summary.json",
        "prediction_payload_schema.json",
    }
    assert all(row["exists"] and len(row["sha256"]) == 64 for row in artifacts.values())


def test_summary_has_manifest_counts_hash_and_scope(tmp_path: Path) -> None:
    _audit(tmp_path)
    summary = json.loads(
        (tmp_path / "prediction_payloads/full_dataset_prediction_stream_summary.json").read_text(encoding="utf-8")
    )
    assert summary["row_count"] == 6
    assert sum(summary["split_counts"].values()) == 6
    assert len(summary["sha256"]) == 64
    assert summary["denominator_scope"] == "SYNTHETIC_FIXTURE_ROWS"


def test_validator_negative_cases_fail_closed(tmp_path: Path) -> None:
    board = {row["check_name"]: row for row in _audit(tmp_path)["fixture_validator_result_board"]}
    for check_name in (
        "duplicate_key_failure",
        "missing_predicted_label_failure",
        "invalid_predicted_label_failure",
        "forbidden_ml_labels_direction_label_source_failure",
        "forbidden_actual_prediction_source_failure",
        "config_mismatch_failure",
    ):
        assert board[check_name]["observed_status"] == "PREDICTION_SIDECAR_INVALID"
        assert board[check_name]["passed"] is True


def test_all_required_fail_closed_scenarios_pass(tmp_path: Path) -> None:
    board = {row["scenario"]: row for row in _audit(tmp_path)["fixture_fail_closed_board"]}
    assert set(board) == {
        "duplicate join key",
        "missing predicted_label",
        "predicted_label from ml_labels.direction_label",
        "predicted_label from actual_label/target source",
        "config_id mismatch",
        "feature_version mismatch",
        "label_version mismatch",
    }
    assert all(row["passed"] for row in board.values())


def test_compact_whitelist_fixture_paths_are_narrow(tmp_path: Path) -> None:
    board = {row["path"]: row for row in _audit(tmp_path)["fixture_compact_whitelist_retention_board"]}
    for path in (
        "prediction_payloads/full_dataset_prediction_stream.jsonl",
        "prediction_payloads/full_dataset_prediction_stream_summary.json",
        "prediction_payloads/prediction_payload_schema.json",
        "prediction_payloads/test_prediction_stream.jsonl",
    ):
        assert board[path]["observed_preserved"] is True
    assert board["prediction_payloads/raw_feature_dump.jsonl"]["observed_preserved"] is False
    assert board["raw_features/features.jsonl"]["observed_preserved"] is False
    assert board["credentials/token.json"]["observed_preserved"] is False


def test_guardrail_and_decisions_remain_fixture_only(tmp_path: Path) -> None:
    audit = _audit(tmp_path)
    guardrail = audit["real_stream_guardrail"]
    decisions = audit["ml38_10_51_sidecar_fixture_audit_decision"]

    assert guardrail["real_full_dataset_prediction_stream_created"] is False
    assert guardrail["fixture_artifacts_written_to_reports"] is False
    assert guardrail["real_stream_row_count"] == 0
    assert "SYNTHETIC_FIXTURE_ONLY" in decisions
    assert "REAL_FULL_6481_STREAM_NOT_CREATED" in decisions
    assert "QUICK_QUALITY_RERUN_REQUIRES_SEPARATE_APPROVAL" in decisions
    assert audit["fixture_export_input_summary"]["actual_label_included_as_target_only"] is True
    assert audit["fixture_export_input_summary"]["forbidden_prediction_source_used"] is False
