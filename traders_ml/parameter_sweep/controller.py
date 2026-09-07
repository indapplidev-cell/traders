"""Thread-safe bridge between the headless engine and presentation clients."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import queue
from pathlib import Path
import threading
from typing import Any

from .engine import ParameterSweepEngine
from .events import EventType, SweepEvent
from .texts import REASONS_RU, STRATEGIES_RU, RU
from .state import read_effective_status
from .utils import generate_run_id, open_directory


@dataclass(slots=True)
class PresentationState:
    status_text: str = RU["ready"]
    run_id: str = "—"
    output_directory: str = "—"
    phase: str = "READY"
    raw_space: int = 0
    planned: int = 0
    completed: int = 0
    accepted: int = 0
    rejected: int = 0
    insufficient: int = 0
    errors: int = 0
    current_index: int = 0
    strategy: str = "—"
    changed_parameters: dict[str, Any] = field(default_factory=dict)
    resolved_config: dict[str, Any] = field(default_factory=dict)
    current_result: dict[str, Any] = field(default_factory=dict)
    started_at: str | None = None
    finished_at: str | None = None
    duration_seconds: float | None = None
    eta_seconds: float | None = None
    integrity_status: str = "—"
    integrity_files: list[str] = field(default_factory=list)
    resume_available: bool = False
    active: bool = False
    error_reason: str | None = None

    @property
    def progress_percent(self) -> float:
        return 100.0 * self.completed / self.planned if self.planned else 0.0


class ParameterSweepController:
    def __init__(self, config_path: Path, output_root: Path) -> None:
        self.config_path = config_path
        self.output_root = output_root
        self.events: queue.Queue[SweepEvent] = queue.Queue()
        self.state = PresentationState()
        self.engine = ParameterSweepEngine(self.events.put)
        self.worker: threading.Thread | None = None
        self._close_after_stop = False
        self._discover_incomplete_run()

    def _discover_incomplete_run(self) -> None:
        if not self.output_root.is_dir():
            return
        candidates = sorted(self.output_root.glob("*/STATUS.json"), reverse=True)
        for path in candidates:
            try:
                value = read_effective_status(path)
            except (OSError, ValueError, KeyError):
                continue
            if value.get("state") in {"INTERRUPTED", "CANCELLED", "INTERRUPTED_RESUMABLE"} and value.get("resume_available"):
                self.state.run_id = str(value["run_id"])
                self.state.output_directory = str(path.parent)
                self.state.completed = int(value.get("completed_configs", 0))
                self.state.planned = int(value.get("planned_configs", 0))
                self.state.resume_available = True
                self.state.status_text = (
                    f"Найден незавершённый запуск: {self.state.run_id}\n"
                    f"Выполнено: {self.state.completed} из {self.state.planned}"
                )
                return

    def start_new_run(self, *, max_configs: int | None = None) -> str:
        if self.worker and self.worker.is_alive():
            raise RuntimeError("PARAMETER_SWEEP_ALREADY_RUNNING")
        run_id = generate_run_id(self.output_root)
        self._start(run_id, resume=False, max_configs=max_configs)
        return run_id

    def resume_run(self, run_id: str) -> None:
        if self.worker and self.worker.is_alive():
            raise RuntimeError("PARAMETER_SWEEP_ALREADY_RUNNING")
        self._start(run_id, resume=True, max_configs=None)

    def _start(self, run_id: str, *, resume: bool, max_configs: int | None) -> None:
        self.engine = ParameterSweepEngine(self.events.put)
        self.state = PresentationState(
            status_text=RU["preparing"], run_id=run_id,
            output_directory=str(self.output_root / run_id), active=True,
        )

        def target() -> None:
            try:
                self.engine.run(
                    self.config_path, run_id=run_id, resume=resume,
                    max_configs=max_configs,
                )
            except BaseException as error:
                if not any(event.type == EventType.RUN_FAILED for event in list(self.events.queue)):
                    self.events.put(SweepEvent.create(
                        EventType.RUN_FAILED, run_id,
                        reason=getattr(error, "reason", type(error).__name__),
                        resume_available=(self.output_root / run_id / "CHECKPOINT.json").is_file(),
                    ))

        self.worker = threading.Thread(target=target, name=f"sweep-{run_id}", daemon=False)
        self.worker.start()

    def request_stop_after_current(self) -> None:
        self.engine.request_stop_after_current()
        self.state.status_text = RU["cancel_requested"]
        self.state.phase = "CANCEL_REQUESTED"

    def open_reports_directory(self) -> None:
        open_directory(Path(self.state.output_directory))

    def close_ui(self) -> bool:
        if self.state.active:
            self._close_after_stop = True
            self.request_stop_after_current()
            return False
        return True

    def drain_events(self) -> list[SweepEvent]:
        drained: list[SweepEvent] = []
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            drained.append(event)
            self._apply(event)
        return drained

    def _apply(self, event: SweepEvent) -> None:
        payload = event.payload
        self.state.phase = event.type.value
        if event.type in {EventType.RUN_STARTED, EventType.RUN_RESUMED}:
            self.state.started_at = event.occurred_at
            self.state.status_text = RU["preparing"]
        elif event.type == EventType.PREFLIGHT_STARTED:
            self.state.status_text = RU["preflight"]
        elif event.type == EventType.SEARCH_PLANNING_STARTED:
            self.state.status_text = RU["planning"]
        elif event.type == EventType.SEARCH_PLANNED:
            self.state.raw_space = int(payload["raw_space"])
            self.state.planned = int(payload["planned"])
            self.state.strategy = STRATEGIES_RU.get(str(payload["strategy"]), str(payload["strategy"]))
        elif event.type == EventType.CONFIG_STARTED:
            self.state.status_text = RU["running"]
            self.state.current_index = int(payload["index"])
            self.state.changed_parameters = dict(payload["changed_parameters"])
            self.state.resolved_config = dict(payload["resolved_config"])
        elif event.type == EventType.CONFIG_PROGRESS:
            self.state.completed = int(payload.get("completed", self.state.completed))
            self.state.planned = int(payload.get("planned", self.state.planned))
            self.state.accepted = int(payload.get("accepted", self.state.accepted))
            self.state.rejected = int(payload.get("rejected", self.state.rejected))
            self.state.errors = int(payload.get("errors", self.state.errors))
        elif event.type == EventType.CONFIG_COMPLETED:
            self.state.current_result = dict(payload["result"])
        elif event.type == EventType.RESULT_WRITE_STARTED:
            self.state.status_text = RU["writing"]
        elif event.type == EventType.RESULT_WRITE_COMPLETED:
            self.state.status_text = RU["saved"].format(index=payload["index"])
        elif event.type == EventType.CHECKPOINT_WRITTEN:
            self.state.completed = int(payload["completed"])
            self.state.accepted = int(payload["accepted"])
            self.state.rejected = int(payload["rejected"])
            self.state.insufficient = int(payload["insufficient"])
            self.state.errors = int(payload["errors"])
            if self.state.completed >= 3 and self.state.started_at:
                elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(self.state.started_at)).total_seconds()
                self.state.eta_seconds = elapsed / self.state.completed * max(0, self.state.planned - self.state.completed)
        elif event.type == EventType.RUN_FINALIZING:
            self.state.status_text = RU["finalizing"]
        elif event.type == EventType.INTEGRITY_CHECK_STARTED:
            self.state.status_text = RU["integrity"]
        elif event.type == EventType.INTEGRITY_FILE_CHECKED:
            mark = "✓" if payload["passed"] else "✗"
            self.state.integrity_files.append(f"{mark} {payload['file']}")
        elif event.type == EventType.INTEGRITY_CHECK_COMPLETED:
            self.state.integrity_status = str(payload["status"])
        elif event.type == EventType.RUN_COMPLETED:
            self.state.status_text = RU["completed"].format(count=payload["completed"])
            self.state.duration_seconds = float(payload["duration_seconds"])
            self.state.finished_at = event.occurred_at
            self.state.active = False
        elif event.type == EventType.RUN_CANCELLED:
            self.state.status_text = RU["cancelled"]
            self.state.resume_available = True
            self.state.active = False
        elif event.type == EventType.RUN_FAILED:
            reason = str(payload.get("reason", "UNKNOWN"))
            self.state.error_reason = REASONS_RU.get(reason, reason)
            self.state.status_text = f"{RU['failed']}\nПричина: {self.state.error_reason}"
            self.state.resume_available = bool(payload.get("resume_available"))
            self.state.errors += 1
            self.state.active = False
