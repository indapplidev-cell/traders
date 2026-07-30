from __future__ import annotations

from dataclasses import replace

import pytest

from app.engine_paper.controlled_worker import (
    MAX_STAGES_PER_CYCLE,
    PAPER_LIFECYCLE_CYCLE_CONTRACT_VERSION,
    PaperLifecycleCycleOutcome,
    PaperLifecycleCycleScope,
    PaperLifecycleGraph,
    PaperLifecycleOrderNode,
    PaperLifecycleState,
    classify_paper_lifecycle_state,
)
from app.engine_safety import ExecutionMode, PaperEventType, PaperOrderState

from .conftest import make_cycle, make_worker


VALID_STATES = (
    ("empty", PaperLifecycleState.APPROVALS_ONLY),
    ("entry_open", PaperLifecycleState.ENTRY_ORDER_OPEN),
    ("position_open", PaperLifecycleState.POSITION_OPEN_CURSOR_READY),
    (
        "position_closing",
        PaperLifecycleState.POSITION_CLOSING_CLOSE_ORDER_OPEN,
    ),
    ("position_closed", PaperLifecycleState.POSITION_CLOSED),
)


@pytest.mark.parametrize(("graph_name", "expected"), VALID_STATES)
def test_classifier_accepts_each_exact_lifecycle_graph(
    lifecycle_graphs, graph_name, expected
):
    assert classify_paper_lifecycle_state(getattr(lifecycle_graphs, graph_name)) is expected


@pytest.mark.parametrize(("graph_name", "expected"), VALID_STATES)
def test_classifier_is_repeatable_without_mutating_graph(
    lifecycle_graphs, graph_name, expected
):
    graph = getattr(lifecycle_graphs, graph_name)
    before = repr(graph)
    assert {classify_paper_lifecycle_state(graph) for _ in range(25)} == {expected}
    assert repr(graph) == before


def _structural_mutations(graphs):
    g = graphs
    bad_command = replace(g.command, command_id="command:worker:other")
    bad_entry_command = replace(
        g.entry_open.orders[0].order, command_id="command:worker:other"
    )
    bad_entry_symbol = replace(g.entry_open.orders[0].order, symbol="ETHUSDT")
    bad_cursor_position = replace(g.cursor, position_id="position:worker:other")
    bad_cursor_policy = replace(g.cursor, evaluation_policy_id="policy:worker:other")
    bad_cursor_symbol = replace(g.cursor, symbol="ETHUSDT")
    bad_cursor_boundary = replace(
        g.cursor,
        position_opened_closed_until_ms=g.cursor.position_opened_closed_until_ms
        + 60_000,
        last_evaluated_closed_until_ms=g.cursor.last_evaluated_closed_until_ms
        + 60_000,
    )
    bad_fill_order = replace(g.entry_fill, order_id="order:worker:other")
    bad_position_order = replace(g.position, entry_order_id="order:worker:other")
    bad_position_fill = replace(g.position, entry_fill_id="fill:worker:other")
    bad_decision_position = replace(
        g.decision, position_id="position:worker:other"
    )
    bad_decision_boundary = replace(
        g.decision, source_closed_until_ms=g.decision.source_closed_until_ms + 60_000
    )
    return (
        replace(g.empty, bounded_limit_reached=True),
        replace(g.empty, command=g.command),
        replace(g.entry_open, command=None),
        replace(g.entry_open, command=bad_command),
        replace(g.entry_open, command_id="command:worker:other"),
        replace(g.entry_open, orders=()),
        replace(
            g.entry_open,
            orders=(PaperLifecycleOrderNode("", g.entry_open.orders[0].order),),
        ),
        replace(
            g.entry_open,
            orders=(PaperLifecycleOrderNode("UNKNOWN", g.entry_open.orders[0].order),),
        ),
        replace(
            g.entry_open,
            orders=(PaperLifecycleOrderNode("EXIT", g.entry_open.orders[0].order),),
        ),
        replace(
            g.entry_open,
            orders=(
                g.entry_open.orders[0],
                PaperLifecycleOrderNode("ENTRY", g.entry_open.orders[0].order),
            ),
        ),
        replace(
            g.entry_open,
            orders=(PaperLifecycleOrderNode("ENTRY", bad_entry_command),),
        ),
        replace(
            g.entry_open,
            orders=(PaperLifecycleOrderNode("ENTRY", bad_entry_symbol),),
        ),
        replace(g.entry_open, fills=(g.entry_fill,)),
        replace(g.entry_open, positions=(g.position,)),
        replace(g.entry_open, cursors=(g.cursor,)),
        replace(g.entry_open, exit_decisions=(g.decision,)),
        replace(g.entry_open, order_events=g.entry_open.order_events[:-1]),
        replace(g.entry_open, journal=g.entry_open.journal[:-1]),
        replace(g.position_open, fills=()),
        replace(g.position_open, positions=()),
        replace(g.position_open, cursors=()),
        replace(g.position_open, cursors=(g.cursor, g.cursor)),
        replace(g.position_open, cursors=(bad_cursor_position,)),
        replace(g.position_open, cursors=(bad_cursor_policy,)),
        replace(g.position_open, cursors=(bad_cursor_symbol,)),
        replace(g.position_open, cursors=(bad_cursor_boundary,)),
        replace(g.position_open, fills=(bad_fill_order,)),
        replace(g.position_open, positions=(bad_position_order,)),
        replace(g.position_open, positions=(bad_position_fill,)),
        replace(g.position_open, exit_decisions=(g.decision,)),
        replace(g.position_open, journal=g.position_open.journal[:-1]),
        replace(g.position_open, order_events=g.position_open.order_events[:-1]),
        replace(g.position_closing, exit_decisions=()),
        replace(g.position_closing, orders=g.position_closing.orders[:1]),
        replace(g.position_closing, exit_decisions=(bad_decision_position,)),
        replace(g.position_closing, exit_decisions=(bad_decision_boundary,)),
        replace(g.position_closing, cursors=(g.cursor,)),
        replace(g.position_closing, fills=(g.entry_fill, g.close_fill)),
        replace(
            g.position_closing,
            orders=(
                g.position_closing.orders[0],
                PaperLifecycleOrderNode(
                    "EXIT",
                    replace(g.position_closing.orders[1].order, state=PaperOrderState.FAILED),
                ),
            ),
        ),
        replace(g.position_closing, journal=g.position_closing.journal[:-1]),
        replace(g.position_closing, order_events=g.position_closing.order_events[:-1]),
        replace(g.position_closed, fills=(g.entry_fill,)),
        replace(g.position_closed, exit_decisions=()),
        replace(g.position_closed, cursors=()),
        replace(g.position_closed, journal=g.position_closed.journal[:-1]),
        replace(g.position_closed, order_events=g.position_closed.order_events[:-1]),
        replace(g.position_closed, fills=(g.entry_fill, g.close_fill, g.close_fill)),
    )


@pytest.mark.parametrize("mutation_index", range(47))
def test_classifier_rejects_each_structural_inconsistency(
    lifecycle_graphs, mutation_index
):
    graph = _structural_mutations(lifecycle_graphs)[mutation_index]
    assert classify_paper_lifecycle_state(graph) is PaperLifecycleState.INCONSISTENT


@pytest.mark.parametrize("suffix", range(40))
def test_classifier_rejects_wrong_exact_command_identity(lifecycle_graphs, suffix):
    graph = replace(
        lifecycle_graphs.entry_open, command_id=f"command:wrong:{suffix}"
    )
    assert classify_paper_lifecycle_state(graph) is PaperLifecycleState.INCONSISTENT


@pytest.mark.parametrize("suffix", range(40))
def test_classifier_rejects_wrong_cursor_position_identity(lifecycle_graphs, suffix):
    cursor = replace(
        lifecycle_graphs.cursor, position_id=f"position:wrong:{suffix}"
    )
    graph = replace(lifecycle_graphs.position_open, cursors=(cursor,))
    assert classify_paper_lifecycle_state(graph) is PaperLifecycleState.INCONSISTENT


@pytest.mark.parametrize("event_index", range(24))
def test_classifier_rejects_extra_audit_material(lifecycle_graphs, event_index):
    template = lifecycle_graphs.entry_open.journal[event_index % 4]
    extra = replace(template, event_id=f"journal:extra:{event_index}")
    graph = replace(
        lifecycle_graphs.entry_open,
        journal=(*lifecycle_graphs.entry_open.journal, extra),
    )
    assert classify_paper_lifecycle_state(graph) is PaperLifecycleState.INCONSISTENT


UNKNOWN_MODES = (
    None,
    "",
    "UNKNOWN",
    "paper",
    "live",
    0,
    1,
    object(),
    *tuple(f"UNKNOWN_MODE_{index}" for index in range(64)),
)


@pytest.mark.parametrize("mode", UNKNOWN_MODES)
def test_unknown_execution_modes_fail_before_graph_load(lifecycle_graphs, mode):
    request = make_cycle(lifecycle_graphs.command.command_id, execution_mode=mode)
    result = make_worker(lifecycle_graphs.empty).run_cycle(request)
    assert result.outcome is PaperLifecycleCycleOutcome.MODE_UNKNOWN
    assert result.stages_attempted == 0


@pytest.mark.parametrize(
    ("mode", "expected"),
    (
        (ExecutionMode.OFF, PaperLifecycleCycleOutcome.MODE_OFF),
        (ExecutionMode.LIVE, PaperLifecycleCycleOutcome.MODE_LIVE_FORBIDDEN),
    ),
)
def test_off_and_live_are_denied_with_zero_mutation(lifecycle_graphs, mode, expected):
    result = make_worker(lifecycle_graphs.empty).run_cycle(
        make_cycle(lifecycle_graphs.command.command_id, execution_mode=mode)
    )
    assert result.outcome is expected
    assert result.stage_trace == ()


@pytest.mark.parametrize(
    "authorization", (False, None, 0, 1, "", "true", (), [], {}, object())
)
def test_missing_or_non_boolean_authorization_is_denied(
    lifecycle_graphs, authorization
):
    result = make_worker(lifecycle_graphs.empty).run_cycle(
        make_cycle(
            lifecycle_graphs.command.command_id,
            explicit_paper_authorization=authorization,
        )
    )
    assert result.outcome is PaperLifecycleCycleOutcome.PAPER_AUTHORIZATION_MISSING


@pytest.mark.parametrize(
    "scope", (None, "", "ONE", "UNBOUNDED", 0, 1, object(), *(f"SCOPE_{i}" for i in range(24)))
)
def test_unknown_scopes_are_denied(lifecycle_graphs, scope):
    result = make_worker(lifecycle_graphs.empty).run_cycle(
        make_cycle(lifecycle_graphs.command.command_id, scope=scope)
    )
    assert result.outcome is PaperLifecycleCycleOutcome.INVALID_CYCLE_SCOPE


@pytest.mark.parametrize("max_stages", (-10, -1, 0, 2, 3, 4, 5, 100))
def test_one_step_scope_requires_exactly_one_stage(lifecycle_graphs, max_stages):
    result = make_worker(lifecycle_graphs.empty).run_cycle(
        make_cycle(lifecycle_graphs.command.command_id, max_stages=max_stages)
    )
    assert result.outcome is PaperLifecycleCycleOutcome.INVALID_CYCLE_SCOPE


@pytest.mark.parametrize("max_stages", (-5, -1, 0, 5, 6, 100))
def test_multi_stage_scope_honors_hard_bound(lifecycle_graphs, max_stages):
    result = make_worker(lifecycle_graphs.empty).run_cycle(
        make_cycle(
            lifecycle_graphs.command.command_id,
            scope=PaperLifecycleCycleScope.ADVANCE_UNTIL_BLOCKED_WITHIN_REQUEST,
            max_stages=max_stages,
        )
    )
    assert result.outcome is PaperLifecycleCycleOutcome.INVALID_CYCLE_SCOPE


def test_contract_and_hard_bounds_are_explicit():
    assert PAPER_LIFECYCLE_CYCLE_CONTRACT_VERSION == "PAPER_LIFECYCLE_CYCLE_V1"
    assert MAX_STAGES_PER_CYCLE == 4
