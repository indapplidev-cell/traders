from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.labels.label_builder import LabelBuilder
from app.labels.label_config import (
    LABEL_MODE_SETUP_PURE_FIRST_TOUCH,
    LabelConfig,
    normalize_label_mode,
)
from app.labels.label_models import LABEL_DOWN, LABEL_FLAT, LABEL_UP


def test_label_config_changes_direction_threshold_and_flat_behavior() -> None:
    builder = LabelBuilder()
    candles = _build_candles()

    default_labels = builder.build(
        candles=candles,
        symbol="BTCUSDT",
        interval="15m",
        horizon_candles=2,
        label_version="lv1",
    )
    configured_labels = builder.build(
        candles=candles,
        symbol="BTCUSDT",
        interval="15m",
        horizon_candles=2,
        label_version="lv_custom",
        config=LabelConfig(
            label_version="lv_custom",
            horizon_candles=2,
            direction_atr_threshold=2.0,
            take_profit_atr=1.5,
            stop_loss_atr=1.0,
            flat_class_enabled=False,
        ),
    )

    default_by_time = {label.candle_open_time: label for label in default_labels}
    configured_by_time = {label.candle_open_time: label for label in configured_labels}
    target_time = candles[14].open_time

    assert default_by_time[target_time].direction_label == LABEL_FLAT
    assert configured_by_time[target_time].direction_label in {LABEL_UP, LABEL_DOWN}
    assert LABEL_FLAT not in {label.direction_label for label in configured_labels}


def test_label_config_supports_setup_pure_first_touch_mode() -> None:
    assert normalize_label_mode(LABEL_MODE_SETUP_PURE_FIRST_TOUCH) == LABEL_MODE_SETUP_PURE_FIRST_TOUCH


def _build_candles() -> list[SimpleNamespace]:
    candles = []
    start_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for index in range(20):
        close_price = 100.0 if index < 14 else 100.0 + (index - 13) * 0.3
        candles.append(
            SimpleNamespace(
                open_time=start_at + timedelta(minutes=15 * index),
                open=100.0,
                high=close_price + 1.0,
                low=99.0,
                close=close_price,
                volume=100.0,
                taker_buy_base_volume=50.0,
            )
        )
    return candles
