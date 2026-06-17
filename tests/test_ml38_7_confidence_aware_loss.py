import torch

from app.training.loss import MultiTaskLoss


def test_focal_loss_and_confidence_margin_return_metrics() -> None:
    loss_fn = MultiTaskLoss(
        direction_loss_name="focal",
        focal_gamma=2.0,
        label_smoothing=0.02,
        confidence_margin_weight=0.2,
        confidence_margin_target=0.12,
    )
    batch = {
        "direction_target": torch.tensor([0, 1, 2], dtype=torch.long),
        "tp_sl_target": torch.tensor([1.0, 0.0, 0.0], dtype=torch.float32),
        "tp_sl_mask": torch.tensor([1.0, 1.0, 0.0], dtype=torch.float32),
        "move_target": torch.tensor([1.0, -1.0, 0.1], dtype=torch.float32),
        "risk_target": torch.tensor([0.5, 0.4, 0.2], dtype=torch.float32),
    }
    outputs = {
        "direction_logits": torch.tensor(
            [
                [0.35, 0.33, 0.32],
                [0.33, 0.35, 0.32],
                [0.33, 0.32, 0.35],
            ],
            dtype=torch.float32,
        ),
        "tp_sl_logits": torch.tensor([0.5, -0.5, 0.0], dtype=torch.float32),
        "expected_move_atr": torch.tensor([0.8, -0.7, 0.2], dtype=torch.float32),
        "risk_score": torch.tensor([0.4, 0.3, 0.2], dtype=torch.float32),
    }

    total_loss, metrics = loss_fn.compute(outputs, batch)

    assert float(total_loss.detach().item()) > 0
    assert metrics["direction_loss_name"] == "focal"
    assert metrics["confidence_margin_loss"] > 0
    assert "total_loss" in metrics
