from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from app.dataset.dataset_models import DatasetRow
from app.training.training_service import TrainingService


def test_rows_to_tensors_include_setup_quality_score_tensor() -> None:
    row = DatasetRow(
        symbol="BTCUSDT",
        interval="15m",
        candle_open_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        feature_version="fv4_book_setup_context",
        label_version="lv18_h08_tts_thr065_sq060",
        horizon_candles=8,
        features_json={"x": 1.0},
        direction_label="UP",
        tp_before_sl=True,
        future_return=0.01,
        future_move_atr=1.0,
        max_favorable_move_atr=1.2,
        max_adverse_move_atr=0.3,
        opportunity_label=1,
        setup_quality_score=0.77,
        setup_invalidation_distance_atr=0.3,
        setup_expected_move_atr=1.0,
        label_ambiguity_score=0.1,
    )
    legacy_row = SimpleNamespace(
        features_json={"x": 2.0},
        direction_label="FLAT",
        tp_before_sl=None,
        future_move_atr=0.0,
        max_adverse_move_atr=0.0,
        max_favorable_move_atr=0.0,
        opportunity_label=0,
        setup_expected_move_atr=0.0,
        setup_invalidation_distance_atr=0.0,
        label_ambiguity_score=1.0,
    )

    tensors = TrainingService.rows_to_tensors(
        [row, legacy_row],
        feature_columns=["x"],
        scaler={"mean": [0.0], "std": [1.0]},
        training_objective="trade_two_stage",
    )

    assert "setup_quality_score" in tensors
    assert abs(tensors["setup_quality_score"][0].item() - 0.77) < 1e-6
    assert tensors["setup_quality_score"][1].item() == 0.0
    assert len(tensors["setup_quality_score"]) == 2


def test_empty_tensors_include_setup_quality_score_tensor() -> None:
    tensors = TrainingService.empty_tensors(3)
    assert "setup_quality_score" in tensors
    assert tensors["setup_quality_score"].numel() == 0
