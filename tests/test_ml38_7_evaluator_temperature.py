import torch

from app.training.evaluator import Evaluator


class FakeModel(torch.nn.Module):
    def forward(self, features):
        return {
            "direction_logits": torch.tensor([[0.20, 0.18, 0.17]], dtype=torch.float32),
            "tp_sl_logits": torch.tensor([0.0], dtype=torch.float32),
            "expected_move_atr": torch.tensor([1.0], dtype=torch.float32),
            "risk_score": torch.tensor([0.5], dtype=torch.float32),
        }


def test_evaluator_uses_direction_temperature() -> None:
    dataset = {
        "features": torch.tensor([[1.0]], dtype=torch.float32),
        "direction_target": torch.tensor([0], dtype=torch.long),
        "tp_sl_target": torch.tensor([1.0], dtype=torch.float32),
        "tp_sl_mask": torch.tensor([1.0], dtype=torch.float32),
        "move_target": torch.tensor([1.0], dtype=torch.float32),
        "risk_target": torch.tensor([0.5], dtype=torch.float32),
    }

    evaluator = Evaluator()
    raw = evaluator.evaluate(FakeModel(), dataset, direction_temperature=1.0)
    sharp = evaluator.evaluate(FakeModel(), dataset, direction_temperature=0.5)

    assert raw["direction_temperature"] == 1.0
    assert sharp["direction_temperature"] == 0.5
    assert sharp["brier_score"] <= raw["brier_score"]
