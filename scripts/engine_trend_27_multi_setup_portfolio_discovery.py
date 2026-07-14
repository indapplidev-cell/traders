"""ENGINE-TREND-27 audit-only multi-setup discovery on a held-out history window.

The five setup contracts are intentionally fixed in this file.  Candidate generation
uses only candles available at the confirmation close.  Plans are serialized and
hashed before the separate outcome labeller is called.  This module does not import
or mutate execution/runtime configuration and does not use any V1/V2 score.
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
from statistics import mean
from typing import Any, Iterable

from sqlalchemy import create_engine, text

from app.config.settings import get_settings

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
DEFAULT_OUTPUT = ROOT / "reports/engine_trend/engine_trend_27_multi_setup_portfolio_discovery"
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
INTERVAL = "15m"
STEP = timedelta(minutes=15)
# This common window predates the ENGINE-23 discovery universe (2025-07-03 onward)
# and ENGINE-26 forward window (2025-12-18 onward).
SCAN_START = datetime(2025, 1, 4, 0, 0, tzinfo=timezone.utc)
LAST_CONFIRMATION = datetime(2025, 6, 29, 23, 45, tzinfo=timezone.utc)
LOAD_START = SCAN_START - 240 * STEP
LOAD_END_EXCLUSIVE = LAST_CONFIRMATION + 97 * STEP
HORIZON = 96
ROUND_TRIP_COST_BPS = 24.0
RISK_FRACTION = 0.01
FAMILIES = (
    "SHORT_CONTINUATION_PRACTICAL_TARGET",
    "SHORT_FAILED_REBOUND",
    "RANGE_BOUNDARY_REJECTION",
    "TRAP_REVERSAL",
    "MOMENTUM_BREAKDOWN_PULLBACK",
)
OUTPUT_FILES = (
    "ENGINE_TREND_27_LOCKED_PORTFOLIO_CONTRACT.json",
    "ENGINE_TREND_27_DATA_COVERAGE.json",
    "ENGINE_TREND_27_PRE_ENTRY_PLANS.json",
    "ENGINE_TREND_27_CANDIDATES.csv",
    "ENGINE_TREND_27_OUTCOMES.csv",
    "ENGINE_TREND_27_FAMILY_FUNNEL.csv",
    "ENGINE_TREND_27_PORTFOLIO_METRICS.json",
    "ENGINE_TREND_27_FAILURE_MODES.json",
    "ENGINE_TREND_27_LEAKAGE_AUDIT.md",
    "ENGINE_TREND_27_DISCOVERY_REPORT.md",
    "ENGINE_TREND_27_DECISION_RECORD.json",
    "ENGINE_TREND_27_ARTIFACT_MANIFEST.json",
)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def locked_contract() -> dict[str, Any]:
    return {
        "version": "ENGINE_TREND_27_MULTI_SETUP_PORTFOLIO_V1_LOCKED",
        "locked_before_outcome_read": True,
        "audit_only": True,
        "runtime_changed": False,
        "paper_enabled": False,
        "old_scores_loaded": False,
        "short_v2_status": "RESEARCH_ONLY_FAILED_FORWARD_CONTRACT_CLOSED",
        "symbols": list(SYMBOLS),
        "timeframe": INTERVAL,
        "held_out_window": {
            "start": iso(SCAN_START),
            "last_confirmation": iso(LAST_CONFIRMATION),
            "horizon_bars": HORIZON,
            "relationship_to_prior_research": "pre-ENGINE-23 universe; disjoint from ENGINE-26 forward window",
            "limitation": "backward-held-out historical evidence, not a live chronological forward",
        },
        "common": {
            "causal_pivots": "2-bar wings; pivot known only after right wing closes",
            "costs_round_trip_bps": ROUND_TRIP_COST_BPS,
            "outcome_horizon_bars": HORIZON,
            "same_bar_policy": "close-entry outcomes begin on the next candle; simultaneous future-candle TP/SL is excluded from clean metrics",
            "deduplication": "first candidate per symbol/family, then 8 closed bars cooldown",
            "portfolio_risk_model": "chronological clean trades, fixed 1% equity risk per trade; simultaneous candidates remain separate research observations",
        },
        "families": {
            "SHORT_CONTINUATION_PRACTICAL_TARGET": {
                "context": "confirmed LH/LL, EMA20 < EMA50, close breaks latest confirmed swing low",
                "trigger": "bearish close, body >=0.35 ATR, close in lower 35%, volume ratio >=1.0",
                "entry": "confirmation close",
                "stop": "max prior six highs + 0.10 ATR",
                "target": "nearest causal support when 1.5R..2R; otherwise fixed 2R only for strong momentum, else fixed 1.5R",
            },
            "SHORT_FAILED_REBOUND": {
                "context": "LH/LL, EMA20 < EMA50, 1.25 ATR downswing followed by 2..6 bar rebound not exceeding prior confirmed high",
                "trigger": "bearish failure close below previous low near EMA20/rebound high; volume ratio >=0.9",
                "entry": "confirmation close", "stop": "rebound high + 0.10 ATR",
                "target": "closer of prior impulse low and fixed 1.25R, requiring at least 1R room",
            },
            "RANGE_BOUNDARY_REJECTION": {
                "context": "48-bar confirmed range, >=2 causal pivot touches each side, width 2..8 ATR, EMA spread <=0.6 ATR, ADX <=25",
                "trigger": "boundary touch and rejection close back inside; volume ratio >=0.8",
                "entry": "confirmation close", "stop": "beyond candle/boundary by 0.15 ATR", "target": "range midline; minimum 1R",
            },
            "TRAP_REVERSAL": {
                "context": "same confirmed range geometry (ADX <=30)",
                "trigger": "false break by >=0.05 ATR and close back inside with volume ratio >=1.0",
                "entry": "return-to-range confirmation close", "stop": "beyond trap extreme by 0.15 ATR", "target": "range midline; minimum 1R",
            },
            "MOMENTUM_BREAKDOWN_PULLBACK": {
                "context": "EMA20 < EMA50 and a 1..3 bar-old support breakdown with body >=0.55 ATR, lower-third close, volume ratio >=1.2",
                "trigger": "short pullback stays within 0.75 ATR of broken support, then bearish continuation below previous low; volume ratio >=0.9",
                "entry": "continuation close", "stop": "pullback high + 0.12 ATR", "target": "fixed 1.5R",
            },
        },
        "minimum_gate_per_family": {
            "clean_trades_min": 30,
            "profit_factor_min": 1.05,
            "expectancy_net_r_gt": 0,
            "max_drawdown_pct_lt": 15,
            "positive_symbols_min": 2,
            "single_trade_profit_share_max": 0.5,
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
    out = []
    for symbol in SYMBOLS:
        candles = rows_by_symbol[symbol]
        times = [c.timestamp for c in candles]
        problems = {
            "irregular": sum(b - a != STEP for a, b in zip(times, times[1:])),
            "duplicates": len(times) - len(set(times)),
            "ohlc_errors": sum(c.low > min(c.open, c.close) or c.high < max(c.open, c.close) or c.high < c.low for c in candles),
            "non_finite": sum(not all(math.isfinite(x) for x in (c.open, c.high, c.low, c.close, c.volume)) for c in candles),
        }
        row = {"symbol": symbol, "expected": expected, "actual": len(candles),
               "first": iso(candles[0].timestamp) if candles else None,
               "last": iso(candles[-1].timestamp) if candles else None, **problems}
        row["status"] = "PASS" if len(candles) == expected and not any(problems.values()) else "FAIL"
        out.append(row)
    return out


def volume_ratio(candles: list[Candle], index: int) -> float:
    base = mean(c.volume for c in candles[index - 19:index + 1])
    return candles[index].volume / base if base else 0.0


def structure(candles: list[Candle], index: int) -> tuple[list[tuple[int, float]], list[tuple[int, float]], bool]:
    highs, lows = pivots(candles, index)
    down = len(highs) >= 2 and len(lows) >= 2 and highs[-1][1] < highs[-2][1] and lows[-1][1] < lows[-2][1]
    return highs, lows, down


def range_context(candles: list[Candle], index: int, atr: float, ind: dict[str, list[float | None]], adx_max: float) -> dict[str, Any] | None:
    highs, lows = pivots(candles, index, lookback=48)
    if len(highs) < 2 or len(lows) < 2:
        return None
    upper = mean(price for _, price in highs[-2:])
    lower = mean(price for _, price in lows[-2:])
    width = upper - lower
    if width <= 0 or not 2.0 <= width / atr <= 8.0:
        return None
    tolerance = 0.35 * atr
    high_touches = sum(abs(price - upper) <= tolerance for _, price in highs)
    low_touches = sum(abs(price - lower) <= tolerance for _, price in lows)
    ema20, ema50, adx = ind["ema20"][index], ind["ema50"][index], ind["adx"][index]
    if high_touches < 2 or low_touches < 2 or not finite(ema20) or not finite(ema50) or abs(ema20 - ema50) > 0.6 * atr:
        return None
    if not finite(adx) or adx > adx_max:
        return None
    return {"lower": lower, "upper": upper, "midline": (upper + lower) / 2,
            "width_atr": width / atr, "high_touches": high_touches, "low_touches": low_touches, "adx14": adx}


def make_plan(*, symbol: str, family: str, direction: str, candles: list[Candle], index: int,
              atr: float, entry: float, stop: float, target: float, target_kind: str,
              evidence: dict[str, Any]) -> dict[str, Any] | None:
    risk = entry - stop if direction == "LONG" else stop - entry
    reward = target - entry if direction == "LONG" else entry - target
    if risk <= 0 or reward <= 0:
        return None
    return {
        "candidate_id": "", "family": family, "symbol": symbol, "timeframe": INTERVAL,
        "direction": direction, "confirmation_time": iso(candles[index].timestamp),
        "entry_time": iso(candles[index].timestamp), "entry_price": entry, "stop_price": stop,
        "target_price": target, "target_kind": target_kind, "atr14": atr,
        "stop_distance_atr": risk / atr, "target_distance_atr": reward / atr,
        "planned_rr": reward / risk, "volume_ratio_20": volume_ratio(candles, index),
        "evidence": evidence, "fill_index_internal": index,
        "generation_used_post_entry_outcome": False,
    }


def detect_short_continuation(symbol: str, candles: list[Candle], index: int, atr: float,
                              ind: dict[str, list[float | None]]) -> dict[str, Any] | None:
    current = candles[index]
    highs, lows, down = structure(candles, index)
    ema20, ema50 = ind["ema20"][index], ind["ema50"][index]
    feat = candle_features(current, atr)
    if not down or not finite(ema20) or not finite(ema50) or ema20 >= ema50 or current.close >= lows[-1][1]:
        return None
    if not (current.close < current.open and feat["body_atr"] >= 0.35 and feat["close_location"] <= 0.35 and volume_ratio(candles, index) >= 1.0):
        return None
    entry = current.close
    stop = max(c.high for c in candles[index - 5:index + 1]) + 0.10 * atr
    risk = stop - entry
    if risk <= 0:
        return None
    prior_supports = [price for pivot_index, price in lows[:-1] if pivot_index >= index - 95 and price < entry]
    nearest = max(prior_supports) if prior_supports else None
    nearest_rr = (entry - nearest) / risk if nearest is not None else None
    if nearest is not None and 1.5 <= nearest_rr <= 2.0:
        target, kind = nearest, "NEAREST_CONFIRMED_SUPPORT"
    elif feat["body_atr"] >= 0.8 and volume_ratio(candles, index) >= 1.3:
        target, kind = entry - 2.0 * risk, "FIXED_2R_STRONG_MOMENTUM"
    else:
        target, kind = entry - 1.5 * risk, "FIXED_1_5R"
    return make_plan(symbol=symbol, family=FAMILIES[0], direction="SHORT", candles=candles, index=index,
                     atr=atr, entry=entry, stop=stop, target=target, target_kind=kind,
                     evidence={"pivot_highs": highs[-2:], "pivot_lows": lows[-2:], "broken_support": lows[-1][1]})


def detect_failed_rebound(symbol: str, candles: list[Candle], index: int, atr: float,
                          ind: dict[str, list[float | None]]) -> dict[str, Any] | None:
    current = candles[index]
    highs, lows, down = structure(candles, index)
    ema20, ema50 = ind["ema20"][index], ind["ema50"][index]
    if not down or not finite(ema20) or not finite(ema50) or ema20 >= ema50 or volume_ratio(candles, index) < 0.9:
        return None
    for rebound_bars in range(2, 7):
        impulse_window = candles[index - rebound_bars - 8:index - rebound_bars + 1]
        if len(impulse_window) < 9:
            continue
        impulse_high = max(c.high for c in impulse_window)
        impulse_low = candles[index - rebound_bars].low
        rebound_high = max(c.high for c in candles[index - rebound_bars + 1:index + 1])
        if (impulse_high - impulse_low) / atr < 1.25 or rebound_high >= highs[-2][1]:
            continue
        near_failure_zone = abs(rebound_high - ema20) <= 0.75 * atr or rebound_high <= lows[-2][1] + 0.5 * atr
        if not near_failure_zone or not (current.close < current.open and current.close < candles[index - 1].low):
            continue
        entry, stop = current.close, rebound_high + 0.10 * atr
        risk = stop - entry
        if risk <= 0:
            return None
        prior_low = min(c.low for c in candles[index - rebound_bars:index])
        available_r = (entry - prior_low) / risk
        if available_r < 1.0:
            return None
        target = max(prior_low, entry - 1.25 * risk)
        return make_plan(symbol=symbol, family=FAMILIES[1], direction="SHORT", candles=candles, index=index,
                         atr=atr, entry=entry, stop=stop, target=target, target_kind="CLOSER_PRIOR_LOW_OR_1_25R",
                         evidence={"rebound_bars": rebound_bars, "impulse_high": impulse_high,
                                   "impulse_low": impulse_low, "rebound_high": rebound_high})
    return None


def detect_range_rejection(symbol: str, candles: list[Candle], index: int, atr: float,
                           ind: dict[str, list[float | None]]) -> dict[str, Any] | None:
    context = range_context(candles, index, atr, ind, 25.0)
    if context is None or volume_ratio(candles, index) < 0.8:
        return None
    c = candles[index]
    feat = candle_features(c, atr)
    if c.high >= context["upper"] - 0.20 * atr and c.close < context["upper"] and c.close < c.open and feat["upper_wick_fraction"] >= 0.25:
        direction, stop, target = "SHORT", max(c.high, context["upper"]) + 0.15 * atr, context["midline"]
    elif c.low <= context["lower"] + 0.20 * atr and c.close > context["lower"] and c.close > c.open and feat["lower_wick_fraction"] >= 0.25:
        direction, stop, target = "LONG", min(c.low, context["lower"]) - 0.15 * atr, context["midline"]
    else:
        return None
    plan = make_plan(symbol=symbol, family=FAMILIES[2], direction=direction, candles=candles, index=index,
                     atr=atr, entry=c.close, stop=stop, target=target, target_kind="CONFIRMED_RANGE_MIDLINE", evidence=context)
    return plan if plan and plan["planned_rr"] >= 1.0 else None


def detect_trap_reversal(symbol: str, candles: list[Candle], index: int, atr: float,
                         ind: dict[str, list[float | None]]) -> dict[str, Any] | None:
    context = range_context(candles, index, atr, ind, 30.0)
    if context is None or volume_ratio(candles, index) < 1.0:
        return None
    c = candles[index]
    if c.high >= context["upper"] + 0.05 * atr and c.close < context["upper"] and c.close > context["midline"]:
        direction, stop, target, kind = "SHORT", c.high + 0.15 * atr, context["midline"], "FALSE_BREAKOUT_TO_MIDLINE"
    elif c.low <= context["lower"] - 0.05 * atr and c.close > context["lower"] and c.close < context["midline"]:
        direction, stop, target, kind = "LONG", c.low - 0.15 * atr, context["midline"], "FALSE_BREAKDOWN_TO_MIDLINE"
    else:
        return None
    plan = make_plan(symbol=symbol, family=FAMILIES[3], direction=direction, candles=candles, index=index,
                     atr=atr, entry=c.close, stop=stop, target=target, target_kind=kind, evidence=context)
    return plan if plan and plan["planned_rr"] >= 1.0 else None


def detect_momentum_pullback(symbol: str, candles: list[Candle], index: int, atr: float,
                             ind: dict[str, list[float | None]]) -> dict[str, Any] | None:
    ema20, ema50 = ind["ema20"][index], ind["ema50"][index]
    c = candles[index]
    if not finite(ema20) or not finite(ema50) or ema20 >= ema50 or volume_ratio(candles, index) < 0.9:
        return None
    for age in range(1, 4):
        break_index = index - age
        _, known_lows = pivots(candles, break_index - 1)
        if not known_lows:
            continue
        support = known_lows[-1][1]
        breakdown = candles[break_index]
        feat = candle_features(breakdown, atr)
        breakdown_volume = volume_ratio(candles, break_index)
        if not (breakdown.close < support and breakdown.open >= support and feat["body_atr"] >= 0.55 and feat["close_location"] <= 0.33 and breakdown_volume >= 1.2):
            continue
        pullback = candles[break_index + 1:index + 1]
        pullback_high = max(bar.high for bar in pullback)
        if pullback_high > support + 0.75 * atr or not (c.close < c.open and c.close < candles[index - 1].low and c.close < support):
            continue
        entry, stop = c.close, pullback_high + 0.12 * atr
        risk = stop - entry
        if risk <= 0:
            return None
        return make_plan(symbol=symbol, family=FAMILIES[4], direction="SHORT", candles=candles, index=index,
                         atr=atr, entry=entry, stop=stop, target=entry - 1.5 * risk,
                         target_kind="FIXED_1_5R", evidence={"breakdown_time": iso(breakdown.timestamp),
                         "broken_support": support, "pullback_bars": age, "breakdown_volume_ratio": breakdown_volume})
    return None


DETECTORS = (detect_short_continuation, detect_failed_rebound, detect_range_rejection,
             detect_trap_reversal, detect_momentum_pullback)


def scan_symbol(symbol: str, candles: list[Candle]) -> tuple[list[dict[str, Any]], Counter[tuple[str, str]]]:
    ind = indicators(candles)
    plans: list[dict[str, Any]] = []
    funnel: Counter[tuple[str, str]] = Counter()
    cooldown = {family: -1 for family in FAMILIES}
    for index in range(240, len(candles) - HORIZON):
        if not SCAN_START <= candles[index].timestamp <= LAST_CONFIRMATION:
            continue
        atr = ind["atr"][index]
        for family, detector in zip(FAMILIES, DETECTORS):
            funnel[(family, "DECISION_POINTS")] += 1
            if index <= cooldown[family]:
                funnel[(family, "COOLDOWN_SKIPPED")] += 1
                continue
            if not finite(atr) or atr <= 0:
                funnel[(family, "ATR_UNAVAILABLE")] += 1
                continue
            plan = detector(symbol, candles, index, float(atr), ind)
            if plan is None:
                funnel[(family, "NO_SETUP")] += 1
                continue
            plans.append(plan)
            funnel[(family, "TRADE_CANDIDATE")] += 1
            cooldown[family] = index + 8
    return plans, funnel


def freeze_plans(plans: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str, bytes]:
    plans = sorted(plans, key=lambda p: (p["confirmation_time"], p["symbol"], p["family"]))
    for number, plan in enumerate(plans, 1):
        plan["candidate_id"] = f"ET27-{number:05d}"
    public = [{key: value for key, value in plan.items() if key != "fill_index_internal"} for plan in plans]
    payload = (json.dumps({"plans": public}, indent=2, ensure_ascii=False) + "\n").encode()
    return plans, hashlib.sha256(payload).hexdigest(), payload


def label_plan(plan: dict[str, Any], candles: list[Candle]) -> dict[str, Any]:
    """Outcome-only phase; called only after every pre-entry plan is frozen."""
    start = plan["fill_index_internal"]
    entry, stop, target = plan["entry_price"], plan["stop_price"], plan["target_price"]
    direction = plan["direction"]
    # Entry is the confirmation close. Its already-formed high/low cannot be an
    # outcome; observation therefore begins with the next closed candle.
    observed = candles[start + 1:start + 1 + HORIZON]
    if len(observed) < HORIZON:
        return {"label": "INSUFFICIENT_FUTURE_DATA", "net_return_pct": None, "net_r": None, "bars_to_outcome": None}
    risk = abs(entry - stop)
    cost_pct = ROUND_TRIP_COST_BPS / 100
    cost_r = (cost_pct / 100 * entry) / risk
    for offset, candle in enumerate(observed, 1):
        tp = candle.high >= target if direction == "LONG" else candle.low <= target
        sl = candle.low <= stop if direction == "LONG" else candle.high >= stop
        if tp and sl:
            return {"label": "AMBIGUOUS_INTRACANDLE", "net_return_pct": None, "net_r": None, "bars_to_outcome": offset}
        if tp or sl:
            exit_price = target if tp else stop
            gross_pct = ((exit_price - entry) / entry if direction == "LONG" else (entry - exit_price) / entry) * 100
            return {"label": "TP_BEFORE_SL" if tp else "SL_BEFORE_TP",
                    "net_return_pct": gross_pct - cost_pct,
                    "net_r": (plan["planned_rr"] if tp else -1.0) - cost_r,
                    "bars_to_outcome": offset}
    last = observed[-1].close
    gross_pct = ((last - entry) / entry if direction == "LONG" else (entry - last) / entry) * 100
    return {"label": "NEITHER_EXPIRED", "net_return_pct": gross_pct - cost_pct,
            "net_r": ((last - entry) / risk if direction == "LONG" else (entry - last) / risk) - cost_r,
            "bars_to_outcome": HORIZON}


def performance(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = sorted(list(rows), key=lambda r: (r["entry_time"], r["candidate_id"]))
    clean = [r for r in rows if r["label"] in {"TP_BEFORE_SL", "SL_BEFORE_TP"}]
    net_r = [float(r["net_r"]) for r in clean]
    gains = sum(value for value in net_r if value > 0)
    losses = -sum(value for value in net_r if value < 0)
    equity = peak = 1.0
    max_dd = 0.0
    streak = max_streak = 0
    for value in net_r:
        equity *= 1 + RISK_FRACTION * value
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak - equity) / peak * 100)
        streak = streak + 1 if value < 0 else 0
        max_streak = max(max_streak, streak)
    positive = [value for value in net_r if value > 0]
    largest_share = max(positive) / sum(positive) if positive and sum(positive) else None
    return {
        "candidates": len(rows), "clean_trades": len(clean),
        "wins": sum(r["label"] == "TP_BEFORE_SL" for r in clean),
        "losses": sum(r["label"] == "SL_BEFORE_TP" for r in clean),
        "ambiguous": sum(r["label"].startswith("AMBIGUOUS") for r in rows),
        "expired": sum(r["label"] == "NEITHER_EXPIRED" for r in rows),
        "winrate_pct": 100 * sum(r["label"] == "TP_BEFORE_SL" for r in clean) / len(clean) if clean else None,
        "profit_factor_net_r": gains / losses if losses else None,
        "expectancy_net_r": sum(net_r) / len(net_r) if net_r else None,
        "total_net_r": sum(net_r), "max_drawdown_pct_fixed_1pct_risk": max_dd,
        "max_consecutive_losses": max_streak, "largest_winner_share_of_gross_profit": largest_share,
    }


def family_gate(rows: list[dict[str, Any]], metrics: dict[str, Any]) -> dict[str, Any]:
    symbols = {symbol: performance(r for r in rows if r["symbol"] == symbol) for symbol in SYMBOLS}
    positive_symbols = sum(m["expectancy_net_r"] is not None and m["expectancy_net_r"] > 0 for m in symbols.values())
    checks = {
        "clean_trades_gte_30": metrics["clean_trades"] >= 30,
        "profit_factor_gte_1_05": metrics["profit_factor_net_r"] is not None and metrics["profit_factor_net_r"] >= 1.05,
        "expectancy_after_costs_positive": metrics["expectancy_net_r"] is not None and metrics["expectancy_net_r"] > 0,
        "max_drawdown_lt_15pct": metrics["max_drawdown_pct_fixed_1pct_risk"] < 15,
        "positive_symbols_gte_2": positive_symbols >= 2,
        "not_one_trade_dependent": metrics["largest_winner_share_of_gross_profit"] is not None and metrics["largest_winner_share_of_gross_profit"] <= 0.5,
    }
    return {"pass": all(checks.values()), "checks": checks, "positive_symbols": positive_symbols, "by_symbol": symbols}


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: json.dumps(row[field], ensure_ascii=False) if isinstance(row.get(field), (dict, list)) else row.get(field) for field in fields})


def fmt(value: Any, digits: int = 3) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}" if isinstance(value, float) else str(value)


def run(output_dir: Path = DEFAULT_OUTPUT, rows_by_symbol: dict[str, list[Candle]] | None = None) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    contract = locked_contract()
    rows_by_symbol = rows_by_symbol or load_rows()
    coverage = data_coverage(rows_by_symbol)
    if any(row["status"] != "PASS" for row in coverage):
        raise RuntimeError(f"Data coverage gate failed: {coverage}")
    plans: list[dict[str, Any]] = []
    funnel: Counter[tuple[str, str]] = Counter()
    for symbol in SYMBOLS:
        found, counts = scan_symbol(symbol, rows_by_symbol[symbol])
        plans.extend(found)
        funnel.update(counts)
    frozen, freeze_hash, payload = freeze_plans(plans)
    (output_dir / OUTPUT_FILES[0]).write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    (output_dir / OUTPUT_FILES[1]).write_text(json.dumps({"coverage": coverage}, indent=2) + "\n", encoding="utf-8")
    (output_dir / OUTPUT_FILES[2]).write_bytes(payload)

    outcomes = []
    for plan in frozen:
        outcomes.append({"candidate_id": plan["candidate_id"], "family": plan["family"], "symbol": plan["symbol"],
                         "direction": plan["direction"], "entry_time": plan["entry_time"],
                         **label_plan(plan, rows_by_symbol[plan["symbol"]])})
    outcome_by_id = {row["candidate_id"]: row for row in outcomes}
    candidates = [{key: plan[key] for key in ("candidate_id", "family", "symbol", "direction", "confirmation_time",
                   "entry_price", "stop_price", "target_price", "target_kind", "stop_distance_atr",
                   "target_distance_atr", "planned_rr", "volume_ratio_20", "evidence")} |
                  {key: outcome_by_id[plan["candidate_id"]][key] for key in ("label", "net_return_pct", "net_r")}
                  for plan in frozen]
    candidate_fields = ["candidate_id", "family", "symbol", "direction", "confirmation_time", "entry_price", "stop_price",
                        "target_price", "target_kind", "stop_distance_atr", "target_distance_atr", "planned_rr",
                        "volume_ratio_20", "evidence", "label", "net_return_pct", "net_r"]
    write_csv(output_dir / OUTPUT_FILES[3], candidates, candidate_fields)
    write_csv(output_dir / OUTPUT_FILES[4], outcomes, ["candidate_id", "family", "symbol", "direction", "entry_time", "label", "net_return_pct", "net_r", "bars_to_outcome"])
    funnel_rows = [{"family": family, "stage": stage, "count": count} for (family, stage), count in sorted(funnel.items())]
    write_csv(output_dir / OUTPUT_FILES[5], funnel_rows, ["family", "stage", "count"])

    by_family: dict[str, Any] = {}
    gates: dict[str, Any] = {}
    for family in FAMILIES:
        family_rows = [row for row in outcomes if row["family"] == family]
        by_family[family] = performance(family_rows)
        gates[family] = family_gate(family_rows, by_family[family])
    portfolio = performance(outcomes)
    overlap_groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in outcomes:
        overlap_groups[(row["symbol"], row["entry_time"])].append(row["family"])
    overlap = {f"{symbol}|{time}": families for (symbol, time), families in overlap_groups.items() if len(families) > 1}
    metrics_payload = {"pre_entry_freeze_sha256": freeze_hash, "portfolio": portfolio,
                       "by_family": by_family, "family_gates": gates,
                       "same_symbol_same_bar_overlaps": overlap, "families_passing_gate": [f for f, g in gates.items() if g["pass"]]}
    (output_dir / OUTPUT_FILES[6]).write_text(json.dumps(metrics_payload, indent=2) + "\n", encoding="utf-8")

    failures = {}
    for family in FAMILIES:
        rows = [r for r in outcomes if r["family"] == family]
        failures[family] = {
            "outcome_counts": dict(Counter(r["label"] for r in rows)),
            "losses_by_symbol": dict(Counter(r["symbol"] for r in rows if r["label"] == "SL_BEFORE_TP")),
            "losses_by_month": dict(Counter(r["entry_time"][:7] for r in rows if r["label"] == "SL_BEFORE_TP")),
            "fast_stop_losses_le_4_bars": sum(r["label"] == "SL_BEFORE_TP" and r["bars_to_outcome"] <= 4 for r in rows),
            "late_stop_losses_ge_24_bars": sum(r["label"] == "SL_BEFORE_TP" and r["bars_to_outcome"] >= 24 for r in rows),
        }
    (output_dir / OUTPUT_FILES[7]).write_text(json.dumps(failures, indent=2) + "\n", encoding="utf-8")

    leakage = f"""# ENGINE-TREND-27 Leakage Audit

- The scan window `{iso(SCAN_START)}`..`{iso(LAST_CONFIRMATION)}` predates the ENGINE-23 universe and is disjoint from ENGINE-26.
- No ENGINE-23/24/25/26 candidate, score, label, selected ID, metric, or SOLUSDT pocket is loaded.
- The five family contracts are constants in source and recorded before labelling.
- All plans were serialized before `label_plan` ran. Pre-entry SHA-256: `{freeze_hash}`.
- Detection functions receive only the current index and causal candle/indicator arrays. Pivots require their two-bar right wing to have closed.
- Close-entry outcome observation starts on the next candle. Simultaneous TP/SL bars are excluded from clean PF, expectancy, drawdown, and gates.
- This is one reference scan. No family rule or threshold was selected from these outcomes.

Status: **PASS**, with the explicit limitation that this is backward-held-out history, not a future live forward.
"""
    (output_dir / OUTPUT_FILES[8]).write_text(leakage, encoding="utf-8")
    passing = metrics_payload["families_passing_gate"]
    status = "ENGINE_TREND_27_GATE_PASS_READY_FOR_ENGINE_28_AUDIT_ONLY" if passing else "ENGINE_TREND_27_NO_FAMILY_PASSES_GATE_NO_PAPER"
    lines = []
    for family in FAMILIES:
        m = by_family[family]
        lines.append(f"| {family} | {m['candidates']} | {m['clean_trades']} | {fmt(m['winrate_pct'])}% | {fmt(m['profit_factor_net_r'])} | {fmt(m['expectancy_net_r'])}R | {fmt(m['max_drawdown_pct_fixed_1pct_risk'])}% | {m['max_consecutive_losses']} | {'PASS' if gates[family]['pass'] else 'FAIL'} |")
    report = f"""# ENGINE-TREND-27 Multi-Setup Candidate Portfolio Discovery

## Decision

**{status}**. SHORT_V2 remains closed as a research-only failed forward contract. Runtime and paper trading are unchanged.

This is a single, frozen scan on previously unused common history. It tests whether distinct setup families produce enough clean observations and positive after-cost evidence; it does not claim a profitable strategy.

| Setup family | Candidates | Clean | Win rate | PF | Expectancy | Max DD (1% risk) | Loss streak | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
{chr(10).join(lines)}

Portfolio research observations: {portfolio['candidates']} candidates, {portfolio['clean_trades']} clean, PF {fmt(portfolio['profit_factor_net_r'])}, expectancy {fmt(portfolio['expectancy_net_r'])}R, max DD {fmt(portfolio['max_drawdown_pct_fixed_1pct_risk'])}% under the stated fixed-risk audit model. Same-bar family overlaps are reported and are not silently netted.

Families passing the minimum gate: **{', '.join(passing) if passing else 'none'}**.

## Boundary

- Costs: 24 bps round trip; close-entry outcomes start on the next candle and ambiguous TP/SL bars are excluded, not guessed.
- Gate is per family: >=30 clean trades, PF >=1.05, expectancy >0 after costs, DD <15%, positive expectancy on at least two symbols, and no single winner above 50% of gross profit.
- Backward-held-out evidence is weaker than a new chronological forward. A pass authorizes only ENGINE-28 performance audit, never paper activation by itself.
- Failure-mode counts and symbol/month partitions are preserved in JSON for audit instead of tuning this window.
"""
    (output_dir / OUTPUT_FILES[9]).write_text(report, encoding="utf-8")
    decision = {"final_status": status, "short_v2_status": contract["short_v2_status"], "families_passing_gate": passing,
                "engine_28_authorized": bool(passing), "paper_enabled": False, "runtime_changed": False,
                "old_scores_loaded": False, "engine_26_window_used": False, "pre_entry_freeze_sha256": freeze_hash,
                "next_stage": "ENGINE-TREND-28 portfolio performance audit" if passing else "stop; obtain genuinely new data or design a new preregistered research stage"}
    (output_dir / OUTPUT_FILES[10]).write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")
    manifest = {"created_files": list(OUTPUT_FILES), "pre_entry_freeze_sha256": freeze_hash}
    (output_dir / OUTPUT_FILES[11]).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {"contract": contract, "coverage": coverage, "plans": frozen, "outcomes": outcomes,
            "funnel": funnel, "metrics": metrics_payload, "failures": failures, "decision": decision}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run(args.output_dir)
    print(json.dumps(result["decision"], indent=2))


if __name__ == "__main__":
    main()
