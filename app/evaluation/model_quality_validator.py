from __future__ import annotations

from dataclasses import dataclass
from typing import Any


MODEL_QUALITY_VALIDATOR_NAME = "model_training_quality_validator"
MODEL_QUALITY_VALIDATOR_VERSION = "ml25"

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
        }


class ModelQualityValidator:
    """Validate whether a trained model looks analytically useful."""

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
        training_summary: dict[str, Any],
        baseline_summary: dict[str, Any],
        probability_diagnostics: dict[str, Any],
        calibration_summary: dict[str, Any],
        profit_aware_summary: dict[str, Any],
        walk_forward_summary: dict[str, Any],
        gate_policy_replay_summary: dict[str, Any],
    ) -> ModelQualityValidationResult:
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
        collapse_detected = bool(
            self._extract_value(
                training_summary,
                "collapse_detected",
            )
            or self._extract_value(
                probability_diagnostics,
                "collapse_detected",
            )
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

        if reasons:
            quality_status = INSUFFICIENT_REAL_HISTORY
        else:
            if sample_mode:
                reasons.append("sample_mode_requires_long_history_validation")

            if baseline_accuracy is None:
                reasons.append("baseline_accuracy_missing")
            if baseline_accuracy is not None and model_accuracy is not None and model_accuracy <= baseline_accuracy:
                reasons.append("model_does_not_beat_baseline")
            if collapse_detected:
                reasons.append("collapse_detected")
            if profit_aware_status in self.REJECTING_PROFIT_STATUSES:
                reasons.append("profit_aware_not_acceptable")
            if walk_forward_status in self.REJECTING_WALK_FORWARD_STATUSES:
                reasons.append("walk_forward_unstable")
            if gate_policy_replay_status in self.REJECTING_GATE_POLICY_REPLAY_STATUSES:
                reasons.append("gate_policy_replay_degrades_safety")

            if quality_rejected := any(
                reason
                in {
                    "model_does_not_beat_baseline",
                    "collapse_detected",
                    "profit_aware_not_acceptable",
                    "walk_forward_unstable",
                    "gate_policy_replay_degrades_safety",
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
            and model_accuracy > baseline_accuracy
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
            gate_results = profit_aware_summary.get("gate_results", [])
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


def validate_model_quality(
    training_summary: dict[str, Any],
    baseline_summary: dict[str, Any],
    probability_diagnostics: dict[str, Any],
    calibration_summary: dict[str, Any],
    profit_aware_summary: dict[str, Any],
    walk_forward_summary: dict[str, Any],
    gate_policy_replay_summary: dict[str, Any],
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
    )
