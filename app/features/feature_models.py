from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

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

FV2_REGIME_FEATURE_NAMES = FEATURE_NAMES + [
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

FEATURE_NAMES_BY_VERSION = {
    "fv1": FEATURE_NAMES,
    "fv2_regime": FV2_REGIME_FEATURE_NAMES,
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
