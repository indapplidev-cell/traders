"""Production PAPER-only bridge from Operator Control START to ingestion."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256

from app.engine_paper.command_ingestion_service import (
    PaperCommandIngestionRequest,
    PaperCommandIngestionService,
    paper_ingestion_command_id,
)
from app.engine_paper.fill_policy import (
    PaperFillPriceSource,
    PaperFillSimulationPolicy,
    PaperIntrabarConflictPolicy,
)
from app.engine_paper.first_canary_correlation import SqlAlchemyPaperFirstCanaryStore
from app.engine_paper.eligible_approval_ranking import (
    EligibleApprovalSelectionResult,
    ProductionEligibleApprovalSelector,
)
from app.engine_paper.production_approval import (
    EXECUTION_PROFILE_BY_TIMEFRAME,
    EXECUTION_TIMEFRAMES,
    PaperProductionApprovalRequest,
    PaperProductionApprovalScope,
    PaperProductionApprovalSourceAdapter,
)
from app.engine_safety.paper_domain import ExecutionMode
from app.engine_safety.paper_production_control import (
    MutationPrerequisites,
    MutationStage,
    PaperProductionMutationSafetyGate,
    PaperProductionMutationTarget,
    PaperProductionSafetyControl,
    PersistentState,
    SafetyControlError,
)

from .schemas import PaperCanaryNormalizedState, PaperOperatorCanaryStatus


def _id(request_id: str, role: str) -> str:
    digest = sha256(f"{request_id}|{role}".encode("ascii")).hexdigest()
    return f"paper:first-canary:{role}:{digest}"


def _foundation_policy() -> PaperFillSimulationPolicy:
    quantum = Decimal("0.00000001")
    return PaperFillSimulationPolicy(
        simulation_policy_id="simulation:foundation:v1",
        fee_policy_id="fee:quote:10bps:v1",
        slippage_policy_id="slippage:adverse:2bps:v1",
        latency_policy_id="latency:one-closed-1m:v1",
        price_source=PaperFillPriceSource.NEXT_ELIGIBLE_CLOSED_1M_OPEN,
        timeframe="1m",
        latency_candles=1,
        slippage_bps=Decimal("2"),
        fee_bps=Decimal("10"),
        partial_fill_enabled=False,
        future_data_allowed=False,
        intrabar_conflict_policy=PaperIntrabarConflictPolicy.STOP_FIRST_CONSERVATIVE,
        price_quantum=quantum,
        fee_quantum=quantum,
        contract_version="PAPER_FILL_SIMULATION_V1",
    )


@dataclass(frozen=True, slots=True)
class ExistingCanaryRuntimeReadiness:
    """Current infrastructure gates for an already-authorized PAPER canary."""

    market_data_ready: bool = False
    approval_source_ready: bool = False
    wal_ready: bool = False
    pitr_ready: bool = False
    live_disabled: bool = True

    @property
    def backup_pitr_pass(self) -> bool:
        return self.wal_ready and self.pitr_ready


class ProductionPaperFirstCanaryExecutor:
    """One-command maximum, simulated-only production first-canary executor."""

    def __init__(
        self,
        *,
        control: PaperProductionSafetyControl,
        canary_store: SqlAlchemyPaperFirstCanaryStore,
        approval_source: PaperProductionApprovalSourceAdapter,
        ingestion_service: PaperCommandIngestionService,
        mutation_safety_gate: PaperProductionMutationSafetyGate,
        runtime_readiness: Callable[[], ExistingCanaryRuntimeReadiness],
        selector: ProductionEligibleApprovalSelector | None = None,
    ) -> None:
        self._control = control
        self._canary_store = canary_store
        self._approval_source = approval_source
        self._ingestion_service = ingestion_service
        self._mutation_safety_gate = mutation_safety_gate
        self._runtime_readiness = runtime_readiness
        self._selector = selector or ProductionEligibleApprovalSelector()
        self._prepared = None
        self.last_selection_diagnostics = None

    def _validate_boundary(self, transition_id: str, generation: int):
        state = self._control.read_authoritative()
        canary = self._canary_store.current()
        if (
            state.state is not PersistentState.ARMED
            or state.transition_id != transition_id
            or state.generation != generation
            or canary is None
            or canary.arming_transition_id != transition_id
            or canary.arming_generation != generation
            or canary.mode != "PAPER"
            or canary.max_new_commands != 1
            or canary.max_open_positions != 1
            or canary.command_count not in (0, 1)
            or canary.position_count not in (0, 1)
        ):
            return None
        return canary

    def _read_approvals(self, canary, request_id: str):
        """Read every executable profile at one causal wall-clock boundary."""
        as_of_ms = None
        results = []
        for timeframe in EXECUTION_TIMEFRAMES:
            result = self._approval_source.read(PaperProductionApprovalRequest(
                PaperProductionApprovalScope(
                    symbols=canary.allowed_symbols,
                    primary_timeframe=timeframe,
                    max_candidates=len(canary.allowed_symbols),
                ),
                request_id=f"{request_id}:{timeframe}",
                as_of_ms=as_of_ms,
            ))
            results.append(result)
            if as_of_ms is None:
                as_of_ms = result.as_of_ms
        return tuple(results)

    def _select_candidate(self, canary, results) -> EligibleApprovalSelectionResult:
        candidates = tuple(
            value.candidate for result in results for value in result.symbol_results
            if value.candidate is not None
        )
        selection = self._selector.select(
            candidates, policy_version=canary.selection_policy_version
        )
        self.last_selection_diagnostics = selection.diagnostics
        return selection

    @staticmethod
    def _approval_source_error(results) -> tuple[str, ...]:
        unhealthy = tuple(
            result for result in results
            if result.readiness.value not in {"READY", "HEALTHY_NO_ELIGIBLE_APPROVAL"}
        )
        if unhealthy:
            codes = tuple(dict.fromkeys(
                finding.code.value for result in unhealthy for finding in result.findings
            ))
            return codes or ("APPROVAL_SOURCE_NOT_READY",)
        if not any(
            value.candidate is not None
            for result in results for value in result.symbol_results
        ):
            return ("NO_ELIGIBLE_APPROVAL",)
        return ()

    def preflight(self, *, transition_id: str, generation: int) -> tuple[str, ...]:
        canary = self._validate_boundary(transition_id, generation)
        if canary is None:
            return ("CANARY_NOT_ARMED",)
        results = self._read_approvals(canary, _id(canary.canary_id, "approval-preflight"))
        errors = self._approval_source_error(results)
        if errors:
            return errors
        selection = self._select_candidate(canary, results)
        if selection.failure_code is not None or selection.winner is None:
            return (selection.failure_code or "APPROVAL_SOURCE_NOT_READY",)
        self._prepared = (canary.canary_id, transition_id, generation, selection.winner)
        return ()

    def start_bounded_canary(
        self, *, request_id: str, canary_id: str, transition_id: str, generation: int
    ) -> tuple[str, ...]:
        canary = self._validate_boundary(transition_id, generation)
        if canary is None or canary.canary_id != canary_id:
            return ("CANARY_NOT_ARMED",)
        candidate = None
        if self._prepared is not None and self._prepared[:3] == (canary_id, transition_id, generation):
            candidate = self._prepared[3]
        if candidate is None:
            results = self._read_approvals(canary, _id(request_id, "approval-start"))
            errors = self._approval_source_error(results)
            if errors:
                return errors
            selection = self._select_candidate(canary, results)
            if selection.failure_code is not None or selection.winner is None:
                return (selection.failure_code or "APPROVAL_SOURCE_NOT_READY",)
            candidate = selection.winner
        return self._ingest_candidate(
            candidate=candidate, request_id=request_id, canary_id=canary_id
        )

    def continue_waiting_canary(self, canary_id: str) -> tuple[str, ...]:
        """Continue the original START lineage without creating another START."""

        canary = self._canary_store.get(canary_id)
        if (
            canary is None
            or canary.state.value != "NO_ELIGIBLE_APPROVAL"
            or canary.started_at is None
            or canary.start_request_id is None
            or canary.command_count != 0
            or canary.position_count != 0
        ):
            return ("CANARY_NOT_WAITING",)
        validated = self._validate_boundary(
            canary.arming_transition_id or "", canary.arming_generation or 0
        )
        if validated is None or validated.canary_id != canary_id:
            return ("CANARY_NOT_ARMED",)
        results = self._read_approvals(
            validated, _id(canary.start_request_id, "approval-continuation")
        )
        errors = self._approval_source_error(results)
        if errors:
            return errors
        selection = self._select_candidate(validated, results)
        if selection.failure_code is not None or selection.winner is None:
            return (selection.failure_code or "APPROVAL_SOURCE_NOT_READY",)
        return self._ingest_candidate(
            candidate=selection.winner,
            request_id=canary.start_request_id,
            canary_id=canary_id,
        )

    def _ingest_candidate(self, *, candidate, request_id: str, canary_id: str) -> tuple[str, ...]:
        canary = self._canary_store.get(canary_id)
        if canary is None:
            return ("CANARY_NOT_ARMED",)
        expected_profile = EXECUTION_PROFILE_BY_TIMEFRAME.get(
            getattr(candidate, "primary_timeframe", "")
        )
        if (
            expected_profile is None
            or getattr(candidate, "trade_profile_id", "") != expected_profile
            or candidate.watermark.primary_timeframe != candidate.primary_timeframe
            or candidate.lineage.source_run_id != candidate.ranking.source_run_id
        ):
            return ("APPROVAL_PROFILE_IDENTITY_MISMATCH",)
        readiness = self._runtime_readiness()
        command_id = paper_ingestion_command_id(
            candidate.paper_strategy_approval.approval_id,
            candidate.paper_quantity_approval.quantity_approval_id,
            candidate.paper_risk_approval.approval_id,
        )
        created_at = candidate.paper_risk_approval.approved_at
        request = PaperCommandIngestionRequest(
            paper_strategy_approval=candidate.paper_strategy_approval,
            paper_quantity_approval=candidate.paper_quantity_approval,
            paper_risk_approval=candidate.paper_risk_approval,
            simulation_policy=_foundation_policy(), execution_mode=ExecutionMode.PAPER,
            explicit_paper_authorization=True, command_id=command_id,
            order_id=_id(request_id, "entry-order"),
            command_event_id=_id(request_id, "command-event"),
            order_created_event_id=_id(request_id, "order-created-event"),
            order_validated_event_id=_id(request_id, "order-validated-event"),
            order_opened_event_id=_id(request_id, "order-opened-event"),
            journal_entry_ids=(
                _id(request_id, "command-event"), _id(request_id, "order-created-event"),
                _id(request_id, "order-validated-event"), _id(request_id, "order-opened-event"),
            ),
            created_at=created_at,
            correlation_id=candidate.paper_strategy_approval.correlation_id,
            causation_id=candidate.paper_risk_approval.approval_id, canary_id=canary_id,
        )
        target = PaperProductionMutationTarget(
            environment=canary.environment, mode=canary.mode, symbol=candidate.symbol,
            candidate_identity=candidate.candidate_id,
            current_generation=canary.current_control_generation,
            new_commands_before=canary.command_count,
            open_positions_before=canary.position_count,
        )
        prerequisites = MutationPrerequisites(
            market_data_ready=(
                readiness.market_data_ready and readiness.approval_source_ready
            ),
            approval_candidate_eligible=True,
            backup_pitr_pass=readiness.backup_pitr_pass,
            paper_target_authorized=True,
            live_disabled=readiness.live_disabled,
        )
        try:
            with self._mutation_safety_gate.authorize_mutation(
                MutationStage.COMMAND_INGESTION, target, prerequisites
            ):
                result = self._ingestion_service.ingest_and_create_entry_order(request)
        except SafetyControlError as error:
            code = str(error)
            if code in {
                "MUTATION_DENIED_DISABLED", "MUTATION_DENIED_EMERGENCY_STOP",
                "STALE_GENERATION", "INDEPENDENT_READINESS_GATE_DENIED",
                "SYMBOL_SCOPE_DENIED", "NEW_COMMAND_BUDGET_EXHAUSTED",
                "OPEN_POSITION_BUDGET_EXHAUSTED", "INVALID_MUTATION_COUNTER",
                "INVALID_CANDIDATE_IDENTITY", "LIVE_OR_NON_PRODUCTION_TARGET_DENIED",
            }:
                return (code,)
            raise
        return () if result.successful else (str(result.reason_code),)

    def status(self) -> PaperOperatorCanaryStatus:
        canary = self._canary_store.current()
        if canary is None:
            return PaperOperatorCanaryStatus(
                state=PaperCanaryNormalizedState.NOT_CONFIGURED,
                availability_code="NO_ACTIVE_CANARY",
                deployment_status="DEPLOYED",
            )
        waiting = canary.state.value == "NO_ELIGIBLE_APPROVAL"
        return PaperOperatorCanaryStatus(
            canary_id=canary.canary_id,
            state=(PaperCanaryNormalizedState.WAITING_FOR_ELIGIBLE_APPROVAL if waiting
                   else PaperCanaryNormalizedState(canary.state.value)),
            availability_code=("NO_ELIGIBLE_APPROVAL" if waiting else "AVAILABLE"),
            deployment_status="DEPLOYED",
            selection_policy_version=canary.selection_policy_version,
            live_allowed=False,
            binance_order_calls_allowed=False,
        )


__all__ = ("ExistingCanaryRuntimeReadiness", "ProductionPaperFirstCanaryExecutor")
