from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn


class FocalCrossEntropyLoss(nn.Module):
    """Focal loss для direction head с optional sample weights."""

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

    def forward(
        self,
        logits: torch.Tensor,
        targets: torch.Tensor,
        sample_weights: torch.Tensor | None = None,
    ) -> torch.Tensor:
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
        return _weighted_mean(focal_factor * ce, sample_weights)


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
        direction_logit_gap_weight: float = 0.0,
        direction_logit_gap_target: float = 0.35,
    ) -> None:
        weights = torch.tensor(direction_class_weights, dtype=torch.float32) if direction_class_weights is not None else None
        self._direction_loss_name = direction_loss_name
        self._direction_loss_weight = float(direction_loss_weight)
        self._tp_sl_loss_weight = float(tp_sl_loss_weight)
        self._move_loss_weight = float(move_loss_weight)
        self._risk_loss_weight = float(risk_loss_weight)
        self._confidence_margin_weight = float(confidence_margin_weight)
        self._confidence_margin_target = float(confidence_margin_target)
        self._direction_logit_gap_weight = float(direction_logit_gap_weight)
        self._direction_logit_gap_target = float(direction_logit_gap_target)
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
        direction_sample_weights = _direction_sample_weights(batch, direction_logits)

        direction_loss = self._compute_direction_loss(
            direction_logits,
            direction_targets,
            sample_weights=direction_sample_weights,
        )
        confidence_margin_loss = self._confidence_margin_loss(
            direction_logits,
            direction_targets,
            sample_weights=direction_sample_weights,
        )
        direction_logit_gap_loss = self._direction_logit_gap_loss(
            direction_logits,
            direction_targets,
            sample_weights=direction_sample_weights,
        )

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
            + self._direction_logit_gap_weight * direction_logit_gap_loss
        )
        return total_loss, {
            "direction_loss": float(direction_loss.detach().item()),
            "tp_sl_loss": float(tp_sl_loss.detach().item()),
            "move_loss": float(move_loss.detach().item()),
            "risk_loss": float(risk_loss.detach().item()),
            "confidence_margin_loss": float(confidence_margin_loss.detach().item()),
            "direction_logit_gap_loss": float(direction_logit_gap_loss.detach().item()),
            "direction_sample_weight_mean": float(direction_sample_weights.mean().detach().item()),
            "direction_loss_name": self._direction_loss_name,
            "direction_loss_weight": self._direction_loss_weight,
            "tp_sl_loss_weight": self._tp_sl_loss_weight,
            "move_loss_weight": self._move_loss_weight,
            "risk_loss_weight": self._risk_loss_weight,
            "total_loss": float(total_loss.detach().item()),
        }

    def _compute_direction_loss(
        self,
        logits: torch.Tensor,
        targets: torch.Tensor,
        sample_weights: torch.Tensor | None = None,
    ) -> torch.Tensor:
        if self._direction_loss_name == "focal":
            return self._direction_loss(logits, targets, sample_weights=sample_weights)

        weight = self._direction_class_weights.to(logits.device) if self._direction_class_weights is not None else None
        ce = F.cross_entropy(logits, targets, weight=weight, reduction="none")
        return _weighted_mean(ce, sample_weights)

    def _confidence_margin_loss(
        self,
        logits: torch.Tensor,
        targets: torch.Tensor,
        sample_weights: torch.Tensor | None = None,
    ) -> torch.Tensor:
        if self._confidence_margin_weight <= 0:
            return logits.new_tensor(0.0)

        target_gap = _target_logit_gap(logits, targets)
        deficit = torch.relu(self._confidence_margin_target - target_gap)
        return _weighted_mean(deficit ** 2, sample_weights)

    def _direction_logit_gap_loss(
        self,
        logits: torch.Tensor,
        targets: torch.Tensor,
        sample_weights: torch.Tensor | None = None,
    ) -> torch.Tensor:
        if self._direction_logit_gap_weight <= 0:
            return logits.new_tensor(0.0)

        target_gap = _target_logit_gap(logits, targets)
        deficit = torch.relu(self._direction_logit_gap_target - target_gap)
        return _weighted_mean(deficit, sample_weights)


def _target_logit_gap(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    target_logits = logits.gather(1, targets.view(-1, 1)).squeeze(1)
    mask = F.one_hot(targets, num_classes=logits.shape[1]).bool()
    other_logits = logits.masked_fill(mask, float("-inf")).max(dim=1).values
    return target_logits - other_logits


def _direction_sample_weights(batch: dict[str, torch.Tensor], logits: torch.Tensor) -> torch.Tensor:
    weights = batch.get("direction_sample_weight")
    if weights is None:
        return torch.ones((logits.shape[0],), dtype=logits.dtype, device=logits.device)
    return weights.to(dtype=logits.dtype, device=logits.device).clamp(0.20, 1.50)


def _weighted_mean(values: torch.Tensor, sample_weights: torch.Tensor | None = None) -> torch.Tensor:
    if sample_weights is None:
        return torch.mean(values)
    weights = sample_weights.to(dtype=values.dtype, device=values.device)
    if weights.shape != values.shape:
        weights = weights.view_as(values)
    denominator = torch.sum(weights).clamp_min(1e-8)
    return torch.sum(values * weights) / denominator
