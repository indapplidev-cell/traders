from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date, datetime, time as datetime_time, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import text

from app import __version__
from app.config.settings import get_settings
from app.data.binance_client import BinanceClient
from app.data.candle_gap_checker import CandleGapChecker
from app.data.historical_loader import HistoricalLoader
from app.dataset.dataset_builder import DatasetBuilder
from app.db.repositories.candle_repository import CandleRepository
from app.db.repositories.feature_repository import FeatureRepository
from app.db.repositories.label_repository import LabelRepository
from app.db.repositories.model_registry_repository import ModelRegistryRepository
from app.db.repositories.training_run_repository import TrainingRunRepository
from app.evaluation.gate_policy_replay_evaluator import GatePolicyReplayEvaluator
from app.evaluation.gate_policy_replay_reporter import GatePolicyReplayReporter
from app.evaluation.model_quality_reporter import ModelQualityReporter
from app.evaluation.model_quality_validator import (
    INSUFFICIENT_REAL_HISTORY,
    validate_model_quality,
)
from app.diagnostics.collapse_diagnostics_v2 import CollapseDiagnosticsV2
from app.diagnostics.class_margin_objective_decision import load_latest_class_margin_runtime_evidence
from app.diagnostics.diagnostics_service import DiagnosticsService
from app.diagnostics.flat_subtype_audit import FlatSubtypeAudit
from app.diagnostics.gap_quality_diagnostics import GapQualityDiagnostics
from app.diagnostics.label_mode_comparison_audit import LabelModeComparisonAudit
from app.diagnostics.opportunity_diagnostics import OpportunityDiagnostics
from app.diagnostics.schwager_robustness_decision_board import SchwagerRobustnessDecisionBoard
from app.diagnostics.setup_aware_label_diagnostics import SetupAwareLabelDiagnostics
from app.diagnostics.walk_forward_profit_diagnostics import WalkForwardProfitDiagnostics
from app.db.session import get_session
from app.features.feature_pipeline import FeaturePipeline
from app.labels.label_builder import LabelBuilder
from app.labels.label_config import LabelConfig
from app.labels.regime_label_builder import RegimeLabelBuilder
from app.registry.artifact_storage import ArtifactStorage
from app.registry.model_registry import ModelRegistry
from app.training.two_stage_thresholds import DEFAULT_OPPORTUNITY_THRESHOLD_CANDIDATES
from app.training.training_service import TrainingService
from app.training.training_pipeline_logger import TrainingPipelineLogger
from app.training.training_pipeline_reporter import TrainingPipelineReporter


PENDING = "PENDING"
RUNNING = "RUNNING"
COMPLETED = "COMPLETED"
FAILED = "FAILED"
SKIPPED = "SKIPPED"
SKIPPED_NOT_AVAILABLE = "SKIPPED_NOT_AVAILABLE"

PIPELINE_COMPLETED = "COMPLETED"
PIPELINE_COMPLETED_WITH_SKIPS = "COMPLETED_WITH_SKIPS"
PIPELINE_FAILED = "FAILED"
PIPELINE_DRY_RUN_COMPLETED = "DRY_RUN_COMPLETED"
PIPELINE_SAMPLE_COMPLETED = "SAMPLE_COMPLETED"


@dataclass(frozen=True)
class TrainingPipelineConfig:
    symbol: str
    interval: str
    start_date: str
    end_date: str | None = None
    run_id: str | None = None
    feature_version: str = "fv1"
    dry_run: bool = False
    sample_mode: bool = False
    run_gate_policy_replay: bool = True
    export_report: bool = True
    output_dir: Path = Path("reports/training_pipeline_runs")
    skip_candle_load: bool = False
    training_objective: str = "direction_global"
    baseline_edge_objective_enabled: bool = False
    baseline_edge_focal_gamma: float = 1.25
    baseline_edge_margin_penalty: float = 0.02
    baseline_edge_entropy_penalty: float = 0.01
    baseline_edge_gate_min: float = 0.0
    collapse_critical_gate_enabled: bool = True
    decision_calibration_enabled: bool = False
    decision_flat_if_max_prob_below: float = 0.42
    decision_flat_if_margin_below: float = 0.06
    decision_min_direction_prob: float = 0.40
    decision_min_up_down_margin: float = 0.03
    decision_down_boost: float = 0.0
    decision_up_penalty: float = 0.0
    decision_flat_boost: float = 0.0
    decision_calibration_mode: str = "legacy_calibration"
    decision_fallback_to_raw: bool = False
    decision_max_flat_ratio: float = 0.45
    decision_min_down_ratio_when_actual_down_high: float = 0.12
    decision_min_up_ratio_when_actual_up_high: float = 0.12
    decision_max_dominant_class_ratio: float = 0.75
    decision_require_non_worse_baseline_edge: bool = True
    decision_baseline_edge_tolerance: float = 0.0025
    decision_actual_class_high_threshold: float = 0.25
    decision_policy_grid_enabled: bool = False
    decision_policy_grid_stage: str | None = None
    opportunity_probability_threshold: float = 0.5
    setup_quality_min_threshold: float | None = None
    setup_quality_decision_mask_enabled: bool = False
    setup_quality_decision_mask_min_threshold: float | None = None
    opportunity_threshold_sweep_enabled: bool = False
    opportunity_threshold_candidates: tuple[float, ...] = DEFAULT_OPPORTUNITY_THRESHOLD_CANDIDATES
    opportunity_min_precision: float = 0.25
    opportunity_min_recall: float = 0.50
    opportunity_max_predicted_trade_rate: float = 0.15
    opportunity_max_predicted_to_actual_trade_rate_ratio: float = 3.0
    opportunity_max_false_positive_rate: float = 0.25
    entry_path_quality_filter_enabled: bool = False
    entry_path_quality_min_threshold: float | None = None
    stop_pressure_max_risk_score: float | None = None
    mae_pressure_max_risk_score: float | None = None
    exit_policy_profile: str | None = None
    exit_timeout_bars: int | None = None
    exit_mitigation_loss_r: float | None = None
    exit_neutral_abs_r: float | None = None
    directional_side_filter_profile: str | None = None
    allowed_signal_directions: tuple[str, ...] | None = None
    side_aware_validation_relaxation_enabled: bool = False
    side_aware_min_validation_signal_count: int | None = None
    side_aware_min_validation_profit_factor: float | None = None
    side_aware_min_validation_total_r: float | None = None
    side_aware_min_validation_expectancy_r: float | None = None
    side_aware_allow_single_direction_validation: bool = False
    research_only_total_r_repair_enabled: bool = False
    validation_total_r_repair_profile: str | None = None
    research_only_acceptance_block_reason: str | None = None
    research_only_fold_repair_probe_enabled: bool = False
    fold_repair_probe_profile: str | None = None
    fold_repair_target_dates: tuple[str, ...] = ()
    fold_repair_time_slice_blackout_enabled: bool = False
    fold_repair_blackout_dates: tuple[str, ...] = ()
    class_margin_objective_enabled: bool = False
    true_class_margin_weight: float = 0.0
    true_class_margin_target: float = 0.06
    up_down_margin_weight: float = 0.0
    up_down_margin_target: float = 0.05
    flat_margin_weight: float = 0.0
    flat_margin_target: float = 0.05
    hard_negative_margin_weight: float = 0.0
    hard_negative_margin_target: float = 0.08

    def resolved_end_date(self) -> str:
        if self.end_date is not None:
            return self.end_date
        return date.today().isoformat()

    def resolved_run_id(self) -> str:
        if self.run_id is not None:
            return self.run_id
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"{timestamp}_{self.symbol}_{self.interval}"


@dataclass(frozen=True)
class TrainingPipelineStageResult:
    stage: str
    status: str
    message: str
    duration_seconds: float
    started_at: str
    ended_at: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "status": self.status,
            "message": self.message,
            "duration_seconds": self.duration_seconds,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "data": dict(self.data),
        }


@dataclass(frozen=True)
class TrainingPipelineResult:
    run_id: str
    status: str
    symbol: str
    interval: str
    start_date: str
    end_date: str
    dry_run: bool
    sample_mode: bool
    run_gate_policy_replay: bool
    export_report: bool
    started_at: str
    ended_at: str
    duration_seconds: float
    stage_results: tuple[TrainingPipelineStageResult, ...]
    quality_summary: dict[str, Any]
    model_summary: dict[str, Any]
    baseline_summary: dict[str, Any]
    gate_policy_replay_summary: dict[str, Any]
    gap_quality_summary: dict[str, Any]
    anti_collapse_summary: dict[str, Any]
    candidate_selection_summary: dict[str, Any]
    label_config_summary: dict[str, Any]
    quality_gates_summary: dict[str, Any]
    output_dir: str
    log_path: str
    events_path: str
    json_report_path: str
    markdown_report_path: str
    safety: dict[str, Any]
    command_snapshot: dict[str, Any]
    next_recommendations: tuple[str, ...]
    prediction_root_cause_audit: dict[str, Any] = field(default_factory=dict)
    book_driven_forensic_audit: dict[str, Any] = field(default_factory=dict)
    label_mode_comparison_audit: dict[str, Any] = field(default_factory=dict)
    flat_subtype_audit: dict[str, Any] = field(default_factory=dict)
    setup_aware_label_diagnostics: dict[str, Any] = field(default_factory=dict)
    schwager_slice_robustness: dict[str, Any] = field(default_factory=dict)
    schwager_robustness_decision_board: dict[str, Any] = field(default_factory=dict)
    class_margin_objective_decision: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "symbol": self.symbol,
            "interval": self.interval,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "dry_run": self.dry_run,
            "sample_mode": self.sample_mode,
            "run_gate_policy_replay": self.run_gate_policy_replay,
            "export_report": self.export_report,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_seconds": self.duration_seconds,
            "stage_results": [item.to_dict() for item in self.stage_results],
            "quality_summary": dict(self.quality_summary),
            "model_summary": dict(self.model_summary),
            "baseline_summary": dict(self.baseline_summary),
            "gate_policy_replay_summary": dict(self.gate_policy_replay_summary),
            "gap_quality_summary": dict(self.gap_quality_summary),
            "anti_collapse_summary": dict(self.anti_collapse_summary),
            "candidate_selection_summary": dict(self.candidate_selection_summary),
            "label_config_summary": dict(self.label_config_summary),
            "quality_gates_summary": dict(self.quality_gates_summary),
            "output_dir": self.output_dir,
            "log_path": self.log_path,
            "events_path": self.events_path,
            "json_report_path": self.json_report_path,
            "markdown_report_path": self.markdown_report_path,
            "safety": dict(self.safety),
            "command_snapshot": dict(self.command_snapshot),
            "next_recommendations": list(self.next_recommendations),
            "prediction_root_cause_audit": dict(self.prediction_root_cause_audit),
            "book_driven_forensic_audit": dict(self.book_driven_forensic_audit),
            "label_mode_comparison_audit": dict(self.label_mode_comparison_audit),
            "flat_subtype_audit": dict(self.flat_subtype_audit),
            "setup_aware_label_diagnostics": dict(self.setup_aware_label_diagnostics),
            "schwager_slice_robustness": dict(self.schwager_slice_robustness),
            "schwager_robustness_decision_board": dict(self.schwager_robustness_decision_board),
            "class_margin_objective_decision": dict(self.class_margin_objective_decision),
        }


class LongHistoryTrainingPipelineRunner:
    DEFAULT_FEATURE_VERSION = "fv1"
    DEFAULT_LABEL_VERSION = "lv1"
    DEFAULT_MODEL_NAME = "candle_mlp"
    DEFAULT_DIRECTION_LOSS_NAME = "focal"
    DEFAULT_FOCAL_GAMMA = 2.2
    DEFAULT_LABEL_SMOOTHING = 0.01
    DEFAULT_CONFIDENCE_MARGIN_WEIGHT = 0.25
    DEFAULT_CONFIDENCE_MARGIN_TARGET = 0.18
    DEFAULT_DIRECTION_LOSS_WEIGHT = 3.00
    DEFAULT_TP_SL_LOSS_WEIGHT = 0.10
    DEFAULT_MOVE_LOSS_WEIGHT = 0.10
    DEFAULT_RISK_LOSS_WEIGHT = 0.10
    DEFAULT_DIRECTION_LOGIT_GAP_WEIGHT = 0.20
    DEFAULT_DIRECTION_LOGIT_GAP_TARGET = 0.45
    DEFAULT_DIRECTION_DISTRIBUTION_LOSS_WEIGHT = 0.75
    DEFAULT_FLAT_PROBABILITY_FLOOR_WEIGHT = 1.00
    DEFAULT_FLAT_PROBABILITY_FLOOR_TARGET = 0.20
    DEFAULT_MIN_CLASS_PROBABILITY_FLOOR = 0.05
    DEFAULT_CLASS_PROBABILITY_FLOOR_WEIGHT = 1.50
    # Class order: UP, DOWN, FLAT.
    DEFAULT_CLASS_PROBABILITY_FLOOR_TARGETS = (0.10, 0.18, 0.12)
    DEFAULT_DOMINANT_CLASS_CEILING_WEIGHT = 1.25
    DEFAULT_DOMINANT_CLASS_CEILING_TARGET = 0.72
    DEFAULT_LABEL_NOISE_HARDENING_ENABLED = True
    DEFAULT_PROBABILITY_TEMPERATURE_ENABLED = True
    DEFAULT_OPPORTUNITY_LOSS_WEIGHT = 1.0
    DEFAULT_DIRECTION_ATR_THRESHOLD = 0.5
    DEFAULT_TAKE_PROFIT_ATR = 1.5
    DEFAULT_STOP_LOSS_ATR = 1.0
    DEFAULT_LABEL_MODE = "future_close_atr"
    DEFAULT_FEE_R = 0.02
    DEFAULT_SLIPPAGE_R = 0.01
    DEFAULT_SAME_CANDLE_POLICY = "conservative"
    DEFAULT_WALK_FORWARD_MODE = "expanding"
    DEFAULT_WALK_FORWARD_TRAIN_DAYS = 45
    DEFAULT_WALK_FORWARD_VALIDATION_DAYS = 10
    DEFAULT_WALK_FORWARD_TEST_DAYS = 10
    DEFAULT_WALK_FORWARD_STEP_DAYS = 10
    DEFAULT_WALK_FORWARD_MIN_TRAIN_ROWS = 1000

    STAGES = (
        "health_check",
        "db_check",
        "load_candles",
        "check_candle_gaps",
        "build_features",
        "build_labels",
        "build_dataset",
        "train_model",
        "probability_diagnostics",
        "baseline_compare",
        "calibration_diagnostics",
        "profit_aware_evaluation",
        "walk_forward_evaluation",
        "gate_policy_replay_evaluation",
        "model_quality_validation",
        "export_reports",
    )

    def __init__(
        self,
        *,
        logger_class: type[TrainingPipelineLogger] = TrainingPipelineLogger,
        reporter: TrainingPipelineReporter | None = None,
        stage_handlers: dict[str, Callable[[TrainingPipelineConfig, dict[str, Any]], dict[str, Any]]] | None = None,
    ) -> None:
        self._logger_class = logger_class
        self._reporter = reporter or TrainingPipelineReporter()
        self._stage_handlers = stage_handlers or {}

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}
    
    def _attach_profit_exit_root_cause_payload(
        self,
        payload: dict[str, Any],
        *,
        profit_aware_summary: Any = None,
        walk_forward_profit_diagnostics: Any = None,
    ) -> dict[str, Any]:
        """Attach ML38.10.13+ exit/root-cause diagnostics defensively.

        Dry-run and sample-mode paths often do not have real profit-aware or
        walk-forward payloads. This enrichment must never fail the pipeline.
        """

        if not isinstance(payload, dict):
            return payload

        profit_aware_summary_payload = self._as_dict(profit_aware_summary)
        if profit_aware_summary_payload:
            try:
                profit_aware_diagnostics_payload = (
                    WalkForwardProfitDiagnostics().build_profit_aware_diagnostics(
                        profit_aware_summary=profit_aware_summary_payload
                    )
                )
            except Exception as exc:
                payload["profit_exit_root_cause_audit_missing_reason"] = (
                    f"profit_aware_diagnostics_build_failed:{type(exc).__name__}"
                )
            else:
                profit_exit_root_cause_audit = self._as_dict(
                    profit_aware_diagnostics_payload.get("profit_exit_root_cause_audit")
                )
                if profit_exit_root_cause_audit:
                    payload["profit_exit_root_cause_audit"] = profit_exit_root_cause_audit

                entry_path_prediction_filter_summary = self._as_dict(
                    profit_aware_diagnostics_payload.get(
                        "entry_path_prediction_filter_summary"
                    )
                )
                if entry_path_prediction_filter_summary:
                    payload["entry_path_prediction_filter_summary"] = (
                        entry_path_prediction_filter_summary
                    )

                stop_pressure_effectiveness_audit = self._as_dict(
                    profit_aware_diagnostics_payload.get(
                        "stop_pressure_effectiveness_audit"
                    )
                )
                if stop_pressure_effectiveness_audit:
                    payload["stop_pressure_effectiveness_audit"] = (
                        stop_pressure_effectiveness_audit
                    )

        walk_forward_profit_payload = self._as_dict(walk_forward_profit_diagnostics)
        if walk_forward_profit_payload:
            walk_forward_exit_summary = self._as_dict(
                walk_forward_profit_payload.get(
                    "walk_forward_profit_exit_root_cause_summary"
                )
            )
            if walk_forward_exit_summary:
                payload["walk_forward_profit_exit_root_cause_summary"] = (
                    walk_forward_exit_summary
                )

        return payload

    @staticmethod
    def _as_list(value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return list(value)
        if isinstance(value, (tuple, set)):
            return list(value)
        return [value]

    @staticmethod
    def _as_bool(value: Any, *, default: bool = False) -> bool:
        if value is None:
            return default
        return bool(value)

    def run(self, config: TrainingPipelineConfig) -> TrainingPipelineResult:
        resolved_run_id = config.resolved_run_id()
        resolved_end_date = config.resolved_end_date()
        logger = self._logger_class(run_id=resolved_run_id, output_dir=config.output_dir)
        started_at = self._timestamp()
        pipeline_start = time.perf_counter()
        logger.pipeline_started(
            message="Training quality pipeline started",
            data={
                "symbol": config.symbol,
                "interval": config.interval,
                "start_date": config.start_date,
                "end_date": resolved_end_date,
                "feature_version": config.feature_version,
                "dry_run": config.dry_run,
                "sample_mode": config.sample_mode,
                "run_gate_policy_replay": config.run_gate_policy_replay,
                "export_report": config.export_report,
                "skip_candle_load": config.skip_candle_load,
            },
        )

        stage_results: list[TrainingPipelineStageResult] = []
        stage_payloads: dict[str, dict[str, Any]] = {}
        failed = False

        for stage in self.STAGES:
            if failed:
                break
            if stage == "export_reports":
                continue

            result = self._run_stage(
                stage=stage,
                config=config,
                logger=logger,
                stage_payloads=stage_payloads,
                run_id=resolved_run_id,
                end_date=resolved_end_date,
            )
            stage_results.append(result)
            stage_payloads[stage] = dict(result.data)
            if result.status == FAILED:
                failed = True

        provisional_status = self._resolve_final_status(
            dry_run=config.dry_run,
            sample_mode=config.sample_mode,
            stage_results=stage_results,
        )
        quality_summary = self._build_quality_summary(stage_payloads)
        model_summary = self._as_dict(stage_payloads.get("train_model"))
        baseline_summary = self._as_dict(stage_payloads.get("baseline_compare"))
        gate_policy_replay_summary = self._as_dict(stage_payloads.get("gate_policy_replay_evaluation"))
        gap_quality_summary = self._as_dict(quality_summary.get("gap_quality"))
        anti_collapse_summary = self._as_dict(quality_summary.get("anti_collapse"))
        candidate_selection_summary = self._as_dict(quality_summary.get("candidate_selection"))
        label_config_summary = self._as_dict(quality_summary.get("label_config"))
        quality_gates_summary = self._as_dict(quality_summary.get("quality_gates_summary"))

        export_stage_result = self._run_export_stage(
            config=config,
            logger=logger,
            run_id=resolved_run_id,
            resolved_end_date=resolved_end_date,
            started_at=started_at,
            current_status=provisional_status,
            stage_results=stage_results,
            quality_summary=quality_summary,
            model_summary=model_summary,
            baseline_summary=baseline_summary,
            gate_policy_replay_summary=gate_policy_replay_summary,
            gap_quality_summary=gap_quality_summary,
            anti_collapse_summary=anti_collapse_summary,
            candidate_selection_summary=candidate_selection_summary,
            label_config_summary=label_config_summary,
            quality_gates_summary=quality_gates_summary,
        )
        stage_results.append(export_stage_result)
        if export_stage_result.status == FAILED:
            failed = True

        final_status = self._resolve_final_status(
            dry_run=config.dry_run,
            sample_mode=config.sample_mode,
            stage_results=stage_results,
        )
        ended_at = self._timestamp()
        total_duration = time.perf_counter() - pipeline_start

        result = TrainingPipelineResult(
            run_id=resolved_run_id,
            status=PIPELINE_FAILED if failed else final_status,
            symbol=config.symbol,
            interval=config.interval,
            start_date=config.start_date,
            end_date=resolved_end_date,
            dry_run=config.dry_run,
            sample_mode=config.sample_mode,
            run_gate_policy_replay=config.run_gate_policy_replay,
            export_report=config.export_report,
            started_at=started_at,
            ended_at=ended_at,
            duration_seconds=total_duration,
            stage_results=tuple(stage_results),
            quality_summary=quality_summary,
            model_summary=model_summary,
            baseline_summary=baseline_summary,
            gate_policy_replay_summary=gate_policy_replay_summary,
            gap_quality_summary=gap_quality_summary,
            anti_collapse_summary=anti_collapse_summary,
            candidate_selection_summary=candidate_selection_summary,
            label_config_summary=label_config_summary,
            quality_gates_summary=quality_gates_summary,
            output_dir=str(logger.paths.run_dir),
            log_path=str(logger.paths.log_path),
            events_path=str(logger.paths.events_path),
            json_report_path=str(logger.paths.json_report_path),
            markdown_report_path=str(logger.paths.markdown_report_path),
            safety={
                "approved_for_traders_core_integration": bool(
                    quality_summary.get("approved_for_traders_core_integration", False)
                ),
                "approved_for_live_trading": False,
                "approved_for_auto_activation": False,
                "traders_core_connected": False,
                "live_trading_connected": False,
                "orders_enabled": False,
            },
            command_snapshot={
                "symbol": config.symbol,
                "interval": config.interval,
                "start_date": config.start_date,
                "end_date": resolved_end_date,
                "run_id": resolved_run_id,
                "feature_version": config.feature_version,
                "dry_run": config.dry_run,
                "sample_mode": config.sample_mode,
                "run_gate_policy_replay": config.run_gate_policy_replay,
                "export_report": config.export_report,
                "output_dir": str(config.output_dir),
                "skip_candle_load": config.skip_candle_load,
                "training_objective": config.training_objective,
                "decision_policy_grid_enabled": config.decision_policy_grid_enabled,
                "decision_policy_grid_stage": config.decision_policy_grid_stage,
                "class_margin_objective_enabled": config.class_margin_objective_enabled,
            },
            next_recommendations=self._next_recommendations(
                quality_status=str(quality_summary.get("quality_status", INSUFFICIENT_REAL_HISTORY)),
                dry_run=config.dry_run,
                sample_mode=config.sample_mode,
            ),
            prediction_root_cause_audit=self._as_dict(
                quality_summary.get("prediction_root_cause_audit")
            ),
            book_driven_forensic_audit=self._as_dict(
                quality_summary.get("book_driven_forensic_audit")
            ),
            label_mode_comparison_audit=self._as_dict(
                quality_summary.get("label_mode_comparison_audit")
            ),
            flat_subtype_audit=self._as_dict(
                quality_summary.get("flat_subtype_audit")
            ),
            setup_aware_label_diagnostics=self._as_dict(
                quality_summary.get("setup_aware_label_diagnostics")
            ),
            schwager_slice_robustness=self._as_dict(
                quality_summary.get("schwager_slice_robustness")
            ),
            schwager_robustness_decision_board=self._as_dict(
                quality_summary.get("schwager_robustness_decision_board")
            ),
            class_margin_objective_decision=self._as_dict(
                quality_summary.get("class_margin_objective_decision")
                or model_summary.get("class_margin_objective_decision")
            ),
        )

        if config.export_report:
            self._reporter.write_json_report(result)
            self._reporter.write_markdown_report(result)

        if result.status == PIPELINE_FAILED:
            logger.pipeline_failed(
                message="Training quality pipeline failed",
                duration_seconds=total_duration,
                data={"status": result.status},
            )
        else:
            logger.pipeline_completed(
                status=result.status,
                message="Training quality pipeline completed",
                duration_seconds=total_duration,
                data={
                    "quality_status": result.quality_summary.get("quality_status"),
                    "completed_stage_count": self._count_status(stage_results, COMPLETED),
                    "skipped_stage_count": self._count_skipped(stage_results),
                },
            )

        return result

    def _run_stage(
        self,
        *,
        stage: str,
        config: TrainingPipelineConfig,
        logger: TrainingPipelineLogger,
        stage_payloads: dict[str, dict[str, Any]],
        run_id: str,
        end_date: str,
    ) -> TrainingPipelineStageResult:
        started_at = self._timestamp()
        started_perf = time.perf_counter()
        logger.stage_started(
            stage=stage,
            message=f"Starting stage {stage}",
            data={"symbol": config.symbol, "interval": config.interval},
        )
        try:
            handler = self._resolve_stage_handler(stage, config)
            payload = handler(config, stage_payloads)
            status = str(payload.get("status", COMPLETED))
            message = str(payload.get("message", f"{stage} completed"))
            data = dict(payload.get("data", {}))
            data.setdefault("run_id", run_id)
            data.setdefault("end_date", end_date)
            duration = time.perf_counter() - started_perf
            logger.stage_completed(
                stage=stage,
                status=status,
                message=message,
                duration_seconds=duration,
                data=data,
            )
            return TrainingPipelineStageResult(
                stage=stage,
                status=status,
                message=message,
                duration_seconds=duration,
                started_at=started_at,
                ended_at=self._timestamp(),
                data=data,
            )
        except Exception as exc:
            duration = time.perf_counter() - started_perf
            logger.stage_failed(
                stage=stage,
                message=str(exc),
                duration_seconds=duration,
                data={"error": str(exc)},
            )
            return TrainingPipelineStageResult(
                stage=stage,
                status=FAILED,
                message=str(exc),
                duration_seconds=duration,
                started_at=started_at,
                ended_at=self._timestamp(),
                data={"error": str(exc)},
            )

    def _run_export_stage(
        self,
        *,
        config: TrainingPipelineConfig,
        logger: TrainingPipelineLogger,
        run_id: str,
        resolved_end_date: str,
        started_at: str,
        current_status: str,
        stage_results: list[TrainingPipelineStageResult],
        quality_summary: dict[str, Any],
        model_summary: dict[str, Any],
        baseline_summary: dict[str, Any],
        gate_policy_replay_summary: dict[str, Any],
        gap_quality_summary: dict[str, Any],
        anti_collapse_summary: dict[str, Any],
        candidate_selection_summary: dict[str, Any],
        label_config_summary: dict[str, Any],
        quality_gates_summary: dict[str, Any],
    ) -> TrainingPipelineStageResult:
        started_stage = self._timestamp()
        started_perf = time.perf_counter()
        logger.stage_started(
            stage="export_reports",
            message="Exporting training pipeline reports",
            data={"export_report": config.export_report},
        )
        if not config.export_report:
            duration = time.perf_counter() - started_perf
            logger.stage_completed(
                stage="export_reports",
                status=SKIPPED,
                message="Report export disabled",
                duration_seconds=duration,
                data={"export_report": False},
            )
            return TrainingPipelineStageResult(
                stage="export_reports",
                status=SKIPPED,
                message="Report export disabled",
                duration_seconds=duration,
                started_at=started_stage,
                ended_at=self._timestamp(),
                data={"export_report": False},
            )

        temporary_result = TrainingPipelineResult(
            run_id=run_id,
            status=current_status,
            symbol=config.symbol,
            interval=config.interval,
            start_date=config.start_date,
            end_date=resolved_end_date,
            dry_run=config.dry_run,
            sample_mode=config.sample_mode,
            run_gate_policy_replay=config.run_gate_policy_replay,
            export_report=config.export_report,
            started_at=started_at,
            ended_at=self._timestamp(),
            duration_seconds=0.0,
            stage_results=tuple(stage_results),
            quality_summary=quality_summary,
            model_summary=model_summary,
            baseline_summary=baseline_summary,
            gate_policy_replay_summary=gate_policy_replay_summary,
            gap_quality_summary=gap_quality_summary,
            anti_collapse_summary=anti_collapse_summary,
            candidate_selection_summary=candidate_selection_summary,
            label_config_summary=label_config_summary,
            quality_gates_summary=quality_gates_summary,
            output_dir=str(logger.paths.run_dir),
            log_path=str(logger.paths.log_path),
            events_path=str(logger.paths.events_path),
            json_report_path=str(logger.paths.json_report_path),
            markdown_report_path=str(logger.paths.markdown_report_path),
            safety={
                "approved_for_traders_core_integration": bool(
                    quality_summary.get("approved_for_traders_core_integration", False)
                ),
                "approved_for_live_trading": False,
                "approved_for_auto_activation": False,
                "traders_core_connected": False,
                "live_trading_connected": False,
                "orders_enabled": False,
            },
            command_snapshot={
                "symbol": config.symbol,
                "interval": config.interval,
                "start_date": config.start_date,
                "end_date": resolved_end_date,
                "run_id": run_id,
                "dry_run": config.dry_run,
                "sample_mode": config.sample_mode,
                "run_gate_policy_replay": config.run_gate_policy_replay,
                "export_report": config.export_report,
                "output_dir": str(config.output_dir),
                "skip_candle_load": config.skip_candle_load,
                "training_objective": config.training_objective,
                "decision_policy_grid_enabled": config.decision_policy_grid_enabled,
                "decision_policy_grid_stage": config.decision_policy_grid_stage,
            },
            next_recommendations=self._next_recommendations(
                quality_status=str(quality_summary.get("quality_status", INSUFFICIENT_REAL_HISTORY)),
                dry_run=config.dry_run,
                sample_mode=config.sample_mode,
            ),
            book_driven_forensic_audit=self._as_dict(
                quality_summary.get("book_driven_forensic_audit")
            ),
            schwager_slice_robustness=self._as_dict(
                quality_summary.get("schwager_slice_robustness")
            ),
            schwager_robustness_decision_board=self._as_dict(
                quality_summary.get("schwager_robustness_decision_board")
            ),
        )
        self._reporter.write_json_report(temporary_result)
        self._reporter.write_markdown_report(temporary_result)
        duration = time.perf_counter() - started_perf
        data = {
            "json_report_path": str(logger.paths.json_report_path),
            "markdown_report_path": str(logger.paths.markdown_report_path),
        }
        logger.stage_completed(
            stage="export_reports",
            status=COMPLETED,
            message="Reports exported",
            duration_seconds=duration,
            data=data,
        )
        return TrainingPipelineStageResult(
            stage="export_reports",
            status=COMPLETED,
            message="Reports exported",
            duration_seconds=duration,
            started_at=started_stage,
            ended_at=self._timestamp(),
            data=data,
        )

    def _resolve_stage_handler(
        self,
        stage: str,
        config: TrainingPipelineConfig,
    ) -> Callable[[TrainingPipelineConfig, dict[str, Any]], dict[str, Any]]:
        if stage in self._stage_handlers:
            return self._stage_handlers[stage]
        if config.dry_run:
            return self._dry_run_stage_handler(stage)
        if config.sample_mode:
            return self._sample_mode_stage_handler(stage)
        if stage == "load_candles" and config.skip_candle_load:
            return self._skip_load_candles_stage()
        return {
            "health_check": self._health_check_real,
            "db_check": self._db_check_real,
            "load_candles": self._load_candles_real,
            "check_candle_gaps": self._check_candle_gaps_real,
            "build_features": self._build_features_real,
            "build_labels": self._build_labels_real,
            "build_dataset": self._build_dataset_real,
            "train_model": self._train_model_real,
            "probability_diagnostics": self._probability_diagnostics_real,
            "baseline_compare": self._baseline_compare_real,
            "calibration_diagnostics": self._calibration_diagnostics_real,
            "profit_aware_evaluation": self._profit_aware_evaluation_real,
            "walk_forward_evaluation": self._walk_forward_evaluation_real,
            "gate_policy_replay_evaluation": self._gate_policy_replay_sample,
            "model_quality_validation": self._quality_validation_real,
        }.get(stage, self._real_stage_not_available(stage, reason="missing_real_stage_handler"))

    def _dry_run_stage_handler(
        self,
        stage: str,
    ) -> Callable[[TrainingPipelineConfig, dict[str, Any]], dict[str, Any]]:
        mapping = {
            "health_check": self._health_check_sample,
            "db_check": self._skip_stage("Dry-run does not require DB access"),
            "gate_policy_replay_evaluation": self._gate_policy_replay_sample,
            "model_quality_validation": self._quality_validation_sample,
        }
        return mapping.get(stage, self._skip_stage("Dry-run simulated stage"))

    def _sample_mode_stage_handler(
        self,
        stage: str,
    ) -> Callable[[TrainingPipelineConfig, dict[str, Any]], dict[str, Any]]:
        mapping = {
            "health_check": self._health_check_sample,
            "db_check": self._skip_stage("Sample mode does not require DB access"),
            "load_candles": self._sample_payload_stage(
                "Sample long-history candle load simulated",
                {"candles_loaded": 8433},
            ),
            "check_candle_gaps": self._sample_payload_stage(
                "Sample candle gap check simulated",
                {"gap_count": 0},
            ),
            "build_features": self._sample_payload_stage(
                "Sample feature build simulated",
                {"feature_version": "fv1", "feature_rows": 8433},
            ),
            "build_labels": self._sample_payload_stage(
                "Sample label build simulated",
                {"label_version": "sample_lv1", "label_rows": 8433},
            ),
            "build_dataset": self._sample_payload_stage(
                "Sample dataset build simulated",
                {
                    "dataset_rows": 8433,
                    "train_rows": 5903,
                    "validation_rows": 1265,
                    "test_rows": 1265,
                },
            ),
            "train_model": self._sample_payload_stage(
                "Sample training simulated",
                {
                    "model_version": "ml_candle_mlp_sample_v1",
                    "training_run_id": "sample_training_run_ml26",
                    "model_accuracy": 0.3927,
                    "collapse_detected": False,
                },
            ),
            "probability_diagnostics": self._sample_payload_stage(
                "Sample probability diagnostics generated",
                {
                    "total_rows": 1265,
                    "predicted_direction_ratios": {
                        "UP": 0.39,
                        "DOWN": 0.34,
                        "FLAT": 0.27,
                    },
                },
            ),
            "baseline_compare": self._sample_payload_stage(
                "Sample baseline comparison generated",
                {
                    "baseline_accuracy": 0.3783,
                    "baseline_name": "majority_class",
                },
            ),
            "calibration_diagnostics": self._sample_payload_stage(
                "Sample calibration diagnostics generated",
                {
                    "calibration_status": "ACCEPTABLE_SAMPLE",
                    "expected_calibration_error": 0.061,
                    "brier_score": 0.612,
                },
            ),
            "profit_aware_evaluation": self._sample_payload_stage(
                "Sample profit-aware evaluation generated",
                {"profit_aware_status": "NEEDS_MORE_DATA"},
            ),
            "walk_forward_evaluation": self._sample_payload_stage(
                "Sample walk-forward evaluation generated",
                {
                    "walk_forward_status": "NEEDS_MORE_DATA",
                    "summary": {"fold_count": 1, "total_test_signal_count": 5},
                },
            ),
            "gate_policy_replay_evaluation": self._gate_policy_replay_sample,
            "model_quality_validation": self._quality_validation_sample,
        }
        return mapping.get(stage, self._skip_stage("Sample mode simulated stage"))

    def _health_check_real(
        self,
        config: TrainingPipelineConfig,
        stage_payloads: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "status": COMPLETED,
            "message": "Health check completed",
            "data": self._build_health_payload(),
        }

    def _health_check_sample(
        self,
        config: TrainingPipelineConfig,
        stage_payloads: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "status": COMPLETED,
            "message": "Health check completed in simulated mode",
            "data": self._build_health_payload(),
        }

    def _db_check_real(
        self,
        config: TrainingPipelineConfig,
        stage_payloads: dict[str, Any],
    ) -> dict[str, Any]:
        with get_session() as session:
            session.execute(text("SELECT 1"))
        return {
            "status": COMPLETED,
            "message": "Database check completed",
            "data": {"db_check": "ok"},
        }

    def _load_candles_real(
        self,
        config: TrainingPipelineConfig,
        stage_payloads: dict[str, Any],
    ) -> dict[str, Any]:
        start_at, end_at = self._build_utc_date_range(
            self._parse_date(config.start_date),
            self._parse_date(config.resolved_end_date()),
        )
        with get_session() as session:
            repository = CandleRepository(session)
            loader = HistoricalLoader(client=BinanceClient(), repository=repository)
            result = loader.load_range(
                symbol=config.symbol,
                interval=config.interval,
                start_at=start_at,
                end_at=end_at,
            )
        return {
            "status": COMPLETED,
            "message": "Historical candles loaded",
            "data": dict(result),
        }

    def _check_candle_gaps_real(
        self,
        config: TrainingPipelineConfig,
        stage_payloads: dict[str, Any],
    ) -> dict[str, Any]:
        start_at, end_at = self._build_utc_date_range(
            self._parse_date(config.start_date),
            self._parse_date(config.resolved_end_date()),
        )
        checker = CandleGapChecker()
        with get_session() as session:
            repository = CandleRepository(session)
            candles = repository.get_range(
                symbol=config.symbol,
                interval=config.interval,
                start_at=start_at,
                end_at=end_at,
            )
        result = checker.check(
            candles=candles,
            interval=config.interval,
            start_at=start_at,
            end_at=end_at,
            symbol=config.symbol,
        )
        return {
            "status": COMPLETED,
            "message": "Candle gap check completed",
            "data": dict(result),
        }

    def _build_features_real(
        self,
        config: TrainingPipelineConfig,
        stage_payloads: dict[str, Any],
    ) -> dict[str, Any]:
        feature_version = config.feature_version
        start_at, end_at = self._resolved_datetime_range(config)
        with get_session() as session:
            candle_repository = CandleRepository(session)
            feature_repository = FeatureRepository(session)
            pipeline = FeaturePipeline(
                candle_repository=candle_repository,
                feature_repository=feature_repository,
            )
            result = pipeline.build_and_store(
                symbol=config.symbol,
                interval=config.interval,
                feature_version=feature_version,
                start_at=start_at,
                end_at=end_at,
            )
        return {
            "status": COMPLETED,
            "message": "Features built",
            "data": dict(result),
        }

    def _build_labels_real(
        self,
        config: TrainingPipelineConfig,
        stage_payloads: dict[str, Any],
    ) -> dict[str, Any]:
        label_version = self.DEFAULT_LABEL_VERSION
        horizon_candles = self._resolve_horizon_from_label_version(label_version)
        label_config = LabelConfig(
            label_version=label_version,
            horizon_candles=horizon_candles,
            direction_atr_threshold=self.DEFAULT_DIRECTION_ATR_THRESHOLD,
            take_profit_atr=self.DEFAULT_TAKE_PROFIT_ATR,
            stop_loss_atr=self.DEFAULT_STOP_LOSS_ATR,
            flat_class_enabled=True,
            label_mode=self.DEFAULT_LABEL_MODE,
            setup_quality_min_threshold=config.setup_quality_min_threshold,
            setup_quality_decision_mask_enabled=config.setup_quality_decision_mask_enabled,
            setup_quality_decision_mask_min_threshold=config.setup_quality_decision_mask_min_threshold,
        )
        start_at, end_at = self._resolved_datetime_range(config)
        with get_session() as session:
            candle_repository = CandleRepository(session)
            feature_repository = FeatureRepository(session)
            label_repository = LabelRepository(session)
            if hasattr(candle_repository, "get_range"):
                candles = candle_repository.get_range(
                    symbol=config.symbol,
                    interval=config.interval,
                    start_at=start_at,
                    end_at=end_at,
                )
            else:
                candles = candle_repository.get_all(
                    symbol=config.symbol,
                    interval=config.interval,
                )
            
            if hasattr(feature_repository, "get_range"):
                feature_rows = feature_repository.get_range(
                    symbol=config.symbol,
                    interval=config.interval,
                    feature_version=config.feature_version,
                    start_at=start_at,
                    end_at=end_at,
                )
            else:
                feature_rows = feature_repository.get_all(
                    symbol=config.symbol,
                    interval=config.interval,
                    feature_version=config.feature_version,
                )
            regime_builder_result = RegimeLabelBuilder().build(
                candles=candles,
                symbol=config.symbol,
                interval=config.interval,
                feature_rows=feature_rows,
                base_config=label_config,
            )
            builder = LabelBuilder()
            records = list(regime_builder_result.records)
            regime_label_builder_status = regime_builder_result.to_dict()
            label_mode_rows = list(regime_builder_result.label_mode_rows)
            label_mode_comparison_audit = LabelModeComparisonAudit().evaluate(label_mode_rows)
            flat_subtype_audit = FlatSubtypeAudit().evaluate(label_mode_rows)
            setup_aware_label_diagnostics = SetupAwareLabelDiagnostics().evaluate(label_mode_rows)
            opportunity_diagnostics = OpportunityDiagnostics().evaluate(label_mode_rows)
            if not records:
                return {
                    "status": FAILED,
                    "message": "Runtime regime labels were not built",
                    "data": {
                        "symbol": config.symbol,
                        "interval": config.interval,
                        "horizon_candles": horizon_candles,
                        "label_version": label_version,
                        "start_at": start_at.isoformat(),
                        "end_at": end_at.isoformat(),
                        "date_range_limited": True,
                        "candles_used": len(candles),
                        "built": 0,
                        "inserted_or_updated": 0,
                        "direction_counts": {},
                        "direction_atr_threshold": self.DEFAULT_DIRECTION_ATR_THRESHOLD,
                        "take_profit_atr": self.DEFAULT_TAKE_PROFIT_ATR,
                        "stop_loss_atr": self.DEFAULT_STOP_LOSS_ATR,
                        "flat_class_enabled": True,
                        "label_mode": self.DEFAULT_LABEL_MODE,
                        "exit_policy_profile": config.exit_policy_profile,
                        "exit_timeout_bars": config.exit_timeout_bars,
                        "exit_mitigation_loss_r": config.exit_mitigation_loss_r,
                        "exit_neutral_abs_r": config.exit_neutral_abs_r,
                        "directional_side_filter_profile": config.directional_side_filter_profile,
                        "allowed_signal_directions": list(config.allowed_signal_directions or []),
                        "side_aware_validation_relaxation_enabled": config.side_aware_validation_relaxation_enabled,
                        "side_aware_min_validation_signal_count": config.side_aware_min_validation_signal_count,
                        "side_aware_min_validation_profit_factor": config.side_aware_min_validation_profit_factor,
                        "side_aware_min_validation_total_r": config.side_aware_min_validation_total_r,
                        "side_aware_min_validation_expectancy_r": config.side_aware_min_validation_expectancy_r,
                        "side_aware_allow_single_direction_validation": config.side_aware_allow_single_direction_validation,
                        "research_only_total_r_repair_enabled": config.research_only_total_r_repair_enabled,
                        "validation_total_r_repair_profile": config.validation_total_r_repair_profile,
                        "research_only_acceptance_block_reason": config.research_only_acceptance_block_reason,
                        "research_only_fold_repair_probe_enabled": config.research_only_fold_repair_probe_enabled,
                        "fold_repair_probe_profile": config.fold_repair_probe_profile,
                        "fold_repair_target_dates": list(config.fold_repair_target_dates),
                        "fold_repair_time_slice_blackout_enabled": config.fold_repair_time_slice_blackout_enabled,
                        "fold_repair_blackout_dates": list(config.fold_repair_blackout_dates),
                        "config_id": label_version,
                        "training_objective": config.training_objective,
                        "decision_calibration_enabled": config.decision_calibration_enabled,
                        "decision_flat_if_max_prob_below": config.decision_flat_if_max_prob_below,
                        "decision_flat_if_margin_below": config.decision_flat_if_margin_below,
                        "decision_min_direction_prob": config.decision_min_direction_prob,
                        "decision_min_up_down_margin": config.decision_min_up_down_margin,
                        "decision_down_boost": config.decision_down_boost,
                        "decision_up_penalty": config.decision_up_penalty,
                        "decision_flat_boost": config.decision_flat_boost,
                        "decision_calibration_mode": config.decision_calibration_mode,
                        "decision_fallback_to_raw": config.decision_fallback_to_raw,
                        "decision_max_flat_ratio": config.decision_max_flat_ratio,
                        "decision_min_down_ratio_when_actual_down_high": config.decision_min_down_ratio_when_actual_down_high,
                        "decision_min_up_ratio_when_actual_up_high": config.decision_min_up_ratio_when_actual_up_high,
                        "decision_max_dominant_class_ratio": config.decision_max_dominant_class_ratio,
                        "decision_require_non_worse_baseline_edge": config.decision_require_non_worse_baseline_edge,
                        "decision_baseline_edge_tolerance": config.decision_baseline_edge_tolerance,
                        "decision_actual_class_high_threshold": config.decision_actual_class_high_threshold,
                        "decision_policy_grid_enabled": config.decision_policy_grid_enabled,
                        "decision_policy_grid_stage": config.decision_policy_grid_stage,
                        "setup_quality_min_threshold": config.setup_quality_min_threshold,
                        "setup_quality_decision_mask_enabled": config.setup_quality_decision_mask_enabled,
                        "setup_quality_decision_mask_min_threshold": config.setup_quality_decision_mask_min_threshold,
                        "entry_path_quality_filter_enabled": bool(config.entry_path_quality_filter_enabled),
                        "entry_path_quality_min_threshold": config.entry_path_quality_min_threshold,
                        "stop_pressure_max_risk_score": config.stop_pressure_max_risk_score,
                        "mae_pressure_max_risk_score": config.mae_pressure_max_risk_score,
                        "regime_label_builder_status": regime_label_builder_status,
                        "label_mode_comparison_audit": label_mode_comparison_audit,
                        "flat_subtype_audit": flat_subtype_audit,
                        "setup_aware_label_diagnostics": setup_aware_label_diagnostics,
                        "opportunity_diagnostics": opportunity_diagnostics,
                        "first_open_time": None,
                        "last_open_time": None,
                    },
                }
            inserted_or_updated = label_repository.upsert_many(
                [record.to_dict() for record in records]
            )
            label_counts = builder.summarize(records)
        return {
            "status": COMPLETED,
            "message": "Labels built",
            "data": {
                "symbol": config.symbol,
                "interval": config.interval,
                "horizon_candles": horizon_candles,
                "label_version": label_version,
                "start_at": start_at.isoformat(),
                "end_at": end_at.isoformat(),
                "date_range_limited": True,
                "candles_used": len(candles),
                "built": len(records),
                "inserted_or_updated": inserted_or_updated,
                "direction_counts": label_counts,
                "direction_atr_threshold": self.DEFAULT_DIRECTION_ATR_THRESHOLD,
                "take_profit_atr": self.DEFAULT_TAKE_PROFIT_ATR,
                "stop_loss_atr": self.DEFAULT_STOP_LOSS_ATR,
                "flat_class_enabled": True,
                "label_mode": self.DEFAULT_LABEL_MODE,
                "exit_policy_profile": config.exit_policy_profile,
                "exit_timeout_bars": config.exit_timeout_bars,
                "exit_mitigation_loss_r": config.exit_mitigation_loss_r,
                "exit_neutral_abs_r": config.exit_neutral_abs_r,
                "directional_side_filter_profile": config.directional_side_filter_profile,
                "allowed_signal_directions": list(config.allowed_signal_directions or []),
                "side_aware_validation_relaxation_enabled": config.side_aware_validation_relaxation_enabled,
                "side_aware_min_validation_signal_count": config.side_aware_min_validation_signal_count,
                "side_aware_min_validation_profit_factor": config.side_aware_min_validation_profit_factor,
                "side_aware_min_validation_total_r": config.side_aware_min_validation_total_r,
                "side_aware_min_validation_expectancy_r": config.side_aware_min_validation_expectancy_r,
                "side_aware_allow_single_direction_validation": config.side_aware_allow_single_direction_validation,
                "research_only_total_r_repair_enabled": config.research_only_total_r_repair_enabled,
                "validation_total_r_repair_profile": config.validation_total_r_repair_profile,
                "research_only_acceptance_block_reason": config.research_only_acceptance_block_reason,
                "research_only_fold_repair_probe_enabled": config.research_only_fold_repair_probe_enabled,
                "fold_repair_probe_profile": config.fold_repair_probe_profile,
                "fold_repair_target_dates": list(config.fold_repair_target_dates),
                "fold_repair_time_slice_blackout_enabled": config.fold_repair_time_slice_blackout_enabled,
                "fold_repair_blackout_dates": list(config.fold_repair_blackout_dates),
                "config_id": label_version,
                "training_objective": config.training_objective,
                "decision_calibration_enabled": config.decision_calibration_enabled,
                "decision_flat_if_max_prob_below": config.decision_flat_if_max_prob_below,
                "decision_flat_if_margin_below": config.decision_flat_if_margin_below,
                "decision_min_direction_prob": config.decision_min_direction_prob,
                "decision_min_up_down_margin": config.decision_min_up_down_margin,
                "decision_down_boost": config.decision_down_boost,
                "decision_up_penalty": config.decision_up_penalty,
                "decision_flat_boost": config.decision_flat_boost,
                "decision_calibration_mode": config.decision_calibration_mode,
                "decision_fallback_to_raw": config.decision_fallback_to_raw,
                "decision_max_flat_ratio": config.decision_max_flat_ratio,
                "decision_min_down_ratio_when_actual_down_high": config.decision_min_down_ratio_when_actual_down_high,
                "decision_min_up_ratio_when_actual_up_high": config.decision_min_up_ratio_when_actual_up_high,
                "decision_max_dominant_class_ratio": config.decision_max_dominant_class_ratio,
                "decision_require_non_worse_baseline_edge": config.decision_require_non_worse_baseline_edge,
                "decision_baseline_edge_tolerance": config.decision_baseline_edge_tolerance,
                "decision_actual_class_high_threshold": config.decision_actual_class_high_threshold,
                "decision_policy_grid_enabled": config.decision_policy_grid_enabled,
                "decision_policy_grid_stage": config.decision_policy_grid_stage,
                "setup_quality_min_threshold": config.setup_quality_min_threshold,
                "setup_quality_decision_mask_enabled": config.setup_quality_decision_mask_enabled,
                "setup_quality_decision_mask_min_threshold": config.setup_quality_decision_mask_min_threshold,
                "entry_path_quality_filter_enabled": bool(config.entry_path_quality_filter_enabled),
                "entry_path_quality_min_threshold": config.entry_path_quality_min_threshold,
                "stop_pressure_max_risk_score": config.stop_pressure_max_risk_score,
                "mae_pressure_max_risk_score": config.mae_pressure_max_risk_score,
                "regime_label_builder_status": regime_label_builder_status,
                "label_mode_comparison_audit": label_mode_comparison_audit,
                "flat_subtype_audit": flat_subtype_audit,
                "setup_aware_label_diagnostics": setup_aware_label_diagnostics,
                "opportunity_diagnostics": opportunity_diagnostics,
                "first_open_time": records[0].candle_open_time.isoformat() if records else None,
                "last_open_time": records[-1].candle_open_time.isoformat() if records else None,
            },
        }

    def _build_dataset_real(
        self,
        config: TrainingPipelineConfig,
        stage_payloads: dict[str, Any],
    ) -> dict[str, Any]:
        feature_version = config.feature_version
        label_version = self.DEFAULT_LABEL_VERSION
        horizon_candles = self._resolve_horizon_from_label_version(label_version)
        start_at, end_at = self._resolved_datetime_range(config)
        with get_session() as session:
            feature_repository = FeatureRepository(session)
            label_repository = LabelRepository(session)
            builder = DatasetBuilder(
                feature_repository=feature_repository,
                label_repository=label_repository,
            )
            result = builder.build(
                symbol=config.symbol,
                interval=config.interval,
                horizon_candles=horizon_candles,
                feature_version=feature_version,
                label_version=label_version,
                start_at=start_at,
                end_at=end_at,
            )
        return {
            "status": COMPLETED,
            "message": "Dataset built",
            "data": dict(result),
        }

    def _train_model_real(
        self,
        config: TrainingPipelineConfig,
        stage_payloads: dict[str, Any],
    ) -> dict[str, Any]:
        feature_version = config.feature_version
        label_version = self.DEFAULT_LABEL_VERSION
        horizon_candles = self._resolve_horizon_from_label_version(label_version)
        dataset_summary = dict(stage_payloads.get("build_dataset", {}))
        start_at, end_at = self._resolved_datetime_range(config)
        class_margin_objective_decision = {
            "diagnostic_name": "class_margin_objective_decision",
            "diagnostic_version": "ml38_10_3",
            "class_margin_objective_allowed": False,
            "reason": "class_margin_config_disabled",
            "required_diagnostics": [],
            "missing_diagnostics": [],
            "class_margin_objective_enabled": False,
        }
        if config.class_margin_objective_enabled:
            class_margin_objective_decision = load_latest_class_margin_runtime_evidence()
            class_margin_objective_decision["class_margin_objective_enabled"] = True
        with get_session() as session:
            feature_repository = FeatureRepository(session)
            label_repository = LabelRepository(session)
            dataset_builder = DatasetBuilder(
                feature_repository=feature_repository,
                label_repository=label_repository,
            )
            artifact_storage = ArtifactStorage()
            model_registry_repository = ModelRegistryRepository(session)
            training_run_repository = TrainingRunRepository(session)
            model_registry = ModelRegistry(
                repository=model_registry_repository,
                artifact_storage=artifact_storage,
            )
            service = TrainingService(
                dataset_builder=dataset_builder,
                model_registry=model_registry,
                training_run_repository=training_run_repository,
                artifact_storage=artifact_storage,
            )
            result = service.train(
                symbol=config.symbol,
                interval=config.interval,
                horizon_candles=horizon_candles,
                feature_version=feature_version,
                label_version=label_version,
                model_name=self.DEFAULT_MODEL_NAME,
                start_at=start_at,
                end_at=end_at,
                training_objective=config.training_objective,
                direction_loss_name=self.DEFAULT_DIRECTION_LOSS_NAME,
                focal_gamma=self.DEFAULT_FOCAL_GAMMA,
                label_smoothing=self.DEFAULT_LABEL_SMOOTHING,
                opportunity_loss_weight=self.DEFAULT_OPPORTUNITY_LOSS_WEIGHT,
                confidence_margin_weight=self.DEFAULT_CONFIDENCE_MARGIN_WEIGHT,
                confidence_margin_target=self.DEFAULT_CONFIDENCE_MARGIN_TARGET,
                probability_temperature_enabled=self.DEFAULT_PROBABILITY_TEMPERATURE_ENABLED,
                direction_loss_weight=self.DEFAULT_DIRECTION_LOSS_WEIGHT,
                tp_sl_loss_weight=self.DEFAULT_TP_SL_LOSS_WEIGHT,
                move_loss_weight=self.DEFAULT_MOVE_LOSS_WEIGHT,
                risk_loss_weight=self.DEFAULT_RISK_LOSS_WEIGHT,
                direction_logit_gap_weight=self.DEFAULT_DIRECTION_LOGIT_GAP_WEIGHT,
                direction_logit_gap_target=self.DEFAULT_DIRECTION_LOGIT_GAP_TARGET,
                direction_distribution_loss_weight=self.DEFAULT_DIRECTION_DISTRIBUTION_LOSS_WEIGHT,
                flat_probability_floor_weight=self.DEFAULT_FLAT_PROBABILITY_FLOOR_WEIGHT,
                flat_probability_floor_target=self.DEFAULT_FLAT_PROBABILITY_FLOOR_TARGET,
                min_class_probability_floor=self.DEFAULT_MIN_CLASS_PROBABILITY_FLOOR,
                class_probability_floor_weight=self.DEFAULT_CLASS_PROBABILITY_FLOOR_WEIGHT,
                class_probability_floor_targets=self.DEFAULT_CLASS_PROBABILITY_FLOOR_TARGETS,
                dominant_class_ceiling_weight=self.DEFAULT_DOMINANT_CLASS_CEILING_WEIGHT,
                dominant_class_ceiling_target=self.DEFAULT_DOMINANT_CLASS_CEILING_TARGET,
                label_noise_hardening_enabled=self.DEFAULT_LABEL_NOISE_HARDENING_ENABLED,
                baseline_edge_objective_enabled=config.baseline_edge_objective_enabled,
                baseline_edge_focal_gamma=config.baseline_edge_focal_gamma,
                baseline_edge_margin_penalty=config.baseline_edge_margin_penalty,
                baseline_edge_entropy_penalty=config.baseline_edge_entropy_penalty,
                class_margin_objective_enabled=config.class_margin_objective_enabled,
                class_margin_objective_allowed=bool(
                    class_margin_objective_decision.get("class_margin_objective_allowed", False)
                ),
                class_margin_objective_reason=str(
                    class_margin_objective_decision.get("reason") or "class_margin_config_disabled"
                ),
                class_margin_feature_separability_rating=class_margin_objective_decision.get(
                    "feature_separability_rating"
                ),
                true_class_margin_weight=config.true_class_margin_weight,
                true_class_margin_target=config.true_class_margin_target,
                up_down_margin_weight=config.up_down_margin_weight,
                up_down_margin_target=config.up_down_margin_target,
                flat_margin_weight=config.flat_margin_weight,
                flat_margin_target=config.flat_margin_target,
                hard_negative_margin_weight=config.hard_negative_margin_weight,
                hard_negative_margin_target=config.hard_negative_margin_target,
                opportunity_probability_threshold=config.opportunity_probability_threshold,
                setup_quality_min_threshold=config.setup_quality_min_threshold,
                setup_quality_decision_mask_enabled=config.setup_quality_decision_mask_enabled,
                setup_quality_decision_mask_min_threshold=config.setup_quality_decision_mask_min_threshold,
                opportunity_threshold_sweep_enabled=config.opportunity_threshold_sweep_enabled,
                opportunity_threshold_candidates=tuple(config.opportunity_threshold_candidates),
                opportunity_min_precision=config.opportunity_min_precision,
                opportunity_min_recall=config.opportunity_min_recall,
                opportunity_max_predicted_trade_rate=config.opportunity_max_predicted_trade_rate,
                opportunity_max_predicted_to_actual_trade_rate_ratio=(
                    config.opportunity_max_predicted_to_actual_trade_rate_ratio
                ),
                opportunity_max_false_positive_rate=config.opportunity_max_false_positive_rate,
                entry_path_quality_filter_enabled=bool(config.entry_path_quality_filter_enabled),
                entry_path_quality_min_threshold=config.entry_path_quality_min_threshold,
                stop_pressure_max_risk_score=config.stop_pressure_max_risk_score,
                mae_pressure_max_risk_score=config.mae_pressure_max_risk_score,
            )
        test_metrics = dict(result.get("test_metrics", {}))
        return {
            "status": COMPLETED,
            "message": "Model training completed",
            "data": {
                **dict(result),
                "training_run_id": result.get("run_id"),
                "model_accuracy": test_metrics.get("accuracy"),
                "dataset_summary": dataset_summary,
                "dataset_rows": int(dataset_summary.get("dataset_rows", 0)),
                "train_rows": int(dataset_summary.get("train_rows", 0)),
                "validation_rows": int(dataset_summary.get("validation_rows", 0)),
                "val_rows": int(dataset_summary.get("validation_rows", 0)),
                "test_rows": int(dataset_summary.get("test_rows", 0)),
                "feature_version": feature_version,
                "label_version": label_version,
                "horizon_candles": horizon_candles,
                "sample_mode": False,
                "real_training_executed": True,
                "start_at": start_at.isoformat(),
                "end_at": end_at.isoformat(),
                "date_range_limited": True,
                "training_objective": config.training_objective,
                "direction_loss_name": self.DEFAULT_DIRECTION_LOSS_NAME,
                "focal_gamma": self.DEFAULT_FOCAL_GAMMA,
                "label_smoothing": self.DEFAULT_LABEL_SMOOTHING,
                "opportunity_loss_weight": self.DEFAULT_OPPORTUNITY_LOSS_WEIGHT,
                "confidence_margin_weight": self.DEFAULT_CONFIDENCE_MARGIN_WEIGHT,
                "confidence_margin_target": self.DEFAULT_CONFIDENCE_MARGIN_TARGET,
                "probability_temperature_enabled": self.DEFAULT_PROBABILITY_TEMPERATURE_ENABLED,
                "direction_loss_weight": self.DEFAULT_DIRECTION_LOSS_WEIGHT,
                "tp_sl_loss_weight": self.DEFAULT_TP_SL_LOSS_WEIGHT,
                "move_loss_weight": self.DEFAULT_MOVE_LOSS_WEIGHT,
                "risk_loss_weight": self.DEFAULT_RISK_LOSS_WEIGHT,
                "direction_logit_gap_weight": self.DEFAULT_DIRECTION_LOGIT_GAP_WEIGHT,
                "direction_logit_gap_target": self.DEFAULT_DIRECTION_LOGIT_GAP_TARGET,
                "direction_distribution_loss_weight": self.DEFAULT_DIRECTION_DISTRIBUTION_LOSS_WEIGHT,
                "flat_probability_floor_weight": self.DEFAULT_FLAT_PROBABILITY_FLOOR_WEIGHT,
                "flat_probability_floor_target": self.DEFAULT_FLAT_PROBABILITY_FLOOR_TARGET,
                "min_class_probability_floor": self.DEFAULT_MIN_CLASS_PROBABILITY_FLOOR,
                "class_probability_floor_weight": self.DEFAULT_CLASS_PROBABILITY_FLOOR_WEIGHT,
                "class_probability_floor_targets": list(self.DEFAULT_CLASS_PROBABILITY_FLOOR_TARGETS),
                "dominant_class_ceiling_weight": self.DEFAULT_DOMINANT_CLASS_CEILING_WEIGHT,
                "dominant_class_ceiling_target": self.DEFAULT_DOMINANT_CLASS_CEILING_TARGET,
                "label_noise_hardening_enabled": self.DEFAULT_LABEL_NOISE_HARDENING_ENABLED,
                "baseline_edge_objective_enabled": config.baseline_edge_objective_enabled,
                "baseline_edge_focal_gamma": config.baseline_edge_focal_gamma,
                "baseline_edge_margin_penalty": config.baseline_edge_margin_penalty,
                "baseline_edge_entropy_penalty": config.baseline_edge_entropy_penalty,
                "baseline_edge_gate_min": config.baseline_edge_gate_min,
                "collapse_critical_gate_enabled": config.collapse_critical_gate_enabled,
                "decision_calibration_enabled": config.decision_calibration_enabled,
                "decision_flat_if_max_prob_below": config.decision_flat_if_max_prob_below,
                "decision_flat_if_margin_below": config.decision_flat_if_margin_below,
                "decision_min_direction_prob": config.decision_min_direction_prob,
                "decision_min_up_down_margin": config.decision_min_up_down_margin,
                "decision_down_boost": config.decision_down_boost,
                "decision_up_penalty": config.decision_up_penalty,
                "decision_flat_boost": config.decision_flat_boost,
                "decision_calibration_mode": config.decision_calibration_mode,
                "decision_fallback_to_raw": config.decision_fallback_to_raw,
                "decision_max_flat_ratio": config.decision_max_flat_ratio,
                "decision_min_down_ratio_when_actual_down_high": config.decision_min_down_ratio_when_actual_down_high,
                "decision_min_up_ratio_when_actual_up_high": config.decision_min_up_ratio_when_actual_up_high,
                "decision_max_dominant_class_ratio": config.decision_max_dominant_class_ratio,
                "decision_require_non_worse_baseline_edge": config.decision_require_non_worse_baseline_edge,
                "decision_baseline_edge_tolerance": config.decision_baseline_edge_tolerance,
                "decision_actual_class_high_threshold": config.decision_actual_class_high_threshold,
                "decision_policy_grid_enabled": config.decision_policy_grid_enabled,
                "decision_policy_grid_stage": config.decision_policy_grid_stage,
                "opportunity_probability_threshold": config.opportunity_probability_threshold,
                "setup_quality_min_threshold": config.setup_quality_min_threshold,
                "setup_quality_decision_mask_enabled": config.setup_quality_decision_mask_enabled,
                "setup_quality_decision_mask_min_threshold": config.setup_quality_decision_mask_min_threshold,
                "opportunity_threshold_sweep_enabled": config.opportunity_threshold_sweep_enabled,
                "entry_path_quality_filter_enabled": bool(config.entry_path_quality_filter_enabled),
                "entry_path_quality_min_threshold": config.entry_path_quality_min_threshold,
                "stop_pressure_max_risk_score": config.stop_pressure_max_risk_score,
                "mae_pressure_max_risk_score": config.mae_pressure_max_risk_score,
                "opportunity_threshold_candidates": list(config.opportunity_threshold_candidates),
                "opportunity_min_precision": config.opportunity_min_precision,
                "opportunity_min_recall": config.opportunity_min_recall,
                "opportunity_max_predicted_trade_rate": config.opportunity_max_predicted_trade_rate,
                "opportunity_max_predicted_to_actual_trade_rate_ratio": (
                    config.opportunity_max_predicted_to_actual_trade_rate_ratio
                ),
                "opportunity_max_false_positive_rate": config.opportunity_max_false_positive_rate,
                "class_margin_objective_enabled": config.class_margin_objective_enabled,
                "class_margin_objective_decision": class_margin_objective_decision,
                "true_class_margin_weight": config.true_class_margin_weight,
                "true_class_margin_target": config.true_class_margin_target,
                "up_down_margin_weight": config.up_down_margin_weight,
                "up_down_margin_target": config.up_down_margin_target,
                "flat_margin_weight": config.flat_margin_weight,
                "flat_margin_target": config.flat_margin_target,
                "hard_negative_margin_weight": config.hard_negative_margin_weight,
                "hard_negative_margin_target": config.hard_negative_margin_target,
            },
        }

    def _probability_diagnostics_real(
        self,
        config: TrainingPipelineConfig,
        stage_payloads: dict[str, Any],
    ) -> dict[str, Any]:
        model_version = self._require_model_version(stage_payloads, "probability_diagnostics")
        start_at, end_at = self._resolved_datetime_range(config)
        result = self._with_diagnostics_service(
            lambda service: service.probability_report(
                model_version=model_version,
                symbol=config.symbol,
                interval=config.interval,
                horizon_candles=self._resolve_horizon_from_label_version(self.DEFAULT_LABEL_VERSION),
                feature_version=config.feature_version,
                label_version=self.DEFAULT_LABEL_VERSION,
                start_at=start_at,
                end_at=end_at,
                label_config=self._label_config_summary(config, stage_payloads),
            )
        )
        collapse_v2 = result.get("collapse_v2", {})
        payload = dict(result)
        payload["collapse_detected"] = bool(collapse_v2.get("collapse_detected", False))
        payload["start_at"] = start_at.isoformat()
        payload["end_at"] = end_at.isoformat()
        payload["date_range_limited"] = True
        return {
            "status": COMPLETED,
            "message": "Probability diagnostics generated",
            "data": payload,
        }

    def _baseline_compare_real(
        self,
        config: TrainingPipelineConfig,
        stage_payloads: dict[str, Any],
    ) -> dict[str, Any]:
        model_version = self._require_model_version(stage_payloads, "baseline_compare")
        start_at, end_at = self._resolved_datetime_range(config)
        result = self._with_diagnostics_service(
            lambda service: service.compare_models(
                symbol=config.symbol,
                interval=config.interval,
                horizon_candles=self._resolve_horizon_from_label_version(self.DEFAULT_LABEL_VERSION),
                feature_version=config.feature_version,
                label_version=self.DEFAULT_LABEL_VERSION,
                train_end=None,
                validation_end=None,
                start_at=start_at,
                end_at=end_at,
                model_versions=[model_version],
                skip_incompatible_models=False,
            )
        )
        payload = dict(result)
        payload["baseline_accuracy"] = self._extract_baseline_accuracy(result)
        payload["candidate_model_version"] = model_version
        payload["start_at"] = start_at.isoformat()
        payload["end_at"] = end_at.isoformat()
        payload["date_range_limited"] = True
        return {
            "status": COMPLETED,
            "message": "Baseline comparison generated",
            "data": payload,
        }

    def _calibration_diagnostics_real(
        self,
        config: TrainingPipelineConfig,
        stage_payloads: dict[str, Any],
    ) -> dict[str, Any]:
        model_version = self._require_model_version(stage_payloads, "calibration_diagnostics")
        start_at, end_at = self._resolved_datetime_range(config)
        result = self._with_diagnostics_service(
            lambda service: service.calibration_report(
                model_version=model_version,
                symbol=config.symbol,
                interval=config.interval,
                horizon_candles=self._resolve_horizon_from_label_version(self.DEFAULT_LABEL_VERSION),
                feature_version=config.feature_version,
                label_version=self.DEFAULT_LABEL_VERSION,
                start_at=start_at,
                end_at=end_at,
            )
        )
        payload = dict(result)
        payload["start_at"] = start_at.isoformat()
        payload["end_at"] = end_at.isoformat()
        payload["date_range_limited"] = True
        return {
            "status": COMPLETED,
            "message": "Calibration diagnostics generated",
            "data": payload,
        }

    def _profit_aware_evaluation_real(
        self,
        config: TrainingPipelineConfig,
        stage_payloads: dict[str, Any],
    ) -> dict[str, Any]:
        model_version = self._require_model_version(stage_payloads, "profit_aware_evaluation")
        start_at, end_at = self._resolved_datetime_range(config)
        result = self._with_diagnostics_service(
            lambda service: service.profit_report_v2(
                model_version=model_version,
                symbol=config.symbol,
                interval=config.interval,
                horizon_candles=self._resolve_horizon_from_label_version(self.DEFAULT_LABEL_VERSION),
                feature_version=config.feature_version,
                label_version=self.DEFAULT_LABEL_VERSION,
                take_profit_atr=self.DEFAULT_TAKE_PROFIT_ATR,
                stop_loss_atr=self.DEFAULT_STOP_LOSS_ATR,
                fee_r=self.DEFAULT_FEE_R,
                slippage_r=self.DEFAULT_SLIPPAGE_R,
                same_candle_policy=self.DEFAULT_SAME_CANDLE_POLICY,
                start_at=start_at,
                end_at=end_at,
                exit_policy_profile=config.exit_policy_profile,
                exit_timeout_bars=config.exit_timeout_bars,
                exit_mitigation_loss_r=config.exit_mitigation_loss_r,
                exit_neutral_abs_r=config.exit_neutral_abs_r,
                directional_side_filter_profile=config.directional_side_filter_profile,
                allowed_signal_directions=config.allowed_signal_directions,
                research_only_fold_repair_probe_enabled=config.research_only_fold_repair_probe_enabled,
                fold_repair_probe_profile=config.fold_repair_probe_profile,
                fold_repair_target_dates=config.fold_repair_target_dates,
                fold_repair_time_slice_blackout_enabled=config.fold_repair_time_slice_blackout_enabled,
                fold_repair_blackout_dates=config.fold_repair_blackout_dates,
            )
        )
        payload = dict(result)
        self._merge_summary_fields(
            payload,
            summary_keys=("total_r", "profit_factor", "signal_count", "same_candle_policy"),
        )
        payload["start_at"] = start_at.isoformat()
        payload["end_at"] = end_at.isoformat()
        payload["date_range_limited"] = True
        return {
            "status": COMPLETED,
            "message": "Profit-aware evaluation generated",
            "data": payload,
        }

    def _walk_forward_evaluation_real(
        self,
        config: TrainingPipelineConfig,
        stage_payloads: dict[str, Any],
    ) -> dict[str, Any]:
        model_version = self._require_model_version(stage_payloads, "walk_forward_evaluation")
        start_at, end_at = self._resolved_datetime_range(config)
        result = self._with_diagnostics_service(
            lambda service: service.walk_forward_eval(
                model_version=model_version,
                symbol=config.symbol,
                interval=config.interval,
                horizon_candles=self._resolve_horizon_from_label_version(self.DEFAULT_LABEL_VERSION),
                feature_version=config.feature_version,
                label_version=self.DEFAULT_LABEL_VERSION,
                mode=self.DEFAULT_WALK_FORWARD_MODE,
                train_days=self.DEFAULT_WALK_FORWARD_TRAIN_DAYS,
                validation_days=self.DEFAULT_WALK_FORWARD_VALIDATION_DAYS,
                test_days=self.DEFAULT_WALK_FORWARD_TEST_DAYS,
                step_days=self.DEFAULT_WALK_FORWARD_STEP_DAYS,
                min_train_rows=self.DEFAULT_WALK_FORWARD_MIN_TRAIN_ROWS,
                take_profit_atr=self.DEFAULT_TAKE_PROFIT_ATR,
                stop_loss_atr=self.DEFAULT_STOP_LOSS_ATR,
                fee_r=self.DEFAULT_FEE_R,
                slippage_r=self.DEFAULT_SLIPPAGE_R,
                same_candle_policy=self.DEFAULT_SAME_CANDLE_POLICY,
                start_at=start_at,
                end_at=end_at,
                exit_policy_profile=config.exit_policy_profile,
                exit_timeout_bars=config.exit_timeout_bars,
                exit_mitigation_loss_r=config.exit_mitigation_loss_r,
                exit_neutral_abs_r=config.exit_neutral_abs_r,
                directional_side_filter_profile=config.directional_side_filter_profile,
                allowed_signal_directions=config.allowed_signal_directions,
                research_only_fold_repair_probe_enabled=config.research_only_fold_repair_probe_enabled,
                fold_repair_probe_profile=config.fold_repair_probe_profile,
                fold_repair_target_dates=config.fold_repair_target_dates,
                fold_repair_time_slice_blackout_enabled=config.fold_repair_time_slice_blackout_enabled,
                fold_repair_blackout_dates=config.fold_repair_blackout_dates,
                side_aware_validation_relaxation_enabled=config.side_aware_validation_relaxation_enabled,
                side_aware_min_validation_signal_count=config.side_aware_min_validation_signal_count,
                side_aware_min_validation_profit_factor=config.side_aware_min_validation_profit_factor,
                side_aware_min_validation_total_r=config.side_aware_min_validation_total_r,
                side_aware_min_validation_expectancy_r=config.side_aware_min_validation_expectancy_r,
                side_aware_allow_single_direction_validation=config.side_aware_allow_single_direction_validation,
            )
        )
        payload = dict(result)
        self._merge_summary_fields(
            payload,
            summary_keys=(
                "fold_count",
                "profitable_fold_ratio",
                "global_total_r",
                "global_profit_factor",
                "total_test_signal_count",
            ),
        )
        payload["start_at"] = start_at.isoformat()
        payload["end_at"] = end_at.isoformat()
        payload["date_range_limited"] = True
        return {
            "status": COMPLETED,
            "message": "Walk-forward evaluation generated",
            "data": payload,
        }

    def _gate_policy_replay_sample(
        self,
        config: TrainingPipelineConfig,
        stage_payloads: dict[str, Any],
    ) -> dict[str, Any]:
        if not config.run_gate_policy_replay:
            return {
                "status": SKIPPED,
                "message": "GatePolicy replay disabled by configuration",
                "data": {"run_gate_policy_replay": False},
            }
        evaluator = GatePolicyReplayEvaluator()
        reporter = GatePolicyReplayReporter()
        payloads = [
            {
                "timestamp": "2026-06-11T12:00:00Z",
                "symbol": config.symbol,
                "interval": config.interval,
                "model_version": "ml_candle_mlp_sample_v1",
                "prob_up": 0.61,
                "prob_down": 0.21,
                "prob_flat": 0.18,
                "confidence": 0.72,
                "tp_before_sl_probability": 0.64,
                "risk_score": 0.31,
                "expected_move_atr": 1.45,
                "regime": "trend_up",
            },
            {
                "timestamp": "2026-06-11T12:15:00Z",
                "symbol": config.symbol,
                "interval": config.interval,
                "model_version": "ml_candle_mlp_sample_v1",
                "prob_up": 0.15,
                "prob_down": 0.67,
                "prob_flat": 0.18,
                "confidence": 0.67,
                "tp_before_sl_probability": 0.63,
                "risk_score": 0.25,
                "expected_move_atr": 1.20,
                "regime": "trend_down",
            },
            {
                "timestamp": "2026-06-11T12:30:00Z",
                "symbol": config.symbol,
                "interval": config.interval,
                "model_version": "ml_candle_mlp_sample_v1",
                "prob_up": 0.20,
                "prob_down": 0.18,
                "prob_flat": 0.62,
                "confidence": 0.62,
                "tp_before_sl_probability": 0.59,
                "risk_score": 0.20,
                "expected_move_atr": 0.60,
                "regime": "trend_up",
            },
            {
                "timestamp": "2026-06-11T12:45:00Z",
                "symbol": config.symbol,
                "interval": config.interval,
                "model_version": "ml_candle_mlp_sample_v1",
                "prob_up": 0.40,
                "prob_down": 0.40,
                "prob_flat": 0.20,
                "confidence": 0.40,
                "tp_before_sl_probability": 0.50,
                "risk_score": 0.40,
                "expected_move_atr": 0.80,
                "regime": "trend_up",
            },
            {
                "timestamp": "2026-06-11T13:00:00Z",
                "symbol": config.symbol,
                "interval": config.interval,
                "model_version": "ml_candle_mlp_sample_v1",
                "prob_up": 0.55,
                "prob_flat": 0.45,
                "confidence": 0.55,
                "tp_before_sl_probability": 0.58,
                "regime": "trend_up",
            },
        ]
        summary = evaluator.evaluate(payloads)
        payload = reporter.compact_summary_to_dict(summary)
        payload["gate_policy_replay_status"] = "SAMPLE_ONLY"
        return {
            "status": COMPLETED,
            "message": "GatePolicy replay sample evaluation completed",
            "data": payload,
        }

    def _quality_validation_sample(
        self,
        config: TrainingPipelineConfig,
        stage_payloads: dict[str, Any],
    ) -> dict[str, Any]:
        training_summary = {
            "model_version": "ml_candle_mlp_sample_v1",
            "run_id": "sample_training_run_ml26",
            "dataset_summary": {
                "dataset_rows": 8433,
                "train_rows": 5903,
                "validation_rows": 1265,
                "test_rows": 1265,
            },
            "test_metrics": {"accuracy": 0.3927},
            "collapse_detected": False,
            "sample_mode": True,
            "real_training_executed": False,
        }
        baseline_summary = {
            "baselines": {
                "majority_class": {"test": {"accuracy": 0.3783}},
            }
        }
        probability_diagnostics = self._as_dict(stage_payloads.get("probability_diagnostics"))
        calibration_summary = self._as_dict(stage_payloads.get("calibration_diagnostics"))
        profit_aware_summary = self._as_dict(stage_payloads.get("profit_aware_evaluation"))
        walk_forward_summary = self._as_dict(stage_payloads.get("walk_forward_evaluation"))
        gate_policy_replay_summary = self._as_dict(stage_payloads.get("gate_policy_replay_evaluation"))
        label_config_summary = self._label_config_summary(config, stage_payloads)
        feature_config_summary = self._feature_config_summary(config.feature_version)
        calibrated_model_accuracy, calibrated_baseline_accuracy, calibrated_accuracy_edge = (
            self._calibrated_accuracy_triplet(probability_diagnostics)
        )
        if calibrated_model_accuracy is not None:
            training_summary["model_accuracy"] = calibrated_model_accuracy
            training_summary["test_metrics"] = dict(training_summary.get("test_metrics", {}))
            training_summary["test_metrics"]["accuracy"] = calibrated_model_accuracy
        if calibrated_baseline_accuracy is not None:
            baseline_summary["baseline_accuracy"] = calibrated_baseline_accuracy
        collapse_diagnostics_v2 = CollapseDiagnosticsV2().analyze(
            probability_report=probability_diagnostics,
            symbol=config.symbol,
            feature_version=str(feature_config_summary.get("feature_version")),
            label_version=str(label_config_summary.get("label_version")),
            accuracy_edge=(
                calibrated_accuracy_edge
                if calibrated_accuracy_edge is not None
                else self._extract_baseline_accuracy_delta(
                    training_summary=training_summary,
                    baseline_summary=baseline_summary,
                )
            ),
            walk_forward_summary=walk_forward_summary,
        )
        walk_forward_profit_diagnostics = WalkForwardProfitDiagnostics().analyze(
            symbol=config.symbol,
            feature_version=str(feature_config_summary.get("feature_version")),
            model_version=str(training_summary.get("model_version")),
            walk_forward_summary=walk_forward_summary,
            profit_aware_summary=profit_aware_summary,
        )

        result = validate_model_quality(
            training_summary=training_summary,
            baseline_summary=baseline_summary,
            probability_diagnostics=probability_diagnostics,
            calibration_summary=calibration_summary,
            profit_aware_summary=profit_aware_summary,
            walk_forward_summary=walk_forward_summary,
            gate_policy_replay_summary=gate_policy_replay_summary,
            gap_quality_summary=self._build_gap_quality_summary(config, stage_payloads),
            label_config_summary=label_config_summary,
            feature_config_summary=feature_config_summary,
            symbol=config.symbol,
            collapse_diagnostics_v2_summary=collapse_diagnostics_v2,
            regime_label_builder_status_summary=dict(
                label_config_summary.get("regime_label_builder_status", {})
            ),
            walk_forward_profit_diagnostics_summary=walk_forward_profit_diagnostics,
            profit_aware_diagnostics_summary=WalkForwardProfitDiagnostics().build_profit_aware_diagnostics(
                profit_aware_summary=profit_aware_summary
            ),
        )
        payload = ModelQualityReporter().build_full_quality_report(result)
        payload = self._attach_profit_exit_root_cause_payload(
            payload,
            profit_aware_summary=profit_aware_summary,
            walk_forward_profit_diagnostics=walk_forward_profit_diagnostics,
        )
        build_labels_payload = self._as_dict(stage_payloads.get("build_labels"))
        prediction_root_cause_audit = self._as_dict(
            probability_diagnostics.get("prediction_root_cause_audit")
        )
        if prediction_root_cause_audit:
            payload["prediction_root_cause_audit"] = prediction_root_cause_audit
        book_driven_forensic_audit = self._as_dict(
            probability_diagnostics.get("book_driven_forensic_audit")
        )
        if book_driven_forensic_audit:
            payload["book_driven_forensic_audit"] = book_driven_forensic_audit
        schwager_slice_robustness = self._as_dict(
            probability_diagnostics.get("schwager_slice_robustness")
        )
        if schwager_slice_robustness:
            payload["schwager_slice_robustness"] = schwager_slice_robustness
        class_margin_objective_decision = self._as_dict(
            training_summary.get("class_margin_objective_decision")
        )
        if class_margin_objective_decision:
            payload["class_margin_objective_decision"] = class_margin_objective_decision
        for key in (
            "label_mode_comparison_audit",
            "flat_subtype_audit",
            "setup_aware_label_diagnostics",
        ):
            value = self._as_dict(build_labels_payload.get(key))
            if value:
                payload[key] = value
        self._attach_two_stage_threshold_payload(payload=payload, training_summary=training_summary)
        payload["schwager_robustness_decision_board"] = SchwagerRobustnessDecisionBoard().evaluate(
            payload
        )
        return {
            "status": COMPLETED,
            "message": "Model quality validation sample completed",
            "data": payload,
        }

    def _quality_validation_real(
        self,
        config: TrainingPipelineConfig,
        stage_payloads: dict[str, Any],
    ) -> dict[str, Any]:
        raw_training_summary = stage_payloads.get("train_model")
        raw_baseline_summary = stage_payloads.get("baseline_compare")
        raw_probability_diagnostics = stage_payloads.get("probability_diagnostics")
        raw_calibration_summary = stage_payloads.get("calibration_diagnostics")
        raw_profit_aware_summary = stage_payloads.get("profit_aware_evaluation")
        raw_walk_forward_summary = stage_payloads.get("walk_forward_evaluation")
        raw_gate_policy_replay_summary = stage_payloads.get("gate_policy_replay_evaluation")
        training_summary = self._as_dict(raw_training_summary)
        baseline_summary = self._as_dict(raw_baseline_summary)
        probability_diagnostics = self._as_dict(raw_probability_diagnostics)
        calibration_summary = self._as_dict(raw_calibration_summary)
        profit_aware_summary = self._as_dict(raw_profit_aware_summary)
        walk_forward_summary = self._as_dict(raw_walk_forward_summary)
        gate_policy_replay_summary = self._as_dict(raw_gate_policy_replay_summary)
        label_config_summary = self._label_config_summary(config, stage_payloads)
        feature_config_summary = self._feature_config_summary(config.feature_version)
        calibrated_model_accuracy, calibrated_baseline_accuracy, calibrated_accuracy_edge = (
            self._calibrated_accuracy_triplet(probability_diagnostics)
        )
        if calibrated_model_accuracy is not None:
            training_summary["model_accuracy"] = calibrated_model_accuracy
            training_summary["test_metrics"] = dict(training_summary.get("test_metrics", {}))
            training_summary["test_metrics"]["accuracy"] = calibrated_model_accuracy
        if calibrated_baseline_accuracy is not None:
            baseline_summary["baseline_accuracy"] = calibrated_baseline_accuracy
        collapse_diagnostics_v2 = CollapseDiagnosticsV2().analyze(
            probability_report=probability_diagnostics,
            symbol=config.symbol,
            feature_version=str(feature_config_summary.get("feature_version")),
            label_version=str(label_config_summary.get("label_version")),
            accuracy_edge=(
                calibrated_accuracy_edge
                if calibrated_accuracy_edge is not None
                else self._extract_baseline_accuracy_delta(
                    training_summary=training_summary,
                    baseline_summary=baseline_summary,
                )
            ),
            walk_forward_summary=walk_forward_summary,
        )
        walk_forward_profit_helper = WalkForwardProfitDiagnostics()
        walk_forward_profit_diagnostics = walk_forward_profit_helper.analyze(
            symbol=config.symbol,
            feature_version=str(feature_config_summary.get("feature_version")),
            model_version=str(training_summary.get("model_version")),
            walk_forward_summary=walk_forward_summary,
            profit_aware_summary=profit_aware_summary,
        )
        result = validate_model_quality(
            training_summary=training_summary,
            baseline_summary=baseline_summary,
            probability_diagnostics=raw_probability_diagnostics,
            calibration_summary=raw_calibration_summary,
            profit_aware_summary=raw_profit_aware_summary,
            walk_forward_summary=raw_walk_forward_summary,
            gate_policy_replay_summary=raw_gate_policy_replay_summary,
            gap_quality_summary=self._build_gap_quality_summary(config, stage_payloads),
            label_config_summary=label_config_summary,
            feature_config_summary=feature_config_summary,
            symbol=config.symbol,
            collapse_diagnostics_v2_summary=collapse_diagnostics_v2,
            regime_label_builder_status_summary=self._as_dict(
                label_config_summary.get("regime_label_builder_status", {})
            ),
            walk_forward_profit_diagnostics_summary=walk_forward_profit_diagnostics,
            profit_aware_diagnostics_summary=walk_forward_profit_helper.build_profit_aware_diagnostics(
                profit_aware_summary=profit_aware_summary
            ),
        )
        payload = ModelQualityReporter().build_full_quality_report(result)
        payload = self._attach_profit_exit_root_cause_payload(
            payload,
            profit_aware_summary=profit_aware_summary,
            walk_forward_profit_diagnostics=walk_forward_profit_diagnostics,
        )
        build_labels_payload = self._as_dict(stage_payloads.get("build_labels"))
        prediction_root_cause_audit = self._as_dict(
            probability_diagnostics.get("prediction_root_cause_audit")
        )
        if prediction_root_cause_audit:
            payload["prediction_root_cause_audit"] = prediction_root_cause_audit
        book_driven_forensic_audit = self._as_dict(
            probability_diagnostics.get("book_driven_forensic_audit")
        )
        if book_driven_forensic_audit:
            payload["book_driven_forensic_audit"] = book_driven_forensic_audit
        schwager_slice_robustness = self._as_dict(
            probability_diagnostics.get("schwager_slice_robustness")
        )
        if schwager_slice_robustness:
            payload["schwager_slice_robustness"] = schwager_slice_robustness
        class_margin_objective_decision = self._as_dict(
            training_summary.get("class_margin_objective_decision")
        )
        if class_margin_objective_decision:
            payload["class_margin_objective_decision"] = class_margin_objective_decision
        for key in (
            "label_mode_comparison_audit",
            "flat_subtype_audit",
            "setup_aware_label_diagnostics",
        ):
            value = self._as_dict(build_labels_payload.get(key))
            if value:
                payload[key] = value
        self._attach_two_stage_threshold_payload(payload=payload, training_summary=training_summary)
        payload["schwager_robustness_decision_board"] = SchwagerRobustnessDecisionBoard().evaluate(
            payload
        )
        return {
            "status": COMPLETED,
            "message": "Model quality validation completed",
            "data": payload,
        }

    def _attach_two_stage_threshold_payload(
        self,
        *,
        payload: dict[str, Any],
        training_summary: dict[str, Any],
    ) -> None:
        test_metrics = self._as_dict(training_summary.get("test_metrics"))
        for key in (
            "opportunity_probability_threshold",
            "setup_quality_min_threshold",
            "setup_quality_decision_mask_enabled",
            "setup_quality_decision_mask_min_threshold",
            "selected_opportunity_threshold",
            "opportunity_threshold_selection",
        ):
            value = training_summary.get(key)
            if value is not None:
                payload[key] = value
        if "opportunity_threshold_selection" in training_summary:
            payload["opportunity_threshold_sweep"] = self._as_dict(
                training_summary.get("opportunity_threshold_selection")
            )
        for key in (
            "predicted_to_actual_trade_rate_ratio",
            "predicted_trade_rate",
            "actual_trade_rate",
            "raw_predicted_trade_rate",
            "masked_predicted_trade_rate",
            "opportunity_precision",
            "opportunity_recall",
            "opportunity_f1",
            "raw_opportunity_precision",
            "raw_opportunity_recall",
            "raw_opportunity_f1",
            "opportunity_false_positive_rate",
            "setup_quality_decision_mask_enabled",
            "setup_quality_decision_mask_min_threshold",
            "setup_quality_masked_row_count",
            "setup_quality_forced_no_trade_count",
            "setup_quality_mask_false_positive_removed_count",
            "setup_quality_mask_trade_prediction_removed_count",
            "setup_quality_bucket_metrics",
            "setup_quality_bucket_metrics_raw",
            "setup_quality_bucket_metrics_after_mask",
            "setup_quality_distribution",
            "setup_quality_filter_summary",
            "entry_path_quality_filter_enabled",
            "entry_path_quality_min_threshold",
            "stop_pressure_max_risk_score",
            "mae_pressure_max_risk_score",
            "entry_path_quality_masked_row_count",
            "entry_path_quality_forced_no_trade_count",
            "entry_path_quality_mask_trade_prediction_removed_count",
            "entry_path_quality_mask_false_positive_removed_count",
            "entry_path_quality_filter_summary",
            "entry_path_quality_filter_diagnostics",
            "trap_invalidation_feature_impact_audit",
        ):
            value = test_metrics.get(key)
            if value is not None:
                payload[key] = value
        if "two_stage_trade_diagnostics" in test_metrics:
            payload["two_stage_trade_diagnostics"] = self._as_dict(
                test_metrics.get("two_stage_trade_diagnostics")
            )
            diagnostics_payload = self._as_dict(test_metrics.get("two_stage_trade_diagnostics"))
            for key in (
                "setup_quality_decision_mask_summary",
                "setup_quality_bucket_metrics_raw",
                "setup_quality_bucket_metrics_after_mask",
                "entry_path_quality_filter_summary",
                "entry_path_quality_filter_diagnostics",
                "trap_invalidation_feature_impact_audit",
            ):
                value = diagnostics_payload.get(key)
                if value is not None and key not in payload:
                    payload[key] = value

    def _sample_payload_stage(
        self,
        message: str,
        payload: dict[str, Any],
    ) -> Callable[[TrainingPipelineConfig, dict[str, Any]], dict[str, Any]]:
        def handler(
            config: TrainingPipelineConfig,
            stage_payloads: dict[str, Any],
        ) -> dict[str, Any]:
            return {"status": COMPLETED, "message": message, "data": payload}

        return handler

    def _skip_load_candles_stage(
        self,
    ) -> Callable[[TrainingPipelineConfig, dict[str, Any]], dict[str, Any]]:
        """Пропускает сетевую загрузку свечей для cached training режима.

        Внешний wrapper уже проверяет PostgreSQL candle cache через
        check-candle-gaps. Поэтому внутренний candidate pipeline не должен
        повторно обращаться к Binance и не должен падать из-за сетевых timeout.
        """

        def handler(
            config: TrainingPipelineConfig,
            stage_payloads: dict[str, Any],
        ) -> dict[str, Any]:
            return {
                "status": SKIPPED,
                "message": "Candle loading skipped; using existing PostgreSQL DB cache.",
                "data": {
                    "skip_candle_load": True,
                    "candle_source": "postgresql_db_cache",
                    "symbol": config.symbol,
                    "interval": config.interval,
                    "start_date": config.start_date,
                    "end_date": config.resolved_end_date(),
                },
            }

        return handler

    def _skip_stage(
        self,
        message: str,
    ) -> Callable[[TrainingPipelineConfig, dict[str, Any]], dict[str, Any]]:
        def handler(
            config: TrainingPipelineConfig,
            stage_payloads: dict[str, Any],
        ) -> dict[str, Any]:
            return {"status": SKIPPED, "message": message, "data": {}}

        return handler

    def _real_stage_not_available(
        self,
        stage: str,
        *,
        reason: str,
    ) -> Callable[[TrainingPipelineConfig, dict[str, Any]], dict[str, Any]]:
        def handler(
            config: TrainingPipelineConfig,
            stage_payloads: dict[str, Any],
        ) -> dict[str, Any]:
            return {
                "status": SKIPPED_NOT_AVAILABLE,
                "message": f"{stage} is not available in the current real-mode wiring",
                "data": {
                    "reason": reason,
                    "symbol": config.symbol,
                    "interval": config.interval,
                    "start_date": config.start_date,
                    "end_date": config.resolved_end_date(),
                },
            }

        return handler

    def _build_quality_summary(
        self,
        stage_payloads: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        return self._as_dict(stage_payloads.get("model_quality_validation"))

    def _build_gap_quality_summary(
        self,
        config: TrainingPipelineConfig,
        stage_payloads: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        gap_stage = self._as_dict(stage_payloads.get("check_candle_gaps"))
        return GapQualityDiagnostics().analyze(
            symbol=config.symbol,
            interval=config.interval,
            start_date=config.start_date,
            end_date=config.resolved_end_date(),
            gap_count=int(gap_stage.get("gap_count", 0)),
            missing_open_times=[str(item) for item in self._as_list(gap_stage.get("missing_open_times"))],
            last_open_time=gap_stage.get("last_open_time"),
            real_gap_count=gap_stage.get("real_gap_count"),
            real_missing_open_times=[str(item) for item in self._as_list(gap_stage.get("real_missing_open_times"))],
            trailing_incomplete_count=gap_stage.get("trailing_incomplete_count"),
            trailing_incomplete_open_times=[
                str(item) for item in self._as_list(gap_stage.get("trailing_incomplete_open_times"))
            ],
            trailing_incomplete_range_detected=self._as_bool(
                gap_stage.get("trailing_incomplete_range_detected"),
            ),
        )

    def _label_config_summary(
        self,
        config: TrainingPipelineConfig,
        stage_payloads: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        build_labels_payload = self._as_dict((stage_payloads or {}).get("build_labels"))
        return {
            "label_version": self.DEFAULT_LABEL_VERSION,
            "horizon_candles": self._resolve_horizon_from_label_version(self.DEFAULT_LABEL_VERSION),
            "direction_atr_threshold": self.DEFAULT_DIRECTION_ATR_THRESHOLD,
            "take_profit_atr": self.DEFAULT_TAKE_PROFIT_ATR,
            "stop_loss_atr": self.DEFAULT_STOP_LOSS_ATR,
            "flat_class_enabled": True,
            "label_mode": build_labels_payload.get("label_mode", self.DEFAULT_LABEL_MODE),
            "exit_policy_profile": config.exit_policy_profile,
            "exit_timeout_bars": config.exit_timeout_bars,
            "exit_mitigation_loss_r": config.exit_mitigation_loss_r,
            "exit_neutral_abs_r": config.exit_neutral_abs_r,
            "training_objective": build_labels_payload.get("training_objective", config.training_objective),
            "direction_counts": self._as_dict(build_labels_payload.get("direction_counts")),
            "regime_label_builder_status": self._as_dict(
                build_labels_payload.get("regime_label_builder_status", {})
            ),
            "config_id": build_labels_payload.get("config_id", self.DEFAULT_LABEL_VERSION),
            "decision_calibration_enabled": self._as_bool(
                build_labels_payload.get("decision_calibration_enabled", config.decision_calibration_enabled),
            ),
            "decision_flat_if_max_prob_below": float(
                build_labels_payload.get("decision_flat_if_max_prob_below", config.decision_flat_if_max_prob_below)
            ),
            "decision_flat_if_margin_below": float(
                build_labels_payload.get("decision_flat_if_margin_below", config.decision_flat_if_margin_below)
            ),
            "decision_min_direction_prob": float(
                build_labels_payload.get("decision_min_direction_prob", config.decision_min_direction_prob)
            ),
            "decision_min_up_down_margin": float(
                build_labels_payload.get("decision_min_up_down_margin", config.decision_min_up_down_margin)
            ),
            "decision_down_boost": float(
                build_labels_payload.get("decision_down_boost", config.decision_down_boost)
            ),
            "decision_up_penalty": float(
                build_labels_payload.get("decision_up_penalty", config.decision_up_penalty)
            ),
            "decision_flat_boost": float(
                build_labels_payload.get("decision_flat_boost", config.decision_flat_boost)
            ),
            "decision_calibration_mode": str(
                build_labels_payload.get("decision_calibration_mode", config.decision_calibration_mode)
                or config.decision_calibration_mode
            ),
            "decision_fallback_to_raw": self._as_bool(
                build_labels_payload.get("decision_fallback_to_raw", config.decision_fallback_to_raw)
            ),
            "decision_max_flat_ratio": float(
                build_labels_payload.get("decision_max_flat_ratio", config.decision_max_flat_ratio)
            ),
            "decision_min_down_ratio_when_actual_down_high": float(
                build_labels_payload.get(
                    "decision_min_down_ratio_when_actual_down_high",
                    config.decision_min_down_ratio_when_actual_down_high,
                )
            ),
            "decision_min_up_ratio_when_actual_up_high": float(
                build_labels_payload.get(
                    "decision_min_up_ratio_when_actual_up_high",
                    config.decision_min_up_ratio_when_actual_up_high,
                )
            ),
            "decision_max_dominant_class_ratio": float(
                build_labels_payload.get(
                    "decision_max_dominant_class_ratio",
                    config.decision_max_dominant_class_ratio,
                )
            ),
            "decision_require_non_worse_baseline_edge": self._as_bool(
                build_labels_payload.get(
                    "decision_require_non_worse_baseline_edge",
                    config.decision_require_non_worse_baseline_edge,
                )
            ),
            "decision_baseline_edge_tolerance": float(
                build_labels_payload.get(
                    "decision_baseline_edge_tolerance",
                    config.decision_baseline_edge_tolerance,
                )
            ),
            "decision_actual_class_high_threshold": float(
                build_labels_payload.get(
                    "decision_actual_class_high_threshold",
                    config.decision_actual_class_high_threshold,
                )
            ),
            "decision_policy_grid_enabled": self._as_bool(
                build_labels_payload.get("decision_policy_grid_enabled", config.decision_policy_grid_enabled),
            ),
            "decision_policy_grid_stage": build_labels_payload.get(
                "decision_policy_grid_stage",
                config.decision_policy_grid_stage,
            ),
            "opportunity_probability_threshold": float(
                build_labels_payload.get(
                    "opportunity_probability_threshold",
                    config.opportunity_probability_threshold,
                )
            ),
            "setup_quality_min_threshold": build_labels_payload.get(
                "setup_quality_min_threshold",
                config.setup_quality_min_threshold,
            ),
            "setup_quality_decision_mask_enabled": self._as_bool(
                build_labels_payload.get(
                    "setup_quality_decision_mask_enabled",
                    config.setup_quality_decision_mask_enabled,
                )
            ),
            "setup_quality_decision_mask_min_threshold": build_labels_payload.get(
                "setup_quality_decision_mask_min_threshold",
                config.setup_quality_decision_mask_min_threshold,
            ),
            "entry_path_quality_filter_enabled": self._as_bool(
                build_labels_payload.get(
                    "entry_path_quality_filter_enabled",
                    config.entry_path_quality_filter_enabled,
                )
            ),
            "entry_path_quality_min_threshold": build_labels_payload.get(
                "entry_path_quality_min_threshold",
                config.entry_path_quality_min_threshold,
            ),
            "stop_pressure_max_risk_score": build_labels_payload.get(
                "stop_pressure_max_risk_score",
                config.stop_pressure_max_risk_score,
            ),
            "mae_pressure_max_risk_score": build_labels_payload.get(
                "mae_pressure_max_risk_score",
                config.mae_pressure_max_risk_score,
            ),
            "opportunity_threshold_sweep_enabled": self._as_bool(
                build_labels_payload.get(
                    "opportunity_threshold_sweep_enabled",
                    config.opportunity_threshold_sweep_enabled,
                )
            ),
            "opportunity_threshold_candidates": [
                float(item)
                for item in self._as_list(
                    build_labels_payload.get(
                        "opportunity_threshold_candidates",
                        config.opportunity_threshold_candidates,
                    )
                )
            ],
            "opportunity_min_precision": float(
                build_labels_payload.get("opportunity_min_precision", config.opportunity_min_precision)
            ),
            "opportunity_min_recall": float(
                build_labels_payload.get("opportunity_min_recall", config.opportunity_min_recall)
            ),
            "opportunity_max_predicted_trade_rate": float(
                build_labels_payload.get(
                    "opportunity_max_predicted_trade_rate",
                    config.opportunity_max_predicted_trade_rate,
                )
            ),
            "opportunity_max_predicted_to_actual_trade_rate_ratio": float(
                build_labels_payload.get(
                    "opportunity_max_predicted_to_actual_trade_rate_ratio",
                    config.opportunity_max_predicted_to_actual_trade_rate_ratio,
                )
            ),
            "opportunity_max_false_positive_rate": float(
                build_labels_payload.get(
                    "opportunity_max_false_positive_rate",
                    config.opportunity_max_false_positive_rate,
                )
            ),
            "class_margin_objective_enabled": self._as_bool(
                build_labels_payload.get("class_margin_objective_enabled", config.class_margin_objective_enabled),
            ),
            "true_class_margin_weight": float(
                build_labels_payload.get("true_class_margin_weight", config.true_class_margin_weight)
            ),
            "true_class_margin_target": float(
                build_labels_payload.get("true_class_margin_target", config.true_class_margin_target)
            ),
            "up_down_margin_weight": float(
                build_labels_payload.get("up_down_margin_weight", config.up_down_margin_weight)
            ),
            "up_down_margin_target": float(
                build_labels_payload.get("up_down_margin_target", config.up_down_margin_target)
            ),
            "flat_margin_weight": float(
                build_labels_payload.get("flat_margin_weight", config.flat_margin_weight)
            ),
            "flat_margin_target": float(
                build_labels_payload.get("flat_margin_target", config.flat_margin_target)
            ),
            "hard_negative_margin_weight": float(
                build_labels_payload.get("hard_negative_margin_weight", config.hard_negative_margin_weight)
            ),
            "hard_negative_margin_target": float(
                build_labels_payload.get("hard_negative_margin_target", config.hard_negative_margin_target)
            ),
        }

    def _feature_config_summary(self, feature_version: str | None = None) -> dict[str, Any]:
        return {
            "feature_version": feature_version or self.DEFAULT_FEATURE_VERSION,
            "model_name": self.DEFAULT_MODEL_NAME,
        }

    @staticmethod
    def _extract_baseline_accuracy_delta(
        *,
        training_summary: dict[str, Any],
        baseline_summary: dict[str, Any],
    ) -> float | None:
        model_accuracy = LongHistoryTrainingPipelineRunner._extract_metric(
            training_summary,
            ("model_accuracy", "accuracy_test"),
            nested_key="test_metrics",
            nested_metric="accuracy",
        )
        baseline_accuracy = LongHistoryTrainingPipelineRunner._extract_metric(
            baseline_summary,
            ("baseline_accuracy",),
            nested_key="best_baseline",
            nested_metric="test_metrics.accuracy",
        )
        if baseline_accuracy is None:
            baselines = baseline_summary.get("baselines")
            if isinstance(baselines, dict):
                scores = []
                for payload in baselines.values():
                    if not isinstance(payload, dict):
                        continue
                    test_payload = dict(payload.get("test", {}))
                    accuracy = test_payload.get("accuracy")
                    if accuracy is not None:
                        scores.append(float(accuracy))
                if scores:
                    baseline_accuracy = max(scores)
        if model_accuracy is None or baseline_accuracy is None:
            return None
        return model_accuracy - baseline_accuracy

    @staticmethod
    def _calibrated_accuracy_triplet(
        probability_diagnostics: dict[str, Any],
    ) -> tuple[float | None, float | None, float | None]:
        calibrated = dict(probability_diagnostics.get("calibrated_decision_diagnostics", {}))
        model_accuracy = calibrated.get("calibrated_accuracy")
        baseline_accuracy = calibrated.get("baseline_accuracy")
        if model_accuracy is None or baseline_accuracy is None:
            return None, None, None
        model_accuracy = float(model_accuracy)
        baseline_accuracy = float(baseline_accuracy)
        return model_accuracy, baseline_accuracy, model_accuracy - baseline_accuracy

    @staticmethod
    def _extract_metric(
        payload: dict[str, Any],
        direct_keys: tuple[str, ...],
        *,
        nested_key: str,
        nested_metric: str,
    ) -> float | None:
        for key in direct_keys:
            value = payload.get(key)
            if value is not None:
                return float(value)
        current: Any = payload.get(nested_key, {})
        for part in nested_metric.split("."):
            if not isinstance(current, dict):
                return None
            current = current.get(part)
            if current is None:
                return None
        return float(current)

    def _resolve_final_status(
        self,
        *,
        dry_run: bool,
        sample_mode: bool,
        stage_results: list[TrainingPipelineStageResult],
    ) -> str:
        if any(item.status == FAILED for item in stage_results):
            return PIPELINE_FAILED
        if dry_run:
            return PIPELINE_DRY_RUN_COMPLETED
        if sample_mode:
            return PIPELINE_SAMPLE_COMPLETED
        if any(item.status in {SKIPPED, SKIPPED_NOT_AVAILABLE} for item in stage_results):
            return PIPELINE_COMPLETED_WITH_SKIPS
        return PIPELINE_COMPLETED

    def _next_recommendations(
        self,
        *,
        quality_status: str,
        dry_run: bool,
        sample_mode: bool,
    ) -> tuple[str, ...]:
        recommendations = []
        if dry_run or sample_mode:
            recommendations.append("Run the pipeline in real long-history mode for actual training.")
        if quality_status in {"NEEDS_MORE_DATA", "INSUFFICIENT_REAL_HISTORY"}:
            recommendations.append("Collect longer real history and increase walk-forward coverage.")
        if quality_status == "QUALITY_REJECTED":
            recommendations.append("Review diagnostics before considering another candidate model.")
        if not recommendations:
            recommendations.append("Prepare ML27 real long-history candidate selection review.")
        recommendations.append("Keep live trading, orders, and traders-core integration disabled.")
        return tuple(recommendations)

    @staticmethod
    def _count_status(
        stage_results: list[TrainingPipelineStageResult],
        status: str,
    ) -> int:
        return sum(int(item.status == status) for item in stage_results)

    @staticmethod
    def _count_skipped(stage_results: list[TrainingPipelineStageResult]) -> int:
        return sum(
            int(item.status in {SKIPPED, SKIPPED_NOT_AVAILABLE})
            for item in stage_results
        )

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _build_health_payload() -> dict[str, str]:
        settings = get_settings()
        return {
            "status": "ok",
            "service": settings.service_name,
            "version": __version__,
        }

    @staticmethod
    @staticmethod
    def _parse_date(value: str) -> date:
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"date must be in YYYY-MM-DD format: {value}") from exc

    def _resolved_datetime_range(self, config: TrainingPipelineConfig) -> tuple[datetime, datetime]:
        """Возвращает UTC datetime range для текущего pipeline config."""

        return self._build_utc_date_range(
            self._parse_date(config.start_date),
            self._parse_date(config.resolved_end_date()),
        )

    @staticmethod
    def _build_utc_date_range(start_date: date, end_date: date) -> tuple[datetime, datetime]:
        if end_date < start_date:
            raise ValueError("end-date must be greater than or equal to start-date")
        start_at = datetime.combine(start_date, datetime_time.min, tzinfo=timezone.utc)
        end_at = datetime.combine(end_date, datetime_time.min, tzinfo=timezone.utc) + timedelta(days=1)
        return start_at, end_at

    @staticmethod
    def _resolve_horizon_from_label_version(label_version: str) -> int:
        if "_h" not in label_version:
            if label_version == "lv1":
                return 8
            raise ValueError(f"cannot resolve horizon from label-version: {label_version}")
        marker = label_version.split("_h", 1)[1]
        value = marker.split("_", 1)[0]
        try:
            return int(value)
        except ValueError as exc:
            raise ValueError(f"cannot resolve horizon from label-version: {label_version}") from exc

    def _with_diagnostics_service(self, callback: Callable[[DiagnosticsService], dict[str, Any]]) -> dict[str, Any]:
        with get_session() as session:
            feature_repository = FeatureRepository(session)
            label_repository = LabelRepository(session)
            candle_repository = CandleRepository(session)
            model_registry_repository = ModelRegistryRepository(session)
            dataset_builder = DatasetBuilder(
                feature_repository=feature_repository,
                label_repository=label_repository,
            )
            service = DiagnosticsService(
                dataset_builder=dataset_builder,
                feature_repository=feature_repository,
                label_repository=label_repository,
                candle_repository=candle_repository,
                model_registry_repository=model_registry_repository,
                artifact_storage=ArtifactStorage(),
            )
            return callback(service)

    @staticmethod
    def _require_model_version(
        stage_payloads: dict[str, Any],
        stage_name: str,
    ) -> str:
        model_version = str(stage_payloads.get("train_model", {}).get("model_version") or "")
        if not model_version:
            raise ValueError(f"{stage_name} requires a completed train_model stage with model_version")
        return model_version

    @staticmethod
    def _merge_summary_fields(payload: dict[str, Any], *, summary_keys: tuple[str, ...]) -> None:
        summary = payload.get("summary")
        if not isinstance(summary, dict):
            return
        for key in summary_keys:
            if key in summary and key not in payload:
                payload[key] = summary[key]

    @staticmethod
    def _extract_baseline_accuracy(payload: dict[str, Any]) -> float | None:
        best_baseline = payload.get("best_baseline", {})
        if isinstance(best_baseline, dict):
            test_metrics = best_baseline.get("test_metrics", {})
            if isinstance(test_metrics, dict) and test_metrics.get("accuracy") is not None:
                return float(test_metrics["accuracy"])
        return None
