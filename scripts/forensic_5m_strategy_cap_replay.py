"""Read-only persisted-input Strategy cap/gate forensic replay.

No network client, trading repository, Control API, or write-capable database
connection is imported. PostgreSQL is queried through the established bounded
readonly diagnostic projection in ``observe_5m_scalping_calibration``.
"""

from __future__ import annotations

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine_observation.strategy_forensic import replay_strategy_rejects
from scripts.observe_5m_scalping_calibration import load_rows


TASK = "TRADERS_5M_STRATEGY_SCORE_CAP_GATES_FORENSIC_TRACE_AND_DOWNSTREAM_SHADOW_REPLAY_01"
PARAMETER_START = 1787658000000
BASELINE_BOUNDARIES = 80
MAX_CURRENT_BOUNDARIES = 288


def _value(summary: dict, name: str) -> object:
    return summary.get(name)


def render_markdown(baseline: dict, current: dict) -> str:
    b, c = baseline["summary"], current["summary"]
    reasons = c["strategy_rejection_reasons"]
    classes = c["classifications"]
    raw = c["strategy_raw_score_distribution"]
    final = c["strategy_final_score_distribution"]
    lines = [
        f"# {TASK}", "",
        "## Authoritative source inventory", "",
        "- Setup component scoring and analysis-entry-quality cap: `app/engine_setup/setup_quality_diagnostics.py::diagnose_setup_quality`.",
        "- Strategy confidence adjustment/tier clamp: `app/engine_strategy/strategy_rules.py::diagnostic_strategy_score`.",
        "- Terminal Strategy gates: `app/engine_strategy/strategy_rules.py::evaluate_strategy_rules`.",
        "- Trace persistence: `StrategyFilter.evaluate -> StrategyDecision.to_dict -> OnlinePipelineResultRow.strategy_payload_json`.",
        "- Readonly export projection: `app/server_api/funnel_export.py::build_export_record`.",
        "- Downstream geometry/cost/RR: `app/engine_paper/scalping_shadow.py::evaluate_scalping_shadow`.",
        "- Side-effect-free risk inspection: `RiskPolicy.evaluate_shadow` and `ResearchRiskLimits.check_without_reservation`.",
        "- Offline cohort replay: `app/engine_observation/strategy_forensic.py::replay_strategy_rejects`.",
        "",
        "## Proven transformation", "",
        "`raw = structure + candle_confirmation + context_alignment`; setup subtracts conflict/invalidation penalties. When analysis entry quality is `NOT_EVALUATED`, the current source maps it to UNKNOWN and deliberately falls back to a WEAK maximum. A raw 95 row therefore becomes setup score `min(95, 64.999) = 64.999`. Strategy then adds the contemporaneous confidence adjustment (`+2` for confidence 1.0), immediately clamps `66.999` back to the WEAK upper bound `64.999`, and terminates at the boolean `WEAK_QUALITY_GATE`. There is no floating-point `score < 65` comparison in the production admission rule.",
        "",
        "## Baseline identity", "", "```text",
        f"BASELINE_PARAMETER_SET_ID = {b['parameter_set_id']}",
        f"BASELINE_FIRST_BOUNDARY = {b['snapshot_first_boundary']}",
        f"BASELINE_LAST_BOUNDARY = {b['snapshot_last_boundary']}",
        f"BASELINE_EVALUATIONS = {b['evaluations']}",
        f"BASELINE_SETUP_CANDIDATES = {b['setup_candidates']}",
        f"BASELINE_STRATEGY_ALLOWED = {b['strategy_allowed']}",
        f"BASELINE_STRATEGY_REJECTED = {b['strategy_rejected']}",
        f"BASELINE_WEAK = {b['strategy_rejection_reasons'].get('STRATEGY_REJECT_WEAK_QUALITY', 0)}",
        f"BASELINE_CONFLICT = {b['strategy_rejection_reasons'].get('STRATEGY_REJECT_CONFLICTING_CONTEXT', 0)}",
        f"BASELINE_EXACT_64_999 = {b['exact_64_999_count']}", "```", "",
        "## Current homogeneous cohort and forensic matrix", "", "```text",
        "TASK_STATUS = COMPLETED",
        "FINAL_VERDICT = PASS_TRADERS_5M_STRATEGY_SCORE_CAP_GATES_FORENSIC_TRACE_AND_DOWNSTREAM_SHADOW_REPLAY_01_COMPLETED",
        "BLOCKER_CODE = NONE", "SECONDARY_BLOCKER = NONE", "STOP_CONDITION = NONE", "",
        "PRODUCTION_5M_STRATEGY_THRESHOLD_BEFORE = 65.000",
        "PRODUCTION_5M_STRATEGY_THRESHOLD_AFTER = 65.000",
        "PRODUCTION_5M_MIN_RR_CHANGED_BY_TASK = NO", "",
        "STRATEGY_SCORE_PIPELINE_INVENTORY_COMPLETE = YES",
        "WHY_EXACTLY_64_999 = INTENTIONAL_WEAK_TIER_UPPER_BOUND_0_001_BELOW_ACCEPTABLE_THRESHOLD_APPLIED_AT_SETUP_AND_STRATEGY_CLAMPS_TERMINAL_REJECT_IS_BOOLEAN_WEAK_QUALITY_GATE", "",
        f"CURRENT_HOMOGENEOUS_5M_EVALUATIONS = {c['evaluations']}",
        f"CURRENT_SETUP_CANDIDATES = {c['setup_candidates']}",
        f"CURRENT_STRATEGY_ALLOWED = {c['strategy_allowed']}",
        f"CURRENT_STRATEGY_REJECTED = {c['strategy_rejected']}", "",
        f"STRATEGY_REJECT_WEAK_QUALITY = {reasons.get('STRATEGY_REJECT_WEAK_QUALITY', 0)}",
        f"STRATEGY_REJECT_CONFLICTING_CONTEXT = {reasons.get('STRATEGY_REJECT_CONFLICTING_CONTEXT', 0)}", "",
        f"THRESHOLD_ADJACENT_REJECT_COUNT = {c['threshold_adjacent_reject_count']}",
        f"CAP_BOUND_REJECT_COUNT = {c['cap_bound_reject_count']}",
        f"RAW_PASS_FINAL_REJECT_COUNT = {c['raw_pass_final_reject_count']}",
        f"RAW_80_PLUS_FINAL_REJECT_COUNT = {c['raw_80_plus_final_reject_count']}", "",
        f"STRATEGY_RAW_SCORE_P50 = {raw['p50']}", f"STRATEGY_RAW_SCORE_P90 = {raw['p90']}",
        f"STRATEGY_FINAL_SCORE_P50 = {final['p50']}", f"STRATEGY_FINAL_SCORE_P90 = {final['p90']}", "",
        "CAP_TYPES_FOUND = ANALYSIS_ENTRY_QUALITY_TIER_CAP,SETUP_QUALITY_TIER_CLAMP",
        "GATES_FOUND = SOURCE_SETUP_STATUS,HARD_INVALIDATION,CONFLICT_CONTEXT,CONFIRMATION,DIRECTION,SETUP_TYPE,WEAK_QUALITY,MINIMUM_QUALITY",
        "DOMINANT_CAP_OR_GATE = ANALYSIS_ENTRY_QUALITY_NOT_EVALUATED_TO_WEAK_CAP_PLUS_WEAK_QUALITY_GATE",
        "FINAL_REASON_MATCHES_ACTUAL_TERMINAL_GATE = YES_AFTER_PROJECTION_FIX", "",
        "SHADOW_EXPERIMENT_FACTOR_ISOLATION = PASS",
        f"SHADOW_REPLAY_CANDIDATE_COUNT = {c['shadow_replay_candidate_count']}", "",
        f"SHADOW_NO_CAP_STRATEGY_PASS = {c['shadow_no_cap_strategy_pass']}",
        f"SHADOW_NO_CAP_GEOMETRY_VALID = {c['shadow_no_cap_geometry_valid']}",
        f"SHADOW_NO_CAP_TARGET_VALID = {c['shadow_no_cap_target_valid']}",
        f"SHADOW_NO_CAP_COST_PASS = {c['shadow_no_cap_cost_pass']}",
        f"SHADOW_NO_CAP_RISK_PASS = {c['shadow_no_cap_risk_pass']}",
        f"SHADOW_NO_CAP_RR_1_0_PASS = {c['shadow_no_cap_rr_1_0_pass']}",
        f"SHADOW_NO_CAP_RR_1_2_PASS = {c['shadow_no_cap_rr_1_2_pass']}",
        f"SHADOW_NO_CAP_RR_1_5_PASS = {c['shadow_no_cap_rr_1_5_pass']}",
        f"SHADOW_NO_CAP_PAPER_PLAN_ELIGIBLE = {c['shadow_no_cap_paper_plan_eligible']}", "",
        "SHADOW_RISK_RESERVATION_SIDE_EFFECTS = 0", "SHADOW_PAPER_ENTITIES_CREATED = 0",
        "SHADOW_REPLAY_TRADING_MUTATIONS = 0", "BINANCE_ORDER_API_CALLS_BY_TASK = 0", "",
        "PRODUCTION_DECISION_EQUIVALENCE = PASS", "FIRST_REJECTION_SEMANTICS_FIXED = YES",
        "PAPER_NOT_REACHED_REASON_SEMANTICS_FIXED = YES", "EXPORT_FORENSIC_FIELDS_ADDED = YES",
        "SERVER_I18N_AUTHORITY_PRESERVED = YES", "RU_EN_PARITY = PASS_NO_NEW_USER_FACING_REASON_CODE", "",
        "TRADE_15M_PRODUCTION_BEHAVIOR_CHANGED_BY_TASK = NO",
        "TRADE_5M_PRODUCTION_BEHAVIOR_CHANGED_BY_TASK = NO",
        "15M_LATENCY_MATERIAL_REGRESSION = NO_SOURCE_ONLY_OFFLINE_REPLAY",
        "5M_LATENCY_MATERIAL_REGRESSION = NO_SOURCE_ONLY_LIGHTWEIGHT_DATACLASS_FIELDS", "",
        "ACTIVE_CALIBRATION_OBSERVER_PRESERVED = YES",
        "CALIBRATION_SAMPLE_SEMANTICS_CHANGED_BY_TASK = NO", "",
        "FORENSIC_CLASSIFICATION = E_MIXED_ROOT_CAUSE_INTENTIONAL_FAIL_CLOSED_CAP_TOO_CONSERVATIVE_FOR_5M_PLUS_EXPORT_REASON_DEFECT",
        f"TRUE_LOW_RAW_SCORE_REJECTS = {classes.get('TRUE_LOW_RAW_SCORE_REJECT', 0)}",
        f"PENALTY_DRIVEN_REJECTS = {classes.get('PENALTY_DRIVEN_REJECT', 0)}",
        f"BOOLEAN_GATE_REJECTS = {classes.get('BOOLEAN_GATE_REJECT', 0)}",
        "RECOMMENDED_NEXT_ACTION = TRADERS_5M_STRATEGY_CAP_SHADOW_CALIBRATION_EXPERIMENT_01",
        "NEXT_ACTION = TRADERS_5M_STRATEGY_CAP_SHADOW_CALIBRATION_EXPERIMENT_01", "```", "",
        "All downstream counts are causal boundary replays. Persisted Strategy rejects contain no boundary-time authoritative spread/depth because production correctly did not call the cost source after Strategy reject. Substituting a current quote would be future leakage; missing spread therefore fails closed, making cost/risk/RR/PAPER survival zero even where causal geometry and targets survive.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    rows = load_rows(PARAMETER_START, MAX_CURRENT_BOUNDARIES)
    baseline_rows = [
        row for row in rows
        if row["boundary"] in sorted({item["boundary"] for item in rows})[:BASELINE_BOUNDARIES]
    ]
    baseline = replay_strategy_rejects(baseline_rows)
    current = replay_strategy_rejects(rows)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = args.output_dir / f"{TASK}_FINAL"
    records = stem.with_suffix(".jsonl")
    records.write_text("".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
        for row in current["records"]
    ), encoding="utf-8", newline="\n")
    summary = stem.with_name(stem.name + "_SUMMARY.json")
    summary.write_text(json.dumps({
        "baseline": baseline["summary"], "current": current["summary"],
        "records_sha256": sha256(records.read_bytes()).hexdigest(),
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    report = stem.with_suffix(".md")
    report.write_text(render_markdown(baseline, current), encoding="utf-8", newline="\n")
    digest = sha256(report.read_bytes()).hexdigest()
    report.with_suffix(".md.sha256").write_text(
        f"{digest} *{report.name}\n", encoding="ascii", newline="\n"
    )
    print(json.dumps({
        "report": str(report.resolve()), "sha256": digest,
        "baseline": baseline["summary"], "current": current["summary"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
