"""Secret-safe production Scalping night diagnostic and deterministic replay.

Run inside the passive calibration container.  The script performs read-only
PostgreSQL queries, never prints connection material, and writes only bounded
causal trading data under the mounted reports directory.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import statistics
from typing import Any, Iterable, Mapping

import psycopg
from psycopg.rows import dict_row

from app.engine_paper.scalping_shadow import (
    CausalTarget,
    ShadowCostInputs,
    ShadowGeometryCandidate,
    ShadowGeometryConfig,
    evaluate_scalping_shadow,
    minimum_reward_bps_for_net_rr,
)


PROFILE = "trade-5m-v2"
SYMBOLS = (
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "LINKUSDT", "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "SUIUSDT",
)
STAGES = (
    "ANALYSIS", "STRUCTURAL_SETUP", "STRATEGY", "RISK_COMPATIBILITY",
    "GEOMETRY", "TARGET", "COSTS", "RR", "FINAL_PICK", "PLAN_PAPER",
)


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _number(value: object) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat().replace("+00:00", "Z")


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def distribution(values: Iterable[object]) -> dict[str, float | int | None]:
    numeric = [value for item in values if (value := _number(item)) is not None]
    result: dict[str, float | int | None] = {"count": len(numeric)}
    if not numeric:
        return {**result, **{key: None for key in (
            "min", "p01", "p05", "p10", "p25", "p50", "p75", "p90",
            "p95", "p99", "max", "mean", "std",
        )}}
    result.update({
        "min": min(numeric), "p01": _percentile(numeric, .01),
        "p05": _percentile(numeric, .05), "p10": _percentile(numeric, .10),
        "p25": _percentile(numeric, .25), "p50": _percentile(numeric, .50),
        "p75": _percentile(numeric, .75), "p90": _percentile(numeric, .90),
        "p95": _percentile(numeric, .95), "p99": _percentile(numeric, .99),
        "max": max(numeric), "mean": statistics.fmean(numeric),
        "std": statistics.pstdev(numeric),
    })
    return result


def _connect() -> psycopg.Connection[Any]:
    url = os.environ.get("DATABASE_URL")
    if url:
        return psycopg.connect(url, autocommit=True, row_factory=dict_row)
    secret = Path("/run/secrets/traders_shared_db_password")
    if not secret.is_file():
        raise RuntimeError("PROTECTED_DATABASE_BINDING_NOT_AVAILABLE")
    password = secret.read_text(encoding="utf-8").strip()
    return psycopg.connect(
        host="postgres", dbname="traders_ml", user="traders_ml",
        password=password, autocommit=True, row_factory=dict_row,
        application_name="traders_scalping_night_diagnostic_readonly",
    )


def load_rows(connection: psycopg.Connection[Any], start_ms: int, end_ms: int) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute("SET default_transaction_read_only = on")
        cursor.execute(
            """
            SELECT u.run_id,u.symbol,u.closed_until_ms,u.finished_at,u.duration_ms,
                   u.status pipeline_status,u.analysis_status,u.setup_status,
                   u.strategy_status,u.risk_status,u.paper_status,u.final_result,
                   u.final_reason,u.error_code,u.future_bars_used,u.daemon_instance_id,
                   r.id result_id,r.market_data_payload_json market,
                   r.analysis_payload_json analysis,r.setup_payload_json setup,
                   r.strategy_payload_json strategy,r.risk_payload_json risk,
                   r.paper_payload_json paper,r.module_reasons_json module_reasons,
                   r.module_warnings_json module_warnings,
                   r.safety_counters_json safety_counters
              FROM online_pipeline_runs u
              LEFT JOIN online_pipeline_results r ON r.run_id=u.run_id
             WHERE u.trade_profile_id=%s AND u.primary_timeframe='5m'
               AND u.closed_until_ms>%s AND u.closed_until_ms<=%s
             ORDER BY u.closed_until_ms,u.symbol,u.run_id
            """,
            (PROFILE, start_ms, end_ms),
        )
        return list(cursor.fetchall())


def _diagnostic(row: Mapping[str, Any]) -> dict[str, Any]:
    return _mapping(_mapping(row.get("paper")).get("paper_context")).get(
        "scalping_geometry_diagnostics", {}
    ) or {}


def _required_rr(row: Mapping[str, Any], diagnostic: Mapping[str, Any]) -> float | None:
    context = _mapping(_mapping(row.get("paper")).get("paper_context"))
    return _number(diagnostic.get("required_rr") or context.get("production_rr_floor") or 1.5)


def stage_trace(row: Mapping[str, Any], diagnostic: Mapping[str, Any]) -> dict[str, str]:
    setup, strategy, risk, paper = (
        _mapping(row.get(name)) for name in ("setup", "strategy", "risk", "paper")
    )
    setup_pass = str(row.get("setup_status") or "") not in {
        "", "NO_SETUP", "ERROR", "SKIPPED", "NO_DECISION",
    }
    strategy_pass = strategy.get("decision_status") in {
        "APPROVED", "PRE_APPROVED", "STRATEGY_APPROVED", "DECISION",
        "ALLOW_RESEARCH_TRADE_PLAN",
    }
    risk_pass = risk.get("risk_status") in {
        "RISK_APPROVED", "RISK_PRE_APPROVED_RESEARCH", "APPROVED",
    }
    rejection_stage = str(diagnostic.get("rejection_stage") or "")
    geometry_pass = bool(diagnostic) and rejection_stage not in {
        "CAUSAL_INVALIDATION", "ATR_BUFFER", "STOP_ENVELOPE",
    }
    target_pass = geometry_pass and bool(diagnostic.get("causal_target_exists"))
    costs_pass = target_pass and diagnostic.get("total_cost_bps") is not None
    required = _required_rr(row, diagnostic)
    rr_pass = bool(
        costs_pass and _number(diagnostic.get("net_rr")) is not None
        and required is not None and float(diagnostic["net_rr"]) >= required
        and bool(diagnostic.get("valid_plan"))
    )
    final_pick = paper.get("paper_status") == "PAPER_PLAN_READY"
    passes = (
        True, setup_pass, strategy_pass, risk_pass, geometry_pass, target_pass,
        costs_pass, rr_pass, final_pick, final_pick,
    )
    trace: dict[str, str] = {}
    reached = True
    for stage, passed in zip(STAGES, passes):
        trace[stage] = "PASS" if reached and passed else "REJECTED" if reached else "NOT_REACHED"
        reached = reached and passed
    return trace


def _reason(row: Mapping[str, Any], diagnostic: Mapping[str, Any]) -> str | None:
    if diagnostic.get("rejection_reason"):
        return str(diagnostic["rejection_reason"])
    reasons = _mapping(row.get("module_reasons"))
    setup_reasons = reasons.get("setup")
    if str(row.get("setup_status") or "") in {"NO_SETUP", "NO_DECISION"}:
        if isinstance(setup_reasons, list) and setup_reasons:
            return str(setup_reasons[-1])
        return "NO_STRUCTURAL_SETUP"
    flattened = [str(value) for values in reasons.values() for value in (values if isinstance(values, list) else [values])]
    return flattened[-1] if flattened else str(row.get("final_reason") or "") or None


def causal_record(row: Mapping[str, Any]) -> dict[str, Any]:
    analysis, setup, strategy, risk, paper = (
        _mapping(row.get(name)) for name in ("analysis", "setup", "strategy", "risk", "paper")
    )
    diagnostic = _mapping(_diagnostic(row))
    context = _mapping(paper.get("paper_context"))
    primitives = _mapping(context.get("causal_primitives"))
    direction = str(paper.get("paper_direction") or risk.get("direction_hint") or strategy.get("direction_hint") or "")
    side = "LONG" if direction == "BULLISH" else "SHORT" if direction == "BEARISH" else None
    trace = stage_trace(row, diagnostic)
    rejected_stage = next((stage for stage, status in trace.items() if status == "REJECTED"), None)
    cost_components = {
        key: _number(diagnostic.get(key)) for key in (
            "entry_fee_bps", "exit_fee_bps", "spread_bps",
            "entry_slippage_bps", "exit_slippage_bps", "depth_impact_bps",
            "safety_margin_bps",
        )
    }
    entry = _number(diagnostic.get("entry") or paper.get("hypothetical_entry_reference"))
    stop = _number(diagnostic.get("final_stop") or paper.get("hypothetical_stop_level"))
    target = _number(diagnostic.get("causal_target") or paper.get("hypothetical_target_level"))
    gross_reward = _number(diagnostic.get("gross_reward_bps"))
    gross_risk = _number(diagnostic.get("gross_risk_bps"))
    total_cost = _number(diagnostic.get("total_cost_bps"))
    required = _required_rr(row, diagnostic)
    minimum_required = None
    if gross_risk is not None and total_cost is not None and required is not None:
        minimum_required = minimum_reward_bps_for_net_rr(
            gross_risk_bps=gross_risk, total_cost_bps=total_cost,
            required_net_rr=required,
        )
    net_rr = _number(diagnostic.get("net_rr"))
    return {
        "timestamp": _iso(int(row["closed_until_ms"])),
        "boundary": int(row["closed_until_ms"]), "symbol": row.get("symbol"),
        "profile_id": PROFILE, "universe_id": "trading-universe-v2",
        "run_id": row.get("run_id"), "result_id": row.get("result_id"),
        "opportunity_id": diagnostic.get("opportunity_id") or setup.get("opportunity_id"),
        "candidate_id": diagnostic.get("candidate_id") or setup.get("setup_id"),
        "setup_type": setup.get("setup_type"), "setup_status": row.get("setup_status"),
        "setup_quality_score": _number(setup.get("quality_score")),
        "setup_diagnostics": setup.get("diagnostics") or _mapping(setup.get("context")).get("scalping"),
        "analysis_regime": analysis.get("regime"),
        "analysis_confidence": _number(analysis.get("confidence")),
        "strategy_type": strategy.get("strategy_type"),
        "strategy_score": _number(strategy.get("strategy_score")),
        "strategy_threshold": _number(strategy.get("strategy_quality_threshold")),
        "strategy_distance_to_threshold": _number(strategy.get("strategy_margin_to_threshold")),
        "strategy_rejection_reasons": strategy.get("rejection_reasons") or [],
        "risk_compatibility": risk.get("risk_status"), "side": side,
        "entry": entry, "entry_source": paper.get("entry_reference_source"),
        "structural_stop_raw": _number(diagnostic.get("raw_stop")),
        "stop_normalized": stop, "stop_source": paper.get("stop_source"),
        "stop_distance_absolute": None if entry is None or stop is None else abs(entry-stop),
        "stop_distance_bps": _number(diagnostic.get("stop_distance_bps")),
        "target_raw": (_mapping(diagnostic.get("first_causal_target")).get("target_price")),
        "target_normalized": target, "target_source": diagnostic.get("target_source_type") or paper.get("target_source"),
        "target_distance_absolute": None if entry is None or target is None else abs(entry-target),
        "target_distance_bps": _number(diagnostic.get("target_distance_bps")),
        "target_considerations": diagnostic.get("target_considerations") or [],
        "atr": _number(diagnostic.get("atr") or primitives.get("atr_value")),
        "atr_multiplier": _number(diagnostic.get("atr_buffer_multiplier")),
        "gross_reward_bps": gross_reward, "gross_risk_bps": gross_risk,
        "gross_rr": _number(diagnostic.get("gross_rr")),
        **cost_components, "total_round_trip_cost_bps": total_cost,
        "net_reward_bps": _number(diagnostic.get("net_reward_bps") or diagnostic.get("expected_net_edge_bps")),
        "net_risk_bps": _number(diagnostic.get("effective_risk_bps")),
        "net_rr": net_rr, "required_rr": required,
        "gross_net_rr_drag": None if net_rr is None or _number(diagnostic.get("gross_rr")) is None else float(diagnostic["gross_rr"])-net_rr,
        "gross_rr_minus_required": None if _number(diagnostic.get("gross_rr")) is None or required is None else float(diagnostic["gross_rr"])-required,
        "net_rr_minus_required": None if net_rr is None or required is None else net_rr-required,
        "minimum_economically_valid_target_bps": minimum_required,
        "actual_target_shortfall_bps": None if minimum_required is None or _number(diagnostic.get("target_distance_bps")) is None else minimum_required-float(diagnostic["target_distance_bps"]),
        "break_even_win_rate": _number(diagnostic.get("break_even_win_rate")),
        "quantity": _number(_mapping(paper.get("final_approval_generation")).get("quantity")),
        "notional": _number(_mapping(paper.get("final_approval_generation")).get("notional")),
        "risk_amount": _number(_mapping(paper.get("final_approval_generation")).get("risk_amount")),
        "stage_trace": trace, "stage_rejected": rejected_stage,
        "machine_reason": _reason(row, diagnostic), "terminal_reason": row.get("final_reason"),
        "plan_id": paper.get("paper_plan_id"),
        "approval_id": _mapping(paper.get("final_approval_generation")).get("final_approval_id"),
        "execution_command_id": None, "position_id": None,
        "future_bars_used": bool(row.get("future_bars_used")),
        "economic_input_timestamp_ms": diagnostic.get("economic_input_timestamp_ms"),
        "geometry_calculation_version": diagnostic.get("geometry_calculation_version") or "scalping-causal-geometry-v1",
        "cost_model_version": diagnostic.get("cost_model_version") or "scalping-round-trip-net-pnl-v1",
        "rr_policy_version": diagnostic.get("rr_policy_version") or "implicit-net-rr-1.5-v1",
        "target_policy_version": diagnostic.get("target_policy_version") or "first-positive-net-edge-target-v1",
    }


def replay_after(row: Mapping[str, Any], record: Mapping[str, Any]) -> dict[str, Any] | None:
    if record.get("side") not in {"LONG", "SHORT"} or record.get("entry") is None:
        return None
    diagnostic = _mapping(_diagnostic(row))
    considerations = diagnostic.get("target_considerations") or []
    targets: list[CausalTarget] = []
    for item in considerations:
        if not isinstance(item, Mapping) or item.get("target_price") is None:
            continue
        targets.append(CausalTarget(
            float(item["target_price"]), str(item.get("target_source") or "LOCAL_5M"),
            int(row["closed_until_ms"]) if item.get("future_safe") is not False else int(row["closed_until_ms"])+1,
            validated=bool(item.get("causal_valid", True)),
            relevant=bool(item.get("still_relevant", True)),
            achievable=bool(item.get("still_relevant", True)),
            timeframe=str(item.get("target_timeframe") or "5m"),
        ))
    if not targets and record.get("target_normalized") is not None:
        targets.append(CausalTarget(float(record["target_normalized"]), str(record.get("target_source") or "LOCAL_5M"), int(row["closed_until_ms"])))
    costs = ShadowCostInputs(
        entry_fee_bps=float(record.get("entry_fee_bps") or 10),
        exit_fee_bps=float(record.get("exit_fee_bps") or 10),
        entry_slippage_bps=float(record.get("entry_slippage_bps") or 2),
        exit_slippage_bps=float(record.get("exit_slippage_bps") or 2),
        safety_margin_bps=float(record.get("safety_margin_bps") or 3),
        spread_bps=record.get("spread_bps"), depth_impact_bps=record.get("depth_impact_bps"),
        spread_authoritative=record.get("spread_bps") is not None,
        depth_authoritative=record.get("depth_impact_bps") is not None,
    )
    result = evaluate_scalping_shadow(
        ShadowGeometryCandidate(
            trade_profile_id=PROFILE, symbol=str(record["symbol"]),
            boundary_ms=int(row["closed_until_ms"]),
            direction="BULLISH" if record["side"] == "LONG" else "BEARISH",
            entry=float(record["entry"]),
            causal_invalidation=_number(diagnostic.get("causal_invalidation")),
            atr=_number(diagnostic.get("atr")), targets=tuple(targets),
            setup_identity=str(record.get("opportunity_id") or record.get("setup_type")),
        ),
        costs,
        ShadowGeometryConfig(
            atr_buffer_multiplier=.25, stop_envelope_bps=80.0,
            minimum_target_diagnostic_bps=45.0,
        ),
    )
    return result.to_dict()


def funnel(records: list[Mapping[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    previous = len(records)
    for stage in STAGES:
        reached = [record for record in records if _mapping(record.get("stage_trace")).get(stage) != "NOT_REACHED"]
        passed = [record for record in records if _mapping(record.get("stage_trace")).get(stage) == "PASS"]
        rejected = [record for record in records if _mapping(record.get("stage_trace")).get(stage) == "REJECTED"]
        output[stage] = {
            "input_count": len(reached), "pass_count": len(passed),
            "reject_count": len(rejected),
            "conversion": len(passed)/previous if previous else None,
            "top_reject_reasons": dict(Counter(str(record.get("machine_reason")) for record in rejected).most_common(10)),
        }
        previous = len(passed)
    return output


def numeric_distributions(records: list[Mapping[str, Any]]) -> dict[str, Any]:
    keys = (
        "strategy_score", "atr", "stop_distance_bps", "target_distance_bps",
        "gross_rr", "net_rr", "required_rr", "gross_rr_minus_required",
        "net_rr_minus_required", "entry_fee_bps", "exit_fee_bps", "spread_bps",
        "gross_net_rr_drag",
        "entry_slippage_bps", "exit_slippage_bps", "depth_impact_bps",
        "total_round_trip_cost_bps", "break_even_win_rate", "quantity", "notional",
        "risk_amount", "actual_target_shortfall_bps",
    )
    return {key: distribution(record.get(key) for record in records) for key in keys}


def grouped(records: list[Mapping[str, Any]], key) -> dict[str, Any]:
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        groups[str(key(record) or "UNKNOWN")].append(record)
    return {
        name: {"count": len(values), "funnel": funnel(values), "distributions": numeric_distributions(values)}
        for name, values in sorted(groups.items())
    }


def quality(connection: psycopg.Connection[Any], start_ms: int, end_ms: int) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT closed_until_ms,count(*) rows,count(distinct symbol) symbols,
                      count(*)-count(distinct symbol) duplicate_symbols,
                      sum(CASE WHEN future_bars_used THEN 1 ELSE 0 END) future_rows
                 FROM online_pipeline_runs
                WHERE trade_profile_id=%s AND primary_timeframe='5m'
                  AND closed_until_ms>%s AND closed_until_ms<=%s
                GROUP BY closed_until_ms ORDER BY closed_until_ms""",
            (PROFILE, start_ms, end_ms),
        )
        boundaries = list(cursor.fetchall())
        cursor.execute(
            """SELECT count(*) rows,count(distinct (symbol,open_time_ms)) distinct_rows,
                      min(open_time_ms) min_open,max(open_time_ms) max_open
                 FROM candles_5m WHERE symbol=ANY(%s)
                  AND open_time_ms>=%s AND open_time_ms<%s""",
            (list(SYMBOLS), start_ms, end_ms),
        )
        candles = dict(cursor.fetchone())
    expected_boundaries = max(0, (end_ms-start_ms)//300_000)
    actual = {int(item["closed_until_ms"]): item for item in boundaries}
    expected = [start_ms+300_000*(index+1) for index in range(expected_boundaries)]
    missing_boundaries = [value for value in expected if value not in actual]
    partial = [int(value) for value, item in actual.items() if int(item["symbols"]) != len(SYMBOLS)]
    return {
        "expected_boundary_count": expected_boundaries,
        "actual_boundary_count": len(boundaries),
        "expected_symbols_per_boundary": len(SYMBOLS),
        "missing_boundaries": missing_boundaries, "partial_boundaries": partial,
        "duplicate_symbol_rows": sum(int(item["duplicate_symbols"]) for item in boundaries),
        "future_leakage_rows": sum(int(item["future_rows"] or 0) for item in boundaries),
        "candle_rows": int(candles["rows"]),
        "candle_distinct_rows": int(candles["distinct_rows"]),
        "duplicate_candles": int(candles["rows"])-int(candles["distinct_rows"]),
        "missing_candles": expected_boundaries*len(SYMBOLS)-int(candles["distinct_rows"]),
    }


def analyze(connection: psycopg.Connection[Any], start_ms: int, end_ms: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = load_rows(connection, start_ms, end_ms)
    records = [causal_record(row) for row in rows]
    after_results = [replay_after(row, record) for row, record in zip(rows, records)]
    for record, after in zip(records, after_results):
        record["after_replay"] = after
    rr_rows = [record for record in records if record.get("total_round_trip_cost_bps") is not None]
    after_pass = [item for item in after_results if item and item.get("valid_plan")]
    claimed_opportunities: set[str] = set()
    after_final_pick = 0
    for record, item in zip(records, after_results):
        if not item or not item.get("valid_plan"):
            continue
        identity = str(item.get("opportunity_id") or record.get("candidate_id"))
        if identity not in claimed_opportunities:
            claimed_opportunities.add(identity)
            after_final_pick += 1
    structural_rejected = [
        record for record in records
        if record.get("stage_rejected") == "STRUCTURAL_SETUP"
    ]
    structural_diagnostic_reasons: Counter[str] = Counter()
    structural_missing_conditions: Counter[str] = Counter()
    for record in structural_rejected:
        diagnostic = _mapping(record.get("setup_diagnostics"))
        structural_diagnostic_reasons.update(
            str(value) for value in diagnostic.get("diagnostic_reasons") or []
        )
        structural_missing_conditions.update(
            str(value) for value in diagnostic.get("missing_setup_conditions") or []
        )

    recompute_rows: list[dict[str, Any]] = []
    for record in rr_rows:
        components = [
            record.get(key) for key in (
                "entry_fee_bps", "exit_fee_bps", "spread_bps",
                "entry_slippage_bps", "exit_slippage_bps",
                "depth_impact_bps", "safety_margin_bps",
            )
        ]
        if any(value is None for value in components):
            continue
        total = sum(float(value) for value in components)
        reward = float(record["gross_reward_bps"])
        risk = float(record["gross_risk_bps"])
        net_reward = reward-total
        net_risk = risk+total
        net_rr = None if net_reward <= 0 else net_reward/net_risk
        recompute_rows.append({
            "side": record.get("side"),
            "cost_error": abs(total-float(record["total_round_trip_cost_bps"])),
            "net_reward_error": abs(net_reward-float(record["net_reward_bps"])),
            "net_risk_error": abs(net_risk-float(record["net_risk_bps"])),
            "net_rr_error": None if net_rr is None or record.get("net_rr") is None else abs(net_rr-float(record["net_rr"])),
        })

    def maximum_error(name: str, selected: list[Mapping[str, Any]]) -> float | None:
        values = [_number(item.get(name)) for item in selected]
        present = [value for value in values if value is not None]
        return max(present) if present else None
    report = {
        "window": {"start_ms": start_ms, "end_ms": end_ms, "start_utc": _iso(start_ms), "end_utc": _iso(end_ms), "timezone": "Europe/Moscow", "interval_semantics": "boundary_close > start and <= end"},
        "quality": quality(connection, start_ms, end_ms),
        "candidate_count": len(records), "funnel_before": funnel(records),
        "distributions": numeric_distributions(records),
        "slices": {
            "symbol": grouped(records, lambda item: item.get("symbol")),
            "setup": grouped(records, lambda item: item.get("setup_type")),
            "side": grouped(records, lambda item: item.get("side")),
            "hour_utc": grouped(records, lambda item: str(item.get("timestamp"))[11:13]),
            "stage_rejected": grouped(records, lambda item: item.get("stage_rejected")),
            "reason": grouped(records, lambda item: item.get("machine_reason")),
        },
        "rr_candidates": rr_rows,
        "rr_replay": {
            "input_count": len(rr_rows),
            "gross_threshold_pass_before": sum((record.get("gross_rr") or -1) >= (record.get("required_rr") or 1.5) for record in rr_rows),
            "net_threshold_pass_before": sum((record.get("net_rr") or -1) >= (record.get("required_rr") or 1.5) for record in rr_rows),
            "valid_plan_before": sum(_mapping(record.get("stage_trace")).get("PLAN_PAPER") == "PASS" for record in rr_rows),
            "valid_plan_after": len(after_pass),
            "final_pick_after_opportunity_dedup": after_final_pick,
            "plan_paper_after_opportunity_dedup": after_final_pick,
            "after_reasons": dict(Counter(str(item.get("rejection_reason")) for item in after_results if item and not item.get("valid_plan"))),
            "after_target_sources": dict(Counter(str(item.get("target_source_type")) for item in after_pass)),
        },
        "structural_rejections": dict(Counter(str(record.get("machine_reason")) for record in structural_rejected)),
        "structural_diagnosis": {
            "diagnostic_reasons": dict(structural_diagnostic_reasons),
            "missing_setup_conditions": dict(structural_missing_conditions),
            "distance_to_setup_condition": distribution(
                _mapping(record.get("setup_diagnostics")).get("distance_to_setup_condition")
                for record in structural_rejected
            ),
            "regime": dict(Counter(str(record.get("analysis_regime")) for record in structural_rejected)),
        },
        "formula_recompute": {
            side: {
                "count": len(selected),
                "max_cost_error_bps": maximum_error("cost_error", selected),
                "max_net_reward_error_bps": maximum_error("net_reward_error", selected),
                "max_net_risk_error_bps": maximum_error("net_risk_error", selected),
                "max_net_rr_error": maximum_error("net_rr_error", selected),
            }
            for side, selected in {
                "LONG": [item for item in recompute_rows if item.get("side") == "LONG"],
                "SHORT": [item for item in recompute_rows if item.get("side") == "SHORT"],
                "ALL": recompute_rows,
            }.items()
        },
        "version_identities": {
            "runtime_parameter_sets": sorted({str(_mapping(row.get("paper")).get("runtime_parameter_set_id")) for row in rows}),
            "daemon_instances": sorted({str(row.get("daemon_instance_id")) for row in rows}),
        },
        "safety": {"live_enabled": False, "binance_order_api_calls_by_script": 0, "production_mutations": 0, "secret_output": 0},
    }
    return records, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-ms", type=int, required=True)
    parser.add_argument("--end-ms", type=int, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.end_ms <= args.start_ms or not args.label.replace("-", "").replace("_", "").isalnum():
        raise SystemExit("INVALID_BOUNDED_WINDOW")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with _connect() as connection:
        records, report = analyze(connection, args.start_ms, args.end_ms)
    dataset = args.output_dir / f"{args.label}-candidates.jsonl"
    dataset.write_text("".join(json.dumps(item, sort_keys=True, separators=(",", ":"))+"\n" for item in records), encoding="utf-8")
    report_path = args.output_dir / f"{args.label}-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    summary = {
        "label": args.label, "candidate_count": len(records),
        "quality": report["quality"], "funnel_before": report["funnel_before"],
        "rr_replay": report["rr_replay"], "dataset": dataset.name,
        "report": report_path.name, "safety": report["safety"],
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
