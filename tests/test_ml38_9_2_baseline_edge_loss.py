import torch

from app.training.loss import baseline_edge_aware_direction_loss


def test_baseline_edge_aware_direction_loss_returns_scalar() -> None:
    logits = torch.tensor(
        [
            [2.0, 0.2, 0.1],
            [0.1, 2.0, 0.2],
            [0.2, 0.1, 2.0],
        ],
        dtype=torch.float32,
    )
    targets = torch.tensor([0, 1, 2], dtype=torch.long)
    sample_weights = torch.tensor([1.0, 1.5, 2.0], dtype=torch.float32)

    loss = baseline_edge_aware_direction_loss(
        logits,
        targets,
        sample_weights=sample_weights,
    )

    assert loss.ndim == 0
    assert float(loss.detach().cpu()) > 0
