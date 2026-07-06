from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from typing import Any, Callable

from app.experiments.compact_archive_pruner import should_preserve_prediction_sidecar_artifact
from app.experiments.prediction_sidecar_exporter import (
    validate_prediction_sidecar_rows,
    write_prediction_sidecar_artifacts,
)


DIAGNOSTIC_NAME = "read_only_sidecar_exporter_fixture_audit"
DIAGNOSTIC_VERSION = "ml38.10.51"
EXECUTION_MODE = "FIXTURE_DRY_RUN_NO_TRAINING_NO_DB_WRITES"
FIXTURE_SCOPE = "SYNTHETIC_FIXTURE_ONLY"
DENOMINATOR_SCOPE = "SYNTHETIC_FIXTURE_ROWS"
CONFIG_ID = "ml38_10_51_fixture_config"
MODEL_VERSION = "ml38_10_51_fixture_model_v1"
FEATURE_VERSION = "ml38_10_51_fixture_features_v1"
LABEL_VERSION = "ml38_10_51_fixture_labels_v1"


def build_synthetic_prediction_rows(row_count: int = 6) -> list[dict[str, Any]]:
    """Build deterministic model-output fixtures; actual labels remain target-only."""
    if row_count < 1:
        raise ValueError("row_count must be positive")
    split_names = ("train", "val", "test")
    assigned_splits = [split_names[min(index * 3 // row_count, 2)] for index in range(row_count)]
    split_totals = Counter(assigned_splits)
    split_indexes: Counter[str] = Counter()
    rows: list[dict[str, Any]] = []
    for index, split_name in enumerate(assigned_splits):
        predicted_label = ("UP", "DOWN", "FLAT")[index % 3]
        probabilities = {
            "UP": (0.70, 0.15, 0.15),
            "DOWN": (0.15, 0.70, 0.15),
            "FLAT": (0.15, 0.15, 0.70),
        }[predicted_label]
        rows.append(
            {
                "symbol": "FIXTUREUSDT",
                "interval": "5m",
                "candle_open_time": f"2026-01-01T00:{index:02d}:00Z",
                "dataset_row_index": index,
                "split_name": split_name,
                "split_row_index": split_indexes[split_name],
                "split_total_rows": split_totals[split_name],
                "feature_version": FEATURE_VERSION,
                "label_version": LABEL_VERSION,
                "horizon_candles": 12,
                "config_id": CONFIG_ID,
                "model_name": "fixture_classifier",
                "model_version": MODEL_VERSION,
                "candidate_id": "ml38_10_51_fixture_candidate",
                "predicted_label": predicted_label,
                "prediction_source_stage": "synthetic_fixture_model_inference",
                "prob_up": probabilities[0],
                "prob_down": probabilities[1],
                "prob_flat": probabilities[2],
                "confidence": 0.70,
                "actual_label": ("DOWN", "FLAT", "UP")[index % 3],
                "actual_label_source": "synthetic_fixture_target_only",
                "actual_label_version": LABEL_VERSION,
            }
        )
        split_indexes[split_name] += 1
    return rows


def _validation(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return validate_prediction_sidecar_rows(
        rows,
        expected_row_count=len(rows),
        denominator_scope=DENOMINATOR_SCOPE,
        expected_config_id=CONFIG_ID,
        expected_model_version=MODEL_VERSION,
        expected_feature_version=FEATURE_VERSION,
        expected_label_version=LABEL_VERSION,
    )


def build_fixture_export_input_summary(
    rows: Sequence[Mapping[str, Any]], *, rows_written: int
) -> dict[str, Any]:
    validation = _validation(rows)
    return {
        "fixture_scope": FIXTURE_SCOPE,
        "fixture_rows_requested": len(rows),
        "fixture_rows_written": rows_written,
        "denominator_scope": DENOMINATOR_SCOPE,
        "expected_row_count": len(rows),
        "split_counts": validation["split_counts"],
        "predicted_label_distribution": validation["predicted_label_distribution"],
        "actual_label_included_as_target_only": True,
        "forbidden_prediction_source_used": False,
        "config_id": CONFIG_ID,
        "model_version": MODEL_VERSION,
        "feature_version": FEATURE_VERSION,
        "label_version": LABEL_VERSION,
        "input_status": (
            "FIXTURE_INPUTS_READY"
            if validation["status"] == "PREDICTION_SIDECAR_VALID" and rows_written == len(rows)
            else "FIXTURE_INPUTS_INVALID"
        ),
    }


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def build_fixture_sidecar_artifact_board(paths: Mapping[str, str]) -> list[dict[str, Any]]:
    specs = (
        ("full_dataset_prediction_stream.jsonl", "stream_path"),
        ("full_dataset_prediction_stream_summary.json", "summary_path"),
        ("prediction_payload_schema.json", "schema_path"),
    )
    board = []
    for artifact_name, path_key in specs:
        path = Path(paths[path_key])
        exists = path.is_file()
        parse_status = "NOT_PARSED"
        schema_status = "NOT_CHECKED"
        row_count: int | None = None
        if exists:
            try:
                if path.suffix == ".jsonl":
                    parsed = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
                    row_count = len(parsed)
                    schema_status = "ROW_OBJECTS_PRESENT" if all(isinstance(row, dict) for row in parsed) else "INVALID"
                else:
                    parsed = json.loads(path.read_text(encoding="utf-8"))
                    schema_status = (
                        "SCHEMA_DOCUMENT_VALID"
                        if artifact_name == "prediction_payload_schema.json" and parsed.get("$schema")
                        else "SUMMARY_DOCUMENT_VALID"
                    )
                parse_status = "JSON_VALID"
            except (json.JSONDecodeError, OSError, AttributeError):
                parse_status = "JSON_INVALID"
                schema_status = "INVALID"
        board.append(
            {
                "artifact_name": artifact_name,
                "relative_path": f"prediction_payloads/{artifact_name}",
                "created_in_temp_dir": exists and path.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve()),
                "exists": exists,
                "row_count_if_applicable": row_count,
                "bytes": path.stat().st_size if exists else 0,
                "sha256": _sha256(path) if exists else None,
                "json_parse_status": parse_status,
                "schema_status": schema_status,
                "status": "FIXTURE_ARTIFACT_VALID" if exists and parse_status == "JSON_VALID" else "FIXTURE_ARTIFACT_INVALID",
            }
        )
    return board


def _case_row_mutator(field: str, value: Any) -> Callable[[list[dict[str, Any]]], None]:
    def mutate(rows: list[dict[str, Any]]) -> None:
        if value is None:
            rows[0].pop(field, None)
        else:
            rows[0][field] = value

    return mutate


def _duplicate_key(rows: list[dict[str, Any]]) -> None:
    for field in ("symbol", "interval", "candle_open_time"):
        rows[1][field] = rows[0][field]


def build_fixture_validator_result_board(
    fixture_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    cases: tuple[tuple[str, str, Callable[[list[dict[str, Any]]], None] | None], ...] = (
        ("valid_fixture_stream", "PREDICTION_SIDECAR_VALID", None),
        ("duplicate_key_failure", "PREDICTION_SIDECAR_INVALID", _duplicate_key),
        ("missing_predicted_label_failure", "PREDICTION_SIDECAR_INVALID", _case_row_mutator("predicted_label", None)),
        ("invalid_predicted_label_failure", "PREDICTION_SIDECAR_INVALID", _case_row_mutator("predicted_label", "LONG")),
        ("probability_sum_failure_or_warning", "PREDICTION_SIDECAR_INVALID", _case_row_mutator("prob_up", 0.95)),
        ("config_mismatch_failure", "PREDICTION_SIDECAR_INVALID", _case_row_mutator("config_id", "wrong_config")),
        ("forbidden_actual_prediction_source_failure", "PREDICTION_SIDECAR_INVALID", _case_row_mutator("prediction_source_stage", "actual_label/target source")),
        ("forbidden_ml_labels_direction_label_source_failure", "PREDICTION_SIDECAR_INVALID", _case_row_mutator("prediction_source_stage", "ml_labels.direction_label")),
    )
    board = []
    for check_name, expected_status, mutator in cases:
        rows = deepcopy(list(fixture_rows))
        if mutator is not None:
            mutator(rows)
        result = _validation(rows)
        board.append(
            {
                "check_name": check_name,
                "expected_status": expected_status,
                "observed_status": result["status"],
                "errors": result["errors"],
                "warnings": result["warnings"],
                "passed": result["status"] == expected_status,
            }
        )
    return board


def build_fixture_compact_whitelist_retention_board() -> list[dict[str, Any]]:
    expected = {
        "prediction_payloads/full_dataset_prediction_stream.jsonl": True,
        "prediction_payloads/full_dataset_prediction_stream_summary.json": True,
        "prediction_payloads/prediction_payload_schema.json": True,
        "prediction_payloads/test_prediction_stream.jsonl": True,
        "prediction_payloads/raw_feature_dump.jsonl": False,
        "raw_features/features.jsonl": False,
        "credentials/token.json": False,
    }
    board = []
    for path, expected_preserved in expected.items():
        observed = should_preserve_prediction_sidecar_artifact(path)
        board.append(
            {
                "path": path,
                "expected_preserved": expected_preserved,
                "observed_preserved": observed,
                "reason": "explicit_prediction_sidecar_whitelist" if observed else "not_in_prediction_sidecar_whitelist",
                "passed": observed is expected_preserved,
            }
        )
    return board


def build_fixture_fail_closed_board(
    fixture_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    cases: tuple[tuple[str, Callable[[list[dict[str, Any]]], None]], ...] = (
        ("duplicate join key", _duplicate_key),
        ("missing predicted_label", _case_row_mutator("predicted_label", None)),
        ("predicted_label from ml_labels.direction_label", _case_row_mutator("prediction_source_stage", "ml_labels.direction_label")),
        ("predicted_label from actual_label/target source", _case_row_mutator("prediction_source_stage", "actual_label/target source")),
        ("config_id mismatch", _case_row_mutator("config_id", "wrong_config")),
        ("feature_version mismatch", _case_row_mutator("feature_version", "wrong_feature_version")),
        ("label_version mismatch", _case_row_mutator("label_version", "wrong_label_version")),
    )
    board = []
    for scenario, mutator in cases:
        rows = deepcopy(list(fixture_rows))
        mutator(rows)
        validation = _validation(rows)
        observed = validation["status"] == "PREDICTION_SIDECAR_INVALID"
        board.append(
            {
                "scenario": scenario,
                "expected_fail_closed": True,
                "observed_fail_closed": observed,
                "validation_status": validation["status"],
                "passed": observed,
            }
        )
    return board


def build_real_stream_guardrail() -> dict[str, Any]:
    return {
        "real_full_dataset_prediction_stream_created": False,
        "real_full_dataset_prediction_stream_path": None,
        "real_stream_row_count": 0,
        "fixture_artifacts_written_to_reports": False,
        "quick_quality_executed": False,
        "training_or_runtime_executed": False,
        "db_writes": False,
        "ml_labels_writes": False,
        "ml_predictions_writes": False,
        "full_6481_cascade_allowed_now": False,
        "full_6481_outcome_allowed_now": False,
        "production_like_recompute": False,
        "tradable_edge_confirmed": False,
        "real_generation_requires_separate_approval": True,
    }


def build_ml38_10_51_sidecar_fixture_audit_decision() -> list[str]:
    return [
        "SIDECAR_FIXTURE_AUDIT_ADDED",
        "FIXTURE_EXPORT_SUCCEEDED",
        "FIXTURE_VALIDATION_SUCCEEDED",
        "FIXTURE_FAIL_CLOSED_CASES_PASSED",
        "COMPACT_WHITELIST_FIXTURE_CHECK_PASSED",
        "SYNTHETIC_FIXTURE_ONLY",
        "REAL_FULL_6481_STREAM_NOT_CREATED",
        "QUICK_QUALITY_RERUN_REQUIRES_SEPARATE_APPROVAL",
        "DB_WRITES_NOT_ALLOWED",
        "ML_PREDICTIONS_NOT_WRITTEN",
        "DO_NOT_SUBSTITUTE_ACTUAL_LABEL_FOR_PREDICTION",
        "FULL_6481_CASCADE_NOT_ALLOWED_UNTIL_STREAM_EXISTS",
        "DO_NOT_CHANGE_LABELS_YET",
        "DO_NOT_CHANGE_GATES",
        "DO_NOT_RUN_TRAINING",
    ]


def _require_temporary_output_dir(output_dir: str | Path) -> Path:
    resolved = Path(output_dir).resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    if not resolved.is_relative_to(temp_root):
        raise ValueError(f"fixture artifacts must be written below the system temp directory: {temp_root}")
    if "reports" in {part.lower() for part in resolved.parts}:
        raise ValueError("fixture artifacts must not be written to reports/")
    return resolved


def build_read_only_sidecar_exporter_fixture_audit(
    output_dir: str | Path,
    *,
    fixture_rows: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Execute the ML38.10.51 synthetic-only audit in a caller-owned temp directory."""
    temp_output_dir = _require_temporary_output_dir(output_dir)
    rows = list(fixture_rows) if fixture_rows is not None else build_synthetic_prediction_rows()
    export = write_prediction_sidecar_artifacts(
        temp_output_dir,
        rows,
        metadata={
            "fixture_scope": FIXTURE_SCOPE,
            "config_id": CONFIG_ID,
            "model_version": MODEL_VERSION,
            "feature_version": FEATURE_VERSION,
            "label_version": LABEL_VERSION,
        },
        expected_row_count=len(rows),
        denominator_scope=DENOMINATOR_SCOPE,
    )
    artifact_board = build_fixture_sidecar_artifact_board(export["paths"])
    validator_board = build_fixture_validator_result_board(rows)
    whitelist_board = build_fixture_compact_whitelist_retention_board()
    fail_closed_board = build_fixture_fail_closed_board(rows)
    decisions = build_ml38_10_51_sidecar_fixture_audit_decision()
    return {
        "diagnostic_name": DIAGNOSTIC_NAME,
        "diagnostic_version": DIAGNOSTIC_VERSION,
        "execution_mode": EXECUTION_MODE,
        "fixture_scope": FIXTURE_SCOPE,
        "source_counts": {"synthetic_fixture_rows": len(rows), "real_project_rows": 0},
        "fixture_export_input_summary": build_fixture_export_input_summary(rows, rows_written=export["summary"]["row_count"]),
        "fixture_sidecar_artifact_board": artifact_board,
        "fixture_validator_result_board": validator_board,
        "fixture_compact_whitelist_retention_board": whitelist_board,
        "fixture_fail_closed_board": fail_closed_board,
        "real_stream_guardrail": build_real_stream_guardrail(),
        "next_step_plan": [
            "review fixture-only audit evidence",
            "keep real 6481 generation blocked pending separate approval",
            "do not run quick-quality, training, runtime, or DB writes in ML38.10.51",
        ],
        "decision": decisions,
        "ml38_10_51_sidecar_fixture_audit_decision": decisions,
    }
