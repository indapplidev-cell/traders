from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from app.dataset.dataset_models import DatasetRow
from app.dataset.dataset_builder import DatasetBuilder
from app.db.repositories.candle_repository import CandleRepository
from app.db.repositories.feature_repository import FeatureRepository
from app.db.repositories.label_repository import LabelRepository
from app.db.session import get_session
from app.diagnostics.feature_group_quality import FeatureGroupQualityScorer
from app.diagnostics.feature_leakage_guard import FeatureLeakageGuard
from app.diagnostics.feature_quality_diagnostics import FeatureQualityDiagnostics
from app.diagnostics.gap_quality_diagnostics import GapQualityDiagnostics
from app.diagnostics.real_feature_diagnostics_service import RealFeatureDiagnosticsService
from app.diagnostics.regime_feature_diagnostics import RegimeFeatureDiagnostics
from app.labels.label_builder import LabelBuilder
from app.labels.label_config import LabelConfig
from app.labels.regime_label_builder import RegimeLabelBuilder
from app.experiments.feature_regime_experiment_reporter import FeatureRegimeExperimentReporter
from app.experiments.label_grid_experiment_runner import (
    LabelGridExperimentConfig,
    LabelGridExperimentRunner,
)
from app.experiments.regime_experiment_planner import RegimeExperimentPlanner
from app.features.feature_models import feature_names_for_version
from app.labels.label_quality_grid import LabelQualityGridPlanner
from app.labels.regime_label_integration_status import RegimeLabelIntegrationStatus
from app.labels.regime_label_config import RegimeLabelConfigPlanner


FEATURE_REGIME_EXPERIMENT_RUNNER_NAME = "feature_regime_experiment_runner"
FEATURE_REGIME_EXPERIMENT_RUNNER_VERSION = "ml36"
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
    feature_version: str = "fv2"
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
    raw_candidate_status: str | None
    score: float | None
    failed_gates: tuple[str, ...] = ()
    passed_gates: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()
    regime_specific_training_applied: bool = False
    feature_weak_signal_detected: bool = False
    feature_leakage_risk_detected: bool = False
    probability_diagnostics: dict[str, Any] = field(default_factory=dict)
    probability_diagnostics_missing_reason: str | None = None
    real_feature_diagnostics: dict[str, Any] = field(default_factory=dict)
    real_feature_diagnostics_missing_reason: str | None = None
    collapse_diagnostics_v2: dict[str, Any] = field(default_factory=dict)
    collapse_diagnostics_v2_missing_reason: str | None = None
    regime_label_builder_status: dict[str, Any] = field(default_factory=dict)
    regime_label_builder_status_missing_reason: str | None = None
    walk_forward_profit_diagnostics: dict[str, Any] = field(default_factory=dict)
    walk_forward_profit_diagnostics_missing_reason: str | None = None
    profit_aware_diagnostics: dict[str, Any] = field(default_factory=dict)
    profit_aware_diagnostics_missing_reason: str | None = None
    approved_for_live_trading: bool = False
    approved_for_auto_activation: bool = False
    orders_enabled: bool = False
    traders_core_connected: bool = False
    model_quality_validation_status: str | None = None
    model_accuracy: float | None = None
    baseline_accuracy: float | None = None
    accuracy_edge: float | None = None
    profit_total_r: float | None = None
    profit_factor: float | None = None
    walk_forward_total_r: float | None = None
    walk_forward_profit_factor: float | None = None
    predicted_class_distribution: dict[str, Any] = field(default_factory=dict)
    actual_class_distribution: dict[str, Any] = field(default_factory=dict)
    collapse_detected: bool = False
    collapse_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "config_id": self.config_id,
            "label_config": dict(self.label_config),
            "status": self.status,
            "quality_status": self.quality_status,
            "candidate_status": self.candidate_status,
            "raw_candidate_status": self.raw_candidate_status,
            "score": self.score,
            "failed_gates": list(self.failed_gates),
            "passed_gates": list(self.passed_gates),
            "warnings": list(self.warnings),
            "recommendations": list(self.recommendations),
            "regime_specific_training_applied": self.regime_specific_training_applied,
            "feature_weak_signal_detected": self.feature_weak_signal_detected,
            "feature_leakage_risk_detected": self.feature_leakage_risk_detected,
            "probability_diagnostics": dict(self.probability_diagnostics),
            "probability_diagnostics_missing_reason": self.probability_diagnostics_missing_reason,
            "real_feature_diagnostics": dict(self.real_feature_diagnostics),
            "real_feature_diagnostics_missing_reason": self.real_feature_diagnostics_missing_reason,
            "collapse_diagnostics_v2": dict(self.collapse_diagnostics_v2),
            "collapse_diagnostics_v2_missing_reason": self.collapse_diagnostics_v2_missing_reason,
            "regime_label_builder_status": dict(self.regime_label_builder_status),
            "regime_label_builder_status_missing_reason": self.regime_label_builder_status_missing_reason,
            "walk_forward_profit_diagnostics": dict(self.walk_forward_profit_diagnostics),
            "walk_forward_profit_diagnostics_missing_reason": self.walk_forward_profit_diagnostics_missing_reason,
            "profit_aware_diagnostics": dict(self.profit_aware_diagnostics),
            "profit_aware_diagnostics_missing_reason": self.profit_aware_diagnostics_missing_reason,
            "approved_for_live_trading": self.approved_for_live_trading,
            "approved_for_auto_activation": self.approved_for_auto_activation,
            "orders_enabled": self.orders_enabled,
            "traders_core_connected": self.traders_core_connected,
            "model_quality_validation_status": self.model_quality_validation_status,
            "model_accuracy": self.model_accuracy,
            "baseline_accuracy": self.baseline_accuracy,
            "accuracy_edge": self.accuracy_edge,
            "profit_total_r": self.profit_total_r,
            "profit_factor": self.profit_factor,
            "walk_forward_total_r": self.walk_forward_total_r,
            "walk_forward_profit_factor": self.walk_forward_profit_factor,
            "predicted_class_distribution": dict(self.predicted_class_distribution),
            "actual_class_distribution": dict(self.actual_class_distribution),
            "collapse_detected": self.collapse_detected,
            "collapse_type": self.collapse_type,
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
    evaluated_candidate_count: int
    failed_candidate_count: int
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
    real_feature_diagnostics_used: bool
    real_feature_diagnostics_row_count: int
    feature_version_used: str
    regime_features_attached: bool
    regime_feature_count: int
    regime_feature_source: str
    regime_specific_labeling_available: bool
    regime_specific_training_applied: bool
    missing_requirements: tuple[str, ...]
    effective_gap_count_for_training: int
    gap_severity_for_training: str
    gap_training_safe: bool
    output_dir: str
    log_path: str
    events_path: str
    summary_json_path: str
    summary_markdown_path: str
    baseline_reference: dict[str, Any]
    probability_diagnostics: dict[str, Any] = field(default_factory=dict)
    probability_diagnostics_missing_reason: str | None = None
    real_feature_diagnostics: dict[str, Any] = field(default_factory=dict)
    real_feature_diagnostics_missing_reason: str | None = None
    collapse_diagnostics_v2: dict[str, Any] = field(default_factory=dict)
    collapse_diagnostics_v2_missing_reason: str | None = None
    regime_label_builder_status: dict[str, Any] = field(default_factory=dict)
    regime_label_builder_status_missing_reason: str | None = None
    walk_forward_profit_diagnostics: dict[str, Any] = field(default_factory=dict)
    walk_forward_profit_diagnostics_missing_reason: str | None = None
    profit_aware_diagnostics: dict[str, Any] = field(default_factory=dict)
    profit_aware_diagnostics_missing_reason: str | None = None
    regime_label_builder_used_in_training_any: bool = False
    regime_label_builder_used_in_training_all: bool = False
    regime_specific_training_applied_any: bool = False
    regime_specific_training_applied_all: bool = False
    approved_for_traders_core_integration: bool = False
    approved_for_live_trading: bool = False
    approved_for_auto_activation: bool = False
    orders_enabled: bool = False
    traders_core_connected: bool = False
    candle_ta_context_features_attached: bool = False
    candidate_status: str | None = None
    model_quality_validation_status: str | None = None

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
            "evaluated_candidate_count": self.evaluated_candidate_count,
            "failed_candidate_count": self.failed_candidate_count,
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
            "real_feature_diagnostics_used": self.real_feature_diagnostics_used,
            "real_feature_diagnostics_row_count": self.real_feature_diagnostics_row_count,
            "feature_version_used": self.feature_version_used,
            "regime_features_attached": self.regime_features_attached,
            "regime_feature_count": self.regime_feature_count,
            "regime_feature_source": self.regime_feature_source,
            "regime_specific_labeling_available": self.regime_specific_labeling_available,
            "regime_specific_training_applied": self.regime_specific_training_applied,
            "missing_requirements": list(self.missing_requirements),
            "effective_gap_count_for_training": self.effective_gap_count_for_training,
            "gap_severity_for_training": self.gap_severity_for_training,
            "gap_training_safe": self.gap_training_safe,
            "output_dir": self.output_dir,
            "log_path": self.log_path,
            "events_path": self.events_path,
            "summary_json_path": self.summary_json_path,
            "summary_markdown_path": self.summary_markdown_path,
            "baseline_reference": dict(self.baseline_reference),
            "probability_diagnostics": dict(self.probability_diagnostics),
            "probability_diagnostics_missing_reason": self.probability_diagnostics_missing_reason,
            "real_feature_diagnostics": dict(self.real_feature_diagnostics),
            "real_feature_diagnostics_missing_reason": self.real_feature_diagnostics_missing_reason,
            "collapse_diagnostics_v2": dict(self.collapse_diagnostics_v2),
            "collapse_diagnostics_v2_missing_reason": self.collapse_diagnostics_v2_missing_reason,
            "regime_label_builder_status": dict(self.regime_label_builder_status),
            "regime_label_builder_status_missing_reason": self.regime_label_builder_status_missing_reason,
            "walk_forward_profit_diagnostics": dict(self.walk_forward_profit_diagnostics),
            "walk_forward_profit_diagnostics_missing_reason": self.walk_forward_profit_diagnostics_missing_reason,
            "profit_aware_diagnostics": dict(self.profit_aware_diagnostics),
            "profit_aware_diagnostics_missing_reason": self.profit_aware_diagnostics_missing_reason,
            "regime_label_builder_used_in_training_any": self.regime_label_builder_used_in_training_any,
            "regime_label_builder_used_in_training_all": self.regime_label_builder_used_in_training_all,
            "regime_specific_training_applied_any": self.regime_specific_training_applied_any,
            "regime_specific_training_applied_all": self.regime_specific_training_applied_all,
            "approved_for_traders_core_integration": self.approved_for_traders_core_integration,
            "approved_for_live_trading": self.approved_for_live_trading,
            "approved_for_auto_activation": self.approved_for_auto_activation,
            "orders_enabled": self.orders_enabled,
            "traders_core_connected": self.traders_core_connected,
            "candle_ta_context_features_attached": self.candle_ta_context_features_attached,
            "candidate_status": self.candidate_status,
            "model_quality_validation_status": self.model_quality_validation_status,
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
        real_feature_diagnostics_service: RealFeatureDiagnosticsService | None = None,
        regime_experiment_planner: RegimeExperimentPlanner | None = None,
        base_grid_planner: LabelQualityGridPlanner | None = None,
        regime_label_planner: RegimeLabelConfigPlanner | None = None,
        regime_label_integration_status: RegimeLabelIntegrationStatus | None = None,
        label_grid_runner: LabelGridExperimentRunner | None = None,
        reporter: FeatureRegimeExperimentReporter | None = None,
    ) -> None:
        self._feature_quality_diagnostics = feature_quality_diagnostics or FeatureQualityDiagnostics()
        self._feature_group_quality_scorer = feature_group_quality_scorer or FeatureGroupQualityScorer()
        self._regime_feature_diagnostics = regime_feature_diagnostics or RegimeFeatureDiagnostics()
        self._feature_leakage_guard = feature_leakage_guard or FeatureLeakageGuard()
        self._real_feature_diagnostics_service = real_feature_diagnostics_service or RealFeatureDiagnosticsService(
            feature_quality_diagnostics=self._feature_quality_diagnostics,
            feature_group_quality_scorer=self._feature_group_quality_scorer,
            feature_leakage_guard=self._feature_leakage_guard,
            regime_feature_diagnostics=self._regime_feature_diagnostics,
        )
        self._regime_experiment_planner = regime_experiment_planner or RegimeExperimentPlanner()
        self._base_grid_planner = base_grid_planner or LabelQualityGridPlanner()
        self._regime_label_planner = regime_label_planner or RegimeLabelConfigPlanner()
        self._regime_label_integration_status = regime_label_integration_status or RegimeLabelIntegrationStatus()
        self._label_grid_runner = label_grid_runner or LabelGridExperimentRunner()
        self._reporter = reporter or FeatureRegimeExperimentReporter()

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

    @staticmethod
    def _regime_status_is_built(status: dict[str, Any]) -> bool:
        return bool(
            status.get("regime_label_builder_status") == "built"
            or status.get("regime_label_builder_used_in_training", False)
            or status.get("regime_specific_training_applied", False)
        )

    @classmethod
    def _aggregate_regime_label_builder_status(
        cls,
        *,
        diagnostics_status: dict[str, Any],
        candidate_results: list[FeatureRegimeCandidateResult],
        fallback_missing_requirements: list[str],
    ) -> dict[str, Any]:
        candidate_statuses = [
            cls._as_dict(item.regime_label_builder_status)
            for item in candidate_results
            if cls._as_dict(item.regime_label_builder_status)
        ]
        primary_status = next(
            (status for status in candidate_statuses if cls._regime_status_is_built(status)),
            candidate_statuses[0] if candidate_statuses else cls._as_dict(diagnostics_status),
        )
        primary_status = cls._as_dict(primary_status)
        if not primary_status and diagnostics_status:
            primary_status = cls._as_dict(diagnostics_status)

        used_flags = [
            bool(status.get("regime_label_builder_used_in_training", False))
            for status in candidate_statuses
        ]
        applied_flags = [
            bool(status.get("regime_specific_training_applied", False))
            for status in candidate_statuses
        ]
        built_any = any(used_flags) or any(applied_flags) or any(
            cls._regime_status_is_built(status) for status in candidate_statuses
        )
        built_all = bool(candidate_statuses) and all(
            bool(status.get("regime_label_builder_used_in_training", False))
            or bool(status.get("regime_specific_training_applied", False))
            for status in candidate_statuses
        )
        used_any = any(used_flags)
        used_all = bool(candidate_statuses) and all(used_flags)
        applied_any = any(applied_flags)
        applied_all = bool(candidate_statuses) and all(applied_flags)

        if not candidate_statuses:
            used_any = bool(primary_status.get("regime_label_builder_used_in_training", False))
            used_all = used_any
            applied_any = bool(primary_status.get("regime_specific_training_applied", False))
            applied_all = applied_any
            built_any = cls._regime_status_is_built(primary_status)
            built_all = built_any

        missing_requirements = list(
            dict.fromkeys(
                cls._string_list(primary_status.get("missing_requirements"))
                + cls._string_list(fallback_missing_requirements)
            )
        )
        if built_any or used_any or applied_any:
            missing_requirements = [
                item for item in missing_requirements if item != "regime_runtime_labels_not_built"
            ]
        elif (candidate_statuses or primary_status) and "regime_runtime_labels_not_built" not in missing_requirements:
            missing_requirements.append("regime_runtime_labels_not_built")

        primary_status["regime_label_builder_status"] = "built" if built_any else str(
            primary_status.get("regime_label_builder_status") or "blocked"
        )
        primary_status["regime_label_builder_used_in_training"] = used_any
        primary_status["regime_specific_training_applied"] = applied_any
        primary_status["regime_label_builder_used_in_training_any"] = used_any
        primary_status["regime_label_builder_used_in_training_all"] = used_all
        primary_status["regime_specific_training_applied_any"] = applied_any
        primary_status["regime_specific_training_applied_all"] = applied_all
        primary_status["missing_requirements"] = missing_requirements
        return primary_status

    def build_preview(self) -> dict[str, Any]:
        feature_names = feature_names_for_version("fv3_candle_ta_context")
        regime_feature_count = len([name for name in feature_names if name.startswith("regime_")])
        return {
            "runner_name": FEATURE_REGIME_EXPERIMENT_RUNNER_NAME,
            "runner_version": FEATURE_REGIME_EXPERIMENT_RUNNER_VERSION,
            "feature_version_default": "fv3_candle_ta_context",
            "feature_versions_available": ["fv1", "fv2", "fv2_regime", "fv3_candle_ta_context"],
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
            "feature_regime_integration": {
                "feature_version_used": "fv3_candle_ta_context",
                "regime_features_attached": True,
                "regime_feature_count": regime_feature_count,
                "candle_ta_context_features_attached": True,
                "regime_specific_labeling_available": True,
                "regime_specific_training_applied": True,
            },
            "safety_flags": {
                "approved_for_live_trading": False,
                "approved_for_auto_activation": False,
                "orders_enabled": False,
                "traders_core_connected": False,
            },
        }

    def run(self, config: FeatureRegimeExperimentConfig) -> FeatureRegimeExperimentResult:
        feature_names_for_version(config.feature_version)
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
                "feature_version": config.feature_version,
                "dry_run": config.dry_run,
                "sample_mode": config.sample_mode,
                "max_configs": config.max_configs,
            },
            message="Feature/regime experiment started",
        )

        selected_base_configs = self._select_base_configs(config)
        selected_regime_configs = self._select_regime_configs(config, selected_base_configs)
        diagnostics = self._collect_diagnostics(
            config=config,
            selected_base_configs=selected_base_configs,
            logger=logger,
        )
        regime_status = self._build_regime_status(
            regime_config_count=len(selected_regime_configs),
            regime_features_attached=bool(diagnostics["regime_features_attached"]),
            regime_feature_count=int(diagnostics["regime_feature_count"]),
        )
        regime_training_applied = bool(regime_status["regime_specific_training_applied"])
        warnings = self._string_list(diagnostics.get("warnings")) + self._string_list(
            regime_status.get("missing_requirements")
        )

        if config.dry_run:
            candidate_results = self._dry_run_candidates(
                selected_base_configs,
                feature_weak_signal_detected=bool(diagnostics["feature_quality_summary"]["weak_signal_detected"]),
                feature_leakage_risk_detected=bool(diagnostics["feature_leakage_summary"]["leakage_risk_detected"]),
                real_feature_diagnostics=self._as_dict(diagnostics.get("real_feature_diagnostics")),
                real_feature_diagnostics_missing_reason=diagnostics.get("real_feature_diagnostics_missing_reason"),
                logger=logger,
            )
            experiment_status = "DRY_RUN_COMPLETED"
        elif config.sample_mode:
            candidate_results = self._sample_candidates(
                selected_base_configs,
                feature_weak_signal_detected=bool(diagnostics["feature_quality_summary"]["weak_signal_detected"]),
                feature_leakage_risk_detected=bool(diagnostics["feature_leakage_summary"]["leakage_risk_detected"]),
                real_feature_diagnostics=self._as_dict(diagnostics.get("real_feature_diagnostics")),
                real_feature_diagnostics_missing_reason=diagnostics.get("real_feature_diagnostics_missing_reason"),
                logger=logger,
            )
            experiment_status = "SAMPLE_COMPLETED"
        else:
            candidate_results, experiment_status, runtime_warnings = self._real_candidates(
                config=config,
                experiment_id=experiment_id,
                selected_base_configs=selected_base_configs,
                feature_weak_signal_detected=bool(diagnostics["feature_quality_summary"]["weak_signal_detected"]),
                feature_leakage_risk_detected=bool(diagnostics["feature_leakage_summary"]["leakage_risk_detected"]),
                real_feature_diagnostics=self._as_dict(diagnostics.get("real_feature_diagnostics")),
                real_feature_diagnostics_missing_reason=diagnostics.get("real_feature_diagnostics_missing_reason"),
                logger=logger,
                experiment_dir=logger.paths.experiment_dir,
            )
            warnings.extend(runtime_warnings)

        regime_training_applied = any(
            item.regime_specific_training_applied for item in candidate_results
        )
        aggregate_regime_status = self._aggregate_regime_label_builder_status(
            diagnostics_status=self._as_dict(diagnostics.get("regime_label_builder_status")),
            candidate_results=candidate_results,
            fallback_missing_requirements=self._string_list(regime_status.get("missing_requirements")),
        )
        if (
            aggregate_regime_status.get("regime_label_builder_used_in_training_any", False)
            or aggregate_regime_status.get("regime_specific_training_applied_any", False)
        ):
            warnings = [
                item for item in warnings if item != "regime_runtime_labels_not_built"
            ]
        ranking = self._ranking(candidate_results)
        accepted_count = sum(
            int(item.candidate_status == "ACCEPTED")
            for item in candidate_results
        )
        rejected_count = sum(
            int(item.candidate_status == "REJECTED")
            for item in candidate_results
        )
        failed_count = sum(int(item.candidate_status == "FAILED") for item in candidate_results)
        best_candidate = next((item for item in candidate_results if item.score is not None), None)
        failed_gates_summary = self._failed_gates_summary(candidate_results)
        recommendations = self._recommendations(
            feature_quality=diagnostics["feature_quality_summary"],
            regime_feature_diagnostics=diagnostics["regime_feature_summary"],
            leakage_guard=diagnostics["feature_leakage_summary"],
            regime_plan=diagnostics["regime_experiment_plan_summary"],
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
            evaluated_candidate_count=sum(
                int(item.candidate_status in {"ACCEPTED", "REJECTED", "FAILED"})
                for item in candidate_results
            ),
            failed_candidate_count=failed_count,
            accepted_candidate_count=accepted_count,
            rejected_candidate_count=rejected_count,
            best_candidate_id=None if best_candidate is None else best_candidate.candidate_id,
            best_candidate_config_id=None if best_candidate is None else best_candidate.config_id,
            best_candidate_score=None if best_candidate is None else best_candidate.score,
            feature_quality_summary=diagnostics["feature_quality_summary"],
            feature_group_quality_summary=diagnostics["feature_group_quality_summary"],
            regime_feature_summary=diagnostics["regime_feature_summary"],
            feature_leakage_summary=diagnostics["feature_leakage_summary"],
            regime_experiment_plan_summary=diagnostics["regime_experiment_plan_summary"],
            candidate_results=tuple(candidate_results),
            ranking=tuple(ranking),
            failed_gates_summary=failed_gates_summary,
            warnings=tuple(dict.fromkeys(warnings)),
            recommendations=tuple(recommendations),
            regime_training_applied=regime_training_applied,
            real_feature_diagnostics_used=bool(diagnostics["real_feature_diagnostics_used"]),
            real_feature_diagnostics_row_count=int(diagnostics["real_feature_diagnostics_row_count"]),
            feature_version_used=config.feature_version,
            regime_features_attached=bool(diagnostics["regime_features_attached"]),
            regime_feature_count=int(diagnostics["regime_feature_count"]),
            regime_feature_source=str(diagnostics["regime_feature_source"]),
            regime_specific_labeling_available=bool(regime_status["regime_specific_labeling_available"]),
            regime_specific_training_applied=regime_training_applied,
            missing_requirements=tuple(
                self._string_list(aggregate_regime_status.get("missing_requirements"))
            ),
            effective_gap_count_for_training=int(diagnostics["effective_gap_count_for_training"]),
            gap_severity_for_training=str(diagnostics["gap_severity_for_training"]),
            gap_training_safe=bool(diagnostics["gap_training_safe"]),
            output_dir=str(logger.paths.experiment_dir),
            log_path=str(logger.paths.log_path),
            events_path=str(logger.paths.events_path),
            summary_json_path=str(logger.paths.summary_json_path),
            summary_markdown_path=str(logger.paths.summary_markdown_path),
            baseline_reference=dict(DEFAULT_ML31_BASELINE_REFERENCE),
            probability_diagnostics=dict(
                {} if best_candidate is None else best_candidate.probability_diagnostics
            ),
            probability_diagnostics_missing_reason=(
                None
                if best_candidate is not None and best_candidate.probability_diagnostics
                else "not_available_from_final_candidate"
                if best_candidate is None
                else best_candidate.probability_diagnostics_missing_reason
                or "not_available_from_final_candidate"
            ),
            real_feature_diagnostics=self._as_dict(diagnostics.get("real_feature_diagnostics")),
            real_feature_diagnostics_missing_reason=(
                None
                if self._as_dict(diagnostics.get("real_feature_diagnostics"))
                else diagnostics.get("real_feature_diagnostics_missing_reason")
                or "real_feature_diagnostics_not_available"
            ),
            collapse_diagnostics_v2=dict(
                {} if best_candidate is None else best_candidate.collapse_diagnostics_v2
            ),
            collapse_diagnostics_v2_missing_reason=(
                None
                if best_candidate is not None and best_candidate.collapse_diagnostics_v2
                else "not_available_from_final_candidate"
                if best_candidate is None
                else best_candidate.collapse_diagnostics_v2_missing_reason
                or "not_available_from_final_candidate"
            ),
            regime_label_builder_status=dict(aggregate_regime_status),
            regime_label_builder_status_missing_reason=(
                None if aggregate_regime_status else "not_available_from_runtime_payload"
            ),
            walk_forward_profit_diagnostics=dict(
                {} if best_candidate is None else best_candidate.walk_forward_profit_diagnostics
            ),
            walk_forward_profit_diagnostics_missing_reason=(
                None
                if best_candidate is not None and best_candidate.walk_forward_profit_diagnostics
                else "not_available_from_final_candidate"
                if best_candidate is None
                else best_candidate.walk_forward_profit_diagnostics_missing_reason
                or "not_available_from_final_candidate"
            ),
            profit_aware_diagnostics=dict(
                {} if best_candidate is None else best_candidate.profit_aware_diagnostics
            ),
            profit_aware_diagnostics_missing_reason=(
                None
                if best_candidate is not None and best_candidate.profit_aware_diagnostics
                else "not_available_from_final_candidate"
                if best_candidate is None
                else best_candidate.profit_aware_diagnostics_missing_reason
                or "not_available_from_final_candidate"
            ),
            regime_label_builder_used_in_training_any=bool(
                aggregate_regime_status.get("regime_label_builder_used_in_training_any", False)
            ),
            regime_label_builder_used_in_training_all=bool(
                aggregate_regime_status.get("regime_label_builder_used_in_training_all", False)
            ),
            regime_specific_training_applied_any=bool(
                aggregate_regime_status.get("regime_specific_training_applied_any", False)
            ),
            regime_specific_training_applied_all=bool(
                aggregate_regime_status.get("regime_specific_training_applied_all", False)
            ),
            candle_ta_context_features_attached=bool(diagnostics.get("candle_ta_context_features_attached", False)),
            candidate_status=None if best_candidate is None else best_candidate.candidate_status,
            model_quality_validation_status=(
                None if best_candidate is None else best_candidate.model_quality_validation_status
            ),
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
                "failed_candidate_count": failed_count,
                "best_candidate_config_id": result.best_candidate_config_id,
                "selected_regime_config_count": len(selected_regime_configs),
                "regime_training_applied": regime_training_applied,
                "feature_version_used": config.feature_version,
                "real_feature_diagnostics_used": diagnostics["real_feature_diagnostics_used"],
                "real_feature_diagnostics_row_count": diagnostics["real_feature_diagnostics_row_count"],
                "regime_features_attached": diagnostics["regime_features_attached"],
                "candle_ta_context_features_attached": diagnostics.get("candle_ta_context_features_attached", False),
                "effective_gap_count_for_training": diagnostics["effective_gap_count_for_training"],
                "gap_severity_for_training": diagnostics["gap_severity_for_training"],
            },
            message="Feature/regime experiment completed",
        )
        return result

    def _collect_diagnostics(
        self,
        *,
        config: FeatureRegimeExperimentConfig,
        selected_base_configs: list[dict[str, Any]],
        logger: _ExperimentLogger,
    ) -> dict[str, Any]:
        logger.event(event="diagnostics_started", status="RUNNING", message="Diagnostics collection started")
        diagnostics_dir = logger.paths.diagnostics_dir
        selected_label_config = (
            dict(selected_base_configs[0]) if selected_base_configs else self._fallback_label_config_payload()
        )
        real_feature_diagnostics = self._build_real_feature_diagnostics(
            config=config,
            label_config_payload=selected_label_config,
        )
        feature_quality = (
            dict(real_feature_diagnostics.get("feature_quality", {}))
            if config.run_feature_diagnostics
            else {"diagnostic_name": "feature_quality_diagnostics", "diagnostic_skipped": True, "weak_signal_detected": False}
        )
        feature_group_quality = (
            dict(real_feature_diagnostics.get("feature_group_quality", {}))
            if config.run_feature_diagnostics
            else {"group_name": "feature_group_quality", "diagnostic_skipped": True}
        )
        regime_feature_diagnostics = (
            dict(real_feature_diagnostics.get("regime_feature_diagnostics", {}))
            if config.run_regime_diagnostics
            else {"diagnostic_name": "regime_feature_diagnostics", "diagnostic_skipped": True, "regime_data_available": False}
        )
        feature_leakage = (
            dict(real_feature_diagnostics.get("leakage_guard", {}))
            if config.run_leakage_guard
            else {"guard_name": "feature_leakage_guard", "diagnostic_skipped": True, "leakage_risk_detected": False}
        )
        regime_experiment_plan = self._regime_experiment_planner.build_plan(
            symbol=config.symbol,
            interval=config.interval,
            start_date=config.start_date,
            regime_data_available=bool(regime_feature_diagnostics.get("regime_data_available", False)),
            base_label_config_id=(selected_base_configs[0]["config_id"] if selected_base_configs else "lv2_h12_thr05_tp15_sl10"),
        )
        gap_quality = self._build_gap_quality_summary(config)
        feature_names = feature_names_for_version(config.feature_version)
        regime_feature_names = [name for name in feature_names if name.startswith("regime_")]
        regime_features_attached = bool(regime_feature_names) and bool(regime_feature_diagnostics.get("regime_data_available", False))
        self._reporter.write_diagnostics_json(feature_quality, diagnostics_dir / "feature_quality.json")
        self._reporter.write_diagnostics_json(feature_group_quality, diagnostics_dir / "feature_group_quality.json")
        self._reporter.write_diagnostics_json(regime_feature_diagnostics, diagnostics_dir / "regime_feature_diagnostics.json")
        self._reporter.write_diagnostics_json(feature_leakage, diagnostics_dir / "feature_leakage_guard.json")
        self._reporter.write_diagnostics_json(regime_experiment_plan, diagnostics_dir / "regime_experiment_plan.json")
        self._reporter.write_diagnostics_json(real_feature_diagnostics, diagnostics_dir / "real_feature_diagnostics.json")
        self._reporter.write_diagnostics_json(gap_quality, diagnostics_dir / "gap_quality.json")
        logger.event(
            event="diagnostics_completed",
            status="COMPLETED",
            data={
                "feature_weak_signal_detected": feature_quality.get("weak_signal_detected"),
                "regime_data_available": regime_feature_diagnostics.get("regime_data_available"),
                "feature_leakage_risk_detected": feature_leakage.get("leakage_risk_detected"),
                "ready_for_real_regime_training": regime_experiment_plan.get("ready_for_real_regime_training"),
                "real_feature_diagnostics_used": real_feature_diagnostics.get("real_feature_diagnostics_used"),
                "real_feature_diagnostics_row_count": real_feature_diagnostics.get("row_count"),
                "regime_features_attached": regime_features_attached,
                "candle_ta_context_features_attached": real_feature_diagnostics.get("candle_ta_context_features_attached"),
            },
            message="Diagnostics collection completed",
        )
        return {
            "feature_quality_summary": feature_quality,
            "feature_group_quality_summary": feature_group_quality,
            "regime_feature_summary": regime_feature_diagnostics,
            "feature_leakage_summary": feature_leakage,
            "regime_experiment_plan_summary": regime_experiment_plan,
            "real_feature_diagnostics": real_feature_diagnostics,
            "regime_label_builder_status": self._as_dict(
                real_feature_diagnostics.get("regime_label_builder_status", {})
            ),
            "real_feature_diagnostics_used": bool(real_feature_diagnostics.get("real_feature_diagnostics_used", False)),
            "real_feature_diagnostics_row_count": int(real_feature_diagnostics.get("row_count", 0) or 0),
            "regime_features_attached": regime_features_attached,
            "candle_ta_context_features_attached": bool(
                real_feature_diagnostics.get("candle_ta_context_features_attached", False)
            ),
            "regime_feature_count": len(regime_feature_names),
            "regime_feature_source": str(real_feature_diagnostics.get("source", "unknown")),
            "effective_gap_count_for_training": int(gap_quality.get("effective_gap_count_for_training", 0) or 0),
            "gap_severity_for_training": str(gap_quality.get("gap_severity_for_training") or "OK"),
            "gap_training_safe": bool(gap_quality.get("dataset_safe_for_training", False)),
            "warnings": self._string_list(real_feature_diagnostics.get("warnings")),
            "real_feature_diagnostics_missing_reason": (
                None
                if bool(real_feature_diagnostics.get("row_count", 0))
                else str(real_feature_diagnostics.get("reason") or "real_feature_diagnostics_not_computed")
            ),
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

    def _build_real_feature_diagnostics(
        self,
        *,
        config: FeatureRegimeExperimentConfig,
        label_config_payload: dict[str, Any],
    ) -> dict[str, Any]:
        label_version = str(label_config_payload["label_version"])
        horizon_candles = int(label_config_payload["horizon"])
        if config.dry_run or config.sample_mode:
            payload = self._real_feature_diagnostics_service.analyze(
                symbol=config.symbol,
                interval=config.interval,
                feature_version=config.feature_version,
                label_version=label_version,
                rows=self._build_sample_rows(),
                source="sample_rows",
                sample_mode=True,
            )
            payload["regime_label_builder_status"] = self._sample_regime_label_builder_status()
            return payload

        with get_session() as session:
            dataset_builder = DatasetBuilder(
                feature_repository=FeatureRepository(session),
                label_repository=LabelRepository(session),
            )
            try:
                rows, _summary = dataset_builder.build_rows(
                    symbol=config.symbol,
                    interval=config.interval,
                    horizon_candles=horizon_candles,
                    feature_version=config.feature_version,
                    label_version=label_version,
                )
            except Exception as exc:
                rows = []
                warnings = [f"dataset_rows_unavailable:{exc}"]
            else:
                warnings = ["dataset_rows_unavailable"] if not rows else []

        if rows:
            payload = self._real_feature_diagnostics_service.analyze(
                symbol=config.symbol,
                interval=config.interval,
                feature_version=config.feature_version,
                label_version=label_version,
                rows=rows,
                source="dataset_builder",
                sample_mode=False,
            )
            payload["regime_label_builder_status"] = self._runtime_regime_label_builder_status(
                label_config_payload=label_config_payload,
                used_in_training=False,
            )
            return payload

        runtime_rows, runtime_warnings, runtime_source, regime_status = self._build_runtime_diagnostic_rows(
            config=config,
            label_config_payload=label_config_payload,
        )
        resolved_warnings = list(runtime_warnings)
        if not runtime_rows:
            resolved_warnings = warnings + runtime_warnings
        payload = self._real_feature_diagnostics_service.analyze(
            symbol=config.symbol,
            interval=config.interval,
            feature_version=config.feature_version,
            label_version=label_version,
            rows=runtime_rows,
            source=runtime_source,
            sample_mode=False,
            warnings=resolved_warnings,
            reason="dataset_rows_unavailable" if not runtime_rows else None,
        )
        payload["regime_label_builder_status"] = regime_status
        return payload

    def _build_gap_quality_summary(self, config: FeatureRegimeExperimentConfig) -> dict[str, Any]:
        if config.dry_run or config.sample_mode:
            return self._gap_quality_fallback(
                config,
                reason="gap_quality_skipped_for_non_real_run",
            )

        from app.data.candle_gap_checker import CandleGapChecker
        from app.db.repositories.candle_repository import CandleRepository
        from app.training.training_pipeline_runner import LongHistoryTrainingPipelineRunner

        start_at, end_at = LongHistoryTrainingPipelineRunner._build_utc_date_range(
            LongHistoryTrainingPipelineRunner._parse_date(config.start_date),
            LongHistoryTrainingPipelineRunner._parse_date(config.resolved_end_date()),
        )

        try:
            with get_session() as session:
                candles = CandleRepository(session).get_range(
                    symbol=config.symbol,
                    interval=config.interval,
                    start_at=start_at,
                    end_at=end_at,
                )
        except Exception as exc:
            return self._gap_quality_fallback(
                config,
                reason=f"gap_quality_data_unavailable:{type(exc).__name__}",
            )

        gap_stage = self._as_dict(CandleGapChecker().check(
            candles=candles,
            interval=config.interval,
            start_at=start_at,
            end_at=end_at,
            symbol=config.symbol,
        ))
        return GapQualityDiagnostics().analyze(
            symbol=config.symbol,
            interval=config.interval,
            start_date=config.start_date,
            end_date=config.resolved_end_date(),
            gap_count=int(gap_stage.get("gap_count", 0)),
            missing_open_times=self._string_list(gap_stage.get("missing_open_times")),
            last_open_time=gap_stage.get("last_open_time"),
            real_gap_count=gap_stage.get("real_gap_count"),
            real_missing_open_times=self._string_list(gap_stage.get("real_missing_open_times")),
            trailing_incomplete_count=gap_stage.get("trailing_incomplete_count"),
            trailing_incomplete_open_times=self._string_list(
                gap_stage.get("trailing_incomplete_open_times")
            ),
            trailing_incomplete_range_detected=gap_stage.get("trailing_incomplete_range_detected"),
        )

    def _gap_quality_fallback(
        self,
        config: FeatureRegimeExperimentConfig,
        *,
        reason: str,
    ) -> dict[str, Any]:
        payload = GapQualityDiagnostics().analyze(
            symbol=config.symbol,
            interval=config.interval,
            start_date=config.start_date,
            end_date=config.resolved_end_date(),
            gap_count=0,
            missing_open_times=[],
            last_open_time=None,
            real_gap_count=0,
            real_missing_open_times=[],
            trailing_incomplete_count=0,
            trailing_incomplete_open_times=[],
            trailing_incomplete_range_detected=False,
        )
        warnings = self._string_list(payload.get("warnings"))
        warnings.append(reason)
        recommendations = self._string_list(payload.get("recommendations"))
        recommendations.insert(
            0,
            "Gap quality summary is in degraded fallback mode; use a real dataset-backed run for authoritative gap classification.",
        )
        payload["degraded_mode"] = True
        payload["detail_gap_data_available"] = False
        payload["dataset_safe_for_training"] = False
        payload["warnings"] = list(dict.fromkeys(warnings))
        payload["recommendations"] = list(dict.fromkeys(recommendations))
        return payload

    def _build_regime_status(
        self,
        *,
        regime_config_count: int,
        regime_features_attached: bool,
        regime_feature_count: int,
    ) -> dict[str, Any]:
        return self._regime_label_integration_status.build_status(
            regime_specific_labeling_available=regime_config_count > 0,
            regime_features_attached=regime_features_attached,
            regime_feature_count=regime_feature_count,
            training_pipeline_supports_regime_labels=True,
        )

    def _dry_run_candidates(
        self,
        selected_base_configs: list[dict[str, Any]],
        *,
        feature_weak_signal_detected: bool,
        feature_leakage_risk_detected: bool,
        real_feature_diagnostics: dict[str, Any],
        real_feature_diagnostics_missing_reason: str | None,
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
                candidate_status="PLANNED",
                raw_candidate_status="PLANNED",
                score=None,
                warnings=("dry_run_no_training",),
                recommendations=("Dry-run only; no training was executed.",),
                regime_specific_training_applied=False,
                feature_weak_signal_detected=feature_weak_signal_detected,
                feature_leakage_risk_detected=feature_leakage_risk_detected,
                real_feature_diagnostics=real_feature_diagnostics,
                real_feature_diagnostics_missing_reason=real_feature_diagnostics_missing_reason,
                regime_label_builder_status=self._runtime_regime_label_builder_status(
                    label_config_payload=dict(config_payload),
                    used_in_training=False,
                ),
                regime_label_builder_status_missing_reason=None,
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
        real_feature_diagnostics: dict[str, Any],
        real_feature_diagnostics_missing_reason: str | None,
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
                candidate_status="REJECTED",
                raw_candidate_status="CANDIDATE_REJECTED",
                score=score,
                failed_gates=failed_gates,
                passed_gates=("baseline_edge_gate",),
                warnings=("sample_mode_result",),
                recommendations=("Sample-only candidate; use for research workflow validation only.",),
                regime_specific_training_applied=False,
                feature_weak_signal_detected=feature_weak_signal_detected,
                feature_leakage_risk_detected=feature_leakage_risk_detected,
                real_feature_diagnostics=real_feature_diagnostics,
                real_feature_diagnostics_missing_reason=real_feature_diagnostics_missing_reason,
                regime_label_builder_status=self._sample_regime_label_builder_status(),
                regime_label_builder_status_missing_reason=None,
            )
            candidates.append(result)
            logger.event(
                event="candidate_rejected",
                status="REJECTED",
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
        real_feature_diagnostics: dict[str, Any],
        real_feature_diagnostics_missing_reason: str | None,
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
                feature_version=config.feature_version,
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
                raw_candidate_status=getattr(item, "raw_candidate_status", item.candidate_status),
                score=ranking_row.get("score"),
                failed_gates=tuple(item.failed_gates),
                passed_gates=tuple(item.passed_gates),
                warnings=tuple(item.warnings),
                recommendations=tuple(item.recommendations),
                regime_specific_training_applied=bool(
                    self._as_dict(item.regime_label_builder_status).get(
                        "regime_specific_training_applied",
                        False,
                    )
                ),
                feature_weak_signal_detected=feature_weak_signal_detected,
                feature_leakage_risk_detected=feature_leakage_risk_detected,
                probability_diagnostics=self._as_dict(getattr(item, "probability_diagnostics", {})),
                probability_diagnostics_missing_reason=getattr(
                    item,
                    "probability_diagnostics_missing_reason",
                    None,
                ),
                real_feature_diagnostics=real_feature_diagnostics,
                real_feature_diagnostics_missing_reason=real_feature_diagnostics_missing_reason,
                collapse_diagnostics_v2=self._as_dict(item.collapse_diagnostics_v2),
                collapse_diagnostics_v2_missing_reason=getattr(
                    item,
                    "collapse_diagnostics_v2_missing_reason",
                    None,
                ),
                regime_label_builder_status=self._as_dict(item.regime_label_builder_status),
                regime_label_builder_status_missing_reason=getattr(
                    item,
                    "regime_label_builder_status_missing_reason",
                    None,
                ),
                walk_forward_profit_diagnostics=self._as_dict(item.walk_forward_profit_diagnostics),
                walk_forward_profit_diagnostics_missing_reason=getattr(
                    item,
                    "walk_forward_profit_diagnostics_missing_reason",
                    None,
                ),
                profit_aware_diagnostics=self._as_dict(item.profit_aware_diagnostics),
                profit_aware_diagnostics_missing_reason=getattr(
                    item,
                    "profit_aware_diagnostics_missing_reason",
                    None,
                ),
                model_quality_validation_status=getattr(item, "model_quality_validation_status", "COMPLETED"),
                model_accuracy=getattr(item, "model_accuracy", None),
                baseline_accuracy=getattr(item, "baseline_accuracy", None),
                accuracy_edge=getattr(item, "accuracy_edge", None),
                profit_total_r=getattr(item, "profit_total_r", None),
                profit_factor=getattr(item, "profit_factor", None),
                walk_forward_total_r=getattr(item, "walk_forward_global_total_r", None),
                walk_forward_profit_factor=getattr(item, "walk_forward_profit_factor", None),
                predicted_class_distribution=self._as_dict(getattr(item, "predicted_distribution", {})),
                actual_class_distribution=self._as_dict(getattr(item, "actual_distribution", {})),
                collapse_detected=bool(getattr(item, "collapse_detected", False)),
                collapse_type=getattr(item, "collapse_type", None),
            )
            candidate_results.append(candidate)
            logger.event(
                event=(
                    "candidate_accepted_for_research"
                    if item.candidate_status == "ACCEPTED"
                    else "candidate_failed"
                    if item.candidate_status == "FAILED"
                    else "candidate_rejected"
                ),
                status=item.status,
                candidate_id=item.config_id,
                data={
                    "config_id": item.config_id,
                    "candidate_status": item.candidate_status,
                    "score": ranking_row.get("score"),
                },
                message="Real candidate completed",
            )
        runtime_warnings: list[str] = []
        if not any(
            dict(item.regime_label_builder_status).get("regime_label_builder_used_in_training", False)
            for item in inner_result.candidate_results
        ):
            runtime_warnings.append("regime_specific_training_not_applied")
        if inner_result.feature_version_used != config.feature_version:
            runtime_warnings.append("feature_version_requested_but_not_applied")
        return candidate_results, str(inner_result.experiment_status), runtime_warnings

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

    @classmethod
    def _recommendations(
        cls,
        *,
        feature_quality: dict[str, Any],
        regime_feature_diagnostics: dict[str, Any],
        leakage_guard: dict[str, Any],
        regime_plan: dict[str, Any],
        regime_training_applied: bool,
    ) -> list[str]:
        recommendations = cls._string_list(feature_quality.get("recommendations"))
        recommendations.extend(cls._string_list(regime_feature_diagnostics.get("recommendations")))
        recommendations.extend(cls._string_list(leakage_guard.get("recommendations")))
        recommendations.extend(cls._string_list(regime_plan.get("recommendations")))
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
                    "regime_unknown": 0.0,
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
                    "regime_unknown": 0.0,
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
                    "regime_unknown": 0.0,
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
                    "regime_unknown": 0.0,
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
                    "regime_unknown": 0.0,
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
                    "regime_unknown": 1.0,
                },
            },
        ]

    @staticmethod
    def _fallback_label_config_payload() -> dict[str, Any]:
        return {
            "config_id": "lv2_h12_thr05_tp15_sl10",
            "label_version": "lv2_h12_thr05_tp15_sl10",
            "horizon": 12,
            "threshold": 0.5,
            "take_profit_atr": 1.5,
            "stop_loss_atr": 1.0,
        }

    def _build_runtime_diagnostic_rows(
        self,
        *,
        config: FeatureRegimeExperimentConfig,
        label_config_payload: dict[str, Any],
    ) -> tuple[list[DatasetRow], list[str], str, dict[str, Any]]:
        warnings: list[str] = []
        with get_session() as session:
            candles = CandleRepository(session).get_all(symbol=config.symbol, interval=config.interval)
            feature_rows = FeatureRepository(session).get_all(
                symbol=config.symbol,
                interval=config.interval,
                feature_version=config.feature_version,
            )

        if not candles:
            return [], ["market_data_missing_for_symbol"], "runtime_context", self._runtime_regime_label_builder_status(
                label_config_payload=label_config_payload,
                used_in_training=False,
                missing_requirements=["market_data_missing_for_symbol"],
                reason="candles_missing",
            )
        if not feature_rows:
            return [], ["features_not_persisted_for_symbol"], "runtime_context", self._runtime_regime_label_builder_status(
                label_config_payload=label_config_payload,
                used_in_training=False,
                missing_requirements=["features_not_persisted_for_symbol"],
                reason="feature_rows_missing",
            )

        base_config = LabelConfig(
            label_version=str(label_config_payload["label_version"]),
            horizon_candles=int(label_config_payload["horizon"]),
            direction_atr_threshold=float(label_config_payload["threshold"]),
            take_profit_atr=float(label_config_payload["take_profit_atr"]),
            stop_loss_atr=float(label_config_payload["stop_loss_atr"]),
            flat_class_enabled=True,
        )
        regime_result = RegimeLabelBuilder().build(
            candles=candles,
            symbol=config.symbol,
            interval=config.interval,
            feature_rows=feature_rows,
            base_config=base_config,
        )
        warnings.extend(regime_result.warnings)
        label_records = regime_result.records
        source = "runtime_regime_label_builder"
        if not label_records:
            source = "runtime_label_builder"
            warnings.extend(regime_result.missing_requirements)
            label_records = LabelBuilder().build(
                candles=candles,
                symbol=config.symbol,
                interval=config.interval,
                horizon_candles=base_config.horizon_candles,
                label_version=base_config.label_version,
                config=base_config,
            )
        labels_by_open_time = {record.candle_open_time: record for record in label_records}
        rows: list[DatasetRow] = []
        for feature_row in feature_rows:
            features_json = dict(feature_row.features_json)
            if any(value is None for value in features_json.values()):
                continue
            label_row = labels_by_open_time.get(feature_row.candle_open_time)
            if label_row is None:
                continue
            rows.append(
                DatasetRow(
                    symbol=feature_row.symbol,
                    interval=feature_row.interval,
                    candle_open_time=feature_row.candle_open_time,
                    feature_version=feature_row.feature_version,
                    label_version=label_row.label_version,
                    horizon_candles=label_row.horizon_candles,
                    features_json=features_json,
                    direction_label=label_row.direction_label,
                    tp_before_sl=label_row.tp_before_sl,
                    future_return=float(label_row.future_return),
                    future_move_atr=float(label_row.future_move_atr),
                    max_favorable_move_atr=float(label_row.max_favorable_move_atr),
                    max_adverse_move_atr=float(label_row.max_adverse_move_atr),
                )
            )
        if not rows:
            warnings.append("runtime_dataset_not_built_for_symbol")
        return rows, list(dict.fromkeys(warnings)), source, regime_result.to_dict()

    @staticmethod
    def _runtime_regime_label_builder_status(
        *,
        label_config_payload: dict[str, Any],
        used_in_training: bool,
        missing_requirements: list[str] | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        return {
            "regime_label_builder_status": "built" if used_in_training else "blocked",
            "regime_label_builder_available": True,
            "regime_label_builder_used_in_training": used_in_training,
            "regime_specific_labeling_available": True,
            "regime_specific_training_applied": used_in_training,
            "regime_label_config_used": {
                "trend_up": f"{label_config_payload['label_version']}_trend_up",
                "trend_down": f"{label_config_payload['label_version']}_trend_down",
                "range": f"{label_config_payload['label_version']}_range",
                "high_volatility": f"{label_config_payload['label_version']}_high_volatility",
                "low_volatility": f"{label_config_payload['label_version']}_low_volatility",
                "unknown": f"{label_config_payload['label_version']}_unknown",
            },
            "label_distribution_by_regime": {},
            "missing_requirements": list(missing_requirements or ([] if used_in_training else ["regime_runtime_labels_not_built"])),
            "warnings": [],
            "reason": reason,
        }

    @staticmethod
    def _sample_regime_label_builder_status() -> dict[str, Any]:
        return {
            "regime_label_builder_status": "blocked",
            "regime_label_builder_available": True,
            "regime_label_builder_used_in_training": False,
            "regime_specific_labeling_available": True,
            "regime_specific_training_applied": False,
            "regime_label_config_used": {
                "trend_up": "lv2_h12_thr05_tp15_sl10_trend_up",
                "trend_down": "lv2_h12_thr05_tp15_sl10_trend_down",
                "range": "lv2_h12_thr05_tp15_sl10_range",
                "high_volatility": "lv2_h12_thr05_tp15_sl10_high_volatility",
                "low_volatility": "lv2_h12_thr05_tp15_sl10_low_volatility",
                "unknown": "lv2_h12_thr05_tp15_sl10_unknown",
            },
            "label_distribution_by_regime": {
                "trend_up": {"UP": 2, "DOWN": 0, "FLAT": 0},
                "trend_down": {"UP": 0, "DOWN": 1, "FLAT": 0},
            },
            "missing_requirements": ["sample_mode_no_real_training"],
            "warnings": ["sample_mode_result"],
            "reason": "sample_mode",
        }
