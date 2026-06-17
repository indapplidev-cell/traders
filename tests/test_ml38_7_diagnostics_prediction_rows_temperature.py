from datetime import datetime, timezone
from types import SimpleNamespace

import torch

from app.diagnostics.diagnostics_service import DiagnosticsService


class FakeModel(torch.nn.Module):
    def eval(self):
        return self

    def forward(self, features):
        return {
            "direction_logits": torch.tensor([[0.20, 0.18, 0.17]], dtype=torch.float32),
            "tp_sl_logits": torch.tensor([0.0], dtype=torch.float32),
            "expected_move_atr": torch.tensor([1.0], dtype=torch.float32),
            "risk_score": torch.tensor([0.5], dtype=torch.float32),
        }


class FakeModelLoader:
    def load(self, model_version):
        return (
            FakeModel(),
            {"mean": [0.0], "std": [1.0]},
            ["x"],
            {"probability_calibration": {"selected_temperature": 0.5}},
            {},
        )


class FakeCandleRepository:
    def get_all(self, symbol, interval):
        return [
            SimpleNamespace(
                open_time=datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc),
                close=100.0,
                high=101.0,
                low=99.0,
            ),
            SimpleNamespace(
                open_time=datetime(2026, 5, 1, 0, 15, tzinfo=timezone.utc),
                close=101.0,
                high=102.0,
                low=100.0,
            ),
        ]


def test_diagnostics_prediction_rows_use_loaded_direction_temperature(tmp_path) -> None:
    service = DiagnosticsService(
        dataset_builder=object(),
        feature_repository=object(),
        model_registry_repository=object(),
        artifact_storage=object(),
        model_loader=FakeModelLoader(),
        reports_dir=tmp_path,
        candle_repository=FakeCandleRepository(),
    )
    target_row = SimpleNamespace(
        candle_open_time=datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc),
        direction_label="UP",
        tp_before_sl=True,
        future_move_atr=1.0,
        max_adverse_move_atr=0.30,
        features_json={"x": 1.0, "atr_14": 10.0},
    )

    rows = service._build_prediction_rows_for_subset(
        model_version="mv1",
        symbol="BTCUSDT",
        interval="15m",
        horizon_candles=1,
        feature_version="fv1",
        label_version="lv1",
        target_rows=[target_row],
    )

    assert rows[0]["direction_temperature"] == 0.5
    assert rows[0]["probability_source"] == "temperature_scaled"
    assert rows[0]["confidence"] > 0.34
