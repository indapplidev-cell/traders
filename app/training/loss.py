from __future__ import annotations

from collections.abc import Sequence

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
        direction_distribution_loss_weight: float = 0.0,
        flat_probability_floor_weight: float = 0.0,
        flat_probability_floor_target: float = 0.18,
        min_class_probability_floor: float = 0.04,
        class_probability_floor_weight: float = 0.0,
        class_probability_floor_targets: Sequence[float] | None = None,
        dominant_class_ceiling_weight: float = 0.0,
        dominant_class_ceiling_target: float = 0.75,
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
        self._direction_distribution_loss_weight = float(direction_distribution_loss_weight)
        self._flat_probability_floor_weight = float(flat_probability_floor_weight)
        self._flat_probability_floor_target = float(flat_probability_floor_target)
        self._min_class_probability_floor = float(min_class_probability_floor)
        self._class_probability_floor_weight = float(class_probability_floor_weight)
        raw_floor_targets = tuple(float(item) for item in (class_probability_floor_targets or (0.0, 0.0, 0.0)))
        if len(raw_floor_targets) != 3:
            raise ValueError("class_probability_floor_targets must contain exactly 3 values: UP, DOWN, FLAT")
        self._class_probability_floor_targets = raw_floor_targets
        self._dominant_class_ceiling_weight = float(dominant_class_ceiling_weight)
        self._dominant_class_ceiling_target = float(dominant_class_ceiling_target)
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
        direction_probabilities = torch.softmax(direction_logits, dim=1)

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
        direction_distribution_loss = self._direction_distribution_loss(
            probabilities=direction_probabilities,
            targets=direction_targets,
        )
        flat_probability_floor_loss = self._flat_probability_floor_loss(
            probabilities=direction_probabilities,
        )
        class_probability_floor_loss = self._class_probability_floor_loss(
            probabilities=direction_probabilities,
        )
        dominant_class_ceiling_loss = self._dominant_class_ceiling_loss(
            probabilities=direction_probabilities,
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
            + self._direction_distribution_loss_weight * direction_distribution_loss
            + self._flat_probability_floor_weight * flat_probability_floor_loss
            + self._class_probability_floor_weight * class_probability_floor_loss
            + self._dominant_class_ceiling_weight * dominant_class_ceiling_loss
        )
        predicted_distribution = direction_probabilities.mean(dim=0)
        return total_loss, {
            "direction_loss": float(direction_loss.detach().item()),
            "tp_sl_loss": float(tp_sl_loss.detach().item()),
            "move_loss": float(move_loss.detach().item()),
            "risk_loss": float(risk_loss.detach().item()),
            "confidence_margin_loss": float(confidence_margin_loss.detach().item()),
            "direction_logit_gap_loss": float(direction_logit_gap_loss.detach().item()),
            "direction_distribution_loss": float(direction_distribution_loss.detach().item()),
            "flat_probability_floor_loss": float(flat_probability_floor_loss.detach().item()),
            "class_probability_floor_loss": float(class_probability_floor_loss.detach().item()),
            "dominant_class_ceiling_loss": float(dominant_class_ceiling_loss.detach().item()),
            "direction_sample_weight_mean": float(direction_sample_weights.mean().detach().item()),
            "direction_predicted_up_probability_mean": float(predicted_distribution[0].detach().item()),
            "direction_predicted_down_probability_mean": float(predicted_distribution[1].detach().item()),
            "direction_predicted_flat_probability_mean": float(predicted_distribution[2].detach().item()),
            "direction_loss_name": self._direction_loss_name,
            "direction_loss_weight": self._direction_loss_weight,
            "tp_sl_loss_weight": self._tp_sl_loss_weight,
            "move_loss_weight": self._move_loss_weight,
            "risk_loss_weight": self._risk_loss_weight,
            "direction_distribution_loss_weight": self._direction_distribution_loss_weight,
            "flat_probability_floor_weight": self._flat_probability_floor_weight,
            "flat_probability_floor_target": self._flat_probability_floor_target,
            "min_class_probability_floor": self._min_class_probability_floor,
            "class_probability_floor_weight": self._class_probability_floor_weight,
            "class_probability_floor_targets": list(self._class_probability_floor_targets),
            "dominant_class_ceiling_weight": self._dominant_class_ceiling_weight,
            "dominant_class_ceiling_target": self._dominant_class_ceiling_target,
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

    def _direction_distribution_loss(
        self,
        probabilities: torch.Tensor,
        targets: torch.Tensor,
    ) -> torch.Tensor:
        if self._direction_distribution_loss_weight <= 0:
            return probabilities.new_tensor(0.0)

        predicted_distribution = probabilities.mean(dim=0)
        actual_distribution = F.one_hot(targets, num_classes=probabilities.shape[1]).float().mean(dim=0)

        floor = probabilities.new_full(actual_distribution.shape, self._min_class_probability_floor)
        target_distribution = torch.maximum(actual_distribution, floor)
        target_distribution = target_distribution / target_distribution.sum().clamp_min(1e-8)

        # FLAT is class index 2. We intentionally penalize FLAT under-coverage more,
        # because quick-quality showed predicted FLAT=0 while actual FLAT is about 30%.
        class_penalty = probabilities.new_tensor([1.0, 1.0, 1.75])
        return torch.mean(class_penalty * (predicted_distribution - target_distribution) ** 2)

    def _flat_probability_floor_loss(self, probabilities: torch.Tensor) -> torch.Tensor:
        if self._flat_probability_floor_weight <= 0:
            return probabilities.new_tensor(0.0)

        flat_probability_mean = probabilities[:, 2].mean()
        deficit = torch.relu(probabilities.new_tensor(self._flat_probability_floor_target) - flat_probability_mean)
        return deficit ** 2

    def _class_probability_floor_loss(self, probabilities: torch.Tensor) -> torch.Tensor:
        if self._class_probability_floor_weight <= 0:
            return probabilities.new_tensor(0.0)

        predicted_distribution = probabilities.mean(dim=0)
        floor_targets = probabilities.new_tensor(self._class_probability_floor_targets)
        deficits = torch.relu(floor_targets - predicted_distribution)

        # UP, DOWN, FLAT. DOWN and FLAT get stronger pressure because quick-quality
        # showed UP-dominance plus weak DOWN/FLAT coverage.
        class_penalty = probabilities.new_tensor([0.75, 1.35, 1.25])
        return torch.mean(class_penalty * deficits ** 2)

    def _dominant_class_ceiling_loss(self, probabilities: torch.Tensor) -> torch.Tensor:
        if self._dominant_class_ceiling_weight <= 0:
            return probabilities.new_tensor(0.0)

        predicted_distribution = probabilities.mean(dim=0)
        dominant_probability = torch.max(predicted_distribution)
        excess = torch.relu(dominant_probability - probabilities.new_tensor(self._dominant_class_ceiling_target))
        return excess ** 2


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
