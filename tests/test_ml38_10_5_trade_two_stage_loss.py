from __future__ import annotations

import torch

from app.training.loss import MultiTaskLoss


def test_trade_two_stage_loss_uses_opportunity_and_masked_binary_direction() -> None:
    loss_fn = MultiTaskLoss(training_objective="trade_two_stage")
    outputs = {
        "direction_logits": torch.tensor([[3.0, 0.0, 6.0], [0.0, 3.0, 6.0], [0.0, 0.0, 6.0]], dtype=torch.float32),
        "opportunity_logit": torch.tensor([3.0, 3.0, -3.0], dtype=torch.float32),
        "tp_sl_logits": torch.tensor([1.0, 1.0, 0.0], dtype=torch.float32),
        "expected_move_atr": torch.tensor([1.0, 1.0, 0.0], dtype=torch.float32),
        "risk_score": torch.tensor([0.3, 0.3, 0.0], dtype=torch.float32),
    }
    batch = {
        "direction_target": torch.tensor([0, 1, 2]),
        "direction_sample_weight": torch.tensor([1.0, 1.0, 1.0]),
        "direction_trade_target": torch.tensor([0, 1, 1]),
        "direction_trade_mask": torch.tensor([1.0, 1.0, 0.0]),
        "opportunity_target": torch.tensor([1.0, 1.0, 0.0]),
        "tp_sl_target": torch.tensor([1.0, 1.0, 0.0]),
        "tp_sl_mask": torch.tensor([1.0, 1.0, 0.0]),
        "move_target": torch.tensor([1.0, 1.0, 0.0]),
        "risk_target": torch.tensor([0.3, 0.3, 0.0]),
        "flat_margin_allowed_mask": torch.tensor([0.0, 0.0, 1.0]),
    }

    total_loss, losses = loss_fn.compute(outputs, batch)

    assert float(total_loss.item()) >= 0.0
    assert losses["trade_two_stage_enabled"] == 1.0
    assert losses["direction_trade_rows"] == 2.0
    assert 0.0 < losses["trade_row_ratio"] < 1.0
