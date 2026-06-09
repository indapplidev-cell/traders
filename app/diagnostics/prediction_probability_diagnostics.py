from __future__ import annotations

import math
from typing import Any


class PredictionProbabilityDiagnostics:
    THRESHOLDS = [0.34, 0.36, 0.38, 0.40, 0.42, 0.45, 0.50]
    LABELS = ["UP", "DOWN", "FLAT"]
    QUANTILES = [
        ("q00", 0.00),
        ("q10", 0.10),
        ("q25", 0.25),
        ("q50", 0.50),
        ("q75", 0.75),
        ("q90", 0.90),
        ("q95", 0.95),
        ("q99", 0.99),
        ("q100", 1.00),
    ]

    def build_report(self, model_version: str, predictions: list[dict[str, Any]]) -> dict[str, Any]:
        total_rows = len(predictions)
        predicted_counts = {label: 0 for label in self.LABELS}
        actual_counts = {label: 0 for label in self.LABELS}
        prob_up_values: list[float] = []
        prob_down_values: list[float] = []
        prob_flat_values: list[float] = []
        max_prob_values: list[float] = []
        margin_values: list[float] = []
        entropy_values: list[float] = []
        directional_edge_values: list[float] = []
        up_down_edge_values: list[float] = []

        for row in predictions:
            predicted_counts[row["predicted_label"]] += 1
            actual_counts[row["actual_label"]] += 1

            prob_up = float(row["prob_up"])
            prob_down = float(row["prob_down"])
            prob_flat = float(row["prob_flat"])
            sorted_probabilities = sorted([prob_up, prob_down, prob_flat], reverse=True)

            prob_up_values.append(prob_up)
            prob_down_values.append(prob_down)
            prob_flat_values.append(prob_flat)
            max_prob_values.append(sorted_probabilities[0])
            margin_values.append(sorted_probabilities[0] - sorted_probabilities[1])
            entropy_values.append(self._entropy([prob_up, prob_down, prob_flat]))
            directional_edge_values.append(abs(prob_up - prob_down))
            up_down_edge_values.append(prob_up - prob_down)

        average_probabilities = {
            "avg_prob_up": self._mean(prob_up_values),
            "avg_prob_down": self._mean(prob_down_values),
            "avg_prob_flat": self._mean(prob_flat_values),
        }
        report = {
            "model_version": model_version,
            "total_rows": total_rows,
            "predicted_direction_counts": predicted_counts,
            "predicted_direction_ratios": self._ratios(predicted_counts, total_rows),
            "actual_direction_counts": actual_counts,
            "actual_direction_ratios": self._ratios(actual_counts, total_rows),
            **average_probabilities,
            **self._build_quantile_block("max_prob", max_prob_values),
            **self._build_quantile_block("margin", margin_values),
            **self._build_quantile_block("entropy", entropy_values),
            **self._build_quantile_block("directional_edge", directional_edge_values),
            **self._build_quantile_block("up_down_edge", up_down_edge_values),
            "flat_dominance": average_probabilities["avg_prob_flat"]
            - max(average_probabilities["avg_prob_up"], average_probabilities["avg_prob_down"]),
            "top_class_by_threshold": self._top_class_by_threshold(predictions),
        }
        report["rows_above_thresholds"] = {
            f"{item['threshold']:.2f}": item["rows_above_threshold"] for item in report["top_class_by_threshold"]
        }
        return report

    def _top_class_by_threshold(self, predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows = []
        for threshold in self.THRESHOLDS:
            selected = [row for row in predictions if float(row["confidence"]) >= threshold]
            counts = {label: 0 for label in self.LABELS}
            for row in selected:
                counts[row["predicted_label"]] += 1
            rows.append(
                {
                    "threshold": threshold,
                    "rows_above_threshold": len(selected),
                    "predicted_direction_counts": counts,
                }
            )
        return rows

    def _build_quantile_block(self, prefix: str, values: list[float]) -> dict[str, float | None]:
        return {f"{prefix}_{name}": self._quantile(values, fraction) for name, fraction in self.QUANTILES}

    @staticmethod
    def _ratios(counts: dict[str, int], total_rows: int) -> dict[str, float]:
        if total_rows == 0:
            return {label: 0.0 for label in counts}
        return {label: counts[label] / total_rows for label in counts}

    @staticmethod
    def _mean(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    @staticmethod
    def _entropy(probabilities: list[float]) -> float:
        entropy = 0.0
        for probability in probabilities:
            if probability > 0:
                entropy -= probability * math.log(probability)
        return entropy

    @staticmethod
    def _quantile(values: list[float], fraction: float) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        if len(ordered) == 1:
            return ordered[0]
        position = fraction * (len(ordered) - 1)
        lower_index = int(math.floor(position))
        upper_index = int(math.ceil(position))
        if lower_index == upper_index:
            return ordered[lower_index]
        lower_value = ordered[lower_index]
        upper_value = ordered[upper_index]
        weight = position - lower_index
        return lower_value + (upper_value - lower_value) * weight
