from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
import math
from pathlib import Path
from typing import Any

from app.experiments.prediction_sidecar_exporter import (
    FULL_DATASET_DENOMINATOR_SCOPE,
    FULL_DATASET_ROW_COUNT,
    PREDICTION_FIELD_CONTRACT_VERSION,
    PREDICTION_LABELS,
    SIDECAR_SCHEMA_VERSION,
    WRITER_CONTRACT_VERSION,
    build_prediction_row_alignment_key,
    validate_prediction_sidecar_rows,
    write_prediction_sidecar_artifacts,
)


QUICK_QUALITY_ENTRYPOINT = (
    "python run_fv3_cached_tuning.py --quick-quality --quick-quality-symbol SOLUSDT"
)
PREDICTION_SOURCE_STAGE = "training_service_calibrated_model_softmax_argmax"
RAW_PROBABILITY_SOURCE = "direction_logits_temperature_1_softmax"
CALIBRATED_PROBABILITY_SOURCE = "direction_logits_temperature_scaled_softmax"


def _value(row: Any, field: str, default: Any = None) -> Any:
    if isinstance(row, Mapping):
        return row.get(field, default)
    return getattr(row, field, default)


def _timestamp(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value or "").strip()


def _probability_triplet(value: Any) -> tuple[float, float, float]:
    if isinstance(value, Mapping):
        values = (value.get("prob_up"), value.get("prob_down"), value.get("prob_flat"))
    else:
        values = tuple(value) if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) else ()
    if len(values) != 3:
        raise ValueError("each model prediction must contain UP/DOWN/FLAT probabilities")
    try:
        return float(values[0]), float(values[1]), float(values[2])
    except (TypeError, ValueError) as exc:
        raise ValueError("model probabilities must be numeric") from exc


def _raw_softmax_triplet(value: Any) -> tuple[float, float, float]:
    """Return stable UP/DOWN/FLAT softmax probabilities for one logits row."""
    if isinstance(value, Mapping):
        values = (value.get("logit_up"), value.get("logit_down"), value.get("logit_flat"))
    else:
        values = tuple(value) if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) else ()
    if len(values) != 3:
        raise ValueError("each direction_logits row must contain UP/DOWN/FLAT logits")
    try:
        logits = tuple(float(item) for item in values)
    except (TypeError, ValueError) as exc:
        raise ValueError("direction_logits must be numeric") from exc
    if not all(math.isfinite(item) for item in logits):
        raise ValueError("direction_logits must be finite")
    maximum = max(logits)
    exponentials = tuple(math.exp(item - maximum) for item in logits)
    denominator = sum(exponentials)
    if not math.isfinite(denominator) or denominator <= 0.0:
        raise ValueError("direction_logits softmax denominator must be finite and positive")
    return tuple(item / denominator for item in exponentials)  # type: ignore[return-value]


def build_full_dataset_prediction_sidecar_rows(
    *,
    split_rows: Mapping[str, Sequence[Any]],
    split_probabilities: Mapping[str, Sequence[Any]],
    split_direction_logits: Mapping[str, Sequence[Any]],
    symbol: str,
    interval: str,
    feature_version: str,
    label_version: str,
    horizon_candles: int,
    config_id: str,
    model_name: str,
    model_version: str,
    run_id: str,
    candidate_id: str,
    prediction_source_stage: str = PREDICTION_SOURCE_STAGE,
) -> list[dict[str, Any]]:
    """Join model probabilities to original rows without deriving predictions from targets."""
    rows: list[dict[str, Any]] = []
    aliases = (("train", "train"), ("validation", "val"), ("val", "val"), ("test", "test"))
    consumed: set[str] = set()
    dataset_row_index = 0
    for source_name, sidecar_name in aliases:
        if sidecar_name in consumed or source_name not in split_rows:
            continue
        consumed.add(sidecar_name)
        source_rows = list(split_rows.get(source_name) or [])
        probabilities = list(
            split_probabilities.get(source_name)
            or split_probabilities.get(sidecar_name)
            or []
        )
        direction_logits = list(
            split_direction_logits.get(source_name)
            or split_direction_logits.get(sidecar_name)
            or []
        )
        if len(source_rows) != len(probabilities):
            raise ValueError(
                f"row/probability count mismatch for {source_name}: "
                f"{len(source_rows)} != {len(probabilities)}"
            )
        if len(source_rows) != len(direction_logits):
            raise ValueError(
                f"row/direction_logits count mismatch for {source_name}: "
                f"{len(source_rows)} != {len(direction_logits)}"
            )
        for split_row_index, (source_row, probability_value, logits_value) in enumerate(
            zip(source_rows, probabilities, direction_logits)
        ):
            prob_up, prob_down, prob_flat = _probability_triplet(probability_value)
            raw_prob_up, raw_prob_down, raw_prob_flat = _raw_softmax_triplet(logits_value)
            probability_values = (prob_up, prob_down, prob_flat)
            predicted_index = max(range(3), key=probability_values.__getitem__)
            raw_probability_values = (raw_prob_up, raw_prob_down, raw_prob_flat)
            raw_predicted_index = max(range(3), key=raw_probability_values.__getitem__)
            timestamp = _timestamp(_value(source_row, "candle_open_time"))
            actual_label_value = _value(source_row, "direction_label")
            actual_label = str(actual_label_value or "").strip().upper()
            row_alignment_key = build_prediction_row_alignment_key(
                candidate_id=candidate_id,
                symbol=symbol,
                interval=interval,
                horizon=horizon_candles,
                split=sidecar_name,
                row_index_global=dataset_row_index,
                row_index_split=split_row_index,
                timestamp=timestamp,
            )
            sidecar_argmax_label = PREDICTION_LABELS[predicted_index]
            raw_argmax_label = PREDICTION_LABELS[raw_predicted_index]
            raw_probabilities = {
                "DOWN": raw_prob_down,
                "FLAT": raw_prob_flat,
                "UP": raw_prob_up,
            }
            calibrated_probabilities = {
                "DOWN": prob_down,
                "FLAT": prob_flat,
                "UP": prob_up,
            }
            row = {
                "sidecar_schema_version": SIDECAR_SCHEMA_VERSION,
                "sidecar_writer_version": WRITER_CONTRACT_VERSION,
                "prediction_field_contract_version": PREDICTION_FIELD_CONTRACT_VERSION,
                "symbol": symbol,
                "interval": interval,
                "candle_open_time": timestamp,
                "timestamp": timestamp,
                "dataset_row_index": dataset_row_index,
                "row_index_global": dataset_row_index,
                "split_name": sidecar_name,
                "split": sidecar_name,
                "split_row_index": split_row_index,
                "row_index_split": split_row_index,
                "split_total_rows": len(source_rows),
                "feature_version": feature_version,
                "label_version": label_version,
                "horizon_candles": int(horizon_candles),
                "horizon": int(horizon_candles),
                "config_id": config_id,
                "model_name": model_name,
                "model_version": model_version,
                "run_id": run_id,
                "candidate_id": candidate_id,
                "row_alignment_key": row_alignment_key,
                "actual_label": actual_label,
                "actual_label_source": "source_row.direction_label",
                "predicted_label": sidecar_argmax_label,
                "current_predicted_label": sidecar_argmax_label,
                "sidecar_argmax_label": sidecar_argmax_label,
                "sidecar_argmax_layer": "calibrated_model_softmax",
                "predicted_label_semantics": "backward-compatible alias of sidecar calibrated argmax",
                "prediction_layer_name": "sidecar_selected",
                "prediction_layer_source": prediction_source_stage,
                "prediction_source_stage": prediction_source_stage,
                "predicted_label_source": "model_probability_argmax",
                "prob_up": prob_up,
                "prob_down": prob_down,
                "prob_flat": prob_flat,
                "raw_prob_up": raw_prob_up,
                "raw_prob_down": raw_prob_down,
                "raw_prob_flat": raw_prob_flat,
                "raw_probabilities": raw_probabilities,
                "calibrated_prob_up": prob_up,
                "calibrated_prob_down": prob_down,
                "calibrated_prob_flat": prob_flat,
                "calibrated_probabilities": calibrated_probabilities,
                "confidence": max(probability_values),
                "prediction_layers": {
                    "raw_model_softmax_temperature_1": {
                        "probabilities": raw_probabilities,
                        "argmax_label": raw_argmax_label,
                    },
                    "calibrated_model_softmax": {
                        "probabilities": calibrated_probabilities,
                        "argmax_label": sidecar_argmax_label,
                    },
                    "sidecar_selected": {
                        "label": sidecar_argmax_label,
                        "source": prediction_source_stage,
                    },
                },
                "downstream_policy_output_available_in_writer": False,
                "downstream_policy_output_reason": "not available at sidecar writer stage",
                "downstream_policy_output_must_not_be_conflated_with_sidecar_argmax": True,
            }
            setup_quality_score = _value(source_row, "setup_quality_score")
            if setup_quality_score is not None:
                row["setup_quality_score"] = setup_quality_score
            rows.append(row)
            dataset_row_index += 1
    return rows


def validate_full_dataset_prediction_sidecar_ready(
    rows: Sequence[Mapping[str, Any]],
    *,
    expected_row_count: int = FULL_DATASET_ROW_COUNT,
    denominator_scope: str = FULL_DATASET_DENOMINATOR_SCOPE,
    config_id: str,
    candidate_id: str,
    run_id: str,
    model_version: str,
    feature_version: str,
    label_version: str,
    horizon_candles: int,
    symbol: str,
    interval: str,
) -> dict[str, Any]:
    return validate_prediction_sidecar_rows(
        rows,
        expected_row_count=expected_row_count,
        denominator_scope=denominator_scope,
        expected_config_id=config_id,
        expected_candidate_id=candidate_id,
        expected_run_id=run_id,
        expected_model_version=model_version,
        expected_feature_version=feature_version,
        expected_label_version=label_version,
        expected_horizon_candles=horizon_candles,
        expected_symbol=symbol,
        expected_interval=interval,
    )


def write_full_dataset_prediction_sidecar_for_candidate(
    output_dir: str | Path,
    rows: Sequence[Mapping[str, Any]],
    *,
    expected_row_count: int = FULL_DATASET_ROW_COUNT,
    denominator_scope: str = FULL_DATASET_DENOMINATOR_SCOPE,
    allow_overwrite: bool = False,
    real_quick_quality_run_executed: bool | None = None,
    archive_expected: bool | None = None,
    **identity: Any,
) -> dict[str, Any]:
    validation = validate_full_dataset_prediction_sidecar_ready(
        rows,
        expected_row_count=expected_row_count,
        denominator_scope=denominator_scope,
        **identity,
    )
    if validation["status"] != "PREDICTION_SIDECAR_VALID":
        raise ValueError(
            "full-dataset prediction sidecar is not ready: "
            + "; ".join(validation["errors"][:8])
        )
    metadata = dict(identity)
    metadata.update(
        denominator_scope=denominator_scope,
        prediction_source_stage=PREDICTION_SOURCE_STAGE,
        real_quick_quality_run_executed=real_quick_quality_run_executed,
        archive_expected=archive_expected,
        full_dataset_prediction_sidecar_wiring=build_sidecar_wiring_metadata(),
    )
    return write_prediction_sidecar_artifacts(
        output_dir,
        rows,
        metadata=metadata,
        expected_row_count=expected_row_count,
        denominator_scope=denominator_scope,
        allow_overwrite=allow_overwrite,
    )


def build_sidecar_wiring_metadata() -> dict[str, Any]:
    return {
        "implementation_status": "WIRED_NOT_EXECUTED",
        "quick_quality_entrypoint": QUICK_QUALITY_ENTRYPOINT,
        "exporter_invocation_wired": True,
        "full_dataset_boundary_required": True,
        "test_only_boundary_rejected": True,
        "sidecar_output_paths_declared": True,
        "overwrite_guard_enabled": True,
        "source_config_consistency_validation": "FAIL_CLOSED",
        "real_quick_quality_run_executed": False,
        "real_full_dataset_stream_created": False,
        "db_writes": False,
        "ml_labels_writes": False,
        "ml_predictions_writes": False,
        "requires_separate_approval_for_generation": True,
        "guardrails": [
            "NO_ACTUAL_OR_TARGET_LABEL_AS_PREDICTION",
            "NO_ML_LABELS_DIRECTION_LABEL_AS_PREDICTION",
            "REJECT_TEST_ONLY_973_STREAM_AS_FULL_DATASET",
            "FAIL_CLOSED_ON_CANDIDATE_RUN_CONFIG_MODEL_FEATURE_LABEL_HORIZON_SYMBOL_INTERVAL_MISMATCH",
            "FAIL_CLOSED_ON_DUPLICATE_ROW_KEYS",
            "FAIL_CLOSED_ON_OVERWRITE_ATTEMPT",
            "FULL_6481_CASCADE_OUTCOME_FORBIDDEN_UNTIL_REAL_STREAM_EXISTS_AND_VALIDATES",
        ],
    }


def build_ml38_10_54_sidecar_wiring_decision() -> list[str]:
    return [
        "SIDECAR_QUICK_QUALITY_WIRING_IMPLEMENTED",
        "EXPORTER_INVOCATION_WIRED_NOT_EXECUTED",
        "FULL_DATASET_BOUNDARY_REQUIRED",
        "TEST_ONLY_973_STREAM_REJECTED",
        "SOURCE_CONFIG_CONSISTENCY_HARDENED",
        "OVERWRITE_GUARD_IMPLEMENTED",
        "REPORTER_ANALYZER_METADATA_WIRED",
        "SYNTHETIC_OR_MOCKED_TESTS_ONLY",
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
