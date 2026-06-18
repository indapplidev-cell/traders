from __future__ import annotations

from typing import Any, Mapping


class CollapseDiagnosticsV2:
    DIAGNOSTIC_NAME = "collapse_diagnostics_v2"
    DIAGNOSTIC_VERSION = "ml36"
    LABELS = ("UP", "DOWN", "FLAT")

    def analyze(
        self,
        *,
        probability_report: dict[str, Any],
        symbol: str | None,
        feature_version: str | None,
        label_version: str | None,
        accuracy_edge: float | None = None,
        walk_forward_summary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        actual_distribution = self._distribution(
            dict(probability_report.get("actual_direction_counts", {})),
            dict(probability_report.get("actual_direction_ratios", {})),
        )
        predicted_distribution = self._distribution(
            dict(probability_report.get("predicted_direction_counts", {})),
            dict(probability_report.get("predicted_direction_ratios", {})),
        )
        dominant_class = max(predicted_distribution, key=predicted_distribution.get, default="FLAT")
        dominant_class_ratio = float(predicted_distribution.get(dominant_class, 0.0))
        confidence_distribution = {
            "avg_prob_up": self._safe_float(probability_report.get("avg_prob_up")),
            "avg_prob_down": self._safe_float(probability_report.get("avg_prob_down")),
            "avg_prob_flat": self._safe_float(probability_report.get("avg_prob_flat")),
            "max_prob_q50": self._safe_float(probability_report.get("max_prob_q50")),
            "max_prob_q90": self._safe_float(probability_report.get("max_prob_q90")),
            "rows_above_thresholds": self._json_safe_mapping(
                dict(probability_report.get("rows_above_thresholds", {}))
            ),
        }
        probability_margin_distribution = {
            "margin_q50": self._safe_float(probability_report.get("margin_q50")),
            "margin_q90": self._safe_float(probability_report.get("margin_q90")),
        }
        flat_prediction_rate = float(predicted_distribution.get("FLAT", 0.0))
        up_prediction_rate = float(predicted_distribution.get("UP", 0.0))
        down_prediction_rate = float(predicted_distribution.get("DOWN", 0.0))
        class_absence = {
            label: bool(predicted_distribution.get(label, 0.0) <= 0.0)
            for label in self.LABELS
        }

        dominant_class_detected = dominant_class_ratio >= 0.85
        low_margin_detected = self._low_margin_detected(probability_margin_distribution)
        uniform_probability_detected = self._uniform_probability_detected(confidence_distribution)
        flat_underprediction_detected = self._flat_underprediction_detected(
            actual_distribution=actual_distribution,
            predicted_distribution=predicted_distribution,
        )
        collapse_detected = any(
            (
                dominant_class_detected,
                low_margin_detected,
                uniform_probability_detected,
                flat_underprediction_detected,
            )
        )
        collapse_type = self._collapse_type(
            dominant_class_detected=dominant_class_detected,
            low_margin_detected=low_margin_detected,
            uniform_probability_detected=uniform_probability_detected,
            flat_underprediction_detected=flat_underprediction_detected,
        )
        recommendations = self._recommendations(
            dominant_class_detected=dominant_class_detected,
            low_margin_detected=low_margin_detected,
            uniform_probability_detected=uniform_probability_detected,
            flat_underprediction_detected=flat_underprediction_detected,
            accuracy_edge=accuracy_edge,
            walk_forward_summary=walk_forward_summary or {},
        )

        return {
            "diagnostic_name": self.DIAGNOSTIC_NAME,
            "diagnostic_version": self.DIAGNOSTIC_VERSION,
            "symbol": symbol,
            "feature_version": feature_version,
            "label_version": label_version,
            "collapse_detected": collapse_detected,
            "collapse_type": collapse_type,
            "actual_distribution": actual_distribution,
            "predicted_distribution": predicted_distribution,
            "confidence_distribution": confidence_distribution,
            "probability_margin_distribution": probability_margin_distribution,
            "flat_prediction_rate": flat_prediction_rate,
            "up_prediction_rate": up_prediction_rate,
            "down_prediction_rate": down_prediction_rate,
            "class_absence": class_absence,
            "dominant_class": dominant_class,
            "dominant_class_ratio": dominant_class_ratio,
            "low_margin_detected": low_margin_detected,
            "uniform_probability_detected": uniform_probability_detected,
            "flat_underprediction_detected": flat_underprediction_detected,
            "recommendations": recommendations,
        }

    def _distribution(
        self,
        counts: dict[str, Any],
        ratios: dict[str, Any],
    ) -> dict[str, float]:
        if ratios:
            return {
                label: float(ratios.get(label, 0.0) or 0.0)
                for label in self.LABELS
            }
        total = sum(int(counts.get(label, 0) or 0) for label in self.LABELS)
        if total <= 0:
            return {label: 0.0 for label in self.LABELS}
        return {
            label: int(counts.get(label, 0) or 0) / total
            for label in self.LABELS
        }

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        if value is None:
            return None
        numeric = float(value)
        if numeric == float("inf") or numeric == float("-inf"):
            return None
        return numeric

    def _json_safe_mapping(self, payload: dict[str, Any]) -> dict[str, float | int | None]:
        return {
            str(key): self._json_safe_value(value)
            for key, value in payload.items()
        }

    def _json_safe_value(self, value: Any) -> float | int | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        numeric = float(value)
        if numeric == float("inf") or numeric == float("-inf"):
            return None
        return numeric

    @staticmethod
    def _low_margin_detected(probability_margin_distribution: dict[str, float | None]) -> bool:
        margin_q90_raw = probability_margin_distribution.get("margin_q90")
        margin_q50_raw = probability_margin_distribution.get("margin_q50")
        if margin_q90_raw is None and margin_q50_raw is None:
            return False
        margin_q90 = float(margin_q90_raw or 0.0)
        margin_q50 = float(margin_q50_raw or 0.0)
        return margin_q90 < 0.05 or margin_q50 < 0.03

    @staticmethod
    def _uniform_probability_detected(confidence_distribution: dict[str, Any]) -> bool:
        if (
            confidence_distribution.get("avg_prob_up") is None
            and confidence_distribution.get("avg_prob_down") is None
            and confidence_distribution.get("avg_prob_flat") is None
            and confidence_distribution.get("max_prob_q90") is None
            and not dict(confidence_distribution.get("rows_above_thresholds", {}))
        ):
            return False
        avg_probabilities = [
            float(confidence_distribution.get("avg_prob_up") or 0.0),
            float(confidence_distribution.get("avg_prob_down") or 0.0),
            float(confidence_distribution.get("avg_prob_flat") or 0.0),
        ]
        max_prob_q90 = float(confidence_distribution.get("max_prob_q90") or 0.0)
        rows_above_045 = int(
            dict(confidence_distribution.get("rows_above_thresholds", {})).get("0.45", 0) or 0
        )
        return max(avg_probabilities, default=0.0) <= 0.38 and (max_prob_q90 < 0.40 or rows_above_045 == 0)

    @staticmethod
    def _flat_underprediction_detected(
        *,
        actual_distribution: dict[str, float],
        predicted_distribution: dict[str, float],
    ) -> bool:
        actual_flat = float(actual_distribution.get("FLAT", 0.0))
        predicted_flat = float(predicted_distribution.get("FLAT", 0.0))
        return actual_flat >= 0.12 and predicted_flat <= max(0.05, actual_flat - 0.15)

    @staticmethod
    def _collapse_type(
        *,
        dominant_class_detected: bool,
        low_margin_detected: bool,
        uniform_probability_detected: bool,
        flat_underprediction_detected: bool,
    ) -> str:
        active = [
            ("DOMINANT_CLASS_COLLAPSE", dominant_class_detected),
            ("LOW_MARGIN", low_margin_detected),
            ("UNIFORM_PROBABILITIES", uniform_probability_detected),
            ("FLAT_UNDERPREDICTION", flat_underprediction_detected),
        ]
        names = [name for name, enabled in active if enabled]
        if not names:
            return "NONE"
        if len(names) > 1:
            return "MIXED_COLLAPSE"
        return names[0]

    def _recommendations(
        self,
        *,
        dominant_class_detected: bool,
        low_margin_detected: bool,
        uniform_probability_detected: bool,
        flat_underprediction_detected: bool,
        accuracy_edge: float | None,
        walk_forward_summary: dict[str, Any],
    ) -> list[str]:
        recommendations: list[str] = []
        if flat_underprediction_detected:
            recommendations.append(
                "Increase flat-aware labeling/calibration or add flat threshold diagnostics."
            )
        if dominant_class_detected:
            recommendations.append(
                "Tune class weighting, thresholds, or balanced sampling to reduce dominant-class collapse."
            )
        if low_margin_detected or uniform_probability_detected:
            recommendations.append(
                "Audit calibration and confidence thresholds because prediction separation is too weak."
            )
        walk_forward_status = str(walk_forward_summary.get("walk_forward_status") or "")
        if accuracy_edge is not None and accuracy_edge > 0.0 and walk_forward_status in {"UNSTABLE", "NEGATIVE"}:
            recommendations.append("Run temporal stability analysis because walk-forward fails despite positive baseline edge.")
        if not recommendations:
            recommendations.append("Collapse profile looks stable enough for research review.")
        return list(dict.fromkeys(recommendations))


CRITICAL_COLLAPSE_TYPES = {
    "SINGLE_CLASS_COLLAPSE",
    "DOWN_BLINDNESS",
    "FLAT_UNDERPREDICTION_CRITICAL",
    "UNIFORM_PROBABILITY_COLLAPSE",
}


def classify_collapse_severity(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Classify collapse severity without softening safety gates.

    Severity meaning:
    - OK: no collapse detected.
    - WATCH: collapse/bias is present, but not automatically critical.
    - CRITICAL: model is structurally unsafe and must fail collapse_gate.
    """
    data: Mapping[str, Any] = payload or {}

    collapse_detected = bool(data.get("collapse_detected"))
    collapse_type = data.get("collapse_type")
    dominant_class_ratio = _to_float(data.get("dominant_class_ratio"))
    flat_prediction_rate = _to_float(data.get("flat_prediction_rate"))
    down_prediction_rate = _to_float(data.get("down_prediction_rate"))
    up_prediction_rate = _to_float(data.get("up_prediction_rate"))
    actual_distribution = data.get("actual_distribution") or {}
    actual_down = _to_float(actual_distribution.get("DOWN"))
    actual_flat = _to_float(actual_distribution.get("FLAT"))

    reasons: list[str] = []

    if not collapse_detected:
        return {
            "collapse_severity": "OK",
            "collapse_gate_failed": False,
            "collapse_severity_reasons": [],
        }

    normalized_type = str(collapse_type or "").upper()

    if normalized_type in CRITICAL_COLLAPSE_TYPES:
        reasons.append(f"critical_collapse_type={collapse_type}")

    if dominant_class_ratio is not None and dominant_class_ratio >= 0.90:
        reasons.append(f"dominant_class_ratio={dominant_class_ratio:.4f}")

    if actual_flat is not None and actual_flat >= 0.20:
        if flat_prediction_rate is not None and flat_prediction_rate <= 0.01:
            reasons.append(
                f"flat_underprediction: predicted={flat_prediction_rate:.4f}, actual={actual_flat:.4f}"
            )

    if actual_down is not None and actual_down >= 0.25:
        if down_prediction_rate is not None and down_prediction_rate <= 0.10:
            reasons.append(
                f"down_underprediction: predicted={down_prediction_rate:.4f}, actual={actual_down:.4f}"
            )

    if up_prediction_rate is not None and up_prediction_rate >= 0.85:
        reasons.append(f"up_overprediction={up_prediction_rate:.4f}")

    severity = "CRITICAL" if reasons else "WATCH"
    return {
        "collapse_severity": severity,
        "collapse_gate_failed": severity == "CRITICAL",
        "collapse_severity_reasons": reasons,
    }


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
