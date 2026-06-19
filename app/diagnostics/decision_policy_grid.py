from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


DIRECTION_LABELS: tuple[str, str, str] = ("DOWN", "FLAT", "UP")


@dataclass(frozen=True)
class DecisionPolicyConfig:
    policy_id: str
    down_offset: float = 0.0
    flat_offset: float = 0.0
    up_offset: float = 0.0
    min_top_prob: float | None = None
    min_margin: float | None = None
    ambiguous_to_flat: bool = True
    max_dominant_class_ratio: float = 0.75
    max_flat_ratio: float = 0.45
    actual_class_high_threshold: float = 0.25
    min_down_ratio_when_actual_down_high: float = 0.12
    min_up_ratio_when_actual_up_high: float = 0.12
    baseline_edge_min: float = 0.0
    baseline_edge_tolerance: float = 0.0025
    score_baseline_edge_weight: float = 100.0
    score_distribution_penalty: float = 25.0


@dataclass(frozen=True)
class DecisionPolicyResult:
    policy_id: str
    selected_predictions: list[str]
    predicted_counts: dict[str, int]
    predicted_ratios: dict[str, float]
    actual_counts: dict[str, int]
    actual_ratios: dict[str, float]
    accuracy: float
    baseline_accuracy: float
    baseline_edge: float
    baseline_edge_status: str
    dominant_class: str | None
    dominant_class_ratio: float
    distribution_safe: bool
    distribution_rejection_reasons: list[str]
    score: float
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "selected_predictions": self.selected_predictions,
            "predicted_counts": self.predicted_counts,
            "predicted_ratios": self.predicted_ratios,
            "actual_counts": self.actual_counts,
            "actual_ratios": self.actual_ratios,
            "accuracy": self.accuracy,
            "baseline_accuracy": self.baseline_accuracy,
            "baseline_edge": self.baseline_edge,
            "baseline_edge_status": self.baseline_edge_status,
            "dominant_class": self.dominant_class,
            "dominant_class_ratio": self.dominant_class_ratio,
            "distribution_safe": self.distribution_safe,
            "distribution_rejection_reasons": self.distribution_rejection_reasons,
            "score": self.score,
            "config": self.config,
        }


class DecisionPolicyGrid:
    diagnostic_name = "decision_policy_grid"
    diagnostic_version = "ml38_9_5"

    def __init__(self, configs: Sequence[DecisionPolicyConfig] | None = None) -> None:
        self.configs = tuple(configs or self.default_configs())

    @staticmethod
    def default_configs() -> tuple[DecisionPolicyConfig, ...]:
        return (
            DecisionPolicyConfig(
                policy_id="raw_argmax",
            ),
            DecisionPolicyConfig(
                policy_id="flat_on_low_margin",
                min_margin=0.055,
                ambiguous_to_flat=True,
                max_dominant_class_ratio=0.72,
                max_flat_ratio=0.42,
                min_down_ratio_when_actual_down_high=0.12,
                min_up_ratio_when_actual_up_high=0.12,
            ),
            DecisionPolicyConfig(
                policy_id="down_flat_offset_soft",
                down_offset=0.020,
                flat_offset=0.015,
                min_margin=0.035,
                ambiguous_to_flat=True,
                max_dominant_class_ratio=0.72,
                max_flat_ratio=0.42,
                min_down_ratio_when_actual_down_high=0.15,
                min_up_ratio_when_actual_up_high=0.15,
            ),
            DecisionPolicyConfig(
                policy_id="down_flat_offset_medium",
                down_offset=0.035,
                flat_offset=0.020,
                min_margin=0.030,
                ambiguous_to_flat=True,
                max_dominant_class_ratio=0.70,
                max_flat_ratio=0.40,
                min_down_ratio_when_actual_down_high=0.15,
                min_up_ratio_when_actual_up_high=0.15,
            ),
            DecisionPolicyConfig(
                policy_id="down_offset_strong_flat_light",
                down_offset=0.050,
                flat_offset=0.010,
                min_margin=0.025,
                ambiguous_to_flat=True,
                max_dominant_class_ratio=0.70,
                max_flat_ratio=0.38,
                min_down_ratio_when_actual_down_high=0.18,
                min_up_ratio_when_actual_up_high=0.15,
            ),
        )

    def evaluate(
        self,
        *,
        probability_rows: Sequence[Mapping[str, Any]],
        actual_labels: Sequence[str],
        baseline_accuracy: float | None = None,
    ) -> dict[str, Any]:
        labels = [str(label).upper() for label in actual_labels]
        if not probability_rows or not labels or len(probability_rows) != len(labels):
            return {
                "diagnostic_name": self.diagnostic_name,
                "diagnostic_version": self.diagnostic_version,
                "enabled": True,
                "policy_count": len(self.configs),
                "selected_policy_id": None,
                "selected_decision_source": "raw_argmax_no_policy_rows",
                "best_policy": None,
                "policies_ranked": [],
                "reason": "empty_probability_rows_or_label_mismatch",
            }

        resolved_baseline = (
            float(baseline_accuracy)
            if baseline_accuracy is not None
            else self._majority_baseline_accuracy(labels)
        )

        results = [
            self._evaluate_one_policy(
                config=config,
                probability_rows=probability_rows,
                actual_labels=labels,
                baseline_accuracy=resolved_baseline,
            )
            for config in self.configs
        ]

        ranked = sorted(results, key=lambda item: item.score, reverse=True)
        safe_ranked = [
            item for item in ranked
            if item.distribution_safe and item.baseline_edge >= -0.000001
        ]
        selected = safe_ranked[0] if safe_ranked else ranked[0]

        return {
            "diagnostic_name": self.diagnostic_name,
            "diagnostic_version": self.diagnostic_version,
            "enabled": True,
            "policy_count": len(self.configs),
            "selected_policy_id": selected.policy_id,
            "selected_decision_source": f"decision_policy_grid:{selected.policy_id}",
            "selected_predictions": selected.selected_predictions,
            "selected_policy": selected.to_dict(),
            "best_policy": ranked[0].to_dict(),
            "safe_policy_count": len(safe_ranked),
            "policies_ranked": [item.to_dict() for item in ranked],
            "baseline_accuracy": resolved_baseline,
            "quality": {
                "selected_baseline_edge": selected.baseline_edge,
                "selected_distribution_safe": selected.distribution_safe,
                "selected_dominant_class_ratio": selected.dominant_class_ratio,
                "selected_rejection_reasons": selected.distribution_rejection_reasons,
            },
        }

    def _evaluate_one_policy(
        self,
        *,
        config: DecisionPolicyConfig,
        probability_rows: Sequence[Mapping[str, Any]],
        actual_labels: Sequence[str],
        baseline_accuracy: float,
    ) -> DecisionPolicyResult:
        predictions = [
            self._predict_one(row=row, config=config)
            for row in probability_rows
        ]
        predicted_counts = self._counts(predictions)
        actual_counts = self._counts(actual_labels)
        predicted_ratios = self._ratios(predicted_counts, len(predictions))
        actual_ratios = self._ratios(actual_counts, len(actual_labels))
        correct_count = sum(1 for pred, actual in zip(predictions, actual_labels) if pred == actual)
        accuracy = correct_count / len(actual_labels) if actual_labels else 0.0
        baseline_edge = accuracy - baseline_accuracy
        baseline_edge_status = (
            "POSITIVE_EDGE"
            if baseline_edge > config.baseline_edge_tolerance
            else "NEUTRAL_EDGE"
            if baseline_edge >= -config.baseline_edge_tolerance
            else "NEGATIVE_EDGE"
        )

        dominant_class = None
        dominant_class_ratio = 0.0
        if predicted_ratios:
            dominant_class, dominant_class_ratio = max(
                predicted_ratios.items(),
                key=lambda item: item[1],
            )

        distribution_safe, distribution_reasons = self._distribution_safety(
            config=config,
            predicted_ratios=predicted_ratios,
            actual_ratios=actual_ratios,
            dominant_class=dominant_class,
            dominant_class_ratio=dominant_class_ratio,
        )
        score = self._score(
            config=config,
            baseline_edge=baseline_edge,
            distribution_safe=distribution_safe,
            distribution_rejection_reasons=distribution_reasons,
            dominant_class_ratio=dominant_class_ratio,
        )

        return DecisionPolicyResult(
            policy_id=config.policy_id,
            selected_predictions=predictions,
            predicted_counts=predicted_counts,
            predicted_ratios=predicted_ratios,
            actual_counts=actual_counts,
            actual_ratios=actual_ratios,
            accuracy=accuracy,
            baseline_accuracy=baseline_accuracy,
            baseline_edge=baseline_edge,
            baseline_edge_status=baseline_edge_status,
            dominant_class=dominant_class,
            dominant_class_ratio=dominant_class_ratio,
            distribution_safe=distribution_safe,
            distribution_rejection_reasons=distribution_reasons,
            score=score,
            config={
                "down_offset": config.down_offset,
                "flat_offset": config.flat_offset,
                "up_offset": config.up_offset,
                "min_top_prob": config.min_top_prob,
                "min_margin": config.min_margin,
                "ambiguous_to_flat": config.ambiguous_to_flat,
                "max_dominant_class_ratio": config.max_dominant_class_ratio,
                "max_flat_ratio": config.max_flat_ratio,
                "actual_class_high_threshold": config.actual_class_high_threshold,
                "min_down_ratio_when_actual_down_high": config.min_down_ratio_when_actual_down_high,
                "min_up_ratio_when_actual_up_high": config.min_up_ratio_when_actual_up_high,
                "baseline_edge_min": config.baseline_edge_min,
                "baseline_edge_tolerance": config.baseline_edge_tolerance,
            },
        )

    def _predict_one(self, *, row: Mapping[str, Any], config: DecisionPolicyConfig) -> str:
        probs = {
            "DOWN": self._float_value(row, "prob_down", "down_probability", "p_down"),
            "FLAT": self._float_value(row, "prob_flat", "flat_probability", "p_flat"),
            "UP": self._float_value(row, "prob_up", "up_probability", "p_up"),
        }
        adjusted = {
            "DOWN": probs["DOWN"] + config.down_offset,
            "FLAT": probs["FLAT"] + config.flat_offset,
            "UP": probs["UP"] + config.up_offset,
        }
        ranked = sorted(adjusted.items(), key=lambda item: item[1], reverse=True)
        top_label, top_value = ranked[0]
        second_value = ranked[1][1]
        raw_top_prob = probs[top_label]
        margin = top_value - second_value

        if config.min_top_prob is not None and raw_top_prob < config.min_top_prob:
            return "FLAT" if config.ambiguous_to_flat else top_label

        if config.min_margin is not None and margin < config.min_margin:
            return "FLAT" if config.ambiguous_to_flat else top_label

        return top_label

    @staticmethod
    def _float_value(row: Mapping[str, Any], *keys: str) -> float:
        for key in keys:
            value = row.get(key)
            if value is not None:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    continue
        return 0.0

    @staticmethod
    def _counts(labels: Sequence[str]) -> dict[str, int]:
        return {label: sum(1 for item in labels if item == label) for label in DIRECTION_LABELS}

    @staticmethod
    def _ratios(counts: Mapping[str, int], total: int) -> dict[str, float]:
        if total <= 0:
            return {label: 0.0 for label in DIRECTION_LABELS}
        return {label: float(counts.get(label, 0)) / float(total) for label in DIRECTION_LABELS}

    @staticmethod
    def _majority_baseline_accuracy(labels: Sequence[str]) -> float:
        if not labels:
            return 0.0
        counts = DecisionPolicyGrid._counts(labels)
        return max(counts.values()) / len(labels)

    def _distribution_safety(
        self,
        *,
        config: DecisionPolicyConfig,
        predicted_ratios: Mapping[str, float],
        actual_ratios: Mapping[str, float],
        dominant_class: str | None,
        dominant_class_ratio: float,
    ) -> tuple[bool, list[str]]:
        reasons: list[str] = []

        if dominant_class and dominant_class_ratio > config.max_dominant_class_ratio:
            reasons.append(
                f"dominant_class_ratio>{config.max_dominant_class_ratio}:"
                f"{dominant_class}={dominant_class_ratio:.4f}"
            )

        flat_ratio = float(predicted_ratios.get("FLAT", 0.0))
        if flat_ratio > config.max_flat_ratio:
            reasons.append(f"flat_ratio>{config.max_flat_ratio}:{flat_ratio:.4f}")

        actual_down = float(actual_ratios.get("DOWN", 0.0))
        predicted_down = float(predicted_ratios.get("DOWN", 0.0))
        if (
            actual_down >= config.actual_class_high_threshold
            and predicted_down < config.min_down_ratio_when_actual_down_high
        ):
            reasons.append(
                "down_coverage_too_low:"
                f"actual={actual_down:.4f},predicted={predicted_down:.4f},"
                f"min={config.min_down_ratio_when_actual_down_high:.4f}"
            )

        actual_up = float(actual_ratios.get("UP", 0.0))
        predicted_up = float(predicted_ratios.get("UP", 0.0))
        if (
            actual_up >= config.actual_class_high_threshold
            and predicted_up < config.min_up_ratio_when_actual_up_high
        ):
            reasons.append(
                "up_coverage_too_low:"
                f"actual={actual_up:.4f},predicted={predicted_up:.4f},"
                f"min={config.min_up_ratio_when_actual_up_high:.4f}"
            )

        return not reasons, reasons

    def _score(
        self,
        *,
        config: DecisionPolicyConfig,
        baseline_edge: float,
        distribution_safe: bool,
        distribution_rejection_reasons: Sequence[str],
        dominant_class_ratio: float,
    ) -> float:
        score = baseline_edge * config.score_baseline_edge_weight

        if baseline_edge >= config.baseline_edge_min:
            score += 10.0
        else:
            score -= 10.0

        if distribution_safe:
            score += 5.0
        else:
            score -= config.score_distribution_penalty
            score -= len(distribution_rejection_reasons) * 2.0

        if dominant_class_ratio > 0.0:
            score -= max(0.0, dominant_class_ratio - 0.55) * 10.0

        return score
