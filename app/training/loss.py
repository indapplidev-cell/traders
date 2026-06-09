from __future__ import annotations

import torch
from torch import nn


class MultiTaskLoss:
    def __init__(self, direction_class_weights: list[float] | None = None) -> None:
        if direction_class_weights is not None:
            weights = torch.tensor(direction_class_weights, dtype=torch.float32)
            self._cross_entropy = nn.CrossEntropyLoss(weight=weights)
        else:
            self._cross_entropy = nn.CrossEntropyLoss()
        self._bce = nn.BCEWithLogitsLoss()
        self._regression = nn.HuberLoss()

    def compute(self, outputs: dict[str, torch.Tensor], batch: dict[str, torch.Tensor]) -> tuple[torch.Tensor, dict[str, float]]:
        direction_loss = self._cross_entropy(outputs["direction_logits"], batch["direction_target"])

        tp_mask = batch["tp_sl_mask"] > 0
        if torch.any(tp_mask):
            tp_sl_loss = self._bce(outputs["tp_sl_logits"][tp_mask], batch["tp_sl_target"][tp_mask])
        else:
            tp_sl_loss = outputs["direction_logits"].new_tensor(0.0)

        move_loss = self._regression(outputs["expected_move_atr"], batch["move_target"])
        risk_loss = self._regression(outputs["risk_score"], batch["risk_target"])

        total_loss = direction_loss + tp_sl_loss + move_loss + risk_loss
        return total_loss, {
            "direction_loss": float(direction_loss.detach().item()),
            "tp_sl_loss": float(tp_sl_loss.detach().item()),
            "move_loss": float(move_loss.detach().item()),
            "risk_loss": float(risk_loss.detach().item()),
            "total_loss": float(total_loss.detach().item()),
        }
