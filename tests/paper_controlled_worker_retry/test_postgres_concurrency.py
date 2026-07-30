from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier, Lock

import pytest
from sqlalchemy import func, select

from app.db.paper_models import (
    PaperExecutionCommandRecord,
    PaperExitDecisionRecord,
    PaperExitEvaluationCursorRecord,
    PaperFillRecord,
    PaperJournalEntryRecord,
    PaperOrderRecord,
    PaperPositionRecord,
)
from app.engine_execution.paper_idempotency import simulated_close_fill_id
from app.engine_paper.command_ingestion_service import PaperCommandIngestionService
from app.engine_paper.controlled_worker import (
    PaperControlledLifecycleWorker,
    PaperLifecycleCycleOutcome,
    PaperLifecycleFaultPoint,
    SqlAlchemyPaperLifecycleGraphLoader,
)
from app.engine_paper.exit_evaluation_service import PaperExitEvaluationService
from app.engine_paper.fill_causal_boundary import (
    PAPER_FILL_CAUSAL_BOUNDARY_VERSION,
)
from app.engine_paper.fill_simulator import PaperFillRole
from app.engine_paper.order_execution_service import (
    PaperCloseExecutionRequest,
    PaperOrderExecutionService,
)
from app.engine_paper.unit_of_work import PaperUnitOfWork
from tests.paper_command_ingestion_retry.conftest import (
    make_request as make_ingestion_request,
)

from .test_postgres_full_lifecycle import (
    _at,
    _candle,
    _cycle,
    _entry_request,
    _exit_request,
    _load,
    _seed_policy,
    _worker,
    clean_paper_factory,  # noqa: F401
)


class FirstPairBarrierLoader:
    def __init__(self, delegate):
        self.delegate = delegate
        self.barrier = Barrier(2)
        self.lock = Lock()
        self.calls = 0

    def load(self, command_id):
        graph = self.delegate.load(command_id)
        with self.lock:
            self.calls += 1
            wait = self.calls <= 2
        if wait:
            self.barrier.wait(timeout=10)
        return graph


def _concurrent_worker(factory):
    uow_factory = lambda: PaperUnitOfWork(factory)
    loader = FirstPairBarrierLoader(SqlAlchemyPaperLifecycleGraphLoader(uow_factory))
    return PaperControlledLifecycleWorker(
        loader,
        PaperCommandIngestionService(uow_factory, factory),
        PaperOrderExecutionService(uow_factory, factory),
        PaperExitEvaluationService(uow_factory, factory),
    )


def _run_pair(worker, request):
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                worker.run_cycle,
                replace(request, cycle_id=f"cycle:concurrent:{index}"),
            )
            for index in range(2)
        ]
        return tuple(future.result(timeout=20) for future in futures)


def _seed_through_entry(factory, suffix):
    ingestion = make_ingestion_request(identity_suffix=suffix)
    _seed_policy(factory, ingestion)
    normal = _worker(factory)
    ingested = normal.run_cycle(
        _cycle(
            ingestion.command_id,
            f"{suffix}:ingest",
            correlation_id=ingestion.correlation_id,
            entry_order_id=ingestion.order_id,
            ingestion_request=ingestion,
        )
    )
    assert ingested.successful if hasattr(ingested, "successful") else ingested.outcome
    entry = _entry_request(
        _load(factory, ingestion.command_id),
        ingestion.simulation_policy,
        ingestion.correlation_id,
    )
    entered = normal.run_cycle(
        _cycle(
            ingestion.command_id,
            f"{suffix}:entry",
            correlation_id=ingestion.correlation_id,
            entry_execution_request=entry,
        )
    )
    assert entered.outcome is PaperLifecycleCycleOutcome.CYCLE_STAGE_COMPLETED
    return ingestion, entry


def _trigger_setup(factory, suffix):
    ingestion, entry = _seed_through_entry(factory, suffix)
    graph = _load(factory, ingestion.command_id)
    trigger_boundary = graph.cursors[0].last_evaluated_closed_until_ms + 60_000
    decision_id = f"exit:postgres:{suffix}"
    close_order_id = f"order:postgres:close:{suffix}"
    close_fill_id = simulated_close_fill_id(
        fill_contract_version=PAPER_FILL_CAUSAL_BOUNDARY_VERSION,
        order_id=close_order_id,
        exit_decision_id=decision_id,
        exit_source_closed_until_ms=trigger_boundary,
        source_open_time_ms=trigger_boundary,
        source_close_boundary_ms=trigger_boundary + 60_000,
        simulation_policy_id=ingestion.simulation_policy.simulation_policy_id,
        slippage_policy_id=ingestion.simulation_policy.slippage_policy_id,
        fee_policy_id=ingestion.simulation_policy.fee_policy_id,
        latency_policy_id=ingestion.simulation_policy.latency_policy_id,
    )
    trigger = _exit_request(
        graph,
        suffix=suffix,
        trigger=True,
        close_fill_id=close_fill_id,
        correlation_id=ingestion.correlation_id,
    )
    return ingestion, entry, graph, trigger, close_fill_id


def test_concurrent_ingestion_one_created_one_existing(clean_paper_factory):
    factory = clean_paper_factory
    ingestion = make_ingestion_request(identity_suffix="concurrent-ingest")
    _seed_policy(factory, ingestion)
    request = _cycle(
        ingestion.command_id,
        "concurrent-ingest",
        correlation_id=ingestion.correlation_id,
        ingestion_request=ingestion,
    )
    results = _run_pair(_concurrent_worker(factory), request)
    assert {item.outcome for item in results} == {
        PaperLifecycleCycleOutcome.CYCLE_STAGE_COMPLETED
    }
    assert {code for item in results for code in item.child_outcome_codes} == {
        "COMMAND_AND_ORDER_CREATED",
        "COMMAND_AND_ORDER_ALREADY_EXIST",
    }
    with factory() as session:
        assert session.scalar(
            select(func.count()).select_from(PaperExecutionCommandRecord)
        ) == 1
        assert session.scalar(select(func.count()).select_from(PaperOrderRecord)) == 1


def test_concurrent_entry_one_fill_position_cursor_graph(clean_paper_factory):
    factory = clean_paper_factory
    ingestion = make_ingestion_request(identity_suffix="concurrent-entry")
    _seed_policy(factory, ingestion)
    _worker(factory).run_cycle(
        _cycle(
            ingestion.command_id,
            "seed-ingest",
            correlation_id=ingestion.correlation_id,
            ingestion_request=ingestion,
        )
    )
    entry = _entry_request(
        _load(factory, ingestion.command_id),
        ingestion.simulation_policy,
        ingestion.correlation_id,
    )
    results = _run_pair(
        _concurrent_worker(factory),
        _cycle(
            ingestion.command_id,
            "concurrent-entry",
            correlation_id=ingestion.correlation_id,
            entry_execution_request=entry,
        ),
    )
    assert {code for item in results for code in item.child_outcome_codes} == {
        "ENTRY_EXECUTED",
        "ENTRY_ALREADY_EXECUTED",
    }
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(PaperFillRecord)) == 1
        assert session.scalar(select(func.count()).select_from(PaperPositionRecord)) == 1
        assert session.scalar(
            select(func.count()).select_from(PaperExitEvaluationCursorRecord)
        ) == 1


def test_concurrent_no_trigger_one_cursor_advance(clean_paper_factory):
    factory = clean_paper_factory
    ingestion, _ = _seed_through_entry(factory, "concurrent-no-trigger")
    graph = _load(factory, ingestion.command_id)
    request = _exit_request(
        graph,
        suffix="concurrent-no-trigger",
        trigger=False,
        close_fill_id="fill:unused:concurrent:no-trigger",
        correlation_id=ingestion.correlation_id,
    )
    results = _run_pair(
        _concurrent_worker(factory),
        _cycle(
            ingestion.command_id,
            "concurrent-no-trigger",
            correlation_id=ingestion.correlation_id,
            exit_evaluation_request=request,
        ),
    )
    assert {code for item in results for code in item.child_outcome_codes} == {
        "NO_EXIT_TRIGGER_CURSOR_ADVANCED",
        "CURSOR_ALREADY_ADVANCED",
    }
    with factory() as session:
        cursor = session.scalar(select(PaperExitEvaluationCursorRecord))
        assert cursor.version == 1
        assert session.scalar(
            select(func.count()).select_from(PaperExitDecisionRecord)
        ) == 0


def test_concurrent_trigger_one_exit_and_close_order_graph(clean_paper_factory):
    factory = clean_paper_factory
    ingestion, _, _, trigger, _ = _trigger_setup(
        factory, "concurrent-trigger"
    )
    results = _run_pair(
        _concurrent_worker(factory),
        _cycle(
            ingestion.command_id,
            "concurrent-trigger",
            correlation_id=ingestion.correlation_id,
            exit_evaluation_request=trigger,
        ),
    )
    assert {code for item in results for code in item.child_outcome_codes} == {
        "EXIT_PREPARED",
        "EXIT_ALREADY_PREPARED",
    }
    with factory() as session:
        assert session.scalar(
            select(func.count()).select_from(PaperExitDecisionRecord)
        ) == 1
        assert session.scalar(select(func.count()).select_from(PaperOrderRecord)) == 2


def test_concurrent_close_one_fill_and_pnl_application(clean_paper_factory):
    factory = clean_paper_factory
    ingestion, _, graph, trigger, close_fill_id = _trigger_setup(
        factory, "concurrent-close"
    )
    _worker(factory).run_cycle(
        _cycle(
            ingestion.command_id,
            "seed-trigger",
            correlation_id=ingestion.correlation_id,
            exit_evaluation_request=trigger,
        )
    )
    boundary = trigger.candles[0].close_boundary_ms
    candle = _candle(
        symbol=graph.command.symbol,
        open_ms=boundary,
        open_price=graph.command.stop_price,
        high_price=graph.command.stop_price,
        low_price=graph.command.stop_price,
        close_price=graph.command.stop_price,
    )
    close = PaperCloseExecutionRequest(
        command_id=ingestion.command_id,
        order_id=trigger.close_order_id,
        expected_order_version=2,
        position_id=graph.positions[0].position_id,
        expected_position_version=graph.positions[0].version + 1,
        exit_decision_id=trigger.exit_decision_id,
        fill_role=PaperFillRole.CLOSE,
        candidate_candles=(candle,),
        market_snapshot_closed_until_ms=candle.close_boundary_ms,
        simulation_policy=ingestion.simulation_policy,
        price_quantum=ingestion.simulation_policy.price_quantum,
        fee_quantum=ingestion.simulation_policy.fee_quantum,
        quote_asset="USDT",
        fill_id=close_fill_id,
        order_event_id=trigger.close_execution_order_event_id,
        position_event_id=trigger.close_execution_position_event_id,
        journal_entry_ids=trigger.close_execution_journal_entry_ids,
        correlation_id=ingestion.correlation_id,
        causation_id=trigger.causation_id,
        operation_at=_at(candle.close_boundary_ms),
    )
    results = _run_pair(
        _concurrent_worker(factory),
        _cycle(
            ingestion.command_id,
            "concurrent-close",
            correlation_id=ingestion.correlation_id,
            close_execution_request=close,
        ),
    )
    assert {code for item in results for code in item.child_outcome_codes} == {
        "CLOSE_EXECUTED",
        "CLOSE_ALREADY_EXECUTED",
    }
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(PaperFillRecord)) == 2
        position = session.get(PaperPositionRecord, close.position_id)
        assert position.state == "CLOSED"
        accounting = (position.exit_fees, position.realized_pnl)
        assert session.scalar(
            select(func.count()).select_from(PaperJournalEntryRecord)
        ) == 12
    assert accounting[0] > 0


@pytest.mark.parametrize(
    "fault_point",
    (
        PaperLifecycleFaultPoint.BEFORE_GRAPH_LOAD,
        PaperLifecycleFaultPoint.AFTER_GRAPH_LOAD,
        PaperLifecycleFaultPoint.BEFORE_CHILD_INVOCATION,
        PaperLifecycleFaultPoint.AFTER_CHILD_SUCCESS_BEFORE_GRAPH_RELOAD,
        PaperLifecycleFaultPoint.DURING_GRAPH_RELOAD,
        PaperLifecycleFaultPoint.AFTER_GRAPH_RELOAD_BEFORE_RESULT,
        PaperLifecycleFaultPoint.BEFORE_CANCELLATION_CHECK,
    ),
)
def test_postgres_worker_fault_resume_uses_persisted_graph(
    clean_paper_factory, fault_point
):
    factory = clean_paper_factory
    ingestion = make_ingestion_request(
        identity_suffix=f"fault-{fault_point.value.lower()}"
    )
    _seed_policy(factory, ingestion)
    normal = _worker(factory)
    normal.run_cycle(
        _cycle(
            ingestion.command_id,
            "fault-seed-ingest",
            correlation_id=ingestion.correlation_id,
            ingestion_request=ingestion,
        )
    )
    entry = _entry_request(
        _load(factory, ingestion.command_id),
        ingestion.simulation_policy,
        ingestion.correlation_id,
    )
    seen = []

    def inject(actual):
        seen.append(actual)
        if actual is fault_point:
            raise RuntimeError(f"FAULT:{actual.value}")

    uow_factory = lambda: PaperUnitOfWork(factory)
    faulting = PaperControlledLifecycleWorker(
        SqlAlchemyPaperLifecycleGraphLoader(uow_factory),
        PaperCommandIngestionService(uow_factory, factory),
        PaperOrderExecutionService(uow_factory, factory),
        PaperExitEvaluationService(uow_factory, factory),
        fault_injector=inject,
    )
    request = _cycle(
        ingestion.command_id,
        "fault-entry",
        correlation_id=ingestion.correlation_id,
        entry_execution_request=entry,
    )
    with pytest.raises(RuntimeError, match="FAULT:"):
        faulting.run_cycle(request)
    resumed = normal.run_cycle(request)
    assert resumed.outcome in {
        PaperLifecycleCycleOutcome.CYCLE_STAGE_COMPLETED,
        PaperLifecycleCycleOutcome.CYCLE_BLOCKED_AWAITING_INPUT,
    }
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(PaperFillRecord)) == 1
        assert session.scalar(select(func.count()).select_from(PaperPositionRecord)) == 1
        assert session.scalar(
            select(func.count()).select_from(PaperExitEvaluationCursorRecord)
        ) == 1
    assert seen.count(fault_point) == 1
