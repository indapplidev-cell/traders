"""Pure persisted-input Strategy forensics and side-effect-free 5m replay."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from typing import Any, Iterable, Mapping

from app.engine_observation.scalping_calibration import distribution
from app.engine_paper.scalping_shadow import (
    CausalTarget,
    ShadowCostInputs,
    ShadowGeometryCandidate,
    ShadowGeometryConfig,
    evaluate_scalping_shadow,
)


STRATEGY_THRESHOLD = 65.0
WEAK_CAP = 64.999
ALLOW_STATUS = "ALLOW_RESEARCH_TRADE_PLAN"


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _reason(row: Mapping[str, Any]) -> str | None:
    values = _mapping(row.get("strategy")).get("rejection_reasons") or []
    return str(values[0]) if values else None


def reconstruct_strategy_trace(row: Mapping[str, Any]) -> dict[str, Any]:
    """Reconstruct legacy persisted rows using only values known at boundary."""
    setup = _mapping(row.get("setup"))
    strategy = _mapping(row.get("strategy"))
    context = _mapping(strategy.get("context"))
    quality = _mapping(setup.get("quality_diagnostics"))
    components = _mapping(strategy.get("component_scores")) or _mapping(
        context.get("setup_component_scores")
    )
    raw = _number(strategy.get("strategy_raw_score"))
    if raw is None:
        positive = [
            _number(components.get(name))
            for name in ("structure", "candle_confirmation", "context_alignment")
        ]
        raw = round(sum(value for value in positive if value is not None), 3)
    penalty_values = {
        "CONFLICT": _number(quality.get("conflict_penalty"))
        or _number(components.get("conflict_penalty")) or 0.0,
        "INVALIDATION": _number(quality.get("invalidation_penalty"))
        or _number(components.get("invalidation_penalty")) or 0.0,
    }
    penalty_total = round(sum(penalty_values.values()), 3)
    setup_pre_cap = round(max(0.0, min(100.0, raw - penalty_total)), 3)
    confidence = _number(context.get("analysis_confidence"))
    confidence_adjustment = (
        0.0 if confidence is None
        else round((max(0.0, min(1.0, confidence)) - .5) * 4.0, 3)
    )
    setup_score = _number(setup.get("quality_score"))
    immediate_pre_cap = (
        None if setup_score is None else round(setup_score + confidence_adjustment, 3)
    )
    final = _number(strategy.get("strategy_final_score"))
    if final is None:
        final = _number(strategy.get("strategy_score"))
    quality_reasons = list(setup.get("quality_reasons") or quality.get("quality_reasons") or [])
    caps: list[dict[str, Any]] = []
    if quality.get("capped_by_analysis_entry_quality") or (
        "QUALITY_CAPPED_BY_ANALYSIS_ENTRY_QUALITY" in quality_reasons
    ):
        caps.append({
            "cap_type": "ANALYSIS_ENTRY_QUALITY_TIER_CAP",
            "cap_reason": "QUALITY_CAPPED_BY_ANALYSIS_ENTRY_QUALITY",
            "source_analysis_entry_quality": setup.get("source_entry_quality")
            or quality.get("source_analysis_entry_quality"),
            "input_score": setup_pre_cap,
            "cap_value": WEAK_CAP,
            "output_score": setup_score,
        })
    if immediate_pre_cap is not None and final is not None and immediate_pre_cap != final:
        caps.append({
            "cap_type": "SETUP_QUALITY_TIER_CLAMP",
            "cap_reason": "SETUP_QUALITY_WEAK_UPPER_BOUND",
            "input_score": immediate_pre_cap,
            "cap_value": WEAK_CAP,
            "output_score": final,
        })
    terminal_reason = _reason(row)
    terminal_gate = {
        "STRATEGY_REJECT_WEAK_QUALITY": "WEAK_QUALITY_GATE",
        "STRATEGY_REJECT_CONFLICTING_CONTEXT": "CONFLICT_CONTEXT_GATE",
        "STRATEGY_REJECT_HARD_INVALIDATION": "HARD_INVALIDATION_GATE",
        "STRATEGY_REJECT_NEUTRAL_DIRECTION": "DIRECTION_GATE",
        "STRATEGY_REJECT_UNSUPPORTED_SETUP_TYPE": "SETUP_TYPE_GATE",
    }.get(terminal_reason, "ADMISSION" if strategy.get("decision_status") == ALLOW_STATUS else "OTHER_GATE")
    return {
        "strategy_raw_score": raw,
        "strategy_structure_score": _number(components.get("structure")),
        "strategy_context_score": _number(components.get("context_alignment")),
        "strategy_candle_score": _number(components.get("candle_confirmation")),
        "strategy_other_component_scores": {},
        "strategy_penalty_total": penalty_total,
        "strategy_penalties": [
            {"penalty_type": name, "value": value, "applied": value > 0}
            for name, value in penalty_values.items()
        ],
        "strategy_setup_pre_cap_score": setup_pre_cap,
        "strategy_pre_cap_score": immediate_pre_cap,
        "strategy_cap_applied": bool(caps),
        "strategy_cap_type": caps[0]["cap_type"] if caps else None,
        "strategy_cap_reason": caps[0]["cap_reason"] if caps else None,
        "strategy_cap_value": caps[0]["cap_value"] if caps else None,
        "strategy_post_cap_score": final,
        "strategy_caps": caps,
        "strategy_gate_results": [{
            "gate": terminal_gate,
            "outcome": "FAIL" if terminal_reason else "PASS",
            "terminal": True,
            "reason": terminal_reason,
        }],
        "strategy_failed_gate": terminal_gate if terminal_reason else None,
        "strategy_failed_gate_reason": terminal_reason,
        "strategy_final_score": final,
        "strategy_threshold": STRATEGY_THRESHOLD,
        "strategy_margin_to_threshold": (
            None if final is None else round(final - STRATEGY_THRESHOLD, 3)
        ),
        "strategy_decision": strategy.get("decision_status"),
        "strategy_reason_code": terminal_reason,
    }


def _no_cap_pass(trace: Mapping[str, Any]) -> bool:
    return bool(
        trace.get("strategy_setup_pre_cap_score") is not None
        and float(trace["strategy_setup_pre_cap_score"]) >= STRATEGY_THRESHOLD
        and trace.get("strategy_failed_gate_reason")
        in {None, "STRATEGY_REJECT_WEAK_QUALITY"}
    )


def _targets(context: Mapping[str, Any], boundary: int) -> tuple[CausalTarget, ...]:
    values = context.get("causal_target_candidates")
    rows = list(values) if isinstance(values, list) else []
    if not rows and context.get("causal_target_level") is not None:
        rows = [{
            "price": context.get("causal_target_level"),
            "source_type": "LOCAL_5M", "timeframe": "5m",
            "known_at_ms": boundary, "validated": True,
            "still_relevant": True, "future_safe": True,
            "source_detail": "legacy_nearest_opposite_level",
        }]
    output: list[CausalTarget] = []
    seen: set[tuple[str, float, str]] = set()
    for raw in rows:
        if not isinstance(raw, Mapping):
            continue
        price = _number(raw.get("price"))
        source_type = str(raw.get("source_type") or "").upper()
        timeframe = str(raw.get("timeframe") or "").lower() or None
        if price is None or source_type not in {"LOCAL_5M", "STRUCTURAL", "15M", "1H"}:
            continue
        identity = (source_type, price, timeframe or "")
        if identity in seen:
            continue
        seen.add(identity)
        known_at = int(raw.get("known_at_ms") or boundary)
        if raw.get("future_safe") is False:
            known_at = max(known_at, boundary + 1)
        achievable = bool(raw.get("achievable", True))
        if source_type == "1H":
            reachability = _number(raw.get("reachability_atr"))
            entry = _number(context.get("confirmation_close") or context.get("reference_close"))
            achievable = bool(
                achievable and reachability is not None and reachability > 0
                and entry is not None and abs(price - entry) <= reachability
            )
        output.append(CausalTarget(
            price, source_type, known_at,
            validated=bool(raw.get("validated", True)),
            relevant=bool(raw.get("still_relevant", True)),
            achievable=achievable, timeframe=timeframe,
            source_detail=str(raw.get("source_detail")) if raw.get("source_detail") else None,
        ))
    return tuple(output)


def _geometry(row: Mapping[str, Any], costs: ShadowCostInputs | None = None):
    strategy = _mapping(row.get("strategy"))
    context = _mapping(strategy.get("context"))
    entry = _number(context.get("confirmation_close") or context.get("reference_close"))
    if entry is None:
        return None
    direction = str(context.get("direction_hint") or strategy.get("direction_hint") or "")
    invalidation = _number(context.get("causal_invalidation_level"))
    atr = _number(context.get("atr_value"))
    candidate = ShadowGeometryCandidate(
        trade_profile_id="trade-5m-v2", symbol=str(row.get("symbol")),
        boundary_ms=int(row["boundary"]), direction=direction, entry=entry,
        causal_invalidation=invalidation, atr=atr,
        targets=_targets(context, int(row["boundary"])),
        setup_identity=str(context.get("setup_type") or _mapping(row.get("setup")).get("setup_type")),
    )
    return evaluate_scalping_shadow(
        candidate,
        costs or ShadowCostInputs(safety_margin_bps=3.0),
        ShadowGeometryConfig(.25, 80.0, 45.0, production_rr_floor=1.5),
    )


def replay_strategy_rejects(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    source = [dict(row) for row in rows]
    parameter_sets = {row.get("parameter_set_id") for row in source}
    if len(parameter_sets) != 1 or None in parameter_sets:
        raise ValueError("forensic cohort must have one parameter_set_id")
    setups = [row for row in source if _mapping(row.get("setup")).get("setup_status") == "SETUP_CANDIDATE"]
    allowed = [row for row in setups if _mapping(row.get("strategy")).get("decision_status") == ALLOW_STATUS]
    rejects = [row for row in setups if _mapping(row.get("strategy")).get("decision_status") == "REJECT"]
    records: list[dict[str, Any]] = []
    classes = Counter()
    for row in rejects:
        trace = reconstruct_strategy_trace(row)
        no_cap = _no_cap_pass(trace)
        reason = trace["strategy_reason_code"]
        if reason == "STRATEGY_REJECT_CONFLICTING_CONTEXT":
            category = "BOOLEAN_GATE_REJECT"
        elif no_cap:
            category = "CAP_BOUND_REJECT"
        elif float(trace["strategy_raw_score"]) < STRATEGY_THRESHOLD:
            category = "TRUE_LOW_RAW_SCORE_REJECT"
        elif float(trace["strategy_setup_pre_cap_score"]) < STRATEGY_THRESHOLD:
            category = "PENALTY_DRIVEN_REJECT"
        else:
            category = "OTHER_REJECT"
        classes[category] += 1
        diagnostic = _geometry(row) if no_cap else None
        geometry_pass = bool(
            diagnostic is not None and diagnostic.stop_envelope_pass is True
        )
        target_pass = bool(diagnostic is not None and diagnostic.causal_target_exists)
        cost_pass = bool(diagnostic is not None and diagnostic.economic_gate_pass)
        # Cost data was not requested/persisted for Strategy rejects. Reusing a
        # later live quote would leak future state, so every missing spread stays
        # fail-closed and downstream account/PAPER gates remain NOT_REACHED.
        risk_pass = False
        record = {
            "run_id": row.get("run_id"), "boundary": row.get("boundary"),
            "symbol": row.get("symbol"), "parameter_set_id": row.get("parameter_set_id"),
            "classification": category, **trace,
            "shadow_baseline_strategy_pass": False,
            "shadow_no_cap_strategy_pass": no_cap,
            "shadow_no_specific_gate_strategy_pass": False,
            "shadow_raw_score_only_diagnostic_pass": (
                float(trace["strategy_setup_pre_cap_score"]) >= STRATEGY_THRESHOLD
            ),
            "shadow_no_cap_geometry_pass": geometry_pass,
            "shadow_no_cap_target_pass": target_pass,
            "shadow_no_cap_cost_pass": cost_pass,
            "shadow_no_cap_risk_pass": risk_pass,
            "shadow_no_cap_rr_1_0_pass": bool(cost_pass and diagnostic.rr_cohorts_net.get("1.00")),
            "shadow_no_cap_rr_1_2_pass": bool(cost_pass and diagnostic.rr_cohorts_net.get("1.20")),
            "shadow_no_cap_rr_1_5_pass": bool(cost_pass and diagnostic.rr_cohorts_net.get("1.50")),
            "shadow_no_cap_paper_plan_eligible": bool(cost_pass and risk_pass and diagnostic.valid_plan),
            "shadow_geometry": asdict(diagnostic) if diagnostic is not None else None,
            "future_leakage": False,
        }
        records.append(record)
    raw_values = [record["strategy_raw_score"] for record in records]
    final_values = [record["strategy_final_score"] for record in records]
    reasons = Counter(record["strategy_reason_code"] for record in records)
    summary = {
        "parameter_set_id": next(iter(parameter_sets)),
        "snapshot_first_boundary": min(int(row["boundary"]) for row in source),
        "snapshot_last_boundary": max(int(row["boundary"]) for row in source),
        "boundaries": len({int(row["boundary"]) for row in source}),
        "evaluations": len(source), "setup_candidates": len(setups),
        "strategy_allowed": len(allowed), "strategy_rejected": len(rejects),
        "strategy_rejection_reasons": dict(reasons),
        "classifications": dict(classes),
        "threshold_adjacent_reject_count": sum(
            64.9 <= float(record["strategy_final_score"]) < 65.0 for record in records
        ),
        "exact_64_999_count": sum(record["strategy_final_score"] == WEAK_CAP for record in records),
        "cap_bound_reject_count": sum(record["classification"] == "CAP_BOUND_REJECT" for record in records),
        "raw_pass_final_reject_count": sum(
            float(record["strategy_raw_score"]) >= 65
            and float(record["strategy_final_score"]) < 65 for record in records
        ),
        "raw_80_plus_final_reject_count": sum(
            float(record["strategy_raw_score"]) >= 80
            and float(record["strategy_final_score"]) < 65 for record in records
        ),
        "strategy_raw_score_distribution": distribution(raw_values),
        "strategy_final_score_distribution": distribution(final_values),
        "shadow_replay_candidate_count": len(rejects),
        "shadow_no_cap_strategy_pass": sum(record["shadow_no_cap_strategy_pass"] for record in records),
        "shadow_no_cap_geometry_valid": sum(record["shadow_no_cap_geometry_pass"] for record in records),
        "shadow_no_cap_target_valid": sum(record["shadow_no_cap_target_pass"] for record in records),
        "shadow_no_cap_cost_pass": sum(record["shadow_no_cap_cost_pass"] for record in records),
        "shadow_no_cap_risk_pass": sum(record["shadow_no_cap_risk_pass"] for record in records),
        "shadow_no_cap_rr_1_0_pass": sum(record["shadow_no_cap_rr_1_0_pass"] for record in records),
        "shadow_no_cap_rr_1_2_pass": sum(record["shadow_no_cap_rr_1_2_pass"] for record in records),
        "shadow_no_cap_rr_1_5_pass": sum(record["shadow_no_cap_rr_1_5_pass"] for record in records),
        "shadow_no_cap_paper_plan_eligible": sum(record["shadow_no_cap_paper_plan_eligible"] for record in records),
        "future_leakage_count": sum(record["future_leakage"] for record in records),
        "shadow_replay_trading_mutations": 0,
        "shadow_risk_reservation_side_effects": 0,
        "shadow_paper_entities_created": 0,
        "binance_order_api_calls": 0,
    }
    return {"summary": summary, "records": records}
