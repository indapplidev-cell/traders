from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.features.book_setup_context_features import (
    BOOK_SETUP_CONTEXT_FEATURE_NAMES,
    BookSetupContextFeatureBuilder,
)


def test_book_setup_context_builder_is_zero_safe_with_short_history() -> None:
    builder = BookSetupContextFeatureBuilder()
    candles = [_candle(0), _candle(1), _candle(2)]

    payload = builder.build(candles=candles, index=2, base_features={})

    assert set(payload) == set(BOOK_SETUP_CONTEXT_FEATURE_NAMES)
    assert all(value == 0.0 for value in payload.values())


def _candle(index: int) -> SimpleNamespace:
    open_time = datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=15 * index)
    open_price = 100.0 + index
    close_price = open_price + 0.5
    return SimpleNamespace(
        open_time=open_time,
        open=open_price,
        high=close_price + 0.8,
        low=open_price - 0.7,
        close=close_price,
        volume=1000.0 + index * 10.0,
    )
