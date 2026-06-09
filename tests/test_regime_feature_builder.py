from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.features.feature_builder import FeatureBuilder
from app.features.feature_models import FEATURE_NAMES, FV2_REGIME_FEATURE_NAMES


def test_fv2_regime_feature_builder_adds_required_regime_columns() -> None:
    builder = FeatureBuilder()
    candles = _build_candles(260)

    records = builder.build(candles, symbol="BTCUSDT", interval="15m", feature_version="fv2_regime")

    feature_row = records[240].features_json

    assert set(feature_row) == set(FV2_REGIME_FEATURE_NAMES)
    assert len(feature_row) > len(FEATURE_NAMES)
    assert feature_row["ema_9_minus_ema_21"] is not None
    assert feature_row["ema_50_minus_ema_200"] is not None
    assert feature_row["ema_200_slope_10"] is not None
    assert feature_row["regime_trend_up"] in (0.0, 1.0)
    assert feature_row["rsi_14_above_50"] in (0.0, 1.0)
    assert feature_row["macd_histogram_slope_3"] is not None


def test_fv2_regime_feature_builder_does_not_use_future_candles() -> None:
    builder = FeatureBuilder()
    base_candles = _build_candles(260)
    mutated_candles = _build_candles(260)
    mutated_candles[250] = _build_candle(
        open_time=mutated_candles[250].open_time,
        open_price=500.0,
        high_price=1500.0,
        low_price=50.0,
        close_price=1200.0,
        volume=99999.0,
    )

    base_features = builder.build(base_candles, symbol="BTCUSDT", interval="15m", feature_version="fv2_regime")
    mutated_features = builder.build(mutated_candles, symbol="BTCUSDT", interval="15m", feature_version="fv2_regime")

    assert base_features[220].features_json == mutated_features[220].features_json


def _build_candles(count: int) -> list[SimpleNamespace]:
    candles: list[SimpleNamespace] = []
    start_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for index in range(count):
        open_price = 100.0 + (index * 0.5)
        close_price = open_price + (1.0 if index % 7 != 0 else -0.25)
        high_price = max(open_price, close_price) + 2.0
        low_price = min(open_price, close_price) - 1.5
        candles.append(
            _build_candle(
                open_time=start_at + timedelta(minutes=15 * index),
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=1000.0 + (index * 5.0),
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
        taker_buy_base_volume=volume * 0.58,
    )
