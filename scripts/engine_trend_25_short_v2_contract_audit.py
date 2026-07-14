"""ENGINE-TREND-25 audit-only SHORT_DOWN_CONTINUATION_RETEST_V2 replay.

This module changes no application, paper-trading, or execution code.  It
replays the frozen 449 ENGINE-TREND historical candidates against local 15m
OHLCV, separates pre-entry decisions from outcome labelling, and compares
entry/stop/target modes without selecting a winner from validation results.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import create_engine, text

from app.config.settings import get_settings


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "reports/engine_trend/engine_trend_historical_entry_discovery_2025_07_03_2025_12_17/HISTORICAL_ENTRY_DISCOVERY_RESULTS.json"
DEFAULT_ENGINE_24 = ROOT / "reports/engine_trend/engine_trend_24_scoring_redesign_setup_viability_filter/ENGINE_TREND_24_SCORE_V2_RESULTS.csv"
DEFAULT_OUTPUT = ROOT / "reports/engine_trend/engine_trend_25_short_v2_contract_audit"

SHORT_V1 = "SHORT_DOWN_CONTINUATION_RETEST"
SHORT_V2 = "SHORT_DOWN_CONTINUATION_RETEST_V2"
DESIGN_END = datetime(2025, 10, 31, 23, 45, tzinfo=timezone.utc)
STEP = timedelta(minutes=15)
HORIZON = 96
ROUND_TRIP_COST_BPS = 24.0

ENTRY_MODES = ("confirmation_close", "break_confirmation_low", "limit_rejection_body")
STOP_MODES = ("atr_0_15", "atr_0_25", "structural_high_only")
TARGET_MODES = ("previous_low", "nearest_support", "fixed_1_5r", "fixed_2r")
DEFAULT_VARIANT = ("break_confirmation_low", "atr_0_15", "nearest_support")

OUTPUT_FILES = (
    "ENGINE_TREND_25_SHORT_V2_CONTRACT.json",
    "ENGINE_TREND_25_CANDIDATE_REPLAY.csv",
    "ENGINE_TREND_25_VARIANT_METRICS.csv",
    "ENGINE_TREND_25_VALIDATION_COMPARISON.json",
    "ENGINE_TREND_25_SOLUSDT_SHORT_SUBSET.csv",
    "ENGINE_TREND_25_STAGE_AND_FAILURE_COUNTS.csv",
    "ENGINE_TREND_25_LEAKAGE_AUDIT.md",
    "ENGINE_TREND_25_SHORT_V2_AUDIT_REPORT.md",
    "ENGINE_TREND_25_DECISION_RECORD.json",
    "ENGINE_TREND_25_ARTIFACT_MANIFEST.json",
)


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


def finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def stamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def split_name(candidate: dict[str, Any]) -> str:
    return "TRAIN_DESIGN" if stamp(candidate["entry_time"]) <= DESIGN_END else "OUT_OF_TIME_VALIDATION"


def variant_name(entry_mode: str, stop_mode: str, target_mode: str) -> str:
    return f"{entry_mode}__{stop_mode}__{target_mode}"


def default_contract() -> dict[str, Any]:
    return {
        "version": SHORT_V2,
        "audit_only": True,
        "paper_enabled": False,
        "contract_dispositions": {
            SHORT_V1: "ALLOW_FOR_REDESIGN_NOT_PAPER",
            "LONG_UP_CONTINUATION_RETEST": "BLOCK_FROM_PAPER",
            "RANGE_MEAN_REVERSION_CANDIDATE": "BLOCK_FROM_PAPER",
            "SHORT_TREND_ONLY_CONTINUATION_CANDIDATE": "BLOCK_UNTIL_VALIDATION",
        },
        "stages": ["SETUP_READY", "ENTRY_ARMED", "TRADE_CANDIDATE"],
        "required": [
            "source_regime=DOWN", "source_hypothesis=CONFIRMED DOWN_CONTINUATION",
            "LH/LL", "impulse down", "correction/retest", "causal-zone touch",
            "failed reclaim", "bearish confirmation", "no bullish reversal",
            "no confirmed range conflict",
        ],
        "hard_fails": {
            "stop_distance_atr_min": 0.75,
            "volume_ratio_min": 0.7,
            "target_distance_atr_max": 4.0,
            "minimum_rr": 1.5,
            "setup_age_candles_max": 8,
            "unresolved_conflict": True,
            "bullish_reversal": True,
            "exhaustion_conjunction": {
                "impulse_down_atr_gt": 2.5,
                "weak_retest_atr_lt": 0.75,
                "entry_to_lower_bollinger_atr_lte": 0.25,
                "rsi_lt": 35,
            },
        },
        "warnings": {
            "volume_ratio": [0.7, 0.9],
            "target_distance_atr_gt": 3.0,
            "rr_gt": 5.0,
            "stop_distance_atr_gt": 2.0,
            "preferred_rr": [1.5, 3.0],
        },
        "entry_modes": list(ENTRY_MODES),
        "stop_modes": list(STOP_MODES),
        "target_modes": list(TARGET_MODES),
        "locked_default_variant": variant_name(*DEFAULT_VARIANT),
        "execution_assumptions": {
            "timeframe": "15m",
            "horizon_candles_after_fill": HORIZON,
            "round_trip_cost_bps": ROUND_TRIP_COST_BPS,
            "limit_price": "midpoint of bearish rejection candle real body",
            "break_price": "confirmation candle low",
            "structural_invalidation": "retest high",
            "spread_data": "unavailable; ATR buffer variants are audited explicitly",
            "intracandle_order": "unknown; fill-bar or TP+SL ambiguity is excluded from clean metrics",
        },
        "scope_limit": "The 449 frozen candidates were generated by the V1 scanner with planned RR >= 1.5. This audit tests trade conversion/precision, not V2 detector recall.",
    }


def load_candidates(path: Path = DEFAULT_INPUT) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    candidates = payload["candidates"]
    if len(candidates) != 449:
        raise ValueError(f"Expected frozen 449 candidates, got {len(candidates)}")
    return candidates


def load_engine_24_pass_ids(path: Path = DEFAULT_ENGINE_24) -> set[str]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["candidate_id"] for row in csv.DictReader(handle) if row["filter_pass"] == "PASS"}


def load_candles(candidates: list[dict[str, Any]]) -> dict[str, list[Candle]]:
    start = min(stamp(c["context_start"]) for c in candidates) - 4 * STEP
    end = max(stamp(c["entry_time"]) for c in candidates) + (HORIZON + 10) * STEP
    engine = create_engine(get_settings().database_url, pool_pre_ping=True)
    query = text("""SELECT symbol, open_time, open, high, low, close, volume
        FROM public.market_candles
        WHERE interval='15m' AND symbol IN ('BTCUSDT','ETHUSDT','SOLUSDT')
          AND open_time>=:start AND open_time<:end ORDER BY symbol, open_time""")
    result: dict[str, list[Candle]] = {"BTCUSDT": [], "ETHUSDT": [], "SOLUSDT": []}
    with engine.connect() as connection:
        for row in connection.execute(query, {"start": start, "end": end}).mappings():
            result[row["symbol"]].append(Candle(
                row["open_time"].astimezone(timezone.utc),
                *[float(row[key]) for key in ("open", "high", "low", "close", "volume")],
            ))
    for symbol, rows in result.items():
        if not rows or any(b.timestamp - a.timestamp != STEP for a, b in zip(rows, rows[1:])):
            raise RuntimeError(f"Incomplete/irregular candle coverage for {symbol}")
    return result


def pivot_lows_known(candles: list[Candle], confirmation_index: int, wing: int = 2) -> list[tuple[int, float]]:
    """Only pivots confirmed no later than the confirmation close are returned."""
    lows: list[tuple[int, float]] = []
    for i in range(max(wing, confirmation_index - 95), confirmation_index - wing + 1):
        if all(candles[i].low < candles[j].low for j in range(i - wing, i + wing + 1) if j != i):
            lows.append((i, candles[i].low))
    return lows


def candidate_context(candidate: dict[str, Any], candles: list[Candle]) -> dict[str, Any]:
    confirmation_time = stamp(candidate["confirmation_candle_time"])
    index = next((i for i, candle in enumerate(candles) if candle.timestamp == confirmation_time), None)
    if index is None:
        raise RuntimeError(f"Missing confirmation candle for {candidate['candidate_id']}")
    atr = float(candidate["technical_confirmation"]["values"]["atr14"])
    structure = candidate["structure_evidence"]
    level = candidate["range_breakout_evidence"]
    evidence = candidate["candle_evidence"]
    replay = candidate.get("current_engine_trend_replay") or {}
    retest_high = float(structure.get("retest_extreme") or evidence["ohlc"]["high"])
    confirmation = candles[index]
    known_lows = pivot_lows_known(candles, index)
    last_highs = structure.get("confirmed_pivot_highs") or []
    previous_high = float(last_highs[-2]["price"]) if len(last_highs) >= 2 else None
    impulse_low = float(candidate["target_1"])
    prior_highs = [float(item["price"]) for item in last_highs if finite(item.get("price"))]
    impulse_down_atr = (max(prior_highs) - impulse_low) / atr if prior_highs else 0.0
    retest_depth_atr = (retest_high - impulse_low) / atr
    lower = candidate["technical_confirmation"]["values"].get("bollinger_lower")
    entry_to_lower_atr = abs(confirmation.close - lower) / atr if finite(lower) else math.inf
    nearest_supports = [(i, price) for i, price in known_lows if price < confirmation.close]
    strong_supports = [
        (i, price) for i, price in nearest_supports
        if max(candle.high for candle in candles[i + 1 : min(index + 1, i + 13)]) - price >= atr
    ]
    nearest_support = max((price for _, price in strong_supports), default=max((price for _, price in nearest_supports), default=None))
    strong_support = max((price for _, price in strong_supports), default=None)
    most_recent_low = next((price for _, price in reversed(known_lows) if price < confirmation.close), None)
    return {
        "confirmation_index": index,
        "confirmation": confirmation,
        "atr": atr,
        "retest_high": retest_high,
        "causal_zone": float(level["causal_zone"]),
        "nearest_support": nearest_support,
        "strong_support": strong_support,
        "previous_low": most_recent_low,
        "previous_high": previous_high,
        "impulse_down_atr": impulse_down_atr,
        "retest_depth_atr": retest_depth_atr,
        "entry_to_lower_atr": entry_to_lower_atr,
        "replay": replay,
    }


def base_stage(candidate: dict[str, Any], context: dict[str, Any]) -> tuple[str, list[str], list[str]]:
    """Causal setup/arming checks; outcome fields are intentionally inaccessible."""
    failures: list[str] = []
    warnings: list[str] = []
    if candidate.get("setup_type") != SHORT_V1:
        return "BLOCKED_CONTRACT", ["CONTRACT_NOT_ALLOWED_FOR_REDESIGN"], warnings
    replay = context["replay"]
    structure = candidate.get("structure_evidence") or {}
    candle = candidate.get("candle_evidence") or {}
    tech = candidate.get("technical_confirmation", {}).get("values") or {}
    replay_available = bool(replay)
    regime_confirmed = candidate.get("source_regime") == "DOWN" and (not replay_available or replay.get("market_regime") == "DOWN")
    hypothesis_confirmed = (
        replay.get("selected_hypothesis") == "DOWN_CONTINUATION" and replay.get("selected_hypothesis_status") == "CONFIRMED"
        if replay_available
        else candidate.get("source_hypothesis") in {SHORT_V1, "DOWN_CONTINUATION"}
    )
    if not regime_confirmed:
        failures.append("DOWN_REGIME_NOT_CONFIRMED")
    if not hypothesis_confirmed:
        failures.append("DOWN_CONTINUATION_NOT_CONFIRMED")
    if structure.get("classification") != "LH/LL":
        failures.append("LH_LL_NOT_CONFIRMED")
    if not structure.get("impulse_extreme_time"):
        failures.append("IMPULSE_DOWN_MISSING")
    correction_bars = structure.get("correction_bars")
    if not finite(correction_bars) or correction_bars < 2:
        failures.append("CORRECTION_RETEST_MISSING")
    zone_distance = candidate.get("range_breakout_evidence", {}).get("distance_to_zone_atr")
    if not finite(zone_distance) or zone_distance > 0.65:
        failures.append("CAUSAL_ZONE_NOT_TOUCHED")
    confirmation = context["confirmation"]
    if not (confirmation.close < confirmation.open and confirmation.close < context["causal_zone"] and candle.get("close_location", 1) <= 0.32):
        failures.append("BEARISH_FAILED_RECLAIM_NOT_CONFIRMED")
    if replay.get("conflict_level") not in (None, "NONE"):
        failures.append("UNRESOLVED_RANGE_TRAP_CONFLICT")
    if replay.get("indicator_direction") == "BULLISH" or replay.get("agreement_state") == "ALIGNED_BULLISH":
        failures.append("BULLISH_REVERSAL_CONFIRMED")
    volume = tech.get("volume_ratio_20")
    if not finite(volume) or volume < 0.7:
        failures.append("VOLUME_BELOW_0_7")
    elif volume < 0.9:
        warnings.append("VOLUME_0_7_TO_0_9")
    rsi = tech.get("rsi14")
    exhaustion = (
        context["impulse_down_atr"] > 2.5 and context["retest_depth_atr"] < 0.75
        and context["entry_to_lower_atr"] <= 0.25 and finite(rsi) and rsi < 35
    )
    if exhaustion:
        failures.append("LATE_ENTRY_AFTER_EXHAUSTION")
    if failures:
        return "NO_TRADE", failures, warnings
    return "ENTRY_ARMED", failures, warnings


SETUP_FAILURES = {
    "DOWN_REGIME_NOT_CONFIRMED", "DOWN_CONTINUATION_NOT_CONFIRMED", "LH_LL_NOT_CONFIRMED",
    "IMPULSE_DOWN_MISSING", "UNRESOLVED_RANGE_TRAP_CONFLICT", "BULLISH_REVERSAL_CONFIRMED",
}
ARMING_FAILURES = {"CORRECTION_RETEST_MISSING", "CAUSAL_ZONE_NOT_TOUCHED", "LATE_ENTRY_AFTER_EXHAUSTION"}


def reached_stages(failures: Iterable[str], trade_candidate: bool = False) -> list[str]:
    failures = set(failures)
    stages: list[str] = []
    if not failures.intersection(SETUP_FAILURES):
        stages.append("SETUP_READY")
    if stages and not failures.intersection(ARMING_FAILURES):
        stages.append("ENTRY_ARMED")
    if trade_candidate:
        stages.append("TRADE_CANDIDATE")
    return stages


def bullish_reversal(bar: Candle, previous: Candle, atr: float) -> bool:
    body = bar.close - bar.open
    return body >= 0.5 * atr and bar.close > previous.high


def find_entry(entry_mode: str, context: dict[str, Any], candles: list[Candle]) -> dict[str, Any]:
    confirmation: Candle = context["confirmation"]
    index = context["confirmation_index"]
    atr = context["atr"]
    if entry_mode == "confirmation_close":
        return {"status": "FILLED", "price": confirmation.close, "fill_index": index + 1, "age": 0, "fill_on_bar": False}
    limit = (confirmation.open + confirmation.close) / 2.0
    next_bar = candles[index + 1]
    next_reclaims_confirmation_high = next_bar.high > confirmation.high
    for age in range(1, 9):
        bar_index = index + age
        bar = candles[bar_index]
        previous = candles[bar_index - 1]
        if bar.close > context["retest_high"]:
            return {"status": "INVALIDATED", "reason": "CLOSE_ABOVE_RETEST_HIGH", "age": age}
        if context["previous_high"] is not None and bar.high > context["previous_high"]:
            return {"status": "INVALIDATED", "reason": "NEW_HH_BEFORE_ENTRY", "age": age}
        if bullish_reversal(bar, previous, atr):
            return {"status": "INVALIDATED", "reason": "BULLISH_REVERSAL_BEFORE_ENTRY", "age": age}
        if entry_mode == "break_confirmation_low":
            if next_reclaims_confirmation_high:
                return {"status": "INVALIDATED", "reason": "NEXT_CANDLE_RECLAIMED_CONFIRMATION_HIGH", "age": 1}
            if bar.low < confirmation.low:
                return {"status": "FILLED", "price": confirmation.low, "fill_index": bar_index, "age": age, "fill_on_bar": True}
        elif entry_mode == "limit_rejection_body" and bar.high >= limit:
            return {"status": "FILLED", "price": limit, "fill_index": bar_index, "age": age, "fill_on_bar": True}
    return {"status": "STALE", "reason": "SETUP_AGE_OVER_8_CANDLES", "age": 9}


def stop_price(mode: str, context: dict[str, Any]) -> float:
    multiplier = {"atr_0_15": 0.15, "atr_0_25": 0.25, "structural_high_only": 0.0}[mode]
    return context["retest_high"] + multiplier * context["atr"]


def target_price(mode: str, entry: float, stop: float, context: dict[str, Any]) -> float | None:
    risk = stop - entry
    if mode == "previous_low":
        return context["previous_low"]
    if mode == "nearest_support":
        return context["nearest_support"]
    if mode == "fixed_1_5r":
        return entry - 1.5 * risk
    if mode == "fixed_2r":
        return entry - 2.0 * risk
    raise ValueError(mode)


def trade_geometry(entry: float, stop: float, target: float | None, context: dict[str, Any], target_mode: str) -> tuple[list[str], list[str], dict[str, float | None]]:
    failures: list[str] = []
    warnings: list[str] = []
    atr = context["atr"]
    if not finite(target) or not (target < entry < stop):
        return ["INVALID_TRADE_GEOMETRY"], warnings, {"risk": None, "rr": None, "stop_atr": None, "target_atr": None}
    risk = stop - entry
    reward = entry - target
    stop_atr = risk / atr
    target_atr = reward / atr
    rr = reward / risk
    if stop_atr < 0.75:
        failures.append("STOP_DISTANCE_ATR_BELOW_0_75")
    if stop_atr > 2.0:
        warnings.append("STOP_DISTANCE_ATR_ABOVE_2_0")
    if target_atr > 4.0:
        failures.append("TARGET_DISTANCE_ATR_ABOVE_4_0")
    elif target_atr > 3.0:
        warnings.append("TARGET_DISTANCE_ATR_ABOVE_3_0")
    if rr < 1.5:
        failures.append("NO_ROOM_TO_TARGET_RR_BELOW_1_5")
    elif rr > 5.0:
        warnings.append("RR_ABOVE_5_PENALTY")
    elif rr > 3.0:
        warnings.append("RR_ABOVE_PREFERRED_3")
    nearest = context["strong_support"]
    if target_mode.startswith("fixed") and finite(nearest) and nearest > target + 0.15 * atr:
        failures.append("TARGET_BEHIND_FRESH_SUPPORT")
    return failures, warnings, {"risk": risk, "rr": rr, "stop_atr": stop_atr, "target_atr": target_atr}


def simulate_short(candles: list[Candle], entry_info: dict[str, Any], entry: float, stop: float, target: float) -> dict[str, Any]:
    start = entry_info["fill_index"]
    fill_on_bar = entry_info["fill_on_bar"]
    for offset, bar in enumerate(candles[start : start + HORIZON], 1):
        hit_tp = bar.low <= target
        hit_sl = bar.high >= stop
        if offset == 1 and fill_on_bar and (hit_tp or hit_sl):
            return {"label": "AMBIGUOUS_FILL_BAR", "net_return_pct": None, "bars": 1}
        if hit_tp and hit_sl:
            return {"label": "AMBIGUOUS_INTRACANDLE", "net_return_pct": None, "bars": offset}
        if hit_tp:
            gross = (entry - target) / entry * 100.0
            return {"label": "TP_BEFORE_SL", "net_return_pct": gross - ROUND_TRIP_COST_BPS / 100.0, "bars": offset}
        if hit_sl:
            gross = (entry - stop) / entry * 100.0
            return {"label": "SL_BEFORE_TP", "net_return_pct": gross - ROUND_TRIP_COST_BPS / 100.0, "bars": offset}
    if len(candles[start : start + HORIZON]) < HORIZON:
        return {"label": "INSUFFICIENT_FUTURE_DATA", "net_return_pct": None, "bars": None}
    exit_price = candles[start + HORIZON - 1].close
    gross = (entry - exit_price) / entry * 100.0
    return {"label": "NEITHER_EXPIRED", "net_return_pct": gross - ROUND_TRIP_COST_BPS / 100.0, "bars": HORIZON}


def evaluate_variant(candidate: dict[str, Any], candles: list[Candle], entry_mode: str, stop_mode: str, target_mode: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    if candidate.get("setup_type") != SHORT_V1:
        return {
            "candidate_id": candidate["candidate_id"], "symbol": candidate["symbol"],
            "setup_type": candidate["setup_type"], "split": split_name(candidate),
            "entry_mode": entry_mode, "stop_mode": stop_mode, "target_mode": target_mode,
            "variant": variant_name(entry_mode, stop_mode, target_mode),
            "stage": "BLOCKED_CONTRACT", "failures": ["CONTRACT_NOT_ALLOWED_FOR_REDESIGN"],
            "stage_trace": [], "warnings": [], "entry": None, "stop": None, "target": None, "rr": None,
            "stop_atr": None, "target_atr": None, "entry_age": None,
            "label": "NO_TRADE", "net_return_pct": None,
        }
    context = context or candidate_context(candidate, candles)
    stage, failures, warnings = base_stage(candidate, context)
    base = {
        "candidate_id": candidate["candidate_id"], "symbol": candidate["symbol"],
        "setup_type": candidate["setup_type"], "split": split_name(candidate),
        "entry_mode": entry_mode, "stop_mode": stop_mode, "target_mode": target_mode,
        "variant": variant_name(entry_mode, stop_mode, target_mode),
        "stage": stage, "failures": list(failures), "warnings": list(warnings),
        "stage_trace": reached_stages(failures),
        "entry": None, "stop": None, "target": None, "rr": None,
        "stop_atr": None, "target_atr": None, "entry_age": None,
        "label": "NO_TRADE", "net_return_pct": None,
    }
    if stage != "ENTRY_ARMED":
        return base
    entry_info = find_entry(entry_mode, context, candles)
    base["entry_age"] = entry_info["age"]
    if entry_info["status"] != "FILLED":
        base["stage"] = "NO_TRADE"
        base["failures"].append(entry_info["reason"])
        return base
    entry = float(entry_info["price"])
    stop = stop_price(stop_mode, context)
    target = target_price(target_mode, entry, stop, context)
    geometry_failures, geometry_warnings, geometry = trade_geometry(entry, stop, target, context, target_mode)
    base.update({"entry": entry, "stop": stop, "target": target, "rr": geometry["rr"], "stop_atr": geometry["stop_atr"], "target_atr": geometry["target_atr"]})
    base["failures"].extend(geometry_failures)
    base["warnings"].extend(geometry_warnings)
    if geometry_failures:
        base["stage"] = "NO_TRADE"
        return base
    base["stage"] = "TRADE_CANDIDATE"
    base["stage_trace"] = reached_stages(base["failures"], trade_candidate=True)
    outcome = simulate_short(candles, entry_info, entry, stop, float(target))
    base["label"] = outcome["label"]
    base["net_return_pct"] = outcome["net_return_pct"]
    base["bars_to_outcome"] = outcome["bars"]
    return base


def performance(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(rows)
    trades = [row for row in rows if row["stage"] == "TRADE_CANDIDATE"]
    clean = [row for row in trades if row["label"] in {"TP_BEFORE_SL", "SL_BEFORE_TP"}]
    returns = [float(row["net_return_pct"]) for row in clean]
    gains = sum(value for value in returns if value > 0)
    losses = -sum(value for value in returns if value < 0)
    return {
        "universe": len(rows), "trade_candidates": len(trades), "clean_trades": len(clean),
        "wins": sum(row["label"] == "TP_BEFORE_SL" for row in clean),
        "losses": sum(row["label"] == "SL_BEFORE_TP" for row in clean),
        "ambiguous": sum(row["label"].startswith("AMBIGUOUS") for row in trades),
        "expired": sum(row["label"] == "NEITHER_EXPIRED" for row in trades),
        "winrate_pct": 100 * sum(row["label"] == "TP_BEFORE_SL" for row in clean) / len(clean) if clean else None,
        "profit_factor": gains / losses if losses else None,
        "expectancy_pct": sum(returns) / len(returns) if returns else None,
        "total_net_return_pct_naive": sum(returns),
    }


def old_short_metrics(candidates: list[dict[str, Any]], pass_ids: set[str], split: str | None = None) -> dict[str, Any]:
    selected = [c for c in candidates if c["setup_type"] == SHORT_V1 and (split is None or split_name(c) == split)]
    all_rows = [{"stage": "TRADE_CANDIDATE", "label": c["outcome"]["label_status"], "net_return_pct": c["outcome"]["net_return_pct"]} for c in selected]
    pass_rows = [{"stage": "TRADE_CANDIDATE", "label": c["outcome"]["label_status"], "net_return_pct": c["outcome"]["net_return_pct"]} for c in selected if c["candidate_id"] in pass_ids]
    return {"old_short_all": performance(all_rows), "old_engine_24_pass_short": performance(pass_rows)}


def csv_value(value: Any) -> Any:
    if isinstance(value, list):
        return "|".join(value)
    return value


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    fields = fields or sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: csv_value(row.get(field)) for field in fields} for row in rows)


def metric_row(variant: str, split: str, metrics: dict[str, Any], disposition: str = "AUDIT_ONLY") -> dict[str, Any]:
    return {"variant": variant, "split": split, "disposition": disposition, **metrics}


def fmt(value: Any, digits: int = 4) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}" if isinstance(value, float) else str(value)


def run(input_path: Path = DEFAULT_INPUT, engine_24_path: Path = DEFAULT_ENGINE_24, output_dir: Path = DEFAULT_OUTPUT, candles_by_symbol: dict[str, list[Candle]] | None = None) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    candidates = load_candidates(input_path)
    pass_ids = load_engine_24_pass_ids(engine_24_path)
    candles_by_symbol = candles_by_symbol or load_candles(candidates)
    all_rows: list[dict[str, Any]] = []
    for candidate in candidates:
        candles = candles_by_symbol[candidate["symbol"]]
        context = candidate_context(candidate, candles) if candidate["setup_type"] == SHORT_V1 else None
        for entry_mode in ENTRY_MODES:
            for stop_mode in STOP_MODES:
                for target_mode in TARGET_MODES:
                    all_rows.append(evaluate_variant(candidate, candles, entry_mode, stop_mode, target_mode, context))

    default_name = variant_name(*DEFAULT_VARIANT)
    default_rows = [row for row in all_rows if row["variant"] == default_name]
    variant_metrics: list[dict[str, Any]] = []
    by_variant: dict[str, dict[str, dict[str, Any]]] = {}
    for name in sorted({row["variant"] for row in all_rows}):
        by_variant[name] = {}
        for split in ("TRAIN_DESIGN", "OUT_OF_TIME_VALIDATION", "FULL_DIAGNOSTIC"):
            subset = [row for row in all_rows if row["variant"] == name and (split == "FULL_DIAGNOSTIC" or row["split"] == split)]
            metrics = performance(subset)
            by_variant[name][split] = metrics
            variant_metrics.append(metric_row(name, split, metrics))

    baseline_design = by_variant[default_name]["TRAIN_DESIGN"]
    baseline_validation = by_variant[default_name]["OUT_OF_TIME_VALIDATION"]
    rejected_in_sample_only: set[str] = set()
    for name in by_variant:
        if name == default_name:
            continue
        design = by_variant[name]["TRAIN_DESIGN"]
        validation = by_variant[name]["OUT_OF_TIME_VALIDATION"]
        design_value = design["expectancy_pct"] if design["expectancy_pct"] is not None else -math.inf
        baseline_design_value = baseline_design["expectancy_pct"] if baseline_design["expectancy_pct"] is not None else -math.inf
        validation_value = validation["expectancy_pct"] if validation["expectancy_pct"] is not None else -math.inf
        baseline_validation_value = baseline_validation["expectancy_pct"] if baseline_validation["expectancy_pct"] is not None else -math.inf
        design_uplift = design_value > baseline_design_value
        validation_uplift = validation_value > baseline_validation_value
        if design_uplift and not validation_uplift:
            rejected_in_sample_only.add(name)
    for row in variant_metrics:
        if row["variant"] in rejected_in_sample_only:
            row["disposition"] = "REJECT_IN_SAMPLE_ONLY_UPLIFT"

    mode_comparison = {
        "entry_modes_at_atr_0_15_previous_low": {
            mode: by_variant[variant_name(mode, "atr_0_15", "previous_low")]
            for mode in ENTRY_MODES
        },
        "target_modes_at_break_atr_0_15": {
            mode: by_variant[variant_name("break_confirmation_low", "atr_0_15", mode)]
            for mode in TARGET_MODES
        },
        "stop_modes_at_break_previous_low": {
            mode: by_variant[variant_name("break_confirmation_low", mode, "previous_low")]
            for mode in STOP_MODES
        },
    }

    old_comparison = {
        "full": old_short_metrics(candidates, pass_ids),
        "validation": old_short_metrics(candidates, pass_ids, "OUT_OF_TIME_VALIDATION"),
        "short_v2_locked_default_full": performance(default_rows),
        "short_v2_locked_default_validation": performance([row for row in default_rows if row["split"] == "OUT_OF_TIME_VALIDATION"]),
    }
    sol_rows = [row for row in default_rows if row["symbol"] == "SOLUSDT" and row["setup_type"] == SHORT_V1]
    failure_counts = Counter(reason for row in default_rows for reason in row["failures"])
    stage_counts = Counter(row["stage"] for row in default_rows)
    reached_counts = Counter(stage for row in default_rows for stage in row["stage_trace"])
    count_rows = ([{"kind": "STAGE", "code": key, "count": value} for key, value in stage_counts.most_common()] +
                  [{"kind": "STAGE_REACHED", "code": key, "count": value} for key, value in reached_counts.items()] +
                  [{"kind": "HARD_FAIL", "code": key, "count": value} for key, value in failure_counts.most_common()])

    contract = default_contract()
    (output_dir / OUTPUT_FILES[0]).write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    candidate_fields = ["candidate_id", "symbol", "setup_type", "split", "stage", "stage_trace", "entry_mode", "stop_mode", "target_mode", "entry", "stop", "target", "rr", "stop_atr", "target_atr", "entry_age", "label", "net_return_pct", "failures", "warnings"]
    write_csv(output_dir / OUTPUT_FILES[1], default_rows, candidate_fields)
    write_csv(output_dir / OUTPUT_FILES[2], variant_metrics)
    comparison_payload = {"locked_default_variant": default_name, "comparison": old_comparison, "mode_comparison": mode_comparison, "variant_metrics": by_variant, "rejected_in_sample_only_variants": sorted(rejected_in_sample_only)}
    (output_dir / OUTPUT_FILES[3]).write_text(json.dumps(comparison_payload, indent=2) + "\n", encoding="utf-8")
    write_csv(output_dir / OUTPUT_FILES[4], sol_rows, candidate_fields)
    write_csv(output_dir / OUTPUT_FILES[5], count_rows, ["kind", "code", "count"])

    leakage_md = f"""# ENGINE-TREND-25 Leakage Audit

- Frozen universe: **{len(candidates)}** candidates; no V2 candidate discovery or recall claim.
- Split is unchanged: design through 2025-10-31; validation begins 2025-11-01.
- Setup, arming, entry, stop, and target decisions use candles no later than the relevant entry/fill decision.
- Outcomes are evaluated only after the entry decision. Outcome/MFE/MAE fields are never read by `base_stage`, `find_entry`, `trade_geometry`, or `evaluate_variant`.
- The locked default variant was declared before variant metrics were computed: `{default_name}`.
- Legacy provenance is explicit: discovery attached current-engine replay to top-10 only. For other frozen SHORT candidates, `SHORT_DOWN_CONTINUATION_RETEST` is normalized to the generator's DOWN-continuation hypothesis; any available replay must explicitly confirm DOWN continuation.
- Variant comparisons are diagnostics. A full-sample row is marked `REJECT_IN_SAMPLE_ONLY_UPLIFT` when it improves design expectancy but not validation expectancy.
- 15m OHLC does not identify intrabar order. Ambiguous fill/exit bars and simultaneous TP/SL bars are excluded from clean PF and expectancy.
- Limitation: V1 generated the universe with RR >= 1.5, so this audit cannot measure missed SHORT_V2 setups.

Status: **PASS WITH DECLARED SCOPE LIMITATION**.
"""
    (output_dir / OUTPUT_FILES[6]).write_text(leakage_md, encoding="utf-8")

    full_default = old_comparison["short_v2_locked_default_full"]
    validation_default = old_comparison["short_v2_locked_default_validation"]
    sol_validation = performance([row for row in sol_rows if row["split"] == "OUT_OF_TIME_VALIDATION"])
    status = "ENGINE_TREND_25_SHORT_V2_AUDITED_NOT_READY_FOR_PAPER"
    report = f"""# ENGINE-TREND-25 SHORT_V2 Contract Audit

## Decision

**{status}**. Runtime and paper contracts remain unchanged. Only `{SHORT_V1}` is retained for redesign research; LONG continuation and range mean reversion remain blocked from paper, and trend-only SHORT remains blocked until separate validation.

## Locked default (not selected from results)

`{default_name}`: break below confirmation low, structural retest high + 0.15 ATR stop, nearest pre-entry confirmed support target.

- full: universe={full_default['universe']}, trade candidates={full_default['trade_candidates']}, clean={full_default['clean_trades']}, PF={fmt(full_default['profit_factor'])}, expectancy={fmt(full_default['expectancy_pct'])}%
- validation: trade candidates={validation_default['trade_candidates']}, clean={validation_default['clean_trades']}, PF={fmt(validation_default['profit_factor'])}, expectancy={fmt(validation_default['expectancy_pct'])}%
- SOLUSDT validation: trade candidates={sol_validation['trade_candidates']}, clean={sol_validation['clean_trades']}, PF={fmt(sol_validation['profit_factor'])}, expectancy={fmt(sol_validation['expectancy_pct'])}%

## Old SHORT reference

- old validation all SHORT: N={old_comparison['validation']['old_short_all']['clean_trades']}, PF={fmt(old_comparison['validation']['old_short_all']['profit_factor'])}, expectancy={fmt(old_comparison['validation']['old_short_all']['expectancy_pct'])}%
- ENGINE-TREND-24 validation pocket: N={old_comparison['validation']['old_engine_24_pass_short']['clean_trades']}, PF={fmt(old_comparison['validation']['old_engine_24_pass_short']['profit_factor'])}, expectancy={fmt(old_comparison['validation']['old_engine_24_pass_short']['expectancy_pct'])}%

## Interpretation

The three-stage state machine is now explicit in the audit: setup context, armed causal-zone retest, then a separately filled trade candidate. Too-tight structural stops are rejected rather than rewarded; volume below 0.7, stale/invalidation events, exhaustion conjunctions, target distance above 4 ATR, unresolved conflicts, bullish reversal, and RR below 1.5 are hard failures. Volume 0.7–0.9, targets above 3 ATR, stops above 2 ATR, and RR above 3/5 are warnings/penalties.

All 36 entry/stop/target variants are recorded for design and validation. They are not ranked into a production choice. This is precision analysis over the 449 V1-frozen candidates, not a new detector backtest; a fresh causal scan is required before any paper decision.

The JSON comparison contains controlled slices for entry modes (fixed 0.15 ATR + previous-low target), target modes (break entry + 0.15 ATR), and stop modes (break entry + previous-low target). Variants with design-only expectancy uplift are explicitly marked `REJECT_IN_SAMPLE_ONLY_UPLIFT`.
"""
    (output_dir / OUTPUT_FILES[7]).write_text(report, encoding="utf-8")
    decision = {
        "final_status": status, "paper_enabled": False, "profitable_system_validated": False,
        "runtime_changed": False, "trading_runtime_changed": False, "setup_runtime_changed": False,
        "processed_candidates": len(candidates), "locked_default_variant": default_name,
        "validation_metrics": validation_default, "solusdt_validation_metrics": sol_validation,
        "next_stage": "fresh SHORT_V2 causal candidate scan with untouched forward validation",
    }
    (output_dir / OUTPUT_FILES[8]).write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")

    artifacts = []
    for name in OUTPUT_FILES[:-1]:
        payload = (output_dir / name).read_bytes()
        artifacts.append({"file": name, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()})
    manifest = {"created_files": list(OUTPUT_FILES), "artifacts": artifacts, "manifest_self_excluded_from_hashes": True}
    manifest_path = output_dir / OUTPUT_FILES[-1]
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {"decision": decision, "comparison": old_comparison, "processed": len(candidates), "rows": len(all_rows), "default_rows": default_rows, "variant_metrics": variant_metrics}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--engine-24", type=Path, default=DEFAULT_ENGINE_24)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run(args.input, args.engine_24, args.output)
    print(json.dumps({"status": result["decision"]["final_status"], "processed": result["processed"], "variant_rows": result["rows"]}, indent=2))


if __name__ == "__main__":
    main()
