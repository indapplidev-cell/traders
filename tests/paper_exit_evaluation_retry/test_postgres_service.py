from __future__ import annotations

from dataclasses import replace
from threading import Thread

import pytest
from sqlalchemy import func, select

from app.db.paper_mappings import (
    orm_values_to_paper_exit_decision,
    orm_values_to_paper_fill,
    orm_values_to_paper_order,
    orm_values_to_paper_position,
)
from app.db.paper_models import (
    PaperExitDecisionRecord,
    PaperExitEvaluationCursorRecord,
    PaperFillRecord,
    PaperJournalEntryRecord,
    PaperOrderEventRecord,
    PaperOrderRecord,
    PaperPositionRecord,
)
from app.engine_paper.exit_evaluation_service import (
    PaperExitEvaluationService,
    PaperExitServiceOutcome,
)
from app.engine_paper.fill_causal_boundary import (
    PaperFillSourceEntityType,
    resolve_paper_fill_causal_boundary,
)
from app.engine_paper.fill_roles import PaperFillRole
from app.engine_paper.repositories import PaperRepositories
from app.engine_paper.repository_results import RepositoryOutcome, result
from app.engine_paper.unit_of_work import PaperUnitOfWork
from app.engine_safety import ExecutionMode, PaperExitCause

from .conftest import T2, make_request, make_safety, seed_exit_graph


def service(exit_service_factory, paper_session_factory):
    return PaperExitEvaluationService(
        exit_service_factory, paper_session_factory
    )


def counts(factory):
    with factory() as session:
        return {
            "decisions": session.scalar(
                select(func.count()).select_from(PaperExitDecisionRecord)
            ),
            "orders": session.scalar(
                select(func.count()).select_from(PaperOrderRecord)
            ),
            "events": session.scalar(
                select(func.count()).select_from(PaperOrderEventRecord)
            ),
            "journal": session.scalar(
                select(func.count()).select_from(PaperJournalEntryRecord)
            ),
        }


@pytest.mark.parametrize(
    ("mode", "authorization", "outcome"),
    [
        (ExecutionMode.OFF, True, PaperExitServiceOutcome.MODE_OFF),
        (ExecutionMode.LIVE, True, PaperExitServiceOutcome.MODE_LIVE_FORBIDDEN),
        ("UNKNOWN", True, PaperExitServiceOutcome.MODE_UNKNOWN),
        (
            ExecutionMode.PAPER,
            False,
            PaperExitServiceOutcome.PAPER_AUTHORIZATION_MISSING,
        ),
    ],
)
def test_authorization_rejects_before_any_mutation(
    paper_session_factory,
    causal_graph,
    exit_service_factory,
    mode,
    authorization,
    outcome,
):
    cursor = seed_exit_graph(paper_session_factory, causal_graph)
    before = counts(paper_session_factory)
    request = make_request(
        causal_graph,
        cursor,
        execution_mode=mode,
        explicit_paper_authorization=authorization,
    )
    actual = service(
        exit_service_factory, paper_session_factory
    ).evaluate(request)
    assert actual.outcome is outcome
    assert counts(paper_session_factory) == before


def test_no_trigger_advances_only_cursor_once(
    paper_session_factory, causal_graph, exit_service_factory
):
    cursor = seed_exit_graph(paper_session_factory, causal_graph)
    request = make_request(causal_graph, cursor)
    subject = service(exit_service_factory, paper_session_factory)
    first = subject.evaluate(request)
    replay = subject.evaluate(request)
    assert first.outcome is PaperExitServiceOutcome.NO_EXIT_TRIGGER_CURSOR_ADVANCED
    assert replay.outcome is PaperExitServiceOutcome.CURSOR_ALREADY_ADVANCED
    assert first.cursor_boundary_ms == T2
    assert first.cursor_version == 1
    assert first.position_state.value == "OPEN"
    assert first.position_version == 0
    with paper_session_factory() as session:
        persisted = session.get(PaperExitEvaluationCursorRecord, cursor.cursor_id)
        position = session.get(PaperPositionRecord, request.position_id)
        assert persisted.version == 1
        assert persisted.last_evaluated_closed_until_ms == T2
        assert position.state == "OPEN" and position.version == 0
        assert session.scalar(select(PaperExitDecisionRecord)) is None
        assert session.scalar(
            select(func.count()).select_from(PaperOrderRecord)
        ) == 1
        assert session.scalar(
            select(func.count()).select_from(PaperJournalEntryRecord)
        ) == 0


@pytest.mark.parametrize(
    ("field", "outcome"),
    [
        ("source_command_id", PaperExitServiceOutcome.COMMAND_NOT_FOUND),
        ("entry_order_id", PaperExitServiceOutcome.ENTRY_ORDER_NOT_FOUND),
        ("entry_fill_id", PaperExitServiceOutcome.ENTRY_FILL_NOT_FOUND),
    ],
)
def test_exact_source_graph_ids_are_mandatory(
    paper_session_factory,
    causal_graph,
    exit_service_factory,
    field,
    outcome,
):
    cursor = seed_exit_graph(paper_session_factory, causal_graph)
    request = make_request(
        causal_graph,
        cursor,
        **{field: f"{field}:missing"},
    )
    actual = service(
        exit_service_factory, paper_session_factory
    ).evaluate(request)
    assert actual.outcome is outcome


@pytest.mark.parametrize(
    ("trigger", "cause"),
    [
        ("STOP", PaperExitCause.STOP_LOSS),
        ("TARGET", PaperExitCause.TAKE_PROFIT),
        ("SAFETY", PaperExitCause.SYSTEM_SAFETY_EXIT),
    ],
)
def test_trigger_prepares_complete_graph_without_fill(
    paper_session_factory,
    causal_graph,
    exit_service_factory,
    trigger,
    cause,
):
    cursor = seed_exit_graph(paper_session_factory, causal_graph)
    safety = make_safety(causal_graph) if trigger == "SAFETY" else None
    request = make_request(
        causal_graph,
        cursor,
        trigger=None if trigger == "SAFETY" else trigger,
        safety=safety,
    )
    actual = service(
        exit_service_factory, paper_session_factory
    ).evaluate(request)
    assert actual.outcome is PaperExitServiceOutcome.EXIT_PREPARED
    assert actual.trigger.cause is cause
    assert actual.cursor_boundary_ms == T2
    assert actual.position_state.value == "CLOSING"
    assert actual.close_order_state.value == "OPEN"
    assert actual.event_count == 4
    assert actual.journal_count == 4
    close_request = actual.close_execution_request
    assert close_request is not None
    assert close_request.expected_order_version == 2
    assert close_request.expected_position_version == 1
    assert close_request.candidate_candles == ()
    with paper_session_factory() as session:
        decision_row = session.get(
            PaperExitDecisionRecord, request.exit_decision_id
        )
        order_row = session.get(PaperOrderRecord, request.close_order_id)
        position_row = session.get(PaperPositionRecord, request.position_id)
        assert decision_row.source_closed_until_ms == T2
        assert order_row.order_role == "EXIT"
        assert order_row.state == "OPEN" and order_row.version == 2
        assert position_row.state == "CLOSING" and position_row.version == 1
        assert session.scalar(
            select(func.count()).select_from(PaperOrderEventRecord)
        ) == 3
        assert session.scalar(
            select(func.count()).select_from(PaperJournalEntryRecord)
        ) == 4
        assert session.scalar(
            select(func.count()).select_from(PaperFillRecord)
        ) == 1
        assert position_row.exit_fill_id is None
        assert position_row.closed_at is None


def test_exact_trigger_replay_is_zero_mutation(
    paper_session_factory, causal_graph, exit_service_factory
):
    cursor = seed_exit_graph(paper_session_factory, causal_graph)
    request = make_request(causal_graph, cursor, trigger="STOP")
    subject = service(exit_service_factory, paper_session_factory)
    first = subject.evaluate(request)
    before = counts(paper_session_factory)
    replay = subject.evaluate(request)
    assert first.outcome is PaperExitServiceOutcome.EXIT_PREPARED
    assert replay.outcome is PaperExitServiceOutcome.EXIT_ALREADY_PREPARED
    assert counts(paper_session_factory) == before


def test_conflicting_trigger_replay_is_idempotency_conflict(
    paper_session_factory, causal_graph, exit_service_factory
):
    cursor = seed_exit_graph(paper_session_factory, causal_graph)
    subject = service(exit_service_factory, paper_session_factory)
    assert subject.evaluate(
        make_request(causal_graph, cursor, trigger="STOP")
    ).successful
    conflict = make_request(
        causal_graph,
        cursor,
        trigger="TARGET",
        exit_decision_id="exit:evaluation:conflict",
    )
    actual = subject.evaluate(conflict)
    assert actual.outcome in {
        PaperExitServiceOutcome.IDEMPOTENCY_CONFLICT,
        PaperExitServiceOutcome.EXISTING_EXIT_GRAPH_INCONSISTENT,
    }


def test_partial_existing_graph_is_detected_not_repaired(
    paper_session_factory, causal_graph, exit_service_factory
):
    cursor = seed_exit_graph(paper_session_factory, causal_graph)
    request = make_request(causal_graph, cursor, trigger="STOP")
    subject = service(exit_service_factory, paper_session_factory)
    assert subject.evaluate(request).successful
    with paper_session_factory() as session:
        row = session.get(
            PaperJournalEntryRecord, request.exit_event_id
        )
        session.delete(row)
        session.commit()
    before = counts(paper_session_factory)
    actual = subject.evaluate(request)
    assert (
        actual.outcome
        is PaperExitServiceOutcome.EXISTING_EXIT_GRAPH_INCONSISTENT
    )
    assert counts(paper_session_factory) == before


def test_two_identical_trigger_requests_create_one_graph(
    paper_session_factory, causal_graph, exit_service_factory
):
    cursor = seed_exit_graph(paper_session_factory, causal_graph)
    request = make_request(causal_graph, cursor, trigger="STOP")
    outcomes = []

    def run():
        outcomes.append(
            service(
                exit_service_factory, paper_session_factory
            ).evaluate(request).outcome
        )

    threads = [Thread(target=run), Thread(target=run)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(10)
    assert sorted(value.value for value in outcomes) == [
        "EXIT_ALREADY_PREPARED",
        "EXIT_PREPARED",
    ]
    assert counts(paper_session_factory)["decisions"] == 1
    assert counts(paper_session_factory)["orders"] == 2


def test_fault_after_core_trigger_writes_rolls_back_everything(
    paper_session_factory, causal_graph
):
    cursor = seed_exit_graph(paper_session_factory, causal_graph)
    request = make_request(causal_graph, cursor, trigger="STOP")

    class FaultUow(PaperUnitOfWork):
        def __enter__(self):
            value = super().__enter__()

            def inject(stage):
                if stage == "exit_trigger_after_cursor_position_decision_order":
                    raise RuntimeError("bounded injected failure")

            value.repositories.fault_injector = inject
            return value

    subject = PaperExitEvaluationService(
        lambda: FaultUow(paper_session_factory), paper_session_factory
    )
    actual = subject.evaluate(request)
    assert actual.outcome is PaperExitServiceOutcome.INTERNAL_INVARIANT_FAILURE
    with paper_session_factory() as session:
        persisted = session.get(PaperExitEvaluationCursorRecord, cursor.cursor_id)
        position = session.get(PaperPositionRecord, request.position_id)
        assert persisted.version == 0
        assert position.state == "OPEN"
        assert session.scalar(select(PaperExitDecisionRecord)) is None
        assert session.get(PaperOrderRecord, request.close_order_id) is None


@pytest.mark.parametrize("trigger", [None, "STOP"])
def test_uncertain_commit_uses_fresh_session_and_resolves_committed(
    paper_session_factory, causal_graph, trigger
):
    cursor = seed_exit_graph(paper_session_factory, causal_graph)
    request = make_request(causal_graph, cursor, trigger=trigger)

    class CommittedButUncertainUow(PaperUnitOfWork):
        def commit(self):
            committed = super().commit()
            assert committed.outcome is RepositoryOutcome.UPDATED
            return result(RepositoryOutcome.UNCERTAIN_COMMIT_UNRESOLVED)

    actual = PaperExitEvaluationService(
        lambda: CommittedButUncertainUow(paper_session_factory),
        paper_session_factory,
    ).evaluate(request)
    assert (
        actual.outcome
        is PaperExitServiceOutcome.UNCERTAIN_COMMIT_RESOLVED_COMMITTED
    )


def test_close_causal_boundary_is_exit_decision_and_no_command_fallback(
    paper_session_factory, causal_graph, exit_service_factory
):
    cursor = seed_exit_graph(paper_session_factory, causal_graph)
    request = make_request(causal_graph, cursor, trigger="STOP")
    actual = service(
        exit_service_factory, paper_session_factory
    ).evaluate(request)
    with paper_session_factory() as session:
        repositories = PaperRepositories(session)
        command = repositories.commands.get_command(
            causal_graph["command"].command_id
        )
        close_order = repositories.orders.get_order(request.close_order_id)
        entry_order = repositories.orders.get_order(
            causal_graph["position"].entry_order_id
        )
        position = repositories.positions.get_position(request.position_id)
        decision = orm_values_to_paper_exit_decision(
            session.get(PaperExitDecisionRecord, request.exit_decision_id)
        )
        entry_fill = orm_values_to_paper_fill(
            session.get(PaperFillRecord, position.entry_fill_id)
        )
    boundary = resolve_paper_fill_causal_boundary(
        fill_role=PaperFillRole.CLOSE,
        command=command,
        order=close_order,
        simulation_policy=actual.close_execution_request.simulation_policy,
        correlation_id=request.correlation_id,
        causation_id=request.causation_id,
        exit_decision=decision,
        position=position,
        entry_order=entry_order,
        entry_fill=entry_fill,
    )
    assert boundary.successful
    assert (
        boundary.boundary.source_entity_type
        is PaperFillSourceEntityType.PAPER_EXIT_DECISION
    )
    assert boundary.boundary.source_entity_id == request.exit_decision_id
    assert boundary.boundary.source_closed_until_ms == T2
    assert boundary.boundary.source_closed_until_ms != command.closed_until_ms


def test_result_builds_close_request_but_never_executes_it(
    paper_session_factory, causal_graph, exit_service_factory
):
    cursor = seed_exit_graph(paper_session_factory, causal_graph)
    actual = service(
        exit_service_factory, paper_session_factory
    ).evaluate(make_request(causal_graph, cursor, trigger="STOP"))
    assert actual.close_execution_request is not None
    with paper_session_factory() as session:
        assert session.scalar(
            select(func.count()).select_from(PaperFillRecord)
        ) == 1
        position = session.get(
            PaperPositionRecord, causal_graph["position"].position_id
        )
        assert position.state == "CLOSING"
        assert position.realized_pnl == causal_graph["position"].realized_pnl
