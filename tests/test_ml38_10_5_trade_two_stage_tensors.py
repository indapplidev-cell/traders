from __future__ import annotations

from datetime import datetime, timezone

from app.dataset.dataset_models import DatasetRow
from app.training.training_service import TrainingService


def _row(label: str, opportunity_label: int) -> DatasetRow:
    return DatasetRow(
        symbol="BTCUSDT",
        interval="15m",
        candle_open_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        feature_version="fv4_book_setup_context",
        label_version="lv16_h12_trade_two_stage",
        horizon_candles=12,
        features_json={"x": 1.0},
        direction_label=label,
        tp_before_sl=True if opportunity_label else None,
        future_return=0.01 if opportunity_label else 0.0,
        future_move_atr=1.0 if opportunity_label else 0.1,
        max_favorable_move_atr=1.2 if opportunity_label else 0.1,
        max_adverse_move_atr=0.4 if opportunity_label else 0.1,
        opportunity_label=opportunity_label,
        setup_type="test_setup" if opportunity_label else "no_setup",
        setup_quality_score=0.8 if opportunity_label else 0.0,
        setup_invalidation_distance_atr=0.4,
        setup_expected_move_atr=1.0,
        label_ambiguity_score=0.1,
    )


def test_trade_two_stage_rows_to_tensors_adds_trade_targets() -> None:
    rows = [_row("UP", 1), _row("DOWN", 1), _row("FLAT", 0)]
    tensors = TrainingService.rows_to_tensors(
        rows,
        feature_columns=["x"],
        scaler={"mean": [0.0], "std": [1.0]},
        training_objective="trade_two_stage",
    )

    assert tensors["opportunity_target"].tolist() == [1.0, 1.0, 0.0]
    assert tensors["direction_trade_target"].tolist() == [0, 1, 1]
    assert tensors["direction_trade_mask"].tolist() == [1.0, 1.0, 0.0]
    assert tensors["no_trade_target"].tolist() == [0.0, 0.0, 1.0]
