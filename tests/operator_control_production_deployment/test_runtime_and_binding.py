from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.engine_safety.paper_production_control import (
    ArmReadinessPreflight,
    PaperProductionArmingScope,
    PaperProductionSafetyControl,
    PersistentState,
    ReasonCode,
)
from app.operator_control.auth import ProtectedFileOperatorCredentialBinding
from app.operator_control.runtime import create_runtime_app, main


TOKEN = b"isolated-control-token-material-0123456789abcdef"


def generation_three_control(root: Path) -> PaperProductionSafetyControl:
    control = PaperProductionSafetyControl(root, acl_checker=lambda _path: True)
    control.initialize_disabled(acknowledge=True)
    control.transition(
        PersistentState.ARMED, expected_generation=1, reason=ReasonCode.OPERATOR_ARM,
        acknowledge=True, acknowledge_paper_arming=True,
        preflight=ArmReadinessPreflight(True, True, True, True, True, True, True, True, True),
        arming_scope=PaperProductionArmingScope(
            max_new_commands=1, max_open_positions=1,
            allowed_symbols=("BTCUSDT",),
        ),
    )
    control.transition(
        PersistentState.DISABLED, expected_generation=2,
        reason=ReasonCode.OPERATOR_DISABLE, acknowledge=True,
    )
    return control


def test_production_app_binding_auth_routes_and_disabled_state(tmp_path):
    token_path = tmp_path / "token"
    token_path.write_bytes(TOKEN)
    binding = ProtectedFileOperatorCredentialBinding(token_path)
    control = generation_three_control(tmp_path / "control")
    app = create_runtime_app(
        credential_binding=binding,
        control=control,
        runtime_identity="build-1",
        require_production_store=False,
    )
    routes = [(route.path, route.methods) for route in app.routes]
    assert sum("GET" in methods for _, methods in routes) == 3
    assert sum("POST" in methods for _, methods in routes) == 5
    with TestClient(app) as client:
        assert client.post("/control/v1/disable", json={}).status_code == 401
        assert client.post("/control/v1/disable", headers={"Authorization": "Bearer invalid"}, json={}).status_code == 401
        response = client.get("/control/v1/status", headers={"Authorization": "Bearer " + TOKEN.decode()})
        assert response.status_code == 200
        assert response.json()["control_state"] == "DISABLED"
        assert response.json()["generation"] == 3
        assert response.json()["foundation_mode"] == "PRODUCTION_PAPER"
        assert response.json()["production_mutation_enabled"] is True
    after = control.read_authoritative()
    assert (after.state.value, after.generation) == ("DISABLED", 3)
    assert app.state.runtime_identity == "build-1"
    assert "protected=True" in repr(binding) and TOKEN.decode() not in repr(binding)


def test_entrypoint_binds_exact_loopback_port_and_single_factory(monkeypatch):
    captured = {}
    monkeypatch.setattr("app.operator_control.runtime.run_server", lambda *args, **kwargs: captured.update(args=args, kwargs=kwargs))
    assert main([]) == 0
    assert captured["args"] == ("app.operator_control.runtime:create_runtime_app",)
    assert captured["kwargs"]["factory"] is True
    assert captured["kwargs"]["host"] == "127.0.0.1"
    assert captured["kwargs"]["port"] == 8766
    assert captured["kwargs"]["workers"] == 1


def test_binding_failures_and_repr_never_disclose_secret(tmp_path):
    binding = ProtectedFileOperatorCredentialBinding(tmp_path / "missing")
    try:
        binding.load_current()
    except Exception as error:
        assert str(error) == "CONTROL_CREDENTIAL_UNAVAILABLE"
        assert TOKEN.decode() not in str(error)
    else:
        raise AssertionError("missing credential accepted")
