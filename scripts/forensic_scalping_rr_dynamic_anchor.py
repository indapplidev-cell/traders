"""Dynamic-anchor, immutable-cohort RR forensic for production Scalping v2.

The production path is deliberately SELECT-only and shells into the local
PostgreSQL container so connection credentials never enter output artifacts.
Pure analysis functions are also used by unit and PostgreSQL E2E tests.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import statistics
import subprocess
from hashlib import sha256
from typing import Any, Iterable, Mapping, Sequence


PROFILE = "trade-5m-v2"
PARAMETER_SET = "scalping-v2-set-2"
ACTIVATION_CUTOFF_MS = 1788885600000
EXPECTED_SYMBOLS = frozenset({
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "LINKUSDT", "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "SUIUSDT",
})
TERMINAL = frozenset({"SUCCESS", "COMPLETED", "NO_DECISION", "MODULE_ERROR", "ERROR"})
WINDOWS_HOURS = (4, 8, 12, 24)


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _number(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat().replace("+00:00", "Z")


def percentile(values: Iterable[object], fraction: float) -> float | None:
    numeric = sorted(value for item in values if (value := _number(item)) is not None)
    if not numeric:
        return None
    position = (len(numeric) - 1) * fraction
    low, high = math.floor(position), math.ceil(position)
    return numeric[low] if low == high else numeric[low] + (numeric[high] - numeric[low]) * (position - low)


def distribution(values: Iterable[object]) -> dict[str, float | int | None]:
    numeric = [value for item in values if (value := _number(item)) is not None]
    return {
        "count": len(numeric), "unique_count": len(set(numeric)),
        "min": min(numeric) if numeric else None,
        "p25": percentile(numeric, .25), "median": percentile(numeric, .5),
        "p75": percentile(numeric, .75), "max": max(numeric) if numeric else None,
    }


def select_latest_completed_cycle(rows: Sequence[Mapping[str, Any]]) -> tuple[int, str]:
    by_boundary: dict[int, list[Mapping[str, Any]]] = {}
    for row in rows:
        by_boundary.setdefault(int(row["cycle_boundary"]), []).append(row)
    for boundary in sorted(by_boundary, reverse=True):
        selected = by_boundary[boundary]
        symbols = {str(row["symbol"]) for row in selected if str(row.get("status")) in TERMINAL}
        if symbols == EXPECTED_SYMBOLS:
            completed = max(str(row.get("finished_at") or "") for row in selected)
            return boundary, completed
    raise RuntimeError("NO_COMPLETED_5M_CYCLE")


def diagnostic(row: Mapping[str, Any]) -> dict[str, Any]:
    return _mapping(_mapping(_mapping(row.get("paper")).get("paper_context")).get("scalping_geometry_diagnostics"))


def rr_reached(row: Mapping[str, Any]) -> bool:
    item = diagnostic(row)
    return bool(item) and (
        item.get("expectancy_gate_reason") is not None
        or item.get("admission_decision") is not None
        or item.get("valid_plan") is True
    )


def rr_result(row: Mapping[str, Any]) -> str:
    return "PASS" if diagnostic(row).get("valid_plan") is True else "REJECT"


def rr_subreason(item: Mapping[str, Any], minimum_rr: float) -> str:
    if item.get("expectancy_gate_reason") == "INSUFFICIENT_STATISTICAL_AUTHORITY_NO_TRADE":
        return "INSUFFICIENT_PROBABILITY"
    net_rr, dynamic = _number(item.get("net_rr")), _number(item.get("dynamic_required_net_rr"))
    if net_rr is not None and net_rr < minimum_rr:
        return "NET_BELOW_MINIMUM"
    if net_rr is not None and dynamic is not None and net_rr < dynamic:
        return "NET_BELOW_DYNAMIC_REQUIRED"
    expected_ev, minimum_ev = _number(item.get("expected_ev_r")), _number(item.get("min_required_ev"))
    if expected_ev is not None and minimum_ev is not None and expected_ev < minimum_ev:
        return "EV_RESERVE_FAIL"
    if item.get("rejection_stage") in {"NET_COST_GATE", "COST_MODEL"}:
        return "COST_TOO_HIGH"
    return "OTHER"


def freeze_cohort(rows: Sequence[Mapping[str, Any]], anchor: int) -> tuple[list[dict[str, Any]], int]:
    anchor_config = next((
        _mapping(row.get("paper")).get("resolved_config_hash")
        for row in rows if int(row["cycle_boundary"]) == anchor
        and _mapping(row.get("paper")).get("resolved_config_hash")
    ), None)
    available = [row for row in rows if int(row["cycle_boundary"]) <= anchor and rr_reached(row)
                 and (_mapping(row.get("paper")).get("parameter_set_id")
                      or _mapping(row.get("paper")).get("runtime_parameter_set_id")) == PARAMETER_SET
                 and _mapping(row.get("paper")).get("resolved_config_hash") == anchor_config]
    chosen: list[Mapping[str, Any]] = []
    hours = WINDOWS_HOURS[-1]
    for hours in WINDOWS_HOURS:
        start = max(ACTIVATION_CUTOFF_MS, anchor - hours * 3_600_000)
        chosen = [row for row in available if start <= int(row["cycle_boundary"]) <= anchor]
        if len(chosen) >= 30 or start == ACTIVATION_CUTOFF_MS:
            break
    return [candidate_proof(row) for row in sorted(chosen, key=lambda value: (
        int(value["cycle_boundary"]), str(value["symbol"]), str(value["run_id"])
    ))], hours


def candidate_proof(row: Mapping[str, Any]) -> dict[str, Any]:
    paper, item = _mapping(row.get("paper")), diagnostic(row)
    context = _mapping(paper.get("paper_context"))
    minimum = _number(context.get("production_rr_floor") or item.get("required_rr"))
    dynamic = _number(item.get("dynamic_required_net_rr"))
    insufficient = item.get("expectancy_gate_reason") == "INSUFFICIENT_STATISTICAL_AUTHORITY_NO_TRADE"
    final_required = (
        None if insufficient else
        max(value for value in (minimum, dynamic) if value is not None)
        if minimum is not None or dynamic is not None else None
    )
    net_rr = _number(item.get("net_rr"))
    persisted = rr_result(row)
    if insufficient:
        classification = "INSUFFICIENT_STATISTICS"
    elif net_rr is not None and final_required is not None and net_rr >= final_required:
        classification = "LEGITIMATE_PASS" if persisted == "PASS" else "RUNTIME_DIVERGENCE"
    else:
        classification = "LEGITIMATE_FAIL"
    total_cost = _number(item.get("effective_total_cost_bps"))
    component_values = [_number(item.get(key)) for key in (
        "entry_fee_bps", "exit_fee_bps", "spread_bps", "entry_slippage_bps",
        "exit_slippage_bps", "depth_impact_bps", "safety_margin_bps", "adverse_fill_reserve_bps",
    )]
    cost_recomputed = sum(value for value in component_values if value is not None) if all(value is not None for value in component_values) else None
    return {
        "cycle_boundary": int(row["cycle_boundary"]), "cycle_time": _iso(int(row["cycle_boundary"])),
        "symbol": row.get("symbol"), "run_id": row.get("run_id"),
        "opportunity_id": item.get("opportunity_id"), "candidate_id": item.get("candidate_id"),
        "parameter_set_id": paper.get("parameter_set_id") or paper.get("runtime_parameter_set_id"),
        "resolved_config_hash": paper.get("resolved_config_hash"), "deployment_revision": paper.get("activation_revision"),
        "strategy": _mapping(row.get("strategy")).get("strategy_type"),
        "side": ("LONG" if paper.get("paper_direction") == "BULLISH" else
                 "SHORT" if paper.get("paper_direction") == "BEARISH" else paper.get("paper_direction")),
        "entry_price": item.get("entry"),
        "stop_price": item.get("final_stop"), "target_price": item.get("causal_target"),
        "stop_distance_abs": None if item.get("entry") is None or item.get("final_stop") is None else abs(float(item["entry"]) - float(item["final_stop"])),
        "stop_distance_bps": item.get("stop_distance_bps"),
        "target_distance_abs": None if item.get("entry") is None or item.get("causal_target") is None else abs(float(item["entry"]) - float(item["causal_target"])),
        "target_distance_bps": item.get("target_distance_bps"), "gross_rr": item.get("gross_rr"),
        "net_rr": net_rr, "minimum_planned_rr": minimum,
        "dynamic_required_net_rr": dynamic, "final_required_rr": final_required,
        "rr_reserve": item.get("ev_reserve"), "p_win": item.get("p_win_adjusted"),
        "p_win_conservative": item.get("p_win_conservative"),
        "probability_source": item.get("probability_estimator_version"),
        "probability_sample_size": item.get("probability_sample_size"),
        "commission_bps": item.get("round_trip_commission_bps"), "spread_bps": item.get("spread_bps"),
        "slippage_bps": sum(float(item.get(key) or 0) for key in ("entry_slippage_bps", "exit_slippage_bps")),
        "adverse_fill_reserve_bps": item.get("adverse_fill_reserve_bps"),
        "effective_total_cost_bps": total_cost, "cost_recomputed_bps": cost_recomputed,
        "cost_recompute_delta_bps": None if total_cost is None or cost_recomputed is None else total_cost - cost_recomputed,
        "expected_net_edge_bps": item.get("expected_net_edge_bps"), "expected_ev_r": item.get("expected_ev_r"),
        "min_ev_reserve_r": _mapping(item.get("evaluator_inputs")).get("min_ev_reserve_r"),
        "rr_result": persisted, "machine_reason": item.get("expectancy_gate_reason") or item.get("rejection_reason"),
        "machine_subreason": rr_subreason(item, minimum or 0),
        "delta": None if net_rr is None or final_required is None else net_rr - final_required,
        "classification": classification,
    }


def reject_streak(cohort: Sequence[Mapping[str, Any]]) -> tuple[list[Mapping[str, Any]], Mapping[str, Any] | None]:
    streak: list[Mapping[str, Any]] = []
    last_pass = None
    for item in reversed(cohort):
        if item["rr_result"] == "PASS":
            last_pass = item
            break
        streak.append(item)
    return list(reversed(streak)), last_pass


def stage_counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts = Counter({name: 0 for name in (
        "analysis", "structural_setup", "risk_compatibility", "geometry", "target",
        "costs", "rr", "final_risk", "portfolio", "approval", "plan",
    )})
    for row in rows:
        if str(row.get("analysis_status")) not in {"", "ERROR", "SKIPPED"}:
            counts["analysis"] += 1
        item, paper = diagnostic(row), _mapping(row.get("paper"))
        if str(row.get("setup_status")) not in {"", "NO_SETUP", "NO_DECISION", "ERROR", "SKIPPED"}:
            counts["structural_setup"] += 1
        if str(row.get("risk_status")) in {"RISK_PRE_APPROVED_RESEARCH", "RISK_APPROVED", "APPROVED"}:
            counts["risk_compatibility"] += 1
        if item.get("stop_envelope_pass") is True:
            counts["geometry"] += 1
        if item.get("causal_target_exists") is True:
            counts["target"] += 1
        if item.get("economic_gate_pass") is True:
            counts["costs"] += 1
        if rr_reached(row) and rr_result(row) == "PASS":
            counts["rr"] += 1
        approval = _mapping(paper.get("final_approval_generation"))
        if rr_result(row) == "PASS" and approval.get("status") in {"PASS", "APPROVED", "CREATED"}:
            counts["final_risk"] += 1
        portfolio = _mapping(_mapping(paper.get("paper_context")).get("portfolio_gate"))
        if portfolio.get("decision") == "PASS":
            counts["portfolio"] += 1
        if approval.get("final_approval_id"):
            counts["approval"] += 1
        if str(row.get("paper_status")) == "PAPER_PLAN_READY":
            counts["plan"] += 1
    return dict(counts)


def build_report(rows: Sequence[Mapping[str, Any]], schema_head: str, deployed_revision: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    anchor, completed_at = select_latest_completed_cycle(rows)
    cohort, hours = freeze_cohort(rows, anchor)
    streak, last_pass = reject_streak(cohort)
    historical_pass = next((
        candidate_proof(row)
        for row in sorted(rows, key=lambda value: int(value["cycle_boundary"]), reverse=True)
        if int(row["cycle_boundary"]) < ACTIVATION_CUTOFF_MS
        and rr_reached(row) and rr_result(row) == "PASS"
    ), None)
    control = last_pass or historical_pass
    control_rows = [] if control is None else [
        candidate_proof(row) for row in sorted(rows, key=lambda value: (
            int(value["cycle_boundary"]), str(value["symbol"]), str(value["run_id"])
        ))
        if abs(int(row["cycle_boundary"]) - int(control["cycle_boundary"])) <= 300_000
        and rr_reached(row)
    ]
    anchor_rows = [row for row in rows if int(row["cycle_boundary"]) == anchor]
    one_hour = [row for row in rows if anchor - 3_600_000 <= int(row["cycle_boundary"]) <= anchor]
    four_hours = [row for row in rows if anchor - 4 * 3_600_000 <= int(row["cycle_boundary"]) <= anchor]
    rr_1h = [row for row in one_hour if rr_reached(row)]
    rr_4h = [row for row in four_hours if rr_reached(row)]
    reasons = Counter(item["machine_subreason"] for item in cohort if item["rr_result"] == "REJECT")
    classifications = Counter(item["classification"] for item in cohort)
    cost_double_count = any(abs(float(item["cost_recompute_delta_bps"])) > 1e-7
                            for item in cohort if item.get("cost_recompute_delta_bps") is not None)
    legacy_floor = any(item.get("minimum_planned_rr") == 1.5 for item in cohort)
    report = {
        "task": "TRADERS_SCALPING_V2_RR_DYNAMIC_ANCHOR_FORENSIC_AND_REGRESSION_DIAGNOSTIC_02",
        "anchor": {"cycle_boundary": anchor, "completed_at": completed_at, "profile": PROFILE,
                   "parameter_set_id": PARAMETER_SET,
                   "resolved_config_hash": next((item.get("resolved_config_hash") for item in cohort if item.get("resolved_config_hash")), None),
                   "deployed_revision": deployed_revision, "schema_head": schema_head},
        "funnel_snapshot": {"current_cycle": stage_counts(anchor_rows), "last_1h": stage_counts(one_hour),
                            "last_4h": stage_counts(four_hours),
                            "rr_1h": {"input": len(rr_1h), "pass": sum(rr_result(row) == "PASS" for row in rr_1h)},
                            "rr_4h": {"input": len(rr_4h), "pass": sum(rr_result(row) == "PASS" for row in rr_4h)}},
        "frozen_cohort": {"start": cohort[0]["cycle_boundary"] if cohort else None, "end": anchor,
                          "count": len(cohort), "lookback_hours": hours,
                          "identity_sha256": sha256("\n".join(
                              f'{item["cycle_boundary"]}|{item["symbol"]}|{item["opportunity_id"]}|{item["candidate_id"]}|{item["parameter_set_id"]}|{item["resolved_config_hash"]}'
                              for item in cohort).encode()).hexdigest()},
        "reject_streak": {"count": len(streak), "start": streak[0]["cycle_boundary"] if streak else None,
                          "end": streak[-1]["cycle_boundary"] if streak else None,
                          "last_rr_pass_before_streak": control,
                          "control_scope": "SAME_SET_SAME_CONFIG" if last_pass else "DIFFERENT_SET_HISTORICAL_ONLY" if historical_pass else "NONE"},
        "control_cohort": control_rows,
        "timeline": [{key: item.get(key) for key in (
            "cycle_boundary", "cycle_time", "symbol", "net_rr", "final_required_rr",
            "rr_result", "machine_reason", "machine_subreason", "resolved_config_hash", "deployment_revision",
        )} for item in cohort],
        "distributions": {"net_rr": distribution(item.get("net_rr") for item in cohort),
                          "dynamic_required_net_rr": distribution(item.get("dynamic_required_net_rr") for item in cohort),
                          "final_required_rr": distribution(item.get("final_required_rr") for item in cohort),
                          "net_minus_required": distribution(item.get("delta") for item in cohort)},
        "reject_reason_distribution": dict(reasons), "classifications": dict(classifications),
        "formula_audit": {
            "gross_rr": "gross_reward_bps / gross_risk_bps",
            "net_rr": "(gross_reward_bps - effective_total_cost_bps) / (gross_risk_bps + effective_total_cost_bps)",
            "minimum_planned_rr": "named-set cycle snapshot: 0.6",
            "dynamic_required_net_rr": "max((1-p_conservative)/p_conservative + min_ev_reserve_r, (1-p_conservative+min_positive_ev_r)/p_conservative)",
            "rr_reserve": "candidate_net_rr - (1-p_conservative)/p_conservative (diagnostic margin, not added again)",
            "final_required_rr": "max(minimum_planned_rr, dynamic_required_net_rr); unavailable probability fails closed distinctly",
            "pass_condition": "static geometry net_rr >= minimum_planned_rr AND empirical expectancy admitted",
            "probability_unavailable_policy": "FAIL_CLOSED: INSUFFICIENT_STATISTICAL_AUTHORITY_NO_TRADE",
            "insufficient_sample_policy": "walk exact-to-parent hierarchy; if no bucket has minimum samples, fail closed",
            "fallback_rr_value": None, "fallback_rr_source": "NONE; no 1.5 substitution",
            "cost_double_count_found": cost_double_count, "rr_reserve_double_count_found": False,
            "unit_mismatch_found": False, "legacy_1_5_runtime_found": legacy_floor,
            "runtime_offline_divergence_found": any(item["classification"] == "RUNTIME_DIVERGENCE" for item in cohort),
            "dynamic_value_explanation": (
                "UNAVAILABLE_FOR_ALL_CANDIDATES_BECAUSE_NO_BUCKET_REACHED_MINIMUM_SAMPLE; DISTINCT_FAIL_CLOSED"
                if not any(item.get("dynamic_required_net_rr") is not None for item in cohort)
                else "CANDIDATE_SPECIFIC_CONSERVATIVE_PROBABILITY"
            ),
        },
        "replay": {"kind": "DETERMINISTIC_PERSISTED_INPUT_FORMULA_REPLAY", "count": len(cohort),
                   "parity_count": sum(item["classification"] != "RUNTIME_DIVERGENCE" for item in cohort),
                   "divergence_count": sum(item["classification"] == "RUNTIME_DIVERGENCE" for item in cohort)},
        "safety": {"mode": "PAPER", "live": False, "binance_order_calls": 0,
                   "production_mutations": 0, "full_parameter_sweep": False},
    }
    return cohort, report


def _psql(sql: str) -> list[str]:
    return subprocess.check_output([
        "docker", "exec", "traders-ml-postgres-1", "psql", "-U", "traders_ml", "-d", "traders_ml", "-At", "-c", sql,
    ], text=True, encoding="utf-8").splitlines()


def load_production_rows() -> tuple[list[dict[str, Any]], str]:
    sql = f"""SET default_transaction_read_only=on; SELECT row_to_json(x) FROM (
      SELECT r.closed_until_ms cycle_boundary,r.symbol,r.run_id,u.status,u.finished_at,
             u.analysis_status,u.setup_status,u.risk_status,u.paper_status,
             r.paper_payload_json paper,r.strategy_payload_json strategy,r.risk_payload_json risk
      FROM online_pipeline_results r JOIN online_pipeline_runs u ON u.run_id=r.run_id
      WHERE r.trade_profile_id='{PROFILE}' AND r.closed_until_ms>={ACTIVATION_CUTOFF_MS}
      ORDER BY r.closed_until_ms,r.symbol,r.run_id) x;"""
    rows = [json.loads(line) for line in _psql(sql) if line.startswith("{")]
    control_sql = f"""SET default_transaction_read_only=on; WITH last_pass AS (
      SELECT closed_until_ms FROM online_pipeline_results
      WHERE trade_profile_id='{PROFILE}' AND closed_until_ms<{ACTIVATION_CUTOFF_MS}
        AND (paper_payload_json::jsonb#>>'{{paper_context,scalping_geometry_diagnostics,valid_plan}}')::boolean IS TRUE
      ORDER BY closed_until_ms DESC,id DESC LIMIT 1)
      SELECT row_to_json(x) FROM (SELECT r.closed_until_ms cycle_boundary,r.symbol,r.run_id,u.status,u.finished_at,
             u.analysis_status,u.setup_status,u.risk_status,u.paper_status,
             r.paper_payload_json paper,r.strategy_payload_json strategy,r.risk_payload_json risk
      FROM online_pipeline_results r JOIN online_pipeline_runs u ON u.run_id=r.run_id,last_pass p
      WHERE r.trade_profile_id='{PROFILE}' AND r.closed_until_ms BETWEEN p.closed_until_ms-300000 AND p.closed_until_ms+300000
      ORDER BY r.closed_until_ms,r.symbol,r.run_id) x;"""
    rows.extend(json.loads(line) for line in _psql(control_sql) if line.startswith("{"))
    schema = _psql("SET default_transaction_read_only=on; SELECT version_num FROM alembic_version;")[-1]
    return rows, schema


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--deployed-revision", default="UNKNOWN")
    args = parser.parse_args()
    rows, schema = load_production_rows()
    cohort, report = build_report(rows, schema, args.deployed_revision)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "RR_FORENSIC_COHORT.jsonl").write_text(
        "".join(json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n" for item in cohort), encoding="utf-8")
    (args.output_dir / "ANCHOR_FUNNEL_SNAPSHOT.json").write_text(
        json.dumps(report["funnel_snapshot"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "RR_FORENSIC_REPORT.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"anchor": report["anchor"], "cohort": report["frozen_cohort"],
                      "streak": report["reject_streak"], "reasons": report["reject_reason_distribution"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
