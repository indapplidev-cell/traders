from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from app.engine_safety.paper_production_control import (
    PaperProductionSafetyControl,
    PersistentState,
    ReasonCode,
)
from app.operator_control.app import create_paper_operator_control_app
from app.operator_control.auth import (
    ALL_OPERATOR_SCOPES,
    PaperOperatorAuthenticator,
    PaperOperatorCapability,
)
from app.operator_control.config import (
    PaperOperatorControlConfig,
    PaperOperatorControlOperationMode,
)
from app.operator_control.schemas import (
    PaperCanaryNormalizedState,
    PaperOperatorCanaryStatus,
)
from app.operator_control.service import (
    PaperOperatorArmReadiness,
    PaperOperatorControlService,
)


TOKEN = "isolated-operator-capability-0000000000000001"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@dataclass
class IsolatedExecutor:
    started: int = 0

    def preflight(self, *, transition_id: str, generation: int) -> tuple[str, ...]:
        return ()

    def start_bounded_canary(self, *, request_id: str, transition_id: str, generation: int) -> tuple[str, ...]:
        self.started += 1
        return ()

    def status(self) -> PaperOperatorCanaryStatus:
        return PaperOperatorCanaryStatus(
            state=PaperCanaryNormalizedState.ARMED_WAITING,
            availability_code="READY",
            deployment_status="ISOLATED",
            allowed_symbols=("BTCUSDT",),
        )


@pytest.fixture
def capability() -> PaperOperatorCapability:
    return PaperOperatorCapability(TOKEN.encode("ascii"), ALL_OPERATOR_SCOPES)


@pytest.fixture
def isolated_control(tmp_path) -> PaperProductionSafetyControl:
    control = PaperProductionSafetyControl(tmp_path / "control", acl_checker=lambda _path: True)
    control.initialize_disabled(acknowledge=True)
    return control


@pytest.fixture
def isolated_executor() -> IsolatedExecutor:
    return IsolatedExecutor()


@pytest.fixture
def isolated_client(isolated_control, isolated_executor, capability) -> TestClient:
    config = PaperOperatorControlConfig(
        enabled=True,
        operation_mode=PaperOperatorControlOperationMode.ISOLATED_CONTROL_ROOT,
    )
    service = PaperOperatorControlService(
        config=config,
        control=isolated_control,
        readiness=PaperOperatorArmReadiness.isolated_ready,
        executor=isolated_executor,
    )
    app = create_paper_operator_control_app(
        config=config,
        authenticator=PaperOperatorAuthenticator((capability,)),
        service=service,
    )
    return TestClient(app)


def arm_body(request_id: str = "request-arm-0001", generation: int = 1, **changes):
    body = {
        "request_id": request_id,
        "expected_generation": generation,
        "environment": "PRODUCTION",
        "mode": "PAPER",
        "max_new_commands": 1,
        "max_open_positions": 1,
        "allowed_symbols": ["BTCUSDT"],
        "operator_acknowledgement": True,
        "paper_acknowledgement": True,
        "live_forbidden_acknowledgement": True,
    }
    body.update(changes)
    return body


def transition_body(request_id: str, generation: int, **changes):
    body = {
        "request_id": request_id,
        "expected_generation": generation,
        "operator_acknowledgement": True,
    }
    body.update(changes)
    return body
