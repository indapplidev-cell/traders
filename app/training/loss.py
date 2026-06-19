from __future__ import annotations

from collections.abc import Callable
from collections.abc import Sequence

import torch
import torch.nn.functional as F
from torch import nn

from app.training.training_objectives import TRAINING_OBJECTIVE_TRADE_TWO_STAGE
from app.training.training_objectives import is_trade_two_stage_objective


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
        training_objective: str = "direction_global",
        direction_loss_name: str = "cross_entropy",
        focal_gamma: float = 2.0,
        label_smoothing: float = 0.0,
        opportunity_loss_weight: float = 1.0,
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
        baseline_edge_loss_fn: Callable[..., torch.Tensor] | None = None,
        baseline_edge_focal_gamma: float = 1.25,
        baseline_edge_margin_penalty: float = 0.02,
        baseline_edge_entropy_penalty: float = 0.01,
        class_margin_objective_enabled: bool = False,
        class_margin_objective_allowed: bool = False,
        true_class_margin_weight: float = 0.0,
        true_class_margin_target: float = 0.06,
        up_down_margin_weight: float = 0.0,
        up_down_margin_target: float = 0.05,
        flat_margin_weight: float = 0.0,
        flat_margin_target: float = 0.05,
        hard_negative_margin_weight: float = 0.0,
        hard_negative_margin_target: float = 0.08,
    ) -> None:
        weights = torch.tensor(direction_class_weights, dtype=torch.float32) if direction_class_weights is not None else None
        self._training_objective = training_objective
        self._direction_loss_name = direction_loss_name
        self._opportunity_loss_weight = float(opportunity_loss_weight)
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
        self._baseline_edge_loss_fn = baseline_edge_loss_fn
        self._baseline_edge_focal_gamma = float(baseline_edge_focal_gamma)
        self._baseline_edge_margin_penalty = float(baseline_edge_margin_penalty)
        self._baseline_edge_entropy_penalty = float(baseline_edge_entropy_penalty)
        self._class_margin_objective_enabled = bool(class_margin_objective_enabled)
        self._class_margin_objective_allowed = bool(class_margin_objective_allowed)
        self._true_class_margin_weight = float(true_class_margin_weight)
        self._true_class_margin_target = float(true_class_margin_target)
        self._up_down_margin_weight = float(up_down_margin_weight)
        self._up_down_margin_target = float(up_down_margin_target)
        self._flat_margin_weight = float(flat_margin_weight)
        self._flat_margin_target = float(flat_margin_target)
        self._hard_negative_margin_weight = float(hard_negative_margin_weight)
        self._hard_negative_margin_target = float(hard_negative_margin_target)

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

    @staticmethod
    def _balanced_bce_with_logits(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        targets = targets.to(dtype=logits.dtype, device=logits.device)
        positive_count = torch.clamp(targets.sum(), min=1.0)
        negative_count = torch.clamp((1.0 - targets).sum(), min=1.0)
        pos_weight = torch.clamp(negative_count / positive_count, min=1.0, max=12.0)
        return F.binary_cross_entropy_with_logits(logits, targets, pos_weight=pos_weight)

    @staticmethod
    def _binary_trade_direction_loss(
        direction_logits: torch.Tensor,
        direction_trade_targets: torch.Tensor,
        direction_trade_mask: torch.Tensor,
    ) -> torch.Tensor:
        trade_mask = direction_trade_mask > 0.5
        if not torch.any(trade_mask):
            return direction_logits.new_tensor(0.0)

        # Use only UP/DOWN logits. FLAT is not a direction class in trade_two_stage.
        up_down_logits = direction_logits[trade_mask][:, :2]
        targets = direction_trade_targets[trade_mask].to(dtype=torch.long, device=direction_logits.device)

        up_count = torch.clamp((targets == 0).sum().to(dtype=torch.float32), min=1.0)
        down_count = torch.clamp((targets == 1).sum().to(dtype=torch.float32), min=1.0)
        total = up_count + down_count
        weights = torch.stack([
            torch.clamp(total / (2.0 * up_count), min=0.65, max=2.50),
            torch.clamp(total / (2.0 * down_count), min=0.65, max=2.50),
        ]).to(device=direction_logits.device, dtype=direction_logits.dtype)

        return F.cross_entropy(up_down_logits, targets, weight=weights)

    def compute(self, outputs: dict[str, torch.Tensor], batch: dict[str, torch.Tensor]) -> tuple[torch.Tensor, dict[str, float]]:
        direction_logits = outputs["direction_logits"]
        direction_targets = batch["direction_target"]
        direction_sample_weights = _direction_sample_weights(batch, direction_logits)
        direction_probabilities = torch.softmax(direction_logits, dim=1)
        opportunity_targets = batch.get("opportunity_target")
        opportunity_mask = None if opportunity_targets is None else (opportunity_targets > 0.5)
        trade_two_stage = is_trade_two_stage_objective(self._training_objective)
        direction_trade_targets = batch.get("direction_trade_target")
        direction_trade_mask = batch.get("direction_trade_mask")
        if direction_trade_targets is None:
            direction_trade_targets = torch.where(direction_targets == 0, 0, 1).to(dtype=torch.long)
        if direction_trade_mask is None:
            direction_trade_mask = (
                opportunity_mask.to(dtype=torch.float32)
                if opportunity_mask is not None
                else torch.ones_like(direction_targets, dtype=torch.float32)
            )
        masked_direction_probabilities = direction_probabilities
        masked_direction_targets = direction_targets
        if self._training_objective == "opportunity_first" and opportunity_mask is not None and torch.any(opportunity_mask):
            masked_direction_probabilities = direction_probabilities[opportunity_mask]
            masked_direction_targets = direction_targets[opportunity_mask]

        opportunity_loss = direction_logits.new_tensor(0.0)
        if trade_two_stage and opportunity_targets is not None:
            opportunity_loss = self._balanced_bce_with_logits(outputs["opportunity_logit"], opportunity_targets)
            direction_loss = self._binary_trade_direction_loss(
                direction_logits=direction_logits,
                direction_trade_targets=direction_trade_targets,
                direction_trade_mask=direction_trade_mask,
            )
        elif self._training_objective == "opportunity_first" and opportunity_targets is not None:
            opportunity_loss = self._bce(outputs["opportunity_logit"], opportunity_targets)
            if torch.any(opportunity_mask):
                direction_loss = self._compute_direction_loss(
                    direction_logits[opportunity_mask],
                    direction_targets[opportunity_mask],
                    sample_weights=direction_sample_weights[opportunity_mask],
                )
            else:
                direction_loss = direction_logits.new_tensor(0.0)
        else:
            direction_loss = self._compute_direction_loss(
                direction_logits,
                direction_targets,
                sample_weights=direction_sample_weights,
            )
        if trade_two_stage:
            regularizer_sample_weights = direction_trade_mask.to(dtype=direction_logits.dtype, device=direction_logits.device)
        else:
            regularizer_sample_weights = (
                direction_sample_weights
                if self._training_objective != "opportunity_first" or opportunity_mask is None
                else direction_sample_weights * opportunity_mask.float()
            )
        confidence_margin_loss = self._confidence_margin_loss(
            direction_logits,
            direction_targets,
            sample_weights=regularizer_sample_weights,
        )
        direction_logit_gap_loss = self._direction_logit_gap_loss(
            direction_logits,
            direction_targets,
            sample_weights=regularizer_sample_weights,
        )
        direction_distribution_loss = self._direction_distribution_loss(
            probabilities=masked_direction_probabilities,
            targets=masked_direction_targets,
        )
        flat_probability_floor_loss = self._flat_probability_floor_loss(
            probabilities=masked_direction_probabilities,
        )
        class_probability_floor_loss = self._class_probability_floor_loss(
            probabilities=masked_direction_probabilities,
        )
        dominant_class_ceiling_loss = self._dominant_class_ceiling_loss(
            probabilities=masked_direction_probabilities,
        )
        true_class_margin_loss = self._true_class_margin_loss(
            direction_logits,
            direction_targets,
            sample_weights=regularizer_sample_weights,
        )
        up_down_margin_loss = self._up_down_margin_loss(
            direction_logits,
            direction_targets,
            sample_weights=regularizer_sample_weights,
        )
        flat_margin_loss = self._flat_margin_loss(
            direction_logits,
            direction_targets,
            batch=batch,
            sample_weights=regularizer_sample_weights,
        )
        hard_negative_margin_loss = self._hard_negative_margin_loss(
            direction_logits,
            direction_targets,
            sample_weights=regularizer_sample_weights,
        )
        if trade_two_stage:
            direction_distribution_loss = direction_logits.new_tensor(0.0)
            flat_probability_floor_loss = direction_logits.new_tensor(0.0)
            class_probability_floor_loss = direction_logits.new_tensor(0.0)
            dominant_class_ceiling_loss = direction_logits.new_tensor(0.0)
            flat_margin_loss = direction_logits.new_tensor(0.0)

        tp_mask = batch["tp_sl_mask"] > 0
        trade_aware_mask = direction_trade_mask > 0.5 if trade_two_stage else opportunity_mask
        if self._training_objective in {"opportunity_first", TRAINING_OBJECTIVE_TRADE_TWO_STAGE} and trade_aware_mask is not None:
            tp_mask = tp_mask & trade_aware_mask
        if torch.any(tp_mask):
            tp_sl_loss = self._bce(outputs["tp_sl_logits"][tp_mask], batch["tp_sl_target"][tp_mask])
        else:
            tp_sl_loss = direction_logits.new_tensor(0.0)

        if self._training_objective in {"opportunity_first", TRAINING_OBJECTIVE_TRADE_TWO_STAGE} and trade_aware_mask is not None:
            if torch.any(trade_aware_mask):
                move_loss = self._regression(outputs["expected_move_atr"][trade_aware_mask], batch["move_target"][trade_aware_mask])
                risk_loss = self._regression(outputs["risk_score"][trade_aware_mask], batch["risk_target"][trade_aware_mask])
            else:
                move_loss = direction_logits.new_tensor(0.0)
                risk_loss = direction_logits.new_tensor(0.0)
        else:
            move_loss = self._regression(outputs["expected_move_atr"], batch["move_target"])
            risk_loss = self._regression(outputs["risk_score"], batch["risk_target"])

        total_loss = (
            self._opportunity_loss_weight * opportunity_loss
            + self._direction_loss_weight * direction_loss
            + self._tp_sl_loss_weight * tp_sl_loss
            + self._move_loss_weight * move_loss
            + self._risk_loss_weight * risk_loss
            + self._confidence_margin_weight * confidence_margin_loss
            + self._direction_logit_gap_weight * direction_logit_gap_loss
            + self._direction_distribution_loss_weight * direction_distribution_loss
            + self._flat_probability_floor_weight * flat_probability_floor_loss
            + self._class_probability_floor_weight * class_probability_floor_loss
            + self._dominant_class_ceiling_weight * dominant_class_ceiling_loss
            + self._true_class_margin_weight * true_class_margin_loss
            + self._up_down_margin_weight * up_down_margin_loss
            + self._flat_margin_weight * flat_margin_loss
            + self._hard_negative_margin_weight * hard_negative_margin_loss
        )
        predicted_distribution = direction_probabilities.mean(dim=0)
        return total_loss, {
            "opportunity_loss": float(opportunity_loss.detach().item()),
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
            "true_class_margin_loss": float(true_class_margin_loss.detach().item()),
            "up_down_margin_loss": float(up_down_margin_loss.detach().item()),
            "flat_margin_loss": float(flat_margin_loss.detach().item()),
            "hard_negative_margin_loss": float(hard_negative_margin_loss.detach().item()),
            "direction_sample_weight_mean": float(direction_sample_weights.mean().detach().item()),
            "direction_predicted_up_probability_mean": float(predicted_distribution[0].detach().item()),
            "direction_predicted_down_probability_mean": float(predicted_distribution[1].detach().item()),
            "direction_predicted_flat_probability_mean": float(predicted_distribution[2].detach().item()),
            "trade_two_stage_enabled": float(1.0 if trade_two_stage else 0.0),
            "trade_row_ratio": float(direction_trade_mask.float().mean().detach().item()) if direction_trade_mask is not None else 0.0,
            "direction_trade_rows": float((direction_trade_mask > 0.5).sum().detach().item()) if direction_trade_mask is not None else 0.0,
            "training_objective": self._training_objective,
            "direction_loss_name": self._direction_loss_name,
            "opportunity_loss_weight": self._opportunity_loss_weight,
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
            "class_margin_objective_enabled": self._class_margin_objective_enabled,
            "class_margin_objective_allowed": self._class_margin_objective_allowed,
            "true_class_margin_weight": self._true_class_margin_weight,
            "true_class_margin_target": self._true_class_margin_target,
            "up_down_margin_weight": self._up_down_margin_weight,
            "up_down_margin_target": self._up_down_margin_target,
            "flat_margin_weight": self._flat_margin_weight,
            "flat_margin_target": self._flat_margin_target,
            "hard_negative_margin_weight": self._hard_negative_margin_weight,
            "hard_negative_margin_target": self._hard_negative_margin_target,
            "total_loss": float(total_loss.detach().item()),
        }

    def _compute_direction_loss(
        self,
        logits: torch.Tensor,
        targets: torch.Tensor,
        sample_weights: torch.Tensor | None = None,
    ) -> torch.Tensor:
        if self._baseline_edge_loss_fn is not None:
            weight = self._direction_class_weights.to(logits.device) if self._direction_class_weights is not None else None
            return self._baseline_edge_loss_fn(
                logits,
                targets,
                sample_weights=sample_weights,
                class_weights=weight,
                focal_gamma=self._baseline_edge_focal_gamma,
                confidence_margin_penalty=self._baseline_edge_margin_penalty,
                entropy_floor_penalty=self._baseline_edge_entropy_penalty,
            )

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
        if self._direction_distribution_loss_weight <= 0 or probabilities.shape[0] == 0:
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
        if self._flat_probability_floor_weight <= 0 or probabilities.shape[0] == 0:
            return probabilities.new_tensor(0.0)

        flat_probability_mean = probabilities[:, 2].mean()
        deficit = torch.relu(probabilities.new_tensor(self._flat_probability_floor_target) - flat_probability_mean)
        return deficit ** 2

    def _class_probability_floor_loss(self, probabilities: torch.Tensor) -> torch.Tensor:
        if self._class_probability_floor_weight <= 0 or probabilities.shape[0] == 0:
            return probabilities.new_tensor(0.0)

        predicted_distribution = probabilities.mean(dim=0)
        floor_targets = probabilities.new_tensor(self._class_probability_floor_targets)
        deficits = torch.relu(floor_targets - predicted_distribution)

        # UP, DOWN, FLAT. DOWN and FLAT get stronger pressure because quick-quality
        # showed UP-dominance plus weak DOWN/FLAT coverage.
        class_penalty = probabilities.new_tensor([0.75, 1.35, 1.25])
        return torch.mean(class_penalty * deficits ** 2)

    def _dominant_class_ceiling_loss(self, probabilities: torch.Tensor) -> torch.Tensor:
        if self._dominant_class_ceiling_weight <= 0 or probabilities.shape[0] == 0:
            return probabilities.new_tensor(0.0)

        predicted_distribution = probabilities.mean(dim=0)
        dominant_probability = torch.max(predicted_distribution)
        excess = torch.relu(dominant_probability - probabilities.new_tensor(self._dominant_class_ceiling_target))
        return excess ** 2

    def _true_class_margin_loss(
        self,
        logits: torch.Tensor,
        targets: torch.Tensor,
        sample_weights: torch.Tensor | None = None,
    ) -> torch.Tensor:
        if not self._class_margin_active() or self._true_class_margin_weight <= 0 or logits.shape[0] == 0:
            return logits.new_tensor(0.0)

        probabilities = torch.softmax(logits, dim=1)
        target_probabilities = probabilities.gather(1, targets.view(-1, 1)).squeeze(1)
        mask = F.one_hot(targets, num_classes=logits.shape[1]).bool()
        competing_probabilities = probabilities.masked_fill(mask, 0.0).max(dim=1).values
        deficit = torch.relu(
            logits.new_tensor(self._true_class_margin_target)
            - (target_probabilities - competing_probabilities)
        )
        return _weighted_mean(deficit, sample_weights)

    def _up_down_margin_loss(
        self,
        logits: torch.Tensor,
        targets: torch.Tensor,
        sample_weights: torch.Tensor | None = None,
    ) -> torch.Tensor:
        if not self._class_margin_active() or self._up_down_margin_weight <= 0 or logits.shape[0] == 0:
            return logits.new_tensor(0.0)

        probabilities = torch.softmax(logits, dim=1)
        directional_mask = (targets == 0) | (targets == 1)
        if not torch.any(directional_mask):
            return logits.new_tensor(0.0)

        direction_targets = targets[directional_mask]
        direction_probabilities = probabilities[directional_mask]
        target_direction_probabilities = direction_probabilities.gather(1, direction_targets.view(-1, 1)).squeeze(1)
        opposite_targets = torch.where(direction_targets == 0, 1, 0)
        opposite_probabilities = direction_probabilities.gather(1, opposite_targets.view(-1, 1)).squeeze(1)
        deficit = torch.relu(
            logits.new_tensor(self._up_down_margin_target)
            - (target_direction_probabilities - opposite_probabilities)
        )
        masked_weights = None if sample_weights is None else sample_weights[directional_mask]
        return _weighted_mean(deficit, masked_weights)

    def _flat_margin_loss(
        self,
        logits: torch.Tensor,
        targets: torch.Tensor,
        *,
        batch: dict[str, torch.Tensor],
        sample_weights: torch.Tensor | None = None,
    ) -> torch.Tensor:
        if not self._class_margin_active() or self._flat_margin_weight <= 0 or logits.shape[0] == 0:
            return logits.new_tensor(0.0)

        base_mask = targets == 2
        allowed_mask = batch.get("flat_margin_allowed_mask")
        if allowed_mask is not None:
            base_mask = base_mask & (allowed_mask.to(device=targets.device) > 0.5)
        if not torch.any(base_mask):
            return logits.new_tensor(0.0)

        probabilities = torch.softmax(logits[base_mask], dim=1)
        flat_probabilities = probabilities[:, 2]
        competing_probabilities = probabilities[:, :2].max(dim=1).values
        deficit = torch.relu(
            logits.new_tensor(self._flat_margin_target)
            - (flat_probabilities - competing_probabilities)
        )
        masked_weights = None if sample_weights is None else sample_weights[base_mask]
        return _weighted_mean(deficit, masked_weights)

    def _hard_negative_margin_loss(
        self,
        logits: torch.Tensor,
        targets: torch.Tensor,
        sample_weights: torch.Tensor | None = None,
    ) -> torch.Tensor:
        if not self._class_margin_active() or self._hard_negative_margin_weight <= 0 or logits.shape[0] == 0:
            return logits.new_tensor(0.0)

        probabilities = torch.softmax(logits, dim=1)
        target_probabilities = probabilities.gather(1, targets.view(-1, 1)).squeeze(1)
        predicted_labels = torch.argmax(probabilities, dim=1)
        hard_mask = predicted_labels != targets
        if not torch.any(hard_mask):
            return logits.new_tensor(0.0)

        mask = F.one_hot(targets, num_classes=logits.shape[1]).bool()
        competing_probabilities = probabilities.masked_fill(mask, 0.0).max(dim=1).values
        hard_target_probabilities = target_probabilities[hard_mask]
        hard_competing_probabilities = competing_probabilities[hard_mask]
        deficit = torch.relu(
            logits.new_tensor(self._hard_negative_margin_target)
            - (hard_target_probabilities - hard_competing_probabilities)
        )
        masked_weights = None if sample_weights is None else sample_weights[hard_mask]
        return _weighted_mean(deficit, masked_weights)

    def _class_margin_active(self) -> bool:
        return self._class_margin_objective_enabled and self._class_margin_objective_allowed


def _target_logit_gap(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    target_logits = logits.gather(1, targets.view(-1, 1)).squeeze(1)
    mask = F.one_hot(targets, num_classes=logits.shape[1]).bool()
    other_logits = logits.masked_fill(mask, float("-inf")).max(dim=1).values
    return target_logits - other_logits


def _direction_sample_weights(batch: dict[str, torch.Tensor], logits: torch.Tensor) -> torch.Tensor:
    weights = batch.get("direction_sample_weight")
    if weights is None:
        return torch.ones((logits.shape[0],), dtype=logits.dtype, device=logits.device)
    return weights.to(dtype=logits.dtype, device=logits.device).clamp(0.20, 4.00)


def _weighted_mean(values: torch.Tensor, sample_weights: torch.Tensor | None = None) -> torch.Tensor:
    if sample_weights is None:
        return torch.mean(values)
    weights = sample_weights.to(dtype=values.dtype, device=values.device)
    if weights.shape != values.shape:
        weights = weights.view_as(values)
    denominator = torch.sum(weights).clamp_min(1e-8)
    return torch.sum(values * weights) / denominator


def baseline_edge_aware_direction_loss(
    logits: torch.Tensor,
    targets: torch.Tensor,
    *,
    sample_weights: torch.Tensor | None = None,
    class_weights: torch.Tensor | None = None,
    focal_gamma: float = 1.25,
    confidence_margin_penalty: float = 0.02,
    entropy_floor_penalty: float = 0.01,
) -> torch.Tensor:
    """Direction loss for ML38.9.2.

    This loss keeps cross entropy as the core objective, adds focal pressure for
    hard rows, uses sample weights from baseline_edge_sample_weight_for_row, and
    adds small regularizers to discourage low-margin uniform outputs and extreme
    one-class collapse.
    """
    ce = F.cross_entropy(logits, targets, weight=class_weights, reduction="none")
    probs = torch.softmax(logits, dim=1)
    target_probs = probs.gather(1, targets.view(-1, 1)).squeeze(1)
    focal = torch.pow(1.0 - target_probs.clamp(0.0, 1.0), focal_gamma)
    per_row = ce * focal

    if sample_weights is not None:
        per_row = per_row * sample_weights.to(per_row.device).float()

    loss = per_row.mean()

    if confidence_margin_penalty > 0:
        top2 = torch.topk(probs, k=2, dim=1).values
        margin = top2[:, 0] - top2[:, 1]
        loss = loss + confidence_margin_penalty * torch.relu(0.08 - margin).mean()

    if entropy_floor_penalty > 0:
        mean_probs = probs.mean(dim=0)
        max_mean_prob = mean_probs.max()
        loss = loss + entropy_floor_penalty * torch.relu(max_mean_prob - 0.78)

    return loss
