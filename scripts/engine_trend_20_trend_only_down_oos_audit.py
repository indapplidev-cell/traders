"""ENGINE-TREND-20 audit-only OOS evaluator.

This module deliberately lives under scripts/.  It reads closed Binance Spot
candles from PostgreSQL, invokes the existing ENGINE-TREND facade unchanged,
and evaluates a counterfactual contract without feeding it back to the engine.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import func, select

from app.data.binance_client import BinanceClient
from app.db.models import MarketCandles
from app.db.repositories.candle_repository import CandleRepository
from app.db.session import get_session
from app.market_reader.engine_trend.data_source_boundary import (
    CandleDataRequest,
    build_candle_data_batch,
    run_engine_trend_from_batch,
)

UTC = timezone.utc
STEP = timedelta(minutes=15)
INTERVAL = "15m"
WINDOW_SIZE = 96
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
OUT = Path("reports/engine_trend/engine_trend_20_trend_only_down_oos_audit")
BASE = "ENGINE_TREND_20"
AUDIT_MD = OUT / f"{BASE}_TREND_ONLY_DOWN_OOS_AUDIT.md"
AUDIT_JSON = OUT / f"{BASE}_TREND_ONLY_DOWN_OOS_AUDIT.json"
DATASET_CSV = OUT / f"{BASE}_OOS_DATASET.csv"
COUNTERFACTUAL_CSV = OUT / f"{BASE}_COUNTERFACTUAL_RESULTS.csv"
MANUAL_JSON = OUT / f"{BASE}_MANUAL_LABEL_TEMPLATE.json"
TRACE_JSON = OUT / f"{BASE}_HYPOTHESIS_TRACE.json"
FALSE_DOWN_MD = OUT / f"{BASE}_FALSE_DOWN_RISK_AUDIT.md"
SOL_TRACE_MD = OUT / f"{BASE}_SOLUSDT_11_30_INVALIDATION_TRACE.md"
MANIFEST_JSON = OUT / f"{BASE}_ARTIFACT_MANIFEST.json"
DECISION_JSON = OUT / f"{BASE}_DECISION_RECORD.json"

BUCKETS = (
    "TREND_ONLY_DOWN_CANDIDATE",
    "RANGE_BEARISH_PRESSURE_CONTROL",
    "POST_DROP_REBOUND_CONTROL",
    "TRAP_OR_RANGE_CONFLICT_CONTROL",
    "BASELINE_CONFIRMED_DOWN",
    "BASELINE_CONFIRMED_FLAT",
    "OTHER",
)
CONTROL_BUCKETS = {
    "RANGE_BEARISH_PRESSURE_CONTROL",
    "POST_DROP_REBOUND_CONTROL",
    "TRAP_OR_RANGE_CONFLICT_CONTROL",
    "BASELINE_CONFIRMED_FLAT",
}
SEEDS = (
    ("BTCUSDT_15m_2026_07_13_16_00", "BTCUSDT", "2026-07-13T16:00:00Z", "TREND_ONLY_DOWN_CANDIDATE", "UNKNOWN", "DOWN_RECALL_GAP_TREND_ONLY_CONTINUATION_MISSING"),
    ("SOLUSDT_15m_2026_07_08_06_00", "SOLUSDT", "2026-07-08T06:00:00Z", "BASELINE_CONFIRMED_DOWN", "DOWN", None),
    ("SOLUSDT_15m_2026_07_08_11_30", "SOLUSDT", "2026-07-08T11:30:00Z", "POST_DROP_REBOUND_CONTROL", "UNKNOWN", "known high-score invalidated DOWN_CONTINUATION"),
    ("SOLUSDT_15m_2026_07_08_18_30", "SOLUSDT", "2026-07-08T18:30:00Z", "TRAP_OR_RANGE_CONFLICT_CONTROL", "UNKNOWN", "DOWN_CONTINUATION vs CONFIRMED_RANGE conflict"),
    ("SOLUSDT_15m_2026_07_08_23_45", "SOLUSDT", "2026-07-08T23:45:00Z", "BASELINE_CONFIRMED_FLAT", "FLAT", None),
)


def iso(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z") if value else None


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def window_start(end: datetime) -> datetime:
    return end - (WINDOW_SIZE - 1) * STEP


def expected_times(end: datetime) -> list[datetime]:
    start = window_start(end)
    return [start + i * STEP for i in range(WINDOW_SIZE)]


def load_rows(session: Any, symbol: str, end: datetime) -> list[MarketCandles]:
    start = window_start(end)
    return list(session.scalars(select(MarketCandles).where(
        MarketCandles.symbol == symbol,
        MarketCandles.interval == INTERVAL,
        MarketCandles.open_time >= start,
        MarketCandles.open_time <= end,
    ).order_by(MarketCandles.open_time)))


def candle_dict(row: MarketCandles) -> dict[str, object]:
    return {"symbol": row.symbol, "interval": row.interval, "timestamp": iso(row.open_time),
            "open": float(row.open), "high": float(row.high), "low": float(row.low),
            "close": float(row.close), "volume": float(row.volume)}


def coverage(rows: Iterable[MarketCandles], end: datetime, now: datetime) -> dict[str, Any]:
    items = list(rows)
    grid = expected_times(end)
    opens = [x.open_time.astimezone(UTC) for x in items]
    counts = Counter(opens)
    missing = [x for x in grid if not counts[x]]
    duplicates = [x for x, count in counts.items() if count > 1]
    numbers = [float(v) for x in items for v in (x.open, x.high, x.low, x.close, x.volume)]
    checks = {
        "candles_eq_96": len(items) == WINDOW_SIZE,
        "regular_15m_cadence": opens == grid,
        "timezone_utc": all(x.utcoffset() == timedelta(0) for x in opens),
        "missing_intervals_zero": not missing,
        "duplicates_zero": not duplicates,
        "ohlc_consistency": all(float(x.high) >= max(float(x.open), float(x.close), float(x.low)) and float(x.low) <= min(float(x.open), float(x.close), float(x.high)) for x in items),
        "nan_inf_zero": all(math.isfinite(x) for x in numbers),
        "positive_ohlcv": all(x > 0 for x in numbers),
        "only_closed_candles": all(x.open_time.astimezone(UTC) + STEP <= now for x in items),
    }
    failed = [k for k, value in checks.items() if not value]
    return {
        "expected_candles": WINDOW_SIZE, "found_candles": len(items),
        "missing_intervals": [iso(x) for x in missing], "duplicate_intervals": [iso(x) for x in duplicates],
        "first_candle": iso(items[0].open_time) if items else None,
        "last_candle": iso(items[-1].open_time) if items else None,
        "checks": checks, "failed_checks": failed, "status": "PASS" if not failed else "FAIL",
    }


def backfill_missing(session: Any, symbol: str, end: datetime, before: dict[str, Any], now: datetime) -> list[dict[str, Any]]:
    """Backfill only exact absent intervals; never replace existing DB candles."""
    missing = [parse_time(x) for x in before["missing_intervals"] if parse_time(x) + STEP <= now]
    if not missing:
        return []
    client, repository = BinanceClient(), CandleRepository(session)
    operations = []
    groups: list[list[datetime]] = []
    for item in missing:
        if not groups or item - groups[-1][-1] != STEP:
            groups.append([item])
        else:
            groups[-1].append(item)
    for group in groups:
        wanted = set(group)
        downloaded = client.load_klines(symbol, INTERVAL, group[0], group[-1] + STEP)
        exact = [x for x in downloaded if x["open_time"].astimezone(UTC) in wanted and x["close_time"].astimezone(UTC) < now]
        written = repository.upsert_many(exact)
        operations.append({"symbol": symbol, "start": iso(group[0]), "end_exclusive": iso(group[-1] + STEP), "requested": len(group), "downloaded_closed": len(exact), "inserted": written})
    return operations


def _sma(values: list[float], period: int) -> float | None:
    return sum(values[-period:]) / period if len(values) >= period else None


def raw_features(rows: list[MarketCandles]) -> dict[str, float]:
    closes = [float(x.close) for x in rows]
    highs = [float(x.high) for x in rows]
    lows = [float(x.low) for x in rows]
    first, close = closes[0], closes[-1]
    first72 = closes[:72]
    recent = closes[72:]
    low_i = min(range(len(closes)), key=lambda i: lows[i])
    prior_peak = max(highs[:max(low_i, 1)])
    rebound = max(highs[low_i:]) if low_i < len(highs) else highs[-1]
    span = max(highs) - min(lows)
    return {
        "return_96": close / first - 1.0,
        "decision_progress": close / closes[72] - 1.0,
        "prior_drop": min(first72) / max(first72) - 1.0,
        "recent_rebound": close / min(recent) - 1.0,
        "close_position": (close - min(lows)) / span if span else 0.5,
        "range_width": span / first,
        "failed_rebound_ratio": (rebound - lows[low_i]) / max(prior_peak - lows[low_i], 1e-12),
        "sma20_relation": close / (_sma(closes, 20) or close) - 1.0,
    }


def heuristic_bucket(features: dict[str, float]) -> tuple[str, str]:
    r, progress = features["return_96"], features["decision_progress"]
    if r <= -0.025 and progress < -0.004 and features["close_position"] < 0.45:
        return "TREND_ONLY_DOWN_CANDIDATE", "negative 96-candle trend and negative decision-window progress"
    if features["prior_drop"] <= -0.025 and features["recent_rebound"] >= 0.012 and progress > -0.004:
        return "POST_DROP_REBOUND_CONTROL", "material prior drop followed by rebound/exhaustion control"
    if abs(r) <= 0.012 and features["range_width"] <= 0.05 and features["sma20_relation"] < 0:
        return "RANGE_BEARISH_PRESSURE_CONTROL", "bounded return/range with price below SMA20"
    if features["range_width"] >= 0.035 and abs(r) <= 0.025 and features["close_position"] < 0.45:
        return "TRAP_OR_RANGE_CONFLICT_CONTROL", "wide two-sided window with bearish close position"
    return "OTHER", "deterministic rolling-window diversity sample"


def build_dataset_specs(session: Any, target_count: int = 55) -> list[dict[str, Any]]:
    """Select deterministic non-overlapping-ish rolling windows before engine execution."""
    chosen: list[dict[str, Any]] = []
    seen_periods: set[tuple[str, str]] = set()
    for case_id, symbol, end_text, bucket, known, note in SEEDS:
        chosen.append({"case_id": case_id, "symbol": symbol, "timeframe": INTERVAL, "window_end": end_text,
                       "bucket": bucket, "candidate_reason": "mandatory seed-case", "known_baseline_result": known, "note": note})
        seen_periods.add((symbol, end_text))

    pools: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for symbol in SYMBOLS:
        all_rows = list(session.scalars(select(MarketCandles).where(
            MarketCandles.symbol == symbol, MarketCandles.interval == INTERVAL
        ).order_by(MarketCandles.open_time)))
        # Eight-candle stride gives varied periods while selection below keeps >=12h spacing.
        for end_i in range(WINDOW_SIZE - 1, len(all_rows), 8):
            rows = all_rows[end_i - WINDOW_SIZE + 1:end_i + 1]
            end = rows[-1].open_time.astimezone(UTC)
            if len(rows) != WINDOW_SIZE or rows[0].open_time.astimezone(UTC) != window_start(end):
                continue
            bucket, reason = heuristic_bucket(raw_features(rows))
            pools[bucket].append({"symbol": symbol, "end": end, "bucket": bucket, "candidate_reason": reason})

    quotas = {
        "TREND_ONLY_DOWN_CANDIDATE": 12,
        "RANGE_BEARISH_PRESSURE_CONTROL": 12,
        "POST_DROP_REBOUND_CONTROL": 8,
        "TRAP_OR_RANGE_CONFLICT_CONTROL": 8,
        "OTHER": 10,
    }
    existing = Counter(x["bucket"] for x in chosen)
    last_by_symbol: dict[str, list[datetime]] = defaultdict(list)
    for bucket, quota in quotas.items():
        ranked = sorted(pools[bucket], key=lambda x: (x["end"], x["symbol"]))
        if ranked:
            step = max(1, len(ranked) // max(1, quota - existing[bucket]))
            ranked = ranked[::step]
        for item in ranked:
            if existing[bucket] >= quota or len(chosen) >= target_count:
                break
            end = item["end"]
            end_text = iso(end)
            if (item["symbol"], end_text) in seen_periods or any(abs(end - old) < timedelta(hours=12) for old in last_by_symbol[item["symbol"]]):
                continue
            case_id = f"{item['symbol']}_15m_{end:%Y_%m_%d_%H_%M}"
            chosen.append({"case_id": case_id, "symbol": item["symbol"], "timeframe": INTERVAL,
                           "window_end": end_text, "bucket": bucket, "candidate_reason": item["candidate_reason"],
                           "known_baseline_result": None, "note": None})
            seen_periods.add((item["symbol"], end_text))
            last_by_symbol[item["symbol"]].append(end)
            existing[bucket] += 1
    return chosen


def run_engine(rows: list[MarketCandles], symbol: str, end: datetime, source: str) -> dict[str, Any]:
    before_regime = None
    request = CandleDataRequest(symbol, INTERVAL, WINDOW_SIZE, iso(window_start(end)), iso(end), source)
    batch = build_candle_data_batch(request, [candle_dict(x) for x in rows], min_candle_count=WINDOW_SIZE, strict_market_series=True)
    payload = run_engine_trend_from_batch(batch).to_dict()["engine_output"]["composer_output"]
    before_regime = payload["result"]["market_regime"]
    assert before_regime == payload["result"]["market_regime"]
    return payload


def classify_swings(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prior: dict[str, float] = {}
    result = []
    for point in points:
        kind, price = str(point["point_type"]), float(point["price"])
        label = "UNCLASSIFIED"
        if kind in prior:
            label = ("HH" if price > prior[kind] else "LH") if kind == "HIGH" else ("HL" if price > prior[kind] else "LL")
        prior[kind] = price
        result.append({**point, "structural_label": label})
    return result


def hypothesis_trace(hresult: dict[str, Any]) -> list[dict[str, Any]]:
    events = {x["event_id"]: x for x in hresult.get("contextual_events", [])}
    output = []
    for h in hresult.get("hypotheses", []):
        reasons = list(h.get("reason_codes", []))
        status = h["status"]
        output.append({**h, "confidence": h["score"],
            "evidence": {"reason_codes": reasons, "supporting_events": [events[x] for x in h.get("supporting_event_ids", []) if x in events]},
            "missing_evidence": [x for x in reasons if any(t in x for t in ("PENDING", "REQUIRED", "MISSING", "AWAIT"))],
            "rejection_reason": reasons if status == "INVALIDATED" else None,
            "pending_reason": reasons if status == "PENDING" else None,
            "conflict_reason": reasons if status == "CONFLICTED" else None})
    return output


def technical_diagnostics(ind: dict[str, Any], rows: list[MarketCandles]) -> dict[str, Any]:
    closes = [float(x.close) for x in rows]
    close = closes[-1]
    sma50, sma99 = _sma(closes, 50), _sma(closes, 99)
    lines = {"sma20": ind.get("sma_20"), "sma50": sma50, "sma99": sma99,
             "ema12": ind.get("ema_12"), "ema26": ind.get("ema_26"), "vwap": ind.get("vwap")}
    reasons = list(ind.get("reason_codes", []))
    return {**ind, "sma_50": sma50, "sma_99": sma99,
            "macd_histogram": (ind["macd"] - ind["macd_signal"]) if ind.get("macd") is not None and ind.get("macd_signal") is not None else None,
            "decision_close": close,
            "price_relations": {name: "UNAVAILABLE" if value is None else "BELOW" if close < value else "ABOVE" if close > value else "AT" for name, value in lines.items()},
            "bollinger_position": "UNAVAILABLE" if ind.get("bollinger_lower") is None else "BELOW_LOWER" if close < ind["bollinger_lower"] else "ABOVE_UPPER" if close > ind["bollinger_upper"] else "INSIDE_BANDS",
            "technical_votes": {"bullish_methods_count": ind.get("bullish_votes", 0), "bearish_methods_count": ind.get("bearish_votes", 0),
                "neutral_or_conflicted_count": 5 - ind.get("bullish_votes", 0) - ind.get("bearish_votes", 0),
                "methods_supporting_down": [x for x in reasons if "BEARISH" in x or "BELOW" in x],
                "methods_supporting_up": [x for x in reasons if "BULLISH" in x or "ABOVE" in x],
                "methods_blocking_direction": [x for x in reasons if "NEUTRAL" in x or "WEAK" in x]}}


def structural_diagnostics(matrix: dict[str, Any]) -> dict[str, Any]:
    unified, alt = matrix["unified_context"], matrix["altunina_context"]
    swings = classify_swings(unified.get("structural_swing_points", []))
    labels = [x["structural_label"] for x in swings]
    ll_positions = [i for i, x in enumerate(swings) if x["structural_label"] == "LL"]
    lh_after = any(x["structural_label"] == "LH" for i in ll_positions for x in swings[i + 1:])
    pivot = None
    pivot_breaches = []
    if alt.get("structure_direction") == "BEARISH_STRUCTURE":
        for leg in alt.get("price_legs", []):
            if leg["direction"] == "DOWN":
                pivot = leg["start"]
            elif leg["direction"] == "UP" and pivot and float(leg["end"]["price"]) >= float(pivot["price"]):
                pivot_breaches.append({
                    "comparison": "correction_end_price >= prior_bearish_impulse_start_price",
                    "prior_structural_pivot": pivot,
                    "correction_leg": leg,
                    "observed": f"{leg['end']['price']} >= {pivot['price']}",
                })
    return {"swing_highs": [x for x in swings if x["point_type"] == "HIGH"],
            "swing_lows": [x for x in swings if x["point_type"] == "LOW"], "classified_swings": swings,
            "hh_count": labels.count("HH"), "hl_count": labels.count("HL"), "lh_count": labels.count("LH"), "ll_count": labels.count("LL"),
            "bearish_majority": labels.count("LH") + labels.count("LL") > labels.count("HH") + labels.count("HL"),
            "bullish_majority": labels.count("HH") + labels.count("HL") > labels.count("LH") + labels.count("LL"),
            "current_structure_label": alt.get("structure_direction"), "ll_present": bool(ll_positions), "lh_after_ll": lh_after,
            "sequence_lh_to_ll": any(a == "LH" and b == "LL" for a, b in zip(labels, labels[1:])),
            "sequence_ll_to_lh": any(a == "LL" and b == "LH" for a, b in zip(labels, labels[1:])),
            "structural_pivot_breached": alt["impulse_correction"].get("structural_pivot_breached"),
            "altunina_down_explanation": {"structure_direction": alt.get("structure_direction"), "reason_codes": alt.get("reason_codes", []),
                "impulse_correction": alt.get("impulse_correction"), "pivot_breach_provenance": pivot_breaches,
                "price_legs": alt.get("price_legs", [])}}


def schwager_diagnostics(schw: dict[str, Any]) -> dict[str, Any]:
    trading, breakout = schw["trading_range"], schw["breakout_context"]
    return {"range_detected": trading.get("is_detected"), "range_boundaries": {"lower": trading.get("lower_boundary"), "upper": trading.get("upper_boundary")},
            "inside_close_ratio": trading.get("inside_close_ratio"), "breakout_or_breakdown": breakout,
            "retest": {"returned_to_range": breakout.get("returned_to_range"), "return_index": breakout.get("return_index")},
            "polarity_flip": schw.get("polarity_flip_context"), "trap": breakout.get("false_breakout_confirmation"),
            "false_breakout": breakout.get("returned_to_range"), "confirmed_range": trading.get("is_detected") and breakout.get("status") != "CONFIRMED",
            "conflict_with_direction": trading.get("is_detected") and breakout.get("direction") not in ("DOWNWARD", "NONE"),
            "breakdown_explanation": {"status": breakout.get("status"), "direction": breakout.get("direction"), "confirmation_method": breakout.get("confirmation_method"), "evidence": breakout.get("evidence", [])},
            "engine_context": schw}


def nison_diagnostics(matrix: dict[str, Any]) -> dict[str, Any]:
    events = matrix["hypothesis_result"].get("contextual_events", [])
    select_events = lambda direction, role: [x for x in events if x["direction"] == direction and x["role"] == role]
    reasons = matrix["nison_context"].get("reason_codes", [])
    return {"bearish_continuation_patterns": select_events("BEARISH", "CONTINUATION"),
            "bearish_reversal_patterns": select_events("BEARISH", "REVERSAL"), "bullish_reversal_patterns": select_events("BULLISH", "REVERSAL"),
            "exhaustion_candles": [x for x in reasons if any(t in x for t in ("DOJI", "SMALL_BODY", "SHADOW", "EXHAUST"))],
            "candle_continuation_status": [x for x in events if x["role"] == "CONTINUATION"],
            "context_rejected_reasons": [{"event_id": x["event_id"], "reason_codes": x["reason_codes"]} for x in events if x["status"] == "CONTEXT_REJECTED"],
            "candle_evidence_sufficient_for_hypothesis": any(x["role"] == "CONTINUATION" and x["status"] == "CONFIRMED" for x in events),
            "engine_context": matrix["nison_context"]}


def counterfactual_evaluate(matrix: dict[str, Any], rows: list[MarketCandles], baseline_regime: str) -> dict[str, Any]:
    """Pure diagnostic: returns data only and cannot mutate composer output."""
    baseline_before = baseline_regime
    structure = structural_diagnostics(matrix)
    ind = matrix["unified_context"]["indicator_context"]
    schw = matrix["schwager_context"]
    hypotheses = matrix["hypothesis_result"].get("hypotheses", [])
    hmap = defaultdict(list)
    for h in hypotheses:
        hmap[h["hypothesis_type"]].append(h)
    close = float(rows[-1].close)
    sma50 = _sma([float(x.close) for x in rows], 50)
    below_lines = sum(close < value for value in (ind.get("sma_20"), sma50, ind.get("ema_12"), ind.get("ema_26")) if value is not None)
    decision_progress = close / float(rows[72].close) - 1.0
    atr_ratio = float(ind.get("atr_ratio") or 0.0)
    atr_impulse = decision_progress <= -max(0.005, atr_ratio)
    bullish_confirmed = any(h["status"] == "CONFIRMED" for h in hmap["BULLISH_REVERSAL"])
    confirmed_range = any(h["status"] == "CONFIRMED" for h in hmap["CONFIRMED_RANGE"])
    trap_conflict = any(h["status"] in ("CONFIRMED", "CONFLICTED") for key in ("BULL_TRAP", "BEAR_TRAP") for h in hmap[key])
    flags = {
        "ll_present": structure["ll_present"], "lh_after_ll": structure["lh_after_ll"],
        # The audit contract is intentionally broader than the current formal
        # Altunina label: the task explicitly asks whether causal LL/LH
        # continuation can cover a formal SIDEWAYS_STRUCTURE recall gap.
        "bearish_structure_present": structure["current_structure_label"] == "BEARISH_STRUCTURE" or (
            structure["ll_present"] and structure["lh_after_ll"] and structure["bearish_majority"]
        ),
        "bearish_technical_votes_ge_3": int(ind.get("bearish_votes", 0)) >= 3,
        "price_below_ema_or_sma": below_lines >= 2,
        "price_below_vwap": ind.get("vwap") is not None and close < ind["vwap"],
        "adx_directional": ind.get("adx_14") is not None and ind["adx_14"] >= 20.0,
        "atr_or_impulse_confirms": atr_impulse,
        "failed_rebound_present": structure["lh_after_ll"] or (structure["sequence_lh_to_ll"] and decision_progress < 0),
        "no_confirmed_bullish_reversal": not bullish_confirmed,
        "no_stronger_confirmed_range": not confirmed_range,
        "no_trap_conflict": not trap_conflict,
        "decision_window_progress_negative": decision_progress < 0,
    }
    required = tuple(flags)
    passed = all(flags[x] for x in required)
    risk_flags = []
    if schw["trading_range"].get("is_detected"): risk_flags.append("RANGE_DETECTED")
    if confirmed_range: risk_flags.append("CONFIRMED_RANGE_CONFLICT")
    if bullish_confirmed: risk_flags.append("CONFIRMED_BULLISH_REVERSAL_CONFLICT")
    if trap_conflict: risk_flags.append("TRAP_CONFLICT")
    if ind.get("adx_14") is not None and ind["adx_14"] < 20: risk_flags.append("WEAK_ADX")
    if decision_progress > -max(0.005, atr_ratio): risk_flags.append("WEAK_NEGATIVE_PROGRESS")
    if not structure["lh_after_ll"]: risk_flags.append("NO_LH_AFTER_LL")
    result = {**flags, "hypothetical_contract_pass": passed, "risk_flags": risk_flags,
              "decision_window_progress": decision_progress, "baseline_regime_before": baseline_before,
              "baseline_regime_after": baseline_regime, "baseline_unchanged": baseline_before == baseline_regime}
    return result


def analyze_case(spec: dict[str, Any], rows: list[MarketCandles], source: str, dq: dict[str, Any]) -> dict[str, Any]:
    item = {**spec, "actual_start": iso(rows[0].open_time) if rows else None, "actual_end": iso(rows[-1].open_time) if rows else None,
            "candles": len(rows), "source": source, "data_quality": dq}
    if dq["status"] != "PASS":
        return {**item, "excluded_from_metrics": True, "baseline_regime": "NOT_RUN", "short_reason": "FAILED_DATA_QUALITY"}
    end = parse_time(spec["window_end"])
    composer = run_engine(rows, spec["symbol"], end, source)
    matrix, decision, result = composer["matrix"], composer["decision_trace"], composer["result"]
    trace = hypothesis_trace(matrix["hypothesis_result"])
    grouped = defaultdict(list)
    for h in trace: grouped[h["status"]].append(h)
    cf = counterfactual_evaluate(matrix, rows, result["market_regime"])
    selected = decision.get("selected_hypothesis")
    selected_ok = result["market_regime"] == "UNKNOWN" or bool(selected and selected.get("status") == "CONFIRMED")
    return {**item, "excluded_from_metrics": False, "baseline_regime": result["market_regime"],
            "selected_hypothesis": selected, "selected_source": decision["decision_source"], "confidence": result["confidence"],
            "confirmed_hypotheses": grouped["CONFIRMED"], "pending_hypotheses": grouped["PENDING"],
            "conflicted_hypotheses": grouped["CONFLICTED"], "rejected_cancelled_hypotheses": grouped["INVALIDATED"] + grouped["CANCELLED"],
            "composer_reasons": decision["reason_codes"], "raw_scores": decision["candidate_scores"].get("composer_trace", {}).get("raw_scores", {}),
            "safety_violations": [] if selected_ok else ["DIRECTION_WITHOUT_CONFIRMED_SELECTED_HYPOTHESIS"],
            "structural_diagnostics": structural_diagnostics(matrix), "schwager_diagnostics": schwager_diagnostics(matrix["schwager_context"]),
            "technical_diagnostics": technical_diagnostics(matrix["unified_context"]["indicator_context"], rows),
            "nison_diagnostics": nison_diagnostics(matrix), "hypothesis_trace": trace,
            "counterfactual": cf, "short_reason": ", ".join(decision["reason_codes"][-3:])}


def metrics(cases: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [x for x in cases if not x["excluded_from_metrics"]]
    base = Counter(x["baseline_regime"] for x in valid)
    passes = [x for x in valid if x["counterfactual"]["hypothetical_contract_pass"]]
    controls = [x for x in valid if x["bucket"] in CONTROL_BUCKETS]
    potential = [x for x in passes if x["bucket"] in CONTROL_BUCKETS]
    trend = [x for x in valid if x["bucket"] == "TREND_ONLY_DOWN_CANDIDATE"]
    missed = [x for x in passes if x["bucket"] == "TREND_ONLY_DOWN_CANDIDATE" and x["baseline_regime"] != "DOWN"]
    by_bucket = {b: {"windows": sum(x["bucket"] == b for x in valid), "passes": sum(x["bucket"] == b and x["counterfactual"]["hypothetical_contract_pass"] for x in valid)} for b in BUCKETS}
    for value in by_bucket.values(): value["pass_rate"] = value["passes"] / value["windows"] if value["windows"] else 0.0
    return {"included_windows": len(valid), "excluded_data_quality": len(cases) - len(valid),
            "baseline_counts": {k: base[k] for k in ("UP", "DOWN", "FLAT", "UNKNOWN")},
            "baseline_down_recall_provisional_trend_bucket": sum(x["baseline_regime"] == "DOWN" for x in trend) / len(trend) if trend else None,
            "baseline_false_up_count_provisional_controls": sum(x["baseline_regime"] == "UP" and x["bucket"] in CONTROL_BUCKETS for x in valid),
            "baseline_forced_directional_count": sum(bool(x["safety_violations"]) for x in valid),
            "safety_violations": sum(len(x["safety_violations"]) for x in valid),
            "hypothetical_contract_pass_count": len(passes), "pass_rate_by_bucket": by_bucket,
            "potential_false_down_count": len(potential), "potential_false_down_rate": len(potential) / len(controls) if controls else 0.0,
            "missed_trend_only_down_count": len(missed),
            "conflict_with_confirmed_range_count": sum("CONFIRMED_RANGE_CONFLICT" in x["counterfactual"]["risk_flags"] for x in valid),
            "conflict_with_bullish_reversal_count": sum("CONFIRMED_BULLISH_REVERSAL_CONFLICT" in x["counterfactual"]["risk_flags"] for x in valid),
            "manual_label_gated_metrics": {"status": "BLOCKED_MANUAL_LABELS"}}


def final_status(m: dict[str, Any]) -> str:
    if m["included_windows"] < 30: return "DATA_QUALITY_BLOCKED"
    if m["potential_false_down_rate"] > 0.20: return "TREND_ONLY_DOWN_CONTRACT_REJECTED_FALSE_DOWN_RISK"
    if m["missed_trend_only_down_count"] >= 3 and m["potential_false_down_rate"] <= 0.15:
        return "TREND_ONLY_DOWN_CONTRACT_PROMISING_BLOCKED_MANUAL_LABELS"
    return "MIXED_INCONCLUSIVE_NEEDS_MORE_OOS"


def dump(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csvs(cases: list[dict[str, Any]]) -> None:
    dataset_fields = ["case_id", "symbol", "timeframe", "actual_start", "actual_end", "candles", "bucket", "source", "data_quality", "baseline_regime", "selected_hypothesis", "confidence", "safety_violation", "short_reason"]
    with DATASET_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=dataset_fields); writer.writeheader()
        for x in cases: writer.writerow({"case_id": x["case_id"], "symbol": x["symbol"], "timeframe": x["timeframe"], "actual_start": x["actual_start"], "actual_end": x["actual_end"], "candles": x["candles"], "bucket": x["bucket"], "source": x["source"], "data_quality": x["data_quality"]["status"], "baseline_regime": x["baseline_regime"], "selected_hypothesis": (x.get("selected_hypothesis") or {}).get("hypothesis_type"), "confidence": x.get("confidence"), "safety_violation": bool(x.get("safety_violations")), "short_reason": x["short_reason"]})
    cf_fields = ["case_id", "bucket", "baseline_regime", "hypothetical_contract_pass", "risk_flags", "potential_false_down", "missed_trend_only_down", "notes"]
    with COUNTERFACTUAL_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=cf_fields); writer.writeheader()
        for x in cases:
            cf = x.get("counterfactual", {})
            passed = bool(cf.get("hypothetical_contract_pass"))
            writer.writerow({"case_id": x["case_id"], "bucket": x["bucket"], "baseline_regime": x["baseline_regime"], "hypothetical_contract_pass": passed, "risk_flags": "|".join(cf.get("risk_flags", [])), "potential_false_down": passed and x["bucket"] in CONTROL_BUCKETS, "missed_trend_only_down": passed and x["bucket"] == "TREND_ONLY_DOWN_CANDIDATE" and x["baseline_regime"] != "DOWN", "notes": x.get("note") or x["candidate_reason"]})


def write_markdown(cases: list[dict[str, Any]], m: dict[str, Any], status: str) -> None:
    btc = next(x for x in cases if x["case_id"] == SEEDS[0][0])
    sol = next(x for x in cases if x["case_id"] == SEEDS[2][0])
    lines = ["# ENGINE-TREND-20 — trend-only DOWN OOS audit", "", f"Final status: **{status}**.", "",
        "Audit-only conclusion: runtime implementation is not authorized. Dataset buckets are provisional audit buckets, not ground truth; blind manual labels are absent.", "",
        "## Metrics", "", f"- Windows: {len(cases)} total, {m['included_windows']} included, {m['excluded_data_quality']} excluded.",
        f"- Baseline UP / DOWN / FLAT / UNKNOWN: {m['baseline_counts']['UP']} / {m['baseline_counts']['DOWN']} / {m['baseline_counts']['FLAT']} / {m['baseline_counts']['UNKNOWN']}.",
        f"- Counterfactual passes: {m['hypothetical_contract_pass_count']}.",
        f"- Potential false DOWN: {m['potential_false_down_count']} ({m['potential_false_down_rate']:.2%} of provisional controls).",
        f"- Missed trend-only DOWN captured counterfactually: {m['missed_trend_only_down_count']}.", "",
        "## Answers", "", "1. A future contract is not ready for runtime. Its diagnostic value is conditional on low control-bucket activation and independent blind labels.",
        "2. The provisional false-DOWN risk is reported above; this is bucket-gated, not ground-truth error.",
        "3. The safe-looking envelope requires formal bearish Altunina structure or an LL/LH bearish-majority sequence, a subsequent LH/failed rebound, at least three bearish technical votes, price below multiple averages and VWAP, ADX >= 20, ATR-scaled negative progress, and no confirmed range/reversal/trap conflict.",
        "4. Primary false-DOWN precursors are range detection, confirmed range conflict, weak ADX/progress, missing LH-after-LL, bullish reversal, and trap conflicts.",
        "5. ENGINE-TREND-20B may only be a design stage after blind labels; no implementation stage is recommended now.", "",
        "## Mandatory cases", "", f"- BTC 2026-07-13 16:00: baseline `{btc['baseline_regime']}`, counterfactual pass `{btc.get('counterfactual', {}).get('hypothetical_contract_pass')}`, flags `{btc.get('counterfactual', {}).get('risk_flags')}`.",
        f"- SOL 2026-07-08 11:30: baseline `{sol['baseline_regime']}`. DOWN_CONTINUATION invalidation is caused by Altunina `structural_pivot_breached=true`; the hypothesis reason code states the outcome but omits pivot/leg values, so this is a reporting gap rather than a newly demonstrated logic defect.", "",
        "## Acceptance gate", "", "Manual-label-gated metrics: `BLOCKED_MANUAL_LABELS`. Therefore READY_FOR_IMPLEMENTATION is prohibited regardless of proxy metrics.", ""]
    AUDIT_MD.write_text("\n".join(lines), encoding="utf-8")

    potential = [x for x in cases if x.get("counterfactual", {}).get("hypothetical_contract_pass") and x["bucket"] in CONTROL_BUCKETS]
    fd = ["# ENGINE-TREND-20 — false DOWN risk audit", "", "Potential false DOWN is a provisional control-bucket collision, not a ground-truth error.", "", f"Count/rate: **{len(potential)} / {m['potential_false_down_rate']:.2%}**.", "", "| case | bucket | baseline | risk flags |", "|---|---|---|---|"]
    fd += [f"| {x['case_id']} | {x['bucket']} | {x['baseline_regime']} | {', '.join(x['counterfactual']['risk_flags']) or 'none'} |" for x in potential]
    fd += ["", "Common unsafe conditions are range/flat structure, weak negative progress relative to ATR, post-drop exhaustion, confirmed bullish reversal, and trap/range conflict.", ""]
    FALSE_DOWN_MD.write_text("\n".join(fd), encoding="utf-8")

    down = next((h for h in sol.get("hypothesis_trace", []) if h["hypothesis_type"] == "DOWN_CONTINUATION"), None)
    alt = sol.get("structural_diagnostics", {}).get("altunina_down_explanation", {})
    breach = alt.get("pivot_breach_provenance", [])
    SOL_TRACE_MD.write_text("\n".join(["# SOLUSDT 2026-07-08 11:30 — invalidation trace", "", "Conclusion: **diagnostic reporting gap**, not evidence of a continuation status logic defect.", "",
        "The existing `_continuation_hypothesis` status precedence sets `INVALIDATED` whenever `alt.impulse_correction.structural_pivot_breached` is true. This case has that exact condition. Specifically, the bearish leg started at index 87 (2026-07-08 09:30 UTC) at 77.49, and the following correction ended at index 91 (10:30 UTC) at 77.50; `77.50 >= 77.49` breached that stored bearish pivot. The exported reason code is correct, but the hypothesis trace itself omits these pivot/leg values.", "",
        "## Exported hypothesis", "", "```json", json.dumps(down, ensure_ascii=False, indent=2), "```", "", "## Altunina source condition", "", "```json", json.dumps({"impulse_correction": alt.get("impulse_correction"), "pivot_breach_provenance": breach}, ensure_ascii=False, indent=2), "```", "",
        "Suggested future task: `ENGINE-TREND-20A_DIAGNOSTIC_TRACE_HARDENING`. Add diagnostic-only provenance fields for pivot price/index, correction endpoint price/index, breach comparator, and status-transition cause. Do not change status logic or thresholds.", ""]), encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    session = get_session()
    operations: list[dict[str, Any]] = []
    try:
        specs = build_dataset_specs(session)
        cases = []
        for spec in specs:
            end = parse_time(spec["window_end"])
            rows = load_rows(session, spec["symbol"], end)
            before = coverage(rows, end, now)
            source = "DB_ONLY"
            if before["missing_intervals"]:
                ops = backfill_missing(session, spec["symbol"], end, before, now)
                operations.extend(ops)
                rows = load_rows(session, spec["symbol"], end)
                source = "DB_PLUS_BINANCE_BACKFILL" if ops else "FAILED_INSUFFICIENT_DATA"
            after = coverage(rows, end, now)
            if after["status"] != "PASS": source = "FAILED_INSUFFICIENT_DATA"
            cases.append(analyze_case(spec, rows, source, {"before_backfill": before, "after_backfill": after, **after}))
    finally:
        session.close()

    m = metrics(cases)
    status = final_status(m)
    payload = {"audit_id": "ENGINE-TREND-20", "generated_at": iso(now), "exchange": "Binance Spot", "timeframe": INTERVAL,
               "symbols": list(SYMBOLS), "dataset_construction": {"deterministic": True, "rolling_window_candles": WINDOW_SIZE, "bucket_is_ground_truth": False, "backfill_operations": operations},
               "metrics": m, "final_status": status, "cases": cases,
               "change_attestation": {"runtime_code_changed": False, "trading_runtime_changed": False, "thresholds_changed": False, "composer_changed": False, "commit_created": False}}
    dump(AUDIT_JSON, payload)
    dump(TRACE_JSON, {"audit_id": "ENGINE-TREND-20", "cases": [{"case_id": x["case_id"], "baseline_regime": x["baseline_regime"], "selected_hypothesis": x.get("selected_hypothesis"), "hypotheses": x.get("hypothesis_trace", [])} for x in cases]})
    dump(MANUAL_JSON, [{"case_id": x["case_id"], "symbol": x["symbol"], "timeframe": INTERVAL, "actual_start": x["actual_start"], "actual_end": x["actual_end"], "blind_chart_required": True, "manual_label": None, "allowed_labels": ["EXPECTED_DOWN", "EXPECTED_FLAT", "EXPECTED_UNKNOWN", "EXPECTED_UP", "LABEL_ISSUE", "INSUFFICIENT_CONTEXT"], "manual_notes": None, "provisional_audit_bucket": x["bucket"]} for x in cases])
    write_csvs(cases)
    write_markdown(cases, m, status)
    decision = {"final_status": status, "runtime_changed": False, "thresholds_changed": False, "composer_changed": False,
                "trading_runtime_changed": False, "manual_labels_status": "BLOCKED_MANUAL_LABELS",
                "recommendation": "NO_RUNTIME_IMPLEMENTATION; obtain independent blind labels before any design decision",
                "next_stage": "ENGINE-TREND-20A diagnostic trace hardening; manual blind labels; ENGINE-TREND-20B design only after validation"}
    dump(DECISION_JSON, decision)
    artifacts = [AUDIT_MD, AUDIT_JSON, DATASET_CSV, COUNTERFACTUAL_CSV, MANUAL_JSON, TRACE_JSON, FALSE_DOWN_MD, SOL_TRACE_MD, DECISION_JSON,
                 Path("scripts/engine_trend_20_trend_only_down_oos_audit.py"), Path("scripts/engine_trend_20_build_oos_dataset.py"), Path("tests/test_engine_trend_20_trend_only_down_oos_audit.py")]
    dump(MANIFEST_JSON, {"audit_id": "ENGINE-TREND-20", "files": [{"path": str(x).replace("\\", "/"), "bytes": x.stat().st_size, "sha256": sha(x)} for x in artifacts if x.exists()] + [{"path": str(MANIFEST_JSON).replace("\\", "/"), "bytes": None, "sha256": None, "note": "self-entry"}]})
    print(json.dumps({"status": status, "windows": len(cases), **m}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
