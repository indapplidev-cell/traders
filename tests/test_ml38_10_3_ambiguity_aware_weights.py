from __future__ import annotations

from datetime import datetime, timezone

from app.dataset.dataset_models import DatasetRow
from app.training.training_service import TrainingService


def test_class_margin_weighting_prefers_clean_high_quality_rows() -> None:
    rows = [
        DatasetRow(
            symbol="BTCUSDT",
            interval="15m",
            candle_open_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
            feature_version="fv4_book_setup_context",
            label_version="lv14_h12_cm_setup",
            horizon_candles=12,
            features_json={"x": 1.0},
            direction_label="UP",
            tp_before_sl=True,
            future_return=0.02,
            future_move_atr=1.0,
            max_favorable_move_atr=1.2,
            max_adverse_move_atr=0.2,
            opportunity_label=1,
            setup_quality_score=0.85,
            label_ambiguity_score=0.15,
        ),
        DatasetRow(
            symbol="BTCUSDT",
            interval="15m",
            candle_open_time=datetime(2025, 1, 2, tzinfo=timezone.utc),
            feature_version="fv4_book_setup_context",
            label_version="lv14_h12_cm_setup",
            horizon_candles=12,
            features_json={"x": 2.0},
            direction_label="UP",
            tp_before_sl=False,
            future_return=0.0,
            future_move_atr=0.25,
            max_favorable_move_atr=0.3,
            max_adverse_move_atr=0.25,
            opportunity_label=0,
            setup_quality_score=0.20,
            label_ambiguity_score=0.90,
        ),
    ]

    tensors = TrainingService.rows_to_tensors(
        rows=rows,
        feature_columns=["x"],
        scaler={"mean": [0.0], "std": [1.0]},
        class_margin_objective_enabled=True,
        class_margin_objective_allowed=True,
        class_margin_feature_separability_rating="GOOD",
    )

    assert float(tensors["direction_sample_weight"][0].item()) > float(tensors["direction_sample_weight"][1].item())


def test_flat_margin_mask_keeps_only_clean_flat_rows() -> None:
    rows = [
        DatasetRow(
            symbol="BTCUSDT",
            interval="15m",
            candle_open_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
            feature_version="fv4_book_setup_context",
            label_version="lv14_h12_cm_setup",
            horizon_candles=12,
            features_json={"x": 1.0},
            direction_label="FLAT",
            tp_before_sl=None,
            future_return=0.0,
            future_move_atr=0.10,
            max_favorable_move_atr=0.15,
            max_adverse_move_atr=0.12,
            opportunity_label=0,
            setup_quality_score=0.10,
            label_ambiguity_score=0.20,
        ),
        DatasetRow(
            symbol="BTCUSDT",
            interval="15m",
            candle_open_time=datetime(2025, 1, 2, tzinfo=timezone.utc),
            feature_version="fv4_book_setup_context",
            label_version="lv14_h12_cm_setup",
            horizon_candles=12,
            features_json={"x": 2.0},
            direction_label="FLAT",
            tp_before_sl=None,
            future_return=0.0,
            future_move_atr=0.55,
            max_favorable_move_atr=0.85,
            max_adverse_move_atr=0.45,
            opportunity_label=0,
            setup_quality_score=0.10,
            label_ambiguity_score=0.90,
        ),
    ]

    tensors = TrainingService.rows_to_tensors(
        rows=rows,
        feature_columns=["x"],
        scaler={"mean": [0.0], "std": [1.0]},
        class_margin_objective_enabled=True,
        class_margin_objective_allowed=True,
    )

    assert tensors["flat_margin_allowed_mask"].tolist() == [1.0, 0.0]
