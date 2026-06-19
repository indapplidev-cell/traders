from __future__ import annotations

import torch

from app.training.loss import MultiTaskLoss


def test_class_margin_loss_reports_positive_components_when_logits_lack_separation() -> None:
    loss_fn = MultiTaskLoss(
        class_margin_objective_enabled=True,
        class_margin_objective_allowed=True,
        true_class_margin_weight=1.0,
        up_down_margin_weight=1.0,
        flat_margin_weight=1.0,
        hard_negative_margin_weight=1.0,
    )
    batch = {
        "direction_target": torch.tensor([0, 1, 2]),
        "direction_sample_weight": torch.tensor([1.0, 1.0, 1.0]),
        "tp_sl_target": torch.tensor([1.0, 1.0, 0.0]),
        "tp_sl_mask": torch.tensor([1.0, 1.0, 0.0]),
        "move_target": torch.tensor([1.0, 1.0, 0.1]),
        "risk_target": torch.tensor([0.4, 0.4, 0.1]),
        "opportunity_target": torch.tensor([1.0, 1.0, 0.0]),
        "flat_margin_allowed_mask": torch.tensor([0.0, 0.0, 1.0]),
    }
    outputs = {
        "direction_logits": torch.tensor(
            [
                [0.15, 0.10, 0.05],
                [0.20, 0.19, 0.18],
                [0.33, 0.32, 0.31],
            ]
        ),
        "tp_sl_logits": torch.tensor([0.1, 0.1, 0.0]),
        "expected_move_atr": torch.tensor([0.9, 0.9, 0.1]),
        "risk_score": torch.tensor([0.5, 0.5, 0.1]),
    }

    total_loss, metrics = loss_fn.compute(outputs, batch)

    assert float(total_loss.item()) >= 0.0
    assert metrics["true_class_margin_loss"] > 0.0
    assert metrics["up_down_margin_loss"] > 0.0
    assert metrics["flat_margin_loss"] > 0.0
    assert metrics["hard_negative_margin_loss"] > 0.0


def test_flat_margin_loss_ignores_volatile_flat_rows() -> None:
    loss_fn = MultiTaskLoss(
        class_margin_objective_enabled=True,
        class_margin_objective_allowed=True,
        flat_margin_weight=1.0,
    )
    batch = {
        "direction_target": torch.tensor([2]),
        "direction_sample_weight": torch.tensor([1.0]),
        "tp_sl_target": torch.tensor([0.0]),
        "tp_sl_mask": torch.tensor([0.0]),
        "move_target": torch.tensor([0.1]),
        "risk_target": torch.tensor([0.1]),
        "opportunity_target": torch.tensor([0.0]),
        "flat_margin_allowed_mask": torch.tensor([0.0]),
    }
    outputs = {
        "direction_logits": torch.tensor([[0.40, 0.38, 0.36]]),
        "tp_sl_logits": torch.tensor([0.0]),
        "expected_move_atr": torch.tensor([0.1]),
        "risk_score": torch.tensor([0.1]),
    }

    _total_loss, metrics = loss_fn.compute(outputs, batch)

    assert metrics["flat_margin_loss"] == 0.0
