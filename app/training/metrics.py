from __future__ import annotations

import math
from typing import Any

from app.training.two_stage_thresholds import compute_opportunity_threshold_metrics


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
        direction_mask: list[bool] | None = None,
        opportunity_probabilities: list[float] | None = None,
        opportunity_targets: list[int] | None = None,
        opportunity_probability_threshold: float = 0.5,
        training_objective: str = "direction_global",
    ) -> dict[str, Any]:
        if training_objective == "trade_two_stage":
            return self._compute_trade_two_stage_metrics(
                direction_probabilities=direction_probabilities,
                direction_targets=direction_targets,
                tp_sl_probabilities=tp_sl_probabilities,
                tp_sl_targets=tp_sl_targets,
                expected_move_predictions=expected_move_predictions,
                expected_move_targets=expected_move_targets,
                opportunity_probabilities=opportunity_probabilities,
                opportunity_targets=opportunity_targets,
                opportunity_probability_threshold=opportunity_probability_threshold,
            )
        masked_direction_probabilities, masked_direction_targets = self._apply_direction_mask(
            direction_probabilities=direction_probabilities,
            direction_targets=direction_targets,
            direction_mask=direction_mask,
        )
        predicted_classes = [self._argmax(probabilities) for probabilities in masked_direction_probabilities]
        correct = sum(int(predicted == target) for predicted, target in zip(predicted_classes, masked_direction_targets))
        accuracy = correct / len(masked_direction_targets) if masked_direction_targets else 0.0

        confusion_matrix = [[0, 0, 0] for _ in range(3)]
        for predicted, target in zip(predicted_classes, masked_direction_targets):
            confusion_matrix[target][predicted] += 1

        precision_up = self._precision_for_class(confusion_matrix, LABEL_TO_INDEX["UP"])
        precision_down = self._precision_for_class(confusion_matrix, LABEL_TO_INDEX["DOWN"])
        brier_score = self._brier_score(masked_direction_probabilities, masked_direction_targets)
        tp_before_sl_accuracy = self._tp_accuracy(tp_sl_probabilities, tp_sl_targets)
        average_expected_move_error = self._average_absolute_error(expected_move_predictions, expected_move_targets)
        opportunity_accuracy = self._binary_accuracy(opportunity_probabilities, opportunity_targets)
        opportunity_positive_rate = (
            sum(int(probability >= 0.5) for probability in (opportunity_probabilities or [])) / len(opportunity_probabilities)
            if opportunity_probabilities
            else None
        )

        metrics = {
            "accuracy": accuracy,
            "precision_up": precision_up,
            "precision_down": precision_down,
            "confusion_matrix": confusion_matrix,
            "brier_score": brier_score,
            "tp_before_sl_accuracy": tp_before_sl_accuracy,
            "average_expected_move_error": average_expected_move_error,
            "direction_evaluation_rows": len(masked_direction_targets),
        }
        if opportunity_accuracy is not None:
            metrics["opportunity_accuracy"] = opportunity_accuracy
        if opportunity_positive_rate is not None:
            metrics["opportunity_positive_rate"] = opportunity_positive_rate
        return metrics

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

    @staticmethod
    def _apply_direction_mask(
        *,
        direction_probabilities: list[list[float]],
        direction_targets: list[int],
        direction_mask: list[bool] | None,
    ) -> tuple[list[list[float]], list[int]]:
        if not direction_mask:
            return direction_probabilities, direction_targets
        filtered_probabilities: list[list[float]] = []
        filtered_targets: list[int] = []
        for probabilities, target, keep in zip(direction_probabilities, direction_targets, direction_mask):
            if keep:
                filtered_probabilities.append(probabilities)
                filtered_targets.append(target)
        return filtered_probabilities, filtered_targets

    @staticmethod
    def _binary_accuracy(probabilities: list[float] | None, targets: list[int] | None) -> float | None:
        if probabilities is None or targets is None or not targets:
            return None
        correct = 0
        for probability, target in zip(probabilities, targets):
            correct += int((probability >= 0.5) == bool(target))
        return correct / len(targets)

    def _compute_trade_two_stage_metrics(
        self,
        *,
        direction_probabilities: list[list[float]],
        direction_targets: list[int],
        tp_sl_probabilities: list[float],
        tp_sl_targets: list[bool | None],
        expected_move_predictions: list[float],
        expected_move_targets: list[float],
        opportunity_probabilities: list[float] | None,
        opportunity_targets: list[int] | None,
        opportunity_probability_threshold: float = 0.5,
    ) -> dict[str, Any]:
        predicted_classes = [self._argmax(probabilities) for probabilities in direction_probabilities]
        confusion_matrix = [[0, 0, 0] for _ in range(3)]
        for predicted, target in zip(predicted_classes, direction_targets):
            confusion_matrix[target][predicted] += 1

        trade_mask = [target in {0, 1} for target in direction_targets]
        direction_trade_rows = sum(int(value) for value in trade_mask)
        trade_row_ratio = direction_trade_rows / len(direction_targets) if direction_targets else 0.0
        no_trade_row_ratio = 1.0 - trade_row_ratio if direction_targets else 0.0

        direction_correct = 0
        predicted_trade_labels: list[int] = []
        actual_trade_labels: list[int] = []
        for probabilities, target, is_trade_row in zip(direction_probabilities, direction_targets, trade_mask):
            if not is_trade_row:
                continue
            predicted_binary = 0 if probabilities[0] >= probabilities[1] else 1
            actual_binary = 0 if target == 0 else 1
            predicted_trade_labels.append(predicted_binary)
            actual_trade_labels.append(actual_binary)
            direction_correct += int(predicted_binary == actual_binary)
        direction_accuracy_on_trade_rows = direction_correct / direction_trade_rows if direction_trade_rows else 0.0

        opportunity_probabilities = opportunity_probabilities or []
        opportunity_targets = opportunity_targets or []
        threshold = float(opportunity_probability_threshold)
        predicted_trade_flags = [int(probability >= threshold) for probability in opportunity_probabilities]
        actual_trade_flags = [int(target) for target in opportunity_targets]
        opportunity_threshold_metrics = compute_opportunity_threshold_metrics(
            opportunity_probabilities,
            opportunity_targets,
            threshold=threshold,
        )
        predicted_trade_rate = opportunity_threshold_metrics.predicted_trade_rate
        actual_trade_rate = (
            opportunity_threshold_metrics.actual_trade_rate
            if opportunity_threshold_metrics.row_count > 0
            else trade_row_ratio
        )
        predicted_to_actual_trade_rate_ratio = (
            opportunity_threshold_metrics.predicted_to_actual_trade_rate_ratio
            if opportunity_threshold_metrics.row_count > 0
            else (0.0 if trade_row_ratio == 0.0 else predicted_trade_rate / trade_row_ratio)
        )

        true_positive_count = opportunity_threshold_metrics.true_positive_count
        false_positive_count = opportunity_threshold_metrics.false_positive_count
        false_negative_count = opportunity_threshold_metrics.false_negative_count
        true_negative_count = opportunity_threshold_metrics.true_negative_count
        two_stage_confusion_matrix = [[0, 0, 0] for _ in range(3)]
        two_stage_correct = 0
        for index, actual_trade in enumerate(actual_trade_flags):
            predicted_trade = predicted_trade_flags[index]
            actual_class = 0 if actual_trade == 0 else (1 if direction_targets[index] == 0 else 2)
            if predicted_trade == 0:
                predicted_class = 0
            else:
                predicted_class = 1 if direction_probabilities[index][0] >= direction_probabilities[index][1] else 2
            two_stage_confusion_matrix[actual_class][predicted_class] += 1
            two_stage_correct += int(actual_class == predicted_class)

        opportunity_accuracy = opportunity_threshold_metrics.accuracy
        opportunity_precision = opportunity_threshold_metrics.precision
        opportunity_recall = opportunity_threshold_metrics.recall
        opportunity_f1 = opportunity_threshold_metrics.f1
        opportunity_false_positive_rate = opportunity_threshold_metrics.false_positive_rate
        two_stage_accuracy = two_stage_correct / len(actual_trade_flags) if actual_trade_flags else 0.0

        return {
            "accuracy": two_stage_accuracy,
            "two_stage_accuracy": two_stage_accuracy,
            "precision_up": self._precision_for_class(confusion_matrix, LABEL_TO_INDEX["UP"]),
            "precision_down": self._precision_for_class(confusion_matrix, LABEL_TO_INDEX["DOWN"]),
            "confusion_matrix": confusion_matrix,
            "two_stage_confusion_matrix": two_stage_confusion_matrix,
            "brier_score": self._brier_score(direction_probabilities, direction_targets),
            "tp_before_sl_accuracy": self._tp_accuracy(tp_sl_probabilities, tp_sl_targets),
            "average_expected_move_error": self._average_absolute_error(expected_move_predictions, expected_move_targets),
            "direction_evaluation_rows": direction_trade_rows,
            "direction_trade_rows": direction_trade_rows,
            "direction_accuracy_on_trade_rows": direction_accuracy_on_trade_rows,
            "trade_row_ratio": trade_row_ratio,
            "no_trade_row_ratio": no_trade_row_ratio,
            "opportunity_probability_threshold": threshold,
            "predicted_trade_rate": predicted_trade_rate,
            "actual_trade_rate": actual_trade_rate,
            "predicted_to_actual_trade_rate_ratio": predicted_to_actual_trade_rate_ratio,
            "opportunity_accuracy": opportunity_accuracy,
            "opportunity_precision": opportunity_precision,
            "opportunity_recall": opportunity_recall,
            "opportunity_f1": opportunity_f1,
            "opportunity_false_positive_rate": opportunity_false_positive_rate,
            "opportunity_true_positive_count": true_positive_count,
            "opportunity_false_positive_count": false_positive_count,
            "opportunity_false_negative_count": false_negative_count,
            "opportunity_true_negative_count": true_negative_count,
            "opportunity_positive_rate": predicted_trade_rate,
        }
