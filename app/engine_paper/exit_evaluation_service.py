"""Application service for one explicitly supplied PAPER exit-evaluation request."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Callable, TypeAlias

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.paper_mappings import (
    orm_values_to_paper_event,
    orm_values_to_paper_exit_decision,
    orm_values_to_paper_fill,
    orm_values_to_paper_order,
)
from app.db.paper_models import (
    PaperExitDecisionRecord,
    PaperFillRecord,
    PaperJournalEntryRecord,
    PaperOrderEventRecord,
    PaperOrderRecord,
)
from app.engine_execution.paper_idempotency import (
    exit_decision_idempotency_key,
    order_idempotency_key,
)
from app.engine_execution.paper_models import PaperExecutionCommand, PaperOrder
from app.engine_execution.paper_state_machine import create_paper_order, transition_order
from app.engine_exit.paper_exit import (
    PAPER_INTRABAR_CONFLICT_POLICY,
    PaperExitDecision,
    create_exit_decision,
)
from app.engine_journal.paper_events import PaperDomainEvent
from app.engine_paper.commit_recovery import recover_uncertain_commit
from app.engine_paper.exit_evaluation_cursor import (
    PaperExitCursorAdvance,
    PaperExitCursorOutcome,
    PaperExitEvaluationCursor,
    advanced_cursor,
    paper_exit_cursor_window_identity,
)
from app.engine_paper.exit_evaluator import (
    PaperExitEvaluationOutcome,
    PaperExitEvaluationResult,
    PaperExitTriggerCandidate,
    PaperSafetyExitDirective,
    evaluate_paper_exit_window,
)
from app.engine_paper.fill_causal_boundary import PAPER_FILL_CAUSAL_BOUNDARY_VERSION
from app.engine_paper.fill_policy import (
    PaperFillPriceSource,
    PaperFillSimulationPolicy,
    PaperIntrabarConflictPolicy,
)
from app.engine_paper.fill_roles import PaperFillRole
from app.engine_paper.fill_simulator import PaperFillCandle
from app.engine_paper.order_execution_service import PaperCloseExecutionRequest
from app.engine_paper.repositories import (
    PaperRepositories,
    PaperStoredSimulationPolicy,
)
from app.engine_paper.repository_results import (
    RepositoryOutcome,
    RepositoryResult,
)
from app.engine_paper.semantic_idempotency import (
    exit_semantic_tuple,
    journal_semantic_tuple,
    order_semantic_tuple,
)
from app.engine_paper.unit_of_work import PaperUnitOfWork
from app.engine_position.paper_models import PaperPosition
from app.engine_safety.paper_domain import (
    ExecutionMode,
    PaperDomainError,
    PaperExitCause,
    PaperOrderState,
    PaperPositionState,
    PaperReasonCode,
    require_identity,
    require_nonnegative_int,
    require_utc,
)


_POLICY_VERSION = 1
_TRIGGER_ORDER_EVENTS = 3
_TRIGGER_JOURNAL_ROWS = 4


class PaperExitServiceOutcome(StrEnum):
    NO_EXIT_TRIGGER_CURSOR_ADVANCED = "NO_EXIT_TRIGGER_CURSOR_ADVANCED"
    CURSOR_ALREADY_ADVANCED = "CURSOR_ALREADY_ADVANCED"
    EXIT_PREPARED = "EXIT_PREPARED"
    EXIT_ALREADY_PREPARED = "EXIT_ALREADY_PREPARED"
    UNCERTAIN_COMMIT_RESOLVED_COMMITTED = "UNCERTAIN_COMMIT_RESOLVED_COMMITTED"
    EMPTY_WINDOW = "EMPTY_WINDOW"
    WINDOW_TOO_LARGE = "WINDOW_TOO_LARGE"
    WINDOW_START_MISMATCH = "WINDOW_START_MISMATCH"
    MARKET_DATA_GAP = "MARKET_DATA_GAP"
    DUPLICATE_CANDLE = "DUPLICATE_CANDLE"
    CANDLE_CONFLICT = "CANDLE_CONFLICT"
    FUTURE_DATA_REJECTED = "FUTURE_DATA_REJECTED"
    INVALID_CANDLE = "INVALID_CANDLE"
    SAFETY_DIRECTIVE_INVALID = "SAFETY_DIRECTIVE_INVALID"
    SAFETY_DIRECTIVE_EXPIRED = "SAFETY_DIRECTIVE_EXPIRED"
    MODE_OFF = "MODE_OFF"
    MODE_LIVE_FORBIDDEN = "MODE_LIVE_FORBIDDEN"
    MODE_UNKNOWN = "MODE_UNKNOWN"
    PAPER_AUTHORIZATION_MISSING = "PAPER_AUTHORIZATION_MISSING"
    POSITION_NOT_FOUND = "POSITION_NOT_FOUND"
    CURSOR_NOT_FOUND = "CURSOR_NOT_FOUND"
    COMMAND_NOT_FOUND = "COMMAND_NOT_FOUND"
    ENTRY_ORDER_NOT_FOUND = "ENTRY_ORDER_NOT_FOUND"
    ENTRY_FILL_NOT_FOUND = "ENTRY_FILL_NOT_FOUND"
    INVALID_POSITION_STATE = "INVALID_POSITION_STATE"
    STALE_POSITION_VERSION = "STALE_POSITION_VERSION"
    STALE_CURSOR_VERSION = "STALE_CURSOR_VERSION"
    SOURCE_GRAPH_INCONSISTENT = "SOURCE_GRAPH_INCONSISTENT"
    SYMBOL_MISMATCH = "SYMBOL_MISMATCH"
    SIDE_MISMATCH = "SIDE_MISMATCH"
    QUANTITY_MISMATCH = "QUANTITY_MISMATCH"
    INVALID_STOP_TARGET = "INVALID_STOP_TARGET"
    POLICY_MISMATCH = "POLICY_MISMATCH"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    EXISTING_EXIT_GRAPH_INCONSISTENT = "EXISTING_EXIT_GRAPH_INCONSISTENT"
    CURSOR_REGRESSION_REJECTED = "CURSOR_REGRESSION_REJECTED"
    CURSOR_GAP_REJECTED = "CURSOR_GAP_REJECTED"
    CONSTRAINT_VIOLATION = "CONSTRAINT_VIOLATION"
    TRANSIENT_DB_FAILURE = "TRANSIENT_DB_FAILURE"
    UNCERTAIN_COMMIT_RESOLVED_NOT_COMMITTED = (
        "UNCERTAIN_COMMIT_RESOLVED_NOT_COMMITTED"
    )
    UNCERTAIN_COMMIT_UNRESOLVED = "UNCERTAIN_COMMIT_UNRESOLVED"
    INTERNAL_INVARIANT_FAILURE = "INTERNAL_INVARIANT_FAILURE"


@dataclass(frozen=True, slots=True)
class PaperExitEvaluationRequest:
    position_id: str
    expected_position_version: int
    cursor_id: str
    expected_cursor_version: int
    expected_cursor_from_closed_until_ms: int
    source_command_id: str
    entry_order_id: str
    entry_fill_id: str
    candles: tuple[PaperFillCandle, ...]
    market_snapshot_closed_until_ms: int
    safety_directive: PaperSafetyExitDirective | None
    evaluation_policy_id: str
    execution_mode: object
    explicit_paper_authorization: bool
    exit_decision_id: str
    close_order_id: str
    exit_event_id: str
    close_order_created_event_id: str
    close_order_validated_event_id: str
    close_order_opened_event_id: str
    journal_entry_ids: tuple[str, str, str, str]
    close_execution_fill_id: str
    close_execution_order_event_id: str
    close_execution_position_event_id: str
    close_execution_journal_entry_ids: tuple[str, str]
    price_quantum: Decimal
    fee_quantum: Decimal
    quote_asset: str
    created_at: datetime
    correlation_id: str
    causation_id: str

    def __post_init__(self) -> None:
        for name in (
            "position_id",
            "cursor_id",
            "source_command_id",
            "entry_order_id",
            "entry_fill_id",
            "evaluation_policy_id",
            "exit_decision_id",
            "close_order_id",
            "exit_event_id",
            "close_order_created_event_id",
            "close_order_validated_event_id",
            "close_order_opened_event_id",
            "close_execution_fill_id",
            "close_execution_order_event_id",
            "close_execution_position_event_id",
            "quote_asset",
            "correlation_id",
            "causation_id",
        ):
            object.__setattr__(
                self, name, require_identity(getattr(self, name), name)
            )
        for name in (
            "expected_position_version",
            "expected_cursor_version",
            "expected_cursor_from_closed_until_ms",
            "market_snapshot_closed_until_ms",
        ):
            require_nonnegative_int(getattr(self, name), name)
        if not isinstance(self.candles, tuple):
            raise TypeError("candles must be an immutable tuple")
        if not isinstance(self.journal_entry_ids, tuple) or len(
            self.journal_entry_ids
        ) != _TRIGGER_JOURNAL_ROWS:
            raise ValueError("exactly four trigger journal IDs are required")
        trigger_event_ids = (
            self.close_order_created_event_id,
            self.close_order_validated_event_id,
            self.close_order_opened_event_id,
            self.exit_event_id,
        )
        normalized_journal = tuple(
            require_identity(value, f"journal_entry_ids[{index}]")
            for index, value in enumerate(self.journal_entry_ids)
        )
        if normalized_journal != trigger_event_ids:
            raise ValueError("trigger journal IDs must match canonical event IDs")
        object.__setattr__(self, "journal_entry_ids", normalized_journal)
        if not isinstance(self.close_execution_journal_entry_ids, tuple) or len(
            self.close_execution_journal_entry_ids
        ) != 2:
            raise ValueError("exactly two close-execution journal IDs are required")
        close_journal = tuple(
            require_identity(
                value, f"close_execution_journal_entry_ids[{index}]"
            )
            for index, value in enumerate(
                self.close_execution_journal_entry_ids
            )
        )
        if len(set(close_journal)) != 2:
            raise ValueError("close-execution journal IDs must be unique")
        object.__setattr__(
            self, "close_execution_journal_entry_ids", close_journal
        )
        try:
            require_utc(self.created_at, "created_at")
        except PaperDomainError as exc:
            raise ValueError("created_at must be UTC") from exc


@dataclass(frozen=True, slots=True)
class PaperExitServiceResult:
    outcome: PaperExitServiceOutcome
    reason_code: str
    position_id: str
    cursor_id: str
    cursor_boundary_ms: int | None = None
    cursor_version: int | None = None
    position_state: PaperPositionState | None = None
    position_version: int | None = None
    exit_decision_id: str | None = None
    close_order_id: str | None = None
    close_order_state: PaperOrderState | None = None
    trigger: PaperExitTriggerCandidate | None = None
    repository_outcome: RepositoryOutcome | None = None
    event_count: int = 0
    journal_count: int = 0
    close_execution_request: PaperCloseExecutionRequest | None = None

    @property
    def successful(self) -> bool:
        return self.outcome in {
            PaperExitServiceOutcome.NO_EXIT_TRIGGER_CURSOR_ADVANCED,
            PaperExitServiceOutcome.CURSOR_ALREADY_ADVANCED,
            PaperExitServiceOutcome.EXIT_PREPARED,
            PaperExitServiceOutcome.EXIT_ALREADY_PREPARED,
            PaperExitServiceOutcome.UNCERTAIN_COMMIT_RESOLVED_COMMITTED,
        }


@dataclass(frozen=True, slots=True)
class _LoadedGraph:
    position: PaperPosition
    cursor: PaperExitEvaluationCursor
    command: PaperExecutionCommand
    entry_order: PaperOrder
    entry_fill: object
    policy: PaperStoredSimulationPolicy


@dataclass(frozen=True, slots=True)
class _ExpectedTrigger:
    advance: PaperExitCursorAdvance
    decision: PaperExitDecision
    close_order: PaperOrder
    exit_event: PaperDomainEvent
    order_events: tuple[PaperDomainEvent, PaperDomainEvent, PaperDomainEvent]
    changed_cursor: PaperExitEvaluationCursor
    close_execution_request: PaperCloseExecutionRequest
    trigger: PaperExitTriggerCandidate


@dataclass(frozen=True, slots=True)
class _RecoveryProbe:
    classification: str
    cursor: PaperExitEvaluationCursor | None = None


UowFactory: TypeAlias = Callable[[], PaperUnitOfWork]
SessionFactory: TypeAlias = Callable[[], Session]


_EVALUATOR_MAP = {
    value: PaperExitServiceOutcome(value.value)
    for value in PaperExitEvaluationOutcome
    if value.value in PaperExitServiceOutcome._value2member_map_
}


class PaperExitEvaluationService:
    """Evaluate and persist exactly one explicit PAPER position window."""

    def __init__(
        self,
        uow_factory: UowFactory,
        recovery_session_factory: SessionFactory,
    ) -> None:
        self._uow_factory = uow_factory
        self._recovery_session_factory = recovery_session_factory

    def evaluate(
        self, request: PaperExitEvaluationRequest
    ) -> PaperExitServiceResult:
        if not isinstance(request, PaperExitEvaluationRequest):
            raise TypeError("request must be PaperExitEvaluationRequest")
        authorization = self._validate_authorization(request)
        if authorization is not None:
            return authorization
        uncertain_kind: str | None = None
        uncertain_expected: object | None = None
        try:
            with self._uow_factory() as uow:
                repositories = self._repositories(uow)
                loaded_or_failure = self._load_and_validate(
                    request, repositories, uow.session
                )
                if isinstance(loaded_or_failure, PaperExitServiceResult):
                    return loaded_or_failure
                loaded = loaded_or_failure
                evaluation = evaluate_paper_exit_window(
                    position_id=request.position_id,
                    cursor_id=request.cursor_id,
                    expected_position_version=request.expected_position_version,
                    expected_cursor_version=request.expected_cursor_version,
                    cursor_closed_until_ms=(
                        request.expected_cursor_from_closed_until_ms
                    ),
                    candles=request.candles,
                    market_snapshot_closed_until_ms=(
                        request.market_snapshot_closed_until_ms
                    ),
                    safety_directive=request.safety_directive,
                    source_command_id=loaded.command.command_id,
                    entry_fill_id=loaded.position.entry_fill_id,
                    symbol=loaded.position.symbol,
                    side=loaded.position.side,
                    remaining_quantity=loaded.position.remaining_quantity,
                    stop_price=loaded.position.stop_price,
                    target_price=loaded.position.target_price,
                    evaluation_policy_id=request.evaluation_policy_id,
                    correlation_id=request.correlation_id,
                    causation_id=request.causation_id,
                )
                if not evaluation.successful:
                    return self._evaluation_failure(request, evaluation)
                advance = self._build_advance(request, evaluation)
                if evaluation.outcome is PaperExitEvaluationOutcome.NO_EXIT_TRIGGER:
                    replay = self._classify_no_trigger_existing(
                        request, loaded, advance, uow.session
                    )
                    if replay is not None:
                        return replay
                    cursor_result = repositories.exit_cursors.advance_cursor(advance)
                    if cursor_result.outcome not in {
                        PaperExitCursorOutcome.CURSOR_ADVANCED,
                        PaperExitCursorOutcome.CURSOR_ALREADY_ADVANCED,
                    }:
                        return self._cursor_failure(request, cursor_result.outcome)
                    changed = cursor_result.cursor
                    if changed is None:
                        return self._failure(
                            request,
                            PaperExitServiceOutcome.INTERNAL_INVARIANT_FAILURE,
                        )
                    if self._has_exit_graph(request, uow.session):
                        return self._failure(
                            request,
                            PaperExitServiceOutcome.EXISTING_EXIT_GRAPH_INCONSISTENT,
                        )
                    commit = uow.commit()
                    if commit.outcome is RepositoryOutcome.UPDATED:
                        outcome = (
                            PaperExitServiceOutcome.CURSOR_ALREADY_ADVANCED
                            if cursor_result.outcome
                            is PaperExitCursorOutcome.CURSOR_ALREADY_ADVANCED
                            else PaperExitServiceOutcome.NO_EXIT_TRIGGER_CURSOR_ADVANCED
                        )
                        return self._no_trigger_success(
                            request, loaded.position, changed, outcome
                        )
                    if commit.outcome is RepositoryOutcome.UNCERTAIN_COMMIT_UNRESOLVED:
                        uncertain_kind = "NO_TRIGGER"
                        uncertain_expected = changed
                    else:
                        return self._repository_failure(request, commit)
                else:
                    assert evaluation.trigger is not None
                    expected = self._build_expected_trigger(
                        request, loaded, evaluation, advance
                    )
                    classification = self._classify_trigger_graph(
                        request, expected, uow.session
                    )
                    if classification == "MATCH":
                        return self._trigger_success(
                            request,
                            expected,
                            PaperExitServiceOutcome.EXIT_ALREADY_PREPARED,
                            RepositoryOutcome.EXISTING_IDEMPOTENT,
                        )
                    if classification == "PARTIAL":
                        return self._failure(
                            request,
                            PaperExitServiceOutcome.EXISTING_EXIT_GRAPH_INCONSISTENT,
                        )
                    if classification == "CONFLICT":
                        return self._failure(
                            request,
                            PaperExitServiceOutcome.IDEMPOTENCY_CONFLICT,
                        )
                    repository_result = (
                        repositories.apply_exit_trigger_and_open_close_order(
                            expected.advance,
                            expected.decision,
                            expected.close_order,
                            expected.exit_event,
                            expected.order_events,
                        )
                    )
                    if repository_result.outcome is RepositoryOutcome.EXISTING_IDEMPOTENT:
                        classification = self._classify_trigger_graph(
                            request, expected, uow.session
                        )
                        if classification != "MATCH":
                            return self._failure(
                                request,
                                PaperExitServiceOutcome.EXISTING_EXIT_GRAPH_INCONSISTENT,
                            )
                        return self._trigger_success(
                            request,
                            expected,
                            PaperExitServiceOutcome.EXIT_ALREADY_PREPARED,
                            repository_result.outcome,
                        )
                    if repository_result.outcome is not RepositoryOutcome.CREATED:
                        return self._repository_failure(
                            request, repository_result
                        )
                    if (
                        self._classify_trigger_graph(
                            request, expected, uow.session
                        )
                        != "MATCH"
                    ):
                        return self._failure(
                            request,
                            PaperExitServiceOutcome.EXISTING_EXIT_GRAPH_INCONSISTENT,
                        )
                    commit = uow.commit()
                    if commit.outcome is RepositoryOutcome.UPDATED:
                        return self._trigger_success(
                            request,
                            expected,
                            PaperExitServiceOutcome.EXIT_PREPARED,
                            RepositoryOutcome.CREATED,
                        )
                    if commit.outcome is RepositoryOutcome.UNCERTAIN_COMMIT_UNRESOLVED:
                        uncertain_kind = "TRIGGER"
                        uncertain_expected = expected
                    else:
                        return self._repository_failure(request, commit)
        except PaperDomainError:
            return self._failure(
                request, PaperExitServiceOutcome.SOURCE_GRAPH_INCONSISTENT
            )
        except Exception:
            return self._failure(
                request, PaperExitServiceOutcome.INTERNAL_INVARIANT_FAILURE
            )
        if uncertain_kind == "NO_TRIGGER":
            assert isinstance(uncertain_expected, PaperExitEvaluationCursor)
            return self._recover_no_trigger(request, uncertain_expected)
        if uncertain_kind == "TRIGGER":
            assert isinstance(uncertain_expected, _ExpectedTrigger)
            return self._recover_trigger(request, uncertain_expected)
        return self._failure(
            request, PaperExitServiceOutcome.INTERNAL_INVARIANT_FAILURE
        )

    @staticmethod
    def _validate_authorization(
        request: PaperExitEvaluationRequest,
    ) -> PaperExitServiceResult | None:
        try:
            mode = ExecutionMode(request.execution_mode)
        except (TypeError, ValueError):
            return PaperExitEvaluationService._failure(
                request, PaperExitServiceOutcome.MODE_UNKNOWN
            )
        if mode is ExecutionMode.OFF:
            return PaperExitEvaluationService._failure(
                request, PaperExitServiceOutcome.MODE_OFF
            )
        if mode is ExecutionMode.LIVE:
            return PaperExitEvaluationService._failure(
                request, PaperExitServiceOutcome.MODE_LIVE_FORBIDDEN
            )
        if request.explicit_paper_authorization is not True:
            return PaperExitEvaluationService._failure(
                request, PaperExitServiceOutcome.PAPER_AUTHORIZATION_MISSING
            )
        return None

    def _load_and_validate(
        self,
        request: PaperExitEvaluationRequest,
        repositories: PaperRepositories,
        session: Session | None,
    ) -> _LoadedGraph | PaperExitServiceResult:
        if session is None:
            return self._failure(
                request, PaperExitServiceOutcome.INTERNAL_INVARIANT_FAILURE
            )
        position = repositories.positions.get_position(request.position_id)
        if position is None:
            return self._failure(request, PaperExitServiceOutcome.POSITION_NOT_FOUND)
        cursor = repositories.exit_cursors.get_cursor_bounded(request.position_id)
        if cursor is None or cursor.cursor_id != request.cursor_id:
            return self._failure(request, PaperExitServiceOutcome.CURSOR_NOT_FOUND)
        entry_order = repositories.orders.get_order(request.entry_order_id)
        if entry_order is None:
            return self._failure(
                request, PaperExitServiceOutcome.ENTRY_ORDER_NOT_FOUND
            )
        command = repositories.commands.get_command(request.source_command_id)
        if command is None:
            return self._failure(request, PaperExitServiceOutcome.COMMAND_NOT_FOUND)
        fill_row = session.get(PaperFillRecord, request.entry_fill_id)
        if fill_row is None:
            return self._failure(
                request, PaperExitServiceOutcome.ENTRY_FILL_NOT_FOUND
            )
        entry_fill = orm_values_to_paper_fill(fill_row)
        policy = repositories.policies.get_policy(
            command.simulation_policy_id, policy_version=_POLICY_VERSION
        )
        if policy is None:
            return self._failure(request, PaperExitServiceOutcome.POLICY_MISMATCH)

        replay_candidate = (
            position.state is PaperPositionState.CLOSING
            and position.version == request.expected_position_version + 1
        )
        if position.state is not PaperPositionState.OPEN and not replay_candidate:
            return self._failure(
                request, PaperExitServiceOutcome.INVALID_POSITION_STATE
            )
        if (
            position.state is PaperPositionState.OPEN
            and position.version != request.expected_position_version
        ):
            return self._failure(
                request, PaperExitServiceOutcome.STALE_POSITION_VERSION
            )
        cursor_replay_candidate = (
            cursor.version == request.expected_cursor_version + 1
            and cursor.last_advance_expected_version
            == request.expected_cursor_version
            and cursor.last_advance_from_closed_until_ms
            == request.expected_cursor_from_closed_until_ms
        )
        if (
            cursor.version != request.expected_cursor_version
            and not cursor_replay_candidate
        ):
            return self._failure(
                request, PaperExitServiceOutcome.STALE_CURSOR_VERSION
            )
        if (
            cursor.version == request.expected_cursor_version
            and cursor.last_evaluated_closed_until_ms
            != request.expected_cursor_from_closed_until_ms
        ):
            outcome = (
                PaperExitServiceOutcome.CURSOR_REGRESSION_REJECTED
                if request.expected_cursor_from_closed_until_ms
                < cursor.last_evaluated_closed_until_ms
                else PaperExitServiceOutcome.CURSOR_GAP_REJECTED
            )
            return self._failure(request, outcome)
        if (
            cursor.position_id != position.position_id
            or cursor.mode is not ExecutionMode.PAPER
            or command.mode is not ExecutionMode.PAPER
            or position.mode is not ExecutionMode.PAPER
            or cursor.evaluation_policy_id != request.evaluation_policy_id
        ):
            return self._failure(request, PaperExitServiceOutcome.POLICY_MISMATCH)
        if (
            command.symbol != position.symbol
            or entry_order.symbol != position.symbol
            or entry_fill.symbol != position.symbol
            or cursor.symbol != position.symbol
        ):
            return self._failure(request, PaperExitServiceOutcome.SYMBOL_MISMATCH)
        if (
            command.side is not position.side
            or entry_order.side is not position.side
            or entry_fill.side is not position.side
        ):
            return self._failure(request, PaperExitServiceOutcome.SIDE_MISMATCH)
        if (
            entry_order.order_id != position.entry_order_id
            or entry_order.command_id != command.command_id
            or entry_order.state is not PaperOrderState.FILLED
            or entry_order.applied_fill_id != entry_fill.fill_id
            or entry_fill.order_id != entry_order.order_id
            or entry_fill.fill_id != position.entry_fill_id
            or command.command_id != request.source_command_id
            or entry_order.order_id != request.entry_order_id
            or entry_fill.fill_id != request.entry_fill_id
        ):
            return self._failure(
                request, PaperExitServiceOutcome.SOURCE_GRAPH_INCONSISTENT
            )
        if (
            command.requested_quantity != entry_fill.quantity
            or position.entry_quantity != entry_fill.quantity
            or position.remaining_quantity <= 0
            or position.remaining_quantity != position.entry_quantity
        ):
            return self._failure(request, PaperExitServiceOutcome.QUANTITY_MISMATCH)
        if position.side.value == "LONG":
            geometry = (
                position.stop_price
                < position.average_entry_price
                < position.target_price
            )
        else:
            geometry = (
                position.target_price
                < position.average_entry_price
                < position.stop_price
            )
        if not geometry:
            return self._failure(
                request, PaperExitServiceOutcome.INVALID_STOP_TARGET
            )
        if (
            policy.status != "ACTIVE"
            or policy.retired_at is not None
            or policy.policy_id != command.simulation_policy_id
            or policy.timeframe != "1m"
            or policy.intrabar_conflict_policy
            != PAPER_INTRABAR_CONFLICT_POLICY
            or policy.partial_fill_enabled
            or policy.future_data_allowed
        ):
            return self._failure(request, PaperExitServiceOutcome.POLICY_MISMATCH)
        return _LoadedGraph(
            position, cursor, command, entry_order, entry_fill, policy
        )

    @staticmethod
    def _build_advance(
        request: PaperExitEvaluationRequest,
        evaluation: PaperExitEvaluationResult,
    ) -> PaperExitCursorAdvance:
        boundaries = evaluation.evaluated_close_boundaries_ms
        end = boundaries[-1]
        identity = paper_exit_cursor_window_identity(
            position_id=request.position_id,
            expected_version=request.expected_cursor_version,
            from_boundary_ms=request.expected_cursor_from_closed_until_ms,
            to_boundary_ms=end,
            evaluation_policy_id=request.evaluation_policy_id,
            evaluated_close_boundaries_ms=boundaries,
        )
        return PaperExitCursorAdvance(
            position_id=request.position_id,
            expected_version=request.expected_cursor_version,
            from_closed_until_ms=request.expected_cursor_from_closed_until_ms,
            to_closed_until_ms=end,
            evaluation_policy_id=request.evaluation_policy_id,
            evaluated_close_boundaries_ms=boundaries,
            idempotency_key=identity,
            window_identity=identity,
            advanced_at=request.created_at,
            correlation_id=request.correlation_id,
            causation_id=request.causation_id,
        )

    def _build_expected_trigger(
        self,
        request: PaperExitEvaluationRequest,
        loaded: _LoadedGraph,
        evaluation: PaperExitEvaluationResult,
        advance: PaperExitCursorAdvance,
    ) -> _ExpectedTrigger:
        trigger = evaluation.trigger
        assert trigger is not None
        base_position = loaded.position
        if base_position.state is PaperPositionState.CLOSING:
            base_position = replace(
                base_position,
                state=PaperPositionState.OPEN,
                version=request.expected_position_version,
                reason_code=PaperReasonCode.PAPER_POSITION_OPENED,
            )
        candle = next(
            item
            for item in request.candles
            if item.close_boundary_ms
            == trigger.trigger_source_closed_until_ms
        )
        if trigger.cause is PaperExitCause.STOP_LOSS:
            decision_price = base_position.stop_price
            reason = (
                PaperReasonCode.PAPER_EXIT_STOP_FIRST_CONFLICT
                if trigger.stop_hit and trigger.target_hit
                else PaperReasonCode.PAPER_EXIT_STOP_LOSS_TRIGGERED
            )
        elif trigger.cause is PaperExitCause.TAKE_PROFIT:
            decision_price = base_position.target_price
            reason = PaperReasonCode.PAPER_EXIT_TAKE_PROFIT_TRIGGERED
        elif trigger.cause is PaperExitCause.OPERATOR_RECOVERY_CLOSE:
            decision_price = candle.close_price
            reason = (
                PaperReasonCode.PAPER_EXIT_OPERATOR_RECOVERY_CLOSE_AFTER_MISSED_STOP
            )
        else:
            decision_price = candle.close_price
            reason = PaperReasonCode.PAPER_EXIT_SYSTEM_SAFETY_TRIGGERED
        decision, exit_event = create_exit_decision(
            base_position,
            exit_decision_id=request.exit_decision_id,
            idempotency_key=exit_decision_idempotency_key(
                base_position.position_id,
                request.expected_position_version,
                trigger.cause,
            ),
            expected_position_version=request.expected_position_version,
            cause=trigger.cause,
            decision_price=decision_price,
            source_closed_until_ms=trigger.trigger_source_closed_until_ms,
            decided_at=request.created_at,
            reason_code=reason,
            event_id=request.exit_event_id,
            future_bars_used=False,
        )
        created = create_paper_order(
            loaded.command,
            order_id=request.close_order_id,
            idempotency_key=order_idempotency_key(
                loaded.command.command_id, "EXIT"
            ),
            occurred_at=request.created_at,
            event_id=request.close_order_created_event_id,
        )
        validated = transition_order(
            created.order,
            PaperOrderState.VALIDATED,
            expected_version=0,
            occurred_at=request.created_at,
            event_id=request.close_order_validated_event_id,
        )
        opened = transition_order(
            validated.order,
            PaperOrderState.OPEN,
            expected_version=1,
            occurred_at=request.created_at,
            event_id=request.close_order_opened_event_id,
        )
        policy = self._execution_policy(request, loaded)
        close_execution = PaperCloseExecutionRequest(
            command_id=loaded.command.command_id,
            order_id=request.close_order_id,
            expected_order_version=2,
            fill_role=PaperFillRole.CLOSE,
            candidate_candles=(),
            market_snapshot_closed_until_ms=(
                trigger.trigger_source_closed_until_ms
            ),
            simulation_policy=policy,
            price_quantum=request.price_quantum,
            fee_quantum=request.fee_quantum,
            quote_asset=request.quote_asset,
            fill_id=request.close_execution_fill_id,
            order_event_id=request.close_execution_order_event_id,
            position_event_id=request.close_execution_position_event_id,
            journal_entry_ids=request.close_execution_journal_entry_ids,
            correlation_id=request.correlation_id,
            causation_id=request.causation_id,
            operation_at=request.created_at,
            position_id=request.position_id,
            expected_position_version=request.expected_position_version + 1,
            exit_decision_id=request.exit_decision_id,
        )
        return _ExpectedTrigger(
            advance,
            decision,
            opened.order,
            exit_event,
            (created.events[0], validated.events[0], opened.events[0]),
            advanced_cursor(
                replace(
                    loaded.cursor,
                    version=request.expected_cursor_version,
                    last_evaluated_closed_until_ms=(
                        request.expected_cursor_from_closed_until_ms
                    ),
                    last_advance_idempotency_key=None,
                    last_advance_from_closed_until_ms=None,
                    last_advance_to_closed_until_ms=None,
                    last_advance_expected_version=None,
                    last_window_identity=None,
                ),
                advance,
            ),
            close_execution,
            trigger,
        )

    @staticmethod
    def _execution_policy(
        request: PaperExitEvaluationRequest,
        loaded: _LoadedGraph,
    ) -> PaperFillSimulationPolicy:
        stored = loaded.policy
        command = loaded.command
        return PaperFillSimulationPolicy(
            simulation_policy_id=stored.policy_id,
            fee_policy_id=command.fee_policy_id,
            slippage_policy_id=command.slippage_policy_id,
            latency_policy_id=command.latency_policy_id,
            price_source=PaperFillPriceSource(stored.price_source),
            timeframe=stored.timeframe,
            latency_candles=stored.latency_candles,
            slippage_bps=stored.slippage_bps,
            fee_bps=stored.fee_bps,
            partial_fill_enabled=stored.partial_fill_enabled,
            future_data_allowed=stored.future_data_allowed,
            intrabar_conflict_policy=PaperIntrabarConflictPolicy(
                stored.intrabar_conflict_policy
            ),
            price_quantum=request.price_quantum,
            fee_quantum=request.fee_quantum,
            contract_version=PAPER_FILL_CAUSAL_BOUNDARY_VERSION,
        )

    def _classify_no_trigger_existing(
        self,
        request: PaperExitEvaluationRequest,
        loaded: _LoadedGraph,
        advance: PaperExitCursorAdvance,
        session: Session,
    ) -> PaperExitServiceResult | None:
        cursor = loaded.cursor
        if cursor.last_advance_idempotency_key != advance.idempotency_key:
            return None
        exact = (
            cursor.last_advance_expected_version == advance.expected_version
            and cursor.last_advance_from_closed_until_ms
            == advance.from_closed_until_ms
            and cursor.last_advance_to_closed_until_ms
            == advance.to_closed_until_ms
            and cursor.last_window_identity == advance.window_identity
            and cursor.version == advance.expected_version + 1
        )
        if not exact:
            return self._failure(
                request, PaperExitServiceOutcome.IDEMPOTENCY_CONFLICT
            )
        if self._has_exit_graph(request, session):
            return self._failure(
                request,
                PaperExitServiceOutcome.EXISTING_EXIT_GRAPH_INCONSISTENT,
            )
        if loaded.position.state is not PaperPositionState.OPEN:
            return self._failure(
                request,
                PaperExitServiceOutcome.EXISTING_EXIT_GRAPH_INCONSISTENT,
            )
        return self._no_trigger_success(
            request,
            loaded.position,
            cursor,
            PaperExitServiceOutcome.CURSOR_ALREADY_ADVANCED,
        )

    @staticmethod
    def _has_exit_graph(
        request: PaperExitEvaluationRequest, session: Session
    ) -> bool:
        decision = session.scalar(
            select(PaperExitDecisionRecord)
            .where(PaperExitDecisionRecord.position_id == request.position_id)
            .limit(1)
        )
        order = session.get(PaperOrderRecord, request.close_order_id)
        return decision is not None or order is not None

    @staticmethod
    def _classify_trigger_graph(
        request: PaperExitEvaluationRequest,
        expected: _ExpectedTrigger,
        session: Session,
    ) -> str:
        cursor = PaperRepositories(session).exit_cursors.get_cursor_bounded(
            request.position_id
        )
        position = PaperRepositories(session).positions.get_position(
            request.position_id
        )
        decision_row = session.get(
            PaperExitDecisionRecord, request.exit_decision_id
        )
        order_row = session.get(PaperOrderRecord, request.close_order_id)
        components = (cursor, position, decision_row, order_row)
        if all(value is None for value in (decision_row, order_row)):
            if (
                cursor is not None
                and cursor.last_advance_idempotency_key
                == expected.advance.idempotency_key
            ) or (
                position is not None
                and position.state is PaperPositionState.CLOSING
            ):
                return "PARTIAL"
            return "ABSENT"
        if decision_row is None or order_row is None or cursor is None or position is None:
            return "PARTIAL"
        decision = orm_values_to_paper_exit_decision(decision_row)
        order = orm_values_to_paper_order(order_row)
        if (
            exit_semantic_tuple(decision)
            != exit_semantic_tuple(expected.decision)
            or order_semantic_tuple(order)
            != order_semantic_tuple(expected.close_order)
        ):
            return "CONFLICT"
        if (
            cursor != expected.changed_cursor
            or position.state is not PaperPositionState.CLOSING
            or position.version != request.expected_position_version + 1
            or order_row.order_role != "EXIT"
        ):
            return "PARTIAL"
        event_rows = tuple(
            session.scalars(
                select(PaperOrderEventRecord)
                .where(PaperOrderEventRecord.order_id == request.close_order_id)
                .order_by(PaperOrderEventRecord.aggregate_version)
            )
        )
        journal_rows = tuple(
            session.scalars(
                select(PaperJournalEntryRecord).where(
                    PaperJournalEntryRecord.journal_entry_id.in_(
                        request.journal_entry_ids
                    )
                )
            )
        )
        if len(event_rows) != _TRIGGER_ORDER_EVENTS or len(
            journal_rows
        ) != _TRIGGER_JOURNAL_ROWS:
            return "PARTIAL"
        if any(
            (
                row.order_event_id,
                row.event_type,
                row.aggregate_version,
                row.correlation_id,
                row.causation_id,
                row.reason_code,
                row.occurred_at,
            )
            != (
                event.event_id,
                event.event_type.value,
                event.aggregate_version,
                event.correlation_id,
                event.causation_id,
                event.reason_code.value,
                event.occurred_at,
            )
            for row, event in zip(event_rows, expected.order_events)
        ):
            return "PARTIAL"
        expected_journal = (*expected.order_events, expected.exit_event)
        actual_journal = tuple(map(orm_values_to_paper_event, journal_rows))
        if sorted(map(journal_semantic_tuple, actual_journal), key=repr) != sorted(
            map(journal_semantic_tuple, expected_journal), key=repr
        ):
            return "PARTIAL"
        return "MATCH"

    def _recover_no_trigger(
        self,
        request: PaperExitEvaluationRequest,
        expected_cursor: PaperExitEvaluationCursor,
    ) -> PaperExitServiceResult:
        expected_probe = _RecoveryProbe("MATCH", expected_cursor)
        recovery = recover_uncertain_commit(
            self._recovery_session_factory,
            lambda session: self._probe_no_trigger(
                session, request, expected_cursor
            ),
            expected_probe,
            lambda found, _: found.classification == "MATCH",
            attempts=3,
        )
        if recovery.outcome is RepositoryOutcome.UNCERTAIN_COMMIT_RESOLVED_COMMITTED:
            return PaperExitServiceResult(
                PaperExitServiceOutcome.UNCERTAIN_COMMIT_RESOLVED_COMMITTED,
                "PAPER_EXIT_UNCERTAIN_COMMIT_RESOLVED_COMMITTED",
                request.position_id,
                request.cursor_id,
                expected_cursor.last_evaluated_closed_until_ms,
                expected_cursor.version,
                PaperPositionState.OPEN,
                request.expected_position_version,
                repository_outcome=recovery.outcome,
            )
        if (
            recovery.outcome is RepositoryOutcome.IDEMPOTENCY_CONFLICT
            and recovery.value is not None
            and recovery.value.classification == "PARTIAL"
        ):
            return self._failure(
                request,
                PaperExitServiceOutcome.EXISTING_EXIT_GRAPH_INCONSISTENT,
                recovery.outcome,
            )
        return self._repository_failure(request, recovery)

    @staticmethod
    def _probe_no_trigger(
        session: Session,
        request: PaperExitEvaluationRequest,
        expected_cursor: PaperExitEvaluationCursor,
    ) -> _RecoveryProbe | None:
        repositories = PaperRepositories(session)
        cursor = repositories.exit_cursors.get_cursor_bounded(request.position_id)
        position = repositories.positions.get_position(request.position_id)
        if cursor is None:
            return None
        if (
            cursor == expected_cursor
            and position is not None
            and position.state is PaperPositionState.OPEN
            and not PaperExitEvaluationService._has_exit_graph(request, session)
        ):
            return _RecoveryProbe("MATCH", cursor)
        return _RecoveryProbe("PARTIAL", cursor)

    def _recover_trigger(
        self,
        request: PaperExitEvaluationRequest,
        expected: _ExpectedTrigger,
    ) -> PaperExitServiceResult:
        expected_probe = _RecoveryProbe("MATCH", expected.changed_cursor)
        recovery = recover_uncertain_commit(
            self._recovery_session_factory,
            lambda session: self._probe_trigger(session, request, expected),
            expected_probe,
            lambda found, _: found.classification == "MATCH",
            attempts=3,
        )
        if recovery.outcome is RepositoryOutcome.UNCERTAIN_COMMIT_RESOLVED_COMMITTED:
            return self._trigger_success(
                request,
                expected,
                PaperExitServiceOutcome.UNCERTAIN_COMMIT_RESOLVED_COMMITTED,
                recovery.outcome,
            )
        if recovery.value is not None and recovery.value.classification == "PARTIAL":
            return self._failure(
                request,
                PaperExitServiceOutcome.EXISTING_EXIT_GRAPH_INCONSISTENT,
                recovery.outcome,
            )
        return self._repository_failure(request, recovery)

    @staticmethod
    def _probe_trigger(
        session: Session,
        request: PaperExitEvaluationRequest,
        expected: _ExpectedTrigger,
    ) -> _RecoveryProbe | None:
        classification = PaperExitEvaluationService._classify_trigger_graph(
            request, expected, session
        )
        if classification == "ABSENT":
            return None
        return _RecoveryProbe(classification, expected.changed_cursor)

    @staticmethod
    def _evaluation_failure(
        request: PaperExitEvaluationRequest,
        evaluation: PaperExitEvaluationResult,
    ) -> PaperExitServiceResult:
        outcome = _EVALUATOR_MAP.get(
            evaluation.outcome,
            PaperExitServiceOutcome.INTERNAL_INVARIANT_FAILURE,
        )
        return PaperExitEvaluationService._failure(
            request, outcome, reason=evaluation.reason_code
        )

    @staticmethod
    def _cursor_failure(
        request: PaperExitEvaluationRequest,
        outcome: PaperExitCursorOutcome,
    ) -> PaperExitServiceResult:
        mapped = {
            PaperExitCursorOutcome.CURSOR_NOT_FOUND:
                PaperExitServiceOutcome.CURSOR_NOT_FOUND,
            PaperExitCursorOutcome.CURSOR_STALE_VERSION:
                PaperExitServiceOutcome.STALE_CURSOR_VERSION,
            PaperExitCursorOutcome.CURSOR_REGRESSION_REJECTED:
                PaperExitServiceOutcome.CURSOR_REGRESSION_REJECTED,
            PaperExitCursorOutcome.CURSOR_GAP_REJECTED:
                PaperExitServiceOutcome.CURSOR_GAP_REJECTED,
            PaperExitCursorOutcome.CURSOR_IDEMPOTENCY_CONFLICT:
                PaperExitServiceOutcome.IDEMPOTENCY_CONFLICT,
            PaperExitCursorOutcome.SOURCE_GRAPH_INCONSISTENT:
                PaperExitServiceOutcome.SOURCE_GRAPH_INCONSISTENT,
            PaperExitCursorOutcome.TRANSIENT_DB_FAILURE:
                PaperExitServiceOutcome.TRANSIENT_DB_FAILURE,
        }.get(outcome, PaperExitServiceOutcome.INTERNAL_INVARIANT_FAILURE)
        return PaperExitEvaluationService._failure(request, mapped)

    @staticmethod
    def _repository_failure(
        request: PaperExitEvaluationRequest,
        repository_result: RepositoryResult,
    ) -> PaperExitServiceResult:
        mapped = {
            RepositoryOutcome.NOT_FOUND: PaperExitServiceOutcome.SOURCE_GRAPH_INCONSISTENT,
            RepositoryOutcome.STALE_VERSION: PaperExitServiceOutcome.STALE_CURSOR_VERSION,
            RepositoryOutcome.INVALID_STATE: PaperExitServiceOutcome.SOURCE_GRAPH_INCONSISTENT,
            RepositoryOutcome.IDEMPOTENCY_CONFLICT: PaperExitServiceOutcome.IDEMPOTENCY_CONFLICT,
            RepositoryOutcome.CONSTRAINT_VIOLATION: PaperExitServiceOutcome.CONSTRAINT_VIOLATION,
            RepositoryOutcome.TRANSIENT_DB_FAILURE: PaperExitServiceOutcome.TRANSIENT_DB_FAILURE,
            RepositoryOutcome.UNCERTAIN_COMMIT_RESOLVED_NOT_COMMITTED:
                PaperExitServiceOutcome.UNCERTAIN_COMMIT_RESOLVED_NOT_COMMITTED,
            RepositoryOutcome.UNCERTAIN_COMMIT_UNRESOLVED:
                PaperExitServiceOutcome.UNCERTAIN_COMMIT_UNRESOLVED,
            RepositoryOutcome.INTERNAL_INVARIANT_FAILURE:
                PaperExitServiceOutcome.INTERNAL_INVARIANT_FAILURE,
        }.get(
            repository_result.outcome,
            PaperExitServiceOutcome.INTERNAL_INVARIANT_FAILURE,
        )
        return PaperExitEvaluationService._failure(
            request,
            mapped,
            repository_result.outcome,
            repository_result.reason_code,
        )

    @staticmethod
    def _no_trigger_success(
        request: PaperExitEvaluationRequest,
        position: PaperPosition,
        cursor: PaperExitEvaluationCursor,
        outcome: PaperExitServiceOutcome,
    ) -> PaperExitServiceResult:
        return PaperExitServiceResult(
            outcome,
            "PAPER_EXIT_NO_TRIGGER_CURSOR_ADVANCED",
            request.position_id,
            request.cursor_id,
            cursor.last_evaluated_closed_until_ms,
            cursor.version,
            position.state,
            position.version,
            repository_outcome=(
                RepositoryOutcome.EXISTING_IDEMPOTENT
                if outcome is PaperExitServiceOutcome.CURSOR_ALREADY_ADVANCED
                else RepositoryOutcome.UPDATED
            ),
        )

    @staticmethod
    def _trigger_success(
        request: PaperExitEvaluationRequest,
        expected: _ExpectedTrigger,
        outcome: PaperExitServiceOutcome,
        repository_outcome: RepositoryOutcome,
    ) -> PaperExitServiceResult:
        return PaperExitServiceResult(
            outcome,
            "PAPER_EXIT_PREPARED",
            request.position_id,
            request.cursor_id,
            expected.changed_cursor.last_evaluated_closed_until_ms,
            expected.changed_cursor.version,
            PaperPositionState.CLOSING,
            request.expected_position_version + 1,
            request.exit_decision_id,
            request.close_order_id,
            PaperOrderState.OPEN,
            expected.trigger,
            repository_outcome=repository_outcome,
            event_count=_TRIGGER_ORDER_EVENTS + 1,
            journal_count=_TRIGGER_JOURNAL_ROWS,
            close_execution_request=expected.close_execution_request,
        )

    @staticmethod
    def _failure(
        request: PaperExitEvaluationRequest,
        outcome: PaperExitServiceOutcome,
        repository_outcome: RepositoryOutcome | None = None,
        reason: str | None = None,
    ) -> PaperExitServiceResult:
        return PaperExitServiceResult(
            outcome,
            reason or f"PAPER_EXIT_{outcome.value}",
            request.position_id,
            request.cursor_id,
            repository_outcome=repository_outcome,
        )

    @staticmethod
    def _repositories(uow: PaperUnitOfWork) -> PaperRepositories:
        repositories = uow.repositories
        if not isinstance(repositories, PaperRepositories):
            raise RuntimeError("PAPER_UOW_REPOSITORIES_UNAVAILABLE")
        return repositories
