"""Deterministically finalize the YAML-authority 72h PAPER observation window.

The command is read-only with respect to production state.  It reads the
persisted soak marker, PostgreSQL cycle/result rows, and append-only collector
parts, then writes one bounded JSON report.  It never promotes a parameter set
or enables trading.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MARKER = ROOT / "artifacts/yaml_authority_migration_01/soak_marker.json"
DEFAULT_COLLECTOR = ROOT / "reports/calibration/scalping-v2-probability-set2"
DEFAULT_OUTPUT = ROOT / "artifacts/yaml_authority_migration_01/soak_final"
POSTGRES_CONTAINER = "traders-ml-postgres-1"
PROFILE = "trade-5m-v2"
SOAK_BOUNDARIES = 864
OUTCOME_MATURITY_MS = 1_140_000


def _psql(sql: str) -> list[str]:
    result = subprocess.run(
        ["docker", "exec", POSTGRES_CONTAINER, "psql", "-U", "traders_ml",
         "-d", "traders_ml", "-AtX", "-c", sql],
        check=True, capture_output=True, text=True, encoding="utf-8",
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def _load_parts(root: Path, kind: str) -> Iterable[dict[str, Any]]:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    for part in manifest["parts"]:
        if part["kind"] != kind:
            continue
        path = root / part["path"]
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    yield json.loads(line)


def _distribution(values: Iterable[float | int | None]) -> dict[str, Any]:
    usable = sorted(float(value) for value in values if value is not None)
    if not usable:
        return {"count": 0, "min": None, "p50": None, "p95": None, "max": None}

    def percentile(q: float) -> float:
        index = (len(usable) - 1) * q
        lower = int(index)
        upper = min(lower + 1, len(usable) - 1)
        return usable[lower] + (usable[upper] - usable[lower]) * (index - lower)

    return {"count": len(usable), "min": usable[0], "p50": percentile(.5),
            "p95": percentile(.95), "max": usable[-1]}


def _deep(value: Any, *keys: str) -> Any:
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _expected(start: int) -> tuple[list[int], set[tuple[int, str]], dict[str, int]]:
    boundaries = [int(value) for value in _psql(
        "SELECT DISTINCT closed_until_ms FROM online_pipeline_runs "
        f"WHERE trade_profile_id='{PROFILE}' AND closed_until_ms>={start} "
        f"ORDER BY closed_until_ms LIMIT {SOAK_BOUNDARIES}"
    )]
    if not boundaries:
        return [], set(), {}
    end = boundaries[-1]
    identities = {
        (int(boundary), symbol) for boundary, symbol in (
            line.split("|", 1) for line in _psql(
                "SELECT closed_until_ms,symbol FROM online_pipeline_runs "
                f"WHERE trade_profile_id='{PROFILE}' AND closed_until_ms BETWEEN {start} AND {end}"
            )
        )
    }
    hashes = dict(line.split("|", 1) for line in _psql(
        "SELECT coalesce(res.paper_payload_json::jsonb#>>"
        "'{frozen_parameter_snapshot,resolved_config_hash}','MISSING'),count(*) "
        "FROM online_pipeline_runs run JOIN online_pipeline_results res USING(run_id) "
        f"WHERE run.trade_profile_id='{PROFILE}' AND run.closed_until_ms BETWEEN {start} AND {end} "
        "GROUP BY 1 ORDER BY 1"
    ))
    return boundaries, identities, {key: int(value) for key, value in hashes.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--marker", type=Path, default=DEFAULT_MARKER)
    parser.add_argument("--collector-dir", type=Path, default=DEFAULT_COLLECTOR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    marker = json.loads(args.marker.read_text(encoding="utf-8"))
    start = int(marker["SOAK_START_CYCLE"])
    boundaries, expected, hashes = _expected(start)
    end = boundaries[-1] if boundaries else start

    observations: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in _load_parts(args.collector_dir, "observations"):
        identity = row.get("identity") or {}
        boundary = identity.get("boundary_time_ms")
        symbol = identity.get("symbol")
        if boundary is not None and symbol and start <= int(boundary) <= end:
            observations[(int(boundary), str(symbol))].append(row)
    outcomes = [
        row for row in _load_parts(args.collector_dir, "outcomes")
        if start <= int(_deep(row, "frozen_opportunity", "boundary_time_ms") or -1) <= end
    ]
    outcome_counts = Counter(str(row.get("observation_id")) for row in outcomes)
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    mature = [row for rows in observations.values() for row in rows[:1]
              if int(_deep(row, "outcome_followup", "followup_due_ms") or now_ms + 1)
              <= now_ms - OUTCOME_MATURITY_MS]
    mature_missing = [row.get("observation_id") for row in mature
                      if outcome_counts[str(row.get("observation_id"))] == 0]
    predecision = sum(
        row.get("entry_status") == "ENTERED"
        and row.get("entry_candle_open_time_ms") is not None
        and _deep(row, "frozen_opportunity", "entry_decision_time_ms") is not None
        and int(row["entry_candle_open_time_ms"])
        < int(row["frozen_opportunity"]["entry_decision_time_ms"])
        for row in outcomes
    )

    from observe_5m_scalping_calibration import load_rows
    from app.engine_observation.scalping_calibration import aggregate

    source_rows = load_rows(start, SOAK_BOUNDARIES) if boundaries else []
    aggregate_report = aggregate(source_rows) if source_rows else {}
    analysis = [row.get("analysis") or {} for row in source_rows]
    impulse_distribution = Counter(str(row.get("impulse_phase") or "UNKNOWN") for row in analysis)
    regime_distribution = Counter(str(row.get("regime") or "UNKNOWN") for row in analysis)

    watermark = _psql(
        "SELECT max(id),max(closed_until_ms),count(*) FROM online_pipeline_runs "
        "WHERE trade_profile_id='trade-15m-v1'"
    )[0].split("|")
    initial = marker["LEGACY_15M_WATERMARK"]
    new_15m_rows = int(watermark[2]) - int(initial["row_count"])
    missing = sorted(expected - set(observations))
    duplicates = sorted(key for key, values in observations.items() if len(values) > 1)
    expected_hash = marker["SOAK_CONFIG_HASH"]
    config_drift = hashes != {expected_hash: len(expected)} if expected else False
    complete_window = len(boundaries) == SOAK_BOUNDARIES
    pass_state = all((complete_window, not missing, not duplicates, not mature_missing,
                      not predecision, not config_drift, new_15m_rows == 0))
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "task_status": "PASS" if pass_state else "INCOMPLETE_OR_FAIL",
        "promotion_authorized": False,
        "marker": marker,
        "window": {"start_cycle": start, "end_cycle": end,
                   "observed_boundaries": len(boundaries), "required_boundaries": SOAK_BOUNDARIES},
        "collector": {"expected": len(expected), "collected": len(set(observations)),
                      "missing": len(missing), "duplicates": len(duplicates),
                      "mature_missing": len(mature_missing), "predecision_violations": predecision,
                      "v3_outcome_count": len(outcomes),
                      "outcome_duplicates": sum(count > 1 for count in outcome_counts.values())},
        "distributions": {"regime": dict(regime_distribution),
                          "impulse": dict(impulse_distribution),
                          "gross_rr": aggregate_report.get("gross_rr"),
                          "net_rr": aggregate_report.get("net_rr")},
        "economics": {"trades": _deep(aggregate_report, "funnel", "positions"),
                      "closed_trades": _deep(aggregate_report, "funnel", "closed_positions"),
                      "net_pnl_per_day": _deep(aggregate_report, "business_kpis", "net_pnl_per_day"),
                      "profit_factor": _deep(aggregate_report, "business_kpis", "profit_factor"),
                      "max_drawdown": _deep(aggregate_report, "business_kpis", "max_drawdown")},
        "config_identity": {"expected_hash": expected_hash, "observed_hashes": hashes,
                            "drift": config_drift},
        "legacy_15m": {"initial": initial,
                       "final": {"max_id": int(watermark[0]),
                                 "max_boundary": int(watermark[1]), "row_count": int(watermark[2])},
                       "new_rows": new_15m_rows},
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    path = args.output_dir / "TRADERS_YAML_AUTHORITY_72H_SOAK_FINAL.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(path), "task_status": report["task_status"],
                      "observed_boundaries": len(boundaries), "required_boundaries": SOAK_BOUNDARIES,
                      "promotion_authorized": False}, sort_keys=True))
    return 0 if pass_state else 2


if __name__ == "__main__":
    raise SystemExit(main())
