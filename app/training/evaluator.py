from __future__ import annotations

from typing import Any

import torch

from app.training.metrics import TrainingMetrics
from app.training.probability_calibration import softmax_with_temperature


class Evaluator:
    def __init__(self, metrics: TrainingMetrics | None = None) -> None:
        self._metrics = metrics or TrainingMetrics()

    def evaluate(
        self,
        model: torch.nn.Module,
        dataset: dict[str, torch.Tensor],
        direction_temperature: float = 1.0,
        training_objective: str = "direction_global",
    ) -> dict[str, Any]:
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
                "direction_temperature": float(direction_temperature),
                "direction_evaluation_rows": 0,
            }

        model.eval()
        with torch.no_grad():
            raw_outputs = model(dataset["features"])
            outputs = self._normalize_outputs(raw_outputs, dataset["features"])
            direction_probabilities_tensor = softmax_with_temperature(
                outputs["direction_logits"],
                temperature=direction_temperature,
            )
            tp_probabilities_tensor = torch.sigmoid(outputs["tp_sl_logits"])
            opportunity_probabilities_tensor = torch.sigmoid(outputs["opportunity_logit"])
            direction_mask = None
            if training_objective == "opportunity_first":
                direction_mask = (dataset["opportunity_target"] > 0).cpu().tolist()

        metrics = self._metrics.compute(
            direction_probabilities=direction_probabilities_tensor.cpu().tolist(),
            direction_targets=dataset["direction_target"].cpu().tolist(),
            tp_sl_probabilities=tp_probabilities_tensor.cpu().tolist(),
            tp_sl_targets=self._decode_optional_boolean_targets(dataset["tp_sl_target"], dataset["tp_sl_mask"]),
            expected_move_predictions=outputs["expected_move_atr"].cpu().tolist(),
            expected_move_targets=dataset["move_target"].cpu().tolist(),
            direction_mask=direction_mask,
            opportunity_probabilities=opportunity_probabilities_tensor.cpu().tolist(),
            opportunity_targets=dataset["opportunity_target"].cpu().tolist(),
        )
        metrics["rows"] = int(dataset["features"].shape[0])
        metrics["direction_temperature"] = float(direction_temperature)
        metrics["training_objective"] = training_objective
        metrics["opportunity_probability_mean"] = float(opportunity_probabilities_tensor.mean().detach().item())
        metrics["no_trade_probability_mean"] = float((1.0 - opportunity_probabilities_tensor).mean().detach().item())
        conditioned_direction_probabilities = direction_probabilities_tensor
        if training_objective == "opportunity_first" and direction_mask and any(direction_mask):
            conditioned_direction_probabilities = direction_probabilities_tensor[dataset["opportunity_target"] > 0]
        direction_probability_mean = conditioned_direction_probabilities.mean(dim=0)
        metrics["direction_probabilities_conditioned_on_opportunity_mean"] = {
            "UP": float(direction_probability_mean[0].detach().item()),
            "DOWN": float(direction_probability_mean[1].detach().item()),
            "FLAT": float(direction_probability_mean[2].detach().item()),
        }
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

    @staticmethod
    def _normalize_outputs(
        outputs: Any,
        features: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        if isinstance(outputs, dict):
            payload = dict(outputs)
            row_count = int(features.shape[0])
            payload.setdefault("tp_sl_logits", torch.zeros((row_count,), dtype=features.dtype, device=features.device))
            payload.setdefault("expected_move_atr", torch.zeros((row_count,), dtype=features.dtype, device=features.device))
            payload.setdefault("risk_score", torch.zeros((row_count,), dtype=features.dtype, device=features.device))
            payload.setdefault("opportunity_logit", torch.zeros((row_count,), dtype=features.dtype, device=features.device))
            return payload
        logits = outputs
        row_count = int(features.shape[0])
        zero = torch.zeros((row_count,), dtype=features.dtype, device=features.device)
        return {
            "direction_logits": logits,
            "tp_sl_logits": zero,
            "expected_move_atr": zero,
            "risk_score": zero,
            "opportunity_logit": zero,
        }
