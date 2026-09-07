"""Authoritative run-state persistence and stale-heartbeat interpretation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
import json
import os
from pathlib import Path
import threading
from typing import Any


class RunState(StrEnum):
    READY = "READY"
    PREFLIGHT = "PREFLIGHT"
    PLANNING = "PLANNING"
    REPLAY_VALIDATION = "REPLAY_VALIDATION"
    RUNNING_CONFIG = "RUNNING_CONFIG"
    WRITING_RESULT = "WRITING_RESULT"
    FINALIZING = "FINALIZING"
    VERIFYING_ARTIFACTS = "VERIFYING_ARTIFACTS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"
    INTERRUPTED_RESUMABLE = "INTERRUPTED_RESUMABLE"
    RESUMING = "RESUMING"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class SweepRunStatus:
    run_id: str
    state: str = RunState.READY.value
    phase: str = RunState.READY.value
    planned_configs: int = 0
    completed_configs: int = 0
    current_config_index: int | None = None
    current_config: dict[str, Any] | None = None
    accepted_configs: int = 0
    rejected_configs: int = 0
    insufficient_configs: int = 0
    error_configs: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    duration_seconds: float | None = None
    updated_at: str = field(default_factory=utc_now)
    last_checkpoint_at: str | None = None
    pid: int = field(default_factory=os.getpid)
    cancel_requested: bool = False
    resume_available: bool = False
    dataset_fingerprint: str | None = None
    config_hash: str | None = None
    search_space_hash: str | None = None
    engine_version: str | None = None
    failure_reason: str | None = None
    failure_code: str | None = None
    error_title_ru: str | None = None
    error_message_ru: str | None = None
    error_details: dict[str, Any] = field(default_factory=dict)
    search_dimensions: list[str] = field(default_factory=list)
    dimension_values: dict[str, list[Any]] = field(default_factory=dict)
    conditional_dimensions: list[str] = field(default_factory=list)
    replay_diagnostics: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class StatusStore:
    def __init__(self, path: Path, status: SweepRunStatus) -> None:
        self.path = path
        self.status = status
        self._lock = threading.RLock()

    def update(self, *, heartbeat: bool = False, **changes: Any) -> None:
        with self._lock:
            for key, value in changes.items():
                setattr(self.status, key, value)
            self.status.updated_at = utc_now()
            self._write()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return self.status.as_dict()

    def _write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(self.status.as_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(temporary, self.path)


def process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    try:
        os.kill(pid, 0)
    except (OSError, PermissionError):
        return False
    return True


def read_effective_status(path: Path, *, stale_after_seconds: int = 30) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    alive = process_alive(int(value.get("pid", -1)))
    updated = datetime.fromisoformat(str(value["updated_at"]))
    age = (datetime.now(timezone.utc) - updated.astimezone(timezone.utc)).total_seconds()
    value["process_alive"] = alive
    if value.get("state") in {
        RunState.PREFLIGHT.value, RunState.PLANNING.value,
        RunState.REPLAY_VALIDATION.value,
        RunState.RUNNING_CONFIG.value, RunState.WRITING_RESULT.value,
        RunState.FINALIZING.value, RunState.VERIFYING_ARTIFACTS.value,
        RunState.RESUMING.value, RunState.CANCEL_REQUESTED.value,
    } and (not alive or age > stale_after_seconds):
        value["state"] = "INTERRUPTED"
    return value
