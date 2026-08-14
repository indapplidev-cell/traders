from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Protocol
from uuid import uuid4

from app.trading_universe.domain import ACTIVE_TRADING_UNIVERSE, bind_new_canary

from app.engine_safety.paper_production_control import (
    ArmReadinessPreflight,
    PaperProductionArmingScope,
    PaperProductionSafetyControl,
    PersistentState,
    ReasonCode,
    SafetyControlError,
)
from app.engine_paper.first_canary_correlation import (
    CanaryCorrelationError,
    PaperFirstCanarySession,
    PaperFirstCanaryState,
)

from .config import CONTROL_API_VERSION, PaperOperatorControlConfig
from .schemas import (
    PaperCanaryNormalizedState,
    PaperOperatorArmFirstCanaryRequest,
    PaperOperatorCanaryStatus,
    PaperOperatorClearEmergencyStopRequest,
    PaperOperatorControlDecision,
    PaperOperatorControlStatus,
    PaperOperatorStartFirstCanaryRequest,
    PaperOperatorTransitionRequest,
)


ALLOWED_FIRST_CANARY_SYMBOLS = frozenset(ACTIVE_TRADING_UNIVERSE.symbols)


class ControlApiError(RuntimeError):
    def __init__(self, status_code: int, code: str, safe_message: str = "The control request was denied.") -> None:
        super().__init__(code)
        self.status_code = status_code
        self.code = code
        self.safe_message = safe_message


class ControlDecisionError(ControlApiError):
    def __init__(self, status_code: int, decision: PaperOperatorControlDecision) -> None:
        super().__init__(status_code, decision.finding_codes[0] if decision.finding_codes else "CONTROL_SAFE_FAILURE")
        self.decision = decision


@dataclass(frozen=True, slots=True)
class PaperOperatorArmReadiness:
    schema_ready: bool = False
    pitr_ready: bool = False
    wal_ready: bool = False
    pitr_chain_valid: bool = False
    market_data_ready: bool = False
    approval_source_ready: bool = False
    baseline_ready: bool = False
    accounting_healthy: bool = False
    paper_principal_ready: bool = False
    runtime_ready: bool = False
    kill_switch_ready: bool = False
    live_disabled: bool = True
    binance_order_authority_absent: bool = True

    @classmethod
    def isolated_ready(cls) -> "PaperOperatorArmReadiness":
        return cls(
            schema_ready=True,
            pitr_ready=True,
            wal_ready=True,
            pitr_chain_valid=True,
            market_data_ready=True,
            approval_source_ready=True,
            baseline_ready=True,
            accounting_healthy=True,
            paper_principal_ready=True,
            runtime_ready=True,
            kill_switch_ready=True,
            live_disabled=True,
            binance_order_authority_absent=True,
        )

    @property
    def finding_codes(self) -> tuple[str, ...]:
        checks = (
            ("PAPER_SCHEMA_NOT_DEPLOYED", self.schema_ready),
            ("PITR_NOT_READY", self.pitr_ready),
            ("WAL_NOT_READY", self.wal_ready and self.pitr_chain_valid),
            ("MARKET_DATA_NOT_READY", self.market_data_ready),
            ("APPROVAL_SOURCE_NOT_READY", self.approval_source_ready),
            ("BASELINE_NOT_READY", self.baseline_ready),
            ("ACCOUNTING_NOT_HEALTHY", self.accounting_healthy),
            ("PAPER_PRINCIPAL_NOT_READY", self.paper_principal_ready),
            ("RUNTIME_NOT_READY", self.runtime_ready),
            ("CONTROL_STATE_UNAVAILABLE", self.kill_switch_ready),
            ("LIVE_NOT_ALLOWED", self.live_disabled and self.binance_order_authority_absent),
        )
        return tuple(code for code, passed in checks if not passed)

    def authority_preflight(self) -> ArmReadinessPreflight:
        return ArmReadinessPreflight(
            self.schema_ready,
            self.pitr_ready,
            self.market_data_ready,
            self.approval_source_ready,
            self.wal_ready,
            self.wal_ready,
            self.pitr_chain_valid,
            self.runtime_ready,
            self.live_disabled and self.binance_order_authority_absent,
        )


class PaperFirstCanaryExecutor(Protocol):
    def preflight(self, *, transition_id: str, generation: int) -> tuple[str, ...]: ...

    def start_bounded_canary(self, *, request_id: str, canary_id: str, transition_id: str, generation: int) -> tuple[str, ...]: ...

    def status(self) -> PaperOperatorCanaryStatus: ...


class DisabledPaperFirstCanaryExecutor:
    def preflight(self, *, transition_id: str, generation: int) -> tuple[str, ...]:
        return ("CONTROL_API_DISABLED_FOUNDATION",)

    def start_bounded_canary(self, *, request_id: str, canary_id: str, transition_id: str, generation: int) -> tuple[str, ...]:
        return ("CONTROL_API_DISABLED_FOUNDATION",)

    def status(self) -> PaperOperatorCanaryStatus:
        return PaperOperatorCanaryStatus(
            state=PaperCanaryNormalizedState.DISABLED,
            availability_code="PAPER_SCHEMA_NOT_DEPLOYED",
            deployment_status="NOT_DEPLOYED",
            finding_codes=("PAPER_SCHEMA_NOT_DEPLOYED", "RUNTIME_NOT_READY"),
        )


class PaperFirstCanaryStore(Protocol):
    def reserve_arm(self, **kwargs) -> PaperFirstCanarySession: ...
    def complete_arm(self, *args, **kwargs) -> PaperFirstCanarySession: ...
    def reserve_start(self, *args, **kwargs) -> PaperFirstCanarySession: ...
    def mark_started(self, *args, **kwargs) -> PaperFirstCanarySession: ...
    def fail_safe(self, *args, **kwargs) -> PaperFirstCanarySession: ...
    def get(self, canary_id: str) -> PaperFirstCanarySession | None: ...
    def current(self) -> PaperFirstCanarySession | None: ...
    def get_by_arm_request(self, request_id: str) -> PaperFirstCanarySession | None: ...


@dataclass(slots=True)
class _IdempotencyRecord:
    fingerprint: str
    ready: threading.Event = field(default_factory=threading.Event)
    result: PaperOperatorControlDecision | None = None
    error: BaseException | None = None


class _IdempotencyRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: dict[str, _IdempotencyRecord] = {}

    def run(self, request_id: str, fingerprint: str, operation: Callable[[], PaperOperatorControlDecision]) -> PaperOperatorControlDecision:
        owner = False
        with self._lock:
            record = self._records.get(request_id)
            if record is None:
                record = _IdempotencyRecord(fingerprint)
                self._records[request_id] = record
                owner = True
            elif record.fingerprint != fingerprint:
                raise ControlApiError(409, "REQUEST_ID_CONFLICT")
        if owner:
            try:
                record.result = operation()
            except BaseException as error:
                record.error = error
            finally:
                record.ready.set()
        elif not record.ready.wait(timeout=2.0):
            raise ControlApiError(423, "INTERLOCK_BUSY")
        if record.error is not None:
            raise record.error
        if record.result is None:
            raise ControlApiError(503, "CONTROL_SAFE_FAILURE")
        return record.result


class PaperOperatorControlService:
    def __init__(
        self,
        *,
        config: PaperOperatorControlConfig,
        control: PaperProductionSafetyControl,
        readiness: Callable[[], PaperOperatorArmReadiness] | None = None,
        executor: PaperFirstCanaryExecutor | None = None,
        canary_store: PaperFirstCanaryStore | None = None,
        continuation_status: Callable[[], tuple[bool, float | None]] | None = None,
    ) -> None:
        self.config = config
        self.control = control
        self.readiness = readiness or PaperOperatorArmReadiness
        self.executor = executor or DisabledPaperFirstCanaryExecutor()
        self.canary_store = canary_store
        self.continuation_status = continuation_status or (lambda: (False, None))
        self._idempotency = _IdempotencyRegistry()

    @staticmethod
    def _fingerprint(operation: str, request: object) -> str:
        payload = request.model_dump(mode="json", exclude={"request_id"})  # type: ignore[attr-defined]
        canonical = json.dumps({"operation": operation, "payload": payload}, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _state(self):
        try:
            return self.control.read_authoritative()
        except SafetyControlError as error:
            code = str(error)
            mapped = "AUDIT_RECONCILIATION_FAILED" if "AUDIT" in code else (
                "CONTROL_STATE_CORRUPT" if any(item in code for item in ("CORRUPT", "CHECKSUM", "INVALID"))
                else "CONTROL_STATE_UNAVAILABLE"
            )
            raise ControlApiError(503, mapped) from error

    @staticmethod
    def _map_authority_error(error: SafetyControlError) -> ControlApiError:
        raw = str(error)
        if raw == "STALE_GENERATION":
            return ControlApiError(409, "STALE_GENERATION")
        if raw == "ILLEGAL_TRANSITION":
            return ControlApiError(409, "ILLEGAL_CONTROL_TRANSITION")
        if raw == "INTERLOCK_BUSY":
            return ControlApiError(423, "INTERLOCK_BUSY")
        if "AUDIT" in raw:
            return ControlApiError(503, "AUDIT_RECONCILIATION_FAILED")
        if any(value in raw for value in ("STATE", "ACL")):
            return ControlApiError(503, "CONTROL_STATE_UNAVAILABLE")
        return ControlApiError(409, "CONTROL_SAFE_FAILURE")

    def status(self) -> PaperOperatorControlStatus:
        state = self._state()
        health = self.control.health()
        continuation_active, continuation_interval = self.continuation_status()
        return PaperOperatorControlStatus(
            control_api_version=CONTROL_API_VERSION,
            foundation_mode=self.config.operation_mode.value,
            service_enabled=self.config.enabled,
            bind_scope="LOOPBACK_ONLY",
            environment="PRODUCTION",
            mode="PAPER",
            control_state=state.state.value,
            effective_state=health.effective_state.value,
            generation=state.generation,
            control_health=health.health,
            audit_health="PASS" if health.audit_valid else "FAIL",
            state_audit_reconciliation="PASS" if health.effective_state.value != "FAIL_CLOSED" else "FAIL",
            emergency_stop_available=health.emergency_stop_available,
            live_allowed=False,
            production_mutation_enabled=self.config.mutation_foundation_enabled,
            continuation_worker_active=continuation_active,
            continuation_poll_seconds=continuation_interval,
        )

    @staticmethod
    def _canary_dto(value: PaperFirstCanarySession) -> PaperOperatorCanaryStatus:
        waiting = value.state is PaperFirstCanaryState.NO_ELIGIBLE_APPROVAL
        return PaperOperatorCanaryStatus(
            canary_id=value.canary_id,
            state=(PaperCanaryNormalizedState.WAITING_FOR_ELIGIBLE_APPROVAL if waiting
                   else PaperCanaryNormalizedState(value.state.value)),
            availability_code=("NO_ELIGIBLE_APPROVAL" if waiting else "AVAILABLE"),
            deployment_status="SOURCE_READY",
            environment=value.environment,
            mode=value.mode,
            created_at=value.created_at.isoformat().replace("+00:00", "Z"),
            armed_at=value.armed_at.isoformat().replace("+00:00", "Z") if value.armed_at else None,
            started_at=value.started_at.isoformat().replace("+00:00", "Z") if value.started_at else None,
            completed_at=value.completed_at.isoformat().replace("+00:00", "Z") if value.completed_at else None,
            arming_transition_id=value.arming_transition_id,
            current_control_generation=value.current_control_generation,
            max_new_commands=value.max_new_commands,
            max_open_positions=value.max_open_positions,
            allowed_symbols=value.allowed_symbols,
            selection_policy_version=value.selection_policy_version,
            command_count=value.command_count,
            command_id=value.command_id,
            position_count=value.position_count,
            position_id=value.position_id,
            trade_report_available=value.trade_report_available,
            trade_report_position_id=value.position_id if value.trade_report_available else None,
            paper_reconciliation_status=value.paper_reconciliation_status,
            accounting_reconciliation_status=value.accounting_reconciliation_status,
            reconciliation_checked_at=(value.reconciliation_checked_at.isoformat().replace("+00:00", "Z") if value.reconciliation_checked_at else None),
            terminal_reason=value.terminal_reason,
            finding_codes=value.finding_codes,
            live_allowed=False,
            binance_order_calls_allowed=False,
        )

    def canary_status(
        self, canary_id: str | None = None, arm_request_id: str | None = None
    ) -> PaperOperatorCanaryStatus:
        try:
            if self.canary_store is not None:
                if canary_id is not None:
                    value = self.canary_store.get(canary_id)
                    if value is None:
                        raise ControlApiError(404, "CANARY_NOT_FOUND")
                elif arm_request_id is not None:
                    value = self.canary_store.get_by_arm_request(arm_request_id)
                    if value is None:
                        raise ControlApiError(404, "CANARY_NOT_FOUND")
                else:
                    value = self.canary_store.current()
                if value is None:
                    return PaperOperatorCanaryStatus(
                        state=PaperCanaryNormalizedState.NOT_CONFIGURED,
                        availability_code="NO_ACTIVE_CANARY",
                        deployment_status="SOURCE_READY",
                    )
                return self._canary_dto(value)
            return self.executor.status()
        except ControlApiError:
            raise
        except CanaryCorrelationError as error:
            raise ControlApiError(503, error.code) from error
        except BaseException as error:
            raise ControlApiError(503, "CANARY_CORRELATION_UNAVAILABLE") from error

    def _foundation_denial(self, request_id: str, operation: str) -> PaperOperatorControlDecision:
        state = self._state()
        return PaperOperatorControlDecision(
            request_id=request_id, operation=operation, accepted=False, executed=False,
            state_before=state.state.value, state_after=state.state.value,
            generation_before=state.generation, generation_after=state.generation,
            finding_codes=("CONTROL_API_DISABLED_FOUNDATION",),
        )

    def _run(self, request_id: str, operation: str, request: object, function: Callable[[], PaperOperatorControlDecision]) -> PaperOperatorControlDecision:
        fingerprint = self._fingerprint(operation, request)
        return self._idempotency.run(request_id, fingerprint, function)

    def _deny_if_foundation(self, request_id: str, operation: str) -> None:
        if not self.config.mutation_foundation_enabled:
            raise ControlDecisionError(409, self._foundation_denial(request_id, operation))

    @staticmethod
    def _correlation_error(error: CanaryCorrelationError) -> ControlApiError:
        status = 404 if error.code == "CANARY_NOT_FOUND" else (
            409 if error.code in {
                "REQUEST_ID_CONFLICT", "CANARY_ALREADY_ACTIVE", "CANARY_NOT_ARMED",
                "CANARY_ALREADY_STARTED", "CANARY_CORRELATION_CONFLICT",
            } else 503
        )
        return ControlApiError(status, error.code)

    def arm_first_canary(self, request: PaperOperatorArmFirstCanaryRequest) -> PaperOperatorControlDecision:
        def execute() -> PaperOperatorControlDecision:
            if request.environment != "PRODUCTION":
                raise ControlApiError(400, "INVALID_REQUEST")
            if request.mode != "PAPER":
                raise ControlApiError(400, "LIVE_NOT_ALLOWED" if request.mode == "LIVE" else "INVALID_MODE")
            if not (request.operator_acknowledgement and request.paper_acknowledgement and request.live_forbidden_acknowledgement):
                raise ControlApiError(400, "INVALID_REQUEST")
            symbols = tuple(sorted(set(request.allowed_symbols)))
            if not symbols or len(symbols) != len(request.allowed_symbols) or len(symbols) > 10:
                raise ControlApiError(400, "INVALID_CANARY_SCOPE")
            if any(symbol not in ALLOWED_FIRST_CANARY_SYMBOLS for symbol in symbols):
                raise ControlApiError(400, "INVALID_SYMBOL")
            try:
                universe_binding = bind_new_canary(
                    ACTIVE_TRADING_UNIVERSE.version_id, symbols
                )
            except ValueError as error:
                raise ControlApiError(400, "INVALID_SYMBOL") from error
            if request.max_new_commands != 1 or request.max_open_positions != 1:
                raise ControlApiError(400, "INVALID_CANARY_SCOPE")
            self._deny_if_foundation(request.request_id, "ARM_FIRST_CANARY")
            before = self._state()
            readiness = self.readiness()
            if readiness.finding_codes:
                raise ControlApiError(409, readiness.finding_codes[0])
            canary = None
            if self.canary_store is not None:
                fingerprint = self._fingerprint("ARM_FIRST_CANARY", request)
                try:
                    canary = self.canary_store.reserve_arm(
                        request_id=request.request_id,
                        fingerprint=fingerprint,
                        expected_generation=request.expected_generation,
                        allowed_symbols=universe_binding.allowed_symbols,
                        now=datetime.now(timezone.utc),
                    )
                except CanaryCorrelationError as error:
                    raise self._correlation_error(error) from error
            if canary is not None and canary.state is PaperFirstCanaryState.ARMED:
                return PaperOperatorControlDecision(
                    request_id=request.request_id, operation="ARM_FIRST_CANARY",
                    accepted=True, executed=True, state_before="DISABLED", state_after="ARMED",
                    generation_before=(canary.arming_generation or 1) - 1,
                    generation_after=canary.arming_generation or canary.current_control_generation,
                    transition_id=canary.arming_transition_id,
                    arming_transition_id=canary.arming_transition_id,
                    canary_id=canary.canary_id,
                    scope={"max_new_commands": 1, "max_open_positions": 1, "allowed_symbols": list(canary.allowed_symbols)},
                )
            if (
                canary is not None
                and canary.state is PaperFirstCanaryState.RESERVED
                and before.state is PersistentState.ARMED
                and before.generation == request.expected_generation + 1
                and before.arming_scope is not None
                and before.arming_scope.max_new_commands == 1
                and before.arming_scope.max_open_positions == 1
                and tuple(before.arming_scope.allowed_symbols) == symbols
            ):
                try:
                    canary = self.canary_store.complete_arm(
                        canary.canary_id, before.transition_id, before.generation,
                        datetime.now(timezone.utc),
                    )
                except CanaryCorrelationError as error:
                    raise self._correlation_error(error) from error
                return PaperOperatorControlDecision(
                    request_id=request.request_id, operation="ARM_FIRST_CANARY",
                    accepted=True, executed=True, state_before="DISABLED", state_after="ARMED",
                    generation_before=request.expected_generation,
                    generation_after=before.generation, transition_id=before.transition_id,
                    arming_transition_id=before.transition_id, canary_id=canary.canary_id,
                    scope={"max_new_commands": 1, "max_open_positions": 1, "allowed_symbols": list(symbols)},
                )
            try:
                after = self.control.transition(
                    PersistentState.ARMED,
                    expected_generation=request.expected_generation,
                    reason=ReasonCode.OPERATOR_ARM,
                    acknowledge=True,
                    acknowledge_paper_arming=True,
                    preflight=readiness.authority_preflight(),
                    arming_scope=PaperProductionArmingScope(1, 1, symbols),
                )
            except SafetyControlError as error:
                if self.canary_store is not None and canary is not None:
                    try:
                        self.canary_store.fail_safe(canary.canary_id, self._map_authority_error(error).code)
                    except Exception:
                        pass
                raise self._map_authority_error(error) from error
            if self.canary_store is not None and canary is not None:
                try:
                    canary = self.canary_store.complete_arm(
                        canary.canary_id, after.transition_id, after.generation,
                        datetime.now(timezone.utc),
                    )
                except CanaryCorrelationError as error:
                    raise self._correlation_error(error) from error
                canary_id = canary.canary_id
            else:
                # Compatibility-only isolated executor path. Production-capable
                # composition is required to inject the durable store.
                canary_id = str(uuid4())
            return PaperOperatorControlDecision(
                request_id=request.request_id, operation="ARM_FIRST_CANARY", accepted=True, executed=True,
                state_before=before.state.value, state_after=after.state.value,
                generation_before=before.generation, generation_after=after.generation,
                transition_id=after.transition_id, arming_transition_id=after.transition_id,
                canary_id=canary_id,
                scope={"max_new_commands": 1, "max_open_positions": 1, "allowed_symbols": list(symbols)},
            )
        return self._run(request.request_id, "ARM_FIRST_CANARY", request, execute)

    def start_first_canary(self, request: PaperOperatorStartFirstCanaryRequest) -> PaperOperatorControlDecision:
        def execute() -> PaperOperatorControlDecision:
            if not request.canary_acknowledgement:
                raise ControlApiError(400, "INVALID_REQUEST")
            self._deny_if_foundation(request.request_id, "START_FIRST_CANARY")
            state = self._state()
            if state.generation != request.expected_generation:
                raise ControlApiError(409, "STALE_GENERATION")
            if state.state is not PersistentState.ARMED or state.transition_id != request.arming_transition_id:
                raise ControlApiError(409, "CANARY_NOT_ARMED")
            canary = None
            if self.canary_store is not None:
                try:
                    canary = self.canary_store.reserve_start(
                        request.canary_id,
                        request.request_id,
                        self._fingerprint("START_FIRST_CANARY", request),
                        request.arming_transition_id,
                        request.expected_generation,
                    )
                except CanaryCorrelationError as error:
                    raise self._correlation_error(error) from error
            if canary is not None and canary.state is not PaperFirstCanaryState.ARMED:
                if canary.started_at is None and canary.start_request_id == request.request_id:
                    try:
                        canary = self.canary_store.mark_started(
                            canary.canary_id,
                            no_approval=canary.state is PaperFirstCanaryState.NO_ELIGIBLE_APPROVAL,
                            now=datetime.now(timezone.utc),
                        )
                    except CanaryCorrelationError as error:
                        raise self._correlation_error(error) from error
                started = canary.started_at.isoformat().replace("+00:00", "Z") if canary.started_at else None
                return PaperOperatorControlDecision(
                    request_id=request.request_id, operation="START_FIRST_CANARY",
                    accepted=True,
                    executed=canary.state is not PaperFirstCanaryState.NO_ELIGIBLE_APPROVAL,
                    state_before="ARMED", state_after=(
                        "WAITING_FOR_ELIGIBLE_APPROVAL"
                        if canary.state is PaperFirstCanaryState.NO_ELIGIBLE_APPROVAL
                        else canary.state.value
                    ),
                    generation_before=state.generation, generation_after=state.generation,
                    finding_codes=canary.finding_codes,
                    transition_id=state.transition_id,
                    arming_transition_id=state.transition_id,
                    canary_id=canary.canary_id,
                    started_at=started,
                )
            try:
                findings = self.executor.preflight(
                    transition_id=state.transition_id, generation=state.generation
                )
            except BaseException as error:
                raise ControlApiError(503, "CONTROL_SAFE_FAILURE") from error
            if findings == ("NO_ELIGIBLE_APPROVAL",):
                if self.canary_store is not None and canary is not None:
                    try:
                        canary = self.canary_store.mark_started(
                            canary.canary_id, no_approval=True, now=datetime.now(timezone.utc)
                        )
                    except CanaryCorrelationError as error:
                        raise self._correlation_error(error) from error
                return PaperOperatorControlDecision(
                    request_id=request.request_id, operation="START_FIRST_CANARY",
                    accepted=True, executed=False, state_before=state.state.value,
                    state_after="WAITING_FOR_ELIGIBLE_APPROVAL", generation_before=state.generation,
                    generation_after=state.generation, finding_codes=findings,
                    transition_id=state.transition_id, arming_transition_id=state.transition_id,
                    canary_id=request.canary_id,
                    started_at=(canary.started_at.isoformat().replace("+00:00", "Z") if canary is not None and canary.started_at else None),
                )
            if findings:
                raise ControlApiError(503, findings[0])
            try:
                findings = self.executor.start_bounded_canary(
                    request_id=request.request_id,
                    canary_id=request.canary_id,
                    transition_id=state.transition_id,
                    generation=state.generation,
                )
            except BaseException as error:
                raise ControlApiError(503, "CONTROL_SAFE_FAILURE") from error
            if self.canary_store is not None and canary is not None:
                try:
                    canary = self.canary_store.mark_started(
                        canary.canary_id, no_approval=False, now=datetime.now(timezone.utc)
                    )
                except CanaryCorrelationError as error:
                    raise self._correlation_error(error) from error
            return PaperOperatorControlDecision(
                request_id=request.request_id, operation="START_FIRST_CANARY", accepted=not findings,
                executed=not findings, state_before=state.state.value, state_after=state.state.value,
                generation_before=state.generation, generation_after=state.generation,
                finding_codes=findings, transition_id=state.transition_id,
                arming_transition_id=state.transition_id, canary_id=request.canary_id,
                started_at=(canary.started_at.isoformat().replace("+00:00", "Z") if canary is not None and canary.started_at else None),
            )
        return self._run(request.request_id, "START_FIRST_CANARY", request, execute)

    def recover_pending_start(self, canary_id: str) -> PaperOperatorControlDecision:
        """Resume the exact durable GUI START reservation; never mint an id."""

        if self.canary_store is None:
            raise ControlApiError(503, "CANARY_CORRELATION_UNAVAILABLE")
        try:
            canary = self.canary_store.get(canary_id)
        except CanaryCorrelationError as error:
            raise self._correlation_error(error) from error
        if canary is None:
            raise ControlApiError(404, "CANARY_NOT_FOUND")
        if canary.start_request_id is None:
            raise ControlApiError(409, "PENDING_START_REQUEST_NOT_FOUND")
        if canary.arming_transition_id is None or canary.arming_generation is None:
            raise ControlApiError(409, "CANARY_CORRELATION_CONFLICT")
        return self.start_first_canary(PaperOperatorStartFirstCanaryRequest(
            request_id=canary.start_request_id,
            expected_generation=canary.arming_generation,
            canary_id=canary.canary_id,
            arming_transition_id=canary.arming_transition_id,
            canary_acknowledgement=True,
        ))

    def _transition(self, request: PaperOperatorTransitionRequest, operation: str, target: PersistentState, reason: ReasonCode) -> PaperOperatorControlDecision:
        def execute() -> PaperOperatorControlDecision:
            if not request.operator_acknowledgement:
                raise ControlApiError(400, "INVALID_REQUEST")
            if isinstance(request, PaperOperatorClearEmergencyStopRequest) and not request.clear_emergency_stop_acknowledgement:
                raise ControlApiError(400, "INVALID_REQUEST")
            self._deny_if_foundation(request.request_id, operation)
            before = self._state()
            if operation == "CLEAR_EMERGENCY_STOP" and before.state is not PersistentState.EMERGENCY_STOP:
                raise ControlApiError(409, "ILLEGAL_CONTROL_TRANSITION")
            try:
                after = self.control.transition(
                    target, expected_generation=request.expected_generation, reason=reason, acknowledge=True
                )
            except SafetyControlError as error:
                raise self._map_authority_error(error) from error
            return PaperOperatorControlDecision(
                request_id=request.request_id, operation=operation, accepted=True,
                executed=after.transition_id != before.transition_id,
                state_before=before.state.value, state_after=after.state.value,
                generation_before=before.generation, generation_after=after.generation,
                transition_id=after.transition_id,
            )
        return self._run(request.request_id, operation, request, execute)

    def disable(self, request: PaperOperatorTransitionRequest) -> PaperOperatorControlDecision:
        return self._transition(request, "DISABLE", PersistentState.DISABLED, ReasonCode.OPERATOR_DISABLE)

    def emergency_stop(self, request: PaperOperatorTransitionRequest) -> PaperOperatorControlDecision:
        return self._transition(request, "EMERGENCY_STOP", PersistentState.EMERGENCY_STOP, ReasonCode.OPERATOR_EMERGENCY_STOP)

    def clear_emergency_stop(self, request: PaperOperatorClearEmergencyStopRequest) -> PaperOperatorControlDecision:
        return self._transition(request, "CLEAR_EMERGENCY_STOP", PersistentState.DISABLED, ReasonCode.CLEAR_EMERGENCY_STOP)
