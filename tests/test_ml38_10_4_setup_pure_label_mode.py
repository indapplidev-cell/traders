from __future__ import annotations

from types import SimpleNamespace

from app.labels.first_touch_label_builder import build_label_mode_snapshot
from app.labels.label_config import LABEL_MODE_SETUP_PURE_FIRST_TOUCH
from app.labels.label_models import LABEL_FLAT, LABEL_UP


def _candle(open_time: int, open_: float, high: float, low: float, close: float):
    return SimpleNamespace(
        open_time=open_time,
        open=open_,
        high=high,
        low=low,
        close=close,
    )


def test_setup_pure_first_touch_confirms_aligned_support_long() -> None:
    current = _candle(1, 100.0, 101.0, 99.0, 100.0)
    future = [_candle(2, 100.0, 101.20, 99.80, 101.0)]

    payload = build_label_mode_snapshot(
        current_candle=current,
        future_candles=future,
        atr_value=1.0,
        direction_atr_threshold=0.5,
        take_profit_atr=1.0,
        stop_loss_atr=1.0,
        flat_class_enabled=True,
        features_json={"near_support": True, "support_distance_atr": 0.10, "nison_bullish_engulfing": 0.90},
        label_mode=LABEL_MODE_SETUP_PURE_FIRST_TOUCH,
    )

    assert payload["selected_direction_label"] == LABEL_UP
    assert payload["setup_pure_first_touch_label"] == LABEL_UP
    assert payload["setup_purity_reason"] == "confirmed_setup_first_touch"


def test_setup_pure_first_touch_blocks_counter_setup_direction() -> None:
    current = _candle(1, 100.0, 101.0, 99.0, 100.0)
    future = [_candle(2, 100.0, 100.20, 98.80, 99.0)]

    payload = build_label_mode_snapshot(
        current_candle=current,
        future_candles=future,
        atr_value=1.0,
        direction_atr_threshold=0.5,
        take_profit_atr=1.0,
        stop_loss_atr=1.0,
        flat_class_enabled=True,
        features_json={"near_support": True, "support_distance_atr": 0.10, "nison_bullish_engulfing": 0.90},
        label_mode=LABEL_MODE_SETUP_PURE_FIRST_TOUCH,
    )

    assert payload["first_touch_tp_sl_label"] == "DOWN"
    assert payload["setup_direction"] == LABEL_UP
    assert payload["selected_direction_label"] == LABEL_FLAT
    assert payload["setup_purity_reason"] == "setup_direction_conflict"
