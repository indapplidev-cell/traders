from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from app.engine_safety.paper_production_control import PersistentState

from .conftest import AUTH, arm_body, transition_body


def test_disabled_to_armed_and_armed_to_disabled_through_http(isolated_client, isolated_control):
    arm = isolated_client.post("/control/v1/arm-first-canary", json=arm_body(), headers=AUTH)
    assert arm.status_code == 200
    assert arm.json() | {"ignored": None}
    assert arm.json()["state_before"] == "DISABLED"
    assert arm.json()["state_after"] == "ARMED"
    assert arm.json()["generation_after"] == 2
    disable = isolated_client.post(
        "/control/v1/disable", json=transition_body("request-disable-0001", 2), headers=AUTH
    )
    assert disable.status_code == 200
    assert disable.json()["state_after"] == "DISABLED"
    assert disable.json()["generation_after"] == 3
    assert isolated_control.read_authoritative().state is PersistentState.DISABLED


def test_disabled_to_stop_and_stop_to_disabled_through_http(isolated_client, isolated_control):
    stopped = isolated_client.post(
        "/control/v1/emergency-stop", json=transition_body("request-stop-00001", 1), headers=AUTH
    )
    assert stopped.status_code == 200
    assert stopped.json()["state_after"] == "EMERGENCY_STOP"
    cleared = isolated_client.post(
        "/control/v1/clear-emergency-stop",
        json=transition_body("request-clear-0001", 2, clear_emergency_stop_acknowledgement=True),
        headers=AUTH,
    )
    assert cleared.status_code == 200
    assert cleared.json()["state_after"] == "DISABLED"
    assert cleared.json()["generation_after"] == 3
    assert isolated_control.read_authoritative().state is PersistentState.DISABLED


def test_armed_to_emergency_stop_through_http(isolated_client):
    arm = isolated_client.post("/control/v1/arm-first-canary", json=arm_body(), headers=AUTH).json()
    stopped = isolated_client.post(
        "/control/v1/emergency-stop",
        json=transition_body("request-stop-armed", arm["generation_after"]),
        headers=AUTH,
    )
    assert stopped.status_code == 200
    assert stopped.json()["state_before"] == "ARMED"
    assert stopped.json()["state_after"] == "EMERGENCY_STOP"


def test_emergency_stop_to_armed_is_denied(isolated_client):
    isolated_client.post(
        "/control/v1/emergency-stop", json=transition_body("request-stop-00002", 1), headers=AUTH
    )
    response = isolated_client.post(
        "/control/v1/arm-first-canary",
        json=arm_body("request-arm-denied", 2),
        headers=AUTH,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ILLEGAL_CONTROL_TRANSITION"


def test_same_replay_returns_same_result_without_duplicate_transition(isolated_client, isolated_control):
    body = arm_body("request-replay-0001")
    first = isolated_client.post("/control/v1/arm-first-canary", json=body, headers=AUTH)
    audit = isolated_control.audit_path.read_bytes()
    second = isolated_client.post("/control/v1/arm-first-canary", json=body, headers=AUTH)
    assert second.status_code == 200
    assert second.json() == first.json()
    assert isolated_control.audit_path.read_bytes() == audit


def test_conflicting_request_id_is_409(isolated_client):
    first = isolated_client.post(
        "/control/v1/arm-first-canary", json=arm_body("request-conflict-01"), headers=AUTH
    )
    assert first.status_code == 200
    conflict = isolated_client.post(
        "/control/v1/arm-first-canary",
        json=arm_body("request-conflict-01", allowed_symbols=["ETHUSDT"]),
        headers=AUTH,
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "REQUEST_ID_CONFLICT"


def test_stale_generation_is_409(isolated_client):
    response = isolated_client.post(
        "/control/v1/emergency-stop", json=transition_body("request-stale-0001", 2), headers=AUTH
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "STALE_GENERATION"


def test_start_is_immediate_bounded_executor_call(isolated_client, isolated_executor):
    arm = isolated_client.post("/control/v1/arm-first-canary", json=arm_body(), headers=AUTH).json()
    response = isolated_client.post(
        "/control/v1/start-first-canary",
        json={
            "request_id": "request-start-0001",
            "expected_generation": arm["generation_after"],
            "canary_id": arm["canary_id"],
            "arming_transition_id": arm["transition_id"],
            "canary_acknowledgement": True,
        },
        headers=AUTH,
    )
    assert response.status_code == 200
    assert response.json()["executed"] is True
    assert response.json()["generation_before"] == response.json()["generation_after"] == 2
    assert isolated_executor.started == 1


def test_concurrent_arm_at_most_one_wins(isolated_client, isolated_control):
    def call(index: int):
        return isolated_client.post(
            "/control/v1/arm-first-canary",
            json=arm_body(f"concurrent-arm-{index:04d}"),
            headers=AUTH,
        )
    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(call, range(8)))
    assert sum(item.status_code == 200 for item in responses) == 1
    assert all(item.status_code in {200, 409} for item in responses)
    assert isolated_control.read_authoritative().generation == 2


def test_arm_vs_emergency_stop_cannot_overwrite_stop(isolated_client, isolated_control):
    calls = (
        ("/control/v1/arm-first-canary", arm_body("race-arm-0001")),
        ("/control/v1/emergency-stop", transition_body("race-stop-0001", 1)),
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda item: isolated_client.post(item[0], json=item[1], headers=AUTH), calls))
    assert sum(item.status_code == 200 for item in responses) == 1
    assert isolated_control.read_authoritative().state in {PersistentState.ARMED, PersistentState.EMERGENCY_STOP}
    if isolated_control.read_authoritative().state is PersistentState.ARMED:
        stop = isolated_client.post(
            "/control/v1/emergency-stop", json=transition_body("race-stop-followup", 2), headers=AUTH
        )
        assert stop.status_code == 200
        assert isolated_control.read_authoritative().state is PersistentState.EMERGENCY_STOP

@pytest.mark.parametrize("unavailable", ["database", "readonly_api", "market_data", "orchestrator"])
def test_emergency_stop_has_no_external_dependency(isolated_client, isolated_control, unavailable):
    response = isolated_client.post(
        "/control/v1/emergency-stop",
        json=transition_body(f"independent-{unavailable}", 1),
        headers=AUTH,
    )
    assert response.status_code == 200
    assert isolated_control.read_authoritative().state is PersistentState.EMERGENCY_STOP
