from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace

import pytest

from app.engine_paper.reconciliation import (
    EXPECTED_SCHEMA_HEAD,
    PAPER_TABLES,
    PaperReadOnlyReconciliationService,
    PaperReconciliationExitCode,
    PaperReconciliationOutcome,
    PaperReconciliationRequest,
    PaperReconciliationScope,
    safe_report,
)
from .conftest import FakeReader, canonical_rows


def run(rows, request, **reader_kwargs):
    holder = {}
    def factory(_request):
        holder["reader"] = FakeReader(rows, **reader_kwargs)
        return holder["reader"]
    result = PaperReadOnlyReconciliationService(factory, clock_ms=lambda: 10_000).reconcile(request)
    return result, holder["reader"]


@pytest.mark.parametrize("permutation", range(256))
def test_closed_canonical_graph_is_healthy_for_all_table_order_permutations(permutation, reconcile_request):
    rows = canonical_rows()
    for bit, table in enumerate(PAPER_TABLES):
        if permutation & (1 << bit):
            rows[table].reverse()
    result, reader = run(rows, reconcile_request)
    assert result.outcome is PaperReconciliationOutcome.HEALTHY
    assert result.entity_summary.commands == 1
    assert result.entity_summary.orders == 2
    assert result.entity_summary.fills == 2
    assert result.entity_summary.positions == 1
    assert result.entity_summary.cursors == 1
    assert result.entity_summary.exit_decisions == 1
    assert result.entity_summary.events == 8
    assert result.entity_summary.journal_rows == 12
    assert result.business_mutations == result.schema_mutations == 0
    assert reader.closed


def _open_graph(state="OPEN", include_close=False):
    rows = canonical_rows()
    rows["paper_positions"][0].update(
        state=state, exit_fill_id=None, exit_fees=0, realized_pnl=0, closed_at=None, version=2,
    )
    rows["paper_orders"] = rows["paper_orders"] if include_close else rows["paper_orders"][:1]
    rows["paper_fills"] = rows["paper_fills"][:1]
    rows["paper_order_events"] = rows["paper_order_events"] if include_close else rows["paper_order_events"][:4]
    rows["paper_journal_entries"] = [
        item for item in rows["paper_journal_entries"]
        if item["event_type"] not in {"PAPER_POSITION_CLOSED"}
        and (include_close or item.get("order_id") != "close-order-1")
    ]
    if not include_close:
        rows["paper_exit_decisions"] = []
    return rows


def test_healthy_approvals_only(reconcile_request):
    rows = {table: [] for table in PAPER_TABLES}
    rows["paper_execution_commands"] = canonical_rows()["paper_execution_commands"]
    assert run(rows, reconcile_request)[0].outcome is PaperReconciliationOutcome.HEALTHY


def test_healthy_entry_order_open(reconcile_request):
    rows = _open_graph()
    rows["paper_positions"] = []
    rows["paper_fills"] = []
    rows["paper_exit_evaluation_cursors"] = []
    rows["paper_order_events"] = rows["paper_order_events"][:3]
    rows["paper_orders"][0].update(state="OPEN", version=2)
    rows["paper_journal_entries"] = rows["paper_journal_entries"][:3]
    assert run(rows, reconcile_request)[0].outcome is PaperReconciliationOutcome.HEALTHY


@pytest.mark.parametrize("advanced", [False, True])
def test_healthy_position_open_cursor_states(advanced, reconcile_request):
    rows = _open_graph()
    if advanced:
        rows["paper_exit_evaluation_cursors"][0].update(last_evaluated_closed_until_ms=3_000, version=3)
    assert run(rows, reconcile_request)[0].outcome is PaperReconciliationOutcome.HEALTHY


def test_healthy_position_closing_close_order_open(reconcile_request):
    rows = _open_graph("CLOSING", include_close=True)
    rows["paper_orders"][1].update(state="OPEN", version=2)
    rows["paper_order_events"] = rows["paper_order_events"][:7]
    rows["paper_journal_entries"] = [item for item in rows["paper_journal_entries"] if item["event_type"] not in {"PAPER_ORDER_FILLED", "PAPER_POSITION_CLOSED"} or item.get("order_id") == "entry-order-1"]
    assert run(rows, reconcile_request)[0].outcome is PaperReconciliationOutcome.HEALTHY


def test_healthy_position_closed(reconcile_request):
    assert run(canonical_rows(), reconcile_request)[0].outcome is PaperReconciliationOutcome.HEALTHY


def _negative_cases():
    cases = []
    def case(name, code, mutate): cases.append(pytest.param(mutate, code, id=name))
    case("open-without-cursor", "OPEN_WITHOUT_CURSOR", lambda r: (r["paper_positions"][0].update(state="OPEN", exit_fill_id=None, exit_fees=0, realized_pnl=0, closed_at=None), r["paper_exit_evaluation_cursors"].clear()))
    case("open-without-entry-fill", "OPEN_WITHOUT_ENTRY_FILL", lambda r: r["paper_positions"][0].update(entry_fill_id="missing-fill"))
    case("closing-without-exit-decision", "CLOSING_WITHOUT_EXIT_DECISION", lambda r: (r["paper_positions"][0].update(state="CLOSING", exit_fill_id=None, exit_fees=0, realized_pnl=0, closed_at=None), r["paper_exit_decisions"].clear()))
    case("closing-without-close-order", "CLOSING_WITHOUT_CLOSE_ORDER", lambda r: (r["paper_positions"][0].update(state="CLOSING", exit_fill_id=None, exit_fees=0, realized_pnl=0, closed_at=None), r["paper_orders"].pop(), r["paper_fills"].pop()))
    case("closed-without-close-fill", "CLOSED_WITHOUT_CLOSE_FILL", lambda r: r["paper_positions"][0].update(exit_fill_id="missing-close-fill"))
    case("duplicate-fill", "DUPLICATE_FILL", lambda r: r["paper_fills"].append(deepcopy(r["paper_fills"][0])))
    case("duplicate-semantic-order", "DUPLICATE_SEMANTIC_ORDER", lambda r: r["paper_orders"][1].update(idempotency_key=r["paper_orders"][0]["idempotency_key"]))
    case("duplicate-terminal-journal", "DUPLICATE_TERMINAL_JOURNAL_ACCOUNTING", lambda r: r["paper_journal_entries"].append({**r["paper_journal_entries"][-1], "journal_entry_id": "journal-terminal-duplicate"}))
    case("double-fee", "DOUBLE_FEE", lambda r: r["paper_journal_entries"].append({**r["paper_journal_entries"][-1], "journal_entry_id": "journal-fee-duplicate"}))
    case("double-pnl", "DOUBLE_PNL", lambda r: r["paper_journal_entries"].append({**r["paper_journal_entries"][-1], "journal_entry_id": "journal-pnl-duplicate"}))
    case("orphan-fill", "ORPHAN_FILL", lambda r: r["paper_fills"][0].update(order_id="missing-order"))
    case("orphan-order-event", "ORPHAN_ORDER_EVENT", lambda r: r["paper_order_events"][0].update(order_id="missing-order"))
    case("orphan-exit-decision", "ORPHAN_EXIT_DECISION", lambda r: r["paper_exit_decisions"][0].update(position_id="missing-position"))
    case("orphan-cursor", "ORPHAN_CURSOR", lambda r: r["paper_exit_evaluation_cursors"][0].update(position_id="missing-position"))
    case("orphan-journal", "ORPHAN_JOURNAL", lambda r: r["paper_journal_entries"].append({"journal_entry_id": "orphan-journal", "event_type": "PAPER_COMMAND_CREATED", "command_id": "missing", "order_id": "missing", "fill_id": "missing", "position_id": "missing", "exit_decision_id": "missing"}))
    case("cursor-regression", "CURSOR_REGRESSION", lambda r: r["paper_exit_evaluation_cursors"][0].update(last_evaluated_closed_until_ms=999))
    case("future-cursor", "FUTURE_CURSOR", lambda r: r["paper_exit_evaluation_cursors"][0].update(last_evaluated_closed_until_ms=10_001))
    case("invalid-event-order", "INVALID_EVENT_ORDERING", lambda r: r["paper_order_events"][1].update(from_state="OPEN"))
    case("version-regression", "VERSION_REGRESSION", lambda r: r["paper_order_events"][2].update(aggregate_version=1))
    case("causal-id-mismatch", "CAUSAL_ID_MISMATCH", lambda r: r["paper_orders"][0].update(command_id="missing-command"))
    case("wrong-close-lineage", "WRONG_CLOSE_LINEAGE", lambda r: r["paper_journal_entries"][10].update(order_id="entry-order-1"))
    case("impossible-order-position", "IMPOSSIBLE_ORDER_POSITION_COMBINATION", lambda r: r["paper_positions"][0].update(closed_at=None))
    case("missing-required-event", "MISSING_REQUIRED_EVENT", lambda r: r["paper_order_events"].pop(1))
    return cases


@pytest.mark.parametrize("mutate,expected_code", _negative_cases())
def test_negative_fixture_matrix(mutate, expected_code, reconcile_request):
    rows = canonical_rows()
    mutate(rows)
    result, _ = run(rows, reconcile_request)
    assert result.outcome is PaperReconciliationOutcome.INCONSISTENT
    assert expected_code in {finding.code for finding in result.findings}


@pytest.mark.parametrize("revision", [f"0008-engine-{index}" for index in range(100)])
def test_schema_gate_fails_closed_with_zero_paper_queries(revision, reconcile_request):
    result, reader = run(canonical_rows(), reconcile_request, schema_head=revision)
    assert result.outcome is PaperReconciliationOutcome.PAPER_SCHEMA_NOT_DEPLOYED
    assert result.exit_code is PaperReconciliationExitCode.PAPER_SCHEMA_NOT_DEPLOYED
    assert result.paper_table_queries == reader.paper_table_queries == 0
    assert result.business_mutations == result.schema_mutations == 0


@pytest.mark.parametrize("table", PAPER_TABLES)
def test_fault_during_each_read_phase_is_safe_failure_never_healthy(table, reconcile_request):
    result, _ = run(canonical_rows(), reconcile_request, fail_table=table)
    assert result.outcome is PaperReconciliationOutcome.SAFE_FAILURE
    assert result.business_mutations == result.schema_mutations == 0


@pytest.mark.parametrize("phase", ["before_target_validation", "after_schema_gate", "during_invariant_evaluation", "during_rendering"])
def test_fault_injection_returns_typed_safe_failure(phase, reconcile_request):
    def fault(current):
        if current == phase:
            raise RuntimeError("injected")
    result = PaperReadOnlyReconciliationService(lambda _: FakeReader(), fault_injector=fault).reconcile(reconcile_request)
    assert result.outcome is PaperReconciliationOutcome.SAFE_FAILURE


def test_read_only_policy_failure_is_typed(reconcile_request):
    result, _ = run(canonical_rows(), reconcile_request, read_only=False)
    assert result.outcome is PaperReconciliationOutcome.READ_ONLY_POLICY_VIOLATION
    assert result.paper_table_queries == 0


@pytest.mark.parametrize("table,limit_field", [
    ("paper_execution_commands", "max_commands"), ("paper_orders", "max_orders"),
    ("paper_fills", "max_fills"), ("paper_positions", "max_positions"),
    ("paper_exit_evaluation_cursors", "max_cursors"),
    ("paper_exit_decisions", "max_exit_decisions"),
    ("paper_order_events", "max_events"), ("paper_journal_entries", "max_journal_rows"),
])
def test_each_entity_limit_fails_closed_without_truncation(table, limit_field, reconcile_request):
    rows = canonical_rows()
    rows[table].append(deepcopy(rows[table][0]))
    limited = replace(reconcile_request, scope=replace(reconcile_request.scope, **{limit_field: 1}))
    result, _ = run(rows, limited)
    assert result.outcome is PaperReconciliationOutcome.BOUNDED_LIMIT_EXCEEDED


@pytest.mark.parametrize("outcome", list(PaperReconciliationOutcome))
@pytest.mark.parametrize("repeat", range(8))
def test_safe_report_and_exit_codes_are_stable(outcome, repeat, reconcile_request):
    result, _ = run(canonical_rows(), reconcile_request)
    changed = replace(result, outcome=outcome, reason_code=f"SAFE_{repeat}")
    payload = json.loads(safe_report(changed))
    assert payload["outcome"] == outcome.value
    assert int(changed.exit_code) in {0, 10, 11, 12, 13, 14, 15, 16}
    forbidden = ("uri", "password", "credential", "traceback", "raw_sql")
    assert not any(token in safe_report(changed).lower() for token in forbidden)


@pytest.mark.parametrize("cancel_at", range(1, 11))
def test_cancellation_between_bounded_phases_never_returns_healthy(cancel_at, reconcile_request):
    calls = 0
    def cancelled():
        nonlocal calls
        calls += 1
        return calls >= cancel_at
    result = PaperReadOnlyReconciliationService(lambda _: FakeReader(), cancellation_requested=cancelled).reconcile(reconcile_request)
    assert result.outcome in {PaperReconciliationOutcome.CANCELLED, PaperReconciliationOutcome.HEALTHY}
    if calls >= cancel_at:
        assert result.outcome is PaperReconciliationOutcome.CANCELLED


def test_target_class_rejected_before_reader_resolution(reconcile_request):
    called = False
    def factory(_):
        nonlocal called
        called = True
        return FakeReader()
    result = PaperReadOnlyReconciliationService(factory).reconcile(replace(reconcile_request, target_class="LIVE"))
    assert result.outcome is PaperReconciliationOutcome.TARGET_REJECTED
    assert not called


def test_safe_report_contains_only_allowlisted_shape(reconcile_request):
    payload = json.loads(safe_report(run(canonical_rows(), reconcile_request)[0]))
    assert set(payload) == {
        "schema_version", "request_id", "target_class", "schema_head", "scope",
        "outcome", "entity_counts", "severity_counts", "finding_codes", "safe_ids",
        "read_only", "query_count", "paper_table_queries", "duration_ms",
        "correlation_id", "reason_code",
    }
