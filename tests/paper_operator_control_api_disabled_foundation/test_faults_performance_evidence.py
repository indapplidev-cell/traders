from __future__ import annotations

import hashlib
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.engine_safety.paper_production_control import (
    PaperProductionSafetyControl,
    PersistentState,
    ReasonCode,
    SafetyControlError,
)
from app.operator_control.app import create_paper_operator_control_app
from app.operator_control.auth import ALL_OPERATOR_SCOPES, PaperOperatorAuthenticator, PaperOperatorCapability
from app.operator_control.config import PaperOperatorControlConfig, PaperOperatorControlOperationMode
from app.operator_control.schemas import PaperCanaryNormalizedState, PaperOperatorCanaryStatus
from app.operator_control.service import PaperOperatorArmReadiness, PaperOperatorControlService

from .conftest import AUTH, TOKEN, arm_body, transition_body


EVIDENCE = Path(r"D:\disk_E\game_projects\traders\evidence_inbox")
EXPECTED_EVIDENCE = {
    "TRADERS_ML_PAPER_TRADING_PRODUCTION_KILL_SWITCH_AND_EMERGENCY_STOP_01_FINAL.md": "f519157b39c954f166a3fdb4e2095fe02cb7e1df1f93a54531cf8abd841e6f55",
    "TRADERS_ML_PAPER_TRADING_PRODUCTION_PAPER_PREPARATION_DISABLED_WIRING_01_FINAL.md": "8e2d4569bab6e230bcb3418d774b4ecf43ee5a60d53db27c539a8d0643b0b826",
    "TRADERS_ML_PAPER_TRADING_ACCOUNT_BASELINE_PERSISTENCE_SCHEMA_EXTENSION_01_FINAL.md": "bc5377debdae3a014e76bafc32bda4e62f34f413398657033b34916075d8604d",
    "TRADERS_ML_PAPER_TRADING_READONLY_PAPER_REPORTING_API_01_FINAL.md": "f6ee5c1b554b15d4a4643f6326a502a457022fa8d7d1dbd0851b98bce34cd15b",
}


@pytest.mark.parametrize("name,expected", EXPECTED_EVIDENCE.items())
def test_required_source_evidence_hashes(name, expected):
    assert hashlib.sha256((EVIDENCE / name).read_bytes()).hexdigest() == expected


def _client(control, *, executor=None):
    config = PaperOperatorControlConfig(
        enabled=True,
        operation_mode=PaperOperatorControlOperationMode.ISOLATED_CONTROL_ROOT,
    )
    service = PaperOperatorControlService(
        config=config,
        control=control,
        readiness=PaperOperatorArmReadiness.isolated_ready,
        executor=executor,
    )
    capability = PaperOperatorCapability(TOKEN.encode(), ALL_OPERATOR_SCOPES)
    return TestClient(create_paper_operator_control_app(
        config=config, service=service, authenticator=PaperOperatorAuthenticator((capability,))
    ))


def test_audit_mismatch_is_sanitized_fail_closed(isolated_client, isolated_control):
    isolated_control.audit_path.write_bytes(isolated_control.audit_path.read_bytes() + b"{}\n")
    response = isolated_client.get("/control/v1/status", headers=AUTH)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AUDIT_RECONCILIATION_FAILED"
    assert str(isolated_control.root) not in response.text


def test_interlock_busy_maps_to_423(tmp_path):
    root = tmp_path / "busy"
    initializer = PaperProductionSafetyControl(root, acl_checker=lambda _path: True)
    initializer.initialize_disabled(acknowledge=True)
    def fault(point: str):
        if point == "before lock":
            raise SafetyControlError("INTERLOCK_BUSY")
    control = PaperProductionSafetyControl(root, acl_checker=lambda _path: True, fault_injector=fault)
    response = _client(control).post(
        "/control/v1/emergency-stop", json=transition_body("busy-stop-0001", 1), headers=AUTH
    )
    assert response.status_code == 423
    assert response.json()["error"]["code"] == "INTERLOCK_BUSY"
    assert initializer.read_authoritative().state is PersistentState.DISABLED


class FaultingExecutor:
    def preflight(self, **_kwargs):
        raise TimeoutError("private executor diagnostic")
    def start_bounded_canary(self, **_kwargs):
        raise AssertionError("unreachable")
    def status(self):
        raise ConnectionError("private database diagnostic")


class NoApprovalExecutor:
    started = 0
    def preflight(self, **_kwargs):
        return ("NO_ELIGIBLE_APPROVAL",)
    def start_bounded_canary(self, **_kwargs):
        self.started += 1
        return ()
    def status(self):
        return PaperOperatorCanaryStatus(
            state=PaperCanaryNormalizedState.NO_ELIGIBLE_APPROVAL,
            availability_code="NO_ELIGIBLE_APPROVAL",
            deployment_status="ISOLATED",
        )


def _armed_client(tmp_path, executor):
    root = tmp_path / type(executor).__name__
    control = PaperProductionSafetyControl(root, acl_checker=lambda _path: True)
    control.initialize_disabled(acknowledge=True)
    client = _client(control, executor=executor)
    arm = client.post("/control/v1/arm-first-canary", json=arm_body(), headers=AUTH).json()
    start = {
        "request_id": f"start-{type(executor).__name__.lower()}",
        "expected_generation": arm["generation_after"],
        "canary_id": arm["canary_id"],
        "arming_transition_id": arm["transition_id"],
        "canary_acknowledgement": True,
    }
    return client, control, start


def test_executor_timeout_and_database_unavailability_are_sanitized(tmp_path):
    client, control, start = _armed_client(tmp_path, FaultingExecutor())
    status = client.get("/control/v1/canary/status", headers=AUTH)
    assert status.status_code == 503
    assert "private" not in status.text
    response = client.post("/control/v1/start-first-canary", json=start, headers=AUTH)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "CONTROL_SAFE_FAILURE"
    assert control.read_authoritative().generation == 2


def test_no_eligible_approval_is_healthy_zero_mutation(tmp_path):
    executor = NoApprovalExecutor()
    client, control, start = _armed_client(tmp_path, executor)
    before = control.audit_path.read_bytes()
    response = client.post("/control/v1/start-first-canary", json=start, headers=AUTH)
    assert response.status_code == 200
    assert response.json()["accepted"] is True
    assert response.json()["executed"] is False
    assert response.json()["finding_codes"] == ["NO_ELIGIBLE_APPROVAL"]
    assert executor.started == 0
    assert control.audit_path.read_bytes() == before


def test_disable_vs_stop_and_clear_stop_races_are_generation_safe(isolated_client, isolated_control):
    arm = isolated_client.post("/control/v1/arm-first-canary", json=arm_body(), headers=AUTH).json()
    calls = (
        ("/control/v1/disable", transition_body("race-disable-0001", arm["generation_after"])),
        ("/control/v1/emergency-stop", transition_body("race-stop-0002", arm["generation_after"])),
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda item: isolated_client.post(item[0], json=item[1], headers=AUTH), calls))
    assert sum(item.status_code == 200 for item in responses) == 1
    state = isolated_control.read_authoritative()
    if state.state is PersistentState.DISABLED:
        stopped = isolated_client.post(
            "/control/v1/emergency-stop", json=transition_body("race-stop-followup-2", state.generation), headers=AUTH
        )
        assert stopped.status_code == 200
        state = isolated_control.read_authoritative()
    assert state.state is PersistentState.EMERGENCY_STOP
    clear_calls = tuple(
        ("/control/v1/clear-emergency-stop", transition_body(
            f"race-clear-{index:04d}", state.generation, clear_emergency_stop_acknowledgement=True
        ))
        for index in range(4)
    )
    with ThreadPoolExecutor(max_workers=4) as pool:
        clear_results = list(pool.map(lambda item: isolated_client.post(item[0], json=item[1], headers=AUTH), clear_calls))
    assert sum(item.status_code == 200 for item in clear_results) == 1
    assert isolated_control.read_authoritative().state is PersistentState.DISABLED


def test_repeated_emergency_stop_is_idempotent_at_authority(isolated_client, isolated_control):
    first = isolated_client.post(
        "/control/v1/emergency-stop", json=transition_body("repeat-stop-0001", 1), headers=AUTH
    )
    second = isolated_client.post(
        "/control/v1/emergency-stop", json=transition_body("repeat-stop-0002", 2), headers=AUTH
    )
    assert first.status_code == second.status_code == 200
    assert second.json()["executed"] is False
    assert second.json()["generation_before"] == second.json()["generation_after"] == 2
    assert isolated_control.read_authoritative().generation == 2


def _p95(values):
    return statistics.quantiles(values, n=100, method="inclusive")[94]


def test_local_status_and_transition_latency_targets(isolated_client):
    status = []
    canary = []
    for _ in range(30):
        started = time.perf_counter()
        assert isolated_client.get("/control/v1/status", headers=AUTH).status_code == 200
        status.append((time.perf_counter() - started) * 1000)
        started = time.perf_counter()
        assert isolated_client.get("/control/v1/canary/status", headers=AUTH).status_code == 200
        canary.append((time.perf_counter() - started) * 1000)
    assert _p95(status) < 100
    assert _p95(canary) < 150
