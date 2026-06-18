import torch

from app.training.loss import MultiTaskLoss


def _batch() -> dict[str, torch.Tensor]:
    return {
        "direction_target": torch.tensor([0, 1, 1, 2, 2, 1], dtype=torch.long),
        "direction_sample_weight": torch.ones(6, dtype=torch.float32),
        "tp_sl_target": torch.tensor([1.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=torch.float32),
        "tp_sl_mask": torch.tensor([1.0, 1.0, 1.0, 0.0, 0.0, 1.0], dtype=torch.float32),
        "move_target": torch.tensor([1.0, -0.9, -0.8, 0.03, -0.02, -1.1], dtype=torch.float32),
        "risk_target": torch.tensor([0.4, 0.3, 0.5, 0.1, 0.1, 0.4], dtype=torch.float32),
    }


def _collapsed_up_outputs() -> dict[str, torch.Tensor]:
    return {
        "direction_logits": torch.tensor(
            [
                [3.0, -1.0, -1.2],
                [3.0, -1.0, -1.2],
                [3.0, -1.0, -1.2],
                [3.0, -1.0, -1.2],
                [3.0, -1.0, -1.2],
                [3.0, -1.0, -1.2],
            ],
            dtype=torch.float32,
        ),
        "tp_sl_logits": torch.zeros(6, dtype=torch.float32),
        "expected_move_atr": torch.zeros(6, dtype=torch.float32),
        "risk_score": torch.zeros(6, dtype=torch.float32),
    }


def test_ml38_9_1_bias_aware_loss_penalizes_up_dominance_and_missing_down_flat() -> None:
    loss_fn = MultiTaskLoss(
        direction_loss_name="focal",
        focal_gamma=2.2,
        direction_loss_weight=3.0,
        tp_sl_loss_weight=0.10,
        move_loss_weight=0.10,
        risk_loss_weight=0.10,
        direction_distribution_loss_weight=1.0,
        flat_probability_floor_weight=0.75,
        flat_probability_floor_target=0.16,
        min_class_probability_floor=0.05,
        class_probability_floor_weight=1.50,
        class_probability_floor_targets=(0.10, 0.18, 0.12),
        dominant_class_ceiling_weight=1.25,
        dominant_class_ceiling_target=0.72,
    )

    total_loss, metrics = loss_fn.compute(_collapsed_up_outputs(), _batch())

    assert float(total_loss.detach().item()) > 0
    assert metrics["class_probability_floor_loss"] > 0
    assert metrics["dominant_class_ceiling_loss"] > 0
    assert metrics["direction_predicted_up_probability_mean"] > 0.90
    assert metrics["direction_predicted_down_probability_mean"] < 0.18
    assert metrics["direction_predicted_flat_probability_mean"] < 0.12
    assert metrics["class_probability_floor_targets"] == [0.10, 0.18, 0.12]
    assert metrics["dominant_class_ceiling_target"] == 0.72
