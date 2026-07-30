"""Bounded, explicitly authorized orchestration of one PAPER lifecycle.

The worker is deliberately caller-driven.  It does not fetch market data,
poll, sleep, schedule itself, own child transactions, or enable PAPER runtime.
Every mutating stage is delegated to an existing application service and every
stage boundary is reloaded from a fresh read-only Unit of Work.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Protocol

from sqlalchemy import select

from app.db.paper_models import PaperOrderRecord
from app.engine_execution.paper_models import PaperExecutionCommand, PaperFill, PaperOrder
from app.engine_exit.paper_exit import PaperExitDecision
from app.engine_journal.paper_events import PaperDomainEvent
from app.engine_paper.command_ingestion_service import (
    PaperCommandIngestionRequest,
    PaperCommandIngestionResult,
    PaperCommandIngestionService,
)
from app.engine_paper.exit_evaluation_cursor import PaperExitEvaluationCursor
from app.engine_paper.exit_evaluation_service import (
    PaperExitEvaluationRequest,
    PaperExitEvaluationService,
    PaperExitServiceResult,
)
from app.engine_paper.exit_evaluator import PAPER_EXIT_EVALUATION_POLICY_ID
from app.engine_paper.order_execution_service import (
    PaperCloseExecutionRequest,
    PaperEntryExecutionRequest,
    PaperOrderExecutionResult,
    PaperOrderExecutionService,
)
from app.engine_paper.repositories import MAX_GRAPH_ROWS, PaperCommandGraph
from app.engine_paper.repository_results import RepositoryOutcome
from app.engine_paper.unit_of_work import PaperUnitOfWork
from app.engine_position.paper_models import PaperPosition
from app.engine_safety.paper_domain import (
    ExecutionMode,
    PaperEventType,
    PaperOrderState,
    PaperPositionState,
    require_identity,
    require_utc,
)


PAPER_LIFECYCLE_CYCLE_CONTRACT_VERSION: Final = "PAPER_LIFECYCLE_CYCLE_V1"
MAX_STAGES_PER_CYCLE: Final = 4
MAX_STAGE_SERVICE_ATTEMPTS: Final = 1
MAX_STAGE_TRACE_ITEMS: Final = MAX_STAGES_PER_CYCLE


class PaperLifecycleCycleScope(StrEnum):
    ADVANCE_ONE_LIFECYCLE_STEP = "ADVANCE_ONE_LIFECYCLE_STEP"
    ADVANCE_UNTIL_BLOCKED_WITHIN_REQUEST = "ADVANCE_UNTIL_BLOCKED_WITHIN_REQUEST"


class PaperLifecycleState(StrEnum):
    APPROVALS_ONLY = "APPROVALS_ONLY"
    ENTRY_ORDER_OPEN = "ENTRY_ORDER_OPEN"
    POSITION_OPEN_CURSOR_READY = "POSITION_OPEN_CURSOR_READY"
    POSITION_CLOSING_CLOSE_ORDER_OPEN = "POSITION_CLOSING_CLOSE_ORDER_OPEN"
    POSITION_CLOSED = "POSITION_CLOSED"
    INCONSISTENT = "INCONSISTENT"


class PaperLifecycleStage(StrEnum):
    INGEST_COMMAND = "INGEST_COMMAND"
    EXECUTE_ENTRY = "EXECUTE_ENTRY"
    EVALUATE_EXIT = "EVALUATE_EXIT"
    EXECUTE_CLOSE = "EXECUTE_CLOSE"
    COMPLETE = "COMPLETE"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PaperLifecycleCycleOutcome(StrEnum):
    CYCLE_STAGE_COMPLETED = "CYCLE_STAGE_COMPLETED"
    CYCLE_ALREADY_AT_REQUESTED_STATE = "CYCLE_ALREADY_AT_REQUESTED_STATE"
    CYCLE_COMPLETE = "CYCLE_COMPLETE"
    CYCLE_BLOCKED_AWAITING_INPUT = "CYCLE_BLOCKED_AWAITING_INPUT"
    CYCLE_MAX_STAGES_REACHED = "CYCLE_MAX_STAGES_REACHED"
    CANCELLED_AFTER_COMMITTED_STAGE = "CANCELLED_AFTER_COMMITTED_STAGE"
    MODE_OFF = "MODE_OFF"
    MODE_LIVE_FORBIDDEN = "MODE_LIVE_FORBIDDEN"
    MODE_UNKNOWN = "MODE_UNKNOWN"
    PAPER_AUTHORIZATION_MISSING = "PAPER_AUTHORIZATION_MISSING"
    INVALID_CYCLE_SCOPE = "INVALID_CYCLE_SCOPE"
    INVALID_STAGE_INPUT = "INVALID_STAGE_INPUT"
    MISSING_APPROVAL_CHAIN = "MISSING_APPROVAL_CHAIN"
    MISSING_ENTRY_CANDLE_INPUT = "MISSING_ENTRY_CANDLE_INPUT"
    MISSING_EXIT_WINDOW_INPUT = "MISSING_EXIT_WINDOW_INPUT"
    MISSING_CLOSE_CANDLE_INPUT = "MISSING_CLOSE_CANDLE_INPUT"
    CANCELLED = "CANCELLED"
    SOURCE_GRAPH_INCONSISTENT = "SOURCE_GRAPH_INCONSISTENT"
    STALE_EXPECTED_VERSION = "STALE_EXPECTED_VERSION"
    UNSUPPORTED_LIFECYCLE_STATE = "UNSUPPORTED_LIFECYCLE_STATE"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    EXISTING_GRAPH_INCONSISTENT = "EXISTING_GRAPH_INCONSISTENT"
    INGESTION_STAGE_FAILED = "INGESTION_STAGE_FAILED"
    ENTRY_EXECUTION_STAGE_FAILED = "ENTRY_EXECUTION_STAGE_FAILED"
    EXIT_EVALUATION_STAGE_FAILED = "EXIT_EVALUATION_STAGE_FAILED"
    CLOSE_EXECUTION_STAGE_FAILED = "CLOSE_EXECUTION_STAGE_FAILED"
    UNCERTAIN_COMMIT_UNRESOLVED = "UNCERTAIN_COMMIT_UNRESOLVED"
    TRANSIENT_DB_FAILURE = "TRANSIENT_DB_FAILURE"
    INTERNAL_INVARIANT_FAILURE = "INTERNAL_INVARIANT_FAILURE"


class PaperLifecycleReasonCode(StrEnum):
    OK = "PAPER_LIFECYCLE_OK"
    COMPLETE = "PAPER_LIFECYCLE_COMPLETE"
    MAX_STAGES = "PAPER_LIFECYCLE_MAX_STAGES_REACHED"
    MODE_OFF = "PAPER_LIFECYCLE_MODE_OFF"
    MODE_LIVE_FORBIDDEN = "PAPER_LIFECYCLE_MODE_LIVE_FORBIDDEN"
    MODE_UNKNOWN = "PAPER_LIFECYCLE_MODE_UNKNOWN"
    AUTHORIZATION_MISSING = "PAPER_LIFECYCLE_AUTHORIZATION_MISSING"
    INVALID_SCOPE = "PAPER_LIFECYCLE_INVALID_SCOPE"
    INVALID_STAGE_INPUT = "PAPER_LIFECYCLE_INVALID_STAGE_INPUT"
    MISSING_APPROVAL_CHAIN = "PAPER_LIFECYCLE_MISSING_APPROVAL_CHAIN"
    MISSING_ENTRY_INPUT = "PAPER_LIFECYCLE_MISSING_ENTRY_CANDLE_INPUT"
    MISSING_EXIT_INPUT = "PAPER_LIFECYCLE_MISSING_EXIT_WINDOW_INPUT"
    MISSING_CLOSE_INPUT = "PAPER_LIFECYCLE_MISSING_CLOSE_CANDLE_INPUT"
    CANCELLED = "PAPER_LIFECYCLE_CANCELLED"
    CANCELLED_AFTER_COMMIT = "PAPER_LIFECYCLE_CANCELLED_AFTER_COMMIT"
    SOURCE_GRAPH_INCONSISTENT = "PAPER_LIFECYCLE_SOURCE_GRAPH_INCONSISTENT"
    EXISTING_GRAPH_INCONSISTENT = "PAPER_LIFECYCLE_EXISTING_GRAPH_INCONSISTENT"
    STALE_EXPECTED_VERSION = "PAPER_LIFECYCLE_STALE_EXPECTED_VERSION"
    UNSUPPORTED_STATE = "PAPER_LIFECYCLE_UNSUPPORTED_STATE"
    IDEMPOTENCY_CONFLICT = "PAPER_LIFECYCLE_IDEMPOTENCY_CONFLICT"
    INGESTION_FAILED = "PAPER_LIFECYCLE_INGESTION_STAGE_FAILED"
    ENTRY_FAILED = "PAPER_LIFECYCLE_ENTRY_STAGE_FAILED"
    EXIT_FAILED = "PAPER_LIFECYCLE_EXIT_STAGE_FAILED"
    CLOSE_FAILED = "PAPER_LIFECYCLE_CLOSE_STAGE_FAILED"
    UNCERTAIN_COMMIT_UNRESOLVED = "PAPER_LIFECYCLE_UNCERTAIN_COMMIT_UNRESOLVED"
    TRANSIENT_DB_FAILURE = "PAPER_LIFECYCLE_TRANSIENT_DB_FAILURE"
    INTERNAL_INVARIANT = "PAPER_LIFECYCLE_INTERNAL_INVARIANT_FAILURE"


class PaperLifecycleFaultPoint(StrEnum):
    BEFORE_GRAPH_LOAD = "BEFORE_GRAPH_LOAD"
    AFTER_GRAPH_LOAD = "AFTER_GRAPH_LOAD"
    BEFORE_CHILD_INVOCATION = "BEFORE_CHILD_INVOCATION"
    AFTER_CHILD_SUCCESS_BEFORE_GRAPH_RELOAD = (
        "AFTER_CHILD_SUCCESS_BEFORE_GRAPH_RELOAD"
    )
    DURING_GRAPH_RELOAD = "DURING_GRAPH_RELOAD"
    AFTER_GRAPH_RELOAD_BEFORE_RESULT = "AFTER_GRAPH_RELOAD_BEFORE_RESULT"
    BETWEEN_BOUNDED_STAGES = "BETWEEN_BOUNDED_STAGES"
    BEFORE_CANCELLATION_CHECK = "BEFORE_CANCELLATION_CHECK"


class PaperLifecycleCancellationAuthority(Protocol):
    """Explicit cooperative cancellation authority supplied by the caller."""

    def is_cancelled(self) -> bool: ...


class PaperLifecycleGraphLoaderProtocol(Protocol):
    def load(self, command_id: str) -> "PaperLifecycleGraph": ...


class PaperCommandIngestionServiceProtocol(Protocol):
    def ingest_and_create_entry_order(
        self, request: PaperCommandIngestionRequest
    ) -> PaperCommandIngestionResult: ...


class PaperOrderExecutionServiceProtocol(Protocol):
    def execute_entry(
        self, request: PaperEntryExecutionRequest
    ) -> PaperOrderExecutionResult: ...

    def execute_close(
        self, request: PaperCloseExecutionRequest
    ) -> PaperOrderExecutionResult: ...


class PaperExitEvaluationServiceProtocol(Protocol):
    def evaluate(self, request: PaperExitEvaluationRequest) -> PaperExitServiceResult: ...


@dataclass(frozen=True, slots=True)
class PaperLifecycleOrderNode:
    role: str
    order: PaperOrder


@dataclass(frozen=True, slots=True)
class PaperLifecycleGraph:
    command_id: str
    command: PaperExecutionCommand | None = None
    orders: tuple[PaperLifecycleOrderNode, ...] = ()
    fills: tuple[PaperFill, ...] = ()
    positions: tuple[PaperPosition, ...] = ()
    exit_decisions: tuple[PaperExitDecision, ...] = ()
    cursors: tuple[PaperExitEvaluationCursor, ...] = ()
    order_events: tuple[PaperDomainEvent, ...] = ()
    journal: tuple[PaperDomainEvent, ...] = ()
    bounded_limit_reached: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "command_id", require_identity(self.command_id, "command_id")
        )
        for name in (
            "orders",
            "fills",
            "positions",
            "exit_decisions",
            "cursors",
            "order_events",
            "journal",
        ):
            if not isinstance(getattr(self, name), tuple):
                raise TypeError(f"{name} must be an immutable tuple")


@dataclass(frozen=True, slots=True)
class PaperLifecycleStageTrace:
    stage: PaperLifecycleStage
    state_before: PaperLifecycleState
    state_after: PaperLifecycleState
    child_outcome_code: str | None
    child_reason_code: str | None
    mutation_committed: bool


@dataclass(frozen=True, slots=True)
class PaperLifecycleCycleRequest:
    cycle_id: str
    contract_version: str
    execution_mode: object
    explicit_paper_authorization: bool
    scope: object
    max_stages: int
    created_at: datetime
    correlation_id: str
    command_id: str
    entry_order_id: str | None = None
    entry_fill_id: str | None = None
    position_id: str | None = None
    cursor_id: str | None = None
    exit_decision_id: str | None = None
    close_order_id: str | None = None
    close_fill_id: str | None = None
    ingestion_request: PaperCommandIngestionRequest | None = None
    entry_execution_request: PaperEntryExecutionRequest | None = None
    exit_evaluation_request: PaperExitEvaluationRequest | None = None
    close_execution_request: PaperCloseExecutionRequest | None = None
    cancellation_authority: PaperLifecycleCancellationAuthority | None = None

    def __post_init__(self) -> None:
        for name in ("cycle_id", "contract_version", "correlation_id", "command_id"):
            object.__setattr__(
                self, name, require_identity(getattr(self, name), name)
            )
        for name in (
            "entry_order_id",
            "entry_fill_id",
            "position_id",
            "cursor_id",
            "exit_decision_id",
            "close_order_id",
            "close_fill_id",
        ):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, require_identity(value, name))
        require_utc(self.created_at, "created_at")
        if isinstance(self.max_stages, bool) or not isinstance(self.max_stages, int):
            raise TypeError("max_stages must be an integer")


@dataclass(frozen=True, slots=True)
class PaperLifecycleCycleResult:
    cycle_id: str
    outcome: PaperLifecycleCycleOutcome
    reason_code: str
    initial_lifecycle_state: PaperLifecycleState
    final_lifecycle_state: PaperLifecycleState
    stages_attempted: int
    stages_completed: int
    stage_trace: tuple[PaperLifecycleStageTrace, ...]
    child_outcome_codes: tuple[str, ...]
    child_reason_codes: tuple[str, ...]
    command_id: str
    entry_order_id: str | None
    entry_fill_id: str | None
    position_id: str | None
    position_state: PaperPositionState | None
    position_version: int | None
    cursor_id: str | None
    cursor_version: int | None
    cursor_boundary_ms: int | None
    exit_decision_id: str | None
    close_order_id: str | None
    close_fill_id: str | None
    correlation_id: str


class PaperLifecycleGraphLoadError(RuntimeError):
    def __init__(self, outcome: RepositoryOutcome, reason_code: str) -> None:
        super().__init__(reason_code)
        self.outcome = outcome
        self.reason_code = str(reason_code)[:96]


class SqlAlchemyPaperLifecycleGraphLoader:
    """Load one bounded immutable graph in a fresh read-only UoW."""

    def __init__(self, uow_factory: Callable[[], PaperUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def load(self, command_id: str) -> PaperLifecycleGraph:
        exact_command_id = require_identity(command_id, "command_id")
        with self._uow_factory() as uow:
            if uow.repositories is None or uow.session is None:
                raise PaperLifecycleGraphLoadError(
                    RepositoryOutcome.INTERNAL_INVARIANT_FAILURE,
                    "PAPER_LIFECYCLE_READ_UOW_UNAVAILABLE",
                )
            result = uow.repositories.commands.get_command_graph(
                exact_command_id, limit=MAX_GRAPH_ROWS
            )
            if result.outcome is RepositoryOutcome.NOT_FOUND:
                return PaperLifecycleGraph(command_id=exact_command_id)
            if (
                result.outcome is not RepositoryOutcome.EXISTING_IDEMPOTENT
                or not isinstance(result.value, PaperCommandGraph)
            ):
                raise PaperLifecycleGraphLoadError(
                    result.outcome, result.reason_code
                )
            graph = result.value
            role_rows = tuple(
                uow.session.execute(
                    select(PaperOrderRecord.order_id, PaperOrderRecord.order_role)
                    .where(PaperOrderRecord.command_id == exact_command_id)
                    .order_by(PaperOrderRecord.order_role, PaperOrderRecord.order_id)
                    .limit(3)
                )
            )
            role_by_id = {str(row.order_id): str(row.order_role) for row in role_rows}
            orders = tuple(
                PaperLifecycleOrderNode(role_by_id.get(order.order_id, ""), order)
                for order in graph.orders
            )
            bounded_limit_reached = any(
                len(values) >= MAX_GRAPH_ROWS
                for values in (
                    graph.orders,
                    graph.fills,
                    graph.positions,
                    graph.exit_decisions,
                    graph.cursors,
                    graph.order_events,
                    graph.journal,
                )
            )
            if len(role_rows) != len(graph.orders):
                bounded_limit_reached = True
            return PaperLifecycleGraph(
                command_id=exact_command_id,
                command=graph.command,
                orders=orders,
                fills=graph.fills,
                positions=graph.positions,
                exit_decisions=graph.exit_decisions,
                cursors=graph.cursors,
                order_events=graph.order_events,
                journal=graph.journal,
                bounded_limit_reached=bounded_limit_reached,
            )


def _event_counter(events: tuple[PaperDomainEvent, ...]) -> Counter[PaperEventType]:
    return Counter(item.event_type for item in events)


def _audit_matches(
    graph: PaperLifecycleGraph,
    state: PaperLifecycleState,
) -> bool:
    entry_open_events = Counter(
        {
            PaperEventType.PAPER_ORDER_CREATED: 1,
            PaperEventType.PAPER_ORDER_VALIDATED: 1,
            PaperEventType.PAPER_ORDER_OPENED: 1,
        }
    )
    entry_open_journal = entry_open_events + Counter(
        {PaperEventType.PAPER_COMMAND_CREATED: 1}
    )
    if state is PaperLifecycleState.ENTRY_ORDER_OPEN:
        return (
            _event_counter(graph.order_events) == entry_open_events
            and _event_counter(graph.journal) == entry_open_journal
        )
    entry_done_events = entry_open_events + Counter(
        {PaperEventType.PAPER_ORDER_FILLED: 1}
    )
    entry_done_journal = entry_open_journal + Counter(
        {
            PaperEventType.PAPER_ORDER_FILLED: 1,
            PaperEventType.PAPER_POSITION_OPENED: 1,
        }
    )
    if state is PaperLifecycleState.POSITION_OPEN_CURSOR_READY:
        return (
            _event_counter(graph.order_events) == entry_done_events
            and _event_counter(graph.journal) == entry_done_journal
        )
    closing_events = entry_done_events + Counter(
        {
            PaperEventType.PAPER_ORDER_CREATED: 1,
            PaperEventType.PAPER_ORDER_VALIDATED: 1,
            PaperEventType.PAPER_ORDER_OPENED: 1,
        }
    )
    closing_journal = entry_done_journal + Counter(
        {
            PaperEventType.PAPER_EXIT_TRIGGERED: 1,
            PaperEventType.PAPER_ORDER_CREATED: 1,
            PaperEventType.PAPER_ORDER_VALIDATED: 1,
            PaperEventType.PAPER_ORDER_OPENED: 1,
        }
    )
    if state is PaperLifecycleState.POSITION_CLOSING_CLOSE_ORDER_OPEN:
        return (
            _event_counter(graph.order_events) == closing_events
            and _event_counter(graph.journal) == closing_journal
        )
    if state is PaperLifecycleState.POSITION_CLOSED:
        return (
            _event_counter(graph.order_events)
            == closing_events + Counter({PaperEventType.PAPER_ORDER_FILLED: 1})
            and _event_counter(graph.journal)
            == closing_journal
            + Counter(
                {
                    PaperEventType.PAPER_ORDER_FILLED: 1,
                    PaperEventType.PAPER_POSITION_CLOSED: 1,
                }
            )
        )
    return False


def _unique_public_ids(graph: PaperLifecycleGraph) -> bool:
    groups = (
        tuple(item.order.order_id for item in graph.orders),
        tuple(item.fill_id for item in graph.fills),
        tuple(item.position_id for item in graph.positions),
        tuple(item.exit_decision_id for item in graph.exit_decisions),
        tuple(item.cursor_id for item in graph.cursors),
        tuple(item.event_id for item in graph.order_events),
        tuple(item.event_id for item in graph.journal),
    )
    return all(len(values) == len(set(values)) for values in groups)


def classify_paper_lifecycle_state(
    graph: PaperLifecycleGraph,
) -> PaperLifecycleState:
    """Purely classify one immutable graph with zero I/O or clock access."""

    if not isinstance(graph, PaperLifecycleGraph) or graph.bounded_limit_reached:
        return PaperLifecycleState.INCONSISTENT
    if graph.command is None:
        return (
            PaperLifecycleState.APPROVALS_ONLY
            if not any(
                (
                    graph.orders,
                    graph.fills,
                    graph.positions,
                    graph.exit_decisions,
                    graph.cursors,
                    graph.order_events,
                    graph.journal,
                )
            )
            else PaperLifecycleState.INCONSISTENT
        )
    if graph.command.command_id != graph.command_id or not _unique_public_ids(graph):
        return PaperLifecycleState.INCONSISTENT
    if graph.command.mode is not ExecutionMode.PAPER:
        return PaperLifecycleState.INCONSISTENT
    roles = Counter(item.role for item in graph.orders)
    if any(
        node.order.command_id != graph.command_id
        or node.order.symbol != graph.command.symbol
        for node in graph.orders
    ):
        return PaperLifecycleState.INCONSISTENT
    entry_nodes = tuple(item for item in graph.orders if item.role == "ENTRY")
    close_nodes = tuple(item for item in graph.orders if item.role == "EXIT")
    if roles not in (Counter({"ENTRY": 1}), Counter({"ENTRY": 1, "EXIT": 1})):
        return PaperLifecycleState.INCONSISTENT
    if len(entry_nodes) != 1:
        return PaperLifecycleState.INCONSISTENT
    entry_order = entry_nodes[0].order
    if (
        entry_order.state is PaperOrderState.OPEN
        and not graph.fills
        and not graph.positions
        and not graph.exit_decisions
        and not graph.cursors
        and not close_nodes
    ):
        state = PaperLifecycleState.ENTRY_ORDER_OPEN
        return state if _audit_matches(graph, state) else PaperLifecycleState.INCONSISTENT
    if len(graph.positions) != 1 or len(graph.cursors) != 1:
        return PaperLifecycleState.INCONSISTENT
    position = graph.positions[0]
    cursor = graph.cursors[0]
    entry_fills = tuple(item for item in graph.fills if item.order_id == entry_order.order_id)
    if (
        entry_order.state is not PaperOrderState.FILLED
        or len(entry_fills) != 1
        or entry_order.applied_fill_id != entry_fills[0].fill_id
        or position.entry_order_id != entry_order.order_id
        or position.entry_fill_id != entry_fills[0].fill_id
        or cursor.position_id != position.position_id
        or cursor.mode is not ExecutionMode.PAPER
        or cursor.symbol != position.symbol
        or cursor.position_opened_closed_until_ms
        != entry_fills[0].source_closed_until_ms
        or cursor.last_evaluated_closed_until_ms
        < cursor.position_opened_closed_until_ms
        or cursor.evaluation_policy_id != PAPER_EXIT_EVALUATION_POLICY_ID
    ):
        return PaperLifecycleState.INCONSISTENT
    if (
        position.state is PaperPositionState.OPEN
        and not close_nodes
        and not graph.exit_decisions
        and len(graph.fills) == 1
    ):
        state = PaperLifecycleState.POSITION_OPEN_CURSOR_READY
        return state if _audit_matches(graph, state) else PaperLifecycleState.INCONSISTENT
    if len(close_nodes) != 1 or len(graph.exit_decisions) != 1:
        return PaperLifecycleState.INCONSISTENT
    close_order = close_nodes[0].order
    decision = graph.exit_decisions[0]
    close_fills = tuple(item for item in graph.fills if item.order_id == close_order.order_id)
    if (
        decision.position_id != position.position_id
        or decision.source_closed_until_ms != cursor.last_evaluated_closed_until_ms
        or close_order.command_id != graph.command_id
    ):
        return PaperLifecycleState.INCONSISTENT
    if (
        position.state is PaperPositionState.CLOSING
        and close_order.state is PaperOrderState.OPEN
        and not close_fills
        and len(graph.fills) == 1
    ):
        state = PaperLifecycleState.POSITION_CLOSING_CLOSE_ORDER_OPEN
        return state if _audit_matches(graph, state) else PaperLifecycleState.INCONSISTENT
    if (
        position.state is PaperPositionState.CLOSED
        and close_order.state is PaperOrderState.FILLED
        and len(close_fills) == 1
        and len(graph.fills) == 2
        and close_order.applied_fill_id == close_fills[0].fill_id
        and position.exit_fill_id == close_fills[0].fill_id
        and position.remaining_quantity == 0
        and position.closed_at is not None
    ):
        state = PaperLifecycleState.POSITION_CLOSED
        return state if _audit_matches(graph, state) else PaperLifecycleState.INCONSISTENT
    return PaperLifecycleState.INCONSISTENT


_STAGE_FOR_STATE: Final = MappingProxyType({
    PaperLifecycleState.APPROVALS_ONLY: PaperLifecycleStage.INGEST_COMMAND,
    PaperLifecycleState.ENTRY_ORDER_OPEN: PaperLifecycleStage.EXECUTE_ENTRY,
    PaperLifecycleState.POSITION_OPEN_CURSOR_READY: PaperLifecycleStage.EVALUATE_EXIT,
    PaperLifecycleState.POSITION_CLOSING_CLOSE_ORDER_OPEN: (
        PaperLifecycleStage.EXECUTE_CLOSE
    ),
    PaperLifecycleState.POSITION_CLOSED: PaperLifecycleStage.COMPLETE,
})


class PaperControlledLifecycleWorker:
    """Run at most four supplied stages; default use is exactly one stage."""

    def __init__(
        self,
        graph_loader: PaperLifecycleGraphLoaderProtocol,
        ingestion_service: PaperCommandIngestionServiceProtocol,
        order_execution_service: PaperOrderExecutionServiceProtocol,
        exit_evaluation_service: PaperExitEvaluationServiceProtocol,
        *,
        fault_injector: Callable[[PaperLifecycleFaultPoint], None] | None = None,
    ) -> None:
        self._graph_loader = graph_loader
        self._ingestion_service = ingestion_service
        self._order_execution_service = order_execution_service
        self._exit_evaluation_service = exit_evaluation_service
        self._fault_injector = fault_injector

    @classmethod
    def from_factories(
        cls,
        uow_factory: Callable[[], PaperUnitOfWork],
        recovery_session_factory,
        *,
        fault_injector: Callable[[PaperLifecycleFaultPoint], None] | None = None,
    ) -> "PaperControlledLifecycleWorker":
        return cls(
            SqlAlchemyPaperLifecycleGraphLoader(uow_factory),
            PaperCommandIngestionService(uow_factory, recovery_session_factory),
            PaperOrderExecutionService(uow_factory, recovery_session_factory),
            PaperExitEvaluationService(uow_factory, recovery_session_factory),
            fault_injector=fault_injector,
        )

    def run_cycle(
        self, request: PaperLifecycleCycleRequest
    ) -> PaperLifecycleCycleResult:
        if not isinstance(request, PaperLifecycleCycleRequest):
            raise TypeError("request must be PaperLifecycleCycleRequest")
        denied = self._validate_cycle(request)
        empty = PaperLifecycleGraph(command_id=request.command_id)
        if denied is not None:
            outcome, reason = denied
            return self._result(request, empty, empty, outcome, reason, ())
        self._fault(PaperLifecycleFaultPoint.BEFORE_CANCELLATION_CHECK)
        if self._cancelled(request):
            return self._result(
                request,
                empty,
                empty,
                PaperLifecycleCycleOutcome.CANCELLED,
                PaperLifecycleReasonCode.CANCELLED,
                (),
            )
        try:
            self._fault(PaperLifecycleFaultPoint.BEFORE_GRAPH_LOAD)
            initial_graph = self._graph_loader.load(request.command_id)
            self._fault(PaperLifecycleFaultPoint.AFTER_GRAPH_LOAD)
        except PaperLifecycleGraphLoadError as exc:
            outcome = (
                PaperLifecycleCycleOutcome.TRANSIENT_DB_FAILURE
                if exc.outcome is RepositoryOutcome.TRANSIENT_DB_FAILURE
                else PaperLifecycleCycleOutcome.INTERNAL_INVARIANT_FAILURE
            )
            return self._result(
                request, empty, empty, outcome, exc.reason_code, ()
            )
        initial_state = classify_paper_lifecycle_state(initial_graph)
        if (
            initial_state is PaperLifecycleState.INCONSISTENT
            or not self._identities_match(request, initial_graph)
        ):
            return self._result(
                request,
                initial_graph,
                initial_graph,
                PaperLifecycleCycleOutcome.EXISTING_GRAPH_INCONSISTENT,
                PaperLifecycleReasonCode.EXISTING_GRAPH_INCONSISTENT,
                (),
            )
        if initial_state is PaperLifecycleState.POSITION_CLOSED:
            return self._result(
                request,
                initial_graph,
                initial_graph,
                PaperLifecycleCycleOutcome.CYCLE_COMPLETE,
                PaperLifecycleReasonCode.COMPLETE,
                (),
            )

        trace: list[PaperLifecycleStageTrace] = []
        graph = initial_graph
        stage_limit = (
            1
            if PaperLifecycleCycleScope(request.scope)
            is PaperLifecycleCycleScope.ADVANCE_ONE_LIFECYCLE_STEP
            else request.max_stages
        )
        for stage_index in range(stage_limit):
            state_before = classify_paper_lifecycle_state(graph)
            stage = _STAGE_FOR_STATE.get(state_before)
            if stage is None:
                return self._result(
                    request,
                    initial_graph,
                    graph,
                    PaperLifecycleCycleOutcome.UNSUPPORTED_LIFECYCLE_STATE,
                    PaperLifecycleReasonCode.UNSUPPORTED_STATE,
                    tuple(trace),
                )
            if stage is PaperLifecycleStage.COMPLETE:
                return self._result(
                    request,
                    initial_graph,
                    graph,
                    PaperLifecycleCycleOutcome.CYCLE_COMPLETE,
                    PaperLifecycleReasonCode.COMPLETE,
                    tuple(trace),
                )
            self._fault(PaperLifecycleFaultPoint.BEFORE_CANCELLATION_CHECK)
            if self._cancelled(request):
                outcome = (
                    PaperLifecycleCycleOutcome.CANCELLED_AFTER_COMMITTED_STAGE
                    if trace
                    else PaperLifecycleCycleOutcome.CANCELLED
                )
                reason = (
                    PaperLifecycleReasonCode.CANCELLED_AFTER_COMMIT
                    if trace
                    else PaperLifecycleReasonCode.CANCELLED
                )
                return self._result(
                    request, initial_graph, graph, outcome, reason, tuple(trace)
                )
            missing = self._stage_input_failure(request, graph, stage)
            if missing is not None:
                outcome, reason = missing
                return self._result(
                    request, initial_graph, graph, outcome, reason, tuple(trace)
                )
            self._fault(PaperLifecycleFaultPoint.BEFORE_CHILD_INVOCATION)
            child = self._invoke_stage(request, stage)
            child_outcome = str(child.outcome.value)
            child_reason = str(child.reason_code)[:96]
            if not child.successful:
                outcome, reason = self._map_child_failure(stage, child_outcome)
                failed_trace = PaperLifecycleStageTrace(
                    stage,
                    state_before,
                    state_before,
                    child_outcome,
                    child_reason,
                    False,
                )
                return self._result(
                    request,
                    initial_graph,
                    graph,
                    outcome,
                    reason,
                    tuple([*trace, failed_trace]),
                )
            self._fault(PaperLifecycleFaultPoint.AFTER_CHILD_SUCCESS_BEFORE_GRAPH_RELOAD)
            self._fault(PaperLifecycleFaultPoint.DURING_GRAPH_RELOAD)
            try:
                reloaded = self._graph_loader.load(request.command_id)
            except PaperLifecycleGraphLoadError as exc:
                failed_trace = PaperLifecycleStageTrace(
                    stage,
                    state_before,
                    PaperLifecycleState.INCONSISTENT,
                    child_outcome,
                    child_reason,
                    True,
                )
                outcome = (
                    PaperLifecycleCycleOutcome.TRANSIENT_DB_FAILURE
                    if exc.outcome is RepositoryOutcome.TRANSIENT_DB_FAILURE
                    else PaperLifecycleCycleOutcome.INTERNAL_INVARIANT_FAILURE
                )
                return self._result(
                    request,
                    initial_graph,
                    graph,
                    outcome,
                    exc.reason_code,
                    tuple([*trace, failed_trace]),
                )
            state_after = classify_paper_lifecycle_state(reloaded)
            committed = self._stage_transition_valid(
                stage, state_before, state_after, child_outcome
            )
            trace.append(
                PaperLifecycleStageTrace(
                    stage,
                    state_before,
                    state_after,
                    child_outcome,
                    child_reason,
                    committed,
                )
            )
            graph = reloaded
            if not committed or not self._identities_match(request, graph):
                return self._result(
                    request,
                    initial_graph,
                    graph,
                    PaperLifecycleCycleOutcome.SOURCE_GRAPH_INCONSISTENT,
                    PaperLifecycleReasonCode.SOURCE_GRAPH_INCONSISTENT,
                    tuple(trace),
                )
            self._fault(PaperLifecycleFaultPoint.AFTER_GRAPH_RELOAD_BEFORE_RESULT)
            self._fault(PaperLifecycleFaultPoint.BEFORE_CANCELLATION_CHECK)
            if self._cancelled(request):
                return self._result(
                    request,
                    initial_graph,
                    graph,
                    PaperLifecycleCycleOutcome.CANCELLED_AFTER_COMMITTED_STAGE,
                    PaperLifecycleReasonCode.CANCELLED_AFTER_COMMIT,
                    tuple(trace),
                )
            if (
                PaperLifecycleCycleScope(request.scope)
                is PaperLifecycleCycleScope.ADVANCE_ONE_LIFECYCLE_STEP
            ):
                outcome = (
                    PaperLifecycleCycleOutcome.CYCLE_COMPLETE
                    if state_after is PaperLifecycleState.POSITION_CLOSED
                    else PaperLifecycleCycleOutcome.CYCLE_STAGE_COMPLETED
                )
                reason = (
                    PaperLifecycleReasonCode.COMPLETE
                    if outcome is PaperLifecycleCycleOutcome.CYCLE_COMPLETE
                    else PaperLifecycleReasonCode.OK
                )
                return self._result(
                    request, initial_graph, graph, outcome, reason, tuple(trace)
                )
            if state_after is PaperLifecycleState.POSITION_CLOSED:
                return self._result(
                    request,
                    initial_graph,
                    graph,
                    PaperLifecycleCycleOutcome.CYCLE_COMPLETE,
                    PaperLifecycleReasonCode.COMPLETE,
                    tuple(trace),
                )
            if stage_index + 1 < stage_limit:
                self._fault(PaperLifecycleFaultPoint.BETWEEN_BOUNDED_STAGES)
        return self._result(
            request,
            initial_graph,
            graph,
            PaperLifecycleCycleOutcome.CYCLE_MAX_STAGES_REACHED,
            PaperLifecycleReasonCode.MAX_STAGES,
            tuple(trace),
        )

    @staticmethod
    def _validate_cycle(
        request: PaperLifecycleCycleRequest,
    ) -> tuple[PaperLifecycleCycleOutcome, PaperLifecycleReasonCode] | None:
        try:
            mode = ExecutionMode(request.execution_mode)
        except (TypeError, ValueError):
            return (
                PaperLifecycleCycleOutcome.MODE_UNKNOWN,
                PaperLifecycleReasonCode.MODE_UNKNOWN,
            )
        if mode is ExecutionMode.OFF:
            return PaperLifecycleCycleOutcome.MODE_OFF, PaperLifecycleReasonCode.MODE_OFF
        if mode is ExecutionMode.LIVE:
            return (
                PaperLifecycleCycleOutcome.MODE_LIVE_FORBIDDEN,
                PaperLifecycleReasonCode.MODE_LIVE_FORBIDDEN,
            )
        if request.explicit_paper_authorization is not True:
            return (
                PaperLifecycleCycleOutcome.PAPER_AUTHORIZATION_MISSING,
                PaperLifecycleReasonCode.AUTHORIZATION_MISSING,
            )
        if request.contract_version != PAPER_LIFECYCLE_CYCLE_CONTRACT_VERSION:
            return (
                PaperLifecycleCycleOutcome.INVALID_STAGE_INPUT,
                PaperLifecycleReasonCode.INVALID_STAGE_INPUT,
            )
        try:
            scope = PaperLifecycleCycleScope(request.scope)
        except (TypeError, ValueError):
            return (
                PaperLifecycleCycleOutcome.INVALID_CYCLE_SCOPE,
                PaperLifecycleReasonCode.INVALID_SCOPE,
            )
        if (
            request.max_stages < 1
            or request.max_stages > MAX_STAGES_PER_CYCLE
            or (
                scope is PaperLifecycleCycleScope.ADVANCE_ONE_LIFECYCLE_STEP
                and request.max_stages != 1
            )
        ):
            return (
                PaperLifecycleCycleOutcome.INVALID_CYCLE_SCOPE,
                PaperLifecycleReasonCode.INVALID_SCOPE,
            )
        return None

    def _fault(self, point: PaperLifecycleFaultPoint) -> None:
        if self._fault_injector is not None:
            self._fault_injector(point)

    @staticmethod
    def _cancelled(request: PaperLifecycleCycleRequest) -> bool:
        authority = request.cancellation_authority
        return authority is not None and authority.is_cancelled() is True

    @staticmethod
    def _identities_match(
        request: PaperLifecycleCycleRequest, graph: PaperLifecycleGraph
    ) -> bool:
        if graph.command is None:
            return True
        nodes = {item.role: item.order for item in graph.orders}
        values = {
            "entry_order_id": nodes.get("ENTRY").order_id if nodes.get("ENTRY") else None,
            "entry_fill_id": (
                graph.positions[0].entry_fill_id if len(graph.positions) == 1 else None
            ),
            "position_id": (
                graph.positions[0].position_id if len(graph.positions) == 1 else None
            ),
            "cursor_id": graph.cursors[0].cursor_id if len(graph.cursors) == 1 else None,
            "exit_decision_id": (
                graph.exit_decisions[0].exit_decision_id
                if len(graph.exit_decisions) == 1
                else None
            ),
            "close_order_id": nodes.get("EXIT").order_id if nodes.get("EXIT") else None,
            "close_fill_id": (
                graph.positions[0].exit_fill_id if len(graph.positions) == 1 else None
            ),
        }
        return all(
            getattr(request, name) is None or getattr(request, name) == actual
            for name, actual in values.items()
            if actual is not None
        )

    @staticmethod
    def _stage_input_failure(
        request: PaperLifecycleCycleRequest,
        graph: PaperLifecycleGraph,
        stage: PaperLifecycleStage,
    ) -> tuple[PaperLifecycleCycleOutcome, PaperLifecycleReasonCode] | None:
        nested = {
            PaperLifecycleStage.INGEST_COMMAND: request.ingestion_request,
            PaperLifecycleStage.EXECUTE_ENTRY: request.entry_execution_request,
            PaperLifecycleStage.EVALUATE_EXIT: request.exit_evaluation_request,
            PaperLifecycleStage.EXECUTE_CLOSE: request.close_execution_request,
        }[stage]
        if nested is None:
            return {
                PaperLifecycleStage.INGEST_COMMAND: (
                    PaperLifecycleCycleOutcome.CYCLE_BLOCKED_AWAITING_INPUT,
                    PaperLifecycleReasonCode.MISSING_APPROVAL_CHAIN,
                ),
                PaperLifecycleStage.EXECUTE_ENTRY: (
                    PaperLifecycleCycleOutcome.CYCLE_BLOCKED_AWAITING_INPUT,
                    PaperLifecycleReasonCode.MISSING_ENTRY_INPUT,
                ),
                PaperLifecycleStage.EVALUATE_EXIT: (
                    PaperLifecycleCycleOutcome.CYCLE_BLOCKED_AWAITING_INPUT,
                    PaperLifecycleReasonCode.MISSING_EXIT_INPUT,
                ),
                PaperLifecycleStage.EXECUTE_CLOSE: (
                    PaperLifecycleCycleOutcome.CYCLE_BLOCKED_AWAITING_INPUT,
                    PaperLifecycleReasonCode.MISSING_CLOSE_INPUT,
                ),
            }[stage]
        if stage is PaperLifecycleStage.INGEST_COMMAND:
            valid = (
                nested.command_id == request.command_id
                and nested.correlation_id == request.correlation_id
                and (
                    request.entry_order_id is None
                    or nested.order_id == request.entry_order_id
                )
            )
        elif stage is PaperLifecycleStage.EXECUTE_ENTRY:
            valid = (
                nested.command_id == request.command_id
                and nested.correlation_id == request.correlation_id
                and bool(nested.candidate_candles)
                and _matches_optional(request.entry_order_id, nested.order_id)
                and _matches_optional(request.entry_fill_id, nested.fill_id)
                and _matches_optional(request.position_id, nested.position_id)
            )
        elif stage is PaperLifecycleStage.EVALUATE_EXIT:
            valid = (
                nested.source_command_id == request.command_id
                and nested.correlation_id == request.correlation_id
                and bool(nested.candles)
                and _matches_optional(request.entry_order_id, nested.entry_order_id)
                and _matches_optional(request.entry_fill_id, nested.entry_fill_id)
                and _matches_optional(request.position_id, nested.position_id)
                and _matches_optional(request.cursor_id, nested.cursor_id)
                and _matches_optional(
                    request.exit_decision_id, nested.exit_decision_id
                )
                and _matches_optional(request.close_order_id, nested.close_order_id)
            )
        else:
            valid = (
                nested.command_id == request.command_id
                and nested.correlation_id == request.correlation_id
                and bool(nested.candidate_candles)
                and _matches_optional(request.position_id, nested.position_id)
                and _matches_optional(
                    request.exit_decision_id, nested.exit_decision_id
                )
                and _matches_optional(request.close_order_id, nested.order_id)
                and _matches_optional(request.close_fill_id, nested.fill_id)
            )
        if not valid:
            return (
                PaperLifecycleCycleOutcome.INVALID_STAGE_INPUT,
                PaperLifecycleReasonCode.INVALID_STAGE_INPUT,
            )
        return None

    def _invoke_stage(self, request: PaperLifecycleCycleRequest, stage):
        # Authorization is revalidated immediately at every child boundary.
        denied = self._validate_cycle(request)
        if denied is not None:
            raise RuntimeError(denied[1].value)
        if stage is PaperLifecycleStage.INGEST_COMMAND:
            assert request.ingestion_request is not None
            child_request = replace(
                request.ingestion_request,
                execution_mode=ExecutionMode.PAPER,
                explicit_paper_authorization=True,
                correlation_id=request.correlation_id,
            )
            return self._ingestion_service.ingest_and_create_entry_order(child_request)
        if stage is PaperLifecycleStage.EXECUTE_ENTRY:
            assert request.entry_execution_request is not None
            child_request = replace(
                request.entry_execution_request,
                correlation_id=request.correlation_id,
            )
            return self._order_execution_service.execute_entry(child_request)
        if stage is PaperLifecycleStage.EVALUATE_EXIT:
            assert request.exit_evaluation_request is not None
            child_request = replace(
                request.exit_evaluation_request,
                execution_mode=ExecutionMode.PAPER,
                explicit_paper_authorization=True,
                correlation_id=request.correlation_id,
            )
            return self._exit_evaluation_service.evaluate(child_request)
        assert request.close_execution_request is not None
        child_request = replace(
            request.close_execution_request,
            correlation_id=request.correlation_id,
        )
        return self._order_execution_service.execute_close(child_request)

    @staticmethod
    def _map_child_failure(
        stage: PaperLifecycleStage, child_outcome: str
    ) -> tuple[PaperLifecycleCycleOutcome, PaperLifecycleReasonCode]:
        if child_outcome == "UNCERTAIN_COMMIT_UNRESOLVED":
            return (
                PaperLifecycleCycleOutcome.UNCERTAIN_COMMIT_UNRESOLVED,
                PaperLifecycleReasonCode.UNCERTAIN_COMMIT_UNRESOLVED,
            )
        if child_outcome == "TRANSIENT_DB_FAILURE":
            return (
                PaperLifecycleCycleOutcome.TRANSIENT_DB_FAILURE,
                PaperLifecycleReasonCode.TRANSIENT_DB_FAILURE,
            )
        if "IDEMPOTENCY_CONFLICT" in child_outcome:
            return (
                PaperLifecycleCycleOutcome.IDEMPOTENCY_CONFLICT,
                PaperLifecycleReasonCode.IDEMPOTENCY_CONFLICT,
            )
        if child_outcome.startswith("STALE_"):
            return (
                PaperLifecycleCycleOutcome.STALE_EXPECTED_VERSION,
                PaperLifecycleReasonCode.STALE_EXPECTED_VERSION,
            )
        if "EXISTING" in child_outcome and "INCONSISTENT" in child_outcome:
            return (
                PaperLifecycleCycleOutcome.EXISTING_GRAPH_INCONSISTENT,
                PaperLifecycleReasonCode.EXISTING_GRAPH_INCONSISTENT,
            )
        if "SOURCE_GRAPH_INCONSISTENT" in child_outcome:
            return (
                PaperLifecycleCycleOutcome.SOURCE_GRAPH_INCONSISTENT,
                PaperLifecycleReasonCode.SOURCE_GRAPH_INCONSISTENT,
            )
        return {
            PaperLifecycleStage.INGEST_COMMAND: (
                PaperLifecycleCycleOutcome.INGESTION_STAGE_FAILED,
                PaperLifecycleReasonCode.INGESTION_FAILED,
            ),
            PaperLifecycleStage.EXECUTE_ENTRY: (
                PaperLifecycleCycleOutcome.ENTRY_EXECUTION_STAGE_FAILED,
                PaperLifecycleReasonCode.ENTRY_FAILED,
            ),
            PaperLifecycleStage.EVALUATE_EXIT: (
                PaperLifecycleCycleOutcome.EXIT_EVALUATION_STAGE_FAILED,
                PaperLifecycleReasonCode.EXIT_FAILED,
            ),
            PaperLifecycleStage.EXECUTE_CLOSE: (
                PaperLifecycleCycleOutcome.CLOSE_EXECUTION_STAGE_FAILED,
                PaperLifecycleReasonCode.CLOSE_FAILED,
            ),
        }[stage]

    @staticmethod
    def _stage_transition_valid(
        stage: PaperLifecycleStage,
        before: PaperLifecycleState,
        after: PaperLifecycleState,
        child_outcome: str,
    ) -> bool:
        if after is PaperLifecycleState.INCONSISTENT:
            return False
        allowed = {
            PaperLifecycleStage.INGEST_COMMAND: {
                PaperLifecycleState.ENTRY_ORDER_OPEN,
            },
            PaperLifecycleStage.EXECUTE_ENTRY: {
                PaperLifecycleState.POSITION_OPEN_CURSOR_READY,
            },
            PaperLifecycleStage.EVALUATE_EXIT: {
                PaperLifecycleState.POSITION_OPEN_CURSOR_READY,
                PaperLifecycleState.POSITION_CLOSING_CLOSE_ORDER_OPEN,
            },
            PaperLifecycleStage.EXECUTE_CLOSE: {
                PaperLifecycleState.POSITION_CLOSED,
            },
        }[stage]
        if after not in allowed:
            return False
        if (
            stage is PaperLifecycleStage.EVALUATE_EXIT
            and child_outcome
            in {"NO_EXIT_TRIGGER_CURSOR_ADVANCED", "CURSOR_ALREADY_ADVANCED"}
        ):
            return after is PaperLifecycleState.POSITION_OPEN_CURSOR_READY
        if stage is PaperLifecycleStage.EVALUATE_EXIT:
            return after is PaperLifecycleState.POSITION_CLOSING_CLOSE_ORDER_OPEN
        return before is not after

    @staticmethod
    def _result(
        request: PaperLifecycleCycleRequest,
        initial_graph: PaperLifecycleGraph,
        final_graph: PaperLifecycleGraph,
        outcome: PaperLifecycleCycleOutcome,
        reason_code: str | StrEnum,
        trace: tuple[PaperLifecycleStageTrace, ...],
    ) -> PaperLifecycleCycleResult:
        if len(trace) > MAX_STAGE_TRACE_ITEMS:
            trace = trace[:MAX_STAGE_TRACE_ITEMS]
        initial_state = classify_paper_lifecycle_state(initial_graph)
        final_state = classify_paper_lifecycle_state(final_graph)
        roles = {item.role: item.order for item in final_graph.orders}
        entry_order = roles.get("ENTRY")
        close_order = roles.get("EXIT")
        position = final_graph.positions[0] if len(final_graph.positions) == 1 else None
        cursor = final_graph.cursors[0] if len(final_graph.cursors) == 1 else None
        decision = (
            final_graph.exit_decisions[0]
            if len(final_graph.exit_decisions) == 1
            else None
        )
        entry_fill = (
            next(
                (
                    item
                    for item in final_graph.fills
                    if entry_order is not None and item.order_id == entry_order.order_id
                ),
                None,
            )
        )
        close_fill = (
            next(
                (
                    item
                    for item in final_graph.fills
                    if close_order is not None and item.order_id == close_order.order_id
                ),
                None,
            )
        )
        child_outcomes = tuple(
            item.child_outcome_code
            for item in trace
            if item.child_outcome_code is not None
        )
        child_reasons = tuple(
            item.child_reason_code
            for item in trace
            if item.child_reason_code is not None
        )
        return PaperLifecycleCycleResult(
            cycle_id=request.cycle_id,
            outcome=outcome,
            reason_code=str(
                reason_code.value if isinstance(reason_code, StrEnum) else reason_code
            )[:96],
            initial_lifecycle_state=initial_state,
            final_lifecycle_state=final_state,
            stages_attempted=len(trace),
            stages_completed=sum(item.mutation_committed for item in trace),
            stage_trace=trace,
            child_outcome_codes=child_outcomes,
            child_reason_codes=child_reasons,
            command_id=request.command_id,
            entry_order_id=entry_order.order_id if entry_order else request.entry_order_id,
            entry_fill_id=entry_fill.fill_id if entry_fill else request.entry_fill_id,
            position_id=position.position_id if position else request.position_id,
            position_state=position.state if position else None,
            position_version=position.version if position else None,
            cursor_id=cursor.cursor_id if cursor else request.cursor_id,
            cursor_version=cursor.version if cursor else None,
            cursor_boundary_ms=(
                cursor.last_evaluated_closed_until_ms if cursor else None
            ),
            exit_decision_id=(
                decision.exit_decision_id if decision else request.exit_decision_id
            ),
            close_order_id=(
                close_order.order_id if close_order else request.close_order_id
            ),
            close_fill_id=close_fill.fill_id if close_fill else request.close_fill_id,
            correlation_id=request.correlation_id,
        )


def _matches_optional(expected: str | None, actual: str) -> bool:
    return expected is None or expected == actual


__all__ = (
    "MAX_STAGE_SERVICE_ATTEMPTS",
    "MAX_STAGES_PER_CYCLE",
    "PAPER_LIFECYCLE_CYCLE_CONTRACT_VERSION",
    "PaperControlledLifecycleWorker",
    "PaperLifecycleCancellationAuthority",
    "PaperLifecycleCycleOutcome",
    "PaperLifecycleCycleRequest",
    "PaperLifecycleCycleResult",
    "PaperLifecycleCycleScope",
    "PaperLifecycleFaultPoint",
    "PaperLifecycleGraph",
    "PaperLifecycleOrderNode",
    "PaperLifecycleReasonCode",
    "PaperLifecycleStage",
    "PaperLifecycleStageTrace",
    "PaperLifecycleState",
    "SqlAlchemyPaperLifecycleGraphLoader",
    "classify_paper_lifecycle_state",
)
