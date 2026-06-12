from __future__ import annotations

from typing import Any


class AntiCollapseValidator:
    VALIDATOR_NAME = "anti_collapse_validator"
    VALIDATOR_VERSION = "ml27"
    LABELS = ("UP", "DOWN", "FLAT")

    def validate(
        self,
        *,
        actual_class_counts: dict[str, int],
        predicted_class_counts: dict[str, int],
        avg_prob_up: float,
        avg_prob_down: float,
        avg_prob_flat: float,
        confidence_stats: dict[str, float | int | None] | None = None,
        margin_stats: dict[str, float | int | None] | None = None,
    ) -> dict[str, Any]:
        confidence_stats = confidence_stats or {}
        margin_stats = margin_stats or {}
        actual_distribution = self._distribution(actual_class_counts)
        predicted_distribution = self._distribution(predicted_class_counts)
        max_predicted_class_share = max(predicted_distribution.values(), default=0.0)
        min_predicted_class_share = min(predicted_distribution.values(), default=0.0)
        up_down_prediction_ratio = self._safe_ratio(
            predicted_distribution.get("UP", 0.0),
            predicted_distribution.get("DOWN", 0.0),
        )

        dominant_label = max(predicted_distribution, key=predicted_distribution.get, default="FLAT")
        single_class_dominance = max_predicted_class_share >= 0.85
        directional_bias_detected = self._directional_bias_detected(
            actual_distribution=actual_distribution,
            predicted_distribution=predicted_distribution,
        )
        confidence_collapse_detected = self._confidence_collapse_detected(
            avg_prob_up=avg_prob_up,
            avg_prob_down=avg_prob_down,
            avg_prob_flat=avg_prob_flat,
            confidence_stats=confidence_stats,
        )
        low_margin_detected = self._low_margin_detected(margin_stats=margin_stats)
        collapse_detected = any(
            (
                single_class_dominance,
                directional_bias_detected,
                confidence_collapse_detected,
                low_margin_detected,
            )
        )

        warnings: list[str] = []
        reasons: list[str] = []
        if single_class_dominance:
            warnings.append("single_class_prediction_collapse")
            reasons.append("single_class_prediction_collapse")
        if directional_bias_detected:
            direction = "up" if predicted_distribution.get("UP", 0.0) >= predicted_distribution.get("DOWN", 0.0) else "down"
            warnings.append("directional_bias_warning")
            reasons.append(f"directional_bias_{direction}")
        if confidence_collapse_detected:
            warnings.append("low_confidence_uniform_probs")
            reasons.append("low_confidence_uniform_probs")
        if low_margin_detected:
            warnings.append("low_margin_detected")
            reasons.append("low_margin_detected")

        return {
            "validator_name": self.VALIDATOR_NAME,
            "validator_version": self.VALIDATOR_VERSION,
            "collapse_detected": collapse_detected,
            "collapse_type": self._collapse_type(
                single_class_dominance=single_class_dominance,
                directional_bias_detected=directional_bias_detected,
                confidence_collapse_detected=confidence_collapse_detected,
                low_margin_detected=low_margin_detected,
            ),
            "predicted_distribution": predicted_distribution,
            "actual_distribution": actual_distribution,
            "max_predicted_class_share": max_predicted_class_share,
            "min_predicted_class_share": min_predicted_class_share,
            "up_down_prediction_ratio": up_down_prediction_ratio,
            "confidence_collapse_detected": confidence_collapse_detected,
            "low_margin_detected": low_margin_detected,
            "directional_bias_detected": directional_bias_detected,
            "warnings": warnings,
            "reasons": reasons,
            "recommendations": self._recommendations(
                collapse_detected=collapse_detected,
                dominant_label=dominant_label,
                warnings=warnings,
            ),
        }

    def validate_probability_report(self, probability_report: dict[str, Any]) -> dict[str, Any]:
        return self.validate(
            actual_class_counts=dict(probability_report.get("actual_direction_counts", {})),
            predicted_class_counts=dict(probability_report.get("predicted_direction_counts", {})),
            avg_prob_up=float(probability_report.get("avg_prob_up", 0.0)),
            avg_prob_down=float(probability_report.get("avg_prob_down", 0.0)),
            avg_prob_flat=float(probability_report.get("avg_prob_flat", 0.0)),
            confidence_stats={
                "q90": probability_report.get("max_prob_q90"),
                "q50": probability_report.get("max_prob_q50"),
                "rows_above_0_45": dict(probability_report.get("rows_above_thresholds", {})).get("0.45"),
            },
            margin_stats={
                "q90": probability_report.get("margin_q90"),
                "q50": probability_report.get("margin_q50"),
            },
        )

    def _directional_bias_detected(
        self,
        *,
        actual_distribution: dict[str, float],
        predicted_distribution: dict[str, float],
    ) -> bool:
        up_bias = (
            predicted_distribution.get("UP", 0.0) >= 0.70
            and predicted_distribution.get("UP", 0.0) >= actual_distribution.get("UP", 0.0) + 0.20
        )
        down_bias = (
            predicted_distribution.get("DOWN", 0.0) >= 0.70
            and predicted_distribution.get("DOWN", 0.0) >= actual_distribution.get("DOWN", 0.0) + 0.20
        )
        suppressed_side = min(
            predicted_distribution.get("UP", 0.0),
            predicted_distribution.get("DOWN", 0.0),
        ) <= 0.10
        return bool(up_bias or down_bias or (suppressed_side and max(predicted_distribution.get("UP", 0.0), predicted_distribution.get("DOWN", 0.0)) >= 0.75))

    @staticmethod
    def _confidence_collapse_detected(
        *,
        avg_prob_up: float,
        avg_prob_down: float,
        avg_prob_flat: float,
        confidence_stats: dict[str, float | int | None],
    ) -> bool:
        confidence_q90 = float(confidence_stats.get("q90") or 0.0)
        rows_above_045 = int(confidence_stats.get("rows_above_0_45") or 0)
        max_avg_prob = max(avg_prob_up, avg_prob_down, avg_prob_flat)
        return max_avg_prob <= 0.38 and (confidence_q90 < 0.40 or rows_above_045 == 0)

    @staticmethod
    def _low_margin_detected(*, margin_stats: dict[str, float | int | None]) -> bool:
        margin_q90 = float(margin_stats.get("q90") or 0.0)
        margin_q50 = float(margin_stats.get("q50") or 0.0)
        return margin_q90 < 0.05 or margin_q50 < 0.03

    @staticmethod
    def _distribution(counts: dict[str, int]) -> dict[str, float]:
        total = sum(int(counts.get(label, 0)) for label in AntiCollapseValidator.LABELS)
        if total <= 0:
            return {label: 0.0 for label in AntiCollapseValidator.LABELS}
        return {
            label: int(counts.get(label, 0)) / total
            for label in AntiCollapseValidator.LABELS
        }

    @staticmethod
    def _collapse_type(
        *,
        single_class_dominance: bool,
        directional_bias_detected: bool,
        confidence_collapse_detected: bool,
        low_margin_detected: bool,
    ) -> str:
        active = sum(
            int(flag)
            for flag in (
                single_class_dominance,
                directional_bias_detected,
                confidence_collapse_detected,
                low_margin_detected,
            )
        )
        if active == 0:
            return "NONE"
        if active > 1:
            return "MIXED_COLLAPSE"
        if single_class_dominance:
            return "SINGLE_CLASS_DOMINANCE"
        if directional_bias_detected:
            return "DIRECTIONAL_BIAS"
        if confidence_collapse_detected:
            return "LOW_CONFIDENCE_UNIFORM_PROBS"
        return "LOW_MARGIN"

    @staticmethod
    def _recommendations(
        *,
        collapse_detected: bool,
        dominant_label: str,
        warnings: list[str],
    ) -> list[str]:
        if not collapse_detected:
            return ["Prediction distribution looks balanced enough for research review."]
        recommendations = [
            "Do not accept this model as a research candidate until collapse signals are reduced.",
            "Review labels, feature balance, and confidence gating thresholds.",
        ]
        if "directional_bias_warning" in warnings:
            recommendations.append(f"Investigate why predictions are skewed toward {dominant_label}.")
        if "low_margin_detected" in warnings:
            recommendations.append("Increase separability checks because prediction margins are too weak.")
        return recommendations

    @staticmethod
    def _safe_ratio(numerator: float, denominator: float) -> float:
        if denominator <= 0.0:
            return float("inf") if numerator > 0.0 else 0.0
        return numerator / denominator
