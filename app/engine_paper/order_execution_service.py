"""Callable application service for one atomic PAPER order execution attempt.

The service deliberately has no worker, clock, network, candle repository, or
global Session dependency.  Authoritative aggregates are loaded through one
``PaperUnitOfWork``; callers supply the immutable market/policy/identity
context needed for exactly one entry or close attempt.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Final, TypeAlias

from sqlalchemy.orm import Session

from app.engine_execution.paper_idempotency import order_idempotency_key
from app.engine_execution.paper_models import PaperExecutionCommand, PaperOrder
from app.engine_execution.paper_state_machine import fill_order
from app.engine_exit.paper_exit import PaperExitDecision
from app.engine_journal.paper_events import PaperDomainEvent
from app.engine_paper.commit_recovery import recover_uncertain_commit
from app.engine_paper.fill_policy import PaperFillSimulationPolicy
from app.engine_paper.fill_simulator import (
    FillSimulationOutcome,
    FillSimulationRequest,
    PaperFillCandle,
    PaperFillRole,
    simulate_paper_fill,
)
from app.engine_paper.repositories import (
    CloseFillGraph,
    EntryFillGraph,
    PaperCommandGraph,
    PaperRepositories,
)
from app.engine_paper.repository_results import RepositoryOutcome, RepositoryResult
from app.engine_paper.semantic_idempotency import fill_semantic_tuple
from app.engine_paper.unit_of_work import PaperUnitOfWork
from app.engine_position.paper_models import PaperPosition
from app.engine_position.paper_state_machine import apply_close_fill, apply_entry_fill
from app.engine_safety.paper_domain import (
    ExecutionMode,
    PaperDomainError,
    PaperOrderState,
    PaperOrderType,
    PaperPositionState,
    require_identity,
    require_utc,
)


MAX_CANDIDATE_CANDLES: Final = 64
_JOURNAL_EVENT_COUNT: Final = 2
_COMMAND_GRAPH_LIMIT: Final = 100


class PaperOrderExecutionOutcome(StrEnum):
    ENTRY_EXECUTED = "ENTRY_EXECUTED"
    ENTRY_ALREADY_EXECUTED = "ENTRY_ALREADY_EXECUTED"
    CLOSE_EXECUTED = "CLOSE_EXECUTED"
    CLOSE_ALREADY_EXECUTED = "CLOSE_ALREADY_EXECUTED"

    NOT_YET_ELIGIBLE = "NOT_YET_ELIGIBLE"
    ELIGIBLE_CANDLE_MISSING = "ELIGIBLE_CANDLE_MISSING"
    MARKET_DATA_GAP = "MARKET_DATA_GAP"
    DUPLICATE_CANDLE = "DUPLICATE_CANDLE"
    CANDLE_CONFLICT = "CANDLE_CONFLICT"
    COMMAND_EXPIRED = "COMMAND_EXPIRED"
    SYMBOL_MISMATCH = "SYMBOL_MISMATCH"
    TIMEFRAME_MISMATCH = "TIMEFRAME_MISMATCH"
    CANDLE_NOT_CLOSED = "CANDLE_NOT_CLOSED"
    FUTURE_DATA_REJECTED = "FUTURE_DATA_REJECTED"
    INVALID_CANDLE = "INVALID_CANDLE"
    INVALID_POLICY = "INVALID_POLICY"
    INVALID_PRECISION = "INVALID_PRECISION"
    INVALID_QUANTITY = "INVALID_QUANTITY"
    INVALID_SIMULATED_PRICE = "INVALID_SIMULATED_PRICE"
    UNSUPPORTED_PARTIAL_FILL = "UNSUPPORTED_PARTIAL_FILL"

    COMMAND_NOT_FOUND = "COMMAND_NOT_FOUND"
    ORDER_NOT_FOUND = "ORDER_NOT_FOUND"
    POSITION_NOT_FOUND = "POSITION_NOT_FOUND"
    EXIT_DECISION_NOT_FOUND = "EXIT_DECISION_NOT_FOUND"
    INVALID_ORDER_ROLE = "INVALID_ORDER_ROLE"
    INVALID_ORDER_STATE = "INVALID_ORDER_STATE"
    INVALID_POSITION_STATE = "INVALID_POSITION_STATE"
    STALE_ORDER_VERSION = "STALE_ORDER_VERSION"
    STALE_POSITION_VERSION = "STALE_POSITION_VERSION"
    GRAPH_INCONSISTENT = "GRAPH_INCONSISTENT"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    ACTIVE_POSITION_CONFLICT = "ACTIVE_POSITION_CONFLICT"
    CONSTRAINT_VIOLATION = "CONSTRAINT_VIOLATION"
    TRANSIENT_DB_FAILURE = "TRANSIENT_DB_FAILURE"
    UNCERTAIN_COMMIT_RESOLVED_COMMITTED = (
        "UNCERTAIN_COMMIT_RESOLVED_COMMITTED"
    )
    UNCERTAIN_COMMIT_RESOLVED_NOT_COMMITTED = (
        "UNCERTAIN_COMMIT_RESOLVED_NOT_COMMITTED"
    )
    UNCERTAIN_COMMIT_UNRESOLVED = "UNCERTAIN_COMMIT_UNRESOLVED"
    INTERNAL_INVARIANT_FAILURE = "INTERNAL_INVARIANT_FAILURE"


class PaperOrderExecutionReasonCode(StrEnum):
    OK = "PAPER_EXECUTION_OK"
    COMMAND_NOT_FOUND = "PAPER_EXECUTION_COMMAND_NOT_FOUND"
    ORDER_NOT_FOUND = "PAPER_EXECUTION_ORDER_NOT_FOUND"
    POSITION_NOT_FOUND = "PAPER_EXECUTION_POSITION_NOT_FOUND"
    EXIT_NOT_FOUND = "PAPER_EXECUTION_EXIT_NOT_FOUND"
    GRAPH_INCONSISTENT = "PAPER_EXECUTION_GRAPH_INCONSISTENT"
    INVALID_ROLE = "PAPER_EXECUTION_INVALID_ROLE"
    INVALID_ORDER_STATE = "PAPER_EXECUTION_INVALID_ORDER_STATE"
    INVALID_POSITION_STATE = "PAPER_EXECUTION_INVALID_POSITION_STATE"
    POLICY_MISMATCH = "PAPER_EXECUTION_POLICY_MISMATCH"
    STALE_ORDER = "PAPER_EXECUTION_STALE_ORDER"
    STALE_POSITION = "PAPER_EXECUTION_STALE_POSITION"
    ACTIVE_POSITION = "PAPER_EXECUTION_ACTIVE_POSITION_CONFLICT"
    IDEMPOTENCY_CONFLICT = "PAPER_EXECUTION_IDEMPOTENCY_CONFLICT"
    UNCERTAIN_COMMIT = "PAPER_EXECUTION_UNCERTAIN_COMMIT"
    INTERNAL_INVARIANT = "PAPER_EXECUTION_INTERNAL_INVARIANT"


def _identity(value: str, field_name: str) -> str:
    try:
        return require_identity(value, field_name)
    except PaperDomainError as exc:
        raise ValueError(f"{field_name} must be a bounded public identity") from exc


def _validate_common_request(value: "_CommonExecutionRequest") -> None:
    for name in (
        "command_id",
        "order_id",
        "fill_id",
        "order_event_id",
        "position_event_id",
        "correlation_id",
        "causation_id",
    ):
        object.__setattr__(value, name, _identity(getattr(value, name), name))
    if (
        isinstance(value.expected_order_version, bool)
        or not isinstance(value.expected_order_version, int)
        or value.expected_order_version < 0
    ):
        raise ValueError("expected_order_version must be nonnegative")
    if not isinstance(value.candidate_candles, tuple):
        raise TypeError("candidate_candles must be an immutable tuple")
    if len(value.candidate_candles) > MAX_CANDIDATE_CANDLES:
        raise ValueError("candidate_candles exceeds the bounded limit")
    if not all(isinstance(item, PaperFillCandle) for item in value.candidate_candles):
        raise TypeError("candidate_candles must contain PaperFillCandle values")
    if (
        isinstance(value.market_snapshot_closed_until_ms, bool)
        or not isinstance(value.market_snapshot_closed_until_ms, int)
        or value.market_snapshot_closed_until_ms < 0
    ):
        raise ValueError("market_snapshot_closed_until_ms must be nonnegative")
    if not isinstance(value.simulation_policy, PaperFillSimulationPolicy):
        raise TypeError("simulation_policy must be PaperFillSimulationPolicy")
    if value.price_quantum != value.simulation_policy.price_quantum:
        raise ValueError("price_quantum must match simulation_policy")
    if value.fee_quantum != value.simulation_policy.fee_quantum:
        raise ValueError("fee_quantum must match simulation_policy")
    _identity(value.quote_asset, "quote_asset")
    try:
        require_utc(value.operation_at, "operation_at")
    except PaperDomainError as exc:
        raise ValueError("operation_at must be UTC") from exc
    if not isinstance(value.journal_entry_ids, tuple):
        raise TypeError("journal_entry_ids must be an immutable tuple")
    if len(value.journal_entry_ids) != _JOURNAL_EVENT_COUNT:
        raise ValueError("exactly two journal_entry_ids are required")
    normalized = tuple(
        _identity(item, f"journal_entry_ids[{index}]")
        for index, item in enumerate(value.journal_entry_ids)
    )
    if len(set(normalized)) != len(normalized):
        raise ValueError("journal_entry_ids must be unique")
    object.__setattr__(value, "journal_entry_ids", normalized)


@dataclass(frozen=True, slots=True)
class _CommonExecutionRequest:
    command_id: str
    order_id: str
    expected_order_version: int
    fill_role: PaperFillRole
    candidate_candles: tuple[PaperFillCandle, ...]
    market_snapshot_closed_until_ms: int
    simulation_policy: PaperFillSimulationPolicy
    price_quantum: Decimal
    fee_quantum: Decimal
    quote_asset: str
    fill_id: str
    order_event_id: str
    position_event_id: str
    journal_entry_ids: tuple[str, str]
    correlation_id: str
    causation_id: str
    operation_at: datetime


@dataclass(frozen=True, slots=True)
class PaperEntryExecutionRequest(_CommonExecutionRequest):
    position_id: str

    def __post_init__(self) -> None:
        _validate_common_request(self)
        object.__setattr__(self, "position_id", _identity(self.position_id, "position_id"))
        if PaperFillRole(self.fill_role) is not PaperFillRole.ENTRY:
            raise ValueError("entry request requires ENTRY fill_role")
        object.__setattr__(self, "fill_role", PaperFillRole.ENTRY)


@dataclass(frozen=True, slots=True)
class PaperCloseExecutionRequest(_CommonExecutionRequest):
    position_id: str
    expected_position_version: int
    exit_decision_id: str

    def __post_init__(self) -> None:
        _validate_common_request(self)
        object.__setattr__(self, "position_id", _identity(self.position_id, "position_id"))
        object.__setattr__(
            self,
            "exit_decision_id",
            _identity(self.exit_decision_id, "exit_decision_id"),
        )
        if (
            isinstance(self.expected_position_version, bool)
            or not isinstance(self.expected_position_version, int)
            or self.expected_position_version < 0
        ):
            raise ValueError("expected_position_version must be nonnegative")
        if PaperFillRole(self.fill_role) is not PaperFillRole.CLOSE:
            raise ValueError("close request requires CLOSE fill_role")
        object.__setattr__(self, "fill_role", PaperFillRole.CLOSE)


@dataclass(frozen=True, slots=True)
class PaperOrderExecutionResult:
    operation: str
    outcome: PaperOrderExecutionOutcome
    reason_code: str
    command_id: str
    order_id: str
    fill_id: str | None = None
    position_id: str | None = None
    exit_decision_id: str | None = None
    order_state: PaperOrderState | None = None
    position_state: PaperPositionState | None = None
    order_version: int | None = None
    position_version: int | None = None
    simulation_outcome: FillSimulationOutcome | None = None
    repository_outcome: RepositoryOutcome | None = None
    order_version_before: int | None = None
    position_version_before: int | None = None
    source_closed_until_ms: int | None = None

    @property
    def successful(self) -> bool:
        return self.outcome in {
            PaperOrderExecutionOutcome.ENTRY_EXECUTED,
            PaperOrderExecutionOutcome.ENTRY_ALREADY_EXECUTED,
            PaperOrderExecutionOutcome.CLOSE_EXECUTED,
            PaperOrderExecutionOutcome.CLOSE_ALREADY_EXECUTED,
            PaperOrderExecutionOutcome.UNCERTAIN_COMMIT_RESOLVED_COMMITTED,
        }


ExecutionRequest: TypeAlias = PaperEntryExecutionRequest | PaperCloseExecutionRequest
UowFactory: TypeAlias = Callable[[], PaperUnitOfWork]
SessionFactory: TypeAlias = Callable[[], Session]
Simulator: TypeAlias = Callable[[FillSimulationRequest], object]


_SIMULATION_OUTCOME_MAP: Final = {
    value: PaperOrderExecutionOutcome(value.value)
    for value in FillSimulationOutcome
    if value.value in PaperOrderExecutionOutcome._value2member_map_
}

_REPOSITORY_OUTCOME_MAP: Final = {
    RepositoryOutcome.IDEMPOTENCY_CONFLICT: PaperOrderExecutionOutcome.IDEMPOTENCY_CONFLICT,
    RepositoryOutcome.ACTIVE_POSITION_CONFLICT: PaperOrderExecutionOutcome.ACTIVE_POSITION_CONFLICT,
    RepositoryOutcome.CONSTRAINT_VIOLATION: PaperOrderExecutionOutcome.CONSTRAINT_VIOLATION,
    RepositoryOutcome.TRANSIENT_DB_FAILURE: PaperOrderExecutionOutcome.TRANSIENT_DB_FAILURE,
    RepositoryOutcome.UNCERTAIN_COMMIT_RESOLVED_COMMITTED: (
        PaperOrderExecutionOutcome.UNCERTAIN_COMMIT_RESOLVED_COMMITTED
    ),
    RepositoryOutcome.UNCERTAIN_COMMIT_RESOLVED_NOT_COMMITTED: (
        PaperOrderExecutionOutcome.UNCERTAIN_COMMIT_RESOLVED_NOT_COMMITTED
    ),
    RepositoryOutcome.UNCERTAIN_COMMIT_UNRESOLVED: (
        PaperOrderExecutionOutcome.UNCERTAIN_COMMIT_UNRESOLVED
    ),
    RepositoryOutcome.INTERNAL_INVARIANT_FAILURE: (
        PaperOrderExecutionOutcome.INTERNAL_INVARIANT_FAILURE
    ),
}


class PaperOrderExecutionService:
    """Execute exactly one caller-supplied PAPER entry or close request."""

    def __init__(
        self,
        uow_factory: UowFactory,
        recovery_session_factory: SessionFactory,
        *,
        simulator: Callable[[FillSimulationRequest], object] = simulate_paper_fill,
    ) -> None:
        self._uow_factory = uow_factory
        self._recovery_session_factory = recovery_session_factory
        self._simulator = simulator

    def execute_entry(
        self, request: PaperEntryExecutionRequest
    ) -> PaperOrderExecutionResult:
        if not isinstance(request, PaperEntryExecutionRequest):
            raise TypeError("request must be PaperEntryExecutionRequest")
        return self._execute_entry(request)

    def execute_close(
        self, request: PaperCloseExecutionRequest
    ) -> PaperOrderExecutionResult:
        if not isinstance(request, PaperCloseExecutionRequest):
            raise TypeError("request must be PaperCloseExecutionRequest")
        return self._execute_close(request)

    def _execute_entry(
        self, request: PaperEntryExecutionRequest
    ) -> PaperOrderExecutionResult:
        operation = "ENTRY"
        try:
            with self._uow_factory() as uow:
                repositories = self._repositories(uow)
                command = repositories.commands.get_command(request.command_id)
                if command is None:
                    return self._failure(
                        request,
                        operation,
                        PaperOrderExecutionOutcome.COMMAND_NOT_FOUND,
                        PaperOrderExecutionReasonCode.COMMAND_NOT_FOUND,
                    )
                order = repositories.orders.get_order(request.order_id)
                if order is None:
                    return self._failure(
                        request,
                        operation,
                        PaperOrderExecutionOutcome.ORDER_NOT_FOUND,
                        PaperOrderExecutionReasonCode.ORDER_NOT_FOUND,
                    )
                graph_failure = self._validate_entry_graph(request, command, order)
                if graph_failure is not None:
                    return graph_failure

                replay = order.state is PaperOrderState.FILLED
                simulation_order = self._simulation_order(
                    order, request.expected_order_version
                )
                if simulation_order is None:
                    return self._failure(
                        request,
                        operation,
                        PaperOrderExecutionOutcome.INVALID_ORDER_STATE,
                        PaperOrderExecutionReasonCode.INVALID_ORDER_STATE,
                        order=order,
                    )
                simulation = self._simulate(request, command, simulation_order)
                if not simulation.successful:
                    return self._simulation_failure(
                        request, operation, order, None, simulation
                    )
                assert simulation.fill is not None
                if simulation.fill.fill_id != request.fill_id:
                    return self._failure(
                        request,
                        operation,
                        PaperOrderExecutionOutcome.IDEMPOTENCY_CONFLICT,
                        PaperOrderExecutionReasonCode.IDEMPOTENCY_CONFLICT,
                        order=order,
                        simulation_outcome=simulation.outcome,
                    )
                if request.operation_at < simulation.fill.filled_at:
                    return self._failure(
                        request,
                        operation,
                        PaperOrderExecutionOutcome.GRAPH_INCONSISTENT,
                        PaperOrderExecutionReasonCode.GRAPH_INCONSISTENT,
                        order=order,
                        simulation_outcome=simulation.outcome,
                    )
                if replay:
                    graph_result = repositories.commands.get_command_graph(
                        request.command_id, limit=_COMMAND_GRAPH_LIMIT
                    )
                    existing = self._existing_entry_graph(
                        graph_result.value, request, simulation.fill
                    )
                    if existing is None:
                        return self._failure(
                            request,
                            operation,
                            PaperOrderExecutionOutcome.IDEMPOTENCY_CONFLICT,
                            PaperOrderExecutionReasonCode.IDEMPOTENCY_CONFLICT,
                            order=order,
                            simulation_outcome=simulation.outcome,
                        )
                    return self._success(
                        request,
                        operation,
                        PaperOrderExecutionOutcome.ENTRY_ALREADY_EXECUTED,
                        RepositoryResult(
                            RepositoryOutcome.EXISTING_IDEMPOTENT,
                            existing,
                            "PAPER_REPOSITORY_EXISTING_IDEMPOTENT",
                            "existing entry execution graph",
                        ),
                        simulation.outcome,
                        request.expected_order_version,
                        None,
                    )

                order_change = fill_order(
                    simulation_order,
                    simulation.fill,
                    expected_version=request.expected_order_version,
                    event_id=request.order_event_id,
                )
                position_change = apply_entry_fill(
                    None,
                    command,
                    order_change.order,
                    simulation.fill,
                    position_id=request.position_id,
                    event_id=request.position_event_id,
                )
                order_event, position_event, journal = self._events(
                    request,
                    order_change.events[0],
                    position_change.events[0],
                )
                if not replay:
                    active = repositories.positions.get_active_position(
                        ExecutionMode.PAPER, command.symbol
                    )
                    if active is not None and not (
                        active.position_id == request.position_id
                        and active.entry_fill_id == simulation.fill.fill_id
                    ):
                        return self._failure(
                            request,
                            operation,
                            PaperOrderExecutionOutcome.ACTIVE_POSITION_CONFLICT,
                            PaperOrderExecutionReasonCode.ACTIVE_POSITION,
                            order=order,
                            position=active,
                            simulation_outcome=simulation.outcome,
                        )

                repository_result = repositories.apply_entry_fill_and_open_position(
                    request.order_id,
                    request.expected_order_version,
                    simulation.fill,
                    position_change.position,
                    order_event,
                    position_event,
                    journal,
                )
                if repository_result.outcome is RepositoryOutcome.EXISTING_IDEMPOTENT:
                    return self._success(
                        request,
                        operation,
                        PaperOrderExecutionOutcome.ENTRY_ALREADY_EXECUTED,
                        repository_result,
                        simulation.outcome,
                        order.version,
                        None,
                    )
                if repository_result.outcome is not RepositoryOutcome.CREATED:
                    return self._repository_failure(
                        request,
                        operation,
                        repository_result,
                        order,
                        None,
                        simulation.outcome,
                    )
                commit = uow.commit()
                if commit.outcome is RepositoryOutcome.UPDATED:
                    return self._success(
                        request,
                        operation,
                        PaperOrderExecutionOutcome.ENTRY_EXECUTED,
                        repository_result,
                        simulation.outcome,
                        order.version,
                        None,
                    )
                return self._after_commit_failure(
                    request,
                    operation,
                    commit,
                    repository_result.value,
                    simulation.outcome,
                    order.version,
                    None,
                )
        except (PaperDomainError, ValueError):
            return self._failure(
                request,
                operation,
                PaperOrderExecutionOutcome.GRAPH_INCONSISTENT,
                PaperOrderExecutionReasonCode.GRAPH_INCONSISTENT,
            )
        except Exception:
            return self._failure(
                request,
                operation,
                PaperOrderExecutionOutcome.INTERNAL_INVARIANT_FAILURE,
                PaperOrderExecutionReasonCode.INTERNAL_INVARIANT,
            )

    def _execute_close(
        self, request: PaperCloseExecutionRequest
    ) -> PaperOrderExecutionResult:
        operation = "CLOSE"
        try:
            with self._uow_factory() as uow:
                repositories = self._repositories(uow)
                command = repositories.commands.get_command(request.command_id)
                if command is None:
                    return self._failure(
                        request,
                        operation,
                        PaperOrderExecutionOutcome.COMMAND_NOT_FOUND,
                        PaperOrderExecutionReasonCode.COMMAND_NOT_FOUND,
                    )
                order = repositories.orders.get_order(request.order_id)
                if order is None:
                    return self._failure(
                        request,
                        operation,
                        PaperOrderExecutionOutcome.ORDER_NOT_FOUND,
                        PaperOrderExecutionReasonCode.ORDER_NOT_FOUND,
                    )
                position = repositories.positions.get_position(request.position_id)
                if position is None:
                    return self._failure(
                        request,
                        operation,
                        PaperOrderExecutionOutcome.POSITION_NOT_FOUND,
                        PaperOrderExecutionReasonCode.POSITION_NOT_FOUND,
                        order=order,
                    )
                graph_result = repositories.commands.get_command_graph(
                    request.command_id, limit=_COMMAND_GRAPH_LIMIT
                )
                graph = graph_result.value
                decision = self._find_exit_decision(graph, request.exit_decision_id)
                if decision is None:
                    return self._failure(
                        request,
                        operation,
                        PaperOrderExecutionOutcome.EXIT_DECISION_NOT_FOUND,
                        PaperOrderExecutionReasonCode.EXIT_NOT_FOUND,
                        order=order,
                        position=position,
                    )
                graph_failure = self._validate_close_graph(
                    request, command, order, position, decision
                )
                if graph_failure is not None:
                    return graph_failure

                replay = (
                    order.state is PaperOrderState.FILLED
                    and position.state is PaperPositionState.CLOSED
                )
                simulation_order = self._simulation_order(
                    order, request.expected_order_version
                )
                simulation_position = self._simulation_position(
                    position, request.expected_position_version
                )
                if simulation_order is None:
                    return self._failure(
                        request,
                        operation,
                        PaperOrderExecutionOutcome.INVALID_ORDER_STATE,
                        PaperOrderExecutionReasonCode.INVALID_ORDER_STATE,
                        order=order,
                        position=position,
                    )
                if simulation_position is None:
                    return self._failure(
                        request,
                        operation,
                        PaperOrderExecutionOutcome.INVALID_POSITION_STATE,
                        PaperOrderExecutionReasonCode.INVALID_POSITION_STATE,
                        order=order,
                        position=position,
                    )
                simulation = self._simulate(request, command, simulation_order)
                if not simulation.successful:
                    return self._simulation_failure(
                        request, operation, order, position, simulation
                    )
                assert simulation.fill is not None
                if simulation.fill.fill_id != request.fill_id:
                    return self._failure(
                        request,
                        operation,
                        PaperOrderExecutionOutcome.IDEMPOTENCY_CONFLICT,
                        PaperOrderExecutionReasonCode.IDEMPOTENCY_CONFLICT,
                        order=order,
                        position=position,
                        simulation_outcome=simulation.outcome,
                    )
                if request.operation_at < simulation.fill.filled_at:
                    return self._failure(
                        request,
                        operation,
                        PaperOrderExecutionOutcome.GRAPH_INCONSISTENT,
                        PaperOrderExecutionReasonCode.GRAPH_INCONSISTENT,
                        order=order,
                        position=position,
                        simulation_outcome=simulation.outcome,
                    )
                if replay:
                    existing = self._existing_close_graph(
                        graph, request, simulation.fill
                    )
                    if existing is None:
                        return self._failure(
                            request,
                            operation,
                            PaperOrderExecutionOutcome.IDEMPOTENCY_CONFLICT,
                            PaperOrderExecutionReasonCode.IDEMPOTENCY_CONFLICT,
                            order=order,
                            position=position,
                            simulation_outcome=simulation.outcome,
                        )
                    return self._success(
                        request,
                        operation,
                        PaperOrderExecutionOutcome.CLOSE_ALREADY_EXECUTED,
                        RepositoryResult(
                            RepositoryOutcome.EXISTING_IDEMPOTENT,
                            existing,
                            "PAPER_REPOSITORY_EXISTING_IDEMPOTENT",
                            "existing close execution graph",
                        ),
                        simulation.outcome,
                        request.expected_order_version,
                        request.expected_position_version,
                    )
                order_change = fill_order(
                    simulation_order,
                    simulation.fill,
                    expected_version=request.expected_order_version,
                    event_id=request.order_event_id,
                )
                position_change = apply_close_fill(
                    simulation_position,
                    simulation.fill,
                    expected_version=request.expected_position_version,
                    event_id=request.position_event_id,
                )
                order_event, position_event, journal = self._events(
                    request,
                    order_change.events[0],
                    position_change.events[0],
                )
                repository_result = repositories.apply_close_fill_and_close_position(
                    request.exit_decision_id,
                    request.position_id,
                    request.expected_position_version,
                    request.order_id,
                    request.expected_order_version,
                    simulation.fill,
                    (order_event, position_event),
                    journal,
                )
                if repository_result.outcome is RepositoryOutcome.EXISTING_IDEMPOTENT:
                    return self._success(
                        request,
                        operation,
                        PaperOrderExecutionOutcome.CLOSE_ALREADY_EXECUTED,
                        repository_result,
                        simulation.outcome,
                        order.version,
                        position.version,
                    )
                if repository_result.outcome is not RepositoryOutcome.UPDATED:
                    current_order = repositories.orders.get_order(request.order_id)
                    current_position = repositories.positions.get_position(
                        request.position_id
                    )
                    return self._repository_failure(
                        request,
                        operation,
                        repository_result,
                        current_order or order,
                        current_position or position,
                        simulation.outcome,
                    )
                commit = uow.commit()
                if commit.outcome is RepositoryOutcome.UPDATED:
                    return self._success(
                        request,
                        operation,
                        PaperOrderExecutionOutcome.CLOSE_EXECUTED,
                        repository_result,
                        simulation.outcome,
                        order.version,
                        position.version,
                    )
                return self._after_commit_failure(
                    request,
                    operation,
                    commit,
                    repository_result.value,
                    simulation.outcome,
                    order.version,
                    position.version,
                )
        except (PaperDomainError, ValueError):
            return self._failure(
                request,
                operation,
                PaperOrderExecutionOutcome.GRAPH_INCONSISTENT,
                PaperOrderExecutionReasonCode.GRAPH_INCONSISTENT,
            )
        except Exception:
            return self._failure(
                request,
                operation,
                PaperOrderExecutionOutcome.INTERNAL_INVARIANT_FAILURE,
                PaperOrderExecutionReasonCode.INTERNAL_INVARIANT,
            )

    @staticmethod
    def _repositories(uow: PaperUnitOfWork):
        if uow.repositories is None:
            raise RuntimeError("PAPER_EXECUTION_UOW_REPOSITORIES_UNAVAILABLE")
        return uow.repositories

    def _simulate(
        self,
        request: ExecutionRequest,
        command: PaperExecutionCommand,
        order: PaperOrder,
    ):
        simulation_request = FillSimulationRequest(
            command=command,
            order=order,
            fill_role=request.fill_role,
            quote_asset=request.quote_asset,
            simulation_policy=request.simulation_policy,
            candidate_candles=request.candidate_candles,
            market_snapshot_closed_until_ms=request.market_snapshot_closed_until_ms,
            correlation_id=request.correlation_id,
            causation_id=request.causation_id,
        )
        result = self._simulator(simulation_request)
        if not hasattr(result, "successful") or not hasattr(result, "outcome"):
            raise TypeError("simulator returned an invalid result")
        return result

    def _validate_entry_graph(
        self,
        request: PaperEntryExecutionRequest,
        command: PaperExecutionCommand,
        order: PaperOrder,
    ) -> PaperOrderExecutionResult | None:
        common = self._validate_common_graph(request, command, order, "ENTRY")
        if common is not None:
            return common
        if order.state is PaperOrderState.OPEN:
            if order.version != request.expected_order_version:
                return self._failure(
                    request,
                    "ENTRY",
                    PaperOrderExecutionOutcome.STALE_ORDER_VERSION,
                    PaperOrderExecutionReasonCode.STALE_ORDER,
                    order=order,
                )
        elif not (
            order.state is PaperOrderState.FILLED
            and order.version == request.expected_order_version + 1
            and order.applied_fill_id == request.fill_id
        ):
            return self._failure(
                request,
                "ENTRY",
                PaperOrderExecutionOutcome.INVALID_ORDER_STATE,
                PaperOrderExecutionReasonCode.INVALID_ORDER_STATE,
                order=order,
            )
        return None

    def _validate_close_graph(
        self,
        request: PaperCloseExecutionRequest,
        command: PaperExecutionCommand,
        order: PaperOrder,
        position: PaperPosition,
        decision: PaperExitDecision,
    ) -> PaperOrderExecutionResult | None:
        common = self._validate_common_graph(request, command, order, "EXIT")
        if common is not None:
            return common
        if order.state is PaperOrderState.OPEN:
            if order.version != request.expected_order_version:
                return self._failure(
                    request,
                    "CLOSE",
                    PaperOrderExecutionOutcome.STALE_ORDER_VERSION,
                    PaperOrderExecutionReasonCode.STALE_ORDER,
                    order=order,
                    position=position,
                )
        elif not (
            order.state is PaperOrderState.FILLED
            and order.version == request.expected_order_version + 1
            and order.applied_fill_id == request.fill_id
        ):
            return self._failure(
                request,
                "CLOSE",
                PaperOrderExecutionOutcome.INVALID_ORDER_STATE,
                PaperOrderExecutionReasonCode.INVALID_ORDER_STATE,
                order=order,
                position=position,
            )
        if position.state is PaperPositionState.CLOSING:
            if position.version != request.expected_position_version:
                return self._failure(
                    request,
                    "CLOSE",
                    PaperOrderExecutionOutcome.STALE_POSITION_VERSION,
                    PaperOrderExecutionReasonCode.STALE_POSITION,
                    order=order,
                    position=position,
                )
        elif not (
            position.state is PaperPositionState.CLOSED
            and position.version == request.expected_position_version + 1
            and position.exit_fill_id == request.fill_id
        ):
            return self._failure(
                request,
                "CLOSE",
                PaperOrderExecutionOutcome.INVALID_POSITION_STATE,
                PaperOrderExecutionReasonCode.INVALID_POSITION_STATE,
                order=order,
                position=position,
            )
        if (
            decision.position_id != position.position_id
            or decision.position_version + 1 != request.expected_position_version
            or decision.requested_close_quantity != position.entry_quantity
            or (
                position.state is not PaperPositionState.CLOSED
                and decision.requested_close_quantity != position.remaining_quantity
            )
            or order.symbol != position.symbol
            or order.side is not position.side
            or order.requested_quantity
            != (
                position.entry_quantity
                if position.state is PaperPositionState.CLOSED
                else position.remaining_quantity
            )
        ):
            return self._failure(
                request,
                "CLOSE",
                PaperOrderExecutionOutcome.GRAPH_INCONSISTENT,
                PaperOrderExecutionReasonCode.GRAPH_INCONSISTENT,
                order=order,
                position=position,
            )
        return None

    def _validate_common_graph(
        self,
        request: ExecutionRequest,
        command: PaperExecutionCommand,
        order: PaperOrder,
        persistence_role: str,
    ) -> PaperOrderExecutionResult | None:
        operation = "ENTRY" if persistence_role == "ENTRY" else "CLOSE"
        expected_key = order_idempotency_key(command.command_id, persistence_role)
        if order.idempotency_key != expected_key:
            return self._failure(
                request,
                operation,
                PaperOrderExecutionOutcome.INVALID_ORDER_ROLE,
                PaperOrderExecutionReasonCode.INVALID_ROLE,
                order=order,
            )
        if (
            command.mode is not ExecutionMode.PAPER
            or command.final_paper_approval is not True
            or command.future_bars_used is not False
            or order.command_id != command.command_id
            or order.symbol != command.symbol
            or order.side is not command.side
            or order.order_type is not PaperOrderType.MARKET_SIMULATED
            or order.requested_quantity != command.requested_quantity
        ):
            return self._failure(
                request,
                operation,
                PaperOrderExecutionOutcome.GRAPH_INCONSISTENT,
                PaperOrderExecutionReasonCode.GRAPH_INCONSISTENT,
                order=order,
            )
        policy = request.simulation_policy
        if (
            policy.simulation_policy_id != command.simulation_policy_id
            or policy.fee_policy_id != command.fee_policy_id
            or policy.slippage_policy_id != command.slippage_policy_id
            or policy.latency_policy_id != command.latency_policy_id
            or request.price_quantum != policy.price_quantum
            or request.fee_quantum != policy.fee_quantum
        ):
            return self._failure(
                request,
                operation,
                PaperOrderExecutionOutcome.INVALID_POLICY,
                PaperOrderExecutionReasonCode.POLICY_MISMATCH,
                order=order,
            )
        return None

    @staticmethod
    def _simulation_order(
        order: PaperOrder, expected_version: int
    ) -> PaperOrder | None:
        if order.state is PaperOrderState.OPEN:
            return order
        if (
            order.state is PaperOrderState.FILLED
            and order.version == expected_version + 1
        ):
            return replace(
                order,
                state=PaperOrderState.OPEN,
                filled_quantity=Decimal("0"),
                average_fill_price=None,
                total_fees=Decimal("0"),
                version=expected_version,
                applied_fill_id=None,
            )
        return None

    @staticmethod
    def _simulation_position(
        position: PaperPosition, expected_version: int
    ) -> PaperPosition | None:
        if position.state is PaperPositionState.CLOSING:
            return position
        if (
            position.state is PaperPositionState.CLOSED
            and position.version == expected_version + 1
        ):
            return replace(
                position,
                state=PaperPositionState.CLOSING,
                remaining_quantity=position.entry_quantity,
                average_exit_price=None,
                exit_fees=Decimal("0"),
                realized_pnl=-position.entry_fees,
                unrealized_pnl=Decimal("0"),
                closed_at=None,
                last_mark_price=position.average_entry_price,
                version=expected_version,
                exit_fill_id=None,
            )
        return None

    @staticmethod
    def _events(
        request: ExecutionRequest,
        order_event: PaperDomainEvent,
        position_event: PaperDomainEvent,
    ) -> tuple[PaperDomainEvent, PaperDomainEvent, tuple[PaperDomainEvent, ...]]:
        order_persisted = replace(
            order_event,
            event_id=request.order_event_id,
            occurred_at=request.operation_at,
            correlation_id=request.correlation_id,
            causation_id=request.causation_id,
        )
        position_persisted = replace(
            position_event,
            event_id=request.position_event_id,
            occurred_at=request.operation_at,
            correlation_id=request.correlation_id,
            causation_id=request.causation_id,
        )
        journal = (
            replace(order_persisted, event_id=request.journal_entry_ids[0]),
            replace(position_persisted, event_id=request.journal_entry_ids[1]),
        )
        return order_persisted, position_persisted, journal

    @staticmethod
    def _find_exit_decision(
        graph: PaperCommandGraph | None, exit_decision_id: str
    ) -> PaperExitDecision | None:
        if graph is None:
            return None
        return next(
            (
                item
                for item in graph.exit_decisions
                if item.exit_decision_id == exit_decision_id
            ),
            None,
        )

    @staticmethod
    def _existing_entry_graph(
        graph: PaperCommandGraph | None,
        request: PaperEntryExecutionRequest,
        expected_fill,
    ) -> EntryFillGraph | None:
        if graph is None:
            return None
        order = next(
            (item for item in graph.orders if item.order_id == request.order_id),
            None,
        )
        fill = next(
            (item for item in graph.fills if item.fill_id == request.fill_id),
            None,
        )
        position = next(
            (
                item
                for item in graph.positions
                if item.position_id == request.position_id
                and item.entry_fill_id == request.fill_id
            ),
            None,
        )
        if (
            order is None
            or fill is None
            or position is None
            or order.state is not PaperOrderState.FILLED
            or order.applied_fill_id != fill.fill_id
            or fill_semantic_tuple(fill) != fill_semantic_tuple(expected_fill)
        ):
            return None
        return EntryFillGraph(order, fill, position)

    @staticmethod
    def _existing_close_graph(
        graph: PaperCommandGraph | None,
        request: PaperCloseExecutionRequest,
        expected_fill,
    ) -> CloseFillGraph | None:
        if graph is None:
            return None
        order = next(
            (item for item in graph.orders if item.order_id == request.order_id),
            None,
        )
        fill = next(
            (item for item in graph.fills if item.fill_id == request.fill_id),
            None,
        )
        position = next(
            (
                item
                for item in graph.positions
                if item.position_id == request.position_id
                and item.exit_fill_id == request.fill_id
            ),
            None,
        )
        if (
            order is None
            or fill is None
            or position is None
            or order.state is not PaperOrderState.FILLED
            or position.state is not PaperPositionState.CLOSED
            or order.applied_fill_id != fill.fill_id
            or fill_semantic_tuple(fill) != fill_semantic_tuple(expected_fill)
        ):
            return None
        return CloseFillGraph(order, fill, position)

    def _after_commit_failure(
        self,
        request: ExecutionRequest,
        operation: str,
        commit: RepositoryResult[None],
        expected_graph: EntryFillGraph | CloseFillGraph | None,
        simulation_outcome: FillSimulationOutcome,
        order_version_before: int,
        position_version_before: int | None,
    ) -> PaperOrderExecutionResult:
        if (
            commit.outcome is not RepositoryOutcome.UNCERTAIN_COMMIT_UNRESOLVED
            or expected_graph is None
        ):
            return self._failure(
                request,
                operation,
                _REPOSITORY_OUTCOME_MAP.get(
                    commit.outcome,
                    PaperOrderExecutionOutcome.INTERNAL_INVARIANT_FAILURE,
                ),
                commit.reason_code,
                simulation_outcome=simulation_outcome,
                repository_outcome=commit.outcome,
            )
        recovery = recover_uncertain_commit(
            self._recovery_session_factory,
            lambda session: self._lookup_graph(session, request, operation),
            expected_graph,
            self._same_execution_graph,
            attempts=3,
        )
        if recovery.outcome is RepositoryOutcome.UNCERTAIN_COMMIT_RESOLVED_COMMITTED:
            return self._success(
                request,
                operation,
                PaperOrderExecutionOutcome.UNCERTAIN_COMMIT_RESOLVED_COMMITTED,
                recovery,
                simulation_outcome,
                order_version_before,
                position_version_before,
            )
        return self._failure(
            request,
            operation,
            _REPOSITORY_OUTCOME_MAP.get(
                recovery.outcome,
                PaperOrderExecutionOutcome.INTERNAL_INVARIANT_FAILURE,
            ),
            recovery.reason_code,
            simulation_outcome=simulation_outcome,
            repository_outcome=recovery.outcome,
        )

    @staticmethod
    def _lookup_graph(
        session: Session,
        request: ExecutionRequest,
        operation: str,
    ) -> EntryFillGraph | CloseFillGraph | None:
        repositories = PaperRepositories(session)
        graph_result = repositories.commands.get_command_graph(
            request.command_id, limit=_COMMAND_GRAPH_LIMIT
        )
        graph = graph_result.value
        if graph is None:
            return None
        order = next((item for item in graph.orders if item.order_id == request.order_id), None)
        fill = next((item for item in graph.fills if item.fill_id == request.fill_id), None)
        position = next(
            (item for item in graph.positions if item.position_id == request.position_id),
            None,
        )
        if order is None or fill is None or position is None:
            return None
        if operation == "ENTRY":
            return EntryFillGraph(order, fill, position)
        return CloseFillGraph(order, fill, position)

    @staticmethod
    def _same_execution_graph(
        found: EntryFillGraph | CloseFillGraph,
        expected: EntryFillGraph | CloseFillGraph,
    ) -> bool:
        return (
            type(found) is type(expected)
            and found.order == expected.order
            and fill_semantic_tuple(found.fill) == fill_semantic_tuple(expected.fill)
            and found.position == expected.position
        )

    def _simulation_failure(
        self,
        request: ExecutionRequest,
        operation: str,
        order: PaperOrder,
        position: PaperPosition | None,
        simulation,
    ) -> PaperOrderExecutionResult:
        return self._failure(
            request,
            operation,
            _SIMULATION_OUTCOME_MAP.get(
                simulation.outcome,
                PaperOrderExecutionOutcome.INTERNAL_INVARIANT_FAILURE,
            ),
            simulation.reason_code,
            order=order,
            position=position,
            simulation_outcome=simulation.outcome,
        )

    def _repository_failure(
        self,
        request: ExecutionRequest,
        operation: str,
        repository_result: RepositoryResult,
        order: PaperOrder,
        position: PaperPosition | None,
        simulation_outcome: FillSimulationOutcome,
    ) -> PaperOrderExecutionResult:
        if repository_result.outcome is RepositoryOutcome.STALE_VERSION:
            if order.version != request.expected_order_version:
                outcome = PaperOrderExecutionOutcome.STALE_ORDER_VERSION
                reason = PaperOrderExecutionReasonCode.STALE_ORDER
            else:
                outcome = PaperOrderExecutionOutcome.STALE_POSITION_VERSION
                reason = PaperOrderExecutionReasonCode.STALE_POSITION
        elif repository_result.outcome is RepositoryOutcome.INVALID_STATE:
            outcome = (
                PaperOrderExecutionOutcome.INVALID_POSITION_STATE
                if operation == "CLOSE"
                else PaperOrderExecutionOutcome.INVALID_ORDER_STATE
            )
            reason = repository_result.reason_code
        elif repository_result.outcome is RepositoryOutcome.NOT_FOUND:
            outcome = PaperOrderExecutionOutcome.ORDER_NOT_FOUND
            reason = PaperOrderExecutionReasonCode.ORDER_NOT_FOUND
        else:
            outcome = _REPOSITORY_OUTCOME_MAP.get(
                repository_result.outcome,
                PaperOrderExecutionOutcome.INTERNAL_INVARIANT_FAILURE,
            )
            reason = repository_result.reason_code
        return self._failure(
            request,
            operation,
            outcome,
            reason,
            order=order,
            position=position,
            simulation_outcome=simulation_outcome,
            repository_outcome=repository_result.outcome,
        )

    def _success(
        self,
        request: ExecutionRequest,
        operation: str,
        outcome: PaperOrderExecutionOutcome,
        repository_result: RepositoryResult,
        simulation_outcome: FillSimulationOutcome,
        order_version_before: int,
        position_version_before: int | None,
    ) -> PaperOrderExecutionResult:
        graph = repository_result.value
        if not isinstance(graph, (EntryFillGraph, CloseFillGraph)):
            return self._failure(
                request,
                operation,
                PaperOrderExecutionOutcome.INTERNAL_INVARIANT_FAILURE,
                PaperOrderExecutionReasonCode.INTERNAL_INVARIANT,
                simulation_outcome=simulation_outcome,
                repository_outcome=repository_result.outcome,
            )
        return PaperOrderExecutionResult(
            operation=operation,
            outcome=outcome,
            reason_code=repository_result.reason_code,
            command_id=request.command_id,
            order_id=request.order_id,
            fill_id=graph.fill.fill_id,
            position_id=graph.position.position_id,
            exit_decision_id=getattr(request, "exit_decision_id", None),
            order_state=graph.order.state,
            position_state=graph.position.state,
            order_version=graph.order.version,
            position_version=graph.position.version,
            simulation_outcome=simulation_outcome,
            repository_outcome=repository_result.outcome,
            order_version_before=order_version_before,
            position_version_before=position_version_before,
            source_closed_until_ms=graph.fill.source_closed_until_ms,
        )

    @staticmethod
    def _failure(
        request: ExecutionRequest,
        operation: str,
        outcome: PaperOrderExecutionOutcome,
        reason_code: str | StrEnum,
        *,
        order: PaperOrder | None = None,
        position: PaperPosition | None = None,
        simulation_outcome: FillSimulationOutcome | None = None,
        repository_outcome: RepositoryOutcome | None = None,
    ) -> PaperOrderExecutionResult:
        return PaperOrderExecutionResult(
            operation=operation,
            outcome=outcome,
            reason_code=str(
                reason_code.value if isinstance(reason_code, StrEnum) else reason_code
            )[:96],
            command_id=request.command_id,
            order_id=request.order_id,
            fill_id=request.fill_id,
            position_id=getattr(request, "position_id", None),
            exit_decision_id=getattr(request, "exit_decision_id", None),
            order_state=order.state if order else None,
            position_state=position.state if position else None,
            order_version=order.version if order else None,
            position_version=position.version if position else None,
            simulation_outcome=simulation_outcome,
            repository_outcome=repository_outcome,
            order_version_before=order.version if order else None,
            position_version_before=position.version if position else None,
        )
