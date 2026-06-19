from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.labels.first_touch_label_builder import FirstTouchDirectionLabelBuilder
from app.labels.label_models import LABEL_DOWN, LABEL_FLAT, LABEL_UP


def test_first_touch_label_builder_returns_up_when_tp_hits_before_sl() -> None:
    payload = FirstTouchDirectionLabelBuilder().build_label(
        current_candle=_candle(0, 100.0, 101.0, 99.0, 100.0),
        future_candles=[
            _candle(1, 100.0, 101.2, 99.4, 100.5),
            _candle(2, 100.5, 101.4, 99.6, 101.0),
        ],
        config={"atr_value": 1.0, "take_profit_atr": 1.0, "stop_loss_atr": 1.0},
    )

    assert payload["first_touch_direction"] == LABEL_UP
    assert payload["first_touch_tp_hit"] is True
    assert payload["first_touch_ambiguous"] is False


def test_first_touch_label_builder_returns_down_when_sl_hits_before_tp() -> None:
    payload = FirstTouchDirectionLabelBuilder().build_label(
        current_candle=_candle(0, 100.0, 101.0, 99.0, 100.0),
        future_candles=[
            _candle(1, 100.0, 100.2, 98.8, 99.0),
            _candle(2, 99.0, 99.4, 98.5, 98.7),
        ],
        config={"atr_value": 1.0, "take_profit_atr": 1.0, "stop_loss_atr": 1.0},
    )

    assert payload["first_touch_direction"] == LABEL_DOWN
    assert payload["first_touch_tp_hit"] is True
    assert payload["first_touch_ambiguous"] is False


def test_first_touch_label_builder_returns_flat_when_neither_side_touches() -> None:
    payload = FirstTouchDirectionLabelBuilder().build_label(
        current_candle=_candle(0, 100.0, 101.0, 99.0, 100.0),
        future_candles=[
            _candle(1, 100.0, 100.4, 99.7, 100.1),
            _candle(2, 100.1, 100.3, 99.8, 100.0),
        ],
        config={"atr_value": 1.0, "take_profit_atr": 1.0, "stop_loss_atr": 1.0},
    )

    assert payload["first_touch_direction"] == LABEL_FLAT
    assert payload["first_touch_outcome"] == "NO_TRADE"


def test_first_touch_label_builder_returns_ambiguous_for_same_candle_bidirectional_touch() -> None:
    payload = FirstTouchDirectionLabelBuilder().build_label(
        current_candle=_candle(0, 100.0, 101.0, 99.0, 100.0),
        future_candles=[
            _candle(1, 100.0, 101.2, 98.8, 100.0),
        ],
        config={"atr_value": 1.0, "take_profit_atr": 1.0, "stop_loss_atr": 1.0},
    )

    assert payload["first_touch_direction"] == "AMBIGUOUS"
    assert payload["first_touch_ambiguous"] is True


def _candle(index: int, open_price: float, high_price: float, low_price: float, close_price: float) -> SimpleNamespace:
    start_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return SimpleNamespace(
        open_time=start_at + timedelta(minutes=index * 15),
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume=100.0,
        taker_buy_base_volume=50.0,
    )
