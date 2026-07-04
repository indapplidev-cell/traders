from __future__ import annotations

import csv
import json
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
