from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.diagnostics.collapse_diagnostics_v2 import CollapseDiagnosticsV2
from app.diagnostics.walk_forward_profit_diagnostics import WalkForwardProfitDiagnostics
from app.diagnostics.gap_quality_diagnostics import GapQualityDiagnostics
from app.evaluation.anti_collapse_validator import AntiCollapseValidator
from app.evaluation.model_candidate_selector import ModelCandidateSelector


MODEL_QUALITY_VALIDATOR_NAME = "model_training_quality_validator"
MODEL_QUALITY_VALIDATOR_VERSION = "ml27"

QUALITY_APPROVED = "QUALITY_APPROVED"
QUALITY_REJECTED = "QUALITY_REJECTED"
NEEDS_MORE_DATA = "NEEDS_MORE_DATA"
INSUFFICIENT_REAL_HISTORY = "INSUFFICIENT_REAL_HISTORY"


@dataclass(frozen=True)
class ModelQualityValidationResult:
    validator_name: str
    validator_version: str
    quality_status: str
    approved_for_traders_core_integration: bool
    approved_for_live_trading: bool
    approved_for_auto_activation: bool
    sample_mode: bool
    real_training_executed: bool
    model_version: str | None
    training_run_id: str | None
    dataset_rows: int
    train_rows: int
    val_rows: int
    test_rows: int
    model_accuracy: float | None
    baseline_accuracy: float | None
    accuracy_edge: float | None
    collapse_detected: bool
    calibration_status: str
    profit_aware_status: str
    walk_forward_status: str
    gate_policy_replay_status: str
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    integration_status: dict[str, Any]
    probability_diagnostics: dict[str, Any] = field(default_factory=dict)
    gap_quality: dict[str, Any] = field(default_factory=dict)
    anti_collapse: dict[str, Any] = field(default_factory=dict)
    candidate_selection: dict[str, Any] = field(default_factory=dict)
    quality_gates_summary: dict[str, Any] = field(default_factory=dict)
    label_config: dict[str, Any] = field(default_factory=dict)
    feature_config: dict[str, Any] = field(default_factory=dict)
    collapse_diagnostics_v2: dict[str, Any] = field(default_factory=dict)
    regime_label_builder_status: dict[str, Any] = field(default_factory=dict)
    walk_forward_profit_diagnostics: dict[str, Any] = field(default_factory=dict)
    profit_aware_diagnostics: dict[str, Any] = field(default_factory=dict)
    opportunity_diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "validator_name": self.validator_name,
            "validator_version": self.validator_version,
            "quality_status": self.quality_status,
            "approved_for_traders_core_integration": self.approved_for_traders_core_integration,
            "approved_for_live_trading": self.approved_for_live_trading,
            "approved_for_auto_activation": self.approved_for_auto_activation,
            "sample_mode": self.sample_mode,
            "real_training_executed": self.real_training_executed,
            "model_version": self.model_version,
            "training_run_id": self.training_run_id,
            "dataset_rows": self.dataset_rows,
            "train_rows": self.train_rows,
            "val_rows": self.val_rows,
            "test_rows": self.test_rows,
            "model_accuracy": self.model_accuracy,
            "baseline_accuracy": self.baseline_accuracy,
            "accuracy_edge": self.accuracy_edge,
            "collapse_detected": self.collapse_detected,
            "calibration_status": self.calibration_status,
            "profit_aware_status": self.profit_aware_status,
            "walk_forward_status": self.walk_forward_status,
            "gate_policy_replay_status": self.gate_policy_replay_status,
            "reasons": list(self.reasons),
            "warnings": list(self.warnings),
            "integration_status": dict(self.integration_status),
            "probability_diagnostics": dict(self.probability_diagnostics),
            "gap_quality": dict(self.gap_quality),
            "anti_collapse": dict(self.anti_collapse),
            "candidate_selection": dict(self.candidate_selection),
            "quality_gates_summary": dict(self.quality_gates_summary),
            "label_config": dict(self.label_config),
            "feature_config": dict(self.feature_config),
            "collapse_diagnostics_v2": dict(self.collapse_diagnostics_v2),
            "regime_label_builder_status": dict(self.regime_label_builder_status),
            "walk_forward_profit_diagnostics": dict(self.walk_forward_profit_diagnostics),
            "profit_aware_diagnostics": dict(self.profit_aware_diagnostics),
            "opportunity_diagnostics": dict(self.opportunity_diagnostics),
        }


class ModelQualityValidator:
    """Validate whether a trained model looks analytically useful."""

    MIN_BASELINE_EDGE = ModelCandidateSelector.MIN_BASELINE_EDGE
    ACCEPTABLE_CALIBRATION_STATUSES = {"ACCEPTABLE", "ACCEPTABLE_SAMPLE"}
    POSITIVE_PROFIT_STATUSES = {"POSITIVE", "ACCEPTABLE", "ACCEPTABLE_SAMPLE"}
    STABLE_WALK_FORWARD_STATUSES = {"STABLE", "ACCEPTABLE", "ACCEPTABLE_SAMPLE"}
    SAFE_GATE_POLICY_REPLAY_STATUSES = {"ACCEPTABLE"}
    NEEDS_MORE_DATA_STATUSES = {"NEEDS_MORE_DATA", "SAMPLE_ONLY", "ACCEPTABLE_SAMPLE"}
    REJECTING_PROFIT_STATUSES = {"NEGATIVE", "POOR"}
    REJECTING_WALK_FORWARD_STATUSES = {"UNSTABLE"}
    REJECTING_GATE_POLICY_REPLAY_STATUSES = {"DEGRADED"}

    def validate(
        self,
        training_summary: dict[str, Any] | None,
        baseline_summary: dict[str, Any] | None,
        probability_diagnostics: dict[str, Any] | None,
        calibration_summary: dict[str, Any] | None,
        profit_aware_summary: dict[str, Any] | None,
        walk_forward_summary: dict[str, Any] | None,
        gate_policy_replay_summary: dict[str, Any] | None,
        gap_quality_summary: dict[str, Any] | None = None,
        anti_collapse_summary: dict[str, Any] | None = None,
        candidate_selection_summary: dict[str, Any] | None = None,
        label_config_summary: dict[str, Any] | None = None,
        feature_config_summary: dict[str, Any] | None = None,
        symbol: str | None = None,
        collapse_diagnostics_v2_summary: dict[str, Any] | None = None,
        regime_label_builder_status_summary: dict[str, Any] | None = None,
        walk_forward_profit_diagnostics_summary: dict[str, Any] | None = None,
        profit_aware_diagnostics_summary: dict[str, Any] | None = None,
    ) -> ModelQualityValidationResult:
        probability_diagnostics_was_none = probability_diagnostics is None
        calibration_summary_was_none = calibration_summary is None
        profit_aware_summary_was_none = profit_aware_summary is None
        walk_forward_summary_was_none = walk_forward_summary is None
        gate_policy_replay_summary_was_none = gate_policy_replay_summary is None
        training_summary = self._normalize_mapping(training_summary)
        baseline_summary = self._normalize_mapping(baseline_summary)
        probability_diagnostics = self._normalize_mapping(probability_diagnostics)
        calibration_summary = self._normalize_mapping(calibration_summary)
        profit_aware_summary = self._normalize_mapping(profit_aware_summary)
        walk_forward_summary = self._normalize_mapping(walk_forward_summary)
        gate_policy_replay_summary = self._normalize_mapping(gate_policy_replay_summary)
        profit_aware_summary["gate_results"] = self._normalize_sequence(
            profit_aware_summary.get("gate_results")
        )
        profit_aware_summary["summary"] = self._normalize_mapping(
            profit_aware_summary.get("summary")
        )
        walk_forward_summary["folds"] = self._normalize_sequence(
            walk_forward_summary.get("folds")
        )
        walk_forward_summary["summary"] = self._normalize_mapping(
            walk_forward_summary.get("summary")
        )
        model_version = self._extract_str(training_summary, "model_version")
        training_run_id = self._extract_str(training_summary, "training_run_id", "run_id")
        dataset_rows = self._extract_int(
            training_summary,
            "dataset_rows",
            "dataset_summary.dataset_rows",
        )
        train_rows = self._extract_int(
            training_summary,
            "train_rows",
            "dataset_summary.train_rows",
            "dataset_summary.validation_split.train_rows",
        )
        val_rows = self._extract_int(
            training_summary,
            "val_rows",
            "validation_rows",
            "dataset_summary.validation_rows",
        )
        test_rows = self._extract_int(
            training_summary,
            "test_rows",
            "dataset_summary.test_rows",
        )
        model_accuracy = self._extract_float(
            training_summary,
            "model_accuracy",
            "accuracy_test",
            "test_metrics.accuracy",
        )
        baseline_accuracy = self._extract_baseline_accuracy(baseline_summary)
        accuracy_edge = (
            model_accuracy - baseline_accuracy
            if model_accuracy is not None and baseline_accuracy is not None
            else None
        )
        label_config_summary = self._normalize_mapping(label_config_summary)
        feature_config_summary = self._normalize_mapping(feature_config_summary)
        gap_quality = self._normalize_gap_quality(gap_quality_summary or {})
        anti_collapse = self._normalize_anti_collapse(
            anti_collapse_summary=anti_collapse_summary or {},
            probability_diagnostics=probability_diagnostics,
        )
        collapse_diagnostics_v2 = self._normalize_mapping(collapse_diagnostics_v2_summary) or CollapseDiagnosticsV2().analyze(
            probability_report=probability_diagnostics,
            symbol=symbol,
            feature_version=str(feature_config_summary.get("feature_version")),
            label_version=str(label_config_summary.get("label_version")),
            accuracy_edge=accuracy_edge,
            walk_forward_summary=walk_forward_summary,
        )
        collapse_detected = bool(
            self._extract_value(
                training_summary,
                "collapse_detected",
            )
            or self._extract_value(
                probability_diagnostics,
                "collapse_detected",
            )
            or anti_collapse.get("collapse_detected", False)
            or collapse_diagnostics_v2.get("collapse_detected", False)
        )
        sample_mode = bool(training_summary.get("sample_mode", False))
        real_training_executed = bool(
            training_summary.get(
                "real_training_executed",
                bool(training_summary) and not sample_mode,
            )
        )
        calibration_status = self._resolve_calibration_status(calibration_summary)
        profit_aware_status = self._resolve_profit_aware_status(profit_aware_summary)
        walk_forward_status = self._resolve_walk_forward_status(walk_forward_summary)
        gate_policy_replay_status = self._resolve_gate_policy_replay_status(
            gate_policy_replay_summary
        )
        walk_forward_profit_helper = WalkForwardProfitDiagnostics()
        walk_forward_profit_diagnostics = (
            self._normalize_mapping(walk_forward_profit_diagnostics_summary)
            or walk_forward_profit_helper.analyze(
                symbol=symbol,
                feature_version=str(feature_config_summary.get("feature_version")),
                model_version=model_version,
                walk_forward_summary=walk_forward_summary,
                profit_aware_summary=profit_aware_summary,
            )
        )
        profit_aware_diagnostics = (
            self._normalize_mapping(profit_aware_diagnostics_summary)
            or walk_forward_profit_helper.build_profit_aware_diagnostics(
                profit_aware_summary=profit_aware_summary
            )
        )
        regime_label_builder_status = self._normalize_regime_label_builder_status(
            regime_label_builder_status_summary=regime_label_builder_status_summary,
            label_config_summary=label_config_summary,
        )
        opportunity_diagnostics = self._normalize_mapping(training_summary.get("opportunity_diagnostics"))

        integration_status = {
            "training_executed": real_training_executed,
            "baseline_compared": baseline_accuracy is not None,
            "calibration_checked": bool(calibration_summary),
            "profit_aware_checked": bool(profit_aware_summary),
            "walk_forward_checked": bool(walk_forward_summary),
            "gate_policy_replay_checked": bool(gate_policy_replay_summary),
            "traders_core_connected": False,
            "live_trading_connected": False,
            "orders_enabled": False,
            "model_auto_activation_enabled": False,
        }

        reasons: list[str] = []
        warnings: list[str] = []

        if probability_diagnostics_was_none:
            warnings.append("probability_diagnostics_not_provided")
        if calibration_summary_was_none:
            warnings.append("calibration_summary_not_provided")
        if profit_aware_summary_was_none:
            warnings.append("profit_aware_summary_not_provided")
        if walk_forward_summary_was_none:
            warnings.append("walk_forward_summary_not_provided")
        if gate_policy_replay_summary_was_none:
            warnings.append("gate_policy_replay_summary_not_provided")

        if sample_mode:
            warnings.append("sample_mode_true")
        if not real_training_executed:
            warnings.append("real_training_executed_false")

        if dataset_rows <= 0:
            reasons.append("dataset_rows_missing")
        if train_rows <= 0:
            reasons.append("train_rows_missing")
        if test_rows <= 0:
            reasons.append("test_rows_missing")
        if model_accuracy is None:
            reasons.append("model_accuracy_missing")
        if "regime_runtime_labels_not_built" in self._normalize_sequence(
            regime_label_builder_status.get("missing_requirements")
        ):
            reasons.append("regime_runtime_labels_not_built")

        if reasons:
            quality_status = INSUFFICIENT_REAL_HISTORY
        else:
            if sample_mode:
                reasons.append("sample_mode_requires_long_history_validation")

            if baseline_accuracy is None:
                reasons.append("baseline_accuracy_missing")
            if accuracy_edge is not None and accuracy_edge < self.MIN_BASELINE_EDGE:
                reasons.append("baseline_edge_too_small")
            elif baseline_accuracy is not None and model_accuracy is not None and model_accuracy <= baseline_accuracy:
                reasons.append("model_does_not_beat_baseline")
            if gap_quality.get("gap_severity") in {"HIGH", "CRITICAL"}:
                reasons.append("gap_quality_not_clean")
            if collapse_detected:
                reasons.extend(self._collapse_reasons(anti_collapse))
            if profit_aware_status in self.REJECTING_PROFIT_STATUSES:
                reasons.append("profit_aware_negative")
            if walk_forward_status in self.REJECTING_WALK_FORWARD_STATUSES:
                reasons.append("walk_forward_unstable")
            if gate_policy_replay_status in self.REJECTING_GATE_POLICY_REPLAY_STATUSES:
                reasons.append("gate_policy_replay_degrades_safety")

            if quality_rejected := any(
                reason
                in {
                    "model_does_not_beat_baseline",
                    "baseline_edge_too_small",
                    "gap_quality_not_clean",
                    "collapse_detected",
                    "single_class_prediction_collapse",
                    "directional_bias_up",
                    "directional_bias_down",
                    "low_confidence_uniform_probs",
                    "low_margin_detected",
                    "profit_aware_negative",
                    "walk_forward_unstable",
                    "gate_policy_replay_degrades_safety",
                    "regime_runtime_labels_not_built",
                }
                for reason in reasons
            ):
                quality_status = QUALITY_REJECTED
            elif self._needs_more_data(
                sample_mode=sample_mode,
                dataset_rows=dataset_rows,
                train_rows=train_rows,
                val_rows=val_rows,
                test_rows=test_rows,
                walk_forward_summary=walk_forward_summary,
                gate_policy_replay_summary=gate_policy_replay_summary,
                calibration_status=calibration_status,
                profit_aware_status=profit_aware_status,
                walk_forward_status=walk_forward_status,
                gate_policy_replay_status=gate_policy_replay_status,
                warnings=warnings,
                reasons=reasons,
            ):
                quality_status = NEEDS_MORE_DATA
            elif self._quality_approved(
                real_training_executed=real_training_executed,
                model_accuracy=model_accuracy,
                baseline_accuracy=baseline_accuracy,
                collapse_detected=collapse_detected,
                calibration_status=calibration_status,
                profit_aware_status=profit_aware_status,
                walk_forward_status=walk_forward_status,
                gate_policy_replay_status=gate_policy_replay_status,
            ):
                quality_status = QUALITY_APPROVED
                reasons.extend(
                    [
                        "model_beats_baseline",
                        "collapse_not_detected",
                        "calibration_acceptable",
                        "profit_aware_acceptable",
                        "walk_forward_stable_enough",
                        "gate_policy_replay_safe",
                    ]
                )
            else:
                quality_status = NEEDS_MORE_DATA
                reasons.append("quality_signals_inconclusive")

        quality_gates_summary = self._build_quality_gates_summary(
            training_summary=training_summary,
            gap_quality=gap_quality,
            anti_collapse=anti_collapse,
            accuracy_edge=accuracy_edge,
            profit_aware_summary=profit_aware_summary,
            walk_forward_summary=walk_forward_summary,
            gate_policy_replay_summary=gate_policy_replay_summary,
        )
        candidate_selection = self._normalize_candidate_selection(
            self._normalize_mapping(candidate_selection_summary)
            or ModelCandidateSelector().select(
            model_version=model_version,
            quality_status=quality_status,
            gap_quality=gap_quality,
            anti_collapse=anti_collapse,
            calibration_status=calibration_status,
            profit_aware_summary=profit_aware_summary,
            walk_forward_summary=walk_forward_summary,
            gate_policy_replay_summary=gate_policy_replay_summary,
            model_accuracy=model_accuracy,
            baseline_accuracy=baseline_accuracy,
            accuracy_edge=accuracy_edge,
            )
        )
        approved_for_traders_core_integration = quality_status == QUALITY_APPROVED

        return ModelQualityValidationResult(
            validator_name=MODEL_QUALITY_VALIDATOR_NAME,
            validator_version=MODEL_QUALITY_VALIDATOR_VERSION,
            quality_status=quality_status,
            approved_for_traders_core_integration=approved_for_traders_core_integration,
            approved_for_live_trading=False,
            approved_for_auto_activation=False,
            sample_mode=sample_mode,
            real_training_executed=real_training_executed,
            model_version=model_version,
            training_run_id=training_run_id,
            dataset_rows=dataset_rows,
            train_rows=train_rows,
            val_rows=val_rows,
            test_rows=test_rows,
            model_accuracy=model_accuracy,
            baseline_accuracy=baseline_accuracy,
            accuracy_edge=accuracy_edge,
            collapse_detected=collapse_detected,
            calibration_status=calibration_status,
            profit_aware_status=profit_aware_status,
            walk_forward_status=walk_forward_status,
            gate_policy_replay_status=gate_policy_replay_status,
            reasons=tuple(dict.fromkeys(reasons)),
            warnings=tuple(dict.fromkeys(warnings)),
            integration_status=integration_status,
            probability_diagnostics=probability_diagnostics,
            gap_quality=gap_quality,
            anti_collapse=anti_collapse,
            candidate_selection=candidate_selection,
            quality_gates_summary=quality_gates_summary,
            label_config=label_config_summary,
            feature_config=feature_config_summary,
            collapse_diagnostics_v2=collapse_diagnostics_v2,
            regime_label_builder_status=regime_label_builder_status,
            walk_forward_profit_diagnostics=walk_forward_profit_diagnostics,
            profit_aware_diagnostics=profit_aware_diagnostics,
            opportunity_diagnostics=opportunity_diagnostics,
        )

    def _quality_approved(
        self,
        *,
        real_training_executed: bool,
        model_accuracy: float | None,
        baseline_accuracy: float | None,
        collapse_detected: bool,
        calibration_status: str,
        profit_aware_status: str,
        walk_forward_status: str,
        gate_policy_replay_status: str,
    ) -> bool:
        return bool(
            real_training_executed
            and model_accuracy is not None
            and baseline_accuracy is not None
            and (model_accuracy - baseline_accuracy) >= self.MIN_BASELINE_EDGE
            and not collapse_detected
            and calibration_status in self.ACCEPTABLE_CALIBRATION_STATUSES
            and profit_aware_status in self.POSITIVE_PROFIT_STATUSES
            and walk_forward_status in self.STABLE_WALK_FORWARD_STATUSES
            and gate_policy_replay_status in self.SAFE_GATE_POLICY_REPLAY_STATUSES
        )

    def _needs_more_data(
        self,
        *,
        sample_mode: bool,
        dataset_rows: int,
        train_rows: int,
        val_rows: int,
        test_rows: int,
        walk_forward_summary: dict[str, Any],
        gate_policy_replay_summary: dict[str, Any],
        calibration_status: str,
        profit_aware_status: str,
        walk_forward_status: str,
        gate_policy_replay_status: str,
        warnings: list[str],
        reasons: list[str],
    ) -> bool:
        if sample_mode:
            return True

        if dataset_rows < 1000:
            reasons.append("dataset_rows_lt_1000")
            return True
        if train_rows < 500:
            reasons.append("train_rows_lt_500")
            return True
        if val_rows <= 0:
            reasons.append("validation_rows_missing")
            return True
        if test_rows < 100:
            reasons.append("test_rows_lt_100")
            return True
        if calibration_status in self.NEEDS_MORE_DATA_STATUSES:
            warnings.append("calibration_needs_more_data")
            return True
        if profit_aware_status in self.NEEDS_MORE_DATA_STATUSES:
            warnings.append("profit_aware_needs_more_data")
            return True
        if walk_forward_status in self.NEEDS_MORE_DATA_STATUSES:
            warnings.append("walk_forward_needs_more_data")
            return True
        if gate_policy_replay_status in self.NEEDS_MORE_DATA_STATUSES:
            warnings.append("gate_policy_replay_needs_more_data")
            return True

        fold_count = self._extract_int(
            walk_forward_summary,
            "fold_count",
            "summary.fold_count",
        )
        if fold_count < 3:
            reasons.append("fold_count_lt_3")
            return True

        replay_records = self._extract_int(gate_policy_replay_summary, "total_records")
        if replay_records < 10:
            reasons.append("gate_policy_replay_records_lt_10")
            return True

        return False

    def _resolve_calibration_status(self, calibration_summary: dict[str, Any]) -> str:
        explicit = self._extract_str(calibration_summary, "calibration_status")
        if explicit is not None:
            return explicit
        ece = self._extract_float(calibration_summary, "expected_calibration_error")
        brier = self._extract_float(calibration_summary, "brier_score")
        if ece is None and brier is None:
            return INSUFFICIENT_REAL_HISTORY
        if ece is not None and ece <= 0.10 and (brier is None or brier <= 0.80):
            return "ACCEPTABLE"
        return "UNACCEPTABLE"

    def _resolve_profit_aware_status(self, profit_aware_summary: dict[str, Any]) -> str:
        explicit = self._extract_str(profit_aware_summary, "profit_aware_status")
        if explicit is not None:
            return explicit
        total_r = self._extract_float(
            profit_aware_summary,
            "total_r",
            "summary.total_r",
        )
        profit_factor = self._extract_float(
            profit_aware_summary,
            "profit_factor",
            "summary.profit_factor",
        )
        if total_r is None and profit_factor is None:
            gate_results = [
                row
                for row in self._normalize_sequence(profit_aware_summary.get("gate_results"))
                if int(row.get("resolved_signal_count", 0) or 0) > 0
            ]
            if gate_results:
                best_row = max(
                    gate_results,
                    key=lambda row: float(row.get("total_r", 0.0)),
                )
                total_r = self._safe_float(best_row.get("total_r"))
                profit_factor = self._safe_float(best_row.get("profit_factor"))
        if total_r is None and profit_factor is None:
            return NEEDS_MORE_DATA
        if total_r is not None and total_r > 0.0 and profit_factor is not None and profit_factor > 1.0:
            return "POSITIVE"
        if total_r is not None and total_r >= 0.0:
            return "ACCEPTABLE"
        return "NEGATIVE"

    def _resolve_walk_forward_status(self, walk_forward_summary: dict[str, Any]) -> str:
        explicit = self._extract_str(walk_forward_summary, "walk_forward_status")
        if explicit is not None:
            return explicit
        fold_count = self._extract_int(
            walk_forward_summary,
            "fold_count",
            "summary.fold_count",
        )
        profitable_fold_ratio = self._extract_float(
            walk_forward_summary,
            "profitable_fold_ratio",
            "summary.profitable_fold_ratio",
        )
        global_total_r = self._extract_float(
            walk_forward_summary,
            "global_total_r",
            "summary.global_total_r",
        )
        global_profit_factor = self._extract_float(
            walk_forward_summary,
            "global_profit_factor",
            "summary.global_profit_factor",
        )
        signal_count = self._extract_int(
            walk_forward_summary,
            "total_test_signal_count",
            "summary.total_test_signal_count",
        )
        if fold_count < 3 or signal_count < 50:
            return NEEDS_MORE_DATA
        if (
            profitable_fold_ratio is not None
            and profitable_fold_ratio >= 0.60
            and global_total_r is not None
            and global_total_r > 0.0
            and global_profit_factor is not None
            and global_profit_factor > 1.0
        ):
            return "STABLE"
        return "UNSTABLE"

    def _resolve_gate_policy_replay_status(
        self,
        gate_policy_replay_summary: dict[str, Any],
    ) -> str:
        explicit = self._extract_str(
            gate_policy_replay_summary,
            "gate_policy_replay_status",
        )
        if explicit is not None:
            return explicit
        total_records = self._extract_int(gate_policy_replay_summary, "total_records")
        valid_records = self._extract_int(gate_policy_replay_summary, "valid_records")
        invalid_records = self._extract_int(gate_policy_replay_summary, "invalid_records")
        if total_records <= 0:
            return INSUFFICIENT_REAL_HISTORY
        if total_records < 10:
            return "SAMPLE_ONLY"
        if invalid_records > valid_records:
            return "DEGRADED"
        return "ACCEPTABLE"

    def _extract_baseline_accuracy(self, baseline_summary: dict[str, Any]) -> float | None:
        direct = self._extract_float(
            baseline_summary,
            "baseline_accuracy",
            "best_baseline.test_metrics.accuracy",
        )
        if direct is not None:
            return direct

        baselines = baseline_summary.get("baselines")
        if isinstance(baselines, dict):
            scores = []
            for payload in baselines.values():
                accuracy = self._extract_float(payload, "test.accuracy", "accuracy")
                if accuracy is not None:
                    scores.append(accuracy)
            if scores:
                return max(scores)

        baseline_results = baseline_summary.get("baseline_results")
        if isinstance(baseline_results, list):
            scores = []
            for payload in baseline_results:
                accuracy = self._extract_float(payload, "accuracy", "test.accuracy")
                if accuracy is not None:
                    scores.append(accuracy)
            if scores:
                return max(scores)

        return None

    def _extract_str(self, payload: dict[str, Any], *paths: str) -> str | None:
        value = self._extract_value(payload, *paths)
        return None if value is None else str(value)

    def _extract_int(self, payload: dict[str, Any], *paths: str) -> int:
        value = self._extract_value(payload, *paths)
        if value is None:
            return 0
        return int(value)

    def _extract_float(self, payload: dict[str, Any], *paths: str) -> float | None:
        value = self._extract_value(payload, *paths)
        if value is None:
            return None
        return float(value)

    def _extract_value(self, payload: dict[str, Any], *paths: str) -> Any:
        for path in paths:
            current: Any = payload
            found = True
            for part in path.split("."):
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    found = False
                    break
            if found:
                return current
        return None

    @staticmethod
    def _safe_float(value: Any) -> float:
        if value is None:
            return 0.0
        return float(value)

    def _normalize_gap_quality(self, gap_quality_summary: dict[str, Any]) -> dict[str, Any]:
        normalized_gap_quality = self._normalize_mapping(gap_quality_summary)
        if normalized_gap_quality:
            return normalized_gap_quality
        return {
            "diagnostic_name": GapQualityDiagnostics.DIAGNOSTIC_NAME,
            "diagnostic_version": GapQualityDiagnostics.DIAGNOSTIC_VERSION,
            "gap_count": 0,
            "real_gap_count": 0,
            "trailing_incomplete_count": 0,
            "trailing_incomplete_range_detected": False,
            "effective_gap_count_for_training": 0,
            "largest_gap_minutes": 0,
            "total_missing_candles_estimate": 0,
            "gap_severity": "OK",
            "gap_severity_for_training": "OK",
            "dataset_safe_for_training": True,
            "warnings": ["gap_quality_not_provided"],
            "recommendations": ["Provide gap diagnostics from the real pipeline for stricter candidate gating."],
        }

    def _normalize_anti_collapse(
        self,
        *,
        anti_collapse_summary: dict[str, Any],
        probability_diagnostics: dict[str, Any],
    ) -> dict[str, Any]:
        normalized_anti_collapse = self._normalize_mapping(anti_collapse_summary)
        if normalized_anti_collapse:
            return normalized_anti_collapse
        if probability_diagnostics and (
            probability_diagnostics.get("actual_direction_counts")
            or probability_diagnostics.get("predicted_direction_counts")
        ):
            return AntiCollapseValidator().validate_probability_report(probability_diagnostics)
        return self._empty_anti_collapse()

    @staticmethod
    def _collapse_reasons(anti_collapse: dict[str, Any]) -> list[str]:
        reasons = [
            str(item)
            for item in ModelQualityValidator._normalize_sequence(
                anti_collapse.get("reasons")
            )
        ]
        if not reasons:
            reasons.append("collapse_detected")
        return reasons

    def _normalize_regime_label_builder_status(
        self,
        *,
        regime_label_builder_status_summary: dict[str, Any] | None,
        label_config_summary: dict[str, Any],
    ) -> dict[str, Any]:
        payload = self._normalize_mapping(regime_label_builder_status_summary) or self._normalize_mapping(
            label_config_summary.get("regime_label_builder_status")
        )
        if payload:
            payload.setdefault(
                "regime_label_builder_status",
                "built"
                if payload.get("regime_label_builder_used_in_training")
                else "blocked",
            )
            payload["missing_requirements"] = [
                str(item)
                for item in self._normalize_sequence(payload.get("missing_requirements"))
            ]
            payload["warnings"] = [
                str(item) for item in self._normalize_sequence(payload.get("warnings"))
            ]
            return payload
        return {
            "regime_label_builder_status": "blocked",
            "regime_label_builder_available": False,
            "regime_label_builder_used_in_training": False,
            "regime_specific_labeling_available": False,
            "regime_specific_training_applied": False,
            "regime_label_config_used": {},
            "label_distribution_by_regime": {},
            "missing_requirements": ["regime_label_builder_status_not_provided"],
            "warnings": [],
            "reason": "regime_label_builder_status_not_provided",
        }

    def _normalize_candidate_selection(
        self,
        candidate_selection: dict[str, Any],
    ) -> dict[str, Any]:
        normalized = dict(candidate_selection)
        normalized["gates"] = self._normalize_mapping(normalized.get("gates"))
        normalized["failed_gate_explanations"] = self._normalize_mapping(
            normalized.get("failed_gate_explanations")
        )
        normalized["thresholds"] = self._normalize_mapping(normalized.get("thresholds"))
        normalized["failed_gates"] = [
            str(item) for item in self._normalize_sequence(normalized.get("failed_gates"))
        ]
        normalized["passed_gates"] = [
            str(item) for item in self._normalize_sequence(normalized.get("passed_gates"))
        ]
        normalized["warnings"] = [
            str(item) for item in self._normalize_sequence(normalized.get("warnings"))
        ]
        normalized["recommendations"] = [
            str(item)
            for item in self._normalize_sequence(normalized.get("recommendations"))
        ]
        return normalized

    @staticmethod
    def _normalize_mapping(payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            return dict(payload)
        return {}

    @staticmethod
    def _normalize_sequence(payload: Any) -> list[Any]:
        if isinstance(payload, (list, tuple)):
            return list(payload)
        return []

    @staticmethod
    def _empty_anti_collapse() -> dict[str, Any]:
        return {
            "validator_name": AntiCollapseValidator.VALIDATOR_NAME,
            "validator_version": AntiCollapseValidator.VALIDATOR_VERSION,
            "collapse_detected": False,
            "collapse_type": "NONE",
            "predicted_distribution": {"UP": 0.0, "DOWN": 0.0, "FLAT": 0.0},
            "actual_distribution": {"UP": 0.0, "DOWN": 0.0, "FLAT": 0.0},
            "max_predicted_class_share": 0.0,
            "min_predicted_class_share": 0.0,
            "up_down_prediction_ratio": 0.0,
            "confidence_collapse_detected": False,
            "low_margin_detected": False,
            "directional_bias_detected": False,
            "warnings": ["anti_collapse_not_provided"],
            "reasons": [],
            "recommendations": ["Provide probability diagnostics with class counts for stricter anti-collapse validation."],
        }

    def _build_quality_gates_summary(
        self,
        *,
        training_summary: dict[str, Any],
        gap_quality: dict[str, Any],
        anti_collapse: dict[str, Any],
        accuracy_edge: float | None,
        profit_aware_summary: dict[str, Any],
        walk_forward_summary: dict[str, Any],
        gate_policy_replay_summary: dict[str, Any],
    ) -> dict[str, Any]:
        selector_payload = ModelCandidateSelector().select(
            model_version=None,
            quality_status="RESEARCH_ONLY",
            gap_quality=gap_quality,
            anti_collapse=anti_collapse,
            calibration_status="UNKNOWN",
            profit_aware_summary=profit_aware_summary,
            walk_forward_summary=walk_forward_summary,
            gate_policy_replay_summary=gate_policy_replay_summary,
            model_accuracy=None if accuracy_edge is None else 0.0,
            baseline_accuracy=None if accuracy_edge is None else -accuracy_edge,
            accuracy_edge=accuracy_edge,
        )
        opportunity_diagnostics = self._normalize_mapping(training_summary.get("opportunity_diagnostics"))
        opportunity_test = self._normalize_mapping(opportunity_diagnostics.get("test"))
        return {
            "baseline_edge_minimum": self.MIN_BASELINE_EDGE,
            "baseline_edge_passed": "baseline_edge_gate" in selector_payload["passed_gates"],
            "collapse_gate_passed": "collapse_gate" in selector_payload["passed_gates"],
            "profit_aware_gate_passed": "profit_aware_gate" in selector_payload["passed_gates"],
            "walk_forward_gate_passed": "walk_forward_gate" in selector_payload["passed_gates"],
            "gap_quality_gate_passed": "gap_quality_gate" in selector_payload["passed_gates"],
            "gate_policy_replay_gate_passed": "gate_policy_replay_gate" in selector_payload["passed_gates"],
            "opportunity_baseline_edge": opportunity_test.get("opportunity_baseline_edge"),
            "opportunity_collapse_gate": self._normalize_mapping(opportunity_test.get("opportunity_collapse_gate")),
            "no_trade_dominance_gate": self._normalize_mapping(opportunity_test.get("no_trade_dominance_gate")),
            "setup_edge_gate": self._normalize_mapping(opportunity_test.get("setup_edge_gate")),
            "failed_gates": list(selector_payload["failed_gates"]),
            "passed_gates": list(selector_payload["passed_gates"]),
        }


def validate_model_quality(
    training_summary: dict[str, Any],
    baseline_summary: dict[str, Any],
    probability_diagnostics: dict[str, Any],
    calibration_summary: dict[str, Any],
    profit_aware_summary: dict[str, Any],
    walk_forward_summary: dict[str, Any],
    gate_policy_replay_summary: dict[str, Any],
    gap_quality_summary: dict[str, Any] | None = None,
    anti_collapse_summary: dict[str, Any] | None = None,
    candidate_selection_summary: dict[str, Any] | None = None,
    label_config_summary: dict[str, Any] | None = None,
    feature_config_summary: dict[str, Any] | None = None,
    symbol: str | None = None,
    collapse_diagnostics_v2_summary: dict[str, Any] | None = None,
    regime_label_builder_status_summary: dict[str, Any] | None = None,
    walk_forward_profit_diagnostics_summary: dict[str, Any] | None = None,
    profit_aware_diagnostics_summary: dict[str, Any] | None = None,
) -> ModelQualityValidationResult:
    """Validate model quality from precomputed training and diagnostics payloads."""

    return ModelQualityValidator().validate(
        training_summary=training_summary,
        baseline_summary=baseline_summary,
        probability_diagnostics=probability_diagnostics,
        calibration_summary=calibration_summary,
        profit_aware_summary=profit_aware_summary,
        walk_forward_summary=walk_forward_summary,
        gate_policy_replay_summary=gate_policy_replay_summary,
        gap_quality_summary=gap_quality_summary,
        anti_collapse_summary=anti_collapse_summary,
        candidate_selection_summary=candidate_selection_summary,
        label_config_summary=label_config_summary,
        feature_config_summary=feature_config_summary,
        symbol=symbol,
        collapse_diagnostics_v2_summary=collapse_diagnostics_v2_summary,
        regime_label_builder_status_summary=regime_label_builder_status_summary,
        walk_forward_profit_diagnostics_summary=walk_forward_profit_diagnostics_summary,
        profit_aware_diagnostics_summary=profit_aware_diagnostics_summary,
    )
