from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.meta_label.ema_meta_label_builder import EmaMetaLabelBuilder


def test_ema_meta_label_builder_creates_win_loss_no_trade_and_ambiguous() -> None:
    builder = EmaMetaLabelBuilder()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = [
        _candle(start + timedelta(minutes=15 * index), close=100.0 + index, high=100.0 + index, low=100.0 + index)
        for index in range(6)
    ]
    candles[1].high = 102.0
    candles[1].low = 99.2
    candles[2].high = 101.0
    candles[2].low = 98.5
    candles[3].high = 102.0
    candles[3].low = 98.0
    candles[4].high = 105.0
    candles[4].low = 101.0

    feature_rows = [
        _feature_row(candles[0].open_time, ema_9=100.01, ema_21=100.0, atr_14=1.0),
        _feature_row(candles[1].open_time, ema_9=102.0, ema_21=100.0, atr_14=1.0),
        _feature_row(candles[2].open_time, ema_9=98.0, ema_21=100.0, atr_14=1.0),
        _feature_row(candles[3].open_time, ema_9=102.0, ema_21=100.0, atr_14=1.0),
    ]

    records = builder.build(
        feature_rows=feature_rows,
        candles=candles,
        symbol="BTCUSDT",
        interval="15m",
        feature_version="fv2_regime",
        label_version="meta_ema_9_21_tp15_sl10",
        horizon_candles=1,
        take_profit_atr=1.5,
        stop_loss_atr=1.0,
        fee_r=0.02,
        slippage_r=0.01,
        same_candle_policy="skip",
    )

    assert records[0].meta_label == "NO_TRADE"
    assert records[1].meta_label == "LOSS"
    assert records[2].meta_label == "WIN"
    assert records[3].meta_label == "AMBIGUOUS"
    assert records[3].meta_same_candle_ambiguous is True


def _candle(open_time, close: float, high: float, low: float):
    return SimpleNamespace(open_time=open_time, close=close, high=high, low=low)


def _feature_row(open_time, ema_9: float, ema_21: float, atr_14: float):
    return SimpleNamespace(
        candle_open_time=open_time,
        features_json={"ema_9": ema_9, "ema_21": ema_21, "atr_14": atr_14},
    )
