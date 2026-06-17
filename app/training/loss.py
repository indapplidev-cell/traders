from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn


class FocalCrossEntropyLoss(nn.Module):
    """Focal loss для direction head.

    Нужен, чтобы модель меньше застревала в слабом усреднённом softmax около 0.33–0.37
    и сильнее училась на трудных directional примерах.
    """

    def __init__(
        self,
        gamma: float = 2.0,
        weight: torch.Tensor | None = None,
        label_smoothing: float = 0.0,
    ) -> None:
        super().__init__()
        self._gamma = float(gamma)
        self._weight = weight
        self._label_smoothing = float(label_smoothing)

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        weight = self._weight.to(logits.device) if self._weight is not None else None
        ce = F.cross_entropy(
            logits,
            targets,
            weight=weight,
            reduction="none",
            label_smoothing=self._label_smoothing,
        )
        probabilities = torch.softmax(logits, dim=1)
        target_probabilities = probabilities.gather(1, targets.view(-1, 1)).squeeze(1).clamp(1e-8, 1.0)
        focal_factor = (1.0 - target_probabilities) ** self._gamma
        return torch.mean(focal_factor * ce)


class MultiTaskLoss:
    def __init__(
        self,
        direction_class_weights: list[float] | None = None,
        direction_loss_name: str = "cross_entropy",
        focal_gamma: float = 2.0,
        label_smoothing: float = 0.0,
        direction_loss_weight: float = 1.0,
        tp_sl_loss_weight: float = 1.0,
        move_loss_weight: float = 1.0,
        risk_loss_weight: float = 1.0,
        confidence_margin_weight: float = 0.0,
        confidence_margin_target: float = 0.12,
    ) -> None:
        weights = torch.tensor(direction_class_weights, dtype=torch.float32) if direction_class_weights is not None else None
        self._direction_loss_name = direction_loss_name
        self._direction_loss_weight = float(direction_loss_weight)
        self._tp_sl_loss_weight = float(tp_sl_loss_weight)
        self._move_loss_weight = float(move_loss_weight)
        self._risk_loss_weight = float(risk_loss_weight)
        self._confidence_margin_weight = float(confidence_margin_weight)
        self._confidence_margin_target = float(confidence_margin_target)
        self._direction_class_weights = weights

        if direction_loss_name == "focal":
            self._direction_loss = FocalCrossEntropyLoss(
                gamma=focal_gamma,
                weight=weights,
                label_smoothing=label_smoothing,
            )
        elif direction_loss_name == "cross_entropy":
            self._direction_loss = None
        else:
            raise ValueError(f"Unsupported direction_loss_name: {direction_loss_name}")

        self._bce = nn.BCEWithLogitsLoss()
        self._regression = nn.HuberLoss()

    def compute(self, outputs: dict[str, torch.Tensor], batch: dict[str, torch.Tensor]) -> tuple[torch.Tensor, dict[str, float]]:
        direction_logits = outputs["direction_logits"]
        direction_targets = batch["direction_target"]
        direction_loss = self._compute_direction_loss(direction_logits, direction_targets)
        confidence_margin_loss = self._confidence_margin_loss(direction_logits, direction_targets)

        tp_mask = batch["tp_sl_mask"] > 0
        if torch.any(tp_mask):
            tp_sl_loss = self._bce(outputs["tp_sl_logits"][tp_mask], batch["tp_sl_target"][tp_mask])
        else:
            tp_sl_loss = direction_logits.new_tensor(0.0)

        move_loss = self._regression(outputs["expected_move_atr"], batch["move_target"])
        risk_loss = self._regression(outputs["risk_score"], batch["risk_target"])

        total_loss = (
            self._direction_loss_weight * direction_loss
            + self._tp_sl_loss_weight * tp_sl_loss
            + self._move_loss_weight * move_loss
            + self._risk_loss_weight * risk_loss
            + self._confidence_margin_weight * confidence_margin_loss
        )
        return total_loss, {
            "direction_loss": float(direction_loss.detach().item()),
            "tp_sl_loss": float(tp_sl_loss.detach().item()),
            "move_loss": float(move_loss.detach().item()),
            "risk_loss": float(risk_loss.detach().item()),
            "confidence_margin_loss": float(confidence_margin_loss.detach().item()),
            "direction_loss_name": self._direction_loss_name,
            "total_loss": float(total_loss.detach().item()),
        }

    def _compute_direction_loss(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        if self._direction_loss_name == "focal":
            return self._direction_loss(logits, targets)
        weight = self._direction_class_weights.to(logits.device) if self._direction_class_weights is not None else None
        return F.cross_entropy(logits, targets, weight=weight)

    def _confidence_margin_loss(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        if self._confidence_margin_weight <= 0:
            return logits.new_tensor(0.0)

        target_logits = logits.gather(1, targets.view(-1, 1)).squeeze(1)
        mask = F.one_hot(targets, num_classes=logits.shape[1]).bool()
        other_logits = logits.masked_fill(mask, float("-inf")).max(dim=1).values
        margin = target_logits - other_logits
        deficit = torch.relu(self._confidence_margin_target - margin)
        return torch.mean(deficit ** 2)
