from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal
from threading import Barrier

import pytest
from sqlalchemy import func, select

from app.db.paper_models import (
    PaperExecutionCommandRecord,
    PaperExitDecisionRecord,
    PaperFillRecord,
    PaperJournalEntryRecord,
    PaperOrderEventRecord,
    PaperOrderRecord,
    PaperPositionRecord,
)
from app.engine_execution.paper_idempotency import (
    command_idempotency_key,
    exit_decision_idempotency_key,
    fill_idempotency_key,
    order_idempotency_key,
)
from app.engine_execution.paper_state_machine import (
    create_paper_order,
    fill_order,
    transition_order,
)
from app.engine_exit.paper_exit import create_exit_decision
from app.engine_journal.paper_events import PaperDomainEvent
from app.engine_paper.repository_results import RepositoryOutcome
from app.engine_paper.unit_of_work import PaperUnitOfWork
from app.engine_position.paper_state_machine import apply_close_fill, apply_entry_fill
from app.engine_safety.paper_domain import (
    PaperEventType,
    PaperExitCause,
    PaperOrderState,
    PaperReasonCode,
)
from tests.paper_domain.conftest import NOW, make_command, make_fill


def _event(event_id, event_type, aggregate_type, aggregate_id, version, cause, reason):
    return PaperDomainEvent(
        event_id=event_id,
        event_type=event_type,
        occurred_at=NOW,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        correlation_id="command:1",
        causation_id=cause,
        reason_code=reason,
        aggregate_version=version,
    )


def _command(suffix: str = "1"):
    pipeline = f"run:{suffix}"
    analysis = f"analysis:{suffix}"
    setup = f"setup:{suffix}"
    strategy = f"strategy:{suffix}"
    risk = f"risk:{suffix}"
    return make_command(
        command_id=f"command:{suffix}",
        pipeline_run_id=pipeline,
        analysis_result_id=analysis,
        setup_id=setup,
        strategy_decision_id=strategy,
        risk_decision_id=risk,
        idempotency_key=command_idempotency_key(
            pipeline_run_id=pipeline,
            analysis_result_id=analysis,
            setup_id=setup,
            strategy_decision_id=strategy,
            risk_decision_id=risk,
            symbol="BTCUSDT",
            side="LONG",
            closed_until_ms=1_000,
            configuration_fingerprint="config:v1",
        ),
    )


def _open_order(uow, command, suffix: str, role: str = "ENTRY"):
    created = create_paper_order(
        command,
        order_id=f"order:{suffix}",
        idempotency_key=order_idempotency_key(command.command_id, role),
        occurred_at=NOW,
        event_id=f"event:{suffix}:created",
    )
    assert uow.repositories.orders.create_or_get_order(
        command,
        created.order,
        created.events[0],
        created.events[0],
        order_role=role,
    ).outcome is RepositoryOutcome.CREATED
    validated_change = transition_order(
        created.order,
        PaperOrderState.VALIDATED,
        expected_version=0,
        occurred_at=NOW,
        event_id=f"event:{suffix}:validated",
    )
    validated_event = validated_change.events[0]
    validated = uow.repositories.orders.transition_order(
        created.order.order_id,
        0,
        PaperOrderState.VALIDATED,
        validated_event,
        validated_event,
        occurred_at=NOW,
    )
    assert validated.outcome is RepositoryOutcome.UPDATED
    opened_change = transition_order(
        validated_change.order,
        PaperOrderState.OPEN,
        expected_version=1,
        occurred_at=NOW,
        event_id=f"event:{suffix}:opened",
    )
    opened_event = opened_change.events[0]
    opened = uow.repositories.orders.transition_order(
        created.order.order_id,
        1,
        PaperOrderState.OPEN,
        opened_event,
        opened_event,
        occurred_at=NOW,
    )
    assert opened.outcome is RepositoryOutcome.UPDATED
    return opened.value


def _prepare_entry(uow, suffix: str = "1"):
    command = _command(suffix)
    assert uow.repositories.commands.create_or_get_command(command).successful
    order = _open_order(uow, command, suffix)
    fill = make_fill(
        fill_id=f"fill:{suffix}:entry",
        order_id=order.order_id,
        idempotency_key=fill_idempotency_key(order.order_id, "ENTRY"),
    )
    order_change = fill_order(
        order, fill, expected_version=2, event_id=f"event:{suffix}:entry-fill"
    )
    position_change = apply_entry_fill(
        None,
        command,
        order_change.order,
        fill,
        position_id=f"position:{suffix}",
        event_id=f"event:{suffix}:position-open",
    )
    return command, order, fill, order_change.events[0], position_change


def _apply_entry(uow, suffix: str = "1"):
    command, order, fill, order_event, position_change = _prepare_entry(uow, suffix)
    outcome = uow.repositories.apply_entry_fill_and_open_position(
        order.order_id,
        2,
        fill,
        position_change.position,
        order_event,
        position_change.events[0],
        (order_event, position_change.events[0]),
    )
    return outcome, command, fill, position_change.position


def _prepare_close(uow):
    entry, command, _, position = _apply_entry(uow)
    assert entry.successful
    close_order = _open_order(uow, command, "close", role="EXIT")
    decision, exit_event = create_exit_decision(
        position,
        exit_decision_id="exit:1",
        idempotency_key=exit_decision_idempotency_key(
            position.position_id, position.version, PaperExitCause.STOP_LOSS
        ),
        expected_position_version=0,
        cause=PaperExitCause.STOP_LOSS,
        decision_price=Decimal("90"),
        source_closed_until_ms=1_120,
        decided_at=NOW,
        reason_code=PaperReasonCode.PAPER_EXIT_STOP_LOSS_TRIGGERED,
        event_id="event:exit:1",
    )
    assert uow.repositories.exits.create_or_get_exit_decision(
        position.position_id, 0, decision, exit_event, exit_event
    ).outcome is RepositoryOutcome.CREATED
    close_fill = make_fill(
        fill_id="fill:close:1",
        order_id=close_order.order_id,
        idempotency_key=fill_idempotency_key(close_order.order_id, "EXIT"),
        price=Decimal("90"),
        source_closed_until_ms=1_120,
    )
    order_change = fill_order(
        close_order, close_fill, expected_version=2, event_id="event:close-order"
    )
    closing = uow.repositories.positions.get_position(position.position_id)
    position_change = apply_close_fill(
        closing,
        close_fill,
        expected_version=1,
        event_id="event:position-closed",
    )
    return decision, close_order, close_fill, order_change.events[0], position_change.events[0]


def test_entry_fill_and_position_open_are_atomic_and_replay_safe(paper_session_factory):
    with PaperUnitOfWork(paper_session_factory) as uow:
        created, _, fill, position = _apply_entry(uow)
        assert created.outcome is RepositoryOutcome.CREATED
        assert uow.commit().successful
    with PaperUnitOfWork(paper_session_factory) as uow:
        replay = uow.repositories.apply_entry_fill_and_open_position(
            "order:1",
            2,
            fill,
            position,
            _event(
                "event:1:entry-fill",
                PaperEventType.PAPER_ORDER_FILLED,
                "paper_order",
                "order:1",
                3,
                fill.fill_id,
                PaperReasonCode.PAPER_ORDER_FILLED,
            ),
            _event(
                "event:1:position-open",
                PaperEventType.PAPER_POSITION_OPENED,
                "paper_position",
                "position:1",
                0,
                fill.fill_id,
                PaperReasonCode.PAPER_POSITION_OPENED,
            ),
            (),
        )
        assert replay.outcome is RepositoryOutcome.EXISTING_IDEMPOTENT
    with paper_session_factory() as session:
        assert session.scalar(select(func.count()).select_from(PaperFillRecord)) == 1
        assert session.scalar(select(func.count()).select_from(PaperPositionRecord)) == 1


def test_entry_conflicting_fill_and_partial_fill_fail_closed(paper_session_factory):
    with PaperUnitOfWork(paper_session_factory) as uow:
        created, _, fill, position = _apply_entry(uow)
        assert created.successful
        uow.commit()
    conflicting = replace(fill, price=fill.price + Decimal("1"))
    with PaperUnitOfWork(paper_session_factory) as uow:
        outcome = uow.repositories.apply_entry_fill_and_open_position(
            "order:1", 2, conflicting, position,
            _event("event:x", PaperEventType.PAPER_ORDER_FILLED, "paper_order", "order:1", 3, "x", PaperReasonCode.PAPER_ORDER_FILLED),
            _event("event:y", PaperEventType.PAPER_POSITION_OPENED, "paper_position", "position:1", 0, "y", PaperReasonCode.PAPER_POSITION_OPENED),
            (),
        )
        assert outcome.outcome is RepositoryOutcome.IDEMPOTENCY_CONFLICT


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
def test_entry_fault_injection_rolls_back_entire_graph(paper_session_factory, stage):
    with pytest.raises(RuntimeError, match="injected"):
        with PaperUnitOfWork(paper_session_factory) as uow:
            _, order, fill, order_event, position_change = _prepare_entry(uow)
            uow.repositories.fault_injector = (
                lambda current: (_ for _ in ()).throw(RuntimeError("injected"))
                if current == stage
                else None
            )
            uow.repositories.apply_entry_fill_and_open_position(
                order.order_id, 2, fill, position_change.position, order_event,
                position_change.events[0], (order_event, position_change.events[0]),
            )
    with paper_session_factory() as session:
        assert session.scalar(select(func.count()).select_from(PaperExecutionCommandRecord)) == 0
        assert session.scalar(select(func.count()).select_from(PaperFillRecord)) == 0
        assert session.scalar(select(func.count()).select_from(PaperPositionRecord)) == 0


def test_active_position_constraint_is_normalized(paper_session_factory):
    with PaperUnitOfWork(paper_session_factory) as uow:
        first, _, _, _ = _apply_entry(uow, "1")
        assert first.outcome is RepositoryOutcome.CREATED
        second, _, _, _ = _apply_entry(uow, "2")
        assert second.outcome is RepositoryOutcome.ACTIVE_POSITION_CONFLICT
        assert uow.commit().successful
    with paper_session_factory() as session:
        assert session.scalar(select(func.count()).select_from(PaperPositionRecord)) == 1


def test_exit_decision_and_close_fill_are_atomic_and_replay_safe(paper_session_factory):
    with PaperUnitOfWork(paper_session_factory) as uow:
        entry, command, _, position = _apply_entry(uow)
        assert entry.successful
        close_order = _open_order(uow, command, "close", role="EXIT")
        decision, exit_event = create_exit_decision(
            position,
            exit_decision_id="exit:1",
            idempotency_key=exit_decision_idempotency_key(
                position.position_id, position.version, PaperExitCause.STOP_LOSS
            ),
            expected_position_version=0,
            cause=PaperExitCause.STOP_LOSS,
            decision_price=Decimal("90"),
            source_closed_until_ms=1_120,
            decided_at=NOW,
            reason_code=PaperReasonCode.PAPER_EXIT_STOP_LOSS_TRIGGERED,
            event_id="event:exit:1",
        )
        exit_result = uow.repositories.exits.create_or_get_exit_decision(
            position.position_id, 0, decision, exit_event, exit_event
        )
        assert exit_result.outcome is RepositoryOutcome.CREATED
        close_fill = make_fill(
            fill_id="fill:close:1",
            order_id=close_order.order_id,
            idempotency_key=fill_idempotency_key(close_order.order_id, "EXIT"),
            price=Decimal("90"),
            filled_at=NOW,
            source_closed_until_ms=1_120,
        )
        order_change = fill_order(
            close_order, close_fill, expected_version=2, event_id="event:close-order"
        )
        position_change = apply_close_fill(
            replace(position, state=__import__(
                "app.engine_safety.paper_domain", fromlist=["PaperPositionState"]
            ).PaperPositionState.CLOSING, version=1, reason_code=PaperReasonCode.PAPER_POSITION_CLOSING),
            close_fill,
            expected_version=1,
            event_id="event:position-closed",
        )
        closed = uow.repositories.apply_close_fill_and_close_position(
            decision.exit_decision_id,
            position.position_id,
            1,
            close_order.order_id,
            2,
            close_fill,
            (order_change.events[0], position_change.events[0]),
            (order_change.events[0], position_change.events[0]),
        )
        assert closed.outcome is RepositoryOutcome.UPDATED
        assert closed.value.position.realized_pnl == Decimal("-22.4")
        assert uow.commit().successful
    with PaperUnitOfWork(paper_session_factory) as uow:
        replay = uow.repositories.apply_close_fill_and_close_position(
            "exit:1", "position:1", 1, "order:close", 2, close_fill, (), ()
        )
        assert replay.outcome is RepositoryOutcome.EXISTING_IDEMPOTENT
        assert replay.value.position.realized_pnl == Decimal("-22.4")
    with paper_session_factory() as session:
        assert session.scalar(select(func.count()).select_from(PaperExitDecisionRecord)) == 1
        assert session.scalar(select(func.count()).select_from(PaperFillRecord)) == 2


def test_exit_decision_replay_conflict_and_stale_version(paper_session_factory):
    with PaperUnitOfWork(paper_session_factory) as uow:
        entry, _, _, position = _apply_entry(uow)
        assert entry.successful
        decision, event = create_exit_decision(
            position,
            exit_decision_id="exit:replay",
            idempotency_key=exit_decision_idempotency_key(
                position.position_id, 0, PaperExitCause.STOP_LOSS
            ),
            expected_position_version=0,
            cause=PaperExitCause.STOP_LOSS,
            decision_price=Decimal("90"),
            source_closed_until_ms=1_120,
            decided_at=NOW,
            reason_code=PaperReasonCode.PAPER_EXIT_STOP_LOSS_TRIGGERED,
            event_id="event:exit:replay",
        )
        assert uow.repositories.exits.create_or_get_exit_decision(
            position.position_id, 0, decision, event, event
        ).outcome is RepositoryOutcome.CREATED
        assert uow.repositories.exits.create_or_get_exit_decision(
            position.position_id, 0, decision, event, event
        ).outcome is RepositoryOutcome.EXISTING_IDEMPOTENT
        assert uow.repositories.exits.create_or_get_exit_decision(
            position.position_id, 0, replace(decision, decision_price=Decimal("91")), event, event
        ).outcome is RepositoryOutcome.IDEMPOTENCY_CONFLICT
        stale = replace(
            decision,
            exit_decision_id="exit:stale",
            idempotency_key=exit_decision_idempotency_key(
                position.position_id, 0, PaperExitCause.TAKE_PROFIT
            ),
            cause=PaperExitCause.TAKE_PROFIT,
        )
        assert uow.repositories.exits.create_or_get_exit_decision(
            position.position_id, 0, stale, event, event
        ).outcome is RepositoryOutcome.STALE_VERSION


@pytest.mark.parametrize(
    "stage",
    [
        "close_after_fill",
        "close_after_order",
        "close_after_position",
        "close_after_event",
        "close_after_journal",
    ],
)
def test_close_fault_injection_rolls_back_entire_graph(paper_session_factory, stage):
    with pytest.raises(RuntimeError, match="injected"):
        with PaperUnitOfWork(paper_session_factory) as uow:
            decision, order, fill, order_event, position_event = _prepare_close(uow)
            uow.repositories.fault_injector = (
                lambda current: (_ for _ in ()).throw(RuntimeError("injected"))
                if current == stage
                else None
            )
            uow.repositories.apply_close_fill_and_close_position(
                decision.exit_decision_id,
                decision.position_id,
                1,
                order.order_id,
                2,
                fill,
                (order_event, position_event),
                (order_event, position_event),
            )
    with paper_session_factory() as session:
        assert session.scalar(select(func.count()).select_from(PaperExecutionCommandRecord)) == 0
        assert session.scalar(select(func.count()).select_from(PaperFillRecord)) == 0
        assert session.scalar(select(func.count()).select_from(PaperPositionRecord)) == 0
        assert session.scalar(select(func.count()).select_from(PaperExitDecisionRecord)) == 0


def test_concurrent_same_command_creates_one_graph(paper_session_factory):
    barrier = Barrier(2)
    command = _command("concurrent")

    def worker():
        with PaperUnitOfWork(paper_session_factory) as uow:
            barrier.wait()
            outcome = uow.repositories.commands.create_or_get_command(command).outcome
            commit = uow.commit()
            return outcome, commit.outcome

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = [future.result(timeout=20) for future in (pool.submit(worker), pool.submit(worker))]
    assert sorted(item[0].value for item in outcomes) == ["CREATED", "EXISTING_IDEMPOTENT"]
    with paper_session_factory() as session:
        assert session.scalar(select(func.count()).select_from(PaperExecutionCommandRecord)) == 1
        assert session.scalar(select(func.count()).select_from(PaperJournalEntryRecord)) == 1


def test_concurrent_order_transition_one_updates_one_conflicts(paper_session_factory):
    command = _command("race")
    with PaperUnitOfWork(paper_session_factory) as uow:
        uow.repositories.commands.create_or_get_command(command)
        order = _open_order(uow, command, "race")
        uow.commit()
    barrier = Barrier(2)

    def worker(index):
        change = transition_order(
            order,
            PaperOrderState.FAILED,
            expected_version=2,
            occurred_at=NOW,
            event_id=f"event:race:{index}",
            reason_code=PaperReasonCode.PAPER_ORDER_FAILED,
        )
        event = change.events[0]
        with PaperUnitOfWork(paper_session_factory) as uow:
            barrier.wait()
            outcome = uow.repositories.orders.transition_order(
                order.order_id,
                2,
                PaperOrderState.FAILED,
                event,
                event,
                occurred_at=NOW,
                reason_code=PaperReasonCode.PAPER_ORDER_FAILED,
            ).outcome
            uow.commit()
            return outcome

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = [future.result(timeout=20) for future in (pool.submit(worker, 1), pool.submit(worker, 2))]
    assert {item for item in outcomes} == {
        RepositoryOutcome.UPDATED,
        RepositoryOutcome.IDEMPOTENCY_CONFLICT,
    }
