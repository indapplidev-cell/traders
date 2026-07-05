from __future__ import annotations

import csv
import json
import re
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from app.features.technical_indicators import TechnicalIndicators


DIAGNOSTIC_NAME = "read_only_label_grid_sensitivity_recompute"
DIAGNOSTIC_VERSION = "ml38.10.39"
EXECUTION_MODE = "READ_ONLY_NO_TRAINING_NO_DB_WRITES"
DEFAULT_HORIZONS = (8, 12, 16, 24)
DEFAULT_THRESHOLD_PAIRS = (
    (0.6, 0.6), (0.8, 0.8), (1.0, 1.0),
    (1.2, 1.2), (1.5, 1.0), (1.0, 1.5),
)
DEFAULT_FLAT_BOUNDARIES = (0.10, 0.20, 0.30, 0.40)


def _value(row: Any, key: str, default: Any = None) -> Any:
    return row.get(key, default) if isinstance(row, dict) else getattr(row, key, default)


def _datetime(value: date | datetime | str, *, end: bool = False) -> datetime:
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


def _normalized_candle(row: Any) -> dict[str, Any]:
    return {
        "open_time": _value(row, "open_time", _value(row, "timestamp")),
        "open": float(_value(row, "open")),
        "high": float(_value(row, "high")),
        "low": float(_value(row, "low")),
        "close": float(_value(row, "close")),
        "volume": float(_value(row, "volume", 0.0) or 0.0),
    }


def _load_cache(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return [_normalized_candle(row) for row in csv.DictReader(handle)]
    text = path.read_text(encoding="utf-8")
    if suffix in {".jsonl", ".ndjson"}:
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        payload = json.loads(text)
        rows = payload.get("candles", []) if isinstance(payload, dict) else payload
    return [_normalized_candle(row) for row in rows]


def load_candles_read_only(
    symbol: str,
    interval: str,
    start_date: date | datetime | str,
    end_date: date | datetime | str,
    *,
    repository: Any | None = None,
    cache_path: str | Path | None = None,
    database_url: str | None = None,
) -> list[dict[str, Any]]:
    """Read OHLCV rows without calling any repository write method."""

    start_at = _datetime(start_date)
    end_at = _datetime(end_date, end=True)
    if cache_path is not None:
        rows = _load_cache(Path(cache_path))
        return [
            row for row in rows
            if start_at <= _datetime(row["open_time"]) < end_at
        ]
    if repository is not None:
        return [
            _normalized_candle(row)
            for row in repository.get_range(
                symbol=symbol, interval=interval, start_at=start_at, end_at=end_at
            )
        ]

    from app.db.repositories.candle_repository import CandleRepository
    from app.db.session import get_session

    session = get_session(database_url)
    try:
        rows = CandleRepository(session).get_range(
            symbol=symbol, interval=interval, start_at=start_at, end_at=end_at
        )
        return [_normalized_candle(row) for row in rows]
    finally:
        session.rollback()
        session.close()


def compute_forward_path_labels(
    candles: Sequence[Any],
    *,
    horizon: int,
    tp_threshold: float,
    sl_threshold: float,
    flat_boundary: float,
    atr_move_threshold: float | None = None,
    atr_period: int = 14,
) -> list[dict[str, Any]]:
    """Compute diagnostic labels in memory; never persists to ``ml_labels``."""

    if horizon <= 0 or tp_threshold <= 0 or sl_threshold <= 0:
        raise ValueError("horizon and thresholds must be positive")
    rows = [_normalized_candle(row) for row in candles]
    highs = [row["high"] for row in rows]
    lows = [row["low"] for row in rows]
    closes = [row["close"] for row in rows]
    atr_values = TechnicalIndicators.atr(highs, lows, closes, atr_period)
    neutral_boundary = max(float(flat_boundary), float(atr_move_threshold or 0.0))
    labels: list[dict[str, Any]] = []
    for index in range(max(0, len(rows) - horizon)):
        atr = atr_values[index]
        close = closes[index]
        if atr is None or float(atr) <= 0 or close <= 0:
            continue
        atr = float(atr)
        upper = close + float(tp_threshold) * atr
        lower = close - float(sl_threshold) * atr
        label = "FLAT"
        reason = "no_touch_inside_neutral_boundary"
        future = rows[index + 1 : index + 1 + horizon]
        for candle in future:
            up_hit = candle["high"] >= upper
            down_hit = candle["low"] <= lower
            if up_hit and down_hit:
                label, reason = "FLAT", "ambiguous_same_candle_touch"
                break
            if up_hit:
                label, reason = "UP", "upper_atr_threshold_first"
                break
            if down_hit:
                label, reason = "DOWN", "lower_atr_threshold_first"
                break
        else:
            terminal_move_atr = (future[-1]["close"] - close) / atr
            if terminal_move_atr >= neutral_boundary:
                label, reason = "UP", "terminal_move_above_flat_boundary"
            elif terminal_move_atr <= -neutral_boundary:
                label, reason = "DOWN", "terminal_move_below_flat_boundary"
        labels.append(
            {
                "timestamp": rows[index]["open_time"],
                "label": label,
                "atr_at_entry": atr,
                "horizon": horizon,
                "tp_threshold": float(tp_threshold),
                "sl_threshold": float(sl_threshold),
                "flat_boundary": float(flat_boundary),
                "atr_move_threshold": neutral_boundary,
                "reason": reason,
            }
        )
    return labels


def compute_label_distribution(labels: Iterable[Any]) -> dict[str, Any]:
    values = [str(_value(row, "label", row)).upper() for row in labels]
    counts = {name: values.count(name) for name in ("UP", "DOWN", "FLAT")}
    total = sum(counts.values())
    directional_count = counts["UP"] + counts["DOWN"]
    directional_pct = 100.0 * directional_count / total if total else 0.0
    flat_pct = 100.0 * counts["FLAT"] / total if total else 0.0
    balance = (
        min(counts["UP"], counts["DOWN"]) / max(counts["UP"], counts["DOWN"])
        if max(counts["UP"], counts["DOWN"]) else None
    )
    return {
        "row_count": total,
        "up_count": counts["UP"],
        "down_count": counts["DOWN"],
        "flat_count": counts["FLAT"],
        "directional_count": directional_count,
        "up_pct": 100.0 * counts["UP"] / total if total else 0.0,
        "down_pct": 100.0 * counts["DOWN"] / total if total else 0.0,
        "flat_pct": flat_pct,
        "directional_pct": directional_pct,
        "flat_to_directional_ratio": (
            counts["FLAT"] / directional_count if directional_count else None
        ),
        "up_down_balance": balance,
        "expected_baseline_pressure": (
            "HIGH" if flat_pct > 85 else "MEDIUM" if flat_pct >= 55 else "LOW"
        ),
        "sample_warning": (
            "directional_sample_below_100" if directional_count < 100
            else "one_direction_below_40" if min(counts["UP"], counts["DOWN"]) < 40
            else "directional_sample_sufficient_for_diagnostic_review"
        ),
    }


def classify_label_grid_row(row: dict[str, Any]) -> str:
    total = int(row.get("row_count", 0) or 0)
    directional = int(row.get("directional_count", 0) or 0)
    up_count = int(row.get("up_count", 0) or 0)
    down_count = int(row.get("down_count", 0) or 0)
    flat_pct = float(row.get("flat_pct", 0.0) or 0.0)
    noise = str(row.get("label_noise_risk", "UNKNOWN"))
    if total == 0:
        return "INSUFFICIENT_DATA"
    if flat_pct < 50.0:
        return "TOO_NOISY"
    if directional < 100:
        return "DIRECTIONAL_SAMPLE_TOO_SMALL"
    if flat_pct > 85.0:
        return "TOO_FLAT"
    balance = row.get("up_down_balance")
    if min(up_count, down_count) < 30 or (balance is not None and float(balance) < 0.50):
        return "UP_DOWN_IMBALANCED"
    ratio = row.get("flat_to_directional_ratio")
    if (
        min(up_count, down_count) >= 40
        and 55.0 <= flat_pct <= 85.0
        and ratio is not None and float(ratio) < 12.14
        and noise != "HIGH"
    ):
        return "PROMISING_DIAGNOSTIC_ZONE"
    return "UP_DOWN_IMBALANCED" if min(up_count, down_count) < 40 else "TOO_FLAT"


def build_label_grid_sensitivity_board(
    candles: Sequence[Any],
    *,
    symbol: str,
    interval: str,
    start_date: str,
    end_date: str,
    horizons: Sequence[int] = DEFAULT_HORIZONS,
    threshold_pairs: Sequence[tuple[float, float]] = DEFAULT_THRESHOLD_PAIRS,
    flat_boundaries: Sequence[float] = DEFAULT_FLAT_BOUNDARIES,
) -> list[dict[str, Any]]:
    board: list[dict[str, Any]] = []
    for horizon in horizons:
        for tp_threshold, sl_threshold in threshold_pairs:
            for flat_boundary in flat_boundaries:
                labels = compute_forward_path_labels(
                    candles,
                    horizon=int(horizon),
                    tp_threshold=float(tp_threshold),
                    sl_threshold=float(sl_threshold),
                    flat_boundary=float(flat_boundary),
                    atr_move_threshold=float(flat_boundary),
                )
                row = {
                    "symbol": symbol,
                    "interval": interval,
                    "start_date": start_date,
                    "end_date": end_date,
                    "horizon": int(horizon),
                    "tp_threshold": float(tp_threshold),
                    "sl_threshold": float(sl_threshold),
                    "flat_boundary": float(flat_boundary),
                    "atr_move_threshold": float(flat_boundary),
                    **compute_label_distribution(labels),
                }
                directional_pct = float(row["directional_pct"])
                row["label_noise_risk"] = (
                    "HIGH" if row["flat_pct"] < 50 or (
                        min(tp_threshold, sl_threshold) <= 0.6 and directional_pct > 45
                    ) else "MEDIUM" if directional_pct > 35 else "LOW"
                )
                row["diagnostic_verdict"] = classify_label_grid_row(row)
                board.append(row)
    return board


def build_read_only_label_grid_sensitivity_recompute(
    candles: Sequence[Any],
    *,
    symbol: str = "SOLUSDT",
    interval: str = "15m",
    start_date: str = "2026-04-01",
    end_date: str = "2026-06-15",
    horizons: Sequence[int] = DEFAULT_HORIZONS,
    threshold_pairs: Sequence[tuple[float, float]] = DEFAULT_THRESHOLD_PAIRS,
    flat_boundaries: Sequence[float] = DEFAULT_FLAT_BOUNDARIES,
) -> dict[str, Any]:
    board = build_label_grid_sensitivity_board(
        candles, symbol=symbol, interval=interval, start_date=start_date,
        end_date=end_date, horizons=horizons, threshold_pairs=threshold_pairs,
        flat_boundaries=flat_boundaries,
    )
    promising = [row for row in board if row["diagnostic_verdict"] == "PROMISING_DIAGNOSTIC_ZONE"]
    too_flat = [row for row in board if row["diagnostic_verdict"] in {"TOO_FLAT", "DIRECTIONAL_SAMPLE_TOO_SMALL"}]
    too_noisy = [row for row in board if row["diagnostic_verdict"] == "TOO_NOISY"]
    decisions = ["READ_ONLY_LABEL_GRID_RECOMPUTE_READY"]
    if too_flat:
        decisions.append("CURRENT_LABELS_TOO_FLAT_CONFIRMED")
    decisions.append("PROMISING_DIAGNOSTIC_ZONES_FOUND" if promising else "NO_PROMISING_ZONE_FOUND")
    decisions.extend((
        "NEEDS_RUNTIME_QUICK_QUALITY_VALIDATION", "DO_NOT_CHANGE_LABELS_YET",
        "DO_NOT_CHANGE_GATES", "DO_NOT_ACCEPT_RESEARCH_ONLY_CANDIDATE",
    ))
    return {
        "diagnostic_name": DIAGNOSTIC_NAME,
        "diagnostic_version": DIAGNOSTIC_VERSION,
        "execution_mode": EXECUTION_MODE,
        "symbol": symbol,
        "interval": interval,
        "date_range": f"{start_date} -> {end_date}",
        "parameter_grid": {
            "horizons": list(horizons),
            "tp_sl_threshold_pairs": [list(pair) for pair in threshold_pairs],
            "flat_boundaries": list(flat_boundaries),
        },
        "sensitivity_board": board,
        "best_diagnostic_zones": sorted(
            promising,
            key=lambda row: (-int(row["directional_count"]), abs(float(row["up_down_balance"] or 0) - 1.0)),
        )[:10],
        "too_flat_count": len(too_flat),
        "too_noisy_count": len(too_noisy),
        "promising_zone_count": len(promising),
        "current_config_neighborhood": {
            "reference_flat_to_directional_ratio": 12.14,
            "rows": [row for row in board if row["horizon"] == 12 and row["flat_boundary"] == 0.2],
        },
        "decision": decisions,
        "db_writes_performed": False,
        "training_or_runtime_execution": False,
    }


def build_current_config_mapping_audit(
    config_id: str | None,
    config_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(config_payload or {})
    text = str(config_id or "")

    def encoded(pattern: str, scale: float = 1.0) -> float | int | None:
        match = re.search(pattern, text)
        if not match:
            return None
        value = int(match.group(1))
        return value if scale == 1.0 else value / scale

    mapping = {
        "config_id": config_id,
        "horizon": payload.get("horizon", payload.get("horizon_candles", encoded(r"_h(\d+)"))),
        "label_mode": payload.get("label_mode", "first_touch_tp_sl" if "_tts_" in text else None),
        "direction_atr_threshold": payload.get("direction_atr_threshold", encoded(r"_thr(\d+)", 100.0)),
        "tp_threshold": payload.get("take_profit_atr"),
        "sl_threshold": payload.get("stop_loss_atr"),
        "flat_boundary": payload.get("flat_boundary"),
        "setup_quality_mask": payload.get(
            "setup_quality_decision_mask_min_threshold", encoded(r"_sqmask(\d+)", 100.0)
        ),
        "entry_path_quality": payload.get("entry_path_quality_min_threshold", encoded(r"_epq(\d+)", 100.0)),
        "stop_pressure": payload.get("stop_pressure_max_risk_score", encoded(r"_sp(\d+)", 100.0)),
        "recovery_guard": payload.get("recovery_guard_enabled", "rguard" in text),
        "regime_specific_behavior": payload.get("regime_specific_label_configs"),
    }
    required = (
        "horizon", "label_mode", "direction_atr_threshold", "tp_threshold",
        "sl_threshold", "setup_quality_mask", "entry_path_quality",
        "stop_pressure", "regime_specific_behavior",
    )
    missing = [key for key in required if mapping.get(key) is None]
    return {
        "status": "CURRENT_CONFIG_MAPPING_INCOMPLETE" if missing else "CURRENT_CONFIG_MAPPING_COMPLETE",
        "mapping": mapping,
        "missing_mapping_fields": missing,
        "sensitivity_board_actionable": not missing,
        "diagnostic_only": True,
    }


def build_label_recompute_semantics_gap_board(
    *,
    production_reference: dict[str, Any] | None = None,
    recompute_board: Sequence[dict[str, Any]] | None = None,
    denominator_evidence: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    production = dict(production_reference or {})
    board = list(recompute_board or [])
    denominators = dict(denominator_evidence or {})
    flat_values = [float(row["flat_pct"]) for row in board if row.get("flat_pct") is not None]
    common = {"requires_code_change_to_label_builder": False, "requires_db_write": False}
    specs = (
        ("denominator_mismatch", {"production_directional_count": production.get("directional_count"), **denominators}, "HIGH", "compare candle, feature, label, split, regime and quality-mask row counts", "P0"),
        ("missing_setup_quality_mask", "recompute accepts every ATR-valid candle; production configs encode sqmask", "HIGH", "apply the existing setup-quality decision mask in memory and compare distributions", "P0"),
        ("missing_entry_path_quality_mask", "recompute has no epq eligibility field", "HIGH", "join existing feature rows read-only and shadow-filter by entry-path quality", "P0"),
        ("missing_regime_specific_label_builder", "production supports per-regime threshold overrides", "HIGH", "run RegimeLabelBuilder-compatible logic in memory with existing regime features", "P0"),
        ("threshold_unit_mismatch", "production thr065 is direction_atr_threshold; recompute grid treats TP/SL touches as direction", "HIGH", "compare production future-close ATR threshold against recompute thresholds on identical rows", "P0"),
        ("forward_path_tie_or_tp_sl_ordering_mismatch", "production FirstTouchDirectionLabelBuilder evaluates side TP and SL ordering", "MEDIUM", "compare per-row first-touch reason and tie handling", "P1"),
        ("timeout_flat_semantics_mismatch", "recompute terminal movement can turn a no-touch timeout into UP/DOWN", "HIGH", "compare no-touch rows with production selected_direction_label", "P0"),
        ("flat_boundary_not_equivalent_to_production_thr065", {"production_flat_pct": production.get("flat_pct"), "recompute_flat_pct_range": [min(flat_values), max(flat_values)] if flat_values else None}, "HIGH", "treat thr065 as production direction ATR threshold, not a generic neutral boundary", "P0"),
        ("current_config_mapping_missing", "config id does not encode every label, mask and regime parameter", "HIGH", "resolve the full config object read-only before parity recompute", "P0"),
    )
    return [
        {"gap_name": name, "evidence": evidence, "likely_impact": impact,
         "how_to_test_read_only": test, "priority": priority, **common}
        for name, evidence, impact, test, priority in specs
    ]


def build_production_label_semantics_parity_audit(
    *,
    production_reference: dict[str, Any] | None,
    recompute_board: Sequence[dict[str, Any]] | None,
    denominator_evidence: dict[str, Any] | None = None,
    current_config_id: str | None = None,
    current_config_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    production = dict(production_reference or {})
    board = list(recompute_board or [])
    flat_values = [float(row["flat_pct"]) for row in board if row.get("flat_pct") is not None]
    directional_values = [float(row["directional_pct"]) for row in board if row.get("directional_pct") is not None]
    production_flat = production.get("flat_pct")
    mismatch = bool(
        production_flat is not None and flat_values
        and min(abs(float(production_flat) - value) for value in flat_values) > 10.0
    )
    all_too_noisy = bool(board) and all(row.get("diagnostic_verdict") == "TOO_NOISY" for row in board)
    mapping = build_current_config_mapping_audit(current_config_id, current_config_payload)
    gap_board = build_label_recompute_semantics_gap_board(
        production_reference=production, recompute_board=board,
        denominator_evidence=denominator_evidence,
    )
    denominators = dict(denominator_evidence or {})
    denominator_fields = ("candle_count", "feature_row_count", "label_row_count", "candidate_training_rows")
    denominator_complete = all(denominators.get(key) is not None for key in denominator_fields)
    decisions = ["PRODUCTION_LABEL_PARITY_NOT_PROVEN"]
    if mismatch:
        decisions.append("READ_ONLY_RECOMPUTE_SEMANTICS_MISMATCH")
    if all_too_noisy and mismatch:
        decisions.append("CURRENT_SENSITIVITY_BOARD_TOO_NOISY_NOT_ACTIONABLE")
    if mapping["status"] == "CURRENT_CONFIG_MAPPING_INCOMPLETE":
        decisions.append("NEEDS_CURRENT_CONFIG_MAPPING")
    if not denominator_complete:
        decisions.append("NEEDS_DENOMINATOR_ALIGNMENT")
    decisions.extend(("DO_NOT_CHANGE_LABELS_YET", "DO_NOT_CHANGE_GATES", "DO_NOT_RUN_TRAINING"))
    return {
        "diagnostic_name": "production_label_semantics_parity_audit",
        "diagnostic_version": "ml38.10.40",
        "execution_mode": "DIAGNOSTIC_ONLY_NO_TRAINING_NO_DB_WRITES",
        "production_reference": {"source": "latest_quick_quality_compact_report", **production},
        "read_only_recompute_current": {
            "source": "ML38.10.39 current read-only recompute",
            "flat_pct_range": [min(flat_values), max(flat_values)] if flat_values else None,
            "directional_pct_range": [min(directional_values), max(directional_values)] if directional_values else None,
            "verdict": "SEMANTICS_MISMATCH" if mismatch else "PARITY_NOT_PROVEN",
        },
        "denominator_parity_audit": {
            **{key: denominators.get(key) for key in denominator_fields},
            "parity_status": "DENOMINATOR_EVIDENCE_COMPLETE" if denominator_complete else "DENOMINATOR_ALIGNMENT_INCOMPLETE",
        },
        "semantics_gap_hypotheses": [row["gap_name"] for row in gap_board],
        "required_alignment_steps": [row["how_to_test_read_only"] for row in gap_board if row["priority"] == "P0"],
        "sensitivity_board_actionability": "NOT_ACTIONABLE_PARITY_NOT_PROVEN" if mismatch or not board else "REVIEW_REQUIRED",
        "decision": decisions,
        "label_recompute_semantics_gap_board": gap_board,
        "current_config_mapping_audit": mapping,
        "ml38_10_40_parity_decision": decisions,
    }


def build_mask_cascade_board(
    *,
    source_counts: dict[str, Any] | None = None,
    config_mapping: dict[str, Any] | None = None,
    mask_evidence: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Describe the production row-selection cascade without applying it."""

    counts = dict(source_counts or {})
    mapping = dict(config_mapping or {})
    evidence_by_mask = dict(mask_evidence or {})
    split_keys = ("candidate_training_rows", "candidate_validation_rows", "candidate_test_rows")
    split_count = (
        sum(int(counts[key]) for key in split_keys)
        if all(counts.get(key) is not None for key in split_keys)
        else None
    )
    specs = (
        ("raw_candles", None, None, "candles.open_time/OHLCV", "starting denominator", counts.get("candle_count")),
        ("feature_rows_after_feature_builder", None, None, "feature rows joined by candle timestamp", "remove warm-up or otherwise unavailable feature rows", counts.get("feature_row_count")),
        ("atr_valid_rows", "thr065", mapping.get("direction_atr_threshold"), "ATR at label entry", "remove rows without a positive ATR and enforce production threshold units", None),
        ("setup_quality_mask_sqmask060", "sqmask060", mapping.get("setup_quality_mask"), "setup_quality_score", "retain rows eligible under the setup-quality decision mask", None),
        ("entry_path_quality_epq070_or_071", "epq070/observed candidate value", mapping.get("entry_path_quality"), "entry_path_quality_score", "retain rows meeting the effective entry-path threshold", None),
        ("stop_pressure_sp045", "sp045", mapping.get("stop_pressure"), "stop_pressure_risk_score", "remove rows above the maximum stop-pressure risk", None),
        ("regime_specific_behavior", None, mapping.get("regime_specific_behavior"), "regime flags and regime-specific label config", "apply the production regime context before parity comparison", None),
        ("recovery_guard_rguard", "rguard", mapping.get("recovery_guard"), "recovery guard inputs and decision", "remove or alter eligibility according to the configured recovery guard", None),
        ("bad_dates_time_slice_repair_probe", "long_bad_dates_exit45_probe", None, "timestamp/bad-date probe metadata", "exclude research-only repair-probe behavior from tradable parity", None),
        ("production_label_rows", None, mapping.get("direction_atr_threshold"), "production label row identity and selected label", "establish the exact production label denominator", counts.get("label_row_count")),
        ("train_val_test_split_rows", None, None, "training/validation/test split membership", "verify that splitting preserves the feature-row denominator", split_count),
    )
    rows: list[dict[str, Any]] = []
    for step_order, (name, token, threshold, source, impact, default_remaining) in enumerate(specs, 1):
        evidence = dict(evidence_by_mask.get(name) or {})
        per_row = bool(evidence.get("per_row_values_available", False))
        compact = bool(evidence.get("source_available_in_compact", False))
        read_only_db = bool(evidence.get("source_available_read_only_db", False))
        remaining = evidence.get("known_remaining_count", default_remaining)
        removed = evidence.get("known_removed_count")
        if name == "feature_rows_after_feature_builder" and removed is None:
            candle_count = counts.get("candle_count")
            feature_count = counts.get("feature_row_count")
            if candle_count is not None and feature_count is not None:
                removed = int(candle_count) - int(feature_count)
        if name == "raw_candles":
            status = "SOURCE_COUNT_KNOWN" if remaining is not None else "SOURCE_COUNT_MISSING"
        elif name == "train_val_test_split_rows":
            status = (
                "SPLIT_PARITY_OK"
                if split_count is not None and counts.get("feature_row_count") == split_count
                else "SPLIT_PARITY_NOT_PROVEN"
            )
        elif name == "bad_dates_time_slice_repair_probe":
            status = "RESEARCH_ONLY_EXCLUDE_FROM_TRADABLE_PARITY"
        elif name == "production_label_rows":
            status = "COUNT_KNOWN" if remaining is not None else "NEEDS_PRODUCTION_LABEL_ROW_COUNT"
        elif per_row:
            status = evidence.get("parity_status", "PER_ROW_VALUES_AVAILABLE_REVIEW_REQUIRED")
        else:
            status = evidence.get("parity_status", "PER_ROW_VALUES_NOT_AVAILABLE")
        rows.append({
            "step_order": step_order,
            "mask_name": name,
            "config_token": token,
            "mapped_threshold": evidence.get("mapped_threshold", threshold),
            "source_field_or_feature": evidence.get("source_field_or_feature", source),
            "source_available_in_compact": compact,
            "source_available_read_only_db": read_only_db,
            "per_row_values_available": per_row,
            "expected_impact": impact,
            "known_removed_count": removed,
            "known_remaining_count": remaining,
            "evidence": evidence.get("evidence", "no per-row evidence supplied"),
            "parity_status": status,
            "requires_db_write": False,
            "requires_label_builder_change": False,
        })
    return rows


def build_denominator_gap_board(
    *,
    source_counts: dict[str, Any] | None = None,
    production_directional_count: int | None = None,
    recompute_directional_count: int | None = None,
    mask_cascade_board: Sequence[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    counts = dict(source_counts or {})
    split_values = [counts.get(key) for key in (
        "candidate_training_rows", "candidate_validation_rows", "candidate_test_rows"
    )]
    split_total = sum(int(value) for value in split_values) if all(value is not None for value in split_values) else None
    feature_count = counts.get("feature_row_count")
    candle_count = counts.get("candle_count")
    label_count = counts.get("label_row_count")
    mask_rows = list(mask_cascade_board or [])
    mask_counts_known = all(
        row.get("known_removed_count") is not None
        for row in mask_rows
        if row.get("mask_name") in {
            "setup_quality_mask_sqmask060", "entry_path_quality_epq070_or_071", "stop_pressure_sp045"
        }
    )
    common = {"requires_db_write": False}
    return [
        {
            "gap_name": "candles_to_features_gap",
            "known_left_count": candle_count,
            "known_right_count": feature_count,
            "missing_count": int(candle_count) - int(feature_count) if candle_count is not None and feature_count is not None else None,
            "evidence": "candle_count versus feature_row_count",
            "likely_cause": "feature-builder warm-up and rows lacking required feature inputs",
            "how_to_close_read_only": "join candles to feature rows by timestamp and classify every missing row",
            "priority": "P0",
            **common,
        },
        {
            "gap_name": "features_to_training_dataset_gap",
            "known_left_count": feature_count,
            "known_right_count": split_total,
            "missing_count": int(feature_count) - split_total if feature_count is not None and split_total is not None else None,
            "evidence": "SPLIT_PARITY_OK" if feature_count is not None and feature_count == split_total else "SPLIT_PARITY_NOT_PROVEN",
            "likely_cause": "no gap when train, validation, and test counts sum to feature rows",
            "how_to_close_read_only": "compare split membership row identities against feature rows",
            "priority": "P0",
            **common,
        },
        {
            "gap_name": "production_label_count_missing",
            "known_left_count": feature_count,
            "known_right_count": label_count,
            "missing_count": int(feature_count) - int(label_count) if feature_count is not None and label_count is not None else None,
            "evidence": "NEEDS_PRODUCTION_LABEL_ROW_COUNT" if label_count is None else "PRODUCTION_LABEL_ROW_COUNT_AVAILABLE",
            "likely_cause": "compact evidence does not expose the production label denominator",
            "how_to_close_read_only": "count and identify production label rows without writing ml_labels",
            "priority": "P0",
            **common,
        },
        {
            "gap_name": "production_directional_count_vs_recompute_directional_count",
            "known_left_count": production_directional_count,
            "known_right_count": recompute_directional_count,
            "missing_count": (
                int(recompute_directional_count) - int(production_directional_count)
                if production_directional_count is not None and recompute_directional_count is not None else None
            ),
            "evidence": "directional counts use different unresolved denominators/mask semantics",
            "likely_cause": "recompute accepts ATR-valid rows before the production mask cascade",
            "how_to_close_read_only": "compare labels only after identical row identities and masks are joined",
            "priority": "P0",
            **common,
        },
        {
            "gap_name": "mask_removed_count_unknown",
            "known_left_count": feature_count,
            "known_right_count": None,
            "missing_count": None,
            "evidence": "MASK_REMOVED_COUNTS_KNOWN" if mask_counts_known else "PER_ROW_MASKS_NOT_FULLY_JOINED",
            "likely_cause": "setup-quality, entry-path-quality, and stop-pressure row values are incomplete",
            "how_to_close_read_only": "read-only join mask scores by row and record removed/remaining counts at every step",
            "priority": "P0",
            **common,
        },
    ]


def build_production_like_recompute_prerequisite_checklist(
    *,
    config_mapping_status: dict[str, Any],
    mask_cascade_board: Sequence[dict[str, Any]],
    denominator_gap_board: Sequence[dict[str, Any]],
    timeout_flat_semantics_aligned: bool = False,
) -> list[str]:
    required: list[str] = []
    if config_mapping_status.get("status") != "CURRENT_CONFIG_MAPPING_COMPLETE":
        required.append("FULL_CONFIG_OBJECT_REQUIRED")
    by_name = {row.get("mask_name"): row for row in mask_cascade_board}
    for name, decision in (
        ("setup_quality_mask_sqmask060", "PER_ROW_SETUP_QUALITY_REQUIRED"),
        ("entry_path_quality_epq070_or_071", "PER_ROW_ENTRY_PATH_QUALITY_REQUIRED"),
        ("stop_pressure_sp045", "PER_ROW_STOP_PRESSURE_REQUIRED"),
        ("regime_specific_behavior", "REGIME_SPECIFIC_LABEL_CONTEXT_REQUIRED"),
    ):
        if not by_name.get(name, {}).get("per_row_values_available"):
            required.append(decision)
    gaps = {row.get("gap_name"): row for row in denominator_gap_board}
    if gaps.get("production_label_count_missing", {}).get("known_right_count") is None:
        required.append("PRODUCTION_LABEL_DENOMINATOR_REQUIRED")
    if not timeout_flat_semantics_aligned:
        required.append("TIMEOUT_FLAT_SEMANTICS_REQUIRED")
    if by_name.get("bad_dates_time_slice_repair_probe"):
        required.append("BAD_DATE_PROBE_EXCLUDED_FROM_TRADABLE_PARITY")
    required.append("NO_LABEL_CHANGE_ALLOWED_YET")
    return required


def classify_alignment_decision(
    *,
    config_mapping_status: dict[str, Any],
    mask_cascade_board: Sequence[dict[str, Any]],
    denominator_gap_board: Sequence[dict[str, Any]],
    sensitivity_board_actionable: bool = False,
    timeout_flat_semantics_aligned: bool = False,
) -> list[str]:
    gaps = {row.get("gap_name"): row for row in denominator_gap_board}
    missing_label_count = gaps.get("production_label_count_missing", {}).get("known_right_count") is None
    required_masks = {
        "setup_quality_mask_sqmask060", "entry_path_quality_epq070_or_071", "stop_pressure_sp045"
    }
    missing_masks = any(
        row.get("mask_name") in required_masks and not row.get("per_row_values_available")
        for row in mask_cascade_board
    )
    denominator_incomplete = missing_label_count or any(
        row.get("missing_count") is None
        for row in denominator_gap_board
        if row.get("gap_name") in {"candles_to_features_gap", "features_to_training_dataset_gap"}
    )
    decisions: list[str] = []
    if denominator_incomplete:
        decisions.append("DENOMINATOR_ALIGNMENT_NOT_COMPLETE")
    if missing_masks:
        decisions.extend(("MASK_CASCADE_NOT_FULLY_RECONSTRUCTED", "NEEDS_PER_ROW_MASK_JOIN"))
    if missing_label_count:
        decisions.append("NEEDS_PRODUCTION_LABEL_ROW_COUNT")
    if (
        denominator_incomplete or missing_masks
        or config_mapping_status.get("status") != "CURRENT_CONFIG_MAPPING_COMPLETE"
        or not timeout_flat_semantics_aligned
    ):
        decisions.append("PRODUCTION_LIKE_RECOMPUTE_NOT_READY")
    if not sensitivity_board_actionable:
        decisions.append("SENSITIVITY_BOARD_REMAINS_NOT_ACTIONABLE")
    decisions.extend(("DO_NOT_CHANGE_LABELS_YET", "DO_NOT_CHANGE_GATES", "DO_NOT_RUN_TRAINING"))
    return decisions


def build_production_denominator_mask_alignment_audit(
    *,
    source_counts: dict[str, Any] | None = None,
    config_id: str | None = None,
    config_payload: dict[str, Any] | None = None,
    mask_evidence: dict[str, Any] | None = None,
    production_reference: dict[str, Any] | None = None,
    recompute_evidence: dict[str, Any] | None = None,
    symbol: str = "SOLUSDT",
    interval: str = "15m",
    start_date: str = "2026-04-01",
    end_date: str = "2026-06-15",
) -> dict[str, Any]:
    counts = dict(source_counts or {})
    production = dict(production_reference or {})
    recompute = dict(recompute_evidence or {})
    mapping_status = build_current_config_mapping_audit(config_id, config_payload)
    mapping = dict(mapping_status.get("mapping") or {})
    cascade = build_mask_cascade_board(
        source_counts=counts, config_mapping=mapping, mask_evidence=mask_evidence
    )
    gaps = build_denominator_gap_board(
        source_counts=counts,
        production_directional_count=production.get("directional_count"),
        recompute_directional_count=recompute.get("directional_count"),
        mask_cascade_board=cascade,
    )
    timeout_aligned = bool(recompute.get("timeout_flat_semantics_aligned", False))
    actionable = bool(recompute.get("sensitivity_board_actionable", False))
    checklist = build_production_like_recompute_prerequisite_checklist(
        config_mapping_status=mapping_status,
        mask_cascade_board=cascade,
        denominator_gap_board=gaps,
        timeout_flat_semantics_aligned=timeout_aligned,
    )
    decisions = classify_alignment_decision(
        config_mapping_status=mapping_status,
        mask_cascade_board=cascade,
        denominator_gap_board=gaps,
        sensitivity_board_actionable=actionable,
        timeout_flat_semantics_aligned=timeout_aligned,
    )
    return {
        "diagnostic_name": "production_denominator_mask_alignment_audit",
        "diagnostic_version": "ml38.10.41",
        "execution_mode": "DIAGNOSTIC_ONLY_NO_TRAINING_NO_DB_WRITES",
        "symbol": symbol,
        "interval": interval,
        "date_range": f"{start_date} -> {end_date}",
        "reference_config_id": config_id,
        "source_counts": counts,
        "mask_cascade_board": cascade,
        "denominator_gap_board": gaps,
        "config_mapping_status": mapping_status,
        "production_parity_prerequisites": checklist,
        "production_like_recompute_prerequisite_checklist": checklist,
        "decision": decisions,
        "ml38_10_41_alignment_decision": decisions,
        "db_writes_performed": False,
        "training_or_runtime_execution": False,
    }


_REGIME_FIELDS = (
    "regime_trend_up", "regime_trend_down", "regime_range",
    "regime_high_volatility", "regime_low_volatility", "regime_unknown",
    "regime_volatility_expanding", "regime_volatility_contracting",
)


def _audit_row_value(row: Any, field: str) -> Any:
    value = _value(row, field)
    if value is not None:
        return value
    features = _value(row, "features_json", {})
    return features.get(field) if isinstance(features, dict) else None


def _materialize_per_row_values(per_row_values: Any) -> list[dict[str, Any]]:
    if per_row_values is None:
        return []
    if isinstance(per_row_values, Sequence) and not isinstance(per_row_values, (str, bytes, dict)):
        return [dict(row) if isinstance(row, dict) else row for row in per_row_values]
    if not isinstance(per_row_values, dict):
        return []
    row_keys = (
        "setup_quality_score", "entry_path_quality_score", "stop_pressure_risk_score",
        "regime_context_eligible", "recovery_guard_decision", "production_selected_label",
    )
    lengths = [len(value) for key, value in per_row_values.items() if key in row_keys and isinstance(value, Sequence)]
    if not lengths:
        return []
    rows: list[dict[str, Any]] = []
    for index in range(max(lengths)):
        row: dict[str, Any] = {"row_index": index}
        for key, values in per_row_values.items():
            if isinstance(values, Sequence) and not isinstance(values, (str, bytes)) and index < len(values):
                row[key] = values[index]
        rows.append(row)
    return rows


def _join_identity(row: Any) -> tuple[Any, ...] | None:
    timestamp = (
        _audit_row_value(row, "candle_open_time")
        or _audit_row_value(row, "open_time")
        or _audit_row_value(row, "timestamp")
    )
    if timestamp is None:
        return None
    return (
        _audit_row_value(row, "symbol"),
        _audit_row_value(row, "interval"),
        timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp),
    )


def discover_mask_sources(
    *,
    feature_rows: Sequence[Any] | None = None,
    production_label_rows: Sequence[Any] | None = None,
    per_row_values: Any = None,
    compact_payload: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Document code/storage evidence and concrete per-row availability without writes."""

    rows = list(feature_rows or []) or _materialize_per_row_values(per_row_values)
    labels = list(production_label_rows or [])
    compact = dict(compact_payload or {})

    def complete(field: str, source_rows: Sequence[Any] = rows) -> bool:
        return bool(source_rows) and all(_audit_row_value(row, field) is not None for row in source_rows)

    regime_complete = bool(rows) and all(
        any(_audit_row_value(row, field) is not None for field in _REGIME_FIELDS)
        or _audit_row_value(row, "market_regime") is not None
        for row in rows
    )
    specs = [
        ("setup_quality_score", "sqmask060", 0.60, True, "READ_ONLY_DB_COLUMN",
         "ml_labels.setup_quality_score / DatasetRow.setup_quality_score", complete("setup_quality_score") or complete("setup_quality_score", labels),
         "app/db/models.py:MlLabels and app/dataset/dataset_builder.py", "P0"),
        ("entry_path_quality_score", "epq070_or_071", 0.70, True, "IN_MEMORY_EVALUATOR_VALUE",
         "profit-aware/training evaluator row payload", complete("entry_path_quality_score"),
         "app/evaluation/profit_aware_evaluator_v2.py and app/training/metrics.py; not persisted on ml_features/ml_labels", "P0"),
        ("stop_pressure_risk_score", "sp045", 0.45, True, "IN_MEMORY_EVALUATOR_VALUE",
         "profit-aware/training evaluator row payload", complete("stop_pressure_risk_score"),
         "app/evaluation/profit_aware_evaluator_v2.py and app/training/metrics.py; not persisted on ml_features/ml_labels", "P0"),
        ("regime_flags_or_context", None, None, True, "FEATURE_JSON_FIELDS",
         "ml_features.features_json.regime_* / market_regime", regime_complete,
         "app/features/feature_models.py defines per-row regime flags", "P0"),
        ("recovery_guard_decision", "rguard", None, True, "IN_MEMORY_EVALUATOR_DECISION",
         "exit mitigation audit/recovery guard decision", complete("recovery_guard_decision") or complete("recovery_guard_eligible"),
         "app/evaluation/profit_aware_evaluator_v2.py computes recovery behavior; no DB column found", "P0"),
        ("production_selected_label", None, None, True, "READ_ONLY_DB_COLUMN",
         "ml_labels.direction_label", complete("production_selected_label") or complete("direction_label", labels),
         "app/db/models.py:MlLabels.direction_label", "P0"),
        ("production_label_row_identity", None, None, True, "COMPOSITE_DB_IDENTITY",
         "symbol+interval+candle_open_time+horizon_candles+label_version", bool(labels) and all(_join_identity(row) is not None for row in labels),
         "MlLabels unique constraint provides timestamp-based row identity", "P0"),
        ("bad_dates_time_slice_probe_metadata", "bad_dates_probe", None, bool(compact),
         "AGGREGATE_ONLY_COMPACT_SOURCE" if compact else "RESEARCH_ONLY_CONFIG_METADATA",
         "fold_time_slice_exit_repair_probe / config token", False,
         "research-only probe metadata is not a production tradable mask", "P1"),
    ]
    searched = [
        "app/features/*", "app/labels/*", "app/db/models.py", "app/db/repositories/*",
        "app/evaluation/profit_aware_evaluator_v2.py", "app/training/metrics.py",
        "app/experiments/*", "run_fv3_cached_tuning.py",
    ]
    return [{
        "mask_name": name,
        "config_token": token,
        "threshold": threshold,
        "searched_locations": searched,
        "source_found": source_found,
        "source_type": source_type,
        "source_path_or_field": path,
        "per_row_values_available": available,
        "join_key_candidates": ["symbol+interval+candle_open_time", "timestamp/open_time", "row_index", "dataset row identity"],
        "evidence": evidence,
        "priority": priority,
    } for name, token, threshold, source_found, source_type, path, available, evidence, priority in specs]


def build_per_row_mask_join_board(
    *,
    feature_rows: Sequence[Any] | None = None,
    production_label_rows: Sequence[Any] | None = None,
    per_row_values: Any = None,
    mask_source_discovery_board: Sequence[dict[str, Any]] | None = None,
    entry_path_threshold: float = 0.70,
) -> list[dict[str, Any]]:
    base_rows = list(feature_rows or []) or _materialize_per_row_values(per_row_values)
    labels = list(production_label_rows or [])
    discovery = list(mask_source_discovery_board or discover_mask_sources(
        feature_rows=base_rows, production_label_rows=labels, per_row_values=per_row_values
    ))
    by_name = {row["mask_name"]: row for row in discovery}
    base_count = len(base_rows)
    label_keys = {_join_identity(row) for row in labels if _join_identity(row) is not None}
    base_keys = [_join_identity(row) for row in base_rows]
    label_joined = sum(key in label_keys for key in base_keys) if label_keys and all(base_keys) else 0
    definitions = [
        ("setup_quality_score", "setup_quality_score", 0.60, lambda value: float(value) >= 0.60),
        ("entry_path_quality_score", "entry_path_quality_score", entry_path_threshold, lambda value: float(value) >= entry_path_threshold),
        ("stop_pressure_risk_score", "stop_pressure_risk_score", 0.45, lambda value: float(value) <= 0.45),
        ("regime_flags_or_context", None, None, None),
        ("recovery_guard_decision", "recovery_guard_decision", None, None),
        ("production_selected_label", None, None, None),
        ("production_label_row_identity", None, None, None),
        ("bad_dates_time_slice_probe_metadata", None, None, None),
    ]
    result: list[dict[str, Any]] = []
    for name, field, threshold, predicate in definitions:
        source = by_name.get(name, {})
        available = bool(source.get("per_row_values_available"))
        values = [_audit_row_value(row, field) for row in base_rows] if field else []
        if name == "regime_flags_or_context":
            values = [
                _audit_row_value(row, "regime_context_eligible")
                if _audit_row_value(row, "regime_context_eligible") is not None
                else _audit_row_value(row, "regime_eligible")
                for row in base_rows
            ]
        elif name == "recovery_guard_decision":
            values = [
                _audit_row_value(row, "recovery_guard_eligible")
                if _audit_row_value(row, "recovery_guard_eligible") is not None
                else _audit_row_value(row, "recovery_guard_decision")
                for row in base_rows
            ]
        joined = base_count if available else 0
        join_key = "existing feature/dataset row fields"
        if name in {"production_selected_label", "production_label_row_identity"}:
            joined = label_joined
            available = available and joined == base_count and base_count > 0
            join_key = "symbol+interval+candle_open_time"
        countable = (
            available and predicate is not None and len(values) == base_count
            and all(value is not None for value in values)
        )
        if countable:
            remaining = sum(bool(predicate(value)) for value in values)
            status = "JOINED_AND_COUNTED"
        elif name == "bad_dates_time_slice_probe_metadata":
            remaining = None
            status = "RESEARCH_ONLY_EXCLUDED" if not source.get("source_type") == "AGGREGATE_ONLY_COMPACT_SOURCE" else "AGGREGATE_ONLY_COMPACT_SOURCE"
        elif available:
            remaining = None
            status = "SOURCE_FOUND_JOIN_NOT_IMPLEMENTED"
        elif source.get("source_type") == "AGGREGATE_ONLY_COMPACT_SOURCE":
            remaining = None
            status = "AGGREGATE_ONLY_COMPACT_SOURCE"
        else:
            remaining = None
            status = "SOURCE_NOT_FOUND"
        result.append({
            "mask_name": name,
            "join_attempted": bool(base_rows),
            "join_key": join_key if base_rows else None,
            "base_row_count": base_count,
            "joined_row_count": joined,
            "missing_join_count": base_count - joined,
            "per_row_values_available": available,
            "threshold_applied": threshold,
            "removed_count": base_count - remaining if remaining is not None else None,
            "remaining_count": remaining,
            "status": status,
            "evidence": source.get("evidence", "MISSING_PER_ROW_SOURCE"),
            "requires_db_write": False,
            "requires_label_builder_change": False,
        })
    return result


def build_mask_cascade_count_board(
    *,
    feature_rows: Sequence[Any] | None = None,
    per_row_values: Any = None,
    production_label_rows: Sequence[Any] | None = None,
    feature_row_count: int | None = None,
    entry_path_threshold: float = 0.70,
) -> list[dict[str, Any]]:
    rows = list(feature_rows or []) or _materialize_per_row_values(per_row_values)
    start_count = len(rows) if rows else feature_row_count
    active: list[Any] | None = list(rows) if rows else None
    board = [{
        "step_order": 1, "mask_name": "feature_rows_start", "threshold": None,
        "removed_count": 0 if start_count is not None else None, "remaining_count": start_count,
        "status": "COUNTED" if start_count is not None else "CANNOT_COUNT_WITHOUT_PER_ROW_VALUES",
    }]
    steps = [
        ("after_setup_quality_score_gte_0_60", "setup_quality_score", ">= 0.60", lambda value: float(value) >= 0.60),
        (f"after_entry_path_quality_score_gte_{entry_path_threshold:.2f}", "entry_path_quality_score", f">= {entry_path_threshold:.2f}", lambda value: float(value) >= entry_path_threshold),
        ("after_stop_pressure_risk_score_lte_0_45", "stop_pressure_risk_score", "<= 0.45", lambda value: float(value) <= 0.45),
        ("after_regime_context", "regime_context_eligible", "production regime context", lambda value: bool(value)),
        ("after_recovery_guard", "recovery_guard_eligible", "production recovery guard", lambda value: bool(value)),
    ]
    for order, (name, field, threshold, predicate) in enumerate(steps, 2):
        before = len(active) if active is not None else None
        if active is not None:
            values = [_audit_row_value(row, field) for row in active]
            if field == "regime_context_eligible" and any(value is None for value in values):
                values = [_audit_row_value(row, "regime_eligible") for row in active]
            if field == "recovery_guard_eligible" and any(value is None for value in values):
                values = [_audit_row_value(row, "recovery_guard_decision") for row in active]
            if any(value is None for value in values):
                active = None
            else:
                active = [row for row, value in zip(active, values) if predicate(value)]
        remaining = len(active) if active is not None else None
        board.append({
            "step_order": order, "mask_name": name, "threshold": threshold,
            "removed_count": before - remaining if before is not None and remaining is not None else None,
            "remaining_count": remaining,
            "status": "COUNTED" if remaining is not None else "CANNOT_COUNT_WITHOUT_PER_ROW_VALUES",
        })
    prior = len(active) if active is not None else None
    board.append({
        "step_order": 7, "mask_name": "after_excluding_research_only_bad_dates_probe", "threshold": None,
        "removed_count": 0 if prior is not None else None, "remaining_count": prior,
        "status": "RESEARCH_ONLY_EXCLUDED" if prior is not None else "CANNOT_COUNT_WITHOUT_PER_ROW_VALUES",
    })
    label_count = len(production_label_rows) if production_label_rows is not None else None
    board.append({
        "step_order": 8, "mask_name": "production_label_row_count", "threshold": None,
        "removed_count": prior - label_count if prior is not None and label_count is not None else None,
        "remaining_count": label_count,
        "status": "COUNTED" if label_count is not None else "CANNOT_COUNT_WITHOUT_PER_ROW_VALUES",
    })
    return board


def classify_production_mask_join_decision(
    per_row_mask_join_board: Sequence[dict[str, Any]],
) -> list[str]:
    by_name = {row.get("mask_name"): row for row in per_row_mask_join_board}
    missing_map = {
        "setup_quality_score": "SETUP_QUALITY_SOURCE_MISSING",
        "entry_path_quality_score": "ENTRY_PATH_QUALITY_SOURCE_MISSING",
        "stop_pressure_risk_score": "STOP_PRESSURE_SOURCE_MISSING",
        "regime_flags_or_context": "REGIME_CONTEXT_SOURCE_MISSING",
        "production_label_row_identity": "PRODUCTION_LABEL_ROW_IDENTITY_MISSING",
    }
    missing = [decision for name, decision in missing_map.items() if not by_name.get(name, {}).get("per_row_values_available")]
    decisions: list[str] = []
    if missing:
        decisions.append("PER_ROW_MASK_JOIN_NOT_COMPLETE")
        decisions.extend(missing)
        if any(row.get("per_row_values_available") for row in per_row_mask_join_board):
            decisions.extend(("PARTIAL_PER_ROW_MASK_JOIN_AVAILABLE", "NEEDS_REMAINING_MASK_SOURCES"))
        decisions.extend((
            "MASK_CASCADE_COUNTS_NOT_READY", "NEEDS_READ_ONLY_MASK_VALUE_EXTRACTOR",
            "PRODUCTION_LIKE_RECOMPUTE_NOT_READY", "SENSITIVITY_BOARD_REMAINS_NOT_ACTIONABLE",
        ))
    decisions.extend(("DO_NOT_CHANGE_LABELS_YET", "DO_NOT_CHANGE_GATES", "DO_NOT_RUN_TRAINING"))
    return list(dict.fromkeys(decisions))


def build_next_extractor_requirements(
    per_row_mask_join_board: Sequence[dict[str, Any]],
) -> list[str]:
    extractors = {
        "setup_quality_score": "extract_setup_quality_score_by_timestamp",
        "entry_path_quality_score": "extract_entry_path_quality_score_by_timestamp",
        "stop_pressure_risk_score": "extract_stop_pressure_risk_score_by_timestamp",
        "regime_flags_or_context": "extract_regime_context_by_timestamp",
        "recovery_guard_decision": "extract_recovery_guard_decision_by_timestamp",
        "production_selected_label": "extract_production_selected_label_by_timestamp",
        "production_label_row_identity": "extract_production_label_row_identity",
    }
    return [
        extractor for name, extractor in extractors.items()
        if not next((row.get("per_row_values_available") for row in per_row_mask_join_board if row.get("mask_name") == name), False)
    ]


def build_per_row_production_mask_join_audit(
    *,
    source_counts: dict[str, Any] | None = None,
    feature_rows: Sequence[Any] | None = None,
    production_label_rows: Sequence[Any] | None = None,
    per_row_values: Any = None,
    compact_payload: dict[str, Any] | None = None,
    config_payload: dict[str, Any] | None = None,
    reference_config_id: str = "lv31_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_bad_dates_exit45_probe",
    symbol: str = "SOLUSDT",
    interval: str = "15m",
    start_date: str = "2026-04-01",
    end_date: str = "2026-06-15",
) -> dict[str, Any]:
    counts = dict(source_counts or {})
    counts.setdefault("split_total_rows", sum(
        int(counts.get(key) or 0) for key in ("candidate_training_rows", "candidate_validation_rows", "candidate_test_rows")
    ) or None)
    counts.setdefault("production_label_row_count", counts.get("label_row_count"))
    threshold = float((config_payload or {}).get("entry_path_quality_min_threshold", 0.70) or 0.70)
    discovery = discover_mask_sources(
        feature_rows=feature_rows, production_label_rows=production_label_rows,
        per_row_values=per_row_values, compact_payload=compact_payload,
    )
    joins = build_per_row_mask_join_board(
        feature_rows=feature_rows, production_label_rows=production_label_rows,
        per_row_values=per_row_values, mask_source_discovery_board=discovery,
        entry_path_threshold=threshold,
    )
    cascade = build_mask_cascade_count_board(
        feature_rows=feature_rows, per_row_values=per_row_values,
        production_label_rows=production_label_rows,
        feature_row_count=counts.get("feature_row_count"), entry_path_threshold=threshold,
    )
    missing = [
        {"mask_name": row["mask_name"], "status": "MISSING_PER_ROW_SOURCE", "missing_fields": [row["mask_name"]]}
        for row in joins
        if row["status"] in {"SOURCE_NOT_FOUND", "JOIN_KEY_MISSING", "AGGREGATE_ONLY_COMPACT_SOURCE"}
        and row["mask_name"] != "bad_dates_time_slice_probe_metadata"
    ]
    decisions = classify_production_mask_join_decision(joins)
    extractors = build_next_extractor_requirements(joins)
    return {
        "diagnostic_name": "per_row_production_mask_join_audit",
        "diagnostic_version": "ml38.10.42",
        "execution_mode": "DIAGNOSTIC_ONLY_NO_TRAINING_NO_DB_WRITES",
        "symbol": symbol,
        "interval": interval,
        "date_range": f"{start_date} -> {end_date}",
        "reference_config_id": reference_config_id,
        "source_counts": counts,
        "mask_source_discovery_board": discovery,
        "per_row_mask_join_board": joins,
        "mask_cascade_count_board": cascade,
        "missing_per_row_sources": missing,
        "next_extractor_requirements": extractors,
        "production_mask_join_decision": decisions,
        "decision": decisions,
        "db_writes_performed": False,
        "training_or_runtime_execution": False,
    }
