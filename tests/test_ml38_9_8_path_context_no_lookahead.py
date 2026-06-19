from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.features.feature_builder import FeatureBuilder


def test_fv4_path_context_features_do_not_change_when_future_candle_mutates() -> None:
    builder = FeatureBuilder()
    base_candles = _build_candles(260)
    mutated_candles = _build_candles(260)
    mutated_candles[250] = _build_candle(
        open_time=mutated_candles[250].open_time,
        open_price=1000.0,
        high_price=5000.0,
        low_price=100.0,
        close_price=4000.0,
        volume=99999.0,
    )

    base_features = builder.build(
        base_candles,
        symbol="BTCUSDT",
        interval="15m",
        feature_version="fv4_book_setup_context",
    )
    mutated_features = builder.build(
        mutated_candles,
        symbol="BTCUSDT",
        interval="15m",
        feature_version="fv4_book_setup_context",
    )

    assert base_features[220].features_json == mutated_features[220].features_json


def _build_candles(count: int) -> list[SimpleNamespace]:
    candles: list[SimpleNamespace] = []
    start_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for index in range(count):
        open_price = 100.0 + (index * 0.4)
        close_price = open_price + (0.9 if index % 6 != 0 else -0.2)
        high_price = max(open_price, close_price) + 1.2
        low_price = min(open_price, close_price) - 0.9
        candles.append(
            _build_candle(
                open_time=start_at + timedelta(minutes=15 * index),
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=1000.0 + (index * 6.0),
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
        taker_buy_base_volume=volume * 0.58,
    )
