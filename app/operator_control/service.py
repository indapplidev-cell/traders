from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, field
from typing import Callable, Protocol

from app.engine_safety.paper_production_control import (
    ArmReadinessPreflight,
    PaperProductionArmingScope,
    PaperProductionSafetyControl,
    PersistentState,
    ReasonCode,
    SafetyControlError,
)

from .config import CONTROL_API_VERSION, PaperOperatorControlConfig, PaperOperatorControlOperationMode
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


ALLOWED_FIRST_CANARY_SYMBOLS = frozenset({"BTCUSDT", "ETHUSDT", "SOLUSDT"})


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

    def start_bounded_canary(self, *, request_id: str, transition_id: str, generation: int) -> tuple[str, ...]: ...

    def status(self) -> PaperOperatorCanaryStatus: ...


class DisabledPaperFirstCanaryExecutor:
    def preflight(self, *, transition_id: str, generation: int) -> tuple[str, ...]:
        return ("CONTROL_API_DISABLED_FOUNDATION",)

    def start_bounded_canary(self, *, request_id: str, transition_id: str, generation: int) -> tuple[str, ...]:
        return ("CONTROL_API_DISABLED_FOUNDATION",)

    def status(self) -> PaperOperatorCanaryStatus:
        return PaperOperatorCanaryStatus(
            state=PaperCanaryNormalizedState.DISABLED,
            availability_code="PAPER_SCHEMA_NOT_DEPLOYED",
            deployment_status="NOT_DEPLOYED",
            finding_codes=("PAPER_SCHEMA_NOT_DEPLOYED", "RUNTIME_NOT_READY"),
        )


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
    ) -> None:
        self.config = config
        self.control = control
        self.readiness = readiness or PaperOperatorArmReadiness
        self.executor = executor or DisabledPaperFirstCanaryExecutor()
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
            production_mutation_enabled=False,
        )

    def canary_status(self) -> PaperOperatorCanaryStatus:
        try:
            return self.executor.status()
        except BaseException as error:
            raise ControlApiError(503, "CONTROL_SAFE_FAILURE") from error

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
        if self.config.operation_mode is PaperOperatorControlOperationMode.DISABLED_FOUNDATION:
            raise ControlDecisionError(409, self._foundation_denial(request_id, operation))

    def arm_first_canary(self, request: PaperOperatorArmFirstCanaryRequest) -> PaperOperatorControlDecision:
        def execute() -> PaperOperatorControlDecision:
            if request.environment != "PRODUCTION":
                raise ControlApiError(400, "INVALID_REQUEST")
            if request.mode != "PAPER":
                raise ControlApiError(400, "LIVE_NOT_ALLOWED" if request.mode == "LIVE" else "INVALID_MODE")
            if not (request.operator_acknowledgement and request.paper_acknowledgement and request.live_forbidden_acknowledgement):
                raise ControlApiError(400, "INVALID_REQUEST")
            symbols = tuple(sorted(set(request.allowed_symbols)))
            if not symbols or len(symbols) != len(request.allowed_symbols) or len(symbols) > 3:
                raise ControlApiError(400, "INVALID_CANARY_SCOPE")
            if any(symbol not in ALLOWED_FIRST_CANARY_SYMBOLS for symbol in symbols):
                raise ControlApiError(400, "INVALID_SYMBOL")
            if request.max_new_commands != 1 or request.max_open_positions != 1:
                raise ControlApiError(400, "INVALID_CANARY_SCOPE")
            self._deny_if_foundation(request.request_id, "ARM_FIRST_CANARY")
            before = self._state()
            readiness = self.readiness()
            if readiness.finding_codes:
                raise ControlApiError(409, readiness.finding_codes[0])
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
                raise self._map_authority_error(error) from error
            return PaperOperatorControlDecision(
                request_id=request.request_id, operation="ARM_FIRST_CANARY", accepted=True, executed=True,
                state_before=before.state.value, state_after=after.state.value,
                generation_before=before.generation, generation_after=after.generation,
                transition_id=after.transition_id,
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
            try:
                findings = self.executor.preflight(
                    transition_id=state.transition_id, generation=state.generation
                )
            except BaseException as error:
                raise ControlApiError(503, "CONTROL_SAFE_FAILURE") from error
            if findings == ("NO_ELIGIBLE_APPROVAL",):
                return PaperOperatorControlDecision(
                    request_id=request.request_id, operation="START_FIRST_CANARY",
                    accepted=True, executed=False, state_before=state.state.value,
                    state_after=state.state.value, generation_before=state.generation,
                    generation_after=state.generation, finding_codes=findings,
                    transition_id=state.transition_id,
                )
            if findings:
                raise ControlApiError(503, findings[0])
            try:
                findings = self.executor.start_bounded_canary(
                    request_id=request.request_id,
                    transition_id=state.transition_id,
                    generation=state.generation,
                )
            except BaseException as error:
                raise ControlApiError(503, "CONTROL_SAFE_FAILURE") from error
            return PaperOperatorControlDecision(
                request_id=request.request_id, operation="START_FIRST_CANARY", accepted=not findings,
                executed=not findings, state_before=state.state.value, state_after=state.state.value,
                generation_before=state.generation, generation_after=state.generation,
                finding_codes=findings, transition_id=state.transition_id,
            )
        return self._run(request.request_id, "START_FIRST_CANARY", request, execute)

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
