from __future__ import annotations

import torch

from app.training.evaluator import Evaluator


class ThresholdControlModel(torch.nn.Module):
    def forward(self, features: torch.Tensor) -> dict[str, torch.Tensor]:
        return {
            "direction_logits": torch.tensor(
                [[2.0, 0.0, 0.0], [0.0, 2.0, 0.0], [2.0, 0.0, 0.0], [0.0, 2.0, 0.0]],
                dtype=torch.float32,
            ),
            "opportunity_logit": torch.tensor([0.08, 0.32, 0.66, 0.95], dtype=torch.float32),
            "tp_sl_logits": torch.zeros(4, dtype=torch.float32),
            "expected_move_atr": torch.zeros(4, dtype=torch.float32),
            "risk_score": torch.zeros(4, dtype=torch.float32),
        }


def test_evaluator_uses_configured_opportunity_threshold() -> None:
    dataset = {
        "features": torch.tensor([[1.0], [2.0], [3.0], [4.0]], dtype=torch.float32),
        "direction_target": torch.tensor([0, 1, 0, 2], dtype=torch.long),
        "opportunity_target": torch.tensor([1.0, 1.0, 1.0, 0.0], dtype=torch.float32),
        "direction_trade_target": torch.tensor([0, 1, 0, 1], dtype=torch.long),
        "direction_trade_mask": torch.tensor([1.0, 1.0, 1.0, 0.0], dtype=torch.float32),
        "tp_sl_target": torch.tensor([1.0, 1.0, 1.0, 0.0], dtype=torch.float32),
        "tp_sl_mask": torch.tensor([1.0, 1.0, 1.0, 0.0], dtype=torch.float32),
        "move_target": torch.tensor([1.0, 1.0, 1.0, 0.0], dtype=torch.float32),
        "risk_target": torch.tensor([0.3, 0.3, 0.3, 0.0], dtype=torch.float32),
    }

    low_threshold_metrics = Evaluator().evaluate(
        ThresholdControlModel(),
        dataset,
        opportunity_probability_threshold=0.50,
        training_objective="trade_two_stage",
    )
    high_threshold_metrics = Evaluator().evaluate(
        ThresholdControlModel(),
        dataset,
        opportunity_probability_threshold=0.65,
        training_objective="trade_two_stage",
    )

    assert low_threshold_metrics["predicted_trade_rate"] > high_threshold_metrics["predicted_trade_rate"]
    assert high_threshold_metrics["opportunity_probability_threshold"] == 0.65
