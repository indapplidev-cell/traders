"""Production PAPER-only bridge from Operator Control START to ingestion."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from types import SimpleNamespace

from app.engine_paper.command_ingestion_service import (
    PaperCommandIngestionRequest,
    PaperCommandIngestionService,
    paper_ingestion_command_id,
)
from app.engine_paper.continuous_authority import (
    ACTIVE_STATE,
    ContinuousAuthorityError,
    PaperContinuousAuthorityStore,
)
from app.engine_paper.fill_policy import (
    PaperFillPriceSource,
    PaperFillSimulationPolicy,
    PaperIntrabarConflictPolicy,
)
from app.engine_paper.first_canary_correlation import (
    CanaryCorrelationError,
    SqlAlchemyPaperFirstCanaryStore,
    continuous_cycle_id,
)
from app.engine_paper.plan_execution_outcome import PaperPlanExecutionOutcomeStore
from app.engine_paper.eligible_approval_ranking import (
    EligibleApprovalSelectionResult,
    ProductionEligibleApprovalSelector,
)
from app.engine_paper.production_approval import (
    EXECUTION_PROFILES_BY_TIMEFRAME,
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


FOUNDATION_SIMULATION_POLICY_ID = "simulation:foundation:v1"
SCALPING_V2_SIMULATION_POLICY_ID = "simulation:scalping-v2:foundation:v1"


def _foundation_policy(
    simulation_policy_id: str = FOUNDATION_SIMULATION_POLICY_ID,
) -> PaperFillSimulationPolicy:
    quantum = Decimal("0.00000001")
    return PaperFillSimulationPolicy(
        simulation_policy_id=simulation_policy_id,
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
    policy_blockers: tuple[str, ...] = ()
    snapshot_authoritative: bool = True
    control_generation: int | None = None
    reason_source: str = "READONLY_PAPER_READINESS_CURRENT_SNAPSHOT"

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
        outcome_store: PaperPlanExecutionOutcomeStore | None = None,
        continuous_store: PaperContinuousAuthorityStore | None = None,
    ) -> None:
        self._control = control
        self._canary_store = canary_store
        self._approval_source = approval_source
        self._ingestion_service = ingestion_service
        self._mutation_safety_gate = mutation_safety_gate
        self._runtime_readiness = runtime_readiness
        self._selector = selector or ProductionEligibleApprovalSelector()
        self._outcome_store = outcome_store
        self._continuous_store = continuous_store
        self._prepared = None
        self.last_selection_diagnostics = None

    def _validate_boundary(self, transition_id: str, generation: int):
        state = self._control.read_authoritative()
        canary = self._canary_store.current()
        continuous = (
            state.state is PersistentState.CONTINUOUS_ARMED
            and canary is not None
            and canary.authority_mode == "CONTINUOUS"
            and state.generation == generation
            and canary.current_control_generation == generation
        )
        legacy = (
            state.state is PersistentState.ARMED
            and state.transition_id == transition_id
            and state.generation == generation
            and canary is not None
            and canary.authority_mode == "FIRST_CANARY_HISTORICAL"
            and canary.arming_transition_id == transition_id
            and canary.arming_generation == generation
        )
        if (
            not (continuous or legacy)
            or canary is None
            or canary.mode != "PAPER"
            or canary.max_new_commands != 1
            or canary.max_open_positions != 1
            or canary.command_count not in (0, 1)
            or canary.position_count not in (0, 1)
        ):
            return None
        return canary

    def _read_approvals(self, canary, request_id: str, *, timeframes=None):
        """Read every executable profile at one causal wall-clock boundary."""
        as_of_ms = None
        results = []
        for timeframe in (EXECUTION_TIMEFRAMES if timeframes is None else timeframes):
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

    def _select_candidate(
        self, canary, results, *, exclude_executed: bool = False,
    ) -> EligibleApprovalSelectionResult:
        candidates = tuple(
            value.candidate for result in results for value in result.symbol_results
            if value.candidate is not None
        )
        if exclude_executed and self._outcome_store is not None:
            candidates = self._outcome_store.unconsumed_candidates(candidates)
        selection = self._selector.select(
            candidates, policy_version=canary.selection_policy_version
        )
        self.last_selection_diagnostics = selection.diagnostics
        if self._outcome_store is not None and selection.failure_code is None and candidates:
            self._outcome_store.observe_selection(
                candidates,
                selection,
                universe_id=canary.universe_version_id,
                control_generation=canary.current_control_generation,
            )
        return selection

    def expire_due_outcomes(self) -> int:
        if self._outcome_store is None:
            return 0
        return self._outcome_store.expire_due(
            int(datetime.now(timezone.utc).timestamp() * 1000)
        )

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

    def execute_continuous_once(self) -> tuple[str, ...]:
        """Select and dispatch at most one fresh v2 winner for this poll cycle."""

        if self._continuous_store is None:
            return ("CONTINUOUS_CONTROL_NOT_CONFIGURED",)
        state = self._control.read_authoritative()
        if state.state is not PersistentState.CONTINUOUS_ARMED or state.arming_scope is None:
            return (f"MUTATION_DENIED_{state.state.value}",)
        try:
            budget = self._continuous_store.reconcile(generation=state.generation)
        except ContinuousAuthorityError as error:
            return (str(error),)
        if budget.control_state != ACTIVE_STATE or not budget.enabled:
            return (budget.pause_reason or "CONTINUOUS_CONTROL_NOT_ARMED",)
        if budget.budget_reason is not None:
            return (budget.budget_reason,)
        if budget.open_positions >= 1 or budget.in_flight_commands >= 1:
            return ("OPEN_POSITION_BUDGET_EXHAUSTED",)
        authority = SimpleNamespace(
            allowed_symbols=state.arming_scope.allowed_symbols,
            selection_policy_version="eligible-approval-ranking-v1",
            universe_version_id="trading-universe-v2",
            current_control_generation=state.generation,
        )
        request_id = _id(str(state.generation), "continuous-approval-poll")
        results = self._read_approvals(authority, request_id, timeframes=("5m",))
        active_cycle = self._canary_store.current()
        errors = self._approval_source_error(results)
        if errors:
            if (
                errors == ("NO_ELIGIBLE_APPROVAL",)
                and active_cycle is not None
                and active_cycle.authority_mode == "CONTINUOUS"
                and active_cycle.command_id is None
            ):
                self._canary_store.fail_safe(
                    active_cycle.canary_id, "CONTINUOUS_RESERVED_APPROVAL_EXPIRED"
                )
            return errors
        if (
            active_cycle is not None
            and active_cycle.authority_mode == "CONTINUOUS"
            and active_cycle.command_id is None
        ):
            candidates = tuple(
                value.candidate for result in results for value in result.symbol_results
                if value.candidate is not None
                and continuous_cycle_id(state.generation, value.candidate.candidate_id)
                == active_cycle.canary_id
            )
            if len(candidates) != 1:
                self._canary_store.fail_safe(
                    active_cycle.canary_id, "CONTINUOUS_RESERVED_APPROVAL_NOT_CURRENT"
                )
                return ("CONTINUOUS_RESERVED_APPROVAL_NOT_CURRENT",)
            selection = self._selector.select(
                candidates, policy_version=authority.selection_policy_version
            )
            self.last_selection_diagnostics = selection.diagnostics
            if selection.failure_code is not None or selection.winner is None:
                return (selection.failure_code or "CONTINUOUS_RESERVED_APPROVAL_NOT_CURRENT",)
            if self._outcome_store is not None:
                self._outcome_store.observe_selection(
                    candidates,
                    selection,
                    universe_id=authority.universe_version_id,
                    control_generation=authority.current_control_generation,
                )
            candidate = selection.winner
        else:
            selection = self._select_candidate(authority, results, exclude_executed=True)
            if selection.failure_code is not None or selection.winner is None:
                return (selection.failure_code or "NO_ELIGIBLE_APPROVAL",)
            candidate = selection.winner
        if getattr(candidate, "trade_profile_id", None) != "trade-5m-v2":
            return ("SCALPING_V2_AUTHORITY_REQUIRED",)
        if active_cycle is not None and active_cycle.canary_id == continuous_cycle_id(
            state.generation, candidate.candidate_id
        ):
            canary = active_cycle
        else:
            try:
                canary = self._canary_store.reserve_continuous_cycle(
                    candidate_identity=candidate.candidate_id,
                    generation=state.generation,
                    control_transition_id=state.transition_id,
                    allowed_symbols=state.arming_scope.allowed_symbols,
                    now=datetime.now(timezone.utc),
                )
            except CanaryCorrelationError as error:
                return (str(error),)
        findings = self._ingest_candidate(
            candidate=candidate,
            request_id=canary.start_request_id or canary.arm_request_id,
            canary_id=canary.canary_id,
        )
        return findings

    def _ingest_candidate(self, *, candidate, request_id: str, canary_id: str) -> tuple[str, ...]:
        canary = self._canary_store.get(canary_id)
        if canary is None:
            return ("CANARY_NOT_ARMED",)
        expected_profiles = EXECUTION_PROFILES_BY_TIMEFRAME.get(
            getattr(candidate, "primary_timeframe", "")
        )
        if (
            expected_profiles is None
            or getattr(candidate, "trade_profile_id", "") not in expected_profiles
            or (canary.authority_mode == "CONTINUOUS" and getattr(candidate, "trade_profile_id", "") != "trade-5m-v2")
            or candidate.watermark.primary_timeframe != candidate.primary_timeframe
            or candidate.lineage.source_run_id != candidate.ranking.source_run_id
        ):
            if self._outcome_store is not None:
                try:
                    self._outcome_store.record_attempt(
                        candidate.lineage.source_run_id,
                        failure_code="NOT_CREATED_IDENTITY_MISMATCH",
                    )
                except ValueError as error:
                    if str(error) != "PAPER_PLAN_OUTCOME_NOT_OBSERVED":
                        raise
            return ("APPROVAL_PROFILE_IDENTITY_MISMATCH",)
        readiness = self._runtime_readiness()
        command_id = paper_ingestion_command_id(
            candidate.paper_strategy_approval.approval_id,
            candidate.paper_quantity_approval.quantity_approval_id,
            candidate.paper_risk_approval.approval_id,
        )
        created_at = candidate.paper_risk_approval.approved_at
        simulation_policy_id = (
            SCALPING_V2_SIMULATION_POLICY_ID
            if candidate.trade_profile_id == "trade-5m-v2"
            else FOUNDATION_SIMULATION_POLICY_ID
        )
        request = PaperCommandIngestionRequest(
            paper_strategy_approval=candidate.paper_strategy_approval,
            paper_quantity_approval=candidate.paper_quantity_approval,
            paper_risk_approval=candidate.paper_risk_approval,
            simulation_policy=_foundation_policy(simulation_policy_id),
            execution_mode=ExecutionMode.PAPER,
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
        continuous_budget = None
        if canary.authority_mode == "CONTINUOUS":
            if self._continuous_store is None:
                return ("CONTINUOUS_CONTROL_NOT_CONFIGURED",)
            continuous_budget = self._continuous_store.read()
            if continuous_budget is None or continuous_budget.budget_reason is not None:
                return (("CONTINUOUS_CONTROL_NOT_CONFIGURED" if continuous_budget is None else continuous_budget.budget_reason),)
        target = PaperProductionMutationTarget(
            environment=canary.environment, mode=canary.mode, symbol=candidate.symbol,
            candidate_identity=candidate.candidate_id,
            current_generation=canary.current_control_generation,
            new_commands_before=(0 if continuous_budget is not None else canary.command_count),
            open_positions_before=(continuous_budget.open_positions if continuous_budget is not None else canary.position_count),
        )
        snapshot_blockers = tuple(dict.fromkeys(readiness.policy_blockers))
        if not readiness.snapshot_authoritative:
            blockers = snapshot_blockers or ("READONLY_RUNTIME_NOT_READY",)
            if self._outcome_store is not None:
                self._outcome_store.record_attempt(
                    candidate.lineage.source_run_id,
                    blocker_codes=blockers,
                )
            return blockers
        if (
            readiness.control_generation is not None
            and readiness.control_generation != canary.current_control_generation
        ):
            blockers = ("READINESS_CONTROL_GENERATION_MISMATCH",)
            if self._outcome_store is not None:
                self._outcome_store.record_attempt(
                    candidate.lineage.source_run_id,
                    blocker_codes=blockers,
                )
            return blockers
        prerequisites = MutationPrerequisites(
            market_data_ready=(
                readiness.market_data_ready and readiness.approval_source_ready
            ),
            approval_candidate_eligible=True,
            backup_pitr_pass=readiness.backup_pitr_pass,
            paper_target_authorized=True,
            live_disabled=readiness.live_disabled,
        )
        direct_blockers = tuple(
            code for code, passed in (
                ("MARKET_DATA_NOT_READY", readiness.market_data_ready),
                ("APPROVAL_SOURCE_NOT_READY", readiness.approval_source_ready),
                ("WAL_NOT_READY", readiness.wal_ready),
                ("PITR_NOT_READY", readiness.pitr_ready),
                ("LIVE_NOT_DISABLED", readiness.live_disabled),
            ) if not passed
        )
        policy_blockers = tuple(dict.fromkeys(direct_blockers + snapshot_blockers))
        attempt_recorded = False
        if self._outcome_store is not None and policy_blockers:
            self._outcome_store.record_attempt(
                candidate.lineage.source_run_id,
                blocker_codes=policy_blockers,
            )
            attempt_recorded = True
        if readiness.policy_blockers:
            return policy_blockers
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
                if self._outcome_store is not None and not attempt_recorded:
                    self._outcome_store.record_attempt(
                        candidate.lineage.source_run_id,
                        blocker_codes=(code,),
                    )
                return (code,)
            raise
        if self._outcome_store is not None:
            if result.successful:
                self._outcome_store.record_attempt(
                    candidate.lineage.source_run_id,
                    command_id=command_id,
                )
            else:
                self._outcome_store.record_attempt(
                    candidate.lineage.source_run_id,
                    failure_code=str(result.reason_code),
                )
        if result.successful and continuous_budget is not None and self._continuous_store is not None:
            self._continuous_store.record_command(command_id=command_id)
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


__all__ = (
    "ExistingCanaryRuntimeReadiness",
    "FOUNDATION_SIMULATION_POLICY_ID",
    "ProductionPaperFirstCanaryExecutor",
    "SCALPING_V2_SIMULATION_POLICY_ID",
)
