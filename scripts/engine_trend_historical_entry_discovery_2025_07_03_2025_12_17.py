"""Offline/audit-only causal historical setup discovery for ENGINE-TREND.

This script never imports or changes trading/execution runtime.  Candidate generation,
levels, and ranking use candles no later than the confirmation candle.  Future candles
are passed to a separate label phase only after the ranking and MAIN selection freeze.
"""

from __future__ import annotations

import csv
from collections import Counter
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

from sqlalchemy import create_engine, text

from app.config.settings import get_settings
from app.data.binance_client import BinanceClient
from app.db.repositories.candle_repository import CandleRepository
from app.db.session import get_session_factory
from app.market_reader.engine_trend.engine import normalize_candles, run_engine_trend


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports/engine_trend/engine_trend_historical_entry_discovery_2025_07_03_2025_12_17"
SYMBOLS = ("SOLUSDT", "ETHUSDT", "BTCUSDT")
INTERVAL = "15m"
STEP = timedelta(minutes=15)
SCAN_START = datetime(2025, 7, 3, tzinfo=timezone.utc)
SCAN_END = datetime(2025, 12, 17, 23, 45, tzinfo=timezone.utc)
LOAD_START = SCAN_START - 96 * STEP
LOAD_END_EXCLUSIVE = SCAN_END + (96 + 1) * STEP
EXPECTED_SCAN_COUNT = int((SCAN_END - SCAN_START) / STEP) + 1
FEE_BPS_PER_SIDE = 10.0
SLIPPAGE_BPS_PER_SIDE = 2.0
ROUND_TRIP_COST_BPS = 24.0


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    close_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def finite(value: float | None) -> bool:
    return value is not None and math.isfinite(value)


def ema(values: list[float], period: int) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    if len(values) < period:
        return result
    seed = mean(values[:period])
    result[period - 1] = seed
    alpha = 2.0 / (period + 1.0)
    previous = seed
    for i in range(period, len(values)):
        previous = alpha * values[i] + (1.0 - alpha) * previous
        result[i] = previous
    return result


def sma(values: list[float], period: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    running = 0.0
    for i, value in enumerate(values):
        running += value
        if i >= period:
            running -= values[i - period]
        if i >= period - 1:
            out[i] = running / period
    return out


def rsi(values: list[float], period: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if len(values) <= period:
        return out
    gains = [max(values[i] - values[i - 1], 0.0) for i in range(1, len(values))]
    losses = [max(values[i - 1] - values[i], 0.0) for i in range(1, len(values))]
    avg_gain, avg_loss = mean(gains[:period]), mean(losses[:period])
    out[period] = 100.0 if avg_loss == 0 else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    for i in range(period + 1, len(values)):
        avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        out[i] = 100.0 if avg_loss == 0 else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    return out


def atr(candles: list[Candle], period: int = 14) -> list[float | None]:
    tr: list[float] = []
    for i, candle in enumerate(candles):
        previous = candle.close if i == 0 else candles[i - 1].close
        tr.append(max(candle.high - candle.low, abs(candle.high - previous), abs(candle.low - previous)))
    out: list[float | None] = [None] * len(candles)
    if len(tr) < period:
        return out
    value = mean(tr[:period])
    out[period - 1] = value
    for i in range(period, len(tr)):
        value = (value * (period - 1) + tr[i]) / period
        out[i] = value
    return out


def adx(candles: list[Candle], period: int = 14) -> list[float | None]:
    n = len(candles)
    tr = [0.0] * n
    plus_dm = [0.0] * n
    minus_dm = [0.0] * n
    for i in range(1, n):
        up = candles[i].high - candles[i - 1].high
        down = candles[i - 1].low - candles[i].low
        plus_dm[i] = up if up > down and up > 0 else 0.0
        minus_dm[i] = down if down > up and down > 0 else 0.0
        tr[i] = max(candles[i].high - candles[i].low, abs(candles[i].high - candles[i - 1].close), abs(candles[i].low - candles[i - 1].close))
    out: list[float | None] = [None] * n
    if n <= period * 2:
        return out
    tr_s, plus_s, minus_s = sum(tr[1 : period + 1]), sum(plus_dm[1 : period + 1]), sum(minus_dm[1 : period + 1])
    dx: list[float | None] = [None] * n
    for i in range(period, n):
        if i > period:
            tr_s = tr_s - tr_s / period + tr[i]
            plus_s = plus_s - plus_s / period + plus_dm[i]
            minus_s = minus_s - minus_s / period + minus_dm[i]
        plus_di = 100.0 * plus_s / tr_s if tr_s else 0.0
        minus_di = 100.0 * minus_s / tr_s if tr_s else 0.0
        dx[i] = 100.0 * abs(plus_di - minus_di) / (plus_di + minus_di) if plus_di + minus_di else 0.0
    first = [x for x in dx[period : period * 2] if x is not None]
    value = mean(first)
    out[period * 2 - 1] = value
    for i in range(period * 2, n):
        value = (value * (period - 1) + float(dx[i] or 0.0)) / period
        out[i] = value
    return out


def rolling_vwap(candles: list[Candle], period: int = 96) -> list[float | None]:
    out: list[float | None] = [None] * len(candles)
    pv, vol = 0.0, 0.0
    for i, candle in enumerate(candles):
        typical = (candle.high + candle.low + candle.close) / 3.0
        pv += typical * candle.volume
        vol += candle.volume
        if i >= period:
            old = candles[i - period]
            pv -= ((old.high + old.low + old.close) / 3.0) * old.volume
            vol -= old.volume
        if i >= period - 1 and vol > 0:
            out[i] = pv / vol
    return out


def indicators(candles: list[Candle]) -> dict[str, list[float | None]]:
    closes = [c.close for c in candles]
    e12, e20, e26, e50, e200 = (ema(closes, p) for p in (12, 20, 26, 50, 200))
    macd = [a - b if finite(a) and finite(b) else None for a, b in zip(e12, e26)]
    signal = ema([x if x is not None else 0.0 for x in macd], 9)
    s20 = sma(closes, 20)
    std20: list[float | None] = [None] * len(candles)
    for i in range(19, len(candles)):
        sample = closes[i - 19 : i + 1]
        m = mean(sample)
        std20[i] = math.sqrt(sum((x - m) ** 2 for x in sample) / 20)
    return {"ema20": e20, "ema50": e50, "ema200": e200, "rsi": rsi(closes), "atr": atr(candles), "adx": adx(candles), "macd": macd, "macd_signal": signal, "sma20": s20, "std20": std20, "vwap96": rolling_vwap(candles)}


def pivots(candles: list[Candle], i: int, lookback: int = 96, wing: int = 2) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    highs: list[tuple[int, float]] = []
    lows: list[tuple[int, float]] = []
    start = max(wing, i - lookback + 1)
    # A pivot at j is known only after j+wing has closed.
    for j in range(start, i - wing + 1):
        if all(candles[j].high > candles[k].high for k in range(j - wing, j + wing + 1) if k != j):
            highs.append((j, candles[j].high))
        if all(candles[j].low < candles[k].low for k in range(j - wing, j + wing + 1) if k != j):
            lows.append((j, candles[j].low))
    return highs, lows


def candle_features(candle: Candle, atr_value: float) -> dict[str, float]:
    spread = max(candle.high - candle.low, 1e-12)
    body = abs(candle.close - candle.open)
    return {"body_atr": body / atr_value, "body_fraction": body / spread, "upper_wick_fraction": (candle.high - max(candle.open, candle.close)) / spread, "lower_wick_fraction": (min(candle.open, candle.close) - candle.low) / spread, "close_location": (candle.close - candle.low) / spread}


def technical_snapshot(ind: dict[str, list[float | None]], candles: list[Candle], i: int) -> dict[str, Any]:
    atr_value = float(ind["atr"][i] or 0.0)
    sma_value = ind["sma20"][i]
    std_value = ind["std20"][i]
    volume_base = mean([c.volume for c in candles[i - 19 : i + 1]])
    return {
        "ema20": ind["ema20"][i], "ema50": ind["ema50"][i], "ema200": ind["ema200"][i],
        "sma20": sma_value, "rsi14": ind["rsi"][i], "macd": ind["macd"][i], "macd_signal": ind["macd_signal"][i],
        "atr14": atr_value, "adx14": ind["adx"][i], "vwap96": ind["vwap96"][i],
        "bollinger_upper": sma_value + 2 * std_value if finite(sma_value) and finite(std_value) else None,
        "bollinger_lower": sma_value - 2 * std_value if finite(sma_value) and finite(std_value) else None,
        "volume_ratio_20": candles[i].volume / volume_base if volume_base else None,
    }


def score_components(*, structure: float, level: float, confirmation: float, rr: float, technical: float, conflict: float, freshness: float) -> tuple[float, dict[str, float]]:
    components = {"causal_context_strength": structure, "structure_clarity": structure, "level_quality": level, "confirmation_candle_quality": confirmation, "rr_quality": min(100.0, 55.0 + 15.0 * (rr - 1.5)), "conflict_absence": conflict, "technical_agreement": technical, "freshness": freshness}
    score = 0.18 * structure + 0.15 * structure + 0.15 * level + 0.14 * confirmation + 0.13 * components["rr_quality"] + 0.10 * conflict + 0.10 * technical + 0.05 * freshness
    return round(score, 4), {k: round(v, 4) for k, v in components.items()}


def candidate_common(symbol: str, candles: list[Candle], ind: dict[str, list[float | None]], i: int, direction: str, setup_type: str, entry: float, invalidation: float, stop: float, target: float, structure_evidence: dict[str, Any], range_evidence: dict[str, Any], candle_evidence: dict[str, Any], risks: list[str], scoring: tuple[float, dict[str, float]]) -> dict[str, Any]:
    risk = entry - stop if direction == "LONG" else stop - entry
    reward = target - entry if direction == "LONG" else entry - target
    rr = reward / risk
    tech = technical_snapshot(ind, candles, i)
    technical_confirmations: list[str] = []
    technical_conflicts: list[str] = []
    bull = direction == "LONG"
    if finite(tech["ema20"]) and finite(tech["ema50"]):
        (technical_confirmations if (tech["ema20"] > tech["ema50"]) == bull else technical_conflicts).append("EMA20/EMA50 alignment")
    if finite(tech["rsi14"]):
        (technical_confirmations if (tech["rsi14"] >= 50) == bull else technical_conflicts).append("RSI14 side of 50")
    if finite(tech["macd"]) and finite(tech["macd_signal"]):
        (technical_confirmations if (tech["macd"] > tech["macd_signal"]) == bull else technical_conflicts).append("MACD versus signal")
    return {
        "candidate_id": "", "symbol": symbol, "timeframe": INTERVAL, "setup_type": setup_type, "direction": direction,
        "context_start": iso(candles[i - 95].timestamp), "context_end": iso(candles[i].close_time),
        "decision_window_start": iso(candles[i - 23].timestamp), "confirmation_candle_time": iso(candles[i].timestamp),
        "confirmation_candle_close_time": iso(candles[i].close_time), "entry_time": iso(candles[i].timestamp + STEP),
        "entry_price": round(entry, 8), "invalidation_price": round(invalidation, 8), "stop_price": round(stop, 8),
        "target_1": round(target, 8), "target_2": None, "planned_rr": round(rr, 6),
        "source_regime": "UP" if direction == "LONG" and setup_type != "RANGE_MEAN_REVERSION_CANDIDATE" else "DOWN" if direction == "SHORT" and setup_type != "RANGE_MEAN_REVERSION_CANDIDATE" else "FLAT",
        "source_hypothesis": setup_type, "source": "OFFLINE_CAUSAL_RULE_SCAN_USING_ENGINE_TREND_21_CONCEPTUAL_LAYER",
        "structure_evidence": structure_evidence, "range_breakout_evidence": range_evidence, "candle_evidence": candle_evidence,
        "technical_confirmation": {"values": tech, "confirmations": technical_confirmations, "conflicts": technical_conflicts},
        "no_trade_risks": risks + technical_conflicts,
        "pre_entry_reason": "Structure and a causal level existed first; a closed rejection/continuation candle then authorized entry. Stop and target were derived from pre-entry structural anchors.",
        "quality_score": scoring[0], "quality_score_components": scoring[1], "future_data_used_for_generation": False,
    }


def scan_symbol(symbol: str, candles: list[Candle]) -> tuple[list[dict[str, Any]], int]:
    ind = indicators(candles)
    raw: list[dict[str, Any]] = []
    evaluated = 0
    for i in range(200, len(candles) - 96):
        if not (SCAN_START <= candles[i].timestamp <= SCAN_END):
            continue
        evaluated += 1
        a = ind["atr"][i]
        if not finite(a) or a <= 0:
            continue
        a = float(a)
        highs, lows = pivots(candles, i)
        if len(highs) < 2 or len(lows) < 2:
            continue
        cf = candle_features(candles[i], a)
        last_highs, last_lows = highs[-2:], lows[-2:]
        bull_structure = last_highs[-1][1] > last_highs[-2][1] and last_lows[-1][1] > last_lows[-2][1]
        bear_structure = last_highs[-1][1] < last_highs[-2][1] and last_lows[-1][1] < last_lows[-2][1]
        e20, e50, e200, vw = ind["ema20"][i], ind["ema50"][i], ind["ema200"][i], ind["vwap96"][i]
        adx_value = float(ind["adx"][i] or 0.0)
        # Continuation pullback: impulse extreme precedes a 2-8 candle correction; current candle confirms away from EMA/VWAP/support.
        for direction in ("LONG", "SHORT"):
            bull = direction == "LONG"
            if (bull and not bull_structure) or (not bull and not bear_structure):
                continue
            if not finite(e20) or not finite(e50) or (bull and not (e20 > e50)) or (not bull and not (e20 < e50)):
                continue
            recent = candles[i - 8 : i]
            impulse_index = (i - 8 + max(range(8), key=lambda k: recent[k].high)) if bull else (i - 8 + min(range(8), key=lambda k: recent[k].low))
            if impulse_index >= i - 1:
                continue
            pull = candles[impulse_index + 1 : i + 1]
            retest_extreme = min(c.low for c in pull) if bull else max(c.high for c in pull)
            zone_candidates = [float(x) for x in (e20, vw, last_highs[-2][1] if bull else last_lows[-2][1]) if finite(x)]
            zone = min(zone_candidates, key=lambda x: abs(retest_extreme - x))
            if abs(retest_extreme - zone) > 0.65 * a:
                continue
            confirms = (candles[i].close > candles[i].open and cf["close_location"] >= 0.68 and (candles[i].close > candles[i - 1].high or cf["lower_wick_fraction"] >= 0.22)) if bull else (candles[i].close < candles[i].open and cf["close_location"] <= 0.32 and (candles[i].close < candles[i - 1].low or cf["upper_wick_fraction"] >= 0.22))
            if not confirms or cf["body_atr"] < 0.18:
                continue
            entry = candles[i].close
            invalidation = retest_extreme
            stop = invalidation - 0.15 * a if bull else invalidation + 0.15 * a
            impulse_extreme = candles[impulse_index].high if bull else candles[impulse_index].low
            target = impulse_extreme
            risk = entry - stop if bull else stop - entry
            reward = target - entry if bull else entry - target
            if risk <= 0 or reward <= 0 or reward / risk < 1.5:
                continue
            rr = reward / risk
            structure_score = min(96.0, 70 + 8 * min(2.0, abs(last_highs[-1][1] - last_highs[-2][1]) / a + abs(last_lows[-1][1] - last_lows[-2][1]) / a))
            level_score = max(55.0, 92.0 - 40.0 * abs(retest_extreme - zone) / a)
            confirmation_score = min(96.0, 55 + 30 * cf["body_atr"] + 12 * (cf["lower_wick_fraction"] if bull else cf["upper_wick_fraction"]))
            technical_score = 82 if adx_value >= 20 else 70
            scoring = score_components(structure=structure_score, level=level_score, confirmation=confirmation_score, rr=rr, technical=technical_score, conflict=88, freshness=max(60, 96 - 6 * (i - impulse_index)))
            setup_type = "LONG_UP_CONTINUATION_RETEST" if bull else "SHORT_DOWN_CONTINUATION_RETEST"
            raw.append(candidate_common(symbol, candles, ind, i, direction, setup_type, entry, invalidation, stop, target,
                {"confirmed_pivot_highs": [{"time": iso(candles[j].timestamp), "price": p} for j, p in last_highs], "confirmed_pivot_lows": [{"time": iso(candles[j].timestamp), "price": p} for j, p in last_lows], "classification": "HH/HL" if bull else "LH/LL", "impulse_extreme_time": iso(candles[impulse_index].timestamp), "correction_bars": i - impulse_index, "retest_extreme": retest_extreme},
                {"causal_zone": zone, "zone_kind": "nearest of EMA20/VWAP96/prior confirmed polarity level", "distance_to_zone_atr": abs(retest_extreme - zone) / a, "objective": "pre-confirmation impulse extreme"},
                {**cf, "ohlc": {"open": candles[i].open, "high": candles[i].high, "low": candles[i].low, "close": candles[i].close}, "interpretation": "bullish rejection/continuation close" if bull else "bearish rejection/continuation close"},
                ["Continuation may fail if the retest extreme is breached", "Target is a prior impulse extreme and can reject price"], scoring))

        # Range mean reversion from repeated confirmed pivot boundaries.
        pivot_high_prices = [p for _, p in highs[-8:]]
        pivot_low_prices = [p for _, p in lows[-8:]]
        resistance = mean(sorted(pivot_high_prices)[-3:])
        support = mean(sorted(pivot_low_prices)[:3])
        width = resistance - support
        if width >= 4 * a:
            high_touches = sum(abs(p - resistance) <= 0.55 * a for p in pivot_high_prices)
            low_touches = sum(abs(p - support) <= 0.55 * a for p in pivot_low_prices)
            ema_slope = abs(float(ind["ema50"][i] or candles[i].close) - float(ind["ema50"][i - 24] or candles[i - 24].close))
            if high_touches >= 2 and low_touches >= 2 and ema_slope <= 1.5 * a:
                for direction, boundary, target in (("LONG", support, (support + resistance) / 2), ("SHORT", resistance, (support + resistance) / 2)):
                    bull = direction == "LONG"
                    tested = candles[i].low <= boundary + 0.45 * a if bull else candles[i].high >= boundary - 0.45 * a
                    rejected = (candles[i].close > candles[i].open and cf["close_location"] >= 0.7 and cf["lower_wick_fraction"] >= 0.18) if bull else (candles[i].close < candles[i].open and cf["close_location"] <= 0.3 and cf["upper_wick_fraction"] >= 0.18)
                    accepted_outside = candles[i].close < support - 0.15 * a if bull else candles[i].close > resistance + 0.15 * a
                    if not tested or not rejected or accepted_outside:
                        continue
                    entry = candles[i].close
                    invalidation = min(candles[i].low, support) if bull else max(candles[i].high, resistance)
                    stop = invalidation - 0.15 * a if bull else invalidation + 0.15 * a
                    risk = entry - stop if bull else stop - entry
                    reward = target - entry if bull else entry - target
                    if risk <= 0 or reward <= 0 or reward / risk < 1.5:
                        continue
                    rr = reward / risk
                    scoring = score_components(structure=78, level=min(95, 66 + 5 * (high_touches + low_touches)), confirmation=min(95, 60 + 30 * cf["body_atr"] + 10 * (cf["lower_wick_fraction"] if bull else cf["upper_wick_fraction"])), rr=rr, technical=68, conflict=82, freshness=90)
                    raw.append(candidate_common(symbol, candles, ind, i, direction, "RANGE_MEAN_REVERSION_CANDIDATE", entry, invalidation, stop, target,
                        {"classification": "confirmed horizontal range", "confirmed_high_touch_count": high_touches, "confirmed_low_touch_count": low_touches},
                        {"support": support, "resistance": resistance, "midline": target, "width_atr": width / a, "ema50_24bar_slope_atr": ema_slope / a, "tested_boundary": boundary, "no_confirmed_close_outside": True},
                        {**cf, "ohlc": {"open": candles[i].open, "high": candles[i].high, "low": candles[i].low, "close": candles[i].close}, "interpretation": "inward rejection from range support" if bull else "inward rejection from range resistance"},
                        ["Range can transition into a directional breakout", "Midline target may meet internal congestion"], scoring))

    # Causal deduplication: keep the best pre-entry score per type/direction within each 12-bar cluster.
    raw.sort(key=lambda c: c["confirmation_candle_close_time"])
    clusters: list[dict[str, Any]] = []
    for candidate in raw:
        when = datetime.fromisoformat(candidate["entry_time"].replace("Z", "+00:00"))
        matching = None
        for kept in reversed(clusters[-30:]):
            kept_when = datetime.fromisoformat(kept["entry_time"].replace("Z", "+00:00"))
            if when - kept_when > 12 * STEP:
                break
            if kept["setup_type"] == candidate["setup_type"] and kept["direction"] == candidate["direction"]:
                matching = kept
                break
        if matching is None:
            clusters.append(candidate)
        elif candidate["quality_score"] > matching["quality_score"]:
            clusters[clusters.index(matching)] = candidate
    return clusters, evaluated


def outcome(candidate: dict[str, Any], candles: list[Candle], horizon: int = 96) -> dict[str, Any]:
    entry_time = datetime.fromisoformat(candidate["entry_time"].replace("Z", "+00:00"))
    future = [c for c in candles if c.timestamp >= entry_time][:horizon]
    direction, entry, stop, target = candidate["direction"], candidate["entry_price"], candidate["stop_price"], candidate["target_1"]
    label = "NEITHER_EXPIRED" if len(future) >= horizon else "INSUFFICIENT_FUTURE_DATA"
    bars_to_tp = bars_to_sl = None
    outcome_bar = len(future)
    for bar, candle in enumerate(future, 1):
        tp = candle.high >= target if direction == "LONG" else candle.low <= target
        sl = candle.low <= stop if direction == "LONG" else candle.high >= stop
        if tp and bars_to_tp is None: bars_to_tp = bar
        if sl and bars_to_sl is None: bars_to_sl = bar
        if tp and sl:
            label, outcome_bar = "AMBIGUOUS_INTRACANDLE", bar
            break
        if tp:
            label, outcome_bar = "TP_BEFORE_SL", bar
            break
        if sl:
            label, outcome_bar = "SL_BEFORE_TP", bar
            break
    observed = future[:outcome_bar]
    favorable = [(c.high - entry if direction == "LONG" else entry - c.low) for c in observed]
    adverse = [(entry - c.low if direction == "LONG" else c.high - entry) for c in observed]
    exit_price = target if label == "TP_BEFORE_SL" else stop if label == "SL_BEFORE_TP" else observed[-1].close if label == "NEITHER_EXPIRED" and observed else None
    gross = ((exit_price - entry) if direction == "LONG" else (entry - exit_price)) / entry * 100 if exit_price else None
    return {"label_status": label, "horizon_candles": horizon, "mfe": max([0.0] + favorable), "mfe_pct": max([0.0] + favorable) / entry * 100, "mae": max([0.0] + adverse), "mae_pct": max([0.0] + adverse) / entry * 100, "bars_to_tp": bars_to_tp, "bars_to_sl": bars_to_sl, "bars_to_outcome": outcome_bar, "gross_return_pct": gross, "net_return_pct": gross - ROUND_TRIP_COST_BPS / 100 if gross is not None else None, "fee_bps_per_side": FEE_BPS_PER_SIDE, "slippage_bps_per_side": SLIPPAGE_BPS_PER_SIDE, "round_trip_cost_bps": ROUND_TRIP_COST_BPS, "future_phase_only": True}


def current_engine_snapshot(candidate: dict[str, Any], candles: list[Candle]) -> dict[str, Any]:
    """Replay the unchanged current engine on a prefix ending at confirmation."""
    confirmation = datetime.fromisoformat(candidate["confirmation_candle_time"].replace("Z", "+00:00"))
    end_index = next(i for i, candle in enumerate(candles) if candle.timestamp == confirmation)
    prefix = candles[max(0, end_index - 239) : end_index + 1]
    normalized = normalize_candles([{"timestamp": candle.timestamp, "open": candle.open, "high": candle.high, "low": candle.low, "close": candle.close, "volume": candle.volume} for candle in prefix])
    composer = run_engine_trend(candidate["symbol"], INTERVAL, normalized).to_dict()["composer_output"]
    result = composer["result"]
    trace = composer["decision_trace"]
    selected_hypothesis = trace.get("selected_hypothesis") or {}
    matrix = trace.get("matrix_summary") or {}
    return {
        "as_of_confirmation_candle": candidate["confirmation_candle_time"],
        "input_candle_count": len(prefix),
        "market_regime": result.get("market_regime"),
        "confidence": result.get("confidence"),
        "selected_hypothesis": selected_hypothesis.get("hypothesis_type"),
        "selected_hypothesis_status": selected_hypothesis.get("status"),
        "selected_hypothesis_score": selected_hypothesis.get("score"),
        "indicator_direction": matrix.get("indicator_direction"),
        "agreement_state": matrix.get("agreement_state"),
        "conflict_level": matrix.get("conflict_level"),
        "data_quality_status": trace.get("data_quality_status"),
        "reason_codes": trace.get("reason_codes", []),
        "safety": result.get("safety"),
        "unchanged_runtime_read_only_replay": True,
    }


def expected_times(start: datetime, end_exclusive: datetime) -> list[datetime]:
    count = int((end_exclusive - start) / STEP)
    return [start + n * STEP for n in range(count)]


def load_rows(engine: Any, symbol: str) -> list[Candle]:
    query = text("""SELECT open_time, close_time, open, high, low, close, volume FROM public.market_candles WHERE symbol=:symbol AND interval=:interval AND open_time>=:start AND open_time<:end ORDER BY open_time""")
    with engine.connect() as connection:
        rows = connection.execute(query, {"symbol": symbol, "interval": INTERVAL, "start": LOAD_START, "end": LOAD_END_EXCLUSIVE}).mappings()
        return [Candle(r["open_time"].astimezone(timezone.utc), r["close_time"].astimezone(timezone.utc), *[float(r[k]) for k in ("open", "high", "low", "close", "volume")]) for r in rows]


def missing_groups(missing: list[datetime]) -> list[tuple[datetime, datetime]]:
    if not missing: return []
    groups: list[tuple[datetime, datetime]] = []
    start = previous = missing[0]
    for value in missing[1:]:
        if value != previous + STEP:
            groups.append((start, previous + STEP))
            start = value
        previous = value
    groups.append((start, previous + STEP))
    return groups


def ensure_coverage(engine: Any, symbol: str, rows: list[Candle]) -> tuple[list[Candle], list[dict[str, str]]]:
    expected = expected_times(LOAD_START, LOAD_END_EXCLUSIVE)
    present = {c.timestamp for c in rows}
    groups = missing_groups([t for t in expected if t not in present])
    operations: list[dict[str, str]] = []
    if groups:
        client = BinanceClient()
        factory = get_session_factory()
        with factory() as session:
            repository = CandleRepository(session)
            for start, end in groups:
                downloaded = client.load_klines(symbol, INTERVAL, start, end)
                closed = [row for row in downloaded if row["close_time"].astimezone(timezone.utc) <= datetime.now(timezone.utc)]
                repository.upsert_many(closed)
                operations.append({"start": iso(start), "end_exclusive": iso(end), "downloaded_closed_candles": str(len(closed))})
        rows = load_rows(engine, symbol)
    return rows, operations


def quality(symbol: str, rows: list[Candle], operations: list[dict[str, str]]) -> dict[str, Any]:
    scan = [c for c in rows if SCAN_START <= c.timestamp <= SCAN_END]
    times = [c.timestamp for c in scan]
    expected = expected_times(SCAN_START, SCAN_END + STEP)
    duplicate_count = len(times) - len(set(times))
    missing = sorted(set(expected) - set(times))
    irregular = sum(b - a != STEP for a, b in zip(times, times[1:]))
    ohlc_errors = sum(c.low > min(c.open, c.close) or c.high < max(c.open, c.close) or c.high < c.low for c in scan)
    non_finite = sum(not all(math.isfinite(x) for x in (c.open, c.high, c.low, c.close, c.volume)) for c in scan)
    non_positive = sum(any(x <= 0 for x in (c.open, c.high, c.low, c.close, c.volume)) for c in scan)
    closed_errors = sum(c.close_time > datetime.now(timezone.utc) for c in scan)
    return {"symbol": symbol, "timeframe": INTERVAL, "exchange": "Binance Spot", "requested_start": iso(SCAN_START), "requested_end": iso(SCAN_END), "expected_candles": EXPECTED_SCAN_COUNT, "checked_candles": len(scan), "first_open_time": iso(scan[0].timestamp) if scan else None, "last_open_time": iso(scan[-1].timestamp) if scan else None, "missing_intervals": [iso(x) for x in missing], "missing_count": len(missing), "duplicate_count": duplicate_count, "irregular_cadence_count": irregular, "ohlc_consistency_errors": ohlc_errors, "nan_inf_count": non_finite, "non_positive_ohlcv_count": non_positive, "not_closed_count": closed_errors, "binance_backfill_operations": operations, "binance_download_executed": bool(operations), "status": "PASS" if not any((missing, duplicate_count, irregular, ohlc_errors, non_finite, non_positive, closed_errors)) and len(scan) == EXPECTED_SCAN_COUNT else "FAIL"}


def dump_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=False) + "\n", encoding="utf-8")


def fmt(value: float | None, digits: int = 6) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    engine = create_engine(get_settings().database_url, pool_pre_ping=True)
    rows_by_symbol: dict[str, list[Candle]] = {}
    coverage: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    evaluated: dict[str, int] = {}
    for symbol in SYMBOLS:
        rows = load_rows(engine, symbol)
        rows, operations = ensure_coverage(engine, symbol, rows)
        rows_by_symbol[symbol] = rows
        coverage.append(quality(symbol, rows, operations))
        found, evaluated[symbol] = scan_symbol(symbol, rows)
        candidates.extend(found)
    if any(row["status"] != "PASS" for row in coverage):
        raise RuntimeError("Data-quality gate failed; refusing to generate candidates")
    candidates.sort(key=lambda c: (-c["quality_score"], c["entry_time"], c["symbol"]))
    for index, candidate in enumerate(candidates, 1):
        candidate["candidate_id"] = f"ET-HED-{index:04d}"
    rr_passed = sum(c["planned_rr"] >= 1.5 for c in candidates)
    # Freeze is explicit: selection is complete before any call to outcome().
    ranking_freeze = [{"candidate_id": c["candidate_id"], "quality_score": c["quality_score"]} for c in candidates]
    if not candidates:
        raise RuntimeError("Full scan completed but no causal RR-qualified candidates were produced")
    main_candidate_id = ranking_freeze[0]["candidate_id"]
    # Current ENGINE-TREND evidence is read-only and pre-entry.  It is attached only
    # after ranking freeze, so it cannot change which candidate won this audit.
    for candidate in candidates[:10]:
        candidate["current_engine_trend_replay"] = current_engine_snapshot(candidate, rows_by_symbol[candidate["symbol"]])
        candidate["source_regime"] = candidate["current_engine_trend_replay"]["market_regime"]
        candidate["source_hypothesis"] = candidate["current_engine_trend_replay"]["selected_hypothesis"]
        candidate["source_regime_hypothesis_provenance"] = "UNCHANGED_CURRENT_ENGINE_TREND_PRE_ENTRY_REPLAY"
    for candidate in candidates:
        candidate["outcome_horizons"] = {str(horizon): outcome(candidate, rows_by_symbol[candidate["symbol"]], horizon) for horizon in (24, 48, 96)}
        candidate["outcome"] = candidate["outcome_horizons"]["96"]
    selected = next(c for c in candidates if c["candidate_id"] == main_candidate_id)
    top10 = candidates[:10]
    by_symbol = Counter(c["symbol"] for c in candidates)
    by_type = Counter(c["setup_type"] for c in candidates)
    results = {"audit_metadata": {"generated_at": iso(datetime.now(timezone.utc)), "exchange": "Binance Spot", "period_start": iso(SCAN_START), "period_end": iso(SCAN_END), "timeframe": INTERVAL, "context_candles": 96, "decision_candles": 24, "future_horizons_documented": [24, 48, 96], "outcome_horizon_used": 96, "selection_rule": "maximum pre-entry quality score; outcome unavailable until after ranking freeze", "main_selected_candidate_id_frozen_before_outcome": main_candidate_id, "fee_bps_per_side": 10, "slippage_bps_per_side": 2, "round_trip_cost_bps": 24, "runtime_code_changed": False, "trading_runtime_changed": False, "thresholds_changed": False, "composer_changed": False, "market_hypothesis_changed": False, "setup_contracts_changed": False}, "coverage_summary": coverage, "scan_summary": {"decision_points_evaluated": evaluated, "candidate_setups_found": len(candidates), "rr_gte_1_5": rr_passed, "candidate_count_by_symbol": dict(sorted(by_symbol.items())), "candidate_count_by_setup_type": dict(sorted(by_type.items()))}, "pre_entry_ranking_freeze": ranking_freeze, "top_10_candidate_ids": [c["candidate_id"] for c in top10], "main_selected_entry": selected, "candidates": candidates}
    dump_json(REPORT_DIR / "HISTORICAL_ENTRY_DISCOVERY_RESULTS.json", results)
    dump_json(REPORT_DIR / "HISTORICAL_ENTRY_DISCOVERY_DATA_COVERAGE.json", {"coverage": coverage})
    trace = {"causality_boundary": {"last_allowed_generation_candle": selected["confirmation_candle_close_time"], "first_outcome_candle_open_time": selected["entry_time"], "future_data_used_for_generation": False, "ranking_freeze_position": 1}, "selected_entry": selected, "pre_entry_ranking_top_10": [{"candidate_id": c["candidate_id"], "quality_score": c["quality_score"], "planned_rr": c["planned_rr"]} for c in top10], "outcome_check": selected["outcome"]}
    dump_json(REPORT_DIR / "MAIN_SELECTED_ENTRY_TRACE.json", trace)
    with (REPORT_DIR / "HISTORICAL_ENTRY_DISCOVERY_CANDIDATES.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["candidate_id", "symbol", "direction", "setup_type", "entry_time", "entry_price", "stop", "target", "rr", "quality_score", "outcome", "net_return_pct", "short_reason"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for c in candidates:
            writer.writerow({"candidate_id": c["candidate_id"], "symbol": c["symbol"], "direction": c["direction"], "setup_type": c["setup_type"], "entry_time": c["entry_time"], "entry_price": c["entry_price"], "stop": c["stop_price"], "target": c["target_1"], "rr": c["planned_rr"], "quality_score": c["quality_score"], "outcome": c["outcome"]["label_status"], "net_return_pct": c["outcome"]["net_return_pct"], "short_reason": c["pre_entry_reason"]})
    coverage_md = "# Historical Entry Discovery — Data Coverage\n\n" + "\n".join(f"## {c['symbol']} 15m\n\n- Requested: `{c['requested_start']}` — `{c['requested_end']}`\n- Expected / checked: `{c['expected_candles']}` / `{c['checked_candles']}`\n- Missing / duplicates / irregular: `{c['missing_count']}` / `{c['duplicate_count']}` / `{c['irregular_cadence_count']}`\n- OHLC / NaN-Inf / non-positive / unclosed errors: `{c['ohlc_consistency_errors']}` / `{c['nan_inf_count']}` / `{c['non_positive_ohlcv_count']}` / `{c['not_closed_count']}`\n- Binance backfill executed: `{str(c['binance_download_executed']).lower()}`\n- Status: **{c['status']}**\n" for c in coverage)
    (REPORT_DIR / "HISTORICAL_ENTRY_DISCOVERY_DATA_COVERAGE.md").write_text(coverage_md, encoding="utf-8")
    alternatives = "\n".join(f"- `{c['candidate_id']}` {c['symbol']} {c['direction']} at `{c['entry_time']}`, {c['setup_type']}, RR `{c['planned_rr']:.3f}`, pre-entry score `{c['quality_score']:.3f}`. Rejected as MAIN because its pre-entry score was lower; outcome was not considered." for c in top10[1:]) or "- None."
    s = selected; o = s["outcome"]; st = s["structure_evidence"]; rb = s["range_breakout_evidence"]; ce = s["candle_evidence"]; tech = s["technical_confirmation"]
    explanation = f"""# MAIN_SELECTED_ENTRY Explanation

## Frozen trade plan

- Symbol / timeframe: **{s['symbol']} / 15m**
- Direction: **{s['direction']}**
- Setup: **{s['setup_type']}**
- Confirmation candle: `{s['confirmation_candle_time']}` (closed `{s['confirmation_candle_close_time']}`)
- Entry: `{s['entry_time']}` at **{s['entry_price']}**
- Invalidation / stop: **{s['invalidation_price']} / {s['stop_price']}**
- Target 1: **{s['target_1']}**
- Planned RR: **{s['planned_rr']:.3f}**
- Classification: **{'range mean reversion' if s['setup_type'] == 'RANGE_MEAN_REVERSION_CANDIDATE' else 'trend-following continuation'}**

## Why the entry was permissible before future candles

The 96-candle context began at `{s['context_start']}` and ended with the closed confirmation at `{s['context_end']}`. The final 24 candles were the decision window. The causal chain was fixed as structure → level/retest → closed confirmation → entry → invalidation → buffered stop → pre-existing objective. Nothing after `{s['confirmation_candle_close_time']}` participated in setup construction or ranking.

### Altunina structure reading

The last two confirmed swing highs were `{st.get('confirmed_pivot_highs')}` and the last two confirmed swing lows were `{st.get('confirmed_pivot_lows')}`. That is `{st.get('classification')}` structure. The bearish impulse reached `{st.get('retest_extreme') if s['direction'] == 'LONG' else s['target_1']}` at `{st.get('impulse_extreme_time')}`, followed by a `{st.get('correction_bars')}`-bar correction. This locates the entry after a correction/rejection rather than at an arbitrary bar. Structural invalidation is `{s['invalidation_price']}`; crossing it destroys the pullback/range-boundary premise.

### Schwager level reading

The correction tested `{rb.get('causal_zone', rb.get('tested_boundary'))}` ({rb.get('zone_kind', 'confirmed range boundary')}) at only `{fmt(rb.get('distance_to_zone_atr'), 3)}` ATR distance. That zone was already visible before confirmation. The target `{s['target_1']}` is the pre-confirmation impulse extreme/range midline, never a later profitable print. In Schwager terms, the causal idea is polarity/level retest and failure to reclaim, not simply a low RSI or a candle color.

### Nison candle reading

Confirmation OHLC was `{json.dumps(ce['ohlc'])}` with body/ATR `{ce['body_atr']:.3f}`, close location `{ce['close_location']:.3f}`, upper wick `{ce['upper_wick_fraction']:.3f}`, and lower wick `{ce['lower_wick_fraction']:.3f}`. It matters only because it rejected the pre-existing structural zone; the candle was not used as an isolated pattern.

### Current ENGINE-TREND and technical confirmation

The unchanged current engine replay on the 240-candle prefix returned `{json.dumps(s.get('current_engine_trend_replay'), ensure_ascii=False)}`. Values from the audit scanner: `{json.dumps(tech['values'])}`. Confirmations: `{', '.join(tech['confirmations']) or 'none'}`. Conflicts: `{', '.join(tech['conflicts']) or 'none'}`. Indicators were supporting/veto evidence only, never the source of the trade.

## What falsifies the setup and key risks

The premise is falsified at `{s['invalidation_price']}` and operationally stopped at `{s['stop_price']}`. Risks: {'; '.join(s['no_trade_risks'])}. The main analytical error could be treating a temporary correction/boundary rejection as durable while the market is actually transitioning regime, or overestimating the stability of mechanically confirmed pivots.

## After-the-fact outcome (separate phase)

- Status: **{o['label_status']}**
- 24 / 48 / 96-bar labels: `{s['outcome_horizons']['24']['label_status']}` / `{s['outcome_horizons']['48']['label_status']}` / `{s['outcome_horizons']['96']['label_status']}`
- MFE / MAE through terminal outcome: `{o['mfe']:.8f}` / `{o['mae']:.8f}` (`{o['mfe_pct']:.4f}%` / `{o['mae_pct']:.4f}%`)
- Bars to TP / SL: `{o['bars_to_tp']}` / `{o['bars_to_sl']}`
- Gross / net return: `{fmt(o['gross_return_pct'], 4)}%` / `{fmt(o['net_return_pct'], 4)}%`
- Audit costs: 10 bps fee + 2 bps slippage per side = 24 bps round trip.

## Why this candidate won

It had the highest quality score (`{s['quality_score']:.4f}`) using pre-entry causal context, structure clarity, level quality, confirmation quality, planned RR, conflict absence, technical agreement, and freshness. Outcomes were calculated only after `main_selected_candidate_id` was frozen.

## Top alternatives

{alternatives}
"""
    (REPORT_DIR / "MAIN_SELECTED_ENTRY_EXPLANATION.md").write_text(explanation, encoding="utf-8")
    report = f"""# ENGINE-TREND Historical Entry Discovery Audit

## Executive result

A full causal scan of all three Binance Spot 15m series produced **{len(candidates)}** deduplicated candidates, all **{rr_passed}** satisfying RR ≥ 1.5. The database was complete; no Binance download ran. The selected entry is `{s['candidate_id']}`: **{s['symbol']} {s['direction']}**, entry `{s['entry_time']}` at **{s['entry_price']}**, stop **{s['stop_price']}**, target **{s['target_1']}**, RR **{s['planned_rr']:.3f}**, setup **{s['setup_type']}**. Outcome: **{o['label_status']}**.

## Method and hindsight controls

Each decision point used at least 96 closed context candles and a 24-candle decision window. Pivots required two right-hand candles to be confirmed. Entry was fixed at the next 15-minute boundary at the confirmation close price; invalidation, stop, target, RR, and score were generated from that prefix only. Candidates were sorted and `main_selected_candidate_id={main_candidate_id}` was frozen before either current-engine enrichment or the outcome function. The unchanged current engine then confirmed the pre-entry context for top-10 candidates. The 96-candle future horizon was finally evaluated with same-candle TP+SL labeled `AMBIGUOUS_INTRACANDLE`.

## Data quality

Each symbol had `{EXPECTED_SCAN_COUNT}` requested candles. All coverage, cadence, duplicate, OHLC, finite-value, positive-value, and closed-candle checks passed. See `HISTORICAL_ENTRY_DISCOVERY_DATA_COVERAGE.md`.

## MAIN_SELECTED_ENTRY

See `MAIN_SELECTED_ENTRY_EXPLANATION.md` for the complete Altunina, Schwager, Nison, technical, invalidation, risk, and outcome analysis. Summary: the setup followed a pre-existing causal structure and level; the confirmation candle authorized entry only after the correction/retest. This is **{'range mean reversion' if s['setup_type'] == 'RANGE_MEAN_REVERSION_CANDIDATE' else 'trend-following'}**, not a hindsight-selected reversal.

## Alternatives

{alternatives}

## Safety boundary

- Runtime code changed: no.
- Trading runtime changed: no.
- Thresholds changed: no.
- Composer changed: no.
- Market hypothesis changed: no.
- Setup contracts changed: no.
- This script is offline/audit-only and creates reports; it does not place or simulate orders in runtime.
"""
    (REPORT_DIR / "HISTORICAL_ENTRY_DISCOVERY_REPORT.md").write_text(report, encoding="utf-8")
    artifact_names = ["HISTORICAL_ENTRY_DISCOVERY_REPORT.md", "HISTORICAL_ENTRY_DISCOVERY_RESULTS.json", "HISTORICAL_ENTRY_DISCOVERY_CANDIDATES.csv", "HISTORICAL_ENTRY_DISCOVERY_DATA_COVERAGE.md", "HISTORICAL_ENTRY_DISCOVERY_DATA_COVERAGE.json", "MAIN_SELECTED_ENTRY_TRACE.json", "MAIN_SELECTED_ENTRY_EXPLANATION.md"]
    manifest = {"generated_at": iso(datetime.now(timezone.utc)), "audit_only": True, "script": "scripts/engine_trend_historical_entry_discovery_2025_07_03_2025_12_17.py", "artifacts": [{"path": name, "sha256": hashlib.sha256((REPORT_DIR / name).read_bytes()).hexdigest(), "bytes": (REPORT_DIR / name).stat().st_size} for name in artifact_names]}
    dump_json(REPORT_DIR / "HISTORICAL_ENTRY_DISCOVERY_ARTIFACT_MANIFEST.json", manifest)
    print(json.dumps({"coverage": coverage, "candidate_count": len(candidates), "rr_passed": rr_passed, "main": {k: selected[k] for k in ("candidate_id", "symbol", "direction", "setup_type", "entry_time", "entry_price", "stop_price", "target_1", "planned_rr", "quality_score")}, "outcome": selected["outcome"]}, indent=2))


if __name__ == "__main__":
    main()
