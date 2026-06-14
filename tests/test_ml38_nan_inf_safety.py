import math
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.features.feature_builder import FeatureBuilder


def test_ml38_fv3_features_never_emit_nan_or_inf() -> None:
    records = FeatureBuilder().build(
        _build_flat_candles(120),
        symbol="BTCUSDT",
        interval="15m",
        feature_version="fv3_candle_ta_context",
    )

    for record in records:
        for value in record.features_json.values():
            if value is None:
                continue
            assert not math.isnan(float(value))
            assert not math.isinf(float(value))


def _build_flat_candles(count: int) -> list[SimpleNamespace]:
    candles: list[SimpleNamespace] = []
    start_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for index in range(count):
        price = 100.0 if index % 9 else 100.2
        candles.append(
            SimpleNamespace(
                open_time=start_at + timedelta(minutes=15 * index),
                open=price,
                high=price,
                low=price,
                close=price,
                volume=0.0 if index % 7 == 0 else 1000.0,
                taker_buy_base_volume=None,
            )
        )
    return candles
