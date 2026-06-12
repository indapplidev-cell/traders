from __future__ import annotations

from typing import Any


class ModelCandidateSelector:
    SELECTOR_NAME = "model_candidate_selector"
    SELECTOR_VERSION = "ml27"
    MIN_BASELINE_EDGE = 0.005

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
        profit_metrics = self._profit_metrics(profit_aware_summary)
        walk_metrics = self._walk_metrics(walk_forward_summary)
        gate_policy_status = str(gate_policy_replay_summary.get("gate_policy_replay_status") or "")
        gap_severity = str(gap_quality.get("gap_severity") or "OK")

        gates = {
            "baseline_edge_gate": {
                "passed": accuracy_edge is not None and accuracy_edge >= self.MIN_BASELINE_EDGE,
                "threshold": self.MIN_BASELINE_EDGE,
                "actual": accuracy_edge,
            },
            "collapse_gate": {
                "passed": not bool(anti_collapse.get("collapse_detected", False)),
                "collapse_type": anti_collapse.get("collapse_type"),
            },
            "profit_aware_gate": {
                "passed": (
                    profit_metrics["best_total_r"] is not None
                    and profit_metrics["best_total_r"] > 0.0
                    and profit_metrics["best_profit_factor"] is not None
                    and profit_metrics["best_profit_factor"] > 1.0
                ),
                **profit_metrics,
            },
            "walk_forward_gate": {
                "passed": (
                    walk_metrics["global_total_r"] is not None
                    and walk_metrics["global_total_r"] > 0.0
                    and walk_metrics["global_profit_factor"] is not None
                    and walk_metrics["global_profit_factor"] > 1.0
                ),
                **walk_metrics,
            },
            "gap_quality_gate": {
                "passed": gap_severity not in {"HIGH", "CRITICAL"} and bool(gap_quality.get("dataset_safe_for_training", True)),
                "gap_severity": gap_severity,
                "dataset_safe_for_training": gap_quality.get("dataset_safe_for_training"),
            },
            "gate_policy_replay_gate": {
                "passed": gate_policy_status in {"ACCEPTABLE", "SAMPLE_ONLY", ""},
                "gate_policy_replay_status": gate_policy_status,
            },
        }
        passed_gates = sorted(name for name, payload in gates.items() if payload["passed"])
        failed_gates = sorted(name for name, payload in gates.items() if not payload["passed"])

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
            "passed_gates": passed_gates,
            "warnings": warnings,
            "recommendations": recommendations,
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
        if gap_quality.get("gap_severity") in {"HIGH", "CRITICAL"}:
            recommendations.append("Reduce gaps in the candle history before trusting new experiments.")
        if anti_collapse.get("directional_bias_detected"):
            recommendations.append("Investigate directional imbalance because predictions are skewed to one side.")
        return recommendations
