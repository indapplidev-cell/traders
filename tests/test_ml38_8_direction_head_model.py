import torch

from app.models.mlp_model import CandleMLP


def test_ml38_8_direction_head_keeps_output_shapes_and_exposes_hidden() -> None:
    model = CandleMLP(input_dim=34)
    inputs = torch.randn(5, 34)

    outputs = model(inputs)

    assert outputs["direction_logits"].shape == (5, 3)
    assert outputs["direction_hidden"].shape == (5, 96)
    assert outputs["tp_sl_logits"].shape == (5,)
    assert outputs["expected_move_atr"].shape == (5,)
    assert outputs["risk_score"].shape == (5,)
