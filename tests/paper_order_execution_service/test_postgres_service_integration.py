from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal
from threading import Barrier

import pytest
from sqlalchemy import func, select

from app.db.paper_models import (
    PaperFillRecord,
    PaperJournalEntryRecord,
    PaperOrderEventRecord,
    PaperOrderRecord,
    PaperPositionRecord,
)
from app.engine_execution.paper_state_machine import create_paper_order
from app.engine_exit.paper_exit import create_exit_decision
from app.engine_paper.fill_simulator import PaperFillRole
from app.engine_paper.order_execution_service import (
    PaperCloseExecutionRequest,
    PaperEntryExecutionRequest,
    PaperOrderExecutionOutcome,
    PaperOrderExecutionService,
)
from app.engine_paper.repository_results import RepositoryOutcome
from app.engine_paper.unit_of_work import PaperUnitOfWork
from app.engine_safety import PaperExitCause, PaperPositionState, PaperReasonCode

from .conftest import (
    NOW,
    OPERATION_AT,
    FakeUow,
    make_candle,
    make_command,
    make_policy,
    simulated_fill,
)
from tests.paper_repository.test_atomic_lifecycle_and_concurrency import _open_order


def _seed_open_order(factory, *, role="ENTRY", suffix="service-pg"):
    command = make_command(
        command_id=f"command:{suffix}",
        idempotency_key=f"command:key:{suffix}",
        pipeline_run_id=f"run:{suffix}",
        analysis_result_id=f"analysis:{suffix}",
        setup_id=f"setup:{suffix}",
        strategy_decision_id=f"strategy:{suffix}",
        risk_decision_id=f"risk:{suffix}",
    )
    with PaperUnitOfWork(factory) as uow:
        assert (
            uow.repositories.commands.create_or_get_command(command).outcome
            is RepositoryOutcome.CREATED
        )
        order = _open_order(uow, command, suffix, role=role)
        assert uow.commit().successful
    return command, order


def _entry_request(command, order, *, suffix="service-pg"):
    policy = make_policy()
    candle = make_candle()
    fill = simulated_fill(command, order, policy, candle, PaperFillRole.ENTRY)
    return PaperEntryExecutionRequest(
        command_id=command.command_id,
        order_id=order.order_id,
        expected_order_version=order.version,
        fill_role=PaperFillRole.ENTRY,
        candidate_candles=(candle,),
        market_snapshot_closed_until_ms=candle.close_boundary_ms,
        simulation_policy=policy,
        price_quantum=policy.price_quantum,
        fee_quantum=policy.fee_quantum,
        quote_asset="USDT",
        fill_id=fill.fill_id,
        position_id=f"position:{suffix}",
        order_event_id=f"event:{suffix}:fill-order",
        position_event_id=f"event:{suffix}:open-position",
        journal_entry_ids=(
            f"journal:{suffix}:fill-order",
            f"journal:{suffix}:open-position",
        ),
        correlation_id=f"correlation:{suffix}",
        causation_id=f"causation:{suffix}",
        operation_at=OPERATION_AT,
    )


def _service(factory):
    return PaperOrderExecutionService(
        lambda: PaperUnitOfWork(factory),
        factory,
    )


def _seed_close_request(factory, *, suffix="service-pg-close"):
    command, entry_order = _seed_open_order(
        factory, suffix=f"{suffix}-entry"
    )
    entry_request = _entry_request(
        command, entry_order, suffix=f"{suffix}-entry"
    )
    entry = _service(factory).execute_entry(entry_request)
    assert entry.outcome is PaperOrderExecutionOutcome.ENTRY_EXECUTED
    with PaperUnitOfWork(factory) as uow:
        position = uow.repositories.positions.get_position(entry_request.position_id)
        close_order = _open_order(uow, command, suffix, role="EXIT")
        decision, event = create_exit_decision(
            position,
            exit_decision_id=f"exit:{suffix}",
            idempotency_key=f"exit:key:{suffix}",
            expected_position_version=position.version,
            cause=PaperExitCause.STOP_LOSS,
            decision_price=Decimal("90"),
            source_closed_until_ms=position.last_mark_closed_until_ms,
            decided_at=NOW,
            reason_code=PaperReasonCode.PAPER_EXIT_STOP_LOSS_TRIGGERED,
            event_id=f"event:{suffix}:exit",
        )
        assert (
            uow.repositories.exits.create_or_get_exit_decision(
                position.position_id,
                position.version,
                decision,
                event,
                event,
            ).outcome
            is RepositoryOutcome.CREATED
        )
        assert uow.commit().successful
    with factory() as session:
        closing_version = session.get(
            PaperPositionRecord, position.position_id
        ).version
    policy = make_policy()
    candle = make_candle()
    fill = simulated_fill(command, close_order, policy, candle, PaperFillRole.CLOSE)
    request = PaperCloseExecutionRequest(
        command_id=command.command_id,
        order_id=close_order.order_id,
        expected_order_version=close_order.version,
        position_id=position.position_id,
        expected_position_version=closing_version,
        exit_decision_id=decision.exit_decision_id,
        fill_role=PaperFillRole.CLOSE,
        candidate_candles=(candle,),
        market_snapshot_closed_until_ms=candle.close_boundary_ms,
        simulation_policy=policy,
        price_quantum=policy.price_quantum,
        fee_quantum=policy.fee_quantum,
        quote_asset="USDT",
        fill_id=fill.fill_id,
        order_event_id=f"event:{suffix}:fill-order",
        position_event_id=f"event:{suffix}:close-position",
        journal_entry_ids=(
            f"journal:{suffix}:fill-order",
            f"journal:{suffix}:close-position",
        ),
        correlation_id=f"correlation:{suffix}",
        causation_id=f"causation:{suffix}",
        operation_at=OPERATION_AT,
    )
    return request, closing_version


def test_real_postgres_entry_commit_and_exact_replay_are_one_graph(
    paper_session_factory,
):
    command, order = _seed_open_order(paper_session_factory)
    request = _entry_request(command, order)
    first = _service(paper_session_factory).execute_entry(request)
    second = _service(paper_session_factory).execute_entry(request)
    assert first.outcome is PaperOrderExecutionOutcome.ENTRY_EXECUTED
    assert second.outcome is PaperOrderExecutionOutcome.ENTRY_ALREADY_EXECUTED
    with paper_session_factory() as session:
        assert session.scalar(select(func.count()).select_from(PaperFillRecord)) == 1
        assert session.scalar(select(func.count()).select_from(PaperPositionRecord)) == 1
        stored_order = session.get(PaperOrderRecord, order.order_id)
        assert stored_order.state == "FILLED"
        assert stored_order.version == order.version + 1


def test_real_postgres_entry_concurrency_creates_exactly_one_fill_and_position(
    paper_session_factory,
):
    command, order = _seed_open_order(
        paper_session_factory, suffix="service-pg-concurrent"
    )
    request = _entry_request(command, order, suffix="service-pg-concurrent")
    barrier = Barrier(2)

    def worker():
        barrier.wait()
        return _service(paper_session_factory).execute_entry(request).outcome

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = [future.result(timeout=20) for future in (pool.submit(worker), pool.submit(worker))]
    assert set(outcomes) == {
        PaperOrderExecutionOutcome.ENTRY_EXECUTED,
        PaperOrderExecutionOutcome.ENTRY_ALREADY_EXECUTED,
    }
    with paper_session_factory() as session:
        assert session.scalar(select(func.count()).select_from(PaperFillRecord)) == 1
        assert session.scalar(select(func.count()).select_from(PaperPositionRecord)) == 1


def test_real_postgres_close_commit_replay_and_pnl_apply_once(
    paper_session_factory,
):
    request, closing_version = _seed_close_request(paper_session_factory)
    first = _service(paper_session_factory).execute_close(request)
    second = _service(paper_session_factory).execute_close(request)
    assert first.outcome is PaperOrderExecutionOutcome.CLOSE_EXECUTED
    assert second.outcome is PaperOrderExecutionOutcome.CLOSE_ALREADY_EXECUTED
    assert first.position_state is PaperPositionState.CLOSED
    assert first.position_version == closing_version + 1
    assert second.position_version == first.position_version
    assert second.position_id == first.position_id
    with paper_session_factory() as session:
        stored = session.get(PaperPositionRecord, request.position_id)
        assert stored.state == "CLOSED"
        assert stored.version == closing_version + 1
        assert session.scalar(select(func.count()).select_from(PaperFillRecord)) == 2


def test_real_postgres_close_concurrency_applies_one_fill_pnl_and_version(
    paper_session_factory,
):
    request, closing_version = _seed_close_request(
        paper_session_factory, suffix="service-pg-close-concurrent"
    )
    barrier = Barrier(2)

    def worker():
        barrier.wait()
        return _service(paper_session_factory).execute_close(request)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = [
            future.result(timeout=20)
            for future in (pool.submit(worker), pool.submit(worker))
        ]
    assert {item.outcome for item in outcomes} == {
        PaperOrderExecutionOutcome.CLOSE_EXECUTED,
        PaperOrderExecutionOutcome.CLOSE_ALREADY_EXECUTED,
    }
    with paper_session_factory() as session:
        stored = session.get(PaperPositionRecord, request.position_id)
        assert stored.state == "CLOSED"
        assert stored.version == closing_version + 1
        assert session.scalar(select(func.count()).select_from(PaperFillRecord)) == 2


class _FaultPaperUow(PaperUnitOfWork):
    def __init__(self, factory, stage):
        super().__init__(factory)
        self._stage = stage

    def __enter__(self):
        entered = super().__enter__()
        entered.repositories.fault_injector = (
            lambda current: (_ for _ in ()).throw(RuntimeError("injected"))
            if current == self._stage
            else None
        )
        return entered


@pytest.mark.parametrize(
    "stage",
    [
        "entry_after_fill",
        "entry_after_order",
        "entry_after_position",
        "entry_after_event",
        "entry_after_journal",
    ],
)
def test_real_postgres_entry_fault_at_each_atomic_boundary_leaves_no_fragment(
    paper_session_factory,
    stage,
):
    command, order = _seed_open_order(
        paper_session_factory, suffix=f"service-pg-fault-{stage}"
    )
    request = _entry_request(
        command, order, suffix=f"service-pg-fault-{stage}"
    )
    target = PaperOrderExecutionService(
        lambda: _FaultPaperUow(paper_session_factory, stage),
        paper_session_factory,
    )
    outcome = target.execute_entry(request)
    assert outcome.outcome is PaperOrderExecutionOutcome.INTERNAL_INVARIANT_FAILURE
    with paper_session_factory() as session:
        assert session.scalar(select(func.count()).select_from(PaperFillRecord)) == 0
        assert session.scalar(select(func.count()).select_from(PaperPositionRecord)) == 0
        stored = session.get(PaperOrderRecord, order.order_id)
        assert stored.state == "OPEN"
        assert stored.version == order.version


def test_real_postgres_service_journal_and_order_event_counts_are_atomic(
    paper_session_factory,
):
    command, order = _seed_open_order(
        paper_session_factory, suffix="service-pg-events"
    )
    request = _entry_request(command, order, suffix="service-pg-events")
    assert (
        _service(paper_session_factory).execute_entry(request).outcome
        is PaperOrderExecutionOutcome.ENTRY_EXECUTED
    )
    with paper_session_factory() as session:
        # CREATED/VALIDATED/OPEN contribute three order events; execution adds
        # exactly one FILLED order event and two fill-linked journal rows.
        order_events = session.scalar(
            select(func.count())
            .select_from(PaperOrderEventRecord)
            .where(PaperOrderEventRecord.order_id == order.order_id)
        )
        journal = session.scalar(
            select(func.count())
            .select_from(PaperJournalEntryRecord)
            .where(PaperJournalEntryRecord.fill_id == request.fill_id)
        )
        assert order_events == 4
        assert journal == 2
