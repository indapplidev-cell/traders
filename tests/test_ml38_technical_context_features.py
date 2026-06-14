from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.features.feature_builder import FeatureBuilder


def test_ml38_technical_context_features_cover_trend_range_and_indicators() -> None:
    builder = FeatureBuilder()

    uptrend = builder.build(_build_trend_candles(direction=1.0), symbol="BTCUSDT", interval="15m", feature_version="fv3_candle_ta_context")[-1].features_json
    downtrend = builder.build(_build_trend_candles(direction=-1.0), symbol="ETHUSDT", interval="15m", feature_version="fv3_candle_ta_context")[-1].features_json
    ranged = builder.build(_build_range_candles(), symbol="SOLUSDT", interval="15m", feature_version="fv3_candle_ta_context")[-1].features_json

    assert uptrend["trend_slope_short"] > 0
    assert uptrend["trend_slope_medium"] > 0
    assert uptrend["trend_slope_long"] > 0
    assert uptrend["higher_highs_score"] >= uptrend["lower_highs_score"]
    assert uptrend["rsi_value"] is not None
    assert uptrend["bollinger_position"] is not None
    assert uptrend["macd_line"] is not None
    assert uptrend["stochastic_k"] is not None
    assert uptrend["volume_zscore"] is not None

    assert downtrend["trend_slope_short"] < 0
    assert downtrend["trend_slope_medium"] < 0
    assert downtrend["trend_slope_long"] < 0
    assert downtrend["lower_lows_score"] >= downtrend["higher_lows_score"]

    assert ranged["distance_to_support"] is not None
    assert ranged["distance_to_resistance"] is not None
    assert ranged["support_resistance_width_atr"] is not None
    assert ranged["near_support"] is not None
    assert ranged["near_resistance"] is not None


def _build_trend_candles(*, direction: float, count: int = 180) -> list[SimpleNamespace]:
    candles: list[SimpleNamespace] = []
    start_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    price = 100.0 if direction > 0 else 200.0
    for index in range(count):
        open_price = price
        close_price = open_price + (0.8 * direction)
        high_price = max(open_price, close_price) + 0.6
        low_price = min(open_price, close_price) - 0.6
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
        price = close_price + (0.15 * direction)
    return candles


def _build_range_candles(count: int = 180) -> list[SimpleNamespace]:
    candles: list[SimpleNamespace] = []
    start_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for index in range(count):
        base = 100.0 + (((index % 12) - 6) * 0.35)
        open_price = base
        close_price = base + (0.25 if index % 2 == 0 else -0.25)
        high_price = max(open_price, close_price) + 0.7
        low_price = min(open_price, close_price) - 0.7
        candles.append(
            _build_candle(
                open_time=start_at + timedelta(minutes=15 * index),
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=900.0 + ((index % 10) * 15.0),
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
        taker_buy_base_volume=volume * 0.52,
    )
