from __future__ import annotations

import json
import statistics
import time
import tracemalloc
from copy import deepcopy
from dataclasses import asdict, replace

import pytest

from app.engine_paper.reconciliation import (
    PAPER_TABLES,
    PaperReadOnlyReconciliationService,
    PaperReconciliationOutcome,
    PaperReconciliationScope,
    safe_report,
)
from .conftest import FakeReader, canonical_rows


IDENTITY_FIELDS = {
    "command_id", "order_id", "fill_id", "position_id", "cursor_id",
    "exit_decision_id", "order_event_id", "journal_entry_id",
    "entry_order_id", "entry_fill_id", "exit_fill_id",
}


def dataset(size: int):
    combined = {table: [] for table in PAPER_TABLES}
    for index in range(size):
        graph = canonical_rows()
        identities = {
            str(row[field])
            for table in PAPER_TABLES for row in graph[table]
            for field in IDENTITY_FIELDS
            if row.get(field) is not None
        }
        mapping = {value: f"{value}-{index}" for value in identities}
        for table in PAPER_TABLES:
            for row in graph[table]:
                clone = deepcopy(row)
                for field in IDENTITY_FIELDS:
                    if clone.get(field) in mapping:
                        clone[field] = mapping[clone[field]]
                if "idempotency_key" in clone:
                    clone["idempotency_key"] = f"{clone['idempotency_key']}-{index}"
                if "symbol" in clone:
                    clone["symbol"] = f"S{index:03d}USDT"
                combined[table].append(clone)
    return combined


def execute(rows, request):
    return PaperReadOnlyReconciliationService(lambda _request: FakeReader(rows)).reconcile(request)


@pytest.mark.parametrize("scope_kind", ["position", "command", "symbol"])
@pytest.mark.parametrize("index", range(20))
def test_single_entity_scopes_return_exact_linked_graph(scope_kind, index, reconcile_request):
    rows = dataset(20)
    kwargs = {
        "position": {"position_id": f"position-1-{index}"},
        "command": {"command_id": f"command-1-{index}"},
        "symbol": {"symbol": f"S{index:03d}USDT"},
    }[scope_kind]
    scope = PaperReconciliationScope(**kwargs, max_positions=20, max_orders=40, max_fills=40, max_events=160, max_journal_rows=240, max_cursors=20, max_exit_decisions=20, max_commands=20)
    result = execute(rows, replace(reconcile_request, scope=scope))
    assert result.outcome is PaperReconciliationOutcome.HEALTHY
    assert asdict(result.entity_summary) == {
        "commands": 1, "orders": 2, "fills": 2, "positions": 1,
        "cursors": 1, "exit_decisions": 1, "events": 8, "journal_rows": 12,
    }


def _percentile(values, percentile):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * percentile))]


@pytest.mark.parametrize("size,inconsistent", [(1, False), (100, False), (100, True)])
def test_isolated_performance_bounds(size, inconsistent, reconcile_request):
    rows = dataset(size)
    if inconsistent:
        rows["paper_exit_evaluation_cursors"].pop()
        rows["paper_positions"][-1]["state"] = "OPEN"
        rows["paper_positions"][-1].update(exit_fill_id=None, exit_fees=0, realized_pnl=0, closed_at=None)
    scope = PaperReconciliationScope(
        full_isolated_fixture=True, max_positions=100, max_orders=200,
        max_fills=200, max_events=800, max_journal_rows=1200,
        max_cursors=100, max_exit_decisions=100, max_commands=100,
    )
    request = replace(reconcile_request, scope=scope)
    durations = []
    tracemalloc.start()
    result = None
    for _ in range(30):
        started = time.perf_counter_ns()
        result = execute(rows, request)
        durations.append((time.perf_counter_ns() - started) / 1_000_000)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert result is not None
    assert result.outcome is (
        PaperReconciliationOutcome.INCONSISTENT if inconsistent
        else PaperReconciliationOutcome.HEALTHY
    )
    metrics = {
        "size": size, "inconsistent": inconsistent,
        "p50_ms": statistics.median(durations), "p95_ms": _percentile(durations, .95),
        "p99_ms": _percentile(durations, .99), "query_count": result.query_count,
        "rows_scanned": sum(asdict(result.entity_summary).values()),
        "memory_peak_bytes": peak, "result_size_bytes": len(safe_report(result).encode()),
        "max_lock_wait": 0,
    }
    assert metrics["p99_ms"] < 2_000
    assert metrics["query_count"] == 10
    assert metrics["memory_peak_bytes"] < 64 * 1024 * 1024
    assert metrics["result_size_bytes"] < 65_536
    print(json.dumps(metrics, sort_keys=True))
