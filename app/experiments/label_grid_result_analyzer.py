from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.experiments.next_label_experiment_planner import NextLabelExperimentPlanner


LABEL_GRID_RESULT_ANALYZER_NAME = "label_grid_result_analyzer"
LABEL_GRID_RESULT_ANALYZER_VERSION = "ml29"
MIN_BASELINE_EDGE = 0.005


class LabelGridResultAnalyzer:
    """Analyze completed ML28 label-grid experiment outputs."""

    def __init__(
        self,
        *,
        planner: NextLabelExperimentPlanner | None = None,
    ) -> None:
        self._planner = planner or NextLabelExperimentPlanner()

    def analyze(self, result: dict[str, Any] | object) -> dict[str, Any]:
        payload = self._normalize_payload(result)
        candidate_results = [dict(item) for item in payload.get("candidate_results", [])]
        candidate_ranking = [dict(item) for item in payload.get("candidate_ranking", [])]

        gate_failure_counts = self._gate_failure_counts(candidate_results)
        collapse_counts = self._collapse_counts(candidate_results)
        profitability_summary = self._profitability_summary(candidate_results)
        walk_forward_summary = self._walk_forward_summary(candidate_results)
        baseline_edge_summary = self._baseline_edge_summary(candidate_results)
        top_failed_gate = self._top_failed_gate(gate_failure_counts)

        recommendations = list(payload.get("recommendations", []))
        if top_failed_gate is not None:
            recommendations.append(f"Most frequent failing gate: {top_failed_gate}.")

        analysis = {
            "analyzer_name": LABEL_GRID_RESULT_ANALYZER_NAME,
            "analyzer_version": LABEL_GRID_RESULT_ANALYZER_VERSION,
            "experiment_id": payload.get("experiment_id"),
            "experiment_status": payload.get("experiment_status"),
            "config_count": int(payload.get("config_count", 0) or 0),
            "accepted_candidate_count": int(payload.get("accepted_candidate_count", 0) or 0),
            "rejected_candidate_count": int(payload.get("rejected_candidate_count", 0) or 0),
            "best_candidate_config_id": payload.get("best_candidate_config_id"),
            "best_candidate_status": payload.get("best_candidate_status"),
            "best_candidate_score": payload.get("best_candidate_score"),
            "top_failed_gate": top_failed_gate,
            "gate_failure_counts": gate_failure_counts,
            "collapse_counts": collapse_counts,
            "profitability_summary": profitability_summary,
            "walk_forward_summary": walk_forward_summary,
            "baseline_edge_summary": baseline_edge_summary,
            "candidate_ranking": candidate_ranking,
            "candidate_results": candidate_results,
            "recommendations": list(dict.fromkeys(recommendations)),
        }
        planner_payload = self._planner.plan(analysis)
        analysis["planner_name"] = planner_payload["planner_name"]
        analysis["planner_version"] = planner_payload["planner_version"]
        analysis["recommendations"] = list(
            dict.fromkeys(
                list(analysis["recommendations"])
                + list(planner_payload["recommendations"])
            )
        )
        analysis["next_experiment_plan"] = planner_payload["next_experiment_plan"]
        return analysis

    @staticmethod
    def load_summary(experiment_dir: str | Path) -> dict[str, Any]:
        path = Path(experiment_dir) / "label_grid_experiment_summary.json"
        if not path.exists():
            raise ValueError(f"experiment summary not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def latest_experiment_dir(root_dir: str | Path = Path("reports/label_grid_experiments")) -> Path:
        root = Path(root_dir)
        if not root.exists():
            raise ValueError("reports/label_grid_experiments is missing; run label-grid-experiment-run first.")
        directories = [item for item in root.iterdir() if item.is_dir()]
        if not directories:
            raise ValueError("reports/label_grid_experiments is empty; run label-grid-experiment-run first.")
        return max(directories, key=lambda item: item.stat().st_mtime)

    @staticmethod
    def _normalize_payload(result: dict[str, Any] | object) -> dict[str, Any]:
        if isinstance(result, dict):
            return dict(result)
        to_dict = getattr(result, "to_dict", None)
        if callable(to_dict):
            return dict(to_dict())
        raise TypeError("result must be a dict or provide to_dict()")

    @staticmethod
    def _gate_failure_counts(candidate_results: list[dict[str, Any]]) -> dict[str, int]:
        summary: dict[str, int] = {}
        for candidate in candidate_results:
            for gate_name in candidate.get("failed_gates", []):
                summary[gate_name] = summary.get(gate_name, 0) + 1
        return summary

    @staticmethod
    def _collapse_counts(candidate_results: list[dict[str, Any]]) -> dict[str, int]:
        summary: dict[str, int] = {"collapsed": 0, "non_collapsed": 0}
        for candidate in candidate_results:
            collapse_type = str(candidate.get("collapse_type") or "NONE")
            summary[collapse_type] = summary.get(collapse_type, 0) + 1
            if bool(candidate.get("collapse_detected", False)):
                summary["collapsed"] += 1
            else:
                summary["non_collapsed"] += 1
        return summary

    @staticmethod
    def _profitability_summary(candidate_results: list[dict[str, Any]]) -> dict[str, Any]:
        best_profit_factor = None
        best_profit_factor_config_id = None
        best_total_r = None
        best_total_r_config_id = None
        positive_profit_factor_count = 0
        positive_total_r_count = 0

        for candidate in candidate_results:
            profit_factor = candidate.get("profit_factor")
            profit_total_r = candidate.get("profit_total_r")
            config_id = candidate.get("config_id")
            if profit_factor is not None and float(profit_factor) > 1.0:
                positive_profit_factor_count += 1
            if profit_total_r is not None and float(profit_total_r) > 0.0:
                positive_total_r_count += 1
            if profit_factor is not None and (
                best_profit_factor is None or float(profit_factor) > best_profit_factor
            ):
                best_profit_factor = float(profit_factor)
                best_profit_factor_config_id = config_id
            if profit_total_r is not None and (
                best_total_r is None or float(profit_total_r) > best_total_r
            ):
                best_total_r = float(profit_total_r)
                best_total_r_config_id = config_id

        return {
            "positive_profit_factor_count": positive_profit_factor_count,
            "positive_total_r_count": positive_total_r_count,
            "best_profit_factor": best_profit_factor,
            "best_profit_factor_config_id": best_profit_factor_config_id,
            "best_total_r": best_total_r,
            "best_total_r_config_id": best_total_r_config_id,
        }

    @staticmethod
    def _walk_forward_summary(candidate_results: list[dict[str, Any]]) -> dict[str, Any]:
        positive_profit_factor_count = 0
        positive_total_r_count = 0
        best_profit_factor = None
        best_profit_factor_config_id = None

        for candidate in candidate_results:
            profit_factor = candidate.get("walk_forward_profit_factor")
            total_r = candidate.get("walk_forward_global_total_r")
            config_id = candidate.get("config_id")
            if profit_factor is not None and float(profit_factor) > 1.0:
                positive_profit_factor_count += 1
            if total_r is not None and float(total_r) > 0.0:
                positive_total_r_count += 1
            if profit_factor is not None and (
                best_profit_factor is None or float(profit_factor) > best_profit_factor
            ):
                best_profit_factor = float(profit_factor)
                best_profit_factor_config_id = config_id

        return {
            "positive_walk_forward_profit_factor_count": positive_profit_factor_count,
            "positive_walk_forward_total_r_count": positive_total_r_count,
            "best_walk_forward_profit_factor": best_profit_factor,
            "best_walk_forward_profit_factor_config_id": best_profit_factor_config_id,
        }

    @staticmethod
    def _baseline_edge_summary(candidate_results: list[dict[str, Any]]) -> dict[str, Any]:
        positive_edge_count = 0
        above_threshold_count = 0
        best_accuracy_edge = None
        best_accuracy_edge_config_id = None

        for candidate in candidate_results:
            accuracy_edge = candidate.get("accuracy_edge")
            config_id = candidate.get("config_id")
            if accuracy_edge is None:
                continue
            edge_value = float(accuracy_edge)
            if edge_value > 0.0:
                positive_edge_count += 1
            if edge_value >= MIN_BASELINE_EDGE:
                above_threshold_count += 1
            if best_accuracy_edge is None or edge_value > best_accuracy_edge:
                best_accuracy_edge = edge_value
                best_accuracy_edge_config_id = config_id

        return {
            "positive_edge_count": positive_edge_count,
            "above_threshold_count": above_threshold_count,
            "best_accuracy_edge": best_accuracy_edge,
            "best_accuracy_edge_config_id": best_accuracy_edge_config_id,
            "baseline_edge_threshold": MIN_BASELINE_EDGE,
        }

    @staticmethod
    def _top_failed_gate(gate_failure_counts: dict[str, int]) -> str | None:
        if not gate_failure_counts:
            return None
        return min(
            gate_failure_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )[0]
