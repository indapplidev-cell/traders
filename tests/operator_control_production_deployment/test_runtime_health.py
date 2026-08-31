from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.operator_control.runtime_health import (
    FILE_NAME,
    PaperRuntimeHealthPublisher,
    read_paper_runtime_health,
)
from scripts import control_api_runtime_probe


class Loop:
    def __init__(self, *, active: bool = True, ticks: int = 1, poll_seconds: float = 10.0):
        self.active = active
        self.ticks = ticks
        self.poll_seconds = poll_seconds


def test_runtime_health_publishes_actual_paper_only_loops(tmp_path: Path) -> None:
    now = datetime(2026, 8, 31, 12, tzinfo=timezone.utc)
    approval = Loop(ticks=4, poll_seconds=30.0)
    execution = Loop(ticks=9, poll_seconds=10.0)
    subject = PaperRuntimeHealthPublisher(
        tmp_path,
        approval_loop=approval,
        lifecycle_loop=execution,
        mutation_enabled=True,
        clock=lambda: now,
    )

    subject.publish()

    value = read_paper_runtime_health(tmp_path, now=now)
    assert value is not None
    assert value["runtime_enabled"] is True
    assert value["daemon_enabled"] is True
    assert value["scheduler_enabled"] is True
    assert value["mutation_enabled"] is True
    assert value["live_allowed"] is False
    assert value["approval_ticks"] == 4
    assert value["execution_ticks"] == 9


def test_runtime_health_stale_invalid_or_live_fails_closed(tmp_path: Path) -> None:
    now = datetime(2026, 8, 31, 12, tzinfo=timezone.utc)
    subject = PaperRuntimeHealthPublisher(
        tmp_path,
        approval_loop=Loop(),
        lifecycle_loop=Loop(),
        mutation_enabled=True,
        clock=lambda: now - timedelta(minutes=1),
    )
    subject.publish()
    assert read_paper_runtime_health(tmp_path, now=now) is None

    path = tmp_path / FILE_NAME
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["generated_at"] = now.isoformat().replace("+00:00", "Z")
    payload["live_allowed"] = True
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert read_paper_runtime_health(tmp_path, now=now) is None


def test_runtime_health_exposes_scheduler_not_ready_when_a_loop_is_down(tmp_path: Path) -> None:
    now = datetime(2026, 8, 31, 12, tzinfo=timezone.utc)
    subject = PaperRuntimeHealthPublisher(
        tmp_path,
        approval_loop=Loop(active=True),
        lifecycle_loop=Loop(active=False),
        mutation_enabled=True,
        clock=lambda: now,
    )
    subject.publish()
    value = read_paper_runtime_health(tmp_path, now=now)
    assert value is not None
    assert value["scheduler_enabled"] is False
    assert value["execution_worker_active"] is False


def test_docker_health_probe_does_not_compose_a_second_database_runtime(monkeypatch) -> None:
    monkeypatch.setattr(
        control_api_runtime_probe,
        "PROTECTED_TOKEN_PATH",
        type("TokenPath", (), {"read_bytes": lambda self: b"safe-test-token-material-0123456789"})(),
    )
    monkeypatch.setattr(
        control_api_runtime_probe,
        "_request",
        lambda *args, **kwargs: (200, {
            "control_state": "ARMED", "generation": 6,
            "control_health": "HEALTHY", "audit_health": "PASS",
            "foundation_mode": "PRODUCTION_PAPER", "service_enabled": True,
            "production_mutation_enabled": True,
        }),
    )
    monkeypatch.setattr(
        control_api_runtime_probe,
        "create_runtime_app",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("full app composition called")),
    )

    value = control_api_runtime_probe.probe(health_only=True)

    assert value["healthy"] is True
    assert value["control_state"] == "ARMED"
    assert value["production_mutation_enabled"] is True
