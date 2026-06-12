from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ML31GridImprovementReporter:
    """Export ML31 grid improvement analysis artifacts."""

    def analysis_to_dict(self, analysis: dict[str, Any] | object) -> dict[str, Any]:
        if isinstance(analysis, dict):
            return dict(analysis)
        to_dict = getattr(analysis, "to_dict", None)
        if callable(to_dict):
            return dict(to_dict())
        raise TypeError("analysis must be a dict or provide to_dict()")

    def analysis_to_json(
        self,
        analysis: dict[str, Any] | object,
        *,
        indent: int | None = 2,
    ) -> str:
        return json.dumps(
            self.analysis_to_dict(analysis),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def compact_summary_to_dict(
        self,
        analysis: dict[str, Any] | object,
        *,
        json_path: str | None = None,
        markdown_path: str | None = None,
    ) -> dict[str, Any]:
        payload = self.analysis_to_dict(analysis)
        return {
            "status": "ok",
            "overall_improvement_status": payload.get("overall_improvement_status"),
            "current_experiment_id": payload.get("current_experiment_id"),
            "current_config_count": payload.get("current_config_count"),
            "current_accepted_candidate_count": payload.get("current_accepted_candidate_count"),
            "current_best_candidate_config_id": payload.get("current_best_candidate_config_id"),
            "current_best_candidate_score": payload.get("current_best_candidate_score"),
            "score_delta": payload.get("score_delta"),
            "accepted_candidate_improved": payload.get("accepted_candidate_improved"),
            "collapse_improved": payload.get("collapse_improved"),
            "profit_aware_improved": payload.get("profit_aware_improved"),
            "walk_forward_improved": payload.get("walk_forward_improved"),
            "json_path": json_path,
            "markdown_path": markdown_path,
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "orders_enabled": False,
            "traders_core_connected": False,
        }

    def write_analysis_json(self, analysis: dict[str, Any] | object, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.analysis_to_json(analysis), encoding="utf-8")
        return path

    def write_analysis_markdown(self, analysis: dict[str, Any] | object, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._analysis_markdown(self.analysis_to_dict(analysis)), encoding="utf-8")
        return path

    @staticmethod
    def _analysis_markdown(payload: dict[str, Any]) -> str:
        lines = [
            "# ML31 Grid Improvement Analysis",
            "",
            "## Summary",
            "",
            f"- current experiment: `{payload.get('current_experiment_id')}`",
            f"- previous baseline if available: `{payload.get('previous_experiment_id')}`",
            f"- overall_improvement_status: `{payload.get('overall_improvement_status')}`",
            f"- current_best_candidate_config_id: `{payload.get('current_best_candidate_config_id')}`",
            f"- current_best_candidate_score: `{payload.get('current_best_candidate_score')}`",
            f"- previous_best_candidate_score: `{payload.get('previous_best_candidate_score')}`",
            f"- score_delta: `{payload.get('score_delta')}`",
            "",
            "## Candidate Comparison",
            "",
            f"- current_accepted_candidate_count: `{payload.get('current_accepted_candidate_count')}`",
            f"- current_rejected_candidate_count: `{payload.get('current_rejected_candidate_count')}`",
            f"- accepted_candidate_improved: `{payload.get('accepted_candidate_improved')}`",
            "",
            "## Gate Failure Comparison",
            "",
            f"- baseline_edge_improved: `{payload.get('baseline_edge_improved')}`",
            f"- collapse_improved: `{payload.get('collapse_improved')}`",
            f"- profit_aware_improved: `{payload.get('profit_aware_improved')}`",
            f"- walk_forward_improved: `{payload.get('walk_forward_improved')}`",
            f"- gap_quality_improved: `{payload.get('gap_quality_improved')}`",
            "",
            "## Best Candidate",
            "",
            f"- best candidate: `{payload.get('current_best_candidate_config_id')}`",
            f"- why accepted/rejected: `{payload.get('overall_improvement_status')}` with current accepted count `{payload.get('current_accepted_candidate_count')}`",
            "",
            "## What Improved",
            "",
            f"- accepted_candidate_improved: `{payload.get('accepted_candidate_improved')}`",
            f"- collapse_improved: `{payload.get('collapse_improved')}`",
            f"- profit_aware_improved: `{payload.get('profit_aware_improved')}`",
            f"- walk_forward_improved: `{payload.get('walk_forward_improved')}`",
            f"- gap_quality_improved: `{payload.get('gap_quality_improved')}`",
            "",
            "## What Did Not Improve",
            "",
            f"- overall_improvement_status: `{payload.get('overall_improvement_status')}`",
            "",
            "## Next Recommendations",
            "",
        ]
        for item in payload.get("recommendations", []):
            lines.append(f"- {item}")
        lines.extend(
            [
                "",
                "## Safety",
                "",
                "- no traders-core integration",
                "- no live trading",
                "- no orders",
                "- no auto activation",
                "",
            ]
        )
        return "\n".join(lines)
