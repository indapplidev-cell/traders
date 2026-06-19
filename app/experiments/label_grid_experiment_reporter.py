from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class LabelGridExperimentReporter:
    """Serialize and export label-grid experiment results."""

    def result_to_dict(self, result: object) -> dict[str, Any]:
        if isinstance(result, dict):
            return dict(result)
        to_dict = getattr(result, "to_dict", None)
        if callable(to_dict):
            return dict(to_dict())
        raise TypeError("result must be a dict or provide to_dict()")

    def result_to_json(
        self,
        result: object,
        *,
        indent: int | None = 2,
    ) -> str:
        return json.dumps(
            self.result_to_dict(result),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def compact_summary_to_dict(self, result: object) -> dict[str, Any]:
        payload = self.result_to_dict(result)
        return {
            "status": payload.get("status"),
            "experiment_id": payload.get("experiment_id"),
            "symbol": payload.get("symbol"),
            "interval": payload.get("interval"),
            "start_date": payload.get("start_date"),
            "end_date": payload.get("end_date"),
            "config_count": payload.get("config_count"),
            "completed_candidate_count": payload.get("completed_candidate_count"),
            "failed_candidate_count": payload.get("failed_candidate_count"),
            "accepted_candidate_count": payload.get("accepted_candidate_count"),
            "rejected_candidate_count": payload.get("rejected_candidate_count"),
            "experiment_status": payload.get("experiment_status"),
            "best_candidate_config_id": payload.get("best_candidate_config_id"),
            "best_candidate_status": payload.get("best_candidate_status"),
            "best_candidate_score": payload.get("best_candidate_score"),
            "feature_version_used": payload.get("feature_version_used"),
            "output_dir": payload.get("output_dir"),
            "log_path": payload.get("log_path"),
            "events_path": payload.get("events_path"),
            "summary_json_path": payload.get("summary_json_path"),
            "summary_markdown_path": payload.get("summary_markdown_path"),
            "approved_for_live_trading": payload.get("approved_for_live_trading", False),
            "approved_for_auto_activation": payload.get(
                "approved_for_auto_activation",
                False,
            ),
            "orders_enabled": payload.get("orders_enabled", False),
            "traders_core_connected": payload.get("traders_core_connected", False),
        }

    def compact_summary_to_json(
        self,
        result: object,
        *,
        indent: int | None = 2,
    ) -> str:
        return json.dumps(
            self.compact_summary_to_dict(result),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def write_json_summary(self, result: object) -> Path:
        payload = self.result_to_dict(result)
        path = Path(str(payload["summary_json_path"]))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.result_to_json(result), encoding="utf-8")
        return path

    def write_markdown_summary(self, result: object) -> Path:
        payload = self.result_to_dict(result)
        path = Path(str(payload["summary_markdown_path"]))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._summary_markdown(payload), encoding="utf-8")
        return path

    def write_candidate_json(self, candidate: object, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self._normalize_candidate(candidate), ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return path

    def write_candidate_markdown(
        self,
        candidate: object,
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            self._candidate_markdown(self._normalize_candidate(candidate)),
            encoding="utf-8",
        )
        return path

    @staticmethod
    def _normalize_candidate(candidate: object) -> dict[str, Any]:
        if isinstance(candidate, dict):
            return dict(candidate)
        to_dict = getattr(candidate, "to_dict", None)
        if callable(to_dict):
            return dict(to_dict())
        raise TypeError("candidate must be a dict or provide to_dict()")

    def _summary_markdown(self, payload: dict[str, Any]) -> str:
        ranking = payload.get("candidate_ranking", [])
        lines = [
            f"# Label Grid Experiment Summary - {payload.get('experiment_id')}",
            "",
            "## Run",
            "",
            f"- experiment_id: `{payload.get('experiment_id')}`",
            f"- status: `{payload.get('status')}`",
            f"- experiment_status: `{payload.get('experiment_status')}`",
            f"- symbol: `{payload.get('symbol')}`",
            f"- interval: `{payload.get('interval')}`",
            f"- start_date: `{payload.get('start_date')}`",
            f"- end_date: `{payload.get('end_date')}`",
            f"- configs_tested: `{payload.get('config_count')}`",
            "",
            "## Candidate Ranking",
            "",
            "| Rank | Config | Candidate | Quality | Score | Failed Gates |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for item in ranking:
            lines.append(
                "| `{rank}` | `{config_id}` | `{candidate_status}` | `{quality_status}` | `{score}` | `{failed_gates}` |".format(
                    rank=item.get("rank"),
                    config_id=item.get("config_id"),
                    candidate_status=item.get("candidate_status"),
                    quality_status=item.get("quality_status"),
                    score=item.get("score"),
                    failed_gates=",".join(item.get("failed_gates", [])),
                )
            )
        if not ranking:
            lines.append("| `-` | `-` | `-` | `-` | `-` | `-` |")

        best_candidate_config_id = payload.get("best_candidate_config_id")
        accepted_count = int(payload.get("accepted_candidate_count") or 0)
        lines.extend(
            [
                "",
                "## Selection",
                "",
            ]
        )
        if accepted_count > 0 and best_candidate_config_id:
            lines.append(f"- accepted_candidate: `{best_candidate_config_id}`")
        elif best_candidate_config_id:
            lines.append(f"- best_rejected_candidate: `{best_candidate_config_id}`")
        else:
            lines.append("- no_scored_candidates")

        lines.extend(
            [
                f"- accepted_candidate_count: `{payload.get('accepted_candidate_count')}`",
                f"- rejected_candidate_count: `{payload.get('rejected_candidate_count')}`",
                "",
                "## Diagnostics",
                "",
                f"- anti-collapse: `{payload.get('collapse_summary')}`",
                f"- profit-aware: `{payload.get('profit_summary')}`",
                f"- walk-forward: `{payload.get('walk_forward_summary')}`",
                f"- gap quality: `{payload.get('gap_quality_summary')}`",
                f"- failed gates summary: `{payload.get('failed_gates_summary')}`",
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
    def _candidate_markdown(candidate: dict[str, Any]) -> str:
        root_cause_audit = dict(candidate.get("prediction_root_cause_audit", {}))
        forensic_audit = dict(candidate.get("book_driven_forensic_audit", {}))
        robustness_board = dict(candidate.get("schwager_robustness_decision_board", {}))
        class_margin_decision = dict(candidate.get("class_margin_objective_decision", {}))
        collapse_signature = dict(root_cause_audit.get("up_collapse_signature", {}))
        warnings = root_cause_audit.get("warnings") or []
        recommendations = root_cause_audit.get("recommendations") or []
        lines = [
            f"# Candidate Result - {candidate.get('config_id')}",
            "",
            "## Candidate",
            "",
            f"- config_id: `{candidate.get('config_id')}`",
            f"- status: `{candidate.get('status')}`",
            f"- quality_status: `{candidate.get('quality_status')}`",
            f"- candidate_status: `{candidate.get('candidate_status')}`",
            f"- model_version: `{candidate.get('model_version')}`",
            f"- training_run_id: `{candidate.get('training_run_id')}`",
            f"- accuracy_edge: `{candidate.get('accuracy_edge')}`",
            f"- collapse_detected: `{candidate.get('collapse_detected')}`",
            f"- profit_factor: `{candidate.get('profit_factor')}`",
            f"- walk_forward_profit_factor: `{candidate.get('walk_forward_profit_factor')}`",
            f"- failed_gates: `{candidate.get('failed_gates')}`",
            "",
            "## Safety",
            "",
            f"- approved_for_traders_core_integration: `{candidate.get('approved_for_traders_core_integration')}`",
            f"- approved_for_live_trading: `{candidate.get('approved_for_live_trading')}`",
            f"- approved_for_auto_activation: `{candidate.get('approved_for_auto_activation')}`",
            f"- orders_enabled: `{candidate.get('orders_enabled')}`",
            f"- traders_core_connected: `{candidate.get('traders_core_connected')}`",
            "",
            "## Prediction root-cause audit",
            "",
            f"- warnings: `{warnings}`",
            f"- actual_down_predicted_up_ratio: `{collapse_signature.get('actual_down_predicted_up_ratio')}`",
            f"- actual_flat_predicted_up_ratio: `{collapse_signature.get('actual_flat_predicted_up_ratio')}`",
            f"- predicted_up_actual_down_or_flat_share: `{collapse_signature.get('predicted_up_actual_down_or_flat_share')}`",
            f"- recommendation: `{recommendations[0] if recommendations else None}`",
            "",
            "## Book-driven forensic audit",
            "",
            f"- final_diagnosis: `{forensic_audit.get('final_diagnosis')}`",
            f"- next_action_recommendation: `{forensic_audit.get('next_action_recommendation')}`",
            "",
            "## Schwager Decision Board",
            "",
            f"- final_research_decision: `{robustness_board.get('final_research_decision')}`",
            f"- primary_failure: `{robustness_board.get('primary_failure')}`",
            f"- what_not_to_do_next: `{robustness_board.get('what_not_to_do_next')}`",
            f"- what_to_do_next: `{robustness_board.get('what_to_do_next')}`",
            "",
            "## Class-Margin Objective Decision",
            "",
            f"- class_margin_objective_allowed: `{class_margin_decision.get('class_margin_objective_allowed')}`",
            f"- reason: `{class_margin_decision.get('reason')}`",
            f"- missing_diagnostics: `{class_margin_decision.get('missing_diagnostics')}`",
            "",
        ]
        return "\n".join(lines)
