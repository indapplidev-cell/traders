import torch

from app.models.mlp_model import CandleMLP


def test_mlp_model_returns_expected_head_shapes() -> None:
    model = CandleMLP(input_dim=34)
    inputs = torch.randn(5, 34)

    outputs = model(inputs)

    assert outputs["direction_logits"].shape == (5, 3)
    assert outputs["tp_sl_logits"].shape == (5,)
    assert outputs["expected_move_atr"].shape == (5,)
    assert outputs["risk_score"].shape == (5,)
