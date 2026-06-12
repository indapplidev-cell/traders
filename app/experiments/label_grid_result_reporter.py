from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class LabelGridResultReporter:
    """Serialize and export ML29 label-grid result analysis."""

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
        analysis_json_path: str | None = None,
        analysis_markdown_path: str | None = None,
    ) -> dict[str, Any]:
        payload = self.analysis_to_dict(analysis)
        return {
            "status": "ok",
            "experiment_id": payload.get("experiment_id"),
            "experiment_status": payload.get("experiment_status"),
            "config_count": payload.get("config_count"),
            "accepted_candidate_count": payload.get("accepted_candidate_count"),
            "rejected_candidate_count": payload.get("rejected_candidate_count"),
            "best_candidate_config_id": payload.get("best_candidate_config_id"),
            "best_candidate_status": payload.get("best_candidate_status"),
            "best_candidate_score": payload.get("best_candidate_score"),
            "top_failed_gate": payload.get("top_failed_gate"),
            "analysis_json_path": analysis_json_path,
            "analysis_markdown_path": analysis_markdown_path,
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "orders_enabled": False,
            "traders_core_connected": False,
        }

    def write_analysis_json(
        self,
        analysis: dict[str, Any] | object,
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.analysis_to_json(analysis), encoding="utf-8")
        return path

    def write_analysis_markdown(
        self,
        analysis: dict[str, Any] | object,
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._analysis_markdown(self.analysis_to_dict(analysis)), encoding="utf-8")
        return path

    def write_plan_json(self, plan: dict[str, Any], output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def write_plan_markdown(self, plan: dict[str, Any], output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._plan_markdown(plan), encoding="utf-8")
        return path

    @staticmethod
    def _analysis_markdown(payload: dict[str, Any]) -> str:
        lines = [
            f"# Label Grid Result Analysis - {payload.get('experiment_id')}",
            "",
            "## Summary",
            "",
            f"- experiment_status: `{payload.get('experiment_status')}`",
            f"- config_count: `{payload.get('config_count')}`",
            f"- accepted_candidate_count: `{payload.get('accepted_candidate_count')}`",
            f"- rejected_candidate_count: `{payload.get('rejected_candidate_count')}`",
            f"- best_candidate_config_id: `{payload.get('best_candidate_config_id')}`",
            f"- best_candidate_status: `{payload.get('best_candidate_status')}`",
            f"- best_candidate_score: `{payload.get('best_candidate_score')}`",
            f"- top_failed_gate: `{payload.get('top_failed_gate')}`",
            "",
            "## Candidate Comparison",
            "",
            "| Rank | Config | Score | Candidate | Quality | Accuracy Edge | Collapse | Profit Factor | Walk-Forward PF | Failed Gates | Recommendation |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        candidate_results = {
            item.get("config_id"): item for item in payload.get("candidate_results", [])
        }
        for row in payload.get("candidate_ranking", []):
            candidate = candidate_results.get(row.get("config_id"), {})
            recommendation = "; ".join(candidate.get("recommendations", [])[:1])
            lines.append(
                "| `{rank}` | `{config_id}` | `{score}` | `{candidate_status}` | `{quality_status}` | `{accuracy_edge}` | `{collapse_type}` | `{profit_factor}` | `{walk_forward_profit_factor}` | `{failed_gates}` | {recommendation} |".format(
                    rank=row.get("rank"),
                    config_id=row.get("config_id"),
                    score=row.get("score"),
                    candidate_status=row.get("candidate_status"),
                    quality_status=row.get("quality_status"),
                    accuracy_edge=candidate.get("accuracy_edge"),
                    collapse_type=candidate.get("collapse_type"),
                    profit_factor=candidate.get("profit_factor"),
                    walk_forward_profit_factor=candidate.get("walk_forward_profit_factor"),
                    failed_gates=",".join(candidate.get("failed_gates", [])),
                    recommendation=recommendation or "-",
                )
            )

        lines.extend(
            [
                "",
                "## Gate Failures",
                "",
                f"- gate_failure_counts: `{payload.get('gate_failure_counts')}`",
                "",
                "## Recommendations",
                "",
            ]
        )
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

    @staticmethod
    def _plan_markdown(plan: dict[str, Any]) -> str:
        lines = [
            f"# Next Label Experiment Plan - {plan.get('experiment_id')}",
            "",
            f"- planner_name: `{plan.get('planner_name')}`",
            f"- planner_version: `{plan.get('planner_version')}`",
            "",
            "## Recommendations",
            "",
        ]
        for item in plan.get("recommendations", []):
            lines.append(f"- {item}")
        lines.extend(
            [
                "",
                "## Next Plan",
                "",
                f"- best_candidate_config_id: `{plan.get('next_experiment_plan', {}).get('best_candidate_config_id')}`",
                f"- best_candidate_status: `{plan.get('next_experiment_plan', {}).get('best_candidate_status')}`",
                f"- top_failed_gate: `{plan.get('next_experiment_plan', {}).get('top_failed_gate')}`",
                f"- focus_areas: `{plan.get('next_experiment_plan', {}).get('focus_areas')}`",
                "",
            ]
        )
        return "\n".join(lines)
