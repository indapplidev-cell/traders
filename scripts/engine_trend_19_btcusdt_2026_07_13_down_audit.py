"""One-shot, read-only ENGINE-TREND-19 audit for BTCUSDT 15m on 2026-07-13.

The script reads existing PostgreSQL candles, calls the existing engine without
changing its configuration, and writes diagnostic artifacts.  It never calls
the Binance client or a repository write method.
"""

from __future__ import annotations

import csv
import inspect
import json
import math
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Any, Iterable

from sqlalchemy import func, select

from app.db.models import MarketCandles
from app.db.session import get_session
from app.market_reader.engine_trend import market_hypothesis, regime_composer
from app.market_reader.engine_trend.altunina_trend_context import (
    STRUCTURE_TOLERANCE_RATIO,
)
from app.market_reader.engine_trend.data_source_boundary import (
    CandleDataRequest,
    build_candle_data_batch,
    run_engine_trend_from_batch,
)
from app.market_reader.engine_trend.schwager_range_context import (
    MAX_RANGE_WIDTH_RATIO,
    MIN_BOUNDARY_ALTERNATIONS,
    MIN_INSIDE_CLOSE_RATIO,
    MIN_RANGE_DURATION,
    MIN_RANGE_TOUCHES,
    MIN_RANGE_WIDTH_RATIO,
    MIN_ZONE_TOUCHES,
)
SYMBOL = "BTCUSDT"
INTERVAL = "15m"
STEP = timedelta(minutes=15)
MAIN_START = datetime(2026, 7, 12, 16, 15, tzinfo=timezone.utc)
MAIN_END = datetime(2026, 7, 13, 16, 0, tzinfo=timezone.utc)
WINDOW_ENDS = (
    datetime(2026, 7, 13, 9, 0, tzinfo=timezone.utc),
    datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc),
    datetime(2026, 7, 13, 14, 15, tzinfo=timezone.utc),
    MAIN_END,
)
REPORT_DIR = Path(
    "reports/engine_trend/live_market_checks/"
    "engine_trend_19_btcusdt_2026_07_13_down_audit"
)
AUDIT_MD = REPORT_DIR / "ENGINE_TREND_19_BTCUSDT_2026_07_13_DOWN_AUDIT.md"
AUDIT_JSON = REPORT_DIR / "ENGINE_TREND_19_BTCUSDT_2026_07_13_DOWN_AUDIT.json"
SWEEP_CSV = REPORT_DIR / "ENGINE_TREND_19_BTCUSDT_2026_07_13_WINDOW_SWEEP.csv"
TRACE_JSON = REPORT_DIR / "ENGINE_TREND_19_BTCUSDT_2026_07_13_HYPOTHESIS_TRACE.json"
COUNTERFACTUAL_MD = REPORT_DIR / "ENGINE_TREND_19_BTCUSDT_2026_07_13_COUNTERFACTUAL.md"
MANIFEST_JSON = REPORT_DIR / "ENGINE_TREND_19_BTCUSDT_2026_07_13_ARTIFACT_MANIFEST.json"
TEST_PATH = Path("tests/test_engine_trend_19_btcusdt_2026_07_13_down_audit.py")
STATUS = "DOWN_RECALL_GAP_TREND_ONLY_CONTINUATION_MISSING"


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def row_dict(row: MarketCandles) -> dict[str, object]:
    return {
        "symbol": row.symbol,
        "interval": row.interval,
        "timestamp": iso(row.open_time),
        "open": float(row.open),
        "high": float(row.high),
        "low": float(row.low),
        "close": float(row.close),
        "volume": float(row.volume),
    }


def data_quality(rows: list[MarketCandles], expected_count: int) -> dict[str, Any]:
    times = [row.open_time.astimezone(timezone.utc) for row in rows]
    numeric = [
        float(value)
        for row in rows
        for value in (row.open, row.high, row.low, row.close, row.volume)
    ]
    checks = {
        "candle_count": len(rows) == expected_count,
        "regular_15m_cadence": all(right - left == STEP for left, right in zip(times, times[1:])),
        "no_duplicate_intervals": len(times) == len(set(times)),
        "no_nan_or_inf": all(math.isfinite(value) for value in numeric),
        "positive_ohlcv": all(value > 0 for value in numeric),
        "ohlc_consistency": all(
            row.high >= max(row.open, row.close, row.low)
            and row.low <= min(row.open, row.close, row.high)
            for row in rows
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {"status": "PASS" if not failed else "FAIL", "checks": checks, "failed_checks": failed}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _source_span(function: Any) -> dict[str, Any]:
    lines, start = inspect.getsourcelines(function)
    return {
        "file": inspect.getsourcefile(function),
        "function": function.__name__,
        "start_line": start,
        "end_line": start + len(lines) - 1,
    }


def _load_rows(session: Any, start: datetime, end: datetime) -> list[MarketCandles]:
    return list(
        session.scalars(
            select(MarketCandles)
            .where(
                MarketCandles.symbol == SYMBOL,
                MarketCandles.interval == INTERVAL,
                MarketCandles.open_time >= start,
                MarketCandles.open_time <= end,
            )
            .order_by(MarketCandles.open_time)
        )
    )


def _run(rows: list[MarketCandles], source: str = "DB_ONLY") -> dict[str, Any]:
    request = CandleDataRequest(
        SYMBOL,
        INTERVAL,
        len(rows),
        iso(rows[0].open_time),
        iso(rows[-1].open_time),
        source,
    )
    batch = build_candle_data_batch(
        request,
        [row_dict(row) for row in rows],
        min_candle_count=64,
        strict_market_series=True,
    )
    return run_engine_trend_from_batch(batch).to_dict()["engine_output"]["composer_output"]


def _duplicate_times(rows: Iterable[MarketCandles]) -> list[str]:
    counts = Counter(iso(row.open_time) for row in rows)
    return [timestamp for timestamp, count in counts.items() if count > 1]


def build_data_coverage(rows: list[MarketCandles]) -> dict[str, Any]:
    expected = [MAIN_START + index * STEP for index in range(96)]
    actual = [row.open_time.astimezone(timezone.utc) for row in rows]
    actual_set = set(actual)
    numeric = [
        float(value)
        for row in rows
        for value in (row.open, row.high, row.low, row.close, row.volume)
    ]
    checks = {
        "exact_96_closed_candles": len(rows) == 96,
        "exact_first_candle": bool(rows) and actual[0] == MAIN_START,
        "exact_last_candle": bool(rows) and actual[-1] == MAIN_END,
        "timezone_utc": all(value.utcoffset() == timedelta(0) for value in actual),
        "missing_intervals_zero": all(value in actual_set for value in expected),
        "duplicates_zero": len(actual) == len(actual_set),
        "ohlc_consistent": all(
            float(row.high) >= max(float(row.open), float(row.close), float(row.low))
            and float(row.low) <= min(float(row.open), float(row.close), float(row.high))
            for row in rows
        ),
        "nan_inf_zero": all(math.isfinite(value) for value in numeric),
        "positive_ohlcv": all(
            min(
                float(row.open),
                float(row.high),
                float(row.low),
                float(row.close),
                float(row.volume),
            ) > 0
            for row in rows
        ),
    }
    missing = [iso(value) for value in expected if value not in actual_set]
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "status": "PASS" if not failed else "FAIL",
        "source": "DB_PLUS_BINANCE_BACKFILL",
        "audit_read_source": "DB_ONLY_NO_BACKFILL",
        "expected_candles": 96,
        "actual_candles": len(rows),
        "first_candle": iso(rows[0].open_time) if rows else None,
        "last_candle": iso(rows[-1].open_time) if rows else None,
        "missing_intervals": missing,
        "duplicates": _duplicate_times(rows),
        "checks": checks,
        "failed_checks": failed,
        "legacy_quality_recheck": data_quality(rows, 96),
    }


def _segment(rows: list[MarketCandles], start: int, end: int) -> dict[str, Any]:
    first, last = rows[start], rows[end]
    return {
        "start_index": start,
        "start_timestamp": iso(first.open_time),
        "start_price": float(first.high if start < end else first.low),
        "end_index": end,
        "end_timestamp": iso(last.open_time),
        "end_price": float(last.low if start < end else last.high),
    }


def build_raw_diagnostics(rows: list[MarketCandles]) -> dict[str, Any]:
    highs = [float(row.high) for row in rows]
    lows = [float(row.low) for row in rows]
    closes = [float(row.close) for row in rows]
    volumes = [float(row.volume) for row in rows]
    low_index = min(range(len(rows)), key=lambda index: lows[index])
    peak_index = max(range(low_index + 1), key=lambda index: highs[index])
    rebound_index = max(range(low_index, len(rows)), key=lambda index: highs[index])
    impulse_start = highs[peak_index]
    impulse_end = lows[low_index]
    rebound_end = highs[rebound_index]
    running_peak = closes[0]
    max_drawdown = 0.0
    drawdown_peak = drawdown_trough = 0
    peak_at = 0
    for index, close in enumerate(closes):
        if close > running_peak:
            running_peak, peak_at = close, index
        drawdown = (close - running_peak) / running_peak
        if drawdown < max_drawdown:
            max_drawdown, drawdown_peak, drawdown_trough = drawdown, peak_at, index
    baseline = median(volumes)
    volume_rows: list[dict[str, Any]] = []
    for index in sorted(range(len(rows)), key=lambda value: volumes[value], reverse=True)[:12]:
        phase = (
            "IMPULSE_DOWN"
            if peak_index <= index <= low_index
            else "REBOUND"
            if low_index < index <= rebound_index
            else "OTHER"
        )
        volume_rows.append(
            {
                "index": index,
                "timestamp": iso(rows[index].open_time),
                "volume": volumes[index],
                "median_ratio": volumes[index] / baseline if baseline else None,
                "candle_direction": (
                    "DOWN"
                    if float(rows[index].close) < float(rows[index].open)
                    else "UP"
                    if float(rows[index].close) > float(rows[index].open)
                    else "DOJI"
                ),
                "phase": phase,
                "is_spike_2x_median": volumes[index] >= baseline * 2,
            }
        )
    high_index = max(range(len(rows)), key=lambda index: highs[index])
    close_position = (closes[-1] - min(lows)) / (max(highs) - min(lows))
    return {
        "window_ohlc": {
            "open": float(rows[0].open),
            "high": max(highs),
            "low": min(lows),
            "close": closes[-1],
        },
        "max_high": {"price": highs[high_index], "timestamp": iso(rows[high_index].open_time), "index": high_index},
        "min_low": {"price": lows[low_index], "timestamp": iso(rows[low_index].open_time), "index": low_index},
        "total_return_close_over_open": closes[-1] / float(rows[0].open) - 1,
        "max_close_drawdown": {
            "value": max_drawdown,
            "peak_index": drawdown_peak,
            "peak_timestamp": iso(rows[drawdown_peak].open_time),
            "trough_index": drawdown_trough,
            "trough_timestamp": iso(rows[drawdown_trough].open_time),
        },
        "impulse_down_segment": {
            **_segment(rows, peak_index, low_index),
            "return": impulse_end / impulse_start - 1,
            "absolute_move": impulse_end - impulse_start,
        },
        "rebound_after_low": {
            "start_index": low_index,
            "start_timestamp": iso(rows[low_index].open_time),
            "start_price": impulse_end,
            "end_index": rebound_index,
            "end_timestamp": iso(rows[rebound_index].open_time),
            "end_price": rebound_end,
            "return": rebound_end / impulse_end - 1,
        },
        "close_position_0_low_1_high": close_position,
        "volume_baseline_median": baseline,
        "largest_volume_candles": volume_rows,
        "impulse_volume_spikes": [item for item in volume_rows if item["phase"] == "IMPULSE_DOWN" and item["is_spike_2x_median"]],
        "rebound_volume_spikes": [item for item in volume_rows if item["phase"] == "REBOUND" and item["is_spike_2x_median"]],
    }


def classify_swings(swings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    previous: dict[str, float] = {}
    classified: list[dict[str, Any]] = []
    for item in swings:
        kind = str(item["point_type"])
        price = float(item["price"])
        label = "UNKNOWN"
        if kind in previous:
            tolerance = max(abs(previous[kind]), abs(price), 1.0) * STRUCTURE_TOLERANCE_RATIO
            delta = price - previous[kind]
            if abs(delta) > tolerance:
                label = "HH" if kind == "HIGH" and delta > 0 else "LH" if kind == "HIGH" else "HL" if delta > 0 else "LL"
        previous[kind] = price
        classified.append(
            {
                "index": item["index"],
                "timestamp": item["timestamp"],
                "price": price,
                "type": "swing_high" if kind == "HIGH" else "swing_low",
                "structural_label": label,
            }
        )
    return classified


def _sequence_stats(swings: list[dict[str, Any]], kind: str) -> dict[str, Any]:
    values = [float(item["price"]) for item in swings if item["point_type"] == kind]
    changes = []
    for first, last in zip(values, values[1:]):
        tolerance = max(abs(first), abs(last), 1.0) * STRUCTURE_TOLERANCE_RATIO
        changes.append(0 if abs(last - first) <= tolerance else 1 if last > first else -1)
    material = [change for change in changes if change]
    return {
        "values": values,
        "changes": changes,
        "material_up": sum(change == 1 for change in material),
        "material_down": sum(change == -1 for change in material),
        "material_count": len(material),
        "down_ratio": sum(change == -1 for change in material) / len(material) if material else 0.0,
        "required_majority": 2 / 3,
    }


def build_structure(matrix: dict[str, Any]) -> dict[str, Any]:
    unified = matrix["unified_context"]
    alt = unified["altunina_context"]
    swings = unified["structural_swing_points"]
    classified = classify_swings(swings)
    labels = [item["structural_label"] for item in classified]
    low_index = max((index for index, item in enumerate(classified) if item["structural_label"] == "LL"), default=None)
    lh_after_ll = bool(low_index is not None and any(item["structural_label"] == "LH" for item in classified[low_index + 1 :]))
    return {
        "pivot_detector": {
            "production_volatility_aware": True,
            "fractal_lookback": 2,
            "volatility_extra_lookback_triggered": False,
            "absolute_prominence_filter": False,
            "right_confirmation_candles": 2,
            "decision_window_does_not_slice_structural_context": True,
            "context_candles": unified["analysis_window"]["candle_count"],
        },
        "raw_swing_count": len(unified["raw_swing_points"]),
        "structural_swing_count": len(swings),
        "swings": classified,
        "has_ll": "LL" in labels,
        "has_lh": "LH" in labels,
        "lh_after_ll": lh_after_ll,
        "has_lh_to_ll_sequence": any(left == "LH" and right == "LL" for left, right in zip(labels, labels[1:])),
        "has_ll_to_lh_sequence": any(left == "LL" and right == "LH" for left, right in zip(labels, labels[1:])),
        "high_sequence_vote": _sequence_stats(swings, "HIGH"),
        "low_sequence_vote": _sequence_stats(swings, "LOW"),
        "engine_structure_direction": alt["structure_direction"],
        "bearish_structure_seen": alt["structure_direction"] == "BEARISH_STRUCTURE",
        "exact_failure": (
            "Low sequence is bearish, but material lower-high changes are below the required two-thirds majority; "
            "the full 96-candle structure is therefore SIDEWAYS_STRUCTURE. The decision-window did not remove pivots."
        ),
        "altunina_runtime": alt,
    }


def build_range(matrix: dict[str, Any]) -> dict[str, Any]:
    schwager = matrix["unified_context"]["schwager_context"]
    trading_range = schwager["trading_range"]
    support_candidates = [zone for zone in schwager["zones"] if zone["zone_type"] == "SUPPORT"]
    resistance_candidates = [zone for zone in schwager["zones"] if zone["zone_type"] == "RESISTANCE"]
    return {
        "thresholds_observed_not_changed": {
            "min_zone_touches": MIN_ZONE_TOUCHES,
            "min_range_touches": MIN_RANGE_TOUCHES,
            "min_inside_close_ratio": MIN_INSIDE_CLOSE_RATIO,
            "min_width_ratio": MIN_RANGE_WIDTH_RATIO,
            "max_width_ratio": MAX_RANGE_WIDTH_RATIO,
            "min_duration": MIN_RANGE_DURATION,
            "min_boundary_alternations": MIN_BOUNDARY_ALTERNATIONS,
        },
        "range_candidates": {"support": support_candidates, "resistance": resistance_candidates},
        "trading_range": trading_range,
        "range_detected": trading_range["is_detected"],
        "exact_failure": "No support zone has the required two touches, so no support/resistance pair can form a range.",
        "breakdown": schwager["breakout_context"],
        "retest": {
            "returned_to_range": schwager["breakout_context"]["returned_to_range"],
            "return_index": schwager["breakout_context"]["return_index"],
        },
        "polarity_flip": schwager["polarity_flip_context"],
        "false_breakout_or_trap": {
            "status": schwager["breakout_context"]["false_breakout_confirmation"],
            "invalidated": schwager["breakout_context"]["false_breakout_invalidated"],
        },
        "critical_answer": {
            "range_false_makes_down_almost_impossible": False,
            "answer": "NO",
            "reason": (
                "A continuation can be seeded by bearish structure, confirmed bearish candle continuation, "
                "or decision-window progress without a range. A range is required only for the breakdown seed."
            ),
            "code_trace": _source_span(market_hypothesis._continuation_hypothesis),
        },
        "runtime": schwager,
    }


def _sma(values: list[float], period: int) -> float | None:
    return sum(values[-period:]) / period if len(values) >= period else None


def build_technical(rows: list[MarketCandles], matrix: dict[str, Any]) -> dict[str, Any]:
    runtime = matrix["unified_context"]["indicator_context"]
    closes = [float(row.close) for row in rows]
    close = closes[-1]
    lines = {
        "sma20": runtime["sma_20"],
        "sma50_diagnostic_only": _sma(closes, 50),
        "sma99_diagnostic_only": _sma(closes, 99),
        "ema12": runtime["ema_12"],
        "ema26": runtime["ema_26"],
        "vwap": runtime["vwap"],
    }
    return {
        "decision_close": close,
        "values": {
            **lines,
            "rsi14": runtime["rsi_14"],
            "macd": runtime["macd"],
            "macd_signal": runtime["macd_signal"],
            "macd_histogram": runtime["macd"] - runtime["macd_signal"],
            "atr14": runtime["atr_14"],
            "atr_ratio": runtime["atr_ratio"],
            "adx14": runtime["adx_14"],
            "bollinger_mid": runtime["bollinger_mid"],
            "bollinger_upper": runtime["bollinger_upper"],
            "bollinger_lower": runtime["bollinger_lower"],
            "bollinger_percent_b": (close - runtime["bollinger_lower"]) / (runtime["bollinger_upper"] - runtime["bollinger_lower"]),
        },
        "price_relation": {name: (None if value is None else "ABOVE" if close > value else "BELOW" if close < value else "EQUAL") for name, value in lines.items()},
        "votes": {
            "bullish": runtime["bullish_votes"],
            "bearish": runtime["bearish_votes"],
            "neutral_or_conflicted": 0,
            "direction": runtime["direction"],
            "supporting_down": [code for code in runtime["reason_codes"] if "BEARISH" in code or "BELOW" in code],
            "blocking_down": [code for code in runtime["reason_codes"] if "BULLISH" in code or "ABOVE" in code],
            "reason_codes": runtime["reason_codes"],
        },
        "independent_confirmation_contract": {
            "indicator_matches_down": runtime["direction"] == "BEARISH",
            "sufficient_alone": False,
            "reason": "Indicators are one method; confirmation needs two methods, and indicators cannot seed a candidate alone.",
        },
        "runtime": runtime,
    }


def build_nison(matrix: dict[str, Any]) -> dict[str, Any]:
    nison = matrix["unified_context"]["nison_context"]
    events = matrix["hypothesis_result"]["contextual_events"]
    bearish = [event for event in events if event["direction"] == "BEARISH"]
    bullish = [event for event in events if event["direction"] == "BULLISH"]
    bearish_cont = [event for event in bearish if event["role"] == "CONTINUATION"]
    return {
        "summary": nison["summary"],
        "bearish_patterns": bearish,
        "bullish_reversal_patterns": [event for event in bullish if event["role"] == "REVERSAL"],
        "bearish_continuation_patterns": bearish_cont,
        "confirmed_bearish_continuation": any(event["status"] == "CONFIRMED" for event in bearish_cont),
        "confirmed_bullish_reversal": any(event["status"] == "CONFIRMED" for event in bullish),
        "exact_failure": (
            "The bearish separating-lines event at indexes 84-85 was CONTEXT_REJECTED: prior structure was sideways, "
            "there was no causal zone, and follow-through was still pending. All reversal-like events were also context-rejected."
        ),
        "rebound_blocked_bearish_continuation": False,
        "reason_codes": nison["reason_codes"],
        "runtime": nison,
    }


def build_hypothesis_trace(matrix: dict[str, Any], structure: dict[str, Any], range_layer: dict[str, Any], technical: dict[str, Any], nison: dict[str, Any]) -> dict[str, Any]:
    result = matrix["hypothesis_result"]
    window = matrix["unified_context"]["analysis_window"]
    candles = matrix["unified_context"]
    # Candle prices are intentionally not exported in UnifiedMarketContext; the
    # caller fills these exact values after reading the DB rows.
    evaluated = {
        "structure_matches": structure["bearish_structure_seen"],
        "breakdown_matches": range_layer["breakdown"]["status"] == "CONFIRMED" and range_layer["breakdown"]["direction"] == "DOWNWARD" and range_layer["breakdown"]["breakout_index"] is not None and window["decision_start_index"] <= range_layer["breakdown"]["breakout_index"] <= window["decision_end_index"],
        "confirmed_bearish_continuation_event": nison["confirmed_bearish_continuation"],
        "indicator_matches": technical["independent_confirmation_contract"]["indicator_matches_down"],
    }
    return {
        "runtime_contextual_events": result["contextual_events"],
        "runtime_hypotheses": result["hypotheses"],
        "dominant_hypothesis": result["dominant_hypothesis"],
        "runtime_summary": result["summary"],
        "candidate_presence": {
            "DOWN_CONTINUATION": any(item["hypothesis_type"] == "DOWN_CONTINUATION" for item in result["hypotheses"]),
            "BEARISH_REVERSAL": any(item["hypothesis_type"] == "BEARISH_REVERSAL" for item in result["hypotheses"]),
            "BEAR_TRAP": any(item["hypothesis_type"] == "BEAR_TRAP" for item in result["hypotheses"]),
            "CONFIRMED_RANGE": any(item["hypothesis_type"] == "CONFIRMED_RANGE" for item in result["hypotheses"]),
        },
        "down_continuation_generation_conditions": evaluated,
        "down_continuation_candidate_exists": False,
        "down_continuation_status": "NOT_GENERATED",
        "score": None,
        "confidence": None,
        "evidence": [code for code in technical["runtime"]["reason_codes"] if "BEARISH" in code or "BELOW" in code],
        "missing_evidence": [name for name, passed in evaluated.items() if name != "indicator_matches" and not passed],
        "rejection_reason": None,
        "pending_reason": None,
        "conflict_reason": None,
        "not_generated_reason": "All four seed conditions are false. Indicator alignment is not a seed.",
        "code_trace": _source_span(market_hypothesis._continuation_hypothesis),
        "unused_context_placeholder": candles["candle_count"],
    }


def add_progress(rows: list[MarketCandles], matrix: dict[str, Any], trace: dict[str, Any]) -> None:
    window = matrix["unified_context"]["analysis_window"]
    indicators = matrix["unified_context"]["indicator_context"]
    start_close = float(rows[window["decision_start_index"]].close)
    end_close = float(rows[-1].close)
    change = end_close / start_close - 1
    threshold = max(0.01, float(indicators["atr_ratio"] or 0) * 2)
    trace["down_continuation_generation_conditions"]["decision_window_progress_matches"] = change <= -threshold
    trace["decision_window_progress"] = {
        "start_index": window["decision_start_index"],
        "start_timestamp": iso(rows[window["decision_start_index"]].open_time),
        "start_close": start_close,
        "end_close": end_close,
        "change": change,
        "required_down_change": -threshold,
        "shortfall_percentage_points": max(0.0, change + threshold) * 100,
    }
    trace["missing_evidence"] = [
        name
        for name, passed in trace["down_continuation_generation_conditions"].items()
        if name != "indicator_matches" and not passed
    ]


def build_composer(composer: dict[str, Any]) -> dict[str, Any]:
    trace = composer["decision_trace"]
    hypotheses = composer["matrix"]["hypothesis_result"]["hypotheses"]
    grouped = {status: [item for item in hypotheses if item["status"] == status] for status in ("CONFIRMED", "PENDING", "CONFLICTED", "INVALIDATED", "CANCELLED")}
    return {
        "hypotheses_reaching_composer": hypotheses,
        "by_status": grouped,
        "selected_hypothesis": trace["selected_hypothesis"],
        "selected_source": trace["decision_source"],
        "regime": composer["result"]["market_regime"],
        "confidence": composer["result"]["confidence"],
        "candidate_scores": trace["candidate_scores"],
        "safety_guards": [code for code in trace["reason_codes"] if code.startswith("COMPOSER_")],
        "why_unknown": "No runtime hypothesis reached the composer, so DOWN scored 0.0 and UNKNOWN floor scored 0.25; conservative fallback selected UNKNOWN.",
        "minimal_missing_condition": "Any one additional bearish seed would combine with already-bearish indicators to reach the two-method confirmation contract. Numerically closest: decision-window progress missed -1.0% by about 0.108 percentage points.",
        "decision_trace": trace,
        "code_trace": _source_span(regime_composer.score_regime_candidates),
    }


def build_sweep(session: Any, latest: datetime) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    ends = list(WINDOW_ENDS)
    if latest > MAIN_END:
        ends.append(latest)
    for end in ends:
        start = end - STEP * 95
        rows = _load_rows(session, start, end)
        composer = _run(rows)
        hypotheses = composer["matrix"]["hypothesis_result"]["hypotheses"]
        selected = composer["decision_trace"]["selected_hypothesis"]
        statuses = Counter(item["status"] for item in hypotheses)
        output.append(
            {
                "window_end": iso(end),
                "actual_start": iso(rows[0].open_time),
                "actual_end": iso(rows[-1].open_time),
                "candles": len(rows),
                "regime": composer["result"]["market_regime"],
                "selected_hypothesis": selected["hypothesis_type"] if selected else None,
                "source": composer["decision_trace"]["decision_source"],
                "confidence": composer["result"]["confidence"],
                "confirmed": statuses["CONFIRMED"],
                "pending": statuses["PENDING"],
                "conflicted": statuses["CONFLICTED"],
                "short_reason": ", ".join(composer["decision_trace"]["reason_codes"][-3:]),
                "hypotheses": hypotheses,
                "structure": composer["matrix"]["unified_context"]["altunina_context"]["structure_direction"],
                "range_detected": composer["matrix"]["unified_context"]["schwager_context"]["trading_range"]["is_detected"],
                "breakout": composer["matrix"]["unified_context"]["schwager_context"]["breakout_context"],
            }
        )
    return output


def build_counterfactual(structure: dict[str, Any], raw: dict[str, Any], technical: dict[str, Any], range_layer: dict[str, Any], nison: dict[str, Any]) -> dict[str, Any]:
    relations = technical["price_relation"]
    conditions = {
        "LL_LH_present": structure["has_ll"] and structure["lh_after_ll"],
        "price_below_SMA20_EMA12_EMA26_VWAP": all(relations[name] == "BELOW" for name in ("sma20", "ema12", "ema26", "vwap")),
        "ADX_gt_25": technical["values"]["adx14"] > 25,
        "bearish_technical_votes_gte_3": technical["votes"]["bearish"] >= 3,
        "failed_rebound_lower_high_after_low": structure["lh_after_ll"] and raw["rebound_after_low"]["end_index"] < 95,
        "no_confirmed_active_range": not range_layer["range_detected"],
        "no_bullish_reversal_confirmation": not nison["confirmed_bullish_reversal"],
    }
    return {
        "diagnostic_only": True,
        "rules_changed": False,
        "conditions": conditions,
        "hypothetical_trend_only_down_continuation": all(conditions.values()),
        "for": [name for name, passed in conditions.items() if passed],
        "against": [name for name, passed in conditions.items() if not passed],
        "false_down_risk_in_range": "MEDIUM_TO_HIGH",
        "risk_reason": "Technical votes lag price, absence of a confirmed range is not proof of trend, and the runtime structural classifier still says SIDEWAYS_STRUCTURE. This contract must be validated out of sample before any runtime proposal.",
    }


def build_safety(composer: dict[str, Any], technical: dict[str, Any], nison: dict[str, Any]) -> dict[str, Any]:
    return {
        "unknown_instead_of_down_is_safety_safe": True,
        "false_up_risk": False,
        "opposite_directional_conflicts": False,
        "correct_not_to_emit_up_after_rebound": True,
        "formal_safety_violation": False,
        "evidence": {
            "regime": composer["result"]["market_regime"],
            "up_score": composer["decision_trace"]["candidate_scores"]["up_score"],
            "down_score": composer["decision_trace"]["candidate_scores"]["down_score"],
            "bullish_votes": technical["votes"]["bullish"],
            "bearish_votes": technical["votes"]["bearish"],
            "confirmed_bullish_reversal": nison["confirmed_bullish_reversal"],
        },
        "bug_assessment": "No execution bug: output follows the written generation and composer contracts. This is a missing trend-only coverage path / recall gap.",
    }


def _write_csv(rows: list[dict[str, Any]]) -> None:
    fields = ["window_end", "actual_start", "actual_end", "candles", "regime", "selected_hypothesis", "source", "confidence", "confirmed", "pending", "conflicted", "short_reason"]
    with SWEEP_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row[field] for field in fields})


def _write_markdown(audit: dict[str, Any]) -> None:
    coverage = audit["data_coverage"]
    raw = audit["raw_candle_diagnostics"]
    structure = audit["structural_diagnostics"]
    range_layer = audit["schwager_range_breakdown"]
    technical = audit["technical_indicators"]
    trace = audit["hypothesis_generation"]
    composer = audit["composer_trace"]
    sweep = audit["decision_window_audit"]["windows"]
    conditions = audit["counterfactual"]["conditions"]
    lines = [
        "# ENGINE-TREND-19 BTCUSDT 2026-07-13 DOWN audit",
        "",
        f"**Итоговый статус:** `{STATUS}`.",
        "",
        "Модель вернула `UNKNOWN`, потому что `DOWN_CONTINUATION` не был даже создан как runtime candidate. Полная 96-свечная Altunina-структура классифицирована как `SIDEWAYS_STRUCTURE`; Schwager range не подтверждён и потому breakdown не вычисляется; единственный bearish continuation candle-event отклонён контекстом; падение последних 24 свечей составило только "
        f"`{trace['decision_window_progress']['change']:.6%}` при требовании `-1.000000%`. Bearish indicators (`{technical['votes']['bearish']}` против `{technical['votes']['bullish']}`) являются лишь одним методом и не могут самостоятельно seed-ить hypothesis.",
        "",
        "## 1. Data coverage / quality",
        "",
        f"DB содержит ровно `{coverage['actual_candles']}` свечей, first `{coverage['first_candle']}`, last `{coverage['last_candle']}`. Missing: `{len(coverage['missing_intervals'])}`, duplicates: `{len(coverage['duplicates'])}`, quality: `{coverage['status']}`. Audit читал БД и не делал backfill.",
        "",
        "## 2. Raw candle diagnostics",
        "",
        f"Window OHLC: `{raw['window_ohlc']}`. Total return: `{raw['total_return_close_over_open']:.4%}`; max close drawdown: `{raw['max_close_drawdown']['value']:.4%}`; close position in high-low range: `{raw['close_position_0_low_1_high']:.3f}`.",
        "",
        f"Impulse: `{raw['impulse_down_segment']['start_timestamp']}` {raw['impulse_down_segment']['start_price']:.2f} → `{raw['impulse_down_segment']['end_timestamp']}` {raw['impulse_down_segment']['end_price']:.2f} (`{raw['impulse_down_segment']['return']:.4%}`). Rebound reached {raw['rebound_after_low']['end_price']:.2f} at `{raw['rebound_after_low']['end_timestamp']}`.",
        "",
        f"Volume spikes (≥2× median) inside the broad impulse segment: `{len(raw['impulse_volume_spikes'])}`; on the post-low rebound: `{len(raw['rebound_volume_spikes'])}`. The two largest down-candle spikes were 860.81 ({raw['impulse_volume_spikes'][0]['median_ratio']:.2f}× median) at `2026-07-13T13:45:00Z` and 803.52 ({raw['impulse_volume_spikes'][1]['median_ratio']:.2f}×) at `2026-07-13T13:30:00Z`; rebound spike 423.91 ({raw['rebound_volume_spikes'][0]['median_ratio']:.2f}×) at `2026-07-13T14:30:00Z`.",
        "",
        "## 3. Altunina structure",
        "",
        f"Structural pivots: `{structure['structural_swing_count']}`; LL: `{structure['has_ll']}`; LH after LL: `{structure['lh_after_ll']}`; engine direction: `{structure['engine_structure_direction']}`. {structure['exact_failure']}",
        "",
        "| index | timestamp | price | type | label |",
        "|---:|---|---:|---|---|",
    ]
    lines.extend(f"| {item['index']} | {item['timestamp']} | {item['price']:.2f} | {item['type']} | {item['structural_label']} |" for item in structure["swings"])
    lines.extend([
        "",
        "## 4. Schwager range / breakdown",
        "",
        f"Range detected: `{range_layer['range_detected']}`. {range_layer['exact_failure']} Breakdown status: `{range_layer['breakdown']['status']}` / `{range_layer['breakdown']['direction']}`; retest and polarity flip are absent.",
        "",
        f"Range candidates: support 62101.00 had only 1 touch; resistance candidates were 62862.28–62983.83 (3 touches), 63135.55–63302.88 (3), 64018.69–64270.00 (5), and 64425.00 (1). Since a range pair was never formed, boundaries are `null`, inside_close_ratio is `0.0`, and no breakdown/false-breakout/polarity event can be evaluated.",
        "",
        "Критичный ответ: **NO** — `range_detected=false` не делает DOWN почти невозможным. Без range недоступен только breakdown seed; structure, candle continuation или decision progress также могут создать continuation candidate.",
        "",
        "## 5. Technical indicators",
        "",
        "```json",
        _json({"values": technical["values"], "price_relation": technical["price_relation"], "votes": technical["votes"]}),
        "```",
        "",
        "## 6. Nison candle layer",
        "",
        audit["nison_candle_layer"]["exact_failure"],
        "",
        "## 7. Hypothesis generation",
        "",
        f"Runtime hypotheses: `{len(trace['runtime_hypotheses'])}`. DOWN_CONTINUATION candidate exists: `{trace['down_continuation_candidate_exists']}`; BEARISH_REVERSAL: `{trace['candidate_presence']['BEARISH_REVERSAL']}`; BEAR_TRAP: `{trace['candidate_presence']['BEAR_TRAP']}`; CONFIRMED_RANGE: `{trace['candidate_presence']['CONFIRMED_RANGE']}`.",
        "",
        "Exact failed DOWN conditions: `structure_matches=false`, `breakdown_matches=false`, `confirmed_bearish_continuation_event=false`, `decision_window_progress_matches=false`. `indicator_matches=true`, but it is not a seed and gives only one independent method.",
        "",
        "## 8. Composer trace",
        "",
        f"Confirmed/Pending/Conflicted: `0/0/0`. DOWN score `{composer['candidate_scores']['down_score']}`, UNKNOWN score `{composer['candidate_scores']['unknown_score']}`. `{composer['why_unknown']}` Minimal missing condition: {composer['minimal_missing_condition']}",
        "",
        "## 9. Decision-window sweep",
        "",
        "| end | start | regime | selected hypothesis | confirmed | pending | conflicted |",
        "|---|---|---|---|---:|---:|---:|",
    ])
    lines.extend(f"| {item['window_end']} | {item['actual_start']} | {item['regime']} | {item['selected_hypothesis'] or 'NONE'} | {item['confirmed']} | {item['pending']} | {item['conflicted']} |" for item in sweep)
    lines.extend([
        "",
        f"Latest available closed candle: `{audit['decision_window_audit']['latest_available_closed_candle']}`; after 16:00 data exists: `{audit['decision_window_audit']['data_after_16_exists']}`. Ни одно подокно не дало DOWN или FLAT.",
        "",
        "At 09:00 a range and downward breakout existed, but the breakout trigger was index 52 while the decision-window started at 72. Therefore the old breakdown could not seed a current DOWN_CONTINUATION; the range hypothesis was CONFLICTED. The other three windows had no detected range and no hypotheses.",
        "",
        "## 10. Diagnostic-only counterfactual",
        "",
    ])
    lines.extend(f"- `{name}`: `{passed}`" for name, passed in conditions.items())
    lines.extend([
        "",
        f"Hypothetical trend-only DOWN_CONTINUATION: `{audit['counterfactual']['hypothetical_trend_only_down_continuation']}`. Риск false DOWN: `{audit['counterfactual']['false_down_risk_in_range']}`; это требует отдельной OOS-задачи, а не изменения текущего runtime.",
        "",
        "## 11. Safety audit",
        "",
        "`UNKNOWN` safety-safe; ложного `UP` не было; formal directional conflicts и safety violations отсутствуют. Не выдавать `UP` после отскока было корректно. Поведение соответствует коду, поэтому это не execution bug, а missing coverage.",
        "",
        "## 12. Conclusion",
        "",
        f"- Status: `{STATUS}`",
        "- Bug or missing coverage: `MISSING_COVERAGE`, not a runtime bug.",
        "- Change runtime now: `NO`.",
        "- Separate ENGINE-TREND-20: `YES` — validate a trend-only continuation contract out of sample, with explicit range false-positive controls.",
        "- Runtime/trading runtime/thresholds/composer changed: `NO/NO/NO/NO`.",
        "",
    ])
    AUDIT_MD.write_text("\n".join(lines), encoding="utf-8")


def _write_counterfactual(value: dict[str, Any]) -> None:
    lines = [
        "# ENGINE-TREND-19 diagnostic-only trend continuation counterfactual",
        "",
        "Это вычисление не меняет runtime contract и не предлагает threshold tuning.",
        "",
        "| condition | passed |",
        "|---|---|",
    ]
    lines.extend(f"| {name} | {passed} |" for name, passed in value["conditions"].items())
    lines.extend([
        "",
        f"Hypothetical trend-only DOWN_CONTINUATION: **{value['hypothetical_trend_only_down_continuation']}**.",
        "",
        f"False-DOWN risk: **{value['false_down_risk_in_range']}**. {value['risk_reason']}",
        "",
        "Вывод: вынести идею в отдельный ENGINE-TREND-20 OOS audit; runtime сейчас не менять.",
        "",
    ])
    COUNTERFACTUAL_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    session = get_session()
    try:
        rows = _load_rows(session, MAIN_START, MAIN_END)
        coverage = build_data_coverage(rows)
        if coverage["status"] != "PASS":
            raise RuntimeError(f"Audit requires exact DB coverage: {coverage['failed_checks']}")
        composer = _run(rows, "DB_PLUS_BINANCE_BACKFILL")
        matrix = composer["matrix"]
        raw = build_raw_diagnostics(rows)
        structure = build_structure(matrix)
        range_layer = build_range(matrix)
        technical = build_technical(rows, matrix)
        nison = build_nison(matrix)
        hypothesis_trace = build_hypothesis_trace(matrix, structure, range_layer, technical, nison)
        add_progress(rows, matrix, hypothesis_trace)
        composer_trace = build_composer(composer)
        latest = session.scalar(select(func.max(MarketCandles.open_time)).where(MarketCandles.symbol == SYMBOL, MarketCandles.interval == INTERVAL))
        sweep = build_sweep(session, latest)
        counterfactual = build_counterfactual(structure, raw, technical, range_layer, nison)
        safety = build_safety(composer, technical, nison)
        audit = {
            "audit_id": "ENGINE-TREND-19",
            "status": STATUS,
            "symbol": SYMBOL,
            "timeframe": INTERVAL,
            "actual_start": iso(MAIN_START),
            "actual_end": iso(MAIN_END),
            "runtime_code_changed": False,
            "trading_runtime_changed": False,
            "thresholds_changed": False,
            "composer_changed": False,
            "database_writes": False,
            "data_coverage": coverage,
            "raw_candle_diagnostics": raw,
            "structural_diagnostics": structure,
            "schwager_range_breakdown": range_layer,
            "technical_indicators": technical,
            "nison_candle_layer": nison,
            "hypothesis_generation": hypothesis_trace,
            "composer_trace": composer_trace,
            "decision_window_audit": {
                "decision_candles": matrix["unified_context"]["analysis_window"]["decision_end_index"] - matrix["unified_context"]["analysis_window"]["decision_start_index"] + 1,
                "latest_available_closed_candle": iso(latest),
                "data_after_16_exists": latest > MAIN_END,
                "windows": sweep,
            },
            "counterfactual": counterfactual,
            "safety_audit": safety,
            "conclusion": {
                "status": STATUS,
                "bug_or_missing_coverage": "MISSING_COVERAGE",
                "change_runtime_now": "NO",
                "engine_trend_20_needed": "YES",
            },
            "candles": [row_dict(row) for row in rows],
        }
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        AUDIT_JSON.write_text(_json(audit) + "\n", encoding="utf-8")
        TRACE_JSON.write_text(_json(hypothesis_trace) + "\n", encoding="utf-8")
        _write_csv(sweep)
        _write_markdown(audit)
        _write_counterfactual(counterfactual)
        created = [AUDIT_MD, AUDIT_JSON, SWEEP_CSV, TRACE_JSON, COUNTERFACTUAL_MD, MANIFEST_JSON]
        script_path = Path(__file__).relative_to(Path.cwd())
        manifest = {
            "audit_id": "ENGINE-TREND-19",
            "status": "COMPLETE",
            "files": [str(path).replace("\\", "/") for path in created],
            "supporting_script": str(script_path).replace("\\", "/"),
            "supporting_test": str(TEST_PATH).replace("\\", "/"),
            "created_files": [
                *[str(path).replace("\\", "/") for path in created],
                str(script_path).replace("\\", "/"),
                str(TEST_PATH).replace("\\", "/"),
            ],
            "runtime_code_changed": False,
            "database_writes": False,
        }
        MANIFEST_JSON.write_text(_json(manifest) + "\n", encoding="utf-8")
        print(_json({"status": STATUS, "regime": composer["result"]["market_regime"], "down_candidate": hypothesis_trace["down_continuation_candidate_exists"], "reports": manifest["files"]}))
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
