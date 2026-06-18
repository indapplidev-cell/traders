import torch

from app.training.loss import MultiTaskLoss


def _batch(weight: float) -> dict[str, torch.Tensor]:
    return {
        "direction_target": torch.tensor([0, 1, 2], dtype=torch.long),
        "direction_sample_weight": torch.tensor([weight, weight, weight], dtype=torch.float32),
        "tp_sl_target": torch.tensor([1.0, 0.0, 0.0], dtype=torch.float32),
        "tp_sl_mask": torch.tensor([1.0, 1.0, 0.0], dtype=torch.float32),
        "move_target": torch.tensor([1.0, -1.0, 0.1], dtype=torch.float32),
        "risk_target": torch.tensor([0.5, 0.4, 0.2], dtype=torch.float32),
    }


def _outputs() -> dict[str, torch.Tensor]:
    return {
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


def test_ml38_8_loss_reports_direction_logit_gap_and_sample_weight() -> None:
    loss_fn = MultiTaskLoss(
        direction_loss_name="focal",
        focal_gamma=2.2,
        confidence_margin_weight=0.25,
        direction_logit_gap_weight=0.15,
        direction_logit_gap_target=0.35,
        direction_loss_weight=2.25,
        tp_sl_loss_weight=0.30,
        move_loss_weight=0.25,
        risk_loss_weight=0.25,
    )

    total_loss, metrics = loss_fn.compute(_outputs(), _batch(weight=0.5))

    assert float(total_loss.detach().item()) > 0
    assert metrics["direction_loss_name"] == "focal"
    assert metrics["direction_logit_gap_loss"] > 0
    assert metrics["direction_sample_weight_mean"] == 0.5
    assert metrics["direction_loss_weight"] == 2.25
    assert metrics["tp_sl_loss_weight"] == 0.30
