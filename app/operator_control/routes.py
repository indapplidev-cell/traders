from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends

from .auth import PaperOperatorScope
from .schemas import (
    PaperOperatorArmFirstCanaryRequest,
    PaperOperatorCanaryStatus,
    PaperOperatorClearEmergencyStopRequest,
    PaperOperatorControlDecision,
    PaperOperatorControlStatus,
    PaperOperatorStartFirstCanaryRequest,
    PaperOperatorTransitionRequest,
)
from .service import PaperOperatorControlService


def build_operator_control_router(
    service: PaperOperatorControlService,
    require_scope: Callable[[PaperOperatorScope], Callable[..., object]],
) -> APIRouter:
    router = APIRouter(prefix="/control/v1")

    @router.get("/status", response_model=PaperOperatorControlStatus, dependencies=[Depends(require_scope(PaperOperatorScope.CONTROL_STATUS_READ))])
    def status() -> PaperOperatorControlStatus:
        return service.status()

    @router.get("/canary/status", response_model=PaperOperatorCanaryStatus, dependencies=[Depends(require_scope(PaperOperatorScope.CANARY_STATUS_READ))])
    def canary_status(
        canary_id: str | None = None,
        arm_request_id: str | None = None,
    ) -> PaperOperatorCanaryStatus:
        return service.canary_status(canary_id=canary_id, arm_request_id=arm_request_id)

    @router.get("/canaries/{canary_id}", response_model=PaperOperatorCanaryStatus, dependencies=[Depends(require_scope(PaperOperatorScope.CANARY_STATUS_READ))])
    def canary_by_id(canary_id: str) -> PaperOperatorCanaryStatus:
        return service.canary_status(canary_id=canary_id)

    @router.post("/arm-first-canary", response_model=PaperOperatorControlDecision, dependencies=[Depends(require_scope(PaperOperatorScope.CANARY_ARM))])
    def arm(request: PaperOperatorArmFirstCanaryRequest) -> PaperOperatorControlDecision:
        return service.arm_first_canary(request)

    @router.post("/start-first-canary", response_model=PaperOperatorControlDecision, dependencies=[Depends(require_scope(PaperOperatorScope.CANARY_START))])
    def start(request: PaperOperatorStartFirstCanaryRequest) -> PaperOperatorControlDecision:
        return service.start_first_canary(request)

    @router.post("/disable", response_model=PaperOperatorControlDecision, dependencies=[Depends(require_scope(PaperOperatorScope.CONTROL_DISABLE))])
    def disable(request: PaperOperatorTransitionRequest) -> PaperOperatorControlDecision:
        return service.disable(request)

    @router.post("/emergency-stop", response_model=PaperOperatorControlDecision, dependencies=[Depends(require_scope(PaperOperatorScope.CONTROL_EMERGENCY_STOP))])
    def emergency_stop(request: PaperOperatorTransitionRequest) -> PaperOperatorControlDecision:
        return service.emergency_stop(request)

    @router.post("/clear-emergency-stop", response_model=PaperOperatorControlDecision, dependencies=[Depends(require_scope(PaperOperatorScope.CONTROL_CLEAR_EMERGENCY_STOP))])
    def clear_stop(request: PaperOperatorClearEmergencyStopRequest) -> PaperOperatorControlDecision:
        return service.clear_emergency_stop(request)

    return router
