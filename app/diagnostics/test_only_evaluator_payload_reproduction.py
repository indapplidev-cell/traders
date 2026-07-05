from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
from typing import Any, Mapping, Sequence

from app.diagnostics.evaluator_payload_reproduction import (
    reproduce_entry_path_quality_score_read_only,
    reproduce_recovery_guard_decision_read_only,
    reproduce_stop_pressure_risk_score_read_only,
)
from app.diagnostics.predicted_label_payload_trace import (
    PREDICTED_LABEL_FIELDS,
    PROBABILITY_FIELDS,
    TIMESTAMP_FIELDS,
)


DIAGNOSTIC_NAME = "read_only_test_only_evaluator_payload_reproduction_audit"
DIAGNOSTIC_VERSION = "ml38.10.46"
EXECUTION_MODE = "READ_ONLY_TEST_ONLY_NO_TRAINING_NO_DB_WRITES"
REFERENCE_CONFIG_ID = (
    "lv31_h12_tts_thr065_sqmask060_epq070_sp045_"
    "rguard_long_bad_dates_exit45_probe"
)
DENOMINATOR_SCOPE = "TEST_ONLY_973"

_PAYLOAD_PATHS = (
    ("calibrated_decision_diagnostics.calibrated_rows", ("calibrated_decision_diagnostics", "calibrated_rows")),
    ("calibrated_decision_diagnostics.selected_rows", ("calibrated_decision_diagnostics", "selected_rows")),
)
_ENTRY_REQUIRED = (
    "features_json",
    "setup_quality_score",
    "setup_expected_move_atr",
    "setup_invalidation_distance_atr",
    "predicted_label",
)
_RECOVERY_REQUIRED = (
    "current_close",
    "atr_14",
    "future_candles",
    "predicted_label",
    "candidate_config.take_profit_atr",
    "candidate_config.stop_loss_atr",
    "candidate_config.exit_mitigation_loss_r",
)


def _mapping(row: Any) -> dict[str, Any]:
    if isinstance(row, Mapping):
        return dict(row)
    values = getattr(row, "__dict__", {})
    return {key: value for key, value in values.items() if not key.startswith("_")}


def _at_path(payload: Mapping[str, Any], path: Sequence[str]) -> Any:
    value: Any = payload
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _first_field(rows: Sequence[Any], fields: Sequence[str]) -> str | None:
    for field in fields:
        if any(_mapping(row).get(field) is not None for row in rows):
            return field
    return None


def _timestamp_value(row: Any) -> Any:
    values = _mapping(row)
    return next((values.get(field) for field in TIMESTAMP_FIELDS if values.get(field) is not None), None)


def _normalized_timestamp(value: Any) -> str:
    if hasattr(value, "isoformat"):
        value = value.isoformat()
    return str(value or "").replace("+00:00", "Z")


def _join_key(row: Any, *, symbol: str, interval: str) -> tuple[str, str, str]:
    values = _mapping(row)
    return (
        str(values.get("symbol") or symbol).upper(),
        str(values.get("interval") or interval),
        _normalized_timestamp(_timestamp_value(row)),
    )


def _duplicate_count(rows: Sequence[Any], *, symbol: str, interval: str) -> int:
    keys = [_join_key(row, symbol=symbol, interval=interval) for row in rows]
    usable = [key for key in keys if key[-1]]
    return sum(count - 1 for count in Counter(usable).values() if count > 1)


def select_test_prediction_payload(
    probability_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Select the best 973-row prediction list without consulting actual labels."""
    payload = probability_payload or {}
    candidates: list[dict[str, Any]] = []
    for order, (path_name, path) in enumerate(_PAYLOAD_PATHS):
        value = _at_path(payload, path)
        rows = list(value) if isinstance(value, list) else []
        timestamp_field = _first_field(rows, TIMESTAMP_FIELDS)
        predicted_field = _first_field(rows, PREDICTED_LABEL_FIELDS)
        priority = 0
        if timestamp_field and _first_field(rows, ("entry_path_original_predicted_label",)):
            priority = 3
            predicted_field = "entry_path_original_predicted_label"
        elif timestamp_field and _first_field(rows, ("predicted_label",)):
            priority = 2
            predicted_field = "predicted_label"
        elif timestamp_field and _first_field(rows, ("predicted_class", "decision_label")):
            priority = 1
            predicted_field = _first_field(rows, ("predicted_class", "decision_label"))
        candidates.append(
            {
                "path": path_name,
                "rows": rows,
                "row_count": len(rows),
                "timestamp_field": timestamp_field,
                "predicted_label_field": predicted_field,
                "priority": priority,
                "order": order,
            }
        )
    selected = max(candidates, key=lambda row: (row["priority"], row["row_count"], -row["order"]))
    if not selected["rows"]:
        status = "TEST_PREDICTIONS_NOT_FOUND"
    elif not selected["timestamp_field"]:
        status = "TEST_PREDICTIONS_MISSING_TIMESTAMP"
    elif not selected["predicted_label_field"]:
        status = "TEST_PREDICTIONS_MISSING_PREDICTED_LABEL"
    else:
        status = "TEST_TIMESTAMPED_PREDICTIONS_SELECTED"
    return {
        "selected_payload_path": selected["path"] if selected["rows"] else None,
        "rows": selected["rows"],
        "selected_payload_row_count": selected["row_count"],
        "timestamp_field": selected["timestamp_field"],
        "predicted_label_field": selected["predicted_label_field"],
        "probability_fields": [
            field for field in PROBABILITY_FIELDS if _first_field(selected["rows"], (field,))
        ],
        "source_status": status,
        "payload_candidates_checked": [
            {key: row[key] for key in ("path", "row_count", "timestamp_field", "predicted_label_field", "priority")}
            for row in candidates
        ],
    }


def build_test_prediction_payload_source(
    selection: Mapping[str, Any], *, probability_payload_path: str | Path | None = None
) -> dict[str, Any]:
    return {
        "probability_payload_path": str(probability_payload_path) if probability_payload_path else None,
        "payload_candidates_checked": list(selection.get("payload_candidates_checked", [])),
        "selected_payload_path": selection.get("selected_payload_path"),
        "selected_payload_row_count": int(selection.get("selected_payload_row_count") or 0),
        "timestamp_field": selection.get("timestamp_field"),
        "predicted_label_field": selection.get("predicted_label_field"),
        "probability_fields": list(selection.get("probability_fields", [])),
        "source_status": selection.get("source_status"),
        "evidence": (
            f"{selection.get('selected_payload_path')}: "
            f"{int(selection.get('selected_payload_row_count') or 0)} read-only rows"
        ),
    }


def _index(rows: Sequence[Any], *, symbol: str, interval: str) -> dict[tuple[str, str, str], dict[str, Any]]:
    result: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        key = _join_key(row, symbol=symbol, interval=interval)
        if key[-1] and key not in result:
            result[key] = _mapping(row)
    return result


def build_test_prediction_join_board(
    test_prediction_rows: Sequence[Any] | None,
    feature_rows: Sequence[Any] | None = None,
    label_rows: Sequence[Any] | None = None,
    *,
    symbol: str = "SOLUSDT",
    interval: str = "15m",
) -> list[dict[str, Any]]:
    predictions = list(test_prediction_rows or [])
    # The probability artifact already carries evaluator feature/label context. Explicit
    # DB rows can replace these embedded sources, but no DB read is required here.
    features = list(feature_rows) if feature_rows is not None else [
        row for row in predictions if isinstance(_mapping(row).get("features_json"), Mapping)
    ]
    labels = list(label_rows) if label_rows is not None else [
        row for row in predictions
        if _mapping(row).get("actual_label") is not None or _mapping(row).get("direction_label") is not None
    ]
    prediction_keys = {_join_key(row, symbol=symbol, interval=interval) for row in predictions if _timestamp_value(row) is not None}
    feature_keys = set(_index(features, symbol=symbol, interval=interval))
    label_keys = set(_index(labels, symbol=symbol, interval=interval))
    duplicate_counts = (
        _duplicate_count(predictions, symbol=symbol, interval=interval),
        _duplicate_count(features, symbol=symbol, interval=interval),
        _duplicate_count(labels, symbol=symbol, interval=interval),
    )
    matched_features = len(prediction_keys & feature_keys)
    matched_labels = len(prediction_keys & label_keys)
    if any(duplicate_counts):
        status = "TEST_JOIN_DUPLICATES_FOUND"
    elif predictions and matched_features == len(predictions) and matched_labels == len(predictions):
        status = "TEST_JOIN_READY"
    elif matched_features or matched_labels:
        status = "TEST_JOIN_PARTIAL"
    else:
        status = "TEST_JOIN_BLOCKED"
    return [{
        "join_key": "symbol+interval+candle_open_time",
        "test_prediction_rows": len(predictions),
        "matched_feature_rows": matched_features,
        "matched_label_rows": matched_labels,
        "missing_feature_rows": max(0, len(predictions) - matched_features),
        "missing_label_rows": max(0, len(predictions) - matched_labels),
        "duplicate_prediction_rows": duplicate_counts[0],
        "duplicate_feature_rows": duplicate_counts[1],
        "duplicate_label_rows": duplicate_counts[2],
        "join_status": status,
        "denominator_scope": DENOMINATOR_SCOPE,
        "full_dataset_rows_available": False,
    }]


def _joined_rows(
    predictions: Sequence[Any], feature_rows: Sequence[Any] | None, label_rows: Sequence[Any] | None,
    *, symbol: str, interval: str,
) -> list[dict[str, Any]]:
    features = list(feature_rows) if feature_rows is not None else list(predictions)
    labels = list(label_rows) if label_rows is not None else list(predictions)
    feature_index = _index(features, symbol=symbol, interval=interval)
    label_index = _index(labels, symbol=symbol, interval=interval)
    joined = []
    for prediction in predictions:
        key = _join_key(prediction, symbol=symbol, interval=interval)
        if key not in feature_index or key not in label_index:
            continue
        prediction_values = _mapping(prediction)
        # Never inherit a prediction-like field from feature/label rows. In particular,
        # ml_labels.direction_label remains actual/target evidence only.
        base = {**label_index[key], **feature_index[key]}
        for field in PREDICTED_LABEL_FIELDS:
            base.pop(field, None)
        predicted_field = _first_field([prediction_values], PREDICTED_LABEL_FIELDS)
        base.update(prediction_values)
        base["symbol"], base["interval"] = key[0], key[1]
        if predicted_field:
            base["predicted_label"] = prediction_values[predicted_field]
        else:
            base.pop("predicted_label", None)
        joined.append(base)
    return joined


def build_test_only_payload_reproduction_board(
    joined_rows: Sequence[Any] | None,
    *, candidate_config: Mapping[str, Any] | None = None,
    expected_row_count: int | None = None,
) -> list[dict[str, Any]]:
    rows = list(joined_rows or [])
    expected = len(rows) if expected_row_count is None else int(expected_row_count)
    config = dict(candidate_config or {})
    results = (
        reproduce_entry_path_quality_score_read_only(rows, candidate_config=config),
        reproduce_stop_pressure_risk_score_read_only(rows, candidate_config=config),
        reproduce_recovery_guard_decision_read_only(rows, candidate_config=config),
    )
    thresholds = {
        "entry_path_quality_score_by_timestamp": config.get("entry_path_quality_min_threshold", 0.70),
        "stop_pressure_risk_score_by_timestamp": config.get("stop_pressure_max_risk_score", 0.45),
        "recovery_guard_decision_by_timestamp": None,
    }
    board = []
    for result in results:
        reproduced = int(result.get("reproduced_row_count") or 0)
        missing_inputs = sorted({
            item
            for row in result.get("missing_inputs_by_row", [])
            for item in row.get("missing_inputs", [])
        })
        if expected > 0 and reproduced == expected:
            status = "REPRODUCED_READ_ONLY_TEST_ONLY"
        elif reproduced:
            status = "PARTIAL_REPRODUCED_READ_ONLY_TEST_ONLY"
        elif rows:
            status = "SOURCE_FOUND_INPUTS_MISSING"
        else:
            status = "JOIN_KEY_BLOCKED"
        required = list(result.get("required_inputs", []))
        board.append({
            "value_name": result.get("value_name"),
            "denominator_scope": DENOMINATOR_SCOPE,
            "required_inputs": required,
            "available_inputs": sorted(set(required) - set(missing_inputs)),
            "missing_inputs": missing_inputs,
            "reproduction_attempted": True,
            "reproduced_row_count": reproduced,
            "expected_row_count": expected,
            "missing_row_count": max(0, expected - reproduced),
            "duplicate_row_count": int(result.get("duplicate_row_count") or 0),
            "status": status,
            "threshold": thresholds.get(str(result.get("value_name"))),
            "evidence": result.get("source_module_or_function"),
            "requires_db_write": False,
            "requires_training": False,
            "requires_label_builder_change": False,
        })
    return board


def build_test_only_reproduced_mask_summary(
    reproduction_board: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    by_name = {str(row.get("value_name")): row for row in reproduction_board}
    available = {
        "entry": by_name.get("entry_path_quality_score_by_timestamp", {}).get("status") == "REPRODUCED_READ_ONLY_TEST_ONLY",
        "stop": by_name.get("stop_pressure_risk_score_by_timestamp", {}).get("status") == "REPRODUCED_READ_ONLY_TEST_ONLY",
        "recovery": by_name.get("recovery_guard_decision_by_timestamp", {}).get("status") == "REPRODUCED_READ_ONLY_TEST_ONLY",
    }
    count = sum(available.values())
    return {
        "denominator_scope": DENOMINATOR_SCOPE,
        "requested_value_count": 3,
        "reproduced_value_count": count,
        "missing_value_count": 3 - count,
        "entry_path_quality_available": available["entry"],
        "stop_pressure_available": available["stop"],
        "recovery_guard_available": available["recovery"],
        "can_apply_epq_threshold_test_only": available["entry"],
        "can_apply_sp_threshold_test_only": available["stop"],
        "can_apply_recovery_guard_test_only": available["recovery"],
        "can_continue_to_test_only_mask_cascade_counts": all(available.values()),
        "can_continue_to_full_6481_mask_cascade_counts": False,
        "reason_if_not": None if all(available.values()) else "one or more 973-row evaluator values were not fully reproduced",
    }


def build_test_only_cascade_readiness(
    summary: Mapping[str, Any], *, setup_quality_available: bool,
    regime_context_available: bool, production_labels_available: bool,
    test_predictions_available: bool,
) -> dict[str, Any]:
    checks = {
        "setup_quality": setup_quality_available,
        "regime_context": regime_context_available,
        "production_labels": production_labels_available,
        "test_predictions": test_predictions_available,
        "entry_path_quality": bool(summary.get("entry_path_quality_available")),
        "stop_pressure": bool(summary.get("stop_pressure_available")),
        "recovery_guard": bool(summary.get("recovery_guard_available")),
    }
    return {
        "denominator_scope": DENOMINATOR_SCOPE,
        **{f"{key}_available": value for key, value in checks.items()},
        "can_build_test_only_mask_cascade_counts": all(checks.values()),
        "can_build_full_6481_mask_cascade_counts": False,
        "remaining_blockers": [key for key, value in checks.items() if not value],
        "denominator_warning": "test-only 973 rows must not be treated as 6481 dataset rows",
    }


def build_full_dataset_guardrail(
    *, full_dataset_feature_rows: int = 6481, full_dataset_prediction_rows_found: int = 0,
    test_prediction_rows_found: int = 973, test_only_ready: bool = False,
) -> dict[str, Any]:
    return {
        "full_dataset_feature_rows": full_dataset_feature_rows,
        "full_dataset_prediction_rows_found": full_dataset_prediction_rows_found,
        "test_prediction_rows_found": test_prediction_rows_found,
        "full_dataset_cascade_allowed": False,
        "test_only_cascade_allowed_if_all_test_values_reproduced": bool(test_only_ready),
        "actual_label_substitution_allowed": False,
        "reason": [
            "only test denominator has prediction rows",
            "actual labels cannot be used as predicted labels",
            "full 6481 predicted_label stream missing",
        ],
        "decision": [
            "DO_NOT_BUILD_FULL_6481_CASCADE",
            "DO_NOT_SUBSTITUTE_ACTUAL_LABEL_FOR_PREDICTION",
        ],
    }


def classify_test_only_reproduction_decision(
    payload_source: Mapping[str, Any], join_board: Sequence[Mapping[str, Any]],
    reproduction_board: Sequence[Mapping[str, Any]], summary: Mapping[str, Any],
) -> list[str]:
    decisions = ["TEST_ONLY_REPRODUCTION_AUDIT_ADDED"]
    if payload_source.get("source_status") == "TEST_TIMESTAMPED_PREDICTIONS_SELECTED":
        decisions.append("TEST_PREDICTION_PAYLOAD_FOUND")
    if join_board and join_board[0].get("join_status") == "TEST_JOIN_READY":
        decisions.append("TEST_JOIN_READY")
    names = {
        "entry_path_quality_score_by_timestamp": "ENTRY_PATH_QUALITY_REPRODUCED_TEST_ONLY",
        "stop_pressure_risk_score_by_timestamp": "STOP_PRESSURE_REPRODUCED_TEST_ONLY",
        "recovery_guard_decision_by_timestamp": "RECOVERY_GUARD_REPRODUCED_TEST_ONLY",
    }
    for row in reproduction_board:
        if row.get("status") == "REPRODUCED_READ_ONLY_TEST_ONLY":
            decisions.append(names[str(row.get("value_name"))])
    ready = bool(summary.get("can_continue_to_test_only_mask_cascade_counts"))
    if not ready and any(int(row.get("reproduced_row_count") or 0) for row in reproduction_board):
        decisions.append("PARTIAL_TEST_ONLY_REPRODUCTION")
    decisions.append("TEST_ONLY_MASK_CASCADE_COUNTS_READY" if ready else "TEST_ONLY_MASK_CASCADE_COUNTS_NOT_READY")
    decisions.extend((
        "FULL_6481_CASCADE_NOT_ALLOWED",
        "NEEDS_FULL_DATASET_PREDICTION_PAYLOAD_CAPTURE",
        "DO_NOT_SUBSTITUTE_ACTUAL_LABEL_FOR_PREDICTION",
        "DO_NOT_CHANGE_LABELS_YET",
        "DO_NOT_CHANGE_GATES",
        "DO_NOT_RUN_TRAINING",
    ))
    return decisions


def build_read_only_test_only_evaluator_payload_reproduction_audit(
    *, probability_payload: Mapping[str, Any] | None = None,
    probability_payload_path: str | Path | None = None,
    feature_rows: Sequence[Any] | None = None, label_rows: Sequence[Any] | None = None,
    candidate_config: Mapping[str, Any] | None = None,
    source_counts: Mapping[str, Any] | None = None, symbol: str = "SOLUSDT",
    interval: str = "15m", start_date: str = "2026-04-01", end_date: str = "2026-06-15",
    reference_config_id: str = REFERENCE_CONFIG_ID,
    selected_feature_version: str = "fv3_candle_ta_context",
    selected_label_version: str = "lv31_h12_dates_exit45_long",
    selected_horizon_candles: int = 12,
) -> dict[str, Any]:
    payload = probability_payload
    if payload is None and probability_payload_path:
        payload = json.loads(Path(probability_payload_path).read_text(encoding="utf-8"))
    selection = select_test_prediction_payload(payload)
    predictions = list(selection.get("rows", []))
    source = build_test_prediction_payload_source(selection, probability_payload_path=probability_payload_path)
    joins = build_test_prediction_join_board(predictions, feature_rows, label_rows, symbol=symbol, interval=interval)
    joined = _joined_rows(predictions, feature_rows, label_rows, symbol=symbol, interval=interval)
    board = build_test_only_payload_reproduction_board(
        joined, candidate_config=candidate_config, expected_row_count=len(predictions) or 973
    )
    summary = build_test_only_reproduced_mask_summary(board)
    setup_available = bool(joined) and all(row.get("setup_quality_score") is not None for row in joined)
    regime_available = bool(joined) and all(
        row.get("market_regime") is not None or row.get("regime_context") is not None for row in joined
    )
    labels_available = bool(joined) and all(
        row.get("actual_label") is not None or row.get("direction_label") is not None for row in joined
    )
    readiness = build_test_only_cascade_readiness(
        summary, setup_quality_available=setup_available,
        regime_context_available=regime_available, production_labels_available=labels_available,
        test_predictions_available=source["source_status"] == "TEST_TIMESTAMPED_PREDICTIONS_SELECTED",
    )
    guardrail = build_full_dataset_guardrail(
        full_dataset_feature_rows=int((source_counts or {}).get("feature_row_count") or 6481),
        full_dataset_prediction_rows_found=int((source_counts or {}).get("dataset_prediction_rows_found") or 0),
        test_prediction_rows_found=len(predictions),
        test_only_ready=bool(readiness["can_build_test_only_mask_cascade_counts"]),
    )
    decision = classify_test_only_reproduction_decision(source, joins, board, summary)
    missing = sorted({item for row in board for item in row.get("missing_inputs", [])})
    return {
        "diagnostic_name": DIAGNOSTIC_NAME,
        "diagnostic_version": DIAGNOSTIC_VERSION,
        "execution_mode": EXECUTION_MODE,
        "symbol": symbol,
        "interval": interval,
        "date_range": f"{start_date} -> {end_date}",
        "reference_config_id": reference_config_id,
        "selected_feature_version": selected_feature_version,
        "selected_label_version": selected_label_version,
        "selected_horizon_candles": selected_horizon_candles,
        "denominator_scope": DENOMINATOR_SCOPE,
        "source_counts": dict(source_counts or {}),
        "test_prediction_payload_source": source,
        "test_prediction_join_board": joins,
        "test_only_payload_reproduction_board": board,
        "test_only_reproduced_mask_summary": summary,
        "test_only_cascade_readiness": readiness,
        "full_dataset_guardrail": guardrail,
        "next_step_plan": (
            ["build_test_only_mask_cascade_counts_on_973_denominator"]
            if readiness["can_build_test_only_mask_cascade_counts"]
            else [f"supply_missing_test_only_inputs: {', '.join(missing)}"]
        ) + ["capture_full_6481_predicted_label_stream_before_any_full_dataset_cascade"],
        "ml38_10_46_test_only_reproduction_decision": decision,
        "decision": decision,
        "database_writes": False,
        "ml_labels_writes": False,
        "training_or_runtime_execution": False,
    }
