from __future__ import annotations

from collections import Counter
from typing import Any, Callable, Mapping, Sequence

from app.diagnostics.evaluator_payload_reproduction import (
    reproduce_entry_path_quality_score_read_only,
    reproduce_recovery_guard_decision_read_only,
    reproduce_stop_pressure_risk_score_read_only,
)
from app.diagnostics.test_only_evaluator_payload_reproduction import (
    _joined_rows,
    select_test_prediction_payload,
)


DIAGNOSTIC_NAME = "read_only_test_only_mask_cascade_counts_audit"
DIAGNOSTIC_VERSION = "ml38.10.47"
EXECUTION_MODE = "READ_ONLY_TEST_ONLY_NO_TRAINING_NO_DB_WRITES"
DENOMINATOR_SCOPE = "TEST_ONLY_973"
REFERENCE_CONFIG_ID = (
    "lv31_h12_tts_thr065_sqmask060_epq070_sp045_"
    "rguard_long_bad_dates_exit45_probe"
)
EXPECTED_TEST_ROWS = 973
SETUP_QUALITY_THRESHOLD = 0.60
ENTRY_PATH_QUALITY_THRESHOLD = 0.71
STOP_PRESSURE_THRESHOLD = 0.45

_ACTUAL_FIELDS = ("actual_label", "direction_label", "target_label")
_PREDICTED_FIELDS = (
    "entry_path_original_predicted_label",
    "predicted_label",
    "predicted_class",
    "decision_label",
)
_REGIME_CONTEXT_FIELDS = ("regime_context", "market_regime", "regime")
_REGIME_ELIGIBILITY_FIELDS = ("regime_context_eligible", "regime_eligible", "regime_context_pass")
_RECOVERY_FIELDS = ("recovery_guard_eligible", "recovery_guard_pass", "recovery_guard_decision")


def _mapping(row: Any) -> dict[str, Any]:
    if isinstance(row, Mapping):
        return dict(row)
    return {
        key: value
        for key, value in getattr(row, "__dict__", {}).items()
        if not key.startswith("_")
    }


def _value(row: Any, fields: Sequence[str]) -> Any:
    values = _mapping(row)
    for field in fields:
        if field in values and values[field] is not None:
            return values[field]
    return None


def _timestamp(row: Any) -> str:
    value = _value(row, ("candle_open_time", "open_time", "timestamp"))
    if hasattr(value, "isoformat"):
        value = value.isoformat()
    return str(value or "").replace("+00:00", "Z")


def _join_key(row: Any, *, symbol: str = "SOLUSDT", interval: str = "15m") -> tuple[str, str, str]:
    values = _mapping(row)
    return (
        str(values.get("symbol") or symbol).upper(),
        str(values.get("interval") or interval),
        _timestamp(row),
    )


def _duplicate_count(rows: Sequence[Any], *, symbol: str, interval: str) -> int:
    keys = [_join_key(row, symbol=symbol, interval=interval) for row in rows]
    return sum(count - 1 for key, count in Counter(keys).items() if key[-1] and count > 1)


def _available_count(rows: Sequence[Any], fields: Sequence[str]) -> int:
    return sum(_value(row, fields) is not None for row in rows)


def _pct(count: int, denominator: int) -> float:
    return round(100.0 * count / denominator, 6) if denominator else 0.0


def _decision_pass(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value or "").strip().upper()
    if normalized in {"PASS", "PASSED", "ALLOW", "ALLOWED", "ELIGIBLE", "READY", "TRUE", "1"}:
        return True
    if normalized in {"FAIL", "FAILED", "BLOCK", "BLOCKED", "INELIGIBLE", "FALSE", "0"}:
        return False
    raise ValueError(f"Unsupported decision value: {value!r}")


def build_test_only_mask_input_summary(
    test_rows: Sequence[Any] | None,
    *,
    expected_test_rows: int = EXPECTED_TEST_ROWS,
    symbol: str = "SOLUSDT",
    interval: str = "15m",
) -> dict[str, Any]:
    rows = list(test_rows or [])
    counts = {
        "setup_quality_rows_available": _available_count(rows, ("setup_quality_score",)),
        "regime_context_rows_available": _available_count(
            rows, (*_REGIME_CONTEXT_FIELDS, *_REGIME_ELIGIBILITY_FIELDS)
        ),
        "production_label_rows_available": _available_count(rows, _ACTUAL_FIELDS),
        "predicted_label_rows_available": _available_count(rows, _PREDICTED_FIELDS),
        "entry_path_quality_rows_available": _available_count(rows, ("entry_path_quality_score",)),
        "stop_pressure_rows_available": _available_count(rows, ("stop_pressure_risk_score",)),
        "recovery_guard_rows_available": _available_count(rows, _RECOVERY_FIELDS),
    }
    duplicates = _duplicate_count(rows, symbol=symbol, interval=interval)
    complete = (
        len(rows) == expected_test_rows
        and all(value == expected_test_rows for value in counts.values())
        and duplicates == 0
    )
    any_available = bool(rows) and any(counts.values())
    status = (
        "TEST_ONLY_MASK_INPUTS_READY"
        if complete
        else "TEST_ONLY_MASK_INPUTS_PARTIAL"
        if any_available
        else "TEST_ONLY_MASK_INPUTS_BLOCKED"
    )
    missing = [name for name, value in counts.items() if value != expected_test_rows]
    if len(rows) != expected_test_rows:
        missing.insert(0, "test_rows")
    if duplicates:
        missing.append("duplicate_join_keys")
    return {
        "denominator_scope": DENOMINATOR_SCOPE,
        "test_rows": len(rows),
        **counts,
        "duplicate_key_counts": {"test_rows": duplicates},
        "join_key": "symbol+interval+candle_open_time",
        "input_status": status,
        "missing_inputs": list(dict.fromkeys(missing)),
    }


def _cascade_row(
    *, step_name: str, input_rows: int | None, passed_rows: int | None,
    initial_rows: int, threshold: Any, rule: str, status: str, evidence: str,
) -> dict[str, Any]:
    removed = input_rows - passed_rows if input_rows is not None and passed_rows is not None else None
    return {
        "step_name": step_name,
        "denominator_scope": DENOMINATOR_SCOPE,
        "input_rows": input_rows,
        "passed_rows": passed_rows,
        "removed_rows": removed,
        "cumulative_remaining_rows": passed_rows,
        "removed_pct_of_initial": None if removed is None else _pct(removed, initial_rows),
        "passed_pct_of_initial": None if passed_rows is None else _pct(passed_rows, initial_rows),
        "threshold": threshold,
        "rule": rule,
        "status": status,
        "evidence": evidence,
    }


def build_test_only_mask_cascade_board(
    test_rows: Sequence[Any] | None,
    *, setup_quality_threshold: float = SETUP_QUALITY_THRESHOLD,
    entry_path_quality_threshold: float = ENTRY_PATH_QUALITY_THRESHOLD,
    stop_pressure_threshold: float = STOP_PRESSURE_THRESHOLD,
) -> list[dict[str, Any]]:
    rows = list(test_rows or [])
    initial = len(rows)
    board = [_cascade_row(
        step_name="initial_test_rows", input_rows=initial, passed_rows=initial,
        initial_rows=initial, threshold=None, rule="TEST_ONLY denominator rows",
        status="CASCADE_STEP_READY" if rows else "CASCADE_STEP_BLOCKED",
        evidence="ML38.10.46 timestamp join; denominator is never promoted beyond TEST_ONLY_973",
    )]
    active: list[Any] | None = rows if rows else None
    steps: list[tuple[str, Sequence[str], Any, str, Callable[[Any], bool], str]] = [
        (
            "setup_quality_mask", ("setup_quality_score",), setup_quality_threshold,
            f"setup_quality_score >= {setup_quality_threshold:.2f}",
            lambda value: float(value) >= setup_quality_threshold,
            "TrainingMetrics.apply_setup_quality_decision_mask uses a strict-below-threshold block",
        ),
        (
            "entry_path_quality_mask", ("entry_path_quality_score",), entry_path_quality_threshold,
            f"entry_path_quality_score >= {entry_path_quality_threshold:.2f}",
            lambda value: float(value) >= entry_path_quality_threshold,
            "TrainingMetrics.apply_entry_path_quality_decision_mask applies entry quality before the combined result",
        ),
        (
            "stop_pressure_mask", ("stop_pressure_risk_score",), stop_pressure_threshold,
            f"stop_pressure_risk_score <= {stop_pressure_threshold:.2f}",
            lambda value: float(value) <= stop_pressure_threshold,
            "TrainingMetrics.apply_entry_path_quality_decision_mask blocks stop pressure strictly above threshold",
        ),
    ]
    if rows and any(_value(row, _REGIME_ELIGIBILITY_FIELDS) is not None for row in rows):
        steps.append((
            "regime_context_mask", _REGIME_ELIGIBILITY_FIELDS, "decision-based",
            "explicit regime eligibility decision passes", _decision_pass,
            "Optional explicit regime eligibility is applied before recovery guard",
        ))
    steps.append((
        "recovery_guard_mask", _RECOVERY_FIELDS, "boolean/decision-based",
        "recovery guard eligibility/decision passes", _decision_pass,
        "build_mask_cascade_count_board applies recovery_guard_eligible/decision as a boolean predicate",
    ))

    for step_name, fields, threshold, rule, predicate, evidence in steps:
        before = len(active) if active is not None else None
        status = "CASCADE_STEP_BLOCKED"
        passed: int | None = None
        if active is not None:
            values = [_value(row, fields) for row in active]
            available = sum(value is not None for value in values)
            if available == len(active):
                try:
                    active = [row for row, value in zip(active, values) if predicate(value)]
                    passed = len(active)
                    status = "CASCADE_STEP_READY"
                except (TypeError, ValueError):
                    active = None
            elif available:
                status = "CASCADE_STEP_PARTIAL"
                active = None
            else:
                active = None
        board.append(_cascade_row(
            step_name=step_name, input_rows=before, passed_rows=passed,
            initial_rows=initial, threshold=threshold, rule=rule, status=status, evidence=evidence,
        ))

    final = len(active) if active is not None else None
    board.append(_cascade_row(
        step_name="final_test_mask_pass_rows", input_rows=initial, passed_rows=final,
        initial_rows=initial, threshold=None, rule="all applicable test-only masks pass",
        status="CASCADE_STEP_READY" if final is not None else "CASCADE_STEP_BLOCKED",
        evidence="cumulative result of the ordered diagnostic cascade; no full-dataset rows included",
    ))
    return board


def build_test_only_mask_removed_breakdown(
    cascade_board: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    by_name = {str(row.get("step_name")): row for row in cascade_board}
    def removed(name: str) -> int | None:
        value = by_name.get(name, {}).get("removed_rows")
        return None if value is None else int(value)
    values = {
        "removed_by_setup_quality_only": removed("setup_quality_mask"),
        "removed_by_entry_path_quality_after_setup": removed("entry_path_quality_mask"),
        "removed_by_stop_pressure_after_entry": removed("stop_pressure_mask"),
        "removed_by_recovery_guard_after_stop": removed("recovery_guard_mask"),
    }
    regime_removed = removed("regime_context_mask") if "regime_context_mask" in by_name else 0
    numeric = [value for value in values.values() if value is not None]
    final = by_name.get("final_test_mask_pass_rows", {}).get("passed_rows")
    initial = by_name.get("initial_test_rows", {}).get("passed_rows")
    complete = len(numeric) == len(values) and regime_removed is not None and final is not None
    return {
        **values,
        "removed_by_regime_context_after_stop": regime_removed,
        "total_removed": sum(numeric) + int(regime_removed or 0) if complete else None,
        "final_remaining": None if final is None else int(final),
        "no_double_counting": bool(
            complete and int(initial or 0) == sum(numeric) + int(regime_removed or 0) + int(final)
        ),
        "denominator_scope": DENOMINATOR_SCOPE,
    }


def _normalized_label(value: Any) -> str:
    return str(value).strip().upper()


def _distribution(rows: Sequence[Any]) -> dict[str, Any]:
    actual = [_normalized_label(value) for row in rows if (value := _value(row, _ACTUAL_FIELDS)) is not None]
    predicted = [_normalized_label(value) for row in rows if (value := _value(row, _PREDICTED_FIELDS)) is not None]
    directional_names = {"UP", "DOWN", "LONG", "SHORT", "0", "1"}
    flat_names = {"FLAT", "NO_TRADE", "NEUTRAL", "2"}
    directional_actual = sum(value in directional_names for value in actual)
    flat_actual = sum(value in flat_names for value in actual)
    directional_predicted = sum(value in directional_names for value in predicted)
    flat_predicted = sum(value in flat_names for value in predicted)
    count = len(rows)
    return {
        "row_count": count,
        "actual_label_distribution": dict(sorted(Counter(actual).items())),
        "predicted_label_distribution": dict(sorted(Counter(predicted).items())),
        "directional_actual_count": directional_actual,
        "flat_actual_count": flat_actual,
        "directional_predicted_count": directional_predicted,
        "flat_predicted_count": flat_predicted,
        "directional_actual_pct": _pct(directional_actual, len(actual)),
        "flat_actual_pct": _pct(flat_actual, len(actual)),
        "directional_predicted_pct": _pct(directional_predicted, len(predicted)),
        "flat_predicted_pct": _pct(flat_predicted, len(predicted)),
        "warning_if_denominator_small": "DENOMINATOR_LT_30" if count < 30 else None,
    }


def build_test_only_distribution_before_after(
    test_rows: Sequence[Any] | None,
    cascade_board: Sequence[Mapping[str, Any]] | None = None,
    *, setup_quality_threshold: float = SETUP_QUALITY_THRESHOLD,
    entry_path_quality_threshold: float = ENTRY_PATH_QUALITY_THRESHOLD,
    stop_pressure_threshold: float = STOP_PRESSURE_THRESHOLD,
) -> dict[str, Any]:
    rows = list(test_rows or [])
    result = {"initial_test_rows": _distribution(rows)}
    active: list[Any] | None = rows
    steps: list[tuple[str, Sequence[str], Callable[[Any], bool]]] = [
        ("after_setup_quality_mask", ("setup_quality_score",), lambda value: float(value) >= setup_quality_threshold),
        ("after_entry_path_quality_mask", ("entry_path_quality_score",), lambda value: float(value) >= entry_path_quality_threshold),
        ("after_stop_pressure_mask", ("stop_pressure_risk_score",), lambda value: float(value) <= stop_pressure_threshold),
    ]
    if rows and any(_value(row, _REGIME_ELIGIBILITY_FIELDS) is not None for row in rows):
        steps.append(("after_regime_context_mask", _REGIME_ELIGIBILITY_FIELDS, _decision_pass))
    steps.append(("after_recovery_guard_mask", _RECOVERY_FIELDS, _decision_pass))
    for name, fields, predicate in steps:
        if active is None:
            result[name] = None
            continue
        values = [_value(row, fields) for row in active]
        if any(value is None for value in values):
            active = None
            result[name] = None
            continue
        try:
            active = [row for row, value in zip(active, values) if predicate(value)]
            result[name] = _distribution(active)
        except (TypeError, ValueError):
            active = None
            result[name] = None
    return result


def build_test_only_final_mask_summary(
    cascade_board: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    rows = list(cascade_board)
    by_name = {str(row.get("step_name")): row for row in rows}
    initial = int(by_name.get("initial_test_rows", {}).get("passed_rows") or 0)
    final_value = by_name.get("final_test_mask_pass_rows", {}).get("passed_rows")
    final = None if final_value is None else int(final_value)
    mask_rows = [row for row in rows if str(row.get("step_name", "")).endswith("_mask")]
    ready = bool(mask_rows) and all(row.get("status") == "CASCADE_STEP_READY" for row in mask_rows)
    selective = [row for row in mask_rows if row.get("removed_rows") is not None]
    most = max(selective, key=lambda row: int(row.get("removed_rows") or 0))["step_name"] if selective else None
    removed = None if final is None else initial - final
    return {
        "denominator_scope": DENOMINATOR_SCOPE,
        "initial_rows": initial,
        "final_pass_rows": final,
        "final_removed_rows": removed,
        "final_pass_pct": None if final is None else _pct(final, initial),
        "final_removed_pct": None if removed is None else _pct(removed, initial),
        "most_selective_mask": most,
        "masks_applied": [row.get("step_name") for row in mask_rows if row.get("status") == "CASCADE_STEP_READY"],
        "all_masks_ready": ready,
        "can_continue_to_test_only_outcome_audit": bool(ready and final is not None),
        "can_continue_to_full_6481_mask_cascade_counts": False,
        "reason_if_not": None if ready and final is not None else "one or more test-only mask inputs/steps are incomplete",
    }


def build_full_dataset_guardrail(
    *, test_only_cascade_computed: bool = False,
    full_dataset_feature_rows: int = 6481,
    full_dataset_prediction_rows_found: int = 0,
    test_prediction_rows_found: int = EXPECTED_TEST_ROWS,
) -> dict[str, Any]:
    return {
        "full_dataset_feature_rows": full_dataset_feature_rows,
        "full_dataset_prediction_rows_found": full_dataset_prediction_rows_found,
        "test_prediction_rows_found": test_prediction_rows_found,
        "test_only_cascade_computed": bool(test_only_cascade_computed),
        "full_dataset_cascade_allowed": False,
        "actual_label_substitution_allowed": False,
        "reason": [
            "only test denominator has prediction rows",
            "actual labels cannot be used as predicted labels",
            "full 6481 predicted_label stream missing",
            "test-only cascade counts must not be promoted to production-like recompute",
        ],
        "decision": [
            "DO_NOT_BUILD_FULL_6481_CASCADE",
            "DO_NOT_SUBSTITUTE_ACTUAL_LABEL_FOR_PREDICTION",
            "DO_NOT_TREAT_TEST_ONLY_COUNTS_AS_FULL_DATASET",
        ],
    }


def classify_test_only_mask_cascade_decision(
    input_summary: Mapping[str, Any], final_summary: Mapping[str, Any],
) -> list[str]:
    ready = input_summary.get("input_status") == "TEST_ONLY_MASK_INPUTS_READY"
    computed = bool(ready and final_summary.get("all_masks_ready"))
    decisions = ["TEST_ONLY_MASK_CASCADE_AUDIT_ADDED"]
    if ready:
        decisions.append("TEST_ONLY_MASK_INPUTS_READY")
    if computed:
        decisions.extend((
            "TEST_ONLY_MASK_CASCADE_COUNTS_COMPUTED",
            "TEST_ONLY_FINAL_MASK_PASS_ROWS_AVAILABLE",
            "TEST_ONLY_OUTCOME_AUDIT_READY",
        ))
    else:
        decisions.append("TEST_ONLY_MASK_CASCADE_BLOCKED")
    decisions.extend((
        "FULL_6481_CASCADE_NOT_ALLOWED",
        "NEEDS_FULL_DATASET_PREDICTION_PAYLOAD_CAPTURE",
        "DO_NOT_TREAT_TEST_ONLY_COUNTS_AS_FULL_DATASET",
        "DO_NOT_SUBSTITUTE_ACTUAL_LABEL_FOR_PREDICTION",
        "DO_NOT_CHANGE_LABELS_YET",
        "DO_NOT_CHANGE_GATES",
        "DO_NOT_RUN_TRAINING",
    ))
    return decisions


def _merge_reproduced_values(
    rows: Sequence[Any], candidate_config: Mapping[str, Any] | None,
    *, symbol: str, interval: str,
) -> list[dict[str, Any]]:
    merged = [_mapping(row) for row in rows]
    results = (
        ("entry_path_quality_score", reproduce_entry_path_quality_score_read_only(rows, candidate_config=candidate_config)),
        ("stop_pressure_risk_score", reproduce_stop_pressure_risk_score_read_only(rows, candidate_config=candidate_config)),
        ("recovery_guard_decision", reproduce_recovery_guard_decision_read_only(rows, candidate_config=candidate_config)),
    )
    indexes = []
    for field, result in results:
        indexes.append((field, {
            _join_key(row, symbol=symbol, interval=interval): _mapping(row).get(field)
            for row in result.get("rows", [])
        }))
    for row in merged:
        key = _join_key(row, symbol=symbol, interval=interval)
        for field, index in indexes:
            if field not in row and key in index:
                row[field] = index[key]
    return merged


def build_read_only_test_only_mask_cascade_counts_audit(
    test_rows: Sequence[Any] | None = None,
    *, probability_payload: Mapping[str, Any] | None = None,
    feature_rows: Sequence[Any] | None = None,
    label_rows: Sequence[Any] | None = None,
    candidate_config: Mapping[str, Any] | None = None,
    source_counts: Mapping[str, Any] | None = None,
    symbol: str = "SOLUSDT", interval: str = "15m",
    start_date: str = "2026-04-01", end_date: str = "2026-06-15",
    reference_config_id: str = REFERENCE_CONFIG_ID,
    selected_feature_version: str = "fv3_candle_ta_context",
    selected_label_version: str = "lv31_h12_dates_exit45_long",
    selected_horizon_candles: int = 12,
) -> dict[str, Any]:
    rows = list(test_rows or [])
    if not rows and probability_payload is not None:
        selection = select_test_prediction_payload(probability_payload)
        predictions = list(selection.get("rows", []))
        rows = _joined_rows(
            predictions, feature_rows, label_rows, symbol=symbol, interval=interval
        )
        rows = _merge_reproduced_values(
            rows, candidate_config, symbol=symbol, interval=interval
        )
    input_summary = build_test_only_mask_input_summary(
        rows, symbol=symbol, interval=interval
    )
    board = build_test_only_mask_cascade_board(rows)
    removed = build_test_only_mask_removed_breakdown(board)
    distributions = build_test_only_distribution_before_after(rows, board)
    final = build_test_only_final_mask_summary(board)
    decisions = classify_test_only_mask_cascade_decision(input_summary, final)
    computed = "TEST_ONLY_MASK_CASCADE_COUNTS_COMPUTED" in decisions
    counts = {
        "full_dataset_feature_rows": 6481,
        "full_dataset_prediction_rows_found": 0,
        "test_prediction_rows_found": len(rows),
    }
    counts.update(dict(source_counts or {}))
    guardrail = build_full_dataset_guardrail(
        test_only_cascade_computed=computed,
        full_dataset_feature_rows=int(counts.get("full_dataset_feature_rows") or 6481),
        full_dataset_prediction_rows_found=int(counts.get("full_dataset_prediction_rows_found") or 0),
        test_prediction_rows_found=int(counts.get("test_prediction_rows_found") or len(rows)),
    )
    next_steps = (
        ["ML38.10.48 read-only test-only mask outcome audit"]
        if computed else
        [f"supply missing test-only inputs: {', '.join(input_summary.get('missing_inputs', []))}"]
    )
    next_steps.append("capture full 6481 predicted_label payload before any full-dataset cascade")
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
        "test_only_mask_input_summary": input_summary,
        "test_only_mask_cascade_board": board,
        "test_only_mask_removed_breakdown": removed,
        "test_only_distribution_before_after": distributions,
        "test_only_final_mask_summary": final,
        "full_dataset_guardrail": guardrail,
        "next_step_plan": next_steps,
        "ml38_10_47_test_only_mask_cascade_decision": decisions,
        "decision": decisions,
        "database_writes": False,
        "ml_labels_writes": False,
        "training_or_runtime_execution": False,
    }
