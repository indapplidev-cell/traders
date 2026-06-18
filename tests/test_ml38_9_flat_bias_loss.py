import torch

from app.training.loss import MultiTaskLoss


def _batch() -> dict[str, torch.Tensor]:
    return {
        "direction_target": torch.tensor([0, 0, 1, 2, 2, 2], dtype=torch.long),
        "direction_sample_weight": torch.ones(6, dtype=torch.float32),
        "tp_sl_target": torch.tensor([1.0, 1.0, 0.0, 0.0, 0.0, 0.0], dtype=torch.float32),
        "tp_sl_mask": torch.tensor([1.0, 1.0, 1.0, 0.0, 0.0, 0.0], dtype=torch.float32),
        "move_target": torch.tensor([1.0, 0.9, -0.7, 0.05, -0.03, 0.02], dtype=torch.float32),
        "risk_target": torch.tensor([0.4, 0.3, 0.5, 0.1, 0.1, 0.1], dtype=torch.float32),
    }


def _collapsed_up_outputs() -> dict[str, torch.Tensor]:
    return {
        "direction_logits": torch.tensor(
            [
                [2.5, -0.5, -1.0],
                [2.5, -0.5, -1.0],
                [2.5, -0.5, -1.0],
                [2.5, -0.5, -1.0],
                [2.5, -0.5, -1.0],
                [2.5, -0.5, -1.0],
            ],
            dtype=torch.float32,
        ),
        "tp_sl_logits": torch.zeros(6, dtype=torch.float32),
        "expected_move_atr": torch.zeros(6, dtype=torch.float32),
        "risk_score": torch.zeros(6, dtype=torch.float32),
    }


def test_ml38_9_flat_probability_floor_penalizes_flat_underprediction() -> None:
    loss_fn = MultiTaskLoss(
        direction_loss_name="focal",
        focal_gamma=2.2,
        direction_loss_weight=3.0,
        tp_sl_loss_weight=0.10,
        move_loss_weight=0.10,
        risk_loss_weight=0.10,
        direction_distribution_loss_weight=0.75,
        flat_probability_floor_weight=1.0,
        flat_probability_floor_target=0.20,
        min_class_probability_floor=0.05,
    )

    total_loss, metrics = loss_fn.compute(_collapsed_up_outputs(), _batch())

    assert float(total_loss.detach().item()) > 0
    assert metrics["flat_probability_floor_loss"] > 0
    assert metrics["direction_distribution_loss"] > 0
    assert metrics["direction_predicted_flat_probability_mean"] < 0.20
    assert metrics["direction_distribution_loss_weight"] == 0.75
    assert metrics["flat_probability_floor_weight"] == 1.0
