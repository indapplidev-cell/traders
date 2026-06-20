from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class FeatureRegimeExperimentReporter:
    """Serialize and export feature/regime experiment results."""

    @staticmethod
    def _as_list(value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return list(value)
        if isinstance(value, (tuple, set)):
            return list(value)
        return [value]

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}

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
            "feature_weak_signal_detected": self._as_dict(payload.get("feature_quality_summary")).get("weak_signal_detected"),
            "regime_data_available": self._as_dict(payload.get("regime_feature_summary")).get("regime_data_available"),
            "regime_features_attached": payload.get("regime_features_attached"),
            "regime_feature_count": payload.get("regime_feature_count"),
            "book_setup_context_features_attached": payload.get("book_setup_context_features_attached"),
            "book_setup_context_feature_count": payload.get("book_setup_context_feature_count"),
            "fv4_feature_count": payload.get("fv4_feature_count"),
            "nison_feature_count": payload.get("nison_feature_count"),
            "altunina_feature_count": payload.get("altunina_feature_count"),
            "path_context_feature_count": payload.get("path_context_feature_count"),
            "htf_context_feature_count": payload.get("htf_context_feature_count"),
            "missing_context_feature_count": payload.get("missing_context_feature_count"),
            "regime_specific_labeling_available": payload.get("regime_specific_labeling_available"),
            "regime_training_applied": payload.get("regime_training_applied"),
            "regime_specific_training_applied": payload.get("regime_specific_training_applied"),
            "regime_label_builder_used_in_training_any": payload.get("regime_label_builder_used_in_training_any"),
            "regime_label_builder_used_in_training_all": payload.get("regime_label_builder_used_in_training_all"),
            "regime_specific_training_applied_any": payload.get("regime_specific_training_applied_any"),
            "regime_specific_training_applied_all": payload.get("regime_specific_training_applied_all"),
            "probability_diagnostics": payload.get("probability_diagnostics"),
            "probability_diagnostics_missing_reason": payload.get("probability_diagnostics_missing_reason"),
            "real_feature_diagnostics": payload.get("real_feature_diagnostics"),
            "real_feature_diagnostics_missing_reason": payload.get("real_feature_diagnostics_missing_reason"),
            "regime_label_builder_status": payload.get("regime_label_builder_status"),
            "effective_gap_count_for_training": payload.get("effective_gap_count_for_training"),
            "gap_severity_for_training": payload.get("gap_severity_for_training"),
            "gap_training_safe": payload.get("gap_training_safe"),
            "collapse_diagnostics_v2": payload.get("collapse_diagnostics_v2"),
            "collapse_diagnostics_v2_missing_reason": payload.get("collapse_diagnostics_v2_missing_reason"),
            "walk_forward_profit_diagnostics": payload.get("walk_forward_profit_diagnostics"),
            "walk_forward_profit_diagnostics_missing_reason": payload.get("walk_forward_profit_diagnostics_missing_reason"),
            "profit_aware_diagnostics": payload.get("profit_aware_diagnostics"),
            "profit_aware_diagnostics_missing_reason": payload.get("profit_aware_diagnostics_missing_reason"),
            "regime_label_builder_status_missing_reason": payload.get("regime_label_builder_status_missing_reason"),
            "missing_requirements": payload.get("missing_requirements"),
            "feature_leakage_risk_detected": self._as_dict(payload.get("feature_leakage_summary")).get("leakage_risk_detected"),
            "output_dir": payload.get("output_dir"),
            "summary_json_path": payload.get("summary_json_path"),
            "summary_markdown_path": payload.get("summary_markdown_path"),
            "model_accepted": payload.get("model_accepted"),
            "reasons_why_best_still_rejected": payload.get("reasons_why_best_still_rejected"),
            "configs_ranked": payload.get("configs_ranked"),
            "confidence_profitability_diagnostics": payload.get("confidence_profitability_diagnostics"),
            "flat_bias_summary": payload.get("flat_bias_summary"),
            "down_blindness_summary": payload.get("down_blindness_summary"),
            "baseline_edge_summary": payload.get("baseline_edge_summary"),
            "label_mode_comparison_audit": payload.get("label_mode_comparison_audit"),
            "flat_subtype_audit": payload.get("flat_subtype_audit"),
            "setup_aware_label_diagnostics": payload.get("setup_aware_label_diagnostics"),
            "schwager_slice_robustness": payload.get("schwager_slice_robustness"),
            "schwager_robustness_decision_board": payload.get("schwager_robustness_decision_board"),
            "class_margin_objective_decision": payload.get("class_margin_objective_decision"),
            "opportunity_probability_threshold": payload.get("opportunity_probability_threshold"),
            "setup_quality_min_threshold": payload.get("setup_quality_min_threshold"),
            "setup_quality_decision_mask_enabled": payload.get("setup_quality_decision_mask_enabled"),
            "setup_quality_decision_mask_min_threshold": payload.get("setup_quality_decision_mask_min_threshold"),
            "selected_opportunity_threshold": payload.get("selected_opportunity_threshold"),
            "opportunity_threshold_selection": payload.get("opportunity_threshold_selection"),
            "opportunity_threshold_sweep": payload.get("opportunity_threshold_sweep"),
            "setup_quality_filter_passed": payload.get("setup_quality_filter_passed"),
            "setup_quality_bucket_metrics": payload.get("setup_quality_bucket_metrics"),
            "setup_quality_bucket_metrics_raw": payload.get("setup_quality_bucket_metrics_raw"),
            "setup_quality_bucket_metrics_after_mask": payload.get("setup_quality_bucket_metrics_after_mask"),
            "setup_quality_filter_summary": payload.get("setup_quality_filter_summary"),
            "setup_quality_decision_mask_summary": payload.get("setup_quality_decision_mask_summary"),
            "predicted_to_actual_trade_rate_ratio": payload.get("predicted_to_actual_trade_rate_ratio"),
            "predicted_trade_rate": payload.get("predicted_trade_rate"),
            "raw_predicted_trade_rate": payload.get("raw_predicted_trade_rate"),
            "masked_predicted_trade_rate": payload.get("masked_predicted_trade_rate"),
            "actual_trade_rate": payload.get("actual_trade_rate"),
            "opportunity_precision": payload.get("opportunity_precision"),
            "opportunity_recall": payload.get("opportunity_recall"),
            "opportunity_f1": payload.get("opportunity_f1"),
            "raw_opportunity_precision": payload.get("raw_opportunity_precision"),
            "raw_opportunity_recall": payload.get("raw_opportunity_recall"),
            "raw_opportunity_f1": payload.get("raw_opportunity_f1"),
            "opportunity_false_positive_rate": payload.get("opportunity_false_positive_rate"),
            "two_stage_trade_diagnostics": payload.get("two_stage_trade_diagnostics"),
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
            f"- regime_label_builder_used_in_training_any: `{payload.get('regime_label_builder_used_in_training_any')}`",
            f"- regime_label_builder_used_in_training_all: `{payload.get('regime_label_builder_used_in_training_all')}`",
            f"- regime_specific_training_applied_any: `{payload.get('regime_specific_training_applied_any')}`",
            f"- regime_specific_training_applied_all: `{payload.get('regime_specific_training_applied_all')}`",
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
            f"- book_setup_context_features_attached: `{payload.get('book_setup_context_features_attached')}`",
            f"- book_setup_context_feature_count: `{payload.get('book_setup_context_feature_count')}`",
            f"- fv4_feature_count: `{payload.get('fv4_feature_count')}`",
            f"- nison_feature_count: `{payload.get('nison_feature_count')}`",
            f"- altunina_feature_count: `{payload.get('altunina_feature_count')}`",
            f"- path_context_feature_count: `{payload.get('path_context_feature_count')}`",
            f"- htf_context_feature_count: `{payload.get('htf_context_feature_count')}`",
            f"- missing_context_feature_count: `{payload.get('missing_context_feature_count')}`",
            f"- regime plan readiness: `{self._as_dict(payload.get('regime_experiment_plan_summary')).get('ready_for_real_regime_training')}`",
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
        for row in self._as_list(payload.get("ranking")):
            lines.append(
                "| `{rank}` | `{candidate_id}` | `{config_id}` | `{score}` | `{candidate_status}` | `{failed_gates}` |".format(
                    rank=row.get("rank"),
                    candidate_id=row.get("candidate_id"),
                    config_id=row.get("config_id"),
                    score=row.get("score"),
                    candidate_status=row.get("candidate_status"),
                    failed_gates=",".join(self._as_list(row.get("failed_gates"))),
                )
            )
        if not self._as_list(payload.get("ranking")):
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
            f"- flat_bias_summary: `{payload.get('flat_bias_summary')}`",
            f"- down_blindness_summary: `{payload.get('down_blindness_summary')}`",
            f"- baseline_edge_summary: `{payload.get('baseline_edge_summary')}`",
            f"- reasons_why_best_still_rejected: `{payload.get('reasons_why_best_still_rejected')}`",
            f"- walk_forward_profit_diagnostics: `{payload.get('walk_forward_profit_diagnostics')}`",
            f"- profit_aware_diagnostics: `{payload.get('profit_aware_diagnostics')}`",
            f"- confidence_profitability_diagnostics: `{payload.get('confidence_profitability_diagnostics')}`",
            f"- selected_opportunity_threshold: `{payload.get('selected_opportunity_threshold')}`",
            f"- setup_quality_min_threshold: `{payload.get('setup_quality_min_threshold')}`",
            f"- setup_quality_decision_mask_enabled: `{payload.get('setup_quality_decision_mask_enabled')}`",
            f"- setup_quality_decision_mask_min_threshold: `{payload.get('setup_quality_decision_mask_min_threshold')}`",
            f"- setup_quality_filter_passed: `{payload.get('setup_quality_filter_passed')}`",
            f"- opportunity_precision: `{payload.get('opportunity_precision')}`",
            f"- opportunity_recall: `{payload.get('opportunity_recall')}`",
            f"- opportunity_f1: `{payload.get('opportunity_f1')}`",
            "",
            "## Label Mode Audits",
            "",
            f"- label_mode_comparison_audit: `{payload.get('label_mode_comparison_audit')}`",
            f"- flat_subtype_audit: `{payload.get('flat_subtype_audit')}`",
            f"- setup_aware_label_diagnostics: `{payload.get('setup_aware_label_diagnostics')}`",
            f"- schwager_slice_robustness: `{payload.get('schwager_slice_robustness')}`",
            f"- schwager_robustness_decision_board: `{payload.get('schwager_robustness_decision_board')}`",
            f"- class_margin_objective_decision: `{payload.get('class_margin_objective_decision')}`",
            "",
            "## Recommendations",
                "",
            ]
        )
        for item in self._as_list(payload.get("recommendations")):
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
        root_cause_audit = dict(payload.get("prediction_root_cause_audit", {}))
        forensic_audit = dict(payload.get("book_driven_forensic_audit", {}))
        robustness_board = dict(payload.get("schwager_robustness_decision_board", {}))
        class_margin_decision = dict(payload.get("class_margin_objective_decision", {}))
        collapse_signature = dict(root_cause_audit.get("up_collapse_signature", {}))
        warnings = root_cause_audit.get("warnings") or []
        recommendations = root_cause_audit.get("recommendations") or []
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
            f"- selected_opportunity_threshold: `{payload.get('selected_opportunity_threshold')}`",
            f"- opportunity_probability_threshold: `{payload.get('opportunity_probability_threshold')}`",
            f"- setup_quality_min_threshold: `{payload.get('setup_quality_min_threshold')}`",
            f"- setup_quality_decision_mask_enabled: `{payload.get('setup_quality_decision_mask_enabled')}`",
            f"- setup_quality_decision_mask_min_threshold: `{payload.get('setup_quality_decision_mask_min_threshold')}`",
            f"- setup_quality_filter_passed: `{payload.get('setup_quality_filter_passed')}`",
            f"- predicted_to_actual_trade_rate_ratio: `{payload.get('predicted_to_actual_trade_rate_ratio')}`",
            f"- predicted_trade_rate: `{payload.get('predicted_trade_rate')}`",
            f"- raw_predicted_trade_rate: `{payload.get('raw_predicted_trade_rate')}`",
            f"- masked_predicted_trade_rate: `{payload.get('masked_predicted_trade_rate')}`",
            f"- actual_trade_rate: `{payload.get('actual_trade_rate')}`",
            f"- opportunity_precision: `{payload.get('opportunity_precision')}`",
            f"- opportunity_recall: `{payload.get('opportunity_recall')}`",
            f"- opportunity_f1: `{payload.get('opportunity_f1')}`",
            f"- raw_opportunity_precision: `{payload.get('raw_opportunity_precision')}`",
            f"- raw_opportunity_recall: `{payload.get('raw_opportunity_recall')}`",
            f"- raw_opportunity_f1: `{payload.get('raw_opportunity_f1')}`",
            f"- opportunity_false_positive_rate: `{payload.get('opportunity_false_positive_rate')}`",
            f"- setup_quality_decision_mask_summary: `{payload.get('setup_quality_decision_mask_summary')}`",
            f"- two_stage_trade_diagnostics: `{payload.get('two_stage_trade_diagnostics')}`",
            "",
            "## Safety",
            "",
            f"- approved_for_live_trading: `{payload.get('approved_for_live_trading')}`",
            f"- approved_for_auto_activation: `{payload.get('approved_for_auto_activation')}`",
            f"- orders_enabled: `{payload.get('orders_enabled')}`",
            f"- traders_core_connected: `{payload.get('traders_core_connected')}`",
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
            "## Label mode audits",
            "",
            f"- label_mode_recommendation: `{dict(payload.get('label_mode_comparison_audit', {})).get('label_mode_recommendation')}`",
            f"- dominant_flat_subtype: `{dict(payload.get('flat_subtype_audit', {})).get('dominant_flat_subtype')}`",
            f"- recommended_label_mode_by_setup_type: `{dict(payload.get('setup_aware_label_diagnostics', {})).get('recommended_label_mode_by_setup_type')}`",
            "",
            "## Schwager Decision Board",
            "",
            f"- final_research_decision: `{robustness_board.get('final_research_decision')}`",
            f"- primary_failure: `{robustness_board.get('primary_failure')}`",
            f"- secondary_failures: `{robustness_board.get('secondary_failures')}`",
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
