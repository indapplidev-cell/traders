from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, fields
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

from app.diagnostics.decision_policy_grid import apply_selected_decision_policy_metrics
from app.diagnostics.gap_quality_diagnostics import GapQualityDiagnostics
from app.evaluation.gap_quality_gate_normalizer import normalize_gap_quality_gate
from app.evaluation.anti_collapse_validator import AntiCollapseValidator
from app.evaluation.model_quality_validator import validate_model_quality
from app.experiments.label_grid_candidate_ranker import LabelGridCandidateRanker
from app.experiments.label_grid_experiment_reporter import LabelGridExperimentReporter
from app.features.feature_models import feature_names_for_version
from app.labels.label_quality_grid import LabelQualityGridConfig, LabelQualityGridPlanner
from app.training.training_pipeline_runner import (
    LongHistoryTrainingPipelineRunner,
    TrainingPipelineConfig,
)


LABEL_GRID_EXPERIMENT_RUNNER_NAME = "label_grid_experiment_runner"
LABEL_GRID_EXPERIMENT_RUNNER_VERSION = "ml28"
LABEL_QUALITY_GRID_CONFIG_FIELD_NAMES = {item.name for item in fields(LabelQualityGridConfig)}


@dataclass(frozen=True, slots=True)
class LabelGridExperimentConfig:
    symbol: str
    interval: str
    start_date: str
    end_date: str | None = None
    experiment_id: str | None = None
    feature_version: str = "fv1"
    label_config_ids: tuple[str, ...] = ()
    max_configs: int | None = None
    dry_run: bool = False
    sample_mode: bool = False
    run_training: bool = True
    run_walk_forward: bool = True
    run_gate_policy_replay: bool = True
    output_dir: Path = Path("reports/label_grid_experiments")
    skip_candle_load: bool = False

    def resolved_end_date(self) -> str:
        if self.end_date is not None:
            return self.end_date
        return date.today().isoformat()

    def resolved_experiment_id(self) -> str:
        if self.experiment_id is not None:
            return self.experiment_id
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        start = self.start_date.replace("-", "")
        end = self.resolved_end_date().replace("-", "")
        return f"label_grid_{self.symbol}_{self.interval}_{start}_{end}_{timestamp}"


@dataclass(frozen=True, slots=True)
class LabelGridExperimentCandidateResult:
    config_id: str
    label_config: dict[str, Any]
    status: str
    quality_status: str | None
    candidate_status: str | None
    raw_candidate_status: str | None
    model_version: str | None
    training_run_id: str | None
    dataset_rows: int
    train_rows: int
    val_rows: int
    test_rows: int
    class_distribution: dict[str, Any] = field(default_factory=dict)
    actual_distribution: dict[str, Any] = field(default_factory=dict)
    predicted_distribution: dict[str, Any] = field(default_factory=dict)
    model_accuracy: float | None = None
    baseline_accuracy: float | None = None
    accuracy_edge: float | None = None
    collapse_detected: bool = False
    collapse_type: str | None = None
    feature_version_used: str | None = None
    gap_severity: str | None = None
    gap_count: int = 0
    gap_severity_for_training: str | None = None
    effective_gap_count_for_training: int = 0
    gap_training_safe: bool | None = None
    profit_total_r: float | None = None
    profit_factor: float | None = None
    walk_forward_fold_count: int = 0
    walk_forward_global_total_r: float | None = None
    walk_forward_profit_factor: float | None = None
    gate_policy_allowed_count: int = 0
    gate_policy_blocked_count: int = 0
    failed_gates: tuple[str, ...] = ()
    passed_gates: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()
    probability_diagnostics: dict[str, Any] = field(default_factory=dict)
    probability_diagnostics_missing_reason: str | None = None
    collapse_diagnostics_v2: dict[str, Any] = field(default_factory=dict)
    collapse_diagnostics_v2_missing_reason: str | None = None
    calibrated_decision_diagnostics: dict[str, Any] = field(default_factory=dict)
    bounded_calibrated_decision_selection: dict[str, Any] = field(default_factory=dict)
    decision_policy_grid_diagnostics: dict[str, Any] = field(default_factory=dict)
    decision_policy_selected_policy_id: str | None = None
    prediction_root_cause_audit: dict[str, Any] = field(default_factory=dict)
    book_driven_forensic_audit: dict[str, Any] = field(default_factory=dict)
    label_mode_comparison_audit: dict[str, Any] = field(default_factory=dict)
    flat_subtype_audit: dict[str, Any] = field(default_factory=dict)
    setup_aware_label_diagnostics: dict[str, Any] = field(default_factory=dict)
    schwager_slice_robustness: dict[str, Any] = field(default_factory=dict)
    schwager_robustness_decision_board: dict[str, Any] = field(default_factory=dict)
    class_margin_objective_decision: dict[str, Any] = field(default_factory=dict)
    raw_predicted_class_distribution: dict[str, Any] = field(default_factory=dict)
    calibrated_predicted_class_distribution: dict[str, Any] = field(default_factory=dict)
    raw_collapse_diagnostics_v2: dict[str, Any] = field(default_factory=dict)
    prediction_decision_source: str | None = None
    regime_label_builder_status: dict[str, Any] = field(default_factory=dict)
    regime_label_builder_status_missing_reason: str | None = None
    walk_forward_profit_diagnostics: dict[str, Any] = field(default_factory=dict)
    walk_forward_profit_diagnostics_missing_reason: str | None = None
    profit_aware_diagnostics: dict[str, Any] = field(default_factory=dict)
    profit_aware_diagnostics_missing_reason: str | None = None
    opportunity_probability_threshold: float | None = None
    setup_quality_min_threshold: float | None = None
    setup_quality_decision_mask_enabled: bool = False
    setup_quality_decision_mask_min_threshold: float | None = None
    selected_opportunity_threshold: float | None = None
    opportunity_threshold_selection: dict[str, Any] = field(default_factory=dict)
    opportunity_threshold_sweep: dict[str, Any] = field(default_factory=dict)
    setup_quality_filter_passed: bool = False
    setup_quality_bucket_metrics: dict[str, Any] = field(default_factory=dict)
    setup_quality_bucket_metrics_raw: dict[str, Any] = field(default_factory=dict)
    setup_quality_bucket_metrics_after_mask: dict[str, Any] = field(default_factory=dict)
    setup_quality_filter_summary: dict[str, Any] = field(default_factory=dict)
    setup_quality_decision_mask_summary: dict[str, Any] = field(default_factory=dict)
    entry_path_quality_filter_enabled: bool = False
    entry_path_quality_min_threshold: float | None = None
    stop_pressure_max_risk_score: float | None = None
    mae_pressure_max_risk_score: float | None = None
    entry_path_quality_masked_row_count: int = 0
    entry_path_quality_forced_no_trade_count: int = 0
    entry_path_quality_mask_trade_prediction_removed_count: int = 0
    entry_path_quality_mask_false_positive_removed_count: int = 0
    entry_path_quality_filter_summary: dict[str, Any] = field(default_factory=dict)
    entry_path_quality_filter_diagnostics: dict[str, Any] = field(default_factory=dict)
    entry_path_prediction_filter_summary: dict[str, Any] = field(default_factory=dict)
    stop_pressure_effectiveness_audit: dict[str, Any] = field(default_factory=dict)
    predicted_to_actual_trade_rate_ratio: float | None = None
    predicted_trade_rate: float | None = None
    raw_predicted_trade_rate: float | None = None
    masked_predicted_trade_rate: float | None = None
    actual_trade_rate: float | None = None
    opportunity_precision: float | None = None
    opportunity_recall: float | None = None
    opportunity_f1: float | None = None
    raw_opportunity_precision: float | None = None
    raw_opportunity_recall: float | None = None
    raw_opportunity_f1: float | None = None
    opportunity_false_positive_rate: float | None = None
    two_stage_trade_diagnostics: dict[str, Any] = field(default_factory=dict)
    approved_for_traders_core_integration: bool = False
    approved_for_live_trading: bool = False
    approved_for_auto_activation: bool = False
    orders_enabled: bool = False
    traders_core_connected: bool = False
    model_quality_validation_status: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_id": self.config_id,
            "label_config": dict(self.label_config),
            "status": self.status,
            "quality_status": self.quality_status,
            "candidate_status": self.candidate_status,
            "raw_candidate_status": self.raw_candidate_status,
            "model_version": self.model_version,
            "training_run_id": self.training_run_id,
            "dataset_rows": self.dataset_rows,
            "train_rows": self.train_rows,
            "val_rows": self.val_rows,
            "test_rows": self.test_rows,
            "class_distribution": dict(self.class_distribution),
            "actual_distribution": dict(self.actual_distribution),
            "predicted_distribution": dict(self.predicted_distribution),
            "model_accuracy": self.model_accuracy,
            "baseline_accuracy": self.baseline_accuracy,
            "accuracy_edge": self.accuracy_edge,
            "collapse_detected": self.collapse_detected,
            "collapse_type": self.collapse_type,
            "feature_version_used": self.feature_version_used,
            "gap_severity": self.gap_severity,
            "gap_count": self.gap_count,
            "gap_severity_for_training": self.gap_severity_for_training,
            "effective_gap_count_for_training": self.effective_gap_count_for_training,
            "gap_training_safe": self.gap_training_safe,
            "profit_total_r": self.profit_total_r,
            "profit_factor": self.profit_factor,
            "walk_forward_fold_count": self.walk_forward_fold_count,
            "walk_forward_global_total_r": self.walk_forward_global_total_r,
            "walk_forward_profit_factor": self.walk_forward_profit_factor,
            "gate_policy_allowed_count": self.gate_policy_allowed_count,
            "gate_policy_blocked_count": self.gate_policy_blocked_count,
            "failed_gates": list(self.failed_gates),
            "passed_gates": list(self.passed_gates),
            "warnings": list(self.warnings),
            "recommendations": list(self.recommendations),
            "probability_diagnostics": dict(self.probability_diagnostics),
            "probability_diagnostics_missing_reason": self.probability_diagnostics_missing_reason,
            "collapse_diagnostics_v2": dict(self.collapse_diagnostics_v2),
            "collapse_diagnostics_v2_missing_reason": self.collapse_diagnostics_v2_missing_reason,
            "calibrated_decision_diagnostics": dict(self.calibrated_decision_diagnostics),
            "bounded_calibrated_decision_selection": dict(self.bounded_calibrated_decision_selection),
            "decision_policy_grid_diagnostics": dict(self.decision_policy_grid_diagnostics),
            "decision_policy_selected_policy_id": self.decision_policy_selected_policy_id,
            "prediction_root_cause_audit": dict(self.prediction_root_cause_audit),
            "book_driven_forensic_audit": dict(self.book_driven_forensic_audit),
            "label_mode_comparison_audit": dict(self.label_mode_comparison_audit),
            "flat_subtype_audit": dict(self.flat_subtype_audit),
            "setup_aware_label_diagnostics": dict(self.setup_aware_label_diagnostics),
            "schwager_slice_robustness": dict(self.schwager_slice_robustness),
            "schwager_robustness_decision_board": dict(self.schwager_robustness_decision_board),
            "class_margin_objective_decision": dict(self.class_margin_objective_decision),
            "raw_predicted_class_distribution": dict(self.raw_predicted_class_distribution),
            "calibrated_predicted_class_distribution": dict(self.calibrated_predicted_class_distribution),
            "raw_collapse_diagnostics_v2": dict(self.raw_collapse_diagnostics_v2),
            "prediction_decision_source": self.prediction_decision_source,
            "regime_label_builder_status": dict(self.regime_label_builder_status),
            "regime_label_builder_status_missing_reason": self.regime_label_builder_status_missing_reason,
            "walk_forward_profit_diagnostics": dict(self.walk_forward_profit_diagnostics),
            "walk_forward_profit_diagnostics_missing_reason": self.walk_forward_profit_diagnostics_missing_reason,
            "profit_aware_diagnostics": dict(self.profit_aware_diagnostics),
            "profit_aware_diagnostics_missing_reason": self.profit_aware_diagnostics_missing_reason,
            "opportunity_probability_threshold": self.opportunity_probability_threshold,
            "setup_quality_min_threshold": self.setup_quality_min_threshold,
            "setup_quality_decision_mask_enabled": self.setup_quality_decision_mask_enabled,
            "setup_quality_decision_mask_min_threshold": self.setup_quality_decision_mask_min_threshold,
            "selected_opportunity_threshold": self.selected_opportunity_threshold,
            "opportunity_threshold_selection": dict(self.opportunity_threshold_selection),
            "opportunity_threshold_sweep": dict(self.opportunity_threshold_sweep),
            "setup_quality_filter_passed": self.setup_quality_filter_passed,
            "setup_quality_bucket_metrics": dict(self.setup_quality_bucket_metrics),
            "setup_quality_bucket_metrics_raw": dict(self.setup_quality_bucket_metrics_raw),
            "setup_quality_bucket_metrics_after_mask": dict(self.setup_quality_bucket_metrics_after_mask),
            "setup_quality_filter_summary": dict(self.setup_quality_filter_summary),
            "setup_quality_decision_mask_summary": dict(self.setup_quality_decision_mask_summary),
            "entry_path_quality_filter_enabled": self.entry_path_quality_filter_enabled,
            "entry_path_quality_min_threshold": self.entry_path_quality_min_threshold,
            "stop_pressure_max_risk_score": self.stop_pressure_max_risk_score,
            "mae_pressure_max_risk_score": self.mae_pressure_max_risk_score,
            "entry_path_quality_masked_row_count": self.entry_path_quality_masked_row_count,
            "entry_path_quality_forced_no_trade_count": self.entry_path_quality_forced_no_trade_count,
            "entry_path_quality_mask_trade_prediction_removed_count": self.entry_path_quality_mask_trade_prediction_removed_count,
            "entry_path_quality_mask_false_positive_removed_count": self.entry_path_quality_mask_false_positive_removed_count,
            "entry_path_quality_filter_summary": dict(self.entry_path_quality_filter_summary),
            "entry_path_quality_filter_diagnostics": dict(self.entry_path_quality_filter_diagnostics),
            "entry_path_prediction_filter_summary": dict(self.entry_path_prediction_filter_summary),
            "stop_pressure_effectiveness_audit": dict(self.stop_pressure_effectiveness_audit),
            "predicted_to_actual_trade_rate_ratio": self.predicted_to_actual_trade_rate_ratio,
            "predicted_trade_rate": self.predicted_trade_rate,
            "raw_predicted_trade_rate": self.raw_predicted_trade_rate,
            "masked_predicted_trade_rate": self.masked_predicted_trade_rate,
            "actual_trade_rate": self.actual_trade_rate,
            "opportunity_precision": self.opportunity_precision,
            "opportunity_recall": self.opportunity_recall,
            "opportunity_f1": self.opportunity_f1,
            "raw_opportunity_precision": self.raw_opportunity_precision,
            "raw_opportunity_recall": self.raw_opportunity_recall,
            "raw_opportunity_f1": self.raw_opportunity_f1,
            "opportunity_false_positive_rate": self.opportunity_false_positive_rate,
            "two_stage_trade_diagnostics": dict(self.two_stage_trade_diagnostics),
            "approved_for_traders_core_integration": self.approved_for_traders_core_integration,
            "approved_for_live_trading": self.approved_for_live_trading,
            "approved_for_auto_activation": self.approved_for_auto_activation,
            "orders_enabled": self.orders_enabled,
            "traders_core_connected": self.traders_core_connected,
            "model_quality_validation_status": self.model_quality_validation_status,
        }


@dataclass(frozen=True, slots=True)
class LabelGridExperimentRunResult:
    status: str
    experiment_status: str
    experiment_id: str
    symbol: str
    interval: str
    start_date: str
    end_date: str
    dry_run: bool
    sample_mode: bool
    config_count: int
    completed_candidate_count: int
    evaluated_candidate_count: int
    failed_candidate_count: int
    accepted_candidate_count: int
    rejected_candidate_count: int
    best_candidate_config_id: str | None
    best_candidate_status: str | None
    best_candidate_score: float | None
    feature_version_used: str | None
    output_dir: str
    log_path: str
    events_path: str
    summary_json_path: str
    summary_markdown_path: str
    candidate_results_dir: str
    candidate_results: tuple[LabelGridExperimentCandidateResult, ...]
    candidate_ranking: tuple[dict[str, Any], ...]
    failed_gates_summary: dict[str, int]
    collapse_summary: dict[str, int]
    profit_summary: dict[str, Any]
    walk_forward_summary: dict[str, Any]
    gap_quality_summary: dict[str, Any]
    recommendations: tuple[str, ...]
    approved_for_live_trading: bool = False
    approved_for_auto_activation: bool = False
    orders_enabled: bool = False
    traders_core_connected: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "experiment_status": self.experiment_status,
            "experiment_id": self.experiment_id,
            "symbol": self.symbol,
            "interval": self.interval,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "dry_run": self.dry_run,
            "sample_mode": self.sample_mode,
            "config_count": self.config_count,
            "completed_candidate_count": self.completed_candidate_count,
            "evaluated_candidate_count": self.evaluated_candidate_count,
            "failed_candidate_count": self.failed_candidate_count,
            "accepted_candidate_count": self.accepted_candidate_count,
            "rejected_candidate_count": self.rejected_candidate_count,
            "best_candidate_config_id": self.best_candidate_config_id,
            "best_candidate_status": self.best_candidate_status,
            "best_candidate_score": self.best_candidate_score,
            "feature_version_used": self.feature_version_used,
            "output_dir": self.output_dir,
            "log_path": self.log_path,
            "events_path": self.events_path,
            "summary_json_path": self.summary_json_path,
            "summary_markdown_path": self.summary_markdown_path,
            "candidate_results_dir": self.candidate_results_dir,
            "candidate_results": [item.to_dict() for item in self.candidate_results],
            "candidate_ranking": [dict(item) for item in self.candidate_ranking],
            "failed_gates_summary": dict(self.failed_gates_summary),
            "collapse_summary": dict(self.collapse_summary),
            "profit_summary": dict(self.profit_summary),
            "walk_forward_summary": dict(self.walk_forward_summary),
            "gap_quality_summary": dict(self.gap_quality_summary),
            "recommendations": list(self.recommendations),
            "approved_for_live_trading": self.approved_for_live_trading,
            "approved_for_auto_activation": self.approved_for_auto_activation,
            "orders_enabled": self.orders_enabled,
            "traders_core_connected": self.traders_core_connected,
        }


@dataclass(frozen=True)
class _ExperimentLogPaths:
    experiment_dir: Path
    log_path: Path
    events_path: Path
    summary_json_path: Path
    summary_markdown_path: Path
    candidate_results_dir: Path


class _ExperimentLogger:
    def __init__(self, *, experiment_id: str, output_dir: Path | str) -> None:
        root = Path(output_dir)
        experiment_dir = root / experiment_id
        experiment_dir.mkdir(parents=True, exist_ok=True)
        candidate_results_dir = experiment_dir / "candidate_results"
        candidate_results_dir.mkdir(parents=True, exist_ok=True)
        self._experiment_id = experiment_id
        self._paths = _ExperimentLogPaths(
            experiment_dir=experiment_dir,
            log_path=experiment_dir / "label_grid_experiment.log",
            events_path=experiment_dir / "label_grid_experiment_events.jsonl",
            summary_json_path=experiment_dir / "label_grid_experiment_summary.json",
            summary_markdown_path=experiment_dir / "label_grid_experiment_summary.md",
            candidate_results_dir=candidate_results_dir,
        )

    @property
    def paths(self) -> _ExperimentLogPaths:
        return self._paths

    def event(
        self,
        *,
        config_id: str | None,
        event: str,
        status: str,
        data: dict[str, Any] | None = None,
        level: str = "INFO",
        message: str | None = None,
    ) -> None:
        timestamp = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
        event_payload = {
            "timestamp": timestamp,
            "experiment_id": self._experiment_id,
            "config_id": config_id,
            "event": event,
            "status": status,
            "data": data or {},
        }
        with self._paths.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event_payload, ensure_ascii=False, sort_keys=True))
            handle.write("\n")

        human_timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        config_part = f" config_id={config_id}" if config_id else ""
        message_part = f" message={message}" if message else ""
        detail_part = ""
        if data:
            detail_part = " " + " ".join(f"{key}={value}" for key, value in data.items())
        with self._paths.log_path.open("a", encoding="utf-8") as handle:
            handle.write(
                f"[{human_timestamp}] [{level}] experiment_id={self._experiment_id}{config_part} "
                f"status={status} event={event}{message_part}{detail_part}\n"
            )


class LabelGridExperimentRunner:
    DEFAULT_FEATURE_VERSION = LongHistoryTrainingPipelineRunner.DEFAULT_FEATURE_VERSION
    DEFAULT_MODEL_NAME = LongHistoryTrainingPipelineRunner.DEFAULT_MODEL_NAME

    def __init__(
        self,
        *,
        grid_planner: LabelQualityGridPlanner | None = None,
        reporter: LabelGridExperimentReporter | None = None,
        ranker: LabelGridCandidateRanker | None = None,
        candidate_executor: Callable[
            [LabelGridExperimentConfig, LabelQualityGridConfig, Path],
            LabelGridExperimentCandidateResult,
        ]
        | None = None,
    ) -> None:
        self._grid_planner = grid_planner or LabelQualityGridPlanner()
        self._reporter = reporter or LabelGridExperimentReporter()
        self._ranker = ranker or LabelGridCandidateRanker()
        self._candidate_executor = candidate_executor

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}

    @staticmethod
    def _as_list(value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return list(value)
        if isinstance(value, (tuple, set)):
            return list(value)
        return [value]

    @classmethod
    def _string_list(cls, value: Any) -> list[str]:
        return [str(item) for item in cls._as_list(value) if item is not None]

    def build_preview(self) -> dict[str, Any]:
        payload = self._grid_planner.build_grid()
        return {
            "runner_name": LABEL_GRID_EXPERIMENT_RUNNER_NAME,
            "runner_version": LABEL_GRID_EXPERIMENT_RUNNER_VERSION,
            "status": "ok",
            "feature_version_default": self.DEFAULT_FEATURE_VERSION,
            "available_label_configs": payload["configs"],
            "estimated_experiment_plan": {
                "config_count": payload["config_count"],
                "stages": [
                    "build_labels",
                    "build_dataset",
                    "train_model",
                    "probability_diagnostics",
                    "baseline_compare",
                    "profit_aware_evaluation",
                    "walk_forward_evaluation",
                    "gate_policy_replay_evaluation",
                    "model_quality_validation",
                    "candidate_selection",
                ],
            },
            "safety_flags": {
                "approved_for_live_trading": False,
                "approved_for_auto_activation": False,
                "orders_enabled": False,
                "traders_core_connected": False,
            },
        }

    def run(self, config: LabelGridExperimentConfig) -> LabelGridExperimentRunResult:
        feature_names_for_version(config.feature_version)
        experiment_id = config.resolved_experiment_id()
        end_date = config.resolved_end_date()
        logger = _ExperimentLogger(experiment_id=experiment_id, output_dir=config.output_dir)
        selected_configs = self._select_configs(config)

        logger.event(
            config_id=None,
            event="experiment_started",
            status="RUNNING",
            data={
                "symbol": config.symbol,
                "interval": config.interval,
                "start_date": config.start_date,
                "end_date": end_date,
                "config_count": len(selected_configs),
                "dry_run": config.dry_run,
                "sample_mode": config.sample_mode,
            },
            message="Label grid experiment started",
        )

        candidate_results: list[LabelGridExperimentCandidateResult] = []
        failed = False

        for index, label_config in enumerate(selected_configs):
            logger.event(
                config_id=label_config.config_id,
                event="candidate_started",
                status="RUNNING",
                data={"position": index + 1, "config_id": label_config.config_id},
                message="Candidate execution started",
            )
            try:
                result = self._execute_candidate(
                    config,
                    label_config,
                    logger.paths.experiment_dir,
                    experiment_id,
                )
            except Exception as exc:
                failed = True
                result = LabelGridExperimentCandidateResult(
                    config_id=label_config.config_id,
                    label_config=label_config.to_dict(),
                    status="FAILED",
                    quality_status=None,
                    candidate_status="FAILED",
                    raw_candidate_status="FAILED",
                    model_version=None,
                    training_run_id=None,
                    dataset_rows=0,
                    train_rows=0,
                    val_rows=0,
                    test_rows=0,
                    warnings=(str(exc),),
                    recommendations=("Inspect candidate failure before retrying the experiment.",),
                )
                logger.event(
                    config_id=label_config.config_id,
                    event="candidate_failed",
                    status="FAILED",
                    data={"error": str(exc)},
                    level="ERROR",
                    message="Candidate execution failed",
                )
            else:
                logger.event(
                    config_id=label_config.config_id,
                    event="candidate_completed",
                    status=result.status,
                    data=self._event_metrics(result),
                    message="Candidate execution completed",
                )
                terminal_event = (
                    "candidate_accepted_for_research"
                    if result.candidate_status == "ACCEPTED"
                    else "candidate_failed"
                    if result.candidate_status == "FAILED"
                    else "candidate_rejected"
                )
                logger.event(
                    config_id=label_config.config_id,
                    event=terminal_event,
                    status=result.candidate_status or result.status,
                    data=self._event_metrics(result),
                    message="Candidate terminal decision recorded",
                )

            candidate_results.append(result)
            if result.status == "FAILED":
                failed = True
            candidate_json_path = logger.paths.candidate_results_dir / f"{label_config.config_id}.json"
            candidate_md_path = logger.paths.candidate_results_dir / f"{label_config.config_id}.md"
            self._reporter.write_candidate_json(result, candidate_json_path)
            self._reporter.write_candidate_markdown(result, candidate_md_path)

        ranking_payload = self._ranker.rank(
            self._ranking_candidates_payload(
                [item for item in candidate_results if item.status == "COMPLETED"]
            )
        )
        ranking_rows = self._normalize_ranking_rows(ranking_payload.get("ranking", []))
        experiment_status = self._resolve_experiment_status(
            config=config,
            ranking_payload=ranking_payload,
            candidate_results=candidate_results,
            failed=failed,
        )
        best_candidate = ranking_payload.get("best_candidate") or {}
        failed_gates_summary = self._failed_gates_summary(candidate_results)
        collapse_summary = self._collapse_summary(candidate_results)
        profit_summary = self._profit_summary(candidate_results)
        walk_forward_summary = self._walk_summary(candidate_results)
        gap_quality_summary = self._gap_summary(candidate_results)
        recommendations = self._recommendations(
            config=config,
            experiment_status=experiment_status,
            candidate_results=candidate_results,
        )

        result = LabelGridExperimentRunResult(
            status="failed" if experiment_status == "FAILED" else "ok",
            experiment_status=experiment_status,
            experiment_id=experiment_id,
            symbol=config.symbol,
            interval=config.interval,
            start_date=config.start_date,
            end_date=end_date,
            dry_run=config.dry_run,
            sample_mode=config.sample_mode,
            config_count=len(selected_configs),
            completed_candidate_count=sum(int(item.status == "COMPLETED") for item in candidate_results),
            evaluated_candidate_count=sum(
                int(item.candidate_status in {"ACCEPTED", "REJECTED", "FAILED"})
                for item in candidate_results
            ),
            failed_candidate_count=sum(
                int(item.candidate_status == "FAILED") for item in candidate_results
            ),
            accepted_candidate_count=sum(
                int(item.candidate_status == "ACCEPTED")
                for item in candidate_results
            ),
            rejected_candidate_count=sum(
                int(item.candidate_status == "REJECTED")
                for item in candidate_results
            ),
            best_candidate_config_id=best_candidate.get("config_id"),
            best_candidate_status=self._normalize_final_candidate_status(
                best_candidate.get("candidate_status"),
                status="COMPLETED",
            ),
            best_candidate_score=best_candidate.get("score"),
            feature_version_used=config.feature_version,
            output_dir=str(logger.paths.experiment_dir),
            log_path=str(logger.paths.log_path),
            events_path=str(logger.paths.events_path),
            summary_json_path=str(logger.paths.summary_json_path),
            summary_markdown_path=str(logger.paths.summary_markdown_path),
            candidate_results_dir=str(logger.paths.candidate_results_dir),
            candidate_results=tuple(candidate_results),
            candidate_ranking=tuple(ranking_rows),
            failed_gates_summary=failed_gates_summary,
            collapse_summary=collapse_summary,
            profit_summary=profit_summary,
            walk_forward_summary=walk_forward_summary,
            gap_quality_summary=gap_quality_summary,
            recommendations=tuple(recommendations),
            approved_for_live_trading=False,
            approved_for_auto_activation=False,
            orders_enabled=False,
            traders_core_connected=False,
        )

        self._reporter.write_json_summary(result)
        self._reporter.write_markdown_summary(result)

        logger.event(
            config_id=None,
            event="experiment_completed" if experiment_status != "FAILED" else "experiment_failed",
            status=experiment_status,
            data={
                "accepted_candidate_count": result.accepted_candidate_count,
                "rejected_candidate_count": result.rejected_candidate_count,
                "failed_candidate_count": result.failed_candidate_count,
                "evaluated_candidate_count": result.evaluated_candidate_count,
                "best_candidate_config_id": result.best_candidate_config_id,
            },
            level="ERROR" if experiment_status == "FAILED" else "INFO",
            message="Label grid experiment finished",
        )
        return result

    def _select_configs(self, config: LabelGridExperimentConfig) -> list[LabelQualityGridConfig]:
        payload = self._grid_planner.build_grid()
        configs = [
            LabelQualityGridConfig(
                **{key: value for key, value in item.items() if key in LABEL_QUALITY_GRID_CONFIG_FIELD_NAMES}
            )
            for item in payload["configs"]
        ]
        if config.label_config_ids:
            requested = set(config.label_config_ids)
            configs = [item for item in configs if item.config_id in requested]
            missing = sorted(requested - {item.config_id for item in configs})
            if missing:
                raise ValueError(f"unknown label_config_ids: {', '.join(missing)}")
        if config.max_configs is not None:
            configs = configs[: max(int(config.max_configs), 0)]
        return configs

    def _execute_candidate(
        self,
        config: LabelGridExperimentConfig,
        label_config: LabelQualityGridConfig,
        experiment_dir: Path,
        experiment_id: str,
    ) -> LabelGridExperimentCandidateResult:
        if self._candidate_executor is not None:
            return self._candidate_executor(config, label_config, experiment_dir)
        if config.dry_run:
            return LabelGridExperimentCandidateResult(
                config_id=label_config.config_id,
                label_config=label_config.to_dict(),
                status="PLANNED",
                quality_status=None,
                candidate_status="PLANNED",
                raw_candidate_status="PLANNED",
                model_version=None,
                training_run_id=None,
                dataset_rows=0,
                train_rows=0,
                val_rows=0,
                test_rows=0,
                warnings=("dry_run_true",),
                recommendations=("Run sample-mode or real execution to score this candidate.",),
            )
        if config.sample_mode:
            return self._sample_candidate_result(config, label_config)
        if not config.run_training:
            return LabelGridExperimentCandidateResult(
                config_id=label_config.config_id,
                label_config=label_config.to_dict(),
                status="PLANNED",
                quality_status=None,
                candidate_status="PLANNED",
                raw_candidate_status="PLANNED",
                model_version=None,
                training_run_id=None,
                dataset_rows=0,
                train_rows=0,
                val_rows=0,
                test_rows=0,
                warnings=("run_training_false",),
                recommendations=("Enable run_training to produce a scored research candidate.",),
            )
        return self._real_candidate_result(config, label_config, experiment_dir, experiment_id)

    def _sample_candidate_result(
        self,
        config: LabelGridExperimentConfig,
        label_config: LabelQualityGridConfig,
    ) -> LabelGridExperimentCandidateResult:
        index = sum(ord(char) for char in label_config.config_id) % 3
        model_accuracy = [0.381, 0.404, 0.372][index]
        baseline_accuracy = [0.377, 0.389, 0.376][index]
        gap_count = [0, 2, 1][index]
        profit_total_r = [-12.5, 24.0, 3.0][index]
        profit_factor = [0.94, 1.14, 1.01][index]
        walk_total_r = [-4.0, 9.5, -1.0][index]
        walk_profit_factor = [0.97, 1.06, 0.99][index]
        gate_policy_status = "SAMPLE_ONLY" if config.run_gate_policy_replay else "DISABLED"
        probability_diagnostics = [
            {
                "actual_direction_counts": {"UP": 390, "DOWN": 340, "FLAT": 270},
                "predicted_direction_counts": {"UP": 910, "DOWN": 50, "FLAT": 40},
                "avg_prob_up": 0.74,
                "avg_prob_down": 0.13,
                "avg_prob_flat": 0.13,
                "max_prob_q90": 0.88,
                "max_prob_q50": 0.74,
                "rows_above_thresholds": {"0.45": 910},
                "margin_q90": 0.49,
                "margin_q50": 0.32,
            },
            {
                "actual_direction_counts": {"UP": 360, "DOWN": 330, "FLAT": 310},
                "predicted_direction_counts": {"UP": 355, "DOWN": 325, "FLAT": 320},
                "avg_prob_up": 0.37,
                "avg_prob_down": 0.34,
                "avg_prob_flat": 0.29,
                "max_prob_q90": 0.55,
                "max_prob_q50": 0.39,
                "rows_above_thresholds": {"0.45": 190},
                "margin_q90": 0.18,
                "margin_q50": 0.06,
            },
            {
                "actual_direction_counts": {"UP": 365, "DOWN": 335, "FLAT": 300},
                "predicted_direction_counts": {"UP": 460, "DOWN": 280, "FLAT": 260},
                "avg_prob_up": 0.44,
                "avg_prob_down": 0.29,
                "avg_prob_flat": 0.27,
                "max_prob_q90": 0.61,
                "max_prob_q50": 0.41,
                "rows_above_thresholds": {"0.45": 240},
                "margin_q90": 0.16,
                "margin_q50": 0.04,
            },
        ][index]
        anti_collapse = AntiCollapseValidator().validate_probability_report(probability_diagnostics)
        quality = validate_model_quality(
            training_summary={
                "model_version": f"ml28_sample_{label_config.config_id}",
                "run_id": f"sample_training_{label_config.config_id}",
                "dataset_summary": {
                    "dataset_rows": 1000,
                    "train_rows": 700,
                    "validation_rows": 150,
                    "test_rows": 150,
                },
                "test_metrics": {"accuracy": model_accuracy},
                "sample_mode": False,
                "real_training_executed": True,
            },
            baseline_summary={
                "baseline_accuracy": baseline_accuracy,
            },
            probability_diagnostics=probability_diagnostics,
            calibration_summary={
                "calibration_status": "ACCEPTABLE",
                "expected_calibration_error": 0.06,
                "brier_score": 0.61,
            },
            profit_aware_summary={
                "profit_aware_status": "POSITIVE" if profit_total_r > 0.0 else "NEGATIVE",
                "summary": {
                    "total_r": profit_total_r,
                    "profit_factor": profit_factor,
                },
            },
            walk_forward_summary={
                "walk_forward_status": (
                    "STABLE" if config.run_walk_forward and walk_total_r > 0.0 else "UNSTABLE"
                ),
                "summary": {
                    "fold_count": 6,
                    "profitable_fold_ratio": 0.67 if walk_total_r > 0.0 else 0.33,
                    "global_total_r": walk_total_r,
                    "global_profit_factor": walk_profit_factor,
                    "total_test_signal_count": 240,
                },
            },
            gate_policy_replay_summary={
                "gate_policy_replay_status": gate_policy_status,
                "total_records": 5 if gate_policy_status == "SAMPLE_ONLY" else 0,
                "valid_records": 4 if gate_policy_status == "SAMPLE_ONLY" else 0,
                "invalid_records": 1 if gate_policy_status == "SAMPLE_ONLY" else 0,
                "gate_policy_allowed_count": 2 if gate_policy_status == "SAMPLE_ONLY" else 0,
                "gate_policy_blocked_count": 3 if gate_policy_status == "SAMPLE_ONLY" else 0,
            },
            gap_quality_summary=GapQualityDiagnostics().analyze(
                symbol=config.symbol,
                interval=config.interval,
                start_date=config.start_date,
                end_date=config.resolved_end_date(),
                gap_count=gap_count,
            ),
            anti_collapse_summary=anti_collapse,
            label_config_summary={
                "label_version": label_config.label_version,
                "horizon_candles": label_config.horizon,
                "direction_atr_threshold": label_config.threshold,
                "take_profit_atr": label_config.take_profit_atr,
                "stop_loss_atr": label_config.stop_loss_atr,
                "flat_class_enabled": True,
                "label_mode": label_config.label_mode,
            },
            feature_config_summary={
                "feature_version": config.feature_version,
                "model_name": self.DEFAULT_MODEL_NAME,
            },
            symbol=config.symbol,
        )
        quality_payload = quality.to_dict()
        return self._build_candidate_result(
            label_config=label_config,
            quality_payload=quality_payload,
            class_distribution={
                "UP": probability_diagnostics["actual_direction_counts"]["UP"],
                "DOWN": probability_diagnostics["actual_direction_counts"]["DOWN"],
                "FLAT": probability_diagnostics["actual_direction_counts"]["FLAT"],
            },
            gate_policy_summary={
                "gate_policy_allowed_count": 2 if gate_policy_status == "SAMPLE_ONLY" else 0,
                "gate_policy_blocked_count": 3 if gate_policy_status == "SAMPLE_ONLY" else 0,
            },
            extra_warnings=("sample_mode_candidate",),
        )

    def _real_candidate_result(
        self,
        config: LabelGridExperimentConfig,
        label_config: LabelQualityGridConfig,
        experiment_dir: Path,
        experiment_id: str,
    ) -> LabelGridExperimentCandidateResult:
        candidate_runtime_dir = experiment_dir / "pipeline_runs"
        candidate_runtime_dir.mkdir(parents=True, exist_ok=True)
        pipeline_runner = LongHistoryTrainingPipelineRunner()
        pipeline_runner.DEFAULT_FEATURE_VERSION = self.DEFAULT_FEATURE_VERSION
        pipeline_runner.DEFAULT_MODEL_NAME = self.DEFAULT_MODEL_NAME
        pipeline_runner.DEFAULT_LABEL_VERSION = label_config.label_version
        pipeline_runner.DEFAULT_DIRECTION_ATR_THRESHOLD = label_config.threshold
        pipeline_runner.DEFAULT_TAKE_PROFIT_ATR = label_config.take_profit_atr
        pipeline_runner.DEFAULT_STOP_LOSS_ATR = label_config.stop_loss_atr
        pipeline_runner.DEFAULT_LABEL_MODE = label_config.label_mode
        if not config.run_walk_forward:
            pipeline_runner._stage_handlers["walk_forward_evaluation"] = (
                lambda pipeline_config, stage_payloads: {
                    "status": "COMPLETED",
                    "message": "Walk-forward evaluation disabled by experiment configuration",
                    "data": {
                        "walk_forward_status": "NEEDS_MORE_DATA",
                        "summary": {"fold_count": 0, "total_test_signal_count": 0},
                    },
                }
            )

        pipeline_result = pipeline_runner.run(
            TrainingPipelineConfig(
                symbol=config.symbol,
                interval=config.interval,
                start_date=config.start_date,
                end_date=config.resolved_end_date(),
                run_id=f"{experiment_id}_{label_config.config_id}",
                feature_version=config.feature_version,
                dry_run=False,
                sample_mode=False,
                run_gate_policy_replay=config.run_gate_policy_replay,
                export_report=True,
                output_dir=candidate_runtime_dir,
                skip_candle_load=config.skip_candle_load,
                training_objective=label_config.training_objective,
                baseline_edge_objective_enabled=label_config.baseline_edge_objective_enabled,
                baseline_edge_focal_gamma=(
                    1.25
                    if label_config.baseline_edge_focal_gamma is None
                    else float(label_config.baseline_edge_focal_gamma)
                ),
                baseline_edge_margin_penalty=(
                    0.02
                    if label_config.baseline_edge_margin_penalty is None
                    else float(label_config.baseline_edge_margin_penalty)
                ),
                baseline_edge_entropy_penalty=(
                    0.01
                    if label_config.baseline_edge_entropy_penalty is None
                    else float(label_config.baseline_edge_entropy_penalty)
                ),
                decision_calibration_enabled=label_config.decision_calibration_enabled,
                decision_flat_if_max_prob_below=(
                    0.42
                    if label_config.decision_flat_if_max_prob_below is None
                    else float(label_config.decision_flat_if_max_prob_below)
                ),
                decision_flat_if_margin_below=(
                    0.06
                    if label_config.decision_flat_if_margin_below is None
                    else float(label_config.decision_flat_if_margin_below)
                ),
                decision_min_direction_prob=(
                    0.40
                    if label_config.decision_min_direction_prob is None
                    else float(label_config.decision_min_direction_prob)
                ),
                decision_min_up_down_margin=(
                    0.03
                    if label_config.decision_min_up_down_margin is None
                    else float(label_config.decision_min_up_down_margin)
                ),
                decision_down_boost=(
                    0.0
                    if label_config.decision_down_boost is None
                    else float(label_config.decision_down_boost)
                ),
                decision_up_penalty=(
                    0.0
                    if label_config.decision_up_penalty is None
                    else float(label_config.decision_up_penalty)
                ),
                decision_flat_boost=(
                    0.0
                    if label_config.decision_flat_boost is None
                    else float(label_config.decision_flat_boost)
                ),
                decision_calibration_mode=(
                    "legacy_calibration"
                    if label_config.decision_calibration_mode is None
                    else str(label_config.decision_calibration_mode)
                ),
                decision_fallback_to_raw=(
                    False
                    if label_config.decision_fallback_to_raw is None
                    else bool(label_config.decision_fallback_to_raw)
                ),
                decision_max_flat_ratio=(
                    0.45
                    if label_config.decision_max_flat_ratio is None
                    else float(label_config.decision_max_flat_ratio)
                ),
                decision_min_down_ratio_when_actual_down_high=(
                    0.12
                    if label_config.decision_min_down_ratio_when_actual_down_high is None
                    else float(label_config.decision_min_down_ratio_when_actual_down_high)
                ),
                decision_min_up_ratio_when_actual_up_high=(
                    0.12
                    if label_config.decision_min_up_ratio_when_actual_up_high is None
                    else float(label_config.decision_min_up_ratio_when_actual_up_high)
                ),
                decision_max_dominant_class_ratio=(
                    0.75
                    if label_config.decision_max_dominant_class_ratio is None
                    else float(label_config.decision_max_dominant_class_ratio)
                ),
                decision_require_non_worse_baseline_edge=(
                    True
                    if label_config.decision_require_non_worse_baseline_edge is None
                    else bool(label_config.decision_require_non_worse_baseline_edge)
                ),
                decision_baseline_edge_tolerance=(
                    0.0025
                    if label_config.decision_baseline_edge_tolerance is None
                    else float(label_config.decision_baseline_edge_tolerance)
                ),
                decision_actual_class_high_threshold=(
                    0.25
                    if label_config.decision_actual_class_high_threshold is None
                    else float(label_config.decision_actual_class_high_threshold)
                ),
                decision_policy_grid_enabled=bool(label_config.decision_policy_grid_enabled),
                decision_policy_grid_stage=label_config.decision_policy_grid_stage,
                opportunity_probability_threshold=float(label_config.opportunity_probability_threshold),
                setup_quality_min_threshold=label_config.setup_quality_min_threshold,
                setup_quality_decision_mask_enabled=bool(label_config.setup_quality_decision_mask_enabled),
                setup_quality_decision_mask_min_threshold=label_config.setup_quality_decision_mask_min_threshold,
                opportunity_threshold_sweep_enabled=bool(label_config.opportunity_threshold_sweep_enabled),
                opportunity_threshold_candidates=tuple(label_config.opportunity_threshold_candidates),
                opportunity_min_precision=float(label_config.opportunity_min_precision),
                opportunity_min_recall=float(label_config.opportunity_min_recall),
                opportunity_max_predicted_trade_rate=float(label_config.opportunity_max_predicted_trade_rate),
                opportunity_max_predicted_to_actual_trade_rate_ratio=float(
                    label_config.opportunity_max_predicted_to_actual_trade_rate_ratio
                ),
                opportunity_max_false_positive_rate=float(label_config.opportunity_max_false_positive_rate),
                entry_path_quality_filter_enabled=bool(label_config.entry_path_quality_filter_enabled),
                entry_path_quality_min_threshold=label_config.entry_path_quality_min_threshold,
                stop_pressure_max_risk_score=label_config.stop_pressure_max_risk_score,
                mae_pressure_max_risk_score=label_config.mae_pressure_max_risk_score,
                class_margin_objective_enabled=bool(label_config.class_margin_objective_enabled),
                true_class_margin_weight=(
                    0.0 if label_config.true_class_margin_weight is None else float(label_config.true_class_margin_weight)
                ),
                true_class_margin_target=(
                    0.06 if label_config.true_class_margin_target is None else float(label_config.true_class_margin_target)
                ),
                up_down_margin_weight=(
                    0.0 if label_config.up_down_margin_weight is None else float(label_config.up_down_margin_weight)
                ),
                up_down_margin_target=(
                    0.05 if label_config.up_down_margin_target is None else float(label_config.up_down_margin_target)
                ),
                flat_margin_weight=(
                    0.0 if label_config.flat_margin_weight is None else float(label_config.flat_margin_weight)
                ),
                flat_margin_target=(
                    0.05 if label_config.flat_margin_target is None else float(label_config.flat_margin_target)
                ),
                hard_negative_margin_weight=(
                    0.0
                    if label_config.hard_negative_margin_weight is None
                    else float(label_config.hard_negative_margin_weight)
                ),
                hard_negative_margin_target=(
                    0.08
                    if label_config.hard_negative_margin_target is None
                    else float(label_config.hard_negative_margin_target)
                ),
            )
        )
        if pipeline_result.status == "FAILED":
            return self._build_failed_pipeline_candidate_result(
                config=config,
                label_config=label_config,
                pipeline_result=pipeline_result,
            )
        return self._build_candidate_result(
            label_config=label_config,
            quality_payload=dict(pipeline_result.quality_summary),
            class_distribution=dict(
                pipeline_result.label_config_summary.get("direction_counts", {})
            )
            or dict(pipeline_result.gap_quality_summary.get("direction_counts", {})),
            gate_policy_summary=dict(pipeline_result.gate_policy_replay_summary),
            extra_warnings=(
                "gate_policy_replay_real_mode_is_sample_backed"
                if config.run_gate_policy_replay
                else "gate_policy_replay_disabled"
            ,),
        )

    def _build_candidate_result(
        self,
        *,
        label_config: LabelQualityGridConfig,
        quality_payload: dict[str, Any],
        class_distribution: dict[str, Any],
        gate_policy_summary: dict[str, Any],
        extra_warnings: tuple[str, ...] = (),
    ) -> LabelGridExperimentCandidateResult:
        gap_quality = self._as_dict(quality_payload.get("gap_quality"))
        anti_collapse = self._as_dict(quality_payload.get("anti_collapse"))
        candidate_selection = self._as_dict(quality_payload.get("candidate_selection"))
        quality_gates = self._as_dict(quality_payload.get("quality_gates_summary"))
        raw_candidate_status = candidate_selection.get("candidate_status")

        profit_total_r, profit_factor = self._profit_metrics(quality_payload)
        walk_fold_count, walk_total_r, walk_profit_factor = self._walk_metrics(quality_payload)
        probability_diagnostics, probability_diagnostics_missing_reason = self._mandatory_diagnostic(
            quality_payload=quality_payload,
            key="probability_diagnostics",
            fallback_reason="probability_diagnostics_not_provided",
        )
        collapse_diagnostics_v2, collapse_diagnostics_v2_missing_reason = self._mandatory_diagnostic(
            quality_payload=quality_payload,
            key="collapse_diagnostics_v2",
            fallback_reason="collapse_diagnostics_v2_not_provided",
        )
        regime_label_builder_status, regime_label_builder_status_missing_reason = self._mandatory_diagnostic(
            quality_payload=quality_payload,
            key="regime_label_builder_status",
            fallback_reason="regime_label_builder_status_not_provided",
        )
        walk_forward_profit_diagnostics, walk_forward_profit_diagnostics_missing_reason = self._mandatory_diagnostic(
            quality_payload=quality_payload,
            key="walk_forward_profit_diagnostics",
            fallback_reason="walk_forward_profit_diagnostics_not_provided",
        )
        profit_aware_diagnostics, profit_aware_diagnostics_missing_reason = self._mandatory_diagnostic(
            quality_payload=quality_payload,
            key="profit_aware_diagnostics",
            fallback_reason="profit_aware_diagnostics_not_provided",
        )
        raw_probability_diagnostics = self._as_dict(
            probability_diagnostics.get("raw_probability_diagnostics", {})
        )
        calibrated_probability_diagnostics = self._as_dict(
            probability_diagnostics.get("calibrated_probability_diagnostics", {})
        )
        raw_predicted_class_distribution = dict(
            raw_probability_diagnostics.get("predicted_direction_ratios", {})
        )
        calibrated_predicted_class_distribution = dict(
            calibrated_probability_diagnostics.get("predicted_direction_ratios", {})
        )
        failed_gates, passed_gates = self._finalize_gate_sets(
            raw_failed_gates=candidate_selection.get(
                "failed_gates", quality_gates.get("failed_gates", [])
            ),
            raw_passed_gates=candidate_selection.get(
                "passed_gates", quality_gates.get("passed_gates", [])
            ),
            gap_quality=gap_quality,
        )
        final_candidate_status = self._normalize_final_candidate_status(
            raw_candidate_status,
            status="COMPLETED",
        )
        if failed_gates and final_candidate_status == "ACCEPTED":
            final_candidate_status = "REJECTED"
        if (
            regime_label_builder_status.get("regime_label_builder_status") == "blocked"
            and final_candidate_status == "ACCEPTED"
        ):
            final_candidate_status = "REJECTED"

        warnings = tuple(
            dict.fromkeys(
                self._string_list(quality_payload.get("warnings"))
                + self._string_list(candidate_selection.get("warnings"))
                + self._string_list(extra_warnings)
            )
        )
        recommendations = tuple(
            dict.fromkeys(
                self._string_list(quality_payload.get("reasons"))
                + self._string_list(candidate_selection.get("recommendations"))
            )
        )
        selected_policy_payload = {
            "model_accuracy": self._optional_float(quality_payload.get("model_accuracy")),
            "baseline_accuracy": self._optional_float(quality_payload.get("baseline_accuracy")),
            "accuracy_edge": self._optional_float(quality_payload.get("accuracy_edge")),
            "collapse_diagnostics_v2": collapse_diagnostics_v2,
            "decision_policy_grid_diagnostics": dict(
                probability_diagnostics.get("decision_policy_grid_diagnostics", {})
            ),
            "prediction_decision_source": probability_diagnostics.get("prediction_decision_source"),
            "actual_class_distribution": dict(anti_collapse.get("actual_distribution", {})),
            "predicted_class_distribution": dict(anti_collapse.get("predicted_distribution", {})),
        }
        apply_selected_decision_policy_metrics(selected_policy_payload)
        opportunity_threshold_selection = self._as_dict(quality_payload.get("opportunity_threshold_selection"))
        opportunity_threshold_sweep = self._as_dict(quality_payload.get("opportunity_threshold_sweep"))
        test_metrics = self._as_dict(quality_payload.get("test_metrics"))
        two_stage_trade_diagnostics = self._as_dict(
            quality_payload.get("two_stage_trade_diagnostics")
            or test_metrics.get("two_stage_trade_diagnostics", {})
        )
        profit_aware_diagnostics_payload = self._as_dict(
            quality_payload.get("profit_aware_diagnostics")
        )
        profit_aware_best_gate = self._as_dict(
            profit_aware_diagnostics_payload.get("best_gate")
        )
        profit_entry_path_summary = self._as_dict(
            quality_payload.get("entry_path_prediction_filter_summary")
            or profit_aware_diagnostics_payload.get("entry_path_prediction_filter_summary")
            or profit_aware_best_gate.get("entry_path_prediction_filter_summary")
        )
        profit_stop_pressure_audit = self._as_dict(
            quality_payload.get("stop_pressure_effectiveness_audit")
            or profit_aware_diagnostics_payload.get("stop_pressure_effectiveness_audit")
            or profit_aware_best_gate.get("stop_pressure_effectiveness_audit")
            or profit_entry_path_summary.get("stop_pressure_effectiveness_audit")
        )

        metric_sources = (
            quality_payload,
            test_metrics,
            two_stage_trade_diagnostics,
            profit_aware_diagnostics_payload,
            profit_aware_best_gate,
            profit_entry_path_summary,
            profit_stop_pressure_audit,
        )

        def _first_present(key: str, default: Any = None) -> Any:
            for source in metric_sources:
                if isinstance(source, dict) and key in source and source.get(key) is not None:
                    return source.get(key)
            return default

        def _first_dict(key: str) -> dict[str, Any]:
            for source in metric_sources:
                value = source.get(key) if isinstance(source, dict) else None
                if isinstance(value, dict) and value:
                    return dict(value)
            return {}

        entry_path_quality_filter_diagnostics = _first_dict("entry_path_quality_filter_diagnostics")
        entry_path_quality_filter_summary = _first_dict("entry_path_quality_filter_summary")
        entry_path_prediction_filter_summary = _first_dict("entry_path_prediction_filter_summary")
        stop_pressure_effectiveness_audit = _first_dict("stop_pressure_effectiveness_audit")
        if not stop_pressure_effectiveness_audit:
            stop_pressure_effectiveness_audit = self._as_dict(
                entry_path_prediction_filter_summary.get("stop_pressure_effectiveness_audit")
            )
        return LabelGridExperimentCandidateResult(
            config_id=label_config.config_id,
            label_config=label_config.to_dict(),
            status="COMPLETED",
            quality_status=quality_payload.get("quality_status"),
            candidate_status=final_candidate_status,
            raw_candidate_status=raw_candidate_status,
            model_version=quality_payload.get("model_version"),
            training_run_id=quality_payload.get("training_run_id"),
            dataset_rows=int(quality_payload.get("dataset_rows", 0) or 0),
            train_rows=int(quality_payload.get("train_rows", 0) or 0),
            val_rows=int(quality_payload.get("val_rows", 0) or 0),
            test_rows=int(quality_payload.get("test_rows", 0) or 0),
            class_distribution=dict(class_distribution),
            actual_distribution=dict(selected_policy_payload.get("actual_class_distribution", {})),
            predicted_distribution=dict(selected_policy_payload.get("predicted_class_distribution", {})),
            model_accuracy=self._optional_float(selected_policy_payload.get("model_accuracy")),
            baseline_accuracy=self._optional_float(selected_policy_payload.get("baseline_accuracy")),
            accuracy_edge=self._optional_float(selected_policy_payload.get("accuracy_edge")),
            collapse_detected=bool(quality_payload.get("collapse_detected", False)),
            collapse_type=anti_collapse.get("collapse_type"),
            feature_version_used=dict(quality_payload.get("feature_config", {})).get("feature_version")
            or quality_payload.get("feature_version"),
            gap_severity=gap_quality.get("gap_severity"),
            gap_count=int(gap_quality.get("gap_count", 0) or 0),
            gap_severity_for_training=gap_quality.get("gap_severity_for_training"),
            effective_gap_count_for_training=int(gap_quality.get("effective_gap_count_for_training", 0) or 0),
            gap_training_safe=gap_quality.get("dataset_safe_for_training"),
            profit_total_r=profit_total_r,
            profit_factor=profit_factor,
            walk_forward_fold_count=walk_fold_count,
            walk_forward_global_total_r=walk_total_r,
            walk_forward_profit_factor=walk_profit_factor,
            gate_policy_allowed_count=int(
                gate_policy_summary.get("gate_policy_allowed_count", 0) or 0
            ),
            gate_policy_blocked_count=int(
                gate_policy_summary.get("gate_policy_blocked_count", 0) or 0
            ),
            failed_gates=failed_gates,
            passed_gates=passed_gates,
            warnings=warnings,
            recommendations=recommendations,
            probability_diagnostics=probability_diagnostics,
            probability_diagnostics_missing_reason=probability_diagnostics_missing_reason,
            collapse_diagnostics_v2=collapse_diagnostics_v2,
            collapse_diagnostics_v2_missing_reason=collapse_diagnostics_v2_missing_reason,
            calibrated_decision_diagnostics=dict(
                probability_diagnostics.get("calibrated_decision_diagnostics", {})
            ),
            bounded_calibrated_decision_selection=dict(
                probability_diagnostics.get("bounded_calibrated_decision_selection", {})
            ),
            decision_policy_grid_diagnostics=dict(selected_policy_payload["decision_policy_grid_diagnostics"]),
            decision_policy_selected_policy_id=selected_policy_payload.get(
                "decision_policy_selected_policy_id"
            ),
            prediction_root_cause_audit=self._as_dict(
                probability_diagnostics.get("prediction_root_cause_audit", {})
            ),
            book_driven_forensic_audit=self._as_dict(
                probability_diagnostics.get("book_driven_forensic_audit", {})
            ),
            label_mode_comparison_audit=self._as_dict(
                quality_payload.get("label_mode_comparison_audit", {})
            ),
            flat_subtype_audit=self._as_dict(
                quality_payload.get("flat_subtype_audit", {})
            ),
            setup_aware_label_diagnostics=self._as_dict(
                quality_payload.get("setup_aware_label_diagnostics", {})
            ),
            schwager_slice_robustness=self._as_dict(
                quality_payload.get("schwager_slice_robustness", {})
            ),
            schwager_robustness_decision_board=self._as_dict(
                quality_payload.get("schwager_robustness_decision_board", {})
            ),
            class_margin_objective_decision=self._as_dict(
                quality_payload.get("class_margin_objective_decision", {})
            ),
            raw_predicted_class_distribution=raw_predicted_class_distribution,
            calibrated_predicted_class_distribution=calibrated_predicted_class_distribution,
            raw_collapse_diagnostics_v2=dict(
                probability_diagnostics.get("raw_collapse_v2", {})
            ),
            prediction_decision_source=selected_policy_payload.get("prediction_decision_source"),
            regime_label_builder_status=regime_label_builder_status,
            regime_label_builder_status_missing_reason=regime_label_builder_status_missing_reason,
            walk_forward_profit_diagnostics=walk_forward_profit_diagnostics,
            walk_forward_profit_diagnostics_missing_reason=walk_forward_profit_diagnostics_missing_reason,
            profit_aware_diagnostics=profit_aware_diagnostics,
            profit_aware_diagnostics_missing_reason=profit_aware_diagnostics_missing_reason,
            opportunity_probability_threshold=self._optional_float(
                quality_payload.get("opportunity_probability_threshold")
            ),
            setup_quality_min_threshold=self._optional_float(
                quality_payload.get("setup_quality_min_threshold")
            ),
            setup_quality_decision_mask_enabled=bool(
                quality_payload.get("setup_quality_decision_mask_enabled", False)
            ),
            setup_quality_decision_mask_min_threshold=self._optional_float(
                quality_payload.get("setup_quality_decision_mask_min_threshold")
            ),
            selected_opportunity_threshold=self._optional_float(
                quality_payload.get("selected_opportunity_threshold")
            ),
            opportunity_threshold_selection=opportunity_threshold_selection,
            opportunity_threshold_sweep=opportunity_threshold_sweep,
            setup_quality_filter_passed=bool(quality_payload.get("setup_quality_filter_passed", False)),
            setup_quality_bucket_metrics=self._as_dict(
                quality_payload.get("setup_quality_bucket_metrics")
                or two_stage_trade_diagnostics.get("setup_quality_bucket_metrics", {})
            ),
            setup_quality_bucket_metrics_raw=self._as_dict(
                quality_payload.get("setup_quality_bucket_metrics_raw")
                or two_stage_trade_diagnostics.get("setup_quality_bucket_metrics_raw", {})
            ),
            setup_quality_bucket_metrics_after_mask=self._as_dict(
                quality_payload.get("setup_quality_bucket_metrics_after_mask")
                or two_stage_trade_diagnostics.get("setup_quality_bucket_metrics_after_mask", {})
            ),
            setup_quality_filter_summary=self._as_dict(
                quality_payload.get("setup_quality_filter_summary")
                or two_stage_trade_diagnostics.get("setup_quality_filter_summary", {})
            ),
            setup_quality_decision_mask_summary=self._as_dict(
                quality_payload.get("setup_quality_decision_mask_summary")
                or two_stage_trade_diagnostics.get("setup_quality_decision_mask_summary", {})
            ),
            entry_path_quality_filter_enabled=bool(
                _first_present("entry_path_quality_filter_enabled", False)
            ),
            entry_path_quality_min_threshold=self._optional_float(
                _first_present("entry_path_quality_min_threshold")
            ),
            stop_pressure_max_risk_score=self._optional_float(
                _first_present("stop_pressure_max_risk_score")
            ),
            mae_pressure_max_risk_score=self._optional_float(
                _first_present("mae_pressure_max_risk_score")
            ),
            entry_path_quality_masked_row_count=int(
                _first_present("entry_path_quality_masked_row_count", 0) or 0
            ),
            entry_path_quality_forced_no_trade_count=int(
                _first_present("entry_path_quality_forced_no_trade_count", 0) or 0
            ),
            entry_path_quality_mask_trade_prediction_removed_count=int(
                _first_present("entry_path_quality_mask_trade_prediction_removed_count", 0) or 0
            ),
            entry_path_quality_mask_false_positive_removed_count=int(
                _first_present("entry_path_quality_mask_false_positive_removed_count", 0) or 0
            ),
            entry_path_quality_filter_summary=entry_path_quality_filter_summary,
            entry_path_quality_filter_diagnostics=entry_path_quality_filter_diagnostics,
            entry_path_prediction_filter_summary=entry_path_prediction_filter_summary,
            stop_pressure_effectiveness_audit=stop_pressure_effectiveness_audit,
            predicted_to_actual_trade_rate_ratio=self._optional_float(
                _first_present("predicted_to_actual_trade_rate_ratio")
            ),
            predicted_trade_rate=self._optional_float(_first_present("predicted_trade_rate")),
            raw_predicted_trade_rate=self._optional_float(_first_present("raw_predicted_trade_rate")),
            masked_predicted_trade_rate=self._optional_float(_first_present("masked_predicted_trade_rate")),
            actual_trade_rate=self._optional_float(_first_present("actual_trade_rate")),
            opportunity_precision=self._optional_float(_first_present("opportunity_precision")),
            opportunity_recall=self._optional_float(_first_present("opportunity_recall")),
            opportunity_f1=self._optional_float(_first_present("opportunity_f1")),
            raw_opportunity_precision=self._optional_float(_first_present("raw_opportunity_precision")),
            raw_opportunity_recall=self._optional_float(_first_present("raw_opportunity_recall")),
            raw_opportunity_f1=self._optional_float(_first_present("raw_opportunity_f1")),
            opportunity_false_positive_rate=self._optional_float(
                _first_present("opportunity_false_positive_rate")
            ),
            two_stage_trade_diagnostics=two_stage_trade_diagnostics,
            approved_for_traders_core_integration=bool(
                quality_payload.get("approved_for_traders_core_integration", False)
            ),
            approved_for_live_trading=False,
            approved_for_auto_activation=False,
            orders_enabled=False,
            traders_core_connected=False,
            model_quality_validation_status="COMPLETED",
        )

    def _resolve_experiment_status(
        self,
        *,
        config: LabelGridExperimentConfig,
        ranking_payload: dict[str, Any],
        candidate_results: list[LabelGridExperimentCandidateResult],
        failed: bool,
    ) -> str:
        if config.dry_run:
            return "DRY_RUN_COMPLETED"
        if config.sample_mode:
            return "SAMPLE_COMPLETED"
        if failed and not any(item.status == "COMPLETED" for item in candidate_results):
            return "FAILED"
        if failed:
            return "COMPLETED_WITH_ERRORS"
        return str(
            ranking_payload.get("experiment_status")
            or "COMPLETED_NO_ACCEPTED_CANDIDATE"
        )

    def _build_failed_pipeline_candidate_result(
        self,
        *,
        config: LabelGridExperimentConfig,
        label_config: LabelQualityGridConfig,
        pipeline_result: Any,
    ) -> LabelGridExperimentCandidateResult:
        stage_payloads = {
            item.stage: self._as_dict(item.data) for item in getattr(pipeline_result, "stage_results", ())
        }
        failed_stage = next(
            (item for item in getattr(pipeline_result, "stage_results", ()) if item.status == "FAILED"),
            None,
        )
        failed_stage_name = None if failed_stage is None else failed_stage.stage
        failed_stage_reason = (
            "pipeline_failed_without_stage_reason"
            if failed_stage is None
            else f"pipeline_failed_at_{failed_stage.stage}"
        )

        train_payload = self._as_dict(stage_payloads.get("train_model"))
        dataset_payload = self._as_dict(stage_payloads.get("build_dataset"))
        build_labels_payload = self._as_dict(stage_payloads.get("build_labels"))
        gap_quality = self._as_dict(getattr(pipeline_result, "gap_quality_summary", {}))
        model_quality_payload = self._as_dict(stage_payloads.get("model_quality_validation"))
        if not model_quality_payload:
            model_quality_payload = self._as_dict(getattr(pipeline_result, "quality_summary", {}))

        candidate_selection = self._as_dict(model_quality_payload.get("candidate_selection"))
        quality_gates = self._as_dict(model_quality_payload.get("quality_gates_summary"))
        raw_candidate_status = candidate_selection.get("candidate_status")
        normalized_raw_candidate_status = str(raw_candidate_status or "").upper()
        normalized_final_candidate_status = (
            self._normalize_final_candidate_status(raw_candidate_status, status="COMPLETED")
            if normalized_raw_candidate_status not in {"", "UNKNOWN", "NONE"}
            else None
        )
        quality_status = str(model_quality_payload.get("quality_status") or "").upper()

        failed_gates_list, passed_gates_list = normalize_gap_quality_gate(
            gap_severity_for_training=gap_quality.get("gap_severity_for_training"),
            gap_training_safe=gap_quality.get("dataset_safe_for_training"),
            failed_gates=[],
            passed_gates=[],
        )
        gap_failed = "gap_quality_gate" in failed_gates_list

        quality_failed_gates, quality_passed_gates = self._finalize_gate_sets(
            raw_failed_gates=candidate_selection.get(
                "failed_gates",
                quality_gates.get("failed_gates", []),
            ),
            raw_passed_gates=candidate_selection.get(
                "passed_gates",
                quality_gates.get("passed_gates", []),
            ),
            gap_quality=gap_quality,
        )

        known_quality_rejection = (
            gap_failed and failed_stage_name == "model_quality_validation"
        ) or (
            bool(model_quality_payload)
            and (
                normalized_final_candidate_status == "REJECTED"
                or quality_status == "QUALITY_REJECTED"
            )
        )

        if known_quality_rejection:
            failed_gates_list = list(
                dict.fromkeys(list(failed_gates_list) + list(quality_failed_gates))
            )
            passed_gates_list = list(
                dict.fromkeys(list(passed_gates_list) + list(quality_passed_gates))
            )

        probability_diagnostics = self._as_dict(
            model_quality_payload.get("probability_diagnostics")
            or stage_payloads.get("probability_diagnostics")
        )
        raw_probability_diagnostics = self._as_dict(
            probability_diagnostics.get("raw_probability_diagnostics", {})
        )
        collapse_diagnostics_v2 = self._as_dict(
            model_quality_payload.get("collapse_diagnostics_v2", {})
        )
        walk_forward_profit_diagnostics = self._as_dict(
            model_quality_payload.get("walk_forward_profit_diagnostics", {})
        )
        profit_aware_diagnostics = self._as_dict(
            model_quality_payload.get("profit_aware_diagnostics", {})
        )
        regime_label_builder_status = self._as_dict(
            model_quality_payload.get("regime_label_builder_status")
            or build_labels_payload.get("regime_label_builder_status", {})
        )
        if not regime_label_builder_status:
            regime_label_builder_status = {
                "regime_label_builder_status": "blocked",
                "regime_label_builder_available": False,
                "regime_label_builder_used_in_training": False,
                "regime_specific_labeling_available": False,
                "regime_specific_training_applied": False,
                "regime_label_config_used": {},
                "label_distribution_by_regime": {},
                "missing_requirements": [failed_stage_reason],
                "warnings": [],
                "reason": failed_stage_reason,
            }

        warning_items = [
            failed_stage_reason,
            f"failed_stage={failed_stage_name}" if failed_stage_name else failed_stage_reason,
        ]
        if known_quality_rejection:
            warning_items.append("pipeline_failed_after_quality_decision_but_candidate_rejected")
        selected_policy_payload = {
            "model_accuracy": self._optional_float(
                model_quality_payload.get("model_accuracy", train_payload.get("model_accuracy"))
            ),
            "baseline_accuracy": self._optional_float(
                model_quality_payload.get(
                    "baseline_accuracy",
                    self._as_dict(stage_payloads.get("baseline_compare")).get("baseline_accuracy"),
                )
            ),
            "accuracy_edge": self._optional_float(model_quality_payload.get("accuracy_edge")),
            "collapse_diagnostics_v2": collapse_diagnostics_v2,
            "decision_policy_grid_diagnostics": dict(
                probability_diagnostics.get("decision_policy_grid_diagnostics", {})
            ),
            "prediction_decision_source": probability_diagnostics.get("prediction_decision_source"),
            "actual_class_distribution": dict(collapse_diagnostics_v2.get("actual_distribution", {})),
            "predicted_class_distribution": dict(collapse_diagnostics_v2.get("predicted_distribution", {})),
        }
        apply_selected_decision_policy_metrics(selected_policy_payload)

        return LabelGridExperimentCandidateResult(
            config_id=label_config.config_id,
            label_config=label_config.to_dict(),
            status="COMPLETED" if known_quality_rejection else "FAILED",
            quality_status=(
                str(model_quality_payload.get("quality_status") or "QUALITY_REJECTED")
                if known_quality_rejection
                else None
            ),
            candidate_status="REJECTED" if known_quality_rejection else "FAILED",
            raw_candidate_status=(
                str(raw_candidate_status or "CANDIDATE_REJECTED")
                if known_quality_rejection
                else "FAILED"
            ),
            model_version=model_quality_payload.get("model_version") or train_payload.get("model_version"),
            training_run_id=model_quality_payload.get("training_run_id") or train_payload.get("training_run_id"),
            dataset_rows=int(model_quality_payload.get("dataset_rows", dataset_payload.get("dataset_rows", 0)) or 0),
            train_rows=int(model_quality_payload.get("train_rows", dataset_payload.get("train_rows", 0)) or 0),
            val_rows=int(
                model_quality_payload.get(
                    "validation_rows",
                    model_quality_payload.get(
                        "val_rows",
                        dataset_payload.get("validation_rows", dataset_payload.get("val_rows", 0)),
                    ),
                )
                or 0
            ),
            test_rows=int(model_quality_payload.get("test_rows", dataset_payload.get("test_rows", 0)) or 0),
            class_distribution=self._as_dict(build_labels_payload.get("direction_counts", {})),
            actual_distribution=dict(selected_policy_payload.get("actual_class_distribution", {})),
            predicted_distribution=dict(selected_policy_payload.get("predicted_class_distribution", {})),
            model_accuracy=self._optional_float(selected_policy_payload.get("model_accuracy")),
            baseline_accuracy=self._optional_float(selected_policy_payload.get("baseline_accuracy")),
            accuracy_edge=self._optional_float(selected_policy_payload.get("accuracy_edge")),
            collapse_detected=bool(model_quality_payload.get("collapse_detected", False)),
            collapse_type=self._as_dict(model_quality_payload.get("anti_collapse", {})).get("collapse_type"),
            feature_version_used=config.feature_version,
            gap_severity=gap_quality.get("gap_severity"),
            gap_count=int(gap_quality.get("gap_count", 0) or 0),
            gap_severity_for_training=gap_quality.get("gap_severity_for_training"),
            effective_gap_count_for_training=int(
                gap_quality.get("effective_gap_count_for_training", 0) or 0
            ),
            gap_training_safe=gap_quality.get("dataset_safe_for_training"),
            profit_total_r=None,
            profit_factor=None,
            walk_forward_fold_count=0,
            walk_forward_global_total_r=None,
            walk_forward_profit_factor=None,
            gate_policy_allowed_count=0,
            gate_policy_blocked_count=0,
            failed_gates=tuple(failed_gates_list),
            passed_gates=tuple(passed_gates_list),
            warnings=tuple(dict.fromkeys(warning_items)),
            recommendations=(
                ("Reject candidate from available quality decision; pipeline failure did not mean candidate execution crash.",)
                if known_quality_rejection
                else ("Inspect pipeline failure before retrying this candidate.",)
            ),
            probability_diagnostics=probability_diagnostics,
            probability_diagnostics_missing_reason=(
                None if probability_diagnostics else "not_computed_due_to_failed_training"
            ),
            collapse_diagnostics_v2=collapse_diagnostics_v2,
            collapse_diagnostics_v2_missing_reason=(
                None if collapse_diagnostics_v2 else "not_computed_due_to_failed_training"
            ),
            calibrated_decision_diagnostics=dict(
                probability_diagnostics.get("calibrated_decision_diagnostics", {})
            ),
            bounded_calibrated_decision_selection=dict(
                probability_diagnostics.get("bounded_calibrated_decision_selection", {})
            ),
            decision_policy_grid_diagnostics=dict(selected_policy_payload["decision_policy_grid_diagnostics"]),
            decision_policy_selected_policy_id=selected_policy_payload.get(
                "decision_policy_selected_policy_id"
            ),
            prediction_root_cause_audit=self._as_dict(
                probability_diagnostics.get("prediction_root_cause_audit", {})
            ),
            book_driven_forensic_audit=self._as_dict(
                probability_diagnostics.get("book_driven_forensic_audit", {})
            ),
            label_mode_comparison_audit=self._as_dict(
                model_quality_payload.get(
                    "label_mode_comparison_audit",
                    build_labels_payload.get("label_mode_comparison_audit", {}),
                )
            ),
            flat_subtype_audit=self._as_dict(
                model_quality_payload.get(
                    "flat_subtype_audit",
                    build_labels_payload.get("flat_subtype_audit", {}),
                )
            ),
            setup_aware_label_diagnostics=self._as_dict(
                model_quality_payload.get(
                    "setup_aware_label_diagnostics",
                    build_labels_payload.get("setup_aware_label_diagnostics", {}),
                )
            ),
            schwager_slice_robustness=self._as_dict(
                model_quality_payload.get("schwager_slice_robustness", {})
            ),
            schwager_robustness_decision_board=self._as_dict(
                model_quality_payload.get("schwager_robustness_decision_board", {})
            ),
            class_margin_objective_decision=self._as_dict(
                model_quality_payload.get("class_margin_objective_decision")
                or train_payload.get("class_margin_objective_decision", {})
            ),
            raw_predicted_class_distribution=dict(
                raw_probability_diagnostics.get("predicted_direction_ratios", {})
            ),
            calibrated_predicted_class_distribution=dict(
                probability_diagnostics.get("calibrated_probability_diagnostics", {}).get(
                    "predicted_direction_ratios", {}
                )
            ),
            raw_collapse_diagnostics_v2=dict(
                probability_diagnostics.get("raw_collapse_v2", {})
            ),
            prediction_decision_source=selected_policy_payload.get("prediction_decision_source"),
            regime_label_builder_status=regime_label_builder_status,
            regime_label_builder_status_missing_reason=None,
            walk_forward_profit_diagnostics=walk_forward_profit_diagnostics,
            walk_forward_profit_diagnostics_missing_reason=(
                None
                if walk_forward_profit_diagnostics
                else "not_computed_due_to_failed_training"
            ),
            profit_aware_diagnostics=profit_aware_diagnostics,
            profit_aware_diagnostics_missing_reason=(
                None if profit_aware_diagnostics else "not_computed_due_to_failed_training"
            ),
            approved_for_traders_core_integration=False,
            approved_for_live_trading=False,
            approved_for_auto_activation=False,
            orders_enabled=False,
            traders_core_connected=False,
            model_quality_validation_status="COMPLETED" if known_quality_rejection else "FAILED",
        )

    @staticmethod
    def _mandatory_diagnostic(
        *,
        quality_payload: dict[str, Any],
        key: str,
        fallback_reason: str,
    ) -> tuple[dict[str, Any], str | None]:
        payload = quality_payload.get(key)
        if isinstance(payload, dict) and payload:
            return dict(payload), None
        return {}, fallback_reason

    @staticmethod
    def _finalize_gate_sets(
        *,
        raw_failed_gates: Any,
        raw_passed_gates: Any,
        gap_quality: dict[str, Any],
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        failed, passed = normalize_gap_quality_gate(
            gap_severity_for_training=gap_quality.get("gap_severity_for_training"),
            gap_training_safe=gap_quality.get("dataset_safe_for_training"),
            failed_gates=LabelGridExperimentRunner._string_list(raw_failed_gates),
            passed_gates=LabelGridExperimentRunner._string_list(raw_passed_gates),
        )
        return tuple(failed), tuple(passed)

    @staticmethod
    def _normalize_final_candidate_status(
        raw_candidate_status: Any,
        *,
        status: str,
    ) -> str:
        normalized = str(raw_candidate_status or "").upper()
        if status == "FAILED" or normalized == "FAILED":
            return "FAILED"
        if normalized in {"ACCEPTED", "CANDIDATE_ACCEPTED_FOR_RESEARCH"}:
            return "ACCEPTED"
        if normalized in {"PLANNED", "DRY_RUN"}:
            return "PLANNED"
        return "REJECTED"

    @classmethod
    def _ranking_candidates_payload(
        cls,
        candidate_results: list[LabelGridExperimentCandidateResult],
    ) -> list[dict[str, Any]]:
        payloads: list[dict[str, Any]] = []
        for item in candidate_results:
            payload = item.to_dict()
            payload["candidate_status"] = item.raw_candidate_status or item.candidate_status
            payloads.append(payload)
        return payloads

    @classmethod
    def _normalize_ranking_rows(
        cls,
        ranking_rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        normalized_rows: list[dict[str, Any]] = []
        for row in ranking_rows:
            normalized = dict(row)
            normalized["raw_candidate_status"] = row.get("candidate_status")
            normalized["candidate_status"] = cls._normalize_final_candidate_status(
                row.get("candidate_status"),
                status="COMPLETED",
            )
            normalized_rows.append(normalized)
        return normalized_rows

    @staticmethod
    def _failed_gates_summary(
        candidate_results: list[LabelGridExperimentCandidateResult],
    ) -> dict[str, int]:
        summary: dict[str, int] = {}
        for result in candidate_results:
            for item in result.failed_gates:
                summary[item] = summary.get(item, 0) + 1
        return summary

    @staticmethod
    def _collapse_summary(
        candidate_results: list[LabelGridExperimentCandidateResult],
    ) -> dict[str, int]:
        summary = {"collapsed": 0, "non_collapsed": 0}
        for result in candidate_results:
            key = "collapsed" if result.collapse_detected else "non_collapsed"
            summary[key] += 1
        return summary

    @staticmethod
    def _profit_summary(
        candidate_results: list[LabelGridExperimentCandidateResult],
    ) -> dict[str, Any]:
        completed = [item for item in candidate_results if item.status == "COMPLETED"]
        return {
            "positive_profit_factor_count": sum(
                int((item.profit_factor or 0.0) > 1.0) for item in completed
            ),
            "positive_total_r_count": sum(
                int((item.profit_total_r or 0.0) > 0.0) for item in completed
            ),
        }

    @staticmethod
    def _walk_summary(
        candidate_results: list[LabelGridExperimentCandidateResult],
    ) -> dict[str, Any]:
        completed = [item for item in candidate_results if item.status == "COMPLETED"]
        return {
            "positive_walk_forward_profit_factor_count": sum(
                int((item.walk_forward_profit_factor or 0.0) > 1.0)
                for item in completed
            ),
            "positive_walk_forward_total_r_count": sum(
                int((item.walk_forward_global_total_r or 0.0) > 0.0)
                for item in completed
            ),
        }

    @staticmethod
    def _gap_summary(
        candidate_results: list[LabelGridExperimentCandidateResult],
    ) -> dict[str, Any]:
        summary: dict[str, int] = {}
        for result in candidate_results:
            key = result.gap_severity_for_training or result.gap_severity or "UNKNOWN"
            summary[key] = summary.get(key, 0) + 1
        return summary

    @staticmethod
    def _recommendations(
        *,
        config: LabelGridExperimentConfig,
        experiment_status: str,
        candidate_results: list[LabelGridExperimentCandidateResult],
    ) -> list[str]:
        recommendations = []
        if config.dry_run:
            recommendations.append("Run sample-mode or real mode to score the planned label grid.")
        if config.sample_mode:
            recommendations.append("Run a real limited grid to validate the best sample candidate on actual training.")
        if experiment_status == "COMPLETED_NO_ACCEPTED_CANDIDATE":
            recommendations.append(
                "No candidate cleared the research gates; refine labels/features before ML29."
            )
        if experiment_status == "COMPLETED_WITH_ACCEPTED_CANDIDATE":
            recommendations.append(
                "Carry the best research-only candidate into ML29 for deeper label/feature refinement."
            )
        if any(result.collapse_detected for result in candidate_results):
            recommendations.append("Investigate collapse-heavy configs before expanding the grid.")
        recommendations.append("Keep traders-core disconnected and keep live trading disabled.")
        return recommendations

    @staticmethod
    def _event_metrics(result: LabelGridExperimentCandidateResult) -> dict[str, Any]:
        return {
            "quality_status": result.quality_status,
            "candidate_status": result.candidate_status,
            "collapse_detected": result.collapse_detected,
            "accuracy_edge": result.accuracy_edge,
            "profit_factor": result.profit_factor,
            "walk_forward_profit_factor": result.walk_forward_profit_factor,
        }

    @staticmethod
    def _profit_metrics(quality_payload: dict[str, Any]) -> tuple[float | None, float | None]:
        candidate_selection = dict(quality_payload.get("candidate_selection", {}))
        gates = dict(candidate_selection.get("gates", {}))
        profit_gate = dict(gates.get("profit_aware_gate", {}))
        total_r = profit_gate.get("best_total_r")
        profit_factor = profit_gate.get("best_profit_factor")
        return (
            None if total_r is None else float(total_r),
            None if profit_factor is None else float(profit_factor),
        )

    @staticmethod
    def _walk_metrics(quality_payload: dict[str, Any]) -> tuple[int, float | None, float | None]:
        candidate_selection = dict(quality_payload.get("candidate_selection", {}))
        gates = dict(candidate_selection.get("gates", {}))
        walk_gate = dict(gates.get("walk_forward_gate", {}))
        fold_count = int(walk_gate.get("fold_count", 0) or 0)
        total_r = walk_gate.get("global_total_r")
        profit_factor = walk_gate.get("global_profit_factor")
        return (
            fold_count,
            None if total_r is None else float(total_r),
            None if profit_factor is None else float(profit_factor),
        )

    @staticmethod
    def _optional_float(value: Any) -> float | None:
        if value is None:
            return None
        return float(value)
