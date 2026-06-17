from types import SimpleNamespace

import torch

from app.diagnostics.prediction_diagnostics import PredictionDiagnostics


class FakeModel(torch.nn.Module):
    def eval(self):
        return self

    def forward(self, features):
        return {
            "direction_logits": torch.tensor(
                [
                    [0.20, 0.18, 0.17],
                    [0.18, 0.20, 0.17],
                ],
                dtype=torch.float32,
            ),
            "tp_sl_logits": torch.tensor([0.0, 0.0], dtype=torch.float32),
            "expected_move_atr": torch.tensor([1.0, -1.0], dtype=torch.float32),
            "risk_score": torch.tensor([0.5, 0.5], dtype=torch.float32),
        }


def test_prediction_diagnostics_uses_direction_temperature() -> None:
    rows = [
        SimpleNamespace(
            direction_label="UP",
            tp_before_sl=True,
            future_move_atr=1.0,
            max_adverse_move_atr=0.35,
            features_json={"x": 1.0},
        ),
        SimpleNamespace(
            direction_label="DOWN",
            tp_before_sl=False,
            future_move_atr=-1.0,
            max_adverse_move_atr=0.45,
            features_json={"x": 2.0},
        ),
    ]

    report = PredictionDiagnostics().analyze_split(
        FakeModel(),
        rows,
        feature_columns=["x"],
        scaler={"mean": [0.0], "std": [1.0]},
        direction_temperature=0.5,
    )

    assert report["direction_temperature"] == 0.5
    assert report["probability_source"] == "temperature_scaled"
    assert report["rows"] == 2
