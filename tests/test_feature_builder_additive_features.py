from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.features.feature_builder import FeatureBuilder


def test_fv2_additive_features_are_generated_without_future_leakage() -> None:
    builder = FeatureBuilder()
    base_candles = _build_candles(260)
    mutated_candles = _build_candles(260)
    mutated_candles[250] = _build_candle(
        open_time=mutated_candles[250].open_time,
        open_price=600.0,
        high_price=1600.0,
        low_price=100.0,
        close_price=1200.0,
        volume=99999.0,
    )

    base_features = builder.build(base_candles, symbol="BTCUSDT", interval="15m", feature_version="fv2")
    mutated_features = builder.build(mutated_candles, symbol="BTCUSDT", interval="15m", feature_version="fv2")
    feature_row = base_features[240].features_json

    for name in (
        "return_6",
        "range_pct",
        "body_pct",
        "upper_wick_pct",
        "lower_wick_pct",
        "volume_change_pct",
        "atr_normalized_move",
        "trend_slope_short",
        "trend_slope_medium",
        "regime_unknown",
    ):
        assert name in feature_row

    assert not any(token in name.lower() for token in ("future", "target", "label", "next") for name in feature_row)
    assert base_features[220].features_json == mutated_features[220].features_json


def _build_candles(count: int) -> list[SimpleNamespace]:
    candles: list[SimpleNamespace] = []
    start_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for index in range(count):
        open_price = 100.0 + (index * 0.5)
        close_price = open_price + (1.0 if index % 5 != 0 else -0.25)
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
