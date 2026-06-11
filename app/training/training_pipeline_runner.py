from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import text

from app import __version__
from app.config.settings import get_settings
from app.evaluation.gate_policy_replay_evaluator import GatePolicyReplayEvaluator
from app.evaluation.gate_policy_replay_reporter import GatePolicyReplayReporter
from app.evaluation.model_quality_reporter import ModelQualityReporter
from app.evaluation.model_quality_validator import (
    INSUFFICIENT_REAL_HISTORY,
    validate_model_quality,
)
from app.db.session import get_session
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
    dry_run: bool = False
    sample_mode: bool = False
    run_gate_policy_replay: bool = True
    export_report: bool = True
    output_dir: Path = Path("reports/training_pipeline_runs")

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
    output_dir: str
    log_path: str
    events_path: str
    json_report_path: str
    markdown_report_path: str
    safety: dict[str, Any]
    command_snapshot: dict[str, Any]
    next_recommendations: tuple[str, ...]

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
            "output_dir": self.output_dir,
            "log_path": self.log_path,
            "events_path": self.events_path,
            "json_report_path": self.json_report_path,
            "markdown_report_path": self.markdown_report_path,
            "safety": dict(self.safety),
            "command_snapshot": dict(self.command_snapshot),
            "next_recommendations": list(self.next_recommendations),
        }


class LongHistoryTrainingPipelineRunner:
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
                "dry_run": config.dry_run,
                "sample_mode": config.sample_mode,
                "run_gate_policy_replay": config.run_gate_policy_replay,
                "export_report": config.export_report,
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
        model_summary = dict(stage_payloads.get("train_model", {}))
        baseline_summary = dict(stage_payloads.get("baseline_compare", {}))
        gate_policy_replay_summary = dict(stage_payloads.get("gate_policy_replay_evaluation", {}))

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
                "dry_run": config.dry_run,
                "sample_mode": config.sample_mode,
                "run_gate_policy_replay": config.run_gate_policy_replay,
                "export_report": config.export_report,
                "output_dir": str(config.output_dir),
            },
            next_recommendations=self._next_recommendations(
                quality_status=str(quality_summary.get("quality_status", INSUFFICIENT_REAL_HISTORY)),
                dry_run=config.dry_run,
                sample_mode=config.sample_mode,
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
            },
            next_recommendations=self._next_recommendations(
                quality_status=str(quality_summary.get("quality_status", INSUFFICIENT_REAL_HISTORY)),
                dry_run=config.dry_run,
                sample_mode=config.sample_mode,
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
        return {
            "health_check": self._health_check_real,
            "db_check": self._db_check_real,
            "gate_policy_replay_evaluation": self._gate_policy_replay_sample,
            "model_quality_validation": self._quality_validation_real_fallback,
        }.get(stage, self._real_stage_not_available(stage))

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
        probability_diagnostics = dict(stage_payloads.get("probability_diagnostics", {}))
        calibration_summary = dict(stage_payloads.get("calibration_diagnostics", {}))
        profit_aware_summary = dict(stage_payloads.get("profit_aware_evaluation", {}))
        walk_forward_summary = dict(stage_payloads.get("walk_forward_evaluation", {}))
        gate_policy_replay_summary = dict(stage_payloads.get("gate_policy_replay_evaluation", {}))

        result = validate_model_quality(
            training_summary=training_summary,
            baseline_summary=baseline_summary,
            probability_diagnostics=probability_diagnostics,
            calibration_summary=calibration_summary,
            profit_aware_summary=profit_aware_summary,
            walk_forward_summary=walk_forward_summary,
            gate_policy_replay_summary=gate_policy_replay_summary,
        )
        payload = ModelQualityReporter().build_full_quality_report(result)
        return {
            "status": COMPLETED,
            "message": "Model quality validation sample completed",
            "data": payload,
        }

    def _quality_validation_real_fallback(
        self,
        config: TrainingPipelineConfig,
        stage_payloads: dict[str, Any],
    ) -> dict[str, Any]:
        result = validate_model_quality(
            training_summary=dict(stage_payloads.get("train_model", {})),
            baseline_summary=dict(stage_payloads.get("baseline_compare", {})),
            probability_diagnostics=dict(stage_payloads.get("probability_diagnostics", {})),
            calibration_summary=dict(stage_payloads.get("calibration_diagnostics", {})),
            profit_aware_summary=dict(stage_payloads.get("profit_aware_evaluation", {})),
            walk_forward_summary=dict(stage_payloads.get("walk_forward_evaluation", {})),
            gate_policy_replay_summary=dict(stage_payloads.get("gate_policy_replay_evaluation", {})),
        )
        payload = ModelQualityReporter().build_full_quality_report(result)
        return {
            "status": COMPLETED,
            "message": "Model quality validation completed with available diagnostics",
            "data": payload,
        }

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
    ) -> Callable[[TrainingPipelineConfig, dict[str, Any]], dict[str, Any]]:
        def handler(
            config: TrainingPipelineConfig,
            stage_payloads: dict[str, Any],
        ) -> dict[str, Any]:
            return {
                "status": SKIPPED_NOT_AVAILABLE,
                "message": f"{stage} requires an explicit long-history execution path outside ML26 unit scope",
                "data": {
                    "reason": "direct_real_execution_not_wired",
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
        return dict(stage_payloads.get("model_quality_validation", {}))

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
