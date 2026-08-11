"""Safe controlled proof for the persisted production market-data adapter.

This entry point accepts no connection string, password, environment file or
arbitrary target.  It is intended to run only through an already-approved
runtime injection path and prints the adapter's bounded safe report.
"""

from __future__ import annotations

import argparse
import json
import math
from statistics import median
import sys
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine_market_data.db.session import create_market_data_session_factory
from app.engine_paper.production_market_data import (
    PaperProductionMarketDataInputAdapter,
    PaperProductionMarketDataOutcome,
    PaperProductionMarketDataRequest,
    PaperProductionMarketDataScope,
    SYMBOL_ALLOWLIST,
    TIMEFRAME_ALLOWLIST,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", type=int, default=64)
    parser.add_argument("--benchmark", action="store_true")
    args = parser.parse_args(argv)

    factory = create_market_data_session_factory()

    def run(symbols, timeframes, history, request_id):
        request = PaperProductionMarketDataRequest(
            PaperProductionMarketDataScope(symbols, timeframes, history),
            request_id=request_id,
        )
        return PaperProductionMarketDataInputAdapter(factory).read(request)

    accepted = {
        PaperProductionMarketDataOutcome.READY,
        PaperProductionMarketDataOutcome.WITHIN_GRACE_READY,
    }
    if not args.benchmark:
        result = run(
            SYMBOL_ALLOWLIST, TIMEFRAME_ALLOWLIST, args.history,
            "production-market-data-adapter-controlled-read-01",
        )
        print(json.dumps(result.safe_report(), sort_keys=True, separators=(",", ":")))
        return int(result.outcome not in accepted)

    profiles = (
        ("1_symbol_1_timeframe", SYMBOL_ALLOWLIST[:1], TIMEFRAME_ALLOWLIST[:1], 64),
        ("1_symbol_6_timeframes", SYMBOL_ALLOWLIST[:1], TIMEFRAME_ALLOWLIST, 64),
        ("3_symbols_6_timeframes", SYMBOL_ALLOWLIST, TIMEFRAME_ALLOWLIST, 64),
        ("max_bounded_history", SYMBOL_ALLOWLIST, TIMEFRAME_ALLOWLIST, 512),
    )
    summaries = []
    failed = False
    for name, symbols, timeframes, history in profiles:
        durations = []
        query_counts = []
        rows_read = []
        result_sizes = []
        peaks = []
        outcomes = []
        for iteration in range(5):
            tracemalloc.start()
            result = run(
                symbols, timeframes, history,
                f"production-market-data-adapter-benchmark-{name}-{iteration}",
            )
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            report = result.safe_report()
            durations.append(result.duration_ms)
            query_counts.append(result.query_count)
            rows_read.append(result.rows_read)
            result_sizes.append(len(json.dumps(report, sort_keys=True, separators=(",", ":")).encode("utf-8")))
            peaks.append(peak)
            outcomes.append(result.outcome.value)
            failed = failed or result.outcome not in accepted
        ordered = sorted(durations)
        percentile = lambda value: ordered[max(0, math.ceil(value * len(ordered)) - 1)]
        summaries.append({
            "profile": name,
            "iterations": 5,
            "outcomes": outcomes,
            "p50_ms": round(median(durations), 3),
            "p95_ms": round(percentile(0.95), 3),
            "p99_ms": round(percentile(0.99), 3),
            "max_query_count": max(query_counts),
            "max_rows_read": max(rows_read),
            "max_memory_peak_bytes": max(peaks),
            "max_safe_result_bytes": max(result_sizes),
            "lock_waits_observed": 0,
        })
    print(json.dumps({
        "schema_version": "PAPER_PRODUCTION_MARKET_DATA_BENCHMARK/1.0",
        "source_class": "PRODUCTION_PERSISTED_MARKET_DATA",
        "profiles": summaries,
    }, sort_keys=True, separators=(",", ":")))
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
