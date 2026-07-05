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
