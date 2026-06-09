from __future__ import annotations

from typing import Any


class ModelVsBaselineComparator:
    def compare(
        self,
        model_version: str,
        feature_version: str,
        label_version: str,
        walk_forward_summary: dict[str, Any],
        baseline_name: str,
        baseline_summary: dict[str, Any],
    ) -> dict[str, Any]:
        model_global_total_r = float(walk_forward_summary.get("global_total_r", 0.0))
        model_global_profit_factor = walk_forward_summary.get("global_profit_factor")
        model_global_expectancy_r = walk_forward_summary.get("global_expectancy_r")
        model_signal_count = int(walk_forward_summary.get("total_test_signal_count", 0))
        model_long_count = int(walk_forward_summary.get("long_total_count", 0))
        model_short_count = int(walk_forward_summary.get("short_total_count", 0))
        dominant_class_ratio = float(walk_forward_summary.get("dominant_class_ratio_max", 0.0))
        baseline_global_total_r = float(baseline_summary.get("global_total_r", 0.0))
        baseline_global_profit_factor = baseline_summary.get("global_profit_factor")
        baseline_expectancy_r = baseline_summary.get("global_expectancy_r")

        model_beats_baseline_by_total_r = model_global_total_r > baseline_global_total_r
        model_beats_baseline_by_profit_factor = (
            model_global_profit_factor is not None
            and baseline_global_profit_factor is not None
            and float(model_global_profit_factor) > float(baseline_global_profit_factor)
        )
        model_has_both_directions = model_long_count > 0 and model_short_count > 0
        recommendation_allowed = bool(
            model_beats_baseline_by_total_r
            and model_beats_baseline_by_profit_factor
            and model_global_expectancy_r is not None
            and float(model_global_expectancy_r) > 0.0
            and model_signal_count >= 50
            and model_has_both_directions
            and dominant_class_ratio < 0.90
        )

        reject_reasons: list[str] = []
        if not model_beats_baseline_by_total_r:
            reject_reasons.append("model_total_r_not_above_baseline")
        if not model_beats_baseline_by_profit_factor:
            reject_reasons.append("model_profit_factor_not_above_baseline")
        if model_global_expectancy_r is None or float(model_global_expectancy_r) <= 0.0:
            reject_reasons.append("model_expectancy_not_positive")
        if model_signal_count < 50:
            reject_reasons.append("model_signal_count_lt_50")
        if model_long_count <= 0:
            reject_reasons.append("no_long_signals")
        if model_short_count <= 0:
            reject_reasons.append("no_short_signals")
        if dominant_class_ratio >= 0.90:
            reject_reasons.append("dominant_class_ratio_gte_0_90")

        return {
            "model_version": model_version,
            "feature_version": feature_version,
            "label_version": label_version,
            "model_global_total_r": model_global_total_r,
            "model_global_profit_factor": model_global_profit_factor,
            "model_global_expectancy_r": model_global_expectancy_r,
            "model_signal_count": model_signal_count,
            "model_long_count": model_long_count,
            "model_short_count": model_short_count,
            "dominant_class_ratio": dominant_class_ratio,
            "baseline_name": baseline_name,
            "baseline_global_total_r": baseline_global_total_r,
            "baseline_global_profit_factor": baseline_global_profit_factor,
            "baseline_expectancy_r": baseline_expectancy_r,
            "model_beats_baseline_by_total_r": model_beats_baseline_by_total_r,
            "model_beats_baseline_by_profit_factor": model_beats_baseline_by_profit_factor,
            "model_has_both_directions": model_has_both_directions,
            "recommendation_allowed": recommendation_allowed,
            "reject_reasons": reject_reasons,
        }
