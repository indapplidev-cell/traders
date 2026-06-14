from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.features.feature_builder import FeatureBuilder


def test_ml38_pattern_scores_capture_doji_hammer_shooting_star_and_engulfing() -> None:
    candles = _build_pattern_candles()
    records = FeatureBuilder().build(candles, symbol="BTCUSDT", interval="15m", feature_version="fv3_candle_ta_context")

    doji_features = records[30].features_json
    hammer_features = records[40].features_json
    shooting_star_features = records[50].features_json
    engulfing_features = records[61].features_json

    assert doji_features["doji_score"] > 0.70
    assert doji_features["gravestone_doji_score"] > doji_features["dragonfly_doji_score"]
    assert hammer_features["hammer_score"] > 0.45
    assert hammer_features["hammer_score"] > hammer_features["shooting_star_score"]
    assert shooting_star_features["shooting_star_score"] > 0.35
    assert shooting_star_features["shooting_star_score"] > shooting_star_features["hammer_score"]
    assert engulfing_features["bullish_engulfing_score"] > 0.55
    assert engulfing_features["bearish_engulfing_score"] == 0.0
    assert engulfing_features["pattern_strength_score"] >= engulfing_features["bullish_engulfing_score"]


def _build_pattern_candles() -> list[SimpleNamespace]:
    candles: list[SimpleNamespace] = []
    start_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    price = 120.0
    for index in range(80):
        open_price = price
        close_price = open_price - 0.35 if index < 45 else open_price + 0.20
        high_price = max(open_price, close_price) + 0.7
        low_price = min(open_price, close_price) - 0.7

        if index == 30:
            open_price = 108.0
            close_price = 108.02
            high_price = 110.4
            low_price = 107.7
        elif index == 40:
            open_price = 101.0
            close_price = 101.3
            high_price = 101.5
            low_price = 97.3
        elif index == 50:
            open_price = 112.0
            close_price = 111.7
            high_price = 116.1
            low_price = 111.4
        elif index == 60:
            open_price = 109.0
            close_price = 107.8
            high_price = 109.3
            low_price = 107.5
        elif index == 61:
            open_price = 107.5
            close_price = 109.7
            high_price = 110.0
            low_price = 107.2

        candles.append(
            _build_candle(
                open_time=start_at + timedelta(minutes=15 * index),
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=1200.0 + (index * 4.0),
            )
        )
        price = close_price
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
        taker_buy_base_volume=volume * 0.57,
    )
