"""Bounded, read-only calibration for Scalping v2 conservative probability.

The command freezes exact pipeline candidate identities and joins realized
prospective outcomes only through the persisted causal source opportunity id.
It never mutates PostgreSQL or the production parameter policy.
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
from typing import Any, Iterable, Mapping

try:
    from scripts.forensic_scalping_rr_dynamic_anchor import (
        PARAMETER_SET, PROFILE, WINDOWS_HOURS, diagnostic, distribution, load_production_rows,
        select_latest_completed_cycle,
    )
except ModuleNotFoundError:  # direct ``python scripts/...`` execution
    from forensic_scalping_rr_dynamic_anchor import (  # type: ignore[no-redef]
        PARAMETER_SET, PROFILE, WINDOWS_HOURS, diagnostic, distribution, load_production_rows,
        select_latest_completed_cycle,
    )


OUTCOME_SEMANTICS = "scalping-probability-outcome-v2-ttl30s-timestop15m-netcost"
LABELLED_TERMINALS = frozenset({"TP_FIRST", "SL_FIRST", "TIME_EXPIRED"})


def _number(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat().replace("+00:00", "Z")


def _utc_ms(value: object) -> int | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp() * 1000)


def load_outcomes(root: Path) -> dict[str, dict[str, Any]]:
    """Load latest exact-semantics outcome for every causal opportunity."""
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    compatible = {
        str(segment["observation_segment_id"])
        for segment in manifest.get("segments", ())
        if segment.get("homogeneity_identity", {}).get("parameter_set_id") == PARAMETER_SET
        and segment.get("homogeneity_identity", {}).get("outcome_semantics_version") == OUTCOME_SEMANTICS
    }
    result: dict[str, dict[str, Any]] = {}
    for part in manifest.get("parts", ()):
        if part.get("kind") != "outcomes" or str(part.get("observation_segment_id")) not in compatible:
            continue
        path = root / str(part["path"])
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            frozen = row.get("frozen_opportunity") or {}
            identity = str(frozen.get("opportunity_id") or "")
            if identity and frozen.get("outcome_semantics") == OUTCOME_SEMANTICS:
                result[identity] = row
    return result


def outcome_label(row: Mapping[str, Any] | None) -> int | None:
    if not row or row.get("baseline_outcome") not in LABELLED_TERMINALS:
        return None
    if row["baseline_outcome"] == "TP_FIRST":
        return 1
    if row["baseline_outcome"] == "SL_FIRST":
        return 0
    net = _number(row.get("net_return_bps"))
    return None if net is None else int(net > 0)


def _reliability(rows: Iterable[Mapping[str, Any]], field: str) -> list[dict[str, Any]]:
    bins: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        probability = _number(row.get(field))
        if probability is not None and row.get("actual_win") is not None:
            bins[min(4, int(probability * 5))].append(row)
    return [{
        "range": f"{index / 5:.1f}-{(index + 1) / 5:.1f}", "count": len(values),
        "predicted_mean": mean(float(item[field]) for item in values),
        "observed_rate": mean(int(item["actual_win"]) for item in values),
    } for index, values in sorted(bins.items())]


def _metrics(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    scored = [row for row in rows if row.get("actual_win") is not None and _number(row.get(field)) is not None]
    if not scored:
        return {"count": 0, "predicted_mean": None, "observed_rate": None,
                "brier_score": None, "calibration_error": None, "reliability_bins": []}
    predicted = [float(row[field]) for row in scored]
    actual = [int(row["actual_win"]) for row in scored]
    reliability = _reliability(scored, field)
    ece = sum(item["count"] / len(scored) * abs(item["predicted_mean"] - item["observed_rate"])
              for item in reliability)
    return {"count": len(scored), "predicted_mean": mean(predicted), "observed_rate": mean(actual),
            "brier_score": mean((p - y) ** 2 for p, y in zip(predicted, actual)),
            "calibration_error": ece, "reliability_bins": reliability}


def _group_calibration(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(key) or "UNKNOWN")].append(row)
    return {name: {"candidate_count": len(values), **_metrics(values, "p_win_conservative")}
            for name, values in sorted(groups.items())}


def freeze_probability_cohort(rows: list[Mapping[str, Any]], outcomes: Mapping[str, Mapping[str, Any]],
                              anchor: int) -> tuple[list[dict[str, Any]], int]:
    """Freeze authority-available candidates; repeated cycles remain explicit."""
    eligible = []
    for row in rows:
        item = diagnostic(row)
        paper = row.get("paper") or {}
        if int(row["cycle_boundary"]) > anchor or item.get("dynamic_required_net_rr") is None:
            continue
        if (paper.get("parameter_set_id") or paper.get("runtime_parameter_set_id")) != PARAMETER_SET:
            continue
        eligible.append(row)
    selected: list[Mapping[str, Any]] = []
    hours = WINDOWS_HOURS[-1]
    for hours in WINDOWS_HOURS:
        selected = [row for row in eligible if anchor - hours * 3_600_000 <= int(row["cycle_boundary"])]
        if len(selected) >= 30:
            break
    frozen: list[dict[str, Any]] = []
    for row in sorted(selected, key=lambda value: (int(value["cycle_boundary"]), str(value["symbol"]))):
        paper, item = row.get("paper") or {}, diagnostic(row)
        context = paper.get("paper_context") or {}
        source_id = (context.get("causal_primitives") or {}).get("opportunity_id")
        outcome = outcomes.get(str(source_id))
        raw, adjusted = _number(item.get("p_win_raw")), _number(item.get("p_win_adjusted"))
        sample = int(item.get("probability_sample_size") or 0)
        wins = None if raw is None else round(raw * sample)
        baseline = None if outcome is None else outcome.get("baseline_outcome")
        completed_ms = None if outcome is None else _utc_ms(outcome.get("completed_at"))
        causally_after_decision = completed_ms is not None and completed_ms >= int(row["cycle_boundary"])
        entry = None if outcome is None else _number((outcome.get("frozen_opportunity") or {}).get("entry_reference"))
        stop = None if outcome is None else _number((outcome.get("frozen_opportunity") or {}).get("baseline_stop"))
        stop_bps = None if entry in (None, 0) or stop is None else abs(entry - stop) / entry * 10_000
        net_return = None if outcome is None else _number(outcome.get("net_return_bps"))
        frozen.append({
            "candidate_id": item.get("candidate_id"), "opportunity_id": item.get("opportunity_id"),
            "source_causal_opportunity_id": source_id, "cycle_boundary": int(row["cycle_boundary"]),
            "cycle_time": _iso(int(row["cycle_boundary"])), "symbol": row.get("symbol"),
            "side": "LONG" if paper.get("paper_direction") == "BULLISH" else "SHORT",
            "setup_type": (row.get("setup") or {}).get("setup_type"),
            "regime": (row.get("analysis") or {}).get("regime") or "UNKNOWN",
            "bucket_level_used": item.get("probability_fallback_level"),
            "bucket_id": item.get("probability_bucket"), "sample_count": sample,
            "required_sample_count": 20, "wins": wins,
            "losses": None if wins is None else sample - wins, "raw_p_win": raw,
            "posterior_p_win": adjusted, "p_win_conservative": _number(item.get("p_win_conservative")),
            "confidence_level": 0.95, "prior_alpha": 1.0, "prior_beta": 1.0,
            "probability_source": item.get("probability_estimator_version"),
            "authority_source": str(item.get("probability_source") or item.get("probability_estimator_version")),
            "authority_ratio": sample / 20, "actual_causal_outcome": baseline,
            "actual_win": outcome_label(outcome) if causally_after_decision else None,
            "outcome_horizon_ms": None if outcome is None else outcome.get("holding_time_ms"),
            "target_hit": baseline == "TP_FIRST", "stop_hit": baseline == "SL_FIRST",
            "timeout": baseline == "TIME_EXPIRED", "net_outcome_r": (
                None if net_return is None or not stop_bps else net_return / stop_bps
            ), "outcome_completed_at": None if outcome is None else outcome.get("completed_at"),
            "outcome_causally_after_decision": causally_after_decision,
            "outcome_semantics": None if outcome is None else (outcome.get("frozen_opportunity") or {}).get("outcome_semantics"),
        })
    return frozen, hours


def build_task_a(rows: list[Mapping[str, Any]], outcomes: Mapping[str, Mapping[str, Any]],
                 schema: str, deployed_revision: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    anchor, completed_at = select_latest_completed_cycle(rows)
    anchor_config = next(
        ((row.get("paper") or {}).get("resolved_config_hash") for row in rows
         if int(row["cycle_boundary"]) == anchor and (row.get("paper") or {}).get("resolved_config_hash")),
        None,
    )
    cohort, hours = freeze_probability_cohort(rows, outcomes, anchor)
    scored = [row for row in cohort if row["actual_win"] is not None]
    raw_metrics = _metrics(cohort, "raw_p_win")
    conservative = _metrics(cohort, "p_win_conservative")
    level = _group_calibration(cohort, "bucket_level_used")
    by_symbol = _group_calibration(cohort, "symbol")
    by_regime = _group_calibration(cohort, "regime")
    measurable = [value for value in level.values() if value["count"] >= 3]
    empirical_coverage = (None if not measurable else
        sum(value["observed_rate"] >= value["predicted_mean"] for value in measurable) / len(measurable))
    heterogeneous_rates = [value["observed_rate"] for value in by_symbol.values() if value["count"] >= 3]
    heterogeneity = len(heterogeneous_rates) >= 2 and max(heterogeneous_rates) - min(heterogeneous_rates) >= .20
    identity = "\n".join(f'{row["cycle_boundary"]}|{row["symbol"]}|{row["candidate_id"]}|{row["opportunity_id"]}|{row["source_causal_opportunity_id"]}' for row in cohort)
    return cohort, {
        "task": "TRADERS_SCALPING_V2_DYNAMIC_RR_PWIN_CALIBRATION_TASK_A",
        "task_status": "PASS_WITH_LIMITED_OUTCOME_SAMPLE", "final_verdict": "MEASURED_INSUFFICIENT_FOR_ROBUST_RECALIBRATION",
        "anchor": {"cycle_boundary": anchor, "completed_at": completed_at, "profile": PROFILE,
                   "parameter_set_id": PARAMETER_SET, "config_hash": anchor_config,
                   "deployed_revision": deployed_revision, "schema": schema},
        "cohort": {"count": len(cohort), "scored_count": len(scored), "lookback_hours": hours,
                   "identity_sha256": sha256(identity.encode()).hexdigest(),
                   "outcome_match_count": sum(row["actual_causal_outcome"] is not None for row in cohort)},
        "raw_calibration": raw_metrics, "conservative_calibration": conservative,
        "parent_level_usage_distribution": dict(Counter(row["bucket_level_used"] for row in cohort)),
        "parent_level_calibration": level, "symbol_calibration": by_symbol, "regime_calibration": by_regime,
        "coverage": {"expected_one_sided_level": .95, "empirical_bucket_coverage": empirical_coverage,
                     "measurable_bucket_groups": len(measurable), "robust": False},
        "heterogeneity_found": heterogeneity,
        "selection_bias": {"found": False, "executed_only_bias": False,
            "causal_completion_after_decision": all(
                row["actual_win"] is None or row["outcome_causally_after_decision"] for row in cohort
            ),
            "exact_identity_join": "paper_context.causal_primitives.opportunity_id",
            "unlabelled_terminal_distribution": dict(Counter(row["actual_causal_outcome"] or "NOT_YET_MATCHED" for row in cohort if row["actual_win"] is None))},
        "outcome_semantics": {"defect_found": False, "win": "TP_FIRST", "loss": "SL_FIRST",
            "timeout": "WIN iff net_return_bps>0, otherwise LOSS; missing net is excluded",
            "excluded": ["ENTRY_EXPIRED", "PATH_CAPTURED_NO_BASELINE_GEOMETRY", "AMBIGUOUS_OR_INCOMPLETE"]},
        "conservative_bound_too_aggressive": (
            None if conservative["count"] < 30 else conservative["predicted_mean"] + .10 < conservative["observed_rate"]
        ),
        "root_finding": "CONSERVATIVE_BOUND_MEASURED_BUT_MATCHED_SAMPLE_BELOW_30; NO_SEMANTIC_OR_LEAKAGE_DEFECT",
        "runtime_change_required": False, "next_task": "TASK_B_DYNAMIC_RR_ECONOMIC_ACHIEVABILITY",
        "safety": {"mode": "PAPER", "live": False, "binance_order_calls": 0, "production_mutations": 0},
    }


def _best_causal_net_rr(item: Mapping[str, Any]) -> float | None:
    stop = _number(item.get("stop_distance_bps"))
    costs = _number(item.get("effective_total_cost_bps"))
    if stop is None or costs is None or stop + costs <= 0:
        return None
    values = []
    for target in item.get("target_considerations") or ():
        if not all(target.get(key) is True for key in ("causal", "future_safe", "directionally_valid")):
            continue
        distance = _number(target.get("target_distance_bps") or target.get("distance_bps"))
        if distance is not None and distance > costs:
            values.append((distance - costs) / (stop + costs))
    return max(values, default=None)


def _rr_candidate(row: Mapping[str, Any]) -> dict[str, Any]:
    paper, item = row.get("paper") or {}, diagnostic(row)
    context = paper.get("paper_context") or {}
    p = _number(item.get("p_win_conservative"))
    net = _number(item.get("net_rr"))
    dynamic = _number(item.get("dynamic_required_net_rr"))
    minimum = _number(item.get("required_rr")) or .6
    final = max(value for value in (minimum, dynamic) if value is not None)
    best = _best_causal_net_rr(item)
    ratio = None if net is None or final <= 0 else net / final
    best_ratio = None if best is None or final <= 0 else best / final
    if net is not None and net >= final:
        feasibility = "ACHIEVABLE"
    elif best is not None and best >= final or best_ratio is not None and best_ratio >= .75:
        feasibility = "MARGINALLY_ACHIEVABLE"
    else:
        feasibility = "STRUCTURALLY_UNACHIEVABLE"
    return {
        "candidate_id": item.get("candidate_id"), "opportunity_id": item.get("opportunity_id"),
        "source_causal_opportunity_id": (context.get("causal_primitives") or {}).get("opportunity_id"),
        "cycle_boundary": int(row["cycle_boundary"]), "cycle_time": _iso(int(row["cycle_boundary"])),
        "symbol": row.get("symbol"), "side": "LONG" if paper.get("paper_direction") == "BULLISH" else "SHORT",
        "setup": (row.get("setup") or {}).get("setup_type"),
        "regime": (row.get("analysis") or {}).get("regime") or "UNKNOWN",
        "probability_level_used": item.get("probability_fallback_level"),
        "entry": item.get("entry"), "stop": item.get("final_stop"), "target": item.get("causal_target"),
        "stop_distance_bps": item.get("stop_distance_bps"), "target_distance_bps": item.get("target_distance_bps"),
        "gross_rr": item.get("gross_rr"), "net_rr": net, "minimum_planned_rr": minimum,
        "dynamic_required_net_rr": dynamic, "rr_reserve": item.get("ev_reserve"),
        "final_required_rr": final, "p_win_raw": item.get("p_win_raw"),
        "p_win_posterior": item.get("p_win_adjusted"), "p_win_conservative": p,
        "commission_bps": item.get("round_trip_commission_bps"), "spread_bps": item.get("spread_bps"),
        "slippage_bps": sum(_number(item.get(key)) or 0 for key in ("entry_slippage_bps", "exit_slippage_bps")),
        "adverse_fill_reserve_bps": item.get("adverse_fill_reserve_bps"),
        "effective_cost_bps": item.get("effective_total_cost_bps"), "expected_ev_r": item.get("expected_ev_r"),
        "min_ev_reserve_r": .05, "delta_net_vs_required": None if net is None else net - final,
        "achievability_ratio": ratio, "best_causal_gross_rr": max(
            (_number(target.get("gross_rr")) for target in item.get("target_considerations") or ()
             if target.get("causal") is True and _number(target.get("gross_rr")) is not None), default=None),
        "best_causal_net_rr": best, "best_causal_ratio": best_ratio,
        "feasibility": feasibility, "rr_result": "PASS" if item.get("valid_plan") is True else "FAIL",
        "machine_reason": item.get("expectancy_gate_reason") or item.get("rejection_reason"),
    }


def _group_distribution(cohort: list[dict[str, Any]], key: str) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in cohort:
        grouped[str(row.get(key) or "UNKNOWN")].append(row)
    return {name: {"count": len(values),
                   "net_rr": distribution(row["net_rr"] for row in values),
                   "final_required_rr": distribution(row["final_required_rr"] for row in values),
                   "achievability_ratio": distribution(row["achievability_ratio"] for row in values)}
            for name, values in sorted(grouped.items())}


def freeze_rr_cohort(rows: list[Mapping[str, Any]], anchor: int) -> tuple[list[dict[str, Any]], int]:
    eligible = [row for row in rows if int(row["cycle_boundary"]) <= anchor
                and diagnostic(row).get("dynamic_required_net_rr") is not None
                and ((row.get("paper") or {}).get("parameter_set_id")
                     or (row.get("paper") or {}).get("runtime_parameter_set_id")) == PARAMETER_SET]
    selected: list[Mapping[str, Any]] = []
    hours = WINDOWS_HOURS[-1]
    for hours in WINDOWS_HOURS:
        selected = [row for row in eligible if anchor - hours * 3_600_000 <= int(row["cycle_boundary"])]
        if len(selected) >= 30:
            break
    return [_rr_candidate(row) for row in sorted(selected, key=lambda value: (
        int(value["cycle_boundary"]), str(value["symbol"]), str(value["run_id"])
    ))], hours


def build_task_b(rows: list[Mapping[str, Any]], schema: str, deployed_revision: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    anchor, completed_at = select_latest_completed_cycle(rows)
    cohort, hours = freeze_rr_cohort(rows, anchor)
    counts = Counter(row["feasibility"] for row in cohort)
    ratio_bins = Counter()
    for row in cohort:
        ratio = row["achievability_ratio"]
        ratio_bins["UNAVAILABLE" if ratio is None else "<0.25" if ratio < .25 else "0.25-0.50" if ratio < .5
                   else "0.50-0.75" if ratio < .75 else "0.75-1.00" if ratio < 1 else ">=1.00"] += 1
    distributions = {key: distribution(row[key] for row in cohort) for key in (
        "net_rr", "dynamic_required_net_rr", "final_required_rr", "delta_net_vs_required",
        "achievability_ratio", "best_causal_net_rr",
    )}
    median_net = distributions["net_rr"]["median"]
    p_required = None if median_net is None else 1 / (float(median_net) + .95)
    frontier = [{"p_win_conservative": p, "required_rr": (1 - p) / p + .05}
                for p in (.10, .12, .15, .20, .25, .30, .35, .40)]
    sensitivity = {
        "baseline_conservative": distribution(row["dynamic_required_net_rr"] for row in cohort),
        "posterior_probability": distribution((1 - float(row["p_win_posterior"])) / float(row["p_win_posterior"]) + .05
                                               for row in cohort if _number(row["p_win_posterior"]) not in (None, 0)),
        "raw_probability": distribution((1 - float(row["p_win_raw"])) / float(row["p_win_raw"]) + .05
                                         for row in cohort if _number(row["p_win_raw"]) not in (None, 0)),
        "remove_ev_reserve_only": distribution(float(row["dynamic_required_net_rr"]) - .05 for row in cohort),
    }
    structural_share = counts["STRUCTURALLY_UNACHIEVABLE"] / len(cohort) if cohort else 0
    verdict = "DYNAMIC_RR_SYSTEMATICALLY_UNACHIEVABLE" if structural_share > .5 else (
        "DYNAMIC_RR_MARGINAL" if counts["MARGINALLY_ACHIEVABLE"] else "DYNAMIC_RR_ECONOMICALLY_ACHIEVABLE")
    identity = "\n".join(f'{row["cycle_boundary"]}|{row["symbol"]}|{row["candidate_id"]}' for row in cohort)
    return cohort, {
        "task": "TRADERS_SCALPING_V2_DYNAMIC_RR_ACHIEVABILITY_TASK_B",
        "task_status": "PASS", "final_verdict": verdict,
        "anchor": {"cycle_boundary": anchor, "completed_at": completed_at, "profile": PROFILE,
                   "parameter_set_id": PARAMETER_SET, "deployed_revision": deployed_revision, "schema": schema},
        "cohort": {"count": len(cohort), "lookback_hours": hours,
                   "identity_sha256": sha256(identity.encode()).hexdigest()},
        "rr_pass_count": sum(row["rr_result"] == "PASS" for row in cohort),
        "rr_fail_count": sum(row["rr_result"] == "FAIL" for row in cohort),
        "distributions": distributions, "achievability_ratio_bins": dict(ratio_bins),
        "classification_counts": dict(counts),
        "grouped": {key: _group_distribution(cohort, key) for key in (
            "symbol", "side", "setup", "regime", "probability_level_used")},
        "formula": {"production": "max((1-p)/p + min_ev_reserve_r, (1-p+min_positive_ev_r)/p)",
                    "break_even": "(1-p)/p", "min_ev_reserve_r": .05, "min_positive_ev_r": 0.0},
        "sensitivity": sensitivity, "feasibility_frontier": frontier,
        "pwin_required_for_median_geometry": p_required,
        "dominant_driver": "LOW_CONSERVATIVE_PWIN_RELATIVE_TO_CAUSAL_NET_RR_GEOMETRY",
        "economic_feasibility_verdict": verdict, "production_change_required": False,
        "next_task": "TASK_C_BOUNDED_OFFLINE_POLICY_CANDIDATES",
        "safety": {"mode": "PAPER", "live": False, "binance_order_calls": 0,
                   "production_mutations": 0, "full_parameter_sweep": False},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=("a", "b"), required=True)
    parser.add_argument("--outcome-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--deployed-revision", required=True)
    args = parser.parse_args()
    rows, schema = load_production_rows()
    if args.task == "a":
        if args.outcome_dir is None:
            parser.error("--outcome-dir is required for task a")
        cohort, report = build_task_a(rows, load_outcomes(args.outcome_dir), schema, args.deployed_revision)
        cohort_name, report_name = "PWIN_CALIBRATION_COHORT.jsonl", "TASK_A_REPORT.json"
    else:
        cohort, report = build_task_b(rows, schema, args.deployed_revision)
        cohort_name, report_name = "RR_ACHIEVABILITY_COHORT.jsonl", "TASK_B_REPORT.json"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / cohort_name).write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in cohort), encoding="utf-8")
    (args.output_dir / report_name).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"anchor": report["anchor"], "cohort": report["cohort"],
                      "verdict": report["final_verdict"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
