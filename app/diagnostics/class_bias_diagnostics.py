from __future__ import annotations

from typing import Any


class ClassBiasDiagnostics:
    DIAGNOSTIC_NAME = "class_bias_diagnostics"
    DIAGNOSTIC_VERSION = "ml38_9_1"
    LABELS = ("UP", "DOWN", "FLAT")

    def analyze(
        self,
        *,
        predicted_distribution: dict[str, Any],
        actual_distribution: dict[str, Any],
        symbol: str | None = None,
        config_id: str | None = None,
    ) -> dict[str, Any]:
        predicted = self._normalized_distribution(predicted_distribution)
        actual = self._normalized_distribution(actual_distribution)

        predicted_flat_ratio = predicted["FLAT"]
        actual_flat_ratio = actual["FLAT"]
        predicted_down_ratio = predicted["DOWN"]
        actual_down_ratio = actual["DOWN"]
        predicted_up_ratio = predicted["UP"]
        actual_up_ratio = actual["UP"]

        flat_overprediction_ratio = self._safe_ratio(
            numerator=predicted_flat_ratio,
            denominator=actual_flat_ratio,
        )
        flat_underprediction_ratio = self._safe_ratio(
            numerator=predicted_flat_ratio,
            denominator=actual_flat_ratio,
        )
        down_underprediction_ratio = self._safe_ratio(
            numerator=predicted_down_ratio,
            denominator=actual_down_ratio,
        )
        up_bias_ratio = self._safe_ratio(
            numerator=predicted_up_ratio,
            denominator=actual_up_ratio,
        )

        dominant_predicted_class = self._dominant_label(predicted)
        dominant_actual_class = self._dominant_label(actual)
        dominant_predicted_class_ratio = predicted.get(dominant_predicted_class, 0.0)

        flat_bias_detected = (
            predicted_flat_ratio > (actual_flat_ratio * 1.5)
            and predicted_flat_ratio > 0.40
        )
        flat_underprediction_detected = (
            actual_flat_ratio >= 0.12
            and predicted_flat_ratio <= max(0.05, actual_flat_ratio * 0.50)
        )
        down_blindness_detected = (
            predicted_down_ratio < (actual_down_ratio * 0.50)
            and actual_down_ratio > 0.25
        )
        up_bias_detected = (
            predicted_up_ratio > (actual_up_ratio * 1.5)
            and predicted_up_ratio > 0.45
        )
        up_dominance_detected = (
            predicted_up_ratio >= 0.75
            and predicted_up_ratio > actual_up_ratio + 0.25
        )

        bias_rejection_reasons = self._bias_rejection_reasons(
            flat_bias_detected=flat_bias_detected,
            flat_underprediction_detected=flat_underprediction_detected,
            down_blindness_detected=down_blindness_detected,
            up_bias_detected=up_bias_detected,
            up_dominance_detected=up_dominance_detected,
        )
        bias_gate_failed = bool(bias_rejection_reasons)

        return {
            "diagnostic_name": self.DIAGNOSTIC_NAME,
            "diagnostic_version": self.DIAGNOSTIC_VERSION,
            "symbol": symbol,
            "config_id": config_id,
            "predicted_flat_ratio": predicted_flat_ratio,
            "actual_flat_ratio": actual_flat_ratio,
            "flat_overprediction_ratio": flat_overprediction_ratio,
            "flat_underprediction_ratio": flat_underprediction_ratio,
            "predicted_down_ratio": predicted_down_ratio,
            "actual_down_ratio": actual_down_ratio,
            "down_underprediction_ratio": down_underprediction_ratio,
            "predicted_up_ratio": predicted_up_ratio,
            "actual_up_ratio": actual_up_ratio,
            "up_bias_ratio": up_bias_ratio,
            "dominant_predicted_class": dominant_predicted_class,
            "dominant_actual_class": dominant_actual_class,
            "dominant_predicted_class_ratio": dominant_predicted_class_ratio,
            "flat_bias_detected": flat_bias_detected,
            "flat_underprediction_detected": flat_underprediction_detected,
            "down_blindness_detected": down_blindness_detected,
            "up_bias_detected": up_bias_detected,
            "up_dominance_detected": up_dominance_detected,
            "bias_gate_failed": bias_gate_failed,
            "bias_rejection_reasons": bias_rejection_reasons,
            "symbol_bias_severity": self._severity(
                predicted=predicted,
                actual=actual,
                flat_bias_detected=flat_bias_detected,
                flat_underprediction_detected=flat_underprediction_detected,
                down_blindness_detected=down_blindness_detected,
                up_bias_detected=up_bias_detected,
                up_dominance_detected=up_dominance_detected,
            ),
        }

    def _normalized_distribution(self, payload: dict[str, Any]) -> dict[str, float]:
        if not payload:
            return {label: 0.0 for label in self.LABELS}
        return {
            label: self._safe_float(payload.get(label))
            for label in self.LABELS
        }

    @staticmethod
    def _safe_float(value: Any) -> float:
        if value is None:
            return 0.0
        numeric = float(value)
        if numeric == float("inf") or numeric == float("-inf"):
            return 0.0
        return numeric

    @staticmethod
    def _safe_ratio(*, numerator: float, denominator: float) -> float:
        if denominator <= 0.0:
            return 0.0
        return numerator / denominator

    @staticmethod
    def _dominant_label(payload: dict[str, float]) -> str:
        if not payload:
            return "FLAT"
        return max(payload, key=payload.get, default="FLAT")

    @staticmethod
    def _bias_rejection_reasons(
        *,
        flat_bias_detected: bool,
        flat_underprediction_detected: bool,
        down_blindness_detected: bool,
        up_bias_detected: bool,
        up_dominance_detected: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if flat_bias_detected:
            reasons.append("flat_bias_detected")
        if flat_underprediction_detected:
            reasons.append("flat_underprediction_detected")
        if down_blindness_detected:
            reasons.append("down_blindness_detected")
        if up_bias_detected:
            reasons.append("up_bias_detected")
        if up_dominance_detected:
            reasons.append("up_dominance_detected")
        return reasons

    @staticmethod
    def _severity(
        *,
        predicted: dict[str, float],
        actual: dict[str, float],
        flat_bias_detected: bool,
        flat_underprediction_detected: bool,
        down_blindness_detected: bool,
        up_bias_detected: bool,
        up_dominance_detected: bool,
    ) -> str:
        predicted_flat = predicted.get("FLAT", 0.0)
        actual_flat = actual.get("FLAT", 0.0)
        predicted_down = predicted.get("DOWN", 0.0)
        actual_down = actual.get("DOWN", 0.0)

        critical = (
            (up_dominance_detected and (flat_underprediction_detected or down_blindness_detected))
            or (flat_underprediction_detected and down_blindness_detected)
        )
        if critical:
            return "CRITICAL"

        if (
            flat_bias_detected
            or flat_underprediction_detected
            or down_blindness_detected
            or up_bias_detected
            or up_dominance_detected
        ):
            return "HIGH"
        if (
            predicted_flat < max(0.05, actual_flat * 0.70)
            or (
                actual_down > 0.20
                and predicted_down < (actual_down * 0.75)
            )
        ):
            return "WARN"
        return "OK"
