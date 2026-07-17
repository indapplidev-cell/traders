from __future__ import annotations

import math
from statistics import mean

from .observation_models import RunRecord, jsonable


def percentile(values: list[float], p: float) -> float | None:
    if not values: return None
    values = sorted(values)
    rank = (len(values) - 1) * p
    lo, hi = math.floor(rank), math.ceil(rank)
    return values[lo] if lo == hi else values[lo] + (values[hi] - values[lo]) * (rank - lo)


def _stats(values: list[float]) -> dict:
    if not values: return {k: None for k in ("min", "p50", "p90", "p95", "p99", "max", "mean")}
    return {"min": min(values), "p50": percentile(values, .5), "p90": percentile(values, .9),
            "p95": percentile(values, .95), "p99": percentile(values, .99), "max": max(values), "mean": mean(values)}


def analyze_latency(runs: list[RunRecord]) -> dict:
    rows, negative = [], []
    for run in runs:
        if run.status != "COMPLETED" or run.started_at is None or run.finished_at is None: continue
        trigger = (run.started_at - run.closed_until_utc).total_seconds() * 1000
        processing = (run.finished_at - run.started_at).total_seconds() * 1000
        end_to_end = (run.finished_at - run.closed_until_utc).total_seconds() * 1000
        row = {"symbol": run.symbol, "closed_until_utc": run.closed_until_utc,
               "started_at": run.started_at, "finished_at": run.finished_at,
               "trigger_latency_ms": trigger, "processing_duration_ms": processing,
               "end_to_end_latency_ms": end_to_end, "final_result": run.final_result}
        rows.append(row)
        if trigger < 0: negative.append({**row, "violation": "FUTURE_BOUNDARY_PROCESSING"})
    def summary(items):
        return {metric: _stats([row[metric] for row in items]) for metric in
                ("trigger_latency_ms", "processing_duration_ms", "end_to_end_latency_ms")}
    symbols = sorted({row["symbol"] for row in rows})
    return {"aggregate": summary(rows), "by_symbol": {s: summary([r for r in rows if r["symbol"] == s]) for s in symbols},
            "slowest_windows": jsonable(sorted(rows, key=lambda r: r["end_to_end_latency_ms"], reverse=True)[:10]),
            "future_boundary_processing": jsonable(negative), "future_boundary_processing_count": len(negative)}
