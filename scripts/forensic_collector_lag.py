"""Bounded read-only exact-set forensic for the Scalping v2 collector."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import subprocess


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def load_parts(root: Path, kind: str) -> list[dict]:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    rows: list[dict] = []
    for part in manifest["parts"]:
        if part["kind"] != kind:
            continue
        path = root / part["path"]
        if path.exists():
            rows.extend(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line)
    return rows


def query(anchor: int) -> list[dict]:
    sql = f"""COPY (SELECT row_to_json(x) FROM (
      SELECT r.closed_until_ms cycle_boundary,r.symbol,r.run_id,r.finished_at,
             res.id result_id,res.setup_payload_json setup,res.strategy_payload_json strategy,
             res.paper_payload_json paper
      FROM online_pipeline_runs r JOIN online_pipeline_results res ON res.run_id=r.run_id
      WHERE r.trade_profile_id='trade-5m-v2' AND r.closed_until_ms>{anchor}-86400000
        AND r.closed_until_ms<={anchor}
      ORDER BY r.closed_until_ms,r.symbol,res.id) x) TO STDOUT"""
    output = subprocess.check_output([
        "docker", "exec", "traders-ml-postgres-1", "psql", "-U", "traders_ml",
        "-d", "traders_ml", "-At", "-c", sql,
    ], text=True, encoding="utf-8")
    return [json.loads(line) for line in output.splitlines() if line]


def latest_authoritative_boundary() -> int:
    output = subprocess.check_output([
        "docker", "exec", "traders-ml-postgres-1", "psql", "-U", "traders_ml",
        "-d", "traders_ml", "-At", "-c",
        "SELECT max(closed_until_ms) FROM online_pipeline_runs WHERE trade_profile_id='trade-5m-v2' AND status='COMPLETED'",
    ], text=True, encoding="utf-8").strip()
    return int(output)


def iso_ms(value: str | None) -> int | None:
    if not value:
        return None
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--collector-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--fresh-from-boundary", type=int)
    args = parser.parse_args()
    health = json.loads((args.collector_dir / "health.json").read_text(encoding="utf-8"))
    segment = health["observation_segment_id"]
    observations = [row for row in load_parts(args.collector_dir, "observations")
                    if row.get("observation_segment_id") == segment]
    outcomes = [row for row in load_parts(args.collector_dir, "outcomes")
                if row.get("observation_segment_id") == segment]
    anchor = latest_authoritative_boundary()
    expected = query(anchor)
    expected_ids = []
    for row in expected:
        setup, strategy, paper = row.get("setup") or {}, row.get("strategy") or {}, row.get("paper") or {}
        identity = {
            "cycle_boundary": row["cycle_boundary"], "symbol": row["symbol"],
            "opportunity_id": setup.get("opportunity_id") or (strategy.get("context") or {}).get("opportunity_id"),
            "candidate_id": strategy.get("candidate_id") or paper.get("candidate_id"),
            "run_id": row["run_id"], "result_id": row["result_id"], "finished_at": row["finished_at"],
        }
        expected_ids.append(identity)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    expected_path = args.output_dir / "AUTHORITATIVE_5M_EXPECTED_IDS.jsonl"
    expected_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in expected_ids), encoding="utf-8")

    exp = {(r["cycle_boundary"], r["symbol"]): r for r in expected_ids}
    collected_rows = [r for r in observations if r["identity"]["boundary_time_ms"] <= anchor and r["identity"]["boundary_time_ms"] > anchor - 86400000]
    grouped = defaultdict(list)
    for row in collected_rows:
        grouped[(row["identity"]["boundary_time_ms"], row["identity"]["symbol"])].append(row)
    got = set(grouped)
    missing = sorted(set(exp) - got)
    orphan = sorted(got - set(exp))
    duplicate = sorted(key for key, rows in grouped.items() if len(rows) > 1)
    ingestion_lag = []
    fresh_ingestion_lag = []
    for key in set(exp) & got:
        captured = iso_ms(grouped[key][0].get("captured_at"))
        finished = iso_ms(exp[key].get("finished_at"))
        if captured is not None and finished is not None:
            ingestion_lag.append((captured - finished) / 1000)
            if args.fresh_from_boundary is not None and key[0] >= args.fresh_from_boundary:
                fresh_ingestion_lag.append((captured - finished) / 1000)
    outcome_by_obs = Counter(str(r["observation_id"]) for r in outcomes)
    mature_cutoff = int(datetime.now(timezone.utc).timestamp() * 1000) - 1_140_000
    expected_mature = [r for r in collected_rows if r.get("outcome_followup") and r["outcome_followup"]["followup_due_ms"] <= mature_cutoff]
    mature_missing = [r["observation_id"] for r in expected_mature if not outcome_by_obs[r["observation_id"]]]
    not_yet_mature = [r["observation_id"] for r in collected_rows if r.get("outcome_followup") and r["outcome_followup"]["followup_due_ms"] > mature_cutoff]
    outcome_duplicates = [key for key, count in outcome_by_obs.items() if count > 1]
    cycles = {}
    universe = sorted({r["symbol"] for r in expected_ids if r["cycle_boundary"] == anchor})
    for boundary in sorted({r["cycle_boundary"] for r in expected_ids}):
        expected_symbols = {r["symbol"] for r in expected_ids if r["cycle_boundary"] == boundary}
        seen = {symbol for b, symbol in got if b == boundary}
        state = "COMPLETE" if seen == expected_symbols else "PARTIAL" if seen else "SKIPPED"
        cycles[str(boundary)] = {"state": state, "expected_symbols": sorted(expected_symbols),
            "seen_symbols": sorted(seen), "missing_symbols": sorted(expected_symbols-seen)}
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(), "anchor_cycle": anchor,
        "anchor_time": datetime.fromtimestamp(anchor/1000, timezone.utc).isoformat(),
        "profile": "trade-5m-v2", "parameter_set": "scalping-v2-set-2", "segment": segment,
        "collector_last_boundary": health.get("last_boundary"), "universe": universe,
        "expected": len(exp), "collected": len(got), "missing": len(missing), "orphan": len(orphan),
        "duplicates": len(duplicate), "not_yet_mature": len(not_yet_mature),
        "mature_but_not_collected": len(mature_missing), "outcome_duplicates": len(outcome_duplicates),
        "ingestion_lag_seconds": {"min": min(ingestion_lag) if ingestion_lag else None,
            "p50": percentile(ingestion_lag,.5), "p75": percentile(ingestion_lag,.75),
            "p90": percentile(ingestion_lag,.9), "p95": percentile(ingestion_lag,.95),
            "p99": percentile(ingestion_lag,.99), "max": max(ingestion_lag) if ingestion_lag else None},
        "fresh_ingestion_lag_seconds": {"from_boundary": args.fresh_from_boundary,
            "count": len(fresh_ingestion_lag), "p50": percentile(fresh_ingestion_lag,.5),
            "p95": percentile(fresh_ingestion_lag,.95), "p99": percentile(fresh_ingestion_lag,.99),
            "max": max(fresh_ingestion_lag) if fresh_ingestion_lag else None},
        "skipped_cycles": sum(v["state"]=="SKIPPED" for v in cycles.values()),
        "partial_cycles": sum(v["state"]=="PARTIAL" for v in cycles.values()),
        "complete_cycles": sum(v["state"]=="COMPLETE" for v in cycles.values()),
        "missing_ids": missing, "orphan_ids": orphan, "duplicate_ids": duplicate,
        "mature_missing_ids": mature_missing, "outcome_duplicate_ids": outcome_duplicates,
        "cycles": cycles,
    }
    (args.output_dir / "TASK_A_REPORT.json").write_text(json.dumps(summary, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in summary.items() if k not in {"cycles","missing_ids","orphan_ids","duplicate_ids","mature_missing_ids"}}, indent=2))


if __name__ == "__main__":
    main()
