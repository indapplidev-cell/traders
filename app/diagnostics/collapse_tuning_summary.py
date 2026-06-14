from __future__ import annotations

from typing import Any


class CollapseTuningSummaryBuilder:
    DIAGNOSTIC_NAME = "collapse_tuning_summary"
    DIAGNOSTIC_VERSION = "ml38_2"

    def build(
        self,
        *,
        collapse_diagnostics: dict[str, Any],
        class_bias_diagnostics: dict[str, Any],
    ) -> dict[str, Any]:
        collapse = dict(collapse_diagnostics or {})
        bias = dict(class_bias_diagnostics or {})
        confidence = dict(collapse.get("confidence_distribution", {}))

        avg_probabilities = [
            self._safe_float(confidence.get("avg_prob_up")),
            self._safe_float(confidence.get("avg_prob_down")),
            self._safe_float(confidence.get("avg_prob_flat")),
        ]
        max_prob_q50 = self._safe_float(confidence.get("max_prob_q50"))
        max_prob_q90 = self._safe_float(confidence.get("max_prob_q90"))
        rows_above = dict(confidence.get("rows_above_thresholds", {}))

        collapse_detected = bool(collapse.get("collapse_detected", False))
        flat_bias_detected = bool(bias.get("flat_bias_detected", False))
        down_blindness_detected = bool(bias.get("down_blindness_detected", False))
        up_bias_detected = bool(bias.get("up_bias_detected", False))

        return {
            "diagnostic_name": self.DIAGNOSTIC_NAME,
            "diagnostic_version": self.DIAGNOSTIC_VERSION,
            "collapse_detected": collapse_detected,
            "collapse_type": self._collapse_type(
                collapse_detected=collapse_detected,
                flat_bias_detected=flat_bias_detected,
                down_blindness_detected=down_blindness_detected,
                up_bias_detected=up_bias_detected,
                collapse=collapse,
            ),
            "rows_above_0_45": int(rows_above.get("0.45", 0) or 0),
            "rows_above_0_50": int(rows_above.get("0.50", 0) or 0),
            "mean_confidence": max(avg_probabilities, default=0.0),
            "median_confidence": max_prob_q50,
            "confidence_p90": max_prob_q90,
            "dominant_class": collapse.get("dominant_class"),
            "dominant_class_ratio": self._safe_float(collapse.get("dominant_class_ratio")),
            "recommended_action": self._recommended_action(
                collapse_detected=collapse_detected,
                flat_bias_detected=flat_bias_detected,
                down_blindness_detected=down_blindness_detected,
                up_bias_detected=up_bias_detected,
                collapse=collapse,
            ),
        }

    @staticmethod
    def _safe_float(value: Any) -> float:
        if value is None:
            return 0.0
        numeric = float(value)
        if numeric == float("inf") or numeric == float("-inf"):
            return 0.0
        return numeric

    def _collapse_type(
        self,
        *,
        collapse_detected: bool,
        flat_bias_detected: bool,
        down_blindness_detected: bool,
        up_bias_detected: bool,
        collapse: dict[str, Any],
    ) -> str:
        if not collapse_detected:
            return "none"
        if flat_bias_detected and down_blindness_detected:
            return "mixed"
        if flat_bias_detected:
            return "flat_bias"
        if down_blindness_detected:
            return "down_blindness"
        if up_bias_detected:
            return "up_bias"
        if bool(collapse.get("low_margin_detected", False)) or bool(
            collapse.get("uniform_probability_detected", False)
        ):
            return "confidence_collapse"
        return "mixed"

    def _recommended_action(
        self,
        *,
        collapse_detected: bool,
        flat_bias_detected: bool,
        down_blindness_detected: bool,
        up_bias_detected: bool,
        collapse: dict[str, Any],
    ) -> str:
        if not collapse_detected:
            return "reject"
        if flat_bias_detected or down_blindness_detected:
            return "adjust_labels"
        if up_bias_detected:
            return "inspect_symbol"
        if bool(collapse.get("low_margin_detected", False)) or bool(
            collapse.get("uniform_probability_detected", False)
        ):
            return "retune_threshold"
        return "reject"
