from __future__ import annotations

import importlib
from pathlib import Path


REQUIRED_EXPORTS = {
    "ExecutionIntent", "ExecutionAcknowledgement", "ExecutionMode", "ExecutionSide",
    "ExecutionOrderType", "ExecutionIntentStatus", "ExecutionAcknowledgementStatus",
    "ExecutionIntentBuilder", "ExecutionGateway", "DryRunExecutionGateway",
    "PaperExecutionGateway", "DisabledLiveExecutionGateway", "InMemoryIdempotencyRegistry",
}


def test_package_import_and_public_exports_are_valid(monkeypatch):
    import socket

    monkeypatch.setattr(socket.socket, "connect", lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("package import attempted a connection")))
    package = importlib.import_module("app.engine_execution")
    package = importlib.reload(package)
    assert REQUIRED_EXPORTS <= set(package.__all__)
    assert all(hasattr(package, name) for name in package.__all__)


def test_package_import_has_no_heavy_runtime_side_effects():
    package = importlib.import_module("app.engine_execution")
    assert not hasattr(package, "session")
    assert not hasattr(package, "client")
    assert not hasattr(package, "daemon")


def test_correct_dunder_init_exists_and_stray_names_are_absent():
    directory = Path(__file__).resolve().parents[2] / "app" / "engine_execution"
    assert (directory / "__init__.py").is_file()
    assert not (directory / "init.py").exists()
    assert not (directory / "__init.py").exists()
    assert not (directory / "_init_.py").exists()
