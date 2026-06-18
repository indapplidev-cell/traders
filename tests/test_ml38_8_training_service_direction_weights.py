from datetime import datetime, timezone

from app.dataset.dataset_models import DatasetRow
from app.training.training_service import TrainingService


def test_rows_to_tensors_includes_direction_sample_weight() -> None:
    rows = [
        DatasetRow(
            symbol="BTCUSDT",
            interval="15m",
            candle_open_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
            feature_version="fv3",
            label_version="lv_test",
            horizon_candles=8,
            features_json={"x": 1.0},
            direction_label="UP",
            tp_before_sl=True,
            future_return=0.01,
            future_move_atr=1.0,
            max_favorable_move_atr=1.2,
            max_adverse_move_atr=0.1,
        ),
        DatasetRow(
            symbol="BTCUSDT",
            interval="15m",
            candle_open_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
            feature_version="fv3",
            label_version="lv_test",
            horizon_candles=8,
            features_json={"x": 2.0},
            direction_label="UP",
            tp_before_sl=True,
            future_return=0.01,
            future_move_atr=0.1,
            max_favorable_move_atr=0.3,
            max_adverse_move_atr=0.25,
        ),
    ]

    tensors = TrainingService.rows_to_tensors(
        rows=rows,
        feature_columns=["x"],
        scaler={"mean": [0.0], "std": [1.0]},
    )

    assert "direction_sample_weight" in tensors
    assert tensors["direction_sample_weight"].shape == (2,)
    assert float(tensors["direction_sample_weight"][0].item()) > float(tensors["direction_sample_weight"][1].item())
