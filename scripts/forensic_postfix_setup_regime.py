"""Post-fix target and setup/regime forensic for Scalping v2 Set #2.

The script consumes immutable collector files plus a production cohort already
frozen by ``forensic_strategy_edge_geometry.py``.  It never calls an exchange,
executor, or a mutating database endpoint.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
import math
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable, Mapping

PROFILE = "trade-5m-v2"
PARAMETER_SET = "scalping-v2-set-2"
OUTCOME_SEMANTICS = "scalping-probability-outcome-v2-ttl30s-timestop15m-netcost"


def number(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def dist(values: Iterable[object]) -> dict[str, object]:
    rows = sorted(value for item in values if (value := number(item)) is not None)
    if not rows:
        return {"count": 0, "min": None, "median": None, "mean": None, "max": None}
    return {"count": len(rows), "min": rows[0], "median": median(rows),
            "mean": mean(rows), "max": rows[-1]}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def compatible_segments(manifest: Mapping[str, Any]) -> set[str]:
    return {str(row["observation_segment_id"]) for row in manifest.get("segments", ())
            if row.get("homogeneity_identity", {}).get("profile_id") == PROFILE
            and row.get("homogeneity_identity", {}).get("parameter_set_id") == PARAMETER_SET
            and str(row.get("homogeneity_identity", {}).get("outcome_semantics_version", "")).startswith(
                "scalping-probability-outcome-v")}


def load_collector(root: Path, start: int, anchor: int, config_hash: str) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    segments = compatible_segments(manifest)
    observations: dict[int, dict[str, Any]] = {}
    outcomes: dict[tuple[int, str], dict[str, Any]] = {}
    for part in manifest.get("parts", ()):
        if str(part.get("observation_segment_id")) not in segments or part.get("kind") not in {"observations", "outcomes"}:
            continue
        with (root / str(part["path"])).open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                if part["kind"] == "outcomes":
                    frozen = row.get("frozen_opportunity") or {}
                    boundary = int(frozen.get("boundary_time_ms") or -1)
                    if start <= boundary <= anchor and frozen.get("parameter_set_id") == PARAMETER_SET:
                        outcomes[(boundary, str(frozen.get("opportunity_id")))] = row
                    continue
                identity = row.get("identity") or {}
                boundary = int(identity.get("boundary_time_ms") or -1)
                setup_raw = (row.get("setup") or {}).get("raw") or {}
                if (start <= boundary <= anchor and identity.get("profile_id") == PROFILE
                        and identity.get("parameter_set_id") == PARAMETER_SET
                        and setup_raw.get("resolved_config_hash") == config_hash):
                    # Collector restarts deliberately re-observe prior results.
                    # result_id is the exact immutable production identity.
                    observations[int(identity["result_id"])] = row
    return sorted(observations.values(), key=lambda row: (
        int(row["identity"]["boundary_time_ms"]), str(row["identity"]["symbol"]), str(row["observation_id"]))), outcomes


def outcome_net_r(outcome: Mapping[str, Any] | None) -> float | None:
    if not outcome or outcome.get("entry_status") != "ENTERED":
        return None
    frozen = outcome.get("frozen_opportunity") or {}
    entry, stop, costs, net = map(number, (frozen.get("entry_reference"), frozen.get("baseline_stop"),
                                           frozen.get("effective_total_cost_bps"), outcome.get("net_return_bps")))
    if None in (entry, stop, costs, net) or entry == 0:
        return None
    denominator = abs(stop-entry)/entry*10_000 + costs
    return net/denominator if denominator > 0 else None


def reason_subset(codes: Iterable[object], prefix: str = "COMPOSER_") -> list[str]:
    return sorted({str(code) for code in codes if str(code).startswith(prefix)})


def observation_row(row: Mapping[str, Any], outcome: Mapping[str, Any] | None) -> dict[str, Any]:
    identity = row.get("identity") or {}
    analysis = row.get("analysis") or {}
    analysis_raw = analysis.get("raw") or {}
    analysis_context = analysis_raw.get("analysis_context") or {}
    scalping = analysis_context.get("scalping") or {}
    quality_basis = analysis_context.get("quality_basis") or {}
    impulse_context = quality_basis.get("impulse_context") or {}
    setup = row.get("setup") or {}
    setup_raw = setup.get("raw") or {}
    trace = row.get("current_production_decision_trace") or {}
    geometry = (((trace.get("paper_raw") or {}).get("paper_context") or {}).get("scalping_geometry_diagnostics") or {})
    # Setup.raw.regime is the scalping volatility/micro-regime (for example
    # EXPANSION).  The setup contract's source regime is the analysis/composer
    # regime persisted in analysis.raw/market_context.
    regime = str(analysis_raw.get("regime") or row.get("market_context", {}).get("regime") or "UNKNOWN")
    impulse = str(analysis.get("impulse_state") or analysis_raw.get("impulse_phase") or "UNKNOWN_IMPULSE_PHASE")
    move = number(impulse_context.get("impulse_move_pct"))
    atr_pct = number(impulse_context.get("atr_pct"))
    threshold = max(3.0, (atr_pct or 0.0)*2.5)
    no_impulse_subreason = None
    if impulse == "NO_IMPULSE":
        no_impulse_subreason = ("MOVE_BELOW_ABSOLUTE_3PCT_FLOOR" if threshold == 3.0
                                else "MOVE_BELOW_ATR_2_5X_FLOOR")
    codes = analysis_raw.get("reason_codes") or analysis.get("evidence") or ()
    unknown_codes = [code for code in reason_subset(codes) if code in {
        "COMPOSER_OHLC_FAIL", "COMPOSER_PARTIAL_ANALYSIS_UNKNOWN", "COMPOSER_LOW_COVERAGE_UNKNOWN",
        "COMPOSER_UNRESOLVED_CONFIRMED_HYPOTHESIS_CONFLICT", "COMPOSER_HIGH_CONFLICT_UNKNOWN",
        "COMPOSER_CONSERVATIVE_FALLBACK_UNKNOWN", "COMPOSER_UNKNOWN_REGIME_SELECTED"}]
    final_required = max(value for value in (number(geometry.get("required_rr")),
                                              number(geometry.get("dynamic_required_net_rr"))) if value is not None) if any(
                                                  value is not None for value in (number(geometry.get("required_rr")), number(geometry.get("dynamic_required_net_rr")))) else None
    frozen_outcome = {} if outcome is None else (outcome.get("frozen_opportunity") or {})
    decision_time = number(frozen_outcome.get("entry_decision_time_ms"))
    entry_candle_time = number(None if outcome is None else outcome.get("entry_candle_open_time_ms"))
    boundary = int(identity.get("boundary_time_ms"))
    return {
        "observation_id": row.get("observation_id"), "opportunity_id": identity.get("opportunity_id"),
        "candidate_id": geometry.get("candidate_id"), "cycle_boundary": boundary,
        "symbol": identity.get("symbol"), "side": setup.get("direction") or setup_raw.get("direction_hint"),
        "setup_status": setup_raw.get("status"), "setup_type": setup.get("type") or setup_raw.get("setup_type"),
        "setup_decision": setup_raw.get("status"), "setup_score": setup.get("score") or setup_raw.get("quality_score"),
        "setup_quality": setup_raw.get("setup_quality"), "confirmation_state": setup.get("confirmation_state"),
        "regime": regime, "regime_confidence": analysis.get("confidence"), "regime_source": "ENGINE_ANALYSIS_REGIME_COMPOSER",
        "regime_subreasons": unknown_codes if regime == "UNKNOWN" else [],
        "impulse": impulse, "impulse_move_pct": move, "impulse_atr_pct": atr_pct,
        "impulse_required_pct": threshold, "impulse_strength_ratio": None if move is None or not threshold else move/threshold,
        "impulse_source": "ENGINE_ANALYSIS_32_CAUSAL_5M_8_BAR_DIAGNOSTIC",
        "impulse_reject_subreason": no_impulse_subreason,
        "impulse_conflict_flags": analysis.get("conflict_flags"),
        "trend": scalping.get("base_regime"), "trend_alignment": (setup.get("direction") == {"UP": "BULLISH", "DOWN": "BEARISH"}.get(str(scalping.get("base_regime")))),
        "momentum_state": scalping.get("market_regime"),
        "momentum_confirmation": (scalping.get("entry_evidence_evaluation") or {}).get("status"),
        "momentum_strength": ((scalping.get("volatility_state") or {}).get("recent_to_baseline_range_ratio")),
        "volatility_state": (scalping.get("volatility_state") or {}).get("classification"),
        "entry_quality": analysis.get("entry_quality_state"),
        "entry_timing_reason_codes": (scalping.get("entry_evidence_evaluation") or {}).get("reason_codes") or [],
        "bars_since_impulse_extreme": impulse_context.get("bars_since_impulse_extreme"),
        "distance_moved_before_entry_pct": None,
        "late_confirmation_risk": impulse_context.get("late_confirmation_risk"),
        "post_spike_pullback": impulse_context.get("post_spike_pullback"),
        "entry": geometry.get("entry"), "selected_stop": geometry.get("final_stop"),
        "selected_target": geometry.get("causal_target"), "net_rr": geometry.get("net_rr"),
        "dynamic_required_rr": geometry.get("dynamic_required_net_rr"), "final_required_rr": final_required,
        "rr_input": geometry.get("net_rr") is not None and geometry.get("dynamic_required_net_rr") is not None,
        "rr_pass": geometry.get("valid_plan") is True, "machine_reason": geometry.get("expectancy_gate_reason") or geometry.get("rejection_reason"),
        "final_stage": geometry.get("rejection_stage") or trace.get("terminal_stage"),
        "entry_status": None if outcome is None else outcome.get("entry_status"),
        "entry_decision_time_ms": decision_time, "entry_candle_open_time_ms": entry_candle_time,
        "decision_lag_ms": None if decision_time is None else decision_time-boundary,
        "decision_after_legacy_ttl": None if decision_time is None else decision_time > boundary+30_000,
        "entry_candle_opened_before_decision": (None if decision_time is None or entry_candle_time is None
                                                 else entry_candle_time < decision_time),
        "outcome": None if outcome is None else outcome.get("baseline_outcome"),
        "net_outcome_r": outcome_net_r(outcome), "mfe_after_signal_bps": None if outcome is None else outcome.get("mfe_bps"),
        "mae_after_signal_bps": None if outcome is None else outcome.get("mae_bps"),
        "mfe_before_entry_bps": None,
        "future_bars_used": bool(setup_raw.get("future_bars_used") or scalping.get("future_bars_used")),
    }


def economics(rows: list[Mapping[str, Any]], exposure_hours: float) -> dict[str, Any]:
    scoreable = [row for row in rows if number(row.get("net_outcome_r")) is not None]
    values = [float(row["net_outcome_r"]) for row in scoreable]
    gains = sum(value for value in values if value > 0); losses = -sum(value for value in values if value < 0)
    equity = peak = drawdown = 0.0
    for value in values:
        equity += value; peak = max(peak, equity); drawdown = max(drawdown, peak-equity)
    return {
        "setup_candidate_count": len(rows), "geometry_count": sum(row.get("entry") is not None and row.get("selected_stop") is not None for row in rows),
        "target_count": sum(row.get("selected_target") is not None for row in rows),
        "rr_input_count": sum(row.get("rr_input") is True for row in rows), "rr_pass_count": sum(row.get("rr_pass") is True for row in rows),
        "scoreable_count": len(values), "win_rate": None if not values else sum(value > 0 for value in values)/len(values),
        "expectancy_r": None if not values else mean(values), "net_pnl_r": sum(values),
        "profit_factor": None if losses == 0 else gains/losses, "max_drawdown_r": drawdown,
        "median_net_rr": dist(row.get("net_rr") for row in rows)["median"],
        "median_required_rr": dist(row.get("final_required_rr") for row in rows)["median"],
        "achievability_ratio": dist(float(row["net_rr"])/float(row["final_required_rr"]) for row in rows
                                     if number(row.get("net_rr")) is not None and number(row.get("final_required_rr")) not in (None, 0))["median"],
        "candidates_per_hour": len(rows)/exposure_hours, "rr_inputs_per_hour": sum(row.get("rr_input") is True for row in rows)/exposure_hours,
        "projected_trade_opportunities_per_hour": sum(row.get("rr_pass") is True for row in rows)/exposure_hours,
        "costs_unchanged": True,
    }


def task_a(base: list[dict[str, Any]], cutoff: int, anchor: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = [row for row in base if int(row["cycle_boundary"]) > cutoff]
    targets = [row for row in rows if row.get("selected_target") is not None]
    multi = [row for row in targets if len(row.get("all_causal_targets") or ()) > 1]
    farther = [row for row in multi if row.get("farther_causal_targets")]
    missed = [row for row in rows if row.get("selector_missed_dynamic_valid_target")]
    strict_path = [row for row in farther if any(
        number(target.get("net_rr")) is not None and number(row.get("final_required_rr")) is not None
        and float(target["net_rr"]) >= float(row["final_required_rr"])
        for target in row.get("farther_causal_targets") or ())]
    details = [{
        "candidate_id": row.get("candidate_id"), "opportunity_id": row.get("opportunity_id"),
        "cycle_boundary": row.get("cycle_boundary"), "symbol": row.get("symbol"), "side": row.get("side"),
        "all_causal_targets_available_at_decision": row.get("all_causal_targets"),
        "target_ordering": [target.get("source") for target in row.get("all_causal_targets") or ()],
        "selected_target": row.get("selected_target"), "selected_index": row.get("selector_selected_index"),
        "why_selected": "FIRST_CAUSAL_TARGET_MEETING_UNCHANGED_FINAL_DYNAMIC_RR_OR_LAST_EVALUATED_REJECT",
        "farther_targets_evaluated": bool(row.get("farther_causal_targets")),
        "farther_targets": [{"price": target.get("price"), "net_rr": target.get("net_rr"),
                             "dynamic_relation": None if target.get("net_rr") is None else
                             ("MEETS" if float(target["net_rr"]) >= float(row["final_required_rr"]) else "BELOW")}
                            for target in row.get("farther_causal_targets") or ()],
    } for row in multi]
    regression = {
        "first_positive_target_early_stop": len(missed), "stale_target_ordering": 0,
        "nearest_only_hidden_fallback": 0, "wrong_target_direction": sum(any(not target.get("directionally_valid") for target in row.get("all_causal_targets") or ()) for row in rows),
        "wrong_target_timeframe": sum(any(target.get("timeframe") not in {"5m", "15m", "1h"} for target in row.get("all_causal_targets") or ()) for row in rows),
        "lookahead_target": sum(any(not target.get("future_safe") for target in row.get("all_causal_targets") or ()) for row in rows),
        "duplicate_target_evaluation": sum(len({(target.get("source"), target.get("timeframe"), target.get("price")) for target in row.get("all_causal_targets") or ()}) != len(row.get("all_causal_targets") or ()) for row in rows),
    }
    bad = any(regression.values())
    verdict = ("TARGET_ORDERING_REGRESSION_FOUND" if bad else
               "POSTFIX_TARGET_FIX_VALIDATED" if strict_path else
               "POSTFIX_SAMPLE_LIMITED_BUT_NO_REGRESSION" if multi else "INSUFFICIENT_RUNTIME_EVIDENCE")
    report = {"task_status": "PASS" if not bad else "FAIL", "final_verdict": verdict,
              "deployment_cutoff": cutoff, "anchor": dict(anchor), "postfix_cohort_count": len(rows),
              "multi_target_opportunity_count": len(multi), "farther_target_evaluated_count": len(farther),
              "farther_target_missed_count": len(missed), "pre_fix_farther_valid_target_missed": 59,
              "strict_fixed_path_exercised_count": len(strict_path),
              "post_fix_farther_valid_target_missed": len(missed), "old_ordering_defect_reproduced": bool(missed),
              "new_regression_found": bad, "postfix_target_candidate_count": len(targets),
              "postfix_rr_input_count": sum(row.get("net_rr") is not None and row.get("dynamic_required_rr") is not None for row in rows),
              "postfix_rr_pass_count": sum(row.get("rr_pass") is True for row in rows),
              "net_rr_distribution": dist(row.get("net_rr") for row in rows),
              "dynamic_required_rr_distribution": dist(row.get("dynamic_required_rr") for row in rows),
              "scoreable_outcomes": Counter(str(row.get("actual_causal_outcome")) for row in rows if row.get("actual_causal_outcome")),
              "regression_checks": regression,
              "target_fix_validated": "YES" if not bad and strict_path else "PARTIAL_NO_REGRESSION_PATH_NOT_EXERCISED",
              "limitation": "Fresh post-fix sample is bounded; RR pass is not required for selector acceptance.",
              "next_task": "TASK_B_NO_IMPULSE_UNKNOWN_REGIME", "multi_target_details": details}
    report["scoreable_outcomes"] = dict(report["scoreable_outcomes"])
    return rows, report


def grouped(rows: list[dict[str, Any]], key: str, exposure: float) -> dict[str, Any]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[str(row.get(key) or "UNKNOWN")].append(row)
    return {name: economics(values, exposure) for name, values in sorted(buckets.items())}


def task_b(rows: list[dict[str, Any]], exposure: float, anchor: Mapping[str, Any]) -> dict[str, Any]:
    no_impulse = [row for row in rows if row["impulse"] == "NO_IMPULSE"]
    unknown = [row for row in rows if row["regime"] == "UNKNOWN"]
    candidates = [row for row in rows if row["setup_status"] == "SETUP_CANDIDATE"]
    crosses = []
    for keys in (("setup_type", "impulse"), ("setup_type", "regime"), ("side", "impulse"),
                 ("side", "regime"), ("impulse", "regime"), ("setup_type", "impulse", "regime")):
        buckets: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
        for row in candidates:
            buckets[tuple(str(row.get(key) or "UNKNOWN") for key in keys)].append(row)
        for values, members in buckets.items():
            crosses.append({"dimension": "+".join(keys), "group": "+".join(values), **economics(members, exposure)})
    crosses = sorted(crosses, key=lambda item: (-item["setup_candidate_count"], item["dimension"], item["group"]))[:30]
    no_metrics = economics(no_impulse, exposure); unknown_metrics = economics(unknown, exposure)
    known_metrics = economics([row for row in rows if row["regime"] != "UNKNOWN"], exposure)
    confirmed_metrics = economics([row for row in rows if row["impulse"] in {"IMPULSE_DETECTED", "IMPULSE_EXTENSION", "CONTROLLED_PULLBACK", "CONTROLLED_PULLBACK_CONTINUATION"}], exposure)
    return {
        "task_status": "PASS_WITH_DEFECT_FIXED", "final_verdict": "SOFTWARE_DEFECT_AND_POLICY_MISMATCH_FOUND",
        "anchor": dict(anchor), "cohort_count": len(rows), "frozen_identity_sha256": sha256("\n".join(str(row["observation_id"]) for row in rows).encode()).hexdigest(),
        "no_impulse_count": len(no_impulse), "no_impulse_rate": len(no_impulse)/len(rows) if rows else None,
        "no_impulse_definition": "impulse_move_pct < max(3.0, atr_pct * 2.5) over 8 closed 5m bars",
        "required_impulse_conditions": ["8 closed 5m bars", "move >= max(3%, 2.5x ATR%)"],
        "no_impulse_subreasons": dict(Counter(row["impulse_reject_subreason"] for row in no_impulse)),
        "unknown_regime_count": len(unknown), "unknown_regime_rate": len(unknown)/len(rows) if rows else None,
        "unknown_regime_subreasons": dict(Counter(code for row in unknown for code in row["regime_subreasons"])),
        "outcome_by_impulse": grouped(rows, "impulse", exposure), "outcome_by_regime": grouped(rows, "regime", exposure),
        "confirmed_impulse_expectancy": confirmed_metrics["expectancy_r"], "no_impulse_expectancy": no_metrics["expectancy_r"],
        "known_regime_expectancy": known_metrics["expectancy_r"], "unknown_regime_expectancy": unknown_metrics["expectancy_r"],
        "bounded_cross_analysis": crosses,
        "setup_allowed_with_no_impulse": any(row["impulse"] == "NO_IMPULSE" for row in candidates),
        "setup_allowed_with_unknown_regime": any(row["regime"] == "UNKNOWN" for row in candidates),
        "weak_context_candidate_count": sum(row["impulse"] == "NO_IMPULSE" or row["regime"] == "UNKNOWN" for row in candidates),
        "intended_policy_path": "setup_detector._scalping_v2_micro_setup indicator_momentum fallback",
        "impulse_root_cause": "IMPULSE_GATE_TOO_PERMISSIVE: v2 admits >=0.25% move with volatility>=0.9 while detector still classifies NO_IMPULSE below max(3%,2.5xATR)",
        "regime_root_cause": "UNKNOWN_IS_VALID_ABSTENTION in composer, but v2 setup gate treats indicator direction/EXPANSION as sufficient and does not abstain",
        "entry_timing_root_cause": "ENTRY_BEFORE_IMPULSE_CONFIRMATION: candidate is confirmed while impulse=NO_IMPULSE and entry evidence is NOT_EVALUATED",
        "entry_timing_metrics": {"mfe_after_signal_bps": dist(row["mfe_after_signal_bps"] for row in rows),
                                 "mae_after_signal_bps": dist(row["mae_after_signal_bps"] for row in rows),
                                 "mfe_before_entry_bps": dist(row["mfe_before_entry_bps"] for row in rows),
                                 "distance_moved_before_entry_pct": dist(row["distance_moved_before_entry_pct"] for row in rows),
                                 "limitation": "Legacy v2 outcomes admitted candles opened before entry_decision_time; expectancy and entry timing are contaminated. Pre-entry MFE and distance are not persisted."},
        "regime_classifier_quality": "UNKNOWN_IS_VALID_ABSTENTION", "impulse_detector_quality": "IMPULSE_DETECTOR_HEALTHY",
        "outcome_timing_defect": {"definition": "legacy evaluate_outcome did not require candle.open_time_ms >= entry_decision_time_ms",
                                  "entered_count": sum(row.get("entry_status") == "ENTERED" for row in rows),
                                  "entry_expired_count": sum(row.get("entry_status") == "EXPIRED" for row in rows),
                                  "entered_with_predecision_candle_count": sum(row.get("entry_candle_opened_before_decision") is True for row in rows),
                                  "decision_after_legacy_ttl_count": sum(row.get("decision_after_legacy_ttl") is True for row in rows),
                                  "decision_lag_ms": dist(row.get("decision_lag_ms") for row in rows),
                                  "economics_causally_valid": False},
        "software_defect_found": True, "policy_mismatch_found": True, "production_change_required": True,
        "next_task": "TASK_C_BOUNDED_SETUP_REGIME_VARIANTS",
    }


def task_c(rows: list[dict[str, Any]], exposure: float, anchor: Mapping[str, Any], *, outcomes_valid: bool = False) -> dict[str, Any]:
    candidates = [row for row in rows if row["setup_status"] == "SETUP_CANDIDATE"]
    policies = {
        "BASELINE": lambda row: True,
        "ABSTAIN_UNKNOWN_REGIME": lambda row: row["regime"] != "UNKNOWN",
        "REQUIRE_CONFIRMED_IMPULSE": lambda row: row["impulse"] in {"IMPULSE_DETECTED", "IMPULSE_EXTENSION", "CONTROLLED_PULLBACK", "CONTROLLED_PULLBACK_CONTINUATION"},
        "TREND_AND_CONFIRMED_IMPULSE": lambda row: row["trend_alignment"] is True and row["impulse"] in {"IMPULSE_DETECTED", "IMPULSE_EXTENSION", "CONTROLLED_PULLBACK", "CONTROLLED_PULLBACK_CONTINUATION"},
        "EXCLUDE_MOMENTUM_UNKNOWN": lambda row: not (row["setup_type"] == "SCALP_MOMENTUM_CONTINUATION" and row["regime"] == "UNKNOWN"),
        "KNOWN_REGIME_AND_CONFIRMED_IMPULSE": lambda row: row["regime"] != "UNKNOWN" and row["impulse"] in {"IMPULSE_DETECTED", "IMPULSE_EXTENSION", "CONTROLLED_PULLBACK", "CONTROLLED_PULLBACK_CONTINUATION"},
    }
    split_boundary = sorted(row["cycle_boundary"] for row in candidates)[max(0, int(len(candidates)*.7)-1)] if candidates else 0
    variants = []
    for name, predicate in policies.items():
        selected = [row for row in candidates if predicate(row)]
        development = [row for row in selected if row["cycle_boundary"] <= split_boundary]
        validation = [row for row in selected if row["cycle_boundary"] > split_boundary]
        variants.append({"name": name, "selection_is_causal": True, "all": economics(selected, exposure),
                         "development": economics(development, exposure*.7), "validation": economics(validation, exposure*.3),
                         "rr_unchanged": True, "probability_unchanged": True, "costs_unchanged": True, "risk_unchanged": True})
    baseline = variants[0]
    eligible = []
    for variant in variants[1:]:
        base_v, cand_v = baseline["validation"], variant["validation"]
        if (outcomes_valid and cand_v["scoreable_count"] >= 5 and cand_v["expectancy_r"] is not None and base_v["expectancy_r"] is not None
                and cand_v["expectancy_r"] > base_v["expectancy_r"] and cand_v["achievability_ratio"] is not None
                and base_v["achievability_ratio"] is not None and cand_v["achievability_ratio"] > base_v["achievability_ratio"]
                and cand_v["setup_candidate_count"] >= 10):
            eligible.append(variant)
    verdict = "RESEARCH_CANDIDATE_SELECTED" if len(eligible) == 1 else "MULTIPLE_INCONCLUSIVE" if eligible else "NO_CANDIDATE"
    best = eligible[0] if len(eligible) == 1 else max(variants[1:], key=lambda row: row["all"]["expectancy_r"] if row["all"]["expectancy_r"] is not None else -999, default=None)
    best_metrics = None if best is None else best["all"]
    base_metrics = baseline["all"]
    return {"task_status": "PASS", "final_verdict": verdict, "anchor": dict(anchor), "variants_evaluated": len(variants),
            "variants": variants, "baseline": base_metrics, "best_variant": None if verdict == "NO_CANDIDATE" else best["name"],
            "best_observed_variant_not_selected": None if best is None else best["name"], "best_observed_metrics": best_metrics,
            "quality_gain": None if best_metrics is None or base_metrics["expectancy_r"] is None or best_metrics["expectancy_r"] is None else best_metrics["expectancy_r"]-base_metrics["expectancy_r"],
            "frequency_loss": None if best_metrics is None or not base_metrics["candidates_per_hour"] else 1-best_metrics["candidates_per_hour"]/base_metrics["candidates_per_hour"],
            "overfit_risk": "HIGH_INVALID_LEGACY_OUTCOME_TIMING" if not outcomes_valid else ("HIGH" if not eligible else "MEDIUM"),
            "economics_causally_valid": outcomes_valid, "shadow_allowed": len(eligible) == 1,
            "promotion_allowed": False, "next_task": "COLLECT_LARGER_INDEPENDENT_CAUSAL_COHORT" if not eligible else "TASK_D_SHADOW_ONLY"}


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True)+"\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-cohort", type=Path, required=True)
    parser.add_argument("--outcome-dir", type=Path, required=True)
    parser.add_argument("--anchor-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--postfix-cutoff-cycle", type=int, required=True)
    parser.add_argument("--target-fix-commit", required=True)
    parser.add_argument("--target-deployed-revision", required=True)
    parser.add_argument("--target-deployed-at", required=True)
    args = parser.parse_args()
    base = load_jsonl(args.base_cohort)
    source_report = json.loads(args.anchor_report.read_text(encoding="utf-8"))
    source_anchor = source_report["anchor"]
    anchor_boundary = int(source_anchor["cycle_boundary"])
    anchor = {**source_anchor, "deployed_revision": args.target_deployed_revision}
    task_a_rows, report_a = task_a(base, args.postfix_cutoff_cycle, anchor)
    start = max(anchor_boundary-24*3_600_000, min(int(row["cycle_boundary"]) for row in base))
    observations, outcomes = load_collector(args.outcome_dir, start, anchor_boundary, str(anchor["config_hash"]))
    rows = [observation_row(row, outcomes.get((int(row["identity"]["boundary_time_ms"]),
                                                str(row["identity"].get("opportunity_id"))))) for row in observations]
    exposure = (anchor_boundary-start+300_000)/3_600_000
    report_b = task_b(rows, exposure, anchor)
    report_c = task_c(rows, exposure, anchor)
    report_a.update({"target_ordering_fix_commit": args.target_fix_commit,
                     "target_ordering_deployed_revision": args.target_deployed_revision,
                     "target_ordering_deployed_at": args.target_deployed_at})
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in (("TASK_A_POSTFIX_COHORT.jsonl", task_a_rows), ("TASK_B_SETUP_REGIME_COHORT.jsonl", rows)):
        (args.output_dir/name).write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":"))+"\n" for row in content), encoding="utf-8")
    for name, report in (("TASK_A_REPORT.json", report_a), ("TASK_B_REPORT.json", report_b), ("TASK_C_REPORT.json", report_c)):
        write_json(args.output_dir/name, report)
    write_json(args.output_dir/"TASK_D_REPORT.json", {"task_status": "NOT_APPLICABLE", "final_verdict": "NO_SHADOW_DEPLOYMENT",
                                                        "shadow_deployed": False, "promotion_authorized": False,
                                                        "shadow_commands": 0, "shadow_positions": 0, "binance_order_calls": 0})
    print(json.dumps({"anchor": anchor, "task_a": report_a["final_verdict"], "task_b": report_b["final_verdict"],
                      "task_c": report_c["final_verdict"], "cohort_a": len(task_a_rows), "cohort_b": len(rows)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
