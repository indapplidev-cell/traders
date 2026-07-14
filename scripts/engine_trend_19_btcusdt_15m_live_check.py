"""Run the ENGINE-TREND-19 BTCUSDT 15m live-period audit.

This is an intentionally one-shot, reporting-only harness. It checks PostgreSQL
before using Binance, backfills only missing closed intervals, validates the
resulting market series, runs the existing engine, and writes the required
Markdown/JSON reports. It does not alter engine or trading runtime policy.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
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


SYMBOL = "BTCUSDT"
INTERVAL = "15m"
STEP = timedelta(minutes=15)
REPORT_DIR = Path("reports/engine_trend/live_market_checks")
LIVE_JSON = REPORT_DIR / "ENGINE_TREND_19_BTCUSDT_15M_LIVE_PERIOD_CHECK.json"
LIVE_MD = REPORT_DIR / "ENGINE_TREND_19_BTCUSDT_15M_LIVE_PERIOD_CHECK.md"
COVERAGE_JSON = REPORT_DIR / "ENGINE_TREND_19_BTCUSDT_15M_DATA_COVERAGE.json"
COVERAGE_MD = REPORT_DIR / "ENGINE_TREND_19_BTCUSDT_15M_DATA_COVERAGE.md"


@dataclass(frozen=True)
class Period:
    period_id: str
    requested_start: datetime
    requested_end: datetime
    engine_start: datetime
    expected: int

    @property
    def end_exclusive(self) -> datetime:
        return self.requested_end + STEP

    @property
    def engine_end_exclusive(self) -> datetime:
        return self.requested_end + STEP


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def latest_closed_open_time(now: datetime) -> datetime:
    boundary = now.replace(
        minute=(now.minute // 15) * 15,
        second=0,
        microsecond=0,
    )
    return boundary - STEP


def expected_times(start: datetime, end_exclusive: datetime) -> list[datetime]:
    values: list[datetime] = []
    cursor = start
    while cursor < end_exclusive:
        values.append(cursor)
        cursor += STEP
    return values


def periods_at(now: datetime) -> list[Period]:
    latest = latest_closed_open_time(now)
    day_start = datetime(2026, 7, 13, tzinfo=timezone.utc)
    if latest < day_start:
        raise RuntimeError("LATEST_CLOSED_CANDLE_PRECEDES_REQUESTED_LIVE_DAY")
    rolling_start = latest - STEP * 95
    return [
        Period(
            "BTCUSDT_15m_2026_07_10",
            datetime(2026, 7, 10, tzinfo=timezone.utc),
            datetime(2026, 7, 10, 23, 45, tzinfo=timezone.utc),
            datetime(2026, 7, 10, tzinfo=timezone.utc),
            96,
        ),
        Period(
            "BTCUSDT_15m_2026_07_12",
            datetime(2026, 7, 12, tzinfo=timezone.utc),
            datetime(2026, 7, 12, 23, 45, tzinfo=timezone.utc),
            datetime(2026, 7, 12, tzinfo=timezone.utc),
            96,
        ),
        Period(
            "BTCUSDT_15m_2026_07_13",
            day_start,
            latest,
            rolling_start if latest < datetime(2026, 7, 13, 23, 45, tzinfo=timezone.utc) else day_start,
            len(expected_times(day_start, latest + STEP)),
        ),
    ]


def load_db_rows(session: Any, start: datetime, end_exclusive: datetime) -> list[MarketCandles]:
    statement = (
        select(MarketCandles)
        .where(MarketCandles.symbol == SYMBOL)
        .where(MarketCandles.interval == INTERVAL)
        .where(MarketCandles.open_time >= start)
        .where(MarketCandles.open_time < end_exclusive)
        .order_by(MarketCandles.open_time.asc())
    )
    return list(session.scalars(statement))


def coverage(rows: Iterable[MarketCandles], start: datetime, end_exclusive: datetime) -> dict[str, Any]:
    items = list(rows)
    times = [item.open_time.astimezone(timezone.utc) for item in items]
    unique = set(times)
    expected = expected_times(start, end_exclusive)
    missing = [value for value in expected if value not in unique]
    duplicates = len(times) - len(unique)
    return {
        "expected": len(expected),
        "found": len(items),
        "unique": len(unique),
        "first_candle_time": iso(min(times) if times else None),
        "last_candle_time": iso(max(times) if times else None),
        "missing_intervals_count": len(missing),
        "missing_open_times": [iso(value) for value in missing],
        "duplicate_intervals_count": duplicates,
        "status": (
            "PASS"
            if len(items) == len(expected) and len(unique) == len(expected) and not missing
            else "INCOMPLETE"
        ),
    }


def contiguous_ranges(times: Iterable[datetime]) -> list[tuple[datetime, datetime]]:
    ordered = sorted(set(times))
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
    missing_count = sum(
        right - left != STEP for left, right in zip(times, times[1:])
    )
    checks = {
        "candle_count": len(rows) == expected_count,
        "regular_15m_cadence": all(
            right - left == STEP for left, right in zip(times, times[1:])
        ),
        "no_missing_intervals": missing_count == 0,
        "no_duplicate_intervals": len(times) == len(set(times)),
        "no_nan": all(not math.isnan(value) for value in numeric),
        "no_inf": all(math.isfinite(value) for value in numeric),
        "positive_ohlc": all(
            min(float(row.open), float(row.high), float(row.low), float(row.close)) > 0
            for row in rows
        ),
        "high_gte_open": all(row.high >= row.open for row in rows),
        "high_gte_close": all(row.high >= row.close for row in rows),
        "high_gte_low": all(row.high >= row.low for row in rows),
        "low_lte_open": all(row.low <= row.open for row in rows),
        "low_lte_close": all(row.low <= row.close for row in rows),
        "volume_non_negative": all(row.volume >= 0 for row in rows),
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "status": "PASS" if not failed else "FAILED_DATA_QUALITY",
        "expected_candles": expected_count,
        "actual_candles": len(rows),
        "checks": checks,
        "failed_checks": failed,
    }


def alignment(value: bool | None, bullish: str, bearish: str) -> str:
    if value is None:
        return "UNAVAILABLE_INSUFFICIENT_CANDLES"
    return bullish if value else bearish


def technical_diagnostics(indicators: dict[str, Any], last_close: float) -> dict[str, Any]:
    sma = indicators.get("sma_20")
    ema12 = indicators.get("ema_12")
    ema26 = indicators.get("ema_26")
    macd = indicators.get("macd")
    signal = indicators.get("macd_signal")
    lower = indicators.get("bollinger_lower")
    upper = indicators.get("bollinger_upper")
    vwap = indicators.get("vwap")
    return {
        "raw": indicators,
        "sma_alignment": alignment(None if sma is None else last_close >= sma, "PRICE_ABOVE_SMA20", "PRICE_BELOW_SMA20"),
        "ema_alignment": alignment(None if ema12 is None or ema26 is None else ema12 >= ema26, "EMA12_ABOVE_EMA26", "EMA12_BELOW_EMA26"),
        "rsi": {"value": indicators.get("rsi_14"), "available": indicators.get("rsi_14") is not None},
        "macd": {
            "value": macd,
            "signal": signal,
            "alignment": alignment(None if macd is None or signal is None else macd >= signal, "MACD_ABOVE_SIGNAL", "MACD_BELOW_SIGNAL"),
        },
        "atr_volatility_context": {"atr_14": indicators.get("atr_14"), "atr_ratio": indicators.get("atr_ratio")},
        "adx": {"value": indicators.get("adx_14"), "available": indicators.get("adx_14") is not None},
        "bollinger_bands": {
            "mid": indicators.get("bollinger_mid"),
            "upper": upper,
            "lower": lower,
            "price_position": (
                "UNAVAILABLE_INSUFFICIENT_CANDLES"
                if lower is None or upper is None
                else "ABOVE_UPPER" if last_close > upper
                else "BELOW_LOWER" if last_close < lower
                else "INSIDE_BANDS"
            ),
        },
        "vwap": {
            "value": vwap,
            "alignment": alignment(None if vwap is None else last_close >= vwap, "PRICE_ABOVE_VWAP", "PRICE_BELOW_VWAP"),
        },
        "independent_directional_methods": {
            "bullish": indicators.get("bullish_votes", 0),
            "bearish": indicators.get("bearish_votes", 0),
            "engine_indicator_direction": indicators.get("direction"),
        },
    }


def classified_swings(swings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    previous: dict[str, float] = {}
    result: list[dict[str, Any]] = []
    for item in swings:
        kind = item["point_type"]
        price = float(item["price"])
        label = kind
        if kind in previous:
            if kind == "HIGH":
                label = "HH" if price > previous[kind] else "LH"
            else:
                label = "HL" if price > previous[kind] else "LL"
        previous[kind] = price
        result.append({**item, "structure_label": label})
    return result


def structure_diagnostics(matrix: dict[str, Any], rows: list[MarketCandles]) -> dict[str, Any]:
    unified = matrix["unified_context"]
    schwager = matrix["schwager_context"]
    window = unified["analysis_window"]
    swings = classified_swings(unified["structural_swing_points"])
    breakout = schwager["breakout_context"]
    return {
        "swing_high_low_hh_hl_lh_ll": swings,
        "latest_structural_swings": swings[-8:],
        "range_boundaries": schwager["trading_range"],
        "breakout_breakdown": breakout,
        "retest": {
            "returned_to_range": breakout.get("returned_to_range"),
            "return_index": breakout.get("return_index"),
            "confirmation_method": breakout.get("confirmation_method"),
        },
        "trap": {
            "false_breakout_confirmation": breakout.get("false_breakout_confirmation"),
            "false_breakout_invalidated": breakout.get("false_breakout_invalidated"),
        },
        "polarity_flip": schwager["polarity_flip_context"],
        "current_decision_window": window,
        "windows": {
            "context_window": {
                "start_index": window["context_start_index"],
                "end_index": len(rows) - 1,
                "start": iso(rows[window["context_start_index"]].open_time),
                "end": iso(rows[-1].open_time),
            },
            "decision_window": {
                "start_index": window["decision_start_index"],
                "end_index": window["decision_end_index"],
                "start": iso(rows[window["decision_start_index"]].open_time),
                "end": iso(rows[window["decision_end_index"]].open_time),
            },
            "confirmation_window": {
                "lookahead_candles": window["confirmation_lookahead"],
                "note": "Formal lookahead allowance; no future candles beyond actual_end were supplied.",
            },
        },
        "engine_altunina_context": matrix["altunina_context"],
        "engine_schwager_context": schwager,
    }


def safety_audit(regime: str, decision: dict[str, Any], structure: dict[str, Any]) -> dict[str, Any]:
    selected = decision.get("selected_hypothesis")
    breakout = structure["breakout_breakdown"]
    polarity = structure["polarity_flip"]
    trading_range = structure["range_boundaries"]
    decision_start = structure["current_decision_window"]["decision_start_index"]
    selected_direction = {"UP": "BULLISH", "DOWN": "BEARISH", "FLAT": "FLAT"}.get(regime)
    confirmed_match = bool(
        selected
        and selected.get("status") == "CONFIRMED"
        and selected.get("direction") == selected_direction
    )
    bearish_breakdown = breakout.get("direction") == "DOWNWARD" and breakout.get("status") == "CONFIRMED"
    bullish_breakout = breakout.get("direction") == "UPWARD" and breakout.get("status") == "CONFIRMED"
    reclaim = bool(breakout.get("returned_to_range") or polarity.get("held"))
    failure_or_retest = bool(
        breakout.get("returned_to_range")
        or breakout.get("false_breakout_confirmation") == "CONFIRMED"
        or polarity.get("held")
    )
    checks = {
        "opposite_directional_flip_without_confirmation": regime in {"UP", "DOWN"} and not confirmed_match,
        "up_after_bearish_breakdown_without_reclaim": regime == "UP" and bearish_breakdown and not reclaim,
        "down_after_bullish_breakout_without_failure_or_retest": regime == "DOWN" and bullish_breakout and not failure_or_retest,
        "forced_answer_where_unknown_should_be_allowed": regime != "UNKNOWN" and not confirmed_match,
        "range_overridden_by_weak_trap": bool(
            regime in {"UP", "DOWN"}
            and trading_range.get("is_detected")
            and selected
            and "TRAP" in str(selected.get("hypothesis_type", ""))
            and float(selected.get("score", 0.0)) < 0.60
        ),
        "old_trend_context_used_as_current_decision": bool(
            regime in {"UP", "DOWN"}
            and selected
            and selected.get("trigger_index") is not None
            and int(selected["trigger_index"]) < int(decision_start)
        ),
    }
    violations = [name for name, violated in checks.items() if violated]
    return {
        "safety_violation": bool(violations),
        "safety_reason": violations if violations else ["NO_FORMAL_SAFETY_RULE_VIOLATION"],
        "checks": checks,
        "evidence": {
            "selected_hypothesis": selected,
            "breakout_direction": breakout.get("direction"),
            "breakout_status": breakout.get("status"),
            "returned_to_range": breakout.get("returned_to_range"),
            "polarity_flip_status": polarity.get("status"),
            "polarity_flip_held": polarity.get("held"),
            "decision_start_index": decision_start,
        },
    }


def hypotheses_by_status(payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    result = {name: [] for name in ("CONFIRMED", "PENDING", "CONFLICTED", "INVALIDATED", "CANCELLED")}
    for item in payload.get("hypotheses", []):
        result.setdefault(item.get("status", "UNKNOWN"), []).append(item)
    return result


def compact_names(items: list[dict[str, Any]]) -> str:
    if not items:
        return "—"
    return ", ".join(str(item.get("hypothesis_type", item.get("hypothesis_id"))) for item in items)


def json_block(value: Any) -> str:
    return "```json\n" + json.dumps(value, ensure_ascii=False, indent=2) + "\n```"


def write_reports(live: dict[str, Any], coverage_payload: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    LIVE_JSON.write_text(json.dumps(live, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    COVERAGE_JSON.write_text(json.dumps(coverage_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    coverage_lines = [
        "# ENGINE-TREND-19 BTCUSDT 15m Data Coverage",
        "",
        f"Generated at: `{coverage_payload['generated_at']}`. Database was checked before any Binance request.",
        "",
        "| period_id | requested_start | requested_end | actual_start | actual_end | expected | found_before_backfill | missing_before_backfill | duplicates_before_backfill | source | found_after_backfill | missing_after_backfill | duplicates_after_backfill | status |",
        "|---|---|---|---|---|---:|---:|---:|---:|---|---:|---:|---:|---|",
    ]
    for item in coverage_payload["periods"]:
        before, after = item["before_backfill"], item["after_backfill"]
        coverage_lines.append(
            f"| {item['period_id']} | {item['requested_start']} | {item['requested_end']} | "
            f"{after['first_candle_time']} | {after['last_candle_time']} | {item['expected']} | "
            f"{before['found']} | {before['missing_intervals_count']} | {before['duplicate_intervals_count']} | "
            f"{item['source']} | {after['found']} | {after['missing_intervals_count']} | "
            f"{after['duplicate_intervals_count']} | {after['status']} |"
        )
    coverage_lines.extend(["", "## Backfill operations", "", json_block(coverage_payload["backfill_operations"]), ""])
    COVERAGE_MD.write_text("\n".join(coverage_lines), encoding="utf-8")

    live_lines = [
        "# ENGINE-TREND-19 BTCUSDT 15m Live Period Check",
        "",
        f"Generated at: `{live['generated_at']}`. All timestamps are UTC; only closed Binance Spot candles were supplied.",
        "",
        "| period_id | actual_start | actual_end | candles | data_quality | data_source | regime | selected_hypothesis | source | confidence | confirmed | pending | conflicted | safety_violation | short_reason |",
        "|---|---|---|---:|---|---|---|---|---|---:|---|---|---|---|---|",
    ]
    for item in live["periods"]:
        engine = item.get("engine_output", {})
        groups = engine.get("hypotheses_by_status", {})
        live_lines.append(
            f"| {item['period_id']} | {item['actual_start']} | {item['actual_end']} | {item['candles']} | "
            f"{item['data_quality']['status']} | {item['data_source']} | {engine.get('regime', 'NOT_RUN')} | "
            f"{(engine.get('selected_hypothesis') or {}).get('hypothesis_type', '—')} | {engine.get('selected_source', '—')} | "
            f"{engine.get('confidence', 0.0):.6f} | {compact_names(groups.get('CONFIRMED', []))} | "
            f"{compact_names(groups.get('PENDING', []))} | {compact_names(groups.get('CONFLICTED', []))} | "
            f"{str(item['safety_audit'].get('safety_violation', False)).lower()} | {engine.get('short_reason', '—')} |"
        )
    for item in live["periods"]:
        live_lines.extend(
            [
                "",
                f"## {item['period_id']}",
                "",
                f"- Requested window: `{item['requested_start']}` — `{item['requested_end']}`.",
                f"- Engine window: `{item['actual_start']}` — `{item['actual_end']}` ({item['candles']} candles).",
                f"- Data source / quality: `{item['data_source']}` / `{item['data_quality']['status']}`.",
                "",
                "### Engine output",
                "",
                json_block(item["engine_output"]),
                "",
                "### Technical confirmation",
                "",
                json_block(item["technical_confirmation"]),
                "",
                "### Structure and context",
                "",
                json_block(item["structure_context"]),
                "",
                "### Safety audit",
                "",
                json_block(item["safety_audit"]),
            ]
        )
    live_lines.extend(["", "## Summary", "", json_block(live["summary"]), ""])
    LIVE_MD.write_text("\n".join(live_lines), encoding="utf-8")


def main() -> int:
    generated_at = utc_now()
    periods = periods_at(generated_at)
    session = get_session()
    try:
        db_count = int(
            session.scalar(
                select(func.count()).select_from(MarketCandles).where(
                    MarketCandles.symbol == SYMBOL,
                    MarketCandles.interval == INTERVAL,
                )
            )
            or 0
        )
        db_min, db_max = session.execute(
            select(func.min(MarketCandles.open_time), func.max(MarketCandles.open_time)).where(
                MarketCandles.symbol == SYMBOL,
                MarketCandles.interval == INTERVAL,
            )
        ).one()

        before: dict[str, dict[str, Any]] = {}
        required_missing: set[datetime] = set()
        for period in periods:
            requested_rows = load_db_rows(session, period.requested_start, period.end_exclusive)
            before[period.period_id] = coverage(requested_rows, period.requested_start, period.end_exclusive)
            engine_rows = load_db_rows(session, period.engine_start, period.engine_end_exclusive)
            present = {row.open_time.astimezone(timezone.utc) for row in engine_rows}
            required_missing.update(
                value
                for value in expected_times(period.engine_start, period.engine_end_exclusive)
                if value not in present
            )

        backfill_operations: list[dict[str, Any]] = []
        client = BinanceClient()
        repository = CandleRepository(session)
        for start, end_exclusive in contiguous_ranges(required_missing):
            downloaded = client.load_klines(SYMBOL, INTERVAL, start, end_exclusive)
            allowed = set(expected_times(start, end_exclusive))
            closed = [
                item
                for item in downloaded
                if item["open_time"] in allowed and item["close_time"] < generated_at
            ]
            written = repository.upsert_many(closed)
            backfill_operations.append(
                {
                    "start": iso(start),
                    "end_exclusive": iso(end_exclusive),
                    "requested_missing_intervals": len(allowed),
                    "downloaded_closed_candles": len(closed),
                    "upserted": written,
                }
            )

        coverage_periods: list[dict[str, Any]] = []
        live_periods: list[dict[str, Any]] = []
        for period in periods:
            requested_rows = load_db_rows(session, period.requested_start, period.end_exclusive)
            after = coverage(requested_rows, period.requested_start, period.end_exclusive)
            had_before = before[period.period_id]["found"] > 0
            needed_backfill = before[period.period_id]["missing_intervals_count"] > 0
            source = (
                "DB_ONLY"
                if not needed_backfill
                else "DB_PLUS_BINANCE_BACKFILL"
                if after["status"] == "PASS"
                else "FAILED_INSUFFICIENT_DATA"
            )
            coverage_periods.append(
                {
                    "period_id": period.period_id,
                    "requested_start": iso(period.requested_start),
                    "requested_end": iso(period.requested_end),
                    "expected": period.expected,
                    "found_in_db_before_backfill": had_before,
                    "before_backfill": before[period.period_id],
                    "source": source,
                    "after_backfill": after,
                }
            )

            rows = load_db_rows(session, period.engine_start, period.engine_end_exclusive)
            quality = data_quality(rows, len(expected_times(period.engine_start, period.engine_end_exclusive)))
            item: dict[str, Any] = {
                "period_id": period.period_id,
                "requested_start": iso(period.requested_start),
                "requested_end": iso(period.requested_end),
                "actual_start": iso(rows[0].open_time) if rows else None,
                "actual_end": iso(rows[-1].open_time) if rows else None,
                "candles": len(rows),
                "data_source": source,
                "data_quality": quality,
                "engine_output": {},
                "technical_confirmation": {},
                "structure_context": {},
                "safety_audit": {
                    "safety_violation": False,
                    "safety_reason": ["ENGINE_NOT_RUN_DATA_QUALITY_FAILED"],
                },
            }
            if quality["status"] == "PASS":
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
                boundary = run_engine_trend_from_batch(batch).to_dict()
                facade = boundary["engine_output"]
                composer = facade["composer_output"]
                decision = composer["decision_trace"]
                result = composer["result"]
                matrix = composer["matrix"]
                hypothesis_groups = hypotheses_by_status(matrix["hypothesis_result"])
                item["engine_output"] = {
                    "regime": result["market_regime"],
                    "selected_hypothesis": decision.get("selected_hypothesis"),
                    "selected_source": decision["decision_source"],
                    "confidence": result["confidence"],
                    "confirmed_hypotheses": hypothesis_groups["CONFIRMED"],
                    "pending_hypotheses": hypothesis_groups["PENDING"],
                    "conflicted_hypotheses": hypothesis_groups["CONFLICTED"],
                    "rejected_cancelled_hypotheses": hypothesis_groups["INVALIDATED"] + hypothesis_groups["CANCELLED"],
                    "hypotheses_by_status": hypothesis_groups,
                    "composer_reasons": decision["reason_codes"],
                    "short_reason": ", ".join(decision["reason_codes"][-3:]),
                    "full_payload": boundary,
                }
                indicators = matrix["unified_context"]["indicator_context"]
                item["technical_confirmation"] = technical_diagnostics(indicators, float(rows[-1].close))
                item["structure_context"] = structure_diagnostics(matrix, rows)
                item["safety_audit"] = safety_audit(
                    result["market_regime"], decision, item["structure_context"]
                )
            live_periods.append(item)

        coverage_payload = {
            "status": "COMPLETED" if all(item["after_backfill"]["status"] == "PASS" for item in coverage_periods) else "PARTIAL",
            "generated_at": iso(generated_at),
            "symbol": SYMBOL,
            "timeframe": INTERVAL,
            "database_checked_before_binance": True,
            "database_before_backfill": {
                "table": "market_candles",
                "symbol_interval_count": db_count,
                "first_open_time": iso(db_min),
                "last_open_time": iso(db_max),
            },
            "backfill_operations": backfill_operations,
            "periods": coverage_periods,
        }
        live = {
            "status": "COMPLETED" if all(item["data_quality"]["status"] == "PASS" and item["engine_output"] for item in live_periods) else "PARTIAL",
            "generated_at": iso(generated_at),
            "symbol": SYMBOL,
            "timeframe": INTERVAL,
            "periods": live_periods,
            "summary": {
                "period_count": len(live_periods),
                "regimes": {item["period_id"]: item["engine_output"].get("regime", "NOT_RUN") for item in live_periods},
                "safety_violation_periods": [item["period_id"] for item in live_periods if item["safety_audit"].get("safety_violation")],
                "data_quality_error_periods": [item["period_id"] for item in live_periods if item["data_quality"]["status"] != "PASS"],
                "runtime_code_changed_by_check": False,
                "trading_runtime_changed_by_check": False,
                "thresholds_changed_by_check": False,
            },
        }
        write_reports(live, coverage_payload)
        print(json.dumps({"coverage": coverage_payload["status"], "live": live["status"], "regimes": live["summary"]["regimes"], "reports": [str(LIVE_MD), str(LIVE_JSON), str(COVERAGE_MD), str(COVERAGE_JSON)]}, ensure_ascii=False, indent=2))
        return 0 if coverage_payload["status"] == "COMPLETED" and live["status"] == "COMPLETED" else 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
