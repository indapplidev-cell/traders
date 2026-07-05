from __future__ import annotations

from collections import Counter
from statistics import mean, median
from typing import Any, Mapping, Sequence

from app.diagnostics.test_only_mask_cascade_counts import (
    ENTRY_PATH_QUALITY_THRESHOLD,
    EXPECTED_TEST_ROWS,
    REFERENCE_CONFIG_ID,
    SETUP_QUALITY_THRESHOLD,
    STOP_PRESSURE_THRESHOLD,
    _decision_pass,
    _merge_reproduced_values,
    _value,
)
from app.diagnostics.test_only_evaluator_payload_reproduction import (
    _joined_rows,
    select_test_prediction_payload,
)


DIAGNOSTIC_NAME = "read_only_test_only_mask_outcome_audit"
DIAGNOSTIC_VERSION = "ml38.10.48"
EXECUTION_MODE = "READ_ONLY_TEST_ONLY_NO_TRAINING_NO_DB_WRITES"
DENOMINATOR_SCOPE = "TEST_ONLY_973_FINAL_PASS_42"
EXPECTED_FINAL_PASS_ROWS = 42
EXPECTED_FINAL_REMOVED_ROWS = 931
LABELS = ("UP", "DOWN", "FLAT")

_ACTUAL_FIELDS = ("actual_label", "direction_label", "target_label")
_PREDICTED_FIELDS = (
    "entry_path_original_predicted_label",
    "predicted_label",
    "predicted_class",
    "decision_label",
    "direction",
)
_CONFIDENCE_FIELDS = ("confidence",)
_PROBABILITY_FIELDS = {
    "prob_up": ("prob_up", "adjusted_prob_up"),
    "prob_down": ("prob_down", "adjusted_prob_down"),
    "prob_flat": ("prob_flat", "adjusted_prob_flat"),
}
_OUTCOME_R_FIELDS = ("outcome_r", "net_r", "realized_r", "profit_r")
_OUTCOME_STATUS_FIELDS = ("outcome_status", "result", "trade_result")
_RECOVERY_FIELDS = (
    "recovery_guard_eligible",
    "recovery_guard_pass",
    "recovery_guard_decision",
)


def _mapping(row: Any) -> dict[str, Any]:
    if isinstance(row, Mapping):
        return dict(row)
    return {
        key: value
        for key, value in getattr(row, "__dict__", {}).items()
        if not key.startswith("_")
    }


def _timestamp(row: Any) -> str:
    value = _value(row, ("candle_open_time", "open_time", "timestamp"))
    if hasattr(value, "isoformat"):
        value = value.isoformat()
    return str(value or "").replace("+00:00", "Z")


def _join_key(
    row: Any, *, symbol: str = "SOLUSDT", interval: str = "15m"
) -> tuple[str, str, str]:
    values = _mapping(row)
    return (
        str(values.get("symbol") or symbol).upper(),
        str(values.get("interval") or interval),
        _timestamp(row),
    )


def _duplicate_count(
    rows: Sequence[Any], *, symbol: str = "SOLUSDT", interval: str = "15m"
) -> int:
    keys = [
        _join_key(row, symbol=symbol, interval=interval)
        for row in rows
        if _timestamp(row)
    ]
    return sum(count - 1 for count in Counter(keys).values() if count > 1)


def _pct(count: int, denominator: int) -> float:
    return round(100.0 * count / denominator, 6) if denominator else 0.0


def _rate(count: int, denominator: int) -> float | None:
    return count / denominator if denominator else None


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _canonical_label(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().upper()
    aliases = {
        "0": "UP",
        "LONG": "UP",
        "BUY": "UP",
        "1": "DOWN",
        "SHORT": "DOWN",
        "SELL": "DOWN",
        "2": "FLAT",
        "NEUTRAL": "FLAT",
        "NO_TRADE": "FLAT",
        "NONE": "FLAT",
    }
    return aliases.get(normalized, normalized)


def _actual_label(row: Any) -> str | None:
    return _canonical_label(_value(row, _ACTUAL_FIELDS))


def _predicted_label(row: Any) -> str | None:
    # direction_label is deliberately absent: it is target/actual evidence only.
    return _canonical_label(_value(row, _PREDICTED_FIELDS))


def _quantile(values: Sequence[float], probability: float) -> float | None:
    ordered = sorted(values)
    if not ordered:
        return None
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def select_final_test_mask_pass_rows(
    test_rows: Sequence[Any] | None,
    *,
    setup_quality_threshold: float = SETUP_QUALITY_THRESHOLD,
    entry_path_quality_threshold: float = ENTRY_PATH_QUALITY_THRESHOLD,
    stop_pressure_threshold: float = STOP_PRESSURE_THRESHOLD,
) -> list[dict[str, Any]]:
    """Select the final test-only cascade rows without widening the denominator."""

    selected: list[dict[str, Any]] = []
    for source_row in test_rows or []:
        row = _mapping(source_row)
        setup = _number(_value(row, ("setup_quality_score",)))
        entry = _number(_value(row, ("entry_path_quality_score",)))
        stop = _number(_value(row, ("stop_pressure_risk_score",)))
        recovery = _value(row, _RECOVERY_FIELDS)
        if None in (setup, entry, stop) or recovery is None:
            continue
        try:
            passes = (
                setup >= setup_quality_threshold
                and entry >= entry_path_quality_threshold
                and stop <= stop_pressure_threshold
                and _decision_pass(recovery)
            )
        except (TypeError, ValueError):
            passes = False
        if passes:
            selected.append(row)
    return selected


def build_test_only_outcome_input_summary(
    final_pass_rows: Sequence[Any] | None,
    *,
    expected_final_pass_rows: int = EXPECTED_FINAL_PASS_ROWS,
    initial_test_rows: int = EXPECTED_TEST_ROWS,
    final_removed_rows: int = EXPECTED_FINAL_REMOVED_ROWS,
    symbol: str = "SOLUSDT",
    interval: str = "15m",
) -> dict[str, Any]:
    rows = list(final_pass_rows or [])
    keys = sum(bool(_timestamp(row)) for row in rows)
    predicted = sum(_predicted_label(row) is not None for row in rows)
    actual = sum(_actual_label(row) is not None for row in rows)
    probability = sum(
        _value(row, _CONFIDENCE_FIELDS) is not None
        or any(_value(row, fields) is not None for fields in _PROBABILITY_FIELDS.values())
        for row in rows
    )
    outcomes = sum(_value(row, _OUTCOME_R_FIELDS) is not None for row in rows)
    duplicates = _duplicate_count(rows, symbol=symbol, interval=interval)
    ready = (
        len(rows) == expected_final_pass_rows
        and keys == expected_final_pass_rows
        and predicted == expected_final_pass_rows
        and actual == expected_final_pass_rows
        and duplicates == 0
    )
    core_available = bool(rows) and bool(predicted or actual or keys)
    status = (
        "TEST_ONLY_OUTCOME_INPUTS_READY"
        if ready
        else "TEST_ONLY_OUTCOME_INPUTS_PARTIAL"
        if core_available
        else "TEST_ONLY_OUTCOME_INPUTS_BLOCKED"
    )
    missing: list[str] = []
    for name, count in (
        ("final_pass_rows", len(rows)),
        ("final_pass_keys", keys),
        ("predicted_labels", predicted),
        ("actual_labels", actual),
    ):
        if count != expected_final_pass_rows:
            missing.append(name)
    if duplicates:
        missing.append("duplicate_join_keys")
    return {
        "denominator_scope": DENOMINATOR_SCOPE,
        "initial_test_rows": initial_test_rows,
        "final_pass_rows": len(rows),
        "final_removed_rows": final_removed_rows,
        "final_pass_keys_available": keys,
        "predicted_label_rows_available": predicted,
        "actual_label_rows_available": actual,
        "probability_rows_available": probability,
        "profit_outcome_rows_available": outcomes,
        "join_key": "symbol+interval+candle_open_time",
        "duplicate_key_counts": {"final_pass_rows": duplicates},
        "missing_inputs": missing,
        "input_status": status,
    }


def build_final_pass_label_prediction_distribution(
    final_pass_rows: Sequence[Any] | None,
) -> dict[str, Any]:
    rows = list(final_pass_rows or [])
    actual = [label for row in rows if (label := _actual_label(row)) is not None]
    predicted = [label for row in rows if (label := _predicted_label(row)) is not None]
    actual_directional = sum(label in {"UP", "DOWN"} for label in actual)
    actual_flat = sum(label == "FLAT" for label in actual)
    predicted_directional = sum(label in {"UP", "DOWN"} for label in predicted)
    predicted_flat = sum(label == "FLAT" for label in predicted)
    return {
        "final_pass_rows": len(rows),
        "actual_label_distribution": dict(sorted(Counter(actual).items())),
        "predicted_label_distribution": dict(sorted(Counter(predicted).items())),
        "actual_directional_count": actual_directional,
        "actual_flat_count": actual_flat,
        "predicted_directional_count": predicted_directional,
        "predicted_flat_count": predicted_flat,
        "actual_directional_pct": _pct(actual_directional, len(actual)),
        "actual_flat_pct": _pct(actual_flat, len(actual)),
        "predicted_directional_pct": _pct(predicted_directional, len(predicted)),
        "predicted_flat_pct": _pct(predicted_flat, len(predicted)),
        "denominator_scope": DENOMINATOR_SCOPE,
    }


def build_final_pass_confusion_matrix(
    final_pass_rows: Sequence[Any] | None,
) -> dict[str, Any]:
    matrix = {predicted: {actual: 0 for actual in LABELS} for predicted in LABELS}
    paired = 0
    for row in final_pass_rows or []:
        predicted = _predicted_label(row)
        actual = _actual_label(row)
        if predicted in matrix and actual in matrix[predicted]:
            matrix[predicted][actual] += 1
            paired += 1
    up_up = matrix["UP"]["UP"]
    up_down = matrix["UP"]["DOWN"]
    up_flat = matrix["UP"]["FLAT"]
    down_down = matrix["DOWN"]["DOWN"]
    down_up = matrix["DOWN"]["UP"]
    down_flat = matrix["DOWN"]["FLAT"]
    directional_predictions = sum(matrix[side][actual] for side in ("UP", "DOWN") for actual in LABELS)
    hits = up_up + down_down
    hard_misses = up_down + down_up
    leakage = up_flat + down_flat
    return {
        "labels": list(LABELS),
        "matrix": matrix,
        "matrix_orientation": "predicted_vs_actual",
        "paired_rows": paired,
        "correct_directional_predictions": hits,
        "wrong_directional_predictions": hard_misses,
        "predicted_up_actual_up": up_up,
        "predicted_up_actual_down": up_down,
        "predicted_up_actual_flat": up_flat,
        "predicted_down_actual_down": down_down,
        "predicted_down_actual_up": down_up,
        "predicted_down_actual_flat": down_flat,
        "flat_leakage_count": leakage,
        "flat_leakage_pct": _pct(leakage, directional_predictions),
        "directional_hit_rate": _rate(hits, directional_predictions),
        "directional_miss_rate": _rate(hard_misses, directional_predictions),
        "denominator_scope": DENOMINATOR_SCOPE,
    }


def build_final_pass_directional_precision_board(
    final_pass_rows: Sequence[Any] | None,
) -> list[dict[str, Any]]:
    rows = list(final_pass_rows or [])
    board: list[dict[str, Any]] = []
    for side_name, sides in (
        ("predicted_UP", ("UP",)),
        ("predicted_DOWN", ("DOWN",)),
        ("all_predicted_directional", ("UP", "DOWN")),
    ):
        selected = [row for row in rows if _predicted_label(row) in sides]
        same = sum(_actual_label(row) == _predicted_label(row) for row in selected)
        opposite = sum(
            _actual_label(row) in {"UP", "DOWN"}
            and _actual_label(row) != _predicted_label(row)
            for row in selected
        )
        flat = sum(_actual_label(row) == "FLAT" for row in selected)
        count = len(selected)
        board.append(
            {
                "predicted_side": side_name,
                "predicted_count": count,
                "actual_same_side_count": same,
                "actual_opposite_side_count": opposite,
                "actual_flat_count": flat,
                "precision_same_side": _rate(same, count),
                "opposite_side_rate": _rate(opposite, count),
                "flat_rate": _rate(flat, count),
                "denominator_scope": DENOMINATOR_SCOPE,
                "small_sample_warning": count < 100,
            }
        )
    return board


def _confidence_bucket(row: Any) -> str | None:
    predicted = _predicted_label(row)
    actual = _actual_label(row)
    if predicted not in {"UP", "DOWN"} or actual not in LABELS:
        return None
    if actual == "FLAT":
        return "flat_leakage"
    return "directional_hit" if predicted == actual else "hard_wrong_direction"


def build_final_pass_probability_confidence_summary(
    final_pass_rows: Sequence[Any] | None,
) -> dict[str, Any]:
    rows = list(final_pass_rows or [])
    confidence = [
        value
        for row in rows
        if (value := _number(_value(row, _CONFIDENCE_FIELDS))) is not None
    ]
    probabilities = {
        name: [
            value
            for row in rows
            if (value := _number(_value(row, fields))) is not None
        ]
        for name, fields in _PROBABILITY_FIELDS.items()
    }
    missing = [
        name
        for name, values in (("confidence", confidence), *probabilities.items())
        if not values
    ]
    if len(missing) == 4:
        return {
            "status": "PROBABILITY_FIELDS_MISSING",
            "missing_fields": missing,
            "confidence_count": 0,
            "denominator_scope": DENOMINATOR_SCOPE,
        }
    by_bucket: dict[str, dict[str, Any]] = {}
    for bucket in ("directional_hit", "hard_wrong_direction", "flat_leakage"):
        values = [
            value
            for row in rows
            if _confidence_bucket(row) == bucket
            and (value := _number(_value(row, _CONFIDENCE_FIELDS))) is not None
        ]
        by_bucket[bucket] = {
            "count": len(values),
            "confidence_mean": mean(values) if values else None,
            "confidence_median": median(values) if values else None,
        }
    return {
        "status": "PROBABILITY_FIELDS_AVAILABLE" if not missing else "PROBABILITY_FIELDS_PARTIAL",
        "missing_fields": missing,
        "confidence_count": len(confidence),
        "confidence_min": min(confidence) if confidence else None,
        "confidence_max": max(confidence) if confidence else None,
        "confidence_mean": mean(confidence) if confidence else None,
        "confidence_median": median(confidence) if confidence else None,
        "confidence_p25": _quantile(confidence, 0.25),
        "confidence_p75": _quantile(confidence, 0.75),
        "prob_up_mean": mean(probabilities["prob_up"]) if probabilities["prob_up"] else None,
        "prob_down_mean": mean(probabilities["prob_down"]) if probabilities["prob_down"] else None,
        "prob_flat_mean": mean(probabilities["prob_flat"]) if probabilities["prob_flat"] else None,
        "confidence_by_hit_miss": by_bucket,
        "denominator_scope": DENOMINATOR_SCOPE,
    }


def build_final_pass_profit_outcome_summary(
    final_pass_rows: Sequence[Any] | None,
) -> dict[str, Any]:
    rows = list(final_pass_rows or [])
    values: list[float] = []
    fields_used: list[str] = []
    for row in rows:
        mapped = _mapping(row)
        for field in _OUTCOME_R_FIELDS:
            if (value := _number(mapped.get(field))) is not None:
                values.append(value)
                fields_used.append(field)
                break
    unique_fields = list(dict.fromkeys(fields_used))
    if not values:
        return {
            "outcome_source_status": "PROFIT_OUTCOME_MISSING",
            "outcome_fields_used": [],
            "row_count": 0,
            "total_r": None,
            "expectancy_r": None,
            "avg_r": None,
            "median_r": None,
            "win_count": None,
            "loss_count": None,
            "neutral_count": None,
            "win_rate": None,
            "profit_factor": None,
            "gross_profit_r": None,
            "gross_loss_r": None,
            "max_win_r": None,
            "max_loss_r": None,
            "outcome_r_distribution": None,
            "notes": ["No explicit row-level outcome_r/net_r field was found; R metrics were not inferred."],
        }
    wins = [value for value in values if value > 0]
    losses = [value for value in values if value < 0]
    neutral = [value for value in values if value == 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    status = "PROFIT_OUTCOME_AVAILABLE" if len(values) == len(rows) else "PROFIT_OUTCOME_PARTIAL"
    return {
        "outcome_source_status": status,
        "outcome_fields_used": unique_fields,
        "row_count": len(values),
        "total_r": sum(values),
        "expectancy_r": mean(values),
        "avg_r": mean(values),
        "median_r": median(values),
        "win_count": len(wins),
        "loss_count": len(losses),
        "neutral_count": len(neutral),
        "win_rate": len(wins) / len(values),
        "profit_factor": (
            gross_profit / gross_loss
            if gross_loss > 0
            else float("inf")
            if gross_profit > 0
            else 0.0
        ),
        "gross_profit_r": gross_profit,
        "gross_loss_r": gross_loss,
        "max_win_r": max(wins) if wins else None,
        "max_loss_r": min(losses) if losses else None,
        "outcome_r_distribution": {
            "positive": len(wins),
            "negative": len(losses),
            "neutral": len(neutral),
        },
        "notes": [
            "Metrics use only explicit row-level R outcomes from existing read-only payloads.",
            "Partial coverage must not be treated as a complete profit audit."
            if status == "PROFIT_OUTCOME_PARTIAL"
            else "All supplied final-pass rows contained an explicit R outcome.",
        ],
    }


def build_final_pass_sample_rows(
    final_pass_rows: Sequence[Any] | None, *, limit: int = 10
) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for row in list(final_pass_rows or [])[: max(0, min(limit, 10))]:
        sample = {
            "candle_open_time": _timestamp(row),
            "predicted_label": _predicted_label(row),
            "actual_label": _actual_label(row),
            "confidence": _number(_value(row, _CONFIDENCE_FIELDS)),
            "prob_up": _number(_value(row, _PROBABILITY_FIELDS["prob_up"])),
            "prob_down": _number(_value(row, _PROBABILITY_FIELDS["prob_down"])),
            "prob_flat": _number(_value(row, _PROBABILITY_FIELDS["prob_flat"])),
            "setup_quality_score": _number(_value(row, ("setup_quality_score",))),
            "entry_path_quality_score": _number(_value(row, ("entry_path_quality_score",))),
            "stop_pressure_risk_score": _number(_value(row, ("stop_pressure_risk_score",))),
            "recovery_guard_decision": _value(row, _RECOVERY_FIELDS),
        }
        outcome = _number(_value(row, _OUTCOME_R_FIELDS))
        status = _value(row, _OUTCOME_STATUS_FIELDS)
        if outcome is not None:
            sample["outcome_r"] = outcome
        if status is not None:
            sample["outcome_status"] = status
        samples.append(sample)
    return samples


def build_test_only_outcome_interpretation(
    *, sample_size: int = EXPECTED_FINAL_PASS_ROWS
) -> dict[str, Any]:
    return {
        "denominator_scope": DENOMINATOR_SCOPE,
        "sample_size": sample_size,
        "sample_size_warning": sample_size < 100,
        "production_like_recompute": False,
        "production_ready_edge": False,
        "can_infer_tradable_edge": False,
        "reason": [
            "test-only denominator",
            "small sample",
            "full dataset prediction stream missing",
            "no production-like recompute",
            "outcome audit is diagnostic only",
        ],
        "what_this_can_answer": [
            "label and prediction composition of the final test-only mask-pass rows",
            "test-only confusion, directional precision, and FLAT leakage",
            "available confidence and explicit row-level R outcome summaries",
        ],
        "what_this_cannot_answer": [
            "full-dataset mask or outcome behavior",
            "production-ready or tradable edge",
            "live activation suitability",
        ],
    }


def build_full_dataset_guardrail(
    *,
    full_dataset_feature_rows: int = 6481,
    full_dataset_prediction_rows_found: int = 0,
    test_prediction_rows_found: int = EXPECTED_TEST_ROWS,
    final_test_pass_rows: int = EXPECTED_FINAL_PASS_ROWS,
) -> dict[str, Any]:
    return {
        "full_dataset_feature_rows": full_dataset_feature_rows,
        "full_dataset_prediction_rows_found": full_dataset_prediction_rows_found,
        "test_prediction_rows_found": test_prediction_rows_found,
        "final_test_pass_rows": final_test_pass_rows,
        "full_dataset_outcome_audit_allowed": False,
        "full_dataset_cascade_allowed": False,
        "actual_label_substitution_allowed": False,
        "production_like_recompute": False,
        "production_ready_edge": False,
        "decision": [
            "DO_NOT_BUILD_FULL_6481_CASCADE",
            "DO_NOT_TREAT_TEST_ONLY_OUTCOME_AS_FULL_DATASET",
            "DO_NOT_TREAT_TEST_ONLY_OUTCOME_AS_TRADABLE_EDGE",
            "DO_NOT_SUBSTITUTE_ACTUAL_LABEL_FOR_PREDICTION",
        ],
    }


def classify_test_only_outcome_decision(
    input_summary: Mapping[str, Any],
    confusion_matrix: Mapping[str, Any],
    probability_summary: Mapping[str, Any],
    profit_summary: Mapping[str, Any],
    guardrail: Mapping[str, Any] | None = None,
) -> list[str]:
    decisions = ["TEST_ONLY_OUTCOME_AUDIT_ADDED"]
    ready = input_summary.get("input_status") == "TEST_ONLY_OUTCOME_INPUTS_READY"
    if ready:
        decisions.append("TEST_ONLY_OUTCOME_INPUTS_READY")
    if int(confusion_matrix.get("paired_rows") or 0) > 0:
        decisions.extend(
            ("TEST_ONLY_CONFUSION_MATRIX_COMPUTED", "TEST_ONLY_DIRECTIONAL_PRECISION_COMPUTED")
        )
    if probability_summary.get("status") != "PROBABILITY_FIELDS_MISSING":
        decisions.append("TEST_ONLY_PROBABILITY_SUMMARY_COMPUTED")
    outcome_status = profit_summary.get("outcome_source_status")
    decisions.append(
        "TEST_ONLY_PROFIT_OUTCOME_MISSING"
        if outcome_status == "PROFIT_OUTCOME_MISSING"
        else "TEST_ONLY_PROFIT_OUTCOME_AVAILABLE"
    )
    if ready and int(confusion_matrix.get("paired_rows") or 0) == int(
        input_summary.get("final_pass_rows") or 0
    ):
        decisions.append("TEST_ONLY_OUTCOME_DIAGNOSTIC_COMPLETE")
    decisions.extend(
        (
            "DO_NOT_TREAT_TEST_ONLY_OUTCOME_AS_FULL_DATASET",
            "DO_NOT_TREAT_TEST_ONLY_OUTCOME_AS_TRADABLE_EDGE",
            "FULL_6481_CASCADE_NOT_ALLOWED",
            "DO_NOT_SUBSTITUTE_ACTUAL_LABEL_FOR_PREDICTION",
            "DO_NOT_CHANGE_LABELS_YET",
            "DO_NOT_CHANGE_GATES",
            "DO_NOT_RUN_TRAINING",
        )
    )
    if not guardrail or int(guardrail.get("full_dataset_prediction_rows_found") or 0) == 0:
        decisions.append("NEEDS_FULL_DATASET_PREDICTION_PAYLOAD_CAPTURE")
    return list(dict.fromkeys(decisions))


def build_read_only_test_only_mask_outcome_audit(
    final_pass_rows: Sequence[Any] | None = None,
    *,
    test_rows: Sequence[Any] | None = None,
    probability_payload: Mapping[str, Any] | None = None,
    feature_rows: Sequence[Any] | None = None,
    label_rows: Sequence[Any] | None = None,
    candidate_config: Mapping[str, Any] | None = None,
    source_counts: Mapping[str, Any] | None = None,
    symbol: str = "SOLUSDT",
    interval: str = "15m",
    start_date: str = "2026-04-01",
    end_date: str = "2026-06-15",
    reference_config_id: str = REFERENCE_CONFIG_ID,
    selected_feature_version: str = "fv3_candle_ta_context",
    selected_label_version: str = "lv31_h12_dates_exit45_long",
    selected_horizon_candles: int = 12,
) -> dict[str, Any]:
    rows = list(final_pass_rows or [])
    if not rows and test_rows is None and probability_payload is not None:
        selection = select_test_prediction_payload(probability_payload)
        predictions = list(selection.get("rows", []))
        joined = _joined_rows(
            predictions, feature_rows, label_rows, symbol=symbol, interval=interval
        )
        test_rows = _merge_reproduced_values(
            joined, candidate_config, symbol=symbol, interval=interval
        )
    if not rows and test_rows is not None:
        rows = select_final_test_mask_pass_rows(test_rows)
    counts = {
        "full_dataset_feature_rows": 6481,
        "full_dataset_prediction_rows_found": 0,
        "test_prediction_rows_found": EXPECTED_TEST_ROWS,
        "initial_test_rows": EXPECTED_TEST_ROWS,
        "final_pass_rows": len(rows),
        "final_removed_rows": EXPECTED_TEST_ROWS - len(rows),
    }
    counts.update(dict(source_counts or {}))
    input_summary = build_test_only_outcome_input_summary(
        rows,
        initial_test_rows=int(counts.get("initial_test_rows") or EXPECTED_TEST_ROWS),
        final_removed_rows=int(counts.get("final_removed_rows") or 0),
        symbol=symbol,
        interval=interval,
    )
    distribution = build_final_pass_label_prediction_distribution(rows)
    confusion = build_final_pass_confusion_matrix(rows)
    precision = build_final_pass_directional_precision_board(rows)
    probability = build_final_pass_probability_confidence_summary(rows)
    profit = build_final_pass_profit_outcome_summary(rows)
    interpretation = build_test_only_outcome_interpretation(sample_size=len(rows))
    guardrail = build_full_dataset_guardrail(
        full_dataset_feature_rows=int(counts.get("full_dataset_feature_rows") or 6481),
        full_dataset_prediction_rows_found=int(counts.get("full_dataset_prediction_rows_found") or 0),
        test_prediction_rows_found=int(counts.get("test_prediction_rows_found") or EXPECTED_TEST_ROWS),
        final_test_pass_rows=len(rows),
    )
    decisions = classify_test_only_outcome_decision(
        input_summary, confusion, probability, profit, guardrail
    )
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
        "source_counts": counts,
        "test_only_outcome_input_summary": input_summary,
        "final_pass_label_prediction_distribution": distribution,
        "final_pass_confusion_matrix": confusion,
        "final_pass_directional_precision_board": precision,
        "final_pass_probability_confidence_summary": probability,
        "final_pass_profit_outcome_summary": profit,
        "final_pass_sample_rows": build_final_pass_sample_rows(rows),
        "test_only_outcome_interpretation": interpretation,
        "full_dataset_guardrail": guardrail,
        "next_step_plan": [
            "design full-dataset prediction payload capture",
            "design compact-profile prediction/outcome whitelist export",
            "consider a read-only test-only threshold sensitivity audit",
        ],
        "ml38_10_48_test_only_outcome_decision": decisions,
        "decision": decisions,
        "database_writes": False,
        "ml_labels_writes": False,
        "training_or_runtime_execution": False,
    }
