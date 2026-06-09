from __future__ import annotations

import math
from typing import Any


LABEL_TO_INDEX = {"UP": 0, "DOWN": 1, "FLAT": 2}
INDEX_TO_LABEL = {0: "UP", 1: "DOWN", 2: "FLAT"}


class TrainingMetrics:
    def compute(
        self,
        direction_probabilities: list[list[float]],
        direction_targets: list[int],
        tp_sl_probabilities: list[float],
        tp_sl_targets: list[bool | None],
        expected_move_predictions: list[float],
        expected_move_targets: list[float],
    ) -> dict[str, Any]:
        predicted_classes = [self._argmax(probabilities) for probabilities in direction_probabilities]
        correct = sum(int(predicted == target) for predicted, target in zip(predicted_classes, direction_targets))
        accuracy = correct / len(direction_targets) if direction_targets else 0.0

        confusion_matrix = [[0, 0, 0] for _ in range(3)]
        for predicted, target in zip(predicted_classes, direction_targets):
            confusion_matrix[target][predicted] += 1

        precision_up = self._precision_for_class(confusion_matrix, LABEL_TO_INDEX["UP"])
        precision_down = self._precision_for_class(confusion_matrix, LABEL_TO_INDEX["DOWN"])
        brier_score = self._brier_score(direction_probabilities, direction_targets)
        tp_before_sl_accuracy = self._tp_accuracy(tp_sl_probabilities, tp_sl_targets)
        average_expected_move_error = self._average_absolute_error(expected_move_predictions, expected_move_targets)

        return {
            "accuracy": accuracy,
            "precision_up": precision_up,
            "precision_down": precision_down,
            "confusion_matrix": confusion_matrix,
            "brier_score": brier_score,
            "tp_before_sl_accuracy": tp_before_sl_accuracy,
            "average_expected_move_error": average_expected_move_error,
        }

    @staticmethod
    def _argmax(probabilities: list[float]) -> int:
        return max(range(len(probabilities)), key=lambda index: probabilities[index])

    @staticmethod
    def _precision_for_class(confusion_matrix: list[list[int]], class_index: int) -> float:
        true_positive = confusion_matrix[class_index][class_index]
        predicted_positive = sum(row[class_index] for row in confusion_matrix)
        if predicted_positive == 0:
            return 0.0
        return true_positive / predicted_positive

    @staticmethod
    def _brier_score(direction_probabilities: list[list[float]], direction_targets: list[int]) -> float:
        if not direction_targets:
            return 0.0
        total = 0.0
        for probabilities, target in zip(direction_probabilities, direction_targets):
            total += sum((probability - (1.0 if index == target else 0.0)) ** 2 for index, probability in enumerate(probabilities))
        return total / len(direction_targets)

    @staticmethod
    def _tp_accuracy(probabilities: list[float], targets: list[bool | None]) -> float | None:
        filtered = [(probability, target) for probability, target in zip(probabilities, targets) if target is not None]
        if not filtered:
            return None
        correct = 0
        for probability, target in filtered:
            predicted = probability >= 0.5
            correct += int(predicted == target)
        return correct / len(filtered)

    @staticmethod
    def _average_absolute_error(predictions: list[float], targets: list[float]) -> float:
        if not targets:
            return 0.0
        return sum(abs(prediction - target) for prediction, target in zip(predictions, targets)) / len(targets)
