"""ENGINE-TREND-26 fresh SHORT_V2 scan on untouched forward candles.

The V1 candidate universe is never loaded. Rules and the common-symbol forward
window are constants. Candidate plans are generated and hashed before a
separate outcome-label phase receives post-fill candles.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import create_engine, text

from app.config.settings import get_settings
from app.market_reader.engine_trend.engine import normalize_candles, run_engine_trend
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from engine_trend_historical_entry_discovery_2025_07_03_2025_12_17 import (  # noqa: E402
    Candle,
    candle_features,
    indicators,
    pivots,
    technical_snapshot,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "reports/engine_trend/engine_trend_26_fresh_short_v2_forward_scan"
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
INTERVAL = "15m"
STEP = timedelta(minutes=15)
FORWARD_START = datetime(2025, 12, 18, 0, 0, tzinfo=timezone.utc)
COMMON_LAST_CANDLE = datetime(2026, 6, 15, 20, 0, tzinfo=timezone.utc)
SCAN_END = COMMON_LAST_CANDLE - 96 * STEP
LOAD_START = FORWARD_START - 240 * STEP
LOAD_END_EXCLUSIVE = COMMON_LAST_CANDLE + STEP
HORIZON = 96
ROUND_TRIP_COST_BPS = 24.0
COOLDOWN_BARS = 12

OUTPUT_FILES = (
    "ENGINE_TREND_26_LOCKED_SCANNER_CONTRACT.json",
    "ENGINE_TREND_26_DATA_COVERAGE.json",
    "ENGINE_TREND_26_PRE_ENTRY_PLANS.json",
    "ENGINE_TREND_26_CANDIDATES.csv",
    "ENGINE_TREND_26_OUTCOMES.csv",
    "ENGINE_TREND_26_SCAN_FUNNEL.csv",
    "ENGINE_TREND_26_FORWARD_METRICS.json",
    "ENGINE_TREND_26_LEAKAGE_AUDIT.md",
    "ENGINE_TREND_26_FRESH_SCAN_REPORT.md",
    "ENGINE_TREND_26_DECISION_RECORD.json",
    "ENGINE_TREND_26_ARTIFACT_MANIFEST.json",
)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def locked_contract() -> dict[str, Any]:
    return {
        "version": "SHORT_DOWN_CONTINUATION_RETEST_V2/FRESH_SCAN_V1",
        "locked_before_outcome_read": True,
        "audit_only": True,
        "paper_enabled": False,
        "universe": "all 15m decision points; V1 449-candidate artifact is not loaded",
        "symbols": list(SYMBOLS),
        "forward_window": {
            "start": iso(FORWARD_START), "last_confirmation": iso(SCAN_END),
            "common_last_outcome_candle": iso(COMMON_LAST_CANDLE), "horizon_bars": HORIZON,
        },
        "source_hypothesis": {
            "market_regime": "DOWN", "selected_hypothesis": "DOWN_CONTINUATION",
            "selected_hypothesis_status": "CONFIRMED", "conflict_level": "NONE",
            "source": "unchanged current ENGINE-TREND replay on 240 closed candles",
        },
        "structure": {
            "classification": "LH/LL", "ema20_below_ema50": True,
            "impulse_search_bars": 8, "correction_bars": [2, 8],
            "retest_depth_atr": [0.35, 2.0], "causal_zone_max_distance_atr": 0.65,
            "causal_zones": ["EMA20", "VWAP96", "broken confirmed support", "latest confirmed resistance"],
        },
        "trigger": {
            "bearish_body": True, "close_below_zone": True, "close_location_max": 0.32,
            "body_atr_min": 0.18, "rejection_upper_wick_min_or_previous_low_break": 0.22,
        },
        "entry": {
            "mode": "break_confirmation_low", "max_age_bars": 8,
            "next_candle_must_not_reclaim_confirmation_high": True,
        },
        "stop": {"anchor": "retest_high", "buffer_atr": 0.15, "minimum_distance_atr": 0.75},
        "target": {
            "mode": "nearest pre-entry confirmed support; fallback most-recent confirmed swing low",
            "strong_support_min_observed_bounce_atr": 1.0,
            "preferred_distance_atr_max": 3.0, "hard_distance_atr_max": 4.0,
        },
        "risk": {"minimum_rr": 1.5, "preferred_rr": [1.5, 3.0], "rr_above_5_penalty": True},
        "volume": {
            "hard_min": 0.7, "warning_below": 0.9,
            "weak_volume_requires": ["zone_distance<=0.3ATR", "close_location<=0.25", "close_inside_lower_bollinger"],
        },
        "exhaustion_hard_fail_conjunction": {
            "impulse_down_atr_gt": 2.5, "retest_depth_atr_lt": 0.75,
            "distance_to_lower_bollinger_atr_lte": 0.25, "rsi_lt": 35,
        },
        "setup_invalidation": [
            "close above retest high", "new HH", "bullish reversal", "next candle reclaims confirmation high",
            "setup age over 8 candles",
        ],
        "deduplication": f"first causal trade candidate wins; {COOLDOWN_BARS}-bar symbol cooldown after fill",
        "costs": {"round_trip_bps": ROUND_TRIP_COST_BPS},
        "acceptance_gate": {
            "clean_trades_min": 30, "profit_factor_min": 1.15, "expectancy_gt": 0,
            "max_drawdown_pct_max": 10, "non_negative_months_min": 4,
            "positive_symbols_min": 2, "robust_after_top_two_winners_removed": True,
        },
    }


def load_rows() -> dict[str, list[Candle]]:
    engine = create_engine(get_settings().database_url, pool_pre_ping=True)
    query = text("""SELECT symbol, open_time, close_time, open, high, low, close, volume
        FROM public.market_candles
        WHERE interval=:interval AND symbol IN ('BTCUSDT','ETHUSDT','SOLUSDT')
          AND open_time>=:start AND open_time<:end
        ORDER BY symbol, open_time""")
    result = {symbol: [] for symbol in SYMBOLS}
    with engine.connect() as connection:
        for row in connection.execute(query, {"interval": INTERVAL, "start": LOAD_START, "end": LOAD_END_EXCLUSIVE}).mappings():
            result[row["symbol"]].append(Candle(
                row["open_time"].astimezone(timezone.utc), row["close_time"].astimezone(timezone.utc),
                *[float(row[key]) for key in ("open", "high", "low", "close", "volume")],
            ))
    return result


def data_coverage(rows_by_symbol: dict[str, list[Candle]]) -> list[dict[str, Any]]:
    expected = int((LOAD_END_EXCLUSIVE - LOAD_START) / STEP)
    rows: list[dict[str, Any]] = []
    for symbol in SYMBOLS:
        candles = rows_by_symbol[symbol]
        times = [c.timestamp for c in candles]
        irregular = sum(b - a != STEP for a, b in zip(times, times[1:]))
        duplicate = len(times) - len(set(times))
        ohlc_errors = sum(c.low > min(c.open, c.close) or c.high < max(c.open, c.close) or c.high < c.low for c in candles)
        non_finite = sum(not all(math.isfinite(x) for x in (c.open, c.high, c.low, c.close, c.volume)) for c in candles)
        row = {
            "symbol": symbol, "expected": expected, "actual": len(candles),
            "first": iso(candles[0].timestamp) if candles else None,
            "last": iso(candles[-1].timestamp) if candles else None,
            "irregular": irregular, "duplicates": duplicate, "ohlc_errors": ohlc_errors,
            "non_finite": non_finite,
        }
        row["status"] = "PASS" if len(candles) == expected and not any((irregular, duplicate, ohlc_errors, non_finite)) else "FAIL"
        rows.append(row)
    return rows


def engine_hypothesis(symbol: str, candles: list[Candle], index: int) -> dict[str, Any]:
    prefix = candles[index - 239 : index + 1]
    normalized = normalize_candles([{
        "timestamp": c.timestamp, "open": c.open, "high": c.high,
        "low": c.low, "close": c.close, "volume": c.volume,
    } for c in prefix])
    composer = run_engine_trend(symbol, INTERVAL, normalized).to_dict()["composer_output"]
    trace = composer["decision_trace"]
    matrix = trace.get("matrix_summary") or {}
    selected = trace.get("selected_hypothesis") or {}
    return {
        "market_regime": composer["result"].get("market_regime"),
        "selected_hypothesis": selected.get("hypothesis_type"),
        "selected_hypothesis_status": selected.get("status"),
        "conflict_level": matrix.get("conflict_level"),
        "data_quality_status": trace.get("data_quality_status"),
        "indicator_direction": matrix.get("indicator_direction"),
        "agreement_state": matrix.get("agreement_state"),
        "reason_codes": trace.get("reason_codes") or [],
    }


def confirmed_down_hypothesis(value: dict[str, Any]) -> bool:
    return (
        value["market_regime"] == "DOWN"
        and value["selected_hypothesis"] == "DOWN_CONTINUATION"
        and value["selected_hypothesis_status"] == "CONFIRMED"
        and value["conflict_level"] in (None, "NONE")
        and value["data_quality_status"] == "PASS"
        and value["indicator_direction"] != "BULLISH"
        and value["agreement_state"] != "ALIGNED_BULLISH"
    )


def nearest_target(candles: list[Candle], confirmation_index: int, lows: list[tuple[int, float]], entry: float, atr: float) -> tuple[float | None, str | None]:
    recent = [(index, price) for index, price in lows if index >= confirmation_index - 95 and price < entry]
    strong = [
        (index, price) for index, price in recent
        if max(c.high for c in candles[index + 1 : min(confirmation_index + 1, index + 13)]) - price >= atr
    ]
    if strong:
        return max(price for _, price in strong), "NEAREST_STRONG_CONFIRMED_SUPPORT"
    if recent:
        return next(price for _, price in reversed(recent)), "MOST_RECENT_CONFIRMED_SWING_LOW_FALLBACK"
    return None, None


def bullish_reversal(current: Candle, previous: Candle, atr: float) -> bool:
    return current.close - current.open >= 0.5 * atr and current.close > previous.high


def find_break_entry(candles: list[Candle], index: int, confirmation: Candle, retest_high: float, previous_high: float, atr: float) -> dict[str, Any]:
    next_bar = candles[index + 1]
    if next_bar.high > confirmation.high:
        return {"status": "INVALIDATED", "reason": "NEXT_CANDLE_RECLAIMED_CONFIRMATION_HIGH", "age": 1}
    for age in range(1, 9):
        bar_index = index + age
        bar = candles[bar_index]
        if bar.close > retest_high:
            return {"status": "INVALIDATED", "reason": "CLOSE_ABOVE_RETEST_HIGH", "age": age}
        if bar.high > previous_high:
            return {"status": "INVALIDATED", "reason": "NEW_HH_BEFORE_ENTRY", "age": age}
        if bullish_reversal(bar, candles[bar_index - 1], atr):
            return {"status": "INVALIDATED", "reason": "BULLISH_REVERSAL_BEFORE_ENTRY", "age": age}
        if bar.low < confirmation.low:
            return {
                "status": "FILLED", "price": confirmation.low, "age": age,
                "fill_index": bar_index, "fill_time": iso(bar.timestamp),
            }
    return {"status": "STALE", "reason": "SETUP_AGE_OVER_8_CANDLES", "age": 9}


def scan_symbol(symbol: str, candles: list[Candle]) -> tuple[list[dict[str, Any]], Counter[str]]:
    ind = indicators(candles)
    plans: list[dict[str, Any]] = []
    funnel: Counter[str] = Counter()
    cooldown_until = -1
    for index in range(240, len(candles) - HORIZON):
        current = candles[index]
        if not FORWARD_START <= current.timestamp <= SCAN_END:
            continue
        funnel["DECISION_POINTS"] += 1
        if index <= cooldown_until:
            funnel["COOLDOWN_SKIPPED"] += 1
            continue
        atr = ind["atr"][index]
        if not finite(atr) or atr <= 0:
            funnel["ATR_UNAVAILABLE"] += 1
            continue
        atr = float(atr)
        highs, lows = pivots(candles, index)
        if len(highs) < 2 or len(lows) < 2:
            funnel["PIVOTS_UNAVAILABLE"] += 1
            continue
        last_highs, last_lows = highs[-2:], lows[-2:]
        if not (last_highs[-1][1] < last_highs[-2][1] and last_lows[-1][1] < last_lows[-2][1]):
            funnel["NOT_LH_LL"] += 1
            continue
        ema20, ema50, vwap = ind["ema20"][index], ind["ema50"][index], ind["vwap96"][index]
        if not finite(ema20) or not finite(ema50) or ema20 >= ema50:
            funnel["NOT_DOWN_EMA_ALIGNMENT"] += 1
            continue
        funnel["STRUCTURAL_DOWN_CONTEXT"] += 1
        recent = candles[index - 8 : index]
        impulse_index = index - 8 + min(range(8), key=lambda offset: recent[offset].low)
        correction_bars = index - impulse_index
        if correction_bars < 2 or correction_bars > 8:
            funnel["CORRECTION_BARS_OUTSIDE_2_8"] += 1
            continue
        impulse_low = candles[impulse_index].low
        retest_high = max(c.high for c in candles[impulse_index + 1 : index + 1])
        zones = [
            ("EMA20", ema20), ("VWAP96", vwap),
            ("BROKEN_CONFIRMED_SUPPORT", last_lows[-2][1]),
            ("LATEST_CONFIRMED_RESISTANCE", last_highs[-1][1]),
        ]
        zones = [(name, float(price)) for name, price in zones if finite(price)]
        zone_kind, zone = min(zones, key=lambda item: abs(retest_high - item[1]))
        zone_distance_atr = abs(retest_high - zone) / atr
        retest_depth_atr = (retest_high - impulse_low) / atr
        if zone_distance_atr > 0.65:
            funnel["CAUSAL_ZONE_NOT_TOUCHED"] += 1
            continue
        if not 0.35 <= retest_depth_atr <= 2.0:
            funnel["RETEST_DEPTH_OUTSIDE_0_35_2_0"] += 1
            continue
        funnel["ENTRY_ARMED_PREFILTER"] += 1
        candle = candle_features(current, atr)
        bearish_trigger = (
            current.close < current.open and current.close < zone and candle["close_location"] <= 0.32
            and candle["body_atr"] >= 0.18
            and (current.close < candles[index - 1].low or candle["upper_wick_fraction"] >= 0.22)
        )
        if not bearish_trigger:
            funnel["BEARISH_TRIGGER_MISSING"] += 1
            continue
        funnel["BEARISH_TRIGGER_PREFILTER"] += 1
        hypothesis = engine_hypothesis(symbol, candles, index)
        if not confirmed_down_hypothesis(hypothesis):
            funnel["ENGINE_DOWN_CONTINUATION_NOT_CONFIRMED"] += 1
            continue
        funnel["SETUP_READY_CONFIRMED"] += 1
        target, target_kind = nearest_target(candles, index, lows, current.low, atr)
        if not finite(target):
            funnel["REACHABLE_TARGET_MISSING"] += 1
            continue
        tech = technical_snapshot(ind, candles, index)
        volume = tech["volume_ratio_20"]
        if not finite(volume) or volume < 0.7:
            funnel["VOLUME_BELOW_0_7"] += 1
            continue
        warnings: list[str] = []
        lower = tech.get("bollinger_lower")
        if volume < 0.9:
            if not (zone_distance_atr <= 0.3 and candle["close_location"] <= 0.25 and finite(lower) and current.close >= lower):
                funnel["WEAK_VOLUME_WITHOUT_STRONG_STRUCTURE"] += 1
                continue
            warnings.append("VOLUME_0_7_TO_0_9_STRONG_STRUCTURE_EXCEPTION")
        prior_high = max(price for _, price in last_highs)
        impulse_down_atr = (prior_high - impulse_low) / atr
        lower_distance_atr = abs(current.close - lower) / atr if finite(lower) else math.inf
        rsi = tech.get("rsi14")
        if impulse_down_atr > 2.5 and retest_depth_atr < 0.75 and lower_distance_atr <= 0.25 and finite(rsi) and rsi < 35:
            funnel["LATE_ENTRY_AFTER_EXHAUSTION"] += 1
            continue
        funnel["ENTRY_ARMED"] += 1
        entry_info = find_break_entry(candles, index, current, retest_high, last_highs[-2][1], atr)
        if entry_info["status"] != "FILLED":
            funnel[entry_info["reason"]] += 1
            continue
        entry = float(entry_info["price"])
        stop = retest_high + 0.15 * atr
        risk = stop - entry
        reward = entry - float(target)
        if risk <= 0 or reward <= 0:
            funnel["INVALID_TRADE_GEOMETRY"] += 1
            continue
        stop_atr, target_atr, rr = risk / atr, reward / atr, reward / risk
        if stop_atr < 0.75:
            funnel["STOP_DISTANCE_ATR_BELOW_0_75"] += 1
            continue
        if target_atr > 4.0:
            funnel["TARGET_DISTANCE_ATR_ABOVE_4_0"] += 1
            continue
        if rr < 1.5:
            funnel["NO_ROOM_TO_TARGET_RR_BELOW_1_5"] += 1
            continue
        if stop_atr > 2.0:
            warnings.append("STOP_DISTANCE_ATR_ABOVE_2_0")
        if target_atr > 3.0:
            warnings.append("TARGET_DISTANCE_ATR_ABOVE_3_0")
        if rr > 5.0:
            warnings.append("RR_ABOVE_5_PENALTY")
        elif rr > 3.0:
            warnings.append("RR_ABOVE_PREFERRED_3")
        plan = {
            "candidate_id": "", "symbol": symbol, "timeframe": INTERVAL,
            "setup_type": "SHORT_DOWN_CONTINUATION_RETEST_V2",
            "stage_trace": ["SETUP_READY", "ENTRY_ARMED", "TRADE_CANDIDATE"],
            "confirmation_time": iso(current.timestamp), "entry_time": entry_info["fill_time"],
            "entry_age_bars": entry_info["age"], "entry_price": entry,
            "stop_price": stop, "target_price": target, "target_kind": target_kind,
            "invalidation_price": retest_high, "atr14": atr, "stop_distance_atr": stop_atr,
            "target_distance_atr": target_atr, "planned_rr": rr,
            "structure": {
                "classification": "LH/LL", "pivot_highs": last_highs, "pivot_lows": last_lows,
                "impulse_time": iso(candles[impulse_index].timestamp), "impulse_down_atr": impulse_down_atr,
                "correction_bars": correction_bars, "retest_depth_atr": retest_depth_atr,
            },
            "causal_zone": {"kind": zone_kind, "price": zone, "distance_atr": zone_distance_atr},
            "confirmation_candle": {
                "open": current.open, "high": current.high, "low": current.low, "close": current.close, **candle,
            },
            "technical": tech, "engine_hypothesis": hypothesis, "warnings": warnings,
            "fill_index_internal": entry_info["fill_index"],
            "generation_used_post_fill_outcome": False,
        }
        plans.append(plan)
        funnel["TRADE_CANDIDATE"] += 1
        cooldown_until = entry_info["fill_index"] + COOLDOWN_BARS
    return plans, funnel


def freeze_plans(plans: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str, bytes]:
    plans = sorted(plans, key=lambda item: (item["confirmation_time"], item["symbol"]))
    for number, plan in enumerate(plans, 1):
        plan["candidate_id"] = f"ET26-SV2-{number:04d}"
    public = [{key: value for key, value in plan.items() if key != "fill_index_internal"} for plan in plans]
    payload = (json.dumps({"plans": public}, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    return plans, hashlib.sha256(payload).hexdigest(), payload


def label_plan(plan: dict[str, Any], candles: list[Candle]) -> dict[str, Any]:
    """Outcome-only phase. This function is called strictly after plan freeze."""
    start = plan["fill_index_internal"]
    entry, stop, target = plan["entry_price"], plan["stop_price"], plan["target_price"]
    observed = candles[start : start + HORIZON]
    if len(observed) < HORIZON:
        return {"label": "INSUFFICIENT_FUTURE_DATA", "net_return_pct": None, "bars_to_outcome": None}
    for offset, candle in enumerate(observed, 1):
        tp = candle.low <= target
        sl = candle.high >= stop
        if offset == 1 and tp and sl:
            return {"label": "AMBIGUOUS_FILL_BAR", "net_return_pct": None, "bars_to_outcome": 1}
        if offset == 1 and sl:
            return {"label": "AMBIGUOUS_FILL_BAR", "net_return_pct": None, "bars_to_outcome": 1}
        if tp and sl:
            return {"label": "AMBIGUOUS_INTRACANDLE", "net_return_pct": None, "bars_to_outcome": offset}
        if tp:
            gross = (entry - target) / entry * 100
            return {"label": "TP_BEFORE_SL", "net_return_pct": gross - ROUND_TRIP_COST_BPS / 100, "bars_to_outcome": offset}
        if sl:
            gross = (entry - stop) / entry * 100
            return {"label": "SL_BEFORE_TP", "net_return_pct": gross - ROUND_TRIP_COST_BPS / 100, "bars_to_outcome": offset}
    gross = (entry - observed[-1].close) / entry * 100
    return {"label": "NEITHER_EXPIRED", "net_return_pct": gross - ROUND_TRIP_COST_BPS / 100, "bars_to_outcome": HORIZON}


def performance(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(rows)
    clean = [row for row in rows if row["label"] in {"TP_BEFORE_SL", "SL_BEFORE_TP"}]
    returns = [float(row["net_return_pct"]) for row in clean]
    gains = sum(value for value in returns if value > 0)
    losses = -sum(value for value in returns if value < 0)
    equity = peak = drawdown = 0.0
    consecutive = max_consecutive = 0
    for value in returns:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
        consecutive = consecutive + 1 if value < 0 else 0
        max_consecutive = max(max_consecutive, consecutive)
    return {
        "candidates": len(rows), "clean_trades": len(clean),
        "wins": sum(row["label"] == "TP_BEFORE_SL" for row in clean),
        "losses": sum(row["label"] == "SL_BEFORE_TP" for row in clean),
        "ambiguous": sum(row["label"].startswith("AMBIGUOUS") for row in rows),
        "expired": sum(row["label"] == "NEITHER_EXPIRED" for row in rows),
        "winrate_pct": 100 * sum(row["label"] == "TP_BEFORE_SL" for row in clean) / len(clean) if clean else None,
        "profit_factor": gains / losses if losses else None,
        "expectancy_pct": sum(returns) / len(returns) if returns else None,
        "total_net_return_pct_naive": sum(returns),
        "max_drawdown_pct_naive_additive": drawdown,
        "max_consecutive_losses": max_consecutive,
    }


def acceptance_gate(outcomes: list[dict[str, Any]], metrics: dict[str, Any], monthly: dict[str, dict[str, Any]], by_symbol: dict[str, dict[str, Any]]) -> dict[str, Any]:
    clean = sorted((row for row in outcomes if row["label"] in {"TP_BEFORE_SL", "SL_BEFORE_TP"}), key=lambda row: row["net_return_pct"], reverse=True)
    removed = performance(clean[2:]) if len(clean) > 2 else performance([])
    robust = removed["expectancy_pct"] is not None and removed["expectancy_pct"] > 0
    non_negative_months = sum(value["expectancy_pct"] is not None and value["expectancy_pct"] >= 0 for value in monthly.values())
    positive_symbols = sum(value["expectancy_pct"] is not None and value["expectancy_pct"] > 0 for value in by_symbol.values())
    passed = (
        metrics["clean_trades"] >= 30 and metrics["profit_factor"] is not None and metrics["profit_factor"] >= 1.15
        and metrics["expectancy_pct"] is not None and metrics["expectancy_pct"] > 0
        and metrics["max_drawdown_pct_naive_additive"] <= 10 and non_negative_months >= 4
        and positive_symbols >= 2 and robust
    )
    return {
        "paper_evidence_gate_pass": passed, "robust_after_top_two_winners_removed": robust,
        "top_two_removed_metrics": removed, "non_negative_months": non_negative_months,
        "positive_symbols": positive_symbols,
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: "|".join(row[field]) if isinstance(row.get(field), list) else row.get(field) for field in fields})


def fmt(value: Any, digits: int = 4) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}" if isinstance(value, float) else str(value)


def run(output_dir: Path = DEFAULT_OUTPUT, rows_by_symbol: dict[str, list[Candle]] | None = None) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    contract = locked_contract()
    rows_by_symbol = rows_by_symbol or load_rows()
    coverage = data_coverage(rows_by_symbol)
    if any(row["status"] != "PASS" for row in coverage):
        raise RuntimeError(f"Data coverage gate failed: {coverage}")
    plans: list[dict[str, Any]] = []
    funnel: Counter[str] = Counter()
    for symbol in SYMBOLS:
        found, counts = scan_symbol(symbol, rows_by_symbol[symbol])
        plans.extend(found)
        funnel.update(counts)
    frozen, freeze_hash, freeze_payload = freeze_plans(plans)

    (output_dir / OUTPUT_FILES[0]).write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    (output_dir / OUTPUT_FILES[1]).write_text(json.dumps({"coverage": coverage}, indent=2) + "\n", encoding="utf-8")
    (output_dir / OUTPUT_FILES[2]).write_bytes(freeze_payload)

    outcomes: list[dict[str, Any]] = []
    for plan in frozen:
        outcome = label_plan(plan, rows_by_symbol[plan["symbol"]])
        outcomes.append({
            "candidate_id": plan["candidate_id"], "symbol": plan["symbol"],
            "confirmation_time": plan["confirmation_time"], "entry_time": plan["entry_time"],
            **outcome,
        })
    outcome_by_id = {row["candidate_id"]: row for row in outcomes}
    candidate_rows = [{
        "candidate_id": plan["candidate_id"], "symbol": plan["symbol"],
        "confirmation_time": plan["confirmation_time"], "entry_time": plan["entry_time"],
        "entry_age_bars": plan["entry_age_bars"], "entry_price": plan["entry_price"],
        "stop_price": plan["stop_price"], "target_price": plan["target_price"],
        "target_kind": plan["target_kind"], "stop_distance_atr": plan["stop_distance_atr"],
        "target_distance_atr": plan["target_distance_atr"], "planned_rr": plan["planned_rr"],
        "warnings": plan["warnings"], "label": outcome_by_id[plan["candidate_id"]]["label"],
        "net_return_pct": outcome_by_id[plan["candidate_id"]]["net_return_pct"],
    } for plan in frozen]
    candidate_fields = [
        "candidate_id", "symbol", "confirmation_time", "entry_time", "entry_age_bars", "entry_price",
        "stop_price", "target_price", "target_kind", "stop_distance_atr", "target_distance_atr",
        "planned_rr", "warnings", "label", "net_return_pct",
    ]
    write_csv(output_dir / OUTPUT_FILES[3], candidate_rows, candidate_fields)
    write_csv(output_dir / OUTPUT_FILES[4], outcomes, ["candidate_id", "symbol", "confirmation_time", "entry_time", "label", "net_return_pct", "bars_to_outcome"])
    write_csv(output_dir / OUTPUT_FILES[5], [{"stage_or_reason": key, "count": value} for key, value in funnel.most_common()], ["stage_or_reason", "count"])

    full_metrics = performance(outcomes)
    monthly_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    symbol_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in outcomes:
        monthly_groups[row["entry_time"][:7]].append(row)
        symbol_groups[row["symbol"]].append(row)
    month_keys = ("2025-12", "2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06")
    monthly = {key: performance(monthly_groups.get(key, [])) for key in month_keys}
    by_symbol = {key: performance(symbol_groups.get(key, [])) for key in SYMBOLS}
    gates = acceptance_gate(outcomes, full_metrics, monthly, by_symbol)
    metrics_payload = {
        "pre_entry_freeze_sha256": freeze_hash, "full_forward": full_metrics,
        "by_month": monthly, "by_symbol": by_symbol, "acceptance_gate": gates,
    }
    (output_dir / OUTPUT_FILES[6]).write_text(json.dumps(metrics_payload, indent=2) + "\n", encoding="utf-8")

    leakage = f"""# ENGINE-TREND-26 Leakage Audit

- The scanner reads no ENGINE-TREND-23/24/25 candidates, labels, metrics, or selected IDs.
- Rules and the common-symbol window are constants in code and recorded in `ENGINE_TREND_26_LOCKED_SCANNER_CONTRACT.json`.
- Forward confirmations: `{iso(FORWARD_START)}` through `{iso(SCAN_END)}`; every entry has 96 common-symbol future bars available through `{iso(COMMON_LAST_CANDLE)}`.
- Pre-entry plans were written and frozen before `label_plan` ran. Freeze SHA-256: `{freeze_hash}`.
- `scan_symbol`, `engine_hypothesis`, `find_break_entry`, and target/risk construction do not access outcome labels, MFE, MAE, or post-fill returns.
- Post-confirmation candles up to the actual fill are entry-decision data, not outcome data. Outcome labelling begins at the frozen fill.
- Fill-bar stop ambiguity and simultaneous TP/SL ambiguity are excluded from clean PF/expectancy.
- No threshold, entry, stop, target, symbol, or month is selected from forward results. There is one locked reference mode.

Status: **PASS**.
"""
    (output_dir / OUTPUT_FILES[7]).write_text(leakage, encoding="utf-8")
    status = "ENGINE_TREND_26_FORWARD_GATE_PASS_NOT_ACTIVATED" if gates["paper_evidence_gate_pass"] else "ENGINE_TREND_26_FORWARD_GATE_FAIL_NOT_READY_FOR_PAPER"
    report = f"""# ENGINE-TREND-26 Fresh SHORT_V2 Forward Scan

## Decision

**{status}**. This is a fresh scan over all decision points, not a replay of the 449 V1 candidates. Runtime and paper trading remain unchanged.

## Frozen scope

- Symbols: BTCUSDT, ETHUSDT, SOLUSDT; timeframe 15m.
- Untouched forward confirmations: `{iso(FORWARD_START)}` through `{iso(SCAN_END)}`.
- Common data-quality gate: PASS for all symbols; 96 outcome bars reserved per entry.
- Reference contract: break confirmation low; stop retest high + 0.15 ATR; nearest pre-entry confirmed support; RR >= 1.5.
- Pre-entry plan freeze: `{freeze_hash}`.

## Forward result

- decision points: {funnel['DECISION_POINTS']}
- bearish trigger prefilters: {funnel['BEARISH_TRIGGER_PREFILTER']}
- current ENGINE-TREND confirmed DOWN_CONTINUATION setups: {funnel['SETUP_READY_CONFIRMED']}
- trade candidates: {full_metrics['candidates']}; clean: {full_metrics['clean_trades']}; ambiguous: {full_metrics['ambiguous']}; expired: {full_metrics['expired']}
- wins / losses: {full_metrics['wins']} / {full_metrics['losses']}
- PF: {fmt(full_metrics['profit_factor'])}; expectancy: {fmt(full_metrics['expectancy_pct'])}%; win rate: {fmt(full_metrics['winrate_pct'])}%
- naive total: {fmt(full_metrics['total_net_return_pct_naive'])}%; max drawdown: {fmt(full_metrics['max_drawdown_pct_naive_additive'])}%
- non-negative months: {gates['non_negative_months']}; positive symbols: {gates['positive_symbols']}; robust after top-two winners removed: {gates['robust_after_top_two_winners_removed']}

## Interpretation

The acceptance gate was fixed before outcomes: at least 30 clean trades, PF >= 1.15, positive expectancy, drawdown <= 10%, at least four non-negative months, at least two positive symbols, and positive expectancy after removing the top two winners. Passing the numerical gate does not activate paper trading; failure leaves SHORT_V2 in research only.
"""
    (output_dir / OUTPUT_FILES[8]).write_text(report, encoding="utf-8")
    decision = {
        "final_status": status, "paper_enabled": False, "runtime_changed": False,
        "trading_runtime_changed": False, "fresh_scan": True, "v1_candidates_loaded": False,
        "pre_entry_freeze_sha256": freeze_hash, "metrics": full_metrics, "acceptance_gate": gates,
        "next_stage": "paper dry-run design" if gates["paper_evidence_gate_pass"] else "retain research-only and collect a new untouched forward window",
    }
    (output_dir / OUTPUT_FILES[9]).write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")
    artifacts = []
    for name in OUTPUT_FILES[:-1]:
        payload = (output_dir / name).read_bytes()
        artifacts.append({"file": name, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()})
    manifest = {"created_files": list(OUTPUT_FILES), "artifacts": artifacts, "manifest_self_excluded_from_hashes": True}
    (output_dir / OUTPUT_FILES[-1]).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {"decision": decision, "coverage": coverage, "plans": frozen, "outcomes": outcomes, "funnel": funnel, "metrics": metrics_payload}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run(args.output)
    print(json.dumps({
        "status": result["decision"]["final_status"],
        "trade_candidates": result["decision"]["metrics"]["candidates"],
        "clean_trades": result["decision"]["metrics"]["clean_trades"],
    }, indent=2))


if __name__ == "__main__":
    main()
