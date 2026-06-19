from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from app.features.book_setup_context_features import BookSetupContextFeatureBuilder
from app.features.feature_models import FeatureRecord, feature_names_for_version
from app.features.technical_indicators import TechnicalIndicators


class FeatureBuilder:
    FV3_FEATURE_VERSION = "fv3_candle_ta_context"
    FV4_FEATURE_VERSION = "fv4_book_setup_context"
    SHORT_WINDOW = 9
    MEDIUM_WINDOW = 21
    LONG_WINDOW = 50
    SUPPORT_RESISTANCE_WINDOW = 48

    def build(
        self,
        candles: list[Any],
        symbol: str,
        interval: str,
        feature_version: str,
    ) -> list[FeatureRecord]:
        if not candles:
            return []

        target_feature_names = feature_names_for_version(feature_version)
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
        sma_9 = TechnicalIndicators.sma(closes, 9)
        sma_21 = TechnicalIndicators.sma(closes, 21)
        sma_50 = TechnicalIndicators.sma(closes, 50)
        rsi_14 = TechnicalIndicators.rsi(closes, 14)
        macd, macd_signal, macd_histogram = TechnicalIndicators.macd(closes)
        volume_sma_20 = TechnicalIndicators.sma(volumes, 20)
        rolling_volatility_20 = TechnicalIndicators.rolling_stddev(self._simple_returns(closes), 20)
        rolling_volatility_50 = TechnicalIndicators.rolling_stddev(self._simple_returns(closes), 50)
        bollinger_mid, bollinger_upper, bollinger_lower = TechnicalIndicators.bollinger_bands(closes, 20, 2.0)
        stochastic_k, stochastic_d = TechnicalIndicators.stochastic(highs, lows, closes, 14, 3)
        roc_9 = TechnicalIndicators.rate_of_change(closes, self.SHORT_WINDOW)
        momentum_9 = TechnicalIndicators.momentum(closes, self.SHORT_WINDOW)
        volume_zscore_20 = TechnicalIndicators.rolling_zscore(volumes, 20)

        rolling_high_21 = TechnicalIndicators.rolling_max(highs, self.MEDIUM_WINDOW)
        rolling_low_21 = TechnicalIndicators.rolling_min(lows, self.MEDIUM_WINDOW)
        rolling_high_48 = TechnicalIndicators.rolling_max(highs, self.SUPPORT_RESISTANCE_WINDOW)
        rolling_low_48 = TechnicalIndicators.rolling_min(lows, self.SUPPORT_RESISTANCE_WINDOW)
        rolling_high_prev_48 = self._rolling_previous_extreme(highs, self.SUPPORT_RESISTANCE_WINDOW, highest=True)
        rolling_low_prev_48 = self._rolling_previous_extreme(lows, self.SUPPORT_RESISTANCE_WINDOW, highest=False)
        book_setup_context_builder = BookSetupContextFeatureBuilder()

        log_returns = self._log_returns(closes)
        close_slope_3 = self._normalized_slope_series(closes, atr_14, 3)
        close_slope_10 = self._normalized_slope_series(closes, atr_14, 10)
        close_slope_9 = self._normalized_slope_series(closes, atr_14, self.SHORT_WINDOW)
        close_slope_21 = self._normalized_slope_series(closes, atr_14, self.MEDIUM_WINDOW)
        close_slope_50 = self._normalized_slope_series(closes, atr_14, self.LONG_WINDOW)
        ema_9_slope_3 = self._normalized_slope_series(ema_9, atr_14, 3)
        ema_21_slope_3 = self._normalized_slope_series(ema_21, atr_14, 3)
        ema_50_slope_3 = self._normalized_slope_series(ema_50, atr_14, 3)
        ema_200_slope_3 = self._normalized_slope_series(ema_200, atr_14, 3)
        ema_9_slope_10 = self._normalized_slope_series(ema_9, atr_14, 10)
        ema_21_slope_10 = self._normalized_slope_series(ema_21, atr_14, 10)
        ema_50_slope_10 = self._normalized_slope_series(ema_50, atr_14, 10)
        ema_200_slope_10 = self._normalized_slope_series(ema_200, atr_14, 10)
        macd_histogram_slope_3 = self._normalized_slope_series(macd_histogram, atr_14, 3)
        macd_histogram_slope_9 = self._normalized_slope_series(macd_histogram, atr_14, self.SHORT_WINDOW)
        trend_age_series = self._trend_age_series(close_slope_21)
        correction_duration_series = self._correction_duration_series(closes, close_slope_21)
        support_touch_counts = self._touch_count_series(lows, rolling_low_prev_48, atr_14, tolerance_atr=0.35)
        resistance_touch_counts = self._touch_count_series(highs, rolling_high_prev_48, atr_14, tolerance_atr=0.35)

        records: list[FeatureRecord] = []
        for index, candle in enumerate(candles):
            candle_range = max(highs[index] - lows[index], 0.0)
            body_abs = abs(closes[index] - opens[index])
            upper_shadow_abs = max(highs[index] - max(opens[index], closes[index]), 0.0)
            lower_shadow_abs = max(min(opens[index], closes[index]) - lows[index], 0.0)
            body_to_range_ratio = self._safe_divide(body_abs, candle_range)
            close_position = self._safe_divide(closes[index] - lows[index], candle_range)
            open_position = self._safe_divide(opens[index] - lows[index], candle_range)
            candle_direction = self._direction_value(opens[index], closes[index])

            feature_values: dict[str, float | None] = {
                "body_size": body_abs,
                "upper_wick": upper_shadow_abs,
                "lower_wick": lower_shadow_abs,
                "candle_range": candle_range,
                "body_abs": body_abs,
                "body_pct": self._safe_divide(body_abs, abs(closes[index])),
                "body_to_range_ratio": body_to_range_ratio,
                "upper_shadow_abs": upper_shadow_abs,
                "lower_shadow_abs": lower_shadow_abs,
                "upper_shadow_pct": self._safe_divide(upper_shadow_abs, abs(closes[index])),
                "lower_shadow_pct": self._safe_divide(lower_shadow_abs, abs(closes[index])),
                "upper_to_lower_shadow_ratio": self._bounded_ratio(upper_shadow_abs, lower_shadow_abs),
                "shadow_imbalance": self._safe_divide(upper_shadow_abs - lower_shadow_abs, candle_range),
                "close_position_in_range": self._clamp(close_position, 0.0, 1.0),
                "open_position_in_range": self._clamp(open_position, 0.0, 1.0),
                "candle_direction": candle_direction,
                "is_bullish_candle": 1.0 if candle_direction > 0 else 0.0,
                "is_bearish_candle": 1.0 if candle_direction < 0 else 0.0,
                "is_neutral_candle": 1.0 if candle_direction == 0 else 0.0,
                "return_1": self._lookback_return(closes, index, 1),
                "return_3": self._lookback_return(closes, index, 3),
                "return_5": self._lookback_return(closes, index, 5),
                "return_6": self._lookback_return(closes, index, 6),
                "return_10": self._lookback_return(closes, index, 10),
                "log_return_1": log_returns[index],
                "atr_14": atr_14[index],
                "atr_28": atr_28[index],
                "range_percent": self._safe_divide(candle_range, abs(closes[index])),
                "range_pct": self._safe_divide(candle_range, abs(closes[index])),
                "upper_wick_pct": self._safe_divide(upper_shadow_abs, abs(closes[index])),
                "lower_wick_pct": self._safe_divide(lower_shadow_abs, abs(closes[index])),
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
                "volume_spike": self._volume_spike(volumes[index], volume_sma_20[index], volume_zscore_20[index]),
                "volume_change_pct": self._volume_change(volumes, index),
                "atr_normalized_move": self._atr_normalized_move(opens[index], closes[index], atr_14[index]),
                "taker_buy_ratio": self._safe_divide(taker_buy_volumes[index], volumes[index]),
                "trend_slope_short": close_slope_3[index],
                "trend_slope_medium": close_slope_10[index],
                "range_to_atr_ratio": self._bounded_positive_ratio(candle_range, atr_14[index]),
                "body_to_atr_ratio": self._bounded_positive_ratio(body_abs, atr_14[index]),
            }

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
                    macd_histogram_slope_3=macd_histogram_slope_3,
                )
            )

            if feature_version in {self.FV3_FEATURE_VERSION, self.FV4_FEATURE_VERSION}:
                feature_values.update(
                    self._build_fv3_features(
                        index=index,
                        opens=opens,
                        highs=highs,
                        lows=lows,
                        closes=closes,
                        volumes=volumes,
                        atr_14=atr_14,
                        ema_9=ema_9,
                        ema_21=ema_21,
                        ema_50=ema_50,
                        sma_9=sma_9,
                        sma_21=sma_21,
                        sma_50=sma_50,
                        rsi_14=rsi_14,
                        macd=macd,
                        macd_signal=macd_signal,
                        macd_histogram=macd_histogram,
                        macd_histogram_slope_9=macd_histogram_slope_9,
                        stochastic_k=stochastic_k,
                        stochastic_d=stochastic_d,
                        roc_9=roc_9,
                        momentum_9=momentum_9,
                        volume_sma_20=volume_sma_20,
                        volume_zscore_20=volume_zscore_20,
                        bollinger_mid=bollinger_mid,
                        bollinger_upper=bollinger_upper,
                        bollinger_lower=bollinger_lower,
                        rolling_volatility_20=rolling_volatility_20,
                        rolling_volatility_50=rolling_volatility_50,
                        rolling_high_21=rolling_high_21,
                        rolling_low_21=rolling_low_21,
                        rolling_high_48=rolling_high_48,
                        rolling_low_48=rolling_low_48,
                        rolling_high_prev_48=rolling_high_prev_48,
                        rolling_low_prev_48=rolling_low_prev_48,
                        close_slope_9=close_slope_9,
                        close_slope_21=close_slope_21,
                        close_slope_50=close_slope_50,
                        trend_age_series=trend_age_series,
                        correction_duration_series=correction_duration_series,
                        support_touch_counts=support_touch_counts,
                        resistance_touch_counts=resistance_touch_counts,
                    )
                )

            if feature_version == self.FV4_FEATURE_VERSION:
                feature_values.update(
                    book_setup_context_builder.build(
                        candles=candles,
                        index=index,
                        base_features=feature_values,
                    )
                )

            normalized_features = {
                name: self._normalize_number(feature_values.get(name))
                for name in target_feature_names
            }
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
        *,
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
        high_volatility = self._binary_compare(atr_14[index], atr_28[index], ">")
        low_volatility = self._binary_compare(atr_14[index], atr_28[index], "<=")
        volatility_expanding = self._binary_compare(rolling_volatility_20[index], rolling_volatility_50[index], ">")
        volatility_contracting = self._binary_compare(rolling_volatility_20[index], rolling_volatility_50[index], "<=")
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

    def _build_fv3_features(
        self,
        *,
        index: int,
        opens: list[float],
        highs: list[float],
        lows: list[float],
        closes: list[float],
        volumes: list[float],
        atr_14: list[float | None],
        ema_9: list[float | None],
        ema_21: list[float | None],
        ema_50: list[float | None],
        sma_9: list[float | None],
        sma_21: list[float | None],
        sma_50: list[float | None],
        rsi_14: list[float | None],
        macd: list[float | None],
        macd_signal: list[float | None],
        macd_histogram: list[float | None],
        macd_histogram_slope_9: list[float | None],
        stochastic_k: list[float | None],
        stochastic_d: list[float | None],
        roc_9: list[float | None],
        momentum_9: list[float | None],
        volume_sma_20: list[float | None],
        volume_zscore_20: list[float | None],
        bollinger_mid: list[float | None],
        bollinger_upper: list[float | None],
        bollinger_lower: list[float | None],
        rolling_volatility_20: list[float | None],
        rolling_volatility_50: list[float | None],
        rolling_high_21: list[float | None],
        rolling_low_21: list[float | None],
        rolling_high_48: list[float | None],
        rolling_low_48: list[float | None],
        rolling_high_prev_48: list[float | None],
        rolling_low_prev_48: list[float | None],
        close_slope_9: list[float | None],
        close_slope_21: list[float | None],
        close_slope_50: list[float | None],
        trend_age_series: list[float | None],
        correction_duration_series: list[float | None],
        support_touch_counts: list[float | None],
        resistance_touch_counts: list[float | None],
    ) -> dict[str, float | None]:
        atr_value = atr_14[index]
        close_value = closes[index]
        open_value = opens[index]
        high_value = highs[index]
        low_value = lows[index]
        candle_range = max(high_value - low_value, 0.0)
        body_abs = abs(close_value - open_value)
        upper_shadow = max(high_value - max(open_value, close_value), 0.0)
        lower_shadow = max(min(open_value, close_value) - low_value, 0.0)
        body_to_range = self._safe_divide(body_abs, candle_range)
        close_pos = self._clamp(self._safe_divide(close_value - low_value, candle_range), 0.0, 1.0)

        trend_up_flag = self._trend_up(close_value, ema_21[index], ema_50[index], close_slope_50[index])
        trend_down_flag = self._trend_down(close_value, ema_21[index], ema_50[index], close_slope_50[index])
        medium_trend_sign = self._series_sign(close_slope_21[index])

        doji_score = self._small_body_score(body_to_range, full_score_at=0.08, zero_score_at=0.22)
        long_shadow_score = self._large_value_score(self._safe_divide(upper_shadow + lower_shadow, body_abs or 1e-9), start=1.5, full=4.0)
        long_legged_doji_score = self._combine_scores(doji_score, long_shadow_score)
        gravestone_doji_score = self._combine_scores(
            doji_score,
            self._dominant_shadow_score(upper_shadow, lower_shadow),
            self._small_body_score(close_pos, full_score_at=0.20, zero_score_at=0.45),
        )
        dragonfly_doji_score = self._combine_scores(
            doji_score,
            self._dominant_shadow_score(lower_shadow, upper_shadow),
            self._small_body_score(1.0 - (close_pos or 0.5), full_score_at=0.20, zero_score_at=0.45),
        )
        hammer_score = self._combine_scores(
            self._small_body_score(body_to_range, full_score_at=0.30, zero_score_at=0.60),
            self._large_value_score(self._safe_divide(lower_shadow, body_abs or 1e-9), start=1.5, full=2.5),
            self._small_body_score(upper_shadow / (candle_range or 1.0), full_score_at=0.15, zero_score_at=0.35),
            self._optional_to_score(close_pos),
        )
        inverted_hammer_score = self._combine_scores(
            self._small_body_score(body_to_range, full_score_at=0.30, zero_score_at=0.60),
            self._large_value_score(self._safe_divide(upper_shadow, body_abs or 1e-9), start=1.5, full=2.5),
            self._small_body_score(lower_shadow / (candle_range or 1.0), full_score_at=0.15, zero_score_at=0.35),
            self._optional_to_score(close_pos),
        )
        shooting_star_score = self._combine_scores(
            inverted_hammer_score,
            self._optional_to_score(trend_up_flag),
        )
        hanging_man_score = self._combine_scores(
            hammer_score,
            self._optional_to_score(trend_up_flag),
        )
        bullish_engulfing_score = self._engulfing_score(opens, closes, index, bullish=True)
        bearish_engulfing_score = self._engulfing_score(opens, closes, index, bullish=False)
        harami_score = self._harami_score(opens, closes, index)
        morning_star_score = self._star_score(opens, closes, highs, lows, index, bullish=True)
        evening_star_score = self._star_score(opens, closes, highs, lows, index, bullish=False)
        three_white_soldiers_score = self._three_candles_score(opens, closes, highs, lows, index, bullish=True)
        three_black_crows_score = self._three_candles_score(opens, closes, highs, lows, index, bullish=False)
        window_gap_up = self._window_gap_score(highs, lows, index, up=True)
        window_gap_down = self._window_gap_score(highs, lows, index, up=False)
        gap_size_atr = self._gap_size_atr(highs, lows, index, atr_value)

        bullish_pattern_scores = [
            dragonfly_doji_score,
            hammer_score * self._optional_to_score(trend_down_flag),
            inverted_hammer_score * self._optional_to_score(trend_down_flag),
            bullish_engulfing_score,
            morning_star_score,
            three_white_soldiers_score,
            window_gap_up,
        ]
        bearish_pattern_scores = [
            gravestone_doji_score,
            shooting_star_score,
            hanging_man_score,
            bearish_engulfing_score,
            evening_star_score,
            three_black_crows_score,
            window_gap_down,
        ]
        strongest_bullish = max(bullish_pattern_scores)
        strongest_bearish = max(bearish_pattern_scores)
        pattern_strength_score = max(strongest_bullish, strongest_bearish, harami_score, long_legged_doji_score)
        pattern_direction_hint = self._clamp(strongest_bullish - strongest_bearish, -1.0, 1.0)
        pattern_requires_confirmation = 1.0 if pattern_strength_score >= 0.40 else 0.0
        pattern_context_valid = 1.0 if trend_up_flag is not None or trend_down_flag is not None else 0.0

        recent_high = rolling_high_48[index]
        recent_low = rolling_low_48[index]
        recent_high_prev = rolling_high_prev_48[index]
        recent_low_prev = rolling_low_prev_48[index]
        recent_high_distance = self._bounded_positive_ratio((recent_high or close_value) - close_value, atr_value)
        recent_low_distance = self._bounded_positive_ratio(close_value - (recent_low or close_value), atr_value)
        distance_to_support = self._bounded_positive_ratio(close_value - (recent_low_prev or close_value), atr_value)
        distance_to_resistance = self._bounded_positive_ratio((recent_high_prev or close_value) - close_value, atr_value)
        support_resistance_width_atr = self._bounded_positive_ratio(
            None if recent_high is None or recent_low is None else recent_high - recent_low,
            atr_value,
        )
        near_support = self._score_from_distance(distance_to_support, full_score_at=0.30, zero_score_at=1.00)
        near_resistance = self._score_from_distance(distance_to_resistance, full_score_at=0.30, zero_score_at=1.00)
        breakout_candidate = self._breakout_score(close_value, recent_high_prev, atr_value, bullish=True)
        breakdown_candidate = self._breakout_score(close_value, recent_low_prev, atr_value, bullish=False)
        false_breakout_candidate = self._false_break_score(high_value, close_value, recent_high_prev, atr_value, bullish=True)
        false_breakdown_candidate = self._false_break_score(low_value, close_value, recent_low_prev, atr_value, bullish=False)

        bollinger_position = self._band_position(close_value, bollinger_lower[index], bollinger_upper[index])
        bollinger_bandwidth = self._safe_divide(
            None
            if bollinger_upper[index] is None or bollinger_lower[index] is None
            else bollinger_upper[index] - bollinger_lower[index],
            bollinger_mid[index],
        )
        bollinger_squeeze_score = self._small_body_score(bollinger_bandwidth, full_score_at=0.03, zero_score_at=0.12)
        stochastic_cross_hint = self._stochastic_cross_hint(stochastic_k, stochastic_d, index)

        trend_strength_short = self._atr_normalized_distance(close_value, sma_9[index], atr_value)
        trend_strength_medium = self._atr_normalized_distance(close_value, sma_21[index], atr_value)
        trend_strength_long = self._atr_normalized_distance(close_value, sma_50[index], atr_value)
        higher_highs_score = self._directional_sequence_score(highs, index, bullish=True)
        higher_lows_score = self._directional_sequence_score(lows, index, bullish=True)
        lower_highs_score = self._directional_sequence_score(highs, index, bullish=False)
        lower_lows_score = self._directional_sequence_score(lows, index, bullish=False)
        impulse_strength = self._bounded_positive_ratio(
            None if index < self.SHORT_WINDOW else abs(close_value - closes[index - self.SHORT_WINDOW]),
            atr_value,
        )
        correction_depth = self._correction_depth(
            close_value=close_value,
            rolling_high=rolling_high_21[index],
            rolling_low=rolling_low_21[index],
            atr_value=atr_value,
            medium_trend_sign=medium_trend_sign,
        )
        range_position = self._band_position(close_value, recent_low, recent_high)
        volatility_regime_score = self._volatility_regime_score(rolling_volatility_20[index], rolling_volatility_50[index])
        rsi_zone = self._rsi_zone(rsi_14[index])
        ema_fast_distance = self._atr_normalized_distance(close_value, ema_9[index], atr_value)
        ema_slow_distance = self._atr_normalized_distance(close_value, ema_50[index], atr_value)
        sma_fast_distance = self._atr_normalized_distance(close_value, sma_9[index], atr_value)
        sma_slow_distance = self._atr_normalized_distance(close_value, sma_50[index], atr_value)
        sma_fast_slow_spread = self._atr_normalized_distance(sma_9[index], sma_21[index], atr_value)
        ema_fast_slow_spread = self._atr_normalized_distance(ema_9[index], ema_21[index], atr_value)
        volume_confirmation = self._volume_confirmation(
            candle_direction=self._direction_value(open_value, close_value),
            medium_trend_sign=medium_trend_sign,
            volume_zscore=volume_zscore_20[index],
        )

        return {
            "trend_slope_short": close_slope_9[index],
            "trend_slope_medium": close_slope_21[index],
            "trend_slope_long": close_slope_50[index],
            "trend_strength_short": trend_strength_short,
            "trend_strength_medium": trend_strength_medium,
            "trend_strength_long": trend_strength_long,
            "trend_age": trend_age_series[index],
            "higher_highs_score": higher_highs_score,
            "higher_lows_score": higher_lows_score,
            "lower_highs_score": lower_highs_score,
            "lower_lows_score": lower_lows_score,
            "impulse_strength": impulse_strength,
            "correction_depth": correction_depth,
            "correction_duration": correction_duration_series[index],
            "range_position": range_position,
            "volatility_regime_score": volatility_regime_score,
            "recent_high_distance": recent_high_distance,
            "recent_low_distance": recent_low_distance,
            "distance_to_support": distance_to_support,
            "distance_to_resistance": distance_to_resistance,
            "support_touch_count": support_touch_counts[index],
            "resistance_touch_count": resistance_touch_counts[index],
            "support_resistance_width_atr": support_resistance_width_atr,
            "near_support": near_support,
            "near_resistance": near_resistance,
            "breakout_candidate": breakout_candidate,
            "breakdown_candidate": breakdown_candidate,
            "false_breakout_candidate": false_breakout_candidate,
            "false_breakdown_candidate": false_breakdown_candidate,
            "sma_fast_distance": sma_fast_distance,
            "sma_slow_distance": sma_slow_distance,
            "ema_fast_distance": ema_fast_distance,
            "ema_slow_distance": ema_slow_distance,
            "sma_fast_slow_spread": sma_fast_slow_spread,
            "ema_fast_slow_spread": ema_fast_slow_spread,
            "bollinger_position": bollinger_position,
            "bollinger_bandwidth": bollinger_bandwidth,
            "bollinger_squeeze_score": bollinger_squeeze_score,
            "rsi_value": rsi_14[index],
            "rsi_zone": rsi_zone,
            "macd_line": macd[index],
            "macd_signal": macd_signal[index],
            "macd_histogram": macd_histogram[index],
            "macd_histogram_slope": macd_histogram_slope_9[index],
            "stochastic_k": stochastic_k[index],
            "stochastic_d": stochastic_d[index],
            "stochastic_cross_hint": stochastic_cross_hint,
            "roc": roc_9[index],
            "momentum": self._atr_normalized_distance(momentum_9[index], 0.0, atr_value),
            "volume_zscore": volume_zscore_20[index],
            "volume_spike": self._volume_spike(volumes[index], volume_sma_20[index], volume_zscore_20[index]),
            "volume_confirmation": volume_confirmation,
            "doji_score": doji_score,
            "long_legged_doji_score": long_legged_doji_score,
            "gravestone_doji_score": gravestone_doji_score,
            "dragonfly_doji_score": dragonfly_doji_score,
            "hammer_score": hammer_score,
            "inverted_hammer_score": inverted_hammer_score,
            "shooting_star_score": shooting_star_score,
            "hanging_man_score": hanging_man_score,
            "bullish_engulfing_score": bullish_engulfing_score,
            "bearish_engulfing_score": bearish_engulfing_score,
            "harami_score": harami_score,
            "morning_star_score": morning_star_score,
            "evening_star_score": evening_star_score,
            "three_white_soldiers_score": three_white_soldiers_score,
            "three_black_crows_score": three_black_crows_score,
            "window_gap_up": window_gap_up,
            "window_gap_down": window_gap_down,
            "gap_size_atr": gap_size_atr,
            "pattern_strength_score": pattern_strength_score,
            "pattern_direction_hint": pattern_direction_hint,
            "pattern_requires_confirmation": pattern_requires_confirmation,
            "pattern_context_valid": pattern_context_valid,
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
    def _simple_returns(closes: list[float]) -> list[float | None]:
        result: list[float | None] = [None] * len(closes)
        for index in range(1, len(closes)):
            previous_close = closes[index - 1]
            if previous_close == 0:
                continue
            result[index] = (closes[index] / previous_close) - 1.0
        return result

    @staticmethod
    def _log_returns(closes: list[float]) -> list[float | None]:
        result: list[float | None] = [None] * len(closes)
        for index in range(1, len(closes)):
            previous_close = closes[index - 1]
            if previous_close <= 0 or closes[index] <= 0:
                continue
            result[index] = math.log(closes[index] / previous_close)
        return result

    @staticmethod
    def _safe_divide(numerator: float | None, denominator: float | None) -> float | None:
        if numerator is None or denominator is None or denominator == 0:
            return None
        return numerator / denominator

    def _bounded_ratio(self, numerator: float | None, denominator: float | None, *, cap: float = 10.0) -> float | None:
        value = self._safe_divide(numerator, denominator)
        return self._clamp(value, 0.0, cap) if value is not None else None

    def _bounded_positive_ratio(self, numerator: float | None, denominator: float | None, *, cap: float = 10.0) -> float | None:
        value = self._safe_divide(numerator, denominator)
        return self._clamp(abs(value), 0.0, cap) if value is not None else None

    @staticmethod
    def _lookback_return(closes: list[float], index: int, period: int) -> float | None:
        if index < period or closes[index - period] == 0:
            return None
        return (closes[index] / closes[index - period]) - 1.0

    @staticmethod
    def _relative_to_value(close_value: float, indicator_value: float | None) -> float | None:
        if indicator_value is None or indicator_value == 0:
            return None
        return (close_value / indicator_value) - 1.0

    @staticmethod
    def _ratio_delta(left: float | None, right: float | None) -> float | None:
        if left is None or right is None or right == 0:
            return None
        return (left / right) - 1.0

    @staticmethod
    def _relative_delta(left: float | None, right: float | None, base: float) -> float | None:
        if left is None or right is None or base == 0:
            return None
        return (left - right) / base

    def _volume_spike(self, volume: float, volume_sma: float | None, volume_zscore: float | None = None) -> float | None:
        if volume_sma is None or volume_sma == 0:
            return None
        ratio = volume / volume_sma
        zscore_component = 0.0 if volume_zscore is None else self._large_value_score(volume_zscore, start=1.0, full=2.5)
        return self._clamp(max(0.0, min(ratio / 2.0, 1.0), zscore_component), 0.0, 1.0)

    @staticmethod
    def _volume_change(volumes: list[float], index: int) -> float | None:
        if index <= 0 or volumes[index - 1] == 0:
            return None
        return (volumes[index] / volumes[index - 1]) - 1.0

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
            if index < lookback:
                continue
            current = values[index]
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

    def _trend_up(
        self,
        close_value: float,
        ema_21: float | None,
        ema_50: float | None,
        ema_50_slope: float | None,
    ) -> float | None:
        if ema_21 is None or ema_50 is None or ema_50_slope is None:
            return None
        return 1.0 if close_value > ema_50 and ema_21 > ema_50 and ema_50_slope > 0 else 0.0

    def _trend_down(
        self,
        close_value: float,
        ema_21: float | None,
        ema_50: float | None,
        ema_50_slope: float | None,
    ) -> float | None:
        if ema_21 is None or ema_50 is None or ema_50_slope is None:
            return None
        return 1.0 if close_value < ema_50 and ema_21 < ema_50 and ema_50_slope < 0 else 0.0

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
        *,
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
    def _clamp(value: float | None, minimum: float, maximum: float) -> float | None:
        if value is None:
            return None
        return max(minimum, min(maximum, float(value)))

    @staticmethod
    def _direction_value(open_value: float, close_value: float) -> float:
        if close_value > open_value:
            return 1.0
        if close_value < open_value:
            return -1.0
        return 0.0

    @staticmethod
    def _series_sign(value: float | None) -> float:
        if value is None:
            return 0.0
        if value > 0:
            return 1.0
        if value < 0:
            return -1.0
        return 0.0

    def _small_body_score(self, value: float | None, *, full_score_at: float, zero_score_at: float) -> float:
        if value is None:
            return 0.0
        if value <= full_score_at:
            return 1.0
        if value >= zero_score_at:
            return 0.0
        return self._clamp(1.0 - ((value - full_score_at) / (zero_score_at - full_score_at)), 0.0, 1.0) or 0.0

    def _large_value_score(self, value: float | None, *, start: float, full: float) -> float:
        if value is None:
            return 0.0
        if value <= start:
            return 0.0
        if value >= full:
            return 1.0
        return self._clamp((value - start) / (full - start), 0.0, 1.0) or 0.0

    def _score_from_distance(self, value: float | None, *, full_score_at: float, zero_score_at: float) -> float | None:
        if value is None:
            return None
        return self._small_body_score(value, full_score_at=full_score_at, zero_score_at=zero_score_at)

    @staticmethod
    def _optional_to_score(value: float | None) -> float:
        if value is None:
            return 0.0
        return max(0.0, min(1.0, float(value)))

    @staticmethod
    def _combine_scores(*values: float | None) -> float:
        numeric = [max(0.0, min(1.0, float(value))) for value in values if value is not None]
        if not numeric:
            return 0.0
        return sum(numeric) / len(numeric)

    def _dominant_shadow_score(self, dominant: float, other: float) -> float:
        return self._large_value_score(self._safe_divide(dominant, (other or 1e-9)), start=1.5, full=3.0)

    def _engulfing_score(self, opens: list[float], closes: list[float], index: int, *, bullish: bool) -> float:
        if index < 1:
            return 0.0
        prev_open = opens[index - 1]
        prev_close = closes[index - 1]
        curr_open = opens[index]
        curr_close = closes[index]
        prev_body = abs(prev_close - prev_open)
        curr_body = abs(curr_close - curr_open)
        if prev_body == 0 or curr_body == 0:
            return 0.0
        prev_bear = prev_close < prev_open
        prev_bull = prev_close > prev_open
        curr_bull = curr_close > curr_open
        curr_bear = curr_close < curr_open
        if bullish and not (prev_bear and curr_bull):
            return 0.0
        if not bullish and not (prev_bull and curr_bear):
            return 0.0
        prev_low_body = min(prev_open, prev_close)
        prev_high_body = max(prev_open, prev_close)
        curr_low_body = min(curr_open, curr_close)
        curr_high_body = max(curr_open, curr_close)
        engulf = curr_low_body <= prev_low_body and curr_high_body >= prev_high_body
        if not engulf:
            return 0.0
        return self._large_value_score(curr_body / prev_body, start=1.0, full=1.8)

    def _harami_score(self, opens: list[float], closes: list[float], index: int) -> float:
        if index < 1:
            return 0.0
        prev_open = opens[index - 1]
        prev_close = closes[index - 1]
        curr_open = opens[index]
        curr_close = closes[index]
        prev_low_body = min(prev_open, prev_close)
        prev_high_body = max(prev_open, prev_close)
        curr_low_body = min(curr_open, curr_close)
        curr_high_body = max(curr_open, curr_close)
        inside = curr_low_body >= prev_low_body and curr_high_body <= prev_high_body
        if not inside:
            return 0.0
        prev_body = abs(prev_close - prev_open)
        curr_body = abs(curr_close - curr_open)
        return self._combine_scores(
            self._large_value_score(prev_body, start=0.2, full=1.0),
            self._small_body_score(self._safe_divide(curr_body, prev_body), full_score_at=0.30, zero_score_at=0.80),
        )

    def _star_score(
        self,
        opens: list[float],
        closes: list[float],
        highs: list[float],
        lows: list[float],
        index: int,
        *,
        bullish: bool,
    ) -> float:
        if index < 2:
            return 0.0
        first_dir = self._direction_value(opens[index - 2], closes[index - 2])
        second_body = abs(closes[index - 1] - opens[index - 1])
        second_range = highs[index - 1] - lows[index - 1]
        third_dir = self._direction_value(opens[index], closes[index])
        if bullish and not (first_dir < 0 and third_dir > 0):
            return 0.0
        if not bullish and not (first_dir > 0 and third_dir < 0):
            return 0.0
        midpoint_first = (opens[index - 2] + closes[index - 2]) / 2.0
        third_close = closes[index]
        confirmation = third_close >= midpoint_first if bullish else third_close <= midpoint_first
        if not confirmation:
            return 0.0
        second_small = self._small_body_score(self._safe_divide(second_body, second_range), full_score_at=0.20, zero_score_at=0.45)
        return self._combine_scores(1.0, second_small)

    def _three_candles_score(
        self,
        opens: list[float],
        closes: list[float],
        highs: list[float],
        lows: list[float],
        index: int,
        *,
        bullish: bool,
    ) -> float:
        if index < 2:
            return 0.0
        directions = [self._direction_value(opens[index - offset], closes[index - offset]) for offset in (2, 1, 0)]
        if bullish and any(direction <= 0 for direction in directions):
            return 0.0
        if not bullish and any(direction >= 0 for direction in directions):
            return 0.0
        closes_window = [closes[index - offset] for offset in (2, 1, 0)]
        monotonic = closes_window[0] < closes_window[1] < closes_window[2] if bullish else closes_window[0] > closes_window[1] > closes_window[2]
        if not monotonic:
            return 0.0
        range_scores = [
            self._large_value_score(
                self._safe_divide(abs(closes[index - offset] - opens[index - offset]), highs[index - offset] - lows[index - offset]),
                start=0.35,
                full=0.70,
            )
            for offset in (2, 1, 0)
        ]
        return self._combine_scores(*range_scores)

    def _window_gap_score(self, highs: list[float], lows: list[float], index: int, *, up: bool) -> float:
        if index < 1:
            return 0.0
        if up:
            return 1.0 if lows[index] > highs[index - 1] else 0.0
        return 1.0 if highs[index] < lows[index - 1] else 0.0

    def _gap_size_atr(self, highs: list[float], lows: list[float], index: int, atr_value: float | None) -> float | None:
        if index < 1 or atr_value is None or atr_value == 0:
            return None
        gap_up = max(lows[index] - highs[index - 1], 0.0)
        gap_down = max(lows[index - 1] - highs[index], 0.0)
        return self._bounded_positive_ratio(max(gap_up, gap_down), atr_value)

    @staticmethod
    def _rolling_previous_extreme(values: list[float], period: int, *, highest: bool) -> list[float | None]:
        result: list[float | None] = [None] * len(values)
        for index in range(1, len(values)):
            start = max(0, index - period)
            window = values[start:index]
            if not window or len(window) < period:
                continue
            result[index] = max(window) if highest else min(window)
        return result

    def _trend_age_series(self, slope_values: list[float | None]) -> list[float | None]:
        result: list[float | None] = [None] * len(slope_values)
        previous_sign = 0.0
        age = 0
        for index, value in enumerate(slope_values):
            sign = self._series_sign(value)
            if value is None or sign == 0.0:
                previous_sign = 0.0
                age = 0
                continue
            if sign == previous_sign:
                age += 1
            else:
                age = 1
            previous_sign = sign
            result[index] = float(min(age, self.LONG_WINDOW))
        return result

    def _correction_duration_series(self, closes: list[float], trend_slope_values: list[float | None]) -> list[float | None]:
        result: list[float | None] = [None] * len(closes)
        up_duration = 0
        down_duration = 0
        for index in range(1, len(closes)):
            trend_sign = self._series_sign(trend_slope_values[index])
            price_change_sign = self._series_sign(closes[index] - closes[index - 1])
            if trend_sign > 0 and price_change_sign < 0:
                up_duration += 1
            else:
                up_duration = 0
            if trend_sign < 0 and price_change_sign > 0:
                down_duration += 1
            else:
                down_duration = 0
            if trend_sign > 0:
                result[index] = float(up_duration)
            elif trend_sign < 0:
                result[index] = float(down_duration)
        return result

    def _directional_sequence_score(self, values: list[float], index: int, *, bullish: bool, lookback: int = 5) -> float | None:
        if index < lookback - 1:
            return None
        score = 0
        total = 0
        for current in range(index - lookback + 2, index + 1):
            previous = current - 1
            total += 1
            if bullish and values[current] > values[previous]:
                score += 1
            if not bullish and values[current] < values[previous]:
                score += 1
        if total == 0:
            return None
        return score / total

    def _touch_count_series(
        self,
        values: list[float],
        reference_values: list[float | None],
        atr_values: list[float | None],
        *,
        tolerance_atr: float,
        lookback: int = 12,
    ) -> list[float | None]:
        result: list[float | None] = [None] * len(values)
        for index in range(len(values)):
            reference = reference_values[index]
            atr_value = atr_values[index]
            if reference is None or atr_value is None or atr_value == 0:
                continue
            start = max(0, index - lookback + 1)
            count = 0
            for window_index in range(start, index + 1):
                if abs(values[window_index] - reference) <= (tolerance_atr * atr_value):
                    count += 1
            result[index] = float(min(count, 10))
        return result

    def _band_position(self, value: float, low: float | None, high: float | None) -> float | None:
        if low is None or high is None:
            return None
        denominator = high - low
        if denominator == 0:
            return 0.5
        return self._clamp((value - low) / denominator, 0.0, 1.0)

    def _volatility_regime_score(self, short_vol: float | None, long_vol: float | None) -> float | None:
        if short_vol is None or long_vol is None or long_vol == 0:
            return None
        ratio = short_vol / long_vol
        return self._clamp(ratio, 0.0, 3.0)

    def _rsi_zone(self, rsi_value: float | None) -> float | None:
        if rsi_value is None:
            return None
        if rsi_value >= 70:
            return 1.0
        if rsi_value <= 30:
            return -1.0
        return self._clamp((rsi_value - 50.0) / 20.0, -1.0, 1.0)

    def _stochastic_cross_hint(self, stochastic_k: list[float | None], stochastic_d: list[float | None], index: int) -> float | None:
        if index < 1:
            return None
        current_k = stochastic_k[index]
        current_d = stochastic_d[index]
        previous_k = stochastic_k[index - 1]
        previous_d = stochastic_d[index - 1]
        if current_k is None or current_d is None or previous_k is None or previous_d is None:
            return None
        if previous_k <= previous_d and current_k > current_d:
            return 1.0
        if previous_k >= previous_d and current_k < current_d:
            return -1.0
        return 0.0

    def _breakout_score(self, close_value: float, reference: float | None, atr_value: float | None, *, bullish: bool) -> float | None:
        if reference is None or atr_value is None or atr_value == 0:
            return None
        move = (close_value - reference) if bullish else (reference - close_value)
        if move <= 0:
            return 0.0
        return self._large_value_score(move / atr_value, start=0.0, full=1.0)

    def _false_break_score(self, extreme_value: float, close_value: float, reference: float | None, atr_value: float | None, *, bullish: bool) -> float | None:
        if reference is None or atr_value is None or atr_value == 0:
            return None
        if bullish:
            if extreme_value <= reference or close_value > reference:
                return 0.0
            return self._large_value_score((extreme_value - reference) / atr_value, start=0.0, full=1.0)
        if extreme_value >= reference or close_value < reference:
            return 0.0
        return self._large_value_score((reference - extreme_value) / atr_value, start=0.0, full=1.0)

    def _correction_depth(
        self,
        *,
        close_value: float,
        rolling_high: float | None,
        rolling_low: float | None,
        atr_value: float | None,
        medium_trend_sign: float,
    ) -> float | None:
        if atr_value is None or atr_value == 0:
            return None
        if medium_trend_sign > 0 and rolling_high is not None:
            return self._bounded_positive_ratio(rolling_high - close_value, atr_value)
        if medium_trend_sign < 0 and rolling_low is not None:
            return self._bounded_positive_ratio(close_value - rolling_low, atr_value)
        if rolling_high is not None and rolling_low is not None:
            midpoint = (rolling_high + rolling_low) / 2.0
            return self._bounded_positive_ratio(abs(close_value - midpoint), atr_value)
        return None

    def _volume_confirmation(self, *, candle_direction: float, medium_trend_sign: float, volume_zscore: float | None) -> float | None:
        if volume_zscore is None:
            return None
        alignment = 1.0 if medium_trend_sign == 0.0 or candle_direction == medium_trend_sign else 0.0
        volume_score = self._large_value_score(volume_zscore, start=0.5, full=2.0)
        return self._combine_scores(alignment, volume_score)

    @staticmethod
    def _normalize_number(value: float | None) -> float | None:
        if value is None:
            return None
        normalized = float(value)
        if not math.isfinite(normalized):
            return None
        return normalized
