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
        return "\n".join(lines)
