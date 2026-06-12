from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from app.diagnostics.feature_group_quality import FeatureGroupQualityScorer
from app.diagnostics.feature_leakage_guard import FeatureLeakageGuard
from app.diagnostics.feature_quality_diagnostics import FeatureQualityDiagnostics
from app.diagnostics.regime_feature_diagnostics import RegimeFeatureDiagnostics
from app.experiments.feature_regime_experiment_reporter import FeatureRegimeExperimentReporter
from app.experiments.label_grid_experiment_runner import (
    LabelGridExperimentConfig,
    LabelGridExperimentRunner,
)
from app.experiments.regime_experiment_planner import RegimeExperimentPlanner
from app.labels.label_quality_grid import LabelQualityGridPlanner
from app.labels.regime_label_config import RegimeLabelConfigPlanner


FEATURE_REGIME_EXPERIMENT_RUNNER_NAME = "feature_regime_experiment_runner"
FEATURE_REGIME_EXPERIMENT_RUNNER_VERSION = "ml33"
DEFAULT_ML31_BASELINE_REFERENCE = {
    "experiment_id": "real_grid_ml31_3_BTCUSDT_15m_20250101_20260612_130501",
    "best_candidate_config_id": "lv2_h12_thr05_tp15_sl10",
    "best_candidate_score": -6.372101,
}


@dataclass(frozen=True, slots=True)
class FeatureRegimeExperimentConfig:
    symbol: str
    interval: str
    start_date: str
    end_date: str | None = None
    experiment_id: str | None = None
    base_label_config_ids: tuple[str, ...] = ()
    regime_config_ids: tuple[str, ...] = ()
    max_configs: int | None = None
    dry_run: bool = False
    sample_mode: bool = False
    run_training: bool = True
    run_regime_diagnostics: bool = True
    run_feature_diagnostics: bool = True
    run_leakage_guard: bool = True
    run_candidate_selection: bool = True
    output_dir: Path = Path("reports/feature_regime_experiments")

    def resolved_end_date(self) -> str:
        if self.end_date is not None:
            return self.end_date
        return date.today().isoformat()

    def resolved_experiment_id(self) -> str:
        if self.experiment_id is not None:
            return self.experiment_id
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"feature_regime_{self.symbol}_{self.interval}_{timestamp}"


@dataclass(frozen=True, slots=True)
class FeatureRegimeCandidateResult:
    candidate_id: str
    config_id: str
    label_config: dict[str, Any]
    status: str
    quality_status: str | None
    candidate_status: str | None
    score: float | None
    failed_gates: tuple[str, ...] = ()
    passed_gates: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()
    regime_specific_training_applied: bool = False
    feature_weak_signal_detected: bool = False
    feature_leakage_risk_detected: bool = False
    approved_for_live_trading: bool = False
    approved_for_auto_activation: bool = False
    orders_enabled: bool = False
    traders_core_connected: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "config_id": self.config_id,
            "label_config": dict(self.label_config),
            "status": self.status,
            "quality_status": self.quality_status,
            "candidate_status": self.candidate_status,
            "score": self.score,
            "failed_gates": list(self.failed_gates),
            "passed_gates": list(self.passed_gates),
            "warnings": list(self.warnings),
            "recommendations": list(self.recommendations),
            "regime_specific_training_applied": self.regime_specific_training_applied,
            "feature_weak_signal_detected": self.feature_weak_signal_detected,
            "feature_leakage_risk_detected": self.feature_leakage_risk_detected,
            "approved_for_live_trading": self.approved_for_live_trading,
            "approved_for_auto_activation": self.approved_for_auto_activation,
            "orders_enabled": self.orders_enabled,
            "traders_core_connected": self.traders_core_connected,
        }


@dataclass(frozen=True, slots=True)
class FeatureRegimeExperimentResult:
    experiment_id: str
    symbol: str
    interval: str
    start_date: str
    end_date: str
    status: str
    experiment_status: str
    config_count: int
    candidate_count: int
    accepted_candidate_count: int
    rejected_candidate_count: int
    best_candidate_id: str | None
    best_candidate_config_id: str | None
    best_candidate_score: float | None
    feature_quality_summary: dict[str, Any]
    feature_group_quality_summary: dict[str, Any]
    regime_feature_summary: dict[str, Any]
    feature_leakage_summary: dict[str, Any]
    regime_experiment_plan_summary: dict[str, Any]
    candidate_results: tuple[FeatureRegimeCandidateResult, ...]
    ranking: tuple[dict[str, Any], ...]
    failed_gates_summary: dict[str, int]
    warnings: tuple[str, ...]
    recommendations: tuple[str, ...]
    regime_training_applied: bool
    output_dir: str
    log_path: str
    events_path: str
    summary_json_path: str
    summary_markdown_path: str
    baseline_reference: dict[str, Any]
    approved_for_traders_core_integration: bool = False
    approved_for_live_trading: bool = False
    approved_for_auto_activation: bool = False
    orders_enabled: bool = False
    traders_core_connected: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "symbol": self.symbol,
            "interval": self.interval,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "status": self.status,
            "experiment_status": self.experiment_status,
            "config_count": self.config_count,
            "candidate_count": self.candidate_count,
            "accepted_candidate_count": self.accepted_candidate_count,
            "rejected_candidate_count": self.rejected_candidate_count,
            "best_candidate_id": self.best_candidate_id,
            "best_candidate_config_id": self.best_candidate_config_id,
            "best_candidate_score": self.best_candidate_score,
            "feature_quality_summary": dict(self.feature_quality_summary),
            "feature_group_quality_summary": dict(self.feature_group_quality_summary),
            "regime_feature_summary": dict(self.regime_feature_summary),
            "feature_leakage_summary": dict(self.feature_leakage_summary),
            "regime_experiment_plan_summary": dict(self.regime_experiment_plan_summary),
            "candidate_results": [item.to_dict() for item in self.candidate_results],
            "ranking": [dict(item) for item in self.ranking],
            "failed_gates_summary": dict(self.failed_gates_summary),
            "warnings": list(self.warnings),
            "recommendations": list(self.recommendations),
            "regime_training_applied": self.regime_training_applied,
            "output_dir": self.output_dir,
            "log_path": self.log_path,
            "events_path": self.events_path,
            "summary_json_path": self.summary_json_path,
            "summary_markdown_path": self.summary_markdown_path,
            "baseline_reference": dict(self.baseline_reference),
            "approved_for_traders_core_integration": self.approved_for_traders_core_integration,
            "approved_for_live_trading": self.approved_for_live_trading,
            "approved_for_auto_activation": self.approved_for_auto_activation,
            "orders_enabled": self.orders_enabled,
            "traders_core_connected": self.traders_core_connected,
        }


@dataclass(frozen=True, slots=True)
class _ExperimentPaths:
    experiment_dir: Path
    diagnostics_dir: Path
    candidate_results_dir: Path
    log_path: Path
    events_path: Path
    summary_json_path: Path
    summary_markdown_path: Path


class _ExperimentLogger:
    def __init__(self, *, experiment_id: str, output_dir: Path | str) -> None:
        root = Path(output_dir)
        experiment_dir = root / experiment_id
        diagnostics_dir = experiment_dir / "diagnostics"
        candidate_results_dir = experiment_dir / "candidate_results"
        diagnostics_dir.mkdir(parents=True, exist_ok=True)
        candidate_results_dir.mkdir(parents=True, exist_ok=True)
        self._experiment_id = experiment_id
        self._paths = _ExperimentPaths(
            experiment_dir=experiment_dir,
            diagnostics_dir=diagnostics_dir,
            candidate_results_dir=candidate_results_dir,
            log_path=experiment_dir / "feature_regime_experiment.log",
            events_path=experiment_dir / "feature_regime_experiment_events.jsonl",
            summary_json_path=experiment_dir / "feature_regime_experiment_summary.json",
            summary_markdown_path=experiment_dir / "feature_regime_experiment_summary.md",
        )

    @property
    def paths(self) -> _ExperimentPaths:
        return self._paths

    def event(
        self,
        *,
        event: str,
        status: str,
        data: dict[str, Any] | None = None,
        candidate_id: str | None = None,
        message: str | None = None,
    ) -> None:
        timestamp = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
        payload = {
            "timestamp": timestamp,
            "experiment_id": self._experiment_id,
            "candidate_id": candidate_id,
            "event": event,
            "status": status,
            "data": data or {},
        }
        with self._paths.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            handle.write("\n")

        human_timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        candidate_part = f" candidate_id={candidate_id}" if candidate_id else ""
        message_part = f" message={message}" if message else ""
        details = ""
        if data:
            details = " " + " ".join(f"{key}={value}" for key, value in data.items())
        with self._paths.log_path.open("a", encoding="utf-8") as handle:
            handle.write(
                f"[{human_timestamp}] [INFO] experiment_id={self._experiment_id}{candidate_part} "
                f"status={status} event={event}{message_part}{details}\n"
            )


class FeatureRegimeExperimentRunner:
    """Run a feature/regime-aware experiment with attached diagnostics."""

    def __init__(
        self,
        *,
        feature_quality_diagnostics: FeatureQualityDiagnostics | None = None,
        feature_group_quality_scorer: FeatureGroupQualityScorer | None = None,
        regime_feature_diagnostics: RegimeFeatureDiagnostics | None = None,
        feature_leakage_guard: FeatureLeakageGuard | None = None,
        regime_experiment_planner: RegimeExperimentPlanner | None = None,
        base_grid_planner: LabelQualityGridPlanner | None = None,
        regime_label_planner: RegimeLabelConfigPlanner | None = None,
        label_grid_runner: LabelGridExperimentRunner | None = None,
        reporter: FeatureRegimeExperimentReporter | None = None,
    ) -> None:
        self._feature_quality_diagnostics = feature_quality_diagnostics or FeatureQualityDiagnostics()
        self._feature_group_quality_scorer = feature_group_quality_scorer or FeatureGroupQualityScorer()
        self._regime_feature_diagnostics = regime_feature_diagnostics or RegimeFeatureDiagnostics()
        self._feature_leakage_guard = feature_leakage_guard or FeatureLeakageGuard()
        self._regime_experiment_planner = regime_experiment_planner or RegimeExperimentPlanner()
        self._base_grid_planner = base_grid_planner or LabelQualityGridPlanner()
        self._regime_label_planner = regime_label_planner or RegimeLabelConfigPlanner()
        self._label_grid_runner = label_grid_runner or LabelGridExperimentRunner()
        self._reporter = reporter or FeatureRegimeExperimentReporter()

    def build_preview(self) -> dict[str, Any]:
        return {
            "runner_name": FEATURE_REGIME_EXPERIMENT_RUNNER_NAME,
            "runner_version": FEATURE_REGIME_EXPERIMENT_RUNNER_VERSION,
            "available_base_label_configs": self._base_grid_planner.build_grid()["configs"],
            "available_regime_configs": self._regime_label_planner.build_configs()["configs"],
            "feature_diagnostics_plan": {
                "feature_quality": True,
                "feature_group_quality": True,
                "feature_leakage_guard": True,
            },
            "regime_diagnostics_plan": {
                "regime_feature_diagnostics": True,
                "regime_experiment_plan": True,
            },
            "safety_flags": {
                "approved_for_live_trading": False,
                "approved_for_auto_activation": False,
                "orders_enabled": False,
                "traders_core_connected": False,
            },
        }

    def run(self, config: FeatureRegimeExperimentConfig) -> FeatureRegimeExperimentResult:
        experiment_id = config.resolved_experiment_id()
        end_date = config.resolved_end_date()
        logger = _ExperimentLogger(experiment_id=experiment_id, output_dir=config.output_dir)
        logger.event(
            event="experiment_started",
            status="RUNNING",
            data={
                "symbol": config.symbol,
                "interval": config.interval,
                "start_date": config.start_date,
                "end_date": end_date,
                "dry_run": config.dry_run,
                "sample_mode": config.sample_mode,
                "max_configs": config.max_configs,
            },
            message="Feature/regime experiment started",
        )

        sample_rows = self._build_sample_rows()
        diagnostics = self._collect_diagnostics(config=config, rows=sample_rows, logger=logger)
        selected_base_configs = self._select_base_configs(config)
        selected_regime_configs = self._select_regime_configs(config, selected_base_configs)
        regime_training_applied = False
        warnings = ["regime_specific_training_not_integrated_with_label_builder"]

        if config.dry_run:
            candidate_results = self._dry_run_candidates(
                selected_base_configs,
                feature_weak_signal_detected=bool(diagnostics["feature_quality"]["weak_signal_detected"]),
                feature_leakage_risk_detected=bool(diagnostics["feature_leakage"]["leakage_risk_detected"]),
                logger=logger,
            )
            experiment_status = "DRY_RUN_COMPLETED"
        elif config.sample_mode:
            candidate_results = self._sample_candidates(
                selected_base_configs,
                feature_weak_signal_detected=bool(diagnostics["feature_quality"]["weak_signal_detected"]),
                feature_leakage_risk_detected=bool(diagnostics["feature_leakage"]["leakage_risk_detected"]),
                logger=logger,
            )
            experiment_status = "SAMPLE_COMPLETED"
        else:
            candidate_results, experiment_status, runtime_warnings = self._real_candidates(
                config=config,
                experiment_id=experiment_id,
                selected_base_configs=selected_base_configs,
                feature_weak_signal_detected=bool(diagnostics["feature_quality"]["weak_signal_detected"]),
                feature_leakage_risk_detected=bool(diagnostics["feature_leakage"]["leakage_risk_detected"]),
                logger=logger,
                experiment_dir=logger.paths.experiment_dir,
            )
            warnings.extend(runtime_warnings)

        ranking = self._ranking(candidate_results)
        accepted_count = sum(
            int(item.candidate_status == "CANDIDATE_ACCEPTED_FOR_RESEARCH")
            for item in candidate_results
        )
        rejected_count = sum(
            int(item.candidate_status == "CANDIDATE_REJECTED")
            for item in candidate_results
        )
        best_candidate = next((item for item in candidate_results if item.score is not None), None)
        failed_gates_summary = self._failed_gates_summary(candidate_results)
        recommendations = self._recommendations(
            feature_quality=diagnostics["feature_quality"],
            regime_feature_diagnostics=diagnostics["regime_feature_diagnostics"],
            leakage_guard=diagnostics["feature_leakage"],
            regime_plan=diagnostics["regime_experiment_plan"],
            regime_training_applied=regime_training_applied,
        )

        result = FeatureRegimeExperimentResult(
            experiment_id=experiment_id,
            symbol=config.symbol,
            interval=config.interval,
            start_date=config.start_date,
            end_date=end_date,
            status="ok",
            experiment_status=experiment_status,
            config_count=len(selected_base_configs),
            candidate_count=len(candidate_results),
            accepted_candidate_count=accepted_count,
            rejected_candidate_count=rejected_count,
            best_candidate_id=None if best_candidate is None else best_candidate.candidate_id,
            best_candidate_config_id=None if best_candidate is None else best_candidate.config_id,
            best_candidate_score=None if best_candidate is None else best_candidate.score,
            feature_quality_summary=diagnostics["feature_quality"],
            feature_group_quality_summary=diagnostics["feature_group_quality"],
            regime_feature_summary=diagnostics["regime_feature_diagnostics"],
            feature_leakage_summary=diagnostics["feature_leakage"],
            regime_experiment_plan_summary=diagnostics["regime_experiment_plan"],
            candidate_results=tuple(candidate_results),
            ranking=tuple(ranking),
            failed_gates_summary=failed_gates_summary,
            warnings=tuple(dict.fromkeys(warnings)),
            recommendations=tuple(recommendations),
            regime_training_applied=regime_training_applied,
            output_dir=str(logger.paths.experiment_dir),
            log_path=str(logger.paths.log_path),
            events_path=str(logger.paths.events_path),
            summary_json_path=str(logger.paths.summary_json_path),
            summary_markdown_path=str(logger.paths.summary_markdown_path),
            baseline_reference=dict(DEFAULT_ML31_BASELINE_REFERENCE),
        )

        for candidate in candidate_results:
            self._reporter.write_candidate_json(
                candidate,
                logger.paths.candidate_results_dir / f"{candidate.candidate_id}.json",
            )
            self._reporter.write_candidate_markdown(
                candidate,
                logger.paths.candidate_results_dir / f"{candidate.candidate_id}.md",
            )
        self._reporter.write_summary_json(result, logger.paths.summary_json_path)
        self._reporter.write_summary_markdown(result, logger.paths.summary_markdown_path)
        logger.event(
            event="experiment_completed",
            status="COMPLETED",
            data={
                "experiment_status": experiment_status,
                "candidate_count": len(candidate_results),
                "accepted_candidate_count": accepted_count,
                "best_candidate_config_id": result.best_candidate_config_id,
                "selected_regime_config_count": len(selected_regime_configs),
                "regime_training_applied": regime_training_applied,
            },
            message="Feature/regime experiment completed",
        )
        return result

    def _collect_diagnostics(
        self,
        *,
        config: FeatureRegimeExperimentConfig,
        rows: list[dict[str, Any]],
        logger: _ExperimentLogger,
    ) -> dict[str, dict[str, Any]]:
        logger.event(event="diagnostics_started", status="RUNNING", message="Diagnostics collection started")
        diagnostics_dir = logger.paths.diagnostics_dir
        feature_quality = (
            self._feature_quality_diagnostics.analyze(rows)
            if config.run_feature_diagnostics
            else {"diagnostic_name": "feature_quality_diagnostics", "diagnostic_skipped": True, "weak_signal_detected": False}
        )
        feature_group_quality = (
            self._feature_group_quality_scorer.analyze(rows)
            if config.run_feature_diagnostics
            else {"group_name": "feature_group_quality", "diagnostic_skipped": True}
        )
        regime_feature_diagnostics = (
            self._regime_feature_diagnostics.analyze(rows)
            if config.run_regime_diagnostics
            else {"diagnostic_name": "regime_feature_diagnostics", "diagnostic_skipped": True, "regime_data_available": False}
        )
        feature_leakage = (
            self._feature_leakage_guard.check_rows(rows)
            if config.run_leakage_guard
            else {"guard_name": "feature_leakage_guard", "diagnostic_skipped": True, "leakage_risk_detected": False}
        )
        regime_experiment_plan = self._regime_experiment_planner.build_plan(
            symbol=config.symbol,
            interval=config.interval,
            start_date=config.start_date,
            regime_data_available=bool(regime_feature_diagnostics.get("regime_data_available", False)),
            base_label_config_id=(config.base_label_config_ids[0] if config.base_label_config_ids else "lv2_h12_thr05_tp15_sl10"),
        )
        self._reporter.write_diagnostics_json(feature_quality, diagnostics_dir / "feature_quality.json")
        self._reporter.write_diagnostics_json(feature_group_quality, diagnostics_dir / "feature_group_quality.json")
        self._reporter.write_diagnostics_json(regime_feature_diagnostics, diagnostics_dir / "regime_feature_diagnostics.json")
        self._reporter.write_diagnostics_json(feature_leakage, diagnostics_dir / "feature_leakage_guard.json")
        self._reporter.write_diagnostics_json(regime_experiment_plan, diagnostics_dir / "regime_experiment_plan.json")
        logger.event(
            event="diagnostics_completed",
            status="COMPLETED",
            data={
                "feature_weak_signal_detected": feature_quality.get("weak_signal_detected"),
                "regime_data_available": regime_feature_diagnostics.get("regime_data_available"),
                "feature_leakage_risk_detected": feature_leakage.get("leakage_risk_detected"),
                "ready_for_real_regime_training": regime_experiment_plan.get("ready_for_real_regime_training"),
            },
            message="Diagnostics collection completed",
        )
        return {
            "feature_quality": feature_quality,
            "feature_group_quality": feature_group_quality,
            "regime_feature_diagnostics": regime_feature_diagnostics,
            "feature_leakage": feature_leakage,
            "regime_experiment_plan": regime_experiment_plan,
        }

    def _select_base_configs(self, config: FeatureRegimeExperimentConfig) -> list[dict[str, Any]]:
        available = self._base_grid_planner.build_grid()["configs"]
        if config.base_label_config_ids:
            selected = [item for item in available if item["config_id"] in set(config.base_label_config_ids)]
        else:
            selected = list(available)
        if config.max_configs is not None:
            selected = selected[: max(int(config.max_configs), 0)]
        return selected

    def _select_regime_configs(
        self,
        config: FeatureRegimeExperimentConfig,
        selected_base_configs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        base_id = (
            selected_base_configs[0]["config_id"]
            if selected_base_configs
            else (config.base_label_config_ids[0] if config.base_label_config_ids else "lv2_h12_thr05_tp15_sl10")
        )
        available = self._regime_label_planner.build_configs(base_label_config_id=base_id)["configs"]
        if config.regime_config_ids:
            available = [item for item in available if item["config_id"] in set(config.regime_config_ids)]
        if config.max_configs is not None:
            available = available[: max(int(config.max_configs), 0)]
        return available

    def _dry_run_candidates(
        self,
        selected_base_configs: list[dict[str, Any]],
        *,
        feature_weak_signal_detected: bool,
        feature_leakage_risk_detected: bool,
        logger: _ExperimentLogger,
    ) -> list[FeatureRegimeCandidateResult]:
        candidates: list[FeatureRegimeCandidateResult] = []
        for config_payload in selected_base_configs:
            candidate_id = f"dryrun_{config_payload['config_id']}"
            logger.event(
                event="candidate_started",
                status="RUNNING",
                candidate_id=candidate_id,
                data={"config_id": config_payload["config_id"]},
                message="Candidate dry-run started",
            )
            result = FeatureRegimeCandidateResult(
                candidate_id=candidate_id,
                config_id=str(config_payload["config_id"]),
                label_config=dict(config_payload),
                status="DRY_RUN",
                quality_status=None,
                candidate_status=None,
                score=None,
                warnings=("dry_run_no_training",),
                recommendations=("Dry-run only; no training was executed.",),
                regime_specific_training_applied=False,
                feature_weak_signal_detected=feature_weak_signal_detected,
                feature_leakage_risk_detected=feature_leakage_risk_detected,
            )
            candidates.append(result)
            logger.event(
                event="candidate_completed",
                status="COMPLETED",
                candidate_id=candidate_id,
                data={"config_id": config_payload["config_id"], "dry_run": True},
                message="Candidate dry-run completed",
            )
        return candidates

    def _sample_candidates(
        self,
        selected_base_configs: list[dict[str, Any]],
        *,
        feature_weak_signal_detected: bool,
        feature_leakage_risk_detected: bool,
        logger: _ExperimentLogger,
    ) -> list[FeatureRegimeCandidateResult]:
        candidates: list[FeatureRegimeCandidateResult] = []
        for index, config_payload in enumerate(selected_base_configs):
            candidate_id = f"sample_{config_payload['config_id']}"
            logger.event(
                event="candidate_started",
                status="RUNNING",
                candidate_id=candidate_id,
                data={"config_id": config_payload["config_id"], "sample_mode": True},
                message="Sample candidate started",
            )
            score = round(-6.10 - (index * 0.70), 6)
            failed_gates = ("collapse_gate", "walk_forward_gate") if index == 0 else ("collapse_gate", "profit_aware_gate", "gap_quality_gate")
            result = FeatureRegimeCandidateResult(
                candidate_id=candidate_id,
                config_id=str(config_payload["config_id"]),
                label_config=dict(config_payload),
                status="COMPLETED",
                quality_status="QUALITY_REJECTED",
                candidate_status="CANDIDATE_REJECTED",
                score=score,
                failed_gates=failed_gates,
                passed_gates=("baseline_edge_gate",),
                warnings=("sample_mode_result",),
                recommendations=("Sample-only candidate; use for research workflow validation only.",),
                regime_specific_training_applied=False,
                feature_weak_signal_detected=feature_weak_signal_detected,
                feature_leakage_risk_detected=feature_leakage_risk_detected,
            )
            candidates.append(result)
            logger.event(
                event="candidate_rejected",
                status="CANDIDATE_REJECTED",
                candidate_id=candidate_id,
                data={"config_id": config_payload["config_id"], "score": score},
                message="Sample candidate rejected",
            )
        return candidates

    def _real_candidates(
        self,
        *,
        config: FeatureRegimeExperimentConfig,
        experiment_id: str,
        selected_base_configs: list[dict[str, Any]],
        feature_weak_signal_detected: bool,
        feature_leakage_risk_detected: bool,
        logger: _ExperimentLogger,
        experiment_dir: Path,
    ) -> tuple[list[FeatureRegimeCandidateResult], str, list[str]]:
        if not selected_base_configs:
            return [], "COMPLETED_NO_CANDIDATES", ["no_base_configs_selected"]

        for config_payload in selected_base_configs:
            logger.event(
                event="candidate_started",
                status="RUNNING",
                candidate_id=str(config_payload["config_id"]),
                data={"config_id": config_payload["config_id"]},
                message="Real candidate started",
            )

        runtime_dir = experiment_dir / "label_grid_runtime"
        inner_result = self._label_grid_runner.run(
            LabelGridExperimentConfig(
                symbol=config.symbol,
                interval=config.interval,
                start_date=config.start_date,
                end_date=config.end_date,
                experiment_id=f"{experiment_id}_label_grid",
                label_config_ids=tuple(str(item["config_id"]) for item in selected_base_configs),
                max_configs=len(selected_base_configs),
                dry_run=False,
                sample_mode=False,
                run_training=config.run_training,
                run_walk_forward=True,
                run_gate_policy_replay=True,
                output_dir=runtime_dir,
            )
        )
        ranking_map = {
            str(item.get("config_id")): dict(item)
            for item in inner_result.candidate_ranking
        }
        candidate_results: list[FeatureRegimeCandidateResult] = []
        for item in inner_result.candidate_results:
            ranking_row = ranking_map.get(item.config_id, {})
            candidate = FeatureRegimeCandidateResult(
                candidate_id=item.config_id,
                config_id=item.config_id,
                label_config=dict(item.label_config),
                status=item.status,
                quality_status=item.quality_status,
                candidate_status=item.candidate_status,
                score=ranking_row.get("score"),
                failed_gates=tuple(item.failed_gates),
                passed_gates=tuple(item.passed_gates),
                warnings=tuple(item.warnings),
                recommendations=tuple(item.recommendations),
                regime_specific_training_applied=False,
                feature_weak_signal_detected=feature_weak_signal_detected,
                feature_leakage_risk_detected=feature_leakage_risk_detected,
            )
            candidate_results.append(candidate)
            logger.event(
                event=("candidate_accepted_for_research" if item.candidate_status == "CANDIDATE_ACCEPTED_FOR_RESEARCH" else "candidate_rejected" if item.candidate_status == "CANDIDATE_REJECTED" else "candidate_completed"),
                status=item.status,
                candidate_id=item.config_id,
                data={
                    "config_id": item.config_id,
                    "candidate_status": item.candidate_status,
                    "score": ranking_row.get("score"),
                },
                message="Real candidate completed",
            )
        return candidate_results, str(inner_result.experiment_status), ["regime_specific_training_not_applied"]

    @staticmethod
    def _ranking(candidate_results: list[FeatureRegimeCandidateResult]) -> list[dict[str, Any]]:
        scored = [item for item in candidate_results if item.score is not None]
        scored.sort(key=lambda item: float(item.score), reverse=True)
        ranking: list[dict[str, Any]] = []
        for index, item in enumerate(scored, start=1):
            ranking.append(
                {
                    "rank": index,
                    "candidate_id": item.candidate_id,
                    "config_id": item.config_id,
                    "score": item.score,
                    "candidate_status": item.candidate_status,
                    "failed_gates": list(item.failed_gates),
                }
            )
        return ranking

    @staticmethod
    def _failed_gates_summary(candidate_results: list[FeatureRegimeCandidateResult]) -> dict[str, int]:
        summary: dict[str, int] = {}
        for item in candidate_results:
            for gate in item.failed_gates:
                summary[gate] = summary.get(gate, 0) + 1
        return summary

    @staticmethod
    def _recommendations(
        *,
        feature_quality: dict[str, Any],
        regime_feature_diagnostics: dict[str, Any],
        leakage_guard: dict[str, Any],
        regime_plan: dict[str, Any],
        regime_training_applied: bool,
    ) -> list[str]:
        recommendations = list(feature_quality.get("recommendations", []))
        recommendations.extend(regime_feature_diagnostics.get("recommendations", []))
        recommendations.extend(leakage_guard.get("recommendations", []))
        recommendations.extend(regime_plan.get("recommendations", []))
        if not regime_training_applied:
            recommendations.append("Regime-specific labels are still attached as a plan, not as active label-builder integration.")
        recommendations.append("Keep traders-core, live trading, orders, and auto activation disabled.")
        return list(dict.fromkeys(str(item) for item in recommendations))

    @staticmethod
    def _build_sample_rows() -> list[dict[str, Any]]:
        return [
            {
                "direction_label": "UP",
                "features_json": {
                    "trend_strength": 1.20,
                    "ema_21_to_ema_50": 0.14,
                    "volume_ratio_20": 1.30,
                    "rsi_14": 61.0,
                    "regime_trend_up": 1.0,
                    "regime_trend_down": 0.0,
                    "regime_range": 0.0,
                    "regime_high_volatility": 0.0,
                    "regime_low_volatility": 1.0,
                },
            },
            {
                "direction_label": "UP",
                "features_json": {
                    "trend_strength": 1.05,
                    "ema_21_to_ema_50": 0.11,
                    "volume_ratio_20": 1.10,
                    "rsi_14": 58.0,
                    "regime_trend_up": 1.0,
                    "regime_trend_down": 0.0,
                    "regime_range": 0.0,
                    "regime_high_volatility": 0.0,
                    "regime_low_volatility": 1.0,
                },
            },
            {
                "direction_label": "DOWN",
                "features_json": {
                    "trend_strength": -0.95,
                    "ema_21_to_ema_50": -0.12,
                    "volume_ratio_20": 1.35,
                    "rsi_14": 38.0,
                    "regime_trend_up": 0.0,
                    "regime_trend_down": 1.0,
                    "regime_range": 0.0,
                    "regime_high_volatility": 1.0,
                    "regime_low_volatility": 0.0,
                },
            },
            {
                "direction_label": "FLAT",
                "features_json": {
                    "trend_strength": 0.05,
                    "ema_21_to_ema_50": 0.01,
                    "volume_ratio_20": None,
                    "rsi_14": 49.0,
                    "regime_trend_up": 0.0,
                    "regime_trend_down": 0.0,
                    "regime_range": 1.0,
                    "regime_high_volatility": 0.0,
                    "regime_low_volatility": 1.0,
                },
            },
            {
                "direction_label": "DOWN",
                "features_json": {
                    "trend_strength": -0.70,
                    "ema_21_to_ema_50": -0.08,
                    "volume_ratio_20": 1.05,
                    "rsi_14": 42.0,
                    "regime_trend_up": 0.0,
                    "regime_trend_down": 1.0,
                    "regime_range": 0.0,
                    "regime_high_volatility": 1.0,
                    "regime_low_volatility": 0.0,
                },
            },
            {
                "direction_label": "FLAT",
                "features_json": {
                    "trend_strength": 0.02,
                    "ema_21_to_ema_50": 0.0,
                    "volume_ratio_20": 0.95,
                    "rsi_14": 50.0,
                    "regime_trend_up": 0.0,
                    "regime_trend_down": 0.0,
                    "regime_range": 0.0,
                    "regime_high_volatility": 0.0,
                    "regime_low_volatility": 0.0,
                },
            },
        ]
