"""Bounded SELECT-only local production evidence; never submits a trade."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    sql = """SELECT row_to_json(x) FROM (
      SELECT symbol, closed_until_ms AS cycle_boundary, run_id,
             paper_payload_json AS paper, risk_payload_json AS risk,
             safety_counters_json AS safety
      FROM online_pipeline_results WHERE trade_profile_id='trade-5m-v2'
      AND closed_until_ms>=1788885600000
      ORDER BY closed_until_ms DESC, id DESC LIMIT 120) x"""
    output = subprocess.check_output([
        "docker", "exec", "traders-ml-postgres-1", "psql", "-U", "traders_ml",
        "-d", "traders_ml", "-At", "-c", sql], text=True, encoding="utf-8")
    rows = [json.loads(line) for line in output.splitlines() if line]
    candidates = []
    for row in rows:
        paper = row["paper"]
        context = paper.get("paper_context", {})
        diag = context.get("scalping_geometry_diagnostics")
        if not diag or diag.get("effective_total_cost_bps") is None:
            continue
        candidates.append({"symbol": row["symbol"], "cycle_boundary": row["cycle_boundary"],
            "parameter_set_id": paper.get("parameter_set_id"),
            "resolved_config_hash": paper.get("resolved_config_hash"),
            "minimum_planned_rr": context.get("production_rr_floor"), **diag})
    summary = {"count": len(candidates), "reason_distribution": dict(Counter(
        str(row.get("rejection_reason") or row.get("admission_reason") or row.get("rejection_stage"))
        for row in candidates))}
    for key in ("gross_rr", "net_rr", "dynamic_required_net_rr", "effective_total_cost_bps",
                "target_distance_bps", "stop_distance_bps"):
        values = [row[key] for row in candidates if isinstance(row.get(key), (int, float))]
        summary[key] = {"min": min(values), "median": statistics.median(values), "max": max(values)} if values else None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"observed_at": datetime.now(timezone.utc).isoformat(),
        "query": sql, "rows": rows, "candidates": candidates, "summary": summary},
        indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
