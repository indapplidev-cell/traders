from __future__ import annotations

import hashlib
import importlib
import json
import re
import socket
import sys
import threading
from pathlib import Path

import sqlalchemy

from app.server_api import create_app
from app.server_api.repositories import SemanticIncidentReadAdapter, SqlAlchemyReadAdapter
from app.server_api.repositories.protocols import ApiRepositories
from tests.server_api.fakes import FakeReadRepository, NOW
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "docs" / "api" / "contracts" / "client-openapi-v1.json"
SOURCE_SHA256 = "683f5460131e683e89c9ce82be9f05c716f2bbae4e01e07e54db58ea381a7cd4"
REQUIRED_PATHS = {
    "/api/v1/health",
    "/api/v1/dashboard",
    "/api/v1/markets",
    "/api/v1/markets/{symbol}",
    "/api/v1/analysis/{symbol}",
    "/api/v1/setups",
    "/api/v1/setups/{setup_id}",
    "/api/v1/incidents",
    "/api/v1/incidents/{incident_id}",
}
UNIVERSE_PATHS = {"/api/v1/trading-universe"}
ANALYSIS_AGGREGATE_PATHS = {"/api/v1/analysis"}
PAPER_PATHS = {
    "/api/v1/paper/readiness",
    "/api/v1/paper/account",
    "/api/v1/paper/positions",
    "/api/v1/paper/positions/{position_id}",
    "/api/v1/paper/trades",
    "/api/v1/paper/trades/{position_id}/report",
    "/api/v1/paper/reconciliation",
    "/api/v1/paper/runtime/status",
    "/api/v1/paper/control/status",
    "/api/v1/paper/trading-criteria",
    "/api/v1/paper/orders",
    "/api/v1/paper/fills",
    "/api/v1/paper/journal",
}


def _resolve(document: dict, schema: dict) -> dict:
    if "$ref" not in schema:
        return schema
    value = document
    for part in schema["$ref"].removeprefix("#/").split("/"):
        value = value[part]
    return value


def _validate(document: dict, schema: dict, value, path: str = "$") -> None:
    schema = _resolve(document, schema)
    if "anyOf" in schema:
        errors = []
        for candidate in schema["anyOf"]:
            try:
                _validate(document, candidate, value, path)
                return
            except AssertionError as exc:
                errors.append(str(exc))
        raise AssertionError(f"{path}: no anyOf branch matched: {errors}")
    if "const" in schema:
        assert value == schema["const"], f"{path}: expected const {schema['const']!r}"
    if "enum" in schema:
        assert value in schema["enum"], f"{path}: enum mismatch"
    types = schema.get("type")
    if isinstance(types, str):
        types = [types]
    if types:
        checks = {
            "null": value is None,
            "object": isinstance(value, dict),
            "array": isinstance(value, list),
            "string": isinstance(value, str),
            "integer": isinstance(value, int) and not isinstance(value, bool),
            "number": isinstance(value, (int, float)) and not isinstance(value, bool),
            "boolean": isinstance(value, bool),
        }
        assert any(checks[item] for item in types), f"{path}: type mismatch for {types}"
    if isinstance(value, dict):
        for required in schema.get("required", []):
            assert required in value, f"{path}: missing {required}"
        for name, item in value.items():
            if name in schema.get("properties", {}):
                _validate(document, schema["properties"][name], item, f"{path}.{name}")
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            _validate(document, schema["items"], item, f"{path}[{index}]")
    if isinstance(value, str) and "pattern" in schema:
        assert re.search(schema["pattern"], value), f"{path}: pattern mismatch"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema:
            assert value >= schema["minimum"], f"{path}: below minimum"
        if "maximum" in schema:
            assert value <= schema["maximum"], f"{path}: above maximum"


def test_accepted_json_loads_and_snapshot_sha_matches_provenance():
    data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert data["info"]["version"] == "v1"
    assert hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest() == SOURCE_SHA256
    provenance = (SNAPSHOT.parent / "CLIENT_OPENAPI_V1_PROVENANCE.md").read_text(encoding="utf-8")
    assert f"SOURCE_SHA256 = {SOURCE_SHA256}" in provenance
    assert "SNAPSHOT_MATCH = BYTE_FOR_BYTE" in provenance


def test_required_paths_and_get_only_surface():
    accepted = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert set(accepted["paths"]) == REQUIRED_PATHS
    for operations in accepted["paths"].values():
        assert {key for key in operations if key in {"get", "post", "put", "patch", "delete"}} == {"get"}


def test_framework_openapi_has_exact_business_paths_and_no_mutations():
    generated = create_app().openapi()
    assert set(generated["paths"]) == REQUIRED_PATHS | PAPER_PATHS | UNIVERSE_PATHS | ANALYSIS_AGGREGATE_PATHS | {"/api/v1/trading/funnel", "/api/v1/i18n/manifest", "/api/v1/i18n/catalog/{locale}"}
    for operations in generated["paths"].values():
        assert {key for key in operations if key in {"get", "post", "put", "patch", "delete"}} == {"get"}
    assert "/openapi.json" not in generated["paths"]
    assert "/docs" not in generated["paths"]


def test_framework_operation_ids_match_accepted_contract():
    accepted = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    generated = create_app().openapi()
    for path in REQUIRED_PATHS:
        assert generated["paths"][path]["get"]["operationId"] == accepted["paths"][path]["get"]["operationId"]


def test_all_success_payloads_validate_against_accepted_response_schemas():
    accepted = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    fake = FakeReadRepository()
    client = TestClient(create_app(repositories=fake.api_repositories(), clock=lambda: NOW))
    requests = {
        "/api/v1/health": "/api/v1/health",
        "/api/v1/dashboard": "/api/v1/dashboard",
        "/api/v1/markets": "/api/v1/markets",
        "/api/v1/markets/{symbol}": "/api/v1/markets/BTCUSDT",
        "/api/v1/analysis/{symbol}": "/api/v1/analysis/BTCUSDT",
        "/api/v1/setups": "/api/v1/setups",
        "/api/v1/setups/{setup_id}": "/api/v1/setups/setup:BTCUSDT:15m:0",
        "/api/v1/incidents": "/api/v1/incidents",
        "/api/v1/incidents/{incident_id}": "/api/v1/incidents/incident:001",
    }
    for contract_path, request_path in requests.items():
        response = client.get(request_path)
        assert response.status_code == 200, contract_path
        schema = accepted["paths"][contract_path]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
        _validate(accepted, schema, response.json())


def test_error_payload_validates_against_accepted_error_schema():
    accepted = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    fake = FakeReadRepository()
    client = TestClient(create_app(repositories=fake.api_repositories(), clock=lambda: NOW))
    payload = client.get("/api/v1/markets/SOLUSDT").json()
    _validate(accepted, {"$ref": "#/components/schemas/ErrorEnvelope"}, payload)


def test_app_import_and_factory_have_no_socket_db_or_thread_side_effects(monkeypatch):
    counters = {"bind": 0, "connect": 0, "db": 0, "thread": 0}

    def forbidden(name):
        def call(*args, **kwargs):
            counters[name] += 1
            raise AssertionError(f"forbidden side effect: {name}")
        return call

    monkeypatch.setattr(socket.socket, "bind", forbidden("bind"))
    monkeypatch.setattr(socket.socket, "connect", forbidden("connect"))
    monkeypatch.setattr(sqlalchemy.engine.Engine, "connect", forbidden("db"))
    monkeypatch.setattr(threading.Thread, "start", forbidden("thread"))
    for name in list(sys.modules):
        if name == "app.server_api" or name.startswith("app.server_api."):
            del sys.modules[name]
    module = importlib.import_module("app.server_api")
    app = module.create_app()
    assert sum("get" in value for value in app.openapi()["paths"].values()) == 27
    assert counters == {"bind": 0, "connect": 0, "db": 0, "thread": 0}


def test_production_adapters_are_inert_until_read_method_call():
    calls = []

    def session_factory():
        calls.append("session")
        raise AssertionError("must not be called by construction")

    SqlAlchemyReadAdapter(session_factory)
    SemanticIncidentReadAdapter(lambda: calls.append("loader"))
    assert calls == []


def test_app_factory_uses_only_explicit_repositories():
    fake = FakeReadRepository()
    repositories = fake.api_repositories()
    assert isinstance(repositories, ApiRepositories)
    app = create_app(repositories=repositories, clock=lambda: NOW)
    assert sum("get" in value for value in app.openapi()["paths"].values()) == 27
    assert fake.calls == []


def test_runtime_api_code_has_no_forbidden_control_or_write_calls():
    runtime = ROOT / "app" / "server_api"
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in runtime.rglob("*.py")
    ).lower()
    forbidden = (
        "socket.bind(",
        "socket.listen(",
        "uvicorn.run(",
        "subprocess.",
        "docker sdk",
        "binance",
        "alembic.command",
        "session.commit(",
        "session.flush(",
        "session.add(",
        "session.delete(",
        "insert(",
        "truncate ",
        "drop table",
    )
    assert [token for token in forbidden if token in source] == []


def test_no_production_configuration_or_credentials_are_discovered():
    runtime = ROOT / "app" / "server_api"
    source = "\n".join(path.read_text(encoding="utf-8") for path in runtime.rglob("*.py")).lower()
    forbidden = ("dotenv", "database_url", "dsn =", "api_key", "secret_key", "os.environ", "getenv(")
    assert [token for token in forbidden if token in source] == []
