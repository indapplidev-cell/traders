from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
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
from app.diagnostics.baseline_edge_diagnostics import BaselineEdgeDiagnostics
from app.diagnostics.class_bias_diagnostics import ClassBiasDiagnostics
from app.diagnostics.collapse_diagnostics_v2 import classify_collapse_severity
from app.diagnostics.collapse_tuning_summary import CollapseTuningSummaryBuilder
from app.diagnostics.real_feature_diagnostics_service import RealFeatureDiagnosticsService
from app.diagnostics.regime_feature_diagnostics import RegimeFeatureDiagnostics
from app.diagnostics.anti_collapse_diagnostics import AntiCollapseDiagnostics
from app.diagnostics.confidence_profitability_diagnostics import ConfidenceProfitabilityDiagnostics
from app.evaluation.gap_quality_gate_normalizer import normalize_gap_quality_gate
from app.labels.label_builder import LabelBuilder
from app.labels.label_config import LabelConfig
from app.labels.regime_label_builder import RegimeLabelBuilder
from app.experiments.feature_regime_experiment_reporter import FeatureRegimeExperimentReporter
from app.experiments.label_grid_experiment_runner import (
    LabelGridExperimentConfig,
    LabelGridExperimentRunner,
)
from app.experiments.ml38_2_config_ranker import (
    ML382ConfigRanker,
    is_rankable_candidate_status,
)
from app.experiments.regime_experiment_planner import RegimeExperimentPlanner
from app.features.feature_builder import FeatureBuilder
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
    ranking_strategy: str = "default"
    output_dir: Path = Path("reports/feature_regime_experiments")
    skip_candle_load: bool = False

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
    symbol: str | None = None
    interval: str | None = None
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
    gap_severity_for_training: str | None = None
    gap_training_safe: bool = False
    regime_label_builder_used_in_training: bool = False
    real_feature_diagnostics_used: bool = False
    real_feature_diagnostics_row_count: int = 0
    regime_features_attached: bool = False
    regime_feature_count: int = 0
    regime_features_missing_reason: str | None = None
    candle_ta_context_features_attached: bool = False
    candle_ta_context_feature_count: int = 0
    candle_ta_context_missing_reason: str | None = None
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
    flat_bias_diagnostics: dict[str, Any] = field(default_factory=dict)
    flat_bias_diagnostics_missing_reason: str | None = None
    flat_bias_detected: bool = False
    down_blindness_detected: bool = False
    symbol_bias_severity: str | None = None
    collapse_tuning_summary: dict[str, Any] = field(default_factory=dict)
    collapse_tuning_summary_missing_reason: str | None = None
    score_components: dict[str, Any] = field(default_factory=dict)
    anti_collapse_diagnostics: dict[str, Any] = field(default_factory=dict)
    anti_collapse_score: float | None = None
    anti_collapse_status: str | None = None
    confidence_profitability_diagnostics: dict[str, Any] = field(default_factory=dict)
    confidence_profitability_score: float | None = None
    confidence_profitability_status: str | None = None
    baseline_edge: float | None = None
    baseline_edge_status: str | None = None
    baseline_edge_diagnostics: dict[str, Any] = field(default_factory=dict)
    collapse_severity: str | None = None
    collapse_gate_failed: bool = False
    collapse_severity_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
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
            "gap_severity_for_training": self.gap_severity_for_training,
            "gap_training_safe": self.gap_training_safe,
            "regime_label_builder_used_in_training": self.regime_label_builder_used_in_training,
            "real_feature_diagnostics_used": self.real_feature_diagnostics_used,
            "real_feature_diagnostics_row_count": self.real_feature_diagnostics_row_count,
            "regime_features_attached": self.regime_features_attached,
            "regime_feature_count": self.regime_feature_count,
            "regime_features_missing_reason": self.regime_features_missing_reason,
            "candle_ta_context_features_attached": self.candle_ta_context_features_attached,
            "candle_ta_context_feature_count": self.candle_ta_context_feature_count,
            "candle_ta_context_missing_reason": self.candle_ta_context_missing_reason,
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
            "flat_bias_diagnostics": dict(self.flat_bias_diagnostics),
            "flat_bias_diagnostics_missing_reason": self.flat_bias_diagnostics_missing_reason,
            "flat_bias_detected": self.flat_bias_detected,
            "down_blindness_detected": self.down_blindness_detected,
            "symbol_bias_severity": self.symbol_bias_severity,
            "collapse_tuning_summary": dict(self.collapse_tuning_summary),
            "collapse_tuning_summary_missing_reason": self.collapse_tuning_summary_missing_reason,
            "score_components": dict(self.score_components),
            "anti_collapse_diagnostics": dict(self.anti_collapse_diagnostics),
            "anti_collapse_score": self.anti_collapse_score,
            "anti_collapse_status": self.anti_collapse_status,
            "confidence_profitability_diagnostics": dict(self.confidence_profitability_diagnostics),
            "confidence_profitability_score": self.confidence_profitability_score,
            "confidence_profitability_status": self.confidence_profitability_status,
            "baseline_edge": self.baseline_edge,
            "baseline_edge_status": self.baseline_edge_status,
            "baseline_edge_diagnostics": dict(self.baseline_edge_diagnostics),
            "collapse_severity": self.collapse_severity,
            "collapse_gate_failed": self.collapse_gate_failed,
            "collapse_severity_reasons": list(self.collapse_severity_reasons),
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
    candle_ta_context_feature_count: int = 0
    candle_ta_context_missing_reason: str | None = None
    regime_features_missing_reason: str | None = None
    candidate_status: str | None = None
    model_quality_validation_status: str | None = None
    model_accepted: bool = False
    reasons_why_best_still_rejected: tuple[str, ...] = ()
    configs_ranked: tuple[dict[str, Any], ...] = ()
    flat_bias_summary: dict[str, Any] = field(default_factory=dict)
    down_blindness_summary: dict[str, Any] = field(default_factory=dict)
    baseline_edge_summary: dict[str, Any] = field(default_factory=dict)

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
            "candle_ta_context_feature_count": self.candle_ta_context_feature_count,
            "candle_ta_context_missing_reason": self.candle_ta_context_missing_reason,
            "regime_features_missing_reason": self.regime_features_missing_reason,
            "candidate_status": self.candidate_status,
            "model_quality_validation_status": self.model_quality_validation_status,
            "model_accepted": self.model_accepted,
            "reasons_why_best_still_rejected": list(self.reasons_why_best_still_rejected),
            "configs_ranked": [dict(item) for item in self.configs_ranked],
            "flat_bias_summary": dict(self.flat_bias_summary),
            "down_blindness_summary": dict(self.down_blindness_summary),
            "baseline_edge_summary": dict(self.baseline_edge_summary),
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
        self._class_bias_diagnostics = ClassBiasDiagnostics()
        self._collapse_tuning_summary_builder = CollapseTuningSummaryBuilder()
        self._anti_collapse_diagnostics = AntiCollapseDiagnostics()
        self._confidence_profitability_diagnostics = ConfidenceProfitabilityDiagnostics()
        self._ml38_2_ranker = ML382ConfigRanker()

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
    def _feature_names_from_rows(rows: list[Any]) -> set[str]:
        names: set[str] = set()
        for row in rows:
            features_json = (
                dict(row.get("features_json", {}))
                if isinstance(row, dict)
                else dict(getattr(row, "features_json", {}))
            )
            names.update(str(name) for name in features_json.keys())
        return names

    @classmethod
    def _rows_attach_requested_feature_version(
        cls,
        *,
        rows: list[Any],
        feature_version: str,
    ) -> bool:
        if not rows:
            return False
        if feature_version != RealFeatureDiagnosticsService.FV3_FEATURE_VERSION:
            return True
        return RealFeatureDiagnosticsService.FV3_REQUIRED_FEATURES.issubset(
            cls._feature_names_from_rows(rows)
        )

    @staticmethod
    def _candle_ta_context_missing_reason(
        *,
        feature_version: str,
        attached: bool,
        diagnostics: dict[str, Any],
        real_feature_diagnostics_missing_reason: str | None,
    ) -> str | None:
        if attached:
            return None
        if feature_version != RealFeatureDiagnosticsService.FV3_FEATURE_VERSION:
            return "feature_version_not_fv3_candle_ta_context"
        return str(
            diagnostics.get("candle_ta_context_missing_reason")
            or real_feature_diagnostics_missing_reason
            or "fv3_candle_ta_context_features_not_attached"
        )

    @staticmethod
    def _regime_features_missing_reason(
        *,
        attached: bool,
        diagnostics: dict[str, Any],
        real_feature_diagnostics_missing_reason: str | None,
    ) -> str | None:
        if attached:
            return None
        regime_feature_summary = dict(diagnostics.get("regime_feature_summary", {}))
        warnings = regime_feature_summary.get("warnings")
        warning_text = None
        if isinstance(warnings, list) and warnings:
            warning_text = ",".join(str(item) for item in warnings)
        return str(
            real_feature_diagnostics_missing_reason
            or warning_text
            or "regime_features_not_attached"
        )

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
                gap_severity_for_training=str(diagnostics["gap_severity_for_training"]),
                gap_training_safe=bool(diagnostics["gap_training_safe"]),
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
        candidate_results, ranking_payload = self._post_process_candidates_for_ranking(
            config=config,
            candidate_results=candidate_results,
        )
        ranking = (
            list(ranking_payload.get("ranking", []))
            if ranking_payload is not None
            else self._ranking(candidate_results)
        )
        accepted_count = sum(
            int(item.candidate_status == "ACCEPTED")
            for item in candidate_results
        )
        rejected_count = sum(
            int(item.candidate_status == "REJECTED")
            for item in candidate_results
        )
        failed_count = sum(int(item.candidate_status == "FAILED") for item in candidate_results)
        best_candidate = self._best_candidate_from_ranking(
            candidate_results=candidate_results,
            ranking=ranking,
        )
        failed_gates_summary = self._failed_gates_summary(candidate_results)
        recommendations = self._recommendations(
            feature_quality=diagnostics["feature_quality_summary"],
            regime_feature_diagnostics=diagnostics["regime_feature_summary"],
            leakage_guard=diagnostics["feature_leakage_summary"],
            regime_plan=diagnostics["regime_experiment_plan_summary"],
            regime_training_applied=regime_training_applied,
        )
        flat_bias_summary = self._flat_bias_summary(candidate_results)
        down_blindness_summary = self._down_blindness_summary(candidate_results)
        baseline_edge_summary = self._baseline_edge_summary(candidate_results)

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
                if bool(diagnostics.get("real_feature_diagnostics_used", False))
                and self._as_dict(diagnostics.get("real_feature_diagnostics"))
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
            candle_ta_context_feature_count=int(diagnostics.get("candle_ta_context_feature_count", 0) or 0),
            candle_ta_context_missing_reason=diagnostics.get("candle_ta_context_missing_reason"),
            regime_features_missing_reason=diagnostics.get("regime_features_missing_reason"),
            candidate_status=None if best_candidate is None else best_candidate.candidate_status,
            model_quality_validation_status=(
                None if best_candidate is None else best_candidate.model_quality_validation_status
            ),
            model_accepted=accepted_count > 0,
            reasons_why_best_still_rejected=tuple(
                [] if ranking_payload is None else ranking_payload.get("reasons_why_best_still_rejected", [])
            ),
            configs_ranked=tuple(ranking),
            flat_bias_summary=flat_bias_summary,
            down_blindness_summary=down_blindness_summary,
            baseline_edge_summary=baseline_edge_summary,
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
        regime_feature_count = int(
            real_feature_diagnostics.get("regime_feature_count", len(regime_feature_names)) or 0
        )
        regime_features_attached = bool(regime_feature_count) and bool(
            regime_feature_diagnostics.get("regime_data_available", False)
        )
        real_feature_diagnostics_missing_reason = (
            None
            if bool(real_feature_diagnostics.get("row_count", 0))
            else str(real_feature_diagnostics.get("reason") or "real_feature_diagnostics_not_computed")
        )
        candle_ta_context_missing_reason = self._candle_ta_context_missing_reason(
            feature_version=config.feature_version,
            attached=bool(real_feature_diagnostics.get("candle_ta_context_features_attached", False)),
            diagnostics=real_feature_diagnostics,
            real_feature_diagnostics_missing_reason=real_feature_diagnostics_missing_reason,
        )
        regime_features_missing_reason = self._regime_features_missing_reason(
            attached=regime_features_attached,
            diagnostics={
                "regime_feature_summary": regime_feature_diagnostics,
            },
            real_feature_diagnostics_missing_reason=real_feature_diagnostics_missing_reason,
        )
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
            "candle_ta_context_feature_count": int(
                real_feature_diagnostics.get("candle_ta_context_feature_count", 0) or 0
            ),
            "candle_ta_context_missing_reason": candle_ta_context_missing_reason,
            "regime_feature_count": regime_feature_count,
            "regime_features_missing_reason": regime_features_missing_reason,
            "regime_feature_source": str(real_feature_diagnostics.get("source", "unknown")),
            "effective_gap_count_for_training": int(gap_quality.get("effective_gap_count_for_training", 0) or 0),
            "gap_severity_for_training": str(gap_quality.get("gap_severity_for_training") or "OK"),
            "gap_training_safe": bool(gap_quality.get("dataset_safe_for_training", False)),
            "warnings": self._string_list(real_feature_diagnostics.get("warnings")),
            "real_feature_diagnostics_missing_reason": real_feature_diagnostics_missing_reason,
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

        from app.training.training_pipeline_runner import LongHistoryTrainingPipelineRunner

        start_at, end_at = LongHistoryTrainingPipelineRunner._build_utc_date_range(
            LongHistoryTrainingPipelineRunner._parse_date(config.start_date),
            LongHistoryTrainingPipelineRunner._parse_date(config.resolved_end_date()),
        )

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
                    start_at=start_at,
                    end_at=end_at,
                )
            except Exception as exc:
                rows = []
                warnings = [f"dataset_rows_unavailable:{exc}"]
            else:
                warnings = ["dataset_rows_unavailable"] if not rows else []

        if rows and self._rows_attach_requested_feature_version(
            rows=rows,
            feature_version=config.feature_version,
        ):
            payload = self._real_feature_diagnostics_service.analyze(
                symbol=config.symbol,
                interval=config.interval,
                feature_version=config.feature_version,
                label_version=label_version,
                rows=rows,
                source="dataset_builder",
                sample_mode=False,
            )
            payload["start_at"] = start_at.isoformat()
            payload["end_at"] = end_at.isoformat()
            payload["date_range_limited"] = True
            payload["regime_label_builder_status"] = self._runtime_regime_label_builder_status(
                label_config_payload=label_config_payload,
                used_in_training=False,
            )
            return payload
        if rows:
            warnings = warnings + ["dataset_rows_missing_requested_feature_attachment"]

        runtime_rows, runtime_warnings, runtime_source, regime_status = self._build_runtime_diagnostic_rows(
            config=config,
            label_config_payload=label_config_payload,
        )
        resolved_warnings = list(runtime_warnings)
        for warning in warnings:
            if warning == "dataset_rows_unavailable" and runtime_rows:
                continue
            resolved_warnings.append(warning)
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
        payload["start_at"] = start_at.isoformat()
        payload["end_at"] = end_at.isoformat()
        payload["date_range_limited"] = True
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
                regime_label_builder_used_in_training=False,
                feature_weak_signal_detected=feature_weak_signal_detected,
                feature_leakage_risk_detected=feature_leakage_risk_detected,
                real_feature_diagnostics_used=bool(real_feature_diagnostics.get("real_feature_diagnostics_used", False)),
                real_feature_diagnostics_row_count=int(real_feature_diagnostics.get("row_count", 0) or 0),
                regime_features_attached=False,
                regime_feature_count=0,
                regime_features_missing_reason="dry_run_no_runtime_regime_attachment",
                candle_ta_context_features_attached=bool(real_feature_diagnostics.get("candle_ta_context_features_attached", False)),
                candle_ta_context_feature_count=int(real_feature_diagnostics.get("candle_ta_context_feature_count", 0) or 0),
                candle_ta_context_missing_reason=real_feature_diagnostics.get("candle_ta_context_missing_reason"),
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
            failed_gates = ("collapse_gate", "walk_forward_gate") if index == 0 else ("collapse_gate", "profit_aware_gate")
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
                regime_label_builder_used_in_training=False,
                feature_weak_signal_detected=feature_weak_signal_detected,
                feature_leakage_risk_detected=feature_leakage_risk_detected,
                real_feature_diagnostics_used=bool(real_feature_diagnostics.get("real_feature_diagnostics_used", False)),
                real_feature_diagnostics_row_count=int(real_feature_diagnostics.get("row_count", 0) or 0),
                regime_features_attached=False,
                regime_feature_count=0,
                regime_features_missing_reason="sample_mode_no_runtime_regime_attachment",
                candle_ta_context_features_attached=bool(real_feature_diagnostics.get("candle_ta_context_features_attached", False)),
                candle_ta_context_feature_count=int(real_feature_diagnostics.get("candle_ta_context_feature_count", 0) or 0),
                candle_ta_context_missing_reason=real_feature_diagnostics.get("candle_ta_context_missing_reason"),
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
        gap_severity_for_training: str,
        gap_training_safe: bool,
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
                skip_candle_load=config.skip_candle_load,
            )
        )
        ranking_map = {
            str(item.get("config_id")): dict(item)
            for item in inner_result.candidate_ranking
        }
        candidate_results: list[FeatureRegimeCandidateResult] = []
        real_feature_diagnostics_used = bool(real_feature_diagnostics.get("real_feature_diagnostics_used", False))
        real_feature_diagnostics_row_count = int(real_feature_diagnostics.get("row_count", 0) or 0)
        candle_ta_context_features_attached = bool(
            real_feature_diagnostics.get("candle_ta_context_features_attached", False)
        )
        candle_ta_context_feature_count = int(
            real_feature_diagnostics.get("candle_ta_context_feature_count", 0) or 0
        )
        regime_feature_count = int(real_feature_diagnostics.get("regime_feature_count", 0) or 0)
        regime_features_attached = bool(regime_feature_count > 0)
        if isinstance(real_feature_diagnostics.get("regime_feature_diagnostics"), dict):
            regime_features_attached = bool(
                real_feature_diagnostics.get("regime_feature_diagnostics", {}).get("regime_data_available", False)
            ) and regime_features_attached
        regime_features_missing_reason = self._regime_features_missing_reason(
            attached=regime_features_attached,
            diagnostics={"regime_feature_summary": real_feature_diagnostics.get("regime_feature_diagnostics", {})},
            real_feature_diagnostics_missing_reason=real_feature_diagnostics_missing_reason,
        )
        candle_ta_context_missing_reason = self._candle_ta_context_missing_reason(
            feature_version=config.feature_version,
            attached=candle_ta_context_features_attached,
            diagnostics=real_feature_diagnostics,
            real_feature_diagnostics_missing_reason=real_feature_diagnostics_missing_reason,
        )
        for item in inner_result.candidate_results:
            ranking_row = ranking_map.get(item.config_id, {})
            failed_gates, passed_gates = normalize_gap_quality_gate(
                gap_severity_for_training=gap_severity_for_training,
                gap_training_safe=gap_training_safe,
                failed_gates=list(item.failed_gates),
                passed_gates=list(item.passed_gates),
            )
            candidate = FeatureRegimeCandidateResult(
                symbol=config.symbol,
                interval=config.interval,
                candidate_id=item.config_id,
                config_id=item.config_id,
                label_config=dict(item.label_config),
                status=item.status,
                quality_status=item.quality_status,
                candidate_status=item.candidate_status,
                raw_candidate_status=getattr(item, "raw_candidate_status", item.candidate_status),
                score=ranking_row.get("score"),
                failed_gates=tuple(failed_gates),
                passed_gates=tuple(passed_gates),
                warnings=tuple(item.warnings),
                recommendations=tuple(item.recommendations),
                regime_specific_training_applied=bool(
                    self._as_dict(item.regime_label_builder_status).get(
                        "regime_specific_training_applied",
                        False,
                    )
                ),
                regime_label_builder_used_in_training=bool(
                    self._as_dict(item.regime_label_builder_status).get(
                        "regime_label_builder_used_in_training",
                        False,
                    )
                ),
                feature_weak_signal_detected=feature_weak_signal_detected,
                feature_leakage_risk_detected=feature_leakage_risk_detected,
                gap_severity_for_training=gap_severity_for_training,
                gap_training_safe=gap_training_safe,
                probability_diagnostics=self._as_dict(getattr(item, "probability_diagnostics", {})),
                probability_diagnostics_missing_reason=getattr(
                    item,
                    "probability_diagnostics_missing_reason",
                    None,
                ),
                real_feature_diagnostics_used=real_feature_diagnostics_used,
                real_feature_diagnostics_row_count=real_feature_diagnostics_row_count,
                regime_features_attached=regime_features_attached,
                regime_feature_count=regime_feature_count,
                regime_features_missing_reason=regime_features_missing_reason,
                candle_ta_context_features_attached=candle_ta_context_features_attached,
                candle_ta_context_feature_count=candle_ta_context_feature_count,
                candle_ta_context_missing_reason=candle_ta_context_missing_reason,
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

    def _post_process_candidates_for_ranking(
        self,
        *,
        config: FeatureRegimeExperimentConfig,
        candidate_results: list[FeatureRegimeCandidateResult],
    ) -> tuple[list[FeatureRegimeCandidateResult], dict[str, Any] | None]:
        enriched: list[FeatureRegimeCandidateResult] = []
        for candidate in candidate_results:
            baseline_edge_diagnostics = BaselineEdgeDiagnostics().evaluate(
                accuracy=candidate.model_accuracy,
                baseline_accuracy=candidate.baseline_accuracy,
                symbol=config.symbol,
                config_id=candidate.config_id,
                min_positive_edge=float(candidate.label_config.get("baseline_edge_gate_min", 0.0) or 0.0),
            )
            collapse_severity = classify_collapse_severity(candidate.collapse_diagnostics_v2)
            class_bias = self._class_bias_payload(symbol=config.symbol, candidate=candidate)
            bias_failed_gates = self._bias_failed_gates(class_bias)
            failed_gates_list = [
                gate
                for gate in dict.fromkeys([*candidate.failed_gates, *bias_failed_gates])
                if gate not in {"baseline_edge_gate", "collapse_gate"}
            ]
            passed_gates_list = [
                gate
                for gate in candidate.passed_gates
                if gate not in {*bias_failed_gates, "baseline_edge_gate", "collapse_gate"}
            ]
            candidate_status = candidate.candidate_status
            if baseline_edge_diagnostics.baseline_edge_gate_failed and "baseline_edge_gate" not in failed_gates_list:
                failed_gates_list.append("baseline_edge_gate")
            elif not baseline_edge_diagnostics.baseline_edge_gate_failed:
                passed_gates_list.append("baseline_edge_gate")
            if collapse_severity["collapse_gate_failed"] and "collapse_gate" not in failed_gates_list:
                failed_gates_list.append("collapse_gate")
            elif collapse_severity["collapse_severity"] == "OK":
                passed_gates_list.append("collapse_gate")
            passed_gates_list = list(dict.fromkeys(passed_gates_list))
            if bias_failed_gates and candidate_status == "ACCEPTED":
                candidate_status = "REJECTED"
            if (
                baseline_edge_diagnostics.baseline_edge_gate_failed or collapse_severity["collapse_gate_failed"]
            ) and candidate_status == "ACCEPTED":
                candidate_status = "REJECTED"
            collapse_summary = self._collapse_tuning_summary_builder.build(
                collapse_diagnostics=self._as_dict(candidate.collapse_diagnostics_v2),
                class_bias_diagnostics=class_bias,
            ) if candidate.collapse_diagnostics_v2 or class_bias else {}
            anti_collapse = self._anti_collapse_diagnostics.build(
                symbol=config.symbol,
                config_id=candidate.config_id,
                flat_bias_diagnostics=class_bias,
                collapse_diagnostics_v2=self._as_dict(candidate.collapse_diagnostics_v2),
            ).to_dict() if candidate.collapse_diagnostics_v2 or class_bias else {}
            confidence_profitability = self._confidence_profitability_diagnostics.build(
                symbol=config.symbol,
                config_id=candidate.config_id,
                probability_diagnostics=self._as_dict(candidate.probability_diagnostics),
                collapse_diagnostics_v2=self._as_dict(candidate.collapse_diagnostics_v2),
                profit_aware_diagnostics=self._as_dict(candidate.profit_aware_diagnostics),
                walk_forward_profit_diagnostics=self._as_dict(candidate.walk_forward_profit_diagnostics),
                anti_collapse_diagnostics=anti_collapse,
            ).to_dict()
            enriched.append(
                replace(
                    candidate,
                    failed_gates=tuple(failed_gates_list),
                    passed_gates=tuple(passed_gates_list),
                    candidate_status=candidate_status,
                    flat_bias_diagnostics=class_bias,
                    flat_bias_diagnostics_missing_reason=(
                        None if class_bias else "predicted_or_actual_distribution_not_available"
                    ),
                    flat_bias_detected=bool(class_bias.get("flat_bias_detected", False)),
                    down_blindness_detected=bool(class_bias.get("down_blindness_detected", False)),
                    symbol_bias_severity=class_bias.get("symbol_bias_severity") if class_bias else None,
                    collapse_tuning_summary=collapse_summary,
                    collapse_tuning_summary_missing_reason=(
                        None if collapse_summary else "collapse_or_bias_diagnostics_not_available"
                    ),
                    anti_collapse_diagnostics=anti_collapse,
                    anti_collapse_score=anti_collapse.get("anti_collapse_score"),
                    anti_collapse_status=anti_collapse.get("anti_collapse_status"),
                    confidence_profitability_diagnostics=confidence_profitability,
                    confidence_profitability_score=confidence_profitability.get("confidence_profitability_score"),
                    confidence_profitability_status=confidence_profitability.get("confidence_profitability_status"),
                    baseline_edge=baseline_edge_diagnostics.baseline_edge,
                    baseline_edge_status=baseline_edge_diagnostics.baseline_edge_status,
                    baseline_edge_diagnostics=baseline_edge_diagnostics.to_dict(),
                    collapse_severity=collapse_severity["collapse_severity"],
                    collapse_gate_failed=bool(collapse_severity["collapse_gate_failed"]),
                    collapse_severity_reasons=tuple(collapse_severity["collapse_severity_reasons"]),
                )
            )

        if config.ranking_strategy != "ml38_2":
            return enriched, None

        ranking_payload = self._ml38_2_ranker.rank(enriched)
        ranking_by_config = {
            str(item["config_id"]): dict(item)
            for item in ranking_payload.get("ranking", [])
        }
        rescored: list[FeatureRegimeCandidateResult] = []
        for candidate in enriched:
            ranking_row = ranking_by_config.get(candidate.config_id, {})
            rescored.append(
                replace(
                    candidate,
                    score=ranking_row.get("score"),
                    score_components=dict(ranking_row.get("score_components", {})),
                )
            )
        return rescored, ranking_payload

    def _class_bias_payload(
        self,
        *,
        symbol: str,
        candidate: FeatureRegimeCandidateResult,
    ) -> dict[str, Any]:
        predicted = self._as_dict(candidate.predicted_class_distribution)
        actual = self._as_dict(candidate.actual_class_distribution)
        if not predicted or not actual:
            return {}
        return self._class_bias_diagnostics.analyze(
            predicted_distribution=predicted,
            actual_distribution=actual,
            symbol=symbol,
            config_id=candidate.config_id,
        )

    @staticmethod
    def _bias_failed_gates(class_bias: dict[str, Any]) -> tuple[str, ...]:
        if not class_bias:
            return ()
        return ("bias_gate",) if bool(class_bias.get("bias_gate_failed", False)) else ()

    @staticmethod
    def _best_candidate_from_ranking(
        *,
        candidate_results: list[FeatureRegimeCandidateResult],
        ranking: list[dict[str, Any]],
    ) -> FeatureRegimeCandidateResult | None:
        if not candidate_results:
            return None

        candidates_by_config = {
            candidate.config_id: candidate
            for candidate in candidate_results
        }

        if ranking:
            for row in ranking:
                if bool(row.get("excluded_from_best_selection", False)):
                    continue
                candidate = candidates_by_config.get(str(row.get("config_id") or ""))
                if candidate is None:
                    continue
                if is_rankable_candidate_status(candidate.candidate_status):
                    return candidate

        scored = [
            item
            for item in candidate_results
            if item.score is not None and is_rankable_candidate_status(item.candidate_status)
        ]
        if scored:
            return max(scored, key=lambda item: float(item.score or 0.0))

        eligible = [
            item
            for item in candidate_results
            if is_rankable_candidate_status(item.candidate_status)
        ]
        return eligible[0] if eligible else None

    @staticmethod
    def _flat_bias_summary(candidate_results: list[FeatureRegimeCandidateResult]) -> dict[str, Any]:
        return {
            "flat_bias_detected_count": sum(int(item.flat_bias_detected) for item in candidate_results),
            "severity_by_config": {
                item.config_id: item.symbol_bias_severity
                for item in candidate_results
            },
        }

    @staticmethod
    def _down_blindness_summary(candidate_results: list[FeatureRegimeCandidateResult]) -> dict[str, Any]:
        return {
            "down_blindness_detected_count": sum(
                int(item.down_blindness_detected) for item in candidate_results
            ),
            "detected_by_config": {
                item.config_id: item.down_blindness_detected
                for item in candidate_results
            },
        }

    @staticmethod
    def _baseline_edge_summary(candidate_results: list[FeatureRegimeCandidateResult]) -> dict[str, Any]:
        return {
            "positive_accuracy_edge_count": sum(
                int(((item.baseline_edge if item.baseline_edge is not None else item.accuracy_edge) or 0.0) > 0.0)
                for item in candidate_results
            ),
            "accuracy_edge_by_config": {
                item.config_id: item.baseline_edge if item.baseline_edge is not None else item.accuracy_edge
                for item in candidate_results
            },
        }

    @staticmethod
    def _ranking(candidate_results: list[FeatureRegimeCandidateResult]) -> list[dict[str, Any]]:
        scored = [
            item
            for item in candidate_results
            if item.score is not None and is_rankable_candidate_status(item.candidate_status)
        ]
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
                    "excluded_from_best_selection": False,
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
        from app.training.training_pipeline_runner import LongHistoryTrainingPipelineRunner

        warnings: list[str] = []
        start_at, end_at = LongHistoryTrainingPipelineRunner._build_utc_date_range(
            LongHistoryTrainingPipelineRunner._parse_date(config.start_date),
            LongHistoryTrainingPipelineRunner._parse_date(config.resolved_end_date()),
        )
        with get_session() as session:
            candle_repository = CandleRepository(session)
            feature_repository = FeatureRepository(session)

            if hasattr(candle_repository, "get_range"):
                try:
                    candles = candle_repository.get_range(
                        symbol=config.symbol,
                        interval=config.interval,
                        start_at=start_at,
                        end_at=end_at,
                    )
                except AttributeError:
                    candles = candle_repository.get_all(
                        symbol=config.symbol,
                        interval=config.interval,
                    )
            else:
                candles = candle_repository.get_all(
                    symbol=config.symbol,
                    interval=config.interval,
                )

            if hasattr(feature_repository, "get_range"):
                try:
                    feature_rows = feature_repository.get_range(
                        symbol=config.symbol,
                        interval=config.interval,
                        feature_version=config.feature_version,
                        start_at=start_at,
                        end_at=end_at,
                    )
                except AttributeError:
                    feature_rows = feature_repository.get_all(
                        symbol=config.symbol,
                        interval=config.interval,
                        feature_version=config.feature_version,
                    )
            else:
                feature_rows = feature_repository.get_all(
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
        feature_rows_source = "persisted_feature_rows"
        if not self._rows_attach_requested_feature_version(
            rows=feature_rows,
            feature_version=config.feature_version,
        ):
            feature_rows = FeatureBuilder().build(
                candles=candles,
                symbol=config.symbol,
                interval=config.interval,
                feature_version=config.feature_version,
            )
            feature_rows_source = "runtime_feature_builder"
        if not self._rows_attach_requested_feature_version(
            rows=feature_rows,
            feature_version=config.feature_version,
        ):
            missing_reason = (
                "fv3_candle_ta_context_feature_rows_missing"
                if config.feature_version == RealFeatureDiagnosticsService.FV3_FEATURE_VERSION
                else "feature_rows_missing_for_requested_feature_version"
            )
            return [], [missing_reason], "runtime_context", self._runtime_regime_label_builder_status(
                label_config_payload=label_config_payload,
                used_in_training=False,
                missing_requirements=[missing_reason],
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
        source = f"{feature_rows_source}_regime_label_builder"
        if not label_records:
            source = f"{feature_rows_source}_label_builder"
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
