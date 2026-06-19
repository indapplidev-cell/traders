from __future__ import annotations

from collections import defaultdict
from typing import Any, Sequence

from app.diagnostics._book_audit_utils import (
    distribution,
    distribution_counts,
    get_mapping,
    label_from_row,
    majority_accuracy,
    predicted_label_from_row,
    safe_float,
)


class SetupContextAudit:
    diagnostic_name = "setup_context_audit"
    diagnostic_version = "ml38_9_7"

    def evaluate(self, rows: Sequence[Any]) -> dict[str, Any]:
        if not rows:
            return self._empty_payload()

        grouped_rows: dict[str, list[Any]] = defaultdict(list)
        for row in rows:
            for group_name in self._groups_for_row(row):
                grouped_rows[group_name].append(row)

        groups_payload: dict[str, Any] = {}
        positive_edge_groups: list[str] = []
        negative_edge_groups: list[str] = []
        collapse_groups: list[str] = []

        for group_name, group_rows in grouped_rows.items():
            stats = self._group_stats(group_rows)
            groups_payload[group_name] = stats
            baseline_edge = stats.get("baseline_edge")
            if baseline_edge is not None and baseline_edge > 0.0:
                positive_edge_groups.append(group_name)
            if baseline_edge is not None and baseline_edge < 0.0:
                negative_edge_groups.append(group_name)
            if stats.get("collapse_severity") in {"WATCH", "CRITICAL"}:
                collapse_groups.append(group_name)

        dangerous_groups = sorted(
            groups_payload.items(),
            key=lambda item: (
                item[1].get("collapse_severity") == "CRITICAL",
                item[1].get("baseline_edge") is not None and item[1].get("baseline_edge") < 0.0,
                item[1]["row_count"],
            ),
            reverse=True,
        )[:5]
        best_groups = sorted(
            groups_payload.items(),
            key=lambda item: float(item[1].get("baseline_edge") or -999.0),
            reverse=True,
        )[:5]

        schwager_flags: list[str] = []
        if len(positive_edge_groups) == 1 and len(groups_payload) > 1:
            schwager_flags.append("edge_in_one_slice_only")
        if positive_edge_groups and negative_edge_groups:
            schwager_flags.append("unstable_by_regime")
        if negative_edge_groups:
            schwager_flags.append("negative_edge_context")

        return {
            "diagnostic_name": self.diagnostic_name,
            "diagnostic_version": self.diagnostic_version,
            "row_count": len(rows),
            "setup_group_count": len(groups_payload),
            "groups": groups_payload,
            "groups_with_positive_edge": positive_edge_groups,
            "groups_with_negative_edge": negative_edge_groups,
            "groups_with_collapse": collapse_groups,
            "best_candidate_setup_groups": [name for name, _stats in best_groups],
            "dangerous_setup_groups": [name for name, _stats in dangerous_groups],
            "schwager_context_flags": schwager_flags,
        }

    def _group_stats(self, rows: Sequence[Any]) -> dict[str, Any]:
        actual_labels = [label_from_row(row) or "FLAT" for row in rows]
        predicted_labels = [predicted_label_from_row(row) for row in rows]
        predicted_available = all(label is not None for label in predicted_labels) and bool(predicted_labels)
        model_accuracy = None
        predicted_distribution = None
        baseline_accuracy = majority_accuracy(actual_labels)
        baseline_edge = None
        collapse_severity = None
        warnings: list[str] = []

        if predicted_available:
            normalized_predictions = [label for label in predicted_labels if label is not None]
            predicted_distribution = distribution(normalized_predictions)
            matches = sum(
                int(actual == predicted)
                for actual, predicted in zip(actual_labels, normalized_predictions)
            )
            model_accuracy = matches / len(rows) if rows else None
            if baseline_accuracy is not None and model_accuracy is not None:
                baseline_edge = round(model_accuracy - baseline_accuracy, 6)
            dominant_prediction = max(predicted_distribution.values()) if predicted_distribution else 0.0
            dominant_actual = max(distribution(actual_labels).values()) if actual_labels else 0.0
            if dominant_prediction >= 0.85 and dominant_actual <= 0.6:
                collapse_severity = "CRITICAL"
                warnings.append("predicted_distribution_collapsed")
            elif dominant_prediction >= 0.7 and model_accuracy is not None and baseline_accuracy is not None and model_accuracy <= baseline_accuracy:
                collapse_severity = "WATCH"
                warnings.append("group_edge_not_confirmed")
            else:
                collapse_severity = "OK"

        if len(rows) < 10:
            warnings.append("low_group_sample_size")
        if baseline_edge is not None and baseline_edge < 0.0:
            warnings.append("negative_edge_context")

        return {
            "row_count": len(rows),
            "actual_distribution": distribution_counts(actual_labels),
            "predicted_distribution": predicted_distribution,
            "model_accuracy": None if model_accuracy is None else round(model_accuracy, 6),
            "baseline_accuracy": None if baseline_accuracy is None else round(baseline_accuracy, 6),
            "baseline_edge": baseline_edge,
            "collapse_severity": collapse_severity,
            "top_warnings": warnings[:5],
        }

    def _groups_for_row(self, row: Any) -> list[str]:
        features = get_mapping(row, "features_json", "features", "feature_values")
        if not features:
            return []
        groups: list[str] = []
        trend_strength = safe_float(features.get("trend_strength"), 0.0) or 0.0
        volume_ratio = safe_float(features.get("volume_ratio_20", features.get("volume_ratio")), 1.0) or 1.0
        rsi = safe_float(features.get("rsi_14", features.get("rsi")), 50.0) or 50.0
        doji_score = safe_float(features.get("doji_score", features.get("candle_body_ratio")), 0.0) or 0.0
        hammer_score = safe_float(features.get("hammer_score"), 0.0) or 0.0
        shooting_star_score = safe_float(features.get("shooting_star_score"), 0.0) or 0.0
        engulfing_score = safe_float(features.get("engulfing_score"), 0.0) or 0.0
        breakout_strength = safe_float(features.get("breakout_strength"), 0.0) or 0.0
        near_support = bool(features.get("near_support")) or (safe_float(features.get("support_distance_atr")) or 9.0) <= 0.35
        near_resistance = bool(features.get("near_resistance")) or (safe_float(features.get("resistance_distance_atr")) or 9.0) <= 0.35
        range_bias = bool(features.get("regime_range")) or abs(trend_strength) <= 0.2

        if abs(doji_score) <= 0.15 or doji_score >= 0.7:
            groups.append("nison_indecision_doji")
        if hammer_score >= 0.5 or shooting_star_score >= 0.5 or engulfing_score >= 0.5:
            if near_support or near_resistance or abs(trend_strength) >= 0.4:
                groups.append("nison_reversal_candidate")
            else:
                groups.append("nison_confirmation_required")
        if abs(trend_strength) >= 0.6 and breakout_strength >= 0.25:
            groups.append("nison_continuation_candidate")
        if (hammer_score >= 0.4 or shooting_star_score >= 0.4) and not (near_support or near_resistance):
            groups.append("nison_context_invalid")

        if abs(trend_strength) >= 0.7 and volume_ratio >= 1.0:
            groups.append("trend_continuation")
        if abs(trend_strength) >= 0.45 and 40.0 <= rsi <= 60.0:
            groups.append("trend_pullback")
        if abs(trend_strength) >= 0.6 and (rsi >= 70.0 or rsi <= 30.0):
            groups.append("trend_exhaustion")
        if range_bias:
            groups.append("range_chop")
        if near_support:
            groups.append("support_retest")
        if near_resistance:
            groups.append("resistance_rejection")
        if breakout_strength >= 0.4 and volume_ratio >= 1.2:
            groups.append("breakout_with_volume")
        if breakout_strength >= 0.4 and volume_ratio < 1.2:
            groups.append("breakout_without_volume")
        if breakout_strength >= 0.25 and volume_ratio < 1.0:
            groups.append("false_breakout_risk")
        if near_support or near_resistance:
            groups.append("near_support_or_resistance")
        return groups

    def _empty_payload(self) -> dict[str, Any]:
        return {
            "diagnostic_name": self.diagnostic_name,
            "diagnostic_version": self.diagnostic_version,
            "row_count": 0,
            "setup_group_count": 0,
            "groups": {},
            "groups_with_positive_edge": [],
            "groups_with_negative_edge": [],
            "groups_with_collapse": [],
            "best_candidate_setup_groups": [],
            "dangerous_setup_groups": [],
            "schwager_context_flags": [],
        }
