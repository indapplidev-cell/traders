from __future__ import annotations

from collections import Counter
from typing import Any

import torch

from app.dataset.dataset_models import DatasetRow
from app.training.metrics import INDEX_TO_LABEL, LABEL_TO_INDEX
from app.training.metrics import TrainingMetrics
from app.training.probability_calibration import softmax_with_temperature
from app.training.training_service import TrainingService


class PredictionDiagnostics:
    LABELS = ["UP", "DOWN", "FLAT"]

    def __init__(self, metrics: TrainingMetrics | None = None) -> None:
        self._metrics = metrics or TrainingMetrics()

    def analyze_split(
        self,
        model: torch.nn.Module,
        rows: list[DatasetRow],
        feature_columns: list[str],
        scaler: dict[str, list[float]],
        direction_temperature: float = 1.0,
    ) -> dict[str, Any]:
        tensors = TrainingService.rows_to_tensors(rows, feature_columns, scaler)
        if tensors["features"].shape[0] == 0:
            return {
                "actual_counts": {label: 0 for label in self.LABELS},
                "predicted_counts": {label: 0 for label in self.LABELS},
                "average_probabilities": {label: 0.0 for label in self.LABELS},
                "confidence_distribution": self._confidence_distribution([]),
                "confusion_matrix": [[0, 0, 0], [0, 0, 0], [0, 0, 0]],
                "rows": 0,
                "direction_temperature": float(direction_temperature),
                "probability_source": "temperature_scaled"
                if direction_temperature != 1.0
                else "raw_softmax",
            }

        model.eval()
        with torch.no_grad():
            outputs = model(tensors["features"])
            probabilities = softmax_with_temperature(
                outputs["direction_logits"],
                temperature=direction_temperature,
            ).cpu().tolist()

        predicted_indexes = [max(range(3), key=lambda index: probability_row[index]) for probability_row in probabilities]
        actual_indexes = tensors["direction_target"].cpu().tolist()
        predicted_counts = Counter(INDEX_TO_LABEL[index] for index in predicted_indexes)
        actual_counts = Counter(INDEX_TO_LABEL[index] for index in actual_indexes)
        metrics = self._metrics.compute(
            direction_probabilities=probabilities,
            direction_targets=actual_indexes,
            tp_sl_probabilities=[0.0] * len(rows),
            tp_sl_targets=[None] * len(rows),
            expected_move_predictions=[0.0] * len(rows),
            expected_move_targets=[0.0] * len(rows),
        )

        average_probabilities = {
            label: sum(probability_row[LABEL_TO_INDEX[label]] for probability_row in probabilities) / len(probabilities)
            for label in self.LABELS
        }
        confidences = [max(probability_row) for probability_row in probabilities]
        return {
            "actual_counts": {label: actual_counts.get(label, 0) for label in self.LABELS},
            "predicted_counts": {label: predicted_counts.get(label, 0) for label in self.LABELS},
            "average_probabilities": average_probabilities,
            "confidence_distribution": self._confidence_distribution(confidences),
            "confusion_matrix": metrics["confusion_matrix"],
            "accuracy": metrics["accuracy"],
            "brier_score": metrics["brier_score"],
            "rows": len(rows),
            "direction_temperature": float(direction_temperature),
            "probability_source": "temperature_scaled"
            if direction_temperature != 1.0
            else "raw_softmax",
        }

    @staticmethod
    def _confidence_distribution(confidences: list[float]) -> dict[str, int]:
        bins = {
            "0.0-0.2": 0,
            "0.2-0.4": 0,
            "0.4-0.6": 0,
            "0.6-0.8": 0,
            "0.8-1.0": 0,
        }
        for confidence in confidences:
            if confidence < 0.2:
                bins["0.0-0.2"] += 1
            elif confidence < 0.4:
                bins["0.2-0.4"] += 1
            elif confidence < 0.6:
                bins["0.4-0.6"] += 1
            elif confidence < 0.8:
                bins["0.6-0.8"] += 1
            else:
                bins["0.8-1.0"] += 1
        return bins
