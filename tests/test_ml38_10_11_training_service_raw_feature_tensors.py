import pytest
from datetime import datetime, timezone

from app.dataset.dataset_models import DatasetRow
from app.features.feature_models import SCHWAGER_TRAP_INVALIDATION_FEATURE_NAMES
from app.training.training_service import TrainingService


def _dataset_row(
    *,
    direction_label: str = "UP",
    features_json: dict[str, float | None] | None = None,
    opportunity_label: int = 1,
    opportunity_direction: str = "UP",
    setup_quality_score: float = 0.8,
    future_return: float = 0.01,
    future_move_atr: float = 1.0,
) -> DatasetRow:
    return DatasetRow(
        symbol="BTCUSDT",
        interval="15m",
        candle_open_time=datetime(2026, 5, 1, 0, 0),
        feature_version="fv4_book_setup_context",
        label_version="lv20_h12_tts_thr065_sqmask060_trap",
        horizon_candles=12,
        features_json=features_json or {
            "schwager_bull_trap_risk_score": 0.0,
            "schwager_bear_trap_risk_score": 0.0,
            "schwager_trap_safe_setup_score": 1.0,
        },
        direction_label=direction_label,
        tp_before_sl=True if direction_label in {"UP", "DOWN"} else None,
        future_return=future_return,
        future_move_atr=future_move_atr,
        max_favorable_move_atr=1.2,
        max_adverse_move_atr=0.3,
        opportunity_label=opportunity_label,
        opportunity_direction=opportunity_direction,
        opportunity_reason="confirmed_setup_first_touch" if opportunity_label else "no_setup",
        opportunity_score=0.8 if opportunity_label else 0.0,
        setup_type="long_setup" if opportunity_direction == "UP" else "short_setup",
        setup_quality_score=setup_quality_score,
        setup_invalidation_distance_atr=0.4,
        setup_expected_move_atr=1.2,
        label_ambiguity_score=0.1,
    )

def test_rows_to_tensors_exposes_raw_feature_values_for_trap_audit() -> None:
    feature_columns = [
        "schwager_false_breakout_risk_score",
        "schwager_bull_trap_risk_score",
        "schwager_trap_safe_setup_score",
    ]
    rows = [
        _dataset_row(
            direction_label="UP",
            features_json={
                "schwager_false_breakout_risk_score": 0.4,
                "schwager_bull_trap_risk_score": 0.8,
                "schwager_trap_safe_setup_score": 0.2,
            },
            opportunity_label=1,
            opportunity_direction="UP",
            setup_quality_score=0.9,
        ),
        _dataset_row(
            direction_label="FLAT",
            features_json={
                "schwager_false_breakout_risk_score": 0.7,
                "schwager_bull_trap_risk_score": 0.1,
                "schwager_trap_safe_setup_score": 0.9,
            },
            opportunity_label=0,
            opportunity_direction="NONE",
            setup_quality_score=0.0,
            future_return=0.0,
            future_move_atr=0.0,
        ),
    ]

    tensors = TrainingService.rows_to_tensors(
        rows,
        feature_columns,
        {"mean": [0.0, 0.0, 0.0], "std": [1.0, 1.0, 1.0]},
        training_objective="trade_two_stage",
    )

    assert tuple(tensors["feature_columns"]) == tuple(feature_columns)
    assert tensors["raw_feature_values"].shape == (2, 3)

    raw_values = tensors["raw_feature_values"].tolist()
    assert raw_values[0] == pytest.approx([0.4, 0.8, 0.2])
    assert raw_values[1] == pytest.approx([0.7, 0.1, 0.9])

    assert tensors["opportunity_target"].tolist() == [1.0, 0.0]
    assert tensors["setup_quality_score"].tolist() == pytest.approx([0.9, 0.0])
