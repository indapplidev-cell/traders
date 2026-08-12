from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.engine_safety.paper_production_control import (
    PaperProductionSafetyControl,
    PersistentState,
    ReasonCode,
)
from app.operator_control.app import create_paper_operator_control_app
from app.operator_control.auth import ALL_OPERATOR_SCOPES, PaperOperatorAuthenticator, PaperOperatorCapability
from app.operator_control.config import PaperOperatorControlConfig
from app.operator_control.service import PaperOperatorControlService

from .conftest import AUTH, TOKEN, arm_body, transition_body


@pytest.fixture
def foundation(tmp_path):
    control = PaperProductionSafetyControl(tmp_path / "production-snapshot", acl_checker=lambda _path: True)
    control.initialize_disabled(acknowledge=True)
    control.transition(PersistentState.EMERGENCY_STOP, expected_generation=1, reason=ReasonCode.SAFETY_TEST, acknowledge=True)
    control.transition(PersistentState.DISABLED, expected_generation=2, reason=ReasonCode.SAFETY_TEST, acknowledge=True)
    config = PaperOperatorControlConfig()
    service = PaperOperatorControlService(config=config, control=control)
    capability = PaperOperatorCapability(TOKEN.encode("ascii"), ALL_OPERATOR_SCOPES)
    client = TestClient(create_paper_operator_control_app(
        config=config, service=service, authenticator=PaperOperatorAuthenticator((capability,))
    ))
    return client, control


def test_foundation_status_and_canary_status_are_safe(foundation):
    client, _ = foundation
    status = client.get("/control/v1/status", headers=AUTH)
    assert status.status_code == 200
    assert status.json() == {
        "control_api_version": "1",
        "foundation_mode": "DISABLED_FOUNDATION",
        "service_enabled": False,
        "bind_scope": "LOOPBACK_ONLY",
        "environment": "PRODUCTION",
        "mode": "PAPER",
        "control_state": "DISABLED",
        "effective_state": "DISABLED",
        "generation": 3,
        "control_health": "HEALTHY",
        "audit_health": "PASS",
        "state_audit_reconciliation": "PASS",
        "emergency_stop_available": True,
        "live_allowed": False,
        "production_mutation_enabled": False,
    }
    canary = client.get("/control/v1/canary/status", headers=AUTH)
    assert canary.status_code == 200
    assert canary.json()["state"] == "DISABLED"
    assert canary.json()["availability_code"] == "PAPER_SCHEMA_NOT_DEPLOYED"
    assert canary.json()["deployment_status"] == "NOT_DEPLOYED"


def _requests():
    return (
        ("/control/v1/arm-first-canary", arm_body("foundation-arm", 3)),
        ("/control/v1/start-first-canary", {
            "request_id": "foundation-start", "expected_generation": 3,
            "canary_id": "00000000-0000-4000-8000-000000000004",
            "arming_transition_id": "00000000-0000-4000-8000-000000000003",
            "canary_acknowledgement": True,
        }),
        ("/control/v1/disable", transition_body("foundation-disable", 3)),
        ("/control/v1/emergency-stop", transition_body("foundation-stop", 3)),
        ("/control/v1/clear-emergency-stop", transition_body(
            "foundation-clear", 3, clear_emergency_stop_acknowledgement=True
        )),
    )


@pytest.mark.parametrize("path,body", _requests())
def test_every_foundation_post_stops_before_authority(foundation, path, body):
    client, control = foundation
    state_before = control.state_path.read_bytes()
    audit_before = control.audit_path.read_bytes()
    response = client.post(path, json=body, headers=AUTH)
    assert response.status_code == 409
    assert response.json()["finding_codes"] == ["CONTROL_API_DISABLED_FOUNDATION"]
    assert response.json()["executed"] is False
    assert response.json()["generation_before"] == response.json()["generation_after"] == 3
    assert response.json()["state_before"] == response.json()["state_after"] == "DISABLED"
    assert control.state_path.read_bytes() == state_before
    assert control.audit_path.read_bytes() == audit_before


def test_missing_and_corrupt_state_fail_closed_without_raw_error(foundation):
    client, control = foundation
    control.state_path.unlink()
    response = client.get("/control/v1/status", headers=AUTH)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "CONTROL_STATE_UNAVAILABLE"
    assert str(control.root) not in response.text
