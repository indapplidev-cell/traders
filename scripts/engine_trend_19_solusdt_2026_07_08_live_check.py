"""One-shot ENGINE-TREND-19 SOLUSDT 15m live/replay audit.

Audit/check only: reads PostgreSQL first, backfills only missing closed Binance
Spot intervals, invokes the current engine_trend facade unchanged, and writes
diagnostic artifacts. It does not alter model/runtime policy or thresholds.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter
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


SYMBOL = "SOLUSDT"
INTERVAL = "15m"
STEP = timedelta(minutes=15)
UTC = timezone.utc
NOW = datetime.now(UTC)
OUT = Path("reports/engine_trend/live_market_checks/solusdt_2026_07_08")
BASE = "ENGINE_TREND_19_SOLUSDT_2026_07_08"
LIVE_MD = OUT / f"{BASE}_LIVE_CHECK.md"
LIVE_JSON = OUT / f"{BASE}_LIVE_CHECK.json"
COVERAGE_MD = OUT / f"{BASE}_DATA_COVERAGE.md"
COVERAGE_JSON = OUT / f"{BASE}_DATA_COVERAGE.json"
SWEEP_CSV = OUT / f"{BASE}_WINDOW_SWEEP.csv"
TRACE_JSON = OUT / f"{BASE}_HYPOTHESIS_TRACE.json"
MANIFEST_JSON = OUT / f"{BASE}_ARTIFACT_MANIFEST.json"

MAIN_START = datetime(2026, 7, 8, 0, 0, tzinfo=UTC)
MAIN_END = datetime(2026, 7, 8, 23, 45, tzinfo=UTC)
WINDOWS = (
    ("SOLUSDT_2026_07_08_06_00", datetime(2026, 7, 8, 6, 0, tzinfo=UTC)),
    ("SOLUSDT_2026_07_08_11_30", datetime(2026, 7, 8, 11, 30, tzinfo=UTC)),
    ("SOLUSDT_2026_07_08_18_30", datetime(2026, 7, 8, 18, 30, tzinfo=UTC)),
    ("SOLUSDT_2026_07_08_23_45", MAIN_END),
)


def iso(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z") if value else None


def times(start: datetime, end: datetime) -> list[datetime]:
    """Inclusive 15m open-time grid."""
    return [start + index * STEP for index in range(int((end - start) / STEP) + 1)]


def window_start(end: datetime) -> datetime:
    return end - 95 * STEP


def load_rows(session: Any, start: datetime, end: datetime) -> list[MarketCandles]:
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


def coverage(rows: Iterable[MarketCandles], start: datetime, end: datetime) -> dict[str, Any]:
    items = list(rows)
    opens = [row.open_time.astimezone(UTC) for row in items]
    expected = times(start, end)
    counts = Counter(opens)
    missing = [item for item in expected if counts[item] == 0]
    duplicates = sum(count - 1 for count in counts.values() if count > 1)
    return {
        "expected_candles": len(expected),
        "found_candles": len(items),
        "unique_candles": len(counts),
        "first_candle_time": iso(min(opens) if opens else None),
        "last_candle_time": iso(max(opens) if opens else None),
        "missing_intervals_count": len(missing),
        "missing_open_times": [iso(item) for item in missing],
        "duplicate_intervals_count": duplicates,
        "regular_15m": opens == expected,
        "status": "PASS" if opens == expected and not duplicates else "INCOMPLETE",
    }


def contiguous_ranges(values: Iterable[datetime]) -> list[tuple[datetime, datetime]]:
    ordered = sorted(set(values))
    if not ordered:
        return []
    result: list[tuple[datetime, datetime]] = []
    start = previous = ordered[0]
    for value in ordered[1:]:
        if value != previous + STEP:
            result.append((start, previous + STEP))
            start = value
        previous = value
    result.append((start, previous + STEP))
    return result


def source_name(before: dict[str, Any], after: dict[str, Any]) -> str:
    if after["status"] != "PASS":
        return "FAILED_INSUFFICIENT_DATA"
    if before["missing_intervals_count"] == 0:
        return "DB_ONLY"
    if before["found_candles"] == 0:
        return "BINANCE_ONLY"
    return "DB_PLUS_BINANCE_BACKFILL"


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


def quality(rows: list[MarketCandles], start: datetime, end: datetime) -> dict[str, Any]:
    opens = [row.open_time.astimezone(UTC) for row in rows]
    expected = times(start, end)
    finite = all(
        math.isfinite(float(value))
        for row in rows
        for value in (row.open, row.high, row.low, row.close, row.volume)
    )
    checks = {
        "expected_count": len(rows) == len(expected),
        "no_missing_intervals": opens == expected,
        "no_duplicates": len(opens) == len(set(opens)),
        "regular_15m": all(b - a == STEP for a, b in zip(opens, opens[1:])),
        "timezone_utc": all(row.open_time.utcoffset() == timedelta(0) and row.close_time.utcoffset() == timedelta(0) for row in rows),
        "ohlc_consistency": all(float(row.high) >= max(float(row.open), float(row.close)) >= min(float(row.open), float(row.close)) >= float(row.low) for row in rows),
        "no_nan_or_inf": finite,
        "positive_ohlc": all(min(float(row.open), float(row.high), float(row.low), float(row.close)) > 0 for row in rows),
        "non_negative_volume": all(float(row.volume) >= 0 for row in rows),
        "closed_candles_only": all(row.close_time.astimezone(UTC) < NOW for row in rows),
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {"status": "PASS" if not failed else "FAILED_DATA_QUALITY", "checks": checks, "failed_checks": failed}


def sma(values: list[float], period: int) -> float | None:
    return sum(values[-period:]) / period if len(values) >= period else None


def line_relation(close: float, value: float | None, name: str) -> str:
    if value is None:
        return f"{name}_UNAVAILABLE"
    return f"PRICE_{'ABOVE' if close > value else 'BELOW' if close < value else 'AT'}_{name}"


def technical(ind: dict[str, Any], rows: list[MarketCandles]) -> dict[str, Any]:
    closes = [float(row.close) for row in rows]
    close = closes[-1]
    values = {
        "sma_20": ind.get("sma_20"),
        "sma_50": sma(closes, 50),
        "sma_99": sma(closes, 99),
        "ema_12": ind.get("ema_12"),
        "ema_26": ind.get("ema_26"),
        "rsi_14": ind.get("rsi_14"),
        "macd": ind.get("macd"),
        "macd_signal": ind.get("macd_signal"),
        "macd_histogram": (ind["macd"] - ind["macd_signal"]) if ind.get("macd") is not None and ind.get("macd_signal") is not None else None,
        "atr_14": ind.get("atr_14"),
        "atr_ratio": ind.get("atr_ratio"),
        "adx_14": ind.get("adx_14"),
        "bollinger_mid": ind.get("bollinger_mid"),
        "bollinger_upper": ind.get("bollinger_upper"),
        "bollinger_lower": ind.get("bollinger_lower"),
        "vwap": ind.get("vwap"),
    }
    codes = list(ind.get("reason_codes", []))
    up = [code for code in codes if "BULLISH" in code or "PRICE_ABOVE" in code]
    down = [code for code in codes if "BEARISH" in code or "PRICE_BELOW" in code]
    blocked = [code for code in codes if code not in up and code not in down]
    lower, upper = values["bollinger_lower"], values["bollinger_upper"]
    return {
        "decision_candle": iso(rows[-1].open_time),
        "decision_close": close,
        "values": values,
        "price_relations": {name: line_relation(close, value, name.upper()) for name, value in values.items() if name.startswith(("sma", "ema")) or name == "vwap"},
        "bollinger_position": "UNAVAILABLE" if lower is None or upper is None else "ABOVE_UPPER" if close > upper else "BELOW_LOWER" if close < lower else "INSIDE_BANDS",
        "technical_votes": {
            "bullish_methods_count": ind.get("bullish_votes", 0),
            "bearish_methods_count": ind.get("bearish_votes", 0),
            "neutral_or_conflicted_count": max(0, len(blocked)),
            "supported_up": up,
            "supported_down": down,
            "blocked_direction": blocked,
            "formal_direction": ind.get("direction"),
        },
        "engine_raw_indicator_context": ind,
    }


def classify_swings(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prior: dict[str, float] = {}
    result = []
    for item in items:
        kind, price = str(item["point_type"]), float(item["price"])
        label = kind
        if kind in prior:
            label = ("HH" if price > prior[kind] else "LH") if kind == "HIGH" else ("HL" if price > prior[kind] else "LL")
        prior[kind] = price
        result.append({**item, "structure_label": label})
    return result


def structure(matrix: dict[str, Any]) -> dict[str, Any]:
    unified = matrix["unified_context"]
    alt = matrix["altunina_context"]
    schw = matrix["schwager_context"]
    breakout = schw["breakout_context"]
    hypotheses = matrix["hypothesis_result"]["hypotheses"]
    htypes = {item["hypothesis_type"]: item for item in hypotheses}
    swings = classify_swings(unified.get("structural_swing_points", []))
    return {
        "swing_high_swing_low_and_labels": swings,
        "latest_swings": swings[-10:],
        "range_boundaries": schw["trading_range"],
        "inside_close_ratio": schw["trading_range"].get("inside_close_ratio"),
        "breakout_or_breakdown": breakout,
        "retest": {"returned_to_range": breakout.get("returned_to_range"), "return_index": breakout.get("return_index"), "confirmation_method": breakout.get("confirmation_method")},
        "trap": {"false_breakout_confirmation": breakout.get("false_breakout_confirmation"), "invalidated": breakout.get("false_breakout_invalidated")},
        "polarity_flip": schw["polarity_flip_context"],
        "current_decision_window": unified["analysis_window"],
        "bearish_structure_exists": "BEARISH" in str(alt.get("structure_direction")),
        "bullish_reversal_exists": "BULLISH_REVERSAL" in htypes,
        "confirmed_range_exists": htypes.get("CONFIRMED_RANGE", {}).get("status") == "CONFIRMED",
        "engine_altunina_context": alt,
        "engine_schwager_context": schw,
    }


def candle_layer(matrix: dict[str, Any]) -> dict[str, Any]:
    nison = matrix["nison_context"]
    events = matrix["hypothesis_result"]["contextual_events"]
    bearish_continuation = [e for e in events if e["direction"] == "BEARISH" and e["role"] == "CONTINUATION"]
    bullish_reversal = [e for e in events if e["direction"] == "BULLISH" and e["role"] == "REVERSAL"]
    exhaustion_tokens = ("DOJI", "SMALL_BODY", "SHADOW", "EXHAUST")
    exhaustion = [code for code in nison["reason_codes"] if any(token in code for token in exhaustion_tokens)]
    confirmed = [e for e in events if e["status"] == "CONFIRMED"]
    return {
        "bearish_continuation_patterns": bearish_continuation,
        "bullish_reversal_patterns_on_rebound": bullish_reversal,
        "exhaustion_candles_or_clues": exhaustion,
        "confirmed_contextual_patterns": confirmed,
        "direction_confirmation_explanation": "Candle patterns confirm direction only when contextual event status is CONFIRMED; shapes needing context/follow-through do not confirm it.",
        "engine_nison_context": nison,
    }


def hypothesis_trace(hresult: dict[str, Any]) -> list[dict[str, Any]]:
    events = {item["event_id"]: item for item in hresult["contextual_events"]}
    output = []
    for item in hresult["hypotheses"]:
        status = item["status"]
        reasons = item.get("reason_codes", [])
        support = [events[event_id] for event_id in item.get("supporting_event_ids", []) if event_id in events]
        missing = [reason for reason in reasons if any(token in reason for token in ("PENDING", "REQUIRED", "NEEDS", "AWAIT"))]
        output.append({
            **item,
            "confidence": item["score"],
            "confidence_note": "Model exports score, not a separate per-hypothesis confidence; score is repeated as the available confidence proxy.",
            "evidence": {"reason_codes": reasons, "supporting_events": support},
            "missing_evidence": missing,
            "rejection_reason": reasons if status == "INVALIDATED" else None,
            "pending_reason": reasons if status == "PENDING" else None,
            "conflict_reason": reasons if status == "CONFLICTED" else None,
        })
    return output


def group_hypotheses(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups = {key: [] for key in ("CONFIRMED", "PENDING", "CONFLICTED", "INVALIDATED", "CANCELLED")}
    for item in items:
        groups.setdefault(item["status"], []).append(item)
    return groups


def safety(regime: str, decision: dict[str, Any], hypotheses: list[dict[str, Any]], rows: list[MarketCandles]) -> dict[str, Any]:
    selected = decision.get("selected_hypothesis")
    expected_direction = {"UP": "BULLISH", "DOWN": "BEARISH", "FLAT": "FLAT"}.get(regime)
    confirmed = [item for item in hypotheses if item["status"] == "CONFIRMED"]
    opposite = [item for item in confirmed if expected_direction and item["direction"] not in (expected_direction, "FLAT")]
    selected_confirmed = bool(selected and selected.get("status") == "CONFIRMED" and selected.get("direction") == expected_direction)
    period_return = float(rows[-1].close) / float(rows[0].open) - 1.0
    checks = {
        "false_up_after_declining_window": regime == "UP" and period_return < 0 and not selected_confirmed,
        "down_without_sufficient_confirmation": regime == "DOWN" and not selected_confirmed,
        "forced_answer_where_unknown_expected": regime != "UNKNOWN" and not selected_confirmed,
        "opposite_directional_conflicts": bool(opposite),
    }
    violations = [name for name, value in checks.items() if value]
    return {
        "safety_violation": bool(violations),
        "violations": violations,
        "checks": checks,
        "selected_hypothesis_confirmed_and_aligned": selected_confirmed,
        "opposite_confirmed_hypotheses": opposite,
        "window_return": period_return,
        "engine_safety_contract": {"trade_signal": "NOT_EVALUATED", "safe_for_runtime_trading": False, "live_trading_connected": False},
    }


def run_window(window_id: str, start: datetime, end: datetime, rows: list[MarketCandles], data_source: str) -> dict[str, Any]:
    dq = quality(rows, start, end)
    item: dict[str, Any] = {
        "window_id": window_id, "requested_start": iso(start), "requested_end": iso(end),
        "actual_start": iso(rows[0].open_time) if rows else None, "actual_end": iso(rows[-1].open_time) if rows else None,
        "candles": len(rows), "data_source": data_source, "data_quality": dq,
    }
    if dq["status"] != "PASS":
        item.update({"regime": "NOT_RUN", "selected_hypothesis": None, "selected_source": "DATA_QUALITY", "confidence": 0.0, "short_reason": "FAILED_DATA_QUALITY", "safety_audit": {"safety_violation": False, "violations": ["ENGINE_NOT_RUN"]}})
        return item
    request = CandleDataRequest(SYMBOL, INTERVAL, len(rows), iso(start), iso(end), data_source)
    batch = build_candle_data_batch(request, [row_dict(row) for row in rows], min_candle_count=96, strict_market_series=True)
    full = run_engine_trend_from_batch(batch).to_dict()
    composer = full["engine_output"]["composer_output"]
    matrix = composer["matrix"]
    decision, result = composer["decision_trace"], composer["result"]
    trace = hypothesis_trace(matrix["hypothesis_result"])
    groups = group_hypotheses(trace)
    regime = result["market_regime"]
    short = ", ".join(decision["reason_codes"][-4:])
    item.update({
        "regime": regime, "selected_hypothesis": decision.get("selected_hypothesis"), "selected_source": decision["decision_source"],
        "confidence": result["confidence"], "confirmed_hypotheses": groups["CONFIRMED"], "pending_hypotheses": groups["PENDING"],
        "conflicted_hypotheses": groups["CONFLICTED"], "rejected_cancelled_hypotheses": groups["INVALIDATED"] + groups["CANCELLED"],
        "short_reason": short, "composer_reasons": decision["reason_codes"], "candidate_scores": decision["candidate_scores"],
        "technical_indicators": technical(matrix["unified_context"]["indicator_context"], rows),
        "structure_context": structure(matrix), "nison_candle_layer": candle_layer(matrix),
        "hypothesis_diagnostics": trace, "safety_audit": safety(regime, decision, trace, rows), "full_engine_payload": full,
    })
    return item


def dump(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def md_json(value: Any) -> str:
    return "```json\n" + json.dumps(value, ensure_ascii=False, indent=2) + "\n```"


def write_reports(live: dict[str, Any], cov: dict[str, Any], trace: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    dump(LIVE_JSON, live)
    dump(COVERAGE_JSON, cov)
    dump(TRACE_JSON, trace)
    main = live["main_period"]
    lines = [
        "# ENGINE-TREND-19 SOLUSDT 15m — live/replay check", "",
        f"Generated: `{live['generated_at']}`. Audit/check-only; current engine code and defaults were used unchanged.", "",
        "## Formal answer", "",
        f"- Regime: **{main['regime']}**; confidence: `{main['confidence']:.6f}`; source: `{main['selected_source']}`.",
        f"- Selected hypothesis: `{(main.get('selected_hypothesis') or {}).get('hypothesis_type')}`.",
        f"- Short reason: `{main['short_reason']}`.",
        f"- Data source / quality: `{main['data_source']}` / `{main['data_quality']['status']}`.",
        f"- Safety violation: `{main['safety_audit']['safety_violation']}`.", "",
        "## Window sweep", "",
        "| window | actual_start | actual_end | candles | quality | regime | hypothesis | source | confidence | confirmed | pending | conflicted | safety | reason |",
        "|---|---|---|---:|---|---|---|---|---:|---:|---:|---:|---|---|",
    ]
    for w in live["window_sweep"]:
        lines.append(f"| {w['window_id']} | {w['actual_start']} | {w['actual_end']} | {w['candles']} | {w['data_quality']['status']} | {w['regime']} | {(w.get('selected_hypothesis') or {}).get('hypothesis_type')} | {w['selected_source']} | {w['confidence']:.6f} | {len(w.get('confirmed_hypotheses', []))} | {len(w.get('pending_hypotheses', []))} | {len(w.get('conflicted_hypotheses', []))} | {w['safety_audit']['safety_violation']} | {w['short_reason']} |")
    lines += ["", "## Why the model returned this regime", "", md_json({"selected_hypothesis": main.get("selected_hypothesis"), "candidate_scores": main.get("candidate_scores"), "composer_reasons": main.get("composer_reasons"), "hypothesis_presence": live["hypothesis_presence"]}), "", "## Technical indicators and votes", "", md_json(main.get("technical_indicators")), "", "## Structure/context diagnostics", "", md_json(main.get("structure_context")), "", "## Nison/candle layer", "", md_json(main.get("nison_candle_layer")), "", "## Hypotheses", "", md_json(main.get("hypothesis_diagnostics")), "", "## Safety audit", "", md_json(live["safety_audit"]), ""]
    LIVE_MD.write_text("\n".join(lines), encoding="utf-8")

    coverage_lines = ["# ENGINE-TREND-19 SOLUSDT 15m — data coverage", "", f"Generated: `{cov['generated_at']}`. Database was queried before Binance.", "", "| scope | expected | DB before | first after | last after | missing after | duplicates after | source | status |", "|---|---:|---:|---|---|---:|---:|---|---|"]
    for item in cov["scopes"]:
        a, b = item["after_backfill"], item["before_backfill"]
        coverage_lines.append(f"| {item['scope_id']} | {a['expected_candles']} | {b['found_candles']} | {a['first_candle_time']} | {a['last_candle_time']} | {a['missing_intervals_count']} | {a['duplicate_intervals_count']} | {item['source']} | {a['status']} |")
    coverage_lines += ["", "## Backfill operations", "", md_json(cov["backfill_operations"]), "", "## Data-quality checks", "", md_json(cov["data_quality"]), ""]
    COVERAGE_MD.write_text("\n".join(coverage_lines), encoding="utf-8")

    fields = ["window_id", "actual_start", "actual_end", "candles", "data_quality", "regime", "selected_hypothesis", "source", "confidence", "confirmed", "pending", "conflicted", "safety_violation", "short_reason"]
    with SWEEP_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for w in live["window_sweep"]:
            writer.writerow({"window_id": w["window_id"], "actual_start": w["actual_start"], "actual_end": w["actual_end"], "candles": w["candles"], "data_quality": w["data_quality"]["status"], "regime": w["regime"], "selected_hypothesis": (w.get("selected_hypothesis") or {}).get("hypothesis_type"), "source": w["selected_source"], "confidence": w["confidence"], "confirmed": len(w.get("confirmed_hypotheses", [])), "pending": len(w.get("pending_hypotheses", [])), "conflicted": len(w.get("conflicted_hypotheses", [])), "safety_violation": w["safety_audit"]["safety_violation"], "short_reason": w["short_reason"]})


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    session = get_session()
    try:
        db_stats = session.execute(select(func.count(), func.min(MarketCandles.open_time), func.max(MarketCandles.open_time)).where(MarketCandles.symbol == SYMBOL, MarketCandles.interval == INTERVAL)).one()
        scopes = [("SOLUSDT_15m_2026_07_08", MAIN_START, MAIN_END)] + [(wid, window_start(end), end) for wid, end in WINDOWS]
        before = {sid: coverage(load_rows(session, start, end), start, end) for sid, start, end in scopes}
        union_start = min(start for _, start, _ in scopes)
        union_end = max(end for _, _, end in scopes)
        present = {row.open_time.astimezone(UTC) for row in load_rows(session, union_start, union_end)}
        missing = [item for item in times(union_start, union_end) if item not in present]
        operations = []
        repository = CandleRepository(session)
        client = BinanceClient()
        for start, end_exclusive in contiguous_ranges(missing):
            allowed = set(item for item in times(start, end_exclusive - STEP) if item in missing)
            downloaded = client.load_klines(SYMBOL, INTERVAL, start, end_exclusive)
            closed_missing = [item for item in downloaded if item["open_time"] in allowed and item["close_time"] < NOW]
            written = repository.upsert_many(closed_missing)
            operations.append({"start": iso(start), "end_exclusive": iso(end_exclusive), "requested_missing_intervals": len(allowed), "downloaded_closed_candles": len(closed_missing), "inserted_missing_candles": written})

        coverage_scopes = []
        sources: dict[str, str] = {}
        for sid, start, end in scopes:
            after = coverage(load_rows(session, start, end), start, end)
            source = source_name(before[sid], after)
            sources[sid] = source
            coverage_scopes.append({"scope_id": sid, "requested_start": iso(start), "requested_end": iso(end), "before_backfill": before[sid], "after_backfill": after, "source": source})

        main_rows = load_rows(session, MAIN_START, MAIN_END)
        main_run = run_window("SOLUSDT_15m_2026_07_08", MAIN_START, MAIN_END, main_rows, sources["SOLUSDT_15m_2026_07_08"])
        sweep = [run_window(wid, window_start(end), end, load_rows(session, window_start(end), end), sources[wid]) for wid, end in WINDOWS]
        main_types = {item["hypothesis_type"]: item for item in main_run.get("hypothesis_diagnostics", [])}
        presence = {name: {"exists": name in main_types, "status": main_types.get(name, {}).get("status"), "reason_codes": main_types.get(name, {}).get("reason_codes", [])} for name in ("DOWN_CONTINUATION", "BEARISH_REVERSAL", "CONFIRMED_RANGE", "BULLISH_REVERSAL")}
        safety_summary = {"main_period": main_run["safety_audit"], "windows": {item["window_id"]: item["safety_audit"] for item in sweep}, "any_safety_violation": main_run["safety_audit"]["safety_violation"] or any(item["safety_audit"]["safety_violation"] for item in sweep)}
        cov = {"generated_at": iso(NOW), "exchange": "Binance Spot", "symbol": SYMBOL, "timeframe": INTERVAL, "database_checked_before_binance": True, "database_table": "market_candles", "database_before_backfill": {"symbol_interval_count": db_stats[0], "first_open_time": iso(db_stats[1]), "last_open_time": iso(db_stats[2])}, "required_union": {"start": iso(union_start), "end": iso(union_end), "expected_candles": len(times(union_start, union_end)), "found_before_backfill": len(present), "missing_before_backfill": len(missing)}, "backfill_operations": operations, "scopes": coverage_scopes, "data_quality": {"main": quality(main_rows, MAIN_START, MAIN_END), "windows": {item["window_id"]: item["data_quality"] for item in sweep}}, "status": "PASS" if all(item["after_backfill"]["status"] == "PASS" for item in coverage_scopes) else "FAILED_INSUFFICIENT_DATA"}
        live = {"generated_at": iso(NOW), "audit_id": "ENGINE-TREND-19", "exchange": "Binance Spot", "symbol": SYMBOL, "timeframe": INTERVAL, "main_period": main_run, "window_sweep": sweep, "hypothesis_presence": presence, "safety_audit": safety_summary, "change_attestation": {"runtime_code_changed": False, "trading_runtime_changed": False, "thresholds_changed": False, "enum_changed": False, "composer_changed": False, "market_hypothesis_changed": False, "technical_indicator_context_changed": False}}
        trace = {"generated_at": iso(NOW), "main_period": {"window_id": main_run["window_id"], "hypotheses": main_run.get("hypothesis_diagnostics", []), "contextual_events": main_run.get("full_engine_payload", {}).get("engine_output", {}).get("composer_output", {}).get("matrix", {}).get("hypothesis_result", {}).get("contextual_events", [])}, "windows": [{"window_id": item["window_id"], "regime": item["regime"], "selected_hypothesis": item.get("selected_hypothesis"), "hypotheses": item.get("hypothesis_diagnostics", [])} for item in sweep]}
        write_reports(live, cov, trace)
        artifacts = [LIVE_MD, LIVE_JSON, COVERAGE_MD, COVERAGE_JSON, SWEEP_CSV, TRACE_JSON, Path(__file__).resolve()]
        manifest = {"generated_at": iso(NOW), "audit_id": "ENGINE-TREND-19", "files": [{"path": str(path.relative_to(Path.cwd())) if path.is_absolute() else str(path), "bytes": path.stat().st_size, "sha256": sha256(path)} for path in artifacts] + [{"path": str(MANIFEST_JSON), "bytes": None, "sha256": None, "note": "self-entry; hash intentionally omitted"}], "change_attestation": live["change_attestation"]}
        dump(MANIFEST_JSON, manifest)
        print(json.dumps({"coverage": cov["status"], "backfilled": sum(op["inserted_missing_candles"] for op in operations), "main_regime": main_run["regime"], "sweep": {item["window_id"]: item["regime"] for item in sweep}, "safety_violation": safety_summary["any_safety_violation"]}, indent=2))
        return 0 if cov["status"] == "PASS" and main_run["regime"] != "NOT_RUN" else 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
