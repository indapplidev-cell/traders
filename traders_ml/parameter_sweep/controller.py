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
from .texts import PARAMETER_LABELS_RU, REASONS_RU, STRATEGIES_RU, RU
from .state import read_effective_status
from .utils import generate_run_id, open_directory
from .modes import ResearchMode, parse_research_mode


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
    current_index: int | None = None
    strategy: str = "—"
    search_dimensions: list[str] = field(default_factory=list)
    dimension_values: dict[str, list[Any]] = field(default_factory=dict)
    conditional_dimensions: list[str] = field(default_factory=list)
    current_config: dict[str, Any] | None = None
    changed_parameters: dict[str, Any] | None = None
    resolved_config: dict[str, Any] | None = None
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
    error_code: str | None = None
    error_title_ru: str | None = None
    error_message_ru: str | None = None
    error_details: dict[str, Any] = field(default_factory=dict)
    replay_diagnostics: dict[str, int] = field(default_factory=dict)
    failed_before_first_config: bool = False
    terminal_state: str | None = None
    current_stage: str = "—"
    current_parameter_family: str = "—"
    artifact_bytes: int = 0
    artifact_soft_budget_bytes: int = 0
    artifact_hard_budget_bytes: int = 0
    negative_expectancy: int = 0
    promising: int = 0
    validation_candidates: int = 0
    research_mode: str = ResearchMode.ALL.value

    @property
    def progress_percent(self) -> float:
        return 100.0 * self.completed / self.planned if self.planned else 0.0

    def format_search_parameters(self) -> str:
        if not self.search_dimensions:
            return "План исследования ещё не построен"
        rows = []
        for name in self.search_dimensions:
            label = PARAMETER_LABELS_RU.get(name, name)
            values = ", ".join("—" if value is None else str(value) for value in self.dimension_values[name])
            conditional = " · условное" if name in self.conditional_dimensions else ""
            rows.append(f"{label} ({name}){conditional}:\n  {values}")
        return "\n".join(rows)

    def format_current_parameters(self, *, show_all: bool = False) -> str:
        if self.current_config is None:
            return RU["not_started"]
        values = self.resolved_config if show_all else self.changed_parameters
        heading = "Все параметры" if show_all else "Изменяемые параметры"
        rows = [heading]
        for name, value in sorted((values or {}).items()):
            rows.append(f"{name} = {'—' if value is None else value}")
        return "\n".join(rows)


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
                try:
                    mode = parse_research_mode(value.get("research_mode"))
                except ValueError:
                    continue
                self.state.run_id = str(value["run_id"])
                self.state.research_mode = mode.value
                self.state.output_directory = str(path.parent)
                self.state.completed = int(value.get("completed_configs", 0))
                self.state.planned = int(value.get("planned_configs", 0))
                current = value.get("current_config")
                self.state.current_config = dict(current) if isinstance(current, dict) else None
                self.state.resolved_config = self.state.current_config
                self.state.current_index = value.get("current_config_index")
                self.state.resume_available = True
                self.state.terminal_state = "INTERRUPTED"
                self.state.status_text = (
                    f"Найден незавершённый запуск: {self.state.run_id}\n"
                    f"Выполнено: {self.state.completed} из {self.state.planned}"
                )
                return

    def start_new_run(
        self, *, max_configs: int | None = None,
        mode: ResearchMode | str = ResearchMode.ALL,
    ) -> str:
        if self.worker and self.worker.is_alive():
            raise RuntimeError("PARAMETER_SWEEP_ALREADY_RUNNING")
        canonical_mode = parse_research_mode(mode)
        run_id = generate_run_id(self.output_root)
        self._start(run_id, resume=False, max_configs=max_configs, mode=canonical_mode)
        return run_id

    def resume_run(self, run_id: str) -> None:
        if self.worker and self.worker.is_alive():
            raise RuntimeError("PARAMETER_SWEEP_ALREADY_RUNNING")
        self._start(
            run_id, resume=True, max_configs=None,
            mode=parse_research_mode(self.state.research_mode),
        )

    def _start(
        self, run_id: str, *, resume: bool, max_configs: int | None,
        mode: ResearchMode,
    ) -> None:
        failure_emitted = threading.Event()

        def receive(event: SweepEvent) -> None:
            if event.type == EventType.RUN_FAILED:
                failure_emitted.set()
            self.events.put(event)

        self.engine = ParameterSweepEngine(receive)
        self.state = PresentationState(
            status_text=RU["preparing"], run_id=run_id,
            output_directory=str(self.output_root / run_id), active=True,
            research_mode=mode.value,
        )

        def target() -> None:
            try:
                self.engine.run(
                    self.config_path, run_id=run_id, resume=resume,
                    max_configs=max_configs,
                    mode=mode,
                )
            except BaseException as error:
                if not failure_emitted.is_set():
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
            self.state.run_id = event.run_id
            self.state.research_mode = str(payload["research_mode"])
            self.state.output_directory = str(payload.get("output_dir", self.state.output_directory))
            self.state.active = True
            self.state.started_at = event.occurred_at
            self.state.status_text = RU["preparing"]
        elif event.type == EventType.PREFLIGHT_STARTED:
            self.state.status_text = RU["preflight"]
        elif event.type == EventType.SEARCH_PLANNING_STARTED:
            self.state.status_text = RU["planning"]
        elif event.type == EventType.SEARCH_PLANNED:
            self.state.raw_space = int(payload.get("raw_search_space_size", payload.get("raw_space", 0)))
            self.state.planned = int(payload.get("planned_configs", payload.get("planned", 0)))
            strategy = str(payload.get("selected_strategy", payload.get("strategy", "—")))
            self.state.strategy = STRATEGIES_RU.get(strategy, strategy)
            self.state.search_dimensions = list(payload.get("search_dimensions", ()))
            self.state.dimension_values = {
                str(name): list(values)
                for name, values in payload.get("dimension_values", {}).items()
            }
            self.state.conditional_dimensions = list(payload.get("conditional_dimensions", ()))
            self.state.replay_diagnostics = dict(payload.get("replay_diagnostics", {}))
        elif event.type == EventType.REPLAY_VALIDATION_STARTED:
            self.state.status_text = "Статус: Проверка возможности replay"
            self.state.replay_diagnostics = dict(payload.get("replay_diagnostics", {}))
        elif event.type == EventType.CONFIG_STARTED:
            self.state.active = True
            self.state.terminal_state = None
            self.state.status_text = RU["running"]
            self.state.current_index = int(payload["index"])
            self.state.current_config = dict(payload["resolved_config"])
            self.state.changed_parameters = dict(payload["changed_parameters"])
            self.state.resolved_config = dict(payload["resolved_config"])
            self.state.current_stage = str(payload.get("stage", "—"))
            self.state.current_parameter_family = str(payload.get("parameter_family", "—"))
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
            self.state.artifact_bytes = int(payload.get("artifact_bytes", self.state.artifact_bytes))
            self.state.artifact_soft_budget_bytes = int(payload.get("artifact_soft_budget_bytes", self.state.artifact_soft_budget_bytes))
            self.state.artifact_hard_budget_bytes = int(payload.get("artifact_hard_budget_bytes", self.state.artifact_hard_budget_bytes))
            self.state.negative_expectancy = int(payload.get("negative_expectancy", self.state.negative_expectancy))
            self.state.promising = int(payload.get("promising", self.state.promising))
            self.state.validation_candidates = int(payload.get("validation_candidates", self.state.validation_candidates))
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
            self.state.terminal_state = "COMPLETED"
        elif event.type == EventType.RUN_CANCELLED:
            self.state.status_text = RU["cancelled"]
            self.state.resume_available = True
            self.state.active = False
            self.state.terminal_state = "CANCELLED"
        elif event.type == EventType.RUN_FAILED:
            reason = str(payload.get("reason", "UNKNOWN"))
            self.state.error_reason = REASONS_RU.get(reason, reason)
            self.state.error_code = str(payload.get("error_code", reason))
            self.state.error_title_ru = str(payload.get("error_title_ru", self.state.error_reason))
            self.state.error_message_ru = str(payload.get("error_message_ru", self.state.error_reason))
            self.state.error_details = dict(payload.get("error_details", {}))
            self.state.replay_diagnostics = dict(payload.get("replay_diagnostics", self.state.replay_diagnostics))
            self.state.failed_before_first_config = bool(payload.get("failed_before_first_config"))
            if self.state.failed_before_first_config:
                self.state.current_index = None
                self.state.current_config = None
                self.state.changed_parameters = None
                self.state.resolved_config = None
                self.state.completed = 0
                self.state.planned = int(payload.get("planned", self.state.planned))
            self.state.status_text = (
                f"{RU['failed']}\n{self.state.error_title_ru}\n"
                f"{self.state.error_message_ru}"
            )
            self.state.resume_available = bool(payload.get("resume_available"))
            self.state.errors = max(1, self.state.errors)
            self.state.active = False
            self.state.terminal_state = "FAILED"
            if self.state.failed_before_first_config:
                self.state.phase = "REPLAY_VALIDATION"
