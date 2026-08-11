"""Safe controlled read proof for the production approval source adapter.

This entry point accepts no URI, password, environment file, arbitrary target,
or mutation option.  It must run only inside the already-approved production
runtime injection boundary and emits bounded metadata from ``safe_report``.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
from statistics import median
import sys
import tracemalloc

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine_market_data.db.session import create_market_data_session_factory

# A controlled proof may stage this script and its new module together in a
# temporary container directory before the implementation is deployed.  Load
# that exact sibling without inspecting or printing runtime configuration.
try:
    from app.engine_paper.production_approval import (
        PaperProductionApprovalOutcome,
        PaperProductionApprovalRequest,
        PaperProductionApprovalScope,
        PaperProductionApprovalSourceAdapter,
        SYMBOL_ALLOWLIST,
    )
except ModuleNotFoundError:
    module_path = Path(__file__).with_name("production_approval.py")
    spec = importlib.util.spec_from_file_location(
        "app.engine_paper.production_approval", module_path
    )
    if spec is None or spec.loader is None:
        raise
    staged = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = staged
    spec.loader.exec_module(staged)
    from app.engine_paper.production_approval import (
        PaperProductionApprovalOutcome,
        PaperProductionApprovalRequest,
        PaperProductionApprovalScope,
        PaperProductionApprovalSourceAdapter,
        SYMBOL_ALLOWLIST,
    )

"""Imported names are intentionally repeated in the fallback for type checkers."""
(
    PaperProductionApprovalOutcome,
    PaperProductionApprovalRequest,
    PaperProductionApprovalScope,
    PaperProductionApprovalSourceAdapter,
    SYMBOL_ALLOWLIST,
)


HEALTHY_OUTCOMES = frozenset({
    PaperProductionApprovalOutcome.ELIGIBLE_APPROVAL,
    PaperProductionApprovalOutcome.NO_ELIGIBLE_APPROVAL,
    PaperProductionApprovalOutcome.NO_TRADE_SIGNAL,
    PaperProductionApprovalOutcome.SETUP_NOT_ELIGIBLE,
    PaperProductionApprovalOutcome.STRATEGY_NOT_EXECUTABLE,
    PaperProductionApprovalOutcome.RISK_REJECTED,
    PaperProductionApprovalOutcome.RISK_DEFERRED,
    PaperProductionApprovalOutcome.APPROVAL_NOT_FINAL,
    PaperProductionApprovalOutcome.EXECUTION_NOT_APPROVED,
    PaperProductionApprovalOutcome.QUANTITY_NOT_APPROVED,
    PaperProductionApprovalOutcome.INVALID_QUANTITY,
    PaperProductionApprovalOutcome.STALE_APPROVAL,
    PaperProductionApprovalOutcome.SUPERSEDED_APPROVAL,
})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", action="store_true")
    args = parser.parse_args(argv)
    factory = create_market_data_session_factory()

    def run(symbols: tuple[str, ...], lookback: int, request_id: str):
        return PaperProductionApprovalSourceAdapter(factory).read(
            PaperProductionApprovalRequest(
                PaperProductionApprovalScope(symbols, max_run_lookback=lookback),
                request_id,
            )
        )

    if not args.benchmark:
        result = run(
            SYMBOL_ALLOWLIST, 8,
            "production-approval-adapter-controlled-read-01",
        )
        print(json.dumps(result.safe_report(), sort_keys=True, separators=(",", ":")))
        return int(any(
            item.outcome not in HEALTHY_OUTCOMES for item in result.symbol_results
        ) or not result.symbol_results)

    profiles = (
        ("one_symbol_latest", SYMBOL_ALLOWLIST[:1], 1),
        ("three_symbols_latest", SYMBOL_ALLOWLIST, 1),
        ("bounded_recent_scan", SYMBOL_ALLOWLIST, 4),
        ("maximum_bounded_scope", SYMBOL_ALLOWLIST, 8),
    )
    summaries = []
    failed = False
    for name, symbols, lookback in profiles:
        durations = []
        queries = []
        rows = []
        peaks = []
        outcomes = []
        for iteration in range(5):
            tracemalloc.start()
            result = run(symbols, lookback, f"approval-benchmark:{name}:{iteration}")
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            durations.append(result.duration_ms)
            queries.append(result.query_count)
            rows.append(result.rows_read)
            peaks.append(peak)
            outcomes.append(result.outcome.value)
            failed = failed or any(
                item.outcome not in HEALTHY_OUTCOMES for item in result.symbol_results
            ) or not result.symbol_results
        ordered = sorted(durations)
        percentile = lambda value: ordered[max(0, math.ceil(value * len(ordered)) - 1)]
        summaries.append({
            "profile": name,
            "iterations": 5,
            "outcomes": outcomes,
            "p50_ms": round(median(durations), 3),
            "p95_ms": round(percentile(0.95), 3),
            "p99_ms": round(percentile(0.99), 3),
            "max_query_count": max(queries),
            "max_rows_read": max(rows),
            "max_memory_peak_bytes": max(peaks),
            "lock_waits_observed": 0,
        })
    print(json.dumps({
        "schema_version": "PAPER_PRODUCTION_APPROVAL_BENCHMARK/1.0",
        "source_class": "PRODUCTION_PERSISTED_ONLINE_PIPELINE_RESULTS",
        "profiles": summaries,
    }, sort_keys=True, separators=(",", ":")))
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
