from __future__ import annotations

from typing import Any

from app.evaluation.candidate_acceptance_thresholds import (
    default_candidate_acceptance_thresholds,
)
from app.evaluation.gap_quality_gate_normalizer import (
    gap_quality_gate_is_safe,
    gap_quality_gate_should_fail,
    normalize_gap_severity,
)


class ModelCandidateSelector:
    SELECTOR_NAME = "model_candidate_selector"
    SELECTOR_VERSION = "ml30"
    MIN_BASELINE_EDGE = default_candidate_acceptance_thresholds().min_accuracy_edge

    def select(
        self,
        *,
        model_version: str | None,
        quality_status: str,
        gap_quality: dict[str, Any],
        anti_collapse: dict[str, Any],
        calibration_status: str,
        profit_aware_summary: dict[str, Any],
        walk_forward_summary: dict[str, Any],
        gate_policy_replay_summary: dict[str, Any],
        model_accuracy: float | None,
        baseline_accuracy: float | None,
        accuracy_edge: float | None,
    ) -> dict[str, Any]:
        thresholds = default_candidate_acceptance_thresholds()
        profit_metrics = self._profit_metrics(profit_aware_summary)
        walk_metrics = self._walk_metrics(walk_forward_summary)
        gate_policy_status = str(gate_policy_replay_summary.get("gate_policy_replay_status") or "")
        gap_severity = (
            normalize_gap_severity(
                gap_quality.get("gap_severity_for_training")
                or gap_quality.get("gap_severity")
            )
            or "OK"
        )
        gap_training_safe = gap_quality.get("dataset_safe_for_training")
        effective_gap_count = int(
            gap_quality.get("effective_gap_count_for_training")
            or gap_quality.get("real_gap_count")
            or gap_quality.get("gap_count")
            or 0
        )
        raw_gap_severity = (
            normalize_gap_severity(gap_quality.get("gap_severity"))
            or gap_severity
        )
        predicted_distribution = dict(anti_collapse.get("predicted_distribution", {}))
        actual_distribution = dict(anti_collapse.get("actual_distribution", {}))
        max_predicted_class_share = max(
            [float(value) for value in predicted_distribution.values()],
            default=0.0,
        )
        predicted_down_share = float(predicted_distribution.get("DOWN", 0.0) or 0.0)
        actual_down_share = float(actual_distribution.get("DOWN", 0.0) or 0.0)
        baseline_edge_passed = (
            accuracy_edge is not None and accuracy_edge >= thresholds.min_accuracy_edge
        )
        collapse_passed = (
            not bool(anti_collapse.get("collapse_detected", False))
            and max_predicted_class_share <= thresholds.max_predicted_class_share
            and not (
                actual_down_share > 0.30
                and predicted_down_share < thresholds.min_down_prediction_share
            )
        )
        profit_passed = (
            profit_metrics["best_total_r"] is not None
            and profit_metrics["best_total_r"] > thresholds.min_profit_total_r
            and profit_metrics["best_profit_factor"] is not None
            and profit_metrics["best_profit_factor"] >= thresholds.min_profit_factor
        )
        walk_passed = (
            walk_metrics["global_total_r"] is not None
            and walk_metrics["global_total_r"] >= thresholds.min_walk_forward_total_r
            and walk_metrics["global_profit_factor"] is not None
            and walk_metrics["global_profit_factor"] >= thresholds.min_walk_forward_profit_factor
        )
        if gap_quality_gate_is_safe(
            gap_severity_for_training=gap_severity,
            gap_training_safe=gap_training_safe,
        ):
            gap_passed = True
        elif gap_quality_gate_should_fail(
            gap_severity_for_training=gap_severity,
            gap_training_safe=gap_training_safe,
        ):
            gap_passed = False
        else:
            gap_passed = thresholds.gap_severity_allowed(gap_severity) and bool(
                gap_quality.get("dataset_safe_for_training", True)
            )

        gates = {
            "baseline_edge_gate": {
                "passed": baseline_edge_passed,
                "threshold": thresholds.min_accuracy_edge,
                "actual": accuracy_edge,
                "explanation": (
                    "baseline_edge_gate failed because accuracy_edge < min_accuracy_edge"
                    if not baseline_edge_passed
                    else "baseline_edge_gate passed"
                ),
            },
            "collapse_gate": {
                "passed": collapse_passed,
                "collapse_type": anti_collapse.get("collapse_type"),
                "max_predicted_class_share": max_predicted_class_share,
                "max_predicted_class_share_threshold": thresholds.max_predicted_class_share,
                "predicted_down_share": predicted_down_share,
                "min_down_prediction_share": thresholds.min_down_prediction_share,
                "actual_down_share": actual_down_share,
                "explanation": self._collapse_explanation(
                    collapse_passed=collapse_passed,
                    anti_collapse=anti_collapse,
                    max_predicted_class_share=max_predicted_class_share,
                    max_predicted_class_share_threshold=thresholds.max_predicted_class_share,
                    predicted_down_share=predicted_down_share,
                    min_down_prediction_share=thresholds.min_down_prediction_share,
                    actual_down_share=actual_down_share,
                ),
            },
            "profit_aware_gate": {
                "passed": profit_passed,
                **profit_metrics,
                "min_profit_factor": thresholds.min_profit_factor,
                "min_profit_total_r": thresholds.min_profit_total_r,
                "explanation": (
                    "profit_aware_gate failed because profit_factor <= threshold or total_r <= threshold"
                    if not profit_passed
                    else "profit_aware_gate passed"
                ),
            },
            "walk_forward_gate": {
                "passed": walk_passed,
                **walk_metrics,
                "min_walk_forward_profit_factor": thresholds.min_walk_forward_profit_factor,
                "min_walk_forward_total_r": thresholds.min_walk_forward_total_r,
                "explanation": (
                    "walk_forward_gate failed because global_total_r or global_profit_factor is below threshold"
                    if not walk_passed
                    else "walk_forward_gate passed"
                ),
            },
            "gap_quality_gate": {
                "passed": gap_passed,
                "gap_severity": gap_severity,
                "raw_gap_severity": raw_gap_severity,
                "effective_gap_count_for_training": effective_gap_count,
                "dataset_safe_for_training": gap_training_safe,
                "max_allowed_gap_severity": thresholds.max_allowed_gap_severity,
                "explanation": (
                    "gap_quality_gate failed because training-safe gap_severity exceeds max_allowed_gap_severity"
                    if not gap_passed
                    else "gap_quality_gate passed"
                ),
            },
            "gate_policy_replay_gate": {
                "passed": gate_policy_status in {"ACCEPTABLE", "SAMPLE_ONLY", ""},
                "gate_policy_replay_status": gate_policy_status,
                "explanation": (
                    "gate_policy_replay_gate failed because gate_policy_replay_status is degraded"
                    if gate_policy_status not in {"ACCEPTABLE", "SAMPLE_ONLY", ""}
                    else "gate_policy_replay_gate passed"
                ),
            },
        }
        passed_gates = sorted(name for name, payload in gates.items() if payload["passed"])
        failed_gates = sorted(name for name, payload in gates.items() if not payload["passed"])
        failed_gate_explanations = {
            name: str(payload.get("explanation", "gate failed"))
            for name, payload in gates.items()
            if not payload["passed"]
        }

        warnings: list[str] = []
        if gate_policy_status == "SAMPLE_ONLY":
            warnings.append("gate_policy_replay_sample_only")
        if calibration_status == "UNACCEPTABLE":
            warnings.append("calibration_unacceptable")

        candidate_status = "CANDIDATE_REJECTED"
        candidate_decision = "REJECT_FOR_RESEARCH"
        if model_accuracy is None or baseline_accuracy is None or accuracy_edge is None:
            candidate_status = "NEEDS_MORE_DATA"
            candidate_decision = "INSUFFICIENT_METRICS"
        elif all(gates[name]["passed"] for name in ("baseline_edge_gate", "collapse_gate", "profit_aware_gate", "walk_forward_gate", "gap_quality_gate")):
            candidate_status = "CANDIDATE_ACCEPTED_FOR_RESEARCH"
            candidate_decision = "ACCEPT_FOR_RESEARCH_ONLY"

        recommendations = self._recommendations(
            candidate_status=candidate_status,
            failed_gates=failed_gates,
            anti_collapse=anti_collapse,
            gap_quality=gap_quality,
        )
        return {
            "selector_name": self.SELECTOR_NAME,
            "selector_version": self.SELECTOR_VERSION,
            "candidate_status": candidate_status,
            "candidate_decision": candidate_decision,
            "model_version": model_version,
            "quality_status": quality_status,
            "approved_for_traders_core_integration": False,
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "gates": gates,
            "failed_gates": failed_gates,
            "failed_gate_explanations": failed_gate_explanations,
            "passed_gates": passed_gates,
            "warnings": warnings,
            "recommendations": recommendations,
            "thresholds": thresholds.to_dict(),
        }

    @staticmethod
    def _profit_metrics(summary: dict[str, Any]) -> dict[str, float | str | None]:
        rows = [
            row
            for row in summary.get("gate_results", [])
            if int(row.get("resolved_signal_count", 0) or 0) > 0
        ]
        if not rows:
            total_r = summary.get("total_r")
            profit_factor = summary.get("profit_factor")
            report_path = summary.get("report_path")
            return {
                "best_gate_type": None,
                "best_gate_threshold": None,
                "best_total_r": None if total_r is None else float(total_r),
                "best_profit_factor": None if profit_factor is None else float(profit_factor),
                "report_path": report_path,
            }
        best = max(
            rows,
            key=lambda row: (float(row.get("total_r", float("-inf"))), float(row.get("profit_factor") or 0.0)),
        )
        return {
            "best_gate_type": best.get("gate_type"),
            "best_gate_threshold": best.get("threshold"),
            "best_total_r": float(best.get("total_r", 0.0)),
            "best_profit_factor": float(best.get("profit_factor", 0.0)),
            "report_path": summary.get("report_path"),
        }

    @staticmethod
    def _walk_metrics(summary: dict[str, Any]) -> dict[str, float | int | None]:
        root_summary = summary.get("summary") if isinstance(summary.get("summary"), dict) else summary
        return {
            "fold_count": None if root_summary.get("fold_count") is None else int(root_summary.get("fold_count")),
            "global_total_r": None if root_summary.get("global_total_r") is None else float(root_summary.get("global_total_r")),
            "global_profit_factor": None if root_summary.get("global_profit_factor") is None else float(root_summary.get("global_profit_factor")),
            "total_test_signal_count": None if root_summary.get("total_test_signal_count") is None else int(root_summary.get("total_test_signal_count")),
        }

    @staticmethod
    def _recommendations(
        *,
        candidate_status: str,
        failed_gates: list[str],
        anti_collapse: dict[str, Any],
        gap_quality: dict[str, Any],
    ) -> list[str]:
        if candidate_status == "CANDIDATE_ACCEPTED_FOR_RESEARCH":
            return [
                "Keep this candidate in research mode only.",
                "Do not connect traders-core or enable live trading from ML27.",
            ]
        recommendations = ["Do not use this model for live or auto-activation decisions."]
        if "collapse_gate" in failed_gates:
            recommendations.append("Review labels/features because prediction collapse is still present.")
        if "baseline_edge_gate" in failed_gates:
            recommendations.append("Require a stronger edge over the best baseline before selecting a candidate.")
        if "profit_aware_gate" in failed_gates or "walk_forward_gate" in failed_gates:
            recommendations.append("Rework label/feature configuration until profit-aware and walk-forward gates turn positive.")
        effective_gap_severity = str(
            gap_quality.get("gap_severity_for_training")
            or gap_quality.get("gap_severity")
            or "OK"
        )
        if effective_gap_severity in {"HIGH", "CRITICAL"}:
            recommendations.append("Reduce gaps in the candle history before trusting new experiments.")
        if anti_collapse.get("directional_bias_detected"):
            recommendations.append("Investigate directional imbalance because predictions are skewed to one side.")
        return recommendations

    @staticmethod
    def _collapse_explanation(
        *,
        collapse_passed: bool,
        anti_collapse: dict[str, Any],
        max_predicted_class_share: float,
        max_predicted_class_share_threshold: float,
        predicted_down_share: float,
        min_down_prediction_share: float,
        actual_down_share: float,
    ) -> str:
        if collapse_passed:
            return "collapse_gate passed"
        if bool(anti_collapse.get("collapse_detected", False)):
            return "collapse_gate failed because collapse_detected is true"
        if max_predicted_class_share > max_predicted_class_share_threshold:
            return "collapse_gate failed because max_predicted_class_share > threshold"
        if actual_down_share > 0.30 and predicted_down_share < min_down_prediction_share:
            return "collapse_gate failed because DOWN prediction share is too small for the actual DOWN share"
        return "collapse_gate failed because prediction distribution is imbalanced"
