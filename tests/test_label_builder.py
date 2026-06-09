from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.labels.label_builder import LabelBuilder
from app.labels.label_models import LABEL_DOWN, LABEL_FLAT, LABEL_UP


def test_label_builder_uses_only_future_window_after_current_candle() -> None:
    builder = LabelBuilder()
    candles = _build_flat_candles(30)
    changed = _build_flat_candles(30)
    changed[20] = _build_candle(changed[20].open_time, 500.0, 520.0, 490.0, 510.0)

    original_labels = builder.build(candles, "BTCUSDT", "15m", 3, "lv1")
    changed_labels = builder.build(changed, "BTCUSDT", "15m", 3, "lv1")

    target_original = next(item for item in original_labels if item.candle_open_time == candles[14].open_time)
    target_changed = next(item for item in changed_labels if item.candle_open_time == changed[14].open_time)

    assert target_original.direction_label == target_changed.direction_label
    assert target_original.future_return == target_changed.future_return
    assert target_original.tp_before_sl == target_changed.tp_before_sl


def test_label_builder_builds_direction_and_tp_before_sl_correctly() -> None:
    builder = LabelBuilder()
    candles = _build_directional_candles()

    labels = builder.build(candles, "BTCUSDT", "15m", 2, "lv1")
    label_by_open_time = {label.candle_open_time: label for label in labels}

    up_label = label_by_open_time[candles[13].open_time]
    flat_label = label_by_open_time[candles[15].open_time]
    down_label = label_by_open_time[candles[17].open_time]

    assert up_label.direction_label == LABEL_UP
    assert up_label.tp_before_sl is True
    assert flat_label.direction_label == LABEL_FLAT
    assert flat_label.tp_before_sl is None
    assert down_label.direction_label == LABEL_DOWN
    assert down_label.tp_before_sl is True


def _build_flat_candles(count: int) -> list[SimpleNamespace]:
    start_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    candles: list[SimpleNamespace] = []
    for index in range(count):
        candles.append(_build_candle(start_at + timedelta(minutes=15 * index), 100.0, 101.0, 99.0, 100.0))
    return candles


def _build_directional_candles() -> list[SimpleNamespace]:
    candles = _build_flat_candles(20)
    candles[14] = _build_candle(candles[14].open_time, 100.0, 101.0, 99.0, 100.0)
    candles[15] = _build_candle(candles[15].open_time, 100.0, 103.2, 99.2, 103.0)
    candles[16] = _build_candle(candles[16].open_time, 103.0, 104.0, 102.5, 103.5)
    candles[17] = _build_candle(candles[17].open_time, 103.5, 104.0, 103.0, 103.5)
    candles[18] = _build_candle(candles[18].open_time, 103.5, 103.8, 100.0, 100.4)
    candles[19] = _build_candle(candles[19].open_time, 100.4, 100.9, 100.1, 100.3)
    return candles


def _build_candle(open_time: datetime, open_price: float, high_price: float, low_price: float, close_price: float) -> SimpleNamespace:
    return SimpleNamespace(
        open_time=open_time,
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume=100.0,
        taker_buy_base_volume=55.0,
    )
