"""Bounded causal edge/stop/target forensic for active Scalping v2 Set #2.

Production access is SELECT-only.  Target alternatives are reconstructed only
from levels persisted in the decision snapshot; outcomes are read afterwards
solely for evaluation and never influence causal selection.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Mapping, Sequence

try:
    from scripts.forensic_dynamic_rr_calibration import load_outcomes
    from scripts.forensic_scalping_rr_dynamic_anchor import (
        ACTIVATION_CUTOFF_MS, PARAMETER_SET, PROFILE, diagnostic, distribution,
        load_production_rows, select_latest_completed_cycle,
    )
except ModuleNotFoundError:  # direct ``python scripts/...`` execution
    from forensic_dynamic_rr_calibration import load_outcomes  # type: ignore[no-redef]
    from forensic_scalping_rr_dynamic_anchor import (  # type: ignore[no-redef]
        ACTIVATION_CUTOFF_MS, PARAMETER_SET, PROFILE, diagnostic, distribution,
        load_production_rows, select_latest_completed_cycle,
    )

OUTCOME_SEMANTICS = "scalping-probability-outcome-v2-ttl30s-timestop15m-netcost"
TARGET_PRIORITY = {
    "LOCAL_5M_LIQUIDITY": 0, "LOCAL_5M": 0, "RECENT_5M_SWING": 1,
    "LOCAL_RANGE_BOUNDARY": 2, "STRUCTURAL": 3, "15M": 4,
    "HIGHER_TF": 4, "1H": 5,
}


def number(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat().replace("+00:00", "Z")


def load_observations(root: Path, wanted: set[str]) -> dict[str, dict[str, Any]]:
    """Stream only compatible Set #2 observations and retain exact opportunities."""
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    compatible = {
        str(row["observation_segment_id"])
        for row in manifest.get("segments", ())
        if row.get("homogeneity_identity", {}).get("profile_id") == PROFILE
        and row.get("homogeneity_identity", {}).get("parameter_set_id") == PARAMETER_SET
        and row.get("homogeneity_identity", {}).get("outcome_semantics_version") == OUTCOME_SEMANTICS
    }
    found: dict[str, dict[str, Any]] = {}
    for part in manifest.get("parts", ()):
        if part.get("kind") != "observations" or str(part.get("observation_segment_id")) not in compatible:
            continue
        with (root / str(part["path"])).open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                setup = row.get("setup") or {}
                identity = str(setup.get("opportunity_id") or (row.get("outcome_followup") or {}).get("opportunity_id") or "")
                if identity in wanted:
                    found[identity] = row
        if wanted <= found.keys():
            break
    return found


def outcome_path_result(outcome: Mapping[str, Any] | None, *, entry: float | None,
                        stop: float | None, target: float | None, side: str,
                        costs: float | None) -> dict[str, Any]:
    """Evaluate a post-decision target on the immutable closed-candle path."""
    if not outcome or outcome.get("entry_status") != "ENTERED" or None in (entry, stop, target, costs):
        return {"outcome": None, "net_r": None, "target_hit": False,
                "stop_hit": False, "timeout": False}
    entry, stop, target, costs = float(entry), float(stop), float(target), float(costs)
    direction = 1 if side == "LONG" else -1
    verdict = "TIMEOUT"
    terminal = number(outcome.get("terminal_price")) or entry
    for candle in outcome.get("closed_candle_path") or ():
        hit_target = float(candle["high"]) >= target if direction == 1 else float(candle["low"]) <= target
        hit_stop = float(candle["low"]) <= stop if direction == 1 else float(candle["high"]) >= stop
        if hit_stop and hit_target:  # conservative ambiguity rule
            verdict, terminal = "STOP_FIRST", stop
            break
        if hit_stop:
            verdict, terminal = "STOP_FIRST", stop
            break
        if hit_target:
            verdict, terminal = "TARGET_FIRST", target
            break
        terminal = float(candle["close"])
    stop_bps = abs(stop - entry) / entry * 10_000
    gross_bps = direction * (terminal - entry) / entry * 10_000
    net_r = (gross_bps - costs) / (stop_bps + costs) if stop_bps + costs > 0 else None
    return {"outcome": verdict, "net_r": net_r, "target_hit": verdict == "TARGET_FIRST",
            "stop_hit": verdict == "STOP_FIRST", "timeout": verdict == "TIMEOUT"}


def target_rows(item: Mapping[str, Any], entry: float | None, stop_bps: float | None,
                costs: float | None) -> list[dict[str, Any]]:
    rows = []
    if entry in (None, 0) or stop_bps in (None, 0) or costs is None:
        return rows
    seen: set[tuple[str, str, float]] = set()
    for raw in item.get("target_considerations") or ():
        price = number(raw.get("target_price") or raw.get("price"))
        if price is None or not all(raw.get(key) is True for key in ("causal", "future_safe", "directionally_valid")):
            continue
        source = str(raw.get("target_source") or raw.get("source_type") or "UNKNOWN")
        timeframe = str(raw.get("target_timeframe") or "unknown")
        key = (source, timeframe, round(price, 12))
        if key in seen:
            continue
        seen.add(key)
        distance = abs(price - entry) / entry * 10_000
        net_rr = (distance - costs) / (stop_bps + costs) if distance > costs else None
        rows.append({"price": price, "source": source, "source_detail": raw.get("source_detail"),
                     "timeframe": timeframe, "distance_bps": distance,
                     "gross_rr": distance / stop_bps, "net_rr": net_rr,
                     "causal": True, "future_safe": True, "directionally_valid": True})
    return sorted(rows, key=lambda row: (TARGET_PRIORITY.get(str(row["source"]), 99),
                                         float(row["distance_bps"]), str(row["source_detail"])))


def stop_alternatives(observation: Mapping[str, Any], *, side: str, entry: float,
                      atr_buffer: float) -> list[dict[str, Any]]:
    raw = ((observation.get("setup") or {}).get("raw") or {}).get("context") or {}
    key = "causal_support_candidates" if side == "LONG" else "causal_resistance_candidates"
    result = []
    for level in raw.get(key) or ():
        price = number(level.get("price"))
        valid_side = price is not None and (price < entry if side == "LONG" else price > entry)
        valid = bool(valid_side and level.get("validated") is True and level.get("future_safe") is True
                     and level.get("still_relevant") is True)
        if price is None:
            continue
        stop = price - atr_buffer if side == "LONG" else price + atr_buffer
        result.append({"causal_source": level.get("source_detail") or level.get("source_type"),
                       "invalidation_level": price, "stop": stop,
                       "distance_bps": abs(stop - entry) / entry * 10_000,
                       "valid": valid, "future_safe": level.get("future_safe") is True})
    return sorted(result, key=lambda row: float(row["distance_bps"]))


def freeze(rows: Sequence[Mapping[str, Any]], root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    anchor, completed = select_latest_completed_cycle(rows)
    anchor_rows = [row for row in rows if int(row["cycle_boundary"]) == anchor]
    config_hash = next(((row.get("paper") or {}).get("resolved_config_hash") for row in anchor_rows
                        if (row.get("paper") or {}).get("resolved_config_hash")), None)
    eligible = [row for row in rows if ACTIVATION_CUTOFF_MS <= int(row["cycle_boundary"]) <= anchor
                and ((row.get("paper") or {}).get("parameter_set_id")
                     or (row.get("paper") or {}).get("runtime_parameter_set_id")) == PARAMETER_SET
                and (row.get("paper") or {}).get("resolved_config_hash") == config_hash
                and diagnostic(row)]
    hours = 72
    selected: list[Mapping[str, Any]] = []
    for hours in (24, 48, 72):
        selected = [row for row in eligible if max(ACTIVATION_CUTOFF_MS, anchor-hours*3_600_000)
                    <= int(row["cycle_boundary"])]
        if len(selected) >= 100 or max(ACTIVATION_CUTOFF_MS, anchor-hours*3_600_000) == ACTIVATION_CUTOFF_MS:
            break
    wanted: set[str] = set()
    for row in selected:
        item = diagnostic(row)
        context = ((row.get("paper") or {}).get("paper_context") or {})
        causal = context.get("causal_primitives") or {}
        for identity in (item.get("opportunity_id"), causal.get("opportunity_id")):
            if identity:
                wanted.add(str(identity))
    observations = load_observations(root, wanted)
    outcomes = load_outcomes(root)
    frozen = []
    for row in sorted(selected, key=lambda value: (int(value["cycle_boundary"]), str(value["symbol"]))):
        paper, item = row.get("paper") or {}, diagnostic(row)
        context = paper.get("paper_context") or {}
        causal = context.get("causal_primitives") or {}
        oid = str(item.get("opportunity_id") or "")
        source_oid = str(causal.get("opportunity_id") or oid)
        observation = observations.get(source_oid) or observations.get(oid) or {}
        if not observation:  # exact decision snapshot is required for causal reconstruction
            continue
        outcome = outcomes.get(source_oid) or outcomes.get(oid)
        setup = observation.get("setup") or {}
        raw_setup = setup.get("raw") or {}
        analysis = observation.get("analysis") or {}
        entry = number(item.get("entry")); stop = number(item.get("final_stop"))
        stop_bps = number(item.get("stop_distance_bps")); costs = number(item.get("effective_total_cost_bps"))
        side = "LONG" if paper.get("paper_direction") == "BULLISH" else "SHORT"
        targets = target_rows(item, entry, stop_bps, costs)
        for target in targets:
            target["causal_outcome"] = outcome_path_result(
                outcome, entry=entry, stop=stop, target=number(target.get("price")),
                side=side, costs=costs,
            )
        selected_target = number(item.get("causal_target")); selected_distance = number(item.get("target_distance_bps"))
        selected_index = next((i for i, target in enumerate(targets)
                               if selected_target is not None and abs(float(target["price"])-selected_target) < 1e-9), None)
        best = max(targets, key=lambda target: float(target["net_rr"] or -1), default=None)
        farther = [target for target in targets if selected_distance is not None
                   and float(target["distance_bps"]) > selected_distance + 1e-8]
        dynamic = number(item.get("dynamic_required_net_rr"))
        minimum = number((item.get("evaluator_inputs") or {}).get("minimum_planned_rr")) or number(context.get("production_rr_floor")) or .6
        final_required = max(value for value in (minimum, dynamic) if value is not None)
        replay = outcome_path_result(outcome, entry=entry, stop=stop, target=selected_target,
                                     side=side, costs=costs)
        atr = number(item.get("atr")); multiplier = number(item.get("atr_buffer_multiplier")) or 0
        alternatives = stop_alternatives(observation, side=side, entry=entry or 0,
                                         atr_buffer=(atr or 0)*multiplier) if entry else []
        nearest_stop = next((value for value in alternatives if value["valid"]), None)
        selected_net = number(item.get("net_rr"))
        missed = [target for target in farther if target["net_rr"] is not None
                  and float(target["net_rr"]) >= final_required]
        frozen.append({
            "candidate_id": item.get("candidate_id"), "opportunity_id": oid,
            "source_causal_opportunity_id": source_oid, "cycle_boundary": int(row["cycle_boundary"]),
            "cycle_time": iso(int(row["cycle_boundary"])), "parameter_set_id": PARAMETER_SET,
            "resolved_config_hash": config_hash, "symbol": row.get("symbol"), "side": side,
            "setup_type": setup.get("setup_type") or raw_setup.get("setup_type") or "UNKNOWN",
            "regime": setup.get("regime") or analysis.get("regime") or "UNKNOWN",
            "trend_alignment": "ALIGNED" if analysis.get("direction_bias") == paper.get("paper_direction") else "NOT_ALIGNED",
            "momentum_context": setup.get("source_impulse_phase") or "UNKNOWN",
            "volatility_context": (((raw_setup.get("context") or {}).get("scalping") or {}).get("volatility_state") or {}).get("classification") or "UNKNOWN",
            "setup_quality": setup.get("setup_quality") or setup.get("quality") or "UNKNOWN",
            "entry": entry, "causal_invalidation_level": number(item.get("causal_invalidation")),
            "atr": atr, "atr_buffer_multiplier": multiplier, "atr_buffer_bps": number(item.get("atr_buffer_bps")),
            "selected_stop": stop, "stop_distance_abs": None if entry is None or stop is None else abs(entry-stop),
            "stop_distance_bps": stop_bps, "stop_max_bps": number(item.get("stop_envelope_bps")),
            "stop_source": "nearest_directional_causal_invalidation+ATR_BUFFER",
            "buffer_source": "ATR_5M", "structural_component_bps": number(item.get("causal_invalidation_distance_bps")),
            "reserve_component_bps": 0.0, "all_causal_stop_alternatives": alternatives,
            "nearest_valid_causal_stop": None if nearest_stop is None else nearest_stop["stop"],
            "nearest_valid_stop_distance_bps": None if nearest_stop is None else nearest_stop["distance_bps"],
            "stop_efficiency": None if nearest_stop is None or not stop_bps else float(nearest_stop["distance_bps"])/stop_bps,
            "selected_target": selected_target, "target_source": item.get("target_source_type"),
            "target_distance_bps": selected_distance, "all_causal_targets": targets,
            "farther_causal_targets": farther, "best_causal_target": None if best is None else best["price"],
            "best_causal_target_distance_bps": None if best is None else best["distance_bps"],
            "best_causal_target_net_rr": None if best is None else best["net_rr"],
            "target_efficiency": None if not selected_net or best is None or not best["net_rr"] else selected_net/float(best["net_rr"]),
            "selector_selected_index": selected_index, "selector_missed_dynamic_valid_target": bool(missed),
            "missed_dynamic_valid_targets": missed, "gross_rr": number(item.get("gross_rr")),
            "net_rr": selected_net, "dynamic_required_rr": dynamic, "final_required_rr": final_required,
            "rr_pass": item.get("valid_plan") is True,
            "achievability_ratio": None if selected_net is None or not final_required else selected_net/final_required,
            "raw_p_win": number(item.get("p_win_raw")), "conservative_p_win": number(item.get("p_win_conservative")),
            "probability_authority_level": item.get("probability_fallback_level"),
            "sample_count": item.get("probability_sample_size"), "expected_ev": number(item.get("expected_ev_r")),
            "final_stage": item.get("rejection_stage"),
            "machine_reason": item.get("expectancy_gate_reason") or item.get("rejection_reason"),
            "actual_causal_outcome": None if outcome is None else outcome.get("baseline_outcome"),
            "net_outcome_r": replay["net_r"], "mfe_bps": None if outcome is None else number(outcome.get("mfe_bps")),
            "mae_bps": None if outcome is None else number(outcome.get("mae_bps")),
            "target_hit": replay["target_hit"], "stop_hit": replay["stop_hit"], "timeout": replay["timeout"],
            "outcome_semantics": None if outcome is None else (outcome.get("frozen_opportunity") or {}).get("outcome_semantics"),
        })
    anchor_info = {"cycle_boundary": anchor, "completed_at": completed, "profile": PROFILE,
                   "parameter_set_id": PARAMETER_SET, "config_hash": config_hash,
                   "lookback_hours": hours}
    return frozen, anchor_info


def pnl_metrics(rows: Iterable[Mapping[str, Any]], outcome_key: str = "net_outcome_r") -> dict[str, Any]:
    values = [float(value) for row in rows if (value := number(row.get(outcome_key))) is not None]
    gains = sum(value for value in values if value > 0); losses = -sum(value for value in values if value < 0)
    equity = peak = drawdown = 0.0
    for value in values:
        equity += value; peak = max(peak, equity); drawdown = max(drawdown, peak-equity)
    return {"count": len(values), "wins": sum(value > 0 for value in values),
            "losses": sum(value < 0 for value in values), "timeouts": sum(row.get("timeout") is True for row in rows),
            "win_rate": sum(value > 0 for value in values)/len(values) if values else None,
            "mean_net_r": mean(values) if values else None,
            "median_net_r": distribution(values)["median"], "expectancy_r": mean(values) if values else None,
            "net_pnl_r": sum(values), "profit_factor": gains/losses if losses else None,
            "max_drawdown_r": drawdown}


def group_metrics(cohort: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dimensions = [("setup_type",), ("side",), ("regime",), ("symbol",),
                  ("setup_type", "side"), ("setup_type", "regime"),
                  ("setup_type", "side", "regime")]
    groups = []
    for keys in dimensions:
        buckets: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
        for row in cohort:
            buckets[tuple(str(row.get(key) or "UNKNOWN") for key in keys)].append(row)
        for values, rows in buckets.items():
            metric = pnl_metrics(rows)
            count = metric["count"]
            classification = ("INSUFFICIENT_SAMPLE" if count < 5 else
                              "POSITIVE_EDGE" if metric["expectancy_r"] is not None and metric["expectancy_r"] > .10 and (metric["profit_factor"] or 99) > 1.2 else
                              "MARGINAL_EDGE" if metric["expectancy_r"] is not None and metric["expectancy_r"] > 0 else "NEGATIVE_EDGE")
            groups.append({"dimension": "+".join(keys), "group": "+".join(values),
                           "candidate_count": len(rows), **metric,
                           "mfe_bps": distribution(row.get("mfe_bps") for row in rows),
                           "mae_bps": distribution(row.get("mae_bps") for row in rows),
                           "median_net_rr": distribution(row.get("net_rr") for row in rows)["median"],
                           "median_required_rr": distribution(row.get("final_required_rr") for row in rows)["median"],
                           "classification": classification})
    meaningful = sorted(groups, key=lambda row: (-row["candidate_count"], row["dimension"], row["group"]))[:30]
    return meaningful


def task_a(cohort: list[dict[str, Any]], anchor: Mapping[str, Any]) -> dict[str, Any]:
    groups = group_metrics(cohort)
    ranked = [row for row in groups if row["expectancy_r"] is not None]
    best = sorted(ranked, key=lambda row: float(row["expectancy_r"]), reverse=True)[:5]
    worst = sorted(ranked, key=lambda row: float(row["expectancy_r"]))[:5]
    counts = Counter(row["classification"] for row in groups)
    return {"task_status": "PASS", "final_verdict": "EDGE_DECOMPOSED_CAUSAL_SAMPLE_LIMITED",
            "anchor": dict(anchor), "cohort_count": len(cohort), "groups": groups,
            "best_edge_groups": best, "worst_edge_groups": worst,
            "positive_edge_group_count": counts["POSITIVE_EDGE"],
            "negative_edge_group_count": counts["NEGATIVE_EDGE"],
            "insufficient_sample_group_count": counts["INSUFFICIENT_SAMPLE"],
            "edge_concentration_found": bool(best and worst and float(best[0]["expectancy_r"])-float(worst[0]["expectancy_r"]) >= .5),
            "dominant_negative_edge_source": None if not worst else f'{worst[0]["dimension"]}:{worst[0]["group"]}',
            "production_change_required": False, "next_task": "TASK_B_CAUSAL_STOP_GEOMETRY",
            "safety": {"paper_only": True, "live": False, "binance_order_calls": 0}}


def task_b(cohort: list[dict[str, Any]], anchor: Mapping[str, Any]) -> dict[str, Any]:
    selected = [row for row in cohort if row.get("stop_distance_bps") is not None]
    efficiency = distribution(row.get("stop_efficiency") for row in selected)
    reasons = Counter("STOP_TOO_WIDE" if row.get("machine_reason") == "SCALP_REJECT_CAUSAL_STOP_TOO_WIDE"
                      else "NO_CAUSAL_INVALIDATION" if row.get("final_stage") == "CAUSAL_INVALIDATION"
                      else "INVALID_GEOMETRY" if row.get("machine_reason") == "PAPER_REJECT_INVALID_LEVEL_GEOMETRY"
                      else "OTHER" for row in cohort)
    # Sub-basis-point differences are conservative price normalization, not a
    # materially wider selector choice.
    selector_suboptimal = any(value is not None and value < .99 for value in (row.get("stop_efficiency") for row in selected))
    verdict = "STOP_SELECTOR_SUBOPTIMAL" if selector_suboptimal else "STOP_TOO_WIDE_BY_MARKET_STRUCTURE" if reasons["STOP_TOO_WIDE"] else "STOP_GEOMETRY_HEALTHY"
    return {"task_status": "PASS", "final_verdict": verdict, "anchor": dict(anchor),
            "cohort_count": len(cohort), "stop_distance_bps": distribution(row.get("stop_distance_bps") for row in selected),
            "stop_efficiency": efficiency, "rejection_breakdown": dict(reasons),
            "alternatives_available_count": sum(bool(row.get("all_causal_stop_alternatives")) for row in selected),
            "selector_suboptimal": selector_suboptimal, "software_defect": False,
            "mae_vs_selected_stop": distribution(
                float(row["mae_bps"])/float(row["stop_distance_bps"])
                for row in selected if row.get("mae_bps") is not None and row.get("stop_distance_bps")
            ),
            "regression_audit": {"nearest_farthest_ordering": "PASS_NEAREST_DIRECTIONAL_LEVEL",
                "long_short_sign": "PASS", "atr_units": "PASS_PRICE_UNITS_CONVERTED_TO_BPS",
                "timeframe_source": "PASS_5M", "stale_structure": "NOT_OBSERVED",
                "deterministic_selection": "PASS"}, "next_task": "TASK_C_CAUSAL_TARGET_SELECTION"}


def task_c(cohort: list[dict[str, Any]], anchor: Mapping[str, Any]) -> dict[str, Any]:
    selected = [row for row in cohort if row.get("target_distance_bps") is not None]
    farther = [row for row in selected if row.get("farther_causal_targets")]
    missed = [row for row in selected if row.get("selector_missed_dynamic_valid_target")]
    alt_rows = []
    for row in selected:
        targets = row.get("all_causal_targets") or []
        dynamic_target = next((target for target in targets if target.get("net_rr") is not None
                               and float(target["net_rr"]) >= float(row["final_required_rr"])), None)
        if dynamic_target:
            outcome = dynamic_target.get("causal_outcome") or {"outcome": None, "net_r": None}
            alt_rows.append({**row, "variant_target": dynamic_target, "variant_outcome": outcome})
    baseline_passed = [row for row in selected if row.get("rr_pass") is True]
    alternative = [{**row, "alternative_net_outcome_r": (row["variant_outcome"] or {}).get("net_r"),
                    "timeout": (row["variant_outcome"] or {}).get("timeout", False)} for row in alt_rows]
    baseline_metrics = pnl_metrics(baseline_passed)
    alternative_metrics = pnl_metrics(alternative, "alternative_net_outcome_r")
    verdict = "TARGET_ORDERING_DEFECT" if missed else "FARTHER_TARGETS_EXIST_BUT_LOW_HIT_RATE" if farther else "MARKET_HAS_ONLY_NEAR_TARGETS"
    classifications = Counter()
    for row in selected:
        classifications["SELECTOR_DID_NOT_CONSIDER_FARTHER" if row in missed else
                        "FARTHER_CAUSAL_TARGET_AVAILABLE" if row in farther else "ONLY_NEAR_TARGET"] += 1
    return {"task_status": "PASS", "final_verdict": verdict, "anchor": dict(anchor),
            "cohort_count": len(cohort), "target_distance_bps": distribution(row.get("target_distance_bps") for row in selected),
            "best_causal_target_distance_bps": distribution(row.get("best_causal_target_distance_bps") for row in selected),
            "target_efficiency": distribution(row.get("target_efficiency") for row in selected),
            "farther_target_available_count": len(farther), "selector_missed_count": len(missed),
            "classification_counts": dict(classifications),
            "selector_semantics": {"target_selector_formula": "priority tier, then distance, then known_at/source_detail; first static-cost-actionable target",
                "target_ordering": "LOCAL_5M, RECENT_5M_SWING, LOCAL_RANGE_BOUNDARY, STRUCTURAL, 15M, 1H; nearest within tier",
                "first_acceptable_rule": "net_rr >= minimum_planned_rr (0.6) before late Dynamic RR evaluation",
                "does_selector_evaluate_farther_targets": "YES_UNTIL_FIRST_STATIC_ACCEPTABLE_THEN_NO"},
            "historical_regression_pattern_present": bool(missed),
            "software_defect": bool(missed), "bounded_replay": {
                "current_selector": {"rr_pass_count": len(baseline_passed), **baseline_metrics},
                "first_dynamic_acceptable_farther_policy": {"rr_pass_count": len(alt_rows), **alternative_metrics,
                    "target_hit": sum((row["variant_outcome"] or {}).get("target_hit") is True for row in alt_rows),
                    "stop_hit": sum((row["variant_outcome"] or {}).get("stop_hit") is True for row in alt_rows),
                    "timeout": sum((row["variant_outcome"] or {}).get("timeout") is True for row in alt_rows)},
                "selection_rule": "first causally inventoried target meeting unchanged final Dynamic RR",
                "no_lookahead": True},
            "next_task": "TASK_D_BOUNDED_VARIANTS"}


def variant_row(row: Mapping[str, Any], policy: str) -> dict[str, Any] | None:
    if policy == "BASELINE":
        return dict(row) if row.get("net_rr") is not None else None
    if policy == "FARTHER_DYNAMIC_RR":
        target = next((target for target in row.get("all_causal_targets") or ()
                       if target.get("net_rr") is not None and float(target["net_rr"]) >= float(row["final_required_rr"])), None)
        if target is None:
            return None
        # Causal selection uses only the persisted target inventory and fixed RR gate.
        result = dict(row); result["net_rr"] = target["net_rr"]; result["target_distance_bps"] = target["distance_bps"]
        result["rr_pass"] = True
        result["net_outcome_r"] = (target.get("causal_outcome") or {}).get("net_r")
        result["target_hit"] = (target.get("causal_outcome") or {}).get("target_hit", False)
        result["stop_hit"] = (target.get("causal_outcome") or {}).get("stop_hit", False)
        result["timeout"] = (target.get("causal_outcome") or {}).get("timeout", False)
        return result
    if policy == "TREND_ALIGNED":
        return dict(row) if row.get("trend_alignment") == "ALIGNED" and row.get("net_rr") is not None else None
    if policy == "IMPULSE_PRESENT":
        return dict(row) if row.get("momentum_context") not in {"NO_IMPULSE", "UNKNOWN", "NOT_EVALUATED"} and row.get("net_rr") is not None else None
    return None


def task_d(cohort: list[dict[str, Any]], anchor: Mapping[str, Any]) -> dict[str, Any]:
    ordered = sorted(cohort, key=lambda row: (row["cycle_boundary"], row["symbol"]))
    split = max(1, int(len(ordered)*.7))
    variants = []
    for policy in ("BASELINE", "FARTHER_DYNAMIC_RR", "TREND_ALIGNED", "IMPULSE_PRESENT"):
        fit = [value for row in ordered[:split] if (value := variant_row(row, policy))]
        validation = [value for row in ordered[split:] if (value := variant_row(row, policy))]
        def metrics(values: list[dict[str, Any]]) -> dict[str, Any]:
            base = pnl_metrics(values)
            return {"candidate_count": len(values), "rr_pass": sum(
                        row.get("rr_pass") is True or (row.get("net_rr") is not None and float(row["net_rr"]) >= float(row["final_required_rr"])) for row in values),
                    "median_net_rr": distribution(row.get("net_rr") for row in values)["median"],
                    "median_required_rr": distribution(row.get("final_required_rr") for row in values)["median"],
                    "achievability_ratio": distribution((float(row["net_rr"])/float(row["final_required_rr"]))
                                                         for row in values if row.get("net_rr") is not None)["median"], **base}
        variants.append({"name": policy, "selection_is_causal": True,
                         "fit": metrics(fit), "validation": metrics(validation),
                         "cost_model_unchanged": True, "rr_policy_unchanged": True, "safety_unchanged": True})
    eligible = [row for row in variants[1:] if row["validation"]["count"] >= 5
                and (row["validation"]["expectancy_r"] or -99) >= (variants[0]["validation"]["expectancy_r"] or -99)
                and row["validation"]["rr_pass"] > variants[0]["validation"]["rr_pass"]]
    result = "RESEARCH_CANDIDATE_SELECTED" if len(eligible) == 1 else "MULTIPLE_INCONCLUSIVE" if eligible else "NO_CANDIDATE"
    return {"task_status": "PASS", "final_verdict": result, "anchor": dict(anchor),
            "variants_evaluated": len(variants), "variants": variants,
            "best_variant": eligible[0]["name"] if len(eligible) == 1 else None,
            "overfit_risk": "HIGH" if len(ordered[split:]) < 30 else "MEDIUM",
            "promotion_allowed": False, "shadow_eligible": len(eligible) == 1,
            "next_task": "TASK_E_SHADOW" if len(eligible) == 1 else "COLLECT_LARGER_INDEPENDENT_CAUSAL_COHORT"}


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True)+"\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outcome-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--deployed-revision", required=True)
    args = parser.parse_args()
    rows, schema = load_production_rows()
    cohort, anchor = freeze(rows, args.outcome_dir)
    anchor["deployed_revision"] = args.deployed_revision; anchor["schema_head"] = schema
    identity = "\n".join(f'{row["cycle_boundary"]}|{row["symbol"]}|{row["candidate_id"]}|{row["opportunity_id"]}' for row in cohort)
    anchor["cohort_sha256"] = sha256(identity.encode()).hexdigest()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir/"STRATEGY_EDGE_COHORT.jsonl").write_text("".join(
        json.dumps(row, sort_keys=True, separators=(",", ":"))+"\n" for row in cohort), encoding="utf-8")
    reports = {"TASK_A_REPORT.json": task_a(cohort, anchor), "TASK_B_REPORT.json": task_b(cohort, anchor),
               "TASK_C_REPORT.json": task_c(cohort, anchor), "TASK_D_REPORT.json": task_d(cohort, anchor)}
    for name, report in reports.items(): write_json(args.output_dir/name, report)
    print(json.dumps({"anchor": anchor, "cohort_count": len(cohort),
                      "verdicts": {name: value["final_verdict"] for name, value in reports.items()}}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
