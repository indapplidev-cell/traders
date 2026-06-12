from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class FeatureRegimeExperimentReporter:
    """Serialize and export feature/regime experiment results."""

    def result_to_dict(self, result: object) -> dict[str, Any]:
        if isinstance(result, dict):
            return dict(result)
        to_dict = getattr(result, "to_dict", None)
        if callable(to_dict):
            return dict(to_dict())
        raise TypeError("result must be a dict or provide to_dict()")

    def result_to_json(self, result: object, *, indent: int | None = 2) -> str:
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
            "experiment_status": payload.get("experiment_status"),
            "config_count": payload.get("config_count"),
            "candidate_count": payload.get("candidate_count"),
            "evaluated_candidate_count": payload.get("evaluated_candidate_count"),
            "failed_candidate_count": payload.get("failed_candidate_count"),
            "accepted_candidate_count": payload.get("accepted_candidate_count"),
            "rejected_candidate_count": payload.get("rejected_candidate_count"),
            "best_candidate_config_id": payload.get("best_candidate_config_id"),
            "best_candidate_score": payload.get("best_candidate_score"),
            "feature_version_used": payload.get("feature_version_used"),
            "real_feature_diagnostics_used": payload.get("real_feature_diagnostics_used"),
            "real_feature_diagnostics_row_count": payload.get("real_feature_diagnostics_row_count"),
            "feature_weak_signal_detected": dict(payload.get("feature_quality_summary", {})).get("weak_signal_detected"),
            "regime_data_available": dict(payload.get("regime_feature_summary", {})).get("regime_data_available"),
            "regime_features_attached": payload.get("regime_features_attached"),
            "regime_feature_count": payload.get("regime_feature_count"),
            "regime_specific_labeling_available": payload.get("regime_specific_labeling_available"),
            "regime_training_applied": payload.get("regime_training_applied"),
            "regime_specific_training_applied": payload.get("regime_specific_training_applied"),
            "regime_label_builder_status": payload.get("regime_label_builder_status"),
            "effective_gap_count_for_training": payload.get("effective_gap_count_for_training"),
            "gap_severity_for_training": payload.get("gap_severity_for_training"),
            "gap_training_safe": payload.get("gap_training_safe"),
            "collapse_diagnostics_v2": payload.get("collapse_diagnostics_v2"),
            "walk_forward_profit_diagnostics": payload.get("walk_forward_profit_diagnostics"),
            "profit_aware_diagnostics": payload.get("profit_aware_diagnostics"),
            "missing_requirements": payload.get("missing_requirements"),
            "feature_leakage_risk_detected": dict(payload.get("feature_leakage_summary", {})).get("leakage_risk_detected"),
            "output_dir": payload.get("output_dir"),
            "summary_json_path": payload.get("summary_json_path"),
            "summary_markdown_path": payload.get("summary_markdown_path"),
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "orders_enabled": False,
            "traders_core_connected": False,
        }

    def compact_summary_to_json(self, result: object, *, indent: int | None = 2) -> str:
        return json.dumps(
            self.compact_summary_to_dict(result),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def write_summary_json(self, result: object, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.result_to_json(result), encoding="utf-8")
        return path

    def write_summary_markdown(self, result: object, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._summary_markdown(self.result_to_dict(result)), encoding="utf-8")
        return path

    def write_diagnostics_json(self, diagnostics: dict[str, Any], output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(diagnostics, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def write_candidate_json(self, candidate: object, output_path: str | Path) -> Path:
        payload = self._candidate_to_dict(candidate)
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def write_candidate_markdown(self, candidate: object, output_path: str | Path) -> Path:
        payload = self._candidate_to_dict(candidate)
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._candidate_markdown(payload), encoding="utf-8")
        return path

    @staticmethod
    def _candidate_to_dict(candidate: object) -> dict[str, Any]:
        if isinstance(candidate, dict):
            return dict(candidate)
        to_dict = getattr(candidate, "to_dict", None)
        if callable(to_dict):
            return dict(to_dict())
        raise TypeError("candidate must be a dict or provide to_dict()")

    def _summary_markdown(self, payload: dict[str, Any]) -> str:
        lines = [
            f"# Feature/Regime Experiment Summary - {payload.get('experiment_id')}",
            "",
            "## Run",
            "",
            f"- experiment id: `{payload.get('experiment_id')}`",
            f"- symbol: `{payload.get('symbol')}`",
            f"- interval: `{payload.get('interval')}`",
            f"- start_date: `{payload.get('start_date')}`",
            f"- end_date: `{payload.get('end_date')}`",
            f"- status: `{payload.get('status')}`",
            f"- experiment_status: `{payload.get('experiment_status')}`",
            f"- evaluated_candidate_count: `{payload.get('evaluated_candidate_count')}`",
            f"- failed_candidate_count: `{payload.get('failed_candidate_count')}`",
            f"- feature_version_used: `{payload.get('feature_version_used')}`",
            f"- regime_training_applied: `{payload.get('regime_training_applied')}`",
            f"- regime_specific_training_applied: `{payload.get('regime_specific_training_applied')}`",
            f"- real_feature_diagnostics_used: `{payload.get('real_feature_diagnostics_used')}`",
            f"- real_feature_diagnostics_row_count: `{payload.get('real_feature_diagnostics_row_count')}`",
            f"- regime_label_builder_status: `{payload.get('regime_label_builder_status')}`",
            f"- effective_gap_count_for_training: `{payload.get('effective_gap_count_for_training')}`",
            f"- gap_severity_for_training: `{payload.get('gap_severity_for_training')}`",
            "",
            "## Feature Diagnostics Summary",
            "",
            f"- feature diagnostics summary: `{payload.get('feature_quality_summary')}`",
            f"- feature group diagnostics summary: `{payload.get('feature_group_quality_summary')}`",
            "",
            "## Regime Diagnostics Summary",
            "",
            f"- regime diagnostics summary: `{payload.get('regime_feature_summary')}`",
            f"- regime_features_attached: `{payload.get('regime_features_attached')}`",
            f"- regime_feature_count: `{payload.get('regime_feature_count')}`",
            f"- regime plan readiness: `{dict(payload.get('regime_experiment_plan_summary', {})).get('ready_for_real_regime_training')}`",
            f"- missing_requirements: `{payload.get('missing_requirements')}`",
            "",
            "## Feature Leakage Summary",
            "",
            f"- feature leakage summary: `{payload.get('feature_leakage_summary')}`",
            "",
            "## Candidate Ranking",
            "",
            "| Rank | Candidate | Config | Score | Candidate Status | Failed Gates |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for row in payload.get("ranking", []):
            lines.append(
                "| `{rank}` | `{candidate_id}` | `{config_id}` | `{score}` | `{candidate_status}` | `{failed_gates}` |".format(
                    rank=row.get("rank"),
                    candidate_id=row.get("candidate_id"),
                    config_id=row.get("config_id"),
                    score=row.get("score"),
                    candidate_status=row.get("candidate_status"),
                    failed_gates=",".join(row.get("failed_gates", [])),
                )
            )
        if not payload.get("ranking"):
            lines.append("| `-` | `-` | `-` | `-` | `-` | `-` |")
        lines.extend(
            [
                "",
                "## Best Candidate",
                "",
                f"- best candidate: `{payload.get('best_candidate_id')}`",
                f"- best_candidate_config_id: `{payload.get('best_candidate_config_id')}`",
                f"- best_candidate_score: `{payload.get('best_candidate_score')}`",
                f"- why accepted/rejected: `{payload.get('experiment_status')}`",
                f"- collapse_diagnostics_v2: `{payload.get('collapse_diagnostics_v2')}`",
                f"- walk_forward_profit_diagnostics: `{payload.get('walk_forward_profit_diagnostics')}`",
                f"- profit_aware_diagnostics: `{payload.get('profit_aware_diagnostics')}`",
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
    def _candidate_markdown(payload: dict[str, Any]) -> str:
        lines = [
            f"# Feature/Regime Candidate - {payload.get('candidate_id')}",
            "",
            f"- candidate_id: `{payload.get('candidate_id')}`",
            f"- config_id: `{payload.get('config_id')}`",
            f"- status: `{payload.get('status')}`",
            f"- candidate_status: `{payload.get('candidate_status')}`",
            f"- raw_candidate_status: `{payload.get('raw_candidate_status')}`",
            f"- quality_status: `{payload.get('quality_status')}`",
            f"- score: `{payload.get('score')}`",
            f"- regime_specific_training_applied: `{payload.get('regime_specific_training_applied')}`",
            f"- failed_gates: `{payload.get('failed_gates')}`",
            f"- probability_diagnostics_missing_reason: `{payload.get('probability_diagnostics_missing_reason')}`",
            f"- real_feature_diagnostics_missing_reason: `{payload.get('real_feature_diagnostics_missing_reason')}`",
            f"- collapse_diagnostics_v2_missing_reason: `{payload.get('collapse_diagnostics_v2_missing_reason')}`",
            f"- walk_forward_profit_diagnostics_missing_reason: `{payload.get('walk_forward_profit_diagnostics_missing_reason')}`",
            f"- profit_aware_diagnostics_missing_reason: `{payload.get('profit_aware_diagnostics_missing_reason')}`",
            "",
            "## Safety",
            "",
            f"- approved_for_live_trading: `{payload.get('approved_for_live_trading')}`",
            f"- approved_for_auto_activation: `{payload.get('approved_for_auto_activation')}`",
            f"- orders_enabled: `{payload.get('orders_enabled')}`",
            f"- traders_core_connected: `{payload.get('traders_core_connected')}`",
            "",
        ]
        return "\n".join(lines)
