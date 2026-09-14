"""Thread-safe bridge between the headless engine and presentation clients."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import queue
from pathlib import Path
import threading
from typing import Any, Mapping

from .engine import ParameterSweepEngine
from .events import EventType, SweepEvent
from .texts import PARAMETER_LABELS_RU, REASONS_RU, STRATEGIES_RU, RU
from .state import read_effective_status
from .utils import generate_run_id, open_directory
from .modes import ResearchMode, parse_research_mode
from .universe import resolve_parameter_sweep_universe, validate_parameter_sweep_symbol
from .pipeline import PIPELINE_NAME, SingleSymbolResearchPipeline


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
    validation_ranking_eligible_numeric: int = 0
    validation_ranking_eligible_behavioral: int = 0
    validation_ranking_descriptive_behavioral: int = 0
    validation_ranking_top_eligible: str | None = None
    validation_ranking_top_descriptive: str | None = None
    evaluation_status_counts: dict[str, int] = field(default_factory=dict)
    performance_class_counts: dict[str, int] = field(default_factory=dict)
    resolved_seed: int | None = None
    research_mode: str = ResearchMode.ALL.value
    symbol: str | None = None
    research_phase: str = "CALIBRATION_SEARCH"
    holdout_status: str = "UNTOUCHED"
    finalists_frozen: bool = False
    finalist_count: int = 0
    holdout_opened: bool = False
    holdout_evaluated: bool = False
    canonical_validation: dict[str, Any] = field(default_factory=dict)
    validation_minimum_trades: int | None = None
    minimum_independent_periods: int | None = None
    independent_period_unit: str | None = None
    history_target_days: int = 30
    history_start: str | None = None
    history_end: str | None = None
    history_actual_days: float | None = None
    history_depth_status: str | None = None
    gui_orchestrator: str = PIPELINE_NAME
    pipeline_phase: str = "NOT_STARTED"
    pipeline_phase_statuses: dict[str, str] = field(default_factory=dict)
    pipeline_phase_summaries: dict[str, dict[str, Any]] = field(default_factory=dict)
    overall_status: str = "READY"
    pipeline_stop_reason: str | None = None
    progress_sequence: int = 0
    search_source: str | None = None
    dimension_provenance: dict[str, str] = field(default_factory=dict)
    current_config_status: str | None = None
    expanded_planned: int = 0
    expanded_evaluated: int = 0
    adaptive_planned: int = 0
    adaptive_evaluated: int = 0
    total_research_evaluated: int = 0
    behavioral_cluster_count: int = 0
    behavioral_duplicate_count: int = 0
    adaptive_round: int = 0
    adaptive_max_rounds: int | None = None
    adaptive_new_clusters: int = 0
    adaptive_stop_reason: str | None = None
    validation_total_numeric: int = 0
    validation_total_behavioral: int = 0
    validation_eligible_numeric: int = 0
    validation_eligible_behavioral: int = 0
    freeze_requested_finalists: int = 0
    freeze_selected_finalists: int = 0
    freeze_id: str | None = None
    freeze_reason: str | None = None
    replay_diagnostics_status: str = "NOT_AVAILABLE"
    production_closed_trades: int = 0
    opportunity_evidence_rows: int = 0
    counterfactual_configs_evaluated: int = 0
    counterfactual_trade_count: int = 0
    counterfactual_wins: int = 0
    counterfactual_losses: int = 0

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
            provenance = self.dimension_provenance.get(name, self.search_source or "NOT_AVAILABLE")
            rows.append(f"{label} ({name}){conditional} · значений {len(self.dimension_values[name])} · источник {provenance}:\n  {values}")
        return "\n".join(rows)

    def format_current_parameters(self, *, show_all: bool = False) -> str:
        if self.current_config is None:
            return f"Текущая комбинация: не применимо для фазы {self.pipeline_phase}"
        values = self.resolved_config if show_all and self.resolved_config else self.current_config
        heading = "Все активные параметры" if show_all else "Параметры текущей комбинации"
        rows = [heading]
        for name, value in sorted((values or {}).items()):
            rows.append(f"{name} = {'—' if value is None else value}")
        return "\n".join(rows)


class ParameterSweepController:
    @staticmethod
    def prepare_result_search(values: Mapping[str, Any], output_root: Path,
                              dataset_hash: str, *, resume: Path | None = None) -> Path:
        """Internal result-search adapter, using exactly the CLI service contract."""
        from .result_search import ResultSearchService
        service = ResultSearchService()
        return service.prepare(service.request(values), output_root, dataset_hash, resume=resume)

    def __init__(self, config_path: Path, output_root: Path) -> None:
        self.config_path = config_path
        self.output_root = output_root
        self.events: queue.Queue[SweepEvent] = queue.Queue()
        self.pipeline_updates: queue.Queue[dict[str, Any]] = queue.Queue()
        self.state = PresentationState()
        self.engine = ParameterSweepEngine(self.events.put)
        self.pipeline: SingleSymbolResearchPipeline | None = None
        self.worker: threading.Thread | None = None
        self._close_after_stop = False
        self._discover_incomplete_run()

    @property
    def available_symbols(self) -> tuple[str, ...]:
        return resolve_parameter_sweep_universe()[1]

    def _discover_incomplete_run(self) -> None:
        if not self.output_root.is_dir():
            return
        pipeline_candidates = sorted(
            self.output_root.glob("*/SINGLE_SYMBOL_PIPELINE_MANIFEST.json"), reverse=True,
        )
        for path in pipeline_candidates:
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError):
                continue
            if value.get("final_pipeline_status") not in {"CANCELLED", "FAILED"}:
                continue
            symbol = value.get("selected_symbol")
            if symbol not in self.available_symbols:
                continue
            self.state.research_mode = ResearchMode.ALL.value
            self._apply_pipeline_manifest(value)
            self._hydrate_pipeline_artifacts(path.parent)
            self.state.resume_available = True
            self.state.status_text = f"Найден незавершённый pipeline: {self.state.run_id}"
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
                self.state.symbol = str(value.get("symbol") or "") or None
                if self.state.symbol not in self.available_symbols:
                    continue
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
        self, *, symbol: str | None = None, max_configs: int | None = None,
        mode: ResearchMode | str = ResearchMode.ALL,
    ) -> str:
        if self.worker and self.worker.is_alive():
            raise RuntimeError("PARAMETER_SWEEP_ALREADY_RUNNING")
        canonical_mode = parse_research_mode(mode)
        canonical_symbol = validate_parameter_sweep_symbol(symbol)
        run_id = generate_run_id(self.output_root)
        self._start(
            run_id, resume=False, max_configs=max_configs, mode=canonical_mode,
            symbol=canonical_symbol,
        )
        return run_id

    def resume_run(self, run_id: str, *, symbol: str | None = None) -> None:
        if self.worker and self.worker.is_alive():
            raise RuntimeError("PARAMETER_SWEEP_ALREADY_RUNNING")
        self._start(
            run_id, resume=True, max_configs=None,
            mode=parse_research_mode(self.state.research_mode),
            symbol=validate_parameter_sweep_symbol(symbol or self.state.symbol),
        )

    def _start(
        self, run_id: str, *, resume: bool, max_configs: int | None,
        mode: ResearchMode,
        symbol: str,
    ) -> None:
        failure_emitted = threading.Event()

        def receive(event: SweepEvent) -> None:
            if event.type == EventType.RUN_FAILED:
                failure_emitted.set()
            self.events.put(event)

        self.engine = ParameterSweepEngine(receive)
        self.pipeline = None
        self.state = PresentationState(
            status_text=RU["preparing"], run_id=run_id,
            output_directory=str(self.output_root / run_id), active=True,
            research_mode=mode.value,
            symbol=symbol,
            gui_orchestrator=PIPELINE_NAME if mode is ResearchMode.ALL else "LEGACY_EXPLICIT_RESEARCH_MODE",
            overall_status="RUNNING",
        )

        def receive_pipeline(value: Mapping[str, Any]) -> None:
            self.pipeline_updates.put(dict(value))

        def target() -> None:
            try:
                if mode is ResearchMode.ALL:
                    self.pipeline = SingleSymbolResearchPipeline(progress=receive_pipeline)
                    result = self.pipeline.run(
                        symbol=symbol, output_root=self.output_root,
                        run_id=run_id, resume=resume,
                    )
                    self.pipeline_updates.put(dict(result))
                else:
                    self.engine.run(
                        self.config_path, run_id=run_id, resume=resume,
                        max_configs=max_configs,
                        mode=mode,
                        symbol=symbol,
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
        if self.pipeline is not None and self.state.research_mode == ResearchMode.ALL.value:
            self.pipeline.request_cancel()
        else:
            self.engine.request_stop_after_current()
        self.state.status_text = RU["cancel_requested"]
        self.state.phase = "CANCEL_REQUESTED"

    def _apply_pipeline_manifest(self, value: Mapping[str, Any]) -> None:
        state = self.state
        state.gui_orchestrator = str(value.get("gui_orchestrator", PIPELINE_NAME))
        state.pipeline_phase = str(value.get("current_phase", "NOT_STARTED"))
        state.pipeline_phase_statuses = dict(value.get("phase_status", {}))
        state.pipeline_phase_summaries = {
            str(name): dict(summary)
            for name, summary in dict(value.get("phase_summary", {})).items()
        }
        state.overall_status = str(value.get("final_pipeline_status", "RUNNING"))
        state.strategy = PIPELINE_NAME
        state.pipeline_stop_reason = value.get("stop_reason")
        state.progress_sequence = int(value.get("progress_sequence", state.progress_sequence))
        state.search_source = value.get("range_generation_source") or value.get("search_source")
        state.production_closed_trades = int(
            state.pipeline_phase_summaries.get("SEPARABILITY", {}).get("closed_trades", 0)
        )
        state.opportunity_evidence_rows = int(value.get("opportunity_evidence_rows", 0))
        state.counterfactual_configs_evaluated = int(value.get("counterfactual_configs_evaluated", 0))
        state.counterfactual_trade_count = int(value.get("counterfactual_trade_count", 0))
        state.counterfactual_wins = int(value.get("counterfactual_wins", 0))
        state.counterfactual_losses = int(value.get("counterfactual_losses", 0))
        state.output_directory = str(self.output_root / str(value["pipeline_run_id"]))
        state.run_id = str(value["pipeline_run_id"])
        state.symbol = str(value["selected_symbol"])
        state.research_phase = state.pipeline_phase
        state.phase = state.pipeline_phase
        state.started_at = value.get("started_at")
        state.finished_at = value.get("completed_at")
        terminal = state.overall_status in {"COMPLETED", "STOPPED", "FAILED", "CANCELLED"}
        state.active = not terminal
        state.terminal_state = state.overall_status if terminal else None
        state.resume_available = state.overall_status in {"FAILED", "CANCELLED"}
        labels = {
            "SEPARABILITY": "Separability",
            "DATA_DRIVEN_RANGE_GENERATION": "Data-Driven Ranges",
            "EXPANDED_AUTOMATIC_SEARCH": "Expanded Search",
            "ADAPTIVE_REFINEMENT": "Adaptive Refinement",
            "VALIDATION_RANKING": "Validation Ranking",
            "IMMUTABLE_FINALIST_FREEZE": "Finalist Freeze",
            "COMPLETED": "Completed",
        }
        state.status_text = (
            f"Pipeline: {labels.get(state.pipeline_phase, state.pipeline_phase)}\n"
            f"Статус фазы: {state.pipeline_phase_statuses.get(state.pipeline_phase, state.overall_status)}\n"
            f"Общий статус: {state.overall_status}"
            + (f"\nПричина остановки: {state.pipeline_stop_reason}" if state.pipeline_stop_reason else "")
        )
        expanded = state.pipeline_phase_summaries.get("EXPANDED_AUTOMATIC_SEARCH", {})
        adaptive = state.pipeline_phase_summaries.get("ADAPTIVE_REFINEMENT", {})
        validation = state.pipeline_phase_summaries.get("VALIDATION_RANKING", {})
        freeze = state.pipeline_phase_summaries.get("IMMUTABLE_FINALIST_FREEZE", {})
        state.expanded_planned = int(expanded.get("planned", state.expanded_planned))
        state.expanded_evaluated = int(expanded.get("evaluated", state.expanded_evaluated))
        state.adaptive_evaluated = int(adaptive.get("evaluated", state.adaptive_evaluated))
        state.adaptive_round = int(adaptive.get("rounds", state.adaptive_round))
        state.adaptive_new_clusters = int(adaptive.get("new_clusters", state.adaptive_new_clusters))
        state.adaptive_stop_reason = adaptive.get("stop_reason", state.adaptive_stop_reason)
        state.validation_total_numeric = int(validation.get("total_numeric_configs", state.validation_total_numeric))
        state.validation_total_behavioral = int(validation.get("total_behavioral_clusters", state.validation_total_behavioral))
        state.validation_eligible_numeric = int(validation.get("eligible_numeric_configs", state.validation_eligible_numeric))
        state.validation_eligible_behavioral = int(validation.get("eligible_behavioral_clusters", state.validation_eligible_behavioral))
        state.freeze_requested_finalists = int(freeze.get("requested_finalists") or state.freeze_requested_finalists)
        state.freeze_selected_finalists = int(freeze.get("selected_finalists") or 0)
        state.freeze_id = freeze.get("freeze_id", state.freeze_id)
        state.freeze_reason = freeze.get("selection_reason", state.freeze_reason)
        if terminal:
            self._hydrate_pipeline_artifacts(Path(state.output_directory))

    def _apply_pipeline_progress(self, value: Mapping[str, Any]) -> None:
        state = self.state
        sequence = int(value.get("progress_sequence", 0))
        if sequence <= state.progress_sequence:
            return
        state.progress_sequence = sequence
        phase = str(value.get("phase", state.pipeline_phase))
        state.pipeline_phase = phase
        state.phase = phase
        event_type = str(value.get("event_type"))
        if event_type == "CONFIG_PLANNED":
            dimensions = value.get("active_dimensions") or []
            if dimensions:
                state.search_dimensions = [str(row["parameter_id"]) for row in dimensions]
                state.dimension_values = {
                    str(row["parameter_id"]): list(row.get("generated_values", [])) for row in dimensions
                }
                state.dimension_provenance = {
                    str(row["parameter_id"]): str(
                        row.get("evidence_source") or (row.get("provenance") or {}).get("source")
                        or state.search_source or "NOT_AVAILABLE"
                    ) for row in dimensions
                }
            if phase == "EXPANDED_AUTOMATIC_SEARCH":
                state.expanded_planned = int(value.get("planned_total", 0))
                state.planned = state.expanded_planned
            else:
                state.adaptive_planned = int(value.get("planned_total", 0))
                state.adaptive_round = int(value.get("adaptive_round", state.adaptive_round))
                state.adaptive_max_rounds = value.get("adaptive_max_rounds_if_known")
        elif event_type in {"CONFIG_STARTED", "CONFIG_COMPLETED"}:
            state.current_index = int(value.get("config_index", 0))
            state.current_config = dict(value.get("parameters") or {})
            state.changed_parameters = dict(state.current_config)
            state.current_config_status = "RUNNING" if event_type == "CONFIG_STARTED" else str(value.get("status"))
            if event_type == "CONFIG_COMPLETED":
                state.current_result = dict(value.get("result_summary") or {})
                if phase == "EXPANDED_AUTOMATIC_SEARCH":
                    state.expanded_evaluated = int(value.get("evaluated_count", 0))
                    state.planned = int(value.get("planned_total", state.expanded_planned))
                    state.completed = state.expanded_evaluated
                    state.accepted = int(value.get("accepted_count", state.accepted))
                    state.rejected = int(value.get("rejected_count", state.rejected))
                    state.insufficient = int(value.get("insufficient_count", state.insufficient))
                    state.errors = int(value.get("error_count", state.errors))
                    state.behavioral_cluster_count = int(value.get("behavioral_cluster_count", state.behavioral_cluster_count))
                else:
                    state.adaptive_evaluated = int(value.get("evaluated_count", 0))
                    state.adaptive_new_clusters = int(value.get("adaptive_new_clusters", state.adaptive_new_clusters))
            state.total_research_evaluated = state.expanded_evaluated + state.adaptive_evaluated
        elif event_type == "PHASE_COMPLETED" and phase == "ADAPTIVE_REFINEMENT":
            state.adaptive_evaluated = int(value.get("evaluated_count", state.adaptive_evaluated))
            state.adaptive_round = int(value.get("adaptive_round", state.adaptive_round))
            state.adaptive_new_clusters = int(value.get("adaptive_new_clusters", state.adaptive_new_clusters))
            state.adaptive_stop_reason = value.get("adaptive_stop_reason")

    def _hydrate_pipeline_artifacts(self, root: Path) -> None:
        state = self.state
        def read(path: Path) -> dict[str, Any]:
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
                return value if isinstance(value, dict) else {}
            except (OSError, ValueError, TypeError):
                return {}
        range_handoff = read(root / "02_data_driven_ranges" / "DATA_DRIVEN_RANGE_HANDOFF.json")
        parameters = list(range_handoff.get("parameters") or [])
        state.search_dimensions = [str(row["parameter"]) for row in parameters if row.get("eligible_for_search")]
        state.dimension_values = {
            str(row["parameter"]): list(row.get("generated_values") or [])
            for row in parameters if row.get("eligible_for_search")
        }
        state.dimension_provenance = {
            str(row["parameter"]): str((row.get("provenance") or {}).get("source") or range_handoff.get("range_generation_source") or "OUTCOME_INFORMED")
            for row in parameters if row.get("eligible_for_search")
        }
        state.search_source = str(range_handoff.get("range_generation_source") or "OUTCOME_INFORMED")
        expanded_status = read(root / "03_expanded_search" / "STATUS.json")
        state.expanded_planned = int(expanded_status.get("PLANNED_CONFIGS", state.expanded_planned))
        state.expanded_evaluated = int(expanded_status.get("EVALUATED_CONFIGS", state.expanded_evaluated))
        state.planned, state.completed = state.expanded_planned, state.expanded_evaluated
        results_path = root / "03_expanded_search" / "EXPANDED_SEARCH_RESULTS.jsonl"
        try:
            rows = [json.loads(line) for line in results_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        except (OSError, ValueError, TypeError):
            rows = []
        if rows:
            last = rows[-1]
            state.current_index = int(last.get("config_index", len(rows))) + 1
            state.current_config = dict(last.get("parameters") or last.get("overrides") or {})
            state.changed_parameters = dict(state.current_config)
            state.current_result = dict(last)
            state.current_config_status = str(last.get("evaluation_status"))
        statuses = [str(row.get("evaluation_status")) for row in rows]
        classes = [str(row.get("performance_class")) for row in rows]
        state.accepted = statuses.count("ACCEPTED")
        state.rejected = statuses.count("REJECTED")
        state.errors = statuses.count("ERROR")
        state.insufficient = classes.count("INSUFFICIENT_SAMPLE")
        state.negative_expectancy = classes.count("NEGATIVE_EXPECTANCY")
        state.promising = classes.count("PROMISING_RESEARCH")
        state.validation_candidates = classes.count("VALIDATION_CANDIDATE")
        state.behavioral_cluster_count = int(expanded_status.get("BEHAVIORALLY_DISTINCT_CONFIGS", 0))
        state.behavioral_duplicate_count = int(expanded_status.get("BEHAVIORAL_DUPLICATE_CONFIGS", 0))
        adaptive_status = read(root / "04_adaptive_refinement" / "STATUS.json")
        state.adaptive_evaluated = int(adaptive_status.get("NEW_NUMERIC_CONFIGS_EVALUATED", state.adaptive_evaluated))
        state.adaptive_round = int(adaptive_status.get("ADAPTIVE_ROUNDS", state.adaptive_round))
        state.adaptive_new_clusters = int(adaptive_status.get("NEW_BEHAVIORAL_CLUSTERS_DISCOVERED", state.adaptive_new_clusters))
        state.adaptive_stop_reason = adaptive_status.get("STOP_REASON", state.adaptive_stop_reason)
        state.total_research_evaluated = state.expanded_evaluated + state.adaptive_evaluated
        validation = read(root / "05_validation_ranking" / "STATUS.json")
        state.validation_total_numeric = int(validation.get("TOTAL_NUMERIC_CONFIGS", state.validation_total_numeric))
        state.validation_total_behavioral = int(validation.get("TOTAL_BEHAVIORAL_CLUSTERS", state.validation_total_behavioral))
        state.validation_eligible_numeric = int(validation.get("ELIGIBLE_NUMERIC_CONFIGS", state.validation_eligible_numeric))
        state.validation_eligible_behavioral = int(validation.get("ELIGIBLE_BEHAVIORAL_CLUSTERS", state.validation_eligible_behavioral))
        freeze = read(root / "06_finalist_freeze" / "FINALIST_FREEZE.json")
        integrity = read(root / "06_finalist_freeze" / "FINALIST_FREEZE_INTEGRITY.json")
        state.freeze_requested_finalists = int(freeze.get("requested_finalist_count", state.freeze_requested_finalists))
        state.freeze_selected_finalists = int(freeze.get("selected_finalist_count", state.freeze_selected_finalists))
        state.freeze_id = freeze.get("freeze_id", state.freeze_id)
        state.freeze_reason = freeze.get("selection_reason", state.freeze_reason)
        if integrity:
            state.integrity_status = str(integrity.get("integrity_status") or integrity.get("status") or "PASS")
        state.artifact_bytes = sum(path.stat().st_size for path in root.rglob("*") if path.is_file()) if root.is_dir() else 0
        counterfactual = read(root / "03_expanded_search" / "COUNTERFACTUAL_BOOTSTRAP_MANIFEST.json")
        if counterfactual:
            state.replay_diagnostics_status = "COUNTERFACTUAL_REPLAY_COMPLETED"
            state.counterfactual_configs_evaluated = int(counterfactual.get("configs_evaluated", 0))
            state.counterfactual_trade_count = int(counterfactual.get("trade_count", 0))
            state.counterfactual_wins = int(counterfactual.get("wins", 0))
            state.counterfactual_losses = int(counterfactual.get("losses", 0))
        elif rows:
            state.replay_diagnostics_status = "OUTCOME_REPLAY_COMPLETED"

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
        while True:
            try:
                update = self.pipeline_updates.get_nowait()
            except queue.Empty:
                break
            sequence = int(update.get("progress_sequence", 0))
            if sequence and sequence <= self.state.progress_sequence:
                continue
            if update.get("artifact") == "SINGLE_SYMBOL_PIPELINE_PROGRESS_EVENT":
                self._apply_pipeline_progress(update)
            else:
                self._apply_pipeline_manifest(update)
        status_path = Path(self.state.output_directory) / "STATUS.json"
        if status_path.is_file():
            try:
                persisted = read_effective_status(status_path)
            except (OSError, ValueError, KeyError):
                persisted = {}
            self.state.research_phase = str(persisted.get("research_phase", self.state.research_phase))
            self.state.holdout_status = str(persisted.get("holdout_status", self.state.holdout_status))
            self.state.finalists_frozen = bool(persisted.get("finalists_frozen", self.state.finalists_frozen))
            self.state.finalist_count = int(persisted.get("finalist_count", self.state.finalist_count))
            self.state.holdout_opened = bool(persisted.get("holdout_opened", self.state.holdout_opened))
            self.state.holdout_evaluated = bool(persisted.get("holdout_evaluated", self.state.holdout_evaluated))
            self.state.symbol = str(persisted.get("symbol") or self.state.symbol or "") or None
            self.state.canonical_validation = dict(
                persisted.get("canonical_validation") or self.state.canonical_validation
            )
            self.state.validation_minimum_trades = persisted.get("VALIDATION_MINIMUM_TRADES")
            self.state.minimum_independent_periods = persisted.get("MINIMUM_INDEPENDENT_PERIODS")
            self.state.independent_period_unit = persisted.get("INDEPENDENT_PERIOD_UNIT")
            self.state.validation_ranking_eligible_numeric = int(
                persisted.get("validation_ranking_eligible_numeric", self.state.validation_ranking_eligible_numeric)
            )
            self.state.validation_ranking_eligible_behavioral = int(
                persisted.get("validation_ranking_eligible_behavioral", self.state.validation_ranking_eligible_behavioral)
            )
            self.state.validation_ranking_descriptive_behavioral = int(
                persisted.get("validation_ranking_descriptive_behavioral", self.state.validation_ranking_descriptive_behavioral)
            )
            self.state.validation_ranking_top_eligible = persisted.get(
                "validation_ranking_top_eligible", self.state.validation_ranking_top_eligible
            )
            self.state.validation_ranking_top_descriptive = persisted.get(
                "validation_ranking_top_descriptive", self.state.validation_ranking_top_descriptive
            )
            self.state.history_target_days = int(persisted.get("history_target_days") or 30)
            self.state.history_start = persisted.get("history_start") or self.state.history_start
            self.state.history_end = persisted.get("history_end") or self.state.history_end
            self.state.history_actual_days = persisted.get("history_actual_days", self.state.history_actual_days)
            self.state.history_depth_status = persisted.get("history_depth_status") or self.state.history_depth_status
        return drained

    def _apply(self, event: SweepEvent) -> None:
        payload = event.payload
        self.state.phase = event.type.value
        if event.type in {EventType.RUN_STARTED, EventType.RUN_RESUMED}:
            self.state.run_id = event.run_id
            self.state.research_mode = str(payload["research_mode"])
            self.state.symbol = str(payload.get("symbol") or self.state.symbol or "") or None
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
            if payload.get("resolved_seed") is not None:
                self.state.resolved_seed = int(payload["resolved_seed"])
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
            self.state.evaluation_status_counts = dict(payload.get("evaluation_status_counts", self.state.evaluation_status_counts))
            self.state.performance_class_counts = dict(payload.get("performance_class_counts", self.state.performance_class_counts))
        elif event.type == EventType.CONFIG_COMPLETED:
            self.state.current_result = dict(payload["result"])
            self.state.canonical_validation = dict(payload.get("canonical_validation") or {})
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
            self.state.evaluation_status_counts = dict(payload["evaluation_status_counts"])
            self.state.performance_class_counts = dict(payload["performance_class_counts"])
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
