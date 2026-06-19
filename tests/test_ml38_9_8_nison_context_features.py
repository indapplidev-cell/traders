from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.features.book_setup_context_features import BookSetupContextFeatureBuilder


def test_nison_context_features_reward_hammer_after_decline_at_support() -> None:
    builder = BookSetupContextFeatureBuilder()
    candles = [_candle(index) for index in range(20)]
    base_features = {
        "atr_14": 2.0,
        "regime_trend_down": 1.0,
        "trend_strength": -0.08,
        "trend_slope_short": -0.6,
        "trend_slope_medium": -1.1,
        "hammer_score": 0.95,
        "bullish_engulfing_score": 0.4,
        "doji_score": 0.1,
        "pattern_context_valid": 1.0,
        "pattern_requires_confirmation": 0.8,
        "pattern_direction_hint": 1.0,
        "near_support": 1.0,
        "distance_to_support": 0.15,
        "volume_confirmation": 0.9,
        "window_gap_up": 0.0,
        "window_gap_down": 0.0,
        "impulse_strength": 1.4,
    }

    payload = builder.build(candles=candles, index=len(candles) - 1, base_features=base_features)

    assert payload["nison_hammer_after_decline_score"] > 0.9
    assert payload["nison_pattern_at_support_score"] > 0.7
    assert payload["nison_reversal_context_score"] > payload["nison_continuation_context_score"]
    assert payload["nison_confirmation_required_score"] == 0.8


def _candle(index: int) -> SimpleNamespace:
    open_time = datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=15 * index)
    close_price = 120.0 - (index * 0.6)
    open_price = close_price + 0.4
    return SimpleNamespace(
        open_time=open_time,
        open=open_price,
        high=open_price + 0.8,
        low=close_price - 1.2,
        close=close_price,
        volume=900.0 + index * 8.0,
    )
