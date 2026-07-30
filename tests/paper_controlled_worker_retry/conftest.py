from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.engine_execution.paper_idempotency import (
    journal_event_idempotency_key,
    order_idempotency_key,
)
from app.engine_execution.paper_state_machine import (
    command_created_event,
    create_paper_order,
    fill_order,
    transition_order,
)
from app.engine_exit.paper_exit import create_exit_decision
from app.engine_paper.command_ingestion_service import (
    PaperCommandIngestionOutcome,
    PaperCommandIngestionResult,
)
from app.engine_paper.controlled_worker import (
    PAPER_LIFECYCLE_CYCLE_CONTRACT_VERSION,
    PaperControlledLifecycleWorker,
    PaperLifecycleCycleRequest,
    PaperLifecycleCycleScope,
    PaperLifecycleGraph,
    PaperLifecycleOrderNode,
)
from app.engine_paper.exit_evaluation_cursor import (
    PAPER_EXIT_CURSOR_CONTRACT_VERSION,
    PaperExitEvaluationCursor,
    paper_exit_evaluation_cursor_id,
)
from app.engine_paper.exit_evaluation_service import (
    PaperExitServiceOutcome,
    PaperExitServiceResult,
)
from app.engine_paper.exit_evaluator import PAPER_EXIT_EVALUATION_POLICY_ID
from app.engine_paper.fill_simulator import PaperFillRole
from app.engine_paper.order_execution_service import (
    PaperCloseExecutionRequest,
    PaperEntryExecutionRequest,
    PaperOrderExecutionOutcome,
    PaperOrderExecutionResult,
)
from app.engine_paper.repository_results import RepositoryOutcome
from app.engine_position.paper_state_machine import (
    apply_close_fill,
    apply_entry_fill,
    begin_closing,
)
from app.engine_safety import (
    ExecutionMode,
    PaperEventType,
    PaperExitCause,
    PaperOrderState,
    PaperPositionState,
    PaperReasonCode,
)
from tests.paper_command_ingestion_retry.conftest import (
    make_request as make_ingestion_request,
)
from tests.paper_exit_evaluation_retry.conftest import (
    make_request as make_exit_request,
)
from tests.paper_order_execution_service.conftest import (
    NOW as SERVICE_NOW,
    OPERATION_AT as SERVICE_OPERATION_AT,
    make_candle,
    make_command,
    make_policy,
    simulated_fill,
)
from tests.paper_repository.conftest import (  # noqa: F401
    paper_session_factory,
    repository_postgres_engine,
)


NOW = SERVICE_NOW
NEXT = SERVICE_OPERATION_AT


def _journal_event(event_type, suffix, aggregate_type, aggregate_id, version):
    from app.engine_journal.paper_events import PaperDomainEvent

    reason = {
        PaperEventType.PAPER_COMMAND_CREATED: PaperReasonCode.PAPER_ORDER_CREATED,
        PaperEventType.PAPER_ORDER_CREATED: PaperReasonCode.PAPER_ORDER_CREATED,
        PaperEventType.PAPER_ORDER_VALIDATED: PaperReasonCode.PAPER_ORDER_VALIDATED,
        PaperEventType.PAPER_ORDER_OPENED: PaperReasonCode.PAPER_ORDER_OPENED,
        PaperEventType.PAPER_ORDER_FILLED: PaperReasonCode.PAPER_ORDER_FILLED,
        PaperEventType.PAPER_POSITION_OPENED: PaperReasonCode.PAPER_POSITION_OPENED,
        PaperEventType.PAPER_EXIT_TRIGGERED: PaperReasonCode.PAPER_EXIT_STOP_LOSS_TRIGGERED,
        PaperEventType.PAPER_POSITION_CLOSED: PaperReasonCode.PAPER_POSITION_CLOSED,
    }[event_type]
    return PaperDomainEvent(
        event_id=f"journal:worker:{suffix}",
        event_type=event_type,
        occurred_at=NOW,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        correlation_id="correlation:worker:1",
        causation_id="causation:worker:1",
        reason_code=reason,
        aggregate_version=version,
    )


def build_graphs():
    command = make_command(created_at=NOW)
    command_event = command_created_event(
        command, occurred_at=NOW, event_id="event:worker:command"
    )
    created = create_paper_order(
        command,
        order_id="order:worker:entry",
        idempotency_key=order_idempotency_key(command.command_id, "ENTRY"),
        occurred_at=NOW,
        event_id="event:worker:entry:created",
    )
    validated = transition_order(
        created.order,
        PaperOrderState.VALIDATED,
        expected_version=0,
        occurred_at=NOW,
        event_id="event:worker:entry:validated",
    )
    opened = transition_order(
        validated.order,
        PaperOrderState.OPEN,
        expected_version=1,
        occurred_at=NOW,
        event_id="event:worker:entry:opened",
    )
    entry_order = opened.order
    policy = make_policy()
    candle = make_candle()
    entry_fill = simulated_fill(
        command, entry_order, policy, candle, PaperFillRole.ENTRY
    )
    entry_filled = fill_order(
        entry_order,
        entry_fill,
        expected_version=entry_order.version,
        event_id="event:worker:entry:filled",
    )
    position_change = apply_entry_fill(
        None,
        command,
        entry_filled.order,
        entry_fill,
        position_id="position:worker:1",
        event_id="event:worker:position:opened",
    )
    position = position_change.position
    cursor = PaperExitEvaluationCursor(
        cursor_id=paper_exit_evaluation_cursor_id(
            position_id=position.position_id,
            mode=position.mode,
            symbol=position.symbol,
            position_opened_closed_until_ms=entry_fill.source_closed_until_ms,
            evaluation_policy_id=PAPER_EXIT_EVALUATION_POLICY_ID,
        ),
        contract_version=PAPER_EXIT_CURSOR_CONTRACT_VERSION,
        position_id=position.position_id,
        mode=position.mode,
        symbol=position.symbol,
        last_evaluated_closed_until_ms=entry_fill.source_closed_until_ms,
        position_opened_closed_until_ms=entry_fill.source_closed_until_ms,
        evaluation_policy_id=PAPER_EXIT_EVALUATION_POLICY_ID,
        version=0,
        created_at=NOW,
        updated_at=NOW,
        correlation_id="correlation:worker:1",
        causation_id=entry_fill.fill_id,
    )
    decision, exit_event = create_exit_decision(
        position,
        exit_decision_id="exit:worker:1",
        idempotency_key="exit:key:worker:1",
        expected_position_version=position.version,
        cause=PaperExitCause.STOP_LOSS,
        decision_price=position.stop_price,
        source_closed_until_ms=entry_fill.source_closed_until_ms + 60_000,
        decided_at=NEXT,
        reason_code=PaperReasonCode.PAPER_EXIT_STOP_LOSS_TRIGGERED,
        event_id="event:worker:exit",
    )
    closing = begin_closing(
        position,
        expected_version=position.version,
        exit_decision_id=decision.exit_decision_id,
        occurred_at=NEXT,
    ).position
    advanced_cursor = replace(
        cursor,
        last_evaluated_closed_until_ms=decision.source_closed_until_ms,
        version=1,
        updated_at=NEXT,
        last_advance_idempotency_key="cursor:advance:worker:1",
        last_advance_from_closed_until_ms=cursor.last_evaluated_closed_until_ms,
        last_advance_to_closed_until_ms=decision.source_closed_until_ms,
        last_advance_expected_version=0,
        last_window_identity="cursor:window:worker:1",
    )
    close_created = create_paper_order(
        command,
        order_id="order:worker:close",
        idempotency_key=order_idempotency_key(command.command_id, "EXIT"),
        occurred_at=NEXT,
        event_id="event:worker:close:created",
    )
    close_validated = transition_order(
        close_created.order,
        PaperOrderState.VALIDATED,
        expected_version=0,
        occurred_at=NEXT,
        event_id="event:worker:close:validated",
    )
    close_opened = transition_order(
        close_validated.order,
        PaperOrderState.OPEN,
        expected_version=1,
        occurred_at=NEXT,
        event_id="event:worker:close:opened",
    )
    close_order = close_opened.order
    close_candle = make_candle(
        open_time_ms=decision.source_closed_until_ms,
        close_boundary_ms=decision.source_closed_until_ms + 60_000,
        observed_closed_until_ms=decision.source_closed_until_ms + 60_000,
    )
    close_fill = simulated_fill(
        command,
        close_order,
        policy,
        close_candle,
        PaperFillRole.CLOSE,
        exit_decision_id=decision.exit_decision_id,
        source_closed_until_ms=decision.source_closed_until_ms,
    )
    close_filled = fill_order(
        close_order,
        close_fill,
        expected_version=close_order.version,
        event_id="event:worker:close:filled",
    )
    closed_change = apply_close_fill(
        closing,
        close_fill,
        expected_version=closing.version,
        event_id="event:worker:position:closed",
    )
    order_events_open = (
        created.events[0],
        validated.events[0],
        opened.events[0],
    )
    journal_open = (
        command_event,
        *order_events_open,
    )
    order_events_entry = (*order_events_open, entry_filled.events[0])
    journal_entry = (
        *journal_open,
        entry_filled.events[0],
        position_change.events[0],
    )
    order_events_closing = (
        *order_events_entry,
        close_created.events[0],
        close_validated.events[0],
        close_opened.events[0],
    )
    journal_closing = (
        *journal_entry,
        exit_event,
        close_created.events[0],
        close_validated.events[0],
        close_opened.events[0],
    )
    order_events_closed = (*order_events_closing, close_filled.events[0])
    journal_closed = (
        *journal_closing,
        close_filled.events[0],
        closed_change.events[0],
    )
    empty = PaperLifecycleGraph(command_id=command.command_id)
    entry_open = PaperLifecycleGraph(
        command_id=command.command_id,
        command=command,
        orders=(PaperLifecycleOrderNode("ENTRY", entry_order),),
        order_events=order_events_open,
        journal=journal_open,
    )
    position_open = PaperLifecycleGraph(
        command_id=command.command_id,
        command=command,
        orders=(PaperLifecycleOrderNode("ENTRY", entry_filled.order),),
        fills=(entry_fill,),
        positions=(position,),
        cursors=(cursor,),
        order_events=order_events_entry,
        journal=journal_entry,
    )
    position_closing = PaperLifecycleGraph(
        command_id=command.command_id,
        command=command,
        orders=(
            PaperLifecycleOrderNode("ENTRY", entry_filled.order),
            PaperLifecycleOrderNode("EXIT", close_order),
        ),
        fills=(entry_fill,),
        positions=(closing,),
        exit_decisions=(decision,),
        cursors=(advanced_cursor,),
        order_events=order_events_closing,
        journal=journal_closing,
    )
    position_closed = PaperLifecycleGraph(
        command_id=command.command_id,
        command=command,
        orders=(
            PaperLifecycleOrderNode("ENTRY", entry_filled.order),
            PaperLifecycleOrderNode("EXIT", close_filled.order),
        ),
        fills=(entry_fill, close_fill),
        positions=(closed_change.position,),
        exit_decisions=(decision,),
        cursors=(advanced_cursor,),
        order_events=order_events_closed,
        journal=journal_closed,
    )
    return SimpleNamespace(
        command=command,
        policy=policy,
        candle=candle,
        close_candle=close_candle,
        entry_order=entry_order,
        entry_fill=entry_fill,
        position=position,
        cursor=cursor,
        decision=decision,
        close_order=close_order,
        close_fill=close_fill,
        empty=empty,
        entry_open=entry_open,
        position_open=position_open,
        position_closing=position_closing,
        position_closed=position_closed,
    )


@pytest.fixture
def lifecycle_graphs():
    return build_graphs()


class SequenceLoader:
    def __init__(self, *graphs):
        self.graphs = list(graphs)
        self.calls = 0

    def load(self, command_id):
        selected = self.graphs[min(self.calls, len(self.graphs) - 1)]
        self.calls += 1
        assert selected.command_id == command_id
        return selected


class FakeIngestion:
    def __init__(self, result=None):
        self.calls = []
        self.result = result

    def ingest_and_create_entry_order(self, request):
        self.calls.append(request)
        return self.result or PaperCommandIngestionResult(
            PaperCommandIngestionOutcome.COMMAND_AND_ORDER_CREATED,
            "PAPER_INGESTION_OK",
            request.command_id,
            request.order_id,
            PaperOrderState.OPEN,
            2,
            RepositoryOutcome.CREATED,
            3,
            4,
            request.simulation_policy.simulation_policy_id,
        )


class FakeExecution:
    def __init__(self, entry_result=None, close_result=None):
        self.entry_calls = []
        self.close_calls = []
        self.entry_result = entry_result
        self.close_result = close_result

    def execute_entry(self, request):
        self.entry_calls.append(request)
        return self.entry_result or PaperOrderExecutionResult(
            "ENTRY",
            PaperOrderExecutionOutcome.ENTRY_EXECUTED,
            "PAPER_EXECUTION_OK",
            request.command_id,
            request.order_id,
            request.fill_id,
            request.position_id,
        )

    def execute_close(self, request):
        self.close_calls.append(request)
        return self.close_result or PaperOrderExecutionResult(
            "CLOSE",
            PaperOrderExecutionOutcome.CLOSE_EXECUTED,
            "PAPER_EXECUTION_OK",
            request.command_id,
            request.order_id,
            request.fill_id,
            request.position_id,
            request.exit_decision_id,
        )


class FakeExit:
    def __init__(self, result=None):
        self.calls = []
        self.result = result

    def evaluate(self, request):
        self.calls.append(request)
        return self.result or PaperExitServiceResult(
            PaperExitServiceOutcome.NO_EXIT_TRIGGER_CURSOR_ADVANCED,
            "PAPER_EXIT_NO_TRIGGER",
            request.position_id,
            request.cursor_id,
            request.market_snapshot_closed_until_ms,
            request.expected_cursor_version + 1,
            PaperPositionState.OPEN,
            request.expected_position_version,
        )


def make_worker(*graphs, ingestion=None, execution=None, exit_service=None, fault=None):
    return PaperControlledLifecycleWorker(
        SequenceLoader(*graphs),
        ingestion or FakeIngestion(),
        execution or FakeExecution(),
        exit_service or FakeExit(),
        fault_injector=fault,
    )


def make_cycle(command_id, **changes):
    values = {
        "cycle_id": "cycle:worker:1",
        "contract_version": PAPER_LIFECYCLE_CYCLE_CONTRACT_VERSION,
        "execution_mode": ExecutionMode.PAPER,
        "explicit_paper_authorization": True,
        "scope": PaperLifecycleCycleScope.ADVANCE_ONE_LIFECYCLE_STEP,
        "max_stages": 1,
        "created_at": NOW,
        "correlation_id": "correlation:worker:1",
        "command_id": command_id,
    }
    values.update(changes)
    return PaperLifecycleCycleRequest(**values)


def make_entry_request(graphs, **changes):
    values = {
        "command_id": graphs.command.command_id,
        "order_id": graphs.entry_order.order_id,
        "expected_order_version": graphs.entry_order.version,
        "fill_role": PaperFillRole.ENTRY,
        "candidate_candles": (graphs.candle,),
        "market_snapshot_closed_until_ms": graphs.candle.close_boundary_ms,
        "simulation_policy": graphs.policy,
        "price_quantum": graphs.policy.price_quantum,
        "fee_quantum": graphs.policy.fee_quantum,
        "quote_asset": "USDT",
        "fill_id": graphs.entry_fill.fill_id,
        "order_event_id": "event:worker:entry:filled",
        "position_event_id": "event:worker:position:opened",
        "journal_entry_ids": (
            "journal:worker:entry:filled",
            "journal:worker:position:opened",
        ),
        "correlation_id": "correlation:worker:1",
        "causation_id": "causation:worker:1",
        "operation_at": NEXT,
        "position_id": graphs.position.position_id,
    }
    values.update(changes)
    return PaperEntryExecutionRequest(**values)


def make_worker_exit_request(graphs, **changes):
    request = make_exit_request(
        {"command": graphs.command, "position": graphs.position},
        graphs.cursor,
        correlation_id="correlation:worker:1",
        position_id=graphs.position.position_id,
        cursor_id=graphs.cursor.cursor_id,
        source_command_id=graphs.command.command_id,
        entry_order_id=graphs.entry_order.order_id,
        entry_fill_id=graphs.entry_fill.fill_id,
        exit_decision_id=graphs.decision.exit_decision_id,
        close_order_id=graphs.close_order.order_id,
    )
    return replace(request, **changes)


def make_close_request(graphs, **changes):
    values = {
        "command_id": graphs.command.command_id,
        "order_id": graphs.close_order.order_id,
        "expected_order_version": graphs.close_order.version,
        "position_id": graphs.position.position_id,
        "expected_position_version": 1,
        "exit_decision_id": graphs.decision.exit_decision_id,
        "fill_role": PaperFillRole.CLOSE,
        "candidate_candles": (graphs.close_candle,),
        "market_snapshot_closed_until_ms": graphs.close_candle.close_boundary_ms,
        "simulation_policy": graphs.policy,
        "price_quantum": graphs.policy.price_quantum,
        "fee_quantum": graphs.policy.fee_quantum,
        "quote_asset": "USDT",
        "fill_id": graphs.close_fill.fill_id,
        "order_event_id": "event:worker:close:filled",
        "position_event_id": "event:worker:position:closed",
        "journal_entry_ids": (
            "journal:worker:close:filled",
            "journal:worker:position:closed",
        ),
        "correlation_id": "correlation:worker:1",
        "causation_id": "causation:worker:1",
        "operation_at": NEXT + timedelta(minutes=1),
    }
    values.update(changes)
    return PaperCloseExecutionRequest(**values)


@pytest.fixture
def ingestion_request():
    return make_ingestion_request(
        identity_suffix="worker",
        correlation_id="correlation:worker:1",
    )
