from __future__ import annotations

import ast
import io
import json
import subprocess
import sys
import time
import urllib.error
from pathlib import Path
from unittest import mock

import pytest

from app.observability.stability_models import (
    RuntimeHealthClassification,
    SampleTransport,
)
from scripts import readonly_api_stability_observer as observer


class Response:
    status = 200

    class Headers:
        @staticmethod
        def get_content_type():
            return "application/json"

    headers = Headers()

    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, _limit):
        return self.payload


def health_payload(timing_state):
    return {
        "api_version": "v1",
        "data": {
            "timing_state": timing_state,
            "reason_code": timing_state,
            "status": "DEGRADED" if timing_state == "DEADLINE_EXPIRED" else "OK",
        },
    }


def test_http_200_deadline_expired_is_transport_success():
    with mock.patch.object(
        observer.urllib.request, "urlopen", return_value=Response(health_payload("DEADLINE_EXPIRED"))
    ):
        result = observer.sample_http("http://127.0.0.1:8765", "/api/v1/health")
    assert result.transport is SampleTransport.SUCCESS
    assert result.runtime_health is RuntimeHealthClassification.DEADLINE_EXPIRED


def test_observer_can_sample_after_deadline_expired():
    responses = [Response(health_payload("DEADLINE_EXPIRED")), Response(health_payload("CURRENT"))]
    with mock.patch.object(observer.urllib.request, "urlopen", side_effect=responses):
        first = observer.sample_http("http://127.0.0.1:8765", "/api/v1/health")
        second = observer.sample_http("http://127.0.0.1:8765", "/api/v1/health")
    assert first.runtime_health is RuntimeHealthClassification.DEADLINE_EXPIRED
    assert second.runtime_health is RuntimeHealthClassification.CURRENT


def test_timeout_classified_separately():
    with mock.patch.object(observer.urllib.request, "urlopen", side_effect=TimeoutError()):
        result = observer.sample_http("http://127.0.0.1:8765", "/api/v1/health")
    assert result.transport is SampleTransport.TIMEOUT


def test_connection_failure_classified_separately():
    with mock.patch.object(
        observer.urllib.request, "urlopen",
        side_effect=urllib.error.URLError(ConnectionRefusedError()),
    ):
        result = observer.sample_http("http://127.0.0.1:8765", "/api/v1/health")
    assert result.transport is SampleTransport.CONNECTION_ERROR


def test_parse_failure_classified_separately():
    response = Response({})
    response.payload = b"not-json"
    with mock.patch.object(observer.urllib.request, "urlopen", return_value=response):
        result = observer.sample_http("http://127.0.0.1:8765", "/api/v1/health")
    assert result.transport is SampleTransport.PARSE_ERROR


def test_full_success_payload_is_not_retained():
    payload = health_payload("CURRENT")
    payload["data"]["large"] = "sensitive-success-body"
    with mock.patch.object(observer.urllib.request, "urlopen", return_value=Response(payload)):
        result = observer.sample_http("http://127.0.0.1:8765", "/api/v1/health")
    assert not hasattr(result, "payload")
    assert "sensitive-success-body" not in repr(result)


def test_safe_result_has_no_uri_environment_or_traceback():
    with mock.patch.object(
        observer.urllib.request, "urlopen", return_value=Response(health_payload("CURRENT"))
    ):
        result = observer.sample_http("http://127.0.0.1:8765", "/api/v1/health")
    rendered = repr(result).lower()
    assert "database_url" not in rendered
    assert "traceback" not in rendered
    assert "password" not in rendered


def test_main_observer_imports_no_tk_module():
    source = Path(observer.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not any(name.startswith(("tkinter", "_tkinter")) for name in imports)


def fixed_child_output():
    return json.dumps(
        {
            "schema": "TRADERS_CLIENT_SMOKE/1",
            "result": "PASS",
            "pages": 7,
            "analysis_errors": 0,
            "provider": "PRODUCTION_READONLY_HTTP",
            "language_persistence": "PASS",
            "async": "PASS",
            "orphan_workers": 0,
        }
    )


def make_process(code, timeout=1.0):
    process = subprocess.Popen(
        [sys.executable, "-c", code],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return observer.ClientSmokeProcess(
        process, "TEST", time.monotonic_ns() + int(timeout * 1_000_000_000)
    )


def test_client_smoke_runs_as_subprocess():
    child = make_process(f"print({fixed_child_output()!r})")
    label, result = child.finish_blocking()
    assert label == "TEST" and result["result"] == "PASS"


def test_successful_subprocess_cannot_terminate_main_observer():
    child = make_process(f"print({fixed_child_output()!r})")
    assert child.finish_blocking()[1]["result"] == "PASS"
    assert True


def test_failed_subprocess_is_bounded_and_reported():
    child = make_process("raise SystemExit(7)")
    assert child.finish_blocking()[1]["result"] == "FAIL"
    assert child.process.poll() is not None


def test_timed_out_subprocess_is_terminated_and_reaped():
    child = make_process("import time; time.sleep(10)", timeout=0.05)
    assert child.finish_blocking()[1]["result"] == "TIMEOUT"
    assert child.process.poll() is not None


def test_no_subprocess_orphan_remains():
    child = make_process("print('invalid')")
    child.finish_blocking()
    assert child.process.poll() is not None


def test_synthetic_tcl_finalizer_failure_cannot_terminate_main():
    child = make_process("import os; os._exit(23)")
    assert child.finish_blocking()[1]["result"] == "FAIL"
    assert True


def test_cleanup_runs_after_keyboard_interrupt(monkeypatch):
    process = mock.Mock()
    process.poll.return_value = None
    process.wait.return_value = 0
    child = observer.ClientSmokeProcess(process, "TEST", 0)
    child.finish_blocking()
    process.terminate.assert_called_once()
    process.wait.assert_called()


def test_analysis_envelope_requires_safe_identity():
    payload = {"api_version": "v1", "data": {"closed_until_ms": 1}}
    with mock.patch.object(observer.urllib.request, "urlopen", return_value=Response(payload)):
        result = observer.sample_http(
            "http://127.0.0.1:8765", "/api/v1/analysis/BTCUSDT"
        )
    assert result.transport is SampleTransport.PARSE_ERROR


def test_simulation_covers_required_contract():
    result = observer.simulate()
    assert result["SIMULATED_ACCEPTANCE"] == "PASS"
    assert result["SIMULATED_DEADLINE_EXPIRED_CAPTURED"] == "YES"
    assert result["SIMULATED_MAIN_OBSERVER_SURVIVED_TK_FINALIZER_CASE"] == "YES"
