from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

from app.diagnostics.entry_path_quality_filter import EntryPathQualityFilter
from app.evaluation.profit_aware_evaluator_v2 import ProfitAwareEvaluatorV2


DIAGNOSTIC_NAME = "read_only_evaluator_payload_reproduction_audit"
DIAGNOSTIC_VERSION = "ml38.10.44"
EXECUTION_MODE = "READ_ONLY_NO_TRAINING_NO_DB_WRITES"
REFERENCE_CONFIG_ID = (
    "lv31_h12_tts_thr065_sqmask060_epq070_sp045_"
    "rguard_long_bad_dates_exit45_probe"
)

_IDENTITY_FIELDS = ("symbol", "interval", "candle_open_time")
_ENTRY_REQUIRED_FIELDS = (
    "features_json",
    "setup_quality_score",
    "setup_expected_move_atr",
    "setup_invalidation_distance_atr",
    "predicted_label",
)
_RECOVERY_REQUIRED_FIELDS = (
    "current_close",
    "atr_14",
    "future_candles",
    "predicted_label",
)


def _value(row: Any, key: str, default: Any = None) -> Any:
    if isinstance(row, Mapping):
        if key in row:
            return row[key]
        features = row.get("features_json")
    else:
        value = getattr(row, key, None)
        if value is not None:
            return value
        features = getattr(row, "features_json", None)
    return features.get(key, default) if isinstance(features, Mapping) else default


def _prediction_label(row: Any) -> str:
    for field in (
        "entry_path_original_predicted_label",
        "predicted_label",
        "signal_direction",
    ):
        value = _value(row, field)
        if value is not None and str(value).strip():
            label = str(value).upper()
            return {"LONG": "UP", "SHORT": "DOWN"}.get(label, label)
    return ""


def _identity(row: Any) -> dict[str, Any]:
    return {
        "symbol": _value(row, "symbol"),
        "interval": _value(row, "interval"),
        "candle_open_time": _value(
            row,
            "candle_open_time",
            _value(row, "open_time", _value(row, "timestamp")),
        ),
    }


def _join_key(row: Any) -> tuple[Any, Any, Any]:
    identity = _identity(row)
    return tuple(identity[field] for field in _IDENTITY_FIELDS)


def _duplicate_count(rows: Sequence[Mapping[str, Any]]) -> int:
    keys = [_join_key(row) for row in rows]
    usable = [key for key in keys if key[-1] is not None]
    return len(usable) - len(set(usable))


def _missing_entry_inputs(row: Any) -> list[str]:
    missing = []
    features = _value(row, "features_json")
    if not isinstance(features, Mapping):
        missing.append("features_json")
    for field in _ENTRY_REQUIRED_FIELDS[1:-1]:
        if _value(row, field) is None:
            missing.append(field)
    if not _prediction_label(row):
        missing.append("predicted_label")
    return missing


def _missing_recovery_inputs(row: Any) -> list[str]:
    missing = []
    for field in _RECOVERY_REQUIRED_FIELDS[:-1]:
        value = _value(row, field)
        if value is None or (field == "future_candles" and not isinstance(value, Sequence)):
            missing.append(field)
    if not _prediction_label(row):
        missing.append("predicted_label")
    return missing


def _reproduction_result(
    *,
    value_name: str,
    source: str,
    required_inputs: Sequence[str],
    input_rows: Sequence[Any],
    reproduced_rows: list[dict[str, Any]],
    missing_inputs_by_row: list[dict[str, Any]],
) -> dict[str, Any]:
    expected = len(input_rows)
    reproduced = len(reproduced_rows)
    status = (
        "REPRODUCED_READ_ONLY"
        if expected > 0 and reproduced == expected
        else "SOURCE_FOUND_INPUTS_MISSING"
    )
    return {
        "value_name": value_name,
        "source_module_or_function": source,
        "required_inputs": list(required_inputs),
        "rows": reproduced_rows,
        "missing_inputs_by_row": missing_inputs_by_row,
        "reproduction_attempted": True,
        "reproduced_row_count": reproduced,
        "expected_row_count": expected,
        "missing_row_count": max(0, expected - reproduced),
        "duplicate_row_count": _duplicate_count(reproduced_rows),
        "status": status,
        "requires_db_write": False,
        "requires_training": False,
        "requires_label_builder_change": False,
    }


def _reproduce_entry_path_payload_read_only(
    rows: Sequence[Any] | None,
    *,
    candidate_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    input_rows = list(rows or [])
    config = dict(candidate_config or {})
    valid_rows: list[Any] = []
    missing_inputs_by_row: list[dict[str, Any]] = []
    for index, row in enumerate(input_rows):
        missing = _missing_entry_inputs(row)
        if missing:
            missing_inputs_by_row.append(
                {"row_index": index, **_identity(row), "missing_inputs": missing}
            )
        else:
            valid_rows.append(row)

    feature_names = sorted(
        {
            str(name)
            for row in valid_rows
            for name in dict(_value(row, "features_json") or {}).keys()
        }
    )
    scored_rows: list[dict[str, Any]] = []
    if valid_rows:
        score_payload = EntryPathQualityFilter().score_rows(
            feature_names=feature_names,
            feature_rows=[
                [float(dict(_value(row, "features_json") or {}).get(name, 0.0) or 0.0) for name in feature_names]
                for row in valid_rows
            ],
            setup_quality_scores=[float(_value(row, "setup_quality_score")) for row in valid_rows],
            expected_move_atr=[float(_value(row, "setup_expected_move_atr")) for row in valid_rows],
            invalidation_distance_atr=[
                float(_value(row, "setup_invalidation_distance_atr")) for row in valid_rows
            ],
            predicted_labels=[_prediction_label(row) for row in valid_rows],
            score_profile=str(
                config.get("entry_path_quality_score_profile") or "mae_aware_rr_v3"
            ),
        )
        for row, score in zip(valid_rows, score_payload.get("score_rows", [])):
            scored_rows.append({**_identity(row), **dict(score)})

    return {
        "input_rows": input_rows,
        "scored_rows": scored_rows,
        "missing_inputs_by_row": missing_inputs_by_row,
    }


def reproduce_entry_path_quality_score_read_only(
    rows: Sequence[Any] | None,
    *,
    candidate_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _reproduce_entry_path_payload_read_only(rows, candidate_config=candidate_config)
    reproduced = [
        {**_identity(row), "entry_path_quality_score": row["entry_path_quality_score"]}
        for row in payload["scored_rows"]
    ]
    return _reproduction_result(
        value_name="entry_path_quality_score_by_timestamp",
        source="app.diagnostics.entry_path_quality_filter.EntryPathQualityFilter.score_rows",
        required_inputs=_ENTRY_REQUIRED_FIELDS,
        input_rows=payload["input_rows"],
        reproduced_rows=reproduced,
        missing_inputs_by_row=payload["missing_inputs_by_row"],
    )


def reproduce_stop_pressure_risk_score_read_only(
    rows: Sequence[Any] | None,
    *,
    candidate_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _reproduce_entry_path_payload_read_only(rows, candidate_config=candidate_config)
    reproduced = [
        {**_identity(row), "stop_pressure_risk_score": row["stop_pressure_risk_score"]}
        for row in payload["scored_rows"]
    ]
    return _reproduction_result(
        value_name="stop_pressure_risk_score_by_timestamp",
        source="app.diagnostics.entry_path_quality_filter.EntryPathQualityFilter.score_rows",
        required_inputs=_ENTRY_REQUIRED_FIELDS,
        input_rows=payload["input_rows"],
        reproduced_rows=reproduced,
        missing_inputs_by_row=payload["missing_inputs_by_row"],
    )


def reproduce_recovery_guard_decision_read_only(
    rows: Sequence[Any] | None,
    *,
    candidate_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    input_rows = list(rows or [])
    config = dict(candidate_config or {})
    required_config = (
        "take_profit_atr",
        "stop_loss_atr",
        "exit_mitigation_loss_r",
    )
    missing_config = [field for field in required_config if config.get(field) is None]
    reproduced: list[dict[str, Any]] = []
    missing_inputs_by_row: list[dict[str, Any]] = []
    evaluator = ProfitAwareEvaluatorV2()
    for index, row in enumerate(input_rows):
        missing = _missing_recovery_inputs(row) + [
            f"candidate_config.{field}" for field in missing_config
        ]
        if missing:
            missing_inputs_by_row.append(
                {"row_index": index, **_identity(row), "missing_inputs": missing}
            )
            continue
        label = _prediction_label(row)
        simulation_row = {
            "signal_direction": "LONG" if label == "UP" else "SHORT",
            "current_close": float(_value(row, "current_close")),
            "atr_14": float(_value(row, "atr_14")),
            "future_candles": list(_value(row, "future_candles")),
            "future_move_atr": float(_value(row, "future_move_atr", 0.0) or 0.0),
        }
        common = {
            "take_profit_atr": float(config["take_profit_atr"]),
            "stop_loss_atr": float(config["stop_loss_atr"]),
            "fee_r": float(config.get("fee_r", 0.0) or 0.0),
            "slippage_r": float(config.get("slippage_r", 0.0) or 0.0),
            "same_candle_policy": str(config.get("same_candle_policy") or "conservative"),
            "exit_timeout_bars": config.get("exit_timeout_bars"),
            "exit_mitigation_loss_r": float(config["exit_mitigation_loss_r"]),
            "exit_neutral_abs_r": config.get("exit_neutral_abs_r"),
        }
        classic = evaluator._simulate_trade(  # diagnostic adapter; production behavior is unchanged
            simulation_row, exit_policy_profile="stop_loss_mitigation_v1", **common
        )
        guarded = evaluator._simulate_trade(
            simulation_row,
            exit_policy_profile="stop_loss_mitigation_recovery_guard_v1",
            **common,
        )
        guard_applied = bool(
            classic.get("result") == "EXIT_MITIGATED"
            and str(classic.get("exit_mitigation_path_class") or "").startswith("PREMATURE")
            and guarded.get("result") != "EXIT_MITIGATED"
        )
        reproduced.append(
            {
                **_identity(row),
                "recovery_guard_decision": guard_applied,
                "classic_result": classic.get("result"),
                "guarded_result": guarded.get("result"),
                "classic_exit_mitigation_path_class": classic.get(
                    "exit_mitigation_path_class"
                ),
            }
        )
    return _reproduction_result(
        value_name="recovery_guard_decision_by_timestamp",
        source="app.evaluation.profit_aware_evaluator_v2.ProfitAwareEvaluatorV2._simulate_trade",
        required_inputs=(*_RECOVERY_REQUIRED_FIELDS, *required_config),
        input_rows=input_rows,
        reproduced_rows=reproduced,
        missing_inputs_by_row=missing_inputs_by_row,
    )


def build_evaluator_payload_source_audit(
    *,
    payload_rows: Sequence[Any] | None = None,
    candidate_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    rows = list(payload_rows or [])
    config = dict(candidate_config or {})
    available = sorted(
        {
            key
            for row in rows
            for key in (
                set(row.keys()) | set(dict(row.get("features_json") or {}).keys())
                if isinstance(row, Mapping)
                else set()
            )
        }
        | set(config.keys())
    )
    missing = sorted(
        {
            item
            for row in rows
            for item in (_missing_entry_inputs(row) + _missing_recovery_inputs(row))
        }
    )
    if not rows:
        missing = sorted(set(_ENTRY_REQUIRED_FIELDS) | set(_RECOVERY_REQUIRED_FIELDS))
    return {
        "evaluator_module": "app/evaluation/profit_aware_evaluator_v2.py",
        "candidate_functions_or_classes": [
            "EntryPathQualityFilter.score_rows",
            "ProfitAwareEvaluatorV2._simulate_trade",
            "ProfitAwareEvaluatorV2._exit_mitigation_path_audit",
        ],
        "required_inputs": {
            "entry_path_quality_score": list(_ENTRY_REQUIRED_FIELDS),
            "stop_pressure_risk_score": list(_ENTRY_REQUIRED_FIELDS),
            "recovery_guard_decision": [
                *_RECOVERY_REQUIRED_FIELDS,
                "candidate_config.take_profit_atr",
                "candidate_config.stop_loss_atr",
                "candidate_config.exit_mitigation_loss_r",
            ],
        },
        "available_inputs_read_only": available,
        "missing_inputs": missing,
        "can_reproduce_entry_path_quality": bool(rows) and not any(
            _missing_entry_inputs(row) for row in rows
        ),
        "can_reproduce_stop_pressure": bool(rows) and not any(
            _missing_entry_inputs(row) for row in rows
        ),
        "can_reproduce_recovery_guard": bool(rows)
        and not any(_missing_recovery_inputs(row) for row in rows)
        and all(config.get(field) is not None for field in (
            "take_profit_atr", "stop_loss_atr", "exit_mitigation_loss_r"
        )),
        "requires_training": False,
        "requires_db_write": False,
        "requires_label_builder_change": False,
        "evidence": [
            "EntryPathQualityFilter.score_rows emits both entry_path_quality_score and stop_pressure_risk_score.",
            "ProfitAwareEvaluatorV2._simulate_trade applies recovery guard only for premature mitigation paths.",
            "MlLabels persists setup quality, expected move and invalidation distance; MlFeatures persists feature context.",
            "Directional mae_aware_rr_v3 scoring additionally requires the original predicted direction from evaluator/candidate payload.",
        ],
    }


def build_payload_reproduction_board(
    entry_path_result: Mapping[str, Any],
    stop_pressure_result: Mapping[str, Any],
    recovery_guard_result: Mapping[str, Any],
    *,
    candidate_config: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    config = dict(candidate_config or {})
    thresholds = {
        "entry_path_quality_score_by_timestamp": config.get(
            "entry_path_quality_min_threshold", 0.70
        ),
        "stop_pressure_risk_score_by_timestamp": config.get(
            "stop_pressure_max_risk_score", 0.45
        ),
        "recovery_guard_decision_by_timestamp": None,
    }
    board = []
    for result in (entry_path_result, stop_pressure_result, recovery_guard_result):
        row = {key: value for key, value in dict(result).items() if key != "rows"}
        row["available_inputs"] = sorted(
            set(row.get("required_inputs", []))
            - {
                item
                for missing in row.get("missing_inputs_by_row", [])
                for item in missing.get("missing_inputs", [])
            }
        )
        row["missing_inputs"] = sorted(
            {
                item
                for missing in row.get("missing_inputs_by_row", [])
                for item in missing.get("missing_inputs", [])
            }
        )
        row["threshold"] = thresholds.get(str(row.get("value_name")))
        row["evidence"] = row.get("source_module_or_function")
        board.append(row)
    return board


def build_timestamp_payload_join_board(
    *,
    base_feature_rows: Sequence[Any] | None,
    entry_path_result: Mapping[str, Any],
    stop_pressure_result: Mapping[str, Any],
    recovery_guard_result: Mapping[str, Any],
) -> list[dict[str, Any]]:
    base = list(base_feature_rows or [])
    result_rows = [
        list(result.get("rows", []))
        for result in (entry_path_result, stop_pressure_result, recovery_guard_result)
    ]
    base_keys = {_join_key(row) for row in base}
    joined = [len(base_keys & {_join_key(row) for row in rows}) for rows in result_rows]
    missing = [max(0, len(base_keys) - count) for count in joined]
    if base and all(count == len(base_keys) for count in joined):
        status = "PAYLOAD_JOIN_READY"
    elif any(joined):
        status = "PARTIAL_PAYLOAD_JOIN"
    else:
        status = "PAYLOAD_JOIN_BLOCKED"
    return [{
        "join_key": "symbol+interval+candle_open_time",
        "base_feature_rows": len(base),
        "joined_entry_path_rows": joined[0],
        "joined_stop_pressure_rows": joined[1],
        "joined_recovery_guard_rows": joined[2],
        "missing_entry_path_rows": missing[0],
        "missing_stop_pressure_rows": missing[1],
        "missing_recovery_guard_rows": missing[2],
        "duplicate_counts": {
            "base": _duplicate_count([_identity(row) for row in base]),
            "entry_path": _duplicate_count(result_rows[0]),
            "stop_pressure": _duplicate_count(result_rows[1]),
            "recovery_guard": _duplicate_count(result_rows[2]),
        },
        "join_status": status,
    }]


def build_reproduced_mask_value_summary(
    payload_reproduction_board: Sequence[Mapping[str, Any]],
    *,
    setup_quality_available: bool = True,
    regime_context_available: bool = True,
    production_labels_available: bool = True,
) -> dict[str, Any]:
    by_name = {str(row.get("value_name")): row for row in payload_reproduction_board}
    available = {
        "entry": by_name.get("entry_path_quality_score_by_timestamp", {}).get("status")
        == "REPRODUCED_READ_ONLY",
        "stop": by_name.get("stop_pressure_risk_score_by_timestamp", {}).get("status")
        == "REPRODUCED_READ_ONLY",
        "recovery": by_name.get("recovery_guard_decision_by_timestamp", {}).get("status")
        == "REPRODUCED_READ_ONLY",
    }
    reproduced_count = sum(bool(value) for value in available.values())
    cascade = bool(
        all(available.values())
        and setup_quality_available
        and regime_context_available
        and production_labels_available
    )
    missing_names = [name for name, value in available.items() if not value]
    return {
        "requested_value_count": 3,
        "reproduced_value_count": reproduced_count,
        "missing_value_count": 3 - reproduced_count,
        "entry_path_quality_available": available["entry"],
        "stop_pressure_available": available["stop"],
        "recovery_guard_available": available["recovery"],
        "can_apply_epq_threshold": available["entry"],
        "can_apply_sp_threshold": available["stop"],
        "can_apply_recovery_guard": available["recovery"],
        "can_continue_to_mask_cascade_counts": cascade,
        "reason_if_not": None if cascade else "Missing complete inputs/streams: " + ", ".join(missing_names),
    }


def build_cascade_readiness_after_reproduction(
    reproduced_mask_value_summary: Mapping[str, Any],
    *,
    setup_quality_available: bool = True,
    regime_context_available: bool = True,
    production_labels_available: bool = True,
) -> dict[str, Any]:
    summary = dict(reproduced_mask_value_summary)
    blockers = []
    checks = {
        "setup_quality": setup_quality_available,
        "regime_context": regime_context_available,
        "production_labels": production_labels_available,
        "entry_path_quality": bool(summary.get("entry_path_quality_available")),
        "stop_pressure": bool(summary.get("stop_pressure_available")),
        "recovery_guard": bool(summary.get("recovery_guard_available")),
    }
    blockers.extend(name for name, value in checks.items() if not value)
    ready = not blockers
    return {
        "setup_quality_available": setup_quality_available,
        "regime_context_available": regime_context_available,
        "production_labels_available": production_labels_available,
        "entry_path_quality_available": checks["entry_path_quality"],
        "stop_pressure_available": checks["stop_pressure"],
        "recovery_guard_available": checks["recovery_guard"],
        "can_build_mask_cascade_counts": ready,
        "can_build_production_like_recompute": ready,
        "remaining_blockers": blockers,
    }


def classify_evaluator_payload_reproduction_decision(
    reproduced_mask_value_summary: Mapping[str, Any],
) -> list[str]:
    summary = dict(reproduced_mask_value_summary)
    decisions = ["EVALUATOR_PAYLOAD_REPRODUCTION_ADDED"]
    flags = (
        ("entry_path_quality_available", "ENTRY_PATH_QUALITY_REPRODUCED"),
        ("stop_pressure_available", "STOP_PRESSURE_REPRODUCED"),
        ("recovery_guard_available", "RECOVERY_GUARD_REPRODUCED"),
    )
    decisions.extend(decision for field, decision in flags if summary.get(field))
    reproduced = int(summary.get("reproduced_value_count", 0) or 0)
    if 0 < reproduced < 3:
        decisions.append("PARTIAL_EVALUATOR_PAYLOAD_REPRODUCED")
    if reproduced < 3:
        decisions.append("EVALUATOR_INPUTS_MISSING")
    decisions.append(
        "CAN_PROCEED_TO_MASK_CASCADE_COUNTS"
        if summary.get("can_continue_to_mask_cascade_counts")
        else "CANNOT_PROCEED_TO_MASK_CASCADE_COUNTS"
    )
    if not summary.get("can_continue_to_mask_cascade_counts"):
        decisions.append("PRODUCTION_LIKE_RECOMPUTE_NOT_READY")
    decisions.extend(("DO_NOT_CHANGE_LABELS_YET", "DO_NOT_CHANGE_GATES", "DO_NOT_RUN_TRAINING"))
    return decisions


def build_read_only_evaluator_payload_reproduction_audit(
    *,
    payload_rows: Sequence[Any] | None = None,
    base_feature_rows: Sequence[Any] | None = None,
    candidate_config: Mapping[str, Any] | None = None,
    source_counts: Mapping[str, Any] | None = None,
    setup_quality_available: bool = True,
    regime_context_available: bool = True,
    production_labels_available: bool = True,
    symbol: str = "SOLUSDT",
    interval: str = "15m",
    start_date: str = "2026-04-01",
    end_date: str = "2026-06-15",
    reference_config_id: str = REFERENCE_CONFIG_ID,
    selected_feature_version: str = "fv3_candle_ta_context",
    selected_label_version: str = "lv31_h12_dates_exit45_long",
    selected_horizon_candles: int = 12,
) -> dict[str, Any]:
    rows = list(payload_rows or [])
    base = list(base_feature_rows) if base_feature_rows is not None else rows
    counts = {
        "candle_count": 7282,
        "feature_row_count": 6481,
        "ml_features_rows_extracted": 7282,
        "ml_labels_rows_extracted": 7257,
        "production_label_row_count": 7257,
    }
    counts.update(dict(source_counts or {}))
    entry = reproduce_entry_path_quality_score_read_only(rows, candidate_config=candidate_config)
    stop = reproduce_stop_pressure_risk_score_read_only(rows, candidate_config=candidate_config)
    recovery = reproduce_recovery_guard_decision_read_only(rows, candidate_config=candidate_config)
    board = build_payload_reproduction_board(entry, stop, recovery, candidate_config=candidate_config)
    summary = build_reproduced_mask_value_summary(
        board,
        setup_quality_available=setup_quality_available,
        regime_context_available=regime_context_available,
        production_labels_available=production_labels_available,
    )
    readiness = build_cascade_readiness_after_reproduction(
        summary,
        setup_quality_available=setup_quality_available,
        regime_context_available=regime_context_available,
        production_labels_available=production_labels_available,
    )
    decisions = classify_evaluator_payload_reproduction_decision(summary)
    blockers = sorted(
        {
            item
            for row in board
            for item in row.get("missing_inputs", [])
        }
    )
    next_steps = []
    if "features_json" in blockers:
        next_steps.append("map_ml_features.features_json_to_evaluator_feature_columns")
    if any(item.startswith("candidate_config.") for item in blockers):
        next_steps.append("map_reference_candidate_config_exit_parameters")
    if "predicted_label" in blockers:
        next_steps.append("extract_original_candidate_prediction_direction_by_timestamp")
    if "future_candles" in blockers:
        next_steps.append("build_read_only_future_candle_windows_by_timestamp")
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
        "source_counts": counts,
        "evaluator_payload_source_audit": build_evaluator_payload_source_audit(
            payload_rows=rows, candidate_config=candidate_config
        ),
        "payload_reproduction_board": board,
        "timestamp_payload_join_board": build_timestamp_payload_join_board(
            base_feature_rows=base,
            entry_path_result=entry,
            stop_pressure_result=stop,
            recovery_guard_result=recovery,
        ),
        "reproduced_mask_value_summary": summary,
        "cascade_readiness_after_reproduction": readiness,
        "reproduction_blockers": blockers,
        "next_step_plan": next_steps,
        "ml38_10_44_reproduction_decision": decisions,
        "decision": decisions,
        "database_writes": False,
        "ml_labels_writes": False,
        "training_or_runtime_execution": False,
    }
