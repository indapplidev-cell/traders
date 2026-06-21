from __future__ import annotations

from typing import Any

from app.training.two_stage_thresholds import OpportunityThresholdMetrics


LABEL_TO_INDEX = {"UP": 0, "DOWN": 1, "FLAT": 2}
INDEX_TO_LABEL = {0: "UP", 1: "DOWN", 2: "FLAT"}
SETUP_QUALITY_BUCKETS = (
    ("missing_or_zero", None, 0.0),
    ("low_0_00_0_40", 0.0, 0.40),
    ("mid_0_40_0_60", 0.40, 0.60),
    ("good_0_60_0_75", 0.60, 0.75),
    ("strong_0_75_1_00", 0.75, 1.01),
)


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
        setup_quality_scores: list[float] | None = None,
        setup_quality_min_threshold: float | None = None,
        setup_quality_decision_mask_enabled: bool = False,
        setup_quality_decision_mask_min_threshold: float | None = None,
        entry_path_quality_filter_enabled: bool = False,
        entry_path_quality_scores: list[float] | None = None,
        stop_pressure_risk_scores: list[float] | None = None,
        entry_path_quality_min_threshold: float | None = None,
        stop_pressure_max_risk_score: float | None = None,
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
                setup_quality_scores=setup_quality_scores,
                setup_quality_min_threshold=setup_quality_min_threshold,
                setup_quality_decision_mask_enabled=setup_quality_decision_mask_enabled,
                setup_quality_decision_mask_min_threshold=setup_quality_decision_mask_min_threshold,
                entry_path_quality_filter_enabled=entry_path_quality_filter_enabled,
                entry_path_quality_scores=entry_path_quality_scores,
                stop_pressure_risk_scores=stop_pressure_risk_scores,
                entry_path_quality_min_threshold=entry_path_quality_min_threshold,
                stop_pressure_max_risk_score=stop_pressure_max_risk_score,
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
        setup_quality_scores: list[float] | None = None,
        setup_quality_min_threshold: float | None = None,
        setup_quality_decision_mask_enabled: bool = False,
        setup_quality_decision_mask_min_threshold: float | None = None,
        entry_path_quality_filter_enabled: bool = False,
        entry_path_quality_scores: list[float] | None = None,
        stop_pressure_risk_scores: list[float] | None = None,
        entry_path_quality_min_threshold: float | None = None,
        stop_pressure_max_risk_score: float | None = None,
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
        actual_trade_flags = [int(target) for target in opportunity_targets]
        decision_mask_payload = self.apply_setup_quality_decision_mask(
            opportunity_probabilities=opportunity_probabilities,
            setup_quality_scores=setup_quality_scores,
            probability_threshold=threshold,
            setup_quality_decision_mask_enabled=setup_quality_decision_mask_enabled,
            setup_quality_decision_mask_min_threshold=(
                setup_quality_decision_mask_min_threshold
                if setup_quality_decision_mask_min_threshold is not None
                else setup_quality_min_threshold
            ),
        )
        raw_predicted_trade_flags = list(decision_mask_payload["raw_predicted_trade_flags"])
        setup_masked_trade_flags = list(decision_mask_payload["masked_predicted_trade_flags"])
        entry_path_mask_payload = self.apply_entry_path_quality_decision_mask(
            predicted_trade_flags=setup_masked_trade_flags,
            entry_path_quality_scores=entry_path_quality_scores,
            stop_pressure_risk_scores=stop_pressure_risk_scores,
            entry_path_quality_filter_enabled=entry_path_quality_filter_enabled,
            entry_path_quality_min_threshold=entry_path_quality_min_threshold,
            stop_pressure_max_risk_score=stop_pressure_max_risk_score,
        )
        predicted_trade_flags = list(entry_path_mask_payload["masked_predicted_trade_flags"])
        raw_opportunity_threshold_metrics = self._compute_binary_trade_metrics(
            predicted_trade_flags=raw_predicted_trade_flags,
            actual_trade_flags=actual_trade_flags,
            threshold=threshold,
            fallback_actual_trade_rate=trade_row_ratio,
        )
        opportunity_threshold_metrics = self._compute_binary_trade_metrics(
            predicted_trade_flags=predicted_trade_flags,
            actual_trade_flags=actual_trade_flags,
            threshold=threshold,
            fallback_actual_trade_rate=trade_row_ratio,
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
        setup_quality_bucket_metrics_raw = self._compute_setup_quality_bucket_metrics(
            setup_quality_scores=setup_quality_scores or [],
            predicted_trade_flags=raw_predicted_trade_flags,
            actual_trade_flags=actual_trade_flags,
        )
        setup_quality_bucket_metrics = self._compute_setup_quality_bucket_metrics(
            setup_quality_scores=setup_quality_scores or [],
            predicted_trade_flags=predicted_trade_flags,
            actual_trade_flags=actual_trade_flags,
        )
        setup_quality_distribution = {
            bucket_name: {
                "row_count": int(bucket_metrics["row_count"]),
                "row_rate": (
                    float(bucket_metrics["row_count"]) / float(len(actual_trade_flags))
                    if actual_trade_flags
                    else 0.0
                ),
            }
            for bucket_name, bucket_metrics in setup_quality_bucket_metrics.items()
        }
        setup_quality_filter_summary = self._compute_setup_quality_filter_summary(
            setup_quality_scores=setup_quality_scores or [],
            predicted_trade_flags=predicted_trade_flags,
            actual_trade_flags=actual_trade_flags,
            setup_quality_min_threshold=(
                decision_mask_payload["setup_quality_decision_mask_min_threshold"]
                if decision_mask_payload["setup_quality_decision_mask_enabled"]
                else setup_quality_min_threshold
            ),
        )
        setup_mask_metrics = self._compute_binary_trade_metrics(
            predicted_trade_flags=setup_masked_trade_flags,
            actual_trade_flags=actual_trade_flags,
            threshold=threshold,
            fallback_actual_trade_rate=trade_row_ratio,
        )
        setup_quality_mask_false_positive_removed_count = max(
            0,
            raw_opportunity_threshold_metrics.false_positive_count
            - setup_mask_metrics.false_positive_count,
        )
        entry_path_mask_false_positive_removed_count = max(
            0,
            setup_mask_metrics.false_positive_count - false_positive_count,
        )
        entry_path_quality_filter_summary = self._compute_entry_path_quality_filter_summary(
            entry_path_quality_scores=entry_path_quality_scores or [],
            stop_pressure_risk_scores=stop_pressure_risk_scores or [],
            predicted_trade_flags=predicted_trade_flags,
            actual_trade_flags=actual_trade_flags,
            entry_path_quality_min_threshold=entry_path_mask_payload.get("entry_path_quality_min_threshold"),
            stop_pressure_max_risk_score=entry_path_mask_payload.get("stop_pressure_max_risk_score"),
        )

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
            "raw_predicted_trade_rate": raw_opportunity_threshold_metrics.predicted_trade_rate,
            "masked_predicted_trade_rate": predicted_trade_rate,
            "opportunity_accuracy": opportunity_accuracy,
            "opportunity_precision": opportunity_precision,
            "opportunity_recall": opportunity_recall,
            "opportunity_f1": opportunity_f1,
            "opportunity_false_positive_rate": opportunity_false_positive_rate,
            "raw_opportunity_precision": raw_opportunity_threshold_metrics.precision,
            "raw_opportunity_recall": raw_opportunity_threshold_metrics.recall,
            "raw_opportunity_f1": raw_opportunity_threshold_metrics.f1,
            "raw_opportunity_false_positive_rate": raw_opportunity_threshold_metrics.false_positive_rate,
            "raw_predicted_to_actual_trade_rate_ratio": (
                raw_opportunity_threshold_metrics.predicted_to_actual_trade_rate_ratio
            ),
            "opportunity_true_positive_count": true_positive_count,
            "opportunity_false_positive_count": false_positive_count,
            "opportunity_false_negative_count": false_negative_count,
            "opportunity_true_negative_count": true_negative_count,
            "opportunity_positive_rate": predicted_trade_rate,
            "setup_quality_min_threshold": setup_quality_min_threshold,
            "setup_quality_decision_mask_enabled": bool(
                decision_mask_payload["setup_quality_decision_mask_enabled"]
            ),
            "setup_quality_decision_mask_min_threshold": decision_mask_payload[
                "setup_quality_decision_mask_min_threshold"
            ],
            "setup_quality_masked_row_count": int(decision_mask_payload["setup_quality_masked_row_count"]),
            "setup_quality_forced_no_trade_count": int(
                decision_mask_payload["setup_quality_forced_no_trade_count"]
            ),
            "setup_quality_mask_false_positive_removed_count": int(
                setup_quality_mask_false_positive_removed_count
            ),
            "setup_quality_mask_trade_prediction_removed_count": int(
                decision_mask_payload["setup_quality_mask_trade_prediction_removed_count"]
            ),
            "setup_quality_bucket_metrics": setup_quality_bucket_metrics,
            "setup_quality_bucket_metrics_raw": setup_quality_bucket_metrics_raw,
            "setup_quality_bucket_metrics_after_mask": setup_quality_bucket_metrics,
            "setup_quality_distribution": setup_quality_distribution,
            "setup_quality_filter_summary": setup_quality_filter_summary,
            "entry_path_quality_filter_enabled": bool(
                entry_path_mask_payload["entry_path_quality_filter_enabled"]
            ),
            "entry_path_quality_min_threshold": entry_path_mask_payload.get(
                "entry_path_quality_min_threshold"
            ),
            "stop_pressure_max_risk_score": entry_path_mask_payload.get(
                "stop_pressure_max_risk_score"
            ),
            "entry_path_quality_masked_row_count": int(
                entry_path_mask_payload["entry_path_quality_masked_row_count"]
            ),
            "entry_path_quality_forced_no_trade_count": int(
                entry_path_mask_payload["entry_path_quality_forced_no_trade_count"]
            ),
            "entry_path_quality_mask_trade_prediction_removed_count": int(
                entry_path_mask_payload["entry_path_quality_mask_trade_prediction_removed_count"]
            ),
            "entry_path_quality_mask_false_positive_removed_count": int(
                entry_path_mask_false_positive_removed_count
            ),
            "entry_path_quality_filter_summary": entry_path_quality_filter_summary,
        }

    @staticmethod
    def apply_setup_quality_decision_mask(
        *,
        opportunity_probabilities: list[float] | None,
        setup_quality_scores: list[float] | None,
        probability_threshold: float,
        setup_quality_decision_mask_enabled: bool,
        setup_quality_decision_mask_min_threshold: float | None,
    ) -> dict[str, Any]:
        probabilities = list(opportunity_probabilities or [])
        scores = list(setup_quality_scores or [])
        raw_predicted_trade_flags = [int(float(probability) >= float(probability_threshold)) for probability in probabilities]
        if not setup_quality_decision_mask_enabled:
            return {
                "raw_predicted_trade_flags": raw_predicted_trade_flags,
                "masked_predicted_trade_flags": list(raw_predicted_trade_flags),
                "setup_quality_decision_mask_enabled": False,
                "setup_quality_decision_mask_min_threshold": setup_quality_decision_mask_min_threshold,
                "setup_quality_masked_row_count": 0,
                "setup_quality_forced_no_trade_count": 0,
                "setup_quality_mask_trade_prediction_removed_count": 0,
            }

        min_threshold = (
            0.0
            if setup_quality_decision_mask_min_threshold is None
            else float(setup_quality_decision_mask_min_threshold)
        )
        masked_predicted_trade_flags: list[int] = []
        masked_row_count = 0
        forced_no_trade_count = 0

        for index, raw_flag in enumerate(raw_predicted_trade_flags):
            score = scores[index] if index < len(scores) else None
            quality_value = 0.0 if score is None else float(score or 0.0)
            setup_quality_blocked = score is None or quality_value <= 0.0 or quality_value < min_threshold
            if setup_quality_blocked:
                masked_row_count += 1
                masked_flag = 0
            else:
                masked_flag = raw_flag
            if raw_flag == 1 and masked_flag == 0:
                forced_no_trade_count += 1
            masked_predicted_trade_flags.append(masked_flag)

        return {
            "raw_predicted_trade_flags": raw_predicted_trade_flags,
            "masked_predicted_trade_flags": masked_predicted_trade_flags,
            "setup_quality_decision_mask_enabled": True,
            "setup_quality_decision_mask_min_threshold": min_threshold,
            "setup_quality_masked_row_count": int(masked_row_count),
            "setup_quality_forced_no_trade_count": int(forced_no_trade_count),
            "setup_quality_mask_trade_prediction_removed_count": int(forced_no_trade_count),
        }

    @staticmethod
    def apply_entry_path_quality_decision_mask(
        *,
        predicted_trade_flags: list[int],
        entry_path_quality_scores: list[float] | None,
        stop_pressure_risk_scores: list[float] | None,
        entry_path_quality_filter_enabled: bool,
        entry_path_quality_min_threshold: float | None,
        stop_pressure_max_risk_score: float | None,
    ) -> dict[str, Any]:
        raw_flags = [int(value) for value in predicted_trade_flags]
        if not entry_path_quality_filter_enabled:
            return {
                "masked_predicted_trade_flags": list(raw_flags),
                "entry_path_quality_filter_enabled": False,
                "entry_path_quality_min_threshold": entry_path_quality_min_threshold,
                "stop_pressure_max_risk_score": stop_pressure_max_risk_score,
                "entry_path_quality_masked_row_count": 0,
                "entry_path_quality_forced_no_trade_count": 0,
                "entry_path_quality_mask_trade_prediction_removed_count": 0,
            }

        quality_threshold = 0.0 if entry_path_quality_min_threshold is None else float(entry_path_quality_min_threshold)
        stop_threshold = 1.0 if stop_pressure_max_risk_score is None else float(stop_pressure_max_risk_score)
        quality_scores = list(entry_path_quality_scores or [])
        stop_scores = list(stop_pressure_risk_scores or [])

        masked_flags: list[int] = []
        masked_row_count = 0
        forced_no_trade_count = 0

        for index, raw_flag in enumerate(raw_flags):
            quality_value = quality_scores[index] if index < len(quality_scores) else 0.0
            stop_value = stop_scores[index] if index < len(stop_scores) else 1.0
            quality_blocked = float(quality_value or 0.0) < quality_threshold
            stop_blocked = float(stop_value or 0.0) > stop_threshold
            blocked = quality_blocked or stop_blocked
            if blocked:
                masked_row_count += 1
                masked_flag = 0
            else:
                masked_flag = raw_flag
            if raw_flag == 1 and masked_flag == 0:
                forced_no_trade_count += 1
            masked_flags.append(masked_flag)

        return {
            "masked_predicted_trade_flags": masked_flags,
            "entry_path_quality_filter_enabled": True,
            "entry_path_quality_min_threshold": quality_threshold,
            "stop_pressure_max_risk_score": stop_threshold,
            "entry_path_quality_masked_row_count": int(masked_row_count),
            "entry_path_quality_forced_no_trade_count": int(forced_no_trade_count),
            "entry_path_quality_mask_trade_prediction_removed_count": int(forced_no_trade_count),
        }

    @staticmethod
    def _compute_entry_path_quality_filter_summary(
        *,
        entry_path_quality_scores: list[float],
        stop_pressure_risk_scores: list[float],
        predicted_trade_flags: list[int],
        actual_trade_flags: list[int],
        entry_path_quality_min_threshold: float | None,
        stop_pressure_max_risk_score: float | None,
    ) -> dict[str, Any]:
        row_count = len(actual_trade_flags)
        quality_threshold = 0.0 if entry_path_quality_min_threshold is None else float(entry_path_quality_min_threshold)
        stop_threshold = 1.0 if stop_pressure_max_risk_score is None else float(stop_pressure_max_risk_score)
        blocked_indices: list[int] = []
        passed_indices: list[int] = []
        for index in range(row_count):
            quality_value = entry_path_quality_scores[index] if index < len(entry_path_quality_scores) else 0.0
            stop_value = stop_pressure_risk_scores[index] if index < len(stop_pressure_risk_scores) else 1.0
            if float(quality_value or 0.0) < quality_threshold or float(stop_value or 0.0) > stop_threshold:
                blocked_indices.append(index)
            else:
                passed_indices.append(index)

        def _rate(indices: list[int], source: list[int]) -> float:
            if not indices:
                return 0.0
            return sum(int(source[index]) for index in indices) / len(indices)

        return {
            "entry_path_quality_min_threshold": entry_path_quality_min_threshold,
            "stop_pressure_max_risk_score": stop_pressure_max_risk_score,
            "rows_blocked_by_entry_path_filter": int(len(blocked_indices)),
            "rows_passed_entry_path_filter": int(len(passed_indices)),
            "actual_trade_rate_blocked": float(_rate(blocked_indices, actual_trade_flags)),
            "actual_trade_rate_passed": float(_rate(passed_indices, actual_trade_flags)),
            "predicted_trade_rate_blocked": float(_rate(blocked_indices, predicted_trade_flags)),
            "predicted_trade_rate_passed": float(_rate(passed_indices, predicted_trade_flags)),
        }

    @staticmethod
    def _compute_binary_trade_metrics(
        *,
        predicted_trade_flags: list[int],
        actual_trade_flags: list[int],
        threshold: float,
        fallback_actual_trade_rate: float,
    ) -> OpportunityThresholdMetrics:
        row_count = min(len(predicted_trade_flags), len(actual_trade_flags))
        predicted_flags = [int(value) for value in predicted_trade_flags[:row_count]]
        actual_flags = [int(value) for value in actual_trade_flags[:row_count]]

        true_positive_count = 0
        false_positive_count = 0
        false_negative_count = 0
        true_negative_count = 0
        for predicted_trade, actual_trade in zip(predicted_flags, actual_flags):
            if actual_trade == 1 and predicted_trade == 1:
                true_positive_count += 1
            elif actual_trade == 0 and predicted_trade == 1:
                false_positive_count += 1
            elif actual_trade == 1 and predicted_trade == 0:
                false_negative_count += 1
            else:
                true_negative_count += 1

        predicted_trade_rate = sum(predicted_flags) / row_count if row_count > 0 else 0.0
        actual_trade_rate = sum(actual_flags) / row_count if row_count > 0 else fallback_actual_trade_rate
        if actual_trade_rate == 0.0:
            predicted_to_actual_trade_rate_ratio = 0.0 if predicted_trade_rate == 0.0 else 999.0
        else:
            predicted_to_actual_trade_rate_ratio = predicted_trade_rate / actual_trade_rate
        accuracy = (true_positive_count + true_negative_count) / row_count if row_count > 0 else 0.0
        precision = (
            true_positive_count / (true_positive_count + false_positive_count)
            if (true_positive_count + false_positive_count) > 0
            else 0.0
        )
        recall = (
            true_positive_count / (true_positive_count + false_negative_count)
            if (true_positive_count + false_negative_count) > 0
            else 0.0
        )
        f1 = (
            2.0 * precision * recall / (precision + recall)
            if (precision + recall) > 0.0
            else 0.0
        )
        false_positive_rate = (
            false_positive_count / (false_positive_count + true_negative_count)
            if (false_positive_count + true_negative_count) > 0
            else 0.0
        )
        return OpportunityThresholdMetrics(
            threshold=float(threshold),
            row_count=row_count,
            true_positive_count=true_positive_count,
            false_positive_count=false_positive_count,
            false_negative_count=false_negative_count,
            true_negative_count=true_negative_count,
            actual_trade_rate=actual_trade_rate,
            predicted_trade_rate=predicted_trade_rate,
            predicted_to_actual_trade_rate_ratio=predicted_to_actual_trade_rate_ratio,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1=f1,
            false_positive_rate=false_positive_rate,
        )

    @staticmethod
    def _setup_quality_bucket_name(value: float) -> str:
        quality_value = float(value or 0.0)
        if quality_value <= 0.0:
            return "missing_or_zero"
        for bucket_name, lower_bound, upper_bound in SETUP_QUALITY_BUCKETS[1:]:
            if lower_bound is None:
                continue
            if quality_value >= float(lower_bound) and quality_value < float(upper_bound):
                return bucket_name
        return "strong_0_75_1_00"

    def _compute_setup_quality_bucket_metrics(
        self,
        *,
        setup_quality_scores: list[float],
        predicted_trade_flags: list[int],
        actual_trade_flags: list[int],
    ) -> dict[str, dict[str, int | float]]:
        bucketed_indices = {
            bucket_name: []
            for bucket_name, _, _ in SETUP_QUALITY_BUCKETS
        }
        for index, value in enumerate(setup_quality_scores[: len(actual_trade_flags)]):
            bucketed_indices[self._setup_quality_bucket_name(value)].append(index)
        for index in range(len(setup_quality_scores), len(actual_trade_flags)):
            bucketed_indices["missing_or_zero"].append(index)

        payload: dict[str, dict[str, int | float]] = {}
        for bucket_name, indices in bucketed_indices.items():
            row_count = len(indices)
            actual_trade_count = sum(int(actual_trade_flags[index]) for index in indices)
            predicted_trade_count = sum(int(predicted_trade_flags[index]) for index in indices)
            true_positive_count = sum(
                int(predicted_trade_flags[index] == 1 and actual_trade_flags[index] == 1)
                for index in indices
            )
            false_positive_count = sum(
                int(predicted_trade_flags[index] == 1 and actual_trade_flags[index] == 0)
                for index in indices
            )
            false_negative_count = sum(
                int(predicted_trade_flags[index] == 0 and actual_trade_flags[index] == 1)
                for index in indices
            )
            actual_no_trade_count = sum(
                int(actual_trade_flags[index] == 0)
                for index in indices
            )
            precision = (
                true_positive_count / predicted_trade_count
                if predicted_trade_count > 0
                else 0.0
            )
            recall = (
                true_positive_count / actual_trade_count
                if actual_trade_count > 0
                else 0.0
            )
            f1 = (
                (2.0 * precision * recall) / (precision + recall)
                if (precision + recall) > 0.0
                else 0.0
            )
            false_positive_rate = (
                false_positive_count / actual_no_trade_count
                if actual_no_trade_count > 0
                else 0.0
            )
            payload[bucket_name] = {
                "row_count": int(row_count),
                "actual_trade_count": int(actual_trade_count),
                "predicted_trade_count": int(predicted_trade_count),
                "actual_trade_rate": (actual_trade_count / row_count) if row_count > 0 else 0.0,
                "predicted_trade_rate": (predicted_trade_count / row_count) if row_count > 0 else 0.0,
                "true_positive_count": int(true_positive_count),
                "false_positive_count": int(false_positive_count),
                "false_negative_count": int(false_negative_count),
                "precision": float(precision),
                "recall": float(recall),
                "f1": float(f1),
                "false_positive_rate": float(false_positive_rate),
            }
        return payload

    @staticmethod
    def _compute_setup_quality_filter_summary(
        *,
        setup_quality_scores: list[float],
        predicted_trade_flags: list[int],
        actual_trade_flags: list[int],
        setup_quality_min_threshold: float | None,
    ) -> dict[str, int | float | None]:
        if setup_quality_min_threshold is None:
            below_indices: list[int] = []
            above_indices = list(range(len(actual_trade_flags)))
        else:
            threshold = float(setup_quality_min_threshold)
            below_indices = []
            above_indices = []
            for index in range(len(actual_trade_flags)):
                value = setup_quality_scores[index] if index < len(setup_quality_scores) else None
                quality_value = 0.0 if value is None else float(value or 0.0)
                blocked = value is None or quality_value <= 0.0 or quality_value < threshold
                if blocked:
                    below_indices.append(index)
                else:
                    above_indices.append(index)

        def _trade_rate(indices: list[int], source: list[int]) -> float:
            if not indices:
                return 0.0
            return sum(int(source[index]) for index in indices) / len(indices)

        return {
            "setup_quality_min_threshold": setup_quality_min_threshold,
            "rows_below_threshold": int(len(below_indices)),
            "rows_at_or_above_threshold": int(len(above_indices)),
            "actual_trade_rate_below_threshold": float(_trade_rate(below_indices, actual_trade_flags)),
            "actual_trade_rate_at_or_above_threshold": float(_trade_rate(above_indices, actual_trade_flags)),
            "predicted_trade_rate_below_threshold": float(_trade_rate(below_indices, predicted_trade_flags)),
            "predicted_trade_rate_at_or_above_threshold": float(_trade_rate(above_indices, predicted_trade_flags)),
        }
