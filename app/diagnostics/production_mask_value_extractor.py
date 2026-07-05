from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Mapping, Sequence


DIAGNOSTIC_NAME = "read_only_production_mask_value_extractor_audit"
DIAGNOSTIC_VERSION = "ml38.10.43"
EXECUTION_MODE = "READ_ONLY_NO_TRAINING_NO_DB_WRITES"
REFERENCE_CONFIG_ID = "lv31_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_bad_dates_exit45_probe"

_REGIME_FIELDS = (
    "market_regime",
    "regime_context",
    "regime_context_eligible",
    "regime_eligible",
    "regime_trend_up",
    "regime_trend_down",
    "regime_range",
    "regime_high_volatility",
    "regime_low_volatility",
)


def _value(row: Any, key: str, default: Any = None) -> Any:
    return row.get(key, default) if isinstance(row, Mapping) else getattr(row, key, default)


def _nested_value(row: Any, key: str) -> Any:
    value = _value(row, key)
    if value is not None:
        return value
    features = _value(row, "features_json", {})
    return features.get(key) if isinstance(features, Mapping) else None


def _has_value(row: Any, fields: Sequence[str]) -> bool:
    return any(_nested_value(row, field) is not None for field in fields)


def _date_time(value: date | datetime | str, *, end: bool = False) -> datetime:
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, date):
        result = datetime.combine(value, time.min)
    else:
        text = str(value).strip().replace("Z", "+00:00")
        result = datetime.fromisoformat(text)
        if end and len(text) == 10:
            result += timedelta(days=1)
    return result if result.tzinfo else result.replace(tzinfo=timezone.utc)


def extract_feature_rows_read_only(
    session: Any,
    *,
    symbol: str,
    interval: str,
    start_date: date | datetime | str,
    end_date: date | datetime | str,
    feature_version: str | None = None,
) -> list[Any]:
    """Select feature rows only; this function has no write/flush/commit path."""

    from sqlalchemy import select
    from app.db.models import MlFeatures

    statement = (
        select(MlFeatures)
        .where(MlFeatures.symbol == symbol)
        .where(MlFeatures.interval == interval)
        .where(MlFeatures.candle_open_time >= _date_time(start_date))
        .where(MlFeatures.candle_open_time < _date_time(end_date, end=True))
    )
    if feature_version is not None:
        statement = statement.where(MlFeatures.feature_version == feature_version)
    statement = statement.order_by(MlFeatures.candle_open_time.asc())
    return list(session.scalars(statement))


def extract_production_label_rows_read_only(
    session: Any,
    *,
    symbol: str,
    interval: str,
    start_date: date | datetime | str,
    end_date: date | datetime | str,
    label_version: str,
    horizon_candles: int,
) -> list[Any]:
    """Select an explicitly filtered label stream; never writes ``ml_labels``."""

    from sqlalchemy import select
    from app.db.models import MlLabels

    statement = (
        select(MlLabels)
        .where(MlLabels.symbol == symbol)
        .where(MlLabels.interval == interval)
        .where(MlLabels.label_version == label_version)
        .where(MlLabels.horizon_candles == horizon_candles)
        .where(MlLabels.candle_open_time >= _date_time(start_date))
        .where(MlLabels.candle_open_time < _date_time(end_date, end=True))
        .order_by(MlLabels.candle_open_time.asc())
    )
    return list(session.scalars(statement))


def build_timestamp_join_key_audit(
    *,
    candle_fields: Sequence[str] = ("symbol", "interval", "open_time"),
    feature_fields: Sequence[str] = ("symbol", "interval", "candle_open_time"),
    label_fields: Sequence[str] = ("symbol", "interval", "candle_open_time"),
) -> dict[str, Any]:
    candles = set(candle_fields)
    features = set(feature_fields)
    labels = set(label_fields)
    scoped = {"symbol", "interval"}.issubset(candles & features & labels)
    candle_time = "open_time" in candles
    persisted_time = "candle_open_time" in features and "candle_open_time" in labels
    ready = scoped and candle_time and persisted_time
    partial = candle_time and ("candle_open_time" in features or "candle_open_time" in labels)
    return {
        "candidate_join_keys": [
            "symbol+interval+candle_open_time",
            "symbol+interval+open_time",
            "timestamp/open_time",
            "row_index",
        ],
        "preferred_join_key": "symbol+interval+candle_open_time" if ready else None,
        "join_key_status": "READY" if ready else ("PARTIAL" if partial else "BLOCKED"),
        "duplicate_risk": (
            "Low only after feature_version and label_version+horizon filters: DB unique constraints "
            "include those version dimensions; omitting them can duplicate a candle timestamp."
        ),
        "timezone_risk": (
            "All DB model timestamp columns are timezone-aware, but cache/synthetic timestamps may be naive; "
            "normalize to UTC before joining."
        ),
        "missing_feature_rows_risk": (
            "Expected: feature warm-up/windowing can leave fewer feature rows than market candles."
        ),
        "evidence": (
            "MarketCandles.open_time, MlFeatures.candle_open_time and MlLabels.candle_open_time are "
            "DateTime(timezone=True); model unique constraints are scoped by symbol+interval and versions."
        ),
    }


def _duplicate_count(rows: Sequence[Any]) -> int:
    keys = [
        (
            _value(row, "symbol"),
            _value(row, "interval"),
            _value(row, "candle_open_time", _value(row, "open_time", _value(row, "timestamp"))),
        )
        for row in rows
    ]
    usable = [key for key in keys if key[2] is not None]
    return len(usable) - len(set(usable))


def _board_row(
    value_name: str,
    *,
    source_type: str,
    source: str,
    field: str,
    method: str,
    join_key: str | None,
    expected: int | None,
    extracted: int,
    duplicates: int,
    status: str,
    threshold: Any = None,
    can_count: bool = False,
    evidence: str,
) -> dict[str, Any]:
    missing = max(0, expected - extracted) if expected is not None else None
    return {
        "value_name": value_name,
        "source_type": source_type,
        "source_table_or_module": source,
        "source_field_or_function": field,
        "extraction_method": method,
        "join_key": join_key,
        "expected_row_count": expected,
        "extracted_row_count": extracted,
        "missing_row_count": missing,
        "duplicate_row_count": duplicates,
        "extraction_status": status,
        "threshold_if_applicable": threshold,
        "can_count_cascade": can_count,
        "evidence": evidence,
        "requires_db_write": False,
        "requires_label_builder_change": False,
    }


def build_mask_value_extraction_board(
    *,
    feature_rows: Sequence[Any] | None = None,
    production_label_rows: Sequence[Any] | None = None,
    evaluator_rows: Sequence[Any] | None = None,
    expected_row_count: int | None = 6481,
    aggregate_sources: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    features = list(feature_rows or [])
    labels = list(production_label_rows or [])
    evaluator = list(evaluator_rows or [])
    aggregate = dict(aggregate_sources or {})
    join_key = "symbol+interval+candle_open_time"
    feature_duplicates = _duplicate_count(features)
    label_duplicates = _duplicate_count(labels)

    def present(rows: Sequence[Any], fields: Sequence[str]) -> int:
        return sum(_has_value(row, fields) for row in rows)

    def extracted_status(count: int) -> str:
        if count:
            return "EXTRACTED_READ_ONLY"
        return "DB_COLUMN_FOUND_NO_ROWS"

    identity_count = present(features, ("candle_open_time", "open_time", "timestamp"))
    setup_rows = labels if labels else features
    setup_count = present(setup_rows, ("setup_quality_score",))
    regime_count = present(features, _REGIME_FIELDS)
    epq_count = present(evaluator, ("entry_path_quality_score", "entry_path_score", "entry_quality_score"))
    stop_count = present(evaluator, ("stop_pressure_risk_score", "stop_pressure_score", "stop_pressure"))
    recovery_count = present(evaluator, ("recovery_guard_decision", "recovery_guard_eligible"))
    label_count = present(labels, ("direction_label", "production_selected_label"))
    label_identity_count = present(labels, ("candle_open_time", "open_time", "timestamp"))

    rows = [
        _board_row(
            "feature_row_identity_stream", source_type="READ_ONLY_DB_ROWS", source="ml_features",
            field="symbol+interval+candle_open_time+feature_version", method="read-only SELECT or supplied rows",
            join_key=join_key, expected=expected_row_count, extracted=identity_count, duplicates=feature_duplicates,
            status=extracted_status(identity_count), evidence="MlFeatures model and unique constraint.",
        ),
        _board_row(
            "setup_quality_score_by_timestamp", source_type="READ_ONLY_DB_COLUMN", source="ml_labels",
            field="setup_quality_score", method="read-only label SELECT", join_key=join_key,
            expected=expected_row_count, extracted=setup_count, duplicates=label_duplicates if labels else feature_duplicates,
            status=extracted_status(setup_count), threshold=0.60, can_count=setup_count == expected_row_count,
            evidence="MlLabels.setup_quality_score is persisted; no label-builder execution is required.",
        ),
        _board_row(
            "entry_path_quality_score_by_timestamp", source_type="IN_MEMORY_EVALUATOR_VALUE",
            source="app/evaluation/profit_aware_evaluator_v2.py", field="entry_path_quality_score",
            method="use supplied evaluator row payload", join_key=join_key, expected=expected_row_count,
            extracted=epq_count, duplicates=_duplicate_count(evaluator),
            status="EXTRACTED_READ_ONLY" if epq_count else "SOURCE_FOUND_BUT_IN_MEMORY_ONLY",
            threshold=0.70, can_count=epq_count == expected_row_count,
            evidence="Evaluator/training payload computes the value; ml_features/ml_labels have no dedicated column.",
        ),
        _board_row(
            "stop_pressure_risk_score_by_timestamp", source_type="IN_MEMORY_EVALUATOR_VALUE",
            source="app/evaluation/profit_aware_evaluator_v2.py", field="stop_pressure_risk_score",
            method="use supplied evaluator row payload", join_key=join_key, expected=expected_row_count,
            extracted=stop_count, duplicates=_duplicate_count(evaluator),
            status="EXTRACTED_READ_ONLY" if stop_count else "SOURCE_FOUND_BUT_IN_MEMORY_ONLY",
            threshold=0.45, can_count=stop_count == expected_row_count,
            evidence="Evaluator/training payload computes the value; ml_features/ml_labels have no dedicated column.",
        ),
        _board_row(
            "regime_context_by_timestamp", source_type="FEATURE_JSON_FIELDS", source="ml_features",
            field="features_json.regime_* / market_regime", method="read-only feature SELECT and JSON extraction",
            join_key=join_key, expected=expected_row_count, extracted=regime_count, duplicates=feature_duplicates,
            status=extracted_status(regime_count), can_count=regime_count == expected_row_count,
            evidence="Regime fields are emitted per feature row and persisted inside features_json.",
        ),
        _board_row(
            "recovery_guard_decision_by_timestamp", source_type="IN_MEMORY_EVALUATOR_VALUE",
            source="app/evaluation/profit_aware_evaluator_v2.py", field="recovery_guard_decision",
            method="use supplied evaluator row payload", join_key=join_key, expected=expected_row_count,
            extracted=recovery_count, duplicates=_duplicate_count(evaluator),
            status="EXTRACTED_READ_ONLY" if recovery_count else "SOURCE_FOUND_BUT_IN_MEMORY_ONLY",
            can_count=recovery_count == expected_row_count,
            evidence="Recovery guard is an evaluator decision and has no ml_features/ml_labels column.",
        ),
        _board_row(
            "production_selected_label_by_timestamp", source_type="READ_ONLY_DB_COLUMN", source="ml_labels",
            field="direction_label", method="read-only label SELECT with label_version+horizon filters",
            join_key=join_key, expected=expected_row_count, extracted=label_count, duplicates=label_duplicates,
            status=extracted_status(label_count), can_count=label_count == expected_row_count,
            evidence="MlLabels.direction_label is persisted and can be selected without writes.",
        ),
        _board_row(
            "production_label_row_identity", source_type="COMPOSITE_DB_IDENTITY", source="ml_labels",
            field="symbol+interval+candle_open_time+horizon_candles+label_version",
            method="read-only label SELECT", join_key=join_key, expected=expected_row_count,
            extracted=label_identity_count, duplicates=label_duplicates, status=extracted_status(label_identity_count),
            evidence="MlLabels unique constraint defines the production label-row identity.",
        ),
        _board_row(
            "bad_dates_time_slice_probe_metadata", source_type="AGGREGATE_ONLY_SOURCE",
            source="compact archive/config metadata", field="bad_dates/time-slice probe aggregates",
            method="read-only compact metadata inspection", join_key=None, expected=None,
            extracted=0, duplicates=0,
            status="AGGREGATE_ONLY_SOURCE" if aggregate else "RESEARCH_ONLY_EXCLUDED",
            evidence="Research-only probe metadata is not a timestamp-keyed production mask stream.",
        ),
    ]
    return rows


def build_mask_value_availability_summary(
    mask_value_extraction_board: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    rows = list(mask_value_extraction_board)
    extracted = [row for row in rows if row.get("extraction_status") == "EXTRACTED_READ_ONLY"]
    db_backed = [row for row in rows if row.get("source_type") in {"READ_ONLY_DB_ROWS", "READ_ONLY_DB_COLUMN", "FEATURE_JSON_FIELDS", "COMPOSITE_DB_IDENTITY"}]
    in_memory = [row for row in rows if row.get("extraction_status") == "SOURCE_FOUND_BUT_IN_MEMORY_ONLY"]
    aggregate = [row for row in rows if row.get("extraction_status") == "AGGREGATE_ONLY_SOURCE"]
    by_name = {str(row.get("value_name")): row for row in rows}
    cascade_names = (
        "setup_quality_score_by_timestamp", "entry_path_quality_score_by_timestamp",
        "stop_pressure_risk_score_by_timestamp", "regime_context_by_timestamp",
        "recovery_guard_decision_by_timestamp",
    )
    cascade_ready = all(by_name.get(name, {}).get("can_count_cascade") for name in cascade_names)
    production_ready = cascade_ready and all(
        by_name.get(name, {}).get("extraction_status") == "EXTRACTED_READ_ONLY"
        for name in ("production_selected_label_by_timestamp", "production_label_row_identity")
    )
    missing_names = [
        name for name in cascade_names
        if not by_name.get(name, {}).get("can_count_cascade")
    ]
    return {
        "requested_value_count": len(rows),
        "extracted_value_count": len(extracted),
        "missing_value_count": len(rows) - len(extracted),
        "db_backed_value_count": len(db_backed),
        "in_memory_only_value_count": len(in_memory),
        "aggregate_only_value_count": len(aggregate),
        "can_build_mask_cascade_counts": cascade_ready,
        "can_build_production_like_recompute": production_ready,
        "reason_if_not": None if production_ready else "Missing complete timestamp-keyed streams: " + ", ".join(missing_names),
    }


def build_production_label_extraction_summary(
    production_label_rows: Sequence[Any] | None = None,
    *,
    label_version: str | None = None,
    horizon_candles: int | None = None,
) -> dict[str, Any]:
    rows = list(production_label_rows or [])
    values = [str(_value(row, "direction_label", _value(row, "production_selected_label", ""))).upper() for row in rows]
    counts = Counter(value for value in values if value in {"UP", "DOWN", "FLAT"})
    total = sum(counts.values())
    directional = counts["UP"] + counts["DOWN"]

    def item(name: str, count: int) -> dict[str, Any]:
        return {"count": count, "pct": round(100.0 * count / total, 2) if total else 0.0}

    row_versions = {str(_value(row, "label_version")) for row in rows if _value(row, "label_version") is not None}
    row_horizons = {_value(row, "horizon_candles") for row in rows if _value(row, "horizon_candles") is not None}
    filters_found = bool(label_version or len(row_versions) == 1) and bool(horizon_candles is not None or len(row_horizons) == 1)
    if not filters_found:
        status = "LABEL_FILTER_INCOMPLETE"
    elif not rows:
        status = "DB_COLUMN_FOUND_NO_ROWS"
    else:
        status = "EXTRACTED_READ_ONLY"
    blockers = []
    if not (label_version or len(row_versions) == 1):
        blockers.append("missing_label_version_filter")
    if not (horizon_candles is not None or len(row_horizons) == 1):
        blockers.append("missing_horizon_filter")
    return {
        "label_table_available": True,
        "label_row_count": len(rows),
        "selected_label_field": "direction_label",
        "direction_label_distribution": {
            "UP": item("UP", counts["UP"]),
            "DOWN": item("DOWN", counts["DOWN"]),
            "FLAT": item("FLAT", counts["FLAT"]),
            "directional": item("directional", directional),
        },
        "setup_quality_score_available": bool(rows) and all(_value(row, "setup_quality_score") is not None for row in rows),
        "label_version_or_horizon_filters_found": filters_found,
        "join_key": "symbol+interval+candle_open_time",
        "extraction_status": status,
        "blockers": blockers,
    }


def classify_mask_value_extractor_decision(
    availability_summary: Mapping[str, Any],
    production_label_extraction_summary: Mapping[str, Any],
) -> list[str]:
    decisions = ["READ_ONLY_MASK_VALUE_EXTRACTOR_ADDED"]
    extracted = int(availability_summary.get("extracted_value_count", 0) or 0)
    missing = int(availability_summary.get("missing_value_count", 0) or 0)
    if extracted and missing:
        decisions.append("PARTIAL_MASK_VALUES_EXTRACTABLE")
    label_status = production_label_extraction_summary.get("extraction_status")
    decisions.append("PRODUCTION_LABEL_ROWS_EXTRACTABLE" if label_status == "EXTRACTED_READ_ONLY" else "PRODUCTION_LABEL_ROWS_NOT_EXTRACTED")
    if label_status == "LABEL_FILTER_INCOMPLETE":
        decisions.append("NEEDS_LABEL_VERSION_FILTER")
    if int(availability_summary.get("in_memory_only_value_count", 0) or 0):
        decisions.extend((
            "ENTRY_PATH_QUALITY_IN_MEMORY_ONLY",
            "STOP_PRESSURE_IN_MEMORY_ONLY",
            "RECOVERY_GUARD_IN_MEMORY_ONLY",
            "NEEDS_EVALUATOR_PAYLOAD_REPRODUCTION",
        ))
    if availability_summary.get("can_build_mask_cascade_counts"):
        decisions.append("CAN_PROCEED_TO_MASK_CASCADE_COUNTS")
    else:
        decisions.append("CANNOT_PROCEED_TO_MASK_CASCADE_COUNTS")
    if not availability_summary.get("can_build_production_like_recompute"):
        decisions.append("PRODUCTION_LIKE_RECOMPUTE_NOT_READY")
    decisions.extend(("DO_NOT_CHANGE_LABELS_YET", "DO_NOT_CHANGE_GATES", "DO_NOT_RUN_TRAINING"))
    return list(dict.fromkeys(decisions))


def build_next_join_plan(
    mask_value_extraction_board: Sequence[Mapping[str, Any]],
    production_label_extraction_summary: Mapping[str, Any] | None = None,
) -> list[str]:
    plan: list[str] = []
    for row in mask_value_extraction_board:
        status = row.get("extraction_status")
        name = str(row.get("value_name"))
        if status == "SOURCE_FOUND_BUT_IN_MEMORY_ONLY":
            plan.append(f"reproduce_{name}_from_evaluator_payload_read_only")
        elif status in {"DB_COLUMN_FOUND_NO_ROWS", "JOIN_KEY_BLOCKED"}:
            plan.append(f"extract_{name}_with_explicit_read_only_filters")
    if (production_label_extraction_summary or {}).get("extraction_status") == "LABEL_FILTER_INCOMPLETE":
        plan.append("resolve_production_label_version_and_horizon_filters")
    return list(dict.fromkeys(plan))


def build_read_only_production_mask_value_extractor_audit(
    *,
    feature_rows: Sequence[Any] | None = None,
    production_label_rows: Sequence[Any] | None = None,
    evaluator_rows: Sequence[Any] | None = None,
    source_counts: Mapping[str, Any] | None = None,
    label_version: str | None = None,
    horizon_candles: int | None = None,
    aggregate_sources: Mapping[str, Any] | None = None,
    symbol: str = "SOLUSDT",
    interval: str = "15m",
    start_date: str = "2026-04-01",
    end_date: str = "2026-06-15",
    reference_config_id: str = REFERENCE_CONFIG_ID,
) -> dict[str, Any]:
    counts = {
        "candle_count": 7282,
        "feature_row_count": 6481,
        "split_total_rows": 6481,
        "production_label_row_count": None,
        "production_directional_count": 74,
    }
    counts.update(dict(source_counts or {}))
    board = build_mask_value_extraction_board(
        feature_rows=feature_rows,
        production_label_rows=production_label_rows,
        evaluator_rows=evaluator_rows,
        expected_row_count=counts.get("feature_row_count"),
        aggregate_sources=aggregate_sources,
    )
    availability = build_mask_value_availability_summary(board)
    label_summary = build_production_label_extraction_summary(
        production_label_rows, label_version=label_version, horizon_candles=horizon_candles
    )
    blockers = []
    blocker_map = {
        "feature_row_identity_stream": "missing_feature_row_stream",
        "entry_path_quality_score_by_timestamp": "entry_path_quality_in_memory_only",
        "stop_pressure_risk_score_by_timestamp": "stop_pressure_in_memory_only",
        "recovery_guard_decision_by_timestamp": "recovery_guard_in_memory_only",
        "regime_context_by_timestamp": "missing_regime_context_stream",
    }
    for row in board:
        if row.get("extraction_status") != "EXTRACTED_READ_ONLY" and row.get("value_name") in blocker_map:
            blockers.append(blocker_map[str(row["value_name"])])
    blockers.extend(label_summary["blockers"])
    decisions = classify_mask_value_extractor_decision(availability, label_summary)
    return {
        "diagnostic_name": DIAGNOSTIC_NAME,
        "diagnostic_version": DIAGNOSTIC_VERSION,
        "execution_mode": EXECUTION_MODE,
        "symbol": symbol,
        "interval": interval,
        "date_range": f"{start_date} -> {end_date}",
        "reference_config_id": reference_config_id,
        "source_counts": counts,
        "timestamp_join_key_audit": build_timestamp_join_key_audit(),
        "mask_value_extraction_board": board,
        "mask_value_availability_summary": availability,
        "production_label_extraction_summary": label_summary,
        "extractor_blockers": list(dict.fromkeys(blockers)),
        "next_join_plan": build_next_join_plan(board, label_summary),
        "ml38_10_43_extractor_decision": decisions,
        "decision": decisions,
        "db_writes_performed": False,
        "training_or_runtime_execution": False,
    }
