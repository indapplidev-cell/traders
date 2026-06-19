from __future__ import annotations

import torch

from app.training.evaluator import Evaluator


class FakeTwoStageModel(torch.nn.Module):
    def forward(self, features: torch.Tensor) -> dict[str, torch.Tensor]:
        return {
            "direction_logits": torch.tensor([[2.0, 0.0, 5.0], [0.0, 2.0, 5.0], [2.0, 0.0, 5.0]], dtype=torch.float32),
            "opportunity_logit": torch.tensor([3.0, 3.0, -3.0], dtype=torch.float32),
            "tp_sl_logits": torch.zeros(3, dtype=torch.float32),
            "expected_move_atr": torch.zeros(3, dtype=torch.float32),
            "risk_score": torch.zeros(3, dtype=torch.float32),
        }


def test_evaluator_reports_two_stage_metrics() -> None:
    dataset = {
        "features": torch.tensor([[1.0], [2.0], [3.0]], dtype=torch.float32),
        "direction_target": torch.tensor([0, 1, 2], dtype=torch.long),
        "opportunity_target": torch.tensor([1.0, 1.0, 0.0], dtype=torch.float32),
        "direction_trade_target": torch.tensor([0, 1, 1], dtype=torch.long),
        "direction_trade_mask": torch.tensor([1.0, 1.0, 0.0], dtype=torch.float32),
        "tp_sl_target": torch.tensor([1.0, 1.0, 0.0], dtype=torch.float32),
        "tp_sl_mask": torch.tensor([1.0, 1.0, 0.0], dtype=torch.float32),
        "move_target": torch.tensor([1.0, 1.0, 0.0], dtype=torch.float32),
        "risk_target": torch.tensor([0.3, 0.3, 0.0], dtype=torch.float32),
    }

    metrics = Evaluator().evaluate(
        FakeTwoStageModel(),
        dataset,
        training_objective="trade_two_stage",
    )

    assert metrics["training_objective"] == "trade_two_stage"
    assert metrics["direction_trade_rows"] == 2
    assert metrics["direction_accuracy_on_trade_rows"] == 1.0
    assert metrics["opportunity_recall"] == 1.0
    assert "direction_probabilities_conditioned_on_trade_mean" in metrics
