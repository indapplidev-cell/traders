"""Deterministic, side-effect-free 5m Strategy cap calibration matrix.

The module consumes persisted decision-boundary payloads only.  It never opens
a network connection, reserves Risk quota, or creates PAPER entities.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
from statistics import median
from typing import Any, Iterable, Mapping

from app.engine_observation.strategy_forensic import (
    ALLOW_STATUS,
    STRATEGY_THRESHOLD,
    _geometry,
    _mapping,
    _number,
    reconstruct_strategy_trace,
)
from app.engine_paper.scalping_shadow import ShadowCostInputs


DATASET_ID = "5M_STRATEGY_CAP_CALIBRATION_V1"
WEAK_REASON = "STRATEGY_REJECT_WEAK_QUALITY"
CONFLICT_REASON = "STRATEGY_REJECT_CONFLICTING_CONTEXT"
HARD_REASONS = frozenset({
    "STRATEGY_REJECT_HARD_INVALIDATION",
    "STRATEGY_REJECT_SETUP_INVALID",
    "STRATEGY_REJECT_CONFLICTING_CONTEXT",
    "STRATEGY_REJECT_NEUTRAL_DIRECTION",
    "STRATEGY_REJECT_UNSUPPORTED_SETUP_TYPE",
})


def classify_not_evaluated_reason(row: Mapping[str, Any]) -> str | None:
    """Classify NOT_EVALUATED from authoritative analysis provenance."""
    analysis = _mapping(row.get("analysis"))
    setup = _mapping(row.get("setup"))
    quality = str(
        setup.get("source_entry_quality")
        or _mapping(setup.get("quality_diagnostics")).get("source_analysis_entry_quality")
        or analysis.get("entry_quality")
        or ""
    ).upper()
    if quality != "NOT_EVALUATED":
        return None
    phase = str(analysis.get("impulse_phase") or "").upper()
    impulse_context = _mapping(analysis.get("impulse_context"))
    direction = str(analysis.get("impulse_direction") or "").upper()
    if phase == "NO_IMPULSE":
        return "NOT_EVALUATED_NO_APPLICABLE_ENTRY_PATTERN"
    if impulse_context.get("data_sufficient") is False:
        return "NOT_EVALUATED_INSUFFICIENT_CONTEXT"
    if direction in {"", "UNKNOWN", "NEUTRAL", "NOT_EVALUATED"}:
        return "NOT_EVALUATED_DIRECTION_UNRESOLVED"
    if not phase and not impulse_context:
        return "NOT_EVALUATED_LEGACY_OR_NULL_SOURCE"
    return "NOT_EVALUATED_OTHER_EXPLICIT_REASON"


def _policy_specs() -> list[dict[str, Any]]:
    specs = [
        {"id": "C0_PRODUCTION", "kind": "production"},
        {"id": "C1_NO_WEAK_CAP_ONLY", "kind": "no_cap"},
        {"id": "C2_NOT_EVALUATED_BYPASS", "kind": "bypass"},
    ]
    specs.extend({"id": f"C3_UNKNOWN_CAP_{cap:g}", "kind": "unknown_cap", "value": cap}
                 for cap in (65.0, 70.0, 75.0, 80.0))
    specs.extend({"id": f"C4_NOT_EVALUATED_RAW_GE_{value:g}", "kind": "raw", "value": value}
                 for value in (80.0, 85.0, 90.0, 92.5, 95.0))
    specs.append({"id": "C5_CONSERVATIVE_RAW_GE_90", "kind": "conservative", "value": 90.0})
    return specs


def _policy_decision(spec: Mapping[str, Any], row: Mapping[str, Any],
                     trace: Mapping[str, Any], ne_reason: str | None) -> tuple[bool, str, float | None]:
    strategy = _mapping(row.get("strategy"))
    production_allowed = strategy.get("decision_status") == ALLOW_STATUS
    reason = trace.get("strategy_reason_code")
    raw = _number(trace.get("strategy_setup_pre_cap_score"))
    final = _number(trace.get("strategy_final_score"))
    if spec["kind"] == "production":
        return production_allowed, "PRODUCTION_DECISION", final
    if production_allowed:
        return True, "PRODUCTION_ALREADY_ALLOWED", final
    if reason in HARD_REASONS or reason != WEAK_REASON:
        return False, str(reason or "PRODUCTION_NON_WEAK_REJECT_PRESERVED"), final
    if spec["kind"] == "no_cap":
        # Only score presentation changes. The independent WEAK gate remains.
        return False, "WEAK_QUALITY_GATE_PRESERVED", raw
    if ne_reason is None:
        return False, "TRUE_EVALUATED_WEAK_PRESERVED", final
    if spec["kind"] == "bypass":
        return True, "NOT_EVALUATED_WEAK_GATE_BYPASSED", raw
    if spec["kind"] == "unknown_cap":
        score = None if raw is None else min(raw, float(spec["value"]))
        return bool(score is not None and score >= STRATEGY_THRESHOLD), "SEPARATE_UNKNOWN_TIER", score
    if spec["kind"] in {"raw", "conservative"}:
        passed = bool(raw is not None and raw >= float(spec["value"]))
        return passed, "NOT_EVALUATED_RAW_SCORE_GATE", raw
    raise ValueError("unknown shadow policy")


def _opportunity_ids(records: list[dict[str, Any]], interval_ms: int = 300_000) -> None:
    state: dict[tuple[str, str, str], tuple[int, str, str]] = {}
    for record in sorted(records, key=lambda item: (item["boundary"], item["symbol"], item["shadow_policy_id"])):
        direction = record.get("direction")
        if direction not in {"LONG", "SHORT"}:
            record["opportunity_id"] = None
            continue
        family = sha256(
            f"trade-5m-v2|{record['symbol']}|{direction}|{record.get('setup_type')}".encode()
        ).hexdigest()[:24]
        key = (str(record["shadow_policy_id"]), str(record["symbol"]), str(direction))
        prior = state.get(key)
        if prior and int(record["boundary"]) - prior[0] == interval_ms and prior[1] == family:
            opportunity_id = prior[2]
        else:
            opportunity_id = "opportunity-episode:" + sha256(
                f"{family}|{record['boundary']}".encode()
            ).hexdigest()[:24]
        record["opportunity_id"] = opportunity_id
        state[key] = (int(record["boundary"]), family, opportunity_id)


def _economic_snapshot(row: Mapping[str, Any]) -> Mapping[str, Any]:
    paper = _mapping(row.get("paper"))
    context = _mapping(paper.get("paper_context"))
    return _mapping(context.get("strategy_cap_shadow_economic_snapshot"))


def _cost_inputs(snapshot: Mapping[str, Any]) -> ShadowCostInputs | None:
    if not snapshot.get("causally_usable"):
        return None
    fields = {
        "entry_fee_bps", "exit_fee_bps", "entry_slippage_bps", "exit_slippage_bps",
        "safety_margin_bps", "spread_bps", "depth_impact_bps", "fee_source",
        "spread_source", "depth_impact_source", "spread_authoritative", "depth_authoritative",
        "bid", "ask", "buy_vwap", "sell_vwap", "economic_input_timestamp_ms",
        "economic_capture_started_at_ms", "decision_cutoff_timestamp_ms",
        "economic_input_source", "maximum_age_ms", "require_causal_timestamp",
    }
    return ShadowCostInputs(**{key: snapshot[key] for key in fields if key in snapshot})


def calibrate(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    source = sorted((dict(row) for row in rows), key=lambda item: (int(item["boundary"]), str(item["symbol"])))
    if not source:
        raise ValueError("calibration cohort is empty")
    parameter_sets = {row.get("parameter_set_id") for row in source}
    if len(parameter_sets) != 1 or None in parameter_sets:
        raise ValueError("calibration cohort must have one parameter_set_id")
    specs = _policy_specs()
    reason_histogram: Counter[str] = Counter()
    by_symbol: Counter[str] = Counter()
    by_direction: Counter[str] = Counter()
    by_regime: Counter[str] = Counter()
    by_setup: Counter[str] = Counter()
    by_hour: Counter[str] = Counter()
    ne_raw_80 = ne_raw_90 = 0
    records: list[dict[str, Any]] = []
    setup_count = allowed_count = rejected_count = 0
    rejection_histogram: Counter[str] = Counter()
    for row in source:
        setup = _mapping(row.get("setup"))
        strategy = _mapping(row.get("strategy"))
        if setup.get("setup_status") != "SETUP_CANDIDATE":
            continue
        setup_count += 1
        trace = reconstruct_strategy_trace(row)
        terminal = str(trace.get("strategy_reason_code") or "")
        if strategy.get("decision_status") == ALLOW_STATUS:
            allowed_count += 1
        elif strategy.get("decision_status") == "REJECT":
            rejected_count += 1
            rejection_histogram[terminal] += 1
        ne_reason = classify_not_evaluated_reason(row)
        analysis = _mapping(row.get("analysis"))
        direction_raw = str(strategy.get("direction_hint") or setup.get("direction_hint") or "")
        direction = "LONG" if direction_raw == "BULLISH" else "SHORT" if direction_raw == "BEARISH" else None
        if ne_reason:
            reason_histogram[ne_reason] += 1
            by_symbol[str(row.get("symbol"))] += 1
            by_direction[str(direction or "UNRESOLVED")] += 1
            by_regime[str(analysis.get("regime") or "UNKNOWN")] += 1
            by_setup[str(setup.get("setup_type") or "UNKNOWN")] += 1
            hour = datetime.fromtimestamp(int(row["boundary"]) / 1000, timezone.utc).strftime("%H")
            by_hour[hour] += 1
            raw = _number(trace.get("strategy_setup_pre_cap_score")) or -1
            ne_raw_80 += int(raw >= 80)
            ne_raw_90 += int(raw >= 90)
        snapshot = _economic_snapshot(row)
        costs = _cost_inputs(snapshot)
        geometry_without_costs = None
        geometry_with_costs = None
        for spec in specs:
            shadow_allowed, shadow_reason, shadow_score = _policy_decision(spec, row, trace, ne_reason)
            if shadow_allowed and costs is not None:
                if geometry_with_costs is None:
                    geometry_with_costs = _geometry(row, costs)
                diagnostic = geometry_with_costs
            elif shadow_allowed:
                if geometry_without_costs is None:
                    geometry_without_costs = _geometry(row)
                diagnostic = geometry_without_costs
            else:
                diagnostic = None
            # Historical rejects have no causal economics.  A later quote is
            # intentionally never loaded or substituted here.
            economics_replayable = bool(snapshot.get("causally_usable"))
            geometry_valid = bool(diagnostic and diagnostic.stop_envelope_pass is True)
            target_valid = bool(diagnostic and diagnostic.causal_target_exists)
            cost_pass = bool(diagnostic and economics_replayable and diagnostic.economic_gate_pass)
            risk_allowed = bool(cost_pass and shadow_score is not None and shadow_score >= 65)
            record = {
                "timestamp": datetime.fromtimestamp(int(row["boundary"]) / 1000, timezone.utc).isoformat(),
                "boundary": int(row["boundary"]), "symbol": row.get("symbol"),
                "profile_id": row.get("profile") or "trade-5m-v2",
                "parameter_set_id": row.get("parameter_set_id"), "run_id": row.get("run_id"),
                "result_id": row.get("result_id"), "direction": direction,
                "regime": analysis.get("regime"), "setup_type": setup.get("setup_type"),
                "raw_score": trace.get("strategy_setup_pre_cap_score"),
                "analysis_entry_quality_status": setup.get("source_entry_quality"),
                "analysis_entry_quality_reason": ne_reason,
                "analysis_entry_quality_tier": setup.get("source_entry_quality"),
                "setup_quality_tier": setup.get("setup_quality"),
                "penalties": trace.get("strategy_penalties"), "score_before_cap": trace.get("strategy_setup_pre_cap_score"),
                "cap_type": trace.get("strategy_cap_type"), "cap_value": trace.get("strategy_cap_value"),
                "score_after_cap": trace.get("strategy_post_cap_score"),
                "confidence_adjustment": trace.get("strategy_confidence_adjustment"),
                "final_score": trace.get("strategy_final_score"),
                "source_status_gate": terminal not in {"STRATEGY_REJECT_SETUP_INVALID"},
                "hard_invalidation_gate": terminal != "STRATEGY_REJECT_HARD_INVALIDATION",
                "conflict_gate": terminal != CONFLICT_REASON,
                "confirmation_gate": terminal not in {"STRATEGY_WAIT_FOR_CONFIRMATION", "STRATEGY_REJECT_NO_SETUP"},
                "direction_gate": terminal != "STRATEGY_REJECT_NEUTRAL_DIRECTION",
                "setup_type_gate": terminal != "STRATEGY_REJECT_UNSUPPORTED_SETUP_TYPE",
                "weak_quality_gate": terminal != WEAK_REASON,
                "minimum_quality_gate": terminal not in {
                    "STRATEGY_REJECT_POOR_OR_INVALID_QUALITY", "STRATEGY_REJECT_UNKNOWN_QUALITY",
                },
                "production_terminal_reason": trace.get("strategy_reason_code"),
                "shadow_policy_id": spec["id"], "shadow_strategy_allowed": shadow_allowed,
                "shadow_strategy_reason": shadow_reason, "shadow_strategy_score": shadow_score,
                "entry": getattr(diagnostic, "entry", None), "stop": getattr(diagnostic, "final_stop", None),
                "target": getattr(diagnostic, "causal_target", None), "atr": getattr(diagnostic, "atr", None),
                "atr_buffer": getattr(diagnostic, "atr_buffer_bps", None),
                "stop_envelope": getattr(diagnostic, "stop_envelope_bps", None),
                "stop_distance_pct": (
                    None if getattr(diagnostic, "stop_distance_bps", None) is None
                    else getattr(diagnostic, "stop_distance_bps") / 100
                ),
                "target_distance_pct": (
                    None if getattr(diagnostic, "target_distance_bps", None) is None
                    else getattr(diagnostic, "target_distance_bps") / 100
                ),
                "geometry_valid": geometry_valid, "geometry_reject_reason": getattr(diagnostic, "rejection_reason", None),
                "target_valid": target_valid, "target_source": getattr(diagnostic, "target_source_type", None),
                "economic_input_source": snapshot.get("economic_input_source"),
                "economic_input_timestamp": snapshot.get("economic_input_timestamp_ms"),
                "decision_cutoff_timestamp": snapshot.get("decision_cutoff_timestamp_ms"),
                "economic_input_age_ms": snapshot.get("economic_input_age_ms"),
                "bid": snapshot.get("bid"), "ask": snapshot.get("ask"),
                "spread_bps": snapshot.get("spread_bps"), "depth_impact_bps": snapshot.get("depth_impact_bps"),
                "entry_slippage_bps": snapshot.get("entry_slippage_bps"),
                "exit_slippage_bps": snapshot.get("exit_slippage_bps"),
                "fee_bps_round_trip": (
                    None if snapshot.get("entry_fee_bps") is None or snapshot.get("exit_fee_bps") is None
                    else float(snapshot["entry_fee_bps"]) + float(snapshot["exit_fee_bps"])
                ),
                "safety_margin_bps": snapshot.get("safety_margin_bps"),
                "total_cost_bps": getattr(diagnostic, "total_cost_bps", None),
                "gross_rr": getattr(diagnostic, "gross_rr", None),
                "net_rr": getattr(diagnostic, "net_rr", None),
                "expected_net_edge_bps": getattr(diagnostic, "expected_net_edge_bps", None),
                "break_even_win_rate": getattr(diagnostic, "break_even_win_rate", None),
                "cost_pass": cost_pass, "risk_allowed": risk_allowed,
                "risk_reason": "SHADOW_CHECK_WITHOUT_RESERVATION" if risk_allowed else "NOT_REACHED_OR_POLICY_REJECT",
                "rr_1_0_pass": bool(cost_pass and getattr(diagnostic, "rr_cohorts_net", {}).get("1.00")),
                "rr_1_2_pass": bool(cost_pass and getattr(diagnostic, "rr_cohorts_net", {}).get("1.20")),
                "rr_1_5_pass": bool(cost_pass and getattr(diagnostic, "rr_cohorts_net", {}).get("1.50")),
                "paper_plan_eligible": bool(cost_pass and risk_allowed and getattr(diagnostic, "valid_plan", False)),
                "paper_not_reached_reason": None if cost_pass else "UPSTREAM_ECONOMICS_NOT_REPLAYABLE_OR_REJECTED",
            }
            records.append(record)
    _opportunity_ids(records)
    cohorts: dict[str, Any] = {}
    for spec in specs:
        selected = [record for record in records if record["shadow_policy_id"] == spec["id"]]
        passed = [record for record in selected if record["shadow_strategy_allowed"]]
        opportunity_counts = Counter(record["opportunity_id"] for record in passed if record.get("opportunity_id"))
        repeats = sum(opportunity_counts.values()) - len(opportunity_counts)
        reobservations = sorted(opportunity_counts.values())
        p90_index = max(0, int(len(reobservations) * .9 + .999999) - 1) if reobservations else 0
        cohorts[spec["id"]] = {
            "classification": "KEEP_AS_PRODUCTION_CONTROL" if spec["kind"] == "production" else "INSUFFICIENT_ECONOMIC_DATA",
            "strategy_pass": len(passed), "unique_opportunities": len(opportunity_counts),
            "repeat_observations": repeats,
            "opportunity_churn_rate": (repeats / len(passed)) if passed else None,
            "median_reobservations_per_opportunity": median(reobservations) if reobservations else None,
            "p90_reobservations_per_opportunity": reobservations[p90_index] if reobservations else None,
            "geometry_valid": sum(record["geometry_valid"] for record in passed),
            "target_valid": sum(record["target_valid"] for record in passed),
            "cost_pass": sum(record["cost_pass"] for record in passed),
            "risk_pass": sum(record["risk_allowed"] for record in passed),
            "rr_1_0_pass": sum(record["rr_1_0_pass"] for record in passed),
            "rr_1_2_pass": sum(record["rr_1_2_pass"] for record in passed),
            "rr_1_5_pass": sum(record["rr_1_5_pass"] for record in passed),
            "paper_eligible": sum(record["paper_plan_eligible"] for record in passed),
            "net_expectancy": None, "profitability_confidence": "INSUFFICIENT_ECONOMIC_DATA",
            "by_symbol": dict(Counter(record["symbol"] for record in passed)),
            "by_direction": dict(Counter(record["direction"] for record in passed)),
            "by_regime": dict(Counter(record["regime"] for record in passed)),
            "by_setup_type": dict(Counter(record["setup_type"] for record in passed)),
        }
    return {
        "dataset_id": DATASET_ID, "parameter_set_id": next(iter(parameter_sets)),
        "first_boundary": min(int(row["boundary"]) for row in source),
        "last_boundary": max(int(row["boundary"]) for row in source),
        "boundaries": len({int(row["boundary"]) for row in source}), "evaluations": len(source),
        "setup_candidates": setup_count, "strategy_allowed": allowed_count,
        "strategy_rejected": rejected_count, "strategy_rejection_histogram": dict(rejection_histogram),
        "not_evaluated_total": sum(reason_histogram.values()),
        "not_evaluated_classification": "C_EVALUATOR_NON_APPLICABILITY_OR_ABSENCE_OF_POSITIVE_EVIDENCE",
        "not_evaluated_reason_histogram": dict(reason_histogram),
        "not_evaluated_by_symbol": dict(by_symbol), "not_evaluated_by_direction": dict(by_direction),
        "not_evaluated_by_regime": dict(by_regime), "not_evaluated_by_setup_type": dict(by_setup),
        "not_evaluated_by_time_bucket": dict(by_hour),
        "not_evaluated_with_raw_score_ge_80": ne_raw_80,
        "not_evaluated_with_raw_score_ge_90": ne_raw_90,
        "shadow_policy_count": len(specs), "shadow_factor_isolation": "PASS",
        "historical_boundary_time_economics_available": any(
            bool(_economic_snapshot(row).get("causally_usable")) for row in source
        ),
        "historical_economic_replay_count": 0,
        "historical_economic_replay_rejected_future_leakage_count": len({
            record["run_id"] for record in records
            if record["shadow_policy_id"] != "C0_PRODUCTION"
            and record["shadow_strategy_allowed"] and record["economic_input_source"] is None
        }),
        "cohorts": cohorts, "records": records,
        "side_effects": {"risk_reservations": 0, "paper_entities": 0, "trading_mutations": 0, "binance_order_api_calls": 0},
    }


__all__ = ["DATASET_ID", "calibrate", "classify_not_evaluated_reason"]
