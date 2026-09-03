from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal

import pytest

from app.engine_paper.fill_simulator import (
    FillSimulationOutcome,
    FillSimulationResult,
    PaperFillRole,
    SimulatedTradeAction,
    resolve_trade_action,
)
from app.engine_paper.order_execution_service import (
    MAX_CANDIDATE_CANDLES,
    PaperCloseExecutionRequest,
    PaperEntryExecutionRequest,
    PaperOrderExecutionOutcome,
    PaperOrderExecutionService,
)
from app.engine_paper.repository_results import RepositoryOutcome
from app.engine_paper.repository_results import result as repository_result
from app.engine_execution.paper_state_machine import fill_order
from app.engine_position.paper_state_machine import apply_entry_fill
from app.engine_safety import (
    ExecutionMode,
    PaperOrderState,
    PaperPositionState,
    PaperReasonCode,
    PaperSide,
)

from .conftest import FakeUow, make_candle, make_policy, make_position


def service(context, *, simulator=None):
    kwargs = {}
    if simulator is not None:
        kwargs["simulator"] = simulator
    return PaperOrderExecutionService(
        lambda: context.uow,
        lambda: (_ for _ in ()).throw(AssertionError("recovery not expected")),
        **kwargs,
    )


def test_entry_happy_path_calls_simulator_atomic_operation_and_commit_once(entry_context):
    calls = []

    def simulator(request):
        calls.append(request)
        from app.engine_paper.fill_simulator import simulate_paper_fill

        return simulate_paper_fill(request)

    outcome = service(entry_context, simulator=simulator).execute_entry(
        entry_context.request
    )
    assert outcome.outcome is PaperOrderExecutionOutcome.ENTRY_EXECUTED
    assert outcome.order_state is PaperOrderState.FILLED
    assert outcome.position_state is PaperPositionState.OPEN
    assert outcome.order_version == entry_context.order.version + 1
    assert outcome.position_version == 0
    assert outcome.fill_id == entry_context.fill.fill_id
    assert outcome.source_entity_type == "PAPER_EXECUTION_COMMAND"
    assert outcome.source_entity_id == entry_context.command.command_id
    assert (
        calls[0].causal_boundary.source_closed_until_ms
        == entry_context.command.closed_until_ms
    )
    assert len(calls) == 1
    assert entry_context.repositories.atomic_calls == 1
    assert entry_context.uow.commit_calls == 1


def test_scalping_v2_position_journal_preserves_fill_causation(entry_context):
    order_change = fill_order(
        entry_context.order,
        entry_context.fill,
        expected_version=entry_context.order.version,
        event_id="event:scalping-v2:order",
    )
    position_change = apply_entry_fill(
        None,
        entry_context.command,
        order_change.order,
        entry_context.fill,
        position_id="position:scalping-v2",
        event_id="event:scalping-v2:position",
    )
    request = replace(
        entry_context.request,
        simulation_policy=make_policy(
            simulation_policy_id="simulation:scalping-v2:foundation:v1"
        ),
    )

    order_event, position_event, journal = PaperOrderExecutionService._events(
        request, order_change.events[0], position_change.events[0]
    )

    assert order_event.causation_id == request.causation_id
    assert position_event.causation_id == entry_context.fill.fill_id
    assert journal[1].causation_id == entry_context.fill.fill_id


def test_close_happy_path_closes_once_and_uses_role_action(close_context):
    calls = []

    def simulator(request):
        calls.append(request)
        from app.engine_paper.fill_simulator import simulate_paper_fill

        return simulate_paper_fill(request)

    outcome = service(close_context, simulator=simulator).execute_close(
        close_context.request
    )
    assert outcome.outcome is PaperOrderExecutionOutcome.CLOSE_EXECUTED
    assert outcome.order_state is PaperOrderState.FILLED
    assert outcome.position_state is PaperPositionState.CLOSED
    assert outcome.position_version == close_context.position.version + 1
    assert outcome.source_entity_type == "PAPER_EXIT_DECISION"
    assert outcome.source_entity_id == close_context.decision.exit_decision_id
    assert (
        calls[0].causal_boundary.source_closed_until_ms
        == close_context.decision.source_closed_until_ms
    )
    assert outcome.selected_candle_open_ms == close_context.decision.source_closed_until_ms
    assert len(calls) == 1
    assert close_context.repositories.atomic_calls == 1
    assert close_context.uow.commit_calls == 1


@pytest.mark.parametrize(
    "side,role,action",
    [
        (PaperSide.LONG, PaperFillRole.ENTRY, SimulatedTradeAction.BUY),
        (PaperSide.LONG, PaperFillRole.CLOSE, SimulatedTradeAction.SELL),
        (PaperSide.SHORT, PaperFillRole.ENTRY, SimulatedTradeAction.SELL),
        (PaperSide.SHORT, PaperFillRole.CLOSE, SimulatedTradeAction.BUY),
    ],
)
def test_service_reuses_authoritative_long_short_role_action(side, role, action):
    assert resolve_trade_action(side, role) is action


NON_SUCCESS_SIMULATOR_OUTCOMES = tuple(
    value for value in FillSimulationOutcome if value is not FillSimulationOutcome.FILLED
)


@pytest.mark.parametrize("simulation_outcome", NON_SUCCESS_SIMULATOR_OUTCOMES)
def test_entry_every_non_success_simulator_outcome_is_zero_mutation(
    entry_context, simulation_outcome
):
    calls = []

    def simulator(_request):
        calls.append(1)
        return FillSimulationResult(
            simulation_outcome,
            None,
            f"PAPER_FILL_SIMULATOR_{simulation_outcome.value}",
            "safe",
        )

    outcome = service(entry_context, simulator=simulator).execute_entry(
        entry_context.request
    )
    assert outcome.simulation_outcome is simulation_outcome
    assert outcome.outcome.value in {
        simulation_outcome.value,
        PaperOrderExecutionOutcome.INTERNAL_INVARIANT_FAILURE.value,
    }
    assert len(calls) == 1
    assert entry_context.repositories.atomic_calls == 0
    assert entry_context.uow.commit_calls == 0
    assert entry_context.uow.rollback_calls == 1


@pytest.mark.parametrize("simulation_outcome", NON_SUCCESS_SIMULATOR_OUTCOMES)
def test_close_every_non_success_simulator_outcome_is_zero_mutation(
    close_context, simulation_outcome
):
    calls = []

    def simulator(_request):
        calls.append(1)
        return FillSimulationResult(
            simulation_outcome,
            None,
            f"PAPER_FILL_SIMULATOR_{simulation_outcome.value}",
            "safe",
        )

    outcome = service(close_context, simulator=simulator).execute_close(
        close_context.request
    )
    assert outcome.simulation_outcome is simulation_outcome
    assert outcome.outcome.value in {
        simulation_outcome.value,
        PaperOrderExecutionOutcome.INTERNAL_INVARIANT_FAILURE.value,
    }
    assert len(calls) == 1
    assert close_context.repositories.atomic_calls == 0
    assert close_context.uow.commit_calls == 0
    assert close_context.uow.rollback_calls == 1


@pytest.mark.parametrize(
    "repository_outcome,service_outcome",
    [
        (RepositoryOutcome.IDEMPOTENCY_CONFLICT, "IDEMPOTENCY_CONFLICT"),
        (RepositoryOutcome.ACTIVE_POSITION_CONFLICT, "ACTIVE_POSITION_CONFLICT"),
        (RepositoryOutcome.CONSTRAINT_VIOLATION, "CONSTRAINT_VIOLATION"),
        (RepositoryOutcome.TRANSIENT_DB_FAILURE, "TRANSIENT_DB_FAILURE"),
        (RepositoryOutcome.INVALID_STATE, "INVALID_ORDER_STATE"),
        (RepositoryOutcome.INTERNAL_INVARIANT_FAILURE, "INTERNAL_INVARIANT_FAILURE"),
    ],
)
def test_entry_repository_failures_are_stable_and_never_commit(
    entry_context, repository_outcome, service_outcome
):
    entry_context.repositories.atomic_outcome = repository_outcome
    outcome = service(entry_context).execute_entry(entry_context.request)
    assert outcome.outcome.value == service_outcome
    assert outcome.repository_outcome is repository_outcome
    assert entry_context.uow.commit_calls == 0


@pytest.mark.parametrize(
    "repository_outcome,service_outcome",
    [
        (RepositoryOutcome.IDEMPOTENCY_CONFLICT, "IDEMPOTENCY_CONFLICT"),
        (RepositoryOutcome.ACTIVE_POSITION_CONFLICT, "ACTIVE_POSITION_CONFLICT"),
        (RepositoryOutcome.CONSTRAINT_VIOLATION, "CONSTRAINT_VIOLATION"),
        (RepositoryOutcome.TRANSIENT_DB_FAILURE, "TRANSIENT_DB_FAILURE"),
        (RepositoryOutcome.INVALID_STATE, "INVALID_POSITION_STATE"),
        (RepositoryOutcome.INTERNAL_INVARIANT_FAILURE, "INTERNAL_INVARIANT_FAILURE"),
    ],
)
def test_close_repository_failures_are_stable_and_never_commit(
    close_context, repository_outcome, service_outcome
):
    close_context.repositories.atomic_outcome = repository_outcome
    outcome = service(close_context).execute_close(close_context.request)
    assert outcome.outcome.value == service_outcome
    assert outcome.repository_outcome is repository_outcome
    assert close_context.uow.commit_calls == 0


@pytest.mark.parametrize(
    "mutation,expected",
    [
        ("missing_command", "COMMAND_NOT_FOUND"),
        ("missing_order", "ORDER_NOT_FOUND"),
        ("approval", "GRAPH_INCONSISTENT"),
        ("mode", "GRAPH_INCONSISTENT"),
        ("future", "GRAPH_INCONSISTENT"),
        ("command_relation", "GRAPH_INCONSISTENT"),
        ("symbol", "GRAPH_INCONSISTENT"),
        ("side", "GRAPH_INCONSISTENT"),
        ("quantity", "GRAPH_INCONSISTENT"),
        ("role_key", "INVALID_ORDER_ROLE"),
        ("state", "INVALID_ORDER_STATE"),
        ("version", "STALE_ORDER_VERSION"),
        ("policy_simulation", "INVALID_POLICY"),
        ("policy_fee", "INVALID_POLICY"),
        ("policy_slippage", "INVALID_POLICY"),
        ("policy_latency", "INVALID_POLICY"),
        ("fill_id", "IDEMPOTENCY_CONFLICT"),
        ("active_position", "ACTIVE_POSITION_CONFLICT"),
    ],
)
def test_entry_graph_validation_matrix_is_fail_closed(entry_context, mutation, expected):
    if mutation == "missing_command":
        entry_context.repositories.command = None
    elif mutation == "missing_order":
        entry_context.repositories.order = None
    elif mutation == "approval":
        object.__setattr__(entry_context.repositories.command, "final_paper_approval", False)
    elif mutation == "mode":
        # Domain refuses LIVE construction; an authoritative graph mismatch is
        # represented by making the order reference a different command.
        entry_context.repositories.order = replace(
            entry_context.order, command_id="command:other"
        )
    elif mutation == "future":
        object.__setattr__(entry_context.repositories.command, "future_bars_used", True)
    elif mutation == "command_relation":
        entry_context.repositories.order = replace(
            entry_context.order, command_id="command:other"
        )
    elif mutation == "symbol":
        entry_context.repositories.order = replace(entry_context.order, symbol="ETHUSDT")
    elif mutation == "side":
        entry_context.repositories.order = replace(
            entry_context.order, side=PaperSide.SHORT
        )
    elif mutation == "quantity":
        entry_context.repositories.order = replace(
            entry_context.order, requested_quantity=Decimal("3")
        )
    elif mutation == "role_key":
        entry_context.repositories.order = replace(
            entry_context.order, idempotency_key="order:key:wrong"
        )
    elif mutation == "state":
        entry_context.repositories.order = replace(
            entry_context.order, state=PaperOrderState.FAILED
        )
    elif mutation == "version":
        entry_context.repositories.order = replace(entry_context.order, version=3)
    elif mutation.startswith("policy_"):
        field = mutation.removeprefix("policy_") + "_policy_id"
        entry_context.repositories.command = replace(
            entry_context.command, **{field: "policy:mismatch"}
        )
    elif mutation == "fill_id":
        entry_context.request = replace(entry_context.request, fill_id="fill:wrong")
    elif mutation == "active_position":
        entry_context.repositories.active_position = make_position(
            entry_context.command,
            entry_context.order,
            state=PaperPositionState.OPEN,
            version=0,
            reason_code=PaperReasonCode.PAPER_POSITION_OPENED,
        )
    outcome = service(entry_context).execute_entry(entry_context.request)
    assert outcome.outcome.value == expected
    assert entry_context.repositories.atomic_calls == 0
    assert entry_context.uow.commit_calls == 0


@pytest.mark.parametrize(
    "mutation,expected",
    [
        ("missing_command", "COMMAND_NOT_FOUND"),
        ("missing_order", "ORDER_NOT_FOUND"),
        ("missing_position", "POSITION_NOT_FOUND"),
        ("missing_exit", "EXIT_DECISION_NOT_FOUND"),
        ("order_state", "INVALID_ORDER_STATE"),
        ("position_state", "INVALID_POSITION_STATE"),
        ("order_version", "STALE_ORDER_VERSION"),
        ("position_version", "STALE_POSITION_VERSION"),
        ("decision_position", "GRAPH_INCONSISTENT"),
        ("decision_version", "GRAPH_INCONSISTENT"),
        ("decision_quantity", "GRAPH_INCONSISTENT"),
        ("symbol", "GRAPH_INCONSISTENT"),
        ("side", "GRAPH_INCONSISTENT"),
        ("quantity", "GRAPH_INCONSISTENT"),
        ("role_key", "INVALID_ORDER_ROLE"),
        ("fill_id", "IDEMPOTENCY_CONFLICT"),
    ],
)
def test_close_graph_validation_matrix_is_fail_closed(close_context, mutation, expected):
    if mutation == "missing_command":
        close_context.repositories.command = None
    elif mutation == "missing_order":
        close_context.repositories.order = None
    elif mutation == "missing_position":
        close_context.repositories.position = None
    elif mutation == "missing_exit":
        close_context.repositories.decision = None
    elif mutation == "order_state":
        close_context.repositories.order = replace(
            close_context.order, state=PaperOrderState.FAILED
        )
    elif mutation == "position_state":
        close_context.repositories.position = replace(
            close_context.position,
            state=PaperPositionState.OPEN,
            version=close_context.position.version,
        )
    elif mutation == "order_version":
        close_context.repositories.order = replace(close_context.order, version=3)
    elif mutation == "position_version":
        close_context.repositories.position = replace(close_context.position, version=2)
    elif mutation == "decision_position":
        close_context.repositories.decision = replace(
            close_context.decision, position_id="position:other"
        )
    elif mutation == "decision_version":
        close_context.repositories.decision = replace(
            close_context.decision, position_version=1
        )
    elif mutation == "decision_quantity":
        close_context.repositories.decision = replace(
            close_context.decision, requested_close_quantity=Decimal("1")
        )
    elif mutation == "symbol":
        close_context.repositories.order = replace(close_context.order, symbol="ETHUSDT")
    elif mutation == "side":
        close_context.repositories.order = replace(
            close_context.order, side=PaperSide.SHORT
        )
    elif mutation == "quantity":
        close_context.repositories.order = replace(
            close_context.order, requested_quantity=Decimal("1")
        )
    elif mutation == "role_key":
        close_context.repositories.order = replace(
            close_context.order, idempotency_key="order:key:wrong"
        )
    elif mutation == "fill_id":
        close_context.request = replace(close_context.request, fill_id="fill:wrong")
    outcome = service(close_context).execute_close(close_context.request)
    assert outcome.outcome.value == expected
    assert close_context.repositories.atomic_calls == 0
    assert close_context.uow.commit_calls == 0


def _entry_kwargs(request):
    return {name: getattr(request, name) for name in request.__dataclass_fields__}


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("command_id", "", ValueError),
        ("order_id", "", ValueError),
        ("fill_id", "", ValueError),
        ("position_id", "", ValueError),
        ("order_event_id", "", ValueError),
        ("position_event_id", "", ValueError),
        ("correlation_id", "", ValueError),
        ("causation_id", "", ValueError),
        ("expected_order_version", -1, ValueError),
        ("expected_order_version", True, ValueError),
        ("candidate_candles", [], TypeError),
        ("candidate_candles", (object(),), TypeError),
        (
            "candidate_candles",
            tuple(make_candle() for _ in range(MAX_CANDIDATE_CANDLES + 1)),
            ValueError,
        ),
        ("market_snapshot_closed_until_ms", -1, ValueError),
        ("market_snapshot_closed_until_ms", True, ValueError),
        ("simulation_policy", object(), TypeError),
        ("price_quantum", Decimal("0.01"), ValueError),
        ("fee_quantum", Decimal("0.01"), ValueError),
        ("quote_asset", "", ValueError),
        ("operation_at", datetime(2026, 7, 29), ValueError),
        ("journal_entry_ids", [], TypeError),
        ("journal_entry_ids", ("one",), ValueError),
        ("journal_entry_ids", ("same", "same"), ValueError),
        ("fill_role", PaperFillRole.CLOSE, ValueError),
    ],
)
def test_entry_request_shape_is_immutable_and_bounded(entry_context, field, value, error):
    values = _entry_kwargs(entry_context.request)
    values[field] = value
    with pytest.raises(error):
        PaperEntryExecutionRequest(**values)


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("position_id", "", ValueError),
        ("exit_decision_id", "", ValueError),
        ("expected_position_version", -1, ValueError),
        ("expected_position_version", True, ValueError),
        ("fill_role", PaperFillRole.ENTRY, ValueError),
        ("journal_entry_ids", ("same", "same"), ValueError),
        ("candidate_candles", [], TypeError),
        ("market_snapshot_closed_until_ms", -1, ValueError),
    ],
)
def test_close_request_shape_is_immutable_and_bounded(close_context, field, value, error):
    values = {
        name: getattr(close_context.request, name)
        for name in close_context.request.__dataclass_fields__
    }
    values[field] = value
    with pytest.raises(error):
        PaperCloseExecutionRequest(**values)


@pytest.mark.parametrize("operation", ["entry", "close"])
def test_wrong_public_request_type_is_rejected(entry_context, close_context, operation):
    target = service(entry_context if operation == "entry" else close_context)
    with pytest.raises(TypeError):
        if operation == "entry":
            target.execute_entry(close_context.request)
        else:
            target.execute_close(entry_context.request)


@pytest.mark.parametrize("operation", ["entry", "close"])
def test_simulator_invalid_return_is_sanitized_internal_failure(
    entry_context, close_context, operation
):
    context = entry_context if operation == "entry" else close_context
    target = service(context, simulator=lambda _request: object())
    outcome = (
        target.execute_entry(context.request)
        if operation == "entry"
        else target.execute_close(context.request)
    )
    assert outcome.outcome is PaperOrderExecutionOutcome.INTERNAL_INVARIANT_FAILURE
    assert "object" not in outcome.reason_code


@pytest.mark.parametrize("operation", ["entry", "close"])
def test_service_has_no_commit_on_exception(entry_context, close_context, operation):
    context = entry_context if operation == "entry" else close_context

    def boom(_request):
        raise RuntimeError("secret-bearing-driver-error")

    target = service(context, simulator=boom)
    outcome = (
        target.execute_entry(context.request)
        if operation == "entry"
        else target.execute_close(context.request)
    )
    assert outcome.outcome is PaperOrderExecutionOutcome.INTERNAL_INVARIANT_FAILURE
    assert "secret" not in outcome.reason_code
    assert context.uow.commit_calls == 0
    assert context.uow.rollback_calls == 1


@pytest.mark.parametrize("operation", ["entry", "close"])
@pytest.mark.parametrize(
    "recovery_outcome,service_outcome",
    [
        (
            RepositoryOutcome.UNCERTAIN_COMMIT_RESOLVED_COMMITTED,
            PaperOrderExecutionOutcome.UNCERTAIN_COMMIT_RESOLVED_COMMITTED,
        ),
        (
            RepositoryOutcome.UNCERTAIN_COMMIT_RESOLVED_NOT_COMMITTED,
            PaperOrderExecutionOutcome.UNCERTAIN_COMMIT_RESOLVED_NOT_COMMITTED,
        ),
        (
            RepositoryOutcome.IDEMPOTENCY_CONFLICT,
            PaperOrderExecutionOutcome.IDEMPOTENCY_CONFLICT,
        ),
        (
            RepositoryOutcome.UNCERTAIN_COMMIT_UNRESOLVED,
            PaperOrderExecutionOutcome.UNCERTAIN_COMMIT_UNRESOLVED,
        ),
    ],
)
def test_uncertain_commit_uses_bounded_recovery_without_blind_replay(
    monkeypatch,
    entry_context,
    close_context,
    operation,
    recovery_outcome,
    service_outcome,
):
    context = entry_context if operation == "entry" else close_context
    context.uow.commit_outcome = RepositoryOutcome.UNCERTAIN_COMMIT_UNRESOLVED
    calls = []

    def recovery(session_factory, lookup, expected, semantic_equal, *, attempts):
        calls.append((session_factory, lookup, expected, semantic_equal, attempts))
        value = (
            expected
            if recovery_outcome
            is RepositoryOutcome.UNCERTAIN_COMMIT_RESOLVED_COMMITTED
            else None
        )
        return repository_result(recovery_outcome, value)

    monkeypatch.setattr(
        "app.engine_paper.order_execution_service.recover_uncertain_commit",
        recovery,
    )
    target = PaperOrderExecutionService(
        lambda: context.uow,
        lambda: object(),
    )
    outcome = (
        target.execute_entry(context.request)
        if operation == "entry"
        else target.execute_close(context.request)
    )
    assert outcome.outcome is service_outcome
    assert len(calls) == 1
    assert calls[0][-1] == 3
    assert context.repositories.atomic_calls == 1
    assert context.uow.commit_calls == 1
