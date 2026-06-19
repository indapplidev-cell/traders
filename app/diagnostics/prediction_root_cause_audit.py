from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

CLASSES: tuple[str, str, str] = ("DOWN", "FLAT", "UP")


@dataclass(frozen=True)
class RootCauseThresholds:
    max_dominant_prediction_ratio: float = 0.75
    min_predicted_down_when_actual_down_high: float = 0.12
    min_predicted_flat_when_actual_flat_high: float = 0.08
    actual_class_high_threshold: float = 0.25
    actual_down_to_up_warning_ratio: float = 0.45
    actual_flat_to_up_warning_ratio: float = 0.45
    up_predictions_wrong_side_warning_ratio: float = 0.45


def _safe_ratio(value: float, total: float) -> float:
    if total <= 0:
        return 0.0
    return float(value) / float(total)


def _normalize_label(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text in {"SHORT", "SELL"}:
        return "DOWN"
    if text in {"LONG", "BUY"}:
        return "UP"
    if text in {"NONE", "HOLD", "NO_TRADE"}:
        return "FLAT"
    if text in CLASSES:
        return text
    return "FLAT"


def _distribution(labels: Sequence[str]) -> dict[str, Any]:
    normalized = [_normalize_label(label) for label in labels]
    counts = Counter(normalized)
    total = len(normalized)
    ratios = {label: _safe_ratio(counts.get(label, 0), total) for label in CLASSES}
    return {
        "counts": {label: int(counts.get(label, 0)) for label in CLASSES},
        "ratios": ratios,
        "total": int(total),
    }


def _extract_probability(row: Any, label: str) -> float:
    if row is None:
        return 0.0
    key_variants = (
        label,
        label.lower(),
        f"prob_{label}",
        f"prob_{label.lower()}",
        f"probability_{label}",
        f"probability_{label.lower()}",
        f"{label.lower()}_probability",
        f"{label.lower()}_prob",
    )
    if isinstance(row, Mapping):
        for key in key_variants:
            if key in row:
                try:
                    return float(row[key])
                except (TypeError, ValueError):
                    return 0.0
    for key in key_variants:
        if hasattr(row, key):
            try:
                return float(getattr(row, key))
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def _probability_dict(row: Any) -> dict[str, float]:
    return {label: _extract_probability(row, label) for label in CLASSES}


def _mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return float(sum(values)) / float(len(values))


def _quantile(values: Sequence[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(v) for v in values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _quantiles(values: Sequence[float]) -> dict[str, float]:
    return {
        "q10": _quantile(values, 0.10),
        "q25": _quantile(values, 0.25),
        "q50": _quantile(values, 0.50),
        "q75": _quantile(values, 0.75),
        "q90": _quantile(values, 0.90),
    }


class PredictionRootCauseAuditor:
    """Diagnostic-only audit of probability collapse and wrong-side predictions."""

    diagnostic_name = "prediction_root_cause_audit"
    diagnostic_version = "ml38_9_6"

    def __init__(self, thresholds: RootCauseThresholds | None = None) -> None:
        self.thresholds = thresholds or RootCauseThresholds()

    def build(
        self,
        *,
        actual_labels: Sequence[Any],
        predicted_labels: Sequence[Any],
        probability_rows: Sequence[Any] | None = None,
        split_names: Sequence[Any] | None = None,
        regime_labels: Sequence[Any] | None = None,
        timestamps: Sequence[Any] | None = None,
        symbol: str | None = None,
        config_id: str | None = None,
        decision_source: str | None = None,
    ) -> dict[str, Any]:
        actual = [_normalize_label(label) for label in actual_labels]
        predicted = [_normalize_label(label) for label in predicted_labels]
        n = min(len(actual), len(predicted))
        actual = actual[:n]
        predicted = predicted[:n]
        probability_rows = list(probability_rows or [])[:n]

        if not probability_rows:
            probability_rows = [{label: 0.0 for label in CLASSES} for _ in range(n)]

        actual_distribution = _distribution(actual)
        predicted_distribution = _distribution(predicted)
        confusion = self._confusion_matrix(actual, predicted)
        per_actual_probability = self._per_actual_probability_stats(actual, probability_rows)
        up_collapse_signature = self._up_collapse_signature(actual, predicted, probability_rows)
        split_drift = self._split_drift(actual, split_names)
        regime_breakdown = self._regime_breakdown(actual, predicted, regime_labels)

        warnings = self._warnings(
            actual_distribution=actual_distribution,
            predicted_distribution=predicted_distribution,
            up_collapse_signature=up_collapse_signature,
        )
        recommendations = self._recommendations(warnings)

        return {
            "diagnostic_name": self.diagnostic_name,
            "diagnostic_version": self.diagnostic_version,
            "symbol": symbol,
            "config_id": config_id,
            "decision_source": decision_source,
            "row_count": int(n),
            "actual_distribution": actual_distribution,
            "predicted_distribution": predicted_distribution,
            "confusion_matrix": confusion,
            "per_actual_probability_stats": per_actual_probability,
            "up_collapse_signature": up_collapse_signature,
            "split_drift": split_drift,
            "regime_breakdown": regime_breakdown,
            "warnings": warnings,
            "recommendations": recommendations,
            "diagnostic_only": True,
        }

    def _confusion_matrix(self, actual: Sequence[str], predicted: Sequence[str]) -> dict[str, Any]:
        counts: dict[str, dict[str, int]] = {
            actual_label: {predicted_label: 0 for predicted_label in CLASSES}
            for actual_label in CLASSES
        }
        for actual_label, predicted_label in zip(actual, predicted):
            counts[actual_label][predicted_label] += 1
        ratios: dict[str, dict[str, float]] = {}
        for actual_label in CLASSES:
            row_total = sum(counts[actual_label].values())
            ratios[actual_label] = {
                predicted_label: _safe_ratio(count, row_total)
                for predicted_label, count in counts[actual_label].items()
            }
        return {"counts": counts, "row_ratios": ratios}

    def _per_actual_probability_stats(
        self,
        actual: Sequence[str],
        probability_rows: Sequence[Any],
    ) -> dict[str, Any]:
        grouped: dict[str, dict[str, list[float]]] = {
            actual_label: {prob_label: [] for prob_label in CLASSES}
            for actual_label in CLASSES
        }
        margins_by_actual: dict[str, list[float]] = {label: [] for label in CLASSES}
        max_prob_by_actual: dict[str, list[float]] = {label: [] for label in CLASSES}

        for actual_label, row in zip(actual, probability_rows):
            probs = _probability_dict(row)
            for prob_label in CLASSES:
                grouped[actual_label][prob_label].append(probs[prob_label])
            sorted_probs = sorted(probs.values(), reverse=True)
            max_prob_by_actual[actual_label].append(sorted_probs[0] if sorted_probs else 0.0)
            if len(sorted_probs) >= 2:
                margins_by_actual[actual_label].append(sorted_probs[0] - sorted_probs[1])
            else:
                margins_by_actual[actual_label].append(0.0)

        result: dict[str, Any] = {}
        for actual_label in CLASSES:
            result[actual_label] = {
                "row_count": len(grouped[actual_label][actual_label]),
                "mean_probability_by_class": {
                    prob_label: _mean(values)
                    for prob_label, values in grouped[actual_label].items()
                },
                "probability_quantiles_by_class": {
                    prob_label: _quantiles(values)
                    for prob_label, values in grouped[actual_label].items()
                },
                "max_probability_quantiles": _quantiles(max_prob_by_actual[actual_label]),
                "margin_quantiles": _quantiles(margins_by_actual[actual_label]),
            }
        return result

    def _up_collapse_signature(
        self,
        actual: Sequence[str],
        predicted: Sequence[str],
        probability_rows: Sequence[Any],
    ) -> dict[str, Any]:
        actual_counts = Counter(actual)
        predicted_counts = Counter(predicted)
        actual_down_predicted_up = sum(
            1 for a, p in zip(actual, predicted) if a == "DOWN" and p == "UP"
        )
        actual_flat_predicted_up = sum(
            1 for a, p in zip(actual, predicted) if a == "FLAT" and p == "UP"
        )
        predicted_up_actual_down_or_flat = sum(
            1 for a, p in zip(actual, predicted) if p == "UP" and a in {"DOWN", "FLAT"}
        )
        predicted_up_total = predicted_counts.get("UP", 0)

        up_probs_when_actual_down: list[float] = []
        up_probs_when_actual_flat: list[float] = []
        down_probs_when_actual_down: list[float] = []
        flat_probs_when_actual_flat: list[float] = []
        for actual_label, row in zip(actual, probability_rows):
            probs = _probability_dict(row)
            if actual_label == "DOWN":
                up_probs_when_actual_down.append(probs["UP"])
                down_probs_when_actual_down.append(probs["DOWN"])
            if actual_label == "FLAT":
                up_probs_when_actual_flat.append(probs["UP"])
                flat_probs_when_actual_flat.append(probs["FLAT"])

        return {
            "actual_down_predicted_up_count": int(actual_down_predicted_up),
            "actual_down_predicted_up_ratio": _safe_ratio(
                actual_down_predicted_up,
                actual_counts.get("DOWN", 0),
            ),
            "actual_flat_predicted_up_count": int(actual_flat_predicted_up),
            "actual_flat_predicted_up_ratio": _safe_ratio(
                actual_flat_predicted_up,
                actual_counts.get("FLAT", 0),
            ),
            "predicted_up_actual_down_or_flat_count": int(predicted_up_actual_down_or_flat),
            "predicted_up_actual_down_or_flat_share": _safe_ratio(
                predicted_up_actual_down_or_flat,
                predicted_up_total,
            ),
            "up_probability_when_actual_down_quantiles": _quantiles(up_probs_when_actual_down),
            "up_probability_when_actual_flat_quantiles": _quantiles(up_probs_when_actual_flat),
            "down_probability_when_actual_down_quantiles": _quantiles(down_probs_when_actual_down),
            "flat_probability_when_actual_flat_quantiles": _quantiles(flat_probs_when_actual_flat),
        }

    def _split_drift(
        self,
        actual: Sequence[str],
        split_names: Sequence[Any] | None,
    ) -> dict[str, Any]:
        if not split_names:
            return {"available": False, "reason": "split_names_not_provided"}
        rows = list(split_names)[: len(actual)]
        grouped: dict[str, list[str]] = defaultdict(list)
        for label, split_name in zip(actual, rows):
            grouped[str(split_name or "unknown")].append(label)
        return {
            "available": True,
            "splits": {split: _distribution(labels) for split, labels in grouped.items()},
        }

    def _regime_breakdown(
        self,
        actual: Sequence[str],
        predicted: Sequence[str],
        regime_labels: Sequence[Any] | None,
    ) -> dict[str, Any]:
        if not regime_labels:
            return {"available": False, "reason": "regime_labels_not_provided"}
        regimes = list(regime_labels)[: len(actual)]
        grouped_actual: dict[str, list[str]] = defaultdict(list)
        grouped_predicted: dict[str, list[str]] = defaultdict(list)
        for actual_label, predicted_label, regime in zip(actual, predicted, regimes):
            key = str(regime or "unknown")
            grouped_actual[key].append(actual_label)
            grouped_predicted[key].append(predicted_label)
        return {
            "available": True,
            "regimes": {
                regime: {
                    "actual_distribution": _distribution(grouped_actual[regime]),
                    "predicted_distribution": _distribution(grouped_predicted[regime]),
                }
                for regime in sorted(grouped_actual)
            },
        }

    def _warnings(
        self,
        *,
        actual_distribution: Mapping[str, Any],
        predicted_distribution: Mapping[str, Any],
        up_collapse_signature: Mapping[str, Any],
    ) -> list[str]:
        warnings: list[str] = []
        actual_ratios = actual_distribution.get("ratios", {})
        predicted_ratios = predicted_distribution.get("ratios", {})
        dominant_label = max(CLASSES, key=lambda label: predicted_ratios.get(label, 0.0))
        dominant_ratio = float(predicted_ratios.get(dominant_label, 0.0))

        if dominant_ratio > self.thresholds.max_dominant_prediction_ratio:
            warnings.append(f"dominant_prediction_collapse:{dominant_label}:{dominant_ratio:.4f}")
        if (
            actual_ratios.get("DOWN", 0.0) >= self.thresholds.actual_class_high_threshold
            and predicted_ratios.get("DOWN", 0.0)
            < self.thresholds.min_predicted_down_when_actual_down_high
        ):
            warnings.append("down_underprediction_when_actual_down_is_high")
        if (
            actual_ratios.get("FLAT", 0.0) >= self.thresholds.actual_class_high_threshold
            and predicted_ratios.get("FLAT", 0.0)
            < self.thresholds.min_predicted_flat_when_actual_flat_high
        ):
            warnings.append("flat_underprediction_when_actual_flat_is_high")
        if (
            up_collapse_signature.get("actual_down_predicted_up_ratio", 0.0)
            >= self.thresholds.actual_down_to_up_warning_ratio
        ):
            warnings.append("actual_down_rows_mapped_to_up")
        if (
            up_collapse_signature.get("actual_flat_predicted_up_ratio", 0.0)
            >= self.thresholds.actual_flat_to_up_warning_ratio
        ):
            warnings.append("actual_flat_rows_mapped_to_up")
        if (
            up_collapse_signature.get("predicted_up_actual_down_or_flat_share", 0.0)
            >= self.thresholds.up_predictions_wrong_side_warning_ratio
        ):
            warnings.append("predicted_up_often_actual_down_or_flat")
        return warnings

    def _recommendations(self, warnings: Sequence[str]) -> list[str]:
        recommendations: list[str] = []
        warning_set = set(warnings)
        if "actual_down_rows_mapped_to_up" in warning_set:
            recommendations.append(
                "Inspect per-actual DOWN probability stats: model may not separate DOWN setups from UP setups."
            )
        if "flat_underprediction_when_actual_flat_is_high" in warning_set:
            recommendations.append(
                "Inspect FLAT labels and probability floor: model may be over-forced into directional decisions."
            )
        if any(w.startswith("dominant_prediction_collapse") for w in warning_set):
            recommendations.append(
                "Do not add more post-model policies until raw probability class separation is diagnosed."
            )
        if not recommendations:
            recommendations.append("No major root-cause signature detected by ML38.9.6 audit.")
        return recommendations
