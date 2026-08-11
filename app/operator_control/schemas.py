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
    arming_transition_id: Annotated[StrictStr, Field(min_length=16, max_length=128)]
    canary_acknowledgement: StrictBool


class PaperOperatorTransitionRequest(StrictRequest):
    request_id: RequestId
    expected_generation: Generation
    operator_acknowledgement: StrictBool


class PaperOperatorClearEmergencyStopRequest(PaperOperatorTransitionRequest):
    clear_emergency_stop_acknowledgement: StrictBool


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


class PaperCanaryNormalizedState(StrEnum):
    NOT_CONFIGURED = "NOT_CONFIGURED"
    DISABLED = "DISABLED"
    ARMED_WAITING = "ARMED_WAITING"
    NO_ELIGIBLE_APPROVAL = "NO_ELIGIBLE_APPROVAL"
    RUNNING = "RUNNING"
    POSITION_OPEN = "POSITION_OPEN"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"
    RECONCILIATION_PENDING = "RECONCILIATION_PENDING"
    COMPLETED = "COMPLETED"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class PaperOperatorCanaryStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    state: PaperCanaryNormalizedState
    availability_code: str
    deployment_status: str
    mode: str = "PAPER"
    live_allowed: bool = False
    max_new_commands: int = 1
    max_open_positions: int = 1
    allowed_symbols: tuple[str, ...] = ()
    finding_codes: tuple[str, ...] = ()


class ControlErrorItem(BaseModel):
    code: str
    message: str
    details: dict[str, object] = Field(default_factory=dict)


class ControlErrorEnvelope(BaseModel):
    error: ControlErrorItem
    request_id: str
