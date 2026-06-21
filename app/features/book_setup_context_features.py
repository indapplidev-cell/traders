from __future__ import annotations

from statistics import mean
from typing import Any, Mapping, Sequence


NISON_CONTEXT_FEATURE_NAMES = [
    "nison_reversal_context_score",
    "nison_continuation_context_score",
    "nison_indecision_context_score",
    "nison_confirmation_required_score",
    "nison_confirmation_present_score",
    "nison_pattern_invalidated_score",
    "nison_hammer_after_decline_score",
    "nison_shooting_star_after_advance_score",
    "nison_engulfing_with_trend_context_score",
    "nison_doji_after_impulse_score",
    "nison_window_gap_context_score",
    "nison_pattern_at_support_score",
    "nison_pattern_at_resistance_score",
    "nison_invalidation_distance_atr",
    "nison_expected_followthrough_score",
]

ALTUNINA_CONTEXT_FEATURE_NAMES = [
    "alt_trend_continuation_long_score",
    "alt_trend_continuation_short_score",
    "alt_pullback_long_score",
    "alt_pullback_short_score",
    "alt_support_retest_long_score",
    "alt_resistance_rejection_short_score",
    "alt_breakout_long_score",
    "alt_breakdown_short_score",
    "alt_false_breakout_risk_score",
    "alt_range_chop_score",
    "alt_trend_exhaustion_long_risk_score",
    "alt_trend_exhaustion_short_risk_score",
    "alt_volume_confirms_direction_score",
    "alt_indicator_confluence_long_score",
    "alt_indicator_confluence_short_score",
    "alt_no_trade_chop_score",
]

PATH_CONTEXT_FEATURE_NAMES = [
    "path_4_return_atr",
    "path_8_return_atr",
    "path_12_return_atr",
    "path_16_return_atr",
    "path_8_high_low_expansion_atr",
    "path_12_pullback_depth_atr",
    "path_12_upper_wick_pressure",
    "path_12_lower_wick_pressure",
    "path_12_close_progression_score",
    "path_16_trend_consistency_score",
    "path_16_chop_score",
    "volume_8_confirmation_score",
    "volume_16_exhaustion_score",
]

HTF_CONTEXT_FEATURE_NAMES = [
    "htf_1h_trend_score",
    "htf_1h_range_position",
    "htf_1h_volatility_score",
    "htf_4h_trend_score",
    "htf_4h_range_position",
    "htf_4h_support_resistance_context_score",
]

SCHWAGER_TRAP_INVALIDATION_FEATURE_NAMES = [
    "schwager_false_breakout_risk_score",
    "schwager_bull_trap_risk_score",
    "schwager_bear_trap_risk_score",
    "schwager_failed_breakout_return_inside_range_score",
    "schwager_spike_high_retest_risk_score",
    "schwager_spike_low_retest_risk_score",
    "schwager_stop_hunt_like_move_score",
    "schwager_range_reentry_after_breakout_score",
    "schwager_invalidation_quality_score",
    "schwager_trap_safe_setup_score",
]

BOOK_SETUP_CONTEXT_FEATURE_NAMES = [
    *NISON_CONTEXT_FEATURE_NAMES,
    *ALTUNINA_CONTEXT_FEATURE_NAMES,
    *PATH_CONTEXT_FEATURE_NAMES,
    *SCHWAGER_TRAP_INVALIDATION_FEATURE_NAMES,
    *HTF_CONTEXT_FEATURE_NAMES,
]


class BookSetupContextFeatureBuilder:
    feature_version = "fv4_book_setup_context"

    def build(
        self,
        candles: Sequence[Any],
        index: int,
        base_features: Mapping[str, float],
    ) -> dict[str, float]:
        if index < 0 or index >= len(candles):
            return {name: 0.0 for name in BOOK_SETUP_CONTEXT_FEATURE_NAMES}
        if not base_features:
            return {name: 0.0 for name in BOOK_SETUP_CONTEXT_FEATURE_NAMES}

        atr_value = max(abs(self._feature(base_features, "atr_14")), 0.0)
        trend_up = self._score(self._feature(base_features, "regime_trend_up"))
        trend_down = self._score(self._feature(base_features, "regime_trend_down"))
        trend_range = self._score(self._feature(base_features, "regime_range"))
        trend_strength = self._feature(base_features, "trend_strength")
        trend_slope_short = self._feature(base_features, "trend_slope_short")
        trend_slope_medium = self._feature(base_features, "trend_slope_medium")
        trend_slope_long = self._feature(base_features, "trend_slope_long")
        volume_confirmation = self._score(self._feature(base_features, "volume_confirmation"))
        volume_ratio = max(self._feature(base_features, "volume_ratio_20", 0.0), 0.0)
        volume_zscore = self._feature(base_features, "volume_zscore")
        rsi_value = self._feature(base_features, "rsi_value", self._feature(base_features, "rsi_14", 50.0))
        macd_histogram = self._feature(base_features, "macd_histogram")
        stochastic_k = self._feature(base_features, "stochastic_k")
        roc = self._feature(base_features, "roc")
        momentum = self._feature(base_features, "momentum")
        bollinger_position = self._optional_feature(base_features, "bollinger_position")
        range_position = self._optional_feature(base_features, "range_position")
        volatility_regime_score = self._feature(base_features, "volatility_regime_score")
        ema_stack_bullish = self._score(self._feature(base_features, "ema_stack_bullish"))
        ema_stack_bearish = self._score(self._feature(base_features, "ema_stack_bearish"))
        pullback_to_ema_21 = self._score(self._feature(base_features, "pullback_to_ema_21"))
        bearish_pullback_to_ema_21 = self._score(self._feature(base_features, "bearish_pullback_to_ema_21"))
        breakout_candidate = self._score(self._feature(base_features, "breakout_candidate"))
        breakdown_candidate = self._score(self._feature(base_features, "breakdown_candidate"))
        false_breakout_candidate = self._score(self._feature(base_features, "false_breakout_candidate"))
        false_breakdown_candidate = self._score(self._feature(base_features, "false_breakdown_candidate"))
        near_support = max(
            self._score(self._feature(base_features, "near_support")),
            self._proximity_score(self._optional_feature(base_features, "distance_to_support")),
        )
        near_resistance = max(
            self._score(self._feature(base_features, "near_resistance")),
            self._proximity_score(self._optional_feature(base_features, "distance_to_resistance")),
        )

        doji_score = self._score(self._feature(base_features, "doji_score"))
        hammer_score = self._score(self._feature(base_features, "hammer_score"))
        shooting_star_score = self._score(self._feature(base_features, "shooting_star_score"))
        bullish_engulfing_score = self._score(self._feature(base_features, "bullish_engulfing_score"))
        bearish_engulfing_score = self._score(self._feature(base_features, "bearish_engulfing_score"))
        morning_star_score = self._score(self._feature(base_features, "morning_star_score"))
        evening_star_score = self._score(self._feature(base_features, "evening_star_score"))
        window_gap_score = max(
            self._score(self._feature(base_features, "window_gap_up")),
            self._score(self._feature(base_features, "window_gap_down")),
        )
        pattern_strength = self._score(self._feature(base_features, "pattern_strength_score"))
        pattern_direction_hint = self._feature(base_features, "pattern_direction_hint")
        pattern_requires_confirmation = self._score(
            self._feature(base_features, "pattern_requires_confirmation")
        )
        pattern_context_valid = self._score(self._feature(base_features, "pattern_context_valid"))
        impulse_strength = self._score_from_magnitude(
            self._feature(base_features, "impulse_strength", 0.0),
            scale=2.0,
        )

        nison_reversal_context = self._combine(
            max(
                hammer_score,
                shooting_star_score,
                bullish_engulfing_score,
                bearish_engulfing_score,
                morning_star_score,
                evening_star_score,
            ),
            max(near_support, near_resistance),
            self._score_from_magnitude(trend_slope_medium, scale=1.5),
            pattern_context_valid,
        )
        nison_continuation_context = self._combine(
            max(window_gap_score, breakout_candidate, breakdown_candidate),
            self._score_from_magnitude(trend_slope_medium, scale=1.0),
            volume_confirmation,
            self._score_from_magnitude(trend_strength, scale=0.03),
        )
        nison_indecision_context = self._combine(
            doji_score,
            max(trend_range, self._chop_from_range_position(range_position)),
            1.0 - self._score_from_magnitude(trend_slope_short, scale=1.0),
        )
        nison_confirmation_present = self._combine(
            1.0 - pattern_requires_confirmation,
            volume_confirmation,
            self._direction_alignment_score(pattern_direction_hint, trend_strength),
        )
        nison_pattern_invalidated = self._combine(
            1.0 - pattern_context_valid,
            max(false_breakout_candidate, false_breakdown_candidate),
            self._opposition_score(pattern_direction_hint, trend_strength),
        )
        nison_hammer_after_decline = self._combine(
            hammer_score,
            max(trend_down, self._score_from_magnitude(min(trend_slope_medium, 0.0), scale=1.0)),
            near_support,
        )
        nison_shooting_star_after_advance = self._combine(
            shooting_star_score,
            max(trend_up, self._score_from_magnitude(max(trend_slope_medium, 0.0), scale=1.0)),
            near_resistance,
        )
        nison_engulfing_with_trend_context = max(
            self._combine(bullish_engulfing_score, trend_up, pullback_to_ema_21),
            self._combine(bearish_engulfing_score, trend_down, bearish_pullback_to_ema_21),
        )
        nison_doji_after_impulse = self._combine(doji_score, impulse_strength)
        nison_window_gap_context = self._combine(
            window_gap_score,
            volume_confirmation,
            self._score_from_magnitude(trend_strength, scale=0.03),
        )
        nison_pattern_at_support = self._combine(
            near_support,
            max(hammer_score, bullish_engulfing_score, morning_star_score),
            pattern_context_valid,
        )
        nison_pattern_at_resistance = self._combine(
            near_resistance,
            max(shooting_star_score, bearish_engulfing_score, evening_star_score),
            pattern_context_valid,
        )
        nison_invalidation_distance = self._invalidation_distance_atr(
            base_features=base_features,
            atr_value=atr_value,
            near_support=near_support,
            near_resistance=near_resistance,
        )
        nison_expected_followthrough = self._combine(
            max(nison_reversal_context, nison_continuation_context),
            nison_confirmation_present,
            volume_confirmation,
        )

        indicator_confluence_long = self._combine(
            max(trend_up, ema_stack_bullish),
            self._positive_score(rsi_value - 50.0, scale=15.0),
            self._positive_score(macd_histogram, scale=0.15),
            self._positive_score(stochastic_k - 50.0, scale=25.0),
            self._positive_score(roc, scale=3.0),
            self._positive_score(momentum, scale=max(atr_value, 1.0)),
        )
        indicator_confluence_short = self._combine(
            max(trend_down, ema_stack_bearish),
            self._positive_score(50.0 - rsi_value, scale=15.0),
            self._positive_score(-macd_histogram, scale=0.15),
            self._positive_score(50.0 - stochastic_k, scale=25.0),
            self._positive_score(-roc, scale=3.0),
            self._positive_score(-momentum, scale=max(atr_value, 1.0)),
        )
        range_chop_score = self._combine(
            max(trend_range, self._chop_from_range_position(range_position)),
            self._score(volatility_regime_score / 3.0),
            1.0 - self._score_from_magnitude(trend_slope_medium, scale=1.0),
        )
        volume_confirms_direction = self._combine(
            volume_confirmation,
            self._positive_score(volume_ratio - 1.0, scale=0.8),
            self._positive_score(volume_zscore, scale=2.0),
        )

        path_4_return_atr = self._window_return_atr(candles, index, length=4, atr_value=atr_value)
        path_8_return_atr = self._window_return_atr(candles, index, length=8, atr_value=atr_value)
        path_12_return_atr = self._window_return_atr(candles, index, length=12, atr_value=atr_value)
        path_16_return_atr = self._window_return_atr(candles, index, length=16, atr_value=atr_value)
        path_8_high_low_expansion_atr = self._high_low_expansion_atr(
            candles,
            index,
            length=8,
            atr_value=atr_value,
        )
        path_12_pullback_depth_atr = self._pullback_depth_atr(
            candles,
            index,
            length=12,
            atr_value=atr_value,
        )
        path_12_upper_wick_pressure = self._wick_pressure(candles, index, length=12, upper=True)
        path_12_lower_wick_pressure = self._wick_pressure(candles, index, length=12, upper=False)
        path_12_close_progression_score = self._close_progression_score(candles, index, length=12)
        path_16_trend_consistency_score = self._trend_consistency_score(candles, index, length=16)
        path_16_chop_score = self._chop_score(candles, index, length=16)
        volume_8_confirmation_score = self._volume_confirmation_score(candles, index, length=8)
        volume_16_exhaustion_score = self._volume_exhaustion_score(candles, index, length=16)

        schwager_trap_context = self._trap_invalidation_context(
            candles=candles,
            index=index,
            atr_value=atr_value,
            volume_confirms_direction=volume_confirms_direction,
            range_chop_score=range_chop_score,
            path_16_chop_score=path_16_chop_score,
            path_16_trend_consistency_score=path_16_trend_consistency_score,
        )

        return {
            "nison_reversal_context_score": nison_reversal_context,
            "nison_continuation_context_score": nison_continuation_context,
            "nison_indecision_context_score": nison_indecision_context,
            "nison_confirmation_required_score": pattern_requires_confirmation,
            "nison_confirmation_present_score": nison_confirmation_present,
            "nison_pattern_invalidated_score": nison_pattern_invalidated,
            "nison_hammer_after_decline_score": nison_hammer_after_decline,
            "nison_shooting_star_after_advance_score": nison_shooting_star_after_advance,
            "nison_engulfing_with_trend_context_score": nison_engulfing_with_trend_context,
            "nison_doji_after_impulse_score": nison_doji_after_impulse,
            "nison_window_gap_context_score": nison_window_gap_context,
            "nison_pattern_at_support_score": nison_pattern_at_support,
            "nison_pattern_at_resistance_score": nison_pattern_at_resistance,
            "nison_invalidation_distance_atr": nison_invalidation_distance,
            "nison_expected_followthrough_score": nison_expected_followthrough,
            "alt_trend_continuation_long_score": self._combine(
                max(trend_up, ema_stack_bullish),
                volume_confirms_direction,
                indicator_confluence_long,
            ),
            "alt_trend_continuation_short_score": self._combine(
                max(trend_down, ema_stack_bearish),
                volume_confirms_direction,
                indicator_confluence_short,
            ),
            "alt_pullback_long_score": self._combine(
                max(trend_up, ema_stack_bullish),
                pullback_to_ema_21,
                near_support,
                indicator_confluence_long,
            ),
            "alt_pullback_short_score": self._combine(
                max(trend_down, ema_stack_bearish),
                bearish_pullback_to_ema_21,
                near_resistance,
                indicator_confluence_short,
            ),
            "alt_support_retest_long_score": self._combine(
                near_support,
                max(hammer_score, bullish_engulfing_score),
                indicator_confluence_long,
            ),
            "alt_resistance_rejection_short_score": self._combine(
                near_resistance,
                max(shooting_star_score, bearish_engulfing_score),
                indicator_confluence_short,
            ),
            "alt_breakout_long_score": self._combine(
                breakout_candidate,
                max(trend_up, ema_stack_bullish),
                volume_confirms_direction,
                self._positive_score((bollinger_position or 0.0) - 0.55, scale=0.30),
            ),
            "alt_breakdown_short_score": self._combine(
                breakdown_candidate,
                max(trend_down, ema_stack_bearish),
                volume_confirms_direction,
                self._positive_score(0.45 - (bollinger_position or 0.0), scale=0.30),
            ),
            "alt_false_breakout_risk_score": self._combine(
                max(false_breakout_candidate, false_breakdown_candidate),
                1.0 - volume_confirms_direction,
                range_chop_score,
            ),
            "alt_range_chop_score": range_chop_score,
            "alt_trend_exhaustion_long_risk_score": self._combine(
                max(trend_up, ema_stack_bullish),
                self._positive_score(rsi_value - 68.0, scale=10.0),
                self._positive_score((bollinger_position or 0.0) - 0.85, scale=0.15),
                self._positive_score(path_12_return_atr - 2.0, scale=2.0),
            ),
            "alt_trend_exhaustion_short_risk_score": self._combine(
                max(trend_down, ema_stack_bearish),
                self._positive_score(32.0 - rsi_value, scale=10.0),
                self._positive_score(0.15 - (bollinger_position or 0.0), scale=0.15),
                self._positive_score((-path_12_return_atr) - 2.0, scale=2.0),
            ),
            "alt_volume_confirms_direction_score": volume_confirms_direction,
            "alt_indicator_confluence_long_score": indicator_confluence_long,
            "alt_indicator_confluence_short_score": indicator_confluence_short,
            "alt_no_trade_chop_score": self._combine(range_chop_score, path_16_chop_score),
            "path_4_return_atr": path_4_return_atr,
            "path_8_return_atr": path_8_return_atr,
            "path_12_return_atr": path_12_return_atr,
            "path_16_return_atr": path_16_return_atr,
            "path_8_high_low_expansion_atr": path_8_high_low_expansion_atr,
            "path_12_pullback_depth_atr": path_12_pullback_depth_atr,
            "path_12_upper_wick_pressure": path_12_upper_wick_pressure,
            "path_12_lower_wick_pressure": path_12_lower_wick_pressure,
            "path_12_close_progression_score": path_12_close_progression_score,
            "path_16_trend_consistency_score": path_16_trend_consistency_score,
            "path_16_chop_score": path_16_chop_score,
            "volume_8_confirmation_score": volume_8_confirmation_score,
            "volume_16_exhaustion_score": volume_16_exhaustion_score,
            **schwager_trap_context,
            "htf_1h_trend_score": 0.0,
            "htf_1h_range_position": 0.0,
            "htf_1h_volatility_score": 0.0,
            "htf_4h_trend_score": 0.0,
            "htf_4h_range_position": 0.0,
            "htf_4h_support_resistance_context_score": 0.0,
        }

    def _trap_invalidation_context(
        self,
        *,
        candles: Sequence[Any],
        index: int,
        atr_value: float,
        volume_confirms_direction: float,
        range_chop_score: float,
        path_16_chop_score: float,
        path_16_trend_consistency_score: float,
    ) -> dict[str, float]:
        """Build stronger Schwager-style false-breakout/trap/invalidation features.

        ML38.10.12 change:
        - a trap is no longer just "touched previous high/low and closed inside";
        - risk is concentrated when there is a material level sweep, wick rejection,
          return back inside the prior range, weak confirmation/chop, and optional volume burst;
        - safe setup score rewards clean continuation away from the swept level and penalizes traps.

        Diagnostic-only features. They do not open trades and do not connect to traders-core.
        """
        zero = {name: 0.0 for name in SCHWAGER_TRAP_INVALIDATION_FEATURE_NAMES}
        if atr_value <= 0.0 or index < 1 or index >= len(candles):
            return zero

        previous_window = self._previous_window(candles, index, length=24)
        if not previous_window:
            return zero

        previous_high = max(self._high(candle) for candle in previous_window)
        previous_low = min(self._low(candle) for candle in previous_window)
        previous_volume_avg = mean(self._volume(candle) for candle in previous_window)

        current = candles[index]
        open_value = self._open(current)
        high_value = self._high(current)
        low_value = self._low(current)
        close_value = self._close(current)
        volume_value = self._volume(current)

        candle_range = max(high_value - low_value, 0.0)
        if candle_range <= 0.0:
            return zero

        body_size = abs(close_value - open_value)
        body_to_range = self._score(body_size / candle_range)
        upper_wick_pressure = self._score(
            max(high_value - max(open_value, close_value), 0.0) / candle_range
        )
        lower_wick_pressure = self._score(
            max(min(open_value, close_value) - low_value, 0.0) / candle_range
        )
        close_position = self._score((close_value - low_value) / candle_range)

        breakout_up_atr = max(0.0, high_value - previous_high) / atr_value
        breakout_down_atr = max(0.0, previous_low - low_value) / atr_value
        close_above_previous_high_atr = max(0.0, close_value - previous_high) / atr_value
        close_below_previous_low_atr = max(0.0, previous_low - close_value) / atr_value
        reentry_depth_after_up_atr = max(0.0, previous_high - close_value) / atr_value if high_value > previous_high else 0.0
        reentry_depth_after_down_atr = max(0.0, close_value - previous_low) / atr_value if low_value < previous_low else 0.0

        close_back_inside_after_up = 1.0 if high_value > previous_high and close_value <= previous_high else 0.0
        close_back_inside_after_down = 1.0 if low_value < previous_low and close_value >= previous_low else 0.0
        close_inside_previous_range = 1.0 if previous_low <= close_value <= previous_high else 0.0
        bearish_reversal_close = 1.0 if close_value < open_value else 0.0
        bullish_reversal_close = 1.0 if close_value > open_value else 0.0

        volume_burst_score = 0.0
        if previous_volume_avg > 0.0:
            volume_burst_score = self._positive_score((volume_value / previous_volume_avg) - 1.0, scale=1.0)

        breakout_up_size_score = self._positive_score(breakout_up_atr - 0.05, scale=0.85)
        breakout_down_size_score = self._positive_score(breakout_down_atr - 0.05, scale=0.85)
        up_reentry_depth_score = self._positive_score(reentry_depth_after_up_atr, scale=0.65)
        down_reentry_depth_score = self._positive_score(reentry_depth_after_down_atr, scale=0.65)
        up_continuation_depth_score = self._positive_score(close_above_previous_high_atr, scale=0.85)
        down_continuation_depth_score = self._positive_score(close_below_previous_low_atr, scale=0.85)
        chop_pressure = max(range_chop_score, path_16_chop_score)
        weak_confirmation_pressure = max(chop_pressure, 1.0 - volume_confirms_direction)

        # Core trap signal: sweep level -> reject level -> return inside range.
        # The multiplier makes sustained breakouts with tiny wicks score low even if they touched a level.
        up_rejection_core = self._weighted_combine(
            (close_back_inside_after_up, 0.35),
            (up_reentry_depth_score, 0.25),
            (upper_wick_pressure, 0.20),
            (1.0 - close_position, 0.12),
            (bearish_reversal_close, 0.08),
        )
        down_rejection_core = self._weighted_combine(
            (close_back_inside_after_down, 0.35),
            (down_reentry_depth_score, 0.25),
            (lower_wick_pressure, 0.20),
            (close_position, 0.12),
            (bullish_reversal_close, 0.08),
        )
        up_rejection_gate = max(close_back_inside_after_up, up_reentry_depth_score, upper_wick_pressure)
        down_rejection_gate = max(close_back_inside_after_down, down_reentry_depth_score, lower_wick_pressure)

        false_breakout_up = self._score(
            self._weighted_combine(
                (breakout_up_size_score, 0.18),
                (up_rejection_core, 0.52),
                (weak_confirmation_pressure, 0.16),
                (volume_burst_score, 0.10),
                (body_to_range, 0.04),
            )
            * up_rejection_gate
        )
        false_breakout_down = self._score(
            self._weighted_combine(
                (breakout_down_size_score, 0.18),
                (down_rejection_core, 0.52),
                (weak_confirmation_pressure, 0.16),
                (volume_burst_score, 0.10),
                (body_to_range, 0.04),
            )
            * down_rejection_gate
        )
        false_breakout_risk = max(false_breakout_up, false_breakout_down)

        bull_trap_risk = self._score(
            self._weighted_combine(
                (false_breakout_up, 0.55),
                (up_reentry_depth_score, 0.20),
                (1.0 - close_position, 0.15),
                (upper_wick_pressure, 0.10),
            )
        )
        bear_trap_risk = self._score(
            self._weighted_combine(
                (false_breakout_down, 0.55),
                (down_reentry_depth_score, 0.20),
                (close_position, 0.15),
                (lower_wick_pressure, 0.10),
            )
        )

        spike_high_retest_risk = self._score(
            self._weighted_combine(
                (self._proximity_to_level_score(high_value, previous_high, atr_value, tolerance_atr=0.30), 0.25),
                (upper_wick_pressure, 0.35),
                (close_back_inside_after_up, 0.25),
                (up_reentry_depth_score, 0.15),
            )
        )
        spike_low_retest_risk = self._score(
            self._weighted_combine(
                (self._proximity_to_level_score(low_value, previous_low, atr_value, tolerance_atr=0.30), 0.25),
                (lower_wick_pressure, 0.35),
                (close_back_inside_after_down, 0.25),
                (down_reentry_depth_score, 0.15),
            )
        )
        failed_breakout_return_inside_range = self._score(
            self._weighted_combine(
                (false_breakout_risk, 0.45),
                (close_inside_previous_range, 0.25),
                (max(up_reentry_depth_score, down_reentry_depth_score), 0.20),
                (max(upper_wick_pressure, lower_wick_pressure), 0.10),
            )
        )
        stop_hunt_like_move = self._score(
            self._weighted_combine(
                (false_breakout_risk, 0.45),
                (volume_burst_score, 0.25),
                (max(upper_wick_pressure, lower_wick_pressure), 0.20),
                (max(breakout_up_size_score, breakout_down_size_score), 0.10),
            )
        )
        range_reentry_after_breakout = self._score(
            self._weighted_combine(
                (failed_breakout_return_inside_range, 0.45),
                (close_inside_previous_range, 0.20),
                (chop_pressure, 0.20),
                (max(close_back_inside_after_up, close_back_inside_after_down), 0.15),
            )
        )

        sustained_up_breakout = self._weighted_combine(
            (breakout_up_size_score, 0.20),
            (up_continuation_depth_score, 0.30),
            (close_position, 0.20),
            (1.0 - upper_wick_pressure, 0.15),
            (volume_confirms_direction, 0.15),
        )
        sustained_down_breakout = self._weighted_combine(
            (breakout_down_size_score, 0.20),
            (down_continuation_depth_score, 0.30),
            (1.0 - close_position, 0.20),
            (1.0 - lower_wick_pressure, 0.15),
            (volume_confirms_direction, 0.15),
        )
        continuation_quality = max(
            sustained_up_breakout,
            sustained_down_breakout,
            path_16_trend_consistency_score,
        )
        trap_risk = max(
            false_breakout_risk,
            bull_trap_risk,
            bear_trap_risk,
            failed_breakout_return_inside_range,
            stop_hunt_like_move,
            range_reentry_after_breakout,
        )
        invalidation_quality = self._score(
            self._weighted_combine(
                (1.0 - trap_risk, 0.45),
                (continuation_quality, 0.25),
                (volume_confirms_direction, 0.15),
                (1.0 - chop_pressure, 0.15),
            )
        )
        trap_safe_setup = self._score(
            self._weighted_combine(
                (invalidation_quality, 0.45),
                (continuation_quality, 0.25),
                (volume_confirms_direction, 0.15),
                (1.0 - max(false_breakout_risk, stop_hunt_like_move), 0.15),
            )
        )

        return {
            "schwager_false_breakout_risk_score": false_breakout_risk,
            "schwager_bull_trap_risk_score": bull_trap_risk,
            "schwager_bear_trap_risk_score": bear_trap_risk,
            "schwager_failed_breakout_return_inside_range_score": failed_breakout_return_inside_range,
            "schwager_spike_high_retest_risk_score": spike_high_retest_risk,
            "schwager_spike_low_retest_risk_score": spike_low_retest_risk,
            "schwager_stop_hunt_like_move_score": stop_hunt_like_move,
            "schwager_range_reentry_after_breakout_score": range_reentry_after_breakout,
            "schwager_invalidation_quality_score": invalidation_quality,
            "schwager_trap_safe_setup_score": trap_safe_setup,
        }

    def _feature(self, base_features: Mapping[str, float], name: str, default: float = 0.0) -> float:
        value = base_features.get(name, default)
        try:
            return float(value) if value is not None else default
        except (TypeError, ValueError):
            return default

    def _optional_feature(self, base_features: Mapping[str, float], name: str) -> float | None:
        if name not in base_features:
            return None
        value = base_features.get(name)
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _score(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    def _combine(self, *values: float) -> float:
        normalized = [self._score(value) for value in values]
        if not normalized:
            return 0.0
        return sum(normalized) / len(normalized)

    def _weighted_combine(self, *weighted_values: tuple[float, float]) -> float:
        total_weight = sum(max(float(weight), 0.0) for _, weight in weighted_values)
        if total_weight <= 0.0:
            return 0.0
        weighted_sum = sum(
            self._score(float(value)) * max(float(weight), 0.0)
            for value, weight in weighted_values
        )
        return self._score(weighted_sum / total_weight)

    def _proximity_score(self, distance_atr: float | None) -> float:
        if distance_atr is None:
            return 0.0
        if distance_atr <= 0.0:
            return 1.0
        if distance_atr >= 1.5:
            return 0.0
        return self._score(1.0 - (distance_atr / 1.5))

    def _score_from_magnitude(self, value: float, *, scale: float) -> float:
        if scale <= 0.0:
            return 0.0
        return self._score(abs(value) / scale)

    def _positive_score(self, value: float, *, scale: float) -> float:
        if scale <= 0.0 or value <= 0.0:
            return 0.0
        return self._score(value / scale)

    def _direction_alignment_score(self, pattern_direction_hint: float, trend_strength: float) -> float:
        pattern_sign = self._sign(pattern_direction_hint)
        trend_sign = self._sign(trend_strength)
        if pattern_sign == 0.0:
            return 0.0
        if pattern_sign == trend_sign:
            return 1.0
        if trend_sign == 0.0:
            return 0.5
        return 0.0

    def _opposition_score(self, pattern_direction_hint: float, trend_strength: float) -> float:
        pattern_sign = self._sign(pattern_direction_hint)
        trend_sign = self._sign(trend_strength)
        if pattern_sign == 0.0 or trend_sign == 0.0:
            return 0.0
        return 1.0 if pattern_sign != trend_sign else 0.0

    def _invalidation_distance_atr(
        self,
        *,
        base_features: Mapping[str, float],
        atr_value: float,
        near_support: float,
        near_resistance: float,
    ) -> float:
        if atr_value <= 0.0:
            return 0.0
        support_distance = self._feature(base_features, "distance_to_support")
        resistance_distance = self._feature(base_features, "distance_to_resistance")
        candidates: list[float] = []
        if near_support > 0.0 and support_distance > 0.0:
            candidates.append(support_distance)
        if near_resistance > 0.0 and resistance_distance > 0.0:
            candidates.append(resistance_distance)
        if candidates:
            return max(0.0, min(candidates))
        if support_distance > 0.0 and resistance_distance > 0.0:
            return max(0.0, min(support_distance, resistance_distance))
        return max(0.0, support_distance, resistance_distance)

    @staticmethod
    def _sign(value: float) -> float:
        if value > 0.0:
            return 1.0
        if value < 0.0:
            return -1.0
        return 0.0

    def _window_return_atr(
        self,
        candles: Sequence[Any],
        index: int,
        *,
        length: int,
        atr_value: float,
    ) -> float:
        window = self._window(candles, index, length)
        if window is None or atr_value <= 0.0:
            return 0.0
        first_close = self._close(window[0])
        last_close = self._close(window[-1])
        return (last_close - first_close) / atr_value

    def _high_low_expansion_atr(
        self,
        candles: Sequence[Any],
        index: int,
        *,
        length: int,
        atr_value: float,
    ) -> float:
        window = self._window(candles, index, length)
        if window is None or atr_value <= 0.0:
            return 0.0
        highest = max(self._high(candle) for candle in window)
        lowest = min(self._low(candle) for candle in window)
        return (highest - lowest) / atr_value

    def _pullback_depth_atr(
        self,
        candles: Sequence[Any],
        index: int,
        *,
        length: int,
        atr_value: float,
    ) -> float:
        window = self._window(candles, index, length)
        if window is None or atr_value <= 0.0:
            return 0.0
        closes = [self._close(candle) for candle in window]
        highs = [self._high(candle) for candle in window]
        lows = [self._low(candle) for candle in window]
        net_move = closes[-1] - closes[0]
        if net_move >= 0.0:
            return max(0.0, max(highs) - closes[-1]) / atr_value
        return max(0.0, closes[-1] - min(lows)) / atr_value

    def _wick_pressure(
        self,
        candles: Sequence[Any],
        index: int,
        *,
        length: int,
        upper: bool,
    ) -> float:
        window = self._window(candles, index, length)
        if window is None:
            return 0.0
        pressures: list[float] = []
        for candle in window:
            high = self._high(candle)
            low = self._low(candle)
            open_value = self._open(candle)
            close_value = self._close(candle)
            candle_range = high - low
            if candle_range <= 0.0:
                continue
            if upper:
                wick = max(high - max(open_value, close_value), 0.0)
            else:
                wick = max(min(open_value, close_value) - low, 0.0)
            pressures.append(wick / candle_range)
        return float(mean(pressures)) if pressures else 0.0

    def _close_progression_score(
        self,
        candles: Sequence[Any],
        index: int,
        *,
        length: int,
    ) -> float:
        window = self._window(candles, index, length)
        if window is None:
            return 0.0
        closes = [self._close(candle) for candle in window]
        net_sign = self._sign(closes[-1] - closes[0])
        if net_sign == 0.0:
            return 0.0
        aligned = 0
        total = 0
        for current in range(1, len(closes)):
            delta_sign = self._sign(closes[current] - closes[current - 1])
            if delta_sign == 0.0:
                continue
            total += 1
            if delta_sign == net_sign:
                aligned += 1
        return 0.0 if total == 0 else aligned / total

    def _trend_consistency_score(
        self,
        candles: Sequence[Any],
        index: int,
        *,
        length: int,
    ) -> float:
        window = self._window(candles, index, length)
        if window is None:
            return 0.0
        closes = [self._close(candle) for candle in window]
        directions = [self._sign(closes[i] - closes[i - 1]) for i in range(1, len(closes))]
        non_zero = [direction for direction in directions if direction != 0.0]
        if not non_zero:
            return 0.0
        majority = 1.0 if sum(non_zero) >= 0.0 else -1.0
        aligned = sum(int(direction == majority) for direction in non_zero)
        return aligned / len(non_zero)

    def _chop_score(
        self,
        candles: Sequence[Any],
        index: int,
        *,
        length: int,
    ) -> float:
        window = self._window(candles, index, length)
        if window is None:
            return 0.0
        closes = [self._close(candle) for candle in window]
        net_move = abs(closes[-1] - closes[0])
        path_move = sum(abs(closes[i] - closes[i - 1]) for i in range(1, len(closes)))
        if path_move <= 0.0:
            return 0.0
        return self._score(1.0 - min(net_move / path_move, 1.0))

    def _volume_confirmation_score(
        self,
        candles: Sequence[Any],
        index: int,
        *,
        length: int,
    ) -> float:
        window = self._window(candles, index, length)
        if window is None:
            return 0.0
        volumes = [self._volume(candle) for candle in window]
        closes = [self._close(candle) for candle in window]
        avg_volume = mean(volumes[:-1]) if len(volumes) > 1 else volumes[-1]
        if avg_volume <= 0.0:
            return 0.0
        net_move = closes[-1] - closes[0]
        last_move = closes[-1] - closes[-2] if len(closes) > 1 else 0.0
        alignment = 1.0 if self._sign(net_move) == self._sign(last_move) else 0.0
        volume_boost = self._positive_score((volumes[-1] / avg_volume) - 1.0, scale=0.8)
        return self._combine(alignment, volume_boost)

    def _volume_exhaustion_score(
        self,
        candles: Sequence[Any],
        index: int,
        *,
        length: int,
    ) -> float:
        window = self._window(candles, index, length)
        if window is None or len(window) < 4:
            return 0.0
        split_index = max(len(window) - 4, 1)
        early = window[:split_index]
        late = window[split_index:]
        early_volume = mean(self._volume(candle) for candle in early)
        late_volume = mean(self._volume(candle) for candle in late)
        price_extension = abs(self._close(window[-1]) - self._close(window[0]))
        late_extension = abs(self._close(window[-1]) - self._close(window[-4]))
        if early_volume <= 0.0 or price_extension <= 0.0:
            return 0.0
        volume_surge = self._positive_score((late_volume / early_volume) - 1.0, scale=1.0)
        late_progress = min(late_extension / price_extension, 1.0)
        return self._combine(volume_surge, 1.0 - late_progress)

    def _chop_from_range_position(self, range_position: float | None) -> float:
        if range_position is None:
            return 0.0
        return self._score(1.0 - abs((range_position - 0.5) * 2.0))

    @staticmethod
    def _window(candles: Sequence[Any], index: int, length: int) -> list[Any] | None:
        start = index - length + 1
        if start < 0:
            return None
        return list(candles[start : index + 1])

    @staticmethod
    def _previous_window(candles: Sequence[Any], index: int, length: int) -> list[Any] | None:
        end = index
        start = max(0, end - length)
        if start >= end:
            return None
        return list(candles[start:end])

    def _proximity_to_level_score(
        self,
        value: float,
        level: float,
        atr_value: float,
        *,
        tolerance_atr: float,
    ) -> float:
        if atr_value <= 0.0 or tolerance_atr <= 0.0:
            return 0.0
        distance_atr = abs(value - level) / atr_value
        if distance_atr >= tolerance_atr:
            return 0.0
        return self._score(1.0 - (distance_atr / tolerance_atr))

    @staticmethod
    def _open(candle: Any) -> float:
        return float(getattr(candle, "open", 0.0) or 0.0)

    @staticmethod
    def _high(candle: Any) -> float:
        return float(getattr(candle, "high", 0.0) or 0.0)

    @staticmethod
    def _low(candle: Any) -> float:
        return float(getattr(candle, "low", 0.0) or 0.0)

    @staticmethod
    def _close(candle: Any) -> float:
        return float(getattr(candle, "close", 0.0) or 0.0)

    @staticmethod
    def _volume(candle: Any) -> float:
        return float(getattr(candle, "volume", 0.0) or 0.0)
