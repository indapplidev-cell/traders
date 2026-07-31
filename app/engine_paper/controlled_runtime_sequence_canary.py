"""Explicitly bounded composition of the authoritative single-cycle PAPER canary.

The sequence service owns no business transaction and has no child application
service dependency.  Every material step is delegated to a freshly armed
``PaperControlledRuntimeSingleCycleCanaryService`` request.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from datetime import datetime
from enum import StrEnum
from threading import Lock
from typing import Callable, Final, Protocol

from app.engine_paper.controlled_runtime import (
    PaperControlledRuntimeAction,
    PaperControlledRuntimeConfiguration,
    PaperControlledRuntimeTarget,
    PaperDatabaseAccessMode,
    evaluate_controlled_runtime_startup_gate,
)
from app.engine_paper.controlled_runtime_canary import (
    CANARY_ACKNOWLEDGEMENT,
    PAPER_CONTROLLED_RUNTIME_CANARY_ARMING_VERSION,
    TASK_ID as SINGLE_CYCLE_TASK_ID,
    PaperControlledRuntimeCanaryArming,
    PaperControlledRuntimeCanaryMutationBudget,
    PaperControlledRuntimeCanaryOutcome,
    PaperControlledRuntimeCanaryRowCountDeltas,
    PaperControlledRuntimeCanaryStage,
    PaperControlledRuntimeCanaryTargetIdentity,
    PaperControlledRuntimeSingleCycleCanaryRequest,
    PaperControlledRuntimeSingleCycleCanaryResult,
    PaperControlledRuntimeSingleCycleCanaryService,
    canary_ownership_marker,
    paper_canary_graph_fingerprint,
)
from app.engine_paper.controlled_worker import (
    PaperLifecycleCycleRequest,
    PaperLifecycleCycleScope,
    PaperLifecycleGraph,
    PaperLifecycleState,
    classify_paper_lifecycle_state,
)
from app.engine_safety import ExecutionMode
from app.engine_safety.paper_domain import require_identity, require_utc


TASK_ID: Final = (
    "TRADERS_ML_PAPER_TRADING_CONTROLLED_RUNTIME_BOUNDED_SEQUENCE_CANARY_01"
)
PAPER_CONTROLLED_RUNTIME_BOUNDED_SEQUENCE_CONTRACT_VERSION: Final = (
    "PAPER_CONTROLLED_RUNTIME_BOUNDED_SEQUENCE_V1"
)
PAPER_CONTROLLED_RUNTIME_BOUNDED_SEQUENCE_ARMING_VERSION: Final = (
    "PAPER_CONTROLLED_RUNTIME_BOUNDED_SEQUENCE_ARMING_V1"
)
SEQUENCE_ACKNOWLEDGEMENT: Final = (
    "I_AUTHORIZE_THIS_EXACT_ORDERED_BOUNDED_ISOLATED_PAPER_SEQUENCE"
)
MIN_SEQUENCE_STEPS: Final = 1
MAX_SEQUENCE_STEPS: Final = 5
MAX_WORKER_INVOCATIONS_PER_STEP: Final = 1
MAX_MUTATING_STAGES_PER_STEP: Final = 1
MAX_TOTAL_WORKER_INVOCATIONS: Final = 5
MAX_TOTAL_MUTATING_STAGES: Final = 5


class PaperControlledRuntimeBoundedSequenceOutcome(StrEnum):
    SEQUENCE_COMPLETED = "SEQUENCE_COMPLETED"
    SEQUENCE_ALREADY_COMPLETED = "SEQUENCE_ALREADY_COMPLETED"
    SEQUENCE_PARTIAL_RESUMED_AND_COMPLETED = (
        "SEQUENCE_PARTIAL_RESUMED_AND_COMPLETED"
    )
    SEQUENCE_CONFIGURATION_INVALID = "SEQUENCE_CONFIGURATION_INVALID"
    SEQUENCE_AUTHORIZATION_INVALID = "SEQUENCE_AUTHORIZATION_INVALID"
    SEQUENCE_PLAN_INVALID = "SEQUENCE_PLAN_INVALID"
    SEQUENCE_TARGET_INVALID = "SEQUENCE_TARGET_INVALID"
    SEQUENCE_EXPECTED_STATE_MISMATCH = "SEQUENCE_EXPECTED_STATE_MISMATCH"
    SEQUENCE_RESUME_STATE_AMBIGUOUS = "SEQUENCE_RESUME_STATE_AMBIGUOUS"
    SEQUENCE_SINGLE_CYCLE_FAILED = "SEQUENCE_SINGLE_CYCLE_FAILED"
    SEQUENCE_MUTATION_BUDGET_MISMATCH = "SEQUENCE_MUTATION_BUDGET_MISMATCH"
    SEQUENCE_CANCELLED_BEFORE_FIRST_MUTATION = (
        "SEQUENCE_CANCELLED_BEFORE_FIRST_MUTATION"
    )
    SEQUENCE_CANCELLED_WITH_DURABLE_PREFIX = (
        "SEQUENCE_CANCELLED_WITH_DURABLE_PREFIX"
    )
    SEQUENCE_CANCELLED_AFTER_COMPLETION = "SEQUENCE_CANCELLED_AFTER_COMPLETION"
    SEQUENCE_FAULT_BEFORE_FIRST_MUTATION = "SEQUENCE_FAULT_BEFORE_FIRST_MUTATION"
    SEQUENCE_FAULT_WITH_DURABLE_PREFIX = "SEQUENCE_FAULT_WITH_DURABLE_PREFIX"


class PaperControlledRuntimeSequenceFaultPoint(StrEnum):
    BEFORE_SEQUENCE_VALIDATION = "BEFORE_SEQUENCE_VALIDATION"
    AFTER_SEQUENCE_VALIDATION = "AFTER_SEQUENCE_VALIDATION"
    BEFORE_PREFIX_GRAPH_LOAD = "BEFORE_PREFIX_GRAPH_LOAD"
    AFTER_PREFIX_GRAPH_LOAD = "AFTER_PREFIX_GRAPH_LOAD"
    BEFORE_STEP_GRAPH_LOAD = "BEFORE_STEP_GRAPH_LOAD"
    AFTER_STEP_GRAPH_LOAD = "AFTER_STEP_GRAPH_LOAD"
    BEFORE_SINGLE_CYCLE_CALL = "BEFORE_SINGLE_CYCLE_CALL"
    AFTER_SINGLE_CYCLE_CALL = "AFTER_SINGLE_CYCLE_CALL"
    BEFORE_FINAL_POSTFLIGHT = "BEFORE_FINAL_POSTFLIGHT"
    AFTER_FINAL_POSTFLIGHT = "AFTER_FINAL_POSTFLIGHT"


class PaperControlledRuntimeSequenceCancellationAuthority(Protocol):
    def is_cancelled(self) -> bool: ...


class PaperControlledRuntimeSequenceGraphLoader(Protocol):
    def load(self, command_id: str) -> PaperLifecycleGraph: ...


@dataclass(frozen=True, slots=True)
class PaperControlledRuntimeSequenceMutationBudget:
    commands: int = 0
    orders: int = 0
    fills: int = 0
    positions: int = 0
    cursors: int = 0
    exit_decisions: int = 0
    order_events: int = 0
    journal_rows: int = 0
    entity_updates_versions: int = 0
    fees: int = 0
    pnl: int = 0

    def __post_init__(self) -> None:
        for item in fields(self):
            value = getattr(self, item.name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{item.name} must be a non-negative integer")

    def __add__(
        self, other: "PaperControlledRuntimeSequenceMutationBudget"
    ) -> "PaperControlledRuntimeSequenceMutationBudget":
        if not isinstance(other, PaperControlledRuntimeSequenceMutationBudget):
            return NotImplemented
        return PaperControlledRuntimeSequenceMutationBudget(
            **{
                item.name: getattr(self, item.name) + getattr(other, item.name)
                for item in fields(self)
            }
        )

    @classmethod
    def exact_for_stage(
        cls, stage: PaperControlledRuntimeCanaryStage
    ) -> "PaperControlledRuntimeSequenceMutationBudget":
        single = PaperControlledRuntimeCanaryMutationBudget.exact_for_stage(stage)
        return cls(
            commands=single.command_inserts,
            orders=single.order_inserts,
            fills=single.fill_inserts,
            positions=single.position_inserts,
            cursors=single.cursor_inserts,
            exit_decisions=single.exit_decision_inserts,
            order_events=single.order_event_inserts,
            journal_rows=single.journal_inserts,
            entity_updates_versions=(
                single.order_updates
                + single.position_updates
                + single.cursor_updates
            ),
            fees=(
                1
                if stage
                in {
                    PaperControlledRuntimeCanaryStage.EXECUTE_ENTRY,
                    PaperControlledRuntimeCanaryStage.EXECUTE_CLOSE,
                }
                else 0
            ),
            pnl=(
                1
                if stage is PaperControlledRuntimeCanaryStage.EXECUTE_CLOSE
                else 0
            ),
        )

    @classmethod
    def from_single_cycle(
        cls,
        stage: PaperControlledRuntimeCanaryStage,
        deltas: PaperControlledRuntimeCanaryRowCountDeltas,
    ) -> "PaperControlledRuntimeSequenceMutationBudget":
        return cls(
            commands=deltas.command_inserts,
            orders=deltas.order_inserts,
            fills=deltas.fill_inserts,
            positions=deltas.position_inserts,
            cursors=deltas.cursor_inserts,
            exit_decisions=deltas.exit_decision_inserts,
            order_events=deltas.order_event_inserts,
            journal_rows=deltas.journal_inserts,
            entity_updates_versions=(
                deltas.order_updates
                + deltas.position_updates
                + deltas.cursor_updates
            ),
            fees=(
                1
                if stage
                in {
                    PaperControlledRuntimeCanaryStage.EXECUTE_ENTRY,
                    PaperControlledRuntimeCanaryStage.EXECUTE_CLOSE,
                }
                else 0
            ),
            pnl=(
                1
                if stage is PaperControlledRuntimeCanaryStage.EXECUTE_CLOSE
                else 0
            ),
        )


@dataclass(frozen=True, slots=True)
class PaperControlledRuntimeBoundedSequenceStepPlan:
    step_index: int
    step_id: str
    expected_initial_state: PaperLifecycleState
    expected_stage: PaperControlledRuntimeCanaryStage
    expected_terminal_or_next_state_class: PaperLifecycleState
    supplied_input_reference: str
    mutation_budget: PaperControlledRuntimeSequenceMutationBudget
    authorization_expires_at: datetime
    stop_after_step: bool = False

    def __post_init__(self) -> None:
        if (
            isinstance(self.step_index, bool)
            or not isinstance(self.step_index, int)
            or not 0 <= self.step_index < MAX_SEQUENCE_STEPS
        ):
            raise ValueError("step_index is outside the hard bound")
        for name in ("step_id", "supplied_input_reference"):
            object.__setattr__(
                self, name, require_identity(getattr(self, name), name)
            )
        if not isinstance(self.expected_initial_state, PaperLifecycleState):
            raise TypeError("expected_initial_state must be a lifecycle state")
        if not isinstance(self.expected_stage, PaperControlledRuntimeCanaryStage):
            raise TypeError("expected_stage must be an allowed sequence stage")
        if not isinstance(
            self.expected_terminal_or_next_state_class, PaperLifecycleState
        ):
            raise TypeError("expected next state must be a lifecycle state")
        require_utc(self.authorization_expires_at, "authorization_expires_at")
        if not isinstance(self.stop_after_step, bool):
            raise TypeError("stop_after_step must be boolean")


@dataclass(frozen=True, slots=True)
class PaperControlledRuntimeBoundedSequencePlan:
    contract_version: str
    task_id: str
    sequence_run_id: str
    configuration_id: str
    target_identity: PaperControlledRuntimeCanaryTargetIdentity
    symbol: str
    execution_mode: ExecutionMode
    ordered_step_plans: tuple[PaperControlledRuntimeBoundedSequenceStepPlan, ...]
    max_steps: int
    created_at: datetime
    expires_at: datetime
    single_use: bool
    explicit_acknowledgement: str
    aggregate_mutation_budget: PaperControlledRuntimeSequenceMutationBudget
    correlation_id: str

    def __post_init__(self) -> None:
        for name in (
            "contract_version",
            "task_id",
            "sequence_run_id",
            "configuration_id",
            "correlation_id",
        ):
            object.__setattr__(
                self, name, require_identity(getattr(self, name), name)
            )
        object.__setattr__(self, "symbol", str(self.symbol).strip().upper())
        if not isinstance(self.ordered_step_plans, tuple):
            raise TypeError("ordered_step_plans must be an immutable tuple")
        if (
            isinstance(self.max_steps, bool)
            or not isinstance(self.max_steps, int)
            or not MIN_SEQUENCE_STEPS <= self.max_steps <= MAX_SEQUENCE_STEPS
        ):
            raise ValueError("max_steps is outside the hard bound")
        require_utc(self.created_at, "created_at")
        require_utc(self.expires_at, "expires_at")


@dataclass(frozen=True, slots=True)
class PaperControlledRuntimeBoundedSequenceArming:
    arming_contract_version: str
    task_id: str
    sequence_run_id: str
    configuration_id: str
    target_identity: PaperControlledRuntimeCanaryTargetIdentity
    symbol: str
    ordered_stage_list: tuple[PaperControlledRuntimeCanaryStage, ...]
    step_cap: int
    aggregate_mutation_budget: PaperControlledRuntimeSequenceMutationBudget
    expires_at: datetime
    single_use: bool
    explicit_acknowledgement: str

    def __post_init__(self) -> None:
        for name in (
            "arming_contract_version",
            "task_id",
            "sequence_run_id",
            "configuration_id",
            "explicit_acknowledgement",
        ):
            object.__setattr__(
                self, name, require_identity(getattr(self, name), name)
            )
        object.__setattr__(self, "symbol", str(self.symbol).strip().upper())
        if not isinstance(self.ordered_stage_list, tuple):
            raise TypeError("ordered_stage_list must be an immutable tuple")
        if (
            isinstance(self.step_cap, bool)
            or not isinstance(self.step_cap, int)
            or not MIN_SEQUENCE_STEPS <= self.step_cap <= MAX_SEQUENCE_STEPS
        ):
            raise ValueError("step_cap is outside the hard bound")
        require_utc(self.expires_at, "expires_at")


@dataclass(frozen=True, slots=True)
class PaperControlledRuntimeBoundedSequenceCanaryRequest:
    request_id: str
    plan: PaperControlledRuntimeBoundedSequencePlan
    arming: PaperControlledRuntimeBoundedSequenceArming
    configuration: PaperControlledRuntimeConfiguration
    ordered_cycle_requests: tuple[PaperLifecycleCycleRequest, ...]
    evaluated_at: datetime
    cancellation_authority: (
        PaperControlledRuntimeSequenceCancellationAuthority | None
    ) = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "request_id", require_identity(self.request_id, "request_id")
        )
        if not isinstance(self.ordered_cycle_requests, tuple):
            raise TypeError("ordered_cycle_requests must be an immutable tuple")
        require_utc(self.evaluated_at, "evaluated_at")


@dataclass(frozen=True, slots=True)
class PaperControlledRuntimeBoundedSequenceStepResult:
    step_index: int
    step_id: str
    expected_stage: PaperControlledRuntimeCanaryStage
    pre_step_state: PaperLifecycleState | None
    dry_run_result: str
    fingerprint_arming_result: str
    single_cycle_outcome: str
    worker_invocation_count: int
    mutating_stage_count: int
    mutation_budget_result: str
    post_step_state: PaperLifecycleState | None
    safe_entity_version_deltas: PaperControlledRuntimeCanaryRowCountDeltas
    stop_reason: str


@dataclass(frozen=True, slots=True)
class PaperControlledRuntimeBoundedSequenceCanaryResult:
    request_id: str
    sequence_run_id: str
    overall_outcome: PaperControlledRuntimeBoundedSequenceOutcome
    requested_step_count: int
    completed_step_count: int
    skipped_step_count: int
    failed_step_count: int
    initial_persisted_state: PaperLifecycleState | None
    final_persisted_state: PaperLifecycleState | None
    total_worker_calls: int
    total_mutating_stages: int
    aggregate_budget_result: str
    durable_completed_prefix: int
    next_resumable_step_index: int | None
    cancellation_fault_classification: str
    cleanup_result: str
    ordered_step_results: tuple[
        PaperControlledRuntimeBoundedSequenceStepResult, ...
    ]


def aggregate_sequence_budget(
    steps: tuple[PaperControlledRuntimeBoundedSequenceStepPlan, ...]
) -> PaperControlledRuntimeSequenceMutationBudget:
    total = PaperControlledRuntimeSequenceMutationBudget()
    for step in steps:
        total = total + step.mutation_budget
    return total


def _configuration_valid(configuration: object) -> bool:
    if not isinstance(configuration, PaperControlledRuntimeConfiguration):
        return False
    return (
        configuration.runtime_action
        is PaperControlledRuntimeAction.BOUNDED_SEQUENCE_CANARY
        and configuration.target is PaperControlledRuntimeTarget.ISOLATED_POSTGRESQL
        and configuration.execution_mode is ExecutionMode.PAPER
        and configuration.runtime_enabled is True
        and configuration.dry_run_enabled is True
        and configuration.explicit_paper_authorization is True
        and configuration.explicit_sequence_authorization is True
        and configuration.cycle_scope
        is PaperLifecycleCycleScope.ADVANCE_ONE_LIFECYCLE_STEP
        and configuration.max_stages_per_cycle == 1
        and configuration.database_access_mode
        is PaperDatabaseAccessMode.ISOLATED_CANARY_READ_WRITE
        and configuration.network_access_allowed is False
        and configuration.polling_allowed is False
        and configuration.scheduler_allowed is False
        and configuration.daemon_allowed is False
        and evaluate_controlled_runtime_startup_gate(configuration).ready
    )


def _plan_valid(
    request: PaperControlledRuntimeBoundedSequenceCanaryRequest,
) -> bool:
    plan = request.plan
    steps = plan.ordered_step_plans
    if (
        plan.contract_version
        != PAPER_CONTROLLED_RUNTIME_BOUNDED_SEQUENCE_CONTRACT_VERSION
        or plan.task_id != TASK_ID
        or plan.execution_mode is not ExecutionMode.PAPER
        or plan.created_at >= plan.expires_at
        or plan.expires_at <= request.evaluated_at
        or plan.single_use is not True
        or plan.explicit_acknowledgement != SEQUENCE_ACKNOWLEDGEMENT
        or plan.configuration_id != request.configuration.configuration_id
        or plan.symbol not in request.configuration.allowed_symbols
        or not MIN_SEQUENCE_STEPS <= len(steps) <= MAX_SEQUENCE_STEPS
        or len(steps) > plan.max_steps
        or len(request.ordered_cycle_requests) != len(steps)
        or tuple(step.step_index for step in steps) != tuple(range(len(steps)))
        or len({step.step_id for step in steps}) != len(steps)
        or sum(
            step.expected_stage is PaperControlledRuntimeCanaryStage.INGEST_COMMAND
            for step in steps
        )
        > 1
        or any(step.authorization_expires_at <= request.evaluated_at for step in steps)
        or aggregate_sequence_budget(steps) != plan.aggregate_mutation_budget
    ):
        return False
    for index, (step, cycle) in enumerate(
        zip(steps, request.ordered_cycle_requests, strict=True)
    ):
        if (
            cycle.command_id
            != request.ordered_cycle_requests[0].command_id
            or cycle.execution_mode is not ExecutionMode.PAPER
            or cycle.explicit_paper_authorization is not True
            or cycle.scope
            is not PaperLifecycleCycleScope.ADVANCE_ONE_LIFECYCLE_STEP
            or cycle.max_stages != 1
            or cycle.correlation_id != plan.correlation_id
            or step.mutation_budget
            != PaperControlledRuntimeSequenceMutationBudget.exact_for_stage(
                step.expected_stage
            )
        ):
            return False
        if (
            index + 1 < len(steps)
            and step.stop_after_step
        ):
            return False
        if (
            index + 1 < len(steps)
            and step.expected_terminal_or_next_state_class
            is not steps[index + 1].expected_initial_state
        ):
            return False
    return True


def _arming_valid(
    request: PaperControlledRuntimeBoundedSequenceCanaryRequest,
) -> bool:
    plan = request.plan
    arming = request.arming
    return (
        arming.arming_contract_version
        == PAPER_CONTROLLED_RUNTIME_BOUNDED_SEQUENCE_ARMING_VERSION
        and arming.task_id == TASK_ID
        and arming.sequence_run_id == plan.sequence_run_id
        and arming.configuration_id == plan.configuration_id
        and arming.target_identity == plan.target_identity
        and arming.symbol == plan.symbol
        and arming.ordered_stage_list
        == tuple(step.expected_stage for step in plan.ordered_step_plans)
        and arming.step_cap == plan.max_steps
        and arming.aggregate_mutation_budget == plan.aggregate_mutation_budget
        and arming.expires_at > request.evaluated_at
        and arming.single_use is True
        and arming.explicit_acknowledgement == SEQUENCE_ACKNOWLEDGEMENT
    )


def _contains_id(values: tuple[object, ...], name: str, value: str | None) -> bool:
    return value is not None and any(getattr(item, name, None) == value for item in values)


def _step_completed(
    step: PaperControlledRuntimeBoundedSequenceStepPlan,
    cycle: PaperLifecycleCycleRequest,
    graph: PaperLifecycleGraph,
) -> bool:
    stage = step.expected_stage
    if stage is PaperControlledRuntimeCanaryStage.INGEST_COMMAND:
        return graph.command is not None and any(
            node.order.order_id == cycle.entry_order_id for node in graph.orders
        )
    if stage is PaperControlledRuntimeCanaryStage.EXECUTE_ENTRY:
        return (
            _contains_id(graph.fills, "fill_id", cycle.entry_fill_id)
            and _contains_id(graph.positions, "position_id", cycle.position_id)
            and len(graph.cursors) == 1
            and graph.cursors[0].position_id == cycle.position_id
        )
    if stage is PaperControlledRuntimeCanaryStage.EVALUATE_EXIT_NO_TRIGGER:
        source = cycle.exit_evaluation_request
        if source is None or len(graph.cursors) != 1:
            return False
        cursor = graph.cursors[0]
        return (
            cursor.cursor_id == source.cursor_id
            and cursor.version > source.expected_cursor_version
            and not _contains_id(
                graph.exit_decisions,
                "exit_decision_id",
                source.exit_decision_id,
            )
        )
    if stage is PaperControlledRuntimeCanaryStage.EVALUATE_EXIT_TRIGGER:
        return (
            _contains_id(
                graph.exit_decisions, "exit_decision_id", cycle.exit_decision_id
            )
            and any(
                node.order.order_id == cycle.close_order_id
                for node in graph.orders
            )
        )
    if stage is PaperControlledRuntimeCanaryStage.EXECUTE_CLOSE:
        return (
            _contains_id(graph.fills, "fill_id", cycle.close_fill_id)
            and classify_paper_lifecycle_state(graph)
            is PaperLifecycleState.POSITION_CLOSED
        )
    return False


def infer_durable_completed_prefix(
    plan: PaperControlledRuntimeBoundedSequencePlan,
    cycles: tuple[PaperLifecycleCycleRequest, ...],
    graph: PaperLifecycleGraph,
) -> int | None:
    completed = tuple(
        _step_completed(step, cycle, graph)
        for step, cycle in zip(plan.ordered_step_plans, cycles, strict=True)
    )
    seen_incomplete = False
    prefix = 0
    for value in completed:
        if value and seen_incomplete:
            return None
        if value:
            prefix += 1
        else:
            seen_incomplete = True
    state = classify_paper_lifecycle_state(graph)
    if state is PaperLifecycleState.INCONSISTENT:
        return None
    if prefix < len(plan.ordered_step_plans):
        if state is not plan.ordered_step_plans[prefix].expected_initial_state:
            return None
    elif state is not plan.ordered_step_plans[-1].expected_terminal_or_next_state_class:
        return None
    return prefix


class PaperControlledRuntimeBoundedSequenceCanaryService:
    """Run one immutable tuple of at most five authoritative canary calls."""

    def __init__(
        self,
        *,
        graph_loader: PaperControlledRuntimeSequenceGraphLoader,
        single_cycle_canary: PaperControlledRuntimeSingleCycleCanaryService,
        fault_injector: (
            Callable[[PaperControlledRuntimeSequenceFaultPoint], None] | None
        ) = None,
    ) -> None:
        self._graph_loader = graph_loader
        self._single_cycle_canary = single_cycle_canary
        self._fault_injector = fault_injector
        self._invocation_lock = Lock()

    def run(
        self, request: PaperControlledRuntimeBoundedSequenceCanaryRequest
    ) -> PaperControlledRuntimeBoundedSequenceCanaryResult:
        if not isinstance(
            request, PaperControlledRuntimeBoundedSequenceCanaryRequest
        ):
            raise TypeError("request must be a bounded sequence request")
        with self._invocation_lock:
            return self._run_locked(request)

    def _run_locked(
        self, request: PaperControlledRuntimeBoundedSequenceCanaryRequest
    ) -> PaperControlledRuntimeBoundedSequenceCanaryResult:
        if self._cancelled(request):
            return self._result(
                request,
                (
                    PaperControlledRuntimeBoundedSequenceOutcome
                    .SEQUENCE_CANCELLED_BEFORE_FIRST_MUTATION
                ),
                cancellation="CANCELLED_BEFORE_VALIDATION",
            )
        try:
            self._fault(PaperControlledRuntimeSequenceFaultPoint.BEFORE_SEQUENCE_VALIDATION)
        except Exception:
            return self._result(
                request,
                PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_FAULT_BEFORE_FIRST_MUTATION,
                cancellation="FAULT_BEFORE_VALIDATION",
            )
        if not _configuration_valid(request.configuration):
            return self._result(
                request,
                PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_CONFIGURATION_INVALID,
            )
        if not _plan_valid(request):
            return self._result(
                request,
                PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_PLAN_INVALID,
            )
        if not _arming_valid(request):
            return self._result(
                request,
                PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_AUTHORIZATION_INVALID,
            )
        try:
            self._fault(PaperControlledRuntimeSequenceFaultPoint.AFTER_SEQUENCE_VALIDATION)
            self._fault(PaperControlledRuntimeSequenceFaultPoint.BEFORE_PREFIX_GRAPH_LOAD)
            initial_graph = self._graph_loader.load(
                request.ordered_cycle_requests[0].command_id
            )
            self._fault(PaperControlledRuntimeSequenceFaultPoint.AFTER_PREFIX_GRAPH_LOAD)
        except Exception:
            return self._result(
                request,
                PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_FAULT_BEFORE_FIRST_MUTATION,
                cancellation="FAULT_DURING_PREFIX_INFERENCE",
            )
        initial_state = classify_paper_lifecycle_state(initial_graph)
        prefix = infer_durable_completed_prefix(
            request.plan, request.ordered_cycle_requests, initial_graph
        )
        if prefix is None:
            return self._result(
                request,
                PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_RESUME_STATE_AMBIGUOUS,
                initial_state=initial_state,
            )
        if prefix == len(request.plan.ordered_step_plans):
            outcome = (
                PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_CANCELLED_AFTER_COMPLETION
                if self._cancelled(request)
                else PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_ALREADY_COMPLETED
            )
            return self._result(
                request,
                outcome,
                initial_state=initial_state,
                final_state=initial_state,
                completed=prefix,
                skipped=prefix,
                prefix=prefix,
                cancellation=(
                    "CANCELLED_AFTER_COMPLETION"
                    if self._cancelled(request)
                    else "NOT_CANCELLED"
                ),
            )

        step_results: list[PaperControlledRuntimeBoundedSequenceStepResult] = []
        total_budget = PaperControlledRuntimeSequenceMutationBudget()
        total_workers = 0
        total_mutating = 0
        completed = prefix
        last_state = initial_state
        for step_index in range(prefix, len(request.plan.ordered_step_plans)):
            step = request.plan.ordered_step_plans[step_index]
            cycle = request.ordered_cycle_requests[step_index]
            if self._cancelled(request):
                return self._result(
                    request,
                    (
                        PaperControlledRuntimeBoundedSequenceOutcome
                        .SEQUENCE_CANCELLED_WITH_DURABLE_PREFIX
                    ),
                    initial_state=initial_state,
                    final_state=last_state,
                    completed=completed,
                    skipped=prefix,
                    prefix=completed,
                    workers=total_workers,
                    mutating=total_mutating,
                    budget="PASS",
                    cancellation="CANCELLED_BEFORE_STEP",
                    steps=tuple(step_results),
                )
            try:
                self._fault(PaperControlledRuntimeSequenceFaultPoint.BEFORE_STEP_GRAPH_LOAD)
                graph = self._graph_loader.load(cycle.command_id)
                self._fault(PaperControlledRuntimeSequenceFaultPoint.AFTER_STEP_GRAPH_LOAD)
            except Exception:
                return self._fault_result(
                    request,
                    initial_state,
                    last_state,
                    completed,
                    prefix,
                    total_workers,
                    total_mutating,
                    tuple(step_results),
                    "FAULT_DURING_STEP_GRAPH_LOAD",
                )
            pre_state = classify_paper_lifecycle_state(graph)
            if pre_state is not step.expected_initial_state:
                return self._result(
                    request,
                    PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_EXPECTED_STATE_MISMATCH,
                    initial_state=initial_state,
                    final_state=pre_state,
                    completed=completed,
                    skipped=prefix,
                    failed=1,
                    prefix=completed,
                    workers=total_workers,
                    mutating=total_mutating,
                    cancellation="NOT_CANCELLED",
                    steps=tuple(step_results),
                )
            fingerprint = paper_canary_graph_fingerprint(graph, step.expected_stage)
            single_request = self._single_request(
                request, step, cycle, pre_state, fingerprint
            )
            if self._cancelled(request):
                return self._result(
                    request,
                    (
                        PaperControlledRuntimeBoundedSequenceOutcome
                        .SEQUENCE_CANCELLED_WITH_DURABLE_PREFIX
                    ),
                    initial_state=initial_state,
                    final_state=pre_state,
                    completed=completed,
                    skipped=prefix,
                    prefix=completed,
                    workers=total_workers,
                    mutating=total_mutating,
                    cancellation="CANCELLED_BEFORE_SINGLE_CYCLE",
                    steps=tuple(step_results),
                )
            try:
                self._fault(PaperControlledRuntimeSequenceFaultPoint.BEFORE_SINGLE_CYCLE_CALL)
                single = self._single_cycle_canary.run(single_request)
            except Exception:
                return self._fault_result(
                    request,
                    initial_state,
                    pre_state,
                    completed,
                    prefix,
                    total_workers,
                    total_mutating,
                    tuple(step_results),
                    "FAULT_AT_SINGLE_CYCLE_BOUNDARY",
                )
            total_workers += single.worker_invocations
            total_mutating += single.mutating_stage_invocations
            actual_budget = PaperControlledRuntimeSequenceMutationBudget.from_single_cycle(
                step.expected_stage, single.row_count_deltas
            )
            budget_matches = actual_budget == step.mutation_budget
            post_state = single.postflight_lifecycle_state
            step_success = (
                single.outcome
                in {
                    PaperControlledRuntimeCanaryOutcome.CANARY_STAGE_COMPLETED,
                    PaperControlledRuntimeCanaryOutcome.CANARY_CANCELLED_AFTER_COMMITTED_STAGE,
                }
                and single.worker_invocations <= MAX_WORKER_INVOCATIONS_PER_STEP
                and single.mutating_stage_invocations
                <= MAX_MUTATING_STAGES_PER_STEP
                and budget_matches
                and post_state
                is step.expected_terminal_or_next_state_class
            )
            step_results.append(
                PaperControlledRuntimeBoundedSequenceStepResult(
                    step.step_index,
                    step.step_id,
                    step.expected_stage,
                    pre_state,
                    single.dry_run_outcome,
                    "FRESH_FINGERPRINT_AND_ARMING_VALIDATED",
                    single.outcome.value,
                    single.worker_invocations,
                    single.mutating_stage_invocations,
                    "PASS" if budget_matches else "FAIL",
                    post_state,
                    single.row_count_deltas,
                    "EXPLICIT_STOP_AFTER_STEP"
                    if step.stop_after_step
                    else (
                        "STEP_COMPLETED" if step_success else single.reason_code
                    ),
                )
            )
            if not budget_matches:
                return self._result(
                    request,
                    PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_MUTATION_BUDGET_MISMATCH,
                    initial_state=initial_state,
                    final_state=post_state,
                    completed=completed,
                    skipped=prefix,
                    failed=1,
                    prefix=completed,
                    workers=total_workers,
                    mutating=total_mutating,
                    budget="FAIL",
                    steps=tuple(step_results),
                )
            if not step_success:
                return self._result(
                    request,
                    PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_SINGLE_CYCLE_FAILED,
                    initial_state=initial_state,
                    final_state=post_state,
                    completed=completed,
                    skipped=prefix,
                    failed=1,
                    prefix=completed,
                    workers=total_workers,
                    mutating=total_mutating,
                    budget="PASS",
                    cancellation="SINGLE_CYCLE_NON_SUCCESS",
                    steps=tuple(step_results),
                )
            total_budget = total_budget + actual_budget
            completed += 1
            last_state = post_state
            try:
                self._fault(
                    PaperControlledRuntimeSequenceFaultPoint.AFTER_SINGLE_CYCLE_CALL
                )
            except Exception:
                return self._fault_result(
                    request,
                    initial_state,
                    last_state,
                    completed,
                    prefix,
                    total_workers,
                    total_mutating,
                    tuple(step_results),
                    "FAULT_AFTER_COMMITTED_VERIFIED_STEP",
                )
            if (
                total_workers > MAX_TOTAL_WORKER_INVOCATIONS
                or total_mutating > MAX_TOTAL_MUTATING_STAGES
            ):
                return self._result(
                    request,
                    PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_MUTATION_BUDGET_MISMATCH,
                    initial_state=initial_state,
                    final_state=last_state,
                    completed=completed,
                    skipped=prefix,
                    failed=1,
                    prefix=completed,
                    workers=total_workers,
                    mutating=total_mutating,
                    budget="FAIL",
                    steps=tuple(step_results),
                )
            if self._cancelled(request):
                outcome = (
                    PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_CANCELLED_AFTER_COMPLETION
                    if completed == len(request.plan.ordered_step_plans)
                    else (
                        PaperControlledRuntimeBoundedSequenceOutcome
                        .SEQUENCE_CANCELLED_WITH_DURABLE_PREFIX
                    )
                )
                return self._result(
                    request,
                    outcome,
                    initial_state=initial_state,
                    final_state=last_state,
                    completed=completed,
                    skipped=prefix,
                    prefix=completed,
                    workers=total_workers,
                    mutating=total_mutating,
                    budget="PASS",
                    cancellation=outcome.value,
                    steps=tuple(step_results),
                )
            if step.stop_after_step:
                break

        expected_executed_budget = aggregate_sequence_budget(
            request.plan.ordered_step_plans[prefix:completed]
        )
        aggregate_pass = total_budget == expected_executed_budget
        try:
            self._fault(PaperControlledRuntimeSequenceFaultPoint.BEFORE_FINAL_POSTFLIGHT)
            final_graph = self._graph_loader.load(
                request.ordered_cycle_requests[0].command_id
            )
            self._fault(PaperControlledRuntimeSequenceFaultPoint.AFTER_FINAL_POSTFLIGHT)
        except Exception:
            return self._fault_result(
                request,
                initial_state,
                last_state,
                completed,
                prefix,
                total_workers,
                total_mutating,
                tuple(step_results),
                "FAULT_DURING_FINAL_POSTFLIGHT",
            )
        final_state = classify_paper_lifecycle_state(final_graph)
        if not aggregate_pass:
            return self._result(
                request,
                PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_MUTATION_BUDGET_MISMATCH,
                initial_state=initial_state,
                final_state=final_state,
                completed=completed,
                skipped=prefix,
                failed=1,
                prefix=completed,
                workers=total_workers,
                mutating=total_mutating,
                budget="FAIL",
                steps=tuple(step_results),
            )
        return self._result(
            request,
            (
                PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_PARTIAL_RESUMED_AND_COMPLETED
                if prefix
                else PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_COMPLETED
            ),
            initial_state=initial_state,
            final_state=final_state,
            completed=completed,
            skipped=prefix,
            prefix=completed,
            workers=total_workers,
            mutating=total_mutating,
            budget="PASS",
            steps=tuple(step_results),
        )

    def _single_request(
        self,
        request: PaperControlledRuntimeBoundedSequenceCanaryRequest,
        step: PaperControlledRuntimeBoundedSequenceStepPlan,
        cycle: PaperLifecycleCycleRequest,
        state: PaperLifecycleState,
        fingerprint: str,
    ) -> PaperControlledRuntimeSingleCycleCanaryRequest:
        plan = request.plan
        run_id = f"{plan.sequence_run_id}:step:{step.step_index}"
        base_target = plan.target_identity
        target = replace(
            base_target,
            task_id=SINGLE_CYCLE_TASK_ID,
            canary_run_id=run_id,
            ownership_marker=canary_ownership_marker(
                SINGLE_CYCLE_TASK_ID,
                run_id,
                base_target.database_name,
                base_target.database_role_name,
            ),
        )
        single_configuration = replace(
            request.configuration,
            runtime_action=PaperControlledRuntimeAction.SINGLE_CYCLE_CANARY,
            explicit_sequence_authorization=False,
        )
        arming = PaperControlledRuntimeCanaryArming(
            PAPER_CONTROLLED_RUNTIME_CANARY_ARMING_VERSION,
            SINGLE_CYCLE_TASK_ID,
            run_id,
            single_configuration.configuration_id,
            target,
            step.expected_stage,
            fingerprint,
            min(step.authorization_expires_at, request.arming.expires_at),
            True,
            CANARY_ACKNOWLEDGEMENT,
        )
        return PaperControlledRuntimeSingleCycleCanaryRequest(
            request_id=f"{request.request_id}:step:{step.step_index}",
            task_id=SINGLE_CYCLE_TASK_ID,
            canary_run_id=run_id,
            configuration=single_configuration,
            target_identity=target,
            arming=arming,
            cycle_request=cycle,
            expected_initial_state=state,
            expected_stage=step.expected_stage,
            expected_graph_fingerprint=fingerprint,
            expected_mutation_budget=(
                PaperControlledRuntimeCanaryMutationBudget.exact_for_stage(
                    step.expected_stage
                )
            ),
            created_at=plan.created_at,
            evaluated_at=request.evaluated_at,
            correlation_id=plan.correlation_id,
            symbol=plan.symbol,
            cancellation_authority=request.cancellation_authority,
        )

    def _fault_result(
        self,
        request: PaperControlledRuntimeBoundedSequenceCanaryRequest,
        initial_state: PaperLifecycleState | None,
        final_state: PaperLifecycleState | None,
        completed: int,
        skipped: int,
        workers: int,
        mutating: int,
        steps: tuple[PaperControlledRuntimeBoundedSequenceStepResult, ...],
        classification: str,
    ) -> PaperControlledRuntimeBoundedSequenceCanaryResult:
        return self._result(
            request,
            (
                PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_FAULT_WITH_DURABLE_PREFIX
                if completed
                else (
                    PaperControlledRuntimeBoundedSequenceOutcome
                    .SEQUENCE_FAULT_BEFORE_FIRST_MUTATION
                )
            ),
            initial_state=initial_state,
            final_state=final_state,
            completed=completed,
            skipped=skipped,
            failed=1,
            prefix=completed,
            workers=workers,
            mutating=mutating,
            cancellation=classification,
            steps=steps,
        )

    @staticmethod
    def _result(
        request: PaperControlledRuntimeBoundedSequenceCanaryRequest,
        outcome: PaperControlledRuntimeBoundedSequenceOutcome,
        *,
        initial_state: PaperLifecycleState | None = None,
        final_state: PaperLifecycleState | None = None,
        completed: int = 0,
        skipped: int = 0,
        failed: int = 0,
        prefix: int = 0,
        workers: int = 0,
        mutating: int = 0,
        budget: str = "NOT_RUN",
        cancellation: str = "NOT_CANCELLED",
        steps: tuple[PaperControlledRuntimeBoundedSequenceStepResult, ...] = (),
    ) -> PaperControlledRuntimeBoundedSequenceCanaryResult:
        requested = (
            len(request.plan.ordered_step_plans)
            if isinstance(
                request.plan, PaperControlledRuntimeBoundedSequencePlan
            )
            else 0
        )
        return PaperControlledRuntimeBoundedSequenceCanaryResult(
            request.request_id,
            request.plan.sequence_run_id,
            outcome,
            requested,
            completed,
            skipped,
            failed,
            initial_state,
            final_state,
            workers,
            mutating,
            budget,
            prefix,
            prefix if prefix < requested else None,
            cancellation,
            "CALLER_OWNED",
            steps[:MAX_SEQUENCE_STEPS],
        )

    def _fault(self, point: PaperControlledRuntimeSequenceFaultPoint) -> None:
        if self._fault_injector is not None:
            self._fault_injector(point)

    @staticmethod
    def _cancelled(
        request: PaperControlledRuntimeBoundedSequenceCanaryRequest,
    ) -> bool:
        authority = request.cancellation_authority
        if authority is None:
            return False
        try:
            return bool(authority.is_cancelled())
        except Exception:
            return True


__all__ = [
    "MAX_MUTATING_STAGES_PER_STEP",
    "MAX_SEQUENCE_STEPS",
    "MAX_TOTAL_MUTATING_STAGES",
    "MAX_TOTAL_WORKER_INVOCATIONS",
    "MAX_WORKER_INVOCATIONS_PER_STEP",
    "MIN_SEQUENCE_STEPS",
    "PAPER_CONTROLLED_RUNTIME_BOUNDED_SEQUENCE_ARMING_VERSION",
    "PAPER_CONTROLLED_RUNTIME_BOUNDED_SEQUENCE_CONTRACT_VERSION",
    "SEQUENCE_ACKNOWLEDGEMENT",
    "TASK_ID",
    "PaperControlledRuntimeBoundedSequenceArming",
    "PaperControlledRuntimeBoundedSequenceCanaryRequest",
    "PaperControlledRuntimeBoundedSequenceCanaryResult",
    "PaperControlledRuntimeBoundedSequenceCanaryService",
    "PaperControlledRuntimeBoundedSequenceOutcome",
    "PaperControlledRuntimeBoundedSequencePlan",
    "PaperControlledRuntimeBoundedSequenceStepPlan",
    "PaperControlledRuntimeBoundedSequenceStepResult",
    "PaperControlledRuntimeSequenceFaultPoint",
    "PaperControlledRuntimeSequenceMutationBudget",
    "aggregate_sequence_budget",
    "infer_durable_completed_prefix",
]
