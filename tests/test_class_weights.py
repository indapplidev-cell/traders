from datetime import datetime, timezone

from app.dataset.dataset_models import DatasetRow
from app.features.feature_models import FEATURE_NAMES
from app.training.training_service import TrainingService


def test_class_weights_are_computed_with_inverse_frequency_rule() -> None:
    rows = [
        _row("UP", datetime(2025, 1, 1, tzinfo=timezone.utc)),
        _row("UP", datetime(2025, 1, 2, tzinfo=timezone.utc)),
        _row("DOWN", datetime(2025, 1, 3, tzinfo=timezone.utc)),
    ]

    weights = TrainingService.compute_direction_class_weights(rows)

    assert weights == [0.5, 1.0, 0.0]


def _row(direction_label: str, open_time: datetime) -> DatasetRow:
    return DatasetRow(
        symbol="BTCUSDT",
        interval="15m",
        candle_open_time=open_time,
        feature_version="fv1",
        label_version="lv1",
        horizon_candles=8,
        features_json={name: 1.0 for name in FEATURE_NAMES},
        direction_label=direction_label,
        tp_before_sl=None,
        future_return=0.0,
        future_move_atr=1.0,
        max_favorable_move_atr=1.0,
        max_adverse_move_atr=0.5,
    )
