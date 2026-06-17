import torch

from app.training.probability_calibration import fit_direction_temperature_from_logits
from app.training.probability_calibration import softmax_with_temperature


def test_temperature_below_one_sharpens_probabilities() -> None:
    logits = torch.tensor([[0.20, 0.18, 0.17]], dtype=torch.float32)

    raw = softmax_with_temperature(logits, 1.0)
    sharp = softmax_with_temperature(logits, 0.5)

    assert float(sharp.max().item()) > float(raw.max().item())


def test_fit_direction_temperature_returns_report() -> None:
    logits = torch.tensor(
        [
            [1.8, 0.2, 0.0],
            [0.1, 1.7, 0.2],
            [0.2, 0.3, 1.6],
        ],
        dtype=torch.float32,
    )
    targets = torch.tensor([0, 1, 2], dtype=torch.long)

    report = fit_direction_temperature_from_logits(logits, targets, candidate_temperatures=(0.5, 1.0, 1.5))

    payload = report.to_dict()
    assert payload["enabled"] is True
    assert payload["validation_rows"] == 3
    assert payload["selected_temperature"] in {0.5, 1.0, 1.5}
    assert payload["candidate_temperatures"]
