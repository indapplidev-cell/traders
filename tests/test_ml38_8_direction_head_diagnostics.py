from datetime import datetime, timezone

import torch

from app.dataset.dataset_models import DatasetRow
from app.diagnostics.direction_head_separation_diagnostics import DirectionHeadSeparationDiagnostics
from app.diagnostics.direction_head_separation_diagnostics import LabelNoiseDiagnostics
from app.diagnostics.direction_head_separation_diagnostics import direction_sample_weight_for_row


class FakeModel(torch.nn.Module):
    def forward(self, features):
        return {
            "direction_logits": torch.tensor(
                [
                    [0.80, 0.20, 0.10],
                    [0.20, 0.75, 0.10],
                    [0.10, 0.20, 0.70],
                ],
                dtype=torch.float32,
            ),
            "tp_sl_logits": torch.zeros((3,), dtype=torch.float32),
            "expected_move_atr": torch.zeros((3,), dtype=torch.float32),
            "risk_score": torch.zeros((3,), dtype=torch.float32),
        }


def test_direction_head_diagnostics_reports_logit_gap() -> None:
    dataset = {
        "features": torch.ones((3, 2), dtype=torch.float32),
        "direction_target": torch.tensor([0, 1, 2], dtype=torch.long),
    }

    payload = DirectionHeadSeparationDiagnostics().build_for_splits(
        model=FakeModel(),
        datasets={"test": dataset},
    )

    test_payload = payload["splits"]["test"]
    assert test_payload["rows"] == 3
    assert test_payload["top1_logit_gap_q50"] > 0.4
    assert test_payload["positive_target_gap_ratio"] == 1.0
    assert payload["weak_direction_head_detected"] is False


def test_label_noise_diagnostics_and_sample_weight() -> None:
    clean = _row("UP", future_move_atr=1.0, favorable=1.2, adverse=0.2)
    noisy = _row("UP", future_move_atr=0.1, favorable=0.4, adverse=0.35)

    assert direction_sample_weight_for_row(clean) > direction_sample_weight_for_row(noisy)

    payload = LabelNoiseDiagnostics().build_by_split({"train": [clean, noisy], "validation": [], "test": []})
    assert payload["splits"]["train"]["rows"] == 2
    assert payload["splits"]["train"]["low_weight_ratio"] > 0.0


def _row(label: str, future_move_atr: float, favorable: float, adverse: float) -> DatasetRow:
    return DatasetRow(
        symbol="BTCUSDT",
        interval="15m",
        candle_open_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        feature_version="fv3",
        label_version="lv_test",
        horizon_candles=8,
        features_json={"x": 1.0},
        direction_label=label,
        tp_before_sl=True,
        future_return=0.01,
        future_move_atr=future_move_atr,
        max_favorable_move_atr=favorable,
        max_adverse_move_atr=adverse,
    )
