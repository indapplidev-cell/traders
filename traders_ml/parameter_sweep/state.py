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

from .artifact_writer import ArtifactWriteError, ArtifactWriter, DEFAULT_ARTIFACT_WRITER


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
    symbol: str | None = None
    research_mode: str | None = None
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
    dataset_manifest_hash: str | None = None
    dataset_cutoff_at: str | None = None
    dataset_period_start_ms: int | None = None
    dataset_period_end_ms: int | None = None
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
    current_stage: str | None = None
    current_parameter_family: str | None = None
    artifact_bytes: int = 0
    artifact_soft_budget_bytes: int = 0
    artifact_hard_budget_bytes: int = 0
    negative_expectancy_configs: int = 0
    promising_configs: int = 0
    validation_candidate_configs: int = 0
    classification_counts: dict[str, int] = field(default_factory=dict)
    evaluation_status_counts: dict[str, int] = field(default_factory=dict)
    performance_class_counts: dict[str, int] = field(default_factory=dict)
    validation_readiness: dict[str, dict[str, Any]] = field(default_factory=dict)
    resolved_seed: int | None = None
    research_phase: str = "CALIBRATION_SEARCH"
    holdout_status: str = "UNTOUCHED"
    finalists_frozen: bool = False
    finalist_count: int = 0
    holdout_opened: bool = False
    holdout_evaluated: bool = False
    freeze_hash: str | None = None

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["SYMBOL"] = self.symbol
        return value


class StatusStore:
    def __init__(
        self, path: Path, status: SweepRunStatus, *, writer: ArtifactWriter | None = None,
    ) -> None:
        self.path = path
        self.status = status
        self._lock = threading.RLock()
        self.writer = writer or DEFAULT_ARTIFACT_WRITER
        self.last_write_warning: dict[str, Any] | None = None

    def update(self, *, heartbeat: bool = False, **changes: Any) -> None:
        with self._lock:
            for key, value in changes.items():
                setattr(self.status, key, value)
            self.status.updated_at = utc_now()
            try:
                self._write()
                self.last_write_warning = None
            except ArtifactWriteError as error:
                # STATUS is observational. A missed heartbeat must never abort research.
                self.last_write_warning = error.as_dict()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return self.status.as_dict()

    def _write(self) -> None:
        self.writer.atomic_json(
            self.path, self.status.as_dict(), operation="status_replace",
        )


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
