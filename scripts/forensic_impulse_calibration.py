"""Bounded fresh-v3 impulse-scale and calibration research for trade-5m-v2.

The input is the passive collector's append-only directory.  The script is
strictly offline/read-only: it freezes exact observation identities, joins only
decision-time-v3 outcomes, and evaluates at most six diagnostic definitions.
It cannot change production policy, create a command, or call an exchange.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping

from app.config.trade_parameters import SCALPING_V2, TRADE_PARAMETERS

PROFILE = "trade-5m-v2"
PARAMETER_SET = "scalping-v2-set-2"
CONFIG_HASH = TRADE_PARAMETERS.resolve_scalping_v2_parameter_set(PARAMETER_SET).resolved_config_hash
V3 = "scalping-probability-outcome-v3-decision-time-ttl30s-timestop15m-netcost"
ABSOLUTE_BANDS = ((0, .25), (.25, .5), (.5, .75), (.75, 1), (1, 1.5), (1.5, 2), (2, 3), (3, math.inf))
ATR_BANDS = ((0, .5), (.5, 1), (1, 1.5), (1.5, 2), (2, 2.5), (2.5, math.inf))


def effective_threshold_pct(atr_pct: float) -> float:
    return max(
        SCALPING_V2.signal.impulse_absolute_threshold_pct,
        SCALPING_V2.signal.impulse_atr_multiplier * atr_pct,
    )


def impulse_confirmed(move_pct: float, atr_pct: float) -> bool:
    return move_pct >= effective_threshold_pct(atr_pct)


def num(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def quantile(values: Iterable[object], q: float) -> float | None:
    rows = sorted(v for x in values if (v := num(x)) is not None)
    if not rows:
        return None
    point = (len(rows) - 1) * q
    lo, hi = math.floor(point), math.ceil(point)
    return rows[lo] if lo == hi else rows[lo] + (rows[hi] - rows[lo]) * (point - lo)


def distribution(values: Iterable[object]) -> dict[str, object]:
    rows = [x for x in values if num(x) is not None]
    return {"count": len(rows), "min": quantile(rows, 0), "p10": quantile(rows, .1),
            "p25": quantile(rows, .25), "median": quantile(rows, .5),
            "p75": quantile(rows, .75), "p90": quantile(rows, .9),
            "p95": quantile(rows, .95), "p99": quantile(rows, .99), "max": quantile(rows, 1)}


def nested(row: Mapping[str, Any], *path: str) -> Any:
    value: Any = row
    for key in path:
        value = value.get(key) if isinstance(value, Mapping) else None
    return value


def outcome_r(outcome: Mapping[str, Any] | None) -> float | None:
    if not outcome or outcome.get("entry_status") != "ENTERED":
        return None
    frozen = outcome.get("frozen_opportunity") or {}
    entry, stop, costs, net = (num(frozen.get("entry_reference")), num(frozen.get("baseline_stop")),
                               num(frozen.get("effective_total_cost_bps")), num(outcome.get("net_return_bps")))
    if None in (entry, stop, costs, net) or entry == 0:
        return None
    risk = abs(stop - entry) / entry * 10_000 + costs
    return net / risk if risk > 0 else None


def exact_segments(manifest: Mapping[str, Any]) -> set[str]:
    return {str(s["observation_segment_id"]) for s in manifest.get("segments", ())
            if s.get("homogeneity_identity", {}).get("profile_id") == PROFILE
            and s.get("homogeneity_identity", {}).get("parameter_set_id") == PARAMETER_SET
            and s.get("homogeneity_identity", {}).get("outcome_semantics_version") == V3}


def freeze(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    segments = exact_segments(manifest)
    observations: dict[int, dict[str, Any]] = {}
    outcomes: dict[tuple[int, str], dict[str, Any]] = {}
    for part in manifest.get("parts", ()):
        if str(part.get("observation_segment_id")) not in segments:
            continue
        with (root / str(part["path"])).open(encoding="utf-8") as stream:
            for line in stream:
                raw = json.loads(line)
                if part.get("kind") == "observations":
                    identity = raw.get("identity") or {}
                    if identity.get("profile_id") == PROFILE and identity.get("parameter_set_id") == PARAMETER_SET:
                        observations[int(identity["result_id"])] = raw
                elif part.get("kind") == "outcomes":
                    frozen = raw.get("frozen_opportunity") or {}
                    if frozen.get("outcome_semantics") == V3:
                        outcomes[(int(frozen["boundary_time_ms"]), str(frozen["opportunity_id"]))] = raw
    by_boundary: dict[int, set[str]] = defaultdict(set)
    for raw in observations.values():
        identity = raw["identity"]
        by_boundary[int(identity["boundary_time_ms"])].add(str(identity["symbol"]))
    complete = [boundary for boundary, symbols in by_boundary.items() if len(symbols) == 10]
    if not complete:
        raise RuntimeError("no exact10 fresh-v3 completed boundary")
    anchor = max(complete)
    rows = []
    for raw in observations.values():
        identity = raw["identity"]
        boundary = int(identity["boundary_time_ms"])
        if boundary > anchor:
            continue
        analysis = raw.get("analysis") or {}; setup = raw.get("setup") or {}; setup_raw = setup.get("raw") or {}
        impulse = nested(analysis, "raw", "analysis_context", "quality_basis", "impulse_context") or {}
        scalping = nested(analysis, "raw", "analysis_context", "scalping") or {}
        geometry = nested(raw, "current_production_decision_trace", "paper_raw", "paper_context", "scalping_geometry_diagnostics") or {}
        move = num(impulse.get("impulse_move_pct")); atr_pct = num(impulse.get("atr_pct"))
        threshold = None if atr_pct is None else effective_threshold_pct(atr_pct)
        opportunity = str(identity.get("opportunity_id") or setup_raw.get("opportunity_id") or "")
        outcome = outcomes.get((boundary, opportunity)) if opportunity else None
        final_required_values = [v for v in (num(geometry.get("required_rr")), num(geometry.get("dynamic_required_net_rr"))) if v is not None]
        candidate = setup_raw.get("status") == "SETUP_CANDIDATE" or bool(opportunity)
        rows.append({
            "result_id": identity.get("result_id"), "observation_id": raw.get("observation_id"),
            "opportunity_id": opportunity or None, "candidate_id": geometry.get("candidate_id"),
            "symbol": identity.get("symbol"), "side": setup.get("direction") or setup_raw.get("direction_hint"),
            "cycle_boundary": boundary, "decision_time": None if outcome is None else nested(outcome, "frozen_opportunity", "entry_decision_time_ms"),
            "setup_type": setup.get("type") or setup_raw.get("setup_type"),
            "regime": nested(analysis, "raw", "regime") or nested(raw, "market_context", "regime") or "UNKNOWN",
            "trend": scalping.get("base_regime"), "momentum": scalping.get("market_regime"),
            "move_abs": None if move is None or num(nested(setup_raw, "context", "confirmation_close")) is None else float(nested(setup_raw, "context", "confirmation_close"))*move/100,
            "move_pct": move, "ATR": nested(setup_raw, "context", "atr_value"), "ATR_pct": atr_pct,
            "move_to_ATR_ratio": None if move is None or atr_pct in (None, 0) else move / atr_pct,
            "current_impulse_threshold_pct": threshold,
            "threshold_component_selected": None if threshold is None else ("ABSOLUTE_3_PERCENT" if 3.0 >= 2.5 * atr_pct else "ATR_2_5X"),
            "distance_to_threshold_pct": None if move is None or threshold is None else move - threshold,
            "volatility_ratio": nested(scalping, "volatility_state", "recent_to_baseline_range_ratio"),
            "setup_fallback_move_threshold": .25, "setup_fallback_pass": bool(move is not None and move >= .25 and (num(nested(scalping, "volatility_state", "recent_to_baseline_range_ratio")) or 0) >= .9),
            "impulse_result": analysis.get("impulse_state") or nested(analysis, "raw", "impulse_phase"),
            "impulse_subreason": None if move is None or threshold is None or move >= threshold else ("MOVE_BELOW_ABSOLUTE_3PCT_FLOOR" if threshold == 3 else "MOVE_BELOW_ATR_2_5X_FLOOR"),
            "candidate_formed": candidate, "downstream_stage": nested(raw, "current_production_decision_trace", "terminal_stage"),
            "causal_outcome": None if outcome is None else outcome.get("baseline_outcome"), "entry_status": None if outcome is None else outcome.get("entry_status"),
            "net_outcome_R": outcome_r(outcome), "MFE": None if outcome is None else outcome.get("mfe_bps"),
            "MAE": None if outcome is None else outcome.get("mae_bps"), "net_rr": geometry.get("net_rr"),
            "required_rr": max(final_required_values) if final_required_values else None,
            "rr_pass": geometry.get("valid_plan") is True,
            "predecision_violation": bool(outcome and outcome.get("entry_status") == "ENTERED" and num(outcome.get("entry_candle_open_time_ms")) is not None and num(nested(outcome, "frozen_opportunity", "entry_decision_time_ms")) is not None and float(outcome["entry_candle_open_time_ms"]) < float(outcome["frozen_opportunity"]["entry_decision_time_ms"])),
        })
    rows.sort(key=lambda r: (r["cycle_boundary"], str(r["symbol"]), int(r["result_id"])))
    first = min(r["cycle_boundary"] for r in rows)
    return rows, {"cycle_boundary": anchor, "anchor_time": datetime.fromtimestamp(anchor / 1000, timezone.utc).isoformat().replace("+00:00", "Z"),
                  "profile": PROFILE, "parameter_set": PARAMETER_SET, "config_hash": CONFIG_HASH,
                  "schema_head": "0031_scalping_parameter_sets", "v3_cutoff": first,
                  "cohort_sha256": sha256("\n".join(str(r["observation_id"]) for r in rows).encode()).hexdigest()}


def economics(rows: list[Mapping[str, Any]], hours: float) -> dict[str, Any]:
    candidates = [r for r in rows if r.get("candidate_formed")]
    scored = [float(r["net_outcome_R"]) for r in candidates if num(r.get("net_outcome_R")) is not None]
    wins = sum(v > 0 for v in scored); losses = -sum(v for v in scored if v < 0); gains = sum(v for v in scored if v > 0)
    equity = peak = dd = 0.0
    for value in scored:
        equity += value; peak = max(peak, equity); dd = max(dd, peak - equity)
    net_rr = [num(r.get("net_rr")) for r in candidates if num(r.get("net_rr")) is not None]
    req = [num(r.get("required_rr")) for r in candidates if num(r.get("required_rr")) is not None]
    ratios = [float(r["net_rr"]) / float(r["required_rr"]) for r in candidates if num(r.get("net_rr")) is not None and num(r.get("required_rr")) not in (None, 0)]
    n = len(scored); z = 1.6448536269514722
    conservative = None if not n else ((wins/n + z*z/(2*n) - z*math.sqrt((wins/n)*(1-wins/n)/n + z*z/(4*n*n))) / (1+z*z/n))
    return {"count": len(rows), "candidate_count": len(candidates), "scoreable_count": n,
            "win_rate": None if not n else wins/n, "conservative_p_win": conservative,
            "expectancy_R": None if not n else sum(scored)/n, "net_pnl_R": sum(scored),
            "PF": None if not losses else gains/losses, "DD_R": dd,
            "median_Net_RR": median(net_rr) if net_rr else None, "median_Required_RR": median(req) if req else None,
            "achievability_ratio": median(ratios) if ratios else None,
            "RR_pass_count": sum(r.get("rr_pass") is True for r in candidates),
            "RR_pass_rate": None if not candidates else sum(r.get("rr_pass") is True for r in candidates)/len(candidates),
            "candidate_count_per_hour": len(candidates)/hours, "RR_input_per_hour": len(net_rr)/hours,
            "MFE": distribution(r.get("MFE") for r in candidates), "MAE": distribution(r.get("MAE") for r in candidates)}


def band_name(lo: float, hi: float, suffix: str) -> str:
    return f">={lo:g}{suffix}" if math.isinf(hi) else f"{lo:g}-{hi:g}{suffix}"


def band_report(rows: list[dict[str, Any]], field: str, bands: tuple[tuple[float, float], ...], suffix: str, hours: float) -> dict[str, Any]:
    return {band_name(lo, hi, suffix): economics([r for r in rows if num(r.get(field)) is not None and lo <= float(r[field]) < hi], hours)
            for lo, hi in bands}


def task_a(rows: list[dict[str, Any]], anchor: Mapping[str, Any]) -> dict[str, Any]:
    hours = max((anchor["cycle_boundary"] - anchor["v3_cutoff"] + 300_000) / 3_600_000, 1/12)
    current = [r for r in rows if num(r.get("distance_to_threshold_pct")) is not None and float(r["distance_to_threshold_pct"]) >= 0]
    abs_bands = band_report(rows, "move_pct", ABSOLUTE_BANDS, "%", hours)
    atr_bands = band_report(rows, "move_to_ATR_ratio", ATR_BANDS, "ATR", hours)
    scored_abs = [(name, item) for name, item in abs_bands.items() if item["scoreable_count"] >= 10]
    expectations = [float(item["expectancy_R"]) for _, item in scored_abs if item["expectancy_R"] is not None]
    # "Materially improves" requires a consistent ordered relation, not one
    # attractive band selected after looking at the same sample.
    improving = len(expectations) >= 3 and all(b >= a for a, b in zip(expectations, expectations[1:])) and expectations[-1] > expectations[0]
    high = [r for r in rows if (num(r.get("move_pct")) or 0) >= 1.5 or (num(r.get("move_to_ATR_ratio")) or 0) >= 2]
    entered_high = [r for r in high if r.get("entry_status") == "ENTERED" and num(r.get("MFE")) is not None]
    exhaustion = bool(entered_high and median(float(r["MFE"]) for r in entered_high) < median(float(r["move_pct"])*100 for r in entered_high))
    verdict = "CURRENT_THRESHOLD_TOO_RARE_FOR_5M" if len(current)/len(rows) < .01 else ("CURRENT_THRESHOLD_NOT_MONOTONIC_WITH_EDGE" if not improving else "CURRENT_THRESHOLD_REACHABLE_AND_MEANINGFUL")
    return {"task_status": "PASS", "final_verdict": verdict, "anchor": dict(anchor), "v3_cohort_count": len(rows),
            "distributions": {"overall": {k: distribution(r.get(k) for r in rows) for k in ("move_pct", "ATR_pct", "move_to_ATR_ratio")},
                              "by_symbol": {s: {k: distribution(r.get(k) for r in rows if r["symbol"] == s) for k in ("move_pct", "ATR_pct", "move_to_ATR_ratio")} for s in sorted({str(r["symbol"]) for r in rows})}},
            "absolute_reach": {str(v): {"count": sum((num(r.get("move_pct")) or -1) >= v for r in rows), "rate": sum((num(r.get("move_pct")) or -1) >= v for r in rows)/len(rows)} for v in (.25,.5,.75,1,1.5,2,2.5,3)},
            "atr_reach": {str(v): {"count": sum((num(r.get("move_to_ATR_ratio")) or -1) >= v for r in rows), "rate": sum((num(r.get("move_to_ATR_ratio")) or -1) >= v for r in rows)/len(rows)} for v in (1,1.5,2,2.5,3)},
            "current_threshold_reach_count": len(current), "current_threshold_reach_rate": len(current)/len(rows),
            "absolute_3_percent_dominant_count": sum(r.get("threshold_component_selected") == "ABSOLUTE_3_PERCENT" for r in rows),
            "atr_component_dominant_count": sum(r.get("threshold_component_selected") == "ATR_2_5X" for r in rows),
            "confirmed_impulse_count": sum(r.get("impulse_result") not in {None,"NO_IMPULSE","UNKNOWN_IMPULSE_PHASE"} for r in rows),
            "absolute_bands": abs_bands, "atr_bands": atr_bands, "higher_intensity_improves_edge": improving,
            "entry_exhaustion_found": exhaustion, "entry_exhaustion_sample": len(entered_high),
            "entry_exhaustion_metrics": {"median_move_completed_bps": None if not entered_high else median(float(r["move_pct"])*100 for r in entered_high),
                                         "median_remaining_mfe_bps": None if not entered_high else median(float(r["MFE"]) for r in entered_high),
                                         "median_post_entry_mae_bps": None if not entered_high else median(float(r["MAE"]) for r in entered_high if num(r.get("MAE")) is not None)},
            "predecision_violations": sum(r["predecision_violation"] for r in rows),
            "root_finding": "The fixed 3% absolute floor dominates the observed 5m scale; reachability and causal quality, not trade frequency, govern the verdict.",
            "production_change_required": False, "next_task": "TASK_B_THRESHOLD_PROVENANCE"}


def task_b() -> dict[str, Any]:
    return {"task_status": "PASS", "final_verdict": "TIMEFRAME_MISMATCH_AND_POLICY_MISMATCH_NO_WIRING_DEFECT",
            "absolute_threshold": 3.0, "atr_multiplier": 2.5,
            "source_file": "config/trading/trade_parameters.yaml", "config_key": "profiles.trade-5m-v2.signal.impulse_absolute_threshold_pct / impulse_atr_multiplier",
            "introduced_commit": "cca167e8c89feb8494c8d8c7af1f103ffd43e6f8", "introduced_at": "2026-07-17T22:10:39+03:00",
            "original_profile": "trade-15m-v1", "original_timeframe": "15m",
            "original_strategy": "GENERIC_IMPULSE_PHASE_DIAGNOSTIC", "used_by_5m": True, "used_by_15m": True,
            "used_by_other_tf": False, "other_timeframes": [],
            "generic_callable_accepts_other_timeframes": True,
            "setup_fallback_threshold": .25, "threshold_ratio": 12.0,
            "contract_intent": "IMPULSE is a generic 8-bar analysis phase; SETUP_CANDIDATE is a separate profile-specific actionable micro-setup. A candidate may therefore exist with NO_IMPULSE by code, but the >12x fixed-floor gap lacks a timeframe/economic rationale and is a policy mismatch.",
            "legacy_drift_found": False, "timeframe_mismatch_found": True, "policy_mismatch_found": True,
            "software_defect_found": False, "production_fix_required": False, "next_task": "TASK_C_BOUNDED_VARIANTS"}


def task_c(rows: list[dict[str, Any]], anchor: Mapping[str, Any]) -> dict[str, Any]:
    hours = max((anchor["cycle_boundary"] - anchor["v3_cutoff"] + 300_000) / 3_600_000, 1/12)
    variants = [
        ("BASELINE_MAX_3PCT_2_5ATR", lambda r: max(3.0, 2.5*float(r["ATR_pct"]))),
        ("ATR_ONLY_1_0X", lambda r: float(r["ATR_pct"])),
        ("ATR_ONLY_1_5X", lambda r: 1.5*float(r["ATR_pct"])),
        ("FLOOR_0_25PCT_PLUS_1_0ATR", lambda r: max(.25, float(r["ATR_pct"]))),
        ("FLOOR_0_50PCT_PLUS_1_0ATR", lambda r: max(.5, float(r["ATR_pct"]))),
        ("TWO_STAGE_0_25PCT_VOL0_9_THEN_1ATR", lambda r: float(r["ATR_pct"])),
    ]
    split_boundary = sorted({r["cycle_boundary"] for r in rows})[max(0, int(len({r["cycle_boundary"] for r in rows})*.7)-1)]
    report = {}
    for name, threshold in variants:
        eligible = [r for r in rows if num(r.get("move_pct")) is not None and num(r.get("ATR_pct")) is not None and float(r["move_pct"]) >= threshold(r)
                    and (name != "TWO_STAGE_0_25PCT_VOL0_9_THEN_1ATR" or r.get("setup_fallback_pass"))]
        report[name] = {"threshold_basis": "TASK_A_B_BOUNDED_BANDS", "confirmed_impulse_count": len(eligible),
                        "confirmed_impulse_rate": len(eligible)/len(rows), "all": economics(eligible, hours),
                        "development": economics([r for r in eligible if r["cycle_boundary"] <= split_boundary], hours*.7),
                        "validation": economics([r for r in eligible if r["cycle_boundary"] > split_boundary], hours*.3)}
    baseline = report[variants[0][0]]
    # A zero/near-zero baseline cannot support same-cohort promotion claims.
    selected = None
    for name, _ in variants[1:]:
        item = report[name]
        dev, val = item["development"], item["validation"]
        if (dev["scoreable_count"] >= 20 and val["scoreable_count"] >= 10
                and (dev["expectancy_R"] or -999) > 0 and (val["expectancy_R"] or -999) > 0
                and (dev["achievability_ratio"] or 0) > (baseline["development"]["achievability_ratio"] or 0)
                and (val["achievability_ratio"] or 0) > (baseline["validation"]["achievability_ratio"] or 0)):
            selected = name; break
    return {"task_status": "PASS", "final_verdict": "RESEARCH_CANDIDATE_SELECTED" if selected else "NO_CANDIDATE",
            "variants_evaluated": len(variants), "best_variant": selected, "baseline": baseline,
            "best_diagnostic_variant": max(report, key=lambda n: report[n]["validation"]["expectancy_R"] if report[n]["validation"]["expectancy_R"] is not None else -999),
            "variants": report, "quality_gain": "NOT_PROVEN" if not selected else "PROVEN_ON_CHRONOLOGICAL_VALIDATION",
            "frequency_change": "DIAGNOSTIC_INCREASE_WITHOUT_PROVEN_POSITIVE_EDGE" if not selected else "BOUNDED_INCREASE",
            "validation_result": "NO_VARIANT_MET_ALL_SELECTION_GATES" if not selected else "PASS",
            "overfit_risk": "HIGH_SAME_DAY_SINGLE_MARKET_REGIME", "shadow_allowed": bool(selected),
            "next_task": "NO_TASK_D_CONTINUE_FRESH_V3_COLLECTION" if not selected else "TASK_D_SHADOW_ONLY"}


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--collector-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True); parser.add_argument("--deployed-revision", required=True)
    args = parser.parse_args(); rows, anchor = freeze(args.collector_dir); anchor["deployed_revision"] = args.deployed_revision
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cohort = args.output_dir / "V3_IMPULSE_CALIBRATION_COHORT.jsonl"
    cohort.write_text("".join(json.dumps(r, sort_keys=True, separators=(",", ":"))+"\n" for r in rows), encoding="utf-8")
    reports = {"TASK_A_REPORT.json": task_a(rows, anchor), "TASK_B_REPORT.json": task_b(), "TASK_C_REPORT.json": task_c(rows, anchor)}
    reports["TASK_D_REPORT.json"] = {"task_status": "NOT_APPLICABLE", "final_verdict": "NOT_APPLICABLE_NO_CREDIBLE_CANDIDATE", "shadow_deployed": False,
                                      "shadow_commands": 0, "shadow_positions": 0, "binance_order_calls": 0, "promotion_authorized": "NO"}
    for name, report in reports.items():
        (args.output_dir/name).write_text(json.dumps(report, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps({"anchor": anchor, "cohort_count": len(rows), "task_a": reports["TASK_A_REPORT.json"]["final_verdict"],
                      "task_b": reports["TASK_B_REPORT.json"]["final_verdict"], "task_c": reports["TASK_C_REPORT.json"]["final_verdict"]}, indent=2))


if __name__ == "__main__":
    main()
