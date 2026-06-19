from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.features.book_setup_context_features import BookSetupContextFeatureBuilder


def test_altunina_context_features_favor_long_trend_continuation_when_inputs_align() -> None:
    builder = BookSetupContextFeatureBuilder()
    candles = [_candle(index) for index in range(24)]
    base_features = {
        "atr_14": 2.5,
        "regime_trend_up": 1.0,
        "trend_strength": 0.09,
        "trend_slope_short": 0.8,
        "trend_slope_medium": 1.2,
        "trend_slope_long": 1.4,
        "ema_stack_bullish": 1.0,
        "volume_confirmation": 0.9,
        "volume_ratio_20": 1.5,
        "volume_zscore": 2.2,
        "rsi_value": 63.0,
        "macd_histogram": 0.12,
        "stochastic_k": 71.0,
        "roc": 1.8,
        "momentum": 2.0,
        "breakout_candidate": 0.85,
        "breakdown_candidate": 0.0,
        "false_breakout_candidate": 0.0,
        "false_breakdown_candidate": 0.0,
        "pullback_to_ema_21": 0.6,
        "near_support": 0.8,
        "near_resistance": 0.0,
        "bollinger_position": 0.82,
        "range_position": 0.78,
        "volatility_regime_score": 1.1,
    }

    payload = builder.build(candles=candles, index=len(candles) - 1, base_features=base_features)

    assert payload["alt_trend_continuation_long_score"] > 0.7
    assert payload["alt_trend_continuation_long_score"] > payload["alt_trend_continuation_short_score"]
    assert payload["alt_breakout_long_score"] > payload["alt_breakdown_short_score"]
    assert payload["alt_indicator_confluence_long_score"] > payload["alt_indicator_confluence_short_score"]
    assert payload["alt_volume_confirms_direction_score"] > 0.6


def _candle(index: int) -> SimpleNamespace:
    open_time = datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=15 * index)
    open_price = 100.0 + (index * 0.8)
    close_price = open_price + 0.6
    return SimpleNamespace(
        open_time=open_time,
        open=open_price,
        high=close_price + 0.7,
        low=open_price - 0.4,
        close=close_price,
        volume=1000.0 + index * 15.0,
    )
