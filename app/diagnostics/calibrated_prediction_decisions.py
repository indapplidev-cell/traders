from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


LABELS = ("UP", "DOWN", "FLAT")
_CLASS_ORDER = ("DOWN", "FLAT", "UP")


@dataclass(frozen=True)
class BoundedDecisionCalibrationConfig:
    """Distribution guards for selecting calibrated decisions."""

    enabled: bool = True
    max_flat_ratio: float = 0.45
    min_down_ratio_when_actual_down_high: float = 0.12
    min_up_ratio_when_actual_up_high: float = 0.12
    max_dominant_class_ratio: float = 0.75
    require_non_worse_baseline_edge: bool = True
    baseline_edge_tolerance: float = 0.0025
    actual_class_high_threshold: float = 0.25
    fallback_to_raw: bool = True
    diagnostic_version: str = "ml38_9_4"


@dataclass(frozen=True)
class DecisionCalibrationConfig:
    enabled: bool = False
    flat_if_max_prob_below: float = 0.42
    flat_if_margin_below: float = 0.06
    min_direction_prob: float = 0.40
    min_up_down_margin: float = 0.03
    down_boost: float = 0.0
    up_penalty: float = 0.0
    flat_boost: float = 0.0
    mode: str = "legacy_calibration"
    fallback_to_raw: bool = False
    max_flat_ratio: float = 0.45
    min_down_ratio_when_actual_down_high: float = 0.12
    min_up_ratio_when_actual_up_high: float = 0.12
    max_dominant_class_ratio: float = 0.75
    require_non_worse_baseline_edge: bool = True
    baseline_edge_tolerance: float = 0.0025
    actual_class_high_threshold: float = 0.25
    diagnostic_version: str = "ml38_9_4"
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_label_config(cls, label_config: dict[str, Any] | None) -> "DecisionCalibrationConfig":
        payload = dict(label_config or {})
        nested = payload.get("decision_calibration")
        nested_payload = dict(nested) if isinstance(nested, Mapping) else {}

        enabled = bool(
            nested_payload.get(
                "enabled",
                payload.get("decision_calibration_enabled", False),
            )
        )
        mode = str(
            nested_payload.get(
                "mode",
                payload.get("decision_calibration_mode", "legacy_calibration"),
            )
            or "legacy_calibration"
        )

        return cls(
            enabled=enabled,
            flat_if_max_prob_below=float(
                nested_payload.get(
                    "flat_if_max_prob_below",
                    payload.get("decision_flat_if_max_prob_below", 0.42),
                )
            ),
            flat_if_margin_below=float(
                nested_payload.get(
                    "flat_if_margin_below",
                    payload.get("decision_flat_if_margin_below", 0.06),
                )
            ),
            min_direction_prob=float(
                nested_payload.get(
                    "min_direction_prob",
                    payload.get("decision_min_direction_prob", 0.40),
                )
            ),
            min_up_down_margin=float(
                nested_payload.get(
                    "min_up_down_margin",
                    payload.get("decision_min_up_down_margin", 0.03),
                )
            ),
            down_boost=float(
                nested_payload.get(
                    "down_boost",
                    payload.get("decision_down_boost", 0.0),
                )
            ),
            up_penalty=float(
                nested_payload.get(
                    "up_penalty",
                    payload.get("decision_up_penalty", 0.0),
                )
            ),
            flat_boost=float(
                nested_payload.get(
                    "flat_boost",
                    payload.get("decision_flat_boost", 0.0),
                )
            ),
            mode=mode,
            fallback_to_raw=bool(
                nested_payload.get(
                    "fallback_to_raw",
                    payload.get("decision_fallback_to_raw", mode == "bounded_calibration"),
                )
            ),
            max_flat_ratio=float(
                nested_payload.get(
                    "max_flat_ratio",
                    payload.get("decision_max_flat_ratio", 0.45),
                )
            ),
            min_down_ratio_when_actual_down_high=float(
                nested_payload.get(
                    "min_down_ratio_when_actual_down_high",
                    payload.get("decision_min_down_ratio_when_actual_down_high", 0.12),
                )
            ),
            min_up_ratio_when_actual_up_high=float(
                nested_payload.get(
                    "min_up_ratio_when_actual_up_high",
                    payload.get("decision_min_up_ratio_when_actual_up_high", 0.12),
                )
            ),
            max_dominant_class_ratio=float(
                nested_payload.get(
                    "max_dominant_class_ratio",
                    payload.get("decision_max_dominant_class_ratio", 0.75),
                )
            ),
            require_non_worse_baseline_edge=bool(
                nested_payload.get(
                    "require_non_worse_baseline_edge",
                    payload.get("decision_require_non_worse_baseline_edge", True),
                )
            ),
            baseline_edge_tolerance=float(
                nested_payload.get(
                    "baseline_edge_tolerance",
                    payload.get("decision_baseline_edge_tolerance", 0.0025),
                )
            ),
            actual_class_high_threshold=float(
                nested_payload.get(
                    "actual_class_high_threshold",
                    payload.get("decision_actual_class_high_threshold", 0.25),
                )
            ),
            diagnostic_version=str(
                nested_payload.get(
                    "diagnostic_version",
                    payload.get("decision_diagnostic_version", "ml38_9_4"),
                )
            ),
            metadata={
                "config_id": payload.get("config_id"),
                "label_version": payload.get("label_version"),
            },
        )

    def bounded_config(self) -> BoundedDecisionCalibrationConfig:
        return BoundedDecisionCalibrationConfig(
            enabled=self.enabled and self.mode == "bounded_calibration",
            max_flat_ratio=self.max_flat_ratio,
            min_down_ratio_when_actual_down_high=self.min_down_ratio_when_actual_down_high,
            min_up_ratio_when_actual_up_high=self.min_up_ratio_when_actual_up_high,
            max_dominant_class_ratio=self.max_dominant_class_ratio,
            require_non_worse_baseline_edge=self.require_non_worse_baseline_edge,
            baseline_edge_tolerance=self.baseline_edge_tolerance,
            actual_class_high_threshold=self.actual_class_high_threshold,
            fallback_to_raw=self.fallback_to_raw,
            diagnostic_version=self.diagnostic_version,
        )


def _safe_ratio(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return float(count) / float(total)


def _class_counts(labels: Sequence[str]) -> dict[str, int]:
    counts = {name: 0 for name in _CLASS_ORDER}
    for label in labels:
        normalized = str(label).upper()
        if normalized in counts:
            counts[normalized] += 1
    return counts


def _class_ratios(labels: Sequence[str]) -> dict[str, float]:
    counts = _class_counts(labels)
    total = sum(counts.values())
    return {name: _safe_ratio(counts[name], total) for name in _CLASS_ORDER}


def _accuracy(actual: Sequence[str], predicted: Sequence[str]) -> float:
    if not actual or not predicted:
        return 0.0
    total = min(len(actual), len(predicted))
    if total <= 0:
        return 0.0
    correct = sum(1 for left, right in zip(actual[:total], predicted[:total]) if left == right)
    return float(correct) / float(total)


def _majority_baseline_accuracy(actual: Sequence[str]) -> float:
    ratios = _class_ratios(actual)
    return max(ratios.values()) if ratios else 0.0


def _dominant_class(ratios: Mapping[str, float]) -> tuple[str | None, float]:
    if not ratios:
        return None, 0.0
    name = max(_CLASS_ORDER, key=lambda key: float(ratios.get(key, 0.0)))
    return name, float(ratios.get(name, 0.0))


def _distribution_rejection_reasons(
    *,
    actual_ratios: Mapping[str, float],
    predicted_ratios: Mapping[str, float],
    config: BoundedDecisionCalibrationConfig,
) -> list[str]:
    reasons: list[str] = []

    dominant_class, dominant_ratio = _dominant_class(predicted_ratios)
    if dominant_ratio > config.max_dominant_class_ratio:
        reasons.append(f"dominant_class_ratio>{config.max_dominant_class_ratio}:{dominant_class}={dominant_ratio:.4f}")

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

    return reasons


def evaluate_decision_distribution(
    *,
    actual_labels: Sequence[str],
    predicted_labels: Sequence[str],
    config: BoundedDecisionCalibrationConfig | None = None,
) -> dict[str, Any]:
    bounded_config = config or BoundedDecisionCalibrationConfig()

    actual = [str(item).upper() for item in actual_labels]
    predicted = [str(item).upper() for item in predicted_labels]
    total = min(len(actual), len(predicted))
    actual = actual[:total]
    predicted = predicted[:total]

    actual_ratios = _class_ratios(actual)
    predicted_ratios = _class_ratios(predicted)

    accuracy = _accuracy(actual, predicted)
    baseline_accuracy = _majority_baseline_accuracy(actual)
    baseline_edge = accuracy - baseline_accuracy

    distribution_rejection_reasons = _distribution_rejection_reasons(
        actual_ratios=actual_ratios,
        predicted_ratios=predicted_ratios,
        config=bounded_config,
    )

    dominant_class, dominant_ratio = _dominant_class(predicted_ratios)

    return {
        "accuracy": accuracy,
        "baseline_accuracy": baseline_accuracy,
        "baseline_edge": baseline_edge,
        "actual_ratios": dict(actual_ratios),
        "predicted_ratios": dict(predicted_ratios),
        "dominant_class": dominant_class,
        "dominant_class_ratio": dominant_ratio,
        "distribution_rejection_reasons": distribution_rejection_reasons,
        "distribution_safe": len(distribution_rejection_reasons) == 0,
    }


def choose_bounded_calibrated_decisions(
    *,
    actual_labels: Sequence[str],
    raw_predicted_labels: Sequence[str],
    calibrated_predicted_labels: Sequence[str],
    config: BoundedDecisionCalibrationConfig | None = None,
) -> dict[str, Any]:
    """Choose raw or calibrated predictions without softening downstream gates."""

    bounded_config = config or BoundedDecisionCalibrationConfig()

    actual = [str(item).upper() for item in actual_labels]
    raw_predictions = [str(item).upper() for item in raw_predicted_labels]
    calibrated_predictions = [str(item).upper() for item in calibrated_predicted_labels]
    total = min(len(actual), len(raw_predictions), len(calibrated_predictions))
    actual = actual[:total]
    raw_predictions = raw_predictions[:total]
    calibrated_predictions = calibrated_predictions[:total]

    raw_eval = evaluate_decision_distribution(
        actual_labels=actual,
        predicted_labels=raw_predictions,
        config=bounded_config,
    )
    calibrated_eval = evaluate_decision_distribution(
        actual_labels=actual,
        predicted_labels=calibrated_predictions,
        config=bounded_config,
    )

    selected_source = "calibrated_decision_layer"
    selected_predictions = list(calibrated_predictions)
    fallback_reason: str | None = None

    calibrated_edge = float(calibrated_eval["baseline_edge"])
    raw_edge = float(raw_eval["baseline_edge"])

    calibrated_is_worse = calibrated_edge < raw_edge - bounded_config.baseline_edge_tolerance
    calibrated_distribution_bad = not bool(calibrated_eval["distribution_safe"])

    if bounded_config.fallback_to_raw and calibrated_distribution_bad:
        selected_source = "raw_argmax_fallback_distribution_guard"
        selected_predictions = list(raw_predictions)
        fallback_reason = "calibrated_distribution_guard_failed"

    if (
        bounded_config.fallback_to_raw
        and fallback_reason is None
        and bounded_config.require_non_worse_baseline_edge
        and calibrated_is_worse
    ):
        selected_source = "raw_argmax_fallback_baseline_edge_guard"
        selected_predictions = list(raw_predictions)
        fallback_reason = "calibrated_baseline_edge_worse_than_raw"

    selected_eval = evaluate_decision_distribution(
        actual_labels=actual,
        predicted_labels=selected_predictions,
        config=bounded_config,
    )

    return {
        "diagnostic_name": "bounded_calibrated_decision_selection",
        "diagnostic_version": bounded_config.diagnostic_version,
        "enabled": bounded_config.enabled,
        "selected_decision_source": selected_source,
        "fallback_reason": fallback_reason,
        "calibrated_distribution_bad": calibrated_distribution_bad,
        "calibrated_baseline_edge_worse_than_raw": calibrated_is_worse,
        "raw": raw_eval,
        "calibrated": calibrated_eval,
        "selected": selected_eval,
        "selected_predictions": selected_predictions,
        "config": {
            "max_flat_ratio": bounded_config.max_flat_ratio,
            "min_down_ratio_when_actual_down_high": bounded_config.min_down_ratio_when_actual_down_high,
            "min_up_ratio_when_actual_up_high": bounded_config.min_up_ratio_when_actual_up_high,
            "max_dominant_class_ratio": bounded_config.max_dominant_class_ratio,
            "require_non_worse_baseline_edge": bounded_config.require_non_worse_baseline_edge,
            "baseline_edge_tolerance": bounded_config.baseline_edge_tolerance,
            "actual_class_high_threshold": bounded_config.actual_class_high_threshold,
            "fallback_to_raw": bounded_config.fallback_to_raw,
        },
    }


class CalibratedPredictionDecisions:
    DIAGNOSTIC_NAME = "calibrated_prediction_decisions"
    DIAGNOSTIC_VERSION = "ml38_9_4"

    def build_report(
        self,
        *,
        predictions: list[dict[str, Any]],
        label_config: dict[str, Any] | None,
        symbol: str | None = None,
        config_id: str | None = None,
    ) -> dict[str, Any]:
        config = DecisionCalibrationConfig.from_label_config(label_config)
        raw_rows = [dict(row) for row in predictions]
        calibrated_rows = [
            self._calibrate_row(row=dict(row), config=config)
            for row in raw_rows
        ]

        raw_counts = self._counts(raw_rows, key="predicted_label")
        calibrated_counts = self._counts(calibrated_rows, key="predicted_label")
        actual_counts = self._counts(raw_rows, key="actual_label")

        total_rows = len(raw_rows)
        raw_accuracy = self._accuracy(raw_rows)
        calibrated_accuracy = self._accuracy(calibrated_rows)
        baseline_accuracy = self._baseline_accuracy(actual_counts, total_rows)

        actual_labels = [str(row.get("actual_label", "FLAT")).upper() for row in raw_rows]
        raw_predicted_labels = [str(row.get("predicted_label", "FLAT")).upper() for row in raw_rows]
        calibrated_predicted_labels = [
            str(row.get("predicted_label", "FLAT")).upper() for row in calibrated_rows
        ]

        if config.bounded_config().enabled:
            bounded_selection = choose_bounded_calibrated_decisions(
                actual_labels=actual_labels,
                raw_predicted_labels=raw_predicted_labels,
                calibrated_predicted_labels=calibrated_predicted_labels,
                config=config.bounded_config(),
            )
            selected_predictions = list(bounded_selection.get("selected_predictions", calibrated_predicted_labels))
            selected_decision_source = str(
                bounded_selection.get("selected_decision_source") or "calibrated_decision_layer"
            )
        else:
            selected_predictions = list(calibrated_predicted_labels if config.enabled else raw_predicted_labels)
            selected_decision_source = "calibrated_decision_layer" if config.enabled else "raw_argmax"
            bounded_selection = {
                "diagnostic_name": "bounded_calibrated_decision_selection",
                "diagnostic_version": config.diagnostic_version,
                "enabled": False,
                "selected_decision_source": selected_decision_source,
                "fallback_reason": None,
                "raw": evaluate_decision_distribution(
                    actual_labels=actual_labels,
                    predicted_labels=raw_predicted_labels,
                    config=config.bounded_config(),
                ),
                "calibrated": evaluate_decision_distribution(
                    actual_labels=actual_labels,
                    predicted_labels=calibrated_predicted_labels,
                    config=config.bounded_config(),
                ),
                "selected": evaluate_decision_distribution(
                    actual_labels=actual_labels,
                    predicted_labels=selected_predictions,
                    config=config.bounded_config(),
                ),
                "selected_predictions": list(selected_predictions),
                "config": {
                    "max_flat_ratio": config.max_flat_ratio,
                    "min_down_ratio_when_actual_down_high": config.min_down_ratio_when_actual_down_high,
                    "min_up_ratio_when_actual_up_high": config.min_up_ratio_when_actual_up_high,
                    "max_dominant_class_ratio": config.max_dominant_class_ratio,
                    "require_non_worse_baseline_edge": config.require_non_worse_baseline_edge,
                    "baseline_edge_tolerance": config.baseline_edge_tolerance,
                    "actual_class_high_threshold": config.actual_class_high_threshold,
                    "fallback_to_raw": config.fallback_to_raw,
                },
            }

        selected_rows = self._selected_rows(
            source_rows=calibrated_rows if config.enabled else raw_rows,
            selected_predictions=selected_predictions,
            selected_decision_source=selected_decision_source,
        )
        selected_counts = self._counts(selected_rows, key="predicted_label")
        selected_accuracy = self._accuracy(selected_rows)

        return {
            "diagnostic_name": self.DIAGNOSTIC_NAME,
            "diagnostic_version": self.DIAGNOSTIC_VERSION,
            "symbol": symbol,
            "config_id": config_id,
            "enabled": config.enabled,
            "config": {
                "flat_if_max_prob_below": config.flat_if_max_prob_below,
                "flat_if_margin_below": config.flat_if_margin_below,
                "min_direction_prob": config.min_direction_prob,
                "min_up_down_margin": config.min_up_down_margin,
                "down_boost": config.down_boost,
                "up_penalty": config.up_penalty,
                "flat_boost": config.flat_boost,
                "mode": config.mode,
                "fallback_to_raw": config.fallback_to_raw,
                "max_flat_ratio": config.max_flat_ratio,
                "min_down_ratio_when_actual_down_high": config.min_down_ratio_when_actual_down_high,
                "min_up_ratio_when_actual_up_high": config.min_up_ratio_when_actual_up_high,
                "max_dominant_class_ratio": config.max_dominant_class_ratio,
                "require_non_worse_baseline_edge": config.require_non_worse_baseline_edge,
                "baseline_edge_tolerance": config.baseline_edge_tolerance,
                "actual_class_high_threshold": config.actual_class_high_threshold,
                "diagnostic_version": config.diagnostic_version,
            },
            "total_rows": total_rows,
            "raw_predicted_counts": raw_counts,
            "raw_predicted_ratios": self._ratios(raw_counts, total_rows),
            "calibrated_predicted_counts": calibrated_counts,
            "calibrated_predicted_ratios": self._ratios(calibrated_counts, total_rows),
            "selected_predicted_counts": selected_counts,
            "selected_predicted_ratios": self._ratios(selected_counts, total_rows),
            "actual_counts": actual_counts,
            "actual_ratios": self._ratios(actual_counts, total_rows),
            "raw_accuracy": raw_accuracy,
            "calibrated_accuracy": calibrated_accuracy,
            "selected_accuracy": selected_accuracy,
            "baseline_accuracy": baseline_accuracy,
            "raw_baseline_edge": self._edge(raw_accuracy, baseline_accuracy),
            "calibrated_baseline_edge": self._edge(calibrated_accuracy, baseline_accuracy),
            "selected_baseline_edge": self._edge(selected_accuracy, baseline_accuracy),
            "changed_prediction_count": self._changed_count(raw_rows, calibrated_rows),
            "changed_prediction_ratio": self._safe_ratio(self._changed_count(raw_rows, calibrated_rows), total_rows),
            "selected_decision_source": selected_decision_source,
            "bounded_calibrated_decision_selection": bounded_selection,
            "calibrated_rows": calibrated_rows,
            "selected_rows": selected_rows,
        }

    def _calibrate_row(
        self,
        *,
        row: dict[str, Any],
        config: DecisionCalibrationConfig,
    ) -> dict[str, Any]:
        if not config.enabled:
            row["raw_predicted_label"] = row.get("predicted_label")
            row["calibrated_decision_applied"] = False
            return row

        prob_up = self._safe_float(row.get("prob_up"))
        prob_down = self._safe_float(row.get("prob_down"))
        prob_flat = self._safe_float(row.get("prob_flat"))

        adjusted = {
            "UP": prob_up - config.up_penalty,
            "DOWN": prob_down + config.down_boost,
            "FLAT": prob_flat + config.flat_boost,
        }

        raw_probs = {
            "UP": prob_up,
            "DOWN": prob_down,
            "FLAT": prob_flat,
        }

        raw_sorted = sorted(raw_probs.items(), key=lambda item: item[1], reverse=True)
        adjusted_sorted = sorted(adjusted.items(), key=lambda item: item[1], reverse=True)

        raw_top_label, raw_top_prob = raw_sorted[0]
        raw_second_prob = raw_sorted[1][1]
        adjusted_top_label, adjusted_top_prob = adjusted_sorted[0]
        adjusted_second_prob = adjusted_sorted[1][1]

        raw_margin = raw_top_prob - raw_second_prob
        adjusted_margin = adjusted_top_prob - adjusted_second_prob
        up_down_margin = abs(adjusted["UP"] - adjusted["DOWN"])

        predicted_label = adjusted_top_label
        reason = "direction_selected"

        if raw_top_prob < config.flat_if_max_prob_below:
            predicted_label = "FLAT"
            reason = "max_prob_below_threshold"
        elif raw_margin < config.flat_if_margin_below:
            predicted_label = "FLAT"
            reason = "margin_below_threshold"
        elif adjusted_top_label in {"UP", "DOWN"}:
            raw_direction_prob = raw_probs[adjusted_top_label]
            if raw_direction_prob < config.min_direction_prob:
                predicted_label = "FLAT"
                reason = "direction_prob_below_threshold"
            elif up_down_margin < config.min_up_down_margin:
                predicted_label = "FLAT"
                reason = "up_down_margin_below_threshold"

        row["raw_predicted_label"] = row.get("predicted_label")
        row["predicted_label"] = predicted_label
        row["calibrated_decision_applied"] = True
        row["calibrated_decision_reason"] = reason
        row["raw_max_prob"] = raw_top_prob
        row["raw_margin"] = raw_margin
        row["adjusted_top_label"] = adjusted_top_label
        row["adjusted_top_prob"] = adjusted_top_prob
        row["adjusted_margin"] = adjusted_margin
        row["adjusted_prob_up"] = adjusted["UP"]
        row["adjusted_prob_down"] = adjusted["DOWN"]
        row["adjusted_prob_flat"] = adjusted["FLAT"]
        return row

    def _selected_rows(
        self,
        *,
        source_rows: list[dict[str, Any]],
        selected_predictions: Sequence[str],
        selected_decision_source: str,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for row, selected_label in zip(source_rows, selected_predictions):
            selected_row = dict(row)
            selected_row["predicted_label"] = str(selected_label).upper()
            selected_row["selected_decision_source"] = selected_decision_source
            rows.append(selected_row)
        return rows

    def _counts(self, rows: list[dict[str, Any]], *, key: str) -> dict[str, int]:
        counts = {label: 0 for label in LABELS}
        for row in rows:
            label = str(row.get(key, "FLAT")).upper()
            if label not in counts:
                label = "FLAT"
            counts[label] += 1
        return counts

    def _accuracy(self, rows: list[dict[str, Any]]) -> float | None:
        if not rows:
            return None
        correct = sum(
            1
            for row in rows
            if str(row.get("predicted_label")).upper() == str(row.get("actual_label")).upper()
        )
        return correct / len(rows)

    def _baseline_accuracy(self, actual_counts: dict[str, int], total_rows: int) -> float | None:
        if total_rows <= 0:
            return None
        return max(actual_counts.values(), default=0) / total_rows

    def _edge(self, accuracy: float | None, baseline_accuracy: float | None) -> float | None:
        if accuracy is None or baseline_accuracy is None:
            return None
        return accuracy - baseline_accuracy

    def _changed_count(
        self,
        raw_rows: list[dict[str, Any]],
        calibrated_rows: list[dict[str, Any]],
    ) -> int:
        count = 0
        for raw, calibrated in zip(raw_rows, calibrated_rows):
            if str(raw.get("predicted_label")).upper() != str(calibrated.get("predicted_label")).upper():
                count += 1
        return count

    def _ratios(self, counts: dict[str, int], total_rows: int) -> dict[str, float]:
        if total_rows <= 0:
            return {label: 0.0 for label in LABELS}
        return {label: counts.get(label, 0) / total_rows for label in LABELS}

    def _safe_ratio(self, numerator: int | float, denominator: int | float) -> float:
        if denominator <= 0:
            return 0.0
        return float(numerator) / float(denominator)

    def _safe_float(self, value: Any) -> float:
        if value is None:
            return 0.0
        numeric = float(value)
        if numeric != numeric or numeric in {float("inf"), float("-inf")}:
            return 0.0
        return numeric
