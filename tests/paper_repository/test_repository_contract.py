from __future__ import annotations

import ast
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.db.paper_models import (
    PaperExecutionCommandRecord,
    PaperJournalEntryRecord,
    PaperOrderEventRecord,
    PaperOrderRecord,
)
from app.engine_execution.paper_idempotency import (
    journal_event_idempotency_key,
    order_idempotency_key,
)
from app.engine_execution.paper_state_machine import (
    create_paper_order,
    transition_order,
)
from app.engine_journal.paper_events import PaperDomainEvent
from app.engine_paper.commit_recovery import recover_uncertain_commit
from app.engine_paper.db_failures import classify_database_failure
from app.engine_paper.repositories import MAX_GRAPH_ROWS, MAX_JOURNAL_ROWS
from app.engine_paper.repository_results import RepositoryOutcome
from app.engine_paper.semantic_idempotency import (
    COMMAND_FIELDS,
    EXIT_FIELDS,
    FILL_FIELDS,
    JOURNAL_FIELDS,
    ORDER_CAUSAL_FIELDS,
    command_semantic_tuple,
    fill_semantic_tuple,
    journal_semantic_tuple,
    order_semantic_tuple,
)
from app.engine_paper.unit_of_work import PaperUnitOfWork
from app.engine_safety.paper_domain import (
    PaperEventType,
    PaperOrderState,
    PaperReasonCode,
)
from tests.paper_domain.conftest import NOW, make_command, make_fill


def _created_order(command=None, *, suffix="1"):
    command = command or make_command()
    return create_paper_order(
        command,
        order_id=f"order:{suffix}",
        idempotency_key=order_idempotency_key(command.command_id, "ENTRY"),
        occurred_at=NOW,
        event_id=f"event:order-created:{suffix}",
    )


def _event(event_id, event_type, aggregate_type, aggregate_id, version, *, cause="cause:1"):
    return PaperDomainEvent(
        event_id=event_id,
        event_type=event_type,
        occurred_at=NOW,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        correlation_id="command:1",
        causation_id=cause,
        reason_code=PaperReasonCode.PAPER_ORDER_CREATED,
        aggregate_version=version,
    )


@pytest.mark.parametrize("outcome", list(RepositoryOutcome))
def test_all_repository_outcomes_are_stable_uppercase(outcome):
    assert outcome.value == outcome.name
    assert outcome.value.isupper()


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        (COMMAND_FIELDS, 27),
        (ORDER_CAUSAL_FIELDS, 8),
        (FILL_FIELDS, 16),
        (EXIT_FIELDS, 10),
        (JOURNAL_FIELDS, 9),
    ],
)
def test_semantic_tuple_fields_are_explicit_and_unique(fields, expected):
    assert len(fields) == expected
    assert len(set(fields)) == expected
    assert "updated_at" not in fields


@pytest.mark.parametrize("field", COMMAND_FIELDS)
def test_command_semantic_tuple_covers_each_authoritative_field(field):
    command = make_command()
    assert command_semantic_tuple(command)[COMMAND_FIELDS.index(field)] == getattr(command, field)


@pytest.mark.parametrize("field", ORDER_CAUSAL_FIELDS)
def test_order_semantic_tuple_covers_each_authoritative_field(field):
    order = _created_order().order
    assert order_semantic_tuple(order)[ORDER_CAUSAL_FIELDS.index(field)] == getattr(order, field)


@pytest.mark.parametrize("field", FILL_FIELDS)
def test_fill_semantic_tuple_covers_each_authoritative_field(field):
    fill = make_fill()
    assert fill_semantic_tuple(fill)[FILL_FIELDS.index(field)] == getattr(fill, field)


@pytest.mark.parametrize("field", JOURNAL_FIELDS)
def test_journal_semantic_tuple_covers_each_authoritative_field(field):
    event = _event(
        "event:1", PaperEventType.PAPER_COMMAND_CREATED, "paper_command", "command:1", 0
    )
    assert journal_semantic_tuple(event)[JOURNAL_FIELDS.index(field)] == getattr(event, field)


def test_uow_success_persists_command_and_initial_journal(paper_session_factory):
    command = make_command()
    with PaperUnitOfWork(paper_session_factory) as uow:
        created = uow.repositories.commands.create_or_get_command(command)
        assert created.outcome is RepositoryOutcome.CREATED
        assert uow.commit().successful
    with paper_session_factory() as session:
        assert session.scalar(select(func.count()).select_from(PaperExecutionCommandRecord)) == 1
        assert session.scalar(select(func.count()).select_from(PaperJournalEntryRecord)) == 1


def test_uow_without_commit_rolls_back_everything(paper_session_factory):
    with PaperUnitOfWork(paper_session_factory) as uow:
        assert uow.repositories.commands.create_or_get_command(make_command()).successful
    with paper_session_factory() as session:
        assert session.scalar(select(func.count()).select_from(PaperExecutionCommandRecord)) == 0
        assert session.scalar(select(func.count()).select_from(PaperJournalEntryRecord)) == 0


def test_uow_exception_rolls_back_everything(paper_session_factory):
    with pytest.raises(RuntimeError, match="injected"):
        with PaperUnitOfWork(paper_session_factory) as uow:
            uow.repositories.commands.create_or_get_command(make_command())
            raise RuntimeError("injected")
    with paper_session_factory() as session:
        assert session.scalar(select(func.count()).select_from(PaperExecutionCommandRecord)) == 0


def test_uow_session_is_closed_after_exit(paper_session_factory):
    with PaperUnitOfWork(paper_session_factory) as uow:
        session = uow.session
    assert session is not None
    assert not session.in_transaction()


def test_uow_nested_reentry_fails_closed(paper_session_factory):
    uow = PaperUnitOfWork(paper_session_factory)
    with uow:
        with pytest.raises(RuntimeError, match="NESTED"):
            uow.__enter__()


def test_uow_double_commit_fails_closed(paper_session_factory):
    with PaperUnitOfWork(paper_session_factory) as uow:
        assert uow.commit().successful
        with pytest.raises(RuntimeError, match="ALREADY"):
            uow.commit()


def test_command_replay_returns_existing_without_duplicate_journal(paper_session_factory):
    command = make_command()
    with PaperUnitOfWork(paper_session_factory) as uow:
        assert uow.repositories.commands.create_or_get_command(command).outcome is RepositoryOutcome.CREATED
        assert uow.commit().successful
    with PaperUnitOfWork(paper_session_factory) as uow:
        replay = uow.repositories.commands.create_or_get_command(command)
        assert replay.outcome is RepositoryOutcome.EXISTING_IDEMPOTENT
        assert uow.commit().successful
    with paper_session_factory() as session:
        assert session.scalar(select(func.count()).select_from(PaperExecutionCommandRecord)) == 1
        assert session.scalar(select(func.count()).select_from(PaperJournalEntryRecord)) == 1


def test_command_same_key_different_payload_conflicts(paper_session_factory):
    command = make_command()
    with PaperUnitOfWork(paper_session_factory) as uow:
        uow.repositories.commands.create_or_get_command(command)
        uow.commit()
    changed = replace(
        command,
        requested_quantity=Decimal("3"),
        requested_notional=Decimal("300"),
    )
    with PaperUnitOfWork(paper_session_factory) as uow:
        conflict = uow.repositories.commands.create_or_get_command(changed)
        assert conflict.outcome is RepositoryOutcome.IDEMPOTENCY_CONFLICT


def test_command_graph_is_bounded_and_rejects_oversize_limit(paper_session_factory):
    with PaperUnitOfWork(paper_session_factory) as uow:
        uow.repositories.commands.create_or_get_command(make_command())
        uow.commit()
    with PaperUnitOfWork(paper_session_factory) as uow:
        assert uow.repositories.commands.get_command_graph(
            "command:1", limit=MAX_GRAPH_ROWS
        ).successful
        assert uow.repositories.commands.get_command_graph(
            "command:1", limit=MAX_GRAPH_ROWS + 1
        ).outcome is RepositoryOutcome.CONSTRAINT_VIOLATION


def test_order_create_is_atomic_with_event_and_journal(paper_session_factory):
    command = make_command()
    created = _created_order(command)
    with PaperUnitOfWork(paper_session_factory) as uow:
        uow.repositories.commands.create_or_get_command(command)
        outcome = uow.repositories.orders.create_or_get_order(
            command, created.order, created.events[0], created.events[0]
        )
        assert outcome.outcome is RepositoryOutcome.CREATED
        uow.commit()
    with paper_session_factory() as session:
        assert session.scalar(select(func.count()).select_from(PaperOrderRecord)) == 1
        assert session.scalar(select(func.count()).select_from(PaperOrderEventRecord)) == 1
        assert session.scalar(select(func.count()).select_from(PaperJournalEntryRecord)) == 2


def test_order_create_rollback_removes_graph(paper_session_factory):
    command = make_command()
    created = _created_order(command)
    with PaperUnitOfWork(paper_session_factory) as uow:
        uow.repositories.commands.create_or_get_command(command)
        uow.repositories.orders.create_or_get_order(
            command, created.order, created.events[0], created.events[0]
        )
    with paper_session_factory() as session:
        assert session.scalar(select(func.count()).select_from(PaperOrderRecord)) == 0
        assert session.scalar(select(func.count()).select_from(PaperOrderEventRecord)) == 0


def test_order_replay_and_conflict(paper_session_factory):
    command = make_command()
    created = _created_order(command)
    with PaperUnitOfWork(paper_session_factory) as uow:
        uow.repositories.commands.create_or_get_command(command)
        uow.repositories.orders.create_or_get_order(
            command, created.order, created.events[0], created.events[0]
        )
        uow.commit()
    with PaperUnitOfWork(paper_session_factory) as uow:
        assert uow.repositories.orders.create_or_get_order(
            command, created.order, created.events[0], created.events[0]
        ).outcome is RepositoryOutcome.EXISTING_IDEMPOTENT
        conflicting = replace(created.order, requested_quantity=Decimal("3"))
        assert uow.repositories.orders.create_or_get_order(
            command, conflicting, created.events[0], created.events[0]
        ).outcome is RepositoryOutcome.IDEMPOTENCY_CONFLICT


def test_order_transition_select_for_update_and_exact_plus_one(paper_session_factory):
    command = make_command()
    created = _created_order(command)
    with PaperUnitOfWork(paper_session_factory) as uow:
        uow.repositories.commands.create_or_get_command(command)
        uow.repositories.orders.create_or_get_order(
            command, created.order, created.events[0], created.events[0]
        )
        event = _event(
            "event:validated",
            PaperEventType.PAPER_ORDER_CREATED,
            "paper_order",
            created.order.order_id,
            1,
        )
        changed = uow.repositories.orders.transition_order(
            created.order.order_id,
            0,
            PaperOrderState.VALIDATED,
            event,
            event,
            occurred_at=NOW,
        )
        assert changed.outcome is RepositoryOutcome.UPDATED
        assert changed.value.version == 1
        uow.commit()


def test_stale_order_transition_has_no_mutation(paper_session_factory):
    command = make_command()
    created = _created_order(command)
    with PaperUnitOfWork(paper_session_factory) as uow:
        uow.repositories.commands.create_or_get_command(command)
        uow.repositories.orders.create_or_get_order(
            command, created.order, created.events[0], created.events[0]
        )
        stale = uow.repositories.orders.transition_order(
            created.order.order_id, 99, PaperOrderState.VALIDATED, None, None, occurred_at=NOW
        )
        assert stale.outcome is RepositoryOutcome.STALE_VERSION


def test_journal_listing_is_stable_bounded_and_no_delete_api(paper_session_factory):
    with PaperUnitOfWork(paper_session_factory) as uow:
        uow.repositories.commands.create_or_get_command(make_command())
        assert uow.repositories.journal.list_journal_for_aggregate(
            "paper_command", "command:1", limit=MAX_JOURNAL_ROWS + 1
        ).outcome is RepositoryOutcome.CONSTRAINT_VIOLATION
        assert not hasattr(uow.repositories.journal, "delete")
        assert not hasattr(uow.repositories.journal, "update")
        uow.commit()


def test_uncertain_commit_matching_graph_uses_fresh_lookup(paper_session_factory):
    command = make_command()
    with PaperUnitOfWork(paper_session_factory) as uow:
        uow.repositories.commands.create_or_get_command(command)
        uow.commit()
    seen = []
    recovered = recover_uncertain_commit(
        paper_session_factory,
        lambda session: (
            seen.append(session)
            or __import__("app.db.paper_mappings", fromlist=["orm_values_to_paper_command"])
            .orm_values_to_paper_command(session.get(PaperExecutionCommandRecord, command.command_id))
        ),
        command,
        lambda left, right: command_semantic_tuple(left) == command_semantic_tuple(right),
        attempts=1,
    )
    assert recovered.outcome is RepositoryOutcome.UNCERTAIN_COMMIT_RESOLVED_COMMITTED
    assert len(seen) == 1


def test_uncertain_commit_absent_conflict_and_unavailable(paper_session_factory):
    command = make_command()
    absent = recover_uncertain_commit(
        paper_session_factory, lambda session: None, command, lambda a, b: a == b, attempts=2
    )
    assert absent.outcome is RepositoryOutcome.UNCERTAIN_COMMIT_RESOLVED_NOT_COMMITTED
    conflict = recover_uncertain_commit(
        paper_session_factory,
        lambda session: replace(
            command, requested_quantity=Decimal("3"), requested_notional=Decimal("300")
        ),
        command,
        lambda a, b: command_semantic_tuple(a) == command_semantic_tuple(b),
        attempts=1,
    )
    assert conflict.outcome is RepositoryOutcome.IDEMPOTENCY_CONFLICT
    unavailable = recover_uncertain_commit(
        paper_session_factory,
        lambda session: (_ for _ in ()).throw(ConnectionError("unsafe detail")),
        command,
        lambda a, b: a == b,
        attempts=2,
    )
    assert unavailable.outcome is RepositoryOutcome.UNCERTAIN_COMMIT_UNRESOLVED
    assert "unsafe detail" not in unavailable.message


def test_repository_source_contains_locks_and_no_commit_calls():
    path = Path(__file__).parents[2] / "app/engine_paper/repositories.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = [
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]
    assert calls.count("with_for_update") >= 6
    assert "commit" not in calls
    assert ".limit(" in source


def test_migration_0009_remains_byte_identical_to_head():
    path = Path(__file__).parents[2] / "alembic/versions/0009_paper_trading_persistence_foundation.py"
    completed = __import__("subprocess").run(
        ["git", "diff", "--exit-code", "--", "alembic/versions/0009_paper_trading_persistence_foundation.py"],
        cwd=path.parents[2],
        check=False,
        capture_output=True,
    )
    assert completed.returncode == 0


class _StructuredDatabaseError(Exception):
    def __init__(self, state, constraint=None):
        self.sqlstate = state
        self.diag = type("Diagnostic", (), {"constraint_name": constraint})()


@pytest.mark.parametrize(
    ("state", "constraint", "outcome", "reason"),
    [
        ("23505", None, RepositoryOutcome.IDEMPOTENCY_CONFLICT, "UNIQUE"),
        ("23503", None, RepositoryOutcome.CONSTRAINT_VIOLATION, "FOREIGN_KEY"),
        ("23514", None, RepositoryOutcome.CONSTRAINT_VIOLATION, "CHECK"),
        ("40001", None, RepositoryOutcome.TRANSIENT_DB_FAILURE, "SERIALIZATION"),
        ("40P01", None, RepositoryOutcome.TRANSIENT_DB_FAILURE, "DEADLOCK"),
        ("57014", None, RepositoryOutcome.TRANSIENT_DB_FAILURE, "TIMEOUT"),
        (
            "23505",
            "uq_paper_positions_active_mode_symbol",
            RepositoryOutcome.ACTIVE_POSITION_CONFLICT,
            "ACTIVE_POSITION",
        ),
    ],
)
def test_database_failures_use_structured_normalization(state, constraint, outcome, reason):
    classified = classify_database_failure(_StructuredDatabaseError(state, constraint))
    assert classified.outcome is outcome
    assert reason in classified.reason_code
    assert "unsafe" not in classified.reason_code.lower()
