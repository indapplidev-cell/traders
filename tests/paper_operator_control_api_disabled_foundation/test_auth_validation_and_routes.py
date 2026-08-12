from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.operator_control.app import create_paper_operator_control_app
from app.operator_control.auth import (
    PaperOperatorAuthenticator,
    PaperOperatorCapability,
    PaperOperatorScope,
)
from app.operator_control.config import PaperOperatorControlConfig
from app.server_api.app_factory import create_app as create_readonly_app

from .conftest import AUTH, TOKEN, arm_body


def test_exact_control_route_inventory(isolated_client):
    routes = {
        (next(iter(route.methods)), route.path)
        for route in isolated_client.app.routes
        if getattr(route, "methods", None)
    }
    assert routes == {
        ("GET", "/control/v1/status"),
            ("GET", "/control/v1/canary/status"),
            ("GET", "/control/v1/canaries/{canary_id}"),
        ("POST", "/control/v1/arm-first-canary"),
        ("POST", "/control/v1/start-first-canary"),
        ("POST", "/control/v1/disable"),
        ("POST", "/control/v1/emergency-stop"),
        ("POST", "/control/v1/clear-emergency-stop"),
    }


def test_readonly_api_has_no_operator_control_or_write_routes():
    routes = [route for route in create_readonly_app().routes if getattr(route, "methods", None)]
    assert not any(route.path.startswith("/control/v1") for route in routes)
    assert not any(route.methods & {"POST", "PUT", "PATCH", "DELETE"} for route in routes)


@pytest.mark.parametrize("path", ["/orders", "/positions", "/trade", "/buy", "/sell", "/control/state", "/config"])
def test_generic_mutation_routes_do_not_exist(isolated_client, path):
    assert isolated_client.post(path, headers=AUTH, json={}).status_code == 404


def test_missing_invalid_and_insufficient_auth(isolated_client, isolated_control):
    assert isolated_client.get("/control/v1/status").status_code == 401
    invalid = isolated_client.get("/control/v1/status", headers={"Authorization": "Bearer wrong"})
    assert invalid.status_code == 401
    capability = PaperOperatorCapability(
        b"scope-limited-capability-0000000000000000",
        frozenset({PaperOperatorScope.CONTROL_STATUS_READ}),
    )
    config = isolated_client.app.state.operator_control_config
    service = isolated_client.app.state.operator_control_service
    client = TestClient(create_paper_operator_control_app(
        config=config, service=service, authenticator=PaperOperatorAuthenticator((capability,))
    ))
    forbidden = client.post(
        "/control/v1/arm-first-canary", json=arm_body(),
        headers={"Authorization": "Bearer scope-limited-capability-0000000000000000"},
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "CONTROL_FORBIDDEN"


def test_cookie_and_query_credentials_are_not_auth(isolated_client):
    isolated_client.cookies.set("authorization", TOKEN)
    assert isolated_client.get("/control/v1/status").status_code == 401
    isolated_client.cookies.clear()
    response = isolated_client.get(f"/control/v1/status?access_token={TOKEN}", headers=AUTH)
    assert response.status_code == 400
    assert TOKEN not in response.text


def test_browser_origin_is_rejected_without_cors(isolated_client):
    response = isolated_client.get(
        "/control/v1/status", headers={**AUTH, "Origin": "http://127.0.0.1:9999"}
    )
    assert response.status_code == 403
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize("field", [
    "side", "direction", "quantity", "entry_price", "price", "stop", "stop_loss",
    "target", "take_profit", "leverage", "risk_override", "approval_override",
    "final_approval_override",
])
def test_client_trading_decision_fields_get_stable_rejection(isolated_client, field):
    response = isolated_client.post(
        "/control/v1/arm-first-canary", json=arm_body(**{field: "forbidden"}), headers=AUTH
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CLIENT_TRADING_DECISION_NOT_ALLOWED"


@pytest.mark.parametrize("changes,code", [
    ({"mode": "LIVE"}, "LIVE_NOT_ALLOWED"),
    ({"mode": "SIMULATION"}, "INVALID_MODE"),
    ({"max_new_commands": 2}, "INVALID_CANARY_SCOPE"),
    ({"max_open_positions": 2}, "INVALID_CANARY_SCOPE"),
    ({"allowed_symbols": []}, "INVALID_CANARY_SCOPE"),
    ({"allowed_symbols": ["DOGEUSDT"]}, "INVALID_SYMBOL"),
    ({"allowed_symbols": ["BTCUSDT", "BTCUSDT"]}, "INVALID_CANARY_SCOPE"),
])
def test_invalid_scope_and_live_are_denied(isolated_client, changes, code):
    response = isolated_client.post(
        "/control/v1/arm-first-canary", json=arm_body(**changes), headers=AUTH
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == code


def test_malformed_and_oversized_bodies_are_bounded(isolated_client):
    malformed = isolated_client.post(
        "/control/v1/arm-first-canary", content="{", headers={**AUTH, "Content-Type": "application/json"}
    )
    assert malformed.status_code == 400
    oversized = isolated_client.post(
        "/control/v1/arm-first-canary", content=b"x" * 16385, headers=AUTH
    )
    assert oversized.status_code == 413


def test_default_is_disabled_loopback_only_and_docs_off():
    config = PaperOperatorControlConfig()
    app = create_paper_operator_control_app(config=config)
    assert config.enabled is False
    assert config.bind_host == "127.0.0.1"
    assert config.port == 8766
    assert app.docs_url is None and app.openapi_url is None


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "::1", "192.168.1.2", "localhost", "127.0.0.2"])
def test_external_wildcard_and_arbitrary_bind_denied(host):
    with pytest.raises(ValueError, match="CONTROL_EXTERNAL_BIND_DENIED"):
        PaperOperatorControlConfig(bind_host=host)


def test_sources_do_not_log_or_accept_query_credentials():
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (Path(__file__).parents[2] / "app" / "operator_control").glob("*.py")
    )
    assert "logger." not in source
    assert "log(" not in source
    assert "Query(" not in source
    assert ".env.production.local" not in source.replace("``.env.production.local``", "")
    assert "DATABASE_URL" not in source
    assert "TRADERS_ML_POSTGRES_PASSWORD" not in source
