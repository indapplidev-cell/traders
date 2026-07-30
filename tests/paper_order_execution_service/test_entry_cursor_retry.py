from __future__ import annotations

from dataclasses import replace
from copy import copy

import pytest

from app.engine_paper.exit_evaluation_cursor import (
    PAPER_EXIT_CURSOR_CONTRACT_VERSION,
    PAPER_EXIT_CURSOR_IDEMPOTENCY_VERSION,
    paper_exit_evaluation_cursor_id,
)
from app.engine_paper.exit_evaluator import PAPER_EXIT_EVALUATION_POLICY_ID
from app.engine_paper.order_execution_service import (
    PaperOrderExecutionOutcome,
    PaperOrderExecutionService,
)
from app.engine_safety import ExecutionMode


def _service(context):
    return PaperOrderExecutionService(lambda: context.uow, lambda: None)


@pytest.mark.parametrize("case", range(232))
def test_retry_cursor_complete_graph_identity_and_mapping_matrix(
    entry_context, case
):
    request = replace(
        entry_context.request,
        position_id=f"position:entry-cursor-retry:{case}",
        order_event_id=f"event:entry-cursor-retry:{case}:order",
        position_event_id=f"event:entry-cursor-retry:{case}:position",
        journal_entry_ids=(
            f"journal:entry-cursor-retry:{case}:order",
            f"journal:entry-cursor-retry:{case}:position",
        ),
        correlation_id=f"correlation:entry-cursor-retry:{case}",
        causation_id=f"causation:entry-cursor-retry:{case}",
    )

    actual = _service(entry_context).execute_entry(request)
    cursor = entry_context.repositories.cursor
    position = entry_context.repositories.position
    fill = entry_context.repositories.entry_fill

    assert actual.outcome is PaperOrderExecutionOutcome.ENTRY_EXECUTED
    assert actual.successful
    assert cursor is not None
    assert fill is not None
    assert position is not None
    assert cursor.contract_version == PAPER_EXIT_CURSOR_CONTRACT_VERSION
    assert PAPER_EXIT_CURSOR_IDEMPOTENCY_VERSION == "v1"
    assert cursor.position_id == position.position_id == request.position_id
    assert cursor.mode is position.mode
    assert cursor.symbol == position.symbol
    assert cursor.position_opened_closed_until_ms == fill.source_closed_until_ms
    assert cursor.last_evaluated_closed_until_ms == fill.source_closed_until_ms
    assert cursor.evaluation_policy_id == PAPER_EXIT_EVALUATION_POLICY_ID
    assert cursor.version == 0
    assert cursor.created_at == request.operation_at
    assert cursor.updated_at == request.operation_at
    assert cursor.correlation_id == request.correlation_id
    assert cursor.causation_id == fill.fill_id
    assert cursor.cursor_id == paper_exit_evaluation_cursor_id(
        position_id=position.position_id,
        mode=position.mode,
        symbol=position.symbol,
        position_opened_closed_until_ms=fill.source_closed_until_ms,
        evaluation_policy_id=PAPER_EXIT_EVALUATION_POLICY_ID,
    )
    assert actual.cursor_id == cursor.cursor_id
    assert actual.cursor_version == 0
    assert (
        actual.cursor_last_evaluated_closed_until_ms
        == fill.source_closed_until_ms
    )
    assert actual.cursor_evaluation_policy_id == PAPER_EXIT_EVALUATION_POLICY_ID


def test_retry_exact_replay_returns_cursor_complete_graph_without_mutation(
    entry_context,
):
    first = _service(entry_context).execute_entry(entry_context.request)
    first_cursor = entry_context.repositories.cursor
    first_order = entry_context.repositories.order
    first_position = entry_context.repositories.position
    first_journal = entry_context.repositories.entry_journal

    second = _service(entry_context).execute_entry(entry_context.request)

    assert first.outcome is PaperOrderExecutionOutcome.ENTRY_EXECUTED
    assert second.outcome is PaperOrderExecutionOutcome.ENTRY_ALREADY_EXECUTED
    assert second.cursor_id == first.cursor_id
    assert second.cursor_version == first.cursor_version == 0
    assert entry_context.repositories.cursor == first_cursor
    assert entry_context.repositories.order == first_order
    assert entry_context.repositories.position == first_position
    assert entry_context.repositories.entry_journal == first_journal
    assert entry_context.repositories.atomic_calls == 1


@pytest.mark.parametrize(
    "missing",
    ["cursor", "order_event", "order_journal", "position_journal"],
)
def test_retry_preexisting_partial_entry_graph_fails_closed_without_repair(
    entry_context, missing
):
    created = _service(entry_context).execute_entry(entry_context.request)
    assert created.outcome is PaperOrderExecutionOutcome.ENTRY_EXECUTED

    if missing == "cursor":
        entry_context.repositories.cursor = None
    elif missing == "order_event":
        entry_context.repositories.order_event = None
    elif missing == "order_journal":
        entry_context.repositories.entry_journal = (
            entry_context.repositories.entry_journal[1],
        )
    else:
        entry_context.repositories.entry_journal = (
            entry_context.repositories.entry_journal[0],
        )

    replay = _service(entry_context).execute_entry(entry_context.request)

    assert (
        replay.outcome
        is PaperOrderExecutionOutcome.EXISTING_ENTRY_GRAPH_INCONSISTENT
    )
    assert entry_context.repositories.atomic_calls == 1


@pytest.mark.parametrize(
    "mutation",
    ["cursor_id", "policy", "boundary", "symbol", "mode", "position_id"],
)
def test_retry_material_cursor_conflict_is_typed_and_does_not_mutate(
    entry_context, mutation
):
    created = _service(entry_context).execute_entry(entry_context.request)
    assert created.outcome is PaperOrderExecutionOutcome.ENTRY_EXECUTED
    cursor = entry_context.repositories.cursor
    assert cursor is not None

    changes = {
        "cursor_id": {"cursor_id": "paper:exit-cursor:v1:conflict"},
        "policy": {"evaluation_policy_id": "STOP_FIRST_CONSERVATIVE_CONFLICT"},
        "boundary": {
            "last_evaluated_closed_until_ms": (
                cursor.last_evaluated_closed_until_ms + 60_000
            )
        },
        "symbol": {"symbol": "ETHUSDT"},
        "mode": {},
        "position_id": {"position_id": "position:entry-cursor:conflict"},
    }[mutation]
    conflicting = replace(cursor, **changes)
    if mutation == "mode":
        conflicting = copy(cursor)
        object.__setattr__(conflicting, "mode", ExecutionMode.OFF)
    entry_context.repositories.cursor = conflicting

    replay = _service(entry_context).execute_entry(entry_context.request)

    expected = (
        PaperOrderExecutionOutcome.EXISTING_ENTRY_GRAPH_INCONSISTENT
        if mutation == "position_id"
        else PaperOrderExecutionOutcome.IDEMPOTENCY_CONFLICT
    )
    assert replay.outcome is expected
    assert entry_context.repositories.atomic_calls == 1


def test_retry_request_position_identity_conflict_is_typed(entry_context):
    created = _service(entry_context).execute_entry(entry_context.request)
    assert created.outcome is PaperOrderExecutionOutcome.ENTRY_EXECUTED

    replay = _service(entry_context).execute_entry(
        replace(
            entry_context.request,
            position_id="position:entry-cursor:conflicting-request",
        )
    )

    assert replay.outcome is PaperOrderExecutionOutcome.IDEMPOTENCY_CONFLICT
    assert entry_context.repositories.atomic_calls == 1
