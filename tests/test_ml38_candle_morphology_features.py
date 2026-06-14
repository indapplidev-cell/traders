from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.features.feature_builder import FeatureBuilder


def test_ml38_candle_morphology_features_capture_hammer_shape() -> None:
    candles = _build_base_candles(80)
    candles[40] = _build_candle(
        open_time=candles[40].open_time,
        open_price=100.0,
        high_price=102.0,
        low_price=90.0,
        close_price=101.0,
        volume=1800.0,
    )

    record = FeatureBuilder().build(candles, symbol="BTCUSDT", interval="15m", feature_version="fv3_candle_ta_context")[40]
    features = record.features_json

    assert features["body_abs"] == 1.0
    assert features["upper_shadow_abs"] == 1.0
    assert features["lower_shadow_abs"] == 10.0
    assert features["is_bullish_candle"] == 1.0
    assert features["is_bearish_candle"] == 0.0
    assert features["is_neutral_candle"] == 0.0
    assert features["close_position_in_range"] > 0.85
    assert features["body_to_range_ratio"] < 0.10
    assert features["range_to_atr_ratio"] is not None
    assert features["body_to_atr_ratio"] is not None
    assert features["hammer_score"] > features["shooting_star_score"]


def test_ml38_candle_morphology_features_mark_neutral_candle() -> None:
    candles = _build_base_candles(40)
    candles[20] = _build_candle(
        open_time=candles[20].open_time,
        open_price=100.0,
        high_price=101.0,
        low_price=99.0,
        close_price=100.0,
        volume=1200.0,
    )

    record = FeatureBuilder().build(candles, symbol="BTCUSDT", interval="15m", feature_version="fv3_candle_ta_context")[20]
    features = record.features_json

    assert features["candle_direction"] == 0.0
    assert features["is_neutral_candle"] == 1.0
    assert features["is_bullish_candle"] == 0.0
    assert features["is_bearish_candle"] == 0.0


def _build_base_candles(count: int) -> list[SimpleNamespace]:
    candles: list[SimpleNamespace] = []
    start_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for index in range(count):
        open_price = 100.0 + (index * 0.25)
        close_price = open_price + 0.4
        candles.append(
            _build_candle(
                open_time=start_at + timedelta(minutes=15 * index),
                open_price=open_price,
                high_price=close_price + 0.8,
                low_price=open_price - 0.6,
                close_price=close_price,
                volume=1000.0 + (index * 3.0),
            )
        )
    return candles


def _build_candle(
    *,
    open_time: datetime,
    open_price: float,
    high_price: float,
    low_price: float,
    close_price: float,
    volume: float,
) -> SimpleNamespace:
    return SimpleNamespace(
        open_time=open_time,
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume=volume,
        taker_buy_base_volume=volume * 0.55,
    )
