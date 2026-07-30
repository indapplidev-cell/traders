from __future__ import annotations

from dataclasses import replace

import pytest

from app.engine_paper.command_ingestion_service import (
    PaperCommandIngestionOutcome,
    PaperCommandIngestionResult,
)
from app.engine_paper.controlled_worker import (
    MAX_STAGE_TRACE_ITEMS,
    PaperLifecycleCycleOutcome,
    PaperLifecycleCycleScope,
    PaperLifecycleFaultPoint,
    PaperLifecycleReasonCode,
    PaperLifecycleStage,
    PaperLifecycleState,
)
from app.engine_paper.exit_evaluation_service import (
    PaperExitServiceOutcome,
    PaperExitServiceResult,
)
from app.engine_paper.order_execution_service import (
    PaperOrderExecutionOutcome,
    PaperOrderExecutionResult,
)
from app.engine_safety import PaperOrderState, PaperPositionState

from .conftest import (
    FakeExecution,
    FakeExit,
    FakeIngestion,
    make_close_request,
    make_cycle,
    make_entry_request,
    make_worker,
    make_worker_exit_request,
)


@pytest.mark.parametrize(
    ("graph_name", "expected_reason"),
    (
        ("empty", PaperLifecycleReasonCode.MISSING_APPROVAL_CHAIN),
        ("entry_open", PaperLifecycleReasonCode.MISSING_ENTRY_INPUT),
        ("position_open", PaperLifecycleReasonCode.MISSING_EXIT_INPUT),
        ("position_closing", PaperLifecycleReasonCode.MISSING_CLOSE_INPUT),
    ),
)
def test_missing_stage_specific_input_blocks_without_mutation(
    lifecycle_graphs, graph_name, expected_reason
):
    graph = getattr(lifecycle_graphs, graph_name)
    result = make_worker(graph).run_cycle(make_cycle(graph.command_id))
    assert result.outcome is PaperLifecycleCycleOutcome.CYCLE_BLOCKED_AWAITING_INPUT
    assert result.reason_code == expected_reason.value
    assert result.stage_trace == ()


def test_closed_graph_returns_complete_without_child_call(lifecycle_graphs):
    result = make_worker(lifecycle_graphs.position_closed).run_cycle(
        make_cycle(lifecycle_graphs.command.command_id)
    )
    assert result.outcome is PaperLifecycleCycleOutcome.CYCLE_COMPLETE
    assert result.final_lifecycle_state is PaperLifecycleState.POSITION_CLOSED
    assert result.stages_attempted == 0


def test_one_step_ingestion_invokes_only_ingestion(
    lifecycle_graphs, ingestion_request
):
    nested = replace(
        ingestion_request,
        command_id=lifecycle_graphs.command.command_id,
        order_id=lifecycle_graphs.entry_order.order_id,
    )
    ingestion = FakeIngestion()
    execution = FakeExecution()
    exit_service = FakeExit()
    worker = make_worker(
        lifecycle_graphs.empty,
        lifecycle_graphs.entry_open,
        ingestion=ingestion,
        execution=execution,
        exit_service=exit_service,
    )
    result = worker.run_cycle(
        make_cycle(
            lifecycle_graphs.command.command_id,
            entry_order_id=lifecycle_graphs.entry_order.order_id,
            ingestion_request=nested,
        )
    )
    assert result.outcome is PaperLifecycleCycleOutcome.CYCLE_STAGE_COMPLETED
    assert [item.stage for item in result.stage_trace] == [
        PaperLifecycleStage.INGEST_COMMAND
    ]
    assert len(ingestion.calls) == 1
    assert execution.entry_calls == execution.close_calls == []
    assert exit_service.calls == []


def test_one_step_entry_proves_cursor_ready(lifecycle_graphs):
    execution = FakeExecution()
    worker = make_worker(
        lifecycle_graphs.entry_open,
        lifecycle_graphs.position_open,
        execution=execution,
    )
    request = make_cycle(
        lifecycle_graphs.command.command_id,
        entry_order_id=lifecycle_graphs.entry_order.order_id,
        entry_fill_id=lifecycle_graphs.entry_fill.fill_id,
        position_id=lifecycle_graphs.position.position_id,
        cursor_id=lifecycle_graphs.cursor.cursor_id,
        entry_execution_request=make_entry_request(lifecycle_graphs),
    )
    result = worker.run_cycle(request)
    assert result.outcome is PaperLifecycleCycleOutcome.CYCLE_STAGE_COMPLETED
    assert result.final_lifecycle_state is PaperLifecycleState.POSITION_OPEN_CURSOR_READY
    assert result.cursor_id == lifecycle_graphs.cursor.cursor_id
    assert len(execution.entry_calls) == 1


def test_one_step_no_trigger_advances_only_cursor_stage(lifecycle_graphs):
    exit_service = FakeExit()
    worker = make_worker(
        lifecycle_graphs.position_open,
        lifecycle_graphs.position_open,
        exit_service=exit_service,
    )
    result = worker.run_cycle(
        make_cycle(
            lifecycle_graphs.command.command_id,
            entry_order_id=lifecycle_graphs.entry_order.order_id,
            entry_fill_id=lifecycle_graphs.entry_fill.fill_id,
            position_id=lifecycle_graphs.position.position_id,
            cursor_id=lifecycle_graphs.cursor.cursor_id,
            exit_evaluation_request=make_worker_exit_request(lifecycle_graphs),
        )
    )
    assert result.outcome is PaperLifecycleCycleOutcome.CYCLE_STAGE_COMPLETED
    assert result.stage_trace[0].stage is PaperLifecycleStage.EVALUATE_EXIT
    assert result.final_lifecycle_state is PaperLifecycleState.POSITION_OPEN_CURSOR_READY
    assert len(exit_service.calls) == 1


def test_one_step_trigger_never_executes_close_in_same_call(lifecycle_graphs):
    exit_result = PaperExitServiceResult(
        PaperExitServiceOutcome.EXIT_PREPARED,
        "PAPER_EXIT_PREPARED",
        lifecycle_graphs.position.position_id,
        lifecycle_graphs.cursor.cursor_id,
        lifecycle_graphs.decision.source_closed_until_ms,
        1,
        PaperPositionState.CLOSING,
        1,
        lifecycle_graphs.decision.exit_decision_id,
        lifecycle_graphs.close_order.order_id,
        PaperOrderState.OPEN,
    )
    execution = FakeExecution()
    worker = make_worker(
        lifecycle_graphs.position_open,
        lifecycle_graphs.position_closing,
        execution=execution,
        exit_service=FakeExit(exit_result),
    )
    result = worker.run_cycle(
        make_cycle(
            lifecycle_graphs.command.command_id,
            position_id=lifecycle_graphs.position.position_id,
            cursor_id=lifecycle_graphs.cursor.cursor_id,
            exit_decision_id=lifecycle_graphs.decision.exit_decision_id,
            close_order_id=lifecycle_graphs.close_order.order_id,
            exit_evaluation_request=make_worker_exit_request(lifecycle_graphs),
        )
    )
    assert result.outcome is PaperLifecycleCycleOutcome.CYCLE_STAGE_COMPLETED
    assert result.final_lifecycle_state is PaperLifecycleState.POSITION_CLOSING_CLOSE_ORDER_OPEN
    assert execution.close_calls == []


def test_one_step_close_returns_complete(lifecycle_graphs):
    execution = FakeExecution()
    worker = make_worker(
        lifecycle_graphs.position_closing,
        lifecycle_graphs.position_closed,
        execution=execution,
    )
    result = worker.run_cycle(
        make_cycle(
            lifecycle_graphs.command.command_id,
            position_id=lifecycle_graphs.position.position_id,
            exit_decision_id=lifecycle_graphs.decision.exit_decision_id,
            close_order_id=lifecycle_graphs.close_order.order_id,
            close_fill_id=lifecycle_graphs.close_fill.fill_id,
            close_execution_request=make_close_request(lifecycle_graphs),
        )
    )
    assert result.outcome is PaperLifecycleCycleOutcome.CYCLE_COMPLETE
    assert result.final_lifecycle_state is PaperLifecycleState.POSITION_CLOSED
    assert len(execution.close_calls) == 1


@pytest.mark.parametrize("suffix", range(16))
def test_ingestion_exact_identity_mismatch_is_rejected(
    lifecycle_graphs, ingestion_request, suffix
):
    graph = replace(
        lifecycle_graphs.empty, command_id=f"command:cycle:ingest:{suffix}"
    )
    result = make_worker(graph).run_cycle(
        make_cycle(graph.command_id, ingestion_request=ingestion_request)
    )
    assert result.outcome is PaperLifecycleCycleOutcome.INVALID_STAGE_INPUT


@pytest.mark.parametrize("suffix", range(16))
def test_entry_exact_identity_mismatch_is_rejected(lifecycle_graphs, suffix):
    nested = make_entry_request(
        lifecycle_graphs, order_id=f"order:wrong:entry:{suffix}"
    )
    result = make_worker(lifecycle_graphs.entry_open).run_cycle(
        make_cycle(
            lifecycle_graphs.command.command_id,
            entry_order_id=lifecycle_graphs.entry_order.order_id,
            entry_execution_request=nested,
        )
    )
    assert result.outcome is PaperLifecycleCycleOutcome.INVALID_STAGE_INPUT


@pytest.mark.parametrize("suffix", range(16))
def test_exit_exact_identity_mismatch_is_rejected(lifecycle_graphs, suffix):
    nested = make_worker_exit_request(
        lifecycle_graphs, cursor_id=f"cursor:wrong:exit:{suffix}"
    )
    result = make_worker(lifecycle_graphs.position_open).run_cycle(
        make_cycle(
            lifecycle_graphs.command.command_id,
            cursor_id=lifecycle_graphs.cursor.cursor_id,
            exit_evaluation_request=nested,
        )
    )
    assert result.outcome is PaperLifecycleCycleOutcome.INVALID_STAGE_INPUT


@pytest.mark.parametrize("suffix", range(16))
def test_close_exact_identity_mismatch_is_rejected(lifecycle_graphs, suffix):
    nested = make_close_request(
        lifecycle_graphs, fill_id=f"fill:wrong:close:{suffix}"
    )
    result = make_worker(lifecycle_graphs.position_closing).run_cycle(
        make_cycle(
            lifecycle_graphs.command.command_id,
            close_fill_id=lifecycle_graphs.close_fill.fill_id,
            close_execution_request=nested,
        )
    )
    assert result.outcome is PaperLifecycleCycleOutcome.INVALID_STAGE_INPUT


ENTRY_FAILURES = (
    PaperOrderExecutionOutcome.INVALID_ORDER_STATE,
    PaperOrderExecutionOutcome.STALE_ORDER_VERSION,
    PaperOrderExecutionOutcome.GRAPH_INCONSISTENT,
    PaperOrderExecutionOutcome.INTERNAL_INVARIANT_FAILURE,
    PaperOrderExecutionOutcome.TRANSIENT_DB_FAILURE,
    PaperOrderExecutionOutcome.UNCERTAIN_COMMIT_UNRESOLVED,
    PaperOrderExecutionOutcome.IDEMPOTENCY_CONFLICT,
)


@pytest.mark.parametrize("child_outcome", ENTRY_FAILURES)
def test_entry_child_failure_mapping_preserves_child_code(
    lifecycle_graphs, child_outcome
):
    child = PaperOrderExecutionResult(
        "ENTRY",
        child_outcome,
        f"CHILD_REASON_{child_outcome.value}",
        lifecycle_graphs.command.command_id,
        lifecycle_graphs.entry_order.order_id,
    )
    result = make_worker(
        lifecycle_graphs.entry_open,
        execution=FakeExecution(entry_result=child),
    ).run_cycle(
        make_cycle(
            lifecycle_graphs.command.command_id,
            entry_execution_request=make_entry_request(lifecycle_graphs),
        )
    )
    assert result.child_outcome_codes == (child_outcome.value,)
    assert result.child_reason_codes == (f"CHILD_REASON_{child_outcome.value}",)
    if child_outcome is PaperOrderExecutionOutcome.TRANSIENT_DB_FAILURE:
        assert result.outcome is PaperLifecycleCycleOutcome.TRANSIENT_DB_FAILURE
    elif child_outcome is PaperOrderExecutionOutcome.UNCERTAIN_COMMIT_UNRESOLVED:
        assert result.outcome is PaperLifecycleCycleOutcome.UNCERTAIN_COMMIT_UNRESOLVED
    elif child_outcome is PaperOrderExecutionOutcome.IDEMPOTENCY_CONFLICT:
        assert result.outcome is PaperLifecycleCycleOutcome.IDEMPOTENCY_CONFLICT
    elif child_outcome is PaperOrderExecutionOutcome.STALE_ORDER_VERSION:
        assert result.outcome is PaperLifecycleCycleOutcome.STALE_EXPECTED_VERSION
    else:
        assert result.outcome is PaperLifecycleCycleOutcome.ENTRY_EXECUTION_STAGE_FAILED


class Cancellation:
    def __init__(self, values):
        self.values = iter(values)

    def is_cancelled(self):
        return next(self.values, False)


def test_cancellation_before_initial_graph_load(lifecycle_graphs):
    result = make_worker(lifecycle_graphs.empty).run_cycle(
        make_cycle(
            lifecycle_graphs.command.command_id,
            cancellation_authority=Cancellation([True]),
        )
    )
    assert result.outcome is PaperLifecycleCycleOutcome.CANCELLED
    assert result.stages_completed == 0


def test_cancellation_after_committed_stage_returns_persisted_state(lifecycle_graphs):
    cancellation = Cancellation([False, False, True])
    result = make_worker(
        lifecycle_graphs.entry_open, lifecycle_graphs.position_open
    ).run_cycle(
        make_cycle(
            lifecycle_graphs.command.command_id,
            entry_execution_request=make_entry_request(lifecycle_graphs),
            cancellation_authority=cancellation,
        )
    )
    assert result.outcome is PaperLifecycleCycleOutcome.CANCELLED_AFTER_COMMITTED_STAGE
    assert result.final_lifecycle_state is PaperLifecycleState.POSITION_OPEN_CURSOR_READY
    assert result.stages_completed == 1


@pytest.mark.parametrize("fault_point", tuple(PaperLifecycleFaultPoint))
def test_each_worker_fault_point_is_observable_and_never_retried(
    lifecycle_graphs, fault_point
):
    seen = []

    def inject(actual):
        seen.append(actual)
        if actual is fault_point:
            raise RuntimeError(f"FAULT:{actual.value}")

    worker = make_worker(
        lifecycle_graphs.entry_open,
        lifecycle_graphs.position_open,
        fault=inject,
    )
    request = make_cycle(
        lifecycle_graphs.command.command_id,
        entry_execution_request=make_entry_request(lifecycle_graphs),
    )
    if fault_point is PaperLifecycleFaultPoint.BETWEEN_BOUNDED_STAGES:
        request = replace(
            request,
            scope=PaperLifecycleCycleScope.ADVANCE_UNTIL_BLOCKED_WITHIN_REQUEST,
            max_stages=2,
            exit_evaluation_request=make_worker_exit_request(lifecycle_graphs),
        )
    with pytest.raises(RuntimeError, match="FAULT:"):
        worker.run_cycle(request)
    assert seen.count(fault_point) == 1


def test_bounded_four_stage_lifecycle_stops_complete(lifecycle_graphs, ingestion_request):
    nested_ingestion = replace(
        ingestion_request,
        command_id=lifecycle_graphs.command.command_id,
        order_id=lifecycle_graphs.entry_order.order_id,
    )
    trigger_result = PaperExitServiceResult(
        PaperExitServiceOutcome.EXIT_PREPARED,
        "PAPER_EXIT_PREPARED",
        lifecycle_graphs.position.position_id,
        lifecycle_graphs.cursor.cursor_id,
        lifecycle_graphs.decision.source_closed_until_ms,
        1,
        PaperPositionState.CLOSING,
        1,
        lifecycle_graphs.decision.exit_decision_id,
        lifecycle_graphs.close_order.order_id,
        PaperOrderState.OPEN,
    )
    worker = make_worker(
        lifecycle_graphs.empty,
        lifecycle_graphs.entry_open,
        lifecycle_graphs.position_open,
        lifecycle_graphs.position_closing,
        lifecycle_graphs.position_closed,
        exit_service=FakeExit(trigger_result),
    )
    result = worker.run_cycle(
        make_cycle(
            lifecycle_graphs.command.command_id,
            scope=PaperLifecycleCycleScope.ADVANCE_UNTIL_BLOCKED_WITHIN_REQUEST,
            max_stages=4,
            ingestion_request=nested_ingestion,
            entry_execution_request=make_entry_request(lifecycle_graphs),
            exit_evaluation_request=make_worker_exit_request(lifecycle_graphs),
            close_execution_request=make_close_request(lifecycle_graphs),
        )
    )
    assert result.outcome is PaperLifecycleCycleOutcome.CYCLE_COMPLETE
    assert result.stages_completed == 4
    assert len(result.stage_trace) == MAX_STAGE_TRACE_ITEMS == 4
    assert [item.stage for item in result.stage_trace] == [
        PaperLifecycleStage.INGEST_COMMAND,
        PaperLifecycleStage.EXECUTE_ENTRY,
        PaperLifecycleStage.EVALUATE_EXIT,
        PaperLifecycleStage.EXECUTE_CLOSE,
    ]


@pytest.mark.parametrize("max_stages", (1, 2, 3))
def test_bounded_multi_stage_stops_exactly_at_explicit_limit(
    lifecycle_graphs, ingestion_request, max_stages
):
    nested_ingestion = replace(
        ingestion_request,
        command_id=lifecycle_graphs.command.command_id,
        order_id=lifecycle_graphs.entry_order.order_id,
    )
    trigger_result = PaperExitServiceResult(
        PaperExitServiceOutcome.EXIT_PREPARED,
        "PAPER_EXIT_PREPARED",
        lifecycle_graphs.position.position_id,
        lifecycle_graphs.cursor.cursor_id,
        lifecycle_graphs.decision.source_closed_until_ms,
        1,
        PaperPositionState.CLOSING,
        1,
        lifecycle_graphs.decision.exit_decision_id,
        lifecycle_graphs.close_order.order_id,
        PaperOrderState.OPEN,
    )
    result = make_worker(
        lifecycle_graphs.empty,
        lifecycle_graphs.entry_open,
        lifecycle_graphs.position_open,
        lifecycle_graphs.position_closing,
        lifecycle_graphs.position_closed,
        exit_service=FakeExit(trigger_result),
    ).run_cycle(
        make_cycle(
            lifecycle_graphs.command.command_id,
            scope=PaperLifecycleCycleScope.ADVANCE_UNTIL_BLOCKED_WITHIN_REQUEST,
            max_stages=max_stages,
            ingestion_request=nested_ingestion,
            entry_execution_request=make_entry_request(lifecycle_graphs),
            exit_evaluation_request=make_worker_exit_request(lifecycle_graphs),
            close_execution_request=make_close_request(lifecycle_graphs),
        )
    )
    assert result.outcome is PaperLifecycleCycleOutcome.CYCLE_MAX_STAGES_REACHED
    assert result.stages_completed == max_stages
    assert len(result.stage_trace) == max_stages
