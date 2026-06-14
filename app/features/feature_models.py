from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


def _unique_names(*groups: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for name in group:
            if name in seen:
                continue
            seen.add(name)
            ordered.append(name)
    return ordered


FEATURE_NAMES = [
    "body_size",
    "upper_wick",
    "lower_wick",
    "candle_range",
    "body_to_range_ratio",
    "close_position_in_range",
    "return_1",
    "return_3",
    "return_5",
    "return_10",
    "log_return_1",
    "atr_14",
    "atr_28",
    "range_percent",
    "rolling_volatility_20",
    "rolling_volatility_50",
    "ema_9",
    "ema_21",
    "ema_50",
    "ema_200",
    "close_to_ema_9",
    "close_to_ema_21",
    "close_to_ema_50",
    "ema_9_to_ema_21",
    "ema_21_to_ema_50",
    "trend_strength",
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_histogram",
    "volume_sma_20",
    "volume_ratio_20",
    "volume_spike",
    "taker_buy_ratio",
]

FV2_ADDITIVE_FEATURE_NAMES = [
    "return_6",
    "range_pct",
    "body_pct",
    "upper_wick_pct",
    "lower_wick_pct",
    "volume_change_pct",
    "atr_normalized_move",
    "trend_slope_short",
    "trend_slope_medium",
]

FV2_REGIME_FEATURE_NAMES = FEATURE_NAMES + FV2_ADDITIVE_FEATURE_NAMES + [
    "ema_9_minus_ema_21",
    "ema_9_minus_ema_50",
    "ema_21_minus_ema_50",
    "ema_50_minus_ema_200",
    "ema_9_above_ema_21",
    "ema_21_above_ema_50",
    "ema_50_above_ema_200",
    "ema_stack_bullish",
    "ema_stack_bearish",
    "close_above_ema_21",
    "close_above_ema_50",
    "close_above_ema_200",
    "close_minus_ema_21_atr",
    "close_minus_ema_50_atr",
    "close_minus_ema_200_atr",
    "ema_9_slope_3",
    "ema_21_slope_3",
    "ema_50_slope_3",
    "ema_200_slope_3",
    "ema_9_slope_10",
    "ema_21_slope_10",
    "ema_50_slope_10",
    "ema_200_slope_10",
    "close_slope_3",
    "close_slope_10",
    "regime_trend_up",
    "regime_trend_down",
    "regime_range",
    "regime_high_volatility",
    "regime_low_volatility",
    "regime_unknown",
    "regime_volatility_expanding",
    "regime_volatility_contracting",
    "rsi_14_above_50",
    "rsi_14_below_50",
    "rsi_14_overbought",
    "rsi_14_oversold",
    "macd_above_signal",
    "macd_below_signal",
    "macd_histogram_slope_3",
    "pullback_to_ema_21",
    "pullback_to_ema_50",
    "bearish_pullback_to_ema_21",
    "bearish_pullback_to_ema_50",
]

FV2_FEATURE_NAMES = FV2_REGIME_FEATURE_NAMES

CANDLE_MORPHOLOGY_FEATURE_NAMES = [
    "candle_range",
    "body_abs",
    "body_pct",
    "body_to_range_ratio",
    "upper_shadow_abs",
    "lower_shadow_abs",
    "upper_shadow_pct",
    "lower_shadow_pct",
    "upper_to_lower_shadow_ratio",
    "shadow_imbalance",
    "close_position_in_range",
    "open_position_in_range",
    "candle_direction",
    "is_bullish_candle",
    "is_bearish_candle",
    "is_neutral_candle",
    "range_to_atr_ratio",
    "body_to_atr_ratio",
]

CANDLE_PATTERN_FEATURE_NAMES = [
    "doji_score",
    "long_legged_doji_score",
    "gravestone_doji_score",
    "dragonfly_doji_score",
    "hammer_score",
    "inverted_hammer_score",
    "shooting_star_score",
    "hanging_man_score",
    "bullish_engulfing_score",
    "bearish_engulfing_score",
    "harami_score",
    "morning_star_score",
    "evening_star_score",
    "three_white_soldiers_score",
    "three_black_crows_score",
    "window_gap_up",
    "window_gap_down",
    "gap_size_atr",
    "pattern_strength_score",
    "pattern_direction_hint",
    "pattern_requires_confirmation",
    "pattern_context_valid",
]

TECHNICAL_CONTEXT_FEATURE_NAMES = [
    "trend_slope_short",
    "trend_slope_medium",
    "trend_slope_long",
    "trend_strength_short",
    "trend_strength_medium",
    "trend_strength_long",
    "trend_age",
    "higher_highs_score",
    "higher_lows_score",
    "lower_highs_score",
    "lower_lows_score",
    "impulse_strength",
    "correction_depth",
    "correction_duration",
    "range_position",
    "volatility_regime_score",
    "recent_high_distance",
    "recent_low_distance",
    "distance_to_support",
    "distance_to_resistance",
    "support_touch_count",
    "resistance_touch_count",
    "support_resistance_width_atr",
    "near_support",
    "near_resistance",
    "breakout_candidate",
    "breakdown_candidate",
    "false_breakout_candidate",
    "false_breakdown_candidate",
    "sma_fast_distance",
    "sma_slow_distance",
    "ema_fast_distance",
    "ema_slow_distance",
    "sma_fast_slow_spread",
    "ema_fast_slow_spread",
    "bollinger_position",
    "bollinger_bandwidth",
    "bollinger_squeeze_score",
    "rsi_value",
    "rsi_zone",
    "macd_line",
    "macd_signal",
    "macd_histogram",
    "macd_histogram_slope",
    "stochastic_k",
    "stochastic_d",
    "stochastic_cross_hint",
    "roc",
    "momentum",
    "volume_zscore",
    "volume_spike",
    "volume_confirmation",
]

FV3_CANDLE_TA_CONTEXT_FEATURE_NAMES = _unique_names(
    FV2_REGIME_FEATURE_NAMES,
    CANDLE_MORPHOLOGY_FEATURE_NAMES,
    CANDLE_PATTERN_FEATURE_NAMES,
    TECHNICAL_CONTEXT_FEATURE_NAMES,
)

FEATURE_NAMES_BY_VERSION = {
    "fv1": FEATURE_NAMES,
    "fv2": FV2_FEATURE_NAMES,
    "fv2_regime": FV2_REGIME_FEATURE_NAMES,
    "fv3_candle_ta_context": FV3_CANDLE_TA_CONTEXT_FEATURE_NAMES,
}


def feature_names_for_version(feature_version: str) -> list[str]:
    try:
        return list(FEATURE_NAMES_BY_VERSION[feature_version])
    except KeyError as exc:
        raise ValueError(f"Unsupported feature_version: {feature_version}") from exc


@dataclass(slots=True)
class FeatureRecord:
    symbol: str
    interval: str
    candle_open_time: datetime
    feature_version: str
    features_json: dict[str, float | None]
    features_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "candle_open_time": self.candle_open_time,
            "feature_version": self.feature_version,
            "features_json": self.features_json,
            "features_hash": self.features_hash,
        }
