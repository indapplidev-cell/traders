from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from app.experiments.prediction_sidecar_exporter import (
    FULL_DATASET_DENOMINATOR_SCOPE,
    FULL_DATASET_ROW_COUNT,
    PREDICTION_LABELS,
    validate_prediction_sidecar_rows,
    write_prediction_sidecar_artifacts,
)


QUICK_QUALITY_ENTRYPOINT = (
    "python run_fv3_cached_tuning.py --quick-quality --quick-quality-symbol SOLUSDT"
)
PREDICTION_SOURCE_STAGE = "training_service_calibrated_model_softmax_argmax"


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


def build_full_dataset_prediction_sidecar_rows(
    *,
    split_rows: Mapping[str, Sequence[Any]],
    split_probabilities: Mapping[str, Sequence[Any]],
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
        if len(source_rows) != len(probabilities):
            raise ValueError(
                f"row/probability count mismatch for {source_name}: "
                f"{len(source_rows)} != {len(probabilities)}"
            )
        for split_row_index, (source_row, probability_value) in enumerate(
            zip(source_rows, probabilities)
        ):
            prob_up, prob_down, prob_flat = _probability_triplet(probability_value)
            probability_values = (prob_up, prob_down, prob_flat)
            predicted_index = max(range(3), key=probability_values.__getitem__)
            row = {
                "symbol": symbol,
                "interval": interval,
                "candle_open_time": _timestamp(_value(source_row, "candle_open_time")),
                "dataset_row_index": dataset_row_index,
                "split_name": sidecar_name,
                "split_row_index": split_row_index,
                "split_total_rows": len(source_rows),
                "feature_version": feature_version,
                "label_version": label_version,
                "horizon_candles": int(horizon_candles),
                "config_id": config_id,
                "model_name": model_name,
                "model_version": model_version,
                "run_id": run_id,
                "candidate_id": candidate_id,
                "predicted_label": PREDICTION_LABELS[predicted_index],
                "prediction_source_stage": prediction_source_stage,
                "predicted_label_source": "model_probability_argmax",
                "prob_up": prob_up,
                "prob_down": prob_down,
                "prob_flat": prob_flat,
                "confidence": max(probability_values),
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
