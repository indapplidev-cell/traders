"""Explicit, atomic PAPER command-ingestion application service.

The service consumes one already-finalized approval chain.  It never finalizes
approvals, sizes a position, reads market data, simulates a fill, starts a
worker, or enables PAPER/LIVE runtime.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from hashlib import sha256
from typing import Final, TypeAlias
from uuid import UUID

from sqlalchemy.orm import Session

from app.engine_execution.paper_idempotency import (
    PAPER_IDEMPOTENCY_VERSION,
    command_idempotency_key,
    order_idempotency_key,
)
from app.engine_execution.paper_models import PaperExecutionCommand, PaperOrder
from app.engine_execution.paper_state_machine import (
    command_created_event,
    create_paper_order,
    transition_order,
)
from app.engine_journal.paper_events import PaperDomainEvent
from app.engine_paper.commit_recovery import recover_uncertain_commit
from app.engine_paper.fill_policy import PaperFillSimulationPolicy
from app.engine_paper.paper_approvals import (
    PaperQuantityApproval,
    PaperQuantityApprovalSource,
    PaperRiskApproval,
    PaperStrategyApproval,
    map_final_approvals_to_command_compatibility,
)
from app.engine_paper.repositories import (
    MAX_GRAPH_ROWS,
    PaperIngestionGraph,
    PaperRepositories,
    PaperStoredSimulationPolicy,
)
from app.engine_paper.repository_results import RepositoryOutcome, RepositoryResult
from app.engine_paper.semantic_idempotency import (
    command_semantic_tuple,
    journal_semantic_tuple,
    order_semantic_tuple,
)
from app.engine_paper.unit_of_work import PaperUnitOfWork
from app.engine_safety.paper_domain import (
    ExecutionMode,
    PaperDomainError,
    PaperEventType,
    PaperInputHealthStatus,
    PaperOrderState,
    PaperOrderType,
    PaperReasonCode,
    require_identity,
    require_utc,
)


_POLICY_VERSION: Final = 1
_JOURNAL_COUNT: Final = 4
_ORDER_EVENT_COUNT: Final = 3
_COMMAND_GRAPH_LIMIT: Final = 100
_INGESTION_IDENTITY_VERSION: Final = "v1"


class PaperCommandIngestionOutcome(StrEnum):
    COMMAND_AND_ORDER_CREATED = "COMMAND_AND_ORDER_CREATED"
    COMMAND_AND_ORDER_ALREADY_EXIST = "COMMAND_AND_ORDER_ALREADY_EXIST"
    UNCERTAIN_COMMIT_RESOLVED_COMMITTED = "UNCERTAIN_COMMIT_RESOLVED_COMMITTED"

    MODE_OFF = "MODE_OFF"
    MODE_LIVE_FORBIDDEN = "MODE_LIVE_FORBIDDEN"
    MODE_UNKNOWN = "MODE_UNKNOWN"
    PAPER_AUTHORIZATION_MISSING = "PAPER_AUTHORIZATION_MISSING"
    STRATEGY_APPROVAL_INVALID = "STRATEGY_APPROVAL_INVALID"
    QUANTITY_APPROVAL_INVALID = "QUANTITY_APPROVAL_INVALID"
    RISK_APPROVAL_INVALID = "RISK_APPROVAL_INVALID"
    FINAL_APPROVAL_CHAIN_INCONSISTENT = "FINAL_APPROVAL_CHAIN_INCONSISTENT"
    FINAL_APPROVAL_EXPIRED = "FINAL_APPROVAL_EXPIRED"
    INPUT_STALE = "INPUT_STALE"
    INPUT_DEGRADED = "INPUT_DEGRADED"
    FUTURE_DATA_REJECTED = "FUTURE_DATA_REJECTED"
    POLICY_NOT_FOUND = "POLICY_NOT_FOUND"
    POLICY_MISMATCH = "POLICY_MISMATCH"
    INVALID_COMMAND_COMPATIBILITY = "INVALID_COMMAND_COMPATIBILITY"

    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    EXISTING_GRAPH_INCONSISTENT = "EXISTING_GRAPH_INCONSISTENT"
    CONSTRAINT_VIOLATION = "CONSTRAINT_VIOLATION"
    TRANSIENT_DB_FAILURE = "TRANSIENT_DB_FAILURE"
    UNCERTAIN_COMMIT_RESOLVED_NOT_COMMITTED = (
        "UNCERTAIN_COMMIT_RESOLVED_NOT_COMMITTED"
    )
    UNCERTAIN_COMMIT_UNRESOLVED = "UNCERTAIN_COMMIT_UNRESOLVED"
    INTERNAL_INVARIANT_FAILURE = "INTERNAL_INVARIANT_FAILURE"


class PaperCommandIngestionReasonCode(StrEnum):
    OK = "PAPER_INGESTION_OK"
    MODE_OFF = "PAPER_INGESTION_MODE_OFF"
    MODE_LIVE_FORBIDDEN = "PAPER_INGESTION_MODE_LIVE_FORBIDDEN"
    MODE_UNKNOWN = "PAPER_INGESTION_MODE_UNKNOWN"
    PAPER_AUTHORIZATION_MISSING = "PAPER_INGESTION_AUTHORIZATION_MISSING"
    STRATEGY_APPROVAL_INVALID = "PAPER_INGESTION_STRATEGY_APPROVAL_INVALID"
    QUANTITY_APPROVAL_INVALID = "PAPER_INGESTION_QUANTITY_APPROVAL_INVALID"
    RISK_APPROVAL_INVALID = "PAPER_INGESTION_RISK_APPROVAL_INVALID"
    FINAL_APPROVAL_CHAIN_INCONSISTENT = "PAPER_INGESTION_APPROVAL_CHAIN_INCONSISTENT"
    FINAL_APPROVAL_EXPIRED = "PAPER_INGESTION_APPROVAL_EXPIRED"
    INPUT_STALE = "PAPER_INGESTION_INPUT_STALE"
    INPUT_DEGRADED = "PAPER_INGESTION_INPUT_DEGRADED"
    FUTURE_DATA_REJECTED = "PAPER_INGESTION_FUTURE_DATA_REJECTED"
    POLICY_NOT_FOUND = "PAPER_INGESTION_POLICY_NOT_FOUND"
    POLICY_MISMATCH = "PAPER_INGESTION_POLICY_MISMATCH"
    INVALID_COMMAND_COMPATIBILITY = "PAPER_INGESTION_COMMAND_COMPATIBILITY_INVALID"
    IDEMPOTENCY_CONFLICT = "PAPER_INGESTION_IDEMPOTENCY_CONFLICT"
    EXISTING_GRAPH_INCONSISTENT = "PAPER_INGESTION_EXISTING_GRAPH_INCONSISTENT"
    CONSTRAINT_VIOLATION = "PAPER_INGESTION_CONSTRAINT_VIOLATION"
    TRANSIENT_DB_FAILURE = "PAPER_INGESTION_TRANSIENT_DB_FAILURE"
    UNCERTAIN_COMMIT_RESOLVED_NOT_COMMITTED = (
        "PAPER_INGESTION_UNCERTAIN_COMMIT_NOT_COMMITTED"
    )
    UNCERTAIN_COMMIT_UNRESOLVED = "PAPER_INGESTION_UNCERTAIN_COMMIT_UNRESOLVED"
    INTERNAL_INVARIANT_FAILURE = "PAPER_INGESTION_INTERNAL_INVARIANT_FAILURE"


def _identity(value: object, field_name: str) -> str:
    try:
        return require_identity(value, field_name)
    except PaperDomainError as exc:
        raise ValueError(f"{field_name} must be a bounded public identity") from exc


def _epoch_ms(value: datetime) -> int:
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    delta = value - epoch
    return delta.days * 86_400_000 + delta.seconds * 1_000 + delta.microseconds // 1_000


def paper_ingestion_command_id(
    strategy_approval_id: str,
    quantity_approval_id: str,
    risk_approval_id: str,
) -> str:
    """Return the persisted command identity proof for the complete approvals."""

    parts = tuple(
        _identity(value, name)
        for value, name in (
            (strategy_approval_id, "strategy_approval_id"),
            (quantity_approval_id, "quantity_approval_id"),
            (risk_approval_id, "risk_approval_id"),
        )
    )
    canonical = "|".join(f"{len(value)}:{value}" for value in parts)
    digest = sha256(canonical.encode("ascii")).hexdigest()
    return f"paper:ingestion-command:{_INGESTION_IDENTITY_VERSION}:{digest}"


@dataclass(frozen=True, slots=True)
class PaperCommandIngestionRequest:
    paper_strategy_approval: PaperStrategyApproval
    paper_quantity_approval: PaperQuantityApproval
    paper_risk_approval: PaperRiskApproval
    simulation_policy: PaperFillSimulationPolicy
    execution_mode: object
    explicit_paper_authorization: bool
    command_id: str
    order_id: str
    command_event_id: str
    order_created_event_id: str
    order_validated_event_id: str
    order_opened_event_id: str
    journal_entry_ids: tuple[str, str, str, str]
    created_at: datetime
    correlation_id: str
    causation_id: str
    canary_id: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "command_id",
            "order_id",
            "command_event_id",
            "order_created_event_id",
            "order_validated_event_id",
            "order_opened_event_id",
            "correlation_id",
            "causation_id",
        ):
            object.__setattr__(self, name, _identity(getattr(self, name), name))
        if self.canary_id is not None:
            try:
                object.__setattr__(self, "canary_id", str(UUID(self.canary_id)))
            except (TypeError, ValueError, AttributeError) as exc:
                raise ValueError("canary_id must be a UUID") from exc
        if not isinstance(self.journal_entry_ids, tuple):
            raise TypeError("journal_entry_ids must be an immutable tuple")
        if len(self.journal_entry_ids) != _JOURNAL_COUNT:
            raise ValueError("exactly four journal_entry_ids are required")
        normalized = tuple(
            _identity(value, f"journal_entry_ids[{index}]")
            for index, value in enumerate(self.journal_entry_ids)
        )
        if len(set(normalized)) != _JOURNAL_COUNT:
            raise ValueError("journal_entry_ids must be unique")
        object.__setattr__(self, "journal_entry_ids", normalized)
        try:
            require_utc(self.created_at, "created_at")
        except PaperDomainError as exc:
            raise ValueError("created_at must be UTC") from exc


@dataclass(frozen=True, slots=True)
class PaperCommandIngestionResult:
    outcome: PaperCommandIngestionOutcome
    reason_code: str
    command_id: str
    order_id: str
    order_state: PaperOrderState | None = None
    order_version: int | None = None
    repository_outcome: RepositoryOutcome | None = None
    event_count: int = 0
    journal_count: int = 0
    simulation_policy_id: str | None = None

    @property
    def successful(self) -> bool:
        return self.outcome in {
            PaperCommandIngestionOutcome.COMMAND_AND_ORDER_CREATED,
            PaperCommandIngestionOutcome.COMMAND_AND_ORDER_ALREADY_EXIST,
            PaperCommandIngestionOutcome.UNCERTAIN_COMMIT_RESOLVED_COMMITTED,
        }


@dataclass(frozen=True, slots=True)
class _ExpectedIngestionGraph:
    command: PaperExecutionCommand
    created_order: PaperOrder
    open_order: PaperOrder
    order_events: tuple[PaperDomainEvent, PaperDomainEvent, PaperDomainEvent]
    journal: tuple[
        PaperDomainEvent,
        PaperDomainEvent,
        PaperDomainEvent,
        PaperDomainEvent,
    ]


@dataclass(frozen=True, slots=True)
class _RecoveryProbe:
    graph: PaperIngestionGraph | None
    classification: str


UowFactory: TypeAlias = Callable[[], PaperUnitOfWork]
SessionFactory: TypeAlias = Callable[[], Session]


_REPOSITORY_OUTCOME_MAP: Final = {
    RepositoryOutcome.IDEMPOTENCY_CONFLICT: (
        PaperCommandIngestionOutcome.IDEMPOTENCY_CONFLICT
    ),
    RepositoryOutcome.CONSTRAINT_VIOLATION: (
        PaperCommandIngestionOutcome.CONSTRAINT_VIOLATION
    ),
    RepositoryOutcome.TRANSIENT_DB_FAILURE: (
        PaperCommandIngestionOutcome.TRANSIENT_DB_FAILURE
    ),
    RepositoryOutcome.UNCERTAIN_COMMIT_RESOLVED_NOT_COMMITTED: (
        PaperCommandIngestionOutcome.UNCERTAIN_COMMIT_RESOLVED_NOT_COMMITTED
    ),
    RepositoryOutcome.UNCERTAIN_COMMIT_UNRESOLVED: (
        PaperCommandIngestionOutcome.UNCERTAIN_COMMIT_UNRESOLVED
    ),
    RepositoryOutcome.INTERNAL_INVARIANT_FAILURE: (
        PaperCommandIngestionOutcome.INTERNAL_INVARIANT_FAILURE
    ),
}


class PaperCommandIngestionService:
    """Create exactly one command and OPEN entry order in one explicit UoW."""

    def __init__(
        self,
        uow_factory: UowFactory,
        recovery_session_factory: SessionFactory,
    ) -> None:
        self._uow_factory = uow_factory
        self._recovery_session_factory = recovery_session_factory

    def ingest_and_create_entry_order(
        self, request: PaperCommandIngestionRequest
    ) -> PaperCommandIngestionResult:
        if not isinstance(request, PaperCommandIngestionRequest):
            raise TypeError("request must be PaperCommandIngestionRequest")
        validation = self._validate_request(request)
        if validation is not None:
            return validation
        try:
            expected = self._build_expected(request)
        except PaperDomainError:
            return self._failure(
                request,
                PaperCommandIngestionOutcome.INVALID_COMMAND_COMPATIBILITY,
                PaperCommandIngestionReasonCode.INVALID_COMMAND_COMPATIBILITY,
            )
        except Exception:
            return self._failure(
                request,
                PaperCommandIngestionOutcome.INTERNAL_INVARIANT_FAILURE,
                PaperCommandIngestionReasonCode.INTERNAL_INVARIANT_FAILURE,
            )

        uncertain = False
        try:
            with self._uow_factory() as uow:
                repositories = self._repositories(uow)
                policy_failure = self._validate_policy(
                    request,
                    repositories.policies.get_policy(
                        request.simulation_policy.simulation_policy_id,
                        policy_version=_POLICY_VERSION,
                    ),
                )
                if policy_failure is not None:
                    return policy_failure

                existing = repositories.commands.get_command_by_idempotency_key(
                    expected.command.idempotency_key
                )
                exact_command = repositories.commands.get_command(request.command_id)
                existing_order = repositories.orders.get_order(request.order_id)
                existing_order_key = repositories.orders.get_order_by_idempotency_key(
                    expected.created_order.idempotency_key
                )
                if existing is not None or exact_command is not None:
                    selected = existing or exact_command
                    assert selected is not None
                    if command_semantic_tuple(selected) != command_semantic_tuple(
                        expected.command
                    ):
                        return self._failure(
                            request,
                            PaperCommandIngestionOutcome.IDEMPOTENCY_CONFLICT,
                            PaperCommandIngestionReasonCode.IDEMPOTENCY_CONFLICT,
                        )
                    return self._existing_result(
                        request,
                        repositories.commands.get_ingestion_graph(
                            selected.command_id, limit=_COMMAND_GRAPH_LIMIT
                        ),
                        expected,
                    )
                if existing_order is not None or existing_order_key is not None:
                    return self._failure(
                        request,
                        PaperCommandIngestionOutcome.EXISTING_GRAPH_INCONSISTENT,
                        PaperCommandIngestionReasonCode.EXISTING_GRAPH_INCONSISTENT,
                    )

                command_result = repositories.commands.create_or_get_command(
                    expected.command,
                    event_id=request.command_event_id,
                    canary_id=request.canary_id,
                )
                if command_result.outcome is RepositoryOutcome.EXISTING_IDEMPOTENT:
                    return self._existing_result(
                        request,
                        repositories.commands.get_ingestion_graph(
                            expected.command.command_id, limit=_COMMAND_GRAPH_LIMIT
                        ),
                        expected,
                    )
                if command_result.outcome is not RepositoryOutcome.CREATED:
                    return self._repository_failure(request, command_result)
                repositories._fault("ingestion_after_command")

                created_event = expected.order_events[0]
                order_result = repositories.orders.create_or_get_order(
                    expected.command,
                    expected.created_order,
                    created_event,
                    expected.journal[1],
                    order_role="ENTRY",
                )
                if order_result.outcome is not RepositoryOutcome.CREATED:
                    return self._repository_failure(request, order_result)
                repositories._fault("ingestion_after_order_created")

                validated_result = repositories.orders.transition_order(
                    request.order_id,
                    0,
                    PaperOrderState.VALIDATED,
                    expected.order_events[1],
                    expected.journal[2],
                    occurred_at=request.created_at,
                )
                if validated_result.outcome is not RepositoryOutcome.UPDATED:
                    return self._repository_failure(request, validated_result)
                repositories._fault("ingestion_after_order_validated")

                opened_result = repositories.orders.transition_order(
                    request.order_id,
                    1,
                    PaperOrderState.OPEN,
                    expected.order_events[2],
                    expected.journal[3],
                    occurred_at=request.created_at,
                )
                if opened_result.outcome is not RepositoryOutcome.UPDATED:
                    return self._repository_failure(request, opened_result)
                repositories._fault("ingestion_after_order_opened")

                graph_result = repositories.commands.get_ingestion_graph(
                    request.command_id, limit=_COMMAND_GRAPH_LIMIT
                )
                classification = self._classify_graph(graph_result.value, expected)
                if classification != "MATCH":
                    return self._failure(
                        request,
                        PaperCommandIngestionOutcome.EXISTING_GRAPH_INCONSISTENT,
                        PaperCommandIngestionReasonCode.EXISTING_GRAPH_INCONSISTENT,
                    )
                commit = uow.commit()
                if commit.outcome is RepositoryOutcome.UPDATED:
                    return self._success(
                        request,
                        PaperCommandIngestionOutcome.COMMAND_AND_ORDER_CREATED,
                        RepositoryOutcome.CREATED,
                    )
                if commit.outcome is RepositoryOutcome.UNCERTAIN_COMMIT_UNRESOLVED:
                    uncertain = True
                else:
                    return self._repository_failure(request, commit)
        except Exception:
            return self._failure(
                request,
                PaperCommandIngestionOutcome.INTERNAL_INVARIANT_FAILURE,
                PaperCommandIngestionReasonCode.INTERNAL_INVARIANT_FAILURE,
            )

        if uncertain:
            return self._recover_uncertain(request, expected)
        return self._failure(
            request,
            PaperCommandIngestionOutcome.INTERNAL_INVARIANT_FAILURE,
            PaperCommandIngestionReasonCode.INTERNAL_INVARIANT_FAILURE,
        )

    def _validate_request(
        self, request: PaperCommandIngestionRequest
    ) -> PaperCommandIngestionResult | None:
        try:
            mode = ExecutionMode(request.execution_mode)
        except (TypeError, ValueError):
            return self._failure(
                request,
                PaperCommandIngestionOutcome.MODE_UNKNOWN,
                PaperCommandIngestionReasonCode.MODE_UNKNOWN,
            )
        if mode is ExecutionMode.OFF:
            return self._failure(
                request,
                PaperCommandIngestionOutcome.MODE_OFF,
                PaperCommandIngestionReasonCode.MODE_OFF,
            )
        if mode is ExecutionMode.LIVE:
            return self._failure(
                request,
                PaperCommandIngestionOutcome.MODE_LIVE_FORBIDDEN,
                PaperCommandIngestionReasonCode.MODE_LIVE_FORBIDDEN,
            )
        if request.explicit_paper_authorization is not True:
            return self._failure(
                request,
                PaperCommandIngestionOutcome.PAPER_AUTHORIZATION_MISSING,
                PaperCommandIngestionReasonCode.PAPER_AUTHORIZATION_MISSING,
            )
        strategy = request.paper_strategy_approval
        quantity = request.paper_quantity_approval
        risk = request.paper_risk_approval
        if not isinstance(strategy, PaperStrategyApproval):
            return self._failure(
                request,
                PaperCommandIngestionOutcome.STRATEGY_APPROVAL_INVALID,
                PaperCommandIngestionReasonCode.STRATEGY_APPROVAL_INVALID,
            )
        if not isinstance(quantity, PaperQuantityApproval):
            return self._failure(
                request,
                PaperCommandIngestionOutcome.QUANTITY_APPROVAL_INVALID,
                PaperCommandIngestionReasonCode.QUANTITY_APPROVAL_INVALID,
            )
        if not isinstance(risk, PaperRiskApproval):
            return self._failure(
                request,
                PaperCommandIngestionOutcome.RISK_APPROVAL_INVALID,
                PaperCommandIngestionReasonCode.RISK_APPROVAL_INVALID,
            )
        if not isinstance(request.simulation_policy, PaperFillSimulationPolicy):
            return self._failure(
                request,
                PaperCommandIngestionOutcome.POLICY_MISMATCH,
                PaperCommandIngestionReasonCode.POLICY_MISMATCH,
            )
        if strategy.future_bars_used is not False:
            return self._failure(
                request,
                PaperCommandIngestionOutcome.FUTURE_DATA_REJECTED,
                PaperCommandIngestionReasonCode.FUTURE_DATA_REJECTED,
            )
        raw_health = str(
            getattr(strategy.input_health_status, "value", strategy.input_health_status)
        ).upper()
        if "STALE" in raw_health:
            return self._failure(
                request,
                PaperCommandIngestionOutcome.INPUT_STALE,
                PaperCommandIngestionReasonCode.INPUT_STALE,
            )
        if strategy.input_health_status is not PaperInputHealthStatus.CURRENT:
            return self._failure(
                request,
                PaperCommandIngestionOutcome.INPUT_DEGRADED,
                PaperCommandIngestionReasonCode.INPUT_DEGRADED,
            )
        if (
            strategy.paper_execution_approved is not True
            or quantity.position_size_approved is not True
            or quantity.approval_source
            is not PaperQuantityApprovalSource.CONTROLLED_PAPER_AUTHORITY
            or (
                risk.order_approved,
                risk.execution_approved,
                risk.position_size_approved,
                risk.final_paper_approval,
            )
            != (True, True, True, True)
        ):
            outcome = (
                PaperCommandIngestionOutcome.STRATEGY_APPROVAL_INVALID
                if strategy.paper_execution_approved is not True
                else PaperCommandIngestionOutcome.QUANTITY_APPROVAL_INVALID
                if (
                    quantity.position_size_approved is not True
                    or quantity.approval_source
                    is not PaperQuantityApprovalSource.CONTROLLED_PAPER_AUTHORITY
                )
                else PaperCommandIngestionOutcome.RISK_APPROVAL_INVALID
            )
            reason = {
                PaperCommandIngestionOutcome.STRATEGY_APPROVAL_INVALID:
                    PaperCommandIngestionReasonCode.STRATEGY_APPROVAL_INVALID,
                PaperCommandIngestionOutcome.QUANTITY_APPROVAL_INVALID:
                    PaperCommandIngestionReasonCode.QUANTITY_APPROVAL_INVALID,
                PaperCommandIngestionOutcome.RISK_APPROVAL_INVALID:
                    PaperCommandIngestionReasonCode.RISK_APPROVAL_INVALID,
            }[outcome]
            return self._failure(
                request,
                outcome,
                reason,
            )
        if _epoch_ms(request.created_at) > min(
            strategy.valid_until_ms,
            quantity.valid_until_ms,
            risk.valid_until_ms,
        ):
            return self._failure(
                request,
                PaperCommandIngestionOutcome.FINAL_APPROVAL_EXPIRED,
                PaperCommandIngestionReasonCode.FINAL_APPROVAL_EXPIRED,
            )
        if (
            quantity.paper_strategy_approval_id != strategy.approval_id
            or risk.paper_strategy_approval_id != strategy.approval_id
            or risk.quantity_approval_id != quantity.quantity_approval_id
            or risk.research_risk_decision_id != quantity.research_risk_decision_id
            or risk.setup_id != strategy.setup_id
            or risk.pipeline_run_id != strategy.pipeline_run_id
            or risk.analysis_result_id != strategy.analysis_result_id
            or quantity.symbol != strategy.symbol
            or risk.symbol != strategy.symbol
            or quantity.side is not strategy.side
            or risk.side is not strategy.side
            or risk.approved_quantity != quantity.approved_quantity
            or quantity.configuration_fingerprint != strategy.configuration_fingerprint
            or risk.configuration_fingerprint != strategy.configuration_fingerprint
            or quantity.symbol_constraints_id != strategy.symbol_constraints_id
            or risk.symbol_constraints_id != strategy.symbol_constraints_id
        ):
            return self._failure(
                request,
                PaperCommandIngestionOutcome.FINAL_APPROVAL_CHAIN_INCONSISTENT,
                PaperCommandIngestionReasonCode.FINAL_APPROVAL_CHAIN_INCONSISTENT,
            )
        try:
            compatibility = map_final_approvals_to_command_compatibility(
                strategy, quantity, risk
            )
        except PaperDomainError:
            return self._failure(
                request,
                PaperCommandIngestionOutcome.FINAL_APPROVAL_CHAIN_INCONSISTENT,
                PaperCommandIngestionReasonCode.FINAL_APPROVAL_CHAIN_INCONSISTENT,
            )
        if (
            compatibility.final_paper_approval is not True
            or compatibility.paper_execution_approved is not True
            or compatibility.execution_approved is not True
            or compatibility.order_approved is not True
            or compatibility.position_size_approved is not True
        ):
            return self._failure(
                request,
                PaperCommandIngestionOutcome.INVALID_COMMAND_COMPATIBILITY,
                PaperCommandIngestionReasonCode.INVALID_COMMAND_COMPATIBILITY,
            )
        if (
            request.command_id
            != paper_ingestion_command_id(
                strategy.approval_id,
                quantity.quantity_approval_id,
                risk.approval_id,
            )
            or request.correlation_id != strategy.pipeline_run_id
            or request.causation_id != risk.approval_id
        ):
            return self._failure(
                request,
                PaperCommandIngestionOutcome.FINAL_APPROVAL_CHAIN_INCONSISTENT,
                PaperCommandIngestionReasonCode.FINAL_APPROVAL_CHAIN_INCONSISTENT,
            )
        if request.journal_entry_ids != (
            request.command_event_id,
            request.order_created_event_id,
            request.order_validated_event_id,
            request.order_opened_event_id,
        ):
            return self._failure(
                request,
                PaperCommandIngestionOutcome.INVALID_COMMAND_COMPATIBILITY,
                PaperCommandIngestionReasonCode.INVALID_COMMAND_COMPATIBILITY,
            )
        return None

    def _build_expected(
        self, request: PaperCommandIngestionRequest
    ) -> _ExpectedIngestionGraph:
        compatibility = map_final_approvals_to_command_compatibility(
            request.paper_strategy_approval,
            request.paper_quantity_approval,
            request.paper_risk_approval,
        )
        policy = request.simulation_policy
        command = PaperExecutionCommand(
            command_id=request.command_id,
            idempotency_key=command_idempotency_key(
                pipeline_run_id=compatibility.pipeline_run_id,
                analysis_result_id=compatibility.analysis_result_id,
                setup_id=compatibility.setup_id,
                strategy_decision_id=compatibility.strategy_decision_id,
                risk_decision_id=compatibility.risk_decision_id,
                symbol=compatibility.symbol,
                side=compatibility.side,
                closed_until_ms=compatibility.closed_until_ms,
                configuration_fingerprint=compatibility.configuration_fingerprint,
            ),
            mode=ExecutionMode.PAPER,
            symbol=compatibility.symbol,
            side=compatibility.side,
            order_type=PaperOrderType.MARKET_SIMULATED,
            requested_quantity=compatibility.approved_quantity,
            requested_notional=None,
            entry_reference_price=compatibility.entry_reference_price,
            stop_price=compatibility.stop_price,
            target_price=compatibility.target_price,
            strategy_decision_id=compatibility.strategy_decision_id,
            risk_decision_id=compatibility.risk_decision_id,
            setup_id=compatibility.setup_id,
            pipeline_run_id=compatibility.pipeline_run_id,
            analysis_result_id=compatibility.analysis_result_id,
            closed_until_ms=compatibility.closed_until_ms,
            created_at=request.created_at,
            valid_until_ms=compatibility.valid_until_ms,
            configuration_fingerprint=compatibility.configuration_fingerprint,
            simulation_policy_id=policy.simulation_policy_id,
            fee_policy_id=policy.fee_policy_id,
            slippage_policy_id=policy.slippage_policy_id,
            latency_policy_id=policy.latency_policy_id,
            final_paper_approval=True,
            input_health_status=PaperInputHealthStatus.CURRENT,
            future_bars_used=False,
        )
        command_event = command_created_event(
            command,
            event_id=request.command_event_id,
            occurred_at=request.created_at,
        )
        created = create_paper_order(
            command,
            order_id=request.order_id,
            idempotency_key=order_idempotency_key(command.command_id, "ENTRY"),
            occurred_at=request.created_at,
            event_id=request.order_created_event_id,
        )
        validated = transition_order(
            created.order,
            PaperOrderState.VALIDATED,
            expected_version=0,
            occurred_at=request.created_at,
            event_id=request.order_validated_event_id,
        )
        opened = transition_order(
            validated.order,
            PaperOrderState.OPEN,
            expected_version=1,
            occurred_at=request.created_at,
            event_id=request.order_opened_event_id,
        )
        return _ExpectedIngestionGraph(
            command=command,
            created_order=created.order,
            open_order=opened.order,
            order_events=(created.events[0], validated.events[0], opened.events[0]),
            journal=(
                command_event,
                created.events[0],
                validated.events[0],
                opened.events[0],
            ),
        )

    def _validate_policy(
        self,
        request: PaperCommandIngestionRequest,
        stored: PaperStoredSimulationPolicy | None,
    ) -> PaperCommandIngestionResult | None:
        if stored is None:
            return self._failure(
                request,
                PaperCommandIngestionOutcome.POLICY_NOT_FOUND,
                PaperCommandIngestionReasonCode.POLICY_NOT_FOUND,
            )
        policy = request.simulation_policy
        expected = (
            policy.simulation_policy_id,
            _POLICY_VERSION,
            "ACTIVE",
            policy.price_source.value,
            policy.timeframe,
            policy.latency_candles,
            policy.slippage_bps,
            policy.fee_bps,
            policy.partial_fill_enabled,
            policy.future_data_allowed,
            policy.intrabar_conflict_policy.value,
            request.paper_strategy_approval.configuration_fingerprint,
            None,
        )
        actual = (
            stored.policy_id,
            stored.policy_version,
            stored.status,
            stored.price_source,
            stored.timeframe,
            stored.latency_candles,
            stored.slippage_bps,
            stored.fee_bps,
            stored.partial_fill_enabled,
            stored.future_data_allowed,
            stored.intrabar_conflict_policy,
            stored.configuration_fingerprint,
            stored.retired_at,
        )
        if actual != expected:
            return self._failure(
                request,
                PaperCommandIngestionOutcome.POLICY_MISMATCH,
                PaperCommandIngestionReasonCode.POLICY_MISMATCH,
            )
        return None

    def _existing_result(
        self,
        request: PaperCommandIngestionRequest,
        repository_result: RepositoryResult[PaperIngestionGraph],
        expected: _ExpectedIngestionGraph,
    ) -> PaperCommandIngestionResult:
        classification = self._classify_graph(repository_result.value, expected)
        if classification == "MATCH":
            return self._success(
                request,
                PaperCommandIngestionOutcome.COMMAND_AND_ORDER_ALREADY_EXIST,
                RepositoryOutcome.EXISTING_IDEMPOTENT,
            )
        outcome = (
            PaperCommandIngestionOutcome.IDEMPOTENCY_CONFLICT
            if classification == "CONFLICT"
            else PaperCommandIngestionOutcome.EXISTING_GRAPH_INCONSISTENT
        )
        reason = (
            PaperCommandIngestionReasonCode.IDEMPOTENCY_CONFLICT
            if classification == "CONFLICT"
            else PaperCommandIngestionReasonCode.EXISTING_GRAPH_INCONSISTENT
        )
        return self._failure(request, outcome, reason)

    @staticmethod
    def _classify_graph(
        graph: PaperIngestionGraph | None,
        expected: _ExpectedIngestionGraph,
    ) -> str:
        if graph is None:
            return "PARTIAL"
        if command_semantic_tuple(graph.command) != command_semantic_tuple(
            expected.command
        ):
            return "CONFLICT"
        if graph.order is None or graph.order_role != "ENTRY":
            return "PARTIAL"
        if order_semantic_tuple(graph.order) != order_semantic_tuple(
            expected.created_order
        ):
            return "CONFLICT"
        if (
            graph.order != expected.open_order
            or len(graph.order_events) != _ORDER_EVENT_COUNT
            or len(graph.journal) != _JOURNAL_COUNT
        ):
            return "PARTIAL"
        if tuple(map(journal_semantic_tuple, graph.order_events)) != tuple(
            map(journal_semantic_tuple, expected.order_events)
        ):
            return "PARTIAL"
        if sorted(map(journal_semantic_tuple, graph.journal), key=repr) != sorted(
            map(journal_semantic_tuple, expected.journal), key=repr
        ):
            return "PARTIAL"
        return "MATCH"

    def _recover_uncertain(
        self,
        request: PaperCommandIngestionRequest,
        expected: _ExpectedIngestionGraph,
    ) -> PaperCommandIngestionResult:
        expected_probe = _RecoveryProbe(None, "MATCH")
        recovery = recover_uncertain_commit(
            self._recovery_session_factory,
            lambda session: self._recovery_probe(session, request, expected),
            expected_probe,
            lambda found, _: found.classification == "MATCH",
            attempts=3,
        )
        if recovery.outcome is RepositoryOutcome.UNCERTAIN_COMMIT_RESOLVED_COMMITTED:
            return self._success(
                request,
                PaperCommandIngestionOutcome.UNCERTAIN_COMMIT_RESOLVED_COMMITTED,
                recovery.outcome,
            )
        if (
            recovery.outcome is RepositoryOutcome.IDEMPOTENCY_CONFLICT
            and recovery.value is not None
            and recovery.value.classification == "PARTIAL"
        ):
            return self._failure(
                request,
                PaperCommandIngestionOutcome.EXISTING_GRAPH_INCONSISTENT,
                PaperCommandIngestionReasonCode.EXISTING_GRAPH_INCONSISTENT,
                repository_outcome=recovery.outcome,
            )
        return self._repository_failure(request, recovery)

    @staticmethod
    def _recovery_probe(
        session: Session,
        request: PaperCommandIngestionRequest,
        expected: _ExpectedIngestionGraph,
    ) -> _RecoveryProbe | None:
        repositories = PaperRepositories(session)
        command = repositories.commands.get_command_by_idempotency_key(
            expected.command.idempotency_key
        )
        exact = repositories.commands.get_command(request.command_id)
        order = repositories.orders.get_order(request.order_id)
        order_key = repositories.orders.get_order_by_idempotency_key(
            expected.created_order.idempotency_key
        )
        if command is None and exact is None:
            if order is not None or order_key is not None:
                return _RecoveryProbe(None, "PARTIAL")
            return None
        selected = command or exact
        assert selected is not None
        graph_result = repositories.commands.get_ingestion_graph(
            selected.command_id, limit=MAX_GRAPH_ROWS
        )
        classification = PaperCommandIngestionService._classify_graph(
            graph_result.value, expected
        )
        return _RecoveryProbe(graph_result.value, classification)

    @staticmethod
    def _repositories(uow: PaperUnitOfWork) -> PaperRepositories:
        repositories = uow.repositories
        if not isinstance(repositories, PaperRepositories):
            raise RuntimeError("PAPER_UOW_REPOSITORIES_UNAVAILABLE")
        return repositories

    def _repository_failure(
        self,
        request: PaperCommandIngestionRequest,
        repository_result: RepositoryResult,
    ) -> PaperCommandIngestionResult:
        outcome = _REPOSITORY_OUTCOME_MAP.get(
            repository_result.outcome,
            PaperCommandIngestionOutcome.INTERNAL_INVARIANT_FAILURE,
        )
        reason = {
            PaperCommandIngestionOutcome.IDEMPOTENCY_CONFLICT:
                PaperCommandIngestionReasonCode.IDEMPOTENCY_CONFLICT,
            PaperCommandIngestionOutcome.CONSTRAINT_VIOLATION:
                PaperCommandIngestionReasonCode.CONSTRAINT_VIOLATION,
            PaperCommandIngestionOutcome.TRANSIENT_DB_FAILURE:
                PaperCommandIngestionReasonCode.TRANSIENT_DB_FAILURE,
            PaperCommandIngestionOutcome.UNCERTAIN_COMMIT_RESOLVED_NOT_COMMITTED:
                PaperCommandIngestionReasonCode.UNCERTAIN_COMMIT_RESOLVED_NOT_COMMITTED,
            PaperCommandIngestionOutcome.UNCERTAIN_COMMIT_UNRESOLVED:
                PaperCommandIngestionReasonCode.UNCERTAIN_COMMIT_UNRESOLVED,
        }.get(outcome, PaperCommandIngestionReasonCode.INTERNAL_INVARIANT_FAILURE)
        return self._failure(
            request,
            outcome,
            reason,
            repository_outcome=repository_result.outcome,
        )

    @staticmethod
    def _success(
        request: PaperCommandIngestionRequest,
        outcome: PaperCommandIngestionOutcome,
        repository_outcome: RepositoryOutcome,
    ) -> PaperCommandIngestionResult:
        return PaperCommandIngestionResult(
            outcome=outcome,
            reason_code=PaperCommandIngestionReasonCode.OK.value,
            command_id=request.command_id,
            order_id=request.order_id,
            order_state=PaperOrderState.OPEN,
            order_version=2,
            repository_outcome=repository_outcome,
            event_count=_ORDER_EVENT_COUNT,
            journal_count=_JOURNAL_COUNT,
            simulation_policy_id=request.simulation_policy.simulation_policy_id,
        )

    @staticmethod
    def _failure(
        request: PaperCommandIngestionRequest,
        outcome: PaperCommandIngestionOutcome,
        reason_code: PaperCommandIngestionReasonCode | str,
        *,
        repository_outcome: RepositoryOutcome | None = None,
    ) -> PaperCommandIngestionResult:
        policy = request.simulation_policy
        policy_id = (
            policy.simulation_policy_id
            if isinstance(policy, PaperFillSimulationPolicy)
            else None
        )
        return PaperCommandIngestionResult(
            outcome=outcome,
            reason_code=str(getattr(reason_code, "value", reason_code))[:96],
            command_id=request.command_id,
            order_id=request.order_id,
            repository_outcome=repository_outcome,
            simulation_policy_id=policy_id,
        )
