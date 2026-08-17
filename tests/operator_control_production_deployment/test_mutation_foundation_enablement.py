from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.operator_control.auth import ProtectedFileOperatorCredentialBinding
from app.operator_control.config import (
    PaperOperatorControlConfig,
    PaperOperatorControlOperationMode,
)
from app.operator_control.runtime import (
    RUNTIME_DATABASE_HOST_KEY,
    RUNTIME_DATABASE_PORT_KEY,
    ReadonlyExistingCanaryRuntimeReadinessSource,
    ReadonlyPaperArmReadinessSource,
    _production_canary_store,
    create_runtime_app,
)
from app.engine_paper.production_preparation_backend import RUNTIME_DATABASE_KEY
from app.operator_control.service import PaperOperatorArmReadiness

from .test_runtime_and_binding import TOKEN, generation_three_control


def _body(request_id: str, generation: int = 3, *, mode: str = "PAPER") -> dict[str, object]:
    return {
        "request_id": request_id,
        "expected_generation": generation,
        "environment": "PRODUCTION",
        "mode": mode,
        "max_new_commands": 1,
        "max_open_positions": 1,
        "allowed_symbols": ["BTCUSDT"],
        "operator_acknowledgement": True,
        "paper_acknowledgement": True,
        "live_forbidden_acknowledgement": True,
    }


def _client(tmp_path, *, ready: bool) -> tuple[TestClient, object]:
    token_path = tmp_path / "token"
    token_path.write_bytes(TOKEN)
    control = generation_three_control(tmp_path / "control")
    app = create_runtime_app(
        credential_binding=ProtectedFileOperatorCredentialBinding(token_path),
        control=control,
        readiness=(PaperOperatorArmReadiness.isolated_ready if ready else PaperOperatorArmReadiness),
        require_production_store=False,
        runtime_identity="foundation-test",
    )
    return TestClient(app), control


def test_tracked_production_mode_is_enabled_paper_only_and_defaults_remain_disabled():
    default = PaperOperatorControlConfig()
    production = PaperOperatorControlConfig.production_paper()
    assert default.operation_mode is PaperOperatorControlOperationMode.DISABLED_FOUNDATION
    assert default.mutation_foundation_enabled is False
    assert production.operation_mode is PaperOperatorControlOperationMode.PRODUCTION_PAPER
    assert production.mutation_foundation_enabled is True
    assert production.mode == "PAPER"
    assert production.live_allowed is False


def test_enablement_is_non_mutating_and_reaches_normal_readiness_guard(tmp_path):
    client, control = _client(tmp_path, ready=False)
    before_state = control.state_path.read_bytes()
    before_audit = control.audit_path.read_bytes()
    status = client.get(
        "/control/v1/status", headers={"Authorization": "Bearer " + TOKEN.decode()}
    )
    assert status.status_code == 200
    assert status.json()["foundation_mode"] == "PRODUCTION_PAPER"
    assert status.json()["service_enabled"] is True
    assert status.json()["production_mutation_enabled"] is True
    assert status.json()["control_state"] == "DISABLED"
    assert status.json()["generation"] == 3
    response = client.post(
        "/control/v1/arm-first-canary",
        json=_body("production-readiness-guard"),
        headers={"Authorization": "Bearer " + TOKEN.decode()},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PAPER_SCHEMA_NOT_DEPLOYED"
    assert "CONTROL_API_DISABLED_FOUNDATION" not in response.text
    assert control.state_path.read_bytes() == before_state
    assert control.audit_path.read_bytes() == before_audit


def test_auth_generation_idempotency_audit_and_live_guards_survive_enablement(tmp_path):
    client, control = _client(tmp_path, ready=True)
    path = "/control/v1/arm-first-canary"
    assert client.post(path, json=_body("missing-auth")).status_code == 401
    assert client.post(
        path, json=_body("invalid-auth"), headers={"Authorization": "Bearer invalid"}
    ).status_code == 401
    auth = {"Authorization": "Bearer " + TOKEN.decode()}
    stale = client.post(path, json=_body("stale-generation", 2), headers=auth)
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "STALE_GENERATION"
    live = client.post(path, json=_body("live-denied", mode="LIVE"), headers=auth)
    assert live.status_code == 400
    assert live.json()["error"]["code"] == "LIVE_NOT_ALLOWED"
    audit_before = control.audit_path.read_bytes()
    body = _body("valid-isolated-production-arm")
    first = client.post(path, json=body, headers=auth)
    assert first.status_code == 200
    audit_after = control.audit_path.read_bytes()
    assert audit_after != audit_before
    replay = client.post(path, json=body, headers=auth)
    assert replay.status_code == 200
    assert replay.json() == first.json()
    assert control.audit_path.read_bytes() == audit_after
    assert first.json()["state_after"] == "ARMED"
    assert first.json()["generation_after"] == 4
    assert "CONTROL_API_DISABLED_FOUNDATION" not in first.text


def test_route_inventories_remain_exact(tmp_path):
    client, _ = _client(tmp_path, ready=False)
    routes = [route for route in client.app.routes if getattr(route, "methods", None)]
    assert sum("GET" in route.methods for route in routes) == 3
    assert sum("POST" in route.methods for route in routes) == 5


def test_readonly_readiness_source_consumes_authoritative_envelope(monkeypatch):
    payload = {
        "data": {
            "status": "READY",
            "current_mutation_ready": True,
            "current_mutation_denial_reasons": [],
            "paper_control_state": "DISABLED",
            "paper_control_effective_state": "DISABLED",
            "paper_control_health": "HEALTHY",
        }
    }

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return json.dumps(payload).encode()

    monkeypatch.setattr("app.operator_control.runtime.urllib.request.urlopen", lambda *_a, **_k: Response())
    readiness = ReadonlyPaperArmReadinessSource()()
    assert readiness.finding_codes == ()
    assert readiness.live_disabled is True
    assert readiness.binance_order_authority_absent is True


def test_armed_existing_runtime_accepts_only_the_two_precontrol_denials(monkeypatch):
    payload = {
        "data": {
            "status": "READY", "paper_schema_ready": True,
            "account_baseline_exists": True, "account_baseline_valid": True,
            "accounting_reconciliation_status": "HEALTHY",
            "paper_reconciliation_status": "HEALTHY", "paper_runtime_enabled": True,
            "paper_control_state": "ARMED", "paper_control_effective_state": "ARMED",
            "paper_control_health": "HEALTHY", "live_allowed": False,
            "market_data_adapter_ready": True, "approval_source_adapter_ready": True,
            "wal_ready": True, "pitr_ready": True, "current_mutation_ready": False,
            "current_mutation_denial_reasons": [
                "KILL_SWITCH_NOT_READY", "CONTROL_NOT_ELIGIBLE"
            ],
        }
    }

    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *_args): return None
        def read(self): return json.dumps(payload).encode()

    monkeypatch.setattr("app.operator_control.runtime.urllib.request.urlopen", lambda *_a, **_k: Response())
    readiness = ReadonlyExistingCanaryRuntimeReadinessSource()()
    assert readiness.market_data_ready and readiness.approval_source_ready
    assert readiness.wal_ready and readiness.pitr_ready and readiness.backup_pitr_pass
    assert readiness.live_disabled


def test_existing_runtime_readiness_fails_closed_on_wal_pitr_or_extra_denial(monkeypatch):
    base = {
        "status": "READY", "paper_schema_ready": True,
        "account_baseline_exists": True, "account_baseline_valid": True,
        "accounting_reconciliation_status": "HEALTHY",
        "paper_reconciliation_status": "HEALTHY", "paper_runtime_enabled": True,
        "paper_control_state": "ARMED", "paper_control_effective_state": "ARMED",
        "paper_control_health": "HEALTHY", "live_allowed": False,
        "market_data_adapter_ready": True, "approval_source_adapter_ready": True,
        "wal_ready": True, "pitr_ready": True, "current_mutation_ready": False,
        "current_mutation_denial_reasons": ["KILL_SWITCH_NOT_READY", "CONTROL_NOT_ELIGIBLE"],
    }

    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *_args): return None
        def read(self): return json.dumps({"data": current}).encode()

    source = ReadonlyExistingCanaryRuntimeReadinessSource()
    for changes in (
        {"wal_ready": False, "current_mutation_denial_reasons": ["WAL_NOT_READY", "KILL_SWITCH_NOT_READY", "CONTROL_NOT_ELIGIBLE"]},
        {"pitr_ready": False, "current_mutation_denial_reasons": ["PITR_NOT_READY", "KILL_SWITCH_NOT_READY", "CONTROL_NOT_ELIGIBLE"]},
        {"current_mutation_denial_reasons": ["KILL_SWITCH_NOT_READY", "CONTROL_NOT_ELIGIBLE", "CANARY_SCOPE_INVALID"]},
        {"paper_control_state": "EMERGENCY_STOP", "paper_control_effective_state": "EMERGENCY_STOP"},
    ):
        current = {**base, **changes}
        monkeypatch.setattr("app.operator_control.runtime.urllib.request.urlopen", lambda *_a, **_k: Response())
        readiness = source()
        assert not readiness.backup_pitr_pass
        assert not readiness.live_disabled


def test_runtime_database_binding_translates_only_exact_host_endpoint(monkeypatch):
    monkeypatch.setenv(
        RUNTIME_DATABASE_KEY,
        "postgresql+psycopg" + "://traders_paper_runtime:isolated-password@127.0.0.1:5433/traders",
    )
    monkeypatch.setenv(RUNTIME_DATABASE_HOST_KEY, "postgres")
    monkeypatch.setenv(RUNTIME_DATABASE_PORT_KEY, "5432")
    _, engine = _production_canary_store()
    try:
        assert engine.url.host == "postgres"
        assert engine.url.port == 5432
        assert engine.url.username == "traders_paper_runtime"
        assert engine.url.database == "traders"
    finally:
        engine.dispose()
