from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence
from zipfile import ZipFile


DIAGNOSTIC_NAME = "read_only_predicted_label_payload_trace_audit"
DIAGNOSTIC_VERSION = "ml38.10.45"
EXECUTION_MODE = "READ_ONLY_NO_TRAINING_NO_DB_WRITES"
REFERENCE_CONFIG_ID = (
    "lv31_h12_tts_thr065_sqmask060_epq070_sp045_"
    "rguard_long_bad_dates_exit45_probe"
)

TIMESTAMP_FIELDS = ("candle_open_time", "open_time", "timestamp")
PREDICTED_LABEL_FIELDS = (
    "entry_path_original_predicted_label",
    "predicted_label",
    "predicted_class",
    "decision_label",
    "predicted_direction",
    "direction",
    "signal_direction",
    "raw_prediction",
    "calibrated_prediction",
)
PROBABILITY_FIELDS = (
    "prob_up",
    "prob_down",
    "prob_flat",
    "probability",
    "confidence",
)

_LOCATOR_SPECS = (
    ("selected_predictions", ("bounded_calibrated_decision_selection", "selected_predictions"), 973),
    ("calibrated_rows", ("calibrated_decision_diagnostics", "calibrated_rows"), 973),
    ("selected_rows", ("calibrated_decision_diagnostics", "selected_rows"), 973),
    ("entry_path_score_rows", ("entry_path_quality_filter_diagnostics", "score_rows"), 973),
    ("decision_policy_selected_predictions", ("decision_policy_grid_diagnostics", "selected_predictions"), 973),
    ("probability_selected_predictions", ("probability_diagnostics", "selected_predictions"), 973),
    ("profit_aware_signal_rows", ("profit_aware_diagnostics", "signal_rows"), 973),
    ("ml_predictions_db_rows", ("ml_predictions_db_rows",), 6481),
    ("uncompressed_full_candidate_result", ("uncompressed_full_candidate_result",), 973),
    ("compact_zip_candidate_result", ("compact_zip_candidate_result",), 973),
)

_IMPORTANT_OMISSION_PATHS = (
    "entry_path_quality_filter_diagnostics.score_rows",
    "bounded_calibrated_decision_selection.selected_predictions",
    "calibrated_decision_diagnostics.calibrated_rows",
    "calibrated_decision_diagnostics.selected_rows",
    "decision_policy_grid_diagnostics.selected_predictions",
    "probability_diagnostics.selected_predictions",
    "probability_diagnostics.calibrated_rows",
    "profit_aware_diagnostics.signal_rows",
)


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _at_path(payload: Mapping[str, Any], path: Sequence[str]) -> Any:
    value: Any = payload
    for key in path:
        if not isinstance(value, Mapping) or key not in value:
            return None
        value = value[key]
    return value


def _is_omission_marker(value: Any) -> bool:
    return isinstance(value, Mapping) and bool(
        value.get("omitted") is True or value.get("_compact_pruned") is True
    )


def _marker_count(value: Any) -> int:
    marker = _as_mapping(value)
    return int(marker.get("original_count") or marker.get("original_len") or 0)


def _iter_row_lists(value: Any, path: tuple[str, ...] = ()):
    if isinstance(value, list):
        if not value or all(isinstance(row, Mapping) for row in value):
            yield path, value
        for index, item in enumerate(value):
            if isinstance(item, (Mapping, list)):
                yield from _iter_row_lists(item, (*path, str(index)))
    elif isinstance(value, Mapping) and not _is_omission_marker(value):
        for key, item in value.items():
            if isinstance(item, (Mapping, list)):
                yield from _iter_row_lists(item, (*path, str(key)))


def _field_profile(rows: Sequence[Any]) -> dict[str, Any]:
    mapping_rows = [row for row in rows if isinstance(row, Mapping)]
    timestamp_fields = sorted(
        field for field in TIMESTAMP_FIELDS if any(row.get(field) is not None for row in mapping_rows)
    )
    predicted_fields = sorted(
        field
        for field in PREDICTED_LABEL_FIELDS
        if any(row.get(field) is not None for row in mapping_rows)
    )
    probability_fields = sorted(
        field for field in PROBABILITY_FIELDS if any(row.get(field) is not None for row in mapping_rows)
    )
    timestamped_prediction_rows = sum(
        any(row.get(field) is not None for field in TIMESTAMP_FIELDS)
        and any(row.get(field) is not None for field in PREDICTED_LABEL_FIELDS)
        for row in mapping_rows
    )
    return {
        "timestamp_fields": timestamp_fields,
        "predicted_label_fields": predicted_fields,
        "probability_fields": probability_fields,
        "timestamped_prediction_rows": timestamped_prediction_rows,
    }


def _best_rows(value: Any) -> tuple[list[Any], str]:
    if isinstance(value, list):
        return list(value), "root"
    candidates = list(_iter_row_lists(value))
    if not candidates:
        return [], ""
    path, rows = max(
        candidates,
        key=lambda item: (
            _field_profile(item[1])["timestamped_prediction_rows"],
            len(item[1]),
        ),
    )
    return list(rows), ".".join(path)


def _source_row(
    *,
    source_name: str,
    source_type: str,
    source_path_or_table: str,
    value: Any,
    searched: bool = True,
    exists: bool = True,
    access_error: str | None = None,
) -> dict[str, Any]:
    marker = _as_mapping(value) if _is_omission_marker(value) else {}
    rows, row_path = _best_rows(value)
    profile = _field_profile(rows)
    aggregate_predictions = bool(
        isinstance(value, list)
        and value
        and not any(isinstance(item, Mapping) for item in value)
    )
    if access_error:
        status = "READ_ONLY_ACCESS_ERROR"
    elif not exists:
        status = "SOURCE_NOT_FOUND"
    elif marker:
        status = "FOUND_OMITTED_BY_COMPACT_PROFILE"
    elif profile["timestamped_prediction_rows"]:
        status = "FOUND_TIMESTAMPED_PREDICTIONS"
    elif source_type == "database_table":
        status = "DB_TABLE_FOUND_NO_MATCHING_ROWS"
    elif rows or aggregate_predictions:
        status = "FOUND_AGGREGATE_ONLY"
    else:
        status = "SOURCE_EXISTS_NO_ROWS"
    return {
        "source_name": source_name,
        "source_type": source_type,
        "source_path_or_table": source_path_or_table,
        "searched": searched,
        "found": exists and not access_error,
        "contains_timestamp_key": bool(profile["timestamp_fields"]),
        "contains_predicted_label": bool(profile["predicted_label_fields"] or aggregate_predictions),
        "contains_probability_columns": bool(profile["probability_fields"]),
        "row_count": len(rows) or _marker_count(marker),
        "located_timestamped_prediction_rows": profile["timestamped_prediction_rows"],
        "omitted_by_compact_profile": bool(marker),
        "omission_reason": marker.get("reason"),
        "usable_for_reproduction": bool(profile["timestamped_prediction_rows"]),
        "status": status,
        "evidence": access_error or row_path or source_path_or_table,
        "requires_db_write": False,
        "requires_training": False,
        "requires_label_builder_change": False,
    }


def build_predicted_label_source_discovery_board(
    sources: Sequence[Mapping[str, Any]] | None = None,
    *,
    candidate_result: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    descriptors = list(sources or [])
    if candidate_result is not None:
        descriptors.append(
            {
                "source_name": "candidate_result_fields",
                "source_type": "candidate_payload",
                "source_path_or_table": "in_memory_candidate_result",
                "value": candidate_result,
                "exists": True,
            }
        )
        for path in _IMPORTANT_OMISSION_PATHS:
            value = _at_path(candidate_result, path.split("."))
            descriptors.append(
                {
                    "source_name": path,
                    "source_type": "candidate_payload_field",
                    "source_path_or_table": f"candidate_result.{path}",
                    "value": value,
                    "exists": value is not None or path.endswith("signal_rows"),
                }
            )
    canonical = [
            {
                "source_name": name,
                "source_type": source_type,
                "source_path_or_table": path,
                "value": None,
                "exists": source_type == "database_table",
            }
            for name, source_type, path in (
                ("full_uncompressed_candidate_result", "json", "reports/feature_regime_experiments/**/candidate_results/<candidate>.json"),
                ("compact_zip_candidate_result", "zip_json", "quick_quality_fv3_cached_fresh_tuning_solusdt_15m_*.zip!/candidate_results/<candidate>.json"),
                ("ml_predictions", "database_table", "ml_predictions"),
                ("training_evaluation_intermediate_caches", "filesystem_search", "reports/**|cache/**|temp/**|label_grid_runtime/**"),
            )
        ]
    existing_names = {str(item.get("source_name")) for item in descriptors}
    descriptors = [
        item for item in canonical if item["source_name"] not in existing_names
    ] + descriptors
    return [
        _source_row(
            source_name=str(item.get("source_name") or "unknown"),
            source_type=str(item.get("source_type") or "unknown"),
            source_path_or_table=str(item.get("source_path_or_table") or ""),
            value=item.get("value", item.get("rows")),
            searched=bool(item.get("searched", True)),
            exists=bool(item.get("exists", True)),
            access_error=item.get("access_error"),
        )
        for item in descriptors
    ]


def _collect_omissions(value: Any, path: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if _is_omission_marker(value):
        marker = _as_mapping(value)
        found.append(
            {
                "path": ".".join(path),
                "omitted": True,
                "original_count": _marker_count(marker),
                "original_type": marker.get("original_type"),
                "reason": marker.get("reason"),
            }
        )
    elif isinstance(value, Mapping):
        for key, item in value.items():
            found.extend(_collect_omissions(item, (*path, str(key))))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_collect_omissions(item, (*path, str(index))))
    return found


def build_candidate_payload_omission_audit(
    candidate_result: Mapping[str, Any] | None,
    *,
    recovery_sources: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    omissions = _collect_omissions(candidate_result or {})
    recoverable = any(
        row.get("usable_for_reproduction")
        for row in build_predicted_label_source_discovery_board(recovery_sources)
    )
    by_path = {row["path"]: row for row in omissions}
    important = []
    for path in _IMPORTANT_OMISSION_PATHS:
        matches = [row for key, row in by_path.items() if key.endswith(path)]
        if matches:
            row = dict(matches[0])
        else:
            value = _at_path(candidate_result or {}, path.split("."))
            row = {
                "path": path,
                "omitted": _is_omission_marker(value),
                "original_count": _marker_count(value),
                "original_type": _as_mapping(value).get("original_type"),
                "reason": _as_mapping(value).get("reason"),
                "value_is_null": value is None and path.endswith("signal_rows"),
            }
        row["recoverable_from_non_compact_artifact"] = recoverable
        row["is_missing_predicted_label_source"] = any(
            token in path for token in ("selected_predictions", "calibrated_rows", "selected_rows", "score_rows", "signal_rows")
        )
        important.append(row)
    return {
        "omitted_paths": omissions,
        "important_payload_paths": important,
        "omitted_path_count": len(omissions),
        "prediction_rows_recoverable_from_another_non_compact_artifact": recoverable,
    }


def _locator_row(payload_name: str, expected: int, value: Any) -> dict[str, Any]:
    marker = _as_mapping(value) if _is_omission_marker(value) else {}
    rows, row_path = _best_rows(value)
    profile = _field_profile(rows)
    aggregate_labels = bool(rows and not any(isinstance(row, Mapping) for row in rows))
    located = len(rows) or _marker_count(marker)
    if marker:
        status = "FOUND_OMITTED_BY_COMPACT_PROFILE"
    elif profile["timestamped_prediction_rows"]:
        status = "FOUND_TIMESTAMPED_PREDICTIONS"
    elif rows or aggregate_labels:
        status = "FOUND_AGGREGATE_ONLY"
    else:
        status = "SOURCE_NOT_FOUND"
    return {
        "payload_name": payload_name,
        "expected_row_count": expected,
        "located_row_count": located,
        "located_timestamped_prediction_rows": profile["timestamped_prediction_rows"],
        "timestamp_field_candidates": profile["timestamp_fields"],
        "predicted_label_field_candidates": profile["predicted_label_fields"],
        "probability_field_candidates": profile["probability_fields"],
        "has_required_join_key": bool(profile["timestamp_fields"]),
        "has_predicted_label": bool(profile["predicted_label_fields"] or aggregate_labels),
        "can_join_to_6481_feature_rows": profile["timestamped_prediction_rows"] >= 6481,
        "can_join_to_973_test_rows": profile["timestamped_prediction_rows"] >= 973,
        "status": status,
        "evidence": row_path or marker.get("reason"),
    }


def build_prediction_row_locator_board(
    candidate_result: Mapping[str, Any] | None = None,
    *,
    ml_predictions_db_rows: Sequence[Any] | None = None,
    uncompressed_full_candidate_result: Any = None,
    compact_zip_candidate_result: Any = None,
) -> list[dict[str, Any]]:
    payload = candidate_result or {}
    values: dict[str, Any] = {
        name: _at_path(payload, path) for name, path, _ in _LOCATOR_SPECS[:7]
    }
    values.update(
        {
            "ml_predictions_db_rows": list(ml_predictions_db_rows or []),
            "uncompressed_full_candidate_result": uncompressed_full_candidate_result,
            "compact_zip_candidate_result": compact_zip_candidate_result,
        }
    )
    return [
        _locator_row(name, expected, values.get(name))
        for name, _, expected in _LOCATOR_SPECS
    ]


def build_timestamp_prediction_join_readiness(
    prediction_row_locator_board: Sequence[Mapping[str, Any]],
    *,
    base_feature_rows: int = 6481,
    test_prediction_rows_expected: int = 973,
    dataset_prediction_rows_expected: int = 6481,
) -> dict[str, Any]:
    rows = list(prediction_row_locator_board)
    located = max(
        (int(row.get("located_timestamped_prediction_rows") or 0) for row in rows),
        default=0,
    )
    any_label = any(row.get("has_predicted_label") for row in rows)
    any_timestamp = any(row.get("has_required_join_key") for row in rows)
    if located >= dataset_prediction_rows_expected:
        status = "DATASET_PREDICTION_JOIN_READY"
    elif located >= test_prediction_rows_expected:
        status = "PARTIAL_TEST_ONLY_JOIN_READY"
    elif not any_label:
        status = "JOIN_BLOCKED_NO_PREDICTED_LABEL_ROWS"
    elif not any_timestamp:
        status = "JOIN_BLOCKED_NO_TIMESTAMP"
    else:
        status = "JOIN_BLOCKED_DENOMINATOR_MISMATCH"
    return {
        "preferred_join_key": "symbol+interval+candle_open_time",
        "base_feature_rows": base_feature_rows,
        "test_prediction_rows_expected": test_prediction_rows_expected,
        "dataset_prediction_rows_expected": dataset_prediction_rows_expected,
        "located_timestamped_prediction_rows": located,
        "can_join_test_predictions": located >= test_prediction_rows_expected,
        "can_join_dataset_predictions": located >= dataset_prediction_rows_expected,
        "missing_join_fields": [] if any_timestamp else list(TIMESTAMP_FIELDS),
        "duplicate_risk": "UNKNOWN_REQUIRES_KEY_UNIQUENESS_CHECK" if located else "NOT_APPLICABLE",
        "denominator_warning": (
            "973 test prediction rows must not be treated as 6481 dataset-compatible rows"
            if test_prediction_rows_expected <= located < dataset_prediction_rows_expected
            else None
        ),
        "join_status": status,
    }


def build_actual_vs_predicted_guardrail() -> dict[str, Any]:
    return {
        "actual_label_field": "ml_labels.direction_label",
        "predicted_label_field_candidates": list(PREDICTED_LABEL_FIELDS),
        "substitution_allowed": False,
        "reason": "actual labels cannot be used as evaluator predicted direction",
        "violation_if_substituted": [
            "target_leakage",
            "invalid_entry_path_quality",
            "invalid_stop_pressure",
            "invalid_recovery_guard",
            "invalid_mask_cascade_counts",
        ],
        "safe_fallback": None,
        "decision": "DO_NOT_SUBSTITUTE_ACTUAL_LABEL_FOR_PREDICTION",
    }


def _trace_blockers(
    board: Sequence[Mapping[str, Any]],
    readiness: Mapping[str, Any],
    discovery: Sequence[Mapping[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    statuses = {str(row.get("status")) for row in board}
    if "FOUND_OMITTED_BY_COMPACT_PROFILE" in statuses:
        blockers.append("compact_profile_omitted_prediction_rows")
    full_sources = [
        row for row in discovery
        if row.get("source_name") == "full_uncompressed_candidate_result"
    ]
    if full_sources and not any(row.get("found") for row in full_sources):
        blockers.append("full_candidate_result_not_found")
    db_sources = [
        row for row in discovery if row.get("source_type") == "database_table"
    ]
    if db_sources and all(
        row.get("status") == "DB_TABLE_FOUND_NO_MATCHING_ROWS" for row in db_sources
    ):
        blockers.append("ml_predictions_no_matching_rows")
    if readiness.get("join_status") != "DATASET_PREDICTION_JOIN_READY":
        blockers.append("dataset_denominator_6481_missing")
    if readiness.get("join_status") == "PARTIAL_TEST_ONLY_JOIN_READY":
        blockers.append("only_test_denominator_973_available")
    if not readiness.get("located_timestamped_prediction_rows"):
        blockers.append("predicted_label_field_missing")
        blockers.append("timestamp_field_missing")
        blockers.append("runtime_payload_required")
    blockers.append("no_safe_actual_label_substitution")
    return blockers


def classify_predicted_label_trace_decision(
    timestamp_prediction_join_readiness: Mapping[str, Any],
    *,
    source_discovery_board: Sequence[Mapping[str, Any]] | None = None,
) -> list[str]:
    status = timestamp_prediction_join_readiness.get("join_status")
    source_statuses = {str(row.get("status")) for row in (source_discovery_board or [])}
    decisions = ["PREDICTED_LABEL_TRACE_AUDIT_ADDED"]
    if "FOUND_OMITTED_BY_COMPACT_PROFILE" in source_statuses:
        decisions.append("PREDICTION_ROWS_OMITTED_BY_COMPACT_PROFILE")
        decisions.append("NEEDS_COMPACT_PROFILE_PREDICTION_PAYLOAD_WHITELIST")
    full_sources = [
        row for row in (source_discovery_board or [])
        if row.get("source_name") == "full_uncompressed_candidate_result"
    ]
    if full_sources and not any(row.get("found") for row in full_sources):
        decisions.append("FULL_CANDIDATE_RESULT_NOT_FOUND")
    db_sources = [
        row for row in (source_discovery_board or [])
        if row.get("source_type") == "database_table"
    ]
    if db_sources:
        decisions.append("ML_PREDICTIONS_TABLE_AVAILABLE")
        if all(row.get("status") == "DB_TABLE_FOUND_NO_MATCHING_ROWS" for row in db_sources):
            decisions.append("ML_PREDICTIONS_NO_MATCHING_ROWS")
    if timestamp_prediction_join_readiness.get("located_timestamped_prediction_rows"):
        decisions.append("TIMESTAMPED_PREDICTIONS_FOUND")
    if status == "DATASET_PREDICTION_JOIN_READY":
        decisions.append("DATASET_PREDICTIONS_FOUND")
    elif status == "PARTIAL_TEST_ONLY_JOIN_READY":
        decisions.append("TEST_ONLY_PREDICTIONS_FOUND")
    decisions.append(
        "CAN_PROCEED_TO_EVALUATOR_PAYLOAD_REPRODUCTION"
        if timestamp_prediction_join_readiness.get("located_timestamped_prediction_rows")
        else "CANNOT_PROCEED_TO_EVALUATOR_PAYLOAD_REPRODUCTION"
    )
    if status != "DATASET_PREDICTION_JOIN_READY":
        decisions.append("CANNOT_PROCEED_TO_MASK_CASCADE_COUNTS")
    if not timestamp_prediction_join_readiness.get("located_timestamped_prediction_rows"):
        decisions.append("NEEDS_NON_COMPACT_PREDICTION_PAYLOAD_CAPTURE")
    decisions.extend(
        (
            "DO_NOT_SUBSTITUTE_ACTUAL_LABEL_FOR_PREDICTION",
            "DO_NOT_CHANGE_LABELS_YET",
            "DO_NOT_CHANGE_GATES",
            "DO_NOT_RUN_TRAINING",
        )
    )
    return decisions


def build_next_reproduction_plan(
    timestamp_prediction_join_readiness: Mapping[str, Any],
) -> list[str]:
    status = timestamp_prediction_join_readiness.get("join_status")
    if status == "DATASET_PREDICTION_JOIN_READY":
        return ["rerun_ml38_10_44_reproduction_with_located_dataset_predicted_labels"]
    if status == "PARTIAL_TEST_ONLY_JOIN_READY":
        return [
            "rerun_ml38_10_44_reproduction_with_located_test_predicted_labels_on_973_denominator",
            "keep_full_6481_mask_cascade_blocked_until_dataset_predictions_are_located",
        ]
    return [
        "design_diagnostic_only_non_compact_prediction_payload_capture",
        "do_not_run_quick_quality_or_training_for_this_trace_stage",
    ]


def build_read_only_predicted_label_payload_trace_audit(
    *,
    candidate_result: Mapping[str, Any] | None = None,
    sources: Sequence[Mapping[str, Any]] | None = None,
    ml_predictions_db_rows: Sequence[Any] | None = None,
    uncompressed_full_candidate_result: Any = None,
    compact_zip_candidate_result: Any = None,
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
    discovery = build_predicted_label_source_discovery_board(
        sources, candidate_result=candidate_result
    )
    locator = build_prediction_row_locator_board(
        candidate_result,
        ml_predictions_db_rows=ml_predictions_db_rows,
        uncompressed_full_candidate_result=uncompressed_full_candidate_result,
        compact_zip_candidate_result=compact_zip_candidate_result,
    )
    readiness = build_timestamp_prediction_join_readiness(locator)
    decision = classify_predicted_label_trace_decision(
        readiness, source_discovery_board=discovery
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
        "source_counts": dict(source_counts or {}),
        "predicted_label_source_discovery_board": discovery,
        "candidate_payload_omission_audit": build_candidate_payload_omission_audit(
            candidate_result, recovery_sources=sources
        ),
        "prediction_row_locator_board": locator,
        "timestamp_prediction_join_readiness": readiness,
        "actual_vs_predicted_guardrail": build_actual_vs_predicted_guardrail(),
        "trace_blockers": _trace_blockers(locator, readiness, discovery),
        "next_reproduction_plan": build_next_reproduction_plan(readiness),
        "ml38_10_45_predicted_label_trace_decision": decision,
        "decision": decision,
        "database_writes": False,
        "ml_labels_writes": False,
        "training_or_runtime_execution": False,
    }


def discover_read_only_prediction_sources(
    project_root: Path,
    *,
    reference_config_id: str = REFERENCE_CONFIG_ID,
    model_version: str | None = None,
) -> list[dict[str, Any]]:
    """Read existing JSON/ZIP artifacts only; never writes or runs evaluation."""
    root = Path(project_root)
    reports = root / "reports"
    sources: list[dict[str, Any]] = []
    candidate_name = f"{reference_config_id}.json"
    full_paths = sorted((reports / "feature_regime_experiments").glob(f"**/candidate_results/{candidate_name}"))
    for path in full_paths:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            error = None
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            value, error = None, str(exc)
        sources.append({
            "source_name": "full_uncompressed_candidate_result",
            "source_type": "json",
            "source_path_or_table": str(path),
            "value": value,
            "exists": True,
            "access_error": error,
        })
    for zip_path in sorted((reports / "feature_regime_experiments").glob("quick_quality_fv3_cached_fresh_tuning_solusdt_15m_*.zip")):
        try:
            with ZipFile(zip_path) as archive:
                members = [name for name in archive.namelist() if name.endswith(f"candidate_results/{candidate_name}")]
                for member in members:
                    value = json.loads(archive.read(member).decode("utf-8"))
                    sources.append({
                        "source_name": "compact_zip_candidate_result",
                        "source_type": "zip_json",
                        "source_path_or_table": f"{zip_path}!/{member}",
                        "value": value,
                        "exists": True,
                    })
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            sources.append({
                "source_name": "compact_zip_candidate_result",
                "source_type": "zip_json",
                "source_path_or_table": str(zip_path),
                "value": None,
                "exists": True,
                "access_error": str(exc),
            })
    if model_version:
        for path in sorted(reports.glob(f"probability_diagnostics_{model_version}.json")):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
                error = None
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                value, error = None, str(exc)
            sources.append({
                "source_name": "training_evaluation_intermediate_cache",
                "source_type": "probability_diagnostics_json",
                "source_path_or_table": str(path),
                "value": value,
                "exists": True,
                "access_error": error,
            })
    return sources
