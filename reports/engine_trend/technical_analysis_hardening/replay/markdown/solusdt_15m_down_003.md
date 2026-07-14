# Window: solusdt_15m_down_003

Reference: EXPECTED_DOWN; period: 2026-02-05T00:00:00+00:00 — 2026-02-05T23:45:00+00:00.

## UnifiedMarketContext

- trend structure: BEARISH_STRUCTURE
- shared swing points: [{"index": 5, "timestamp": "2026-02-05T01:15:00+00:00", "price": 90.52, "point_type": "LOW"}, {"index": 6, "timestamp": "2026-02-05T01:30:00+00:00", "price": 92.89, "point_type": "HIGH"}, {"index": 13, "timestamp": "2026-02-05T03:15:00+00:00", "price": 90.24, "point_type": "LOW"}, {"index": 22, "timestamp": "2026-02-05T05:30:00+00:00", "price": 92.11, "point_type": "HIGH"}, {"index": 27, "timestamp": "2026-02-05T06:45:00+00:00", "price": 89.68, "point_type": "LOW"}, {"index": 37, "timestamp": "2026-02-05T09:15:00+00:00", "price": 93.43, "point_type": "HIGH"}, {"index": 55, "timestamp": "2026-02-05T13:45:00+00:00", "price": 88.2, "point_type": "LOW"}, {"index": 58, "timestamp": "2026-02-05T14:30:00+00:00", "price": 91.43, "point_type": "HIGH"}, {"index": 62, "timestamp": "2026-02-05T15:30:00+00:00", "price": 83.44, "point_type": "LOW"}, {"index": 67, "timestamp": "2026-02-05T16:45:00+00:00", "price": 86.2, "point_type": "HIGH"}, {"index": 74, "timestamp": "2026-02-05T18:30:00+00:00", "price": 81.21, "point_type": "LOW"}, {"index": 76, "timestamp": "2026-02-05T19:00:00+00:00", "price": 83.31, "point_type": "HIGH"}, {"index": 89, "timestamp": "2026-02-05T22:15:00+00:00", "price": 77.6, "point_type": "LOW"}, {"index": 92, "timestamp": "2026-02-05T23:00:00+00:00", "price": 81.63, "point_type": "HIGH"}]
- range: {"support_zone": null, "resistance_zone": {"zone_type": "RESISTANCE", "lower_price": 83.31, "upper_price": 83.44, "mid_price": 83.375, "touch_count": 2, "source_indexes": [62, 76], "zone_width": 0.12999999999999545, "zone_width_ratio": 0.001559220389805043, "formed_at_index": 76, "first_touch_index": 62, "last_touch_index": 76, "source_point_types": ["LOW", "HIGH"], "original_zone_type": "RESISTANCE", "current_zone_type": "RESISTANCE", "role_changed_at_index": null, "is_significant_single_extreme": false, "positional_zone_type": "RESISTANCE"}, "is_detected": false, "lower_boundary": null, "upper_boundary": null, "midline": null, "width": 0.0, "width_ratio": 0.0, "touch_count": 2, "inside_close_ratio": 0.0, "formed_at_index": 0, "first_touch_index": 0, "duration_candles": 0, "boundary_alternation_count": 0}
- active support/resistance zones: [{"zone_type": "SUPPORT", "lower_price": 77.6, "upper_price": 77.6, "mid_price": 77.6, "touch_count": 1, "source_indexes": [89], "zone_width": 0.0, "zone_width_ratio": 0.0, "formed_at_index": 89, "first_touch_index": 89, "last_touch_index": 89, "source_point_types": ["LOW"], "original_zone_type": "SUPPORT", "current_zone_type": "SUPPORT", "role_changed_at_index": null, "is_significant_single_extreme": true, "positional_zone_type": "SUPPORT"}, {"zone_type": "RESISTANCE", "lower_price": 83.31, "upper_price": 83.44, "mid_price": 83.375, "touch_count": 2, "source_indexes": [62, 76], "zone_width": 0.12999999999999545, "zone_width_ratio": 0.001559220389805043, "formed_at_index": 76, "first_touch_index": 62, "last_touch_index": 76, "source_point_types": ["LOW", "HIGH"], "original_zone_type": "RESISTANCE", "current_zone_type": "RESISTANCE", "role_changed_at_index": null, "is_significant_single_extreme": false, "positional_zone_type": "RESISTANCE"}, {"zone_type": "RESISTANCE", "lower_price": 93.43, "upper_price": 93.43, "mid_price": 93.43, "touch_count": 1, "source_indexes": [37], "zone_width": 0.0, "zone_width_ratio": 0.0, "formed_at_index": 37, "first_touch_index": 37, "last_touch_index": 37, "source_point_types": ["HIGH"], "original_zone_type": "RESISTANCE", "current_zone_type": "RESISTANCE", "role_changed_at_index": null, "is_significant_single_extreme": true, "positional_zone_type": "RESISTANCE"}]
- breakout state: {"direction": "NONE", "status": "NO_BREAKOUT", "breakout_index": null, "boundary_price": null, "breakout_close": null, "distance_ratio": 0.0, "returned_to_range": false, "follow_through_count": 0, "evidence": [], "analysis_start_index": 0, "confirmation_method": "NONE", "confirmation_close_count": 0, "extreme_index": null, "extreme_price": null, "maximum_distance_ratio": 0.0, "return_index": null, "return_depth_ratio": 0.0, "reversal_candle_count": 0, "false_breakout_confirmation": "NONE", "false_breakout_invalidated": false}

## Contextual events

- candle event: SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED; trend context before event: BEARISH_STRUCTURE; causal zone available at event: False (NO_CAUSAL_ZONE); follow-through: PENDING; invalidation: {'invalidated': False, 'event_status': 'CONTEXT_REJECTED', 'reason_codes': ['PATTERN_TREND_CONTEXT_REJECTED']}
- candle event: BEARISH_ENGULFING_CONTEXT; trend context before event: BEARISH_STRUCTURE; causal zone available at event: False (NO_CAUSAL_ZONE); follow-through: CONFIRMED; invalidation: {'invalidated': False, 'event_status': 'CONTEXT_REJECTED', 'reason_codes': ['PATTERN_TREND_CONTEXT_REJECTED']}
- candle event: BULLISH_ENGULFING_CONTEXT; trend context before event: BEARISH_STRUCTURE; causal zone available at event: False (NO_CAUSAL_ZONE); follow-through: PENDING; invalidation: {'invalidated': False, 'event_status': 'CANDIDATE', 'reason_codes': []}
- candle event: BEARISH_ENGULFING_CONTEXT; trend context before event: BEARISH_STRUCTURE; causal zone available at event: False (NO_CAUSAL_ZONE); follow-through: PENDING; invalidation: {'invalidated': False, 'event_status': 'CONTEXT_REJECTED', 'reason_codes': ['PATTERN_TREND_CONTEXT_REJECTED']}
- candle event: BULLISH_ENGULFING_CONTEXT; trend context before event: BEARISH_STRUCTURE; causal zone available at event: False (NO_CAUSAL_ZONE); follow-through: INVALIDATED; invalidation: {'invalidated': True, 'event_status': 'INVALIDATED', 'reason_codes': ['PATTERN_FOLLOW_THROUGH_INVALIDATED']}
- candle event: INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED; trend context before event: BEARISH_STRUCTURE; causal zone available at event: False (NO_CAUSAL_ZONE); follow-through: PENDING; invalidation: {'invalidated': False, 'event_status': 'CANDIDATE', 'reason_codes': []}
- candle event: BULLISH_HARAMI_CONTEXT; trend context before event: BEARISH_STRUCTURE; causal zone available at event: False (NO_CAUSAL_ZONE); follow-through: INVALIDATED; invalidation: {'invalidated': True, 'event_status': 'INVALIDATED', 'reason_codes': ['PATTERN_FOLLOW_THROUGH_INVALIDATED']}
- candle event: TWEEZERS_BOTTOM_CONTEXT_REQUIRED; trend context before event: BEARISH_STRUCTURE; causal zone available at event: False (NO_CAUSAL_ZONE); follow-through: PENDING; invalidation: {'invalidated': False, 'event_status': 'CANDIDATE', 'reason_codes': []}
- candle event: TWEEZERS_TOP_CONTEXT_REQUIRED; trend context before event: BEARISH_STRUCTURE; causal zone available at event: False (NO_CAUSAL_ZONE); follow-through: PENDING; invalidation: {'invalidated': False, 'event_status': 'CONTEXT_REJECTED', 'reason_codes': ['PATTERN_TREND_CONTEXT_REJECTED']}
- candle event: TWEEZERS_BOTTOM_CONTEXT_REQUIRED; trend context before event: BEARISH_STRUCTURE; causal zone available at event: False (NO_CAUSAL_ZONE); follow-through: PENDING; invalidation: {'invalidated': False, 'event_status': 'CANDIDATE', 'reason_codes': []}
- candle event: TWEEZERS_BOTTOM_CONTEXT_REQUIRED; trend context before event: BEARISH_STRUCTURE; causal zone available at event: False (NO_CAUSAL_ZONE); follow-through: PENDING; invalidation: {'invalidated': False, 'event_status': 'CANDIDATE', 'reason_codes': []}

## Hypotheses

- CONFIRMED: [{"hypothesis_id": "hypothesis:down_continuation", "hypothesis_type": "DOWN_CONTINUATION", "direction": "BEARISH", "status": "CONFIRMED", "score": 0.7998530334437659, "trigger_index": 72, "confirmation_index": null, "supporting_event_ids": [], "reason_codes": ["HYPOTHESIS_STRUCTURE_ALIGNED", "HYPOTHESIS_TECHNICAL_INDICATORS_ALIGNED", "HYPOTHESIS_DECISION_WINDOW_PROGRESS_ALIGNED"]}]
- PENDING: none
- INVALIDATED: none
- CANCELLED: none
- CONFLICTED: none

Note: HypothesisStatus.CANCELLED is not implemented; CONFLICTED is reported separately.

## Composer

- selected hypothesis: {"hypothesis_id": "hypothesis:down_continuation", "hypothesis_type": "DOWN_CONTINUATION", "direction": "BEARISH", "status": "CONFIRMED", "score": 0.7998530334437659, "trigger_index": 72, "confirmation_index": null, "supporting_event_ids": [], "reason_codes": ["HYPOTHESIS_STRUCTURE_ALIGNED", "HYPOTHESIS_TECHNICAL_INDICATORS_ALIGNED", "HYPOTHESIS_DECISION_WINDOW_PROGRESS_ALIGNED"]}
- regime: DOWN
- confidence: 0.8665197001104326
- reason: {"status": "COMPOSED", "decision_source": "DIRECTIONAL_CONTEXT", "fallback_reason": null, "reason_codes": ["COMPOSER_MATRIX_READY", "COMPOSER_INPUT_VALID", "COMPOSER_CONTEXT_LINKED_HYPOTHESES_READY", "COMPOSER_DOMINANT_DOWN_CONTINUATION", "COMPOSER_DOWN_REGIME_SELECTED", "COMPOSER_NO_TRADING_ACTION"]}

## Old → new

UNKNOWN (0.3) → DOWN (0.8665197001104326); MATCH.
