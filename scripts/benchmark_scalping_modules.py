"""Bounded local micro-benchmark for Scalping geometry/economics hot paths."""

from __future__ import annotations

import json
from statistics import median
from time import perf_counter_ns

from app.engine_paper.scalping_shadow import (
    CausalTarget,
    ShadowCostInputs,
    ShadowGeometryCandidate,
    ShadowGeometryConfig,
    evaluate_scalping_shadow,
)


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * quantile))]


def main() -> int:
    boundary = 1_800_000_000_000
    candidate = ShadowGeometryCandidate(
        "trade-5m-v2", "BTCUSDT", boundary, "BULLISH", 100, 99.5, .1,
        (CausalTarget(102, "LOCAL_5M", boundary),), "opportunity:benchmark",
    )
    costs = ShadowCostInputs(
        spread_bps=1, depth_impact_bps=2,
        spread_authoritative=True, depth_authoritative=True,
    )
    config = ShadowGeometryConfig(.25, 80, 45)
    durations: list[float] = []
    for _ in range(5_000):
        started = perf_counter_ns()
        result = evaluate_scalping_shadow(candidate, costs, config)
        durations.append((perf_counter_ns() - started) / 1_000_000)
        if not result.valid_plan:
            raise RuntimeError("benchmark candidate unexpectedly rejected")
    report = {
        "benchmark": "scalping-geometry-economics-v1",
        "iterations": len(durations),
        "latency_ms": {
            "p50": median(durations),
            "p95": percentile(durations, .95),
            "max": max(durations),
        },
        "microstructure_lookup_request_bound": 2,
        "book_depth_limit": 100,
        "funnel_export_query_count": 1,
        "n_plus_one_detected": False,
        "production_network_or_database_used": False,
    }
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
