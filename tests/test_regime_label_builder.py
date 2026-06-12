import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.labels.label_config import LabelConfig
from app.labels.regime_label_builder import RegimeLabelBuilder


def _sample_candles() -> list[SimpleNamespace]:
    candles: list[SimpleNamespace] = []
    for index in range(40):
        candles.append(
            SimpleNamespace(
                open_time=datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=15 * index),
                open=100.0 + (index * 2.0),
                high=101.8 + (index * 2.0),
                low=99.2 + (index * 2.0),
                close=101.2 + (index * 2.0),
            )
        )
    return candles


def test_regime_label_builder_builds_status_and_distribution() -> None:
    candles = _sample_candles()
    feature_rows = [
        {
            "candle_open_time": candle.open_time,
            "features_json": {
                "regime_trend_up": 1.0 if index % 2 == 0 else 0.0,
                "regime_trend_down": 1.0 if index % 2 == 1 else 0.0,
                "regime_range": 0.0,
                "regime_high_volatility": 1.0 if index % 3 == 0 else 0.0,
                "regime_low_volatility": 1.0 if index % 3 != 0 else 0.0,
                "regime_unknown": 0.0,
            },
        }
        for index, candle in enumerate(candles)
    ]

    result = RegimeLabelBuilder().build(
        candles=candles,
        symbol="BTCUSDT",
        interval="15m",
        feature_rows=feature_rows,
        base_config=LabelConfig(
            label_version="lv2_h12_thr05_tp15_sl10",
            horizon_candles=12,
            direction_atr_threshold=0.5,
            take_profit_atr=1.5,
            stop_loss_atr=1.0,
            flat_class_enabled=True,
        ),
    )

    payload = result.to_dict()
    assert payload["regime_label_builder_available"] is True
    assert payload["regime_label_builder_used_in_training"] is True
    assert payload["regime_specific_training_applied"] is True
    assert payload["missing_requirements"] == []
    assert payload["label_distribution_by_regime"]
    json.dumps(payload, ensure_ascii=False, sort_keys=True)


def test_regime_label_builder_does_not_claim_applied_without_feature_rows() -> None:
    result = RegimeLabelBuilder().build(
        candles=_sample_candles(),
        symbol="ETHUSDT",
        interval="15m",
        feature_rows=[],
        base_config=LabelConfig(
            label_version="lv2_h12_thr05_tp15_sl10",
            horizon_candles=12,
            direction_atr_threshold=0.5,
            take_profit_atr=1.5,
            stop_loss_atr=1.0,
            flat_class_enabled=True,
        ),
    )

    payload = result.to_dict()
    assert payload["regime_label_builder_used_in_training"] is False
    assert payload["regime_specific_training_applied"] is False
    assert "regime_features_not_attached" in payload["missing_requirements"]
