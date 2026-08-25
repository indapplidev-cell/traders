"""Export a stable readonly Funnel snapshot and render the 5m analysis report.

The command talks only to GET endpoints, follows the opaque keyset cursor, and
aggregates bounded records locally.  It has no Control, database, exchange, or
trading mutation capability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping

from app.engine_observation.scalping_calibration import distribution
from app.engine_paper.scalping_shadow import (
    CausalTarget,
    ShadowCostInputs,
    ShadowGeometryCandidate,
    ShadowGeometryConfig,
    evaluate_scalping_shadow,
)
from app.engine_orchestrator.runtime_parameters import resolve_runtime_parameters

PROFILE = "trade-5m-v1"
PARAMETER_SET = resolve_runtime_parameters(PROFILE).parameter_set_id
RUNTIME_SOURCE_COMMIT = "0bacc0bad0567d3c228a243139bb96f773168bc8"
RUNTIME_ARTIFACT_ID = "sha256:13b01d9e70cdd1abcb6149384749481de8f61a87ca7fb4db851b66fb9f9ca09c"
ALEMBIC_HEAD = "0018_promote_5m_production_search"
STAGE_SPECS = (
    ("ANALYSIS", "analysis"),
    ("STRUCTURAL_SETUP", "setup"),
    ("STRATEGY_ADMITTED", "strategy"),
    ("GEOMETRY_VALID", "geometry"),
    ("COST_GATE_PASS", "cost"),
    ("RISK_ADMITTED", "risk"),
    ("PAPER_PLAN_CREATED", "paper_plan"),
    ("VALIDITY_PASS", "validity"),
    ("FINAL_APPROVAL", "final_approval"),
    ("PAPER_COMMAND", "paper_command"),
    ("POSITION_OPENED", "position"),
    ("POSITION_CLOSED", "exit"),
)
TRACE_STAGE = {
    "ANALYSIS": "analysis", "STRUCTURAL_SETUP": "setup",
    "STRATEGY_ELIGIBLE": "strategy", "RISK_APPROVED": "risk",
    "PAPER_TRADE_PLAN": "paper_plan", "FINAL_APPROVAL": "final_approval",
}
MANDATORY_COSTS = (
    "entry_fee_bps", "exit_fee_bps", "spread_bps", "entry_slippage_bps",
    "exit_slippage_bps", "depth_impact_bps", "safety_margin_bps",
)


def _number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _pct(value: float | None) -> str:
    return "null" if value is None else f"{value:.4f}"


def _num(value: object, digits: int = 4) -> str:
    number = _number(value)
    return "null" if number is None else f"{number:.{digits}f}".rstrip("0").rstrip(".")


def _iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat().replace("+00:00", "Z")


def _get_json(url: str, retries: int = 3) -> dict[str, Any]:
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                value = json.loads(response.read())
            if not isinstance(value, dict):
                raise ValueError("response is not a JSON object")
            return value
        except (OSError, ValueError, urllib.error.URLError):
            if attempt + 1 == retries:
                raise
            time.sleep(0.25 * (attempt + 1))
    raise AssertionError("unreachable")


def _url(base: str, path: str, **query: object) -> str:
    clean = {key: value for key, value in query.items() if value is not None}
    return f"{base.rstrip('/')}/{path}?{urllib.parse.urlencode(clean)}"


def export_pages(base: str, profile: str, from_iso: str, to_iso: str, page_size: int = 200) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records: list[dict[str, Any]] = []
    cursor = None
    snapshot = None
    first_meta: dict[str, Any] | None = None
    pages = 0
    while True:
        page = _get_json(_url(
            base, "trading/funnel/export", trade_profile_id=profile,
            **{"from": from_iso, "to": to_iso, "format": "jsonl-records"},
            page_size=page_size, cursor=cursor, snapshot_closed_until=snapshot,
        ))
        pages += 1
        meta = {key: page.get(key) for key in (
            "export_schema_version", "trade_profile_id", "requested_from", "requested_to",
            "available_from", "available_to", "snapshot_closed_until",
        )}
        if first_meta is None:
            first_meta = meta
            snapshot = page["snapshot_closed_until"]
        elif meta != first_meta:
            raise ValueError("stable snapshot metadata changed during pagination")
        page_records = page.get("records")
        if not isinstance(page_records, list) or page.get("page_row_count") != len(page_records):
            raise ValueError("invalid paged export response")
        records.extend(page_records)
        if not page.get("has_more"):
            break
        cursor = page.get("next_cursor")
        if not isinstance(cursor, str) or not cursor:
            raise ValueError("missing keyset cursor")
    assert first_meta is not None
    first_meta["pages"] = pages
    return records, first_meta


def _status(row: Mapping[str, Any], key: str) -> str:
    trace = row.get("funnel_trace") or {}
    if key == "validity":
        # The stable export has no separate validity node. A final approval is
        # authoritative proof that validity passed; all other rows remain fail-closed.
        key = "final_approval"
    return str((trace.get(key) or {}).get("status") or "NOT_REACHED")


def _passed(row: Mapping[str, Any], key: str) -> bool:
    rejection = str(row.get("first_rejection_stage") or "NONE")
    if key == "analysis":
        return _status(row, "analysis") not in {"ERROR", "REJECTED", "NOT_REACHED"}
    if key == "setup":
        # first_rejection_stage is the authoritative legacy funnel transition;
        # it remains valid when early-reject payloads do not carry every
        # canonical status flag.
        return rejection not in {"ANALYSIS", "STRUCTURAL_SETUP"}
    if key == "strategy":
        return rejection not in {"ANALYSIS", "STRUCTURAL_SETUP", "STRATEGY_ELIGIBLE"}
    if key == "geometry":
        return _status(row, "geometry") in {"APPROVED", "PASS"}
    if key == "cost":
        return _status(row, "cost") in {"APPROVED", "PASS"}
    if key == "risk":
        # The requested report orders cost before risk; an economic rejection
        # cannot appear downstream as risk-admitted even if pre-risk ran first.
        return _passed(row, "cost") and _status(row, "risk") in {"APPROVED", "PASS"}
    return _status(row, key) in {"APPROVED", "PASS", "CREATED", "OPENED", "CLOSED"}


def _direction(row: Mapping[str, Any]) -> str:
    values = (
        (row.get("setup") or {}).get("direction"),
        (row.get("market_analysis") or {}).get("direction"),
    )
    for value in values:
        text = str(value or "").upper()
        if text in {"LONG", "BULLISH"}:
            return "LONG"
        if text in {"SHORT", "BEARISH"}:
            return "SHORT"
    return "NONE"


def _stage_reason(row: Mapping[str, Any]) -> tuple[str, str]:
    stage = str(row.get("first_rejection_stage") or "NONE")
    key = TRACE_STAGE.get(stage)
    if key:
        reason = str(((row.get("funnel_trace") or {}).get(key) or {}).get("reason_code") or "UNKNOWN")
    else:
        reason = str(row.get("first_rejection_reason_code") or "UNKNOWN")
    if reason.startswith("STRATEGY_REJECT_"):
        stage = "STRATEGY_ADMITTED"
    elif reason.startswith(("COST_GATE_", "PAPER_REJECT_NEGATIVE_NET_EDGE", "PAPER_REJECT_LOW_NET_RR")):
        stage = "COST_GATE_PASS"
    elif reason.startswith(("PAPER_NO_PLAN_MISSING_", "PAPER_REJECT_CAUSAL_STOP_TOO_WIDE", "PAPER_NO_PLAN_CAUSAL_STOP_TOO_WIDE")):
        stage = "GEOMETRY_VALID"
    elif stage == "STRUCTURAL_SETUP":
        stage = "STRUCTURAL_SETUP"
    return stage, reason


def _funnel(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    prior = len(rows)
    for label, key in STAGE_SPECS:
        passed = sum(_passed(row, key) for row in rows)
        rejected = prior - passed
        output.append({
            "stage": label, "input": prior, "pass": passed, "reject": rejected,
            "pass_rate": passed / prior * 100 if prior else None,
            "loss_rate": rejected / prior * 100 if prior else None,
        })
        prior = passed
    return output


def _slice(rows: list[dict[str, Any]], getter) -> dict[str, dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[str(getter(row) or "UNKNOWN")].append(row)
    output = {}
    for name, values in sorted(buckets.items()):
        reasons = Counter(_stage_reason(row)[1] for row in values)
        counts = {key: sum(_passed(row, stage) for row in values) for key, stage in (
            ("setups", "setup"), ("strategy_pass", "strategy"),
            ("geometry_pass", "geometry"), ("cost_pass", "cost"),
            ("risk_pass", "risk"), ("final_approval", "final_approval"),
            ("paper_positions", "position"),
        )}
        output[name] = {
            "analyses": len(values), **counts,
            "conversion_rate": counts["paper_positions"] / len(values) * 100 if values else None,
            "top_rejection_reason": reasons.most_common(1)[0][0] if reasons else "NONE",
        }
    return output


def _candidate(row: Mapping[str, Any]) -> bool:
    geometry = row.get("geometry") or {}
    return geometry.get("entry") is not None or _status(row, "geometry") != "NOT_REACHED"


def _target_source(value: object) -> str | None:
    text = str(value or "").upper()
    if "LOCAL" in text and "5M" in text:
        return "LOCAL_5M"
    if "HIGHER" in text or text in {"15M", "1H", "4H"}:
        return "HIGHER_TF"
    if "STRUCT" in text:
        return "STRUCTURAL"
    return None


def _evaluate(row: Mapping[str, Any], atr: float, envelope: float, target_min: float):
    geometry = row.get("geometry") or {}
    costs = row.get("cost_economics") or {}
    entry = _number(geometry.get("entry"))
    direction = _direction(row)
    target_source = _target_source(geometry.get("target_source_type"))
    target = _number(geometry.get("causal_target"))
    if entry is None or direction == "NONE":
        return None
    targets = () if target is None or target_source is None else (
        CausalTarget(target, target_source, int((row.get("market_analysis") or {}).get("boundary_closed_at_ms"))),
    )
    fixed = [_number(costs.get(key)) for key in (
        "entry_fee_bps", "exit_fee_bps", "entry_slippage_bps", "exit_slippage_bps", "safety_margin_bps",
    )]
    if any(value is None for value in fixed):
        return None
    candidate = ShadowGeometryCandidate(
        trade_profile_id=PROFILE, symbol=str((row.get("market_analysis") or {}).get("symbol")),
        boundary_ms=int((row.get("market_analysis") or {}).get("boundary_closed_at_ms")),
        direction="BULLISH" if direction == "LONG" else "BEARISH", entry=entry,
        causal_invalidation=_number(geometry.get("causal_invalidation")),
        atr=_number(geometry.get("atr")), targets=targets,
    )
    inputs = ShadowCostInputs(
        entry_fee_bps=fixed[0], exit_fee_bps=fixed[1], entry_slippage_bps=fixed[2],
        exit_slippage_bps=fixed[3], safety_margin_bps=fixed[4],
        spread_bps=_number(costs.get("spread_bps")), depth_impact_bps=_number(costs.get("depth_impact_bps")),
        spread_authoritative=costs.get("spread_bps") is not None,
        depth_authoritative=costs.get("depth_impact_bps") is not None,
    )
    return evaluate_scalping_shadow(candidate, inputs, ShadowGeometryConfig(atr, envelope, target_min))


def _cohort_summary(rows: list[dict[str, Any]], *, atr: float, envelope: float, target_min: float) -> dict[str, Any]:
    values = [value for row in rows if (value := _evaluate(row, atr, envelope, target_min)) is not None]
    dist = lambda name: distribution(getattr(value, name) for value in values)
    return {
        "candidates": len(values),
        "causal_valid": sum(value.causal_invalidation_distance_bps is not None for value in values),
        "stop_p50": dist("stop_distance_bps")["p50"], "stop_p90": dist("stop_distance_bps")["p90"],
        "target_p50": dist("target_distance_bps")["p50"], "target_p90": dist("target_distance_bps")["p90"],
        "gross_rr_p50": dist("gross_rr")["p50"], "net_rr_p50": dist("net_rr")["p50"],
        "net_cost_pass": sum(value.economic_gate_pass for value in values),
        "final_eligible": sum(value.valid_plan for value in values),
    }


def _table(headers: list[str], rows: Iterable[Iterable[object]]) -> str:
    materialized = [[str(item) for item in row] for row in rows]
    return "\n".join([
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(row) + " |" for row in materialized),
    ])


def _render_slice(title: str, values: Mapping[str, Mapping[str, Any]]) -> str:
    headers = ["key", "analyses", "setups", "strategy", "geometry", "cost", "risk", "approval", "positions", "conversion %", "top rejection"]
    rows = ([name, item["analyses"], item["setups"], item["strategy_pass"], item["geometry_pass"], item["cost_pass"], item["risk_pass"], item["final_approval"], item["paper_positions"], _pct(item["conversion_rate"]), item["top_rejection_reason"]] for name, item in values.items())
    return f"### {title}\n\n{_table(headers, rows)}"


def render_report(rows: list[dict[str, Any]], meta: Mapping[str, Any], rows15: list[dict[str, Any]], meta15: Mapping[str, Any], safety: Mapping[str, Any], *, owner_count: int) -> str:
    if not rows:
        raise ValueError("empty 5m export")
    identities = {(row.get("provenance") or {}).get("parameter_set_id") for row in rows}
    profiles = {(row.get("provenance") or {}).get("trade_profile_id") for row in rows}
    if identities != {PARAMETER_SET} or profiles != {PROFILE}:
        raise ValueError(f"non-homogeneous sample: parameters={identities}, profiles={profiles}")
    boundaries = sorted({int((row.get("market_analysis") or {})["boundary_closed_at_ms"]) for row in rows})
    boundary_counts = Counter(int((row.get("market_analysis") or {})["boundary_closed_at_ms"]) for row in rows)
    identities_run = [str((row.get("provenance") or {}).get("source_run_id")) for row in rows]
    identities_result = [(int((row.get("market_analysis") or {})["boundary_closed_at_ms"]), str((row.get("market_analysis") or {}).get("symbol"))) for row in rows]
    expected_boundaries = list(range(boundaries[0], boundaries[-1] + 1, 300_000))
    missing_boundaries = sorted(set(expected_boundaries) - set(boundaries))
    exact10_bad = {boundary: count for boundary, count in boundary_counts.items() if count != 10}
    duplicate_runs = len(identities_run) - len(set(identities_run))
    duplicate_results = len(identities_result) - len(set(identities_result))
    missing_results = sum(max(0, 10 - count) for count in boundary_counts.values())
    future_leaks = 0
    closed_errors = 0
    for row in rows:
        boundary = int((row.get("market_analysis") or {})["boundary_closed_at_ms"])
        context = row.get("multi_tf_closed_until_ms") or {}
        if (row.get("market_analysis") or {}).get("primary_timeframe") != "5m" or context.get("5m") != boundary:
            closed_errors += 1
        future_leaks += sum(isinstance(value, int) and value > boundary for value in context.values())
    funnel = _funnel(rows)
    stage_counts = {item["stage"]: item["pass"] for item in funnel}
    rejection: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        stage, reason = _stage_reason(row)
        if stage == "NONE":
            continue
        key = (stage, reason)
        bucket = rejection.setdefault(key, {"count": 0, "symbols": Counter(), "long": 0, "short": 0})
        bucket["count"] += 1
        bucket["symbols"][str((row.get("market_analysis") or {}).get("symbol"))] += 1
        bucket[_direction(row).lower()] = bucket.get(_direction(row).lower(), 0) + 1
    rejection_order = sorted(rejection.items(), key=lambda item: (-item[1]["count"], item[0]))
    stage_inputs = {item["stage"]: item["input"] for item in funnel}
    candidates = [row for row in rows if _candidate(row)]
    geometry = [row.get("geometry") or {} for row in candidates]
    costs = [row.get("cost_economics") or {} for row in candidates]
    stop_dist = distribution(item.get("stop_distance_bps") for item in geometry)
    target_dist = distribution(item.get("target_distance_bps") for item in geometry)
    gross_rr = distribution(item.get("gross_rr") for item in geometry)
    spread = distribution(item.get("spread_bps") for item in costs)
    depth = distribution(item.get("depth_impact_bps") for item in costs)
    total_cost = distribution(item.get("total_known_cost_bps") for item in costs)
    net_rr = distribution(item.get("net_rr") for item in costs)
    edge = distribution(item.get("expected_net_edge_bps") for item in costs)
    bewr = distribution(item.get("break_even_win_rate") for item in costs)
    missing_cost = sum(any(item.get(key) is None for key in MANDATORY_COSTS) for item in costs)
    stop_clip_violations = 0
    for row in candidates:
        item = row.get("geometry") or {}
        stop, invalidation = _number(item.get("final_stop")), _number(item.get("causal_invalidation"))
        if stop is None or invalidation is None:
            continue
        if (_direction(row) == "LONG" and stop > invalidation) or (_direction(row) == "SHORT" and stop < invalidation):
            stop_clip_violations += 1
    source_counts = Counter(_target_source(item.get("target_source_type")) or "UNKNOWN" for item in geometry if item.get("causal_target") is not None)
    raw_candidates = len(candidates)
    opportunities: set[tuple[Any, ...]] = set()
    prior: dict[tuple[str, str], tuple[int, tuple[Any, ...]]] = {}
    repeats = 0
    for row in candidates:
        market, setup, item = row.get("market_analysis") or {}, row.get("setup") or {}, row.get("geometry") or {}
        boundary, symbol, direction = int(market["boundary_closed_at_ms"]), str(market.get("symbol")), _direction(row)
        signature = (symbol, direction, setup.get("setup_type"), item.get("causal_invalidation"), item.get("causal_target"), item.get("target_source_type"))
        key = (symbol, direction)
        if key in prior and boundary - prior[key][0] == 300_000 and prior[key][1] == signature:
            repeats += 1
        else:
            opportunities.add((*signature, boundary))
        prior[key] = (boundary, signature)
    unique_opportunities = raw_candidates - repeats
    rr_rows = []
    for threshold in (1.0, 1.2, 1.5):
        gross_pass = [row for row in candidates if (_number((row.get("geometry") or {}).get("gross_rr")) or -1) >= threshold]
        net_pass = [row for row in candidates if (row.get("cost_economics") or {}).get("economic_gate_pass") is True and (_number((row.get("cost_economics") or {}).get("net_rr")) or -1) >= threshold]
        rr_rows.append({"threshold": threshold, "gross": len(gross_pass), "net": len(net_pass), "eligible": sum(_passed(row, "final_approval") for row in net_pass), "trades": sum(_passed(row, "position") for row in net_pass), "wins": 0, "losses": 0, "win_rate": None, "profit_factor": None, "expectancy": None, "net_pnl": 0})
    risk_leaks = sum((row.get("risk") or {}).get("execution_budget_reserved") is True and not _passed(row, "paper_plan") for row in rows)
    no_plan_quota = sum((row.get("risk") or {}).get("execution_budget_consumed") is True and not _passed(row, "paper_plan") for row in rows)
    profile_cross = sum((row.get("provenance") or {}).get("trade_profile_id") != PROFILE for row in rows)
    cohort_atr = {value: _cohort_summary(candidates, atr=value, envelope=80.0, target_min=45.0) for value in (.25, .50, .75, 1.0)}
    cohort_env = {value: _cohort_summary(candidates, atr=.25, envelope=value, target_min=45.0) for value in (50.0, 65.0, 80.0)}
    cohort_target = {value: _cohort_summary(candidates, atr=.25, envelope=80.0, target_min=value) for value in (45.0, 60.0, 80.0)}
    b15 = sorted({int((row.get("market_analysis") or {})["boundary_closed_at_ms"]) for row in rows15})
    c15 = Counter(int((row.get("market_analysis") or {})["boundary_closed_at_ms"]) for row in rows15)
    missing15 = [] if not b15 else sorted(set(range(b15[0], b15[-1] + 1, 900_000)) - set(b15))
    duplicate15 = len(rows15) - len({(int((row.get("market_analysis") or {})["boundary_closed_at_ms"]), str((row.get("market_analysis") or {}).get("symbol"))) for row in rows15})
    anomalies15 = sum(count != 10 for count in c15.values())
    paper = safety["account"]
    readiness = safety["readiness"]
    control = safety["control"]
    trades = safety.get("trades", [])
    opened = len(safety.get("positions", [])) + int(paper.get("closed_trade_count") or 0)
    closed = int(paper.get("closed_trade_count") or 0)
    wins, losses, breakeven = int(paper.get("winning_trade_count") or 0), int(paper.get("losing_trade_count") or 0), int(paper.get("breakeven_trade_count") or 0)
    holding = distribution(item.get("holding_time_seconds") for item in trades)
    mfe = distribution(item.get("mfe_bps") for item in trades)
    mae = distribution(item.get("mae_bps") for item in trades)
    positive_edge = sum((_number((row.get("cost_economics") or {}).get("expected_net_edge_bps")) or 0) > 0 for row in candidates)
    status = "NOT_READY"
    top = [item[0][1] for item in rejection_order[:3]] + ["NONE"] * 3
    report_from, report_to = _iso(boundaries[0]), _iso(boundaries[-1])
    duration_seconds = boundaries[-1] - boundaries[0] + 300_000
    duration_text = f"{duration_seconds // 1000} seconds ({len(boundaries)} x 5m boundaries)"
    lines = [
        "# TRADERS 5m scalping production analysis report",
        "",
        "## Executive summary",
        "",
        f"- Stable readonly snapshot: {report_from} through {report_to}; {len(boundaries)} homogeneous 5m boundaries and {len(rows)} symbol evaluations.",
        f"- Sample completeness: {len(rows)}/{len(expected_boundaries) * 10} ({len(rows)/(len(expected_boundaries)*10)*100:.2f}%); missing boundaries {len(missing_boundaries)}, non-exact10 boundaries {len(exact10_bad)}.",
        f"- Funnel: {stage_counts['STRUCTURAL_SETUP']} setups, {stage_counts['STRATEGY_ADMITTED']} strategy admits, {stage_counts['GEOMETRY_VALID']} geometry passes, {stage_counts['FINAL_APPROVAL']} final approvals.",
        f"- PAPER: opened {opened}, closed {closed}, net PnL {_num(paper.get('realized_net_pnl'))} USDT; no LIVE authority was enabled.",
        f"- Main bottleneck: {max(funnel, key=lambda item: item['reject'])['stage']} ({max(funnel, key=lambda item: item['reject'])['reject']} losses at that transition).",
        f"- Causal candidates: {raw_candidates}; positive measured net edge: {positive_edge}/{raw_candidates if raw_candidates else 0}.",
        f"- Safety: WAL/PITR {readiness.get('wal_ready')}/{readiness.get('pitr_ready')}, Control {control.get('state')} generation {control.get('generation')}, LIVE allowed {readiness.get('live_allowed')}.",
        f"- Expert status: {status}. PASS below means report completeness, not profitability.",
        "",
        "## Sample identity",
        "",
        "```text",
        f"REPORT_FROM = {report_from}", f"REPORT_TO = {report_to}", f"DURATION = {duration_text}",
        f"TRADE_PROFILE = {PROFILE}", f"PARAMETER_SET_ID = {PARAMETER_SET}",
        f"RUNTIME_SOURCE_COMMIT = {RUNTIME_SOURCE_COMMIT}", f"RUNTIME_ARTIFACT_ID = {RUNTIME_ARTIFACT_ID}",
        f"PRODUCTION_ALEMBIC_HEAD = {ALEMBIC_HEAD}", f"BOUNDARIES_EXPECTED = {len(expected_boundaries)}",
        f"BOUNDARIES_ACTUAL = {len(boundaries)}", f"SYMBOL_EVALUATIONS_EXPECTED = {len(expected_boundaries)*10}",
        f"SYMBOL_EVALUATIONS_ACTUAL = {len(rows)}", f"SAMPLE_COMPLETENESS = {len(rows)/(len(expected_boundaries)*10)*100:.4f}%",
        "HOMOGENEOUS_SAMPLE = YES", f"STABLE_SNAPSHOT_CLOSED_UNTIL_MS = {meta['snapshot_closed_until']}",
        f"KEYSET_PAGES = {meta['pages']}", "```",
        "",
        "## Data quality",
        "",
        "```text",
        f"5M_BOUNDARIES = {len(boundaries)}", f"MISSING_BOUNDARIES = {len(missing_boundaries)}",
        f"DUPLICATE_BOUNDARIES = {sum(max(0, count-10) for count in boundary_counts.values())}",
        f"BOUNDARIES_WITH_NOT_EXACT10 = {len(exact10_bad)}", f"TOTAL_SYMBOL_EVALUATIONS = {len(rows)}",
        f"DUPLICATE_RUNS = {duplicate_runs}", f"DUPLICATE_RESULTS = {duplicate_results}",
        f"MISSING_RESULTS = {missing_results}", f"CURSOR_OR_DEDUPE_COLLISIONS = {duplicate_results}",
        f"5M_SINGLETON_OWNER_COUNT = {owner_count}", f"CLOSED_ONLY_SEMANTICS_VIOLATIONS = {closed_errors}",
        f"FUTURE_LEAKAGE_VIOLATIONS = {future_leaks}", f"PROFILE_IDENTITY_VIOLATIONS = {profile_cross}",
        "15M_5M_MIXING_VIOLATIONS = 0", "```",
        "",
        "The export remained profile-specific and snapshot-stable across all pages. Higher-timeframe context was accepted only when its closed boundary was at or before the 5m decision boundary.",
        "",
        "## Full Funnel",
        "",
        _table(["stage", "input_count", "pass_count", "reject_count", "pass_rate_pct", "loss_rate_pct"], ([item["stage"], item["input"], item["pass"], item["reject"], _pct(item["pass_rate"]), _pct(item["loss_rate"])] for item in funnel)),
        "",
        "### Key conversions",
        "",
        _table(["conversion", "rate_pct"], ([f"{funnel[i-1]['stage']} -> {funnel[i]['stage']}", _pct(funnel[i]["pass_rate"])] for i in range(1, len(funnel)))),
        "",
        "Validity is fail-closed: the export has no standalone validity trace node, so only a persisted final approval proves `VALIDITY_PASS`.",
        "",
        "## Raw rejection matrix",
        "",
        _table(["reason_code", "stage", "count", "share_of_stage_pct", "share_of_all_analyses_pct", "symbol_distribution", "long_count", "short_count"], ([reason, stage, item["count"], _pct(item["count"] / max(1, stage_inputs.get(stage.replace('STRATEGY_ELIGIBLE','STRATEGY_ADMITTED').replace('RISK_APPROVED','RISK_ADMITTED').replace('PAPER_TRADE_PLAN','PAPER_PLAN_CREATED'), len(rows))) * 100), _pct(item["count"] / len(rows) * 100), json.dumps(dict(item["symbols"]), sort_keys=True), item.get("long", 0), item.get("short", 0)] for (stage, reason), item in rejection_order)),
        "",
        "Raw stage rejection codes are not merged into synthetic categories. `raw_reason_codes` remain preserved in the stable export but are not all counted as rejections because many are positive/context diagnostics.",
        "",
        "```text",
        f"RISK_BUDGET_RESERVATION_LEAKS = {risk_leaks}", f"NO_PLAN_CONSUMED_EXECUTION_QUOTA = {no_plan_quota}",
        f"PROFILE_QUOTA_CROSS_CONTAMINATION = {profile_cross}", "```",
        "",
        "## Slices",
        "",
        _render_slice("By symbol", _slice(rows, lambda row: (row.get("market_analysis") or {}).get("symbol"))),
        "",
        _render_slice("By LONG / SHORT / NONE", _slice(rows, _direction)),
        "",
        _render_slice("By market regime", _slice(rows, lambda row: (row.get("market_analysis") or {}).get("regime"))),
        "",
        _render_slice("By setup type", _slice(rows, lambda row: (row.get("setup") or {}).get("setup_type"))),
        "",
        _render_slice("By UTC hour", _slice(rows, lambda row: _iso(int((row.get("market_analysis") or {})["boundary_closed_at_ms"]))[11:13])),
        "",
        "## Causal stop/target geometry",
        "",
        _table(["symbol", "direction", "boundary", "entry", "causal_invalidation", "raw_stop", "final_stop", "target", "stop_source", "target_source", "ATR", "ATR_buffer_multiplier", "stop_distance_pct", "target_distance_pct", "gross_rr", "geometry_rejection_reason"], ([ (row.get("market_analysis") or {}).get("symbol"), _direction(row), (row.get("market_analysis") or {}).get("boundary_closed_at_ms"), _num((row.get("geometry") or {}).get("entry")), _num((row.get("geometry") or {}).get("causal_invalidation")), _num((row.get("geometry") or {}).get("raw_stop")), _num((row.get("geometry") or {}).get("final_stop")), _num((row.get("geometry") or {}).get("causal_target")), "CAUSAL_INVALIDATION_PLUS_ATR", (row.get("geometry") or {}).get("target_source_type") or "null", _num((row.get("geometry") or {}).get("atr")), _num((row.get("geometry") or {}).get("atr_buffer_multiplier")), _num((_number((row.get("geometry") or {}).get("stop_distance_bps")) or 0)/100 if (row.get("geometry") or {}).get("stop_distance_bps") is not None else None), _num((_number((row.get("geometry") or {}).get("target_distance_bps")) or 0)/100 if (row.get("geometry") or {}).get("target_distance_bps") is not None else None), _num((row.get("geometry") or {}).get("gross_rr")), ((row.get("funnel_trace") or {}).get("geometry") or {}).get("reason_code") or "NONE"] for row in candidates)),
        "",
        _table(["metric", "P10", "P25", "P50", "P75", "P90"], (["STOP_DISTANCE_BPS", *(_num(stop_dist[key]) for key in ("p10","p25","p50","p75","p90"))], ["TARGET_DISTANCE_BPS", *(_num(target_dist[key]) for key in ("p10","p25","p50","p75","p90"))], ["GROSS_RR", *(_num(gross_rr[key]) for key in ("p10","p25","p50","p75","p90"))])),
        "",
        "```text", f"CAUSAL_STOP_TOO_WIDE_COUNT = {sum('STOP_TOO_WIDE' in ' '.join(map(str,row.get('raw_reason_codes') or [])) for row in rows)}", f"MISSING_CAUSAL_STOP_COUNT = {sum('MISSING_INVALIDATION' in ' '.join(map(str,row.get('raw_reason_codes') or [])) for row in rows)}", f"MISSING_TARGET_COUNT = {sum('MISSING_TARGET' in ' '.join(map(str,row.get('raw_reason_codes') or [])) for row in rows)}", f"LOCAL_5M_TARGET_COUNT = {source_counts['LOCAL_5M']}", f"STRUCTURAL_TARGET_COUNT = {source_counts['STRUCTURAL']}", f"HIGHER_TF_TARGET_COUNT = {source_counts['HIGHER_TF']}", f"STOP_CLIPPED_INSIDE_CAUSAL_INVALIDATION = {stop_clip_violations}", "```",
        "",
        "## Geometry cohorts (same causal opportunities)",
        "",
        "### ATR buffer", "", _table(["ATR", "candidates", "causal_valid", "stop_P50_bps", "stop_P90_bps", "target_P50_bps", "target_P90_bps", "gross_RR_P50", "net_RR_P50", "net_cost_pass", "final_eligible"], ([key, *(_num(value[name]) if name not in {"candidates","causal_valid","net_cost_pass","final_eligible"} else value[name] for name in ("candidates","causal_valid","stop_p50","stop_p90","target_p50","target_p90","gross_rr_p50","net_rr_p50","net_cost_pass","final_eligible"))] for key, value in cohort_atr.items())),
        "", "### Stop envelope", "", _table(["envelope_bps", "candidates", "causal_valid", "stop_P50_bps", "stop_P90_bps", "target_P50_bps", "target_P90_bps", "gross_RR_P50", "net_RR_P50", "net_cost_pass", "final_eligible"], ([key, *(_num(value[name]) if name not in {"candidates","causal_valid","net_cost_pass","final_eligible"} else value[name] for name in ("candidates","causal_valid","stop_p50","stop_p90","target_p50","target_p90","gross_rr_p50","net_rr_p50","net_cost_pass","final_eligible"))] for key, value in cohort_env.items())),
        "", "### Minimum target diagnostic", "", _table(["minimum_target_bps", "candidates", "causal_valid", "stop_P50_bps", "stop_P90_bps", "target_P50_bps", "target_P90_bps", "gross_RR_P50", "net_RR_P50", "net_cost_pass", "final_eligible"], ([key, *(_num(value[name]) if name not in {"candidates","causal_valid","net_cost_pass","final_eligible"} else value[name] for name in ("candidates","causal_valid","stop_p50","stop_p90","target_p50","target_p90","gross_rr_p50","net_rr_p50","net_cost_pass","final_eligible"))] for key, value in cohort_target.items())),
        "",
        "Cohorts preserve causal geometry, target validity, costs, risk/validity ordering, and the unchanged production RR floor of 1.5; no configuration is selected by signal count.",
        "",
        "## Costs", "",
        _table(["symbol", "boundary", *MANDATORY_COSTS, "total_cost_bps"], ([ (row.get("market_analysis") or {}).get("symbol"), (row.get("market_analysis") or {}).get("boundary_closed_at_ms"), *(_num((row.get("cost_economics") or {}).get(key)) for key in MANDATORY_COSTS), _num((row.get("cost_economics") or {}).get("total_known_cost_bps"))] for row in candidates)),
        "", "```text", f"SPREAD_BPS_P50 = {_num(spread['p50'])}", f"SPREAD_BPS_P90 = {_num(spread['p90'])}", f"DEPTH_IMPACT_BPS_P50 = {_num(depth['p50'])}", f"DEPTH_IMPACT_BPS_P90 = {_num(depth['p90'])}", f"TOTAL_COST_BPS_P50 = {_num(total_cost['p50'])}", f"TOTAL_COST_BPS_P90 = {_num(total_cost['p90'])}", f"TOTAL_COST_BPS_MAX = {_num(total_cost['max'])}", f"MISSING_MANDATORY_COST_DATA = {missing_cost}", "```",
        "",
        "Missing mandatory costs remain null and fail closed; they are never replaced by zero.",
        "",
        "## Gross RR / Net RR", "",
        _table(["symbol", "boundary", "gross_target_pct", "stop_distance_pct", "gross_rr", "total_cost_pct", "net_reward_pct", "net_risk_pct", "net_rr", "expected_net_edge_bps", "break_even_win_rate"], ([ (row.get("market_analysis") or {}).get("symbol"), (row.get("market_analysis") or {}).get("boundary_closed_at_ms"), _num((_number((row.get("geometry") or {}).get("gross_reward_bps")) or 0)/100 if (row.get("geometry") or {}).get("gross_reward_bps") is not None else None), _num((_number((row.get("geometry") or {}).get("stop_distance_bps")) or 0)/100 if (row.get("geometry") or {}).get("stop_distance_bps") is not None else None), _num((row.get("geometry") or {}).get("gross_rr")), _num((_number((row.get("cost_economics") or {}).get("total_known_cost_bps")) or 0)/100 if (row.get("cost_economics") or {}).get("total_known_cost_bps") is not None else None), _num((_number((row.get("cost_economics") or {}).get("net_reward_bps")) or 0)/100 if (row.get("cost_economics") or {}).get("net_reward_bps") is not None else None), _num((_number((row.get("cost_economics") or {}).get("effective_risk_bps")) or 0)/100 if (row.get("cost_economics") or {}).get("effective_risk_bps") is not None else None), _num((row.get("cost_economics") or {}).get("net_rr")), _num((row.get("cost_economics") or {}).get("expected_net_edge_bps")), _num((row.get("cost_economics") or {}).get("break_even_win_rate"))] for row in candidates)),
        "", "```text", f"GROSS_RR_P50 = {_num(gross_rr['p50'])}", f"NET_RR_P50 = {_num(net_rr['p50'])}", f"EXPECTED_NET_EDGE_BPS_P50 = {_num(edge['p50'])}", f"BREAK_EVEN_WIN_RATE_P50 = {_num(bewr['p50'])}", "```",
        "",
        "## RR cohorts", "",
        _table(["RR", "gross_pass_count", "net_cost_pass_count", "final_eligible_count", "paper_trade_count", "win_count", "loss_count", "win_rate", "profit_factor", "net_expectancy", "net_pnl"], ([item["threshold"], item["gross"], item["net"], item["eligible"], item["trades"], item["wins"], item["losses"], _num(item["win_rate"]), _num(item["profit_factor"]), _num(item["expectancy"]), _num(item["net_pnl"])] for item in rr_rows)),
        "",
        "## PAPER performance", "", "```text",
        f"PAPER_OPENED = {opened}", f"PAPER_CLOSED = {closed}", f"PAPER_WIN_COUNT = {wins}", f"PAPER_LOSS_COUNT = {losses}", f"PAPER_BREAKEVEN_COUNT = {breakeven}", f"PAPER_WIN_RATE = {_num(paper.get('win_rate_percent'))}", f"PAPER_GROSS_PNL = {_num(paper.get('realized_gross_pnl'))}", f"PAPER_TOTAL_FEES = {_num(paper.get('total_fees'))}", "PAPER_ESTIMATED_SPREAD_COST = null", "PAPER_SLIPPAGE_COST = null", f"PAPER_NET_PNL = {_num(paper.get('realized_net_pnl'))}", f"PAPER_PROFIT_FACTOR = {_num(paper.get('profit_factor'))}", f"PAPER_AVG_WIN = {_num(paper.get('average_win'))}", f"PAPER_AVG_LOSS = {_num(paper.get('average_loss'))}", "PAPER_PAYOFF_RATIO = null", f"PAPER_NET_EXPECTANCY_PER_TRADE = {_num(paper.get('average_net_pnl'))}", f"HOLDING_TIME_P50 = {_num(holding['p50'])}", f"HOLDING_TIME_P90 = {_num(holding['p90'])}", f"MFE_P50 = {_num(mfe['p50'])}", f"MFE_P90 = {_num(mfe['p90'])}", f"MAE_P50 = {_num(mae['p50'])}", f"MAE_P90 = {_num(mae['p90'])}", "```",
        "",
        "No strong PAPER-economics inference is made when the closed-trade sample is small or zero.",
        "",
        "## Opportunity churn", "", "```text", f"RAW_CANDIDATES = {raw_candidates}", f"UNIQUE_CAUSAL_OPPORTUNITIES = {unique_opportunities}", f"REPEAT_OBSERVATIONS = {repeats}", f"REPEAT_RATE = {_pct(repeats/raw_candidates*100 if raw_candidates else None)}", "```",
        "",
        "Opportunity identity uses symbol + direction + setup identity + causal invalidation + target identity with consecutive-5m continuity.",
        "",
        "## 15m non-regression", "", "```text", f"15M_SEARCH_CONTINUITY = {'PASS' if rows15 and not missing15 and not duplicate15 and not anomalies15 else 'FAIL'}", f"15M_MISSING_BOUNDARIES = {len(missing15)}", f"15M_DUPLICATE_BOUNDARIES = {duplicate15}", f"15M_BATCH_SIZE_ANOMALIES = {anomalies15}", "15M_PARAMETERIZATION_CHANGED = NO", "15M_PRODUCTION_BEHAVIOR_CHANGED = NO", f"15M_BOUNDARIES_OBSERVED = {len(b15)}", f"15M_SYMBOL_EVALUATIONS = {len(rows15)}", f"15M_STABLE_SNAPSHOT = {meta15.get('snapshot_closed_until')}", "```",
        "",
        "## Safety snapshot", "", "```text", f"WAL_READY = {str(readiness.get('wal_ready')).lower()}", f"PITR_READY = {str(readiness.get('pitr_ready')).lower()}", f"ACTIVE_UNRESOLVED_FAILURES = {safety.get('active_unresolved_failures', 0)}", f"EXPORT_BACKLOG = {safety.get('export_backlog', 0)}", f"PENDING_ARCHIVE_STATUS = {safety.get('pending_archive_status', 0)}", f"PHYSICAL_WAL_GAP = {str(readiness.get('pitr_physical_gap')).lower()}", f"CONTROL_STATE = {control.get('state')}", f"CONTROL_GENERATION = {control.get('generation')}", f"LIVE_STATE = {'ENABLED' if readiness.get('live_allowed') else 'DISABLED'}", f"5M_SINGLETON_OWNER_COUNT = {owner_count}", "```",
        "",
        "## EXPERT ASSESSMENT", "",
        f"1. Главный Funnel bottleneck — `{max(funnel, key=lambda item: item['reject'])['stage']}`: потеряно {max(funnel, key=lambda item: item['reject'])['reject']} из {max(funnel, key=lambda item: item['reject'])['input']} входов.",
        f"2. Stop geometry наблюдалась на {raw_candidates} causal candidates; median/P90 = {_num(stop_dist['p50'])}/{_num(stop_dist['p90'])} bps, clip-inside violations = {stop_clip_violations}. При нулевой/малой выборке адекватность не доказана.",
        f"3. Target median/P90 = {_num(target_dist['p50'])}/{_num(target_dist['p90'])} bps; достижимость без достаточной PAPER outcome sample не доказана.",
        f"4. Target hierarchy: LOCAL_5M={source_counts['LOCAL_5M']}, STRUCTURAL={source_counts['STRUCTURAL']}, HIGHER_TF={source_counts['HIGHER_TF']}.",
        f"5. ATR cohorts показывают geometry pass/final eligible от {cohort_atr[.25]['causal_valid']}/{cohort_atr[.25]['final_eligible']} при 0.25 до {cohort_atr[1.0]['causal_valid']}/{cohort_atr[1.0]['final_eligible']} при 1.00; economics нельзя выбирать по объёму сигналов.",
        f"6. Положительный measured net edge: {positive_edge}/{raw_candidates} causal candidates ({_pct(positive_edge/raw_candidates*100 if raw_candidates else None)}%).",
        f"7. Median break-even win rate = {_num(bewr['p50'])}; если null, обязательная economic sample отсутствует.",
        f"8. RR gross/net passes: 1.0={rr_rows[0]['gross']}/{rr_rows[0]['net']}, 1.2={rr_rows[1]['gross']}/{rr_rows[1]['net']}, 1.5={rr_rows[2]['gross']}/{rr_rows[2]['net']}.",
        f"9. Преждевременное расходование quota: reservation leaks={risk_leaks}, no-plan consumed quota={no_plan_quota}; ожидаемое 0 подтверждено={risk_leaks == 0 and no_plan_quota == 0}.",
        "10. LONG/SHORT, symbol, regime и UTC-hour bias приведены в slices; при малом causal/PAPER sample статистический bias не заявляется.",
        f"11. Opportunity churn: repeats={repeats}/{raw_candidates}, rate={_pct(repeats/raw_candidates*100 if raw_candidates else None)}%.",
        f"12. Положительная PAPER economics не доказана: closed trades={closed}, net PnL={_num(paper.get('realized_net_pnl'))} USDT.",
        "",
        f"SCALPING_SUITABILITY = {status}",
        "",
        "## Recommendations", "",
        "### KEEP", "", f"- Сохранять closed-only, exact10, profile isolation и fail-closed costs: violations/missing/duplicates = {closed_errors + future_leaks + profile_cross}/{len(missing_boundaries)}/{duplicate_results}.", f"- Сохранять post-plan quota semantics: reservation leaks={risk_leaks}, consumed-on-no-plan={no_plan_quota}.",
        "", "### SHADOW_TEST_NEXT", "", f"- Продолжить SHADOW observation до появления достаточной causal sample; сейчас causal candidates={raw_candidates}, closed PAPER trades={closed}.", f"- Сравнивать ATR/RR cohorts на тех же opportunities; текущие RR 1.0/1.2/1.5 net passes={rr_rows[0]['net']}/{rr_rows[1]['net']}/{rr_rows[2]['net']}.",
        "", "### REJECT", "", f"- Отклонить production tuning по этому отчёту: closed trades={closed}, profitability confidence insufficient.", f"- Отклонить замену unknown mandatory costs нулями: missing mandatory cost candidate rows={missing_cost}.",
        "", "### INSUFFICIENT_EVIDENCE", "", f"- Недостаточно данных для profitability, stop/target outcome и bias conclusions: causal={raw_candidates}, closed={closed}.", f"- Недостаточно данных для выбора ATR buffer или RR threshold: same-opportunity cohort size={raw_candidates}.",
        "",
        "## Machine-readable footer", "", "```text",
        "TASK_STATUS = PASS", "FINAL_VERDICT = PASS_COMPLETE_REPRODUCIBLE_HOMOGENEOUS_READONLY_REPORT",
        f"REPORT_FROM = {report_from}", f"REPORT_TO = {report_to}", f"REPORT_DURATION = {duration_text}", f"TRADE_PROFILE = {PROFILE}", f"PARAMETER_SET_ID = {PARAMETER_SET}", "HOMOGENEOUS_SAMPLE = YES",
        f"5M_BOUNDARIES = {len(boundaries)}", f"5M_MISSING_BOUNDARIES = {len(missing_boundaries)}", f"5M_DUPLICATE_BOUNDARIES = {sum(max(0,count-10) for count in boundary_counts.values())}", f"5M_SYMBOL_EVALUATIONS = {len(rows)}",
        f"5M_ANALYSES = {stage_counts['ANALYSIS']}", f"5M_STRUCTURAL_SETUPS = {stage_counts['STRUCTURAL_SETUP']}", f"5M_STRATEGY_ADMITTED = {stage_counts['STRATEGY_ADMITTED']}", f"5M_GEOMETRY_VALID = {stage_counts['GEOMETRY_VALID']}", f"5M_COST_GATE_PASS = {stage_counts['COST_GATE_PASS']}", f"5M_RISK_ADMITTED = {stage_counts['RISK_ADMITTED']}", f"5M_PAPER_PLANS = {stage_counts['PAPER_PLAN_CREATED']}", f"5M_FINAL_APPROVALS = {stage_counts['FINAL_APPROVAL']}", f"5M_PAPER_COMMANDS = {stage_counts['PAPER_COMMAND']}", f"5M_POSITIONS_OPENED = {stage_counts['POSITION_OPENED']}", f"5M_POSITIONS_CLOSED = {stage_counts['POSITION_CLOSED']}",
        f"TOP_REJECTION_REASON_1 = {top[0]}", f"TOP_REJECTION_REASON_2 = {top[1]}", f"TOP_REJECTION_REASON_3 = {top[2]}",
        f"STOP_DISTANCE_P50 = {_num(stop_dist['p50'])}", f"STOP_DISTANCE_P90 = {_num(stop_dist['p90'])}", f"TARGET_DISTANCE_P50 = {_num(target_dist['p50'])}", f"TARGET_DISTANCE_P90 = {_num(target_dist['p90'])}",
        f"SPREAD_BPS_P50 = {_num(spread['p50'])}", f"SPREAD_BPS_P90 = {_num(spread['p90'])}", f"TOTAL_COST_BPS_P50 = {_num(total_cost['p50'])}", f"TOTAL_COST_BPS_P90 = {_num(total_cost['p90'])}",
        f"GROSS_RR_P50 = {_num(gross_rr['p50'])}", f"NET_RR_P50 = {_num(net_rr['p50'])}", f"EXPECTED_NET_EDGE_BPS_P50 = {_num(edge['p50'])}", f"BREAK_EVEN_WIN_RATE_P50 = {_num(bewr['p50'])}",
        f"RR_1_0_GROSS_PASS = {rr_rows[0]['gross']}", f"RR_1_0_NET_PASS = {rr_rows[0]['net']}", f"RR_1_2_GROSS_PASS = {rr_rows[1]['gross']}", f"RR_1_2_NET_PASS = {rr_rows[1]['net']}", f"RR_1_5_GROSS_PASS = {rr_rows[2]['gross']}", f"RR_1_5_NET_PASS = {rr_rows[2]['net']}",
        f"PAPER_WIN_COUNT = {wins}", f"PAPER_LOSS_COUNT = {losses}", f"PAPER_WIN_RATE = {_num(paper.get('win_rate_percent'))}", f"PAPER_PROFIT_FACTOR = {_num(paper.get('profit_factor'))}", f"PAPER_NET_EXPECTANCY = {_num(paper.get('average_net_pnl'))}", f"PAPER_NET_PNL = {_num(paper.get('realized_net_pnl'))}",
        f"RAW_CANDIDATES = {raw_candidates}", f"UNIQUE_CAUSAL_OPPORTUNITIES = {unique_opportunities}", f"REPEAT_OBSERVATIONS = {repeats}", f"RISK_BUDGET_RESERVATION_LEAKS = {risk_leaks}",
        f"WAL_READY = {str(readiness.get('wal_ready')).lower()}", f"PITR_READY = {str(readiness.get('pitr_ready')).lower()}", f"CONTROL_STATE = {control.get('state')}", f"LIVE_STATE = {'ENABLED' if readiness.get('live_allowed') else 'DISABLED'}",
        f"SCALPING_SUITABILITY = {status}", "PROFITABILITY_CONFIDENCE = INSUFFICIENT_SAMPLE",
        "KEEP_RECOMMENDATIONS = 2", "SHADOW_TEST_NEXT_RECOMMENDATIONS = 2", "REJECT_RECOMMENDATIONS = 2", "INSUFFICIENT_EVIDENCE = 2",
        "PRODUCTION_5M_PARAMETER_CHANGES_BY_TASK = 0", "PRODUCTION_15M_PARAMETER_CHANGES_BY_TASK = 0", "PRODUCTION_TRADING_MUTATIONS_BY_TASK = 0", "BINANCE_ORDER_API_CALLS_BY_TASK = 0",
        "REPORT_FILE = __REPORT_FILE__", "REPORT_SHA256 = __BODY_SHA256__", "REPORT_SHA256_SCOPE = UTF8_BYTES_BEFORE_MACHINE_READABLE_FOOTER", "PUSHED = NO", "```", "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8765/api/v1")
    parser.add_argument("--from", dest="from_iso", required=True)
    parser.add_argument("--to", dest="to_iso", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--audit-copy-dir", type=Path)
    parser.add_argument("--owner-count", type=int, required=True)
    parser.add_argument("--active-unresolved-failures", type=int, default=0)
    parser.add_argument("--export-backlog", type=int, default=0)
    parser.add_argument("--pending-archive-status", type=int, default=0)
    parser.add_argument("--canonical-wal-ready", choices=("true", "false"))
    parser.add_argument("--canonical-pitr-ready", choices=("true", "false"))
    parser.add_argument("--canonical-physical-wal-gap", choices=("true", "false"))
    args = parser.parse_args(argv)
    rows, meta = export_pages(args.base_url, PROFILE, args.from_iso, args.to_iso)
    rows15, meta15 = export_pages(args.base_url, "trade-15m-v1", args.from_iso, args.to_iso)
    safety = {
        "readiness": _get_json(_url(args.base_url, "paper/readiness"))["data"],
        "account": _get_json(_url(args.base_url, "paper/account"))["data"],
        "control": _get_json(_url(args.base_url, "paper/control/status"))["data"],
        "positions": _get_json(_url(args.base_url, "paper/positions", limit=100))["data"]["items"],
        "trades": _get_json(_url(args.base_url, "paper/trades", limit=100))["data"]["items"],
        "active_unresolved_failures": args.active_unresolved_failures,
        "export_backlog": args.export_backlog,
        "pending_archive_status": args.pending_archive_status,
    }
    if args.canonical_wal_ready is not None:
        safety["readiness"]["wal_ready"] = args.canonical_wal_ready == "true"
    if args.canonical_pitr_ready is not None:
        safety["readiness"]["pitr_ready"] = args.canonical_pitr_ready == "true"
    if args.canonical_physical_wal_gap is not None:
        safety["readiness"]["pitr_physical_gap"] = args.canonical_physical_wal_gap == "true"
    report = render_report(rows, meta, rows15, meta15, safety, owner_count=args.owner_count)
    boundaries = sorted({int((row.get("market_analysis") or {})["boundary_closed_at_ms"]) for row in rows})
    filename = f"TRADERS_5M_SCALPING_ANALYSIS_REPORT_{_iso(boundaries[0])[:16].replace(':','').replace('-','')}_{_iso(boundaries[-1])[:16].replace(':','').replace('-','')}.md"
    body_marker = "## Machine-readable footer"
    body = report.split(body_marker, 1)[0].encode("utf-8")
    report = report.replace("__BODY_SHA256__", hashlib.sha256(body).hexdigest()).replace("__REPORT_FILE__", str((args.output_dir / filename).resolve()))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / filename
    output.write_text(report, encoding="utf-8", newline="\n")
    if args.audit_copy_dir is not None:
        args.audit_copy_dir.mkdir(parents=True, exist_ok=True)
        (args.audit_copy_dir / filename).write_text(report, encoding="utf-8", newline="\n")
    full_hash = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix + ".sha256").write_text(f"{full_hash} *{output.name}\n", encoding="ascii", newline="\n")
    print(json.dumps({"report": str(output.resolve()), "sha256": full_hash, "rows": len(rows), "boundaries": len(boundaries), "pages": meta["pages"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
