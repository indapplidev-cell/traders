from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from threading import Event, Thread

import pytest
from alembic import command as alembic_command
from alembic.config import Config
from sqlalchemy import inspect, select, text

from app.db.paper_mappings import (
    paper_command_to_orm_values,
    paper_fill_to_orm_values,
    paper_order_to_orm_values,
    paper_position_to_orm_values,
)
from app.db.paper_models import (
    PaperExecutionCommandRecord,
    PaperExitDecisionRecord,
    PaperExitEvaluationCursorRecord,
    PaperFillRecord,
    PaperJournalEntryRecord,
    PaperOrderRecord,
    PaperPositionRecord,
)
from app.engine_execution.paper_idempotency import order_idempotency_key
from app.engine_execution.paper_state_machine import (
    create_paper_order,
    transition_order,
)
from app.engine_exit.paper_exit import create_exit_decision
from app.engine_paper.exit_cursor_recovery import (
    PaperExitCursorRecoveryOutcome,
    recover_uncertain_cursor_commit,
)
from app.engine_paper.exit_evaluation_cursor import PaperExitCursorOutcome
from app.engine_paper.repositories import PaperRepositories
from app.engine_paper.repository_results import RepositoryOutcome
from app.engine_safety import PaperOrderState

from .conftest import T10, make_advance, make_cursor


def _unsafe_replace(value, **changes):
    clone = object.__new__(type(value))
    for field in type(value).__dataclass_fields__:
        object.__setattr__(
            clone, field, changes.get(field, getattr(value, field))
        )
    return clone


def _seed_open_position(factory, graph):
    with factory() as session:
        session.add(
            PaperExecutionCommandRecord(
                **paper_command_to_orm_values(graph["command"])
            )
        )
        session.flush()
        session.add(
            PaperOrderRecord(
                **paper_order_to_orm_values(
                    graph["filled_entry_order"], order_role="ENTRY"
                )
            )
        )
        session.flush()
        session.add(
            PaperFillRecord(
                **paper_fill_to_orm_values(graph["entry_fill"], fill_role="ENTRY")
            )
        )
        session.flush()
        session.add(
            PaperPositionRecord(
                **paper_position_to_orm_values(graph["position"])
            )
        )
        session.commit()


def test_migration_0010_0011_0010_0011_cycle(repository_postgres_engine):
    engine = repository_postgres_engine
    config = Config("alembic.ini")
    config.set_main_option(
        "sqlalchemy.url", str(engine.url).replace("%", "%%")
    )
    alembic_command.downgrade(
        config, "0010_paper_final_approval_and_order_transition_event_vocabulary"
    )
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one() == "0010_paper_final_approval_and_order_transition_event_vocabulary"
        assert "paper_exit_evaluation_cursors" not in inspect(connection).get_table_names()
    alembic_command.upgrade(
        config, "0011_paper_close_causal_boundary_and_exit_evaluation_cursor"
    )
    assert "paper_exit_evaluation_cursors" in inspect(engine).get_table_names()
    alembic_command.downgrade(
        config, "0010_paper_final_approval_and_order_transition_event_vocabulary"
    )
    assert "paper_exit_evaluation_cursors" not in inspect(engine).get_table_names()
    alembic_command.upgrade(
        config, "0011_paper_close_causal_boundary_and_exit_evaluation_cursor"
    )
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one() == "0011_paper_close_causal_boundary_and_exit_evaluation_cursor"


def test_cursor_table_has_exact_constraints_and_index(repository_postgres_engine):
    inspector = inspect(repository_postgres_engine)
    constraints = {
        value["name"]
        for value in inspector.get_check_constraints(
            "paper_exit_evaluation_cursors"
        )
    }
    assert {
        "ck_paper_exit_cursor_mode",
        "ck_paper_exit_cursor_identities",
        "ck_paper_exit_cursor_boundaries",
        "ck_paper_exit_cursor_version",
        "ck_paper_exit_cursor_timestamps",
        "ck_paper_exit_cursor_last_advance",
    } <= constraints
    assert {
        value["name"]
        for value in inspector.get_indexes("paper_exit_evaluation_cursors")
    } >= {"ix_paper_exit_evaluation_cursors_updated_at"}


def test_cursor_create_is_initialized_from_entry_fill_boundary(
    paper_session_factory, causal_graph
):
    _seed_open_position(paper_session_factory, causal_graph)
    cursor = make_cursor(causal_graph)
    with paper_session_factory() as session:
        repository = PaperRepositories(session).exit_cursors
        created = repository.create_or_get_cursor(cursor.position_id, cursor)
        session.commit()
    assert created.outcome is PaperExitCursorOutcome.CURSOR_CREATED
    assert created.cursor.last_evaluated_closed_until_ms == causal_graph["entry_fill"].source_closed_until_ms


@pytest.mark.parametrize("window_size", [1, 2, 7, 32, 64])
def test_no_trigger_advances_only_cursor_atomically(
    paper_session_factory, causal_graph, window_size
):
    _seed_open_position(paper_session_factory, causal_graph)
    cursor = make_cursor(causal_graph)
    with paper_session_factory() as session:
        repositories = PaperRepositories(session)
        assert repositories.exit_cursors.create_or_get_cursor(
            cursor.position_id, cursor
        ).successful
        session.commit()
    advance = make_advance(cursor, window_size)
    with paper_session_factory() as session:
        repositories = PaperRepositories(session)
        result = repositories.exit_cursors.advance_cursor(advance)
        session.commit()
    assert result.outcome is PaperExitCursorOutcome.CURSOR_ADVANCED
    with paper_session_factory() as session:
        position = session.get(PaperPositionRecord, cursor.position_id)
        assert position.state == "OPEN"
        assert session.scalar(select(PaperExitDecisionRecord)) is None
        assert session.scalars(select(PaperOrderRecord)).all().__len__() == 1


def test_exact_advance_replay_has_no_second_version_increment(
    paper_session_factory, causal_graph
):
    _seed_open_position(paper_session_factory, causal_graph)
    cursor = make_cursor(causal_graph)
    advance = make_advance(cursor, 3)
    with paper_session_factory() as session:
        repository = PaperRepositories(session).exit_cursors
        repository.create_or_get_cursor(cursor.position_id, cursor)
        first = repository.advance_cursor(advance)
        replay = repository.advance_cursor(advance)
        session.commit()
    assert first.outcome is PaperExitCursorOutcome.CURSOR_ADVANCED
    assert replay.outcome is PaperExitCursorOutcome.CURSOR_ALREADY_ADVANCED
    assert replay.cursor.version == 1


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("stale", PaperExitCursorOutcome.CURSOR_STALE_VERSION),
        ("regression", PaperExitCursorOutcome.CURSOR_REGRESSION_REJECTED),
        ("gap", PaperExitCursorOutcome.CURSOR_GAP_REJECTED),
        ("policy", PaperExitCursorOutcome.SOURCE_GRAPH_INCONSISTENT),
    ],
)
def test_cursor_repository_rejects_stale_regression_gap_and_policy(
    paper_session_factory, causal_graph, mutation, expected
):
    _seed_open_position(paper_session_factory, causal_graph)
    cursor = make_cursor(causal_graph)
    first = make_advance(cursor, 1)
    with paper_session_factory() as session:
        repository = PaperRepositories(session).exit_cursors
        repository.create_or_get_cursor(cursor.position_id, cursor)
        repository.advance_cursor(first)
        session.commit()
    proposed = make_advance(first_cursor := replace(
        cursor,
        last_evaluated_closed_until_ms=first.to_closed_until_ms,
        version=1,
        updated_at=first.advanced_at,
        last_advance_idempotency_key=first.idempotency_key,
        last_advance_from_closed_until_ms=first.from_closed_until_ms,
        last_advance_to_closed_until_ms=first.to_closed_until_ms,
        last_advance_expected_version=first.expected_version,
        last_window_identity=first.window_identity,
    ), 1)
    if mutation == "stale":
        proposed = _unsafe_replace(proposed, expected_version=0)
    elif mutation == "regression":
        proposed = _unsafe_replace(
            proposed,
            from_closed_until_ms=cursor.last_evaluated_closed_until_ms,
            idempotency_key="advance:other",
            window_identity="window:other",
        )
    elif mutation == "gap":
        proposed = _unsafe_replace(
            proposed,
            from_closed_until_ms=(
                first_cursor.last_evaluated_closed_until_ms + 60_000
            ),
        )
    else:
        proposed = _unsafe_replace(
            proposed, evaluation_policy_id="policy:other"
        )
    with paper_session_factory() as session:
        result = PaperRepositories(session).exit_cursors.advance_cursor(proposed)
    assert result.outcome is expected


def test_two_concurrent_advances_have_one_authoritative_winner(
    paper_session_factory, causal_graph
):
    _seed_open_position(paper_session_factory, causal_graph)
    cursor = make_cursor(causal_graph)
    advance = make_advance(cursor, 2)
    with paper_session_factory() as session:
        PaperRepositories(session).exit_cursors.create_or_get_cursor(
            cursor.position_id, cursor
        )
        session.commit()
    locked = Event()
    second_started = Event()
    release = Event()
    outcomes = []

    def first():
        with paper_session_factory() as session:
            result = PaperRepositories(session).exit_cursors.advance_cursor(advance)
            locked.set()
            release.wait(5)
            session.commit()
            outcomes.append(result.outcome)

    def second():
        locked.wait(5)
        second_started.set()
        with paper_session_factory() as session:
            result = PaperRepositories(session).exit_cursors.advance_cursor(advance)
            session.commit()
            outcomes.append(result.outcome)

    one = Thread(target=first)
    two = Thread(target=second)
    one.start()
    two.start()
    assert second_started.wait(5)
    release.set()
    one.join(5)
    two.join(5)
    assert sorted(outcome.value for outcome in outcomes) == [
        "CURSOR_ADVANCED",
        "CURSOR_ALREADY_ADVANCED",
    ]


def test_trigger_compatibility_graph_is_atomic(
    paper_session_factory, causal_graph
):
    _seed_open_position(paper_session_factory, causal_graph)
    cursor = make_cursor(causal_graph)
    advance = make_advance(cursor, 9)
    assert advance.to_closed_until_ms == T10
    decision, exit_event = create_exit_decision(
        causal_graph["position"],
        exit_decision_id=causal_graph["decision"].exit_decision_id,
        idempotency_key=causal_graph["decision"].idempotency_key,
        expected_position_version=0,
        cause=causal_graph["decision"].cause,
        decision_price=causal_graph["decision"].decision_price,
        source_closed_until_ms=T10,
        decided_at=causal_graph["decision"].decided_at,
        reason_code=causal_graph["decision"].reason_code,
        event_id="event:exit:triggered",
    )
    created = create_paper_order(
        causal_graph["command"],
        order_id="order:remediation:close",
        idempotency_key=order_idempotency_key(
            causal_graph["command"].command_id, "EXIT"
        ),
        occurred_at=decision.decided_at,
        event_id="event:close:created",
    )
    validated = transition_order(
        created.order,
        PaperOrderState.VALIDATED,
        expected_version=0,
        occurred_at=decision.decided_at,
        event_id="event:close:validated",
    )
    opened = transition_order(
        validated.order,
        PaperOrderState.OPEN,
        expected_version=1,
        occurred_at=decision.decided_at,
        event_id="event:close:opened",
    )
    with paper_session_factory() as session:
        repositories = PaperRepositories(session)
        repositories.exit_cursors.create_or_get_cursor(cursor.position_id, cursor)
        result = repositories.apply_exit_trigger_and_open_close_order(
            advance,
            decision,
            opened.order,
            exit_event,
            (created.events[0], validated.events[0], opened.events[0]),
        )
        session.commit()
    assert result.outcome is RepositoryOutcome.CREATED
    assert result.value.cursor.last_evaluated_closed_until_ms == T10
    assert result.value.position.state.value == "CLOSING"
    assert result.value.close_order.state.value == "OPEN"
    with paper_session_factory() as session:
        assert len(session.scalars(select(PaperJournalEntryRecord)).all()) == 4


def test_uncertain_commit_recovery_against_fresh_postgres_session(
    paper_session_factory, causal_graph
):
    _seed_open_position(paper_session_factory, causal_graph)
    cursor = make_cursor(causal_graph)
    advance = make_advance(cursor, 1)
    with paper_session_factory() as session:
        repository = PaperRepositories(session).exit_cursors
        repository.create_or_get_cursor(cursor.position_id, cursor)
        advanced = repository.advance_cursor(advance).cursor
        session.commit()
    recovery = recover_uncertain_cursor_commit(paper_session_factory, advanced)
    assert recovery.outcome is PaperExitCursorRecoveryOutcome.RESOLVED_COMMITTED
