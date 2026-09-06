from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr


RequestId = Annotated[StrictStr, Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")]
Generation = Annotated[StrictInt, Field(ge=1, le=2_147_483_647)]


class StrictRequest(BaseModel):
    # JSON has arrays rather than tuples. Pydantic may perform only that
    # representation conversion; semantic and numeric bounds are enforced by
    # the service before the safety authority is called.
    model_config = ConfigDict(extra="forbid", frozen=True, strict=False)


class PaperOperatorArmFirstCanaryRequest(StrictRequest):
    request_id: RequestId
    expected_generation: Generation
    environment: StrictStr
    mode: StrictStr
    max_new_commands: StrictInt
    max_open_positions: StrictInt
    allowed_symbols: tuple[StrictStr, ...]
    operator_acknowledgement: StrictBool
    paper_acknowledgement: StrictBool
    live_forbidden_acknowledgement: StrictBool


class PaperOperatorStartFirstCanaryRequest(StrictRequest):
    request_id: RequestId
    expected_generation: Generation
    canary_id: Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")]
    arming_transition_id: Annotated[StrictStr, Field(min_length=16, max_length=128)]
    canary_acknowledgement: StrictBool


class PaperOperatorTransitionRequest(StrictRequest):
    request_id: RequestId
    expected_generation: Generation
    operator_acknowledgement: StrictBool


class PaperOperatorClearEmergencyStopRequest(PaperOperatorTransitionRequest):
    clear_emergency_stop_acknowledgement: StrictBool


class PaperOperatorRecoveryCloseRequest(StrictRequest):
    request_id: RequestId
    position_id: Annotated[StrictStr, Field(min_length=16, max_length=128)]
    profile_id: Annotated[StrictStr, Field(pattern=r"^trade-5m-v2$")]
    operator_acknowledgement: StrictBool
    paper_acknowledgement: StrictBool
    live_forbidden_acknowledgement: StrictBool


class PaperOperatorRecoveryCloseDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    operation: str = "RECOVERY_CLOSE_PAPER_POSITION"
    accepted: bool
    executed: bool
    position_id: str
    state_before: str
    state_after: str
    close_reason: str | None = None
    exit_fill_id: str | None = None
    exit_price: str | None = None
    exit_fee: str | None = None
    source_closed_until_ms: int | None = None
    finding_codes: tuple[str, ...] = ()
    live_allowed: bool = False
    binance_order_calls_allowed: bool = False


class PaperOperatorControlDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    operation: str
    accepted: bool
    executed: bool
    state_before: str
    state_after: str
    generation_before: int
    generation_after: int
    finding_codes: tuple[str, ...] = ()
    transition_id: str | None = None
    canary_id: str | None = None
    arming_transition_id: str | None = None
    started_at: str | None = None
    scope: dict[str, object] | None = None


class PaperOperatorControlStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    control_api_version: str
    foundation_mode: str
    service_enabled: bool
    bind_scope: str
    environment: str
    mode: str
    control_state: str
    effective_state: str
    generation: int | None
    control_health: str
    audit_health: str
    state_audit_reconciliation: str
    emergency_stop_available: bool
    live_allowed: bool
    production_mutation_enabled: bool
    continuation_worker_active: bool = False
    continuation_poll_seconds: float | None = None


class PaperCanaryNormalizedState(StrEnum):
    NOT_CONFIGURED = "NOT_CONFIGURED"
    DISABLED = "DISABLED"
    RESERVED = "RESERVED"
    ARMED = "ARMED"
    ARMED_WAITING = "ARMED_WAITING"
    NO_ELIGIBLE_APPROVAL = "NO_ELIGIBLE_APPROVAL"
    WAITING_FOR_ELIGIBLE_APPROVAL = "WAITING_FOR_ELIGIBLE_APPROVAL"
    RUNNING = "RUNNING"
    POSITION_OPEN = "POSITION_OPEN"
    POSITION_CLOSING = "POSITION_CLOSING"
    POSITION_CLOSED = "POSITION_CLOSED"
    RECONCILIATION_PENDING = "RECONCILIATION_PENDING"
    COMPLETED = "COMPLETED"
    STOPPED = "STOPPED"
    FAILED_SAFE = "FAILED_SAFE"


class PaperOperatorCanaryStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    state: PaperCanaryNormalizedState
    availability_code: str
    deployment_status: str
    canary_id: str | None = None
    environment: str = "PRODUCTION"
    mode: str = "PAPER"
    created_at: str | None = None
    armed_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    arming_transition_id: str | None = None
    current_control_generation: int | None = None
    live_allowed: bool = False
    max_new_commands: int = 1
    max_open_positions: int = 1
    allowed_symbols: tuple[str, ...] = ()
    universe_version_id: str | None = None
    selection_policy_version: str | None = None
    command_count: int = 0
    command_id: str | None = None
    position_count: int = 0
    position_id: str | None = None
    trade_report_available: bool = False
    trade_report_position_id: str | None = None
    paper_reconciliation_status: str = "NOT_STARTED"
    accounting_reconciliation_status: str = "NOT_STARTED"
    reconciliation_checked_at: str | None = None
    terminal_reason: str | None = None
    finding_codes: tuple[str, ...] = ()
    binance_order_calls_allowed: bool = False


class ControlErrorItem(BaseModel):
    code: str
    message: str
    details: dict[str, object] = Field(default_factory=dict)


class ControlErrorEnvelope(BaseModel):
    error: ControlErrorItem
    request_id: str
