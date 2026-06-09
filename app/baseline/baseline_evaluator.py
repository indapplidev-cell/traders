from __future__ import annotations

from collections import Counter
from typing import Any

from app.dataset.dataset_models import DatasetRow
from app.training.metrics import LABEL_TO_INDEX


class BaselineEvaluator:
    LABELS = ["UP", "DOWN", "FLAT"]

    def evaluate(self, rows: list[DatasetRow], predicted_labels: list[str]) -> dict[str, Any]:
        actual_labels = [row.direction_label for row in rows]
        confusion_matrix = [[0, 0, 0] for _ in range(3)]
        correct = 0
        brier_total = 0.0

        for actual_label, predicted_label in zip(actual_labels, predicted_labels):
            actual_index = LABEL_TO_INDEX[actual_label]
            predicted_index = LABEL_TO_INDEX[predicted_label]
            confusion_matrix[actual_index][predicted_index] += 1
            correct += int(actual_index == predicted_index)

            probabilities = [0.0, 0.0, 0.0]
            probabilities[predicted_index] = 1.0
            brier_total += sum(
                (probability - (1.0 if index == actual_index else 0.0)) ** 2
                for index, probability in enumerate(probabilities)
            )

        predicted_counts = Counter(predicted_labels)
        actual_counts = Counter(actual_labels)
        total = len(rows)
        return {
            "accuracy": (correct / total) if total else 0.0,
            "precision_up": self._precision_for_class(confusion_matrix, LABEL_TO_INDEX["UP"]),
            "precision_down": self._precision_for_class(confusion_matrix, LABEL_TO_INDEX["DOWN"]),
            "confusion_matrix": confusion_matrix,
            "brier_score": (brier_total / total) if total else 0.0,
            "predicted_counts": {label: predicted_counts.get(label, 0) for label in self.LABELS},
            "actual_counts": {label: actual_counts.get(label, 0) for label in self.LABELS},
            "rows": total,
        }

    @staticmethod
    def _precision_for_class(confusion_matrix: list[list[int]], class_index: int) -> float:
        true_positive = confusion_matrix[class_index][class_index]
        predicted_positive = sum(row[class_index] for row in confusion_matrix)
        if predicted_positive == 0:
            return 0.0
        return true_positive / predicted_positive
