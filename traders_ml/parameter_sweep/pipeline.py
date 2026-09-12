"""Canonical GUI orchestration for the single-symbol research pipeline.

The pipeline is intentionally a thin coordinator over the already-authoritative
research stages.  It owns symbol/provenance guards and lifecycle state, not any
research formula, trading behavior, holdout access, or promotion action.
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import threading
from typing import Any, Callable, Mapping

from .adaptive_refinement import run_adaptive_refinement
from .artifact_writer import DEFAULT_ARTIFACT_WRITER
from .data_driven_ranges import run_range_generation
from .engine import ReadOnlyResearchDatabase, resolve_database_binding
from .expanded_search import run_expanded_search
from .separability import run_separability
from .universe import validate_parameter_sweep_symbol


PIPELINE_SCHEMA_VERSION = 1
PIPELINE_NAME = "NEW_SINGLE_SYMBOL_PIPELINE"
PROFILE = "trade-5m-v2"
PHASE_ORDER = (
    "SEPARABILITY",
    "DATA_DRIVEN_RANGE_GENERATION",
    "EXPANDED_AUTOMATIC_SEARCH",
    "ADAPTIVE_REFINEMENT",
    "COMPLETED",
)
EXECUTION_PHASES = PHASE_ORDER[:4]
PHASE_DIRECTORIES = {
    "SEPARABILITY": "01_separability",
    "DATA_DRIVEN_RANGE_GENERATION": "02_data_driven_ranges",
    "EXPANDED_AUTOMATIC_SEARCH": "03_expanded_search",
    "ADAPTIVE_REFINEMENT": "04_adaptive_refinement",
}

ProgressCallback = Callable[[Mapping[str, Any]], None]
PhaseRunner = Callable[..., Mapping[str, Any]]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fingerprint(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("FAIL_CLOSED_HANDOFF_MISMATCH")
    return value


class SingleSymbolResearchPipeline:
    """Execute and persist the four-stage GUI research workflow."""

    def __init__(
        self,
        *,
        progress: ProgressCallback | None = None,
        separability_runner: PhaseRunner | None = None,
        range_runner: PhaseRunner = run_range_generation,
        expanded_runner: PhaseRunner = run_expanded_search,
        adaptive_runner: PhaseRunner = run_adaptive_refinement,
    ) -> None:
        self._progress = progress or (lambda _update: None)
        self._separability_runner = separability_runner
        self._range_runner = range_runner
        self._expanded_runner = expanded_runner
        self._adaptive_runner = adaptive_runner
        self._cancel = threading.Event()

    def request_cancel(self) -> None:
        self._cancel.set()

    def _emit(self, manifest: Mapping[str, Any]) -> None:
        self._progress(dict(manifest))

    @staticmethod
    def _new_manifest(*, run_id: str, symbol: str) -> dict[str, Any]:
        return {
            "artifact": "SINGLE_SYMBOL_PIPELINE_MANIFEST",
            "pipeline_schema_version": PIPELINE_SCHEMA_VERSION,
            "gui_orchestrator": PIPELINE_NAME,
            "pipeline_run_id": run_id,
            "gui_run_id": run_id,
            "selected_symbol": symbol,
            "profile": PROFILE,
            "started_at": _utc_now(),
            "completed_at": None,
            "phase_order": list(PHASE_ORDER),
            "current_phase": PHASE_ORDER[0],
            "phase_status": {phase: "NOT_STARTED" for phase in EXECUTION_PHASES},
            "phase_summary": {},
            "separability_status": "NOT_STARTED",
            "separability_handoff_fingerprint": None,
            "range_generation_status": "NOT_STARTED",
            "range_handoff_fingerprint": None,
            "expanded_search_status": "NOT_STARTED",
            "expanded_search_handoff_fingerprint": None,
            "adaptive_refinement_status": "NOT_STARTED",
            "adaptive_handoff_fingerprint": None,
            "dataset_fingerprint": None,
            "legacy_fallback_used": False,
            "legacy_array_fallback": 0,
            "legacy_targeted_staged_used": False,
            "search_source": None,
            "adaptive_source": None,
            "next_stage_available": None,
            "validation_ranking_executed": False,
            "finalist_freeze_executed": False,
            "holdout_opened": False,
            "live_state": False,
            "binance_order_calls": 0,
            "production_mutations": 0,
            "final_pipeline_status": "RUNNING",
            "stop_reason": None,
            "GUI_ORCHESTRATOR": PIPELINE_NAME,
            "PHASE_1": "SEPARABILITY",
            "PHASE_2": "DATA_DRIVEN_RANGE_GENERATION",
            "PHASE_3": "EXPANDED_AUTOMATIC_SEARCH",
            "PHASE_4": "ADAPTIVE_REFINEMENT",
            "PHASE_5": "COMPLETED",
            "LEGACY_TARGETED_STAGED_USED": "NO",
            "LEGACY_ARRAY_FALLBACK": 0,
            "handoff_fingerprint_chain": None,
            "symbol_binding": None,
            "resume_guards": [
                "pipeline_schema_version", "selected_symbol", "profile",
                "dataset_fingerprint", "phase_handoff_fingerprints",
            ],
        }

    @staticmethod
    def _write(root: Path, manifest: Mapping[str, Any]) -> None:
        DEFAULT_ARTIFACT_WRITER.atomic_json(
            root / "SINGLE_SYMBOL_PIPELINE_MANIFEST.json",
            dict(manifest),
            operation="single_symbol_pipeline_manifest",
        )

    @staticmethod
    def _validate_resume(root: Path, manifest: Mapping[str, Any], symbol: str) -> None:
        if manifest.get("pipeline_schema_version") != PIPELINE_SCHEMA_VERSION:
            raise ValueError("FAIL_CLOSED_PIPELINE_VERSION_MISMATCH")
        if manifest.get("selected_symbol") != symbol:
            raise ValueError("FAIL_CLOSED_SYMBOL_MISMATCH")
        if manifest.get("profile") != PROFILE or manifest.get("phase_order") != list(PHASE_ORDER):
            raise ValueError("FAIL_CLOSED_HANDOFF_MISMATCH")
        checks = (
            ("separability_handoff_fingerprint", root / PHASE_DIRECTORIES[PHASE_ORDER[0]] / "SEPARABILITY_HANDOFF.json"),
            ("range_handoff_fingerprint", root / PHASE_DIRECTORIES[PHASE_ORDER[1]] / "DATA_DRIVEN_RANGE_HANDOFF.json"),
            ("expanded_search_handoff_fingerprint", root / PHASE_DIRECTORIES[PHASE_ORDER[2]] / "EXPANDED_SEARCH_HANDOFF.json"),
            ("adaptive_handoff_fingerprint", root / PHASE_DIRECTORIES[PHASE_ORDER[3]] / "ADAPTIVE_REFINEMENT_HANDOFF.json"),
        )
        for field, path in checks:
            expected = manifest.get(field)
            if expected is not None and (not path.is_file() or _fingerprint(path) != expected):
                raise ValueError("FAIL_CLOSED_HANDOFF_MISMATCH")
        dataset_path = root / PHASE_DIRECTORIES[PHASE_ORDER[0]] / "SEPARABILITY_DATASET_MANIFEST.json"
        if manifest.get("dataset_fingerprint") is not None:
            if not dataset_path.is_file() or _read_json(dataset_path).get("dataset_sha256") != manifest["dataset_fingerprint"]:
                raise ValueError("FAIL_CLOSED_HANDOFF_MISMATCH")

    def _run_separability(self, *, symbol: str, output: Path) -> Mapping[str, Any]:
        if self._separability_runner is not None:
            return self._separability_runner(symbol=symbol, output=output)
        database = ReadOnlyResearchDatabase(resolve_database_binding())
        try:
            return run_separability(database=database, symbol=symbol, output=output)
        finally:
            database.dispose()

    def _phase_start(self, root: Path, manifest: dict[str, Any], phase: str) -> None:
        manifest["current_phase"] = phase
        manifest["phase_status"][phase] = "RUNNING"
        self._write(root, manifest)
        self._emit(manifest)

    def _finish(
        self, root: Path, manifest: dict[str, Any], *, status: str, reason: str | None,
    ) -> dict[str, Any]:
        manifest["final_pipeline_status"] = status
        manifest["stop_reason"] = reason
        manifest["completed_at"] = _utc_now()
        manifest["current_phase"] = "COMPLETED" if status == "COMPLETED" else manifest["current_phase"]
        manifest["handoff_fingerprint_chain"] = {
            "separability": manifest.get("separability_handoff_fingerprint"),
            "data_driven_ranges": manifest.get("range_handoff_fingerprint"),
            "expanded_search": manifest.get("expanded_search_handoff_fingerprint"),
            "adaptive_refinement": manifest.get("adaptive_handoff_fingerprint"),
        }
        manifest["symbol_binding"] = {
            "gui_selected_symbol": manifest["selected_symbol"],
            "run_config_symbol": manifest["selected_symbol"],
            "separability_symbol": manifest["selected_symbol"] if manifest.get("separability_handoff_fingerprint") else None,
            "range_generation_symbol": manifest["selected_symbol"] if manifest.get("range_handoff_fingerprint") else None,
            "expanded_search_symbol": manifest["selected_symbol"] if manifest.get("expanded_search_handoff_fingerprint") else None,
            "adaptive_refinement_symbol": manifest["selected_symbol"] if manifest.get("adaptive_handoff_fingerprint") else None,
        }
        self._write(root, manifest)
        self._emit(manifest)
        return manifest

    def _cancel_if_requested(self, root: Path, manifest: dict[str, Any]) -> dict[str, Any] | None:
        if not self._cancel.is_set():
            return None
        current = str(manifest["current_phase"])
        if current in manifest["phase_status"] and manifest["phase_status"][current] == "RUNNING":
            manifest["phase_status"][current] = "STOPPED"
        return self._finish(root, manifest, status="CANCELLED", reason="USER_CANCELLED")

    def run(
        self, *, symbol: object, output_root: Path, run_id: str,
        resume: bool = False,
    ) -> dict[str, Any]:
        self._cancel.clear()
        selected = validate_parameter_sweep_symbol(symbol)
        root = output_root / run_id
        root.mkdir(parents=True, exist_ok=True)
        manifest_path = root / "SINGLE_SYMBOL_PIPELINE_MANIFEST.json"
        if resume:
            if not manifest_path.is_file():
                raise ValueError("RESUME_MANIFEST_NOT_AVAILABLE")
            manifest = _read_json(manifest_path)
            self._validate_resume(root, manifest, selected)
            if manifest.get("final_pipeline_status") in {"COMPLETED", "STOPPED"}:
                self._emit(manifest)
                return manifest
            manifest["completed_at"] = None
            manifest["final_pipeline_status"] = "RUNNING"
            manifest["stop_reason"] = None
        else:
            if manifest_path.exists():
                raise ValueError("PIPELINE_RUN_ALREADY_EXISTS")
            manifest = self._new_manifest(run_id=run_id, symbol=selected)
            self._write(root, manifest)
            self._emit(manifest)

        sep_dir = root / PHASE_DIRECTORIES[PHASE_ORDER[0]]
        range_dir = root / PHASE_DIRECTORIES[PHASE_ORDER[1]]
        expanded_dir = root / PHASE_DIRECTORIES[PHASE_ORDER[2]]
        adaptive_dir = root / PHASE_DIRECTORIES[PHASE_ORDER[3]]

        try:
            if manifest["phase_status"][PHASE_ORDER[0]] not in {"COMPLETED", "LIMITED"}:
                self._phase_start(root, manifest, PHASE_ORDER[0])
                sep = self._run_separability(symbol=selected, output=sep_dir)
                sep_manifest = dict(sep["manifest"])
                if sep_manifest.get("symbol") != selected or sep_manifest.get("profile") != PROFILE:
                    raise ValueError("FAIL_CLOSED_SYMBOL_MISMATCH")
                sep_status = "LIMITED" if sep_manifest.get("final_status") == "PASS_LIMITED_SAMPLE" else "COMPLETED"
                manifest["phase_status"][PHASE_ORDER[0]] = sep_status
                manifest["separability_status"] = sep_status
                manifest["separability_handoff_fingerprint"] = _fingerprint(sep_dir / "SEPARABILITY_HANDOFF.json")
                manifest["dataset_fingerprint"] = sep_manifest.get("dataset_sha256")
                manifest["phase_summary"][PHASE_ORDER[0]] = {
                    "closed_trades": sep_manifest.get("closed_trades", 0),
                    "wins": sep_manifest.get("wins", 0),
                    "losses": sep_manifest.get("losses", 0),
                    "sample_adequacy": sep_manifest.get("sample_adequacy"),
                }
                self._write(root, manifest)
                self._emit(manifest)
            cancelled = self._cancel_if_requested(root, manifest)
            if cancelled:
                return cancelled

            if manifest["phase_status"][PHASE_ORDER[1]] != "COMPLETED":
                self._phase_start(root, manifest, PHASE_ORDER[1])
                ranges = self._range_runner(input_dir=sep_dir, output=range_dir)
                range_handoff = dict(ranges["handoff"])
                if range_handoff.get("symbol") != selected or range_handoff.get("profile") != PROFILE:
                    raise ValueError("FAIL_CLOSED_SYMBOL_MISMATCH")
                range_count = sum(bool(row.get("eligible_for_search")) for row in range_handoff.get("parameters", ()))
                provisional = sum(bool(row.get("provisional")) for row in range_handoff.get("parameters", ()))
                manifest["range_handoff_fingerprint"] = _fingerprint(range_dir / "DATA_DRIVEN_RANGE_HANDOFF.json")
                manifest["phase_summary"][PHASE_ORDER[1]] = {
                    "generated_parameters": range_count, "provisional_count": provisional,
                }
                if range_count == 0:
                    manifest["phase_status"][PHASE_ORDER[1]] = "STOPPED"
                    manifest["range_generation_status"] = "STOPPED"
                    return self._finish(
                        root, manifest, status="STOPPED",
                        reason="STOPPED_NO_DATA_DRIVEN_SEARCH_RANGES",
                    )
                manifest["phase_status"][PHASE_ORDER[1]] = "COMPLETED"
                manifest["range_generation_status"] = "COMPLETED"
                self._write(root, manifest)
                self._emit(manifest)
            cancelled = self._cancel_if_requested(root, manifest)
            if cancelled:
                return cancelled

            if manifest["phase_status"][PHASE_ORDER[2]] != "COMPLETED":
                self._phase_start(root, manifest, PHASE_ORDER[2])
                expanded = self._expanded_runner(
                    handoff_path=range_dir / "DATA_DRIVEN_RANGE_HANDOFF.json",
                    dataset_path=sep_dir / "SEPARABILITY_DATASET.jsonl",
                    dataset_manifest_path=sep_dir / "SEPARABILITY_DATASET_MANIFEST.json",
                    output=expanded_dir, symbol=selected, profile=PROFILE, resume=resume,
                )
                expanded_handoff = dict(expanded["handoff"])
                if expanded_handoff.get("symbol") != selected:
                    raise ValueError("FAIL_CLOSED_SYMBOL_MISMATCH")
                if expanded_handoff.get("search_source") != "DATA_DRIVEN_RANGE_HANDOFF":
                    raise ValueError("FAIL_CLOSED_HANDOFF_MISMATCH")
                if expanded_handoff.get("range_handoff_fingerprint") != manifest["range_handoff_fingerprint"]:
                    raise ValueError("FAIL_CLOSED_HANDOFF_MISMATCH")
                manifest["phase_status"][PHASE_ORDER[2]] = "COMPLETED"
                manifest["expanded_search_status"] = "COMPLETED"
                manifest["expanded_search_handoff_fingerprint"] = _fingerprint(expanded_dir / "EXPANDED_SEARCH_HANDOFF.json")
                manifest["search_source"] = "DATA_DRIVEN_RANGE_HANDOFF"
                status = dict(expanded.get("status", {}))
                manifest["phase_summary"][PHASE_ORDER[2]] = {
                    "planned": status.get("PLANNED_CONFIGS", 0),
                    "evaluated": status.get("EVALUATED_CONFIGS", 0),
                    "behavioral_clusters": status.get("BEHAVIORALLY_DISTINCT_CONFIGS", 0),
                }
                self._write(root, manifest)
                self._emit(manifest)
            cancelled = self._cancel_if_requested(root, manifest)
            if cancelled:
                return cancelled

            if manifest["phase_status"][PHASE_ORDER[3]] != "COMPLETED":
                self._phase_start(root, manifest, PHASE_ORDER[3])
                adaptive = self._adaptive_runner(
                    range_handoff_path=range_dir / "DATA_DRIVEN_RANGE_HANDOFF.json",
                    expanded_config_path=expanded_dir / "EXPANDED_SEARCH_CONFIG.json",
                    expanded_handoff_path=expanded_dir / "EXPANDED_SEARCH_HANDOFF.json",
                    behavioral_clusters_path=expanded_dir / "BEHAVIORAL_CLUSTERS.json",
                    expanded_results_path=expanded_dir / "EXPANDED_SEARCH_RESULTS.jsonl",
                    normalization_path=expanded_dir / "SEARCH_VALUE_NORMALIZATION.json",
                    dataset_path=sep_dir / "SEPARABILITY_DATASET.jsonl",
                    dataset_manifest_path=sep_dir / "SEPARABILITY_DATASET_MANIFEST.json",
                    output=adaptive_dir, symbol=selected, profile=PROFILE, resume=resume,
                )
                adaptive_handoff = dict(adaptive["handoff"])
                if adaptive_handoff.get("symbol") != selected:
                    raise ValueError("FAIL_CLOSED_SYMBOL_MISMATCH")
                inputs = dict(adaptive_handoff.get("campaign_inputs", {}))
                if inputs.get("expanded_search_fingerprint") is None:
                    raise ValueError("FAIL_CLOSED_HANDOFF_MISMATCH")
                manifest["phase_status"][PHASE_ORDER[3]] = "COMPLETED"
                manifest["adaptive_refinement_status"] = "COMPLETED"
                manifest["adaptive_handoff_fingerprint"] = _fingerprint(adaptive_dir / "ADAPTIVE_REFINEMENT_HANDOFF.json")
                manifest["adaptive_source"] = "EXPANDED_SEARCH_HANDOFF"
                status = dict(adaptive.get("status", {}))
                manifest["phase_summary"][PHASE_ORDER[3]] = {
                    "rounds": status.get("ADAPTIVE_ROUNDS", 0),
                    "new_clusters": status.get("NEW_BEHAVIORAL_CLUSTERS_DISCOVERED", 0),
                    "stop_reason": status.get("STOP_REASON"),
                }
                manifest["next_stage_available"] = "VALIDATION_RANKING"
                self._write(root, manifest)
                self._emit(manifest)
            return self._finish(root, manifest, status="COMPLETED", reason=None)
        except BaseException as error:
            reason = str(error) or type(error).__name__
            if "SYMBOL" in reason:
                reason = "FAIL_CLOSED_SYMBOL_MISMATCH"
            elif any(token in reason for token in ("HANDOFF", "FINGERPRINT", "DATASET", "PROFILE")):
                reason = "FAIL_CLOSED_HANDOFF_MISMATCH"
            current = str(manifest["current_phase"])
            if current in manifest["phase_status"]:
                manifest["phase_status"][current] = "FAILED"
            return self._finish(root, manifest, status="FAILED", reason=reason)


__all__ = [
    "PHASE_ORDER", "PIPELINE_NAME", "PIPELINE_SCHEMA_VERSION",
    "SingleSymbolResearchPipeline",
]
