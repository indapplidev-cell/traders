"""Bounded, read-only 5m production calibration aggregation.

The input is the persisted pipeline projection, not future candles.  This
module deliberately has no database, exchange, command, or control dependency.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Iterable, Mapping

from app.engine_observation.scalping_expectancy import calculate_scalping_expectancy
from app.engine_paper.scalping_shadow import (
    CausalTarget,
    ShadowCostInputs,
    ShadowGeometryCandidate,
    ShadowGeometryConfig,
    evaluate_scalping_shadow,
)


RR_COHORTS = (1.0, 1.2, 1.5)
ATR_COHORTS = (0.25, 0.50, 0.75, 1.00)
STOP_ENVELOPES_BPS = (50.0, 65.0, 80.0)
MIN_TARGETS_BPS = (45.0, 60.0, 80.0)
QUOTA_FREE_REASONS = {
    "PAPER_NO_PLAN_SOURCE_NO_DECISION",
    "PAPER_NO_PLAN_MISSING_INVALIDATION_LEVEL",
    "PAPER_NO_PLAN_MISSING_TARGET_LEVEL",
    "PAPER_NO_PLAN_TARGET_NOT_ECONOMICALLY_ACTIONABLE",
    "PAPER_NO_PLAN_CAUSAL_STOP_TOO_WIDE_FOR_PROFILE",
    "PAPER_REJECT_NEGATIVE_NET_EDGE",
    "PAPER_REJECT_LOW_GROSS_RR",
    "PAPER_REJECT_LOW_NET_RR",
}


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def percentile(values: Iterable[object], quantile: float) -> float | None:
    ordered = sorted(value for item in values if (value := _number(item)) is not None)
    if not ordered:
        return None
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def distribution(values: Iterable[object]) -> dict[str, float | None]:
    materialized = list(values)
    return {
        "min": percentile(materialized, 0), "p10": percentile(materialized, .10),
        "p25": percentile(materialized, .25), "p50": percentile(materialized, .50),
        "p75": percentile(materialized, .75), "p90": percentile(materialized, .90),
        "p95": percentile(materialized, .95), "max": percentile(materialized, 1),
    }


def _diagnostic(row: Mapping[str, Any]) -> Mapping[str, Any]:
    paper = _mapping(row.get("paper"))
    return _mapping(_mapping(paper.get("paper_context")).get("scalping_geometry_diagnostics"))


def _reasons(row: Mapping[str, Any]) -> list[str]:
    raw: list[str] = []
    for value in (row.get("final_reason"), _diagnostic(row).get("raw_reason"),
                  _diagnostic(row).get("rejection_reason")):
        if value:
            raw.append(str(value))
    modules = _mapping(row.get("module_reasons"))
    for module in ("setup", "strategy", "risk", "paper"):
        values = modules.get(module)
        if isinstance(values, list):
            raw.extend(str(value) for value in values if value)
    return list(dict.fromkeys(raw))


def rejection_category(row: Mapping[str, Any]) -> str:
    reasons = _reasons(row)
    joined = " ".join(reasons)
    setup = _mapping(row.get("setup"))
    strategy = _mapping(row.get("strategy"))
    risk = _mapping(row.get("risk"))
    paper = _mapping(row.get("paper"))
    ordered = (
        ("MISSING_CAUSAL_INVALIDATION", "MISSING_INVALIDATION"),
        ("CAUSAL_STOP_TOO_WIDE", "STOP_TOO_WIDE"),
        ("MISSING_TARGET", "MISSING_TARGET"),
        ("TARGET_TOO_CLOSE", "TARGET_TOO_CLOSE"),
        ("TARGET_NOT_ECONOMICALLY_ACTIONABLE", "TARGET_NOT_ECONOMICALLY_ACTIONABLE"),
        ("NEGATIVE_NET_EDGE", "NEGATIVE_NET_EDGE"),
        ("LOW_GROSS_RR", "LOW_GROSS_RR"),
        ("LOW_NET_RR", "LOW_NET_RR"),
        ("QUOTA_RESEARCH_LIMIT", "BUDGET_EXCEEDED"),
        ("EXPOSURE_RESTRICTION", "EXPOSURE"),
        ("VALIDITY_EXPIRED", "EXPIRED"),
    )
    for category, token in ordered:
        if token in joined:
            return category
    if setup.get("setup_status") == "NO_SETUP" or "NO_STRUCTURAL_SETUP" in joined:
        return "NO_SETUP"
    if any("WAIT" in reason for reason in reasons):
        return "WAIT"
    if strategy.get("decision_status") in {"REJECTED", "REJECT"}:
        return "STRATEGY_REJECT"
    if risk.get("risk_status") in {"REJECTED", "REJECT"}:
        return "RISK_REJECT"
    if paper.get("paper_status") in {"REJECTED", "REJECT", "NO_PLAN"}:
        return "OTHER"
    return "NONE"


def export_record(row: Mapping[str, Any]) -> dict[str, Any]:
    analysis, setup = _mapping(row.get("analysis")), _mapping(row.get("setup"))
    strategy, risk, paper = (_mapping(row.get(name)) for name in ("strategy", "risk", "paper"))
    diagnostic = _diagnostic(row)
    context = _mapping(paper.get("paper_context"))
    primitives = _mapping(context.get("causal_primitives"))
    direction = paper.get("paper_direction") or risk.get("direction_hint") or strategy.get("direction_hint")
    if direction == "BULLISH":
        direction = "LONG"
    elif direction == "BEARISH":
        direction = "SHORT"
    else:
        direction = None
    boundary = int(row["boundary"])
    return {
        "timestamp": datetime.fromtimestamp(boundary / 1000, timezone.utc).isoformat(),
        "boundary": boundary, "symbol": row.get("symbol"), "profile": row.get("profile"),
        "parameter_set_id": row.get("parameter_set_id"), "regime": analysis.get("regime"),
        "direction": direction, "setup": setup.get("setup_type"),
        "setup_quality_score": setup.get("quality_score"),
        "setup_diagnostics": setup.get("diagnostics") or {},
        "scenario": setup.get("scenario") or setup.get("setup_type"),
        "strategy_result": strategy.get("decision_status"),
        "strategy_score": strategy.get("strategy_score"),
        "strategy_quality_threshold": strategy.get("strategy_quality_threshold"),
        "strategy_margin_to_threshold": strategy.get("strategy_margin_to_threshold"),
        "strategy_raw_score": strategy.get("strategy_raw_score"),
        "strategy_penalty_total": strategy.get("strategy_penalty_total"),
        "strategy_component_scores": strategy.get("component_scores") or {},
        "strategy_context": strategy.get("context") or {},
        "strategy_warnings": strategy.get("decision_warnings") or [],
        "strategy_rejection_reasons": strategy.get("rejection_reasons") or [],
        "strategy_shadow_quality_cohorts": strategy.get("shadow_quality_cohorts") or {},
        "entry": diagnostic.get("entry") or paper.get("hypothetical_entry_reference"),
        "atr": diagnostic.get("atr") or primitives.get("atr_value"),
        "causal_invalidation": diagnostic.get("causal_invalidation") or paper.get("hypothetical_invalidation_level"),
        "raw_stop": diagnostic.get("raw_stop"), "stop": diagnostic.get("final_stop") or paper.get("hypothetical_stop_level"),
        "stop_distance_bps": diagnostic.get("stop_distance_bps"), "stop_envelope_bps": diagnostic.get("stop_envelope_bps"),
        "target": diagnostic.get("causal_target") or paper.get("hypothetical_target_level"),
        "target_source": diagnostic.get("target_source_type") or paper.get("target_source"),
        "target_distance_bps": diagnostic.get("target_distance_bps"), "target_age_ms": diagnostic.get("target_age_ms"),
        "target_valid": diagnostic.get("target_available"), "entry_fee_bps": diagnostic.get("entry_fee_bps"),
        "causal_target_exists": diagnostic.get("causal_target_exists"),
        "economically_actionable_target_exists": diagnostic.get("economically_actionable_target_exists"),
        "minimum_actionable_target_bps": diagnostic.get("minimum_actionable_target_bps"),
        "target_considerations": diagnostic.get("target_considerations") or [],
        "opportunity_family_id": diagnostic.get("opportunity_id"),
        "exit_fee_bps": diagnostic.get("exit_fee_bps"), "spread_bps": diagnostic.get("spread_bps"),
        "entry_slippage_bps": diagnostic.get("entry_slippage_bps"), "exit_slippage_bps": diagnostic.get("exit_slippage_bps"),
        "depth_impact_bps": diagnostic.get("depth_impact_bps"), "safety_margin_bps": diagnostic.get("safety_margin_bps"),
        "total_cost_bps": diagnostic.get("total_cost_bps"), "gross_rr": diagnostic.get("gross_rr"),
        "net_rr": diagnostic.get("net_rr"), "expected_net_edge_bps": diagnostic.get("expected_net_edge_bps"),
        "break_even_win_rate": diagnostic.get("break_even_win_rate"), "risk_result": risk.get("risk_status"),
        "plan_status": paper.get("paper_status"), "final_decision": _mapping(paper.get("final_approval_generation")).get("outcome"),
        "reason_category": rejection_category(row), "raw_reasons": _reasons(row),
        "paper_command_id": row.get("paper_command_id"), "paper_position_id": row.get("paper_position_id"),
        "paper_outcome": row.get("paper_outcome"), "holding_time_seconds": row.get("holding_time_seconds"),
        "mfe_bps": row.get("mfe_bps"), "mae_bps": row.get("mae_bps"),
        "gross_pnl": row.get("gross_pnl"), "net_pnl": row.get("net_pnl"),
    }


def _stage_flags(row: Mapping[str, Any]) -> dict[str, bool]:
    setup = _mapping(row.get("setup"))
    strategy = _mapping(row.get("strategy"))
    risk = _mapping(row.get("risk"))
    paper = _mapping(row.get("paper"))
    diagnostic = _diagnostic(row)
    structural = setup.get("setup_status") not in {None, "NO_SETUP", "ERROR", "SKIPPED"}
    strategy_pass = strategy.get("decision_status") in {
        "APPROVED", "PRE_APPROVED", "STRATEGY_APPROVED", "DECISION",
        "ALLOW_RESEARCH_TRADE_PLAN",
    }
    risk_pre_pass = risk.get("risk_status") in {"RISK_APPROVED", "RISK_PRE_APPROVED_RESEARCH", "APPROVED"}
    geometry = diagnostic.get("rejection_stage") not in {None, "CAUSAL_INVALIDATION", "ATR_BUFFER", "STOP_ENVELOPE", "CAUSAL_TARGET"} if diagnostic else False
    cost = bool(diagnostic.get("economic_gate_pass"))
    actionable_target = bool(diagnostic.get("economically_actionable_target_exists"))
    plan = paper.get("paper_status") == "PAPER_PLAN_READY"
    final = _mapping(paper.get("final_approval_generation")).get("outcome") in {"CREATED", "APPROVED", "ELIGIBLE"}
    return {"analysis": True, "structural_setup": structural, "strategy_admitted": strategy_pass,
            "geometry_valid": geometry, "actionable_target": actionable_target,
            "net_cost_viable": cost, "risk_admitted": risk_pre_pass and actionable_target and cost,
            "paper_plan": plan, "final_approval": final, "paper_command": bool(row.get("paper_command_id")),
            "position": bool(row.get("paper_position_id")), "exit": row.get("paper_outcome") == "CLOSED"}


def aggregate(
    rows: Iterable[Mapping[str, Any]],
    *,
    expected_symbols: int = 10,
    boundary_interval_ms: int = 300_000,
    include_calibration_cohorts: bool = True,
) -> dict[str, Any]:
    source = sorted((dict(row) for row in rows), key=lambda row: (int(row["boundary"]), str(row.get("symbol"))))
    if not source:
        raise ValueError("calibration sample is empty")
    boundaries = sorted({int(row["boundary"]) for row in source})
    parameter_sets = {row.get("parameter_set_id") for row in source}
    if len(parameter_sets) != 1 or None in parameter_sets:
        raise ValueError("sample mixes or omits runtime parameter identity")
    stages = Counter()
    reason_histogram: dict[str, dict[str, Any]] = {}
    exported = [export_record(row) for row in source]
    episode_state: dict[tuple[str, str], tuple[int, str, int, str]] = {}
    for record in exported:
        if not record["direction"]:
            record["opportunity_id"] = None
            continue
        key = (str(record["symbol"]), str(record["direction"]))
        family = str(record.get("opportunity_family_id") or sha256(
            f"{record['profile']}|{record['symbol']}|{record['direction']}|{record['setup']}".encode()
        ).hexdigest()[:24])
        prior = episode_state.get(key)
        if prior and record["boundary"] - prior[0] == boundary_interval_ms and prior[1] == family:
            first_seen = prior[2]
            opportunity_id = prior[3]
        else:
            first_seen = int(record["boundary"])
            opportunity_id = "opportunity-episode:" + sha256(
                f"{family}|{first_seen}".encode()
            ).hexdigest()[:24]
        record["opportunity_family_id"] = family
        record["opportunity_id"] = opportunity_id
        episode_state[key] = (int(record["boundary"]), family, first_seen, opportunity_id)
    for row, record in zip(source, exported):
        stages.update(name for name, passed in _stage_flags(row).items() if passed)
        category = record["reason_category"]
        if category != "NONE":
            bucket = reason_histogram.setdefault(category, {"count": 0, "symbols": Counter(), "hours_utc": Counter(), "raw_reasons": Counter()})
            bucket["count"] += 1; bucket["symbols"][record["symbol"]] += 1
            bucket["hours_utc"][record["timestamp"][11:13]] += 1
            bucket["raw_reasons"].update(record["raw_reasons"])
    for bucket in reason_histogram.values():
        bucket["share"] = bucket["count"] / len(source)
        for key in ("symbols", "hours_utc", "raw_reasons"):
            bucket[key] = dict(bucket[key])
    sequence = ("analysis", "structural_setup", "strategy_admitted", "geometry_valid", "actionable_target", "net_cost_viable",
                "risk_admitted", "paper_plan", "final_approval", "paper_command", "position", "exit")
    funnel = {}
    previous = len(source)
    for stage in sequence:
        count = stages[stage]
        funnel[stage] = {"count": count, "pct_previous": count / previous if previous else None,
                         "pct_analyses": count / len(source)}
        previous = count
    directions: dict[str, dict[str, Any]] = {}
    for direction in ("LONG", "SHORT"):
        selected = [record for record in exported if record["direction"] == direction]
        directions[direction] = {"sample_size": len(selected), "symbols": dict(Counter(r["symbol"] for r in selected)),
                                 "stop_distance": distribution(r["stop_distance_bps"] for r in selected),
                                 "target_distance": distribution(r["target_distance_bps"] for r in selected)}
    diagnostic_rows = [record for record in exported if record["stop_distance_bps"] is not None]
    rr = {}
    for threshold in RR_COHORTS:
        rr[str(threshold)] = {
            "gross_pass": sum((_number(r["gross_rr"]) or -1) >= threshold for r in diagnostic_rows),
            "net_cost_pass": sum(r["total_cost_bps"] is not None for r in diagnostic_rows),
            "net_rr_pass": sum((_number(r["net_rr"]) or -1) >= threshold for r in diagnostic_rows),
            "plan_eligible": sum((_number(r["net_rr"]) or -1) >= threshold and r["expected_net_edge_bps"] is not None and (_number(r["expected_net_edge_bps"]) or 0) > 0 for r in diagnostic_rows),
        }
    signatures: dict[tuple[str, str], tuple[int, str]] = {}
    unique, repeats = set(), 0
    for record in exported:
        if not record["direction"]:
            continue
        raw = "|".join(str(record.get(key)) for key in ("symbol", "direction", "setup", "causal_invalidation", "target", "target_source"))
        signature = sha256(raw.encode()).hexdigest()[:20]
        key = (str(record["symbol"]), str(record["direction"]))
        prior = signatures.get(key)
        if prior and record["boundary"] - prior[0] == boundary_interval_ms and prior[1] == signature:
            repeats += 1
        else:
            unique.add((key, signature, record["boundary"]))
        signatures[key] = (record["boundary"], signature)

    def unique_opportunities(records: list[dict[str, Any]]) -> int:
        # Cohorts must reuse the already assigned contiguous episode identity.
        # Stop/target evolution is diagnostic state, not a new opportunity.
        return len({
            str(record["opportunity_id"])
            for record in records
            if record.get("opportunity_id")
        })

    weak = [record for record in exported if "STRATEGY_REJECT_WEAK_QUALITY" in record["strategy_rejection_reasons"]]
    conflicts = [record for record in exported if "STRATEGY_REJECT_CONFLICTING_CONTEXT" in record["strategy_rejection_reasons"]]
    margins = [_number(record["strategy_margin_to_threshold"]) for record in weak]
    strategy_margin_bins = {
        "[-0.10,0)": sum(value is not None and -.10 <= value < 0 for value in margins),
        "[-0.25,-0.10)": sum(value is not None and -.25 <= value < -.10 for value in margins),
        "[-0.50,-0.25)": sum(value is not None and -.50 <= value < -.25 for value in margins),
        "[-1.00,-0.50)": sum(value is not None and -1.00 <= value < -.50 for value in margins),
        "<-1.00": sum(value is not None and value < -1.00 for value in margins),
    }
    strategy_cohorts: dict[str, dict[str, Any]] = {}
    for threshold in (65.0, 64.9, 64.75, 64.5, 64.0):
        admitted = [
            record for record in exported
            if record["strategy_result"] == "ALLOW_RESEARCH_TRADE_PLAN"
            or (
                "STRATEGY_REJECT_WEAK_QUALITY" in record["strategy_rejection_reasons"]
                and (_number(record["strategy_score"]) or -1) >= threshold
            )
        ]
        replayed: list[object] = []
        for record in admitted:
            context = _mapping(record["strategy_context"])
            entry = _number(context.get("confirmation_close") or context.get("reference_close"))
            invalidation = _number(context.get("causal_invalidation_level"))
            atr = _number(context.get("atr_value"))
            target_price = _number(context.get("causal_target_level"))
            if entry is None or record["direction"] not in {"LONG", "SHORT"}:
                continue
            target_values = () if target_price is None else (
                CausalTarget(target_price, "LOCAL_5M", int(record["boundary"])),
            )
            replayed.append(evaluate_scalping_shadow(
                ShadowGeometryCandidate(
                    trade_profile_id="trade-5m-v1", symbol=str(record["symbol"]),
                    boundary_ms=int(record["boundary"]),
                    direction="BULLISH" if record["direction"] == "LONG" else "BEARISH",
                    entry=entry, causal_invalidation=invalidation, atr=atr,
                    targets=target_values, setup_identity=str(record["setup"]),
                ),
                ShadowCostInputs(),
                ShadowGeometryConfig(.25, 80.0, 45.0),
            ))
        observed_downstream = [record for record in admitted if record["stop_distance_bps"] is not None]
        strategy_cohorts[str(threshold)] = {
            "setup_count": stages["structural_setup"],
            "strategy_admits": len(admitted),
            "unique_opportunities": unique_opportunities(admitted),
            "causal_stops": sum(getattr(item, "final_stop") is not None for item in replayed),
            "target_candidates": sum(getattr(item, "target_candidates_considered") for item in replayed),
            "geometry_valid": sum(
                getattr(item, "stop_envelope_pass") is True and getattr(item, "target_available")
                for item in replayed
            ),
            "actionable_targets": sum(getattr(item, "economically_actionable_target_exists") for item in replayed),
            "net_cost_pass": sum(
                record["expected_net_edge_bps"] is not None
                and (_number(record["expected_net_edge_bps"]) or 0) > 0
                for record in observed_downstream
            ),
            "risk_pass": sum(record["risk_result"] in {"RISK_APPROVED", "RISK_PRE_APPROVED_RESEARCH"} for record in observed_downstream),
            "paper_eligible": sum(record["plan_status"] == "PAPER_PLAN_READY" for record in observed_downstream),
            "downstream_missing_for_shadow_admits": len(admitted) - len(replayed),
            "authoritative_cost_inputs_missing": sum(
                getattr(item, "rejection_stage") == "NET_COST_GATE" for item in replayed
            ),
        }

    no_setup = [record for record in exported if record["reason_category"] == "NO_SETUP"]
    near_miss = Counter()
    for record in no_setup:
        diagnostic = _mapping(record["setup_diagnostics"])
        missing = 0
        for field, reason in (
            ("has_structural_trigger", "MISSING_STRUCTURAL_TRIGGER"),
            ("has_directional_context", "MISSING_DIRECTIONAL_CONTEXT"),
            ("has_level_context", "MISSING_LIQUIDITY_OR_LEVEL_CONTEXT"),
        ):
            if not diagnostic.get(field):
                missing += 1
                near_miss[reason] += 1
        near_miss[f"DISTANCE_{missing}"] += 1
    opportunity_timelines: dict[str, dict[str, Any]] = {}
    for record in exported:
        opportunity_id = record.get("opportunity_id")
        if not opportunity_id:
            continue
        timeline = opportunity_timelines.setdefault(str(opportunity_id), {
            "symbol": record["symbol"], "direction": record["direction"],
            "setup": record["setup"], "first_seen": record["boundary"],
            "last_seen": record["boundary"], "boundaries_seen": 0,
            "strategy_scores_over_time": [], "target_candidates_over_time": [],
            "stop_evolution": [],
        })
        timeline["last_seen"] = record["boundary"]
        timeline["boundaries_seen"] += 1
        timeline["strategy_scores_over_time"].append({
            "boundary": record["boundary"], "score": record["strategy_score"],
            "margin": record["strategy_margin_to_threshold"],
        })
        timeline["target_candidates_over_time"].append({
            "boundary": record["boundary"], "targets": record["target_considerations"],
        })
        timeline["stop_evolution"].append({
            "boundary": record["boundary"], "stop": record["stop"],
            "stop_distance_bps": record["stop_distance_bps"],
        })
    quota_leaks = sum(bool(row.get("risk_budget_reserved")) and any(reason in QUOTA_FREE_REASONS for reason in _reasons(row)) for row in source)
    per_symbol = {}
    for symbol in sorted({str(row["symbol"]) for row in source}):
        values = [record for record in exported if record["symbol"] == symbol]
        source_values = [row for row in source if row["symbol"] == symbol]
        flags = Counter(name for row in source_values for name, passed in _stage_flags(row).items() if passed)
        per_symbol[symbol] = {"analyses": len(values), "setups": flags["structural_setup"],
                              "strategy_admits": flags["strategy_admitted"], "geometry_valid": flags["geometry_valid"],
                              "cost_pass": flags["net_cost_viable"], "risk_pass": flags["risk_admitted"],
                              "plans": flags["paper_plan"], "approvals": flags["final_approval"],
                              "positions": flags["position"], "closed_positions": flags["exit"],
                              "long": sum(r["direction"] == "LONG" for r in values),
                              "short": sum(r["direction"] == "SHORT" for r in values),
                              "dominant_rejection": Counter(r["reason_category"] for r in values).most_common(1)[0][0],
                              "stop_distance": distribution(r["stop_distance_bps"] for r in values),
                              "target_distance": distribution(r["target_distance_bps"] for r in values),
                              "gross_rr": distribution(r["gross_rr"] for r in values), "net_rr": distribution(r["net_rr"] for r in values)}
    def cohort_matrix() -> dict[str, Any]:
        candidates: list[tuple[dict[str, Any], Mapping[str, Any]]] = []
        for row, record in zip(source, exported):
            diagnostic = _diagnostic(row)
            if record["direction"] not in {"LONG", "SHORT"} or record["entry"] is None:
                continue
            if diagnostic.get("causal_invalidation") is None:
                continue
            candidates.append((record, diagnostic))

        def evaluate(record: Mapping[str, Any], diagnostic: Mapping[str, Any], atr: float, envelope: float, target_min: float):
            target = () if record["target"] is None else (CausalTarget(
                float(record["target"]), str(record["target_source"] or "LOCAL_5M"), int(record["boundary"])
            ),)
            candidate = ShadowGeometryCandidate(
                trade_profile_id="trade-5m-v1", symbol=str(record["symbol"]), boundary_ms=int(record["boundary"]),
                direction="BULLISH" if record["direction"] == "LONG" else "BEARISH", entry=float(record["entry"]),
                causal_invalidation=_number(diagnostic.get("causal_invalidation")), atr=_number(diagnostic.get("atr")), targets=target,
            )
            costs = ShadowCostInputs(
                entry_fee_bps=_number(diagnostic.get("entry_fee_bps")) or 0,
                exit_fee_bps=_number(diagnostic.get("exit_fee_bps")) or 0,
                entry_slippage_bps=_number(diagnostic.get("entry_slippage_bps")) or 0,
                exit_slippage_bps=_number(diagnostic.get("exit_slippage_bps")) or 0,
                safety_margin_bps=_number(diagnostic.get("safety_margin_bps")) or 0,
                spread_bps=_number(diagnostic.get("spread_bps")), depth_impact_bps=_number(diagnostic.get("depth_impact_bps")),
                spread_authoritative=diagnostic.get("spread_bps") is not None,
                depth_authoritative=diagnostic.get("depth_impact_bps") is not None,
            )
            return evaluate_scalping_shadow(candidate, costs, ShadowGeometryConfig(
                atr_buffer_multiplier=atr, stop_envelope_bps=envelope,
                minimum_target_diagnostic_bps=target_min, production_rr_floor=1.5,
            ))

        result: dict[str, Any] = {"same_source_candidate_count": len(candidates)}
        result["atr_buffer"] = {}
        for atr in ATR_COHORTS:
            outcomes = [evaluate(record, diagnostic, atr, 80, 45) for record, diagnostic in candidates]
            result["atr_buffer"][str(atr)] = {"geometry_pass": sum(item.stop_envelope_pass is True for item in outcomes),
                                                "cost_pass": sum(item.economic_gate_pass for item in outcomes),
                                                "plan_eligible": sum(item.valid_plan for item in outcomes)}
        result["stop_envelope"] = {}
        for envelope in STOP_ENVELOPES_BPS:
            outcomes = [evaluate(record, diagnostic, .25, envelope, 45) for record, diagnostic in candidates]
            result["stop_envelope"][str(envelope)] = {"geometry_pass": sum(item.stop_envelope_pass is True for item in outcomes),
                                                       "plan_eligible": sum(item.valid_plan for item in outcomes)}
        result["minimum_target"] = {}
        for target_min in MIN_TARGETS_BPS:
            outcomes = [evaluate(record, diagnostic, .25, 80, target_min) for record, diagnostic in candidates]
            result["minimum_target"][str(target_min)] = {
                "diagnostic_pass": sum(item.minimum_target_diagnostic_pass is True for item in outcomes),
                "plan_eligible": sum(item.valid_plan for item in outcomes),
            }
        return result

    def grouped(keys: tuple[str, ...]) -> dict[str, Any]:
        buckets: dict[str, list[tuple[dict[str, Any], dict[str, bool]]]] = defaultdict(list)
        by_identity = {(int(row["boundary"]), str(row["symbol"])): row for row in source}
        for record in exported:
            row = by_identity[(record["boundary"], str(record["symbol"]))]
            parts = []
            for key in keys:
                if key == "hour_utc": parts.append(record["timestamp"][11:13])
                else: parts.append(str(record.get(key) or "UNKNOWN"))
            buckets["|".join(parts)].append((record, _stage_flags(row)))
        return {name: {"analyses": len(values), "setup_rate": sum(v[1]["structural_setup"] for v in values) / len(values),
                       "geometry_pass_rate": sum(v[1]["geometry_valid"] for v in values) / len(values),
                       "cost_pass_rate": sum(v[1]["net_cost_viable"] for v in values) / len(values),
                       "approval_rate": sum(v[1]["final_approval"] for v in values) / len(values)}
                for name, values in sorted(buckets.items())}

    cohorts = cohort_matrix() if include_calibration_cohorts else {
        "atr_buffer": {}, "stop_envelope": {}, "minimum_target": {},
        "same_source_candidate_count": 0,
    }
    closed = [
        row for row in exported
        if row["paper_outcome"] == "CLOSED" and row["net_pnl"] is not None
    ]
    duration_days = (
        boundaries[-1] - boundaries[0] + boundary_interval_ms
    ) / 86_400_000
    expectancy = calculate_scalping_expectancy(
        (float(row["net_pnl"]) for row in closed), observation_days=duration_days
    )
    net_values = [float(row["net_pnl"]) for row in closed]
    positive_pnl = sum(value for value in net_values if value > 0)
    negative_pnl = -sum(value for value in net_values if value < 0)
    equity_curve = peak = max_drawdown = 0.0
    consecutive = max_consecutive_losses = 0
    for value in net_values:
        equity_curve += value
        peak = max(peak, equity_curve)
        max_drawdown = max(max_drawdown, peak - equity_curve)
        consecutive = consecutive + 1 if value < 0 else 0
        max_consecutive_losses = max(max_consecutive_losses, consecutive)
    gross_outcomes = [
        float(row["gross_pnl"]) for row in closed if row["gross_pnl"] is not None
    ]
    known_cost = (
        sum(gross_outcomes) - sum(net_values)
        if len(gross_outcomes) == len(closed) else None
    )
    business_kpis = {
        "trades_per_day": expectancy.observed_trades_per_day,
        "unique_opportunities_per_day": len(opportunity_timelines) / duration_days,
        "net_expectancy_per_trade": expectancy.net_expectancy_per_trade,
        "net_expectancy_per_day": expectancy.net_expectancy_per_day,
        "net_pnl_per_day": sum(net_values) / duration_days if closed else None,
        "win_rate": expectancy.win_probability,
        "profit_factor": positive_pnl / negative_pnl if negative_pnl > 0 else None,
        "average_win": expectancy.average_net_win,
        "average_loss": expectancy.average_net_loss,
        "holding_time_seconds": distribution(row["holding_time_seconds"] for row in closed),
        "mfe_bps": distribution(row["mfe_bps"] for row in closed),
        "mae_bps": distribution(row["mae_bps"] for row in closed),
        "cost_to_gross_profit": (
            known_cost / sum(gross_outcomes)
            if known_cost is not None and sum(gross_outcomes) > 0 else None
        ),
        "max_drawdown": max_drawdown if closed else None,
        "max_consecutive_losses": max_consecutive_losses if closed else None,
        "business_frequency_envelope": {
            "minimum_desirable": 10, "working": [15, 20], "upper": 30,
        },
        "forced_quota": False,
    }
    return {
        "observation_start_ms": boundaries[0], "observation_end_ms": boundaries[-1],
        "duration_seconds": (boundaries[-1] - boundaries[0] + boundary_interval_ms) // 1000,
        "parameter_set_id": next(iter(parameter_sets)), "boundaries_observed": len(boundaries),
        "expected_symbol_evaluations": len(boundaries) * expected_symbols, "actual_symbol_evaluations": len(source),
        "sample_completeness": len(source) / (len(boundaries) * expected_symbols),
        "funnel": funnel, "rejection_histogram": reason_histogram, "per_symbol": per_symbol,
        "strategy_quality": {
            "weak_count": len(weak),
            "conflicting_context_count": len(conflicts),
            "weak_score_distribution": distribution(record["strategy_score"] for record in weak),
            "weak_margin_distribution": distribution(record["strategy_margin_to_threshold"] for record in weak),
            "margin_bins": strategy_margin_bins,
            "conflict_components": dict(Counter(
                warning for record in conflicts for warning in record["strategy_warnings"]
            )),
        },
        "strategy_shadow_cohorts": strategy_cohorts,
        "setup_near_miss": {"no_setup_count": len(no_setup), "histogram": dict(near_miss)},
        "opportunity_timelines": opportunity_timelines,
        "directions": directions, "stop_distance": distribution(r["stop_distance_bps"] for r in exported),
        "target_distance": distribution(r["target_distance_bps"] for r in exported),
        "spread_bps": distribution(r["spread_bps"] for r in exported),
        "total_cost_bps": distribution(r["total_cost_bps"] for r in exported),
        "gross_rr": distribution(r["gross_rr"] for r in exported), "net_rr": distribution(r["net_rr"] for r in exported),
        "expected_net_edge_bps": distribution(r["expected_net_edge_bps"] for r in exported),
        "break_even_win_rate": distribution(r["break_even_win_rate"] for r in exported),
        "rr_cohorts": rr, "atr_buffer_cohorts": cohorts["atr_buffer"],
        "stop_envelope_cohorts": cohorts["stop_envelope"],
        "minimum_target_cohorts": cohorts["minimum_target"],
        "same_source_cohort_candidates": cohorts["same_source_candidate_count"],
        "temporal_hour_utc": grouped(("hour_utc",)), "regime": grouped(("regime",)),
        "setup_scenario": grouped(("setup", "scenario")),
        "raw_candidates": sum(bool(r["direction"]) for r in exported),
        "unique_causal_opportunities": len(opportunity_timelines),
        "repeat_observations": sum(bool(r["direction"]) for r in exported) - len(opportunity_timelines),
        "risk_budget_reservation_leaks": quota_leaks,
        "business_kpis": business_kpis,
        "cycle_latency_ms": distribution(row.get("duration_ms") for row in source), "export_rows": exported,
    }
