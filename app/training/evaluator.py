from __future__ import annotations

from typing import Any

import torch

from app.training.metrics import TrainingMetrics


class Evaluator:
    def __init__(self, metrics: TrainingMetrics | None = None) -> None:
        self._metrics = metrics or TrainingMetrics()

    def evaluate(self, model: torch.nn.Module, dataset: dict[str, torch.Tensor]) -> dict[str, Any]:
        if dataset["features"].shape[0] == 0:
            return {
                "accuracy": 0.0,
                "precision_up": 0.0,
                "precision_down": 0.0,
                "confusion_matrix": [[0, 0, 0], [0, 0, 0], [0, 0, 0]],
                "brier_score": 0.0,
                "tp_before_sl_accuracy": None,
                "average_expected_move_error": 0.0,
                "rows": 0,
            }

        model.eval()
        with torch.no_grad():
            outputs = model(dataset["features"])
            direction_probabilities_tensor = torch.softmax(outputs["direction_logits"], dim=1)
            tp_probabilities_tensor = torch.sigmoid(outputs["tp_sl_logits"])

        metrics = self._metrics.compute(
            direction_probabilities=direction_probabilities_tensor.cpu().tolist(),
            direction_targets=dataset["direction_target"].cpu().tolist(),
            tp_sl_probabilities=tp_probabilities_tensor.cpu().tolist(),
            tp_sl_targets=self._decode_optional_boolean_targets(dataset["tp_sl_target"], dataset["tp_sl_mask"]),
            expected_move_predictions=outputs["expected_move_atr"].cpu().tolist(),
            expected_move_targets=dataset["move_target"].cpu().tolist(),
        )
        metrics["rows"] = int(dataset["features"].shape[0])
        return metrics

    @staticmethod
    def _decode_optional_boolean_targets(tp_targets: torch.Tensor, tp_mask: torch.Tensor) -> list[bool | None]:
        decoded: list[bool | None] = []
        for value, mask in zip(tp_targets.cpu().tolist(), tp_mask.cpu().tolist()):
            if mask <= 0:
                decoded.append(None)
            else:
                decoded.append(value >= 0.5)
        return decoded
