from __future__ import annotations

from typing import Any


NEXT_LABEL_EXPERIMENT_PLANNER_NAME = "next_label_experiment_planner"
NEXT_LABEL_EXPERIMENT_PLANNER_VERSION = "ml29"


class NextLabelExperimentPlanner:
    """Build the next research plan from analyzed label-grid results."""

    def plan(self, analysis: dict[str, Any]) -> dict[str, Any]:
        gate_failure_counts = dict(analysis.get("gate_failure_counts", {}))
        recommendations: list[str] = []
        focus_areas: list[str] = []

        if gate_failure_counts.get("collapse_gate", 0) > 0:
            focus_areas.append("labels")
            recommendations.extend(
                [
                    "Strengthen anti-collapse label configs.",
                    "Try stricter flat thresholds to reduce dominant-direction predictions.",
                    "Review class weights or sampling so UP does not dominate predictions.",
                    "Add stronger penalties for skewed predicted distributions.",
                ]
            )
        if gate_failure_counts.get("profit_aware_gate", 0) > 0:
            focus_areas.append("thresholds")
            recommendations.extend(
                [
                    "Revisit TP/SL label settings because profit-aware behavior remains negative.",
                    "Raise signal quality gates such as min margin or max_prob thresholds.",
                    "Recheck fee and slippage assumptions against the current evaluation setup.",
                ]
            )
        if gate_failure_counts.get("walk_forward_gate", 0) > 0:
            focus_areas.append("training_config")
            recommendations.extend(
                [
                    "Increase walk-forward robustness requirements before trusting a candidate.",
                    "Check regime sensitivity and exclude unstable configs from the next run.",
                    "Inspect whether the current fold structure hides instability across time.",
                ]
            )
        if gate_failure_counts.get("gap_quality_gate", 0) > 0:
            focus_areas.append("gap_handling")
            recommendations.extend(
                [
                    "Improve gap handling before training on candidate windows.",
                    "Exclude or down-weight windows around detected candle gaps.",
                ]
            )
        if gate_failure_counts.get("baseline_edge_gate", 0) > 0:
            focus_areas.append("features")
            recommendations.extend(
                [
                    "Improve feature signal quality because candidates are not beating the baseline edge threshold.",
                    "Compare the best rejected candidate against alternative feature versions before expanding the grid.",
                ]
            )

        if not recommendations:
            recommendations.append("Run a broader grid or feature comparison because the current failure pattern is inconclusive.")
        recommendations.append("Keep traders-core disconnected and keep live trading, orders, and auto activation disabled.")

        next_experiment_plan = {
            "best_candidate_config_id": analysis.get("best_candidate_config_id"),
            "best_candidate_status": analysis.get("best_candidate_status"),
            "top_failed_gate": analysis.get("top_failed_gate"),
            "focus_areas": list(dict.fromkeys(focus_areas)) or ["labels", "features"],
            "suggested_actions": recommendations[:-1],
            "safety": {
                "approved_for_live_trading": False,
                "approved_for_auto_activation": False,
                "orders_enabled": False,
                "traders_core_connected": False,
            },
        }
        return {
            "planner_name": NEXT_LABEL_EXPERIMENT_PLANNER_NAME,
            "planner_version": NEXT_LABEL_EXPERIMENT_PLANNER_VERSION,
            "experiment_id": analysis.get("experiment_id"),
            "recommendations": list(dict.fromkeys(recommendations)),
            "next_experiment_plan": next_experiment_plan,
        }
