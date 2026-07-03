from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class MultiSymbolFeatureRegimeReporter:
    """Serialize multi-symbol feature/regime analysis results."""

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

    @staticmethod
    def _top_n_items(value: Any, *, limit: int = 5) -> dict[str, Any]:
        payload = dict(value) if isinstance(value, dict) else {}
        return dict(list(payload.items())[:limit])

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

    def compact_summary_to_dict(
        self,
        result: object,
        *,
        json_path: str | None = None,
        markdown_path: str | None = None,
    ) -> dict[str, Any]:
        payload = self.result_to_dict(result)
        return {
            "status": "ok",
            "symbols": payload.get("symbols"),
            "experiment_count": payload.get("experiment_count"),
            "candidate_count": payload.get("candidate_count"),
            "evaluated_candidate_count": payload.get("evaluated_candidate_count"),
            "failed_candidate_count": payload.get("failed_candidate_count"),
            "accepted_candidate_count": payload.get("accepted_candidate_count"),
            "rejected_candidate_count": payload.get("rejected_candidate_count"),
            "best_symbol": payload.get("best_symbol"),
            "best_candidate_config_id": payload.get("best_candidate_config_id"),
            "best_candidate_score": payload.get("best_candidate_score"),
            "best_config_by_symbol": payload.get("best_config_by_symbol"),
            "best_global_config": payload.get("best_global_config"),
            "configs_ranked": payload.get("configs_ranked"),
            "all_feature_version_fv2": payload.get("all_feature_version_fv2"),
            "all_gap_training_safe": payload.get("all_gap_training_safe"),
            "all_real_feature_diagnostics_used": payload.get("all_real_feature_diagnostics_used"),
            "any_accepted_candidate": payload.get("any_accepted_candidate"),
            "top_failed_gate": payload.get("top_failed_gate"),
            "symbols_missing_real_diagnostics": payload.get("symbols_missing_real_diagnostics"),
            "symbols_missing_regime_features": payload.get("symbols_missing_regime_features"),
            "symbols_missing_candle_ta_context_features": payload.get("symbols_missing_candle_ta_context_features"),
            "symbol_results": payload.get("symbol_results"),
            "flat_bias_summary": payload.get("flat_bias_summary"),
            "down_blindness_summary": payload.get("down_blindness_summary"),
            "baseline_edge_summary": payload.get("baseline_edge_summary"),
            "label_mode_audit_summary": payload.get("label_mode_audit_summary"),
            "flat_subtype_summary": payload.get("flat_subtype_summary"),
            "setup_aware_label_summary": payload.get("setup_aware_label_summary"),
            "schwager_robustness_summary": payload.get("schwager_robustness_summary"),
            "configs_ranked": payload.get("configs_ranked"),
            "entry_path_audit_by_symbol": {
                item.get("symbol"): {
                    "entry_path_quality_filter_enabled": item.get("entry_path_quality_filter_enabled"),
                    "entry_path_quality_min_threshold": item.get("entry_path_quality_min_threshold"),
                    "stop_pressure_max_risk_score": item.get("stop_pressure_max_risk_score"),
                    "mae_pressure_max_risk_score": item.get("mae_pressure_max_risk_score"),
                    "entry_path_final_signal_original_count": item.get("entry_path_final_signal_original_count"),
                    "entry_path_final_signal_filtered_count": item.get("entry_path_final_signal_filtered_count"),
                    "entry_path_final_signal_blocked_count": item.get("entry_path_final_signal_blocked_count"),
                    "entry_path_stream_consistency_ok": item.get("entry_path_stream_consistency_ok"),
                    "stop_pressure_status": self._as_dict(
                        item.get("stop_pressure_effectiveness_audit")
                    ).get("status"),
                }
                for item in self._as_list(payload.get("symbol_results"))
            },
            "directional_audit_by_symbol": {
                item.get("symbol"): {
                    "directional_edge_bias_audit": item.get("directional_edge_bias_audit"),
                    "directional_side_filter_summary": item.get("directional_side_filter_summary"),
                    "directional_side_filter_profile": item.get("directional_side_filter_profile"),
                    "allowed_signal_directions": item.get("allowed_signal_directions"),
                    "validation_gate_failure_reason_counts": item.get("validation_gate_failure_reason_counts"),
                    "side_aware_relaxed_fold_count": item.get("side_aware_relaxed_fold_count"),
                    "side_aware_validation_relaxation_enabled": item.get("side_aware_validation_relaxation_enabled"),
                    "side_aware_min_validation_signal_count": item.get("side_aware_min_validation_signal_count"),
                    "side_aware_min_validation_profit_factor": item.get("side_aware_min_validation_profit_factor"),
                    "side_aware_min_validation_total_r": item.get("side_aware_min_validation_total_r"),
                    "side_aware_min_validation_expectancy_r": item.get("side_aware_min_validation_expectancy_r"),
                    "side_aware_allow_single_direction_validation": item.get("side_aware_allow_single_direction_validation"),
                    "direction_balance_ratio": item.get("direction_balance_ratio"),
                    "directional_profit_skew_r": item.get("directional_profit_skew_r"),
                    "long_total_r": item.get("long_total_r"),
                    "short_total_r": item.get("short_total_r"),
                }
                for item in self._as_list(payload.get("symbol_results"))
            },
            "directional_side_ablation_comparator": payload.get(
                "directional_side_ablation_comparator"
            ),
            "directional_side_walk_forward_stability": payload.get(
                "directional_side_walk_forward_stability"
            ),
            "directional_side_signal_recovery_summary": payload.get(
                "directional_side_signal_recovery_summary"
            ),
            "walk_forward_validation_candidate_board_summary": payload.get(
                "walk_forward_validation_candidate_board_summary"
            ),
            "walk_forward_fold_root_cause_board": payload.get(
                "walk_forward_fold_root_cause_board"
            ),
            "fold_1_repair_target_selection": payload.get(
                "fold_1_repair_target_selection"
            ),
            "fold_time_slice_exit_repair_probe": payload.get(
                "fold_time_slice_exit_repair_probe"
            ),
            "fold_feature_regime_repair_probe": payload.get(
                "fold_feature_regime_repair_probe"
            ),
            "fold_feature_regime_adaptive_repair_probe": payload.get(
                "fold_feature_regime_adaptive_repair_probe"
            ),
            "validation_gate_failure_reason_counts": payload.get(
                "validation_gate_failure_reason_counts"
            ),
            "side_aware_relaxed_fold_count": payload.get("side_aware_relaxed_fold_count"),
            "side_aware_validation_relaxation_enabled": payload.get(
                "side_aware_validation_relaxation_enabled"
            ),
            "side_aware_min_validation_signal_count": payload.get(
                "side_aware_min_validation_signal_count"
            ),
            "side_aware_min_validation_profit_factor": payload.get(
                "side_aware_min_validation_profit_factor"
            ),
            "side_aware_min_validation_total_r": payload.get(
                "side_aware_min_validation_total_r"
            ),
            "side_aware_min_validation_expectancy_r": payload.get(
                "side_aware_min_validation_expectancy_r"
            ),
            "side_aware_allow_single_direction_validation": payload.get(
                "side_aware_allow_single_direction_validation"
            ),
            "analysis_json_path": json_path,
            "analysis_markdown_path": markdown_path,
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "orders_enabled": False,
            "traders_core_connected": False,
        }

    def compact_summary_to_json(
        self,
        result: object,
        *,
        json_path: str | None = None,
        markdown_path: str | None = None,
        indent: int | None = 2,
    ) -> str:
        return json.dumps(
            self.compact_summary_to_dict(
                result,
                json_path=json_path,
                markdown_path=markdown_path,
            ),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def write_analysis_json(self, result: object, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.result_to_json(result), encoding="utf-8")
        return path

    def write_analysis_markdown(self, result: object, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._markdown(self.result_to_dict(result)), encoding="utf-8")
        return path

    def _markdown(self, payload: dict[str, Any]) -> str:
        lines = [
            "# ML35 Multi-Symbol Feature/Regime Analysis",
            "",
            "## Summary",
            "",
            f"- symbols: `{payload.get('symbols')}`",
            f"- experiment_count: `{payload.get('experiment_count')}`",
            f"- candidate_count: `{payload.get('candidate_count')}`",
            f"- evaluated_candidate_count: `{payload.get('evaluated_candidate_count')}`",
            f"- failed_candidate_count: `{payload.get('failed_candidate_count')}`",
            f"- accepted_candidate_count: `{payload.get('accepted_candidate_count')}`",
            f"- rejected_candidate_count: `{payload.get('rejected_candidate_count')}`",
            f"- best symbol: `{payload.get('best_symbol')}`",
            f"- best candidate config: `{payload.get('best_candidate_config_id')}`",
            f"- best candidate score: `{payload.get('best_candidate_score')}`",
            f"- top failed gate: `{payload.get('top_failed_gate')}`",
                "",
                "## Symbol Comparison Table",
                "",
            "| Symbol | Best Config | Score | Collapse Type | Flat Bias | Down Blindness | Baseline Edge | Profit Factor | Walk-Forward PF | Final Decision | Real Diagnostics | Diag Rows | Regime Features | Regime Count | Candle/TA Context | Candle/TA Count | Failed Gates |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for item in self._as_list(payload.get("symbol_results")):
            lines.append(
                "| `{symbol}` | `{config}` | `{score}` | `{collapse_type}` | `{flat_bias}` | `{down_blindness}` | `{edge}` | `{profit_factor}` | `{walk_forward_pf}` | `{final_decision}` | `{real_diag}` | `{diag_rows}` | `{regime_features}` | `{regime_count}` | `{candle_ta}` | `{candle_ta_count}` | `{failed_gates}` |".format(
                    symbol=item.get("symbol"),
                    config=item.get("best_candidate_config_id"),
                    score=item.get("best_candidate_score"),
                    collapse_type=self._as_dict(item.get("collapse_tuning_summary")).get("collapse_type") or item.get("collapse_type"),
                    flat_bias=item.get("flat_bias_detected"),
                    down_blindness=item.get("down_blindness_detected"),
                    edge=item.get("baseline_edge"),
                    profit_factor=item.get("profit_factor"),
                    walk_forward_pf=item.get("walk_forward_profit_factor"),
                    final_decision=self._as_dict(item.get("schwager_robustness_decision_board")).get("final_research_decision"),
                    real_diag=item.get("real_feature_diagnostics_used"),
                    diag_rows=item.get("real_feature_diagnostics_row_count"),
                    regime_features=item.get("regime_features_attached"),
                    regime_count=item.get("regime_feature_count"),
                    candle_ta=item.get("candle_ta_context_features_attached"),
                    candle_ta_count=item.get("candle_ta_context_feature_count"),
                    failed_gates=",".join(self._as_list(item.get("failed_gates"))),
                )
            )
        if not self._as_list(payload.get("symbol_results")):
            lines.append("| `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` |")

        lines.extend(
            [
                "",
                "## Best Symbol",
                "",
                f"- best symbol: `{payload.get('best_symbol')}`",
                f"- best global config: `{payload.get('best_global_config')}`",
                f"- best score: `{payload.get('best_candidate_score')}`",
                "",
                "## Gate Failures By Symbol",
                "",
            ]
        )
        for item in self._as_list(payload.get("symbol_results")):
            lines.append(f"- {item.get('symbol')}: `{item.get('failed_gates')}`")

        lines.extend(
            [
                "",
                "## Feature Version Check",
                "",
                f"- all_feature_version_fv2: `{payload.get('all_feature_version_fv2')}`",
                f"- all_feature_version_fv3_candle_ta_context: `{self._as_dict(payload.get('feature_version_summary')).get('all_feature_version_fv3_candle_ta_context')}`",
                f"- all_feature_version_fv4_book_setup_context: `{self._as_dict(payload.get('feature_version_summary')).get('all_feature_version_fv4_book_setup_context')}`",
                f"- feature_versions_by_symbol: `{self._as_dict(payload.get('feature_version_summary')).get('feature_versions_by_symbol')}`",
                "",
                "## Gap Training Safety Check",
                "",
                f"- all_gap_training_safe: `{payload.get('all_gap_training_safe')}`",
                f"- gap_severity_by_symbol: `{self._as_dict(payload.get('gap_training_safety_summary')).get('gap_severity_by_symbol')}`",
                f"- effective_gap_count_by_symbol: `{self._as_dict(payload.get('gap_training_safety_summary')).get('effective_gap_count_by_symbol')}`",
                "",
                "## Real Feature Diagnostics Check",
                "",
                f"- all_real_feature_diagnostics_used: `{payload.get('all_real_feature_diagnostics_used')}`",
                f"- symbols_missing_real_diagnostics: `{payload.get('symbols_missing_real_diagnostics')}`",
                f"- real_feature_diagnostics_missing_reason_by_symbol: `{self._as_dict(payload.get('real_feature_diagnostics_summary')).get('missing_reason_by_symbol')}`",
                "",
                "## Regime Integration Status",
                "",
                f"- symbols_missing_regime_features: `{payload.get('symbols_missing_regime_features')}`",
                f"- symbols_missing_candle_ta_context_features: `{payload.get('symbols_missing_candle_ta_context_features')}`",
                f"- regime_features_missing_reason_by_symbol: `{self._as_dict(payload.get('regime_integration_summary')).get('regime_features_missing_reason_by_symbol')}`",
                f"- candle_ta_context_missing_reason_by_symbol: `{self._as_dict(payload.get('regime_integration_summary')).get('candle_ta_context_missing_reason_by_symbol')}`",
                f"- book_setup_context_feature_count_by_symbol: `{self._as_dict(payload.get('regime_integration_summary')).get('book_setup_context_feature_count_by_symbol')}`",
                f"- missing_context_feature_count_by_symbol: `{self._as_dict(payload.get('regime_integration_summary')).get('missing_context_feature_count_by_symbol')}`",
                f"- regime_training_applied_by_symbol: `{self._as_dict(payload.get('regime_integration_summary')).get('regime_training_applied_by_symbol')}`",
                f"- regime_specific_training_applied_any: `{self._as_dict(payload.get('regime_integration_summary')).get('regime_specific_training_applied_any')}`",
                "",
                "## Walk-Forward/Profit-Aware Summary",
                "",
                f"- walk_forward_summary: `{payload.get('walk_forward_summary')}`",
                f"- profit_aware_summary: `{payload.get('profit_aware_summary')}`",
                "",
                "## Collapse Summary",
                "",
                f"- collapse_summary: `{payload.get('collapse_summary')}`",
                f"- collapse_diagnostics_v2_by_symbol: `{ {item.get('symbol'): item.get('collapse_diagnostics_v2') for item in self._as_list(payload.get('symbol_results'))} }`",
                f"- flat_bias_summary: `{payload.get('flat_bias_summary')}`",
                f"- down_blindness_summary: `{payload.get('down_blindness_summary')}`",
                f"- baseline_edge_summary: `{payload.get('baseline_edge_summary')}`",
                "",
                "## Label Mode Audits",
                "",
                f"- label_mode_audit_summary: `{payload.get('label_mode_audit_summary')}`",
                f"- flat_subtype_summary: `{payload.get('flat_subtype_summary')}`",
                f"- setup_aware_label_summary: `{payload.get('setup_aware_label_summary')}`",
                "",
                "## Schwager Robustness",
                "",
                f"- schwager_robustness_summary: `{payload.get('schwager_robustness_summary')}`",
                "",
                "## ML38.10.29 Feature/regime adaptive repair diagnostics",
                "",
            ]
        )
        adaptive_probe = self._as_dict(
            payload.get("fold_feature_regime_adaptive_repair_probe")
            or payload.get("fold_feature_regime_repair_probe")
        )
        adaptive_feature_diag = self._as_dict(
            adaptive_probe.get("feature_filter_diagnostics")
        )
        best_feature_probe = self._as_dict(
            adaptive_probe.get("best_feature_regime_probe")
        )
        best_feature_summary = self._as_dict(
            best_feature_probe.get("fold_feature_regime_filter_summary")
        )
        best_date_probe = self._as_dict(
            adaptive_probe.get("best_date_blackout_probe")
        )
        verdict_detail = self._as_dict(adaptive_probe.get("verdict_detail"))
        lines.extend(
            [
                f"- diagnostic_status: `{adaptive_probe.get('diagnostic_status')}`",
                f"- verdict: `{adaptive_probe.get('verdict')}`",
                f"- verdict_detail.reason: `{verdict_detail.get('reason')}`",
                f"- feature_filter_diagnostics.readiness: `{adaptive_feature_diag.get('readiness')}`",
                f"- regime_propagation_status: `{adaptive_feature_diag.get('regime_propagation_status')}`",
                f"- missing_market_regime_count: `{adaptive_feature_diag.get('missing_market_regime_count')}`",
                f"- active_filter_candidate_count: `{adaptive_feature_diag.get('active_filter_candidate_count')}`",
                f"- zero_removal_candidate_count: `{adaptive_feature_diag.get('zero_removal_candidate_count')}`",
                f"- missing_summary_candidate_count: `{adaptive_feature_diag.get('missing_summary_candidate_count')}`",
                f"- best_feature_regime_probe.config_id: `{best_feature_probe.get('config_id')}`",
                f"- best_feature_regime_probe.fold_feature_regime_filter_summary.removed_signal_count: `{best_feature_summary.get('removed_signal_count')}`",
                f"- best_feature_regime_probe.walk_forward_total_r: `{best_feature_probe.get('walk_forward_total_r')}`",
                f"- best_date_blackout_probe.config_id: `{best_date_probe.get('config_id')}`",
                f"- best_date_blackout_probe.walk_forward_total_r: `{best_date_probe.get('walk_forward_total_r')}`",
                f"- aggregate_primary_removed_counts_by_reason: `{self._top_n_items(adaptive_feature_diag.get('aggregate_primary_removed_counts_by_reason'))}`",
                f"- aggregate_matched_removed_counts_by_reason: `{self._top_n_items(adaptive_feature_diag.get('aggregate_matched_removed_counts_by_reason'))}`",
                f"- aggregate_removed_counts_by_date: `{self._top_n_items(adaptive_feature_diag.get('aggregate_removed_counts_by_date'))}`",
                f"- aggregate_passed_counts_by_date: `{self._top_n_items(adaptive_feature_diag.get('aggregate_passed_counts_by_date'))}`",
                f"- aggregate_removed_counts_by_regime: `{self._top_n_items(adaptive_feature_diag.get('aggregate_removed_counts_by_regime'))}`",
                f"- aggregate_regime_source_counts: `{self._top_n_items(adaptive_feature_diag.get('aggregate_regime_source_counts'))}`",
                f"- aggregate_removed_counts_by_active_regime_flag: `{self._top_n_items(adaptive_feature_diag.get('aggregate_removed_counts_by_active_regime_flag'))}`",
                f"- aggregate_passed_counts_by_active_regime_flag: `{self._top_n_items(adaptive_feature_diag.get('aggregate_passed_counts_by_active_regime_flag'))}`",
                f"- conditional_regime_filter_status: `{adaptive_feature_diag.get('conditional_regime_filter_status')}`",
                f"- aggregate_conditional_regime_rule_counts: `{self._top_n_items(adaptive_feature_diag.get('aggregate_conditional_regime_rule_counts'))}`",
                f"- aggregate_conditional_regime_rule_eligible_counts: `{self._top_n_items(adaptive_feature_diag.get('aggregate_conditional_regime_rule_eligible_counts'))}`",
                f"- aggregate_conditional_regime_rule_passed_counts: `{self._top_n_items(adaptive_feature_diag.get('aggregate_conditional_regime_rule_passed_counts'))}`",
                f"- aggregate_conditional_regime_rule_counts_by_primary_regime: `{self._top_n_items(adaptive_feature_diag.get('aggregate_conditional_regime_rule_counts_by_primary_regime'))}`",
                f"- aggregate_conditional_regime_rule_counts_by_active_flag: `{self._top_n_items(adaptive_feature_diag.get('aggregate_conditional_regime_rule_counts_by_active_flag'))}`",
                f"- aggregate_conditional_regime_rule_metric_failure_counts: `{self._top_n_items(adaptive_feature_diag.get('aggregate_conditional_regime_rule_metric_failure_counts'))}`",
                f"- aggregate_conditional_regime_rule_metric_logic: `{self._top_n_items(adaptive_feature_diag.get('aggregate_conditional_regime_rule_metric_logic'))}`",
                f"- aggregate_conditional_regime_rule_required_metric_failure_count: `{self._top_n_items(adaptive_feature_diag.get('aggregate_conditional_regime_rule_required_metric_failure_count'))}`",
                f"- aggregate_conditional_regime_rule_metric_condition_count: `{self._top_n_items(adaptive_feature_diag.get('aggregate_conditional_regime_rule_metric_condition_count'))}`",
                f"- aggregate_conditional_regime_metric_overlap_board: `{self._as_list(adaptive_feature_diag.get('aggregate_conditional_regime_metric_overlap_board'))[:3]}`",
                f"- aggregate_conditional_regime_rule_metric_failure_count_distribution_by_rule: `{adaptive_feature_diag.get('aggregate_conditional_regime_rule_metric_failure_count_distribution_by_rule')}`",
                f"- aggregate_conditional_regime_rule_observed_metric_failure_counts_by_rule: `{adaptive_feature_diag.get('aggregate_conditional_regime_rule_observed_metric_failure_counts_by_rule')}`",
                f"- aggregate_conditional_regime_rule_metric_pair_failure_counts_by_rule: `{adaptive_feature_diag.get('aggregate_conditional_regime_rule_metric_pair_failure_counts_by_rule')}`",
                f"- aggregate_conditional_regime_rule_removed_outcome_by_rule: `{self._top_n_items(adaptive_feature_diag.get('aggregate_conditional_regime_rule_removed_outcome_by_rule'))}`",
                f"- aggregate_conditional_regime_rule_passed_outcome_by_rule: `{self._top_n_items(adaptive_feature_diag.get('aggregate_conditional_regime_rule_passed_outcome_by_rule'))}`",
                f"- aggregate_conditional_regime_ablation_board: `{self._as_list(adaptive_feature_diag.get('aggregate_conditional_regime_ablation_board'))[:3]}`",
                f"- aggregate_per_regime_contribution_board: `{self._as_list(adaptive_feature_diag.get('aggregate_per_regime_contribution_board'))[:3]}`",
                f"- aggregate_missing_feature_counts: `{self._top_n_items(adaptive_feature_diag.get('aggregate_missing_feature_counts'))}`",
                f"- recommended_next_stage: `{adaptive_probe.get('recommended_next_stage')}`",
            ]
        )
        if (
            adaptive_feature_diag.get("readiness") == "DIAGNOSTICS_READY"
            and not self._as_dict(adaptive_feature_diag.get("aggregate_removed_counts_by_date"))
        ):
            lines.append(
                "- warning: `feature_filter_aggregate_date_counts_missing`"
            )
        if (
            adaptive_feature_diag.get("readiness") == "DIAGNOSTICS_READY"
            and not self._as_dict(adaptive_feature_diag.get("aggregate_missing_feature_counts"))
        ):
            lines.append(
                "- warning: `feature_filter_aggregate_missing_feature_counts_missing`"
            )
        if adaptive_feature_diag.get("regime_propagation_status") == "MARKET_REGIME_MISSING":
            lines.append("- warning: `market_regime_still_missing_after_ml38_10_30`")
        if adaptive_feature_diag.get("missing_market_regime_count", 0) > 0:
            lines.append("- warning: `market_regime_partially_missing_after_ml38_10_30`")
        if adaptive_feature_diag.get("regime_propagation_status") == "MARKET_REGIME_PROPAGATED":
            lines.append("- market regime propagation: `MARKET_REGIME_PROPAGATED`")
        if adaptive_feature_diag.get("conditional_regime_filter_status") == "CONDITIONAL_REGIME_FILTER_ACTIVE":
            lines.append("- conditional regime filter: `ACTIVE`")
        if adaptive_feature_diag.get("conditional_regime_filter_status") == "HARD_REGIME_FILTER_OR_NON_CONDITIONAL_ONLY":
            lines.append("- warning: `conditional_regime_filter_not_active`")
        lines.extend(
            [
                "",
                "### ML38.10.32 Conditional regime ablation board",
                "",
                "| Rule id | Metric logic | Eligible | Removed | Passed | Removal rate | Required metric failures | Metric condition count | Removed total R | Passed total R | Effect | Metric failure counts |",
                "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
            ]
        )
        ablation_board = self._as_list(
            adaptive_feature_diag.get("aggregate_conditional_regime_ablation_board")
        )[:10]
        for row in ablation_board:
            board_row = self._as_dict(row)
            removed_outcome = self._as_dict(board_row.get("removed_outcome"))
            passed_outcome = self._as_dict(board_row.get("passed_outcome"))
            lines.append(
                "| `{rule_id}` | `{metric_logic}` | `{eligible}` | `{removed}` | `{passed}` | `{removal_rate}` | `{required_metric_failure_count}` | `{metric_condition_count}` | `{removed_total_r}` | `{passed_total_r}` | `{effect}` | `{metric_failures}` |".format(
                    rule_id=board_row.get("rule_id"),
                    metric_logic=board_row.get("metric_logic"),
                    eligible=board_row.get("eligible_count"),
                    removed=board_row.get("removed_count"),
                    passed=board_row.get("passed_count"),
                    removal_rate=board_row.get("removal_rate"),
                    required_metric_failure_count=board_row.get(
                        "required_metric_failure_count"
                    ),
                    metric_condition_count=board_row.get("metric_condition_count"),
                    removed_total_r=removed_outcome.get("total_r"),
                    passed_total_r=passed_outcome.get("total_r"),
                    effect=board_row.get("effect_label"),
                    metric_failures=board_row.get("metric_failure_counts"),
                )
            )
        if not ablation_board:
            lines.append(
                "| `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` |"
            )
        lines.extend(
            [
                "",
                "### ML38.10.34 Metric-overlap board",
                "",
                "| Rule id | Metric logic | Eligible | Actual removed | Required metric failures | Metric condition count | failed_0 | failed_1 | failed_2_plus | Status | Bottleneck |",
                "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
            ]
        )
        overlap_board = self._as_list(
            adaptive_feature_diag.get("aggregate_conditional_regime_metric_overlap_board")
        )[:10]
        for row in overlap_board:
            board_row = self._as_dict(row)
            lines.append(
                "| `{rule_id}` | `{metric_logic}` | `{eligible}` | `{removed}` | `{required_metric_failure_count}` | `{metric_condition_count}` | `{failed_0}` | `{failed_1}` | `{failed_2_plus}` | `{status}` | `{bottleneck}` |".format(
                    rule_id=board_row.get("rule_id"),
                    metric_logic=board_row.get("metric_logic"),
                    eligible=board_row.get("eligible_count"),
                    removed=board_row.get("actual_removed_count"),
                    required_metric_failure_count=board_row.get(
                        "required_metric_failure_count"
                    ),
                    metric_condition_count=board_row.get("metric_condition_count"),
                    failed_0=board_row.get("failed_0_count"),
                    failed_1=board_row.get("failed_1_count"),
                    failed_2_plus=board_row.get("failed_2_plus_count"),
                    status=board_row.get("metric_overlap_status"),
                    bottleneck=board_row.get("bottleneck_label"),
                )
            )
        if not overlap_board:
            lines.append(
                "| `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` |"
            )
        lines.extend(
            [
                "",
                "### ML38.10.32 Per-regime contribution board",
                "",
                "| Market regime | Removed signals | Removed total R | Passed signals | Passed total R | Effect |",
                "| --- | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        contribution_board = self._as_list(
            adaptive_feature_diag.get("aggregate_per_regime_contribution_board")
        )[:10]
        for row in contribution_board:
            board_row = self._as_dict(row)
            removed_outcome = self._as_dict(board_row.get("removed_outcome"))
            passed_outcome = self._as_dict(board_row.get("passed_outcome"))
            lines.append(
                "| `{market_regime}` | `{removed_signal_count}` | `{removed_total_r}` | `{passed_signal_count}` | `{passed_total_r}` | `{effect}` |".format(
                    market_regime=board_row.get("market_regime"),
                    removed_signal_count=removed_outcome.get("signal_count"),
                    removed_total_r=removed_outcome.get("total_r"),
                    passed_signal_count=passed_outcome.get("signal_count"),
                    passed_total_r=passed_outcome.get("total_r"),
                    effect=board_row.get("effect_label"),
                )
            )
        if not contribution_board:
            lines.append("| `-` | `-` | `-` | `-` | `-` | `-` |")
        lines.extend(
            [
                "",
                "## Recommendations",
                "",
            ]
        )
        for recommendation in self._as_list(payload.get("recommendations")):
            lines.append(f"- {recommendation}")

        lines.extend(
            [
                "",
                "## Safety",
                "",
                "- approved_for_live_trading: `False`",
                "- approved_for_auto_activation: `False`",
                "- orders_enabled: `False`",
                "- traders_core_connected: `False`",
                "",
            ]
        )
        lines.extend(
            [
                "",
                "## Entry-Path / Stop-Pressure Audit",
                "",
                "| Symbol | Best config | Enabled | EPQ threshold | Stop threshold | MAE threshold | Original | Filtered | Blocked | Stream OK | Stop status |",
                "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
            ]
        )
        for item in self._as_list(payload.get("symbol_results")):
            stop_audit = self._as_dict(item.get("stop_pressure_effectiveness_audit"))
            lines.append(
                "| `{symbol}` | `{config}` | `{enabled}` | `{epq}` | `{stop}` | `{original}` | `{filtered}` | `{blocked}` | `{consistent}` | `{status}` |".format(
                    symbol=item.get("symbol"),
                    config=item.get("best_candidate_config_id"),
                    enabled=item.get("entry_path_quality_filter_enabled"),
                    epq=item.get("entry_path_quality_min_threshold"),
                    stop=item.get("stop_pressure_max_risk_score"),
                    mae=item.get("mae_pressure_max_risk_score"),
                    original=item.get("entry_path_final_signal_original_count"),
                    filtered=item.get("entry_path_final_signal_filtered_count"),
                    blocked=item.get("entry_path_final_signal_blocked_count"),
                    consistent=item.get("entry_path_stream_consistency_ok"),
                    status=stop_audit.get("status"),
                )
            )
        if not self._as_list(payload.get("symbol_results")):
            lines.append("| `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` |")
        lines.extend(
            [
                "",
                "## Directional Side Audit",
                "",
            ]
        )
        for item in self._as_list(payload.get("symbol_results")):
            lines.append(f"### {item.get('symbol')}")
            lines.append(f"- side_filter_profile: `{item.get('directional_side_filter_profile')}`")
            lines.append(f"- allowed_signal_directions: `{item.get('allowed_signal_directions')}`")
            lines.append(
                f"- validation_gate_failure_reason_counts: `{item.get('validation_gate_failure_reason_counts')}`"
            )
            lines.append(
                f"- side_aware_relaxed_fold_count: `{item.get('side_aware_relaxed_fold_count')}`"
            )
            lines.append(f"- direction_balance_ratio: `{item.get('direction_balance_ratio')}`")
            lines.append(f"- long_total_r: `{item.get('long_total_r')}`")
            lines.append(f"- short_total_r: `{item.get('short_total_r')}`")
        if not self._as_list(payload.get("symbol_results")):
            lines.append("- side_filter_profile: `None`")
        comparator = self._as_dict(payload.get("directional_side_ablation_comparator"))
        best_by_profile = self._as_dict(comparator.get("best_by_side_profile"))
        lines.extend(
            [
                "",
                "## Directional side ablation comparator",
                "",
                f"- diagnostic_status: `{comparator.get('diagnostic_status')}`",
                f"- side_profile_counts: `{comparator.get('side_profile_counts')}`",
                f"- best LONG_ONLY: `{self._as_dict(best_by_profile.get('LONG_ONLY'))}`",
                f"- best SHORT_ONLY: `{self._as_dict(best_by_profile.get('SHORT_ONLY'))}`",
                f"- best SUPPRESS_SHORT: `{self._as_dict(best_by_profile.get('SUPPRESS_SHORT'))}`",
                f"- best BOTH_DIRECTIONS: `{self._as_dict(best_by_profile.get('BOTH_DIRECTIONS'))}`",
                f"- long_only_vs_both_delta: `{comparator.get('long_only_vs_both_delta')}`",
                f"- short_only_vs_both_delta: `{comparator.get('short_only_vs_both_delta')}`",
                f"- suppress_short_vs_both_delta: `{comparator.get('suppress_short_vs_both_delta')}`",
                f"- warnings: `{comparator.get('warnings')}`",
                f"- recommendations: `{comparator.get('recommendations')}`",
                "",
                "| Side profile | Config | PF | Total R | WF PF | WF R | Signals | Long R | Short R |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for row in self._as_list(comparator.get("comparison_board")):
            lines.append(
                "| `{side}` | `{config}` | `{pf}` | `{total_r}` | `{wf_pf}` | `{wf_r}` | `{signals}` | `{long_r}` | `{short_r}` |".format(
                    side=row.get("side_profile"),
                    config=row.get("config_id"),
                    pf=row.get("profit_factor"),
                    total_r=row.get("profit_total_r"),
                    wf_pf=row.get("walk_forward_profit_factor"),
                    wf_r=row.get("walk_forward_total_r"),
                    signals=row.get("resolved_signal_count"),
                    long_r=row.get("long_total_r"),
                    short_r=row.get("short_total_r"),
                )
            )
        if not self._as_list(comparator.get("comparison_board")):
            lines.append("| `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` |")
        stability = self._as_dict(payload.get("directional_side_walk_forward_stability"))
        stability_by_profile = self._as_dict(stability.get("stability_by_side_profile"))
        lines.extend(
            [
                "",
                "## Directional side walk-forward stability",
                "",
                f"- diagnostic_status: `{stability.get('diagnostic_status')}`",
                f"- side_profile_counts: `{stability.get('side_profile_counts')}`",
                f"- best_research_side_profile: `{stability.get('best_research_side_profile')}`",
                f"- best_research_verdict: `{stability.get('best_research_verdict')}`",
                f"- long_only_best: `{self._as_dict(stability_by_profile.get('LONG_ONLY'))}`",
                f"- short_only_best: `{self._as_dict(stability_by_profile.get('SHORT_ONLY'))}`",
                f"- suppress_short_best: `{self._as_dict(stability_by_profile.get('SUPPRESS_SHORT'))}`",
                f"- both_directions_best: `{self._as_dict(stability_by_profile.get('BOTH_DIRECTIONS'))}`",
                f"- long_only_vs_both_stability_delta: `{stability.get('long_only_vs_both_stability_delta')}`",
                f"- suppress_short_vs_both_stability_delta: `{stability.get('suppress_short_vs_both_stability_delta')}`",
                f"- warnings: `{stability.get('warnings')}`",
                f"- recommendations: `{stability.get('recommendations')}`",
                "",
                "| Side profile | Config | Verdict | WF PF | WF R | WF signals | Low folds | Zero folds | Test PF | Test R |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for row in self._as_list(stability.get("comparison_board")):
            lines.append(
                "| `{side}` | `{config}` | `{verdict}` | `{wf_pf}` | `{wf_r}` | `{wf_signals}` | `{low}` | `{zero}` | `{pf}` | `{total_r}` |".format(
                    side=row.get("side_profile"),
                    config=row.get("config_id"),
                    verdict=row.get("walk_forward_stability_verdict"),
                    wf_pf=row.get("walk_forward_profit_factor"),
                    wf_r=row.get("walk_forward_total_r"),
                    wf_signals=row.get("total_walk_forward_resolved_signal_count"),
                    low=row.get("low_signal_fold_count"),
                    zero=row.get("zero_signal_fold_count"),
                    pf=row.get("profit_factor"),
                    total_r=row.get("profit_total_r"),
                )
            )
        if not self._as_list(stability.get("comparison_board")):
            lines.append("| `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` |")
        recovery_summary = self._as_dict(payload.get("directional_side_signal_recovery_summary"))
        validation_board_summary = self._as_dict(
            payload.get("walk_forward_validation_candidate_board_summary")
        )
        lines.extend(
            [
                "",
                "## Directional side signal recovery",
                "",
                f"- status_counts: `{recovery_summary.get('status_counts')}`",
                f"- verdict_counts: `{recovery_summary.get('verdict_counts')}`",
                "",
                "### ML38.10.24 validation gate diagnostics",
                f"- validation gate failure reasons: `{payload.get('validation_gate_failure_reason_counts')}`",
                f"- side-aware relaxed folds: `{payload.get('side_aware_relaxed_fold_count')}`",
                "",
                "## Walk-forward validation candidate board / total-R repair",
                "",
                f"- summary: `{validation_board_summary}`",
                f"- repair profile counts: `{validation_board_summary.get('recommended_validation_repair_profile_counts')}`",
                f"- best_total_r_repair_probe: `{validation_board_summary.get('best_total_r_repair_probe')}`",
                "",
                "| Symbol | Config | Side profile | PF | Total R | WF PF | WF R | Recommended repair | Total-R folds | Median deficit | Research-only blocked |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
                "",
                "| Symbol | Config | Side recovery status | Side recovery verdict | Primary signal loss reason counts | Gate fail reasons | Relaxed folds |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for row in self._as_list(payload.get("configs_ranked"))[:10]:
            lines.append(
                "| `{symbol}` | `{config}` | `{side}` | `{pf}` | `{total_r}` | `{wf_pf}` | `{wf_r}` | `{repair}` | `{folds}` | `{median}` | `{blocked}` |".format(
                    symbol=row.get("symbol"),
                    config=row.get("config_id"),
                    side=row.get("directional_side_filter_profile"),
                    pf=row.get("profit_factor"),
                    total_r=row.get("profit_total_r"),
                    wf_pf=row.get("walk_forward_profit_factor"),
                    wf_r=row.get("walk_forward_total_r", row.get("walk_forward_global_total_r")),
                    repair=row.get("recommended_validation_repair_profile"),
                    folds=row.get("total_r_below_min_fold_count"),
                    median=row.get("median_best_total_r_deficit"),
                    blocked=row.get("research_only_total_r_repair_enabled"),
                )
            )
        if not self._as_list(payload.get("configs_ranked")):
            lines.append("| `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` |")
        for row in self._as_list(payload.get("configs_ranked"))[:10]:
            lines.append(
                "| `{symbol}` | `{config}` | `{status}` | `{verdict}` | `{reasons}` | `{gate_fail}` | `{relaxed}` |".format(
                    symbol=row.get("symbol"),
                    config=row.get("config_id"),
                    status=row.get("directional_side_signal_recovery_status"),
                    verdict=row.get("directional_side_signal_recovery_verdict"),
                    reasons=row.get("primary_signal_loss_reason_counts"),
                    gate_fail=row.get("validation_gate_failure_reason_counts"),
                    relaxed=row.get("side_aware_relaxed_fold_count"),
                )
            )
        if not self._as_list(payload.get("configs_ranked")):
            lines.append("| `-` | `-` | `-` | `-` | `-` | `-` | `-` |")
        root_cause_board = self._as_dict(payload.get("walk_forward_fold_root_cause_board"))
        lines.extend(
            [
                "",
                "## ML38.10.26 Walk-forward fold root cause board",
                "",
                f"- candidate_count_with_root_cause: `{root_cause_board.get('candidate_count_with_root_cause')}`",
                f"- primary_root_cause_counts: `{root_cause_board.get('primary_root_cause_counts')}`",
                f"- worst fold: `{self._as_list(root_cause_board.get('worst_candidates'))[:1]}`",
                f"- recommendation: `{root_cause_board.get('recommendations')}`",
                "",
                "| Symbol | Config | Candidate | Validation R | Primary root cause | Root cause flags | Repair profile | PF | Total R | WF PF | WF R |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for row in self._as_list(root_cause_board.get("worst_candidates"))[:10]:
            lines.append(
                "| `{symbol}` | `{config}` | `{candidate}` | `{validation_r}` | `{primary}` | `{flags}` | `{repair}` | `{pf}` | `{total_r}` | `{wf_pf}` | `{wf_r}` |".format(
                    symbol=row.get("symbol"),
                    config=row.get("config_id"),
                    candidate=row.get("candidate_id"),
                    validation_r=row.get("validation_total_r"),
                    primary=row.get("primary_root_cause"),
                    flags=row.get("root_cause_flags"),
                    repair=row.get("recommended_validation_repair_profile"),
                    pf=row.get("profit_factor"),
                    total_r=row.get("profit_total_r"),
                    wf_pf=row.get("walk_forward_profit_factor"),
                    wf_r=row.get("walk_forward_total_r"),
                )
            )
        if not self._as_list(root_cause_board.get("worst_candidates")):
            lines.append("| `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` |")
        repair_selection = self._as_dict(payload.get("fold_1_repair_target_selection"))
        lines.extend(
            [
                "",
                "## ML38.10.26.3 Fold-1 repair target selection",
                "",
                f"- selected_target_count: `{repair_selection.get('selected_target_count')}`",
                f"- primary_root_cause_counts: `{repair_selection.get('primary_root_cause_counts')}`",
                f"- bad_time_slice_counts: `{repair_selection.get('bad_time_slice_counts')}`",
                f"- outcome_counts: `{repair_selection.get('outcome_counts')}`",
                f"- recommended_next_stage: `{repair_selection.get('recommended_next_stage')}`",
                f"- warnings: `{repair_selection.get('warnings')}`",
                f"- recommendations: `{repair_selection.get('recommendations')}`",
                "",
                "| Symbol | Config | Side profile | Fold | Validation R | Signals | Losses | Primary root cause | Bad time slices | Repair actions | PF | Total R | WF PF | WF R |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for row in self._as_list(repair_selection.get("selected_targets"))[:10]:
            lines.append(
                "| `{symbol}` | `{config}` | `{profile}` | `{fold}` | `{val_r}` | `{signals}` | `{losses}` | `{primary}` | `{bad_slices}` | `{actions}` | `{pf}` | `{total_r}` | `{wf_pf}` | `{wf_r}` |".format(
                    symbol=row.get("symbol"),
                    config=row.get("config_id"),
                    profile=row.get("side_profile"),
                    fold=row.get("fold_index"),
                    val_r=row.get("validation_total_r"),
                    signals=row.get("validation_signal_count"),
                    losses=row.get("validation_loss_count"),
                    primary=row.get("primary_root_cause"),
                    bad_slices=row.get("top_bad_time_slices"),
                    actions=row.get("recommended_repair_actions"),
                    pf=row.get("profit_factor"),
                    total_r=row.get("profit_total_r"),
                    wf_pf=row.get("walk_forward_profit_factor"),
                    wf_r=row.get("walk_forward_total_r"),
                )
            )
        if not self._as_list(repair_selection.get("selected_targets")):
            lines.append("| `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` |")
        fold_repair_probe = self._as_dict(payload.get("fold_time_slice_exit_repair_probe"))
        lines.extend(
            [
                "",
                "## ML38.10.27 Fold-1 Time-Slice / Exit-Mitigation Repair Probe",
                "",
                f"- verdict: `{fold_repair_probe.get('verdict')}`",
                f"- probe_candidate_count: `{fold_repair_probe.get('probe_candidate_count')}`",
                f"- profile_counts: `{fold_repair_probe.get('profile_counts')}`",
                f"- target_date_counts: `{fold_repair_probe.get('target_date_counts')}`",
                f"- warnings: `{fold_repair_probe.get('warnings')}`",
                f"- recommendations: `{fold_repair_probe.get('recommendations')}`",
                "",
                "| Symbol | Config | Profile | PF | Total R | WF PF | WF R | Blackout | Removed | Root cause |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for row in self._as_list(fold_repair_probe.get("best_by_walk_forward_total_r"))[:10]:
            lines.append(
                "| `{symbol}` | `{config}` | `{profile}` | `{pf}` | `{total_r}` | `{wf_pf}` | `{wf_r}` | `{blackout}` | `{removed}` | `{root}` |".format(
                    symbol=row.get("symbol"),
                    config=row.get("config_id"),
                    profile=row.get("fold_repair_probe_profile"),
                    pf=row.get("profit_factor"),
                    total_r=row.get("profit_total_r"),
                    wf_pf=row.get("walk_forward_profit_factor"),
                    wf_r=row.get("walk_forward_total_r"),
                    blackout=row.get("fold_repair_time_slice_blackout_enabled"),
                    removed=row.get("removed_signal_count"),
                    root=row.get("primary_root_cause"),
                )
            )
        if not self._as_list(fold_repair_probe.get("best_by_walk_forward_total_r")):
            lines.append("| `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` |")
        fold_feature_probe = self._as_dict(payload.get("fold_feature_regime_repair_probe"))
        best_feature_probe = self._as_dict(fold_feature_probe.get("best_feature_regime_probe"))
        best_date_probe = self._as_dict(fold_feature_probe.get("best_date_blackout_probe"))
        lines.extend(
            [
                "",
                "## ML38.10.28 Feature/regime fold repair probe",
                "",
                f"- diagnostic_status: `{fold_feature_probe.get('diagnostic_status')}`",
                f"- verdict: `{fold_feature_probe.get('verdict')}`",
                f"- feature_regime_probe_candidate_count: `{fold_feature_probe.get('feature_regime_probe_candidate_count')}`",
                f"- date_blackout_probe_candidate_count: `{fold_feature_probe.get('date_blackout_probe_candidate_count')}`",
                f"- best_feature_regime_probe: `{best_feature_probe}`",
                f"- best_date_blackout_probe: `{best_date_probe}`",
                f"- warnings: `{fold_feature_probe.get('warnings')}`",
                f"- recommended_next_stage: `{fold_feature_probe.get('recommended_next_stage')}`",
                "",
                "| Probe type | Config | PF | Total R | WF PF | WF R | Removed | Profile |",
                "| --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for probe_type, row in (
            ("feature_regime", best_feature_probe),
            ("date_blackout", best_date_probe),
        ):
            if not row:
                continue
            removed_summary = self._as_dict(
                row.get("fold_feature_regime_filter_summary")
                or row.get("fold_time_slice_blackout_summary")
            )
            lines.append(
                "| `{probe}` | `{config}` | `{pf}` | `{total_r}` | `{wf_pf}` | `{wf_r}` | `{removed}` | `{profile}` |".format(
                    probe=probe_type,
                    config=row.get("config_id"),
                    pf=row.get("profit_factor"),
                    total_r=row.get("profit_total_r"),
                    wf_pf=row.get("walk_forward_profit_factor"),
                    wf_r=row.get("walk_forward_total_r"),
                    removed=removed_summary.get("removed_signal_count"),
                    profile=row.get("fold_repair_feature_filter_profile")
                    or row.get("fold_repair_probe_profile"),
                )
            )
        if not best_feature_probe and not best_date_probe:
            lines.append("| `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` |")
        return "\n".join(lines)
