from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any


SIDECAR_SCHEMA_VERSION = "ml38.10.69"
WRITER_CONTRACT_VERSION = "ml38.10.69"
PREDICTION_FIELD_CONTRACT_VERSION = "ml38.10.69"
HASH_CONTRACT = "EXACT_BYTES_AFTER_WRITE"
LINE_ENDING_CONTRACT = "LF"
BYTE_SIZE_CONTRACT = "EXACT_BYTES_AFTER_WRITE"
FULL_DATASET_DENOMINATOR_SCOPE = "FULL_DATASET_6481"
FULL_DATASET_ROW_COUNT = 6481
PREDICTION_LABELS = ("UP", "DOWN", "FLAT")
SPLIT_NAMES = ("train", "val", "test")
PROBABILITY_FIELDS = ("prob_up", "prob_down", "prob_flat")
RAW_PROBABILITY_FIELDS = ("raw_prob_up", "raw_prob_down", "raw_prob_flat")
CALIBRATED_PROBABILITY_FIELDS = (
    "calibrated_prob_up",
    "calibrated_prob_down",
    "calibrated_prob_flat",
)
PROBABILITY_CLASS_KEYS = frozenset({"DOWN", "FLAT", "UP"})
JOIN_KEY_FIELDS = ("symbol", "interval", "candle_open_time")

REQUIRED_FIELDS = (
    "symbol",
    "interval",
    "candle_open_time",
    "split_name",
    "split_row_index",
    "split_total_rows",
    "feature_version",
    "label_version",
    "horizon_candles",
    "config_id",
    "model_name",
    "model_version",
    "predicted_label",
    "prediction_source_stage",
    *PROBABILITY_FIELDS,
    "confidence",
)
FIELD_CONTRACT_REQUIRED_FIELDS = (
    "sidecar_schema_version",
    "sidecar_writer_version",
    "prediction_field_contract_version",
    "candidate_id",
    "symbol",
    "interval",
    "horizon",
    "split",
    "row_index_global",
    "row_index_split",
    "timestamp",
    "row_alignment_key",
    "actual_label",
    "current_predicted_label",
    "sidecar_argmax_label",
    "sidecar_argmax_layer",
    "predicted_label_semantics",
    "prediction_layer_name",
    "prediction_layer_source",
    *RAW_PROBABILITY_FIELDS,
    "raw_probabilities",
    *CALIBRATED_PROBABILITY_FIELDS,
    "calibrated_probabilities",
    "prediction_layers",
    "downstream_policy_output_available_in_writer",
    "downstream_policy_output_reason",
    "downstream_policy_output_must_not_be_conflated_with_sidecar_argmax",
)
ALTERNATIVE_REQUIRED_FIELDS = (("dataset_row_index", "row_id"), ("run_id", "candidate_id"))
OPTIONAL_FIELDS = (
    "dataset_row_index",
    "row_id",
    "run_id",
    "candidate_id",
    "original_predicted_label",
    "calibrated_predicted_label",
    "calibration_id",
    "actual_label",
    "actual_label_source",
    "actual_label_version",
    "setup_quality_score",
    "entry_path_quality_score",
    "stop_pressure_risk_score",
    "recovery_guard_decision",
    "net_r",
    "gross_r",
    "exit_reason",
    "profit_outcome_source",
    *FIELD_CONTRACT_REQUIRED_FIELDS,
)
PROVENANCE_FIELDS = (
    "predicted_label_source",
    "prediction_source",
    "prediction_source_field",
    "source_field",
)
FORBIDDEN_PREDICTION_SOURCES = (
    "ml_labels.direction_label",
    "actual_label",
    "target_label",
    "direction_label",
    "ground_truth",
)


def _is_present(value: Any) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _canonical_jsonl(rows: Iterable[Mapping[str, Any]]) -> str:
    return "".join(
        json.dumps(dict(row), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    )


def build_prediction_row_alignment_key(
    *, candidate_id: str, symbol: str, interval: str, horizon: int, split: str,
    row_index_global: int, row_index_split: int, timestamp: str,
) -> str:
    """Hash canonical row identity without random or path-dependent values."""
    identity = {
        "candidate_id": candidate_id,
        "horizon": int(horizon),
        "interval": interval,
        "row_index_global": int(row_index_global),
        "row_index_split": int(row_index_split),
        "split": split,
        "symbol": symbol,
        "timestamp": timestamp,
    }
    canonical = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + sha256(canonical.encode("utf-8")).hexdigest()


def normalize_prediction_sidecar_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Return a deterministic sidecar row without unrelated feature payloads."""
    if not isinstance(row, Mapping):
        raise TypeError("prediction sidecar row must be a mapping")
    allowed = (*REQUIRED_FIELDS, *OPTIONAL_FIELDS, *PROVENANCE_FIELDS)
    normalized = {field: row[field] for field in allowed if field in row}
    for field in (
        "symbol",
        "interval",
        "split_name",
        "feature_version",
        "label_version",
        "config_id",
        "model_name",
        "model_version",
        "predicted_label",
    ):
        if isinstance(normalized.get(field), str):
            normalized[field] = normalized[field].strip()
    if isinstance(normalized.get("predicted_label"), str):
        normalized["predicted_label"] = normalized["predicted_label"].upper()
    if isinstance(normalized.get("split_name"), str):
        normalized["split_name"] = normalized["split_name"].lower()
    return normalized


def _probability_mapping_errors(value: Any, field: str) -> list[str]:
    if not isinstance(value, Mapping):
        return [f"{field} must be an object with exactly DOWN/FLAT/UP keys"]
    if set(value) != PROBABILITY_CLASS_KEYS:
        return [f"{field} class keys must be exactly DOWN/FLAT/UP"]
    errors: list[str] = []
    numbers: list[float] = []
    for label in ("DOWN", "FLAT", "UP"):
        number = _finite_number(value.get(label))
        if number is None:
            errors.append(f"{field}.{label} must be numeric and finite")
        elif number < 0.0:
            errors.append(f"{field}.{label} must be non-negative")
        else:
            numbers.append(number)
    if len(numbers) == 3 and not math.isclose(sum(numbers), 1.0, abs_tol=1e-6):
        errors.append(f"{field} probability sum must equal 1 within 1e-6")
    return errors


def _field_contract_errors(row: Mapping[str, Any]) -> list[str]:
    errors = [
        field + " is required"
        for field in FIELD_CONTRACT_REQUIRED_FIELDS
        if not _is_present(row.get(field))
    ]
    for field in (
        "sidecar_schema_version",
        "sidecar_writer_version",
        "prediction_field_contract_version",
    ):
        if _is_present(row.get(field)) and row.get(field) != PREDICTION_FIELD_CONTRACT_VERSION:
            errors.append(f"{field} must equal {PREDICTION_FIELD_CONTRACT_VERSION}")
    for field in ("actual_label", "current_predicted_label", "sidecar_argmax_label"):
        value = str(row.get(field) or "").upper()
        if _is_present(row.get(field)) and value not in PREDICTION_LABELS:
            errors.append(f"{field} must be one of UP/DOWN/FLAT")
    for fields, mapping_field in (
        (RAW_PROBABILITY_FIELDS, "raw_probabilities"),
        (CALIBRATED_PROBABILITY_FIELDS, "calibrated_probabilities"),
    ):
        scalar_values: list[float] = []
        for field in fields:
            if not _is_present(row.get(field)):
                continue
            number = _finite_number(row.get(field))
            if number is None:
                errors.append(f"{field} must be numeric and finite")
            elif number < 0.0:
                errors.append(f"{field} must be non-negative")
            else:
                scalar_values.append(number)
        if len(scalar_values) == 3 and not math.isclose(sum(scalar_values), 1.0, abs_tol=1e-6):
            errors.append(f"{mapping_field} scalar probability sum must equal 1 within 1e-6")
        if _is_present(row.get(mapping_field)):
            errors.extend(_probability_mapping_errors(row.get(mapping_field), mapping_field))
            mapping = row.get(mapping_field)
            if isinstance(mapping, Mapping) and set(mapping) == PROBABILITY_CLASS_KEYS:
                scalar_by_label = {
                    "UP": row.get(fields[0]),
                    "DOWN": row.get(fields[1]),
                    "FLAT": row.get(fields[2]),
                }
                for label, scalar in scalar_by_label.items():
                    scalar_number = _finite_number(scalar)
                    mapping_number = _finite_number(mapping.get(label))
                    if (
                        scalar_number is not None
                        and mapping_number is not None
                        and not math.isclose(scalar_number, mapping_number, abs_tol=1e-12)
                    ):
                        errors.append(f"{mapping_field}.{label} does not match scalar alias")
    for legacy, calibrated in zip(PROBABILITY_FIELDS, CALIBRATED_PROBABILITY_FIELDS):
        legacy_number = _finite_number(row.get(legacy))
        calibrated_number = _finite_number(row.get(calibrated))
        if (
            legacy_number is not None
            and calibrated_number is not None
            and not math.isclose(legacy_number, calibrated_number, abs_tol=1e-12)
        ):
            errors.append(f"{legacy} must equal backward-compatible alias {calibrated}")
    layers = row.get("prediction_layers")
    if _is_present(layers):
        if not isinstance(layers, Mapping):
            errors.append("prediction_layers must be an object")
        else:
            required_layers = {
                "raw_model_softmax_temperature_1",
                "calibrated_model_softmax",
                "sidecar_selected",
            }
            missing_layers = sorted(required_layers - set(layers))
            if missing_layers:
                errors.append(f"prediction_layers missing required layers: {missing_layers!r}")
    if row.get("downstream_policy_output_must_not_be_conflated_with_sidecar_argmax") is not True:
        errors.append("downstream policy separation flag must be true")
    alignment_inputs = (
        "candidate_id", "symbol", "interval", "horizon", "split",
        "row_index_global", "row_index_split", "timestamp",
    )
    if all(_is_present(row.get(field)) for field in alignment_inputs):
        try:
            expected_alignment_key = build_prediction_row_alignment_key(
                candidate_id=str(row["candidate_id"]), symbol=str(row["symbol"]),
                interval=str(row["interval"]), horizon=int(row["horizon"]),
                split=str(row["split"]), row_index_global=int(row["row_index_global"]),
                row_index_split=int(row["row_index_split"]), timestamp=str(row["timestamp"]),
            )
            if row.get("row_alignment_key") != expected_alignment_key:
                errors.append("row_alignment_key does not match canonical row identity")
        except (TypeError, ValueError):
            errors.append("row alignment identity fields have invalid types")
    return list(dict.fromkeys(errors))


def _forbidden_source_errors(row: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    source_values = [row.get("prediction_source_stage")]
    source_values.extend(row.get(field) for field in PROVENANCE_FIELDS)
    for value in source_values:
        source = str(value or "").strip().lower()
        if not source:
            continue
        if any(forbidden in source for forbidden in FORBIDDEN_PREDICTION_SOURCES):
            errors.append(f"forbidden prediction source: {value}")
    if row.get("predicted_label_from_actual") is True or row.get("used_target_as_prediction") is True:
        errors.append("row declares actual/target label substitution as prediction")
    return errors


def validate_prediction_sidecar_row(
    row: Mapping[str, Any], *, require_field_contract: bool = False
) -> list[str]:
    """Validate one row. Empty result means the row contract is satisfied."""
    if not isinstance(row, Mapping):
        return ["row must be a mapping"]
    normalized = normalize_prediction_sidecar_row(row)
    errors = [field + " is required" for field in REQUIRED_FIELDS if not _is_present(normalized.get(field))]
    for alternatives in ALTERNATIVE_REQUIRED_FIELDS:
        if not any(_is_present(normalized.get(field)) for field in alternatives):
            errors.append(" or ".join(alternatives) + " is required")

    predicted_label = normalized.get("predicted_label")
    if _is_present(predicted_label) and predicted_label not in PREDICTION_LABELS:
        errors.append("predicted_label must be one of UP/DOWN/FLAT")
    split_name = normalized.get("split_name")
    if _is_present(split_name) and split_name not in SPLIT_NAMES:
        errors.append("split_name must be one of train/val/test")

    probabilities: list[float] = []
    for field in PROBABILITY_FIELDS:
        if _is_present(normalized.get(field)):
            number = _finite_number(normalized.get(field))
            if number is None:
                errors.append(f"{field} must be numeric and finite")
            elif not 0.0 <= number <= 1.0:
                errors.append(f"{field} must be between 0 and 1")
            else:
                probabilities.append(number)
    if len(probabilities) == len(PROBABILITY_FIELDS) and not 0.98 <= sum(probabilities) <= 1.02:
        errors.append("probability sum must be between 0.98 and 1.02")
    if _is_present(normalized.get("confidence")):
        confidence = _finite_number(normalized.get("confidence"))
        if confidence is None:
            errors.append("confidence must be numeric and finite")
        elif not 0.0 <= confidence <= 1.0:
            errors.append("confidence must be between 0 and 1")

    errors.extend(_forbidden_source_errors(row))
    if require_field_contract or any(
        field in row
        for field in (
            "sidecar_schema_version",
            "prediction_field_contract_version",
            "raw_probabilities",
            "row_alignment_key",
        )
    ):
        errors.extend(_field_contract_errors(normalized))
    return list(dict.fromkeys(errors))


def validate_prediction_sidecar_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    expected_row_count: int | None,
    denominator_scope: str,
    expected_config_id: str | None = None,
    expected_model_version: str | None = None,
    expected_feature_version: str | None = None,
    expected_label_version: str | None = None,
    expected_candidate_id: str | None = None,
    expected_run_id: str | None = None,
    expected_symbol: str | None = None,
    expected_interval: str | None = None,
    expected_horizon_candles: int | None = None,
    require_field_contract: bool = False,
) -> dict[str, Any]:
    materialized = list(rows)
    normalized_rows = [normalize_prediction_sidecar_row(row) for row in materialized]
    errors: list[str] = []
    warnings: list[str] = []
    row_errors: dict[str, list[str]] = {}
    probability_sum_invalid = 0
    confidence_mismatch = 0

    if not str(denominator_scope or "").strip():
        errors.append("denominator_scope must be explicit")
    if denominator_scope == FULL_DATASET_DENOMINATOR_SCOPE and expected_row_count != FULL_DATASET_ROW_COUNT:
        errors.append("FULL_DATASET_6481 requires expected_row_count=6481")
    if expected_row_count is not None and len(normalized_rows) != expected_row_count:
        errors.append(f"row_count {len(normalized_rows)} does not equal expected_row_count {expected_row_count}")
    if not normalized_rows:
        errors.append("prediction row stream is missing or empty")

    for index, (original, row) in enumerate(zip(materialized, normalized_rows)):
        current_errors = validate_prediction_sidecar_row(
            original, require_field_contract=require_field_contract
        )
        if current_errors:
            row_errors[str(index)] = current_errors
            errors.extend(f"row {index}: {message}" for message in current_errors)
        probabilities = [_finite_number(row.get(field)) for field in PROBABILITY_FIELDS]
        if all(value is not None for value in probabilities):
            values = [float(value) for value in probabilities if value is not None]
            if not 0.98 <= sum(values) <= 1.02:
                probability_sum_invalid += 1
            confidence = _finite_number(row.get("confidence"))
            if confidence is not None and not math.isclose(confidence, max(values), abs_tol=1e-6):
                confidence_mismatch += 1

    if confidence_mismatch:
        warnings.append(
            f"confidence differs from max probability on {confidence_mismatch} rows; pipeline semantics may differ"
        )

    join_keys = [tuple(row.get(field) for field in JOIN_KEY_FIELDS) for row in normalized_rows]
    join_key_counts = Counter(join_keys)
    duplicate_join_key_count = sum(count - 1 for count in join_key_counts.values() if count > 1)
    if duplicate_join_key_count:
        errors.append(f"duplicate symbol+interval+candle_open_time keys: {duplicate_join_key_count}")

    alignment_keys = [row.get("row_alignment_key") for row in normalized_rows]
    alignment_key_counts = Counter(alignment_keys)
    duplicate_alignment_key_count = sum(
        count - 1
        for key, count in alignment_key_counts.items()
        if _is_present(key) and count > 1
    )
    if duplicate_alignment_key_count:
        errors.append(f"duplicate row_alignment_key values: {duplicate_alignment_key_count}")

    split_counts = Counter(str(row.get("split_name") or "") for row in normalized_rows)
    split_counts.pop("", None)
    if sum(split_counts.values()) != len(normalized_rows):
        errors.append("split_counts do not sum to row_count")
    if denominator_scope == FULL_DATASET_DENOMINATOR_SCOPE:
        if set(split_counts) == {"test"}:
            errors.append("test-only rows cannot satisfy FULL_DATASET_6481")
        missing_splits = sorted(set(SPLIT_NAMES) - set(split_counts))
        if missing_splits:
            errors.append(f"FULL_DATASET_6481 requires train/val/test splits; missing: {missing_splits!r}")
    for split_name, split_count in split_counts.items():
        declared_totals = {
            row.get("split_total_rows")
            for row in normalized_rows
            if row.get("split_name") == split_name
        }
        if declared_totals != {split_count}:
            errors.append(
                f"split_total_rows mismatch for {split_name}: expected {split_count}, observed {sorted(map(str, declared_totals))}"
            )
    label_distribution = Counter(str(row.get("predicted_label") or "") for row in normalized_rows)
    label_distribution.pop("", None)

    consistency_expected = {
        "config_id": expected_config_id,
        "model_version": expected_model_version,
        "feature_version": expected_feature_version,
        "label_version": expected_label_version,
        "candidate_id": expected_candidate_id,
        "run_id": expected_run_id,
        "symbol": expected_symbol,
        "interval": expected_interval,
        "horizon_candles": expected_horizon_candles,
    }
    consistency: dict[str, Any] = {}
    for field in (*consistency_expected, "model_name"):
        expected = consistency_expected.get(field)
        observed = sorted({str(row.get(field)) for row in normalized_rows if _is_present(row.get(field))})
        mixed = len(observed) > 1
        mismatch = (expected is not None and observed != [str(expected)]) or mixed
        consistency[field] = {"expected": expected, "observed": observed, "matches": not mismatch}
        if mismatch:
            if mixed:
                errors.append(f"{field} has mixed values: {observed!r}")
            else:
                errors.append(f"{field} mismatch: expected {expected!r}, observed {observed!r}")

    row_identities = [
        ("dataset_row_index", row.get("dataset_row_index"))
        if _is_present(row.get("dataset_row_index"))
        else ("row_id", row.get("row_id"))
        for row in normalized_rows
    ]
    identity_counts = Counter(row_identities)
    duplicate_row_identity_count = sum(count - 1 for count in identity_counts.values() if count > 1)
    if duplicate_row_identity_count:
        errors.append(f"duplicate dataset row identities: {duplicate_row_identity_count}")

    forbidden_errors = [error for error in errors if "forbidden prediction source" in error or "substitution" in error]
    return {
        "status": "PREDICTION_SIDECAR_INVALID" if errors else "PREDICTION_SIDECAR_VALID",
        "row_count": len(normalized_rows),
        "expected_row_count": expected_row_count,
        "denominator_scope": denominator_scope,
        "unique_join_key_count": len(join_key_counts),
        "duplicate_join_key_count": duplicate_join_key_count,
        "duplicate_row_identity_count": duplicate_row_identity_count,
        "duplicate_row_alignment_key_count": duplicate_alignment_key_count,
        "row_alignment_key_unique": duplicate_alignment_key_count == 0,
        "split_counts": dict(sorted(split_counts.items())),
        "predicted_label_distribution": dict(sorted(label_distribution.items())),
        "probability_validation": {
            "tolerance": [0.98, 1.02],
            "invalid_sum_row_count": probability_sum_invalid,
            "confidence_mismatch_row_count": confidence_mismatch,
        },
        "prediction_field_contract_version": PREDICTION_FIELD_CONTRACT_VERSION,
        "config_consistency": consistency,
        "forbidden_substitution_check": {
            "status": "FAILED" if forbidden_errors else "PASSED",
            "actual_label_allowed_only_as_target_field": True,
            "errors": forbidden_errors,
        },
        "manifest_requirements": ["relative_path", "schema_version", "denominator_scope", "row_count", "sha256", "split_counts"],
        "companion_artifacts_required": ["full_dataset_prediction_stream_summary.json", "prediction_payload_schema.json"],
        "row_errors": row_errors,
        "errors": list(dict.fromkeys(errors)),
        "warnings": warnings,
    }


def build_prediction_sidecar_summary(
    rows: Iterable[Mapping[str, Any]],
    validation: Mapping[str, Any],
    metadata: Mapping[str, Any],
    *,
    exact_file_bytes: bytes | None = None,
) -> dict[str, Any]:
    normalized_rows = [normalize_prediction_sidecar_row(row) for row in rows]
    encoded = exact_file_bytes
    if encoded is None:
        encoded = _canonical_jsonl(normalized_rows).encode("utf-8")
    return {
        "schema_version": SIDECAR_SCHEMA_VERSION,
        "sidecar_schema_version": SIDECAR_SCHEMA_VERSION,
        "prediction_field_contract_version": PREDICTION_FIELD_CONTRACT_VERSION,
        "relative_path": "prediction_payloads/full_dataset_prediction_stream.jsonl",
        "denominator_scope": validation.get("denominator_scope"),
        "row_count": len(normalized_rows),
        "expected_row_count": validation.get("expected_row_count"),
        "split_counts": dict(validation.get("split_counts") or {}),
        "predicted_label_distribution": dict(validation.get("predicted_label_distribution") or {}),
        "sha256": sha256(encoded).hexdigest(),
        "size_bytes": len(encoded),
        "hash_contract": HASH_CONTRACT,
        "line_ending_contract": LINE_ENDING_CONTRACT,
        "byte_size_contract": BYTE_SIZE_CONTRACT,
        "writer_contract_version": WRITER_CONTRACT_VERSION,
        "sidecar_writer_version": WRITER_CONTRACT_VERSION,
        "row_alignment_key_present": all(
            _is_present(row.get("row_alignment_key")) for row in normalized_rows
        ),
        "row_alignment_key_unique": validation.get("row_alignment_key_unique") is True,
        "actual_label_present": all(_is_present(row.get("actual_label")) for row in normalized_rows),
        "raw_probabilities_present": all(
            _is_present(row.get("raw_probabilities")) for row in normalized_rows
        ),
        "calibrated_probabilities_present": all(
            _is_present(row.get("calibrated_probabilities")) for row in normalized_rows
        ),
        "prediction_layers_present": all(
            _is_present(row.get("prediction_layers")) for row in normalized_rows
        ),
        "downstream_policy_output_available_in_writer": all(
            row.get("downstream_policy_output_available_in_writer") is True
            for row in normalized_rows
        ),
        "raw_probability_source": "direction_logits_temperature_1_softmax",
        "calibrated_probability_source": "current_temperature_scaled_model_probability_output",
        "actual_label_source": "source_row.direction_label",
        "h08_denominator_fix_applied": False,
        "validation_status": validation.get("status"),
        "config_consistency": validation.get("config_consistency"),
        "metadata": dict(metadata),
    }


def build_prediction_payload_schema() -> dict[str, Any]:
    properties = {field: {} for field in (*REQUIRED_FIELDS, *OPTIONAL_FIELDS)}
    for field in ("symbol", "interval", "candle_open_time", "feature_version", "label_version", "config_id", "model_name", "model_version", "prediction_source_stage"):
        properties[field] = {"type": "string", "minLength": 1}
    properties["predicted_label"] = {"type": "string", "enum": list(PREDICTION_LABELS)}
    properties["split_name"] = {"type": "string", "enum": list(SPLIT_NAMES)}
    for field in (*PROBABILITY_FIELDS, "confidence"):
        properties[field] = {"type": "number", "minimum": 0, "maximum": 1}
    for field in (*RAW_PROBABILITY_FIELDS, *CALIBRATED_PROBABILITY_FIELDS):
        properties[field] = {"type": "number", "minimum": 0, "maximum": 1}
    probability_object = {
        "type": "object",
        "required": ["DOWN", "FLAT", "UP"],
        "properties": {
            label: {"type": "number", "minimum": 0, "maximum": 1}
            for label in ("DOWN", "FLAT", "UP")
        },
        "additionalProperties": False,
    }
    properties["raw_probabilities"] = probability_object
    properties["calibrated_probabilities"] = probability_object
    properties["prediction_layers"] = {
        "type": "object",
        "required": [
            "raw_model_softmax_temperature_1",
            "calibrated_model_softmax",
            "sidecar_selected",
        ],
    }
    for field in ("actual_label", "current_predicted_label", "sidecar_argmax_label"):
        properties[field] = {"type": "string", "enum": list(PREDICTION_LABELS)}
    for field in ("row_index_global", "row_index_split", "horizon"):
        properties[field] = {"type": "integer", "minimum": 0}
    for field in (
        "sidecar_schema_version",
        "sidecar_writer_version",
        "prediction_field_contract_version",
    ):
        properties[field] = {"type": "string", "const": PREDICTION_FIELD_CONTRACT_VERSION}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "prediction_payload_schema.json",
        "title": "Full-dataset prediction sidecar row",
        "schema_version": SIDECAR_SCHEMA_VERSION,
        "type": "object",
        "required": list(dict.fromkeys((*REQUIRED_FIELDS, *FIELD_CONTRACT_REQUIRED_FIELDS))),
        "anyOf": [
            {"required": ["dataset_row_index", "run_id"]},
            {"required": ["dataset_row_index", "candidate_id"]},
            {"required": ["row_id", "run_id"]},
            {"required": ["row_id", "candidate_id"]},
        ],
        "properties": properties,
        "additionalProperties": False,
        "join_key": list(JOIN_KEY_FIELDS),
        "row_alignment_key": {
            "algorithm": "sha256 of canonical JSON",
            "fields": [
                "candidate_id", "symbol", "interval", "horizon", "split",
                "row_index_global", "row_index_split", "timestamp",
            ],
            "path_dependent": False,
        },
        "probability_semantics": {
            "legacy_aliases": {
                "prob_down": "calibrated_prob_down",
                "prob_flat": "calibrated_prob_flat",
                "prob_up": "calibrated_prob_up",
            },
            "raw_probability_source": "direction_logits_temperature_1_softmax",
            "calibrated_probability_source": "current temperature-scaled model probability output",
        },
        "guardrails": [
            "actual_label is target-only and must never populate predicted_label",
            "ml_labels.direction_label is forbidden as prediction source",
            "source/config/model/feature/label mismatches fail closed",
            "prediction layers are explicit and downstream policy output is never inferred",
            "h08 denominator fix is not part of ml38.10.69",
        ],
        "summary_contract": {
            "hash_contract": HASH_CONTRACT,
            "line_ending_contract": LINE_ENDING_CONTRACT,
            "byte_size_contract": BYTE_SIZE_CONTRACT,
            "writer_contract_version": WRITER_CONTRACT_VERSION,
            "sha256_field_semantics": "sha256 of exact JSONL file bytes after write",
            "size_bytes_field_semantics": "exact JSONL file size after write",
        },
    }


def build_archive_status_metadata(*, archive_expected: bool | None = None) -> dict[str, Any]:
    """Describe archive state at sidecar-write time without claiming later packaging facts."""
    if archive_expected is False:
        status = "NOT_REQUESTED"
        created: bool | None = False
        contains: bool | str | None = False
    elif archive_expected is True:
        status = "MISSING"
        created = False
        contains = "unknown"
    else:
        status = "UNKNOWN"
        created = None
        contains = "unknown"
    return {
        "archive_expected": archive_expected,
        "archive_created": created,
        "archive_path": None,
        "archive_contains_sidecars": contains,
        "archive_status": status,
        "sidecar_retention_confirmed": False,
    }


def build_timeout_exit_code_metadata() -> dict[str, Any]:
    """Represent completion facts unavailable inside the sidecar writer explicitly."""
    return {
        "controlling_shell_exit_code": None,
        "python_exit_code": None,
        "timeout_detected": None,
        "child_completed_later": None,
        "completion_marker_written": False,
        "run_exit_code_status": "UNKNOWN_OR_EXTERNAL",
    }


def validate_prediction_sidecar_file_contract(
    stream_path: str | Path, summary: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate exact bytes without rewriting legacy or current artifacts."""
    path = Path(stream_path)
    exact = path.read_bytes()
    exact_hash = sha256(exact).hexdigest()
    expected_hash = str(summary.get("sha256") or "")
    expected_size = summary.get("size_bytes")
    normalized = exact.replace(b"\r\n", b"\n")
    normalized_only = (
        expected_hash == sha256(normalized).hexdigest()
        and expected_hash != exact_hash
    )
    errors: list[str] = []
    if expected_hash != exact_hash:
        errors.append(
            "SUMMARY_HASH_MATCHES_LF_NORMALIZED_NOT_EXACT_BYTES"
            if normalized_only
            else "SUMMARY_HASH_DOES_NOT_MATCH_EXACT_BYTES"
        )
    if expected_size != len(exact):
        errors.append("SUMMARY_SIZE_DOES_NOT_MATCH_EXACT_BYTES")
    declared_contract = summary.get("hash_contract")
    if declared_contract not in (None, HASH_CONTRACT):
        errors.append("UNSUPPORTED_HASH_CONTRACT")
    return {
        "status": "PREDICTION_SIDECAR_EXACT_BYTES_INVALID" if errors else "PREDICTION_SIDECAR_EXACT_BYTES_VALID",
        "exact_file_sha256": exact_hash,
        "exact_file_size_bytes": len(exact),
        "summary_matches_exact_bytes": not errors,
        "summary_matches_lf_normalized_not_exact_bytes": normalized_only,
        "errors": errors,
    }


def build_sidecar_export_implementation_metadata() -> dict[str, Any]:
    return {
        "implementation_status": "IMPLEMENTED_NOT_EXECUTED",
        "sidecar_schema_defined": True,
        "sidecar_writer_defined": True,
        "sidecar_validator_defined": True,
        "compact_whitelist_defined": True,
        "real_full_dataset_stream_created": False,
        "real_quick_quality_run_executed": False,
        "db_writes": False,
        "ml_labels_writes": False,
        "ml_predictions_writes": False,
        "requires_separate_approval_for_generation": True,
        "guardrails": [
            "DO_NOT_SUBSTITUTE_ACTUAL_LABEL_FOR_PREDICTION",
            "FAIL_CLOSED_ON_SOURCE_OR_CONFIG_MISMATCH",
            "FULL_6481_CASCADE_NOT_ALLOWED_UNTIL_STREAM_EXISTS",
        ],
    }


def build_ml38_10_50_sidecar_export_implementation_decision() -> list[str]:
    return [
        "PREDICTION_SIDECAR_EXPORTER_IMPLEMENTED",
        "PREDICTION_SIDECAR_SCHEMA_DEFINED",
        "PREDICTION_SIDECAR_VALIDATOR_IMPLEMENTED",
        "COMPACT_WHITELIST_IMPLEMENTED",
        "SYNTHETIC_TESTS_ONLY",
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


def write_prediction_sidecar_artifacts(
    output_dir: str | Path,
    rows: Iterable[Mapping[str, Any]],
    *,
    metadata: Mapping[str, Any],
    expected_row_count: int | None,
    denominator_scope: str,
    dry_run: bool = False,
    allow_overwrite: bool = False,
    require_field_contract: bool = True,
) -> dict[str, Any]:
    materialized = list(rows)
    normalized_rows = [normalize_prediction_sidecar_row(row) for row in materialized]
    validation = validate_prediction_sidecar_rows(
        materialized,
        expected_row_count=expected_row_count,
        denominator_scope=denominator_scope,
        expected_config_id=metadata.get("config_id"),
        expected_model_version=metadata.get("model_version"),
        expected_feature_version=metadata.get("feature_version"),
        expected_label_version=metadata.get("label_version"),
        expected_candidate_id=metadata.get("candidate_id"),
        expected_run_id=metadata.get("run_id"),
        expected_symbol=metadata.get("symbol"),
        expected_interval=metadata.get("interval"),
        expected_horizon_candles=metadata.get("horizon_candles"),
        require_field_contract=require_field_contract,
    )
    if validation["status"] != "PREDICTION_SIDECAR_VALID":
        raise ValueError("prediction sidecar validation failed: " + "; ".join(validation["errors"][:5]))

    schema = build_prediction_payload_schema()
    payload_dir = Path(output_dir) / "prediction_payloads"
    paths = {
        "stream_path": payload_dir / "full_dataset_prediction_stream.jsonl",
        "summary_path": payload_dir / "full_dataset_prediction_stream_summary.json",
        "schema_path": payload_dir / "prediction_payload_schema.json",
    }
    existing = [path for path in paths.values() if path.exists()]
    if existing and not allow_overwrite:
        raise FileExistsError(
            "prediction sidecar overwrite is disabled; existing targets: "
            + ", ".join(str(path) for path in existing)
        )
    if not dry_run:
        payload_dir.mkdir(parents=True, exist_ok=True)
        stream_bytes = _canonical_jsonl(normalized_rows).encode("utf-8")
        paths["stream_path"].write_bytes(stream_bytes)
        exact_file_bytes = paths["stream_path"].read_bytes()
        runtime_metadata = dict(metadata)
        runtime_metadata["sidecar_runtime_truth"] = {
            "runtime_execution_status": "EXECUTED",
            "export_requested": True,
            "export_completed": True,
            "real_quick_quality_run_executed": metadata.get("real_quick_quality_run_executed"),
            "real_full_dataset_stream_created": True,
            "sidecar_validation_status": validation.get("status"),
            "hash_contract": HASH_CONTRACT,
            "archive": build_archive_status_metadata(
                archive_expected=metadata.get("archive_expected")
            ),
            "completion": build_timeout_exit_code_metadata(),
        }
        summary = build_prediction_sidecar_summary(
            normalized_rows,
            validation,
            runtime_metadata,
            exact_file_bytes=exact_file_bytes,
        )
        file_contract = validate_prediction_sidecar_file_contract(paths["stream_path"], summary)
        if file_contract["status"] != "PREDICTION_SIDECAR_EXACT_BYTES_VALID":
            raise ValueError("prediction sidecar exact-byte validation failed")
        paths["summary_path"].write_bytes(
            (json.dumps(summary, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        )
        paths["schema_path"].write_bytes(
            (json.dumps(schema, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        )
    else:
        preview_metadata = dict(metadata)
        preview_metadata["sidecar_runtime_truth"] = {
            "runtime_execution_status": "NOT_EXECUTED_DRY_RUN",
            "export_requested": True,
            "export_completed": False,
            "real_quick_quality_run_executed": metadata.get("real_quick_quality_run_executed"),
            "real_full_dataset_stream_created": False,
            "sidecar_validation_status": validation.get("status"),
            "hash_contract": HASH_CONTRACT,
            "archive": build_archive_status_metadata(
                archive_expected=metadata.get("archive_expected")
            ),
            "completion": build_timeout_exit_code_metadata(),
        }
        summary = build_prediction_sidecar_summary(normalized_rows, validation, preview_metadata)
    return {
        "status": "DRY_RUN_VALID" if dry_run else "PREDICTION_SIDECAR_ARTIFACTS_WRITTEN",
        "dry_run": dry_run,
        "paths": {key: str(value) for key, value in paths.items()},
        "validation": validation,
        "summary": summary,
        "schema": schema,
    }
