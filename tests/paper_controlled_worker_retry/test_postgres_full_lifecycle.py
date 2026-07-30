from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import delete, func, select

from app.db.paper_models import (
    PaperExecutionCommandRecord,
    PaperExitDecisionRecord,
    PaperExitEvaluationCursorRecord,
    PaperFillRecord,
    PaperJournalEntryRecord,
    PaperOrderEventRecord,
    PaperOrderRecord,
    PaperPositionRecord,
    PaperSimulationPolicyRecord,
)
from app.engine_execution.paper_idempotency import (
    simulated_close_fill_id,
    simulated_fill_id,
)
from app.engine_paper.controlled_worker import (
    PAPER_LIFECYCLE_CYCLE_CONTRACT_VERSION,
    PaperControlledLifecycleWorker,
    PaperLifecycleCycleOutcome,
    PaperLifecycleCycleRequest,
    PaperLifecycleCycleScope,
    PaperLifecycleState,
)
from app.engine_paper.exit_evaluation_service import PaperExitEvaluationRequest
from app.engine_paper.exit_evaluator import PAPER_EXIT_EVALUATION_POLICY_ID
from app.engine_paper.fill_causal_boundary import (
    PAPER_FILL_CAUSAL_BOUNDARY_VERSION,
)
from app.engine_paper.fill_simulator import PaperFillCandle, PaperFillRole
from app.engine_paper.order_execution_service import (
    PaperCloseExecutionRequest,
    PaperEntryExecutionRequest,
)
from app.engine_paper.unit_of_work import PaperUnitOfWork
from app.engine_safety import ExecutionMode, PaperPositionState
from tests.paper_command_ingestion_retry.conftest import (
    Q,
    make_request as make_ingestion_request,
)
from tests.paper_repository.conftest import (  # noqa: F401
    paper_session_factory,
    repository_postgres_engine,
)


def _at(boundary_ms: int) -> datetime:
    return datetime.fromtimestamp(boundary_ms / 1000, tz=timezone.utc)


def _candle(
    *,
    symbol: str,
    open_ms: int,
    open_price: Decimal,
    high_price: Decimal,
    low_price: Decimal,
    close_price: Decimal,
) -> PaperFillCandle:
    return PaperFillCandle(
        symbol=symbol,
        timeframe="1m",
        open_time_ms=open_ms,
        close_boundary_ms=open_ms + 60_000,
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        close_price=close_price,
        is_closed=True,
        observed_closed_until_ms=open_ms + 60_000,
    )


def _cycle(command_id: str, suffix: str, **changes) -> PaperLifecycleCycleRequest:
    values = {
        "cycle_id": f"cycle:postgres:{suffix}",
        "contract_version": PAPER_LIFECYCLE_CYCLE_CONTRACT_VERSION,
        "execution_mode": ExecutionMode.PAPER,
        "explicit_paper_authorization": True,
        "scope": PaperLifecycleCycleScope.ADVANCE_ONE_LIFECYCLE_STEP,
        "max_stages": 1,
        "created_at": _at(1_800_000_000_000),
        "correlation_id": "correlation:postgres:lifecycle",
        "command_id": command_id,
    }
    values.update(changes)
    return PaperLifecycleCycleRequest(**values)


def _seed_policy(factory, request):
    policy = request.simulation_policy
    with factory.begin() as session:
        session.execute(delete(PaperSimulationPolicyRecord))
        session.add(
            PaperSimulationPolicyRecord(
                policy_id=policy.simulation_policy_id,
                policy_version=1,
                status="ACTIVE",
                price_source=policy.price_source.value,
                timeframe=policy.timeframe,
                latency_candles=policy.latency_candles,
                slippage_bps=policy.slippage_bps,
                fee_bps=policy.fee_bps,
                partial_fill_enabled=policy.partial_fill_enabled,
                future_data_allowed=policy.future_data_allowed,
                intrabar_conflict_policy=policy.intrabar_conflict_policy.value,
                configuration_fingerprint=(
                    request.paper_strategy_approval.configuration_fingerprint
                ),
                created_at=request.created_at,
                retired_at=None,
            )
        )


def _worker(factory):
    return PaperControlledLifecycleWorker.from_factories(
        lambda: PaperUnitOfWork(factory), factory
    )


def _load(factory, command_id):
    from app.engine_paper.controlled_worker import SqlAlchemyPaperLifecycleGraphLoader

    return SqlAlchemyPaperLifecycleGraphLoader(
        lambda: PaperUnitOfWork(factory)
    ).load(command_id)


def _entry_request(graph, policy, correlation_id):
    command = graph.command
    entry_order = graph.orders[0].order
    candle = _candle(
        symbol=command.symbol,
        open_ms=command.closed_until_ms,
        open_price=command.entry_reference_price,
        high_price=command.entry_reference_price,
        low_price=command.entry_reference_price,
        close_price=command.entry_reference_price,
    )
    fill_id = simulated_fill_id(
        contract_version=policy.contract_version,
        order_id=entry_order.order_id,
        fill_role=PaperFillRole.ENTRY.value,
        source_open_time_ms=candle.open_time_ms,
        source_close_boundary_ms=candle.close_boundary_ms,
        simulation_policy_id=policy.simulation_policy_id,
        slippage_policy_id=policy.slippage_policy_id,
        fee_policy_id=policy.fee_policy_id,
        latency_policy_id=policy.latency_policy_id,
    )
    return PaperEntryExecutionRequest(
        command_id=command.command_id,
        order_id=entry_order.order_id,
        expected_order_version=entry_order.version,
        fill_role=PaperFillRole.ENTRY,
        candidate_candles=(candle,),
        market_snapshot_closed_until_ms=candle.close_boundary_ms,
        simulation_policy=policy,
        price_quantum=policy.price_quantum,
        fee_quantum=policy.fee_quantum,
        quote_asset="USDT",
        fill_id=fill_id,
        order_event_id="event:postgres:entry:filled",
        position_event_id="event:postgres:position:opened",
        journal_entry_ids=(
            "journal:postgres:entry:filled",
            "journal:postgres:position:opened",
        ),
        correlation_id=correlation_id,
        causation_id="causation:postgres:entry",
        operation_at=_at(candle.close_boundary_ms),
        position_id="position:postgres:lifecycle",
    )


def _exit_request(
    graph,
    *,
    suffix: str,
    trigger: bool,
    close_fill_id: str,
    correlation_id: str,
):
    command = graph.command
    position = graph.positions[0]
    cursor = graph.cursors[0]
    boundary = cursor.last_evaluated_closed_until_ms
    candle = _candle(
        symbol=command.symbol,
        open_ms=boundary,
        open_price=command.entry_reference_price,
        high_price=command.entry_reference_price,
        low_price=command.stop_price if trigger else command.entry_reference_price,
        close_price=command.entry_reference_price,
    )
    return PaperExitEvaluationRequest(
        position_id=position.position_id,
        expected_position_version=position.version,
        cursor_id=cursor.cursor_id,
        expected_cursor_version=cursor.version,
        expected_cursor_from_closed_until_ms=boundary,
        source_command_id=command.command_id,
        entry_order_id=position.entry_order_id,
        entry_fill_id=position.entry_fill_id,
        candles=(candle,),
        market_snapshot_closed_until_ms=candle.close_boundary_ms,
        safety_directive=None,
        evaluation_policy_id=PAPER_EXIT_EVALUATION_POLICY_ID,
        execution_mode=ExecutionMode.PAPER,
        explicit_paper_authorization=True,
        exit_decision_id=f"exit:postgres:{suffix}",
        close_order_id=f"order:postgres:close:{suffix}",
        exit_event_id=f"event:postgres:exit:{suffix}",
        close_order_created_event_id=f"event:postgres:close:created:{suffix}",
        close_order_validated_event_id=f"event:postgres:close:validated:{suffix}",
        close_order_opened_event_id=f"event:postgres:close:opened:{suffix}",
        journal_entry_ids=(
            f"event:postgres:close:created:{suffix}",
            f"event:postgres:close:validated:{suffix}",
            f"event:postgres:close:opened:{suffix}",
            f"event:postgres:exit:{suffix}",
        ),
        close_execution_fill_id=close_fill_id,
        close_execution_order_event_id=f"event:postgres:close:filled:{suffix}",
        close_execution_position_event_id=f"event:postgres:position:closed:{suffix}",
        close_execution_journal_entry_ids=(
            f"journal:postgres:close:filled:{suffix}",
            f"journal:postgres:position:closed:{suffix}",
        ),
        price_quantum=Q,
        fee_quantum=Q,
        quote_asset="USDT",
        created_at=_at(candle.close_boundary_ms),
        correlation_id=correlation_id,
        causation_id=f"causation:postgres:exit:{suffix}",
    )


@pytest.fixture
def clean_paper_factory(paper_session_factory):
    factory = paper_session_factory
    with factory.begin() as session:
        for model in (
            PaperJournalEntryRecord,
            PaperExitEvaluationCursorRecord,
            PaperExitDecisionRecord,
            PaperPositionRecord,
            PaperFillRecord,
            PaperOrderEventRecord,
            PaperOrderRecord,
            PaperExecutionCommandRecord,
            PaperSimulationPolicyRecord,
        ):
            session.execute(delete(model))
    return factory


def test_full_controlled_lifecycle_exact_once_and_journal_complete(
    clean_paper_factory,
):
    factory = clean_paper_factory
    worker = _worker(factory)
    ingestion = make_ingestion_request(identity_suffix="postgres-lifecycle")
    correlation_id = ingestion.correlation_id
    _seed_policy(factory, ingestion)

    ingested = worker.run_cycle(
        _cycle(
            ingestion.command_id,
            "ingest",
            correlation_id=correlation_id,
            entry_order_id=ingestion.order_id,
            ingestion_request=ingestion,
        )
    )
    assert (
        ingested.outcome is PaperLifecycleCycleOutcome.CYCLE_STAGE_COMPLETED
    ), (
        ingested.reason_code,
        ingested.child_outcome_codes,
        ingested.child_reason_codes,
    )
    assert ingested.final_lifecycle_state is PaperLifecycleState.ENTRY_ORDER_OPEN

    graph = _load(factory, ingestion.command_id)
    entry_request = _entry_request(
        graph, ingestion.simulation_policy, correlation_id
    )
    entered = worker.run_cycle(
        _cycle(
            ingestion.command_id,
            "entry",
            correlation_id=correlation_id,
            entry_order_id=entry_request.order_id,
            entry_fill_id=entry_request.fill_id,
            position_id=entry_request.position_id,
            entry_execution_request=entry_request,
        )
    )
    assert entered.outcome is PaperLifecycleCycleOutcome.CYCLE_STAGE_COMPLETED
    assert entered.final_lifecycle_state is PaperLifecycleState.POSITION_OPEN_CURSOR_READY
    assert entered.cursor_id is not None

    graph = _load(factory, ingestion.command_id)
    no_trigger_request = _exit_request(
        graph,
        suffix="no-trigger",
        trigger=False,
        close_fill_id="fill:postgres:unused:no-trigger",
        correlation_id=correlation_id,
    )
    no_trigger = worker.run_cycle(
        _cycle(
            ingestion.command_id,
            "no-trigger",
            correlation_id=correlation_id,
            position_id=graph.positions[0].position_id,
            cursor_id=graph.cursors[0].cursor_id,
            exit_evaluation_request=no_trigger_request,
        )
    )
    assert no_trigger.outcome is PaperLifecycleCycleOutcome.CYCLE_STAGE_COMPLETED
    assert no_trigger.final_lifecycle_state is PaperLifecycleState.POSITION_OPEN_CURSOR_READY
    assert no_trigger.cursor_version == 1

    graph = _load(factory, ingestion.command_id)
    trigger_boundary = graph.cursors[0].last_evaluated_closed_until_ms + 60_000
    exit_decision_id = "exit:postgres:trigger"
    close_order_id = "order:postgres:close:trigger"
    close_fill_id = simulated_close_fill_id(
        fill_contract_version=PAPER_FILL_CAUSAL_BOUNDARY_VERSION,
        order_id=close_order_id,
        exit_decision_id=exit_decision_id,
        exit_source_closed_until_ms=trigger_boundary,
        source_open_time_ms=trigger_boundary,
        source_close_boundary_ms=trigger_boundary + 60_000,
        simulation_policy_id=ingestion.simulation_policy.simulation_policy_id,
        slippage_policy_id=ingestion.simulation_policy.slippage_policy_id,
        fee_policy_id=ingestion.simulation_policy.fee_policy_id,
        latency_policy_id=ingestion.simulation_policy.latency_policy_id,
    )
    trigger_request = _exit_request(
        graph,
        suffix="trigger",
        trigger=True,
        close_fill_id=close_fill_id,
        correlation_id=correlation_id,
    )
    triggered = worker.run_cycle(
        _cycle(
            ingestion.command_id,
            "trigger",
            correlation_id=correlation_id,
            position_id=graph.positions[0].position_id,
            cursor_id=graph.cursors[0].cursor_id,
            exit_decision_id=exit_decision_id,
            close_order_id=close_order_id,
            exit_evaluation_request=trigger_request,
        )
    )
    assert triggered.outcome is PaperLifecycleCycleOutcome.CYCLE_STAGE_COMPLETED
    assert (
        triggered.final_lifecycle_state
        is PaperLifecycleState.POSITION_CLOSING_CLOSE_ORDER_OPEN
    )

    close_candle = _candle(
        symbol=graph.command.symbol,
        open_ms=trigger_boundary,
        open_price=graph.command.stop_price,
        high_price=graph.command.stop_price,
        low_price=graph.command.stop_price,
        close_price=graph.command.stop_price,
    )
    close_request = PaperCloseExecutionRequest(
        command_id=ingestion.command_id,
        order_id=close_order_id,
        expected_order_version=2,
        position_id=graph.positions[0].position_id,
        expected_position_version=graph.positions[0].version + 1,
        exit_decision_id=exit_decision_id,
        fill_role=PaperFillRole.CLOSE,
        candidate_candles=(close_candle,),
        market_snapshot_closed_until_ms=close_candle.close_boundary_ms,
        simulation_policy=ingestion.simulation_policy,
        price_quantum=ingestion.simulation_policy.price_quantum,
        fee_quantum=ingestion.simulation_policy.fee_quantum,
        quote_asset="USDT",
        fill_id=close_fill_id,
        order_event_id=trigger_request.close_execution_order_event_id,
        position_event_id=trigger_request.close_execution_position_event_id,
        journal_entry_ids=trigger_request.close_execution_journal_entry_ids,
        correlation_id=correlation_id,
        causation_id=trigger_request.causation_id,
        operation_at=_at(close_candle.close_boundary_ms),
    )
    closed = worker.run_cycle(
        _cycle(
            ingestion.command_id,
            "close",
            correlation_id=correlation_id,
            position_id=close_request.position_id,
            exit_decision_id=close_request.exit_decision_id,
            close_order_id=close_request.order_id,
            close_fill_id=close_request.fill_id,
            close_execution_request=close_request,
        )
    )
    assert closed.outcome is PaperLifecycleCycleOutcome.CYCLE_COMPLETE
    assert closed.final_lifecycle_state is PaperLifecycleState.POSITION_CLOSED

    with factory() as session:
        counts = {
            model.__tablename__: session.scalar(
                select(func.count()).select_from(model)
            )
            for model in (
                PaperExecutionCommandRecord,
                PaperOrderRecord,
                PaperFillRecord,
                PaperPositionRecord,
                PaperExitEvaluationCursorRecord,
                PaperExitDecisionRecord,
                PaperOrderEventRecord,
                PaperJournalEntryRecord,
            )
        }
        position = session.get(PaperPositionRecord, close_request.position_id)
        accounting = (
            position.entry_fees,
            position.exit_fees,
            position.realized_pnl,
            position.version,
        )
    assert counts == {
        "paper_execution_commands": 1,
        "paper_orders": 2,
        "paper_fills": 2,
        "paper_positions": 1,
        "paper_exit_evaluation_cursors": 1,
        "paper_exit_decisions": 1,
        "paper_order_events": 8,
        "paper_journal_entries": 12,
    }
    assert position.state == PaperPositionState.CLOSED.value
    assert position.exit_fill_id == close_fill_id
    assert position.entry_fees > 0
    assert position.exit_fees > 0

    replay = worker.run_cycle(
        _cycle(
            ingestion.command_id,
            "closed-replay",
            correlation_id=correlation_id,
            position_id=close_request.position_id,
            close_order_id=close_request.order_id,
            close_fill_id=close_request.fill_id,
            close_execution_request=close_request,
        )
    )
    assert replay.outcome is PaperLifecycleCycleOutcome.CYCLE_COMPLETE
    assert replay.stages_attempted == 0
    with factory() as session:
        replay_position = session.get(PaperPositionRecord, close_request.position_id)
        assert (
            replay_position.entry_fees,
            replay_position.exit_fees,
            replay_position.realized_pnl,
            replay_position.version,
        ) == accounting
        assert session.scalar(
            select(func.count()).select_from(PaperJournalEntryRecord)
        ) == 12
