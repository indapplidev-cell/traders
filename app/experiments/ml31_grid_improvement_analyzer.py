from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.experiments.label_grid_result_analyzer import LabelGridResultAnalyzer


ML31_GRID_IMPROVEMENT_ANALYZER_NAME = "ml31_grid_improvement_analyzer"
ML31_GRID_IMPROVEMENT_ANALYZER_VERSION = "ml31"


class ML31GridImprovementAnalyzer:
    """Compare the current ML31 grid run with an optional previous baseline run."""

    def analyze(
        self,
        *,
        current_experiment_summary: dict[str, Any],
        current_analysis: dict[str, Any],
        previous_baseline_summary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        current_summary = dict(current_experiment_summary)
        current_analysis = dict(current_analysis)
        previous = None if previous_baseline_summary is None else dict(previous_baseline_summary)

        current_best_score = self._float_or_none(
            current_analysis.get("best_candidate_score", current_summary.get("best_candidate_score"))
        )
        previous_best_score = self._float_or_none(
            None if previous is None else previous.get("best_candidate_score")
        )
        score_delta = (
            None
            if current_best_score is None or previous_best_score is None
            else round(current_best_score - previous_best_score, 6)
        )

        accepted_candidate_improved = self._compare_counts(
            current=int(current_summary.get("accepted_candidate_count", 0) or 0),
            previous=None if previous is None else int(previous.get("accepted_candidate_count", 0) or 0),
        )
        baseline_edge_improved = self._baseline_edge_improved(current_analysis, previous)
        collapse_improved = self._gate_improved(current_analysis, previous, "collapse_gate")
        profit_aware_improved = self._gate_improved(current_analysis, previous, "profit_aware_gate")
        walk_forward_improved = self._gate_improved(current_analysis, previous, "walk_forward_gate")
        gap_quality_improved = self._gate_improved(current_analysis, previous, "gap_quality_gate")
        overall_improvement_status = self._overall_status(
            score_delta=score_delta,
            accepted_candidate_improved=accepted_candidate_improved,
            improvements=[
                baseline_edge_improved,
                collapse_improved,
                profit_aware_improved,
                walk_forward_improved,
                gap_quality_improved,
            ],
            previous_available=previous is not None,
        )

        return {
            "analyzer_name": ML31_GRID_IMPROVEMENT_ANALYZER_NAME,
            "analyzer_version": ML31_GRID_IMPROVEMENT_ANALYZER_VERSION,
            "current_experiment_id": current_summary.get("experiment_id"),
            "previous_experiment_id": None if previous is None else previous.get("experiment_id"),
            "current_config_count": int(current_summary.get("config_count", 0) or 0),
            "current_accepted_candidate_count": int(current_summary.get("accepted_candidate_count", 0) or 0),
            "current_rejected_candidate_count": int(current_summary.get("rejected_candidate_count", 0) or 0),
            "current_best_candidate_config_id": current_summary.get("best_candidate_config_id"),
            "current_best_candidate_score": current_best_score,
            "previous_best_candidate_score": previous_best_score,
            "score_delta": score_delta,
            "accepted_candidate_improved": accepted_candidate_improved,
            "baseline_edge_improved": baseline_edge_improved,
            "collapse_improved": collapse_improved,
            "profit_aware_improved": profit_aware_improved,
            "walk_forward_improved": walk_forward_improved,
            "gap_quality_improved": gap_quality_improved,
            "overall_improvement_status": overall_improvement_status,
            "recommendations": self._recommendations(
                current_experiment_summary=current_summary,
                current_analysis=current_analysis,
                previous_baseline_summary=previous,
                overall_improvement_status=overall_improvement_status,
            ),
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "orders_enabled": False,
            "traders_core_connected": False,
        }

    @staticmethod
    def load_summary(experiment_dir: str | Path) -> dict[str, Any]:
        return LabelGridResultAnalyzer.load_summary(experiment_dir)

    @staticmethod
    def load_analysis(experiment_dir: str | Path) -> dict[str, Any]:
        path = Path(experiment_dir) / "label_grid_result_analysis.json"
        if not path.exists():
            raise ValueError(f"experiment analysis not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def latest_experiment_dir(root_dir: str | Path = Path("reports/label_grid_experiments")) -> Path:
        return LabelGridResultAnalyzer.latest_experiment_dir(root_dir)

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        return None if value is None else float(value)

    @staticmethod
    def _compare_counts(*, current: int, previous: int | None) -> bool:
        return False if previous is None else current > previous

    @classmethod
    def _baseline_edge_improved(
        cls,
        current_analysis: dict[str, Any],
        previous: dict[str, Any] | None,
    ) -> bool:
        if previous is None:
            return False
        current_summary = dict(current_analysis.get("baseline_edge_summary", {}))
        previous_summary = dict(previous.get("baseline_edge_summary", {}))
        current_count = int(current_summary.get("above_threshold_count", 0) or 0)
        previous_count = int(previous_summary.get("above_threshold_count", 0) or 0)
        if current_count != previous_count:
            return current_count > previous_count
        current_best = cls._float_or_none(current_summary.get("best_accuracy_edge"))
        previous_best = cls._float_or_none(previous_summary.get("best_accuracy_edge"))
        return current_best is not None and previous_best is not None and current_best > previous_best

    @staticmethod
    def _gate_improved(
        current_analysis: dict[str, Any],
        previous: dict[str, Any] | None,
        gate_name: str,
    ) -> bool:
        if previous is None:
            return False
        current_count = int(dict(current_analysis.get("gate_failure_counts", {})).get(gate_name, 0) or 0)
        previous_count = int(dict(previous.get("gate_failure_counts", {})).get(gate_name, 0) or 0)
        return current_count < previous_count

    @staticmethod
    def _overall_status(
        *,
        score_delta: float | None,
        accepted_candidate_improved: bool,
        improvements: list[bool],
        previous_available: bool,
    ) -> str:
        if not previous_available:
            return "INSUFFICIENT_COMPARISON_DATA"

        improvement_count = sum(1 for item in improvements if item)
        if accepted_candidate_improved or (score_delta is not None and score_delta > 0 and improvement_count >= 3):
            return "IMPROVED"
        if (score_delta is not None and score_delta > 0) or improvement_count > 0:
            return "PARTIAL_IMPROVEMENT"
        if score_delta is not None and score_delta < 0 and improvement_count == 0:
            return "REGRESSED"
        return "NO_IMPROVEMENT"

    @staticmethod
    def _recommendations(
        *,
        current_experiment_summary: dict[str, Any],
        current_analysis: dict[str, Any],
        previous_baseline_summary: dict[str, Any] | None,
        overall_improvement_status: str,
    ) -> list[str]:
        recommendations: list[str] = []
        if previous_baseline_summary is None:
            recommendations.append("Previous baseline summary is unavailable; treat ML31 comparison as degraded.")
        if overall_improvement_status in {"NO_IMPROVEMENT", "REGRESSED"}:
            recommendations.append("Move ML32 toward feature engineering and regime-specific labels.")
        if overall_improvement_status in {"IMPROVED", "PARTIAL_IMPROVEMENT"}:
            recommendations.append("Keep the best ML31 candidate in research mode and deepen validation in ML32.")
        if int(current_experiment_summary.get("accepted_candidate_count", 0) or 0) <= 0:
            recommendations.append("No accepted candidate appeared; keep traders-core disconnected.")
        top_failed_gate = current_analysis.get("top_failed_gate")
        if top_failed_gate:
            recommendations.append(f"Most frequent failing gate in ML31 remains {top_failed_gate}.")
        recommendations.append("Keep live trading, orders, and auto activation disabled.")
        return list(dict.fromkeys(recommendations))
