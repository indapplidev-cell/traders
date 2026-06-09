from __future__ import annotations

from typing import Any


class PredictionCollapseDetector:
    def detect(self, probability_report: dict[str, Any]) -> dict[str, Any]:
        predicted_ratios = probability_report.get("predicted_direction_ratios", {})
        dominant_class = max(predicted_ratios, key=predicted_ratios.get, default="FLAT")
        dominant_class_ratio = float(predicted_ratios.get(dominant_class, 0.0))
        rows_above_045 = self._rows_above_threshold(probability_report, 0.45)
        avg_prob_flat = float(probability_report.get("avg_prob_flat", 0.0))
        avg_prob_up = float(probability_report.get("avg_prob_up", 0.0))
        avg_prob_down = float(probability_report.get("avg_prob_down", 0.0))
        margin_q90 = float(probability_report.get("margin_q90", 0.0) or 0.0)

        dominant_class_collapse = dominant_class_ratio >= 0.90
        no_signal_confidence_collapse = rows_above_045 == 0
        low_margin_collapse = margin_q90 < 0.05
        flat_dominance_warning = avg_prob_flat > avg_prob_up and avg_prob_flat > avg_prob_down
        directional_bias_warning = predicted_ratios.get("UP", 0.0) >= 0.80 or predicted_ratios.get("DOWN", 0.0) >= 0.80

        warnings: list[str] = []
        if dominant_class_collapse:
            warnings.append("dominant_class_collapse")
        if no_signal_confidence_collapse:
            warnings.append("no_signal_confidence_collapse")
        if low_margin_collapse:
            warnings.append("low_margin_collapse")
        if flat_dominance_warning:
            warnings.append("flat_dominance_warning")
        if directional_bias_warning:
            warnings.append("directional_bias_warning")

        return {
            "collapse_detected": dominant_class_collapse or no_signal_confidence_collapse or low_margin_collapse,
            "warnings": warnings,
            "dominant_class": dominant_class,
            "dominant_class_ratio": dominant_class_ratio,
            "dominant_class_collapse": dominant_class_collapse,
            "no_signal_confidence_collapse": no_signal_confidence_collapse,
            "low_margin_collapse": low_margin_collapse,
            "flat_dominance_warning": flat_dominance_warning,
            "directional_bias_warning": directional_bias_warning,
            "rows_above_0_45": rows_above_045,
        }

    @staticmethod
    def _rows_above_threshold(probability_report: dict[str, Any], threshold: float) -> int:
        for row in probability_report.get("top_class_by_threshold", []):
            if abs(float(row.get("threshold", -1.0)) - threshold) < 1e-9:
                return int(row.get("rows_above_threshold", 0))
        return int(probability_report.get("rows_above_thresholds", {}).get(f"{threshold:.2f}", 0))
