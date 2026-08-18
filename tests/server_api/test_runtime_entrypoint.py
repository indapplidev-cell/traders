from __future__ import annotations

import importlib
import os
import subprocess
import sys
from contextlib import AbstractContextManager
from types import SimpleNamespace

import pytest
from fastapi.routing import APIRoute
from starlette.testclient import TestClient
from uvicorn.importer import import_from_string

from app.server_api import runtime
from app.server_api.repositories.sqlalchemy_read import SqlAlchemyReadAdapter
from app.server_api.runtime_config import RuntimeConfig
from app.server_api.schema_compatibility import (
    BASE_READONLY_CAPABILITIES,
    ReadonlySchemaCapabilityResult,
)


_RUNTIME_PASSWORD = os.urandom(12).hex()
CONFIG = RuntimeConfig.from_mapping(
    {
        "TRADERS_READONLY_API_DATABASE_URL": (
            "postgresql+psycopg"
            + ":"
            + "//readonly:"
            + _RUNTIME_PASSWORD
            + "@db.invalid/runtime"
        ),
        "TRADERS_READONLY_API_HOST": "127.0.0.9",
        "TRADERS_READONLY_API_PORT": "8123",
        "TRADERS_READONLY_API_LOG_LEVEL": "debug",
    }
)


class FakeConnection(AbstractContextManager):
    def __init__(self, mode: str = "on") -> None:
        self.mode = mode

    def exec_driver_sql(self, statement: str):
        assert statement == "SHOW transaction_read_only"
        return SimpleNamespace(scalar_one=lambda: self.mode)

    def __exit__(self, *args):
        return None


class FakeEngine:
    def __init__(self, mode: str = "on") -> None:
        self.disposed = 0
        self.connections = 0
        self.mode = mode

    def connect(self) -> FakeConnection:
        self.connections += 1
        return FakeConnection(self.mode)

    def dispose(self) -> None:
        self.disposed += 1


def _composed(monkeypatch, *, mode: str = "on"):
    engine = FakeEngine(mode)
    monkeypatch.setattr(
        runtime.RuntimeConfig, "from_environment", classmethod(lambda cls: CONFIG)
    )
    monkeypatch.setattr(runtime, "_create_engine", lambda config: engine)
    monkeypatch.setattr(
        runtime,
        "inspect_readonly_schema_capabilities",
        lambda connection: ReadonlySchemaCapabilityResult(
            True,
            "0016_control_mobile_device_security",
            BASE_READONLY_CAPABILITIES,
        ),
    )
    app = runtime.create_runtime_app()
    return app, engine


def test_module_import_does_not_connect(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        "sqlalchemy.engine.Engine.connect",
        lambda *args, **kwargs: calls.append("connect"),
    )
    sys.modules.pop("app.server_api.runtime", None)
    importlib.import_module("app.server_api.runtime")
    assert calls == []


def test_composition_injects_one_exact_read_adapter(monkeypatch) -> None:
    app, engine = _composed(monkeypatch)
    repositories = app.state.runtime_repositories
    adapters = {
        id(repositories.health),
        id(repositories.markets),
        id(repositories.analysis),
        id(repositories.setups),
        id(repositories.incidents),
        id(repositories.dashboard),
    }
    assert len(adapters) == 1
    assert isinstance(repositories.health, SqlAlchemyReadAdapter)
    assert not any(
        hasattr(repositories.health, name)
        for name in ("add", "delete", "flush", "commit")
    )
    assert engine.connections == 0


def test_startup_validates_readonly_and_shutdown_disposes(monkeypatch) -> None:
    app, engine = _composed(monkeypatch)
    with TestClient(app):
        assert engine.connections == 1
        assert engine.disposed == 0
    assert engine.disposed == 1


def test_failed_startup_also_disposes_engine(monkeypatch) -> None:
    app, engine = _composed(monkeypatch, mode="off")
    with pytest.raises(RuntimeError, match="read-only boundary"):
        with TestClient(app):
            pass
    assert engine.connections == 1
    assert engine.disposed == 1


def test_asgi_factory_reference_resolves_to_canonical_factory() -> None:
    resolved = import_from_string(runtime.FACTORY_REFERENCE)
    assert resolved.__module__ == "app.server_api.runtime"
    assert resolved.__name__ == "create_runtime_app"


def test_factory_exposes_twenty_seven_get_only_source_routes(monkeypatch) -> None:
    app, _ = _composed(monkeypatch)
    operations = [
        method for route in app.openapi()["paths"].values()
        for method in route if method in {"get", "post", "put", "patch", "delete"}
    ]
    assert operations == ["get"] * 27


def test_main_passes_canonical_factory_and_server_settings(monkeypatch) -> None:
    captured = {}
    monkeypatch.setattr(
        runtime.RuntimeConfig, "from_environment", classmethod(lambda cls: CONFIG)
    )
    monkeypatch.setattr(runtime, "run_server", lambda *args, **kwargs: captured.update(
        {"args": args, **kwargs}
    ))
    assert runtime.main([]) == 0
    assert captured == {
        "args": (runtime.FACTORY_REFERENCE,),
        "factory": True,
        "host": "127.0.0.9",
        "port": 8123,
        "log_level": "debug",
        "access_log": True,
        "reload": False,
        "workers": 1,
    }


def test_module_entrypoint_and_help_resolve_without_configuration() -> None:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("TRADERS_READONLY_API_")
    }
    completed = subprocess.run(
        [sys.executable, "-m", "app.server_api.runtime", "--help"],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert completed.returncode == 0
    assert "Traders read-only API" in completed.stdout
