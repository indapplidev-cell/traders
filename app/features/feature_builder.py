from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from app.features.feature_models import FEATURE_NAMES, FeatureRecord, feature_names_for_version
from app.features.technical_indicators import TechnicalIndicators


class FeatureBuilder:
    def build(
        self,
        candles: list[Any],
        symbol: str,
        interval: str,
        feature_version: str,
    ) -> list[FeatureRecord]:
        if not candles:
            return []

        opens = [self._to_float(candle.open) for candle in candles]
        highs = [self._to_float(candle.high) for candle in candles]
        lows = [self._to_float(candle.low) for candle in candles]
        closes = [self._to_float(candle.close) for candle in candles]
        volumes = [self._to_float(candle.volume) for candle in candles]
        taker_buy_volumes = [self._to_optional_float(getattr(candle, "taker_buy_base_volume", None)) for candle in candles]

        atr_14 = TechnicalIndicators.atr(highs, lows, closes, 14)
        atr_28 = TechnicalIndicators.atr(highs, lows, closes, 28)
        ema_9 = TechnicalIndicators.ema(closes, 9)
        ema_21 = TechnicalIndicators.ema(closes, 21)
        ema_50 = TechnicalIndicators.ema(closes, 50)
        ema_200 = TechnicalIndicators.ema(closes, 200)
        rsi_14 = TechnicalIndicators.rsi(closes, 14)
        macd, macd_signal, macd_histogram = TechnicalIndicators.macd(closes)
        volume_sma_20 = TechnicalIndicators.sma(volumes, 20)
        target_feature_names = feature_names_for_version(feature_version)

        ema_9_slope_3 = self._normalized_slope_series(ema_9, atr_14, 3)
        ema_21_slope_3 = self._normalized_slope_series(ema_21, atr_14, 3)
        ema_50_slope_3 = self._normalized_slope_series(ema_50, atr_14, 3)
        ema_200_slope_3 = self._normalized_slope_series(ema_200, atr_14, 3)
        ema_9_slope_10 = self._normalized_slope_series(ema_9, atr_14, 10)
        ema_21_slope_10 = self._normalized_slope_series(ema_21, atr_14, 10)
        ema_50_slope_10 = self._normalized_slope_series(ema_50, atr_14, 10)
        ema_200_slope_10 = self._normalized_slope_series(ema_200, atr_14, 10)
        close_slope_3 = self._normalized_slope_series(closes, atr_14, 3)
        close_slope_10 = self._normalized_slope_series(closes, atr_14, 10)
        macd_histogram_slope_3 = self._normalized_slope_series(macd_histogram, atr_14, 3)

        simple_returns = [None] * len(closes)
        log_returns = [None] * len(closes)
        for index in range(1, len(closes)):
            previous_close = closes[index - 1]
            if previous_close == 0:
                continue
            simple_returns[index] = (closes[index] / previous_close) - 1
            log_returns[index] = math.log(closes[index] / previous_close)

        rolling_volatility_20 = TechnicalIndicators.rolling_stddev(simple_returns, 20)
        rolling_volatility_50 = TechnicalIndicators.rolling_stddev(simple_returns, 50)

        records: list[FeatureRecord] = []
        for index, candle in enumerate(candles):
            candle_range = highs[index] - lows[index]
            body_size = abs(closes[index] - opens[index])
            upper_wick = highs[index] - max(opens[index], closes[index])
            lower_wick = min(opens[index], closes[index]) - lows[index]

            feature_values = {
                "body_size": body_size,
                "upper_wick": upper_wick,
                "lower_wick": lower_wick,
                "candle_range": candle_range,
                "body_to_range_ratio": self._safe_divide(body_size, candle_range),
                "close_position_in_range": self._safe_divide(closes[index] - lows[index], candle_range),
                "return_1": self._lookback_return(closes, index, 1),
                "return_3": self._lookback_return(closes, index, 3),
                "return_5": self._lookback_return(closes, index, 5),
                "return_6": self._lookback_return(closes, index, 6),
                "return_10": self._lookback_return(closes, index, 10),
                "log_return_1": log_returns[index],
                "atr_14": atr_14[index],
                "atr_28": atr_28[index],
                "range_percent": self._safe_divide(candle_range, closes[index]),
                "range_pct": self._safe_divide(candle_range, closes[index]),
                "body_pct": self._safe_divide(body_size, closes[index]),
                "upper_wick_pct": self._safe_divide(upper_wick, closes[index]),
                "lower_wick_pct": self._safe_divide(lower_wick, closes[index]),
                "rolling_volatility_20": rolling_volatility_20[index],
                "rolling_volatility_50": rolling_volatility_50[index],
                "ema_9": ema_9[index],
                "ema_21": ema_21[index],
                "ema_50": ema_50[index],
                "ema_200": ema_200[index],
                "close_to_ema_9": self._relative_to_value(closes[index], ema_9[index]),
                "close_to_ema_21": self._relative_to_value(closes[index], ema_21[index]),
                "close_to_ema_50": self._relative_to_value(closes[index], ema_50[index]),
                "ema_9_to_ema_21": self._ratio_delta(ema_9[index], ema_21[index]),
                "ema_21_to_ema_50": self._ratio_delta(ema_21[index], ema_50[index]),
                "trend_strength": self._relative_delta(ema_9[index], ema_50[index], closes[index]),
                "rsi_14": rsi_14[index],
                "macd": macd[index],
                "macd_signal": macd_signal[index],
                "macd_histogram": macd_histogram[index],
                "volume_sma_20": volume_sma_20[index],
                "volume_ratio_20": self._safe_divide(volumes[index], volume_sma_20[index]),
                "volume_spike": self._volume_spike(volumes[index], volume_sma_20[index]),
                "volume_change_pct": self._volume_change(volumes, index),
                "atr_normalized_move": self._atr_normalized_move(opens[index], closes[index], atr_14[index]),
                "taker_buy_ratio": self._safe_divide(taker_buy_volumes[index], volumes[index]),
                "trend_slope_short": close_slope_3[index],
                "trend_slope_medium": close_slope_10[index],
            }

            if feature_version in {"fv2", "fv2_regime"}:
                feature_values.update(
                    self._build_regime_features(
                        index=index,
                        closes=closes,
                        atr_14=atr_14,
                        atr_28=atr_28,
                        ema_9=ema_9,
                        ema_21=ema_21,
                        ema_50=ema_50,
                        ema_200=ema_200,
                        ema_9_slope_3=ema_9_slope_3,
                        ema_21_slope_3=ema_21_slope_3,
                        ema_50_slope_3=ema_50_slope_3,
                        ema_200_slope_3=ema_200_slope_3,
                        ema_9_slope_10=ema_9_slope_10,
                        ema_21_slope_10=ema_21_slope_10,
                        ema_50_slope_10=ema_50_slope_10,
                        ema_200_slope_10=ema_200_slope_10,
                        close_slope_3=close_slope_3,
                        close_slope_10=close_slope_10,
                        rolling_volatility_20=rolling_volatility_20,
                        rolling_volatility_50=rolling_volatility_50,
                        rsi_14=rsi_14,
                        macd=macd,
                        macd_signal=macd_signal,
                        macd_histogram=macd_histogram,
                        macd_histogram_slope_3=macd_histogram_slope_3,
                    )
                )

            normalized_features = {name: self._normalize_number(feature_values[name]) for name in target_feature_names}
            features_hash = hashlib.sha256(
                json.dumps(normalized_features, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            records.append(
                FeatureRecord(
                    symbol=symbol,
                    interval=interval,
                    candle_open_time=candle.open_time,
                    feature_version=feature_version,
                    features_json=normalized_features,
                    features_hash=features_hash,
                )
            )

        return records

    def _build_regime_features(
        self,
        index: int,
        closes: list[float],
        atr_14: list[float | None],
        atr_28: list[float | None],
        ema_9: list[float | None],
        ema_21: list[float | None],
        ema_50: list[float | None],
        ema_200: list[float | None],
        ema_9_slope_3: list[float | None],
        ema_21_slope_3: list[float | None],
        ema_50_slope_3: list[float | None],
        ema_200_slope_3: list[float | None],
        ema_9_slope_10: list[float | None],
        ema_21_slope_10: list[float | None],
        ema_50_slope_10: list[float | None],
        ema_200_slope_10: list[float | None],
        close_slope_3: list[float | None],
        close_slope_10: list[float | None],
        rolling_volatility_20: list[float | None],
        rolling_volatility_50: list[float | None],
        rsi_14: list[float | None],
        macd: list[float | None],
        macd_signal: list[float | None],
        macd_histogram: list[float | None],
        macd_histogram_slope_3: list[float | None],
    ) -> dict[str, float | None]:
        atr_value = atr_14[index]
        close_value = closes[index]
        ema9 = ema_9[index]
        ema21 = ema_21[index]
        ema50 = ema_50[index]
        ema200 = ema_200[index]
        close_minus_ema_21_atr = self._atr_normalized_distance(close_value, ema21, atr_value)
        close_minus_ema_50_atr = self._atr_normalized_distance(close_value, ema50, atr_value)
        close_minus_ema_200_atr = self._atr_normalized_distance(close_value, ema200, atr_value)
        ema_21_minus_ema_50 = self._atr_normalized_distance(ema21, ema50, atr_value)
        trend_up = self._trend_up(close_value, ema21, ema50, ema_50_slope_10[index])
        trend_down = self._trend_down(close_value, ema21, ema50, ema_50_slope_10[index])
        regime_range = self._regime_range(close_minus_ema_50_atr, ema_21_minus_ema_50)
        high_volatility = self._compare_optional(atr_14[index], atr_28[index], ">")
        low_volatility = self._compare_optional(atr_14[index], atr_28[index], "<=")
        volatility_expanding = self._compare_optional(rolling_volatility_20[index], rolling_volatility_50[index], ">")
        volatility_contracting = self._compare_optional(rolling_volatility_20[index], rolling_volatility_50[index], "<=")
        return {
            "ema_9_minus_ema_21": self._atr_normalized_distance(ema9, ema21, atr_value),
            "ema_9_minus_ema_50": self._atr_normalized_distance(ema9, ema50, atr_value),
            "ema_21_minus_ema_50": ema_21_minus_ema_50,
            "ema_50_minus_ema_200": self._atr_normalized_distance(ema50, ema200, atr_value),
            "ema_9_above_ema_21": self._binary_compare(ema9, ema21, ">"),
            "ema_21_above_ema_50": self._binary_compare(ema21, ema50, ">"),
            "ema_50_above_ema_200": self._binary_compare(ema50, ema200, ">"),
            "ema_stack_bullish": self._ema_stack(ema9, ema21, ema50, ema200, bullish=True),
            "ema_stack_bearish": self._ema_stack(ema9, ema21, ema50, ema200, bullish=False),
            "close_above_ema_21": self._binary_compare(close_value, ema21, ">"),
            "close_above_ema_50": self._binary_compare(close_value, ema50, ">"),
            "close_above_ema_200": self._binary_compare(close_value, ema200, ">"),
            "close_minus_ema_21_atr": close_minus_ema_21_atr,
            "close_minus_ema_50_atr": close_minus_ema_50_atr,
            "close_minus_ema_200_atr": close_minus_ema_200_atr,
            "ema_9_slope_3": ema_9_slope_3[index],
            "ema_21_slope_3": ema_21_slope_3[index],
            "ema_50_slope_3": ema_50_slope_3[index],
            "ema_200_slope_3": ema_200_slope_3[index],
            "ema_9_slope_10": ema_9_slope_10[index],
            "ema_21_slope_10": ema_21_slope_10[index],
            "ema_50_slope_10": ema_50_slope_10[index],
            "ema_200_slope_10": ema_200_slope_10[index],
            "close_slope_3": close_slope_3[index],
            "close_slope_10": close_slope_10[index],
            "regime_trend_up": trend_up,
            "regime_trend_down": trend_down,
            "regime_range": regime_range,
            "regime_high_volatility": high_volatility,
            "regime_low_volatility": low_volatility,
            "regime_unknown": self._regime_unknown(
                trend_up=trend_up,
                trend_down=trend_down,
                regime_range=regime_range,
                high_volatility=high_volatility,
                low_volatility=low_volatility,
            ),
            "regime_volatility_expanding": volatility_expanding,
            "regime_volatility_contracting": volatility_contracting,
            "rsi_14_above_50": self._binary_compare(rsi_14[index], 50.0, ">="),
            "rsi_14_below_50": self._binary_compare(rsi_14[index], 50.0, "<"),
            "rsi_14_overbought": self._binary_compare(rsi_14[index], 70.0, ">="),
            "rsi_14_oversold": self._binary_compare(rsi_14[index], 30.0, "<="),
            "macd_above_signal": self._binary_compare(macd[index], macd_signal[index], ">"),
            "macd_below_signal": self._binary_compare(macd[index], macd_signal[index], "<"),
            "macd_histogram_slope_3": macd_histogram_slope_3[index],
            "pullback_to_ema_21": self._pullback_flag(trend_up, close_minus_ema_21_atr),
            "pullback_to_ema_50": self._pullback_flag(trend_up, close_minus_ema_50_atr),
            "bearish_pullback_to_ema_21": self._pullback_flag(trend_down, close_minus_ema_21_atr),
            "bearish_pullback_to_ema_50": self._pullback_flag(trend_down, close_minus_ema_50_atr),
        }

    @staticmethod
    def _to_float(value: Any) -> float:
        return float(value)

    @staticmethod
    def _to_optional_float(value: Any) -> float | None:
        if value is None:
            return None
        return float(value)

    @staticmethod
    def _safe_divide(numerator: float | None, denominator: float | None) -> float | None:
        if numerator is None or denominator is None or denominator == 0:
            return None
        return numerator / denominator

    @staticmethod
    def _lookback_return(closes: list[float], index: int, period: int) -> float | None:
        if index < period or closes[index - period] == 0:
            return None
        return (closes[index] / closes[index - period]) - 1

    @staticmethod
    def _relative_to_value(close_value: float, indicator_value: float | None) -> float | None:
        if indicator_value is None or indicator_value == 0:
            return None
        return (close_value / indicator_value) - 1

    @staticmethod
    def _ratio_delta(left: float | None, right: float | None) -> float | None:
        if left is None or right is None or right == 0:
            return None
        return (left / right) - 1

    @staticmethod
    def _relative_delta(left: float | None, right: float | None, base: float) -> float | None:
        if left is None or right is None or base == 0:
            return None
        return (left - right) / base

    @staticmethod
    def _volume_spike(volume: float, volume_sma: float | None) -> float | None:
        if volume_sma is None or volume_sma == 0:
            return None
        return 1.0 if volume / volume_sma >= 2.0 else 0.0

    @staticmethod
    def _volume_change(volumes: list[float], index: int) -> float | None:
        if index <= 0:
            return None
        previous_volume = volumes[index - 1]
        if previous_volume == 0:
            return None
        return (volumes[index] / previous_volume) - 1

    @staticmethod
    def _atr_normalized_move(open_value: float, close_value: float, atr_value: float | None) -> float | None:
        if atr_value is None or atr_value == 0:
            return None
        return (close_value - open_value) / atr_value

    def _normalized_slope_series(
        self,
        values: list[float | None],
        atr_values: list[float | None],
        lookback: int,
    ) -> list[float | None]:
        result: list[float | None] = [None] * len(values)
        for index in range(len(values)):
            current = values[index]
            if index < lookback:
                continue
            previous = values[index - lookback]
            atr_value = atr_values[index]
            if current is None or previous is None or atr_value is None or atr_value == 0:
                continue
            result[index] = (float(current) - float(previous)) / atr_value
        return result

    @staticmethod
    def _atr_normalized_distance(left: float | None, right: float | None, atr_value: float | None) -> float | None:
        if left is None or right is None or atr_value is None or atr_value == 0:
            return None
        return (float(left) - float(right)) / atr_value

    @staticmethod
    def _binary_compare(left: float | None, right: float | None, operator: str) -> float | None:
        if left is None or right is None:
            return None
        if operator == ">":
            return 1.0 if left > right else 0.0
        if operator == "<":
            return 1.0 if left < right else 0.0
        if operator == ">=":
            return 1.0 if left >= right else 0.0
        if operator == "<=":
            return 1.0 if left <= right else 0.0
        raise ValueError(f"Unsupported operator: {operator}")

    def _compare_optional(self, left: float | None, right: float | None, operator: str) -> float | None:
        return self._binary_compare(left, right, operator)

    def _trend_up(
        self,
        close_value: float,
        ema_21: float | None,
        ema_50: float | None,
        ema_50_slope_10: float | None,
    ) -> float | None:
        if ema_21 is None or ema_50 is None or ema_50_slope_10 is None:
            return None
        return 1.0 if close_value > ema_50 and ema_21 > ema_50 and ema_50_slope_10 > 0 else 0.0

    def _trend_down(
        self,
        close_value: float,
        ema_21: float | None,
        ema_50: float | None,
        ema_50_slope_10: float | None,
    ) -> float | None:
        if ema_21 is None or ema_50 is None or ema_50_slope_10 is None:
            return None
        return 1.0 if close_value < ema_50 and ema_21 < ema_50 and ema_50_slope_10 < 0 else 0.0

    @staticmethod
    def _regime_range(close_minus_ema_50_atr: float | None, ema_21_minus_ema_50: float | None) -> float | None:
        if close_minus_ema_50_atr is None or ema_21_minus_ema_50 is None:
            return None
        return 1.0 if abs(close_minus_ema_50_atr) < 0.5 and abs(ema_21_minus_ema_50) < 0.3 else 0.0

    @staticmethod
    def _regime_unknown(
        *,
        trend_up: float | None,
        trend_down: float | None,
        regime_range: float | None,
        high_volatility: float | None,
        low_volatility: float | None,
    ) -> float | None:
        regime_values = [trend_up, trend_down, regime_range, high_volatility, low_volatility]
        if any(value is None for value in regime_values):
            if all(value is None for value in regime_values):
                return None
        normalized = [0.0 if value is None else float(value) for value in regime_values]
        return 1.0 if max(normalized, default=0.0) <= 0.0 else 0.0

    @staticmethod
    def _ema_stack(
        ema_9: float | None,
        ema_21: float | None,
        ema_50: float | None,
        ema_200: float | None,
        bullish: bool,
    ) -> float | None:
        if ema_9 is None or ema_21 is None or ema_50 is None or ema_200 is None:
            return None
        if bullish:
            return 1.0 if ema_9 > ema_21 > ema_50 > ema_200 else 0.0
        return 1.0 if ema_9 < ema_21 < ema_50 < ema_200 else 0.0

    @staticmethod
    def _pullback_flag(trend_flag: float | None, normalized_distance: float | None) -> float | None:
        if trend_flag is None or normalized_distance is None:
            return None
        return 1.0 if trend_flag == 1.0 and abs(normalized_distance) <= 0.5 else 0.0

    @staticmethod
    def _normalize_number(value: float | None) -> float | None:
        if value is None:
            return None
        return float(value)
