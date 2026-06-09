from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.features.feature_builder import FeatureBuilder


def test_feature_builder_does_not_use_future_candles() -> None:
    builder = FeatureBuilder()
    base_candles = _build_candles(220)
    mutated_candles = _build_candles(220)
    mutated_candles[210] = _build_candle(
        open_time=mutated_candles[210].open_time,
        open_price=1000.0,
        high_price=5000.0,
        low_price=100.0,
        close_price=4000.0,
        volume=9999.0,
    )

    base_features = builder.build(base_candles, symbol="BTCUSDT", interval="15m", feature_version="fv1")
    mutated_features = builder.build(mutated_candles, symbol="BTCUSDT", interval="15m", feature_version="fv1")

    assert base_features[150].features_json == mutated_features[150].features_json
    assert base_features[180].features_json == mutated_features[180].features_json


def _build_candles(count: int) -> list[SimpleNamespace]:
    candles: list[SimpleNamespace] = []
    start_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for index in range(count):
        open_price = 100.0 + index
        candles.append(
            _build_candle(
                open_time=start_at + timedelta(minutes=15 * index),
                open_price=open_price,
                high_price=open_price + 3.0,
                low_price=open_price - 2.0,
                close_price=open_price + 1.0,
                volume=1000.0 + index,
            )
        )
    return candles


def _build_candle(
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
