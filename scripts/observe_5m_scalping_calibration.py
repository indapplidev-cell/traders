"""Read-only bounded production 5m calibration export.

The command uses the established local PostgreSQL container identity and emits
only public domain diagnostics.  It never reads container environment values.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine_observation.scalping_calibration import aggregate
from app.engine_orchestrator.runtime_parameters import resolve_runtime_parameters

CONTAINER = "traders-ml-postgres-1"
START_BOUNDARY = 1787594700000
PROFILE = "trade-5m-v1"
PARAMETER_SET = resolve_runtime_parameters(PROFILE).parameter_set_id
MAX_BOUNDARIES = 288


def _sql(start: int, limit: int) -> str:
    return f"""
WITH selected_boundaries AS (
  SELECT DISTINCT closed_until_ms FROM online_pipeline_runs
  WHERE trade_profile_id='{PROFILE}' AND closed_until_ms >= {start}
  ORDER BY closed_until_ms ASC LIMIT {limit}
), rows AS (
 SELECT jsonb_build_object(
   'run_id',r.run_id,'result_id',res.id,'boundary',r.closed_until_ms,'symbol',r.symbol,
   'profile',r.trade_profile_id,'parameter_set_id',
      coalesce(res.paper_payload_json::jsonb->>'runtime_parameter_set_id',
               res.analysis_payload_json::jsonb->>'runtime_parameter_set_id'),
   'duration_ms',r.duration_ms,'final_reason',r.final_reason,
   'analysis',jsonb_build_object('regime',res.analysis_payload_json::jsonb->'regime',
      'entry_quality',res.analysis_payload_json::jsonb->'entry_quality',
      'entry_quality_reason_codes',res.analysis_payload_json::jsonb#>'{{entry_quality_diagnostics,reason_codes}}',
      'impulse_phase',res.analysis_payload_json::jsonb->'impulse_phase',
      'impulse_direction',res.analysis_payload_json::jsonb->'impulse_direction',
      'impulse_context',res.analysis_payload_json::jsonb->'impulse_context'),
   'setup',jsonb_build_object('setup_status',coalesce(res.setup_payload_json::jsonb->'setup_status',res.setup_payload_json::jsonb->'status'),
      'setup_type',res.setup_payload_json::jsonb->'setup_type','scenario',res.setup_payload_json::jsonb->'scenario',
      'direction_hint',res.setup_payload_json::jsonb->'direction_hint',
      'setup_quality',res.setup_payload_json::jsonb->'setup_quality',
      'source_entry_quality',res.setup_payload_json::jsonb->'source_entry_quality',
      'quality_score',res.setup_payload_json::jsonb->'quality_score',
      'quality_diagnostics',res.setup_payload_json::jsonb->'quality_diagnostics',
      'quality_reasons',res.setup_payload_json::jsonb->'quality_reasons',
      'quality_warnings',res.setup_payload_json::jsonb->'quality_warnings',
      'diagnostics',res.setup_payload_json::jsonb->'diagnostics'),
   'strategy',jsonb_build_object('decision_status',res.strategy_payload_json::jsonb->'decision_status',
      'direction_hint',res.strategy_payload_json::jsonb->'direction_hint',
      'strategy_score',res.strategy_payload_json::jsonb->'strategy_score',
      'strategy_quality_threshold',res.strategy_payload_json::jsonb->'strategy_quality_threshold',
      'strategy_margin_to_threshold',res.strategy_payload_json::jsonb->'strategy_margin_to_threshold',
      'strategy_raw_score',res.strategy_payload_json::jsonb->'strategy_raw_score',
      'strategy_penalty_total',res.strategy_payload_json::jsonb->'strategy_penalty_total',
      'strategy_pre_cap_score',res.strategy_payload_json::jsonb->'strategy_pre_cap_score',
      'strategy_cap_applied',res.strategy_payload_json::jsonb->'strategy_cap_applied',
      'strategy_cap_type',res.strategy_payload_json::jsonb->'strategy_cap_type',
      'strategy_cap_reason',res.strategy_payload_json::jsonb->'strategy_cap_reason',
      'strategy_cap_value',res.strategy_payload_json::jsonb->'strategy_cap_value',
      'strategy_post_cap_score',res.strategy_payload_json::jsonb->'strategy_post_cap_score',
      'strategy_caps',res.strategy_payload_json::jsonb->'strategy_caps',
      'strategy_gate_results',res.strategy_payload_json::jsonb->'strategy_gate_results',
      'strategy_failed_gate',res.strategy_payload_json::jsonb->'strategy_failed_gate',
      'strategy_failed_gate_reason',res.strategy_payload_json::jsonb->'strategy_failed_gate_reason',
      'component_scores',res.strategy_payload_json::jsonb->'component_scores',
      'context',CASE WHEN res.setup_payload_json::jsonb->>'status'='SETUP_CANDIDATE'
         THEN res.strategy_payload_json::jsonb->'context' ELSE NULL END,
      'decision_warnings',res.strategy_payload_json::jsonb->'decision_warnings',
      'rejection_reasons',res.strategy_payload_json::jsonb->'rejection_reasons',
      'shadow_quality_cohorts',res.strategy_payload_json::jsonb->'shadow_quality_cohorts'),
   'risk',jsonb_build_object('risk_status',res.risk_payload_json::jsonb->'risk_status',
      'direction_hint',res.risk_payload_json::jsonb->'direction_hint'),
   'paper',jsonb_build_object('paper_status',res.paper_payload_json::jsonb->'paper_status',
      'paper_direction',res.paper_payload_json::jsonb->'paper_direction',
      'hypothetical_entry_reference',res.paper_payload_json::jsonb->'hypothetical_entry_reference',
      'hypothetical_invalidation_level',res.paper_payload_json::jsonb->'hypothetical_invalidation_level',
      'hypothetical_stop_level',res.paper_payload_json::jsonb->'hypothetical_stop_level',
      'hypothetical_target_level',res.paper_payload_json::jsonb->'hypothetical_target_level',
      'target_source',res.paper_payload_json::jsonb->'target_source',
      'final_approval_generation',res.paper_payload_json::jsonb->'final_approval_generation',
      'paper_context',jsonb_build_object(
         'causal_primitives',CASE WHEN res.setup_payload_json::jsonb->>'status'='SETUP_CANDIDATE'
            THEN res.paper_payload_json::jsonb#>'{{paper_context,causal_primitives}}' ELSE NULL END,
         'scalping_geometry_diagnostics',CASE WHEN res.setup_payload_json::jsonb->>'status'='SETUP_CANDIDATE'
            THEN res.paper_payload_json::jsonb#>'{{paper_context,scalping_geometry_diagnostics}}' ELSE NULL END,
         'strategy_cap_shadow_economic_snapshot',CASE WHEN res.setup_payload_json::jsonb->>'status'='SETUP_CANDIDATE'
            THEN res.paper_payload_json::jsonb#>'{{paper_context,strategy_cap_shadow_economic_snapshot}}' ELSE NULL END)),
   'module_reasons',res.module_reasons_json::jsonb,
   'paper_command_id',cmd.command_id,'paper_position_id',pos.position_id,
   'paper_outcome',CASE WHEN pos.state='CLOSED' THEN 'CLOSED' ELSE pos.state END,
   'holding_time_seconds',CASE WHEN pos.closed_at IS NOT NULL THEN extract(epoch from pos.closed_at-pos.opened_at) END,
   'net_pnl',pos.realized_pnl,
   'risk_budget_reserved',false
 ) value
 FROM online_pipeline_runs r JOIN selected_boundaries b USING(closed_until_ms)
 JOIN online_pipeline_results res USING(run_id)
 LEFT JOIN paper_execution_commands cmd ON cmd.pipeline_run_id=r.run_id
 LEFT JOIN paper_positions pos ON pos.entry_order_id IN
   (SELECT o.order_id FROM paper_orders o WHERE o.command_id=cmd.command_id AND o.order_role='ENTRY')
 WHERE r.trade_profile_id='{PROFILE}'
 ORDER BY r.closed_until_ms,r.symbol
) SELECT value::text FROM rows
"""


def load_rows(start: int, limit: int) -> list[dict]:
    result = subprocess.run(
        ["docker", "exec", "--user", "postgres", CONTAINER, "psql", "-U", "traders_ml",
         "-d", "traders_ml", "-AtX", "-c", _sql(start, limit)],
        check=True, capture_output=True, text=True, encoding="utf-8",
    )
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    # Historical JSON payloads include a bounded legacy serializer variant
    # that wrapped the otherwise identical parameter identity in apostrophes.
    # Normalize identity representation only; sample semantics are unchanged.
    for row in rows:
        value = row.get("parameter_set_id")
        if isinstance(value, str):
            normalized = value.strip().strip("'\"")
            if PARAMETER_SET in normalized:
                normalized = PARAMETER_SET
            row["parameter_set_id"] = normalized
    return rows


def boundary_count(start: int, limit: int) -> int:
    sql = (
        "SELECT count(*) FROM (SELECT DISTINCT closed_until_ms "
        "FROM online_pipeline_runs WHERE trade_profile_id='trade-5m-v1' "
        f"AND closed_until_ms >= {start} ORDER BY closed_until_ms ASC LIMIT {limit}) q"
    )
    result = subprocess.run(
        ["docker", "exec", "--user", "postgres", CONTAINER, "psql", "-U", "traders_ml",
         "-d", "traders_ml", "-AtX", "-c", sql],
        check=True, capture_output=True, text=True, encoding="utf-8",
    )
    return int(result.stdout.strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-boundary", type=int, default=START_BOUNDARY)
    parser.add_argument("--max-boundaries", type=int, default=MAX_BOUNDARIES, choices=range(1, MAX_BOUNDARIES + 1))
    parser.add_argument("--min-boundaries", type=int, default=144)
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=60, choices=range(30, 301))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    while args.wait:
        observed = boundary_count(args.start_boundary, args.max_boundaries)
        print(json.dumps({"event": "BOUNDARY_PROGRESS", "observed": observed,
                          "required": args.min_boundaries}), flush=True)
        if observed >= args.min_boundaries:
            break
        time.sleep(args.poll_seconds)
    rows = load_rows(args.start_boundary, args.max_boundaries)
    report = aggregate(rows)
    if report["parameter_set_id"] != PARAMETER_SET:
        raise SystemExit("runtime parameter identity mismatch")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    export_path = args.output_dir / "TRADERS_5M_SCALPING_CALIBRATION_BASELINE_01.jsonl"
    summary_path = args.output_dir / "TRADERS_5M_SCALPING_CALIBRATION_BASELINE_01_SUMMARY.json"
    with export_path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in report.pop("export_rows"):
            stream.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    summary_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "export": export_path.name, "export_sha256": sha256(export_path.read_bytes()).hexdigest(),
        "summary": summary_path.name, "summary_sha256": sha256(summary_path.read_bytes()).hexdigest(),
        "boundaries_observed": report["boundaries_observed"],
        "minimum_boundaries": args.min_boundaries,
        "sample_gate": "PASS" if report["boundaries_observed"] >= args.min_boundaries else "INSUFFICIENT_BOUNDARIES",
    }
    manifest_path = args.output_dir / "TRADERS_5M_SCALPING_CALIBRATION_BASELINE_01_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, sort_keys=True))
    return 0 if manifest["sample_gate"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
