# ENGINE-TREND-19 SOLUSDT 15m — live/replay check

Generated: `2026-07-13T17:30:04.359085Z`. Audit/check-only; current engine code and defaults were used unchanged.

## Formal answer

- Regime: **FLAT**; confidence: `0.689744`; source: `RANGE_CONTEXT`.
- Selected hypothesis: `CONFIRMED_RANGE`.
- Short reason: `COMPOSER_CONTEXT_LINKED_HYPOTHESES_READY, COMPOSER_DOMINANT_CONFIRMED_RANGE, COMPOSER_FLAT_REGIME_SELECTED, COMPOSER_NO_TRADING_ACTION`.
- Data source / quality: `BINANCE_ONLY` / `PASS`.
- Safety violation: `False`.

## Window sweep

| window | actual_start | actual_end | candles | quality | regime | hypothesis | source | confidence | confirmed | pending | conflicted | safety | reason |
|---|---|---|---:|---|---|---|---|---:|---:|---:|---:|---|---|
| SOLUSDT_2026_07_08_06_00 | 2026-07-07T06:15:00Z | 2026-07-08T06:00:00Z | 96 | PASS | DOWN | DOWN_CONTINUATION | DIRECTIONAL_CONTEXT | 0.853230 | 1 | 1 | 0 | False | COMPOSER_CONTEXT_LINKED_HYPOTHESES_READY, COMPOSER_DOMINANT_DOWN_CONTINUATION, COMPOSER_DOWN_REGIME_SELECTED, COMPOSER_NO_TRADING_ACTION |
| SOLUSDT_2026_07_08_11_30 | 2026-07-07T11:45:00Z | 2026-07-08T11:30:00Z | 96 | PASS | UNKNOWN | None | COMPOSER_SAFETY | 0.250000 | 0 | 1 | 0 | False | COMPOSER_NO_CONFIRMED_HYPOTHESIS, COMPOSER_CONSERVATIVE_FALLBACK_UNKNOWN, COMPOSER_UNKNOWN_REGIME_SELECTED, COMPOSER_NO_TRADING_ACTION |
| SOLUSDT_2026_07_08_18_30 | 2026-07-07T18:45:00Z | 2026-07-08T18:30:00Z | 96 | PASS | UNKNOWN | None | COMPOSER_SAFETY | 0.350000 | 2 | 0 | 0 | False | COMPOSER_CONTEXT_LINKED_HYPOTHESES_READY, COMPOSER_UNRESOLVED_CONFIRMED_HYPOTHESIS_CONFLICT, COMPOSER_UNKNOWN_REGIME_SELECTED, COMPOSER_NO_TRADING_ACTION |
| SOLUSDT_2026_07_08_23_45 | 2026-07-08T00:00:00Z | 2026-07-08T23:45:00Z | 96 | PASS | FLAT | CONFIRMED_RANGE | RANGE_CONTEXT | 0.689744 | 1 | 0 | 0 | False | COMPOSER_CONTEXT_LINKED_HYPOTHESES_READY, COMPOSER_DOMINANT_CONFIRMED_RANGE, COMPOSER_FLAT_REGIME_SELECTED, COMPOSER_NO_TRADING_ACTION |

## Why the model returned this regime

```json
{
  "selected_hypothesis": {
    "hypothesis_id": "hypothesis:confirmed_range",
    "hypothesis_type": "CONFIRMED_RANGE",
    "direction": "FLAT",
    "status": "CONFIRMED",
    "score": 0.6230769230769231,
    "trigger_index": 92,
    "confirmation_index": null,
    "supporting_event_ids": [],
    "reason_codes": [
      "HYPOTHESIS_RANGE_STRUCTURE_CONFIRMED",
      "HYPOTHESIS_SECONDARY_FLAT_CONTEXT_CONFIRMED",
      "HYPOTHESIS_RANGE_BOUNDARIES_HELD"
    ]
  },
  "candidate_scores": {
    "up_score": 0.0,
    "down_score": 0.0,
    "flat_score": 0.6230769230769231,
    "unknown_score": 0.0,
    "selected_regime": "FLAT",
    "confidence": 0.6897435897435897,
    "confidence_level": "MEDIUM",
    "reason_codes": [
      "COMPOSER_CONTEXT_LINKED_HYPOTHESES_READY",
      "COMPOSER_DOMINANT_CONFIRMED_RANGE",
      "COMPOSER_FLAT_REGIME_SELECTED"
    ],
    "composer_trace": {
      "raw_scores": {
        "UP": 0.0,
        "DOWN": 0.0,
        "FLAT": 0.6230769230769231,
        "UNKNOWN": 0.0
      },
      "clamped_scores": {
        "UP": 0.0,
        "DOWN": 0.0,
        "FLAT": 0.6230769230769231,
        "UNKNOWN": 0.0
      },
      "ranking_before_clamp": [
        {
          "regime": "FLAT",
          "score": 0.6230769230769231
        },
        {
          "regime": "UP",
          "score": 0.0
        },
        {
          "regime": "DOWN",
          "score": 0.0
        },
        {
          "regime": "UNKNOWN",
          "score": 0.0
        }
      ],
      "ranking_after_clamp": [
        {
          "regime": "FLAT",
          "score": 0.6230769230769231
        },
        {
          "regime": "UP",
          "score": 0.0
        },
        {
          "regime": "DOWN",
          "score": 0.0
        },
        {
          "regime": "UNKNOWN",
          "score": 0.0
        }
      ],
      "selected_regime_before_fallback": "FLAT",
      "selected_regime_after_fallback": "FLAT",
      "fallback_triggered": false,
      "fallback_reason": null,
      "confidence_path": [
        "CLAMPED_WINNER:FLAT:0.6230769230769231",
        "WEIGHTED_CONFIDENCE:0.6897435897435897",
        "FINAL:0.6897435897435897"
      ],
      "confidence_final": 0.6897435897435897
    }
  },
  "composer_reasons": [
    "COMPOSER_MATRIX_READY",
    "COMPOSER_INPUT_VALID",
    "COMPOSER_CONTEXT_LINKED_HYPOTHESES_READY",
    "COMPOSER_DOMINANT_CONFIRMED_RANGE",
    "COMPOSER_FLAT_REGIME_SELECTED",
    "COMPOSER_NO_TRADING_ACTION"
  ],
  "hypothesis_presence": {
    "DOWN_CONTINUATION": {
      "exists": false,
      "status": null,
      "reason_codes": []
    },
    "BEARISH_REVERSAL": {
      "exists": false,
      "status": null,
      "reason_codes": []
    },
    "CONFIRMED_RANGE": {
      "exists": true,
      "status": "CONFIRMED",
      "reason_codes": [
        "HYPOTHESIS_RANGE_STRUCTURE_CONFIRMED",
        "HYPOTHESIS_SECONDARY_FLAT_CONTEXT_CONFIRMED",
        "HYPOTHESIS_RANGE_BOUNDARIES_HELD"
      ]
    },
    "BULLISH_REVERSAL": {
      "exists": false,
      "status": null,
      "reason_codes": []
    }
  }
}
```

## Technical indicators and votes

```json
{
  "decision_candle": "2026-07-08T23:45:00Z",
  "decision_close": 77.83,
  "values": {
    "sma_20": 77.34649999999999,
    "sma_50": 77.221,
    "sma_99": null,
    "ema_12": 77.48961209536871,
    "ema_26": 77.37016424496714,
    "rsi_14": 64.97934189213115,
    "macd": 0.11944785040157058,
    "macd_signal": 0.06154669046828092,
    "macd_histogram": 0.057901159933289655,
    "atr_14": 0.22357142857142825,
    "atr_ratio": 0.0028725610763385362,
    "adx_14": 21.062682186108823,
    "bollinger_mid": 77.34649999999999,
    "bollinger_upper": 77.78180563975211,
    "bollinger_lower": 76.91119436024788,
    "vwap": 77.90325949141022
  },
  "price_relations": {
    "sma_20": "PRICE_ABOVE_SMA_20",
    "sma_50": "PRICE_ABOVE_SMA_50",
    "sma_99": "SMA_99_UNAVAILABLE",
    "ema_12": "PRICE_ABOVE_EMA_12",
    "ema_26": "PRICE_ABOVE_EMA_26",
    "vwap": "PRICE_BELOW_VWAP"
  },
  "bollinger_position": "ABOVE_UPPER",
  "technical_votes": {
    "bullish_methods_count": 4,
    "bearish_methods_count": 1,
    "neutral_or_conflicted_count": 1,
    "supported_up": [
      "INDICATOR_EMA_BULLISH",
      "INDICATOR_MACD_BULLISH",
      "INDICATOR_RSI_BULLISH",
      "INDICATOR_PRICE_ABOVE_SMA20"
    ],
    "supported_down": [
      "INDICATOR_PRICE_BELOW_VWAP"
    ],
    "blocked_direction": [
      "INDICATOR_ADX_TRENDING"
    ],
    "formal_direction": "BULLISH"
  },
  "engine_raw_indicator_context": {
    "available": true,
    "sma_20": 77.34649999999999,
    "ema_12": 77.48961209536871,
    "ema_26": 77.37016424496714,
    "rsi_14": 64.97934189213115,
    "macd": 0.11944785040157058,
    "macd_signal": 0.06154669046828092,
    "atr_14": 0.22357142857142825,
    "atr_ratio": 0.0028725610763385362,
    "adx_14": 21.062682186108823,
    "bollinger_mid": 77.34649999999999,
    "bollinger_upper": 77.78180563975211,
    "bollinger_lower": 76.91119436024788,
    "vwap": 77.90325949141022,
    "direction": "BULLISH",
    "bullish_votes": 4,
    "bearish_votes": 1,
    "reason_codes": [
      "INDICATOR_EMA_BULLISH",
      "INDICATOR_MACD_BULLISH",
      "INDICATOR_RSI_BULLISH",
      "INDICATOR_PRICE_ABOVE_SMA20",
      "INDICATOR_PRICE_BELOW_VWAP",
      "INDICATOR_ADX_TRENDING"
    ]
  }
}
```

## Structure/context diagnostics

```json
{
  "swing_high_swing_low_and_labels": [
    {
      "index": 10,
      "timestamp": "2026-07-08T02:30:00Z",
      "price": 78.22,
      "point_type": "LOW",
      "structure_label": "LOW"
    },
    {
      "index": 12,
      "timestamp": "2026-07-08T03:00:00Z",
      "price": 79.34,
      "point_type": "HIGH",
      "structure_label": "HIGH"
    },
    {
      "index": 16,
      "timestamp": "2026-07-08T04:00:00Z",
      "price": 78.57,
      "point_type": "LOW",
      "structure_label": "HL"
    },
    {
      "index": 18,
      "timestamp": "2026-07-08T04:30:00Z",
      "price": 78.93,
      "point_type": "HIGH",
      "structure_label": "LH"
    },
    {
      "index": 28,
      "timestamp": "2026-07-08T07:00:00Z",
      "price": 77.8,
      "point_type": "LOW",
      "structure_label": "LL"
    },
    {
      "index": 32,
      "timestamp": "2026-07-08T08:00:00Z",
      "price": 78.43,
      "point_type": "HIGH",
      "structure_label": "LH"
    },
    {
      "index": 34,
      "timestamp": "2026-07-08T08:30:00Z",
      "price": 76.9,
      "point_type": "LOW",
      "structure_label": "LL"
    },
    {
      "index": 38,
      "timestamp": "2026-07-08T09:30:00Z",
      "price": 77.49,
      "point_type": "HIGH",
      "structure_label": "LH"
    },
    {
      "index": 40,
      "timestamp": "2026-07-08T10:00:00Z",
      "price": 76.94,
      "point_type": "LOW",
      "structure_label": "HL"
    },
    {
      "index": 42,
      "timestamp": "2026-07-08T10:30:00Z",
      "price": 77.5,
      "point_type": "HIGH",
      "structure_label": "HH"
    },
    {
      "index": 45,
      "timestamp": "2026-07-08T11:15:00Z",
      "price": 77.08,
      "point_type": "LOW",
      "structure_label": "HL"
    },
    {
      "index": 46,
      "timestamp": "2026-07-08T11:30:00Z",
      "price": 77.71,
      "point_type": "HIGH",
      "structure_label": "HH"
    },
    {
      "index": 53,
      "timestamp": "2026-07-08T13:15:00Z",
      "price": 76.64,
      "point_type": "LOW",
      "structure_label": "LL"
    },
    {
      "index": 55,
      "timestamp": "2026-07-08T13:45:00Z",
      "price": 77.47,
      "point_type": "HIGH",
      "structure_label": "LH"
    },
    {
      "index": 61,
      "timestamp": "2026-07-08T15:15:00Z",
      "price": 76.29,
      "point_type": "LOW",
      "structure_label": "LL"
    },
    {
      "index": 70,
      "timestamp": "2026-07-08T17:30:00Z",
      "price": 77.68,
      "point_type": "HIGH",
      "structure_label": "HH"
    },
    {
      "index": 74,
      "timestamp": "2026-07-08T18:30:00Z",
      "price": 76.82,
      "point_type": "LOW",
      "structure_label": "HL"
    },
    {
      "index": 80,
      "timestamp": "2026-07-08T20:00:00Z",
      "price": 77.57,
      "point_type": "HIGH",
      "structure_label": "LH"
    },
    {
      "index": 85,
      "timestamp": "2026-07-08T21:15:00Z",
      "price": 76.93,
      "point_type": "LOW",
      "structure_label": "HL"
    },
    {
      "index": 92,
      "timestamp": "2026-07-08T23:00:00Z",
      "price": 77.66,
      "point_type": "HIGH",
      "structure_label": "HH"
    }
  ],
  "latest_swings": [
    {
      "index": 45,
      "timestamp": "2026-07-08T11:15:00Z",
      "price": 77.08,
      "point_type": "LOW",
      "structure_label": "HL"
    },
    {
      "index": 46,
      "timestamp": "2026-07-08T11:30:00Z",
      "price": 77.71,
      "point_type": "HIGH",
      "structure_label": "HH"
    },
    {
      "index": 53,
      "timestamp": "2026-07-08T13:15:00Z",
      "price": 76.64,
      "point_type": "LOW",
      "structure_label": "LL"
    },
    {
      "index": 55,
      "timestamp": "2026-07-08T13:45:00Z",
      "price": 77.47,
      "point_type": "HIGH",
      "structure_label": "LH"
    },
    {
      "index": 61,
      "timestamp": "2026-07-08T15:15:00Z",
      "price": 76.29,
      "point_type": "LOW",
      "structure_label": "LL"
    },
    {
      "index": 70,
      "timestamp": "2026-07-08T17:30:00Z",
      "price": 77.68,
      "point_type": "HIGH",
      "structure_label": "HH"
    },
    {
      "index": 74,
      "timestamp": "2026-07-08T18:30:00Z",
      "price": 76.82,
      "point_type": "LOW",
      "structure_label": "HL"
    },
    {
      "index": 80,
      "timestamp": "2026-07-08T20:00:00Z",
      "price": 77.57,
      "point_type": "HIGH",
      "structure_label": "LH"
    },
    {
      "index": 85,
      "timestamp": "2026-07-08T21:15:00Z",
      "price": 76.93,
      "point_type": "LOW",
      "structure_label": "HL"
    },
    {
      "index": 92,
      "timestamp": "2026-07-08T23:00:00Z",
      "price": 77.66,
      "point_type": "HIGH",
      "structure_label": "HH"
    }
  ],
  "range_boundaries": {
    "support_zone": {
      "zone_type": "SUPPORT",
      "lower_price": 76.64,
      "upper_price": 76.94,
      "mid_price": 76.84599999999999,
      "touch_count": 5,
      "source_indexes": [
        34,
        40,
        53,
        74,
        85
      ],
      "zone_width": 0.29999999999999716,
      "zone_width_ratio": 0.0039039117195429456,
      "formed_at_index": 85,
      "first_touch_index": 34,
      "last_touch_index": 85,
      "source_point_types": [
        "LOW",
        "LOW",
        "LOW",
        "LOW",
        "LOW"
      ],
      "original_zone_type": "SUPPORT",
      "current_zone_type": "SUPPORT",
      "role_changed_at_index": null,
      "is_significant_single_extreme": false,
      "positional_zone_type": "SUPPORT"
    },
    "resistance_zone": {
      "zone_type": "RESISTANCE",
      "lower_price": 77.47,
      "upper_price": 77.8,
      "mid_price": 77.60999999999999,
      "touch_count": 8,
      "source_indexes": [
        28,
        38,
        42,
        46,
        55,
        70,
        80,
        92
      ],
      "zone_width": 0.3299999999999983,
      "zone_width_ratio": 0.004252029377657497,
      "formed_at_index": 92,
      "first_touch_index": 28,
      "last_touch_index": 92,
      "source_point_types": [
        "LOW",
        "HIGH",
        "HIGH",
        "HIGH",
        "HIGH",
        "HIGH",
        "HIGH",
        "HIGH"
      ],
      "original_zone_type": "RESISTANCE",
      "current_zone_type": "RESISTANCE",
      "role_changed_at_index": null,
      "is_significant_single_extreme": false,
      "positional_zone_type": "SUPPORT"
    },
    "is_detected": true,
    "lower_boundary": 76.64,
    "upper_boundary": 77.8,
    "midline": 77.22,
    "width": 1.1599999999999966,
    "width_ratio": 0.015022015022014978,
    "touch_count": 13,
    "inside_close_ratio": 0.8923076923076924,
    "formed_at_index": 92,
    "first_touch_index": 28,
    "duration_candles": 65,
    "boundary_alternation_count": 10
  },
  "inside_close_ratio": 0.8923076923076924,
  "breakout_or_breakdown": {
    "direction": "NONE",
    "status": "NO_BREAKOUT",
    "breakout_index": null,
    "boundary_price": null,
    "breakout_close": null,
    "distance_ratio": 0.0,
    "returned_to_range": false,
    "follow_through_count": 0,
    "evidence": [],
    "analysis_start_index": 93,
    "confirmation_method": "NONE",
    "confirmation_close_count": 0,
    "extreme_index": null,
    "extreme_price": null,
    "maximum_distance_ratio": 0.0,
    "return_index": null,
    "return_depth_ratio": 0.0,
    "reversal_candle_count": 0,
    "false_breakout_confirmation": "NONE",
    "false_breakout_invalidated": false
  },
  "retest": {
    "returned_to_range": false,
    "return_index": null,
    "confirmation_method": "NONE"
  },
  "trap": {
    "false_breakout_confirmation": "NONE",
    "invalidated": false
  },
  "polarity_flip": {
    "status": "NONE",
    "source_zone_type": null,
    "test_index": null,
    "held": false,
    "evidence": [],
    "departure_index": null,
    "role_changed_at_index": null
  },
  "current_decision_window": {
    "candle_count": 96,
    "context_start_index": 0,
    "decision_start_index": 72,
    "decision_end_index": 95,
    "confirmation_lookahead": 3,
    "readiness": "FULL"
  },
  "bearish_structure_exists": false,
  "bullish_reversal_exists": false,
  "confirmed_range_exists": true,
  "engine_altunina_context": {
    "candle_count": 96,
    "swing_points": [
      {
        "index": 10,
        "timestamp": "2026-07-08T02:30:00Z",
        "price": 78.22,
        "point_type": "LOW"
      },
      {
        "index": 12,
        "timestamp": "2026-07-08T03:00:00Z",
        "price": 79.34,
        "point_type": "HIGH"
      },
      {
        "index": 16,
        "timestamp": "2026-07-08T04:00:00Z",
        "price": 78.57,
        "point_type": "LOW"
      },
      {
        "index": 18,
        "timestamp": "2026-07-08T04:30:00Z",
        "price": 78.93,
        "point_type": "HIGH"
      },
      {
        "index": 28,
        "timestamp": "2026-07-08T07:00:00Z",
        "price": 77.8,
        "point_type": "LOW"
      },
      {
        "index": 32,
        "timestamp": "2026-07-08T08:00:00Z",
        "price": 78.43,
        "point_type": "HIGH"
      },
      {
        "index": 34,
        "timestamp": "2026-07-08T08:30:00Z",
        "price": 76.9,
        "point_type": "LOW"
      },
      {
        "index": 38,
        "timestamp": "2026-07-08T09:30:00Z",
        "price": 77.49,
        "point_type": "HIGH"
      },
      {
        "index": 40,
        "timestamp": "2026-07-08T10:00:00Z",
        "price": 76.94,
        "point_type": "LOW"
      },
      {
        "index": 42,
        "timestamp": "2026-07-08T10:30:00Z",
        "price": 77.5,
        "point_type": "HIGH"
      },
      {
        "index": 45,
        "timestamp": "2026-07-08T11:15:00Z",
        "price": 77.08,
        "point_type": "LOW"
      },
      {
        "index": 46,
        "timestamp": "2026-07-08T11:30:00Z",
        "price": 77.71,
        "point_type": "HIGH"
      },
      {
        "index": 53,
        "timestamp": "2026-07-08T13:15:00Z",
        "price": 76.64,
        "point_type": "LOW"
      },
      {
        "index": 55,
        "timestamp": "2026-07-08T13:45:00Z",
        "price": 77.47,
        "point_type": "HIGH"
      },
      {
        "index": 61,
        "timestamp": "2026-07-08T15:15:00Z",
        "price": 76.29,
        "point_type": "LOW"
      },
      {
        "index": 70,
        "timestamp": "2026-07-08T17:30:00Z",
        "price": 77.68,
        "point_type": "HIGH"
      },
      {
        "index": 74,
        "timestamp": "2026-07-08T18:30:00Z",
        "price": 76.82,
        "point_type": "LOW"
      },
      {
        "index": 80,
        "timestamp": "2026-07-08T20:00:00Z",
        "price": 77.57,
        "point_type": "HIGH"
      },
      {
        "index": 85,
        "timestamp": "2026-07-08T21:15:00Z",
        "price": 76.93,
        "point_type": "LOW"
      },
      {
        "index": 92,
        "timestamp": "2026-07-08T23:00:00Z",
        "price": 77.66,
        "point_type": "HIGH"
      }
    ],
    "price_legs": [
      {
        "start": {
          "index": 10,
          "timestamp": "2026-07-08T02:30:00Z",
          "price": 78.22,
          "point_type": "LOW"
        },
        "end": {
          "index": 12,
          "timestamp": "2026-07-08T03:00:00Z",
          "price": 79.34,
          "point_type": "HIGH"
        },
        "direction": "UP",
        "absolute_change": 1.1200000000000045,
        "relative_change": 0.014318588596266998,
        "candle_span": 2
      },
      {
        "start": {
          "index": 12,
          "timestamp": "2026-07-08T03:00:00Z",
          "price": 79.34,
          "point_type": "HIGH"
        },
        "end": {
          "index": 16,
          "timestamp": "2026-07-08T04:00:00Z",
          "price": 78.57,
          "point_type": "LOW"
        },
        "direction": "DOWN",
        "absolute_change": 0.7700000000000102,
        "relative_change": 0.00970506680110928,
        "candle_span": 4
      },
      {
        "start": {
          "index": 16,
          "timestamp": "2026-07-08T04:00:00Z",
          "price": 78.57,
          "point_type": "LOW"
        },
        "end": {
          "index": 18,
          "timestamp": "2026-07-08T04:30:00Z",
          "price": 78.93,
          "point_type": "HIGH"
        },
        "direction": "UP",
        "absolute_change": 0.36000000000001364,
        "relative_change": 0.004581901489118158,
        "candle_span": 2
      },
      {
        "start": {
          "index": 18,
          "timestamp": "2026-07-08T04:30:00Z",
          "price": 78.93,
          "point_type": "HIGH"
        },
        "end": {
          "index": 28,
          "timestamp": "2026-07-08T07:00:00Z",
          "price": 77.8,
          "point_type": "LOW"
        },
        "direction": "DOWN",
        "absolute_change": 1.1300000000000097,
        "relative_change": 0.014316482959584563,
        "candle_span": 10
      },
      {
        "start": {
          "index": 28,
          "timestamp": "2026-07-08T07:00:00Z",
          "price": 77.8,
          "point_type": "LOW"
        },
        "end": {
          "index": 32,
          "timestamp": "2026-07-08T08:00:00Z",
          "price": 78.43,
          "point_type": "HIGH"
        },
        "direction": "UP",
        "absolute_change": 0.6300000000000097,
        "relative_change": 0.008097686375321461,
        "candle_span": 4
      },
      {
        "start": {
          "index": 32,
          "timestamp": "2026-07-08T08:00:00Z",
          "price": 78.43,
          "point_type": "HIGH"
        },
        "end": {
          "index": 34,
          "timestamp": "2026-07-08T08:30:00Z",
          "price": 76.9,
          "point_type": "LOW"
        },
        "direction": "DOWN",
        "absolute_change": 1.5300000000000011,
        "relative_change": 0.01950784138722429,
        "candle_span": 2
      },
      {
        "start": {
          "index": 34,
          "timestamp": "2026-07-08T08:30:00Z",
          "price": 76.9,
          "point_type": "LOW"
        },
        "end": {
          "index": 38,
          "timestamp": "2026-07-08T09:30:00Z",
          "price": 77.49,
          "point_type": "HIGH"
        },
        "direction": "UP",
        "absolute_change": 0.5899999999999892,
        "relative_change": 0.007672301690507011,
        "candle_span": 4
      },
      {
        "start": {
          "index": 38,
          "timestamp": "2026-07-08T09:30:00Z",
          "price": 77.49,
          "point_type": "HIGH"
        },
        "end": {
          "index": 40,
          "timestamp": "2026-07-08T10:00:00Z",
          "price": 76.94,
          "point_type": "LOW"
        },
        "direction": "DOWN",
        "absolute_change": 0.5499999999999972,
        "relative_change": 0.007097690024519257,
        "candle_span": 2
      },
      {
        "start": {
          "index": 40,
          "timestamp": "2026-07-08T10:00:00Z",
          "price": 76.94,
          "point_type": "LOW"
        },
        "end": {
          "index": 42,
          "timestamp": "2026-07-08T10:30:00Z",
          "price": 77.5,
          "point_type": "HIGH"
        },
        "direction": "UP",
        "absolute_change": 0.5600000000000023,
        "relative_change": 0.007278398752274529,
        "candle_span": 2
      },
      {
        "start": {
          "index": 42,
          "timestamp": "2026-07-08T10:30:00Z",
          "price": 77.5,
          "point_type": "HIGH"
        },
        "end": {
          "index": 45,
          "timestamp": "2026-07-08T11:15:00Z",
          "price": 77.08,
          "point_type": "LOW"
        },
        "direction": "DOWN",
        "absolute_change": 0.4200000000000017,
        "relative_change": 0.005419354838709699,
        "candle_span": 3
      },
      {
        "start": {
          "index": 45,
          "timestamp": "2026-07-08T11:15:00Z",
          "price": 77.08,
          "point_type": "LOW"
        },
        "end": {
          "index": 46,
          "timestamp": "2026-07-08T11:30:00Z",
          "price": 77.71,
          "point_type": "HIGH"
        },
        "direction": "UP",
        "absolute_change": 0.6299999999999955,
        "relative_change": 0.008173326414115147,
        "candle_span": 1
      },
      {
        "start": {
          "index": 46,
          "timestamp": "2026-07-08T11:30:00Z",
          "price": 77.71,
          "point_type": "HIGH"
        },
        "end": {
          "index": 53,
          "timestamp": "2026-07-08T13:15:00Z",
          "price": 76.64,
          "point_type": "LOW"
        },
        "direction": "DOWN",
        "absolute_change": 1.0699999999999932,
        "relative_change": 0.0137691416806073,
        "candle_span": 7
      },
      {
        "start": {
          "index": 53,
          "timestamp": "2026-07-08T13:15:00Z",
          "price": 76.64,
          "point_type": "LOW"
        },
        "end": {
          "index": 55,
          "timestamp": "2026-07-08T13:45:00Z",
          "price": 77.47,
          "point_type": "HIGH"
        },
        "direction": "UP",
        "absolute_change": 0.8299999999999983,
        "relative_change": 0.010829853862212921,
        "candle_span": 2
      },
      {
        "start": {
          "index": 55,
          "timestamp": "2026-07-08T13:45:00Z",
          "price": 77.47,
          "point_type": "HIGH"
        },
        "end": {
          "index": 61,
          "timestamp": "2026-07-08T15:15:00Z",
          "price": 76.29,
          "point_type": "LOW"
        },
        "direction": "DOWN",
        "absolute_change": 1.1799999999999926,
        "relative_change": 0.015231702594552634,
        "candle_span": 6
      },
      {
        "start": {
          "index": 61,
          "timestamp": "2026-07-08T15:15:00Z",
          "price": 76.29,
          "point_type": "LOW"
        },
        "end": {
          "index": 70,
          "timestamp": "2026-07-08T17:30:00Z",
          "price": 77.68,
          "point_type": "HIGH"
        },
        "direction": "UP",
        "absolute_change": 1.3900000000000006,
        "relative_change": 0.018219950190064234,
        "candle_span": 9
      },
      {
        "start": {
          "index": 70,
          "timestamp": "2026-07-08T17:30:00Z",
          "price": 77.68,
          "point_type": "HIGH"
        },
        "end": {
          "index": 74,
          "timestamp": "2026-07-08T18:30:00Z",
          "price": 76.82,
          "point_type": "LOW"
        },
        "direction": "DOWN",
        "absolute_change": 0.8600000000000136,
        "relative_change": 0.011071060762101102,
        "candle_span": 4
      },
      {
        "start": {
          "index": 74,
          "timestamp": "2026-07-08T18:30:00Z",
          "price": 76.82,
          "point_type": "LOW"
        },
        "end": {
          "index": 80,
          "timestamp": "2026-07-08T20:00:00Z",
          "price": 77.57,
          "point_type": "HIGH"
        },
        "direction": "UP",
        "absolute_change": 0.75,
        "relative_change": 0.009763082530590992,
        "candle_span": 6
      },
      {
        "start": {
          "index": 80,
          "timestamp": "2026-07-08T20:00:00Z",
          "price": 77.57,
          "point_type": "HIGH"
        },
        "end": {
          "index": 85,
          "timestamp": "2026-07-08T21:15:00Z",
          "price": 76.93,
          "point_type": "LOW"
        },
        "direction": "DOWN",
        "absolute_change": 0.6399999999999864,
        "relative_change": 0.008250612350135186,
        "candle_span": 5
      },
      {
        "start": {
          "index": 85,
          "timestamp": "2026-07-08T21:15:00Z",
          "price": 76.93,
          "point_type": "LOW"
        },
        "end": {
          "index": 92,
          "timestamp": "2026-07-08T23:00:00Z",
          "price": 77.66,
          "point_type": "HIGH"
        },
        "direction": "UP",
        "absolute_change": 0.7299999999999898,
        "relative_change": 0.009489145976861948,
        "candle_span": 7
      }
    ],
    "structure_direction": "SIDEWAYS_STRUCTURE",
    "trend_line": {
      "available": false,
      "direction": "FLAT",
      "start": null,
      "end": null,
      "slope_per_candle": 0.0,
      "anchor_count": 0,
      "method_origin": "ENGINE_TREND_DERIVED_HEURISTIC"
    },
    "trend_duration": {
      "duration_days": 0.9895833333333334,
      "duration_class": "SUB_MONTH_SCALE",
      "hierarchy_role": "UNKNOWN",
      "method_origin": "ALTUNINA_BOOK_RULE"
    },
    "trend_strength_score": 0.0,
    "trend_consistency_score": 0.0,
    "trend_progress_score": 0.0,
    "impulse_correction": {
      "bullish_impulse_total": 0.0,
      "bearish_impulse_total": 0.0,
      "bullish_correction_total": 0.0,
      "bearish_correction_total": 0.0,
      "dominant_impulse_direction": "FLAT",
      "max_pullback_depth": 0.0,
      "average_pullback_depth": 0.0,
      "correction_count": 0,
      "correction_limit": 0.62,
      "correction_limit_breached": false,
      "structural_pivot_breached": false,
      "nearest_fibonacci_level": null
    },
    "evidence": [
      {
        "source": "ALTUNINA",
        "code": "ALTUNINA_PRICE_LEGS_BUILT",
        "description": "Price legs were built from normalized swing points",
        "contribution": 0.0,
        "metadata": {
          "method_origin": "ENGINE_TREND_DERIVED_HEURISTIC",
          "contribution_origin": "ENGINE_TREND_DERIVED_HEURISTIC",
          "leg_count": 19
        }
      },
      {
        "source": "ALTUNINA",
        "code": "ALTUNINA_SIDEWAYS_STRUCTURE",
        "description": "Swing sequences do not establish directional structure",
        "contribution": 0.0,
        "metadata": {
          "method_origin": "ENGINE_TREND_DERIVED_HEURISTIC",
          "contribution_origin": "ENGINE_TREND_DERIVED_HEURISTIC"
        }
      },
      {
        "source": "ALTUNINA",
        "code": "ALTUNINA_TREND_NOT_CONFIRMED",
        "description": "Directional trend is not structurally confirmed",
        "contribution": 0.0,
        "metadata": {
          "method_origin": "ALTUNINA_BOOK_RULE",
          "contribution_origin": "ENGINE_TREND_DERIVED_HEURISTIC"
        }
      }
    ],
    "reason_codes": [
      "ALTUNINA_PRICE_LEGS_BUILT",
      "ALTUNINA_SIDEWAYS_STRUCTURE",
      "ALTUNINA_TREND_NOT_CONFIRMED"
    ],
    "summary": {
      "raw_swing_count": 20,
      "swing_count": 20,
      "leg_count": 19,
      "structure_direction": "SIDEWAYS_STRUCTURE",
      "total_movement": 15.740000000000009,
      "directional_progress": 0.0,
      "score_method_origin": "ENGINE_TREND_DERIVED_HEURISTIC",
      "swing_method_origin": "ENGINE_TREND_DERIVED_HEURISTIC"
    }
  },
  "engine_schwager_context": {
    "candle_count": 96,
    "zones": [
      {
        "zone_type": "SUPPORT",
        "lower_price": 76.29,
        "upper_price": 76.29,
        "mid_price": 76.29,
        "touch_count": 1,
        "source_indexes": [
          61
        ],
        "zone_width": 0.0,
        "zone_width_ratio": 0.0,
        "formed_at_index": 61,
        "first_touch_index": 61,
        "last_touch_index": 61,
        "source_point_types": [
          "LOW"
        ],
        "original_zone_type": "SUPPORT",
        "current_zone_type": "SUPPORT",
        "role_changed_at_index": null,
        "is_significant_single_extreme": true,
        "positional_zone_type": "SUPPORT"
      },
      {
        "zone_type": "SUPPORT",
        "lower_price": 76.64,
        "upper_price": 76.94,
        "mid_price": 76.84599999999999,
        "touch_count": 5,
        "source_indexes": [
          34,
          40,
          53,
          74,
          85
        ],
        "zone_width": 0.29999999999999716,
        "zone_width_ratio": 0.0039039117195429456,
        "formed_at_index": 85,
        "first_touch_index": 34,
        "last_touch_index": 85,
        "source_point_types": [
          "LOW",
          "LOW",
          "LOW",
          "LOW",
          "LOW"
        ],
        "original_zone_type": "SUPPORT",
        "current_zone_type": "SUPPORT",
        "role_changed_at_index": null,
        "is_significant_single_extreme": false,
        "positional_zone_type": "SUPPORT"
      },
      {
        "zone_type": "RESISTANCE",
        "lower_price": 77.47,
        "upper_price": 77.8,
        "mid_price": 77.60999999999999,
        "touch_count": 8,
        "source_indexes": [
          28,
          38,
          42,
          46,
          55,
          70,
          80,
          92
        ],
        "zone_width": 0.3299999999999983,
        "zone_width_ratio": 0.004252029377657497,
        "formed_at_index": 92,
        "first_touch_index": 28,
        "last_touch_index": 92,
        "source_point_types": [
          "LOW",
          "HIGH",
          "HIGH",
          "HIGH",
          "HIGH",
          "HIGH",
          "HIGH",
          "HIGH"
        ],
        "original_zone_type": "RESISTANCE",
        "current_zone_type": "RESISTANCE",
        "role_changed_at_index": null,
        "is_significant_single_extreme": false,
        "positional_zone_type": "SUPPORT"
      },
      {
        "zone_type": "RESISTANCE",
        "lower_price": 78.22,
        "upper_price": 78.43,
        "mid_price": 78.325,
        "touch_count": 2,
        "source_indexes": [
          10,
          32
        ],
        "zone_width": 0.21000000000000796,
        "zone_width_ratio": 0.002681136291094899,
        "formed_at_index": 32,
        "first_touch_index": 10,
        "last_touch_index": 32,
        "source_point_types": [
          "LOW",
          "HIGH"
        ],
        "original_zone_type": "RESISTANCE",
        "current_zone_type": "RESISTANCE",
        "role_changed_at_index": null,
        "is_significant_single_extreme": false,
        "positional_zone_type": "RESISTANCE"
      }
    ],
    "trading_range": {
      "support_zone": {
        "zone_type": "SUPPORT",
        "lower_price": 76.64,
        "upper_price": 76.94,
        "mid_price": 76.84599999999999,
        "touch_count": 5,
        "source_indexes": [
          34,
          40,
          53,
          74,
          85
        ],
        "zone_width": 0.29999999999999716,
        "zone_width_ratio": 0.0039039117195429456,
        "formed_at_index": 85,
        "first_touch_index": 34,
        "last_touch_index": 85,
        "source_point_types": [
          "LOW",
          "LOW",
          "LOW",
          "LOW",
          "LOW"
        ],
        "original_zone_type": "SUPPORT",
        "current_zone_type": "SUPPORT",
        "role_changed_at_index": null,
        "is_significant_single_extreme": false,
        "positional_zone_type": "SUPPORT"
      },
      "resistance_zone": {
        "zone_type": "RESISTANCE",
        "lower_price": 77.47,
        "upper_price": 77.8,
        "mid_price": 77.60999999999999,
        "touch_count": 8,
        "source_indexes": [
          28,
          38,
          42,
          46,
          55,
          70,
          80,
          92
        ],
        "zone_width": 0.3299999999999983,
        "zone_width_ratio": 0.004252029377657497,
        "formed_at_index": 92,
        "first_touch_index": 28,
        "last_touch_index": 92,
        "source_point_types": [
          "LOW",
          "HIGH",
          "HIGH",
          "HIGH",
          "HIGH",
          "HIGH",
          "HIGH",
          "HIGH"
        ],
        "original_zone_type": "RESISTANCE",
        "current_zone_type": "RESISTANCE",
        "role_changed_at_index": null,
        "is_significant_single_extreme": false,
        "positional_zone_type": "SUPPORT"
      },
      "is_detected": true,
      "lower_boundary": 76.64,
      "upper_boundary": 77.8,
      "midline": 77.22,
      "width": 1.1599999999999966,
      "width_ratio": 0.015022015022014978,
      "touch_count": 13,
      "inside_close_ratio": 0.8923076923076924,
      "formed_at_index": 92,
      "first_touch_index": 28,
      "duration_candles": 65,
      "boundary_alternation_count": 10
    },
    "breakout_context": {
      "direction": "NONE",
      "status": "NO_BREAKOUT",
      "breakout_index": null,
      "boundary_price": null,
      "breakout_close": null,
      "distance_ratio": 0.0,
      "returned_to_range": false,
      "follow_through_count": 0,
      "evidence": [],
      "analysis_start_index": 93,
      "confirmation_method": "NONE",
      "confirmation_close_count": 0,
      "extreme_index": null,
      "extreme_price": null,
      "maximum_distance_ratio": 0.0,
      "return_index": null,
      "return_depth_ratio": 0.0,
      "reversal_candle_count": 0,
      "false_breakout_confirmation": "NONE",
      "false_breakout_invalidated": false
    },
    "polarity_flip_context": {
      "status": "NONE",
      "source_zone_type": null,
      "test_index": null,
      "held": false,
      "evidence": [],
      "departure_index": null,
      "role_changed_at_index": null
    },
    "evidence": [
      {
        "source": "SCHWAGER",
        "code": "SCHWAGER_SUPPORT_ZONE_IDENTIFIED",
        "description": "Repeated swing lows form a support zone",
        "contribution": 0.0,
        "metadata": {
          "touches": 1
        }
      },
      {
        "source": "SCHWAGER",
        "code": "SCHWAGER_PREVIOUS_EXTREME_ZONE_IDENTIFIED",
        "description": "A significant previous extreme defines a potential zone",
        "contribution": 0.0,
        "metadata": {
          "index": 61
        }
      },
      {
        "source": "SCHWAGER",
        "code": "SCHWAGER_SUPPORT_ZONE_IDENTIFIED",
        "description": "Repeated swing lows form a support zone",
        "contribution": 0.0,
        "metadata": {
          "touches": 5
        }
      },
      {
        "source": "SCHWAGER",
        "code": "SCHWAGER_SUPPORT_ZONE_HELD",
        "description": "Support zone has repeated touches",
        "contribution": 0.0,
        "metadata": {
          "touches": 5
        }
      },
      {
        "source": "SCHWAGER",
        "code": "SCHWAGER_ZONE_TOO_WIDE",
        "description": "A level zone is too wide for stable context",
        "contribution": 0.0,
        "metadata": {
          "width_ratio": 0.0039039117195429456
        }
      },
      {
        "source": "SCHWAGER",
        "code": "SCHWAGER_RESISTANCE_ZONE_IDENTIFIED",
        "description": "Repeated swing highs form a resistance zone",
        "contribution": 0.0,
        "metadata": {
          "touches": 8
        }
      },
      {
        "source": "SCHWAGER",
        "code": "SCHWAGER_RESISTANCE_ZONE_HELD",
        "description": "Resistance zone has repeated touches",
        "contribution": 0.0,
        "metadata": {
          "touches": 8
        }
      },
      {
        "source": "SCHWAGER",
        "code": "SCHWAGER_ZONE_TOO_WIDE",
        "description": "A level zone is too wide for stable context",
        "contribution": 0.0,
        "metadata": {
          "width_ratio": 0.004252029377657497
        }
      },
      {
        "source": "SCHWAGER",
        "code": "SCHWAGER_RESISTANCE_ZONE_IDENTIFIED",
        "description": "Repeated swing highs form a resistance zone",
        "contribution": 0.0,
        "metadata": {
          "touches": 2
        }
      },
      {
        "source": "SCHWAGER",
        "code": "SCHWAGER_RESISTANCE_ZONE_HELD",
        "description": "Resistance zone has repeated touches",
        "contribution": 0.0,
        "metadata": {
          "touches": 2
        }
      },
      {
        "source": "SCHWAGER",
        "code": "SCHWAGER_TRADING_RANGE_DETECTED",
        "description": "Repeated boundaries define a trading range",
        "contribution": 0.0,
        "metadata": {}
      },
      {
        "source": "SCHWAGER",
        "code": "SCHWAGER_PRICE_INSIDE_RANGE",
        "description": "Closing prices are commonly inside the range",
        "contribution": 0.0,
        "metadata": {
          "ratio": 0.8923076923076924
        }
      },
      {
        "source": "SCHWAGER",
        "code": "SCHWAGER_RANGE_UPPER_BOUNDARY_HELD",
        "description": "The upper range boundary has repeated touches",
        "contribution": 0.0,
        "metadata": {}
      },
      {
        "source": "SCHWAGER",
        "code": "SCHWAGER_RANGE_LOWER_BOUNDARY_HELD",
        "description": "The lower range boundary has repeated touches",
        "contribution": 0.0,
        "metadata": {}
      },
      {
        "source": "SCHWAGER",
        "code": "SCHWAGER_RANGE_DURATION_CONFIRMED",
        "description": "Range boundaries persisted across a sufficient candle span",
        "contribution": 0.0,
        "metadata": {
          "duration": 65
        }
      },
      {
        "source": "SCHWAGER",
        "code": "SCHWAGER_RANGE_BOUNDARY_ALTERNATION_CONFIRMED",
        "description": "Price alternated between both range boundaries",
        "contribution": 0.0,
        "metadata": {
          "count": 10
        }
      }
    ],
    "reason_codes": [
      "SCHWAGER_SUPPORT_ZONE_IDENTIFIED",
      "SCHWAGER_PREVIOUS_EXTREME_ZONE_IDENTIFIED",
      "SCHWAGER_SUPPORT_ZONE_HELD",
      "SCHWAGER_ZONE_TOO_WIDE",
      "SCHWAGER_RESISTANCE_ZONE_IDENTIFIED",
      "SCHWAGER_RESISTANCE_ZONE_HELD",
      "SCHWAGER_TRADING_RANGE_DETECTED",
      "SCHWAGER_PRICE_INSIDE_RANGE",
      "SCHWAGER_RANGE_UPPER_BOUNDARY_HELD",
      "SCHWAGER_RANGE_LOWER_BOUNDARY_HELD",
      "SCHWAGER_RANGE_DURATION_CONFIRMED",
      "SCHWAGER_RANGE_BOUNDARY_ALTERNATION_CONFIRMED"
    ],
    "summary": {
      "swing_count": 20,
      "zone_count": 4,
      "range_detected": true,
      "range_formed_at_index": 92,
      "range_duration_candles": 65,
      "inside_close_ratio": 0.8923076923076924,
      "breakout_direction": "NONE",
      "breakout_status": "NO_BREAKOUT",
      "polarity_status": "NONE"
    }
  }
}
```

## Nison/candle layer

```json
{
  "bearish_continuation_patterns": [],
  "bullish_reversal_patterns_on_rebound": [
    {
      "event_id": "pattern:74:75:BULLISH_ENGULFING_CONTEXT",
      "pattern_code": "BULLISH_ENGULFING_CONTEXT",
      "direction": "BULLISH",
      "role": "REVERSAL",
      "start_index": 74,
      "end_index": 75,
      "prior_structure": "BEARISH_STRUCTURE",
      "zone_relation": "NO_CAUSAL_ZONE",
      "related_zone_mid": null,
      "follow_through": "CONFIRMED",
      "status": "CANDIDATE",
      "reason_codes": [
        "BULLISH_ENGULFING_CONTEXT",
        "PATTERN_PRIOR_BEARISH_STRUCTURE",
        "NO_CAUSAL_ZONE",
        "PATTERN_LEVEL_CONTEXT_MISSING"
      ]
    },
    {
      "event_id": "pattern:72:73:TWEEZERS_BOTTOM_CONTEXT_REQUIRED",
      "pattern_code": "TWEEZERS_BOTTOM_CONTEXT_REQUIRED",
      "direction": "BULLISH",
      "role": "REVERSAL",
      "start_index": 72,
      "end_index": 73,
      "prior_structure": "BEARISH_STRUCTURE",
      "zone_relation": "NO_CAUSAL_ZONE",
      "related_zone_mid": null,
      "follow_through": "INVALIDATED",
      "status": "INVALIDATED",
      "reason_codes": [
        "TWEEZERS_BOTTOM_CONTEXT_REQUIRED",
        "PATTERN_PRIOR_BEARISH_STRUCTURE",
        "NO_CAUSAL_ZONE",
        "PATTERN_FOLLOW_THROUGH_INVALIDATED"
      ]
    },
    {
      "event_id": "pattern:80:81:TWEEZERS_BOTTOM_CONTEXT_REQUIRED",
      "pattern_code": "TWEEZERS_BOTTOM_CONTEXT_REQUIRED",
      "direction": "BULLISH",
      "role": "REVERSAL",
      "start_index": 80,
      "end_index": 81,
      "prior_structure": "SIDEWAYS_STRUCTURE",
      "zone_relation": "NO_CAUSAL_ZONE",
      "related_zone_mid": null,
      "follow_through": "INVALIDATED",
      "status": "CONTEXT_REJECTED",
      "reason_codes": [
        "TWEEZERS_BOTTOM_CONTEXT_REQUIRED",
        "PATTERN_PRIOR_SIDEWAYS_STRUCTURE",
        "NO_CAUSAL_ZONE",
        "PATTERN_TREND_CONTEXT_REJECTED"
      ]
    },
    {
      "event_id": "pattern:82:83:BULLISH_HARAMI_CONTEXT",
      "pattern_code": "BULLISH_HARAMI_CONTEXT",
      "direction": "BULLISH",
      "role": "REVERSAL",
      "start_index": 82,
      "end_index": 83,
      "prior_structure": "SIDEWAYS_STRUCTURE",
      "zone_relation": "NO_CAUSAL_ZONE",
      "related_zone_mid": null,
      "follow_through": "INVALIDATED",
      "status": "CONTEXT_REJECTED",
      "reason_codes": [
        "BULLISH_HARAMI_CONTEXT",
        "PATTERN_PRIOR_SIDEWAYS_STRUCTURE",
        "NO_CAUSAL_ZONE",
        "PATTERN_TREND_CONTEXT_REJECTED"
      ]
    },
    {
      "event_id": "pattern:92:93:TWEEZERS_BOTTOM_CONTEXT_REQUIRED",
      "pattern_code": "TWEEZERS_BOTTOM_CONTEXT_REQUIRED",
      "direction": "BULLISH",
      "role": "REVERSAL",
      "start_index": 92,
      "end_index": 93,
      "prior_structure": "SIDEWAYS_STRUCTURE",
      "zone_relation": "AT_RESISTANCE",
      "related_zone_mid": 77.60999999999999,
      "follow_through": "CONFIRMED",
      "status": "CONTEXT_REJECTED",
      "reason_codes": [
        "TWEEZERS_BOTTOM_CONTEXT_REQUIRED",
        "PATTERN_PRIOR_SIDEWAYS_STRUCTURE",
        "AT_RESISTANCE",
        "PATTERN_TREND_CONTEXT_REJECTED"
      ]
    }
  ],
  "exhaustion_candles_or_clues": [
    "LONG_LOWER_SHADOW_REJECTION",
    "SMALL_BODY_INDECISION",
    "DOJI_INDECISION",
    "LONG_UPPER_SHADOW_REJECTION",
    "LONG_LEGGED_DOJI_CONTEXT",
    "RICKSHAW_MAN_DOJI_CONTEXT",
    "DRAGONFLY_DOJI_CONTEXT",
    "DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT",
    "DOJI_TOP_CONTEXT_REQUIRED",
    "SMALL_BODY_CLUSTER"
  ],
  "confirmed_contextual_patterns": [],
  "direction_confirmation_explanation": "Candle patterns confirm direction only when contextual event status is CONFIRMED; shapes needing context/follow-through do not confirm it.",
  "engine_nison_context": {
    "candle_count": 96,
    "summary": {
      "doji_count": 14,
      "doji_ratio": 0.14583333333333334,
      "small_body_count": 35,
      "small_body_ratio": 0.3645833333333333,
      "bullish_body_total": 5.640000000000001,
      "bearish_body_total": 8.380000000000052
    },
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "DOJI_INDECISION",
      "SPINNING_TOP_INDECISION",
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW",
      "CLOSE_NEAR_HIGH",
      "HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED",
      "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
      "LONG_UPPER_SHADOW_REJECTION",
      "SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED",
      "STRONG_BULLISH_CANDLE_BODY",
      "BEARISH_ENGULFING_CONTEXT",
      "ENGULFING_WITHOUT_FOLLOW_THROUGH",
      "BULLISH_ENGULFING_CONTEXT",
      "LONG_LEGGED_DOJI_CONTEXT",
      "RICKSHAW_MAN_DOJI_CONTEXT",
      "BEARISH_BELT_HOLD_CONTEXT_REQUIRED",
      "HANGING_MAN_LIKE_CONTEXT_REQUIRED",
      "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
      "DRAGONFLY_DOJI_CONTEXT",
      "BULLISH_BELT_HOLD_CONTEXT_REQUIRED",
      "INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED",
      "TWEEZERS_TOP_CONTEXT_REQUIRED",
      "BULLISH_HARAMI_CONTEXT",
      "HARAMI_CROSS_CONTEXT",
      "BEARISH_SEPARATING_LINES_CONTEXT",
      "TWEEZERS_BOTTOM_CONTEXT_REQUIRED",
      "BULLISH_SEPARATING_LINES_CONTEXT",
      "BEARISH_HARAMI_CONTEXT",
      "DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT",
      "DOJI_TOP_CONTEXT_REQUIRED",
      "THREE_MOUNTAINS_CONTEXT_REQUIRED",
      "SMALL_BODY_CLUSTER",
      "LOW_DIRECTIONAL_PROGRESS"
    ],
    "window_evidence": [
      {
        "source": "NISON",
        "code": "BEARISH_ENGULFING_CONTEXT",
        "description": "Bearish body engulfs the preceding bullish body",
        "contribution": -0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T01:00:00Z",
          "timestamp": "2026-07-08T01:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T01:00:00Z",
          "timestamp": "2026-07-08T01:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T01:00:00Z",
          "timestamp": "2026-07-08T01:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_ENGULFING_CONTEXT",
        "description": "Bullish body engulfs the preceding bearish body",
        "contribution": 0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T02:15:00Z",
          "timestamp": "2026-07-08T02:30:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T02:15:00Z",
          "timestamp": "2026-07-08T02:30:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T02:15:00Z",
          "timestamp": "2026-07-08T02:30:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_ENGULFING_CONTEXT",
        "description": "Bullish body engulfs the preceding bearish body",
        "contribution": 0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T04:00:00Z",
          "timestamp": "2026-07-08T04:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T04:00:00Z",
          "timestamp": "2026-07-08T04:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T04:00:00Z",
          "timestamp": "2026-07-08T04:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_ENGULFING_CONTEXT",
        "description": "Bearish body engulfs the preceding bullish body",
        "contribution": -0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T04:15:00Z",
          "timestamp": "2026-07-08T04:30:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T04:15:00Z",
          "timestamp": "2026-07-08T04:30:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T04:15:00Z",
          "timestamp": "2026-07-08T04:30:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_ENGULFING_CONTEXT",
        "description": "Bearish body engulfs the preceding bullish body",
        "contribution": -0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T05:00:00Z",
          "timestamp": "2026-07-08T05:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T05:00:00Z",
          "timestamp": "2026-07-08T05:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T05:00:00Z",
          "timestamp": "2026-07-08T05:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_ENGULFING_CONTEXT",
        "description": "Bullish body engulfs the preceding bearish body",
        "contribution": 0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T07:15:00Z",
          "timestamp": "2026-07-08T07:30:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T07:15:00Z",
          "timestamp": "2026-07-08T07:30:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T07:15:00Z",
          "timestamp": "2026-07-08T07:30:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_ENGULFING_CONTEXT",
        "description": "Bullish body engulfs the preceding bearish body",
        "contribution": 0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T08:30:00Z",
          "timestamp": "2026-07-08T08:45:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T08:30:00Z",
          "timestamp": "2026-07-08T08:45:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T08:30:00Z",
          "timestamp": "2026-07-08T08:45:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_ENGULFING_CONTEXT",
        "description": "Bullish body engulfs the preceding bearish body",
        "contribution": 0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T09:15:00Z",
          "timestamp": "2026-07-08T09:30:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T09:15:00Z",
          "timestamp": "2026-07-08T09:30:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T09:15:00Z",
          "timestamp": "2026-07-08T09:30:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_ENGULFING_CONTEXT",
        "description": "Bearish body engulfs the preceding bullish body",
        "contribution": -0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T09:30:00Z",
          "timestamp": "2026-07-08T09:45:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T09:30:00Z",
          "timestamp": "2026-07-08T09:45:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T09:30:00Z",
          "timestamp": "2026-07-08T09:45:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_ENGULFING_CONTEXT",
        "description": "Bullish body engulfs the preceding bearish body",
        "contribution": 0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T10:00:00Z",
          "timestamp": "2026-07-08T10:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T10:00:00Z",
          "timestamp": "2026-07-08T10:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T10:00:00Z",
          "timestamp": "2026-07-08T10:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_ENGULFING_CONTEXT",
        "description": "Bullish body engulfs the preceding bearish body",
        "contribution": 0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T11:15:00Z",
          "timestamp": "2026-07-08T11:30:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T11:15:00Z",
          "timestamp": "2026-07-08T11:30:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T11:15:00Z",
          "timestamp": "2026-07-08T11:30:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_ENGULFING_CONTEXT",
        "description": "Bearish body engulfs the preceding bullish body",
        "contribution": -0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T14:45:00Z",
          "timestamp": "2026-07-08T15:00:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T14:45:00Z",
          "timestamp": "2026-07-08T15:00:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T14:45:00Z",
          "timestamp": "2026-07-08T15:00:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_ENGULFING_CONTEXT",
        "description": "Bearish body engulfs the preceding bullish body",
        "contribution": -0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T16:45:00Z",
          "timestamp": "2026-07-08T17:00:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T16:45:00Z",
          "timestamp": "2026-07-08T17:00:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T16:45:00Z",
          "timestamp": "2026-07-08T17:00:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_ENGULFING_CONTEXT",
        "description": "Bullish body engulfs the preceding bearish body",
        "contribution": 0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T17:00:00Z",
          "timestamp": "2026-07-08T17:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T17:00:00Z",
          "timestamp": "2026-07-08T17:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T17:00:00Z",
          "timestamp": "2026-07-08T17:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_ENGULFING_CONTEXT",
        "description": "Bearish body engulfs the preceding bullish body",
        "contribution": -0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T18:00:00Z",
          "timestamp": "2026-07-08T18:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T18:00:00Z",
          "timestamp": "2026-07-08T18:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T18:00:00Z",
          "timestamp": "2026-07-08T18:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_ENGULFING_CONTEXT",
        "description": "Bullish body engulfs the preceding bearish body",
        "contribution": 0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T18:30:00Z",
          "timestamp": "2026-07-08T18:45:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T18:30:00Z",
          "timestamp": "2026-07-08T18:45:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T18:30:00Z",
          "timestamp": "2026-07-08T18:45:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_ENGULFING_CONTEXT",
        "description": "Bearish body engulfs the preceding bullish body",
        "contribution": -0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T20:00:00Z",
          "timestamp": "2026-07-08T20:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T20:00:00Z",
          "timestamp": "2026-07-08T20:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T20:00:00Z",
          "timestamp": "2026-07-08T20:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_ENGULFING_CONTEXT",
        "description": "Bearish body engulfs the preceding bullish body",
        "contribution": -0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T20:45:00Z",
          "timestamp": "2026-07-08T21:00:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T20:45:00Z",
          "timestamp": "2026-07-08T21:00:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T20:45:00Z",
          "timestamp": "2026-07-08T21:00:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LEGGED_DOJI_CONTEXT",
        "description": "Doji has extended upper and lower shadows",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T00:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "RICKSHAW_MAN_DOJI_CONTEXT",
        "description": "Long-legged doji opens and closes near range midpoint",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T00:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bearish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T00:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T00:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bearish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T01:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T01:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "HANGING_MAN_LIKE_CONTEXT_REQUIRED",
        "description": "Hanging-man-like shape requires a preceding rise",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T02:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T02:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T02:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "DRAGONFLY_DOJI_CONTEXT",
        "description": "Doji lies near the high with an extended lower shadow",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T02:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bullish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T03:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T03:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bearish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T03:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T03:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bearish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T03:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T03:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LEGGED_DOJI_CONTEXT",
        "description": "Doji has extended upper and lower shadows",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T05:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "RICKSHAW_MAN_DOJI_CONTEXT",
        "description": "Long-legged doji opens and closes near range midpoint",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T05:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "HANGING_MAN_LIKE_CONTEXT_REQUIRED",
        "description": "Hanging-man-like shape requires a preceding rise",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T07:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T07:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T07:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bearish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T08:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T08:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED",
        "description": "Inverted-hammer-like shape requires a preceding decline",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T08:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T08:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T08:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LEGGED_DOJI_CONTEXT",
        "description": "Doji has extended upper and lower shadows",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T09:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "RICKSHAW_MAN_DOJI_CONTEXT",
        "description": "Long-legged doji opens and closes near range midpoint",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T09:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bearish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T09:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T09:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bullish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T11:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T11:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LEGGED_DOJI_CONTEXT",
        "description": "Doji has extended upper and lower shadows",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T11:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "RICKSHAW_MAN_DOJI_CONTEXT",
        "description": "Long-legged doji opens and closes near range midpoint",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T11:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bearish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T12:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T12:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "HANGING_MAN_LIKE_CONTEXT_REQUIRED",
        "description": "Hanging-man-like shape requires a preceding rise",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T13:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T13:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T13:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bullish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T13:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T13:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bearish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T15:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T15:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bullish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T16:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T16:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LEGGED_DOJI_CONTEXT",
        "description": "Doji has extended upper and lower shadows",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T16:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "RICKSHAW_MAN_DOJI_CONTEXT",
        "description": "Long-legged doji opens and closes near range midpoint",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T16:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bullish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T17:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T17:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bearish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T17:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T17:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bearish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T18:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T18:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bullish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T19:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T19:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LEGGED_DOJI_CONTEXT",
        "description": "Doji has extended upper and lower shadows",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T20:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "RICKSHAW_MAN_DOJI_CONTEXT",
        "description": "Long-legged doji opens and closes near range midpoint",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T20:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bearish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T20:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T20:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bearish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T21:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T21:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bullish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T22:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T22:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_TOP_CONTEXT_REQUIRED",
        "description": "Adjacent highs form a tweezer-top candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T00:00:00Z",
            "2026-07-08T00:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T00:00:00Z",
            "2026-07-08T00:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T00:00:00Z",
            "2026-07-08T00:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_HARAMI_CONTEXT",
        "description": "Small body is contained by the preceding bearish body",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T00:45:00Z",
            "2026-07-08T01:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T00:45:00Z",
            "2026-07-08T01:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T00:45:00Z",
            "2026-07-08T01:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "HARAMI_CROSS_CONTEXT",
        "description": "Doji body is contained by the preceding long body",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T00:45:00Z",
            "2026-07-08T01:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_SEPARATING_LINES_CONTEXT",
        "description": "Bullish and bearish candles share approximately one open",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T01:00:00Z",
            "2026-07-08T01:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T01:00:00Z",
            "2026-07-08T01:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_BOTTOM_CONTEXT_REQUIRED",
        "description": "Adjacent lows form a tweezer-bottom candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T02:00:00Z",
            "2026-07-08T02:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T02:00:00Z",
            "2026-07-08T02:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T02:00:00Z",
            "2026-07-08T02:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_SEPARATING_LINES_CONTEXT",
        "description": "Bearish and bullish candles share approximately one open",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T02:15:00Z",
            "2026-07-08T02:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T02:15:00Z",
            "2026-07-08T02:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_HARAMI_CONTEXT",
        "description": "Small body is contained by the preceding bullish body",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T03:00:00Z",
            "2026-07-08T03:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T03:00:00Z",
            "2026-07-08T03:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T03:00:00Z",
            "2026-07-08T03:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_SEPARATING_LINES_CONTEXT",
        "description": "Bearish and bullish candles share approximately one open",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T04:00:00Z",
            "2026-07-08T04:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T04:00:00Z",
            "2026-07-08T04:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_TOP_CONTEXT_REQUIRED",
        "description": "Adjacent highs form a tweezer-top candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T04:15:00Z",
            "2026-07-08T04:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T04:15:00Z",
            "2026-07-08T04:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T04:15:00Z",
            "2026-07-08T04:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_TOP_CONTEXT_REQUIRED",
        "description": "Adjacent highs form a tweezer-top candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T05:00:00Z",
            "2026-07-08T05:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T05:00:00Z",
            "2026-07-08T05:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T05:00:00Z",
            "2026-07-08T05:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_HARAMI_CONTEXT",
        "description": "Small body is contained by the preceding bearish body",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T05:30:00Z",
            "2026-07-08T05:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T05:30:00Z",
            "2026-07-08T05:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T05:30:00Z",
            "2026-07-08T05:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "HARAMI_CROSS_CONTEXT",
        "description": "Doji body is contained by the preceding long body",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T05:30:00Z",
            "2026-07-08T05:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_TOP_CONTEXT_REQUIRED",
        "description": "Adjacent highs form a tweezer-top candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T07:00:00Z",
            "2026-07-08T07:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T07:00:00Z",
            "2026-07-08T07:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T07:00:00Z",
            "2026-07-08T07:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_SEPARATING_LINES_CONTEXT",
        "description": "Bearish and bullish candles share approximately one open",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T07:15:00Z",
            "2026-07-08T07:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T07:15:00Z",
            "2026-07-08T07:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_SEPARATING_LINES_CONTEXT",
        "description": "Bullish and bearish candles share approximately one open",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T08:00:00Z",
            "2026-07-08T08:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T08:00:00Z",
            "2026-07-08T08:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_HARAMI_CONTEXT",
        "description": "Small body is contained by the preceding bullish body",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T10:15:00Z",
            "2026-07-08T10:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T10:15:00Z",
            "2026-07-08T10:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T10:15:00Z",
            "2026-07-08T10:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_BOTTOM_CONTEXT_REQUIRED",
        "description": "Adjacent lows form a tweezer-bottom candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T11:15:00Z",
            "2026-07-08T11:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T11:15:00Z",
            "2026-07-08T11:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T11:15:00Z",
            "2026-07-08T11:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT",
        "description": "Doji follows a long bullish body",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T11:30:00Z",
            "2026-07-08T11:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T11:30:00Z",
            "2026-07-08T11:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T11:30:00Z",
            "2026-07-08T11:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "DOJI_TOP_CONTEXT_REQUIRED",
        "description": "Doji after bullish expansion requires top context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T11:30:00Z",
            "2026-07-08T11:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_TOP_CONTEXT_REQUIRED",
        "description": "Adjacent highs form a tweezer-top candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T11:45:00Z",
            "2026-07-08T12:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T11:45:00Z",
            "2026-07-08T12:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T11:45:00Z",
            "2026-07-08T12:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_HARAMI_CONTEXT",
        "description": "Small body is contained by the preceding bullish body",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T13:30:00Z",
            "2026-07-08T13:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T13:30:00Z",
            "2026-07-08T13:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T13:30:00Z",
            "2026-07-08T13:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "HARAMI_CROSS_CONTEXT",
        "description": "Doji body is contained by the preceding long body",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T13:30:00Z",
            "2026-07-08T13:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_TOP_CONTEXT_REQUIRED",
        "description": "Adjacent highs form a tweezer-top candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T13:30:00Z",
            "2026-07-08T13:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT",
        "description": "Doji follows a long bullish body",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T13:30:00Z",
            "2026-07-08T13:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "DOJI_TOP_CONTEXT_REQUIRED",
        "description": "Doji after bullish expansion requires top context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T13:30:00Z",
            "2026-07-08T13:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_SEPARATING_LINES_CONTEXT",
        "description": "Bullish and bearish candles share approximately one open",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T13:45:00Z",
            "2026-07-08T14:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T13:45:00Z",
            "2026-07-08T14:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_TOP_CONTEXT_REQUIRED",
        "description": "Adjacent highs form a tweezer-top candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T14:00:00Z",
            "2026-07-08T14:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T14:00:00Z",
            "2026-07-08T14:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T14:00:00Z",
            "2026-07-08T14:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_BOTTOM_CONTEXT_REQUIRED",
        "description": "Adjacent lows form a tweezer-bottom candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T14:15:00Z",
            "2026-07-08T14:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T14:15:00Z",
            "2026-07-08T14:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T14:15:00Z",
            "2026-07-08T14:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_BOTTOM_CONTEXT_REQUIRED",
        "description": "Adjacent lows form a tweezer-bottom candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T14:45:00Z",
            "2026-07-08T15:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T14:45:00Z",
            "2026-07-08T15:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T14:45:00Z",
            "2026-07-08T15:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_SEPARATING_LINES_CONTEXT",
        "description": "Bullish and bearish candles share approximately one open",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T16:45:00Z",
            "2026-07-08T17:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T16:45:00Z",
            "2026-07-08T17:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_BOTTOM_CONTEXT_REQUIRED",
        "description": "Adjacent lows form a tweezer-bottom candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T17:00:00Z",
            "2026-07-08T17:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T17:00:00Z",
            "2026-07-08T17:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T17:00:00Z",
            "2026-07-08T17:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_BOTTOM_CONTEXT_REQUIRED",
        "description": "Adjacent lows form a tweezer-bottom candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T18:00:00Z",
            "2026-07-08T18:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T18:00:00Z",
            "2026-07-08T18:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T18:00:00Z",
            "2026-07-08T18:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_BOTTOM_CONTEXT_REQUIRED",
        "description": "Adjacent lows form a tweezer-bottom candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T20:00:00Z",
            "2026-07-08T20:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T20:00:00Z",
            "2026-07-08T20:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T20:00:00Z",
            "2026-07-08T20:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_HARAMI_CONTEXT",
        "description": "Small body is contained by the preceding bearish body",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T20:30:00Z",
            "2026-07-08T20:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T20:30:00Z",
            "2026-07-08T20:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T20:30:00Z",
            "2026-07-08T20:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_BOTTOM_CONTEXT_REQUIRED",
        "description": "Adjacent lows form a tweezer-bottom candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T23:00:00Z",
            "2026-07-08T23:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T23:00:00Z",
            "2026-07-08T23:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T23:00:00Z",
            "2026-07-08T23:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_TOP_CONTEXT_REQUIRED",
        "description": "Adjacent highs form a tweezer-top candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T23:15:00Z",
            "2026-07-08T23:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T23:15:00Z",
            "2026-07-08T23:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T23:15:00Z",
            "2026-07-08T23:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "THREE_MOUNTAINS_CONTEXT_REQUIRED",
        "description": "Three comparable local peaks form a three-mountains candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T20:00:00Z",
            "2026-07-08T22:00:00Z",
            "2026-07-08T23:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T20:00:00Z",
            "2026-07-08T22:00:00Z",
            "2026-07-08T23:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T20:00:00Z",
            "2026-07-08T22:00:00Z",
            "2026-07-08T23:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "ENGINE_TREND",
        "code": "SMALL_BODY_CLUSTER",
        "description": "Small real bodies cluster in the selected window",
        "contribution": 0.0,
        "metadata": {
          "evidence_origin": "ENGINE_TREND_HEURISTIC",
          "book_attribution": false,
          "count": 35,
          "ratio": 0.3645833333333333
        }
      },
      {
        "source": "ENGINE_TREND",
        "code": "LOW_DIRECTIONAL_PROGRESS",
        "description": "Body contraction suggests limited directional progress",
        "contribution": 0.0,
        "metadata": {
          "evidence_origin": "ENGINE_TREND_HEURISTIC",
          "book_attribution": false,
          "count": 35,
          "ratio": 0.3645833333333333
        }
      }
    ],
    "all_evidence": [
      {
        "source": "NISON",
        "code": "LONG_LOWER_SHADOW_REJECTION",
        "description": "Extended lower shadow provides rejection evidence",
        "contribution": 0.05,
        "metadata": {
          "timestamp": "2026-07-08T00:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T00:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "DOJI_INDECISION",
        "description": "Doji morphology provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T00:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LOWER_SHADOW_REJECTION",
        "description": "Extended lower shadow provides rejection evidence",
        "contribution": 0.05,
        "metadata": {
          "timestamp": "2026-07-08T00:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T00:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SPINNING_TOP_INDECISION",
        "description": "Spinning-top morphology provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T00:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "STRONG_BEARISH_CANDLE_BODY",
        "description": "Strong bearish real body",
        "contribution": -0.1,
        "metadata": {
          "timestamp": "2026-07-08T00:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_LOW",
        "description": "Close is near the candle low",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T00:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LOWER_SHADOW_REJECTION",
        "description": "Extended lower shadow provides rejection evidence",
        "contribution": 0.05,
        "metadata": {
          "timestamp": "2026-07-08T01:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T01:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_HIGH",
        "description": "Close is near the candle high",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T01:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "DOJI_INDECISION",
        "description": "Doji morphology provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T01:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "STRONG_BEARISH_CANDLE_BODY",
        "description": "Strong bearish real body",
        "contribution": -0.1,
        "metadata": {
          "timestamp": "2026-07-08T01:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_LOW",
        "description": "Close is near the candle low",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T01:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LOWER_SHADOW_REJECTION",
        "description": "Extended lower shadow provides rejection evidence",
        "contribution": 0.05,
        "metadata": {
          "timestamp": "2026-07-08T02:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T02:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "DOJI_INDECISION",
        "description": "Doji morphology provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T02:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LOWER_SHADOW_REJECTION",
        "description": "Extended lower shadow provides rejection evidence",
        "contribution": 0.05,
        "metadata": {
          "timestamp": "2026-07-08T02:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T02:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_HIGH",
        "description": "Close is near the candle high",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T02:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "DOJI_INDECISION",
        "description": "Doji morphology provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T02:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED",
        "description": "Hammer-like shape requires trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T02:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T02:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T03:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SPINNING_TOP_INDECISION",
        "description": "Spinning-top morphology provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T03:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LOWER_SHADOW_REJECTION",
        "description": "Extended lower shadow provides rejection evidence",
        "contribution": 0.05,
        "metadata": {
          "timestamp": "2026-07-08T04:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T04:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "DOJI_INDECISION",
        "description": "Doji morphology provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T04:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_HIGH",
        "description": "Close is near the candle high",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T04:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "STRONG_BEARISH_CANDLE_BODY",
        "description": "Strong bearish real body",
        "contribution": -0.1,
        "metadata": {
          "timestamp": "2026-07-08T04:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_LOW",
        "description": "Close is near the candle low",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T04:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LOWER_SHADOW_REJECTION",
        "description": "Extended lower shadow provides rejection evidence",
        "contribution": 0.05,
        "metadata": {
          "timestamp": "2026-07-08T04:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T04:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_HIGH",
        "description": "Close is near the candle high",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T04:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "DOJI_INDECISION",
        "description": "Doji morphology provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T04:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T05:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SPINNING_TOP_INDECISION",
        "description": "Spinning-top morphology provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T05:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_LOW",
        "description": "Close is near the candle low",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T05:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "STRONG_BEARISH_CANDLE_BODY",
        "description": "Strong bearish real body",
        "contribution": -0.1,
        "metadata": {
          "timestamp": "2026-07-08T05:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_LOW",
        "description": "Close is near the candle low",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T05:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_UPPER_SHADOW_REJECTION",
        "description": "Extended upper shadow provides rejection evidence",
        "contribution": -0.05,
        "metadata": {
          "timestamp": "2026-07-08T05:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T05:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "DOJI_INDECISION",
        "description": "Doji morphology provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T05:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LOWER_SHADOW_REJECTION",
        "description": "Extended lower shadow provides rejection evidence",
        "contribution": 0.05,
        "metadata": {
          "timestamp": "2026-07-08T06:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LOWER_SHADOW_REJECTION",
        "description": "Extended lower shadow provides rejection evidence",
        "contribution": 0.05,
        "metadata": {
          "timestamp": "2026-07-08T06:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T06:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LOWER_SHADOW_REJECTION",
        "description": "Extended lower shadow provides rejection evidence",
        "contribution": 0.05,
        "metadata": {
          "timestamp": "2026-07-08T07:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T07:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_HIGH",
        "description": "Close is near the candle high",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T07:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SPINNING_TOP_INDECISION",
        "description": "Spinning-top morphology provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T07:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED",
        "description": "Hammer-like shape requires trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T07:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T07:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LOWER_SHADOW_REJECTION",
        "description": "Extended lower shadow provides rejection evidence",
        "contribution": 0.05,
        "metadata": {
          "timestamp": "2026-07-08T07:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T07:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "DOJI_INDECISION",
        "description": "Doji morphology provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T07:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T07:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_HIGH",
        "description": "Close is near the candle high",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T07:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T08:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "STRONG_BEARISH_CANDLE_BODY",
        "description": "Strong bearish real body",
        "contribution": -0.1,
        "metadata": {
          "timestamp": "2026-07-08T08:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_LOW",
        "description": "Close is near the candle low",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T08:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T08:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SPINNING_TOP_INDECISION",
        "description": "Spinning-top morphology provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T08:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_UPPER_SHADOW_REJECTION",
        "description": "Extended upper shadow provides rejection evidence",
        "contribution": -0.05,
        "metadata": {
          "timestamp": "2026-07-08T08:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T08:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_LOW",
        "description": "Close is near the candle low",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T08:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SPINNING_TOP_INDECISION",
        "description": "Spinning-top morphology provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T08:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED",
        "description": "Shooting-star-like shape requires trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T08:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T08:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_UPPER_SHADOW_REJECTION",
        "description": "Extended upper shadow provides rejection evidence",
        "contribution": -0.05,
        "metadata": {
          "timestamp": "2026-07-08T09:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T09:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "DOJI_INDECISION",
        "description": "Doji morphology provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T09:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LOWER_SHADOW_REJECTION",
        "description": "Extended lower shadow provides rejection evidence",
        "contribution": 0.05,
        "metadata": {
          "timestamp": "2026-07-08T09:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T09:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_HIGH",
        "description": "Close is near the candle high",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T09:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SPINNING_TOP_INDECISION",
        "description": "Spinning-top morphology provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T09:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "STRONG_BEARISH_CANDLE_BODY",
        "description": "Strong bearish real body",
        "contribution": -0.1,
        "metadata": {
          "timestamp": "2026-07-08T09:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_LOW",
        "description": "Close is near the candle low",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T09:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "STRONG_BULLISH_CANDLE_BODY",
        "description": "Strong bullish real body",
        "contribution": 0.1,
        "metadata": {
          "timestamp": "2026-07-08T10:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_HIGH",
        "description": "Close is near the candle high",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T10:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_UPPER_SHADOW_REJECTION",
        "description": "Extended upper shadow provides rejection evidence",
        "contribution": -0.05,
        "metadata": {
          "timestamp": "2026-07-08T10:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T10:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SPINNING_TOP_INDECISION",
        "description": "Spinning-top morphology provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T10:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LOWER_SHADOW_REJECTION",
        "description": "Extended lower shadow provides rejection evidence",
        "contribution": 0.05,
        "metadata": {
          "timestamp": "2026-07-08T10:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_LOW",
        "description": "Close is near the candle low",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T11:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T11:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "DOJI_INDECISION",
        "description": "Doji morphology provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T11:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T12:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SPINNING_TOP_INDECISION",
        "description": "Spinning-top morphology provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T12:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T12:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SPINNING_TOP_INDECISION",
        "description": "Spinning-top morphology provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T12:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "STRONG_BEARISH_CANDLE_BODY",
        "description": "Strong bearish real body",
        "contribution": -0.1,
        "metadata": {
          "timestamp": "2026-07-08T12:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_LOW",
        "description": "Close is near the candle low",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T12:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_LOW",
        "description": "Close is near the candle low",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T12:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T13:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LOWER_SHADOW_REJECTION",
        "description": "Extended lower shadow provides rejection evidence",
        "contribution": 0.05,
        "metadata": {
          "timestamp": "2026-07-08T13:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T13:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED",
        "description": "Hammer-like shape requires trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T13:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T13:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "STRONG_BULLISH_CANDLE_BODY",
        "description": "Strong bullish real body",
        "contribution": 0.1,
        "metadata": {
          "timestamp": "2026-07-08T13:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_HIGH",
        "description": "Close is near the candle high",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T13:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LOWER_SHADOW_REJECTION",
        "description": "Extended lower shadow provides rejection evidence",
        "contribution": 0.05,
        "metadata": {
          "timestamp": "2026-07-08T13:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T13:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "DOJI_INDECISION",
        "description": "Doji morphology provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T13:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T14:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SPINNING_TOP_INDECISION",
        "description": "Spinning-top morphology provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T14:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T14:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T14:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_HIGH",
        "description": "Close is near the candle high",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T14:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SPINNING_TOP_INDECISION",
        "description": "Spinning-top morphology provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T14:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "STRONG_BEARISH_CANDLE_BODY",
        "description": "Strong bearish real body",
        "contribution": -0.1,
        "metadata": {
          "timestamp": "2026-07-08T15:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_LOW",
        "description": "Close is near the candle low",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T15:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_LOW",
        "description": "Close is near the candle low",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T15:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "STRONG_BULLISH_CANDLE_BODY",
        "description": "Strong bullish real body",
        "contribution": 0.1,
        "metadata": {
          "timestamp": "2026-07-08T15:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_HIGH",
        "description": "Close is near the candle high",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T15:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "STRONG_BULLISH_CANDLE_BODY",
        "description": "Strong bullish real body",
        "contribution": 0.1,
        "metadata": {
          "timestamp": "2026-07-08T16:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_HIGH",
        "description": "Close is near the candle high",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T16:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T16:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SPINNING_TOP_INDECISION",
        "description": "Spinning-top morphology provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T16:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_HIGH",
        "description": "Close is near the candle high",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T16:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T16:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "DOJI_INDECISION",
        "description": "Doji morphology provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T16:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "STRONG_BEARISH_CANDLE_BODY",
        "description": "Strong bearish real body",
        "contribution": -0.1,
        "metadata": {
          "timestamp": "2026-07-08T17:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_LOW",
        "description": "Close is near the candle low",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T17:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "STRONG_BULLISH_CANDLE_BODY",
        "description": "Strong bullish real body",
        "contribution": 0.1,
        "metadata": {
          "timestamp": "2026-07-08T17:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_HIGH",
        "description": "Close is near the candle high",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T17:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_LOW",
        "description": "Close is near the candle low",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T17:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "STRONG_BEARISH_CANDLE_BODY",
        "description": "Strong bearish real body",
        "contribution": -0.1,
        "metadata": {
          "timestamp": "2026-07-08T17:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_LOW",
        "description": "Close is near the candle low",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T17:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_HIGH",
        "description": "Close is near the candle high",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T18:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "STRONG_BEARISH_CANDLE_BODY",
        "description": "Strong bearish real body",
        "contribution": -0.1,
        "metadata": {
          "timestamp": "2026-07-08T18:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_LOW",
        "description": "Close is near the candle low",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T18:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_LOW",
        "description": "Close is near the candle low",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T19:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "STRONG_BULLISH_CANDLE_BODY",
        "description": "Strong bullish real body",
        "contribution": 0.1,
        "metadata": {
          "timestamp": "2026-07-08T19:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_HIGH",
        "description": "Close is near the candle high",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T19:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LOWER_SHADOW_REJECTION",
        "description": "Extended lower shadow provides rejection evidence",
        "contribution": 0.05,
        "metadata": {
          "timestamp": "2026-07-08T19:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T19:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_HIGH",
        "description": "Close is near the candle high",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T19:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SPINNING_TOP_INDECISION",
        "description": "Spinning-top morphology provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T19:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T20:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "DOJI_INDECISION",
        "description": "Doji morphology provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T20:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "STRONG_BEARISH_CANDLE_BODY",
        "description": "Strong bearish real body",
        "contribution": -0.1,
        "metadata": {
          "timestamp": "2026-07-08T20:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_LOW",
        "description": "Close is near the candle low",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T20:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LOWER_SHADOW_REJECTION",
        "description": "Extended lower shadow provides rejection evidence",
        "contribution": 0.05,
        "metadata": {
          "timestamp": "2026-07-08T20:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T20:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SPINNING_TOP_INDECISION",
        "description": "Spinning-top morphology provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T20:45:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "STRONG_BEARISH_CANDLE_BODY",
        "description": "Strong bearish real body",
        "contribution": -0.1,
        "metadata": {
          "timestamp": "2026-07-08T21:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_LOW",
        "description": "Close is near the candle low",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T21:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_HIGH",
        "description": "Close is near the candle high",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T21:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_HIGH",
        "description": "Close is near the candle high",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T21:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_UPPER_SHADOW_REJECTION",
        "description": "Extended upper shadow provides rejection evidence",
        "contribution": -0.05,
        "metadata": {
          "timestamp": "2026-07-08T22:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "SMALL_BODY_INDECISION",
        "description": "Small real body provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T22:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_LOW",
        "description": "Close is near the candle low",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T22:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "DOJI_INDECISION",
        "description": "Doji morphology provides indecision evidence",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T22:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_HIGH",
        "description": "Close is near the candle high",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T22:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LOWER_SHADOW_REJECTION",
        "description": "Extended lower shadow provides rejection evidence",
        "contribution": 0.05,
        "metadata": {
          "timestamp": "2026-07-08T22:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_HIGH",
        "description": "Close is near the candle high",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T22:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_HIGH",
        "description": "Close is near the candle high",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T23:00:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LOWER_SHADOW_REJECTION",
        "description": "Extended lower shadow provides rejection evidence",
        "contribution": 0.05,
        "metadata": {
          "timestamp": "2026-07-08T23:15:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LOWER_SHADOW_REJECTION",
        "description": "Extended lower shadow provides rejection evidence",
        "contribution": 0.05,
        "metadata": {
          "timestamp": "2026-07-08T23:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "CLOSE_NEAR_HIGH",
        "description": "Close is near the candle high",
        "contribution": 0.0,
        "metadata": {
          "timestamp": "2026-07-08T23:30:00Z"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_ENGULFING_CONTEXT",
        "description": "Bearish body engulfs the preceding bullish body",
        "contribution": -0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T01:00:00Z",
          "timestamp": "2026-07-08T01:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T01:00:00Z",
          "timestamp": "2026-07-08T01:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T01:00:00Z",
          "timestamp": "2026-07-08T01:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_ENGULFING_CONTEXT",
        "description": "Bullish body engulfs the preceding bearish body",
        "contribution": 0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T02:15:00Z",
          "timestamp": "2026-07-08T02:30:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T02:15:00Z",
          "timestamp": "2026-07-08T02:30:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T02:15:00Z",
          "timestamp": "2026-07-08T02:30:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_ENGULFING_CONTEXT",
        "description": "Bullish body engulfs the preceding bearish body",
        "contribution": 0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T04:00:00Z",
          "timestamp": "2026-07-08T04:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T04:00:00Z",
          "timestamp": "2026-07-08T04:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T04:00:00Z",
          "timestamp": "2026-07-08T04:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_ENGULFING_CONTEXT",
        "description": "Bearish body engulfs the preceding bullish body",
        "contribution": -0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T04:15:00Z",
          "timestamp": "2026-07-08T04:30:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T04:15:00Z",
          "timestamp": "2026-07-08T04:30:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T04:15:00Z",
          "timestamp": "2026-07-08T04:30:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_ENGULFING_CONTEXT",
        "description": "Bearish body engulfs the preceding bullish body",
        "contribution": -0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T05:00:00Z",
          "timestamp": "2026-07-08T05:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T05:00:00Z",
          "timestamp": "2026-07-08T05:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T05:00:00Z",
          "timestamp": "2026-07-08T05:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_ENGULFING_CONTEXT",
        "description": "Bullish body engulfs the preceding bearish body",
        "contribution": 0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T07:15:00Z",
          "timestamp": "2026-07-08T07:30:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T07:15:00Z",
          "timestamp": "2026-07-08T07:30:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T07:15:00Z",
          "timestamp": "2026-07-08T07:30:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_ENGULFING_CONTEXT",
        "description": "Bullish body engulfs the preceding bearish body",
        "contribution": 0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T08:30:00Z",
          "timestamp": "2026-07-08T08:45:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T08:30:00Z",
          "timestamp": "2026-07-08T08:45:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T08:30:00Z",
          "timestamp": "2026-07-08T08:45:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_ENGULFING_CONTEXT",
        "description": "Bullish body engulfs the preceding bearish body",
        "contribution": 0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T09:15:00Z",
          "timestamp": "2026-07-08T09:30:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T09:15:00Z",
          "timestamp": "2026-07-08T09:30:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T09:15:00Z",
          "timestamp": "2026-07-08T09:30:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_ENGULFING_CONTEXT",
        "description": "Bearish body engulfs the preceding bullish body",
        "contribution": -0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T09:30:00Z",
          "timestamp": "2026-07-08T09:45:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T09:30:00Z",
          "timestamp": "2026-07-08T09:45:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T09:30:00Z",
          "timestamp": "2026-07-08T09:45:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_ENGULFING_CONTEXT",
        "description": "Bullish body engulfs the preceding bearish body",
        "contribution": 0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T10:00:00Z",
          "timestamp": "2026-07-08T10:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T10:00:00Z",
          "timestamp": "2026-07-08T10:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T10:00:00Z",
          "timestamp": "2026-07-08T10:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_ENGULFING_CONTEXT",
        "description": "Bullish body engulfs the preceding bearish body",
        "contribution": 0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T11:15:00Z",
          "timestamp": "2026-07-08T11:30:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T11:15:00Z",
          "timestamp": "2026-07-08T11:30:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T11:15:00Z",
          "timestamp": "2026-07-08T11:30:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_ENGULFING_CONTEXT",
        "description": "Bearish body engulfs the preceding bullish body",
        "contribution": -0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T14:45:00Z",
          "timestamp": "2026-07-08T15:00:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T14:45:00Z",
          "timestamp": "2026-07-08T15:00:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T14:45:00Z",
          "timestamp": "2026-07-08T15:00:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_ENGULFING_CONTEXT",
        "description": "Bearish body engulfs the preceding bullish body",
        "contribution": -0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T16:45:00Z",
          "timestamp": "2026-07-08T17:00:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T16:45:00Z",
          "timestamp": "2026-07-08T17:00:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T16:45:00Z",
          "timestamp": "2026-07-08T17:00:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_ENGULFING_CONTEXT",
        "description": "Bullish body engulfs the preceding bearish body",
        "contribution": 0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T17:00:00Z",
          "timestamp": "2026-07-08T17:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T17:00:00Z",
          "timestamp": "2026-07-08T17:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T17:00:00Z",
          "timestamp": "2026-07-08T17:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_ENGULFING_CONTEXT",
        "description": "Bearish body engulfs the preceding bullish body",
        "contribution": -0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T18:00:00Z",
          "timestamp": "2026-07-08T18:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T18:00:00Z",
          "timestamp": "2026-07-08T18:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T18:00:00Z",
          "timestamp": "2026-07-08T18:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_ENGULFING_CONTEXT",
        "description": "Bullish body engulfs the preceding bearish body",
        "contribution": 0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T18:30:00Z",
          "timestamp": "2026-07-08T18:45:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T18:30:00Z",
          "timestamp": "2026-07-08T18:45:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T18:30:00Z",
          "timestamp": "2026-07-08T18:45:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_ENGULFING_CONTEXT",
        "description": "Bearish body engulfs the preceding bullish body",
        "contribution": -0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T20:00:00Z",
          "timestamp": "2026-07-08T20:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T20:00:00Z",
          "timestamp": "2026-07-08T20:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T20:00:00Z",
          "timestamp": "2026-07-08T20:15:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_ENGULFING_CONTEXT",
        "description": "Bearish body engulfs the preceding bullish body",
        "contribution": -0.1,
        "metadata": {
          "previous_timestamp": "2026-07-08T20:45:00Z",
          "timestamp": "2026-07-08T21:00:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "ENGULFING_WITHOUT_FOLLOW_THROUGH",
        "description": "Engulfing follow-through is not evaluated at this stage",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T20:45:00Z",
          "timestamp": "2026-07-08T21:00:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Candle shape cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "previous_timestamp": "2026-07-08T20:45:00Z",
          "timestamp": "2026-07-08T21:00:00Z",
          "trend_context_evaluated": false,
          "follow_through_evaluated": false
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LEGGED_DOJI_CONTEXT",
        "description": "Doji has extended upper and lower shadows",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T00:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "RICKSHAW_MAN_DOJI_CONTEXT",
        "description": "Long-legged doji opens and closes near range midpoint",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T00:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bearish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T00:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T00:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bearish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T01:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T01:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "HANGING_MAN_LIKE_CONTEXT_REQUIRED",
        "description": "Hanging-man-like shape requires a preceding rise",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T02:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T02:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T02:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "DRAGONFLY_DOJI_CONTEXT",
        "description": "Doji lies near the high with an extended lower shadow",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T02:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bullish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T03:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T03:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bearish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T03:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T03:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bearish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T03:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T03:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LEGGED_DOJI_CONTEXT",
        "description": "Doji has extended upper and lower shadows",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T05:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "RICKSHAW_MAN_DOJI_CONTEXT",
        "description": "Long-legged doji opens and closes near range midpoint",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T05:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "HANGING_MAN_LIKE_CONTEXT_REQUIRED",
        "description": "Hanging-man-like shape requires a preceding rise",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T07:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T07:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T07:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bearish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T08:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T08:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED",
        "description": "Inverted-hammer-like shape requires a preceding decline",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T08:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T08:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T08:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LEGGED_DOJI_CONTEXT",
        "description": "Doji has extended upper and lower shadows",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T09:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "RICKSHAW_MAN_DOJI_CONTEXT",
        "description": "Long-legged doji opens and closes near range midpoint",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T09:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bearish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T09:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T09:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bullish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T11:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T11:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LEGGED_DOJI_CONTEXT",
        "description": "Doji has extended upper and lower shadows",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T11:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "RICKSHAW_MAN_DOJI_CONTEXT",
        "description": "Long-legged doji opens and closes near range midpoint",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T11:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bearish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T12:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T12:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "HANGING_MAN_LIKE_CONTEXT_REQUIRED",
        "description": "Hanging-man-like shape requires a preceding rise",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T13:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T13:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T13:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bullish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T13:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T13:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bearish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T15:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T15:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bullish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T16:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T16:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LEGGED_DOJI_CONTEXT",
        "description": "Doji has extended upper and lower shadows",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T16:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "RICKSHAW_MAN_DOJI_CONTEXT",
        "description": "Long-legged doji opens and closes near range midpoint",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T16:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bullish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T17:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T17:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bearish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T17:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T17:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bearish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T18:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T18:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bullish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T19:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T19:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "LONG_LEGGED_DOJI_CONTEXT",
        "description": "Doji has extended upper and lower shadows",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T20:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "RICKSHAW_MAN_DOJI_CONTEXT",
        "description": "Long-legged doji opens and closes near range midpoint",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T20:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bearish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T20:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T20:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bearish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T21:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T21:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_BELT_HOLD_CONTEXT_REQUIRED",
        "description": "Bullish belt-hold-like candle geometry",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T22:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T22:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_TOP_CONTEXT_REQUIRED",
        "description": "Adjacent highs form a tweezer-top candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T00:00:00Z",
            "2026-07-08T00:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T00:00:00Z",
            "2026-07-08T00:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T00:00:00Z",
            "2026-07-08T00:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_HARAMI_CONTEXT",
        "description": "Small body is contained by the preceding bearish body",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T00:45:00Z",
            "2026-07-08T01:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T00:45:00Z",
            "2026-07-08T01:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T00:45:00Z",
            "2026-07-08T01:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "HARAMI_CROSS_CONTEXT",
        "description": "Doji body is contained by the preceding long body",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T00:45:00Z",
            "2026-07-08T01:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_SEPARATING_LINES_CONTEXT",
        "description": "Bullish and bearish candles share approximately one open",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T01:00:00Z",
            "2026-07-08T01:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T01:00:00Z",
            "2026-07-08T01:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_BOTTOM_CONTEXT_REQUIRED",
        "description": "Adjacent lows form a tweezer-bottom candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T02:00:00Z",
            "2026-07-08T02:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T02:00:00Z",
            "2026-07-08T02:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T02:00:00Z",
            "2026-07-08T02:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_SEPARATING_LINES_CONTEXT",
        "description": "Bearish and bullish candles share approximately one open",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T02:15:00Z",
            "2026-07-08T02:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T02:15:00Z",
            "2026-07-08T02:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_HARAMI_CONTEXT",
        "description": "Small body is contained by the preceding bullish body",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T03:00:00Z",
            "2026-07-08T03:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T03:00:00Z",
            "2026-07-08T03:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T03:00:00Z",
            "2026-07-08T03:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_SEPARATING_LINES_CONTEXT",
        "description": "Bearish and bullish candles share approximately one open",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T04:00:00Z",
            "2026-07-08T04:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T04:00:00Z",
            "2026-07-08T04:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_TOP_CONTEXT_REQUIRED",
        "description": "Adjacent highs form a tweezer-top candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T04:15:00Z",
            "2026-07-08T04:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T04:15:00Z",
            "2026-07-08T04:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T04:15:00Z",
            "2026-07-08T04:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_TOP_CONTEXT_REQUIRED",
        "description": "Adjacent highs form a tweezer-top candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T05:00:00Z",
            "2026-07-08T05:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T05:00:00Z",
            "2026-07-08T05:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T05:00:00Z",
            "2026-07-08T05:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_HARAMI_CONTEXT",
        "description": "Small body is contained by the preceding bearish body",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T05:30:00Z",
            "2026-07-08T05:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T05:30:00Z",
            "2026-07-08T05:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T05:30:00Z",
            "2026-07-08T05:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "HARAMI_CROSS_CONTEXT",
        "description": "Doji body is contained by the preceding long body",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T05:30:00Z",
            "2026-07-08T05:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_TOP_CONTEXT_REQUIRED",
        "description": "Adjacent highs form a tweezer-top candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T07:00:00Z",
            "2026-07-08T07:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T07:00:00Z",
            "2026-07-08T07:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T07:00:00Z",
            "2026-07-08T07:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_SEPARATING_LINES_CONTEXT",
        "description": "Bearish and bullish candles share approximately one open",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T07:15:00Z",
            "2026-07-08T07:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T07:15:00Z",
            "2026-07-08T07:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_SEPARATING_LINES_CONTEXT",
        "description": "Bullish and bearish candles share approximately one open",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T08:00:00Z",
            "2026-07-08T08:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T08:00:00Z",
            "2026-07-08T08:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_HARAMI_CONTEXT",
        "description": "Small body is contained by the preceding bullish body",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T10:15:00Z",
            "2026-07-08T10:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T10:15:00Z",
            "2026-07-08T10:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T10:15:00Z",
            "2026-07-08T10:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_BOTTOM_CONTEXT_REQUIRED",
        "description": "Adjacent lows form a tweezer-bottom candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T11:15:00Z",
            "2026-07-08T11:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T11:15:00Z",
            "2026-07-08T11:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T11:15:00Z",
            "2026-07-08T11:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT",
        "description": "Doji follows a long bullish body",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T11:30:00Z",
            "2026-07-08T11:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T11:30:00Z",
            "2026-07-08T11:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T11:30:00Z",
            "2026-07-08T11:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "DOJI_TOP_CONTEXT_REQUIRED",
        "description": "Doji after bullish expansion requires top context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T11:30:00Z",
            "2026-07-08T11:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_TOP_CONTEXT_REQUIRED",
        "description": "Adjacent highs form a tweezer-top candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T11:45:00Z",
            "2026-07-08T12:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T11:45:00Z",
            "2026-07-08T12:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T11:45:00Z",
            "2026-07-08T12:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_HARAMI_CONTEXT",
        "description": "Small body is contained by the preceding bullish body",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T13:30:00Z",
            "2026-07-08T13:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T13:30:00Z",
            "2026-07-08T13:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T13:30:00Z",
            "2026-07-08T13:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "HARAMI_CROSS_CONTEXT",
        "description": "Doji body is contained by the preceding long body",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T13:30:00Z",
            "2026-07-08T13:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_TOP_CONTEXT_REQUIRED",
        "description": "Adjacent highs form a tweezer-top candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T13:30:00Z",
            "2026-07-08T13:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT",
        "description": "Doji follows a long bullish body",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T13:30:00Z",
            "2026-07-08T13:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "DOJI_TOP_CONTEXT_REQUIRED",
        "description": "Doji after bullish expansion requires top context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T13:30:00Z",
            "2026-07-08T13:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_SEPARATING_LINES_CONTEXT",
        "description": "Bullish and bearish candles share approximately one open",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T13:45:00Z",
            "2026-07-08T14:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T13:45:00Z",
            "2026-07-08T14:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_TOP_CONTEXT_REQUIRED",
        "description": "Adjacent highs form a tweezer-top candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T14:00:00Z",
            "2026-07-08T14:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T14:00:00Z",
            "2026-07-08T14:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T14:00:00Z",
            "2026-07-08T14:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_BOTTOM_CONTEXT_REQUIRED",
        "description": "Adjacent lows form a tweezer-bottom candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T14:15:00Z",
            "2026-07-08T14:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T14:15:00Z",
            "2026-07-08T14:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T14:15:00Z",
            "2026-07-08T14:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_BOTTOM_CONTEXT_REQUIRED",
        "description": "Adjacent lows form a tweezer-bottom candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T14:45:00Z",
            "2026-07-08T15:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T14:45:00Z",
            "2026-07-08T15:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T14:45:00Z",
            "2026-07-08T15:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BEARISH_SEPARATING_LINES_CONTEXT",
        "description": "Bullish and bearish candles share approximately one open",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T16:45:00Z",
            "2026-07-08T17:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T16:45:00Z",
            "2026-07-08T17:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_BOTTOM_CONTEXT_REQUIRED",
        "description": "Adjacent lows form a tweezer-bottom candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T17:00:00Z",
            "2026-07-08T17:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T17:00:00Z",
            "2026-07-08T17:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T17:00:00Z",
            "2026-07-08T17:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_BOTTOM_CONTEXT_REQUIRED",
        "description": "Adjacent lows form a tweezer-bottom candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T18:00:00Z",
            "2026-07-08T18:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T18:00:00Z",
            "2026-07-08T18:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T18:00:00Z",
            "2026-07-08T18:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_BOTTOM_CONTEXT_REQUIRED",
        "description": "Adjacent lows form a tweezer-bottom candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T20:00:00Z",
            "2026-07-08T20:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T20:00:00Z",
            "2026-07-08T20:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T20:00:00Z",
            "2026-07-08T20:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "BULLISH_HARAMI_CONTEXT",
        "description": "Small body is contained by the preceding bearish body",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T20:30:00Z",
            "2026-07-08T20:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T20:30:00Z",
            "2026-07-08T20:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T20:30:00Z",
            "2026-07-08T20:45:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_BOTTOM_CONTEXT_REQUIRED",
        "description": "Adjacent lows form a tweezer-bottom candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T23:00:00Z",
            "2026-07-08T23:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T23:00:00Z",
            "2026-07-08T23:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T23:00:00Z",
            "2026-07-08T23:15:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "TWEEZERS_TOP_CONTEXT_REQUIRED",
        "description": "Adjacent highs form a tweezer-top candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T23:15:00Z",
            "2026-07-08T23:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T23:15:00Z",
            "2026-07-08T23:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T23:15:00Z",
            "2026-07-08T23:30:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "THREE_MOUNTAINS_CONTEXT_REQUIRED",
        "description": "Three comparable local peaks form a three-mountains candidate",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T20:00:00Z",
            "2026-07-08T22:00:00Z",
            "2026-07-08T23:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        "description": "Pattern geometry cannot determine state without trend context",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T20:00:00Z",
            "2026-07-08T22:00:00Z",
            "2026-07-08T23:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "NISON",
        "code": "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
        "description": "Reversal-like geometry requires follow-through",
        "contribution": 0.0,
        "metadata": {
          "timestamps": [
            "2026-07-08T20:00:00Z",
            "2026-07-08T22:00:00Z",
            "2026-07-08T23:00:00Z"
          ],
          "trend_context_evaluated": false,
          "follow_through_evaluated": false,
          "catalog_scope": "NISON_CHAPTERS_4_TO_8"
        }
      },
      {
        "source": "ENGINE_TREND",
        "code": "SMALL_BODY_CLUSTER",
        "description": "Small real bodies cluster in the selected window",
        "contribution": 0.0,
        "metadata": {
          "evidence_origin": "ENGINE_TREND_HEURISTIC",
          "book_attribution": false,
          "count": 35,
          "ratio": 0.3645833333333333
        }
      },
      {
        "source": "ENGINE_TREND",
        "code": "LOW_DIRECTIONAL_PROGRESS",
        "description": "Body contraction suggests limited directional progress",
        "contribution": 0.0,
        "metadata": {
          "evidence_origin": "ENGINE_TREND_HEURISTIC",
          "book_attribution": false,
          "count": 35,
          "ratio": 0.3645833333333333
        }
      }
    ],
    "candle_contexts": [
      {
        "timestamp": "2026-07-08T00:00:00Z",
        "morphology": {
          "timestamp": "2026-07-08T00:00:00Z",
          "open": 80.58,
          "high": 80.78,
          "low": 80.53,
          "close": 80.66,
          "volume": 21864.8,
          "real_body_size": 0.0799999999999983,
          "full_range_size": 0.25,
          "upper_shadow_size": 0.12000000000000455,
          "lower_shadow_size": 0.04999999999999716,
          "body_to_range_ratio": 0.3199999999999932,
          "upper_shadow_to_range_ratio": 0.4800000000000182,
          "lower_shadow_to_range_ratio": 0.19999999999998863,
          "close_position_in_range": 0.5199999999999818,
          "open_position_in_range": 0.19999999999998863,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [],
        "reason_codes": []
      },
      {
        "timestamp": "2026-07-08T00:15:00Z",
        "morphology": {
          "timestamp": "2026-07-08T00:15:00Z",
          "open": 80.66,
          "high": 80.78,
          "low": 80.48,
          "close": 80.65,
          "volume": 32239.204,
          "real_body_size": 0.009999999999990905,
          "full_range_size": 0.29999999999999716,
          "upper_shadow_size": 0.12000000000000455,
          "lower_shadow_size": 0.1700000000000017,
          "body_to_range_ratio": 0.033333333333303336,
          "upper_shadow_to_range_ratio": 0.40000000000001895,
          "lower_shadow_to_range_ratio": 0.5666666666666778,
          "close_position_in_range": 0.5666666666666778,
          "open_position_in_range": 0.5999999999999811,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": true,
          "is_spinning_top": false,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": true,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "LONG_LOWER_SHADOW_REJECTION",
            "description": "Extended lower shadow provides rejection evidence",
            "contribution": 0.05,
            "metadata": {
              "timestamp": "2026-07-08T00:15:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T00:15:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "DOJI_INDECISION",
            "description": "Doji morphology provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T00:15:00Z"
            }
          }
        ],
        "reason_codes": [
          "LONG_LOWER_SHADOW_REJECTION",
          "SMALL_BODY_INDECISION",
          "DOJI_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T00:30:00Z",
        "morphology": {
          "timestamp": "2026-07-08T00:30:00Z",
          "open": 80.65,
          "high": 80.7,
          "low": 80.4,
          "close": 80.58,
          "volume": 24599.369,
          "real_body_size": 0.07000000000000739,
          "full_range_size": 0.29999999999999716,
          "upper_shadow_size": 0.04999999999999716,
          "lower_shadow_size": 0.1799999999999926,
          "body_to_range_ratio": 0.23333333333336018,
          "upper_shadow_to_range_ratio": 0.16666666666665877,
          "lower_shadow_to_range_ratio": 0.5999999999999811,
          "close_position_in_range": 0.5999999999999811,
          "open_position_in_range": 0.8333333333333413,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": true,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": true,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "LONG_LOWER_SHADOW_REJECTION",
            "description": "Extended lower shadow provides rejection evidence",
            "contribution": 0.05,
            "metadata": {
              "timestamp": "2026-07-08T00:30:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T00:30:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SPINNING_TOP_INDECISION",
            "description": "Spinning-top morphology provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T00:30:00Z"
            }
          }
        ],
        "reason_codes": [
          "LONG_LOWER_SHADOW_REJECTION",
          "SMALL_BODY_INDECISION",
          "SPINNING_TOP_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T00:45:00Z",
        "morphology": {
          "timestamp": "2026-07-08T00:45:00Z",
          "open": 80.57,
          "high": 80.59,
          "low": 80.35,
          "close": 80.37,
          "volume": 13680.291,
          "real_body_size": 0.19999999999998863,
          "full_range_size": 0.2400000000000091,
          "upper_shadow_size": 0.020000000000010232,
          "lower_shadow_size": 0.020000000000010232,
          "body_to_range_ratio": 0.8333333333332544,
          "upper_shadow_to_range_ratio": 0.08333333333337281,
          "lower_shadow_to_range_ratio": 0.08333333333337281,
          "close_position_in_range": 0.08333333333337281,
          "open_position_in_range": 0.9166666666666272,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": true,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": true,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": true
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "STRONG_BEARISH_CANDLE_BODY",
            "description": "Strong bearish real body",
            "contribution": -0.1,
            "metadata": {
              "timestamp": "2026-07-08T00:45:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_LOW",
            "description": "Close is near the candle low",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T00:45:00Z"
            }
          }
        ],
        "reason_codes": [
          "STRONG_BEARISH_CANDLE_BODY",
          "CLOSE_NEAR_LOW"
        ]
      },
      {
        "timestamp": "2026-07-08T01:00:00Z",
        "morphology": {
          "timestamp": "2026-07-08T01:00:00Z",
          "open": 80.37,
          "high": 80.42,
          "low": 80.2,
          "close": 80.38,
          "volume": 16560.043,
          "real_body_size": 0.009999999999990905,
          "full_range_size": 0.21999999999999886,
          "upper_shadow_size": 0.04000000000000625,
          "lower_shadow_size": 0.1700000000000017,
          "body_to_range_ratio": 0.04545454545450435,
          "upper_shadow_to_range_ratio": 0.1818181818182112,
          "lower_shadow_to_range_ratio": 0.7727272727272845,
          "close_position_in_range": 0.8181818181817888,
          "open_position_in_range": 0.7727272727272845,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": true,
          "is_spinning_top": false,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": true,
          "close_near_high": true,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "LONG_LOWER_SHADOW_REJECTION",
            "description": "Extended lower shadow provides rejection evidence",
            "contribution": 0.05,
            "metadata": {
              "timestamp": "2026-07-08T01:00:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T01:00:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_HIGH",
            "description": "Close is near the candle high",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T01:00:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "DOJI_INDECISION",
            "description": "Doji morphology provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T01:00:00Z"
            }
          }
        ],
        "reason_codes": [
          "LONG_LOWER_SHADOW_REJECTION",
          "SMALL_BODY_INDECISION",
          "CLOSE_NEAR_HIGH",
          "DOJI_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T01:15:00Z",
        "morphology": {
          "timestamp": "2026-07-08T01:15:00Z",
          "open": 80.38,
          "high": 80.38,
          "low": 80.07,
          "close": 80.07,
          "volume": 16520.506,
          "real_body_size": 0.3100000000000023,
          "full_range_size": 0.3100000000000023,
          "upper_shadow_size": 0.0,
          "lower_shadow_size": 0.0,
          "body_to_range_ratio": 1.0,
          "upper_shadow_to_range_ratio": 0.0,
          "lower_shadow_to_range_ratio": 0.0,
          "close_position_in_range": 0.0,
          "open_position_in_range": 1.0,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": true,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": true,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": true
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "STRONG_BEARISH_CANDLE_BODY",
            "description": "Strong bearish real body",
            "contribution": -0.1,
            "metadata": {
              "timestamp": "2026-07-08T01:15:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_LOW",
            "description": "Close is near the candle low",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T01:15:00Z"
            }
          }
        ],
        "reason_codes": [
          "STRONG_BEARISH_CANDLE_BODY",
          "CLOSE_NEAR_LOW"
        ]
      },
      {
        "timestamp": "2026-07-08T01:30:00Z",
        "morphology": {
          "timestamp": "2026-07-08T01:30:00Z",
          "open": 80.07,
          "high": 80.09,
          "low": 78.82,
          "close": 79.32,
          "volume": 113777.009,
          "real_body_size": 0.75,
          "full_range_size": 1.2700000000000102,
          "upper_shadow_size": 0.020000000000010232,
          "lower_shadow_size": 0.5,
          "body_to_range_ratio": 0.5905511811023575,
          "upper_shadow_to_range_ratio": 0.015748031496070923,
          "lower_shadow_to_range_ratio": 0.3937007874015716,
          "close_position_in_range": 0.3937007874015716,
          "open_position_in_range": 0.984251968503929,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [],
        "reason_codes": []
      },
      {
        "timestamp": "2026-07-08T01:45:00Z",
        "morphology": {
          "timestamp": "2026-07-08T01:45:00Z",
          "open": 79.31,
          "high": 79.46,
          "low": 78.96,
          "close": 79.1,
          "volume": 22098.11,
          "real_body_size": 0.21000000000000796,
          "full_range_size": 0.5,
          "upper_shadow_size": 0.14999999999999147,
          "lower_shadow_size": 0.14000000000000057,
          "body_to_range_ratio": 0.4200000000000159,
          "upper_shadow_to_range_ratio": 0.29999999999998295,
          "lower_shadow_to_range_ratio": 0.28000000000000114,
          "close_position_in_range": 0.28000000000000114,
          "open_position_in_range": 0.700000000000017,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [],
        "reason_codes": []
      },
      {
        "timestamp": "2026-07-08T02:00:00Z",
        "morphology": {
          "timestamp": "2026-07-08T02:00:00Z",
          "open": 79.09,
          "high": 79.18,
          "low": 78.75,
          "close": 78.94,
          "volume": 31031.38,
          "real_body_size": 0.15000000000000568,
          "full_range_size": 0.4300000000000068,
          "upper_shadow_size": 0.09000000000000341,
          "lower_shadow_size": 0.18999999999999773,
          "body_to_range_ratio": 0.34883720930233325,
          "upper_shadow_to_range_ratio": 0.20930232558139997,
          "lower_shadow_to_range_ratio": 0.44186046511626675,
          "close_position_in_range": 0.44186046511626675,
          "open_position_in_range": 0.7906976744186001,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [],
        "reason_codes": []
      },
      {
        "timestamp": "2026-07-08T02:15:00Z",
        "morphology": {
          "timestamp": "2026-07-08T02:15:00Z",
          "open": 78.93,
          "high": 79.01,
          "low": 78.75,
          "close": 78.91,
          "volume": 28235.112,
          "real_body_size": 0.020000000000010232,
          "full_range_size": 0.2600000000000051,
          "upper_shadow_size": 0.0799999999999983,
          "lower_shadow_size": 0.1599999999999966,
          "body_to_range_ratio": 0.07692307692311476,
          "upper_shadow_to_range_ratio": 0.30769230769229505,
          "lower_shadow_to_range_ratio": 0.6153846153845901,
          "close_position_in_range": 0.6153846153845901,
          "open_position_in_range": 0.692307692307705,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": true,
          "is_spinning_top": false,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": true,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "LONG_LOWER_SHADOW_REJECTION",
            "description": "Extended lower shadow provides rejection evidence",
            "contribution": 0.05,
            "metadata": {
              "timestamp": "2026-07-08T02:15:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T02:15:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "DOJI_INDECISION",
            "description": "Doji morphology provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T02:15:00Z"
            }
          }
        ],
        "reason_codes": [
          "LONG_LOWER_SHADOW_REJECTION",
          "SMALL_BODY_INDECISION",
          "DOJI_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T02:30:00Z",
        "morphology": {
          "timestamp": "2026-07-08T02:30:00Z",
          "open": 78.9,
          "high": 78.97,
          "low": 78.22,
          "close": 78.95,
          "volume": 60990.143,
          "real_body_size": 0.04999999999999716,
          "full_range_size": 0.75,
          "upper_shadow_size": 0.01999999999999602,
          "lower_shadow_size": 0.6800000000000068,
          "body_to_range_ratio": 0.06666666666666288,
          "upper_shadow_to_range_ratio": 0.02666666666666136,
          "lower_shadow_to_range_ratio": 0.9066666666666757,
          "close_position_in_range": 0.9733333333333386,
          "open_position_in_range": 0.9066666666666757,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": true,
          "is_spinning_top": false,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": true,
          "close_near_high": true,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "LONG_LOWER_SHADOW_REJECTION",
            "description": "Extended lower shadow provides rejection evidence",
            "contribution": 0.05,
            "metadata": {
              "timestamp": "2026-07-08T02:30:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T02:30:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_HIGH",
            "description": "Close is near the candle high",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T02:30:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "DOJI_INDECISION",
            "description": "Doji morphology provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T02:30:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED",
            "description": "Hammer-like shape requires trend context",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T02:30:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
            "description": "Candle shape cannot determine state without trend context",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T02:30:00Z"
            }
          }
        ],
        "reason_codes": [
          "LONG_LOWER_SHADOW_REJECTION",
          "SMALL_BODY_INDECISION",
          "CLOSE_NEAR_HIGH",
          "DOJI_INDECISION",
          "HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED",
          "CANDLE_PATTERN_NEEDS_TREND_CONTEXT"
        ]
      },
      {
        "timestamp": "2026-07-08T02:45:00Z",
        "morphology": {
          "timestamp": "2026-07-08T02:45:00Z",
          "open": 78.96,
          "high": 79.18,
          "low": 78.94,
          "close": 79.06,
          "volume": 25185.995,
          "real_body_size": 0.10000000000000853,
          "full_range_size": 0.2400000000000091,
          "upper_shadow_size": 0.12000000000000455,
          "lower_shadow_size": 0.01999999999999602,
          "body_to_range_ratio": 0.4166666666666864,
          "upper_shadow_to_range_ratio": 0.5,
          "lower_shadow_to_range_ratio": 0.0833333333333136,
          "close_position_in_range": 0.5,
          "open_position_in_range": 0.0833333333333136,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [],
        "reason_codes": []
      },
      {
        "timestamp": "2026-07-08T03:00:00Z",
        "morphology": {
          "timestamp": "2026-07-08T03:00:00Z",
          "open": 79.07,
          "high": 79.34,
          "low": 79.05,
          "close": 79.26,
          "volume": 24433.502,
          "real_body_size": 0.19000000000001194,
          "full_range_size": 0.29000000000000625,
          "upper_shadow_size": 0.0799999999999983,
          "lower_shadow_size": 0.01999999999999602,
          "body_to_range_ratio": 0.6551724137931305,
          "upper_shadow_to_range_ratio": 0.2758620689655054,
          "lower_shadow_to_range_ratio": 0.0689655172413641,
          "close_position_in_range": 0.7241379310344946,
          "open_position_in_range": 0.0689655172413641,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": true,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [],
        "reason_codes": []
      },
      {
        "timestamp": "2026-07-08T03:15:00Z",
        "morphology": {
          "timestamp": "2026-07-08T03:15:00Z",
          "open": 79.26,
          "high": 79.31,
          "low": 79.18,
          "close": 79.24,
          "volume": 9724.759,
          "real_body_size": 0.020000000000010232,
          "full_range_size": 0.12999999999999545,
          "upper_shadow_size": 0.04999999999999716,
          "lower_shadow_size": 0.05999999999998806,
          "body_to_range_ratio": 0.15384615384623793,
          "upper_shadow_to_range_ratio": 0.3846153846153762,
          "lower_shadow_to_range_ratio": 0.46153846153838585,
          "close_position_in_range": 0.46153846153838585,
          "open_position_in_range": 0.6153846153846237,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": true,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T03:15:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SPINNING_TOP_INDECISION",
            "description": "Spinning-top morphology provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T03:15:00Z"
            }
          }
        ],
        "reason_codes": [
          "SMALL_BODY_INDECISION",
          "SPINNING_TOP_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T03:30:00Z",
        "morphology": {
          "timestamp": "2026-07-08T03:30:00Z",
          "open": 79.24,
          "high": 79.25,
          "low": 78.92,
          "close": 79.04,
          "volume": 14394.387,
          "real_body_size": 0.19999999999998863,
          "full_range_size": 0.3299999999999983,
          "upper_shadow_size": 0.010000000000005116,
          "lower_shadow_size": 0.12000000000000455,
          "body_to_range_ratio": 0.6060606060605748,
          "upper_shadow_to_range_ratio": 0.03030303030304596,
          "lower_shadow_to_range_ratio": 0.3636363636363793,
          "close_position_in_range": 0.3636363636363793,
          "open_position_in_range": 0.9696969696969541,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": true,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [],
        "reason_codes": []
      },
      {
        "timestamp": "2026-07-08T03:45:00Z",
        "morphology": {
          "timestamp": "2026-07-08T03:45:00Z",
          "open": 79.04,
          "high": 79.04,
          "low": 78.62,
          "close": 78.73,
          "volume": 17215.595,
          "real_body_size": 0.3100000000000023,
          "full_range_size": 0.4200000000000017,
          "upper_shadow_size": 0.0,
          "lower_shadow_size": 0.10999999999999943,
          "body_to_range_ratio": 0.7380952380952405,
          "upper_shadow_to_range_ratio": 0.0,
          "lower_shadow_to_range_ratio": 0.2619047619047595,
          "close_position_in_range": 0.2619047619047595,
          "open_position_in_range": 1.0,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": true,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [],
        "reason_codes": []
      },
      {
        "timestamp": "2026-07-08T04:00:00Z",
        "morphology": {
          "timestamp": "2026-07-08T04:00:00Z",
          "open": 78.73,
          "high": 78.79,
          "low": 78.57,
          "close": 78.72,
          "volume": 17768.025,
          "real_body_size": 0.010000000000005116,
          "full_range_size": 0.22000000000001307,
          "upper_shadow_size": 0.060000000000002274,
          "lower_shadow_size": 0.15000000000000568,
          "body_to_range_ratio": 0.04545454545456601,
          "upper_shadow_to_range_ratio": 0.2727272727272669,
          "lower_shadow_to_range_ratio": 0.6818181818181671,
          "close_position_in_range": 0.6818181818181671,
          "open_position_in_range": 0.7272727272727332,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": true,
          "is_spinning_top": false,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": true,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "LONG_LOWER_SHADOW_REJECTION",
            "description": "Extended lower shadow provides rejection evidence",
            "contribution": 0.05,
            "metadata": {
              "timestamp": "2026-07-08T04:00:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T04:00:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "DOJI_INDECISION",
            "description": "Doji morphology provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T04:00:00Z"
            }
          }
        ],
        "reason_codes": [
          "LONG_LOWER_SHADOW_REJECTION",
          "SMALL_BODY_INDECISION",
          "DOJI_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T04:15:00Z",
        "morphology": {
          "timestamp": "2026-07-08T04:15:00Z",
          "open": 78.72,
          "high": 78.92,
          "low": 78.69,
          "close": 78.88,
          "volume": 8394.533,
          "real_body_size": 0.1599999999999966,
          "full_range_size": 0.23000000000000398,
          "upper_shadow_size": 0.04000000000000625,
          "lower_shadow_size": 0.030000000000001137,
          "body_to_range_ratio": 0.6956521739130166,
          "upper_shadow_to_range_ratio": 0.17391304347828504,
          "lower_shadow_to_range_ratio": 0.13043478260869834,
          "close_position_in_range": 0.8260869565217149,
          "open_position_in_range": 0.13043478260869834,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": true,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": true,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_HIGH",
            "description": "Close is near the candle high",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T04:15:00Z"
            }
          }
        ],
        "reason_codes": [
          "CLOSE_NEAR_HIGH"
        ]
      },
      {
        "timestamp": "2026-07-08T04:30:00Z",
        "morphology": {
          "timestamp": "2026-07-08T04:30:00Z",
          "open": 78.88,
          "high": 78.93,
          "low": 78.66,
          "close": 78.67,
          "volume": 9392.994,
          "real_body_size": 0.20999999999999375,
          "full_range_size": 0.27000000000001023,
          "upper_shadow_size": 0.05000000000001137,
          "lower_shadow_size": 0.010000000000005116,
          "body_to_range_ratio": 0.7777777777777252,
          "upper_shadow_to_range_ratio": 0.18518518518522029,
          "lower_shadow_to_range_ratio": 0.03703703703705458,
          "close_position_in_range": 0.03703703703705458,
          "open_position_in_range": 0.8148148148147797,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": true,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": true,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": true
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "STRONG_BEARISH_CANDLE_BODY",
            "description": "Strong bearish real body",
            "contribution": -0.1,
            "metadata": {
              "timestamp": "2026-07-08T04:30:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_LOW",
            "description": "Close is near the candle low",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T04:30:00Z"
            }
          }
        ],
        "reason_codes": [
          "STRONG_BEARISH_CANDLE_BODY",
          "CLOSE_NEAR_LOW"
        ]
      },
      {
        "timestamp": "2026-07-08T04:45:00Z",
        "morphology": {
          "timestamp": "2026-07-08T04:45:00Z",
          "open": 78.67,
          "high": 78.71,
          "low": 78.35,
          "close": 78.64,
          "volume": 11947.174,
          "real_body_size": 0.030000000000001137,
          "full_range_size": 0.35999999999999943,
          "upper_shadow_size": 0.03999999999999204,
          "lower_shadow_size": 0.29000000000000625,
          "body_to_range_ratio": 0.08333333333333662,
          "upper_shadow_to_range_ratio": 0.11111111111108918,
          "lower_shadow_to_range_ratio": 0.8055555555555742,
          "close_position_in_range": 0.8055555555555742,
          "open_position_in_range": 0.8888888888889108,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": true,
          "is_spinning_top": false,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": true,
          "close_near_high": true,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "LONG_LOWER_SHADOW_REJECTION",
            "description": "Extended lower shadow provides rejection evidence",
            "contribution": 0.05,
            "metadata": {
              "timestamp": "2026-07-08T04:45:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T04:45:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_HIGH",
            "description": "Close is near the candle high",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T04:45:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "DOJI_INDECISION",
            "description": "Doji morphology provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T04:45:00Z"
            }
          }
        ],
        "reason_codes": [
          "LONG_LOWER_SHADOW_REJECTION",
          "SMALL_BODY_INDECISION",
          "CLOSE_NEAR_HIGH",
          "DOJI_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T05:00:00Z",
        "morphology": {
          "timestamp": "2026-07-08T05:00:00Z",
          "open": 78.65,
          "high": 78.82,
          "low": 78.51,
          "close": 78.71,
          "volume": 25705.745,
          "real_body_size": 0.05999999999998806,
          "full_range_size": 0.30999999999998806,
          "upper_shadow_size": 0.10999999999999943,
          "lower_shadow_size": 0.14000000000000057,
          "body_to_range_ratio": 0.19354838709674313,
          "upper_shadow_to_range_ratio": 0.3548387096774312,
          "lower_shadow_to_range_ratio": 0.4516129032258257,
          "close_position_in_range": 0.6451612903225689,
          "open_position_in_range": 0.4516129032258257,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": true,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T05:00:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SPINNING_TOP_INDECISION",
            "description": "Spinning-top morphology provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T05:00:00Z"
            }
          }
        ],
        "reason_codes": [
          "SMALL_BODY_INDECISION",
          "SPINNING_TOP_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T05:15:00Z",
        "morphology": {
          "timestamp": "2026-07-08T05:15:00Z",
          "open": 78.72,
          "high": 78.82,
          "low": 78.57,
          "close": 78.63,
          "volume": 17048.692,
          "real_body_size": 0.09000000000000341,
          "full_range_size": 0.25,
          "upper_shadow_size": 0.09999999999999432,
          "lower_shadow_size": 0.060000000000002274,
          "body_to_range_ratio": 0.36000000000001364,
          "upper_shadow_to_range_ratio": 0.39999999999997726,
          "lower_shadow_to_range_ratio": 0.2400000000000091,
          "close_position_in_range": 0.2400000000000091,
          "open_position_in_range": 0.6000000000000227,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": true
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_LOW",
            "description": "Close is near the candle low",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T05:15:00Z"
            }
          }
        ],
        "reason_codes": [
          "CLOSE_NEAR_LOW"
        ]
      },
      {
        "timestamp": "2026-07-08T05:30:00Z",
        "morphology": {
          "timestamp": "2026-07-08T05:30:00Z",
          "open": 78.62,
          "high": 78.67,
          "low": 78.42,
          "close": 78.42,
          "volume": 16117.089,
          "real_body_size": 0.20000000000000284,
          "full_range_size": 0.25,
          "upper_shadow_size": 0.04999999999999716,
          "lower_shadow_size": 0.0,
          "body_to_range_ratio": 0.8000000000000114,
          "upper_shadow_to_range_ratio": 0.19999999999998863,
          "lower_shadow_to_range_ratio": 0.0,
          "close_position_in_range": 0.0,
          "open_position_in_range": 0.8000000000000114,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": true,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": true,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": true
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "STRONG_BEARISH_CANDLE_BODY",
            "description": "Strong bearish real body",
            "contribution": -0.1,
            "metadata": {
              "timestamp": "2026-07-08T05:30:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_LOW",
            "description": "Close is near the candle low",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T05:30:00Z"
            }
          }
        ],
        "reason_codes": [
          "STRONG_BEARISH_CANDLE_BODY",
          "CLOSE_NEAR_LOW"
        ]
      },
      {
        "timestamp": "2026-07-08T05:45:00Z",
        "morphology": {
          "timestamp": "2026-07-08T05:45:00Z",
          "open": 78.42,
          "high": 78.52,
          "low": 78.35,
          "close": 78.42,
          "volume": 17078.502,
          "real_body_size": 0.0,
          "full_range_size": 0.1700000000000017,
          "upper_shadow_size": 0.09999999999999432,
          "lower_shadow_size": 0.07000000000000739,
          "body_to_range_ratio": 0.0,
          "upper_shadow_to_range_ratio": 0.5882352941176077,
          "lower_shadow_to_range_ratio": 0.4117647058823923,
          "close_position_in_range": 0.4117647058823923,
          "open_position_in_range": 0.4117647058823923,
          "direction": "NEUTRAL",
          "is_bullish": false,
          "is_bearish": false,
          "is_neutral": true,
          "is_doji": true,
          "is_spinning_top": false,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": true,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "LONG_UPPER_SHADOW_REJECTION",
            "description": "Extended upper shadow provides rejection evidence",
            "contribution": -0.05,
            "metadata": {
              "timestamp": "2026-07-08T05:45:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T05:45:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "DOJI_INDECISION",
            "description": "Doji morphology provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T05:45:00Z"
            }
          }
        ],
        "reason_codes": [
          "LONG_UPPER_SHADOW_REJECTION",
          "SMALL_BODY_INDECISION",
          "DOJI_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T06:00:00Z",
        "morphology": {
          "timestamp": "2026-07-08T06:00:00Z",
          "open": 78.43,
          "high": 78.46,
          "low": 78.23,
          "close": 78.36,
          "volume": 20087.116,
          "real_body_size": 0.07000000000000739,
          "full_range_size": 0.22999999999998977,
          "upper_shadow_size": 0.029999999999986926,
          "lower_shadow_size": 0.12999999999999545,
          "body_to_range_ratio": 0.30434782608700217,
          "upper_shadow_to_range_ratio": 0.1304347826086446,
          "lower_shadow_to_range_ratio": 0.5652173913043532,
          "close_position_in_range": 0.5652173913043532,
          "open_position_in_range": 0.8695652173913554,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": true,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "LONG_LOWER_SHADOW_REJECTION",
            "description": "Extended lower shadow provides rejection evidence",
            "contribution": 0.05,
            "metadata": {
              "timestamp": "2026-07-08T06:00:00Z"
            }
          }
        ],
        "reason_codes": [
          "LONG_LOWER_SHADOW_REJECTION"
        ]
      },
      {
        "timestamp": "2026-07-08T06:15:00Z",
        "morphology": {
          "timestamp": "2026-07-08T06:15:00Z",
          "open": 78.36,
          "high": 78.4,
          "low": 78.13,
          "close": 78.29,
          "volume": 19832.905,
          "real_body_size": 0.06999999999999318,
          "full_range_size": 0.27000000000001023,
          "upper_shadow_size": 0.04000000000000625,
          "lower_shadow_size": 0.1600000000000108,
          "body_to_range_ratio": 0.25925925925922416,
          "upper_shadow_to_range_ratio": 0.14814814814816568,
          "lower_shadow_to_range_ratio": 0.5925925925926101,
          "close_position_in_range": 0.5925925925926101,
          "open_position_in_range": 0.8518518518518343,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": true,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "LONG_LOWER_SHADOW_REJECTION",
            "description": "Extended lower shadow provides rejection evidence",
            "contribution": 0.05,
            "metadata": {
              "timestamp": "2026-07-08T06:15:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T06:15:00Z"
            }
          }
        ],
        "reason_codes": [
          "LONG_LOWER_SHADOW_REJECTION",
          "SMALL_BODY_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T06:30:00Z",
        "morphology": {
          "timestamp": "2026-07-08T06:30:00Z",
          "open": 78.28,
          "high": 78.33,
          "low": 77.95,
          "close": 78.06,
          "volume": 35939.385,
          "real_body_size": 0.21999999999999886,
          "full_range_size": 0.37999999999999545,
          "upper_shadow_size": 0.04999999999999716,
          "lower_shadow_size": 0.10999999999999943,
          "body_to_range_ratio": 0.5789473684210565,
          "upper_shadow_to_range_ratio": 0.13157894736841516,
          "lower_shadow_to_range_ratio": 0.28947368421052827,
          "close_position_in_range": 0.28947368421052827,
          "open_position_in_range": 0.8684210526315849,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [],
        "reason_codes": []
      },
      {
        "timestamp": "2026-07-08T06:45:00Z",
        "morphology": {
          "timestamp": "2026-07-08T06:45:00Z",
          "open": 78.05,
          "high": 78.38,
          "low": 77.99,
          "close": 78.23,
          "volume": 29887.189,
          "real_body_size": 0.18000000000000682,
          "full_range_size": 0.39000000000000057,
          "upper_shadow_size": 0.14999999999999147,
          "lower_shadow_size": 0.060000000000002274,
          "body_to_range_ratio": 0.46153846153847833,
          "upper_shadow_to_range_ratio": 0.3846153846153622,
          "lower_shadow_to_range_ratio": 0.15384615384615946,
          "close_position_in_range": 0.6153846153846378,
          "open_position_in_range": 0.15384615384615946,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [],
        "reason_codes": []
      },
      {
        "timestamp": "2026-07-08T07:00:00Z",
        "morphology": {
          "timestamp": "2026-07-08T07:00:00Z",
          "open": 78.23,
          "high": 78.25,
          "low": 77.8,
          "close": 78.14,
          "volume": 56961.959,
          "real_body_size": 0.09000000000000341,
          "full_range_size": 0.45000000000000284,
          "upper_shadow_size": 0.01999999999999602,
          "lower_shadow_size": 0.3400000000000034,
          "body_to_range_ratio": 0.2000000000000063,
          "upper_shadow_to_range_ratio": 0.04444444444443532,
          "lower_shadow_to_range_ratio": 0.7555555555555583,
          "close_position_in_range": 0.7555555555555583,
          "open_position_in_range": 0.9555555555555647,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": true,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": true,
          "close_near_high": true,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "LONG_LOWER_SHADOW_REJECTION",
            "description": "Extended lower shadow provides rejection evidence",
            "contribution": 0.05,
            "metadata": {
              "timestamp": "2026-07-08T07:00:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T07:00:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_HIGH",
            "description": "Close is near the candle high",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T07:00:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SPINNING_TOP_INDECISION",
            "description": "Spinning-top morphology provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T07:00:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED",
            "description": "Hammer-like shape requires trend context",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T07:00:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
            "description": "Candle shape cannot determine state without trend context",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T07:00:00Z"
            }
          }
        ],
        "reason_codes": [
          "LONG_LOWER_SHADOW_REJECTION",
          "SMALL_BODY_INDECISION",
          "CLOSE_NEAR_HIGH",
          "SPINNING_TOP_INDECISION",
          "HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED",
          "CANDLE_PATTERN_NEEDS_TREND_CONTEXT"
        ]
      },
      {
        "timestamp": "2026-07-08T07:15:00Z",
        "morphology": {
          "timestamp": "2026-07-08T07:15:00Z",
          "open": 78.14,
          "high": 78.23,
          "low": 77.96,
          "close": 78.13,
          "volume": 68779.009,
          "real_body_size": 0.010000000000005116,
          "full_range_size": 0.27000000000001023,
          "upper_shadow_size": 0.09000000000000341,
          "lower_shadow_size": 0.1700000000000017,
          "body_to_range_ratio": 0.03703703703705458,
          "upper_shadow_to_range_ratio": 0.3333333333333333,
          "lower_shadow_to_range_ratio": 0.6296296296296121,
          "close_position_in_range": 0.6296296296296121,
          "open_position_in_range": 0.6666666666666666,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": true,
          "is_spinning_top": false,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": true,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "LONG_LOWER_SHADOW_REJECTION",
            "description": "Extended lower shadow provides rejection evidence",
            "contribution": 0.05,
            "metadata": {
              "timestamp": "2026-07-08T07:15:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T07:15:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "DOJI_INDECISION",
            "description": "Doji morphology provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T07:15:00Z"
            }
          }
        ],
        "reason_codes": [
          "LONG_LOWER_SHADOW_REJECTION",
          "SMALL_BODY_INDECISION",
          "DOJI_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T07:30:00Z",
        "morphology": {
          "timestamp": "2026-07-08T07:30:00Z",
          "open": 78.13,
          "high": 78.25,
          "low": 78.05,
          "close": 78.18,
          "volume": 32332.522,
          "real_body_size": 0.05000000000001137,
          "full_range_size": 0.20000000000000284,
          "upper_shadow_size": 0.06999999999999318,
          "lower_shadow_size": 0.0799999999999983,
          "body_to_range_ratio": 0.2500000000000533,
          "upper_shadow_to_range_ratio": 0.3499999999999609,
          "lower_shadow_to_range_ratio": 0.3999999999999858,
          "close_position_in_range": 0.6500000000000391,
          "open_position_in_range": 0.3999999999999858,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T07:30:00Z"
            }
          }
        ],
        "reason_codes": [
          "SMALL_BODY_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T07:45:00Z",
        "morphology": {
          "timestamp": "2026-07-08T07:45:00Z",
          "open": 78.18,
          "high": 78.34,
          "low": 78.09,
          "close": 78.28,
          "volume": 16567.293,
          "real_body_size": 0.09999999999999432,
          "full_range_size": 0.25,
          "upper_shadow_size": 0.060000000000002274,
          "lower_shadow_size": 0.09000000000000341,
          "body_to_range_ratio": 0.39999999999997726,
          "upper_shadow_to_range_ratio": 0.2400000000000091,
          "lower_shadow_to_range_ratio": 0.36000000000001364,
          "close_position_in_range": 0.7599999999999909,
          "open_position_in_range": 0.36000000000001364,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": true,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_HIGH",
            "description": "Close is near the candle high",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T07:45:00Z"
            }
          }
        ],
        "reason_codes": [
          "CLOSE_NEAR_HIGH"
        ]
      },
      {
        "timestamp": "2026-07-08T08:00:00Z",
        "morphology": {
          "timestamp": "2026-07-08T08:00:00Z",
          "open": 78.29,
          "high": 78.43,
          "low": 78.24,
          "close": 78.34,
          "volume": 18586.268,
          "real_body_size": 0.04999999999999716,
          "full_range_size": 0.19000000000001194,
          "upper_shadow_size": 0.09000000000000341,
          "lower_shadow_size": 0.05000000000001137,
          "body_to_range_ratio": 0.2631578947368106,
          "upper_shadow_to_range_ratio": 0.473684210526304,
          "lower_shadow_to_range_ratio": 0.2631578947368854,
          "close_position_in_range": 0.5263157894736961,
          "open_position_in_range": 0.2631578947368854,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T08:00:00Z"
            }
          }
        ],
        "reason_codes": [
          "SMALL_BODY_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T08:15:00Z",
        "morphology": {
          "timestamp": "2026-07-08T08:15:00Z",
          "open": 78.33,
          "high": 78.37,
          "low": 77.17,
          "close": 77.2,
          "volume": 78280.899,
          "real_body_size": 1.1299999999999955,
          "full_range_size": 1.2000000000000028,
          "upper_shadow_size": 0.04000000000000625,
          "lower_shadow_size": 0.030000000000001137,
          "body_to_range_ratio": 0.9416666666666607,
          "upper_shadow_to_range_ratio": 0.03333333333333847,
          "lower_shadow_to_range_ratio": 0.02500000000000089,
          "close_position_in_range": 0.02500000000000089,
          "open_position_in_range": 0.9666666666666616,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": true,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": true,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": true
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "STRONG_BEARISH_CANDLE_BODY",
            "description": "Strong bearish real body",
            "contribution": -0.1,
            "metadata": {
              "timestamp": "2026-07-08T08:15:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_LOW",
            "description": "Close is near the candle low",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T08:15:00Z"
            }
          }
        ],
        "reason_codes": [
          "STRONG_BEARISH_CANDLE_BODY",
          "CLOSE_NEAR_LOW"
        ]
      },
      {
        "timestamp": "2026-07-08T08:30:00Z",
        "morphology": {
          "timestamp": "2026-07-08T08:30:00Z",
          "open": 77.2,
          "high": 77.4,
          "low": 76.9,
          "close": 77.14,
          "volume": 59444.955,
          "real_body_size": 0.060000000000002274,
          "full_range_size": 0.5,
          "upper_shadow_size": 0.20000000000000284,
          "lower_shadow_size": 0.23999999999999488,
          "body_to_range_ratio": 0.12000000000000455,
          "upper_shadow_to_range_ratio": 0.4000000000000057,
          "lower_shadow_to_range_ratio": 0.47999999999998977,
          "close_position_in_range": 0.47999999999998977,
          "open_position_in_range": 0.5999999999999943,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": true,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T08:30:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SPINNING_TOP_INDECISION",
            "description": "Spinning-top morphology provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T08:30:00Z"
            }
          }
        ],
        "reason_codes": [
          "SMALL_BODY_INDECISION",
          "SPINNING_TOP_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T08:45:00Z",
        "morphology": {
          "timestamp": "2026-07-08T08:45:00Z",
          "open": 77.14,
          "high": 77.73,
          "low": 77.13,
          "close": 77.25,
          "volume": 45195.473,
          "real_body_size": 0.10999999999999943,
          "full_range_size": 0.6000000000000085,
          "upper_shadow_size": 0.480000000000004,
          "lower_shadow_size": 0.010000000000005116,
          "body_to_range_ratio": 0.18333333333332977,
          "upper_shadow_to_range_ratio": 0.7999999999999953,
          "lower_shadow_to_range_ratio": 0.016666666666674955,
          "close_position_in_range": 0.20000000000000473,
          "open_position_in_range": 0.016666666666674955,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": true,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": true,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": true
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "LONG_UPPER_SHADOW_REJECTION",
            "description": "Extended upper shadow provides rejection evidence",
            "contribution": -0.05,
            "metadata": {
              "timestamp": "2026-07-08T08:45:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T08:45:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_LOW",
            "description": "Close is near the candle low",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T08:45:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SPINNING_TOP_INDECISION",
            "description": "Spinning-top morphology provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T08:45:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED",
            "description": "Shooting-star-like shape requires trend context",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T08:45:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
            "description": "Candle shape cannot determine state without trend context",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T08:45:00Z"
            }
          }
        ],
        "reason_codes": [
          "LONG_UPPER_SHADOW_REJECTION",
          "SMALL_BODY_INDECISION",
          "CLOSE_NEAR_LOW",
          "SPINNING_TOP_INDECISION",
          "SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED",
          "CANDLE_PATTERN_NEEDS_TREND_CONTEXT"
        ]
      },
      {
        "timestamp": "2026-07-08T09:00:00Z",
        "morphology": {
          "timestamp": "2026-07-08T09:00:00Z",
          "open": 77.26,
          "high": 77.38,
          "low": 77.17,
          "close": 77.26,
          "volume": 28169.241,
          "real_body_size": 0.0,
          "full_range_size": 0.20999999999999375,
          "upper_shadow_size": 0.11999999999999034,
          "lower_shadow_size": 0.09000000000000341,
          "body_to_range_ratio": 0.0,
          "upper_shadow_to_range_ratio": 0.5714285714285424,
          "lower_shadow_to_range_ratio": 0.4285714285714576,
          "close_position_in_range": 0.4285714285714576,
          "open_position_in_range": 0.4285714285714576,
          "direction": "NEUTRAL",
          "is_bullish": false,
          "is_bearish": false,
          "is_neutral": true,
          "is_doji": true,
          "is_spinning_top": false,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": true,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "LONG_UPPER_SHADOW_REJECTION",
            "description": "Extended upper shadow provides rejection evidence",
            "contribution": -0.05,
            "metadata": {
              "timestamp": "2026-07-08T09:00:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T09:00:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "DOJI_INDECISION",
            "description": "Doji morphology provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T09:00:00Z"
            }
          }
        ],
        "reason_codes": [
          "LONG_UPPER_SHADOW_REJECTION",
          "SMALL_BODY_INDECISION",
          "DOJI_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T09:15:00Z",
        "morphology": {
          "timestamp": "2026-07-08T09:15:00Z",
          "open": 77.26,
          "high": 77.3,
          "low": 77.01,
          "close": 77.23,
          "volume": 17936.318,
          "real_body_size": 0.030000000000001137,
          "full_range_size": 0.28999999999999204,
          "upper_shadow_size": 0.03999999999999204,
          "lower_shadow_size": 0.21999999999999886,
          "body_to_range_ratio": 0.10344827586207572,
          "upper_shadow_to_range_ratio": 0.13793103448273497,
          "lower_shadow_to_range_ratio": 0.7586206896551894,
          "close_position_in_range": 0.7586206896551894,
          "open_position_in_range": 0.8620689655172651,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": true,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": true,
          "close_near_high": true,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "LONG_LOWER_SHADOW_REJECTION",
            "description": "Extended lower shadow provides rejection evidence",
            "contribution": 0.05,
            "metadata": {
              "timestamp": "2026-07-08T09:15:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T09:15:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_HIGH",
            "description": "Close is near the candle high",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T09:15:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SPINNING_TOP_INDECISION",
            "description": "Spinning-top morphology provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T09:15:00Z"
            }
          }
        ],
        "reason_codes": [
          "LONG_LOWER_SHADOW_REJECTION",
          "SMALL_BODY_INDECISION",
          "CLOSE_NEAR_HIGH",
          "SPINNING_TOP_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T09:30:00Z",
        "morphology": {
          "timestamp": "2026-07-08T09:30:00Z",
          "open": 77.23,
          "high": 77.49,
          "low": 77.2,
          "close": 77.34,
          "volume": 17852.894,
          "real_body_size": 0.10999999999999943,
          "full_range_size": 0.28999999999999204,
          "upper_shadow_size": 0.14999999999999147,
          "lower_shadow_size": 0.030000000000001137,
          "body_to_range_ratio": 0.3793103448275947,
          "upper_shadow_to_range_ratio": 0.5172413793103297,
          "lower_shadow_to_range_ratio": 0.10344827586207572,
          "close_position_in_range": 0.4827586206896704,
          "open_position_in_range": 0.10344827586207572,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [],
        "reason_codes": []
      },
      {
        "timestamp": "2026-07-08T09:45:00Z",
        "morphology": {
          "timestamp": "2026-07-08T09:45:00Z",
          "open": 77.35,
          "high": 77.37,
          "low": 77.16,
          "close": 77.19,
          "volume": 14774.112,
          "real_body_size": 0.1599999999999966,
          "full_range_size": 0.21000000000000796,
          "upper_shadow_size": 0.020000000000010232,
          "lower_shadow_size": 0.030000000000001137,
          "body_to_range_ratio": 0.7619047619047168,
          "upper_shadow_to_range_ratio": 0.09523809523814035,
          "lower_shadow_to_range_ratio": 0.14285714285714285,
          "close_position_in_range": 0.14285714285714285,
          "open_position_in_range": 0.9047619047618597,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": true,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": true,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": true
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "STRONG_BEARISH_CANDLE_BODY",
            "description": "Strong bearish real body",
            "contribution": -0.1,
            "metadata": {
              "timestamp": "2026-07-08T09:45:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_LOW",
            "description": "Close is near the candle low",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T09:45:00Z"
            }
          }
        ],
        "reason_codes": [
          "STRONG_BEARISH_CANDLE_BODY",
          "CLOSE_NEAR_LOW"
        ]
      },
      {
        "timestamp": "2026-07-08T10:00:00Z",
        "morphology": {
          "timestamp": "2026-07-08T10:00:00Z",
          "open": 77.19,
          "high": 77.3,
          "low": 76.94,
          "close": 77.08,
          "volume": 21172.056,
          "real_body_size": 0.10999999999999943,
          "full_range_size": 0.35999999999999943,
          "upper_shadow_size": 0.10999999999999943,
          "lower_shadow_size": 0.14000000000000057,
          "body_to_range_ratio": 0.30555555555555447,
          "upper_shadow_to_range_ratio": 0.30555555555555447,
          "lower_shadow_to_range_ratio": 0.38888888888889106,
          "close_position_in_range": 0.38888888888889106,
          "open_position_in_range": 0.6944444444444455,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [],
        "reason_codes": []
      },
      {
        "timestamp": "2026-07-08T10:15:00Z",
        "morphology": {
          "timestamp": "2026-07-08T10:15:00Z",
          "open": 77.08,
          "high": 77.41,
          "low": 77.01,
          "close": 77.4,
          "volume": 18512.873,
          "real_body_size": 0.3200000000000074,
          "full_range_size": 0.3999999999999915,
          "upper_shadow_size": 0.009999999999990905,
          "lower_shadow_size": 0.06999999999999318,
          "body_to_range_ratio": 0.8000000000000356,
          "upper_shadow_to_range_ratio": 0.024999999999977797,
          "lower_shadow_to_range_ratio": 0.17499999999998667,
          "close_position_in_range": 0.9750000000000222,
          "open_position_in_range": 0.17499999999998667,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": true,
          "is_strong_bullish_body": true,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": true,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "STRONG_BULLISH_CANDLE_BODY",
            "description": "Strong bullish real body",
            "contribution": 0.1,
            "metadata": {
              "timestamp": "2026-07-08T10:15:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_HIGH",
            "description": "Close is near the candle high",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T10:15:00Z"
            }
          }
        ],
        "reason_codes": [
          "STRONG_BULLISH_CANDLE_BODY",
          "CLOSE_NEAR_HIGH"
        ]
      },
      {
        "timestamp": "2026-07-08T10:30:00Z",
        "morphology": {
          "timestamp": "2026-07-08T10:30:00Z",
          "open": 77.39,
          "high": 77.5,
          "low": 77.31,
          "close": 77.37,
          "volume": 15539.178,
          "real_body_size": 0.01999999999999602,
          "full_range_size": 0.18999999999999773,
          "upper_shadow_size": 0.10999999999999943,
          "lower_shadow_size": 0.060000000000002274,
          "body_to_range_ratio": 0.10526315789471716,
          "upper_shadow_to_range_ratio": 0.5789473684210565,
          "lower_shadow_to_range_ratio": 0.3157894736842263,
          "close_position_in_range": 0.3157894736842263,
          "open_position_in_range": 0.42105263157894346,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": true,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": true,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "LONG_UPPER_SHADOW_REJECTION",
            "description": "Extended upper shadow provides rejection evidence",
            "contribution": -0.05,
            "metadata": {
              "timestamp": "2026-07-08T10:30:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T10:30:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SPINNING_TOP_INDECISION",
            "description": "Spinning-top morphology provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T10:30:00Z"
            }
          }
        ],
        "reason_codes": [
          "LONG_UPPER_SHADOW_REJECTION",
          "SMALL_BODY_INDECISION",
          "SPINNING_TOP_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T10:45:00Z",
        "morphology": {
          "timestamp": "2026-07-08T10:45:00Z",
          "open": 77.38,
          "high": 77.4,
          "low": 77.24,
          "close": 77.33,
          "volume": 10844.158,
          "real_body_size": 0.04999999999999716,
          "full_range_size": 0.1600000000000108,
          "upper_shadow_size": 0.020000000000010232,
          "lower_shadow_size": 0.09000000000000341,
          "body_to_range_ratio": 0.31249999999996114,
          "upper_shadow_to_range_ratio": 0.1250000000000555,
          "lower_shadow_to_range_ratio": 0.5624999999999833,
          "close_position_in_range": 0.5624999999999833,
          "open_position_in_range": 0.8749999999999445,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": true,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "LONG_LOWER_SHADOW_REJECTION",
            "description": "Extended lower shadow provides rejection evidence",
            "contribution": 0.05,
            "metadata": {
              "timestamp": "2026-07-08T10:45:00Z"
            }
          }
        ],
        "reason_codes": [
          "LONG_LOWER_SHADOW_REJECTION"
        ]
      },
      {
        "timestamp": "2026-07-08T11:00:00Z",
        "morphology": {
          "timestamp": "2026-07-08T11:00:00Z",
          "open": 77.33,
          "high": 77.37,
          "low": 77.18,
          "close": 77.22,
          "volume": 18003.94,
          "real_body_size": 0.10999999999999943,
          "full_range_size": 0.18999999999999773,
          "upper_shadow_size": 0.04000000000000625,
          "lower_shadow_size": 0.03999999999999204,
          "body_to_range_ratio": 0.5789473684210565,
          "upper_shadow_to_range_ratio": 0.21052631578950912,
          "lower_shadow_to_range_ratio": 0.21052631578943432,
          "close_position_in_range": 0.21052631578943432,
          "open_position_in_range": 0.7894736842104909,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": true
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_LOW",
            "description": "Close is near the candle low",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T11:00:00Z"
            }
          }
        ],
        "reason_codes": [
          "CLOSE_NEAR_LOW"
        ]
      },
      {
        "timestamp": "2026-07-08T11:15:00Z",
        "morphology": {
          "timestamp": "2026-07-08T11:15:00Z",
          "open": 77.23,
          "high": 77.26,
          "low": 77.08,
          "close": 77.16,
          "volume": 14647.823,
          "real_body_size": 0.07000000000000739,
          "full_range_size": 0.18000000000000682,
          "upper_shadow_size": 0.030000000000001137,
          "lower_shadow_size": 0.0799999999999983,
          "body_to_range_ratio": 0.3888888888889152,
          "upper_shadow_to_range_ratio": 0.16666666666666666,
          "lower_shadow_to_range_ratio": 0.4444444444444181,
          "close_position_in_range": 0.4444444444444181,
          "open_position_in_range": 0.8333333333333334,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [],
        "reason_codes": []
      },
      {
        "timestamp": "2026-07-08T11:30:00Z",
        "morphology": {
          "timestamp": "2026-07-08T11:30:00Z",
          "open": 77.16,
          "high": 77.71,
          "low": 77.1,
          "close": 77.55,
          "volume": 24245.406,
          "real_body_size": 0.39000000000000057,
          "full_range_size": 0.6099999999999994,
          "upper_shadow_size": 0.1599999999999966,
          "lower_shadow_size": 0.060000000000002274,
          "body_to_range_ratio": 0.6393442622950835,
          "upper_shadow_to_range_ratio": 0.26229508196720774,
          "lower_shadow_to_range_ratio": 0.09836065573770873,
          "close_position_in_range": 0.7377049180327923,
          "open_position_in_range": 0.09836065573770873,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": true,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [],
        "reason_codes": []
      },
      {
        "timestamp": "2026-07-08T11:45:00Z",
        "morphology": {
          "timestamp": "2026-07-08T11:45:00Z",
          "open": 77.56,
          "high": 77.66,
          "low": 77.46,
          "close": 77.56,
          "volume": 18678.125,
          "real_body_size": 0.0,
          "full_range_size": 0.20000000000000284,
          "upper_shadow_size": 0.09999999999999432,
          "lower_shadow_size": 0.10000000000000853,
          "body_to_range_ratio": 0.0,
          "upper_shadow_to_range_ratio": 0.4999999999999645,
          "lower_shadow_to_range_ratio": 0.5000000000000355,
          "close_position_in_range": 0.5000000000000355,
          "open_position_in_range": 0.5000000000000355,
          "direction": "NEUTRAL",
          "is_bullish": false,
          "is_bearish": false,
          "is_neutral": true,
          "is_doji": true,
          "is_spinning_top": false,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T11:45:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "DOJI_INDECISION",
            "description": "Doji morphology provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T11:45:00Z"
            }
          }
        ],
        "reason_codes": [
          "SMALL_BODY_INDECISION",
          "DOJI_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T12:00:00Z",
        "morphology": {
          "timestamp": "2026-07-08T12:00:00Z",
          "open": 77.56,
          "high": 77.66,
          "low": 77.4,
          "close": 77.53,
          "volume": 19227.729,
          "real_body_size": 0.030000000000001137,
          "full_range_size": 0.2599999999999909,
          "upper_shadow_size": 0.09999999999999432,
          "lower_shadow_size": 0.12999999999999545,
          "body_to_range_ratio": 0.11538461538462379,
          "upper_shadow_to_range_ratio": 0.3846153846153762,
          "lower_shadow_to_range_ratio": 0.5,
          "close_position_in_range": 0.5,
          "open_position_in_range": 0.6153846153846237,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": true,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T12:00:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SPINNING_TOP_INDECISION",
            "description": "Spinning-top morphology provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T12:00:00Z"
            }
          }
        ],
        "reason_codes": [
          "SMALL_BODY_INDECISION",
          "SPINNING_TOP_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T12:15:00Z",
        "morphology": {
          "timestamp": "2026-07-08T12:15:00Z",
          "open": 77.53,
          "high": 77.59,
          "low": 77.43,
          "close": 77.51,
          "volume": 9794.103,
          "real_body_size": 0.01999999999999602,
          "full_range_size": 0.1599999999999966,
          "upper_shadow_size": 0.060000000000002274,
          "lower_shadow_size": 0.0799999999999983,
          "body_to_range_ratio": 0.1249999999999778,
          "upper_shadow_to_range_ratio": 0.3750000000000222,
          "lower_shadow_to_range_ratio": 0.5,
          "close_position_in_range": 0.5,
          "open_position_in_range": 0.6249999999999778,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": true,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T12:15:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SPINNING_TOP_INDECISION",
            "description": "Spinning-top morphology provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T12:15:00Z"
            }
          }
        ],
        "reason_codes": [
          "SMALL_BODY_INDECISION",
          "SPINNING_TOP_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T12:30:00Z",
        "morphology": {
          "timestamp": "2026-07-08T12:30:00Z",
          "open": 77.51,
          "high": 77.53,
          "low": 77.29,
          "close": 77.32,
          "volume": 13320.335,
          "real_body_size": 0.19000000000001194,
          "full_range_size": 0.23999999999999488,
          "upper_shadow_size": 0.01999999999999602,
          "lower_shadow_size": 0.029999999999986926,
          "body_to_range_ratio": 0.7916666666667332,
          "upper_shadow_to_range_ratio": 0.08333333333331853,
          "lower_shadow_to_range_ratio": 0.1249999999999482,
          "close_position_in_range": 0.1249999999999482,
          "open_position_in_range": 0.9166666666666815,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": true,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": true,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": true
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "STRONG_BEARISH_CANDLE_BODY",
            "description": "Strong bearish real body",
            "contribution": -0.1,
            "metadata": {
              "timestamp": "2026-07-08T12:30:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_LOW",
            "description": "Close is near the candle low",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T12:30:00Z"
            }
          }
        ],
        "reason_codes": [
          "STRONG_BEARISH_CANDLE_BODY",
          "CLOSE_NEAR_LOW"
        ]
      },
      {
        "timestamp": "2026-07-08T12:45:00Z",
        "morphology": {
          "timestamp": "2026-07-08T12:45:00Z",
          "open": 77.31,
          "high": 77.42,
          "low": 77.02,
          "close": 77.03,
          "volume": 24869.887,
          "real_body_size": 0.28000000000000114,
          "full_range_size": 0.4000000000000057,
          "upper_shadow_size": 0.10999999999999943,
          "lower_shadow_size": 0.010000000000005116,
          "body_to_range_ratio": 0.6999999999999929,
          "upper_shadow_to_range_ratio": 0.2749999999999947,
          "lower_shadow_to_range_ratio": 0.025000000000012436,
          "close_position_in_range": 0.025000000000012436,
          "open_position_in_range": 0.7250000000000053,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": true,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": true
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_LOW",
            "description": "Close is near the candle low",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T12:45:00Z"
            }
          }
        ],
        "reason_codes": [
          "CLOSE_NEAR_LOW"
        ]
      },
      {
        "timestamp": "2026-07-08T13:00:00Z",
        "morphology": {
          "timestamp": "2026-07-08T13:00:00Z",
          "open": 77.03,
          "high": 77.1,
          "low": 76.72,
          "close": 76.92,
          "volume": 79109.596,
          "real_body_size": 0.10999999999999943,
          "full_range_size": 0.37999999999999545,
          "upper_shadow_size": 0.06999999999999318,
          "lower_shadow_size": 0.20000000000000284,
          "body_to_range_ratio": 0.28947368421052827,
          "upper_shadow_to_range_ratio": 0.18421052631577373,
          "lower_shadow_to_range_ratio": 0.526315789473698,
          "close_position_in_range": 0.526315789473698,
          "open_position_in_range": 0.8157894736842263,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T13:00:00Z"
            }
          }
        ],
        "reason_codes": [
          "SMALL_BODY_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T13:15:00Z",
        "morphology": {
          "timestamp": "2026-07-08T13:15:00Z",
          "open": 76.93,
          "high": 76.96,
          "low": 76.64,
          "close": 76.85,
          "volume": 32410.936,
          "real_body_size": 0.0800000000000125,
          "full_range_size": 0.3199999999999932,
          "upper_shadow_size": 0.029999999999986926,
          "lower_shadow_size": 0.20999999999999375,
          "body_to_range_ratio": 0.2500000000000444,
          "upper_shadow_to_range_ratio": 0.09374999999996114,
          "lower_shadow_to_range_ratio": 0.6562499999999944,
          "close_position_in_range": 0.6562499999999944,
          "open_position_in_range": 0.9062500000000389,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": true,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "LONG_LOWER_SHADOW_REJECTION",
            "description": "Extended lower shadow provides rejection evidence",
            "contribution": 0.05,
            "metadata": {
              "timestamp": "2026-07-08T13:15:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T13:15:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED",
            "description": "Hammer-like shape requires trend context",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T13:15:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
            "description": "Candle shape cannot determine state without trend context",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T13:15:00Z"
            }
          }
        ],
        "reason_codes": [
          "LONG_LOWER_SHADOW_REJECTION",
          "SMALL_BODY_INDECISION",
          "HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED",
          "CANDLE_PATTERN_NEEDS_TREND_CONTEXT"
        ]
      },
      {
        "timestamp": "2026-07-08T13:30:00Z",
        "morphology": {
          "timestamp": "2026-07-08T13:30:00Z",
          "open": 76.86,
          "high": 77.46,
          "low": 76.86,
          "close": 77.31,
          "volume": 47073.929,
          "real_body_size": 0.45000000000000284,
          "full_range_size": 0.5999999999999943,
          "upper_shadow_size": 0.14999999999999147,
          "lower_shadow_size": 0.0,
          "body_to_range_ratio": 0.7500000000000119,
          "upper_shadow_to_range_ratio": 0.24999999999998815,
          "lower_shadow_to_range_ratio": 0.0,
          "close_position_in_range": 0.7500000000000119,
          "open_position_in_range": 0.0,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": true,
          "is_strong_bullish_body": true,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": true,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "STRONG_BULLISH_CANDLE_BODY",
            "description": "Strong bullish real body",
            "contribution": 0.1,
            "metadata": {
              "timestamp": "2026-07-08T13:30:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_HIGH",
            "description": "Close is near the candle high",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T13:30:00Z"
            }
          }
        ],
        "reason_codes": [
          "STRONG_BULLISH_CANDLE_BODY",
          "CLOSE_NEAR_HIGH"
        ]
      },
      {
        "timestamp": "2026-07-08T13:45:00Z",
        "morphology": {
          "timestamp": "2026-07-08T13:45:00Z",
          "open": 77.3,
          "high": 77.47,
          "low": 76.91,
          "close": 77.31,
          "volume": 38105.296,
          "real_body_size": 0.010000000000005116,
          "full_range_size": 0.5600000000000023,
          "upper_shadow_size": 0.1599999999999966,
          "lower_shadow_size": 0.39000000000000057,
          "body_to_range_ratio": 0.017857142857151922,
          "upper_shadow_to_range_ratio": 0.2857142857142785,
          "lower_shadow_to_range_ratio": 0.6964285714285696,
          "close_position_in_range": 0.7142857142857215,
          "open_position_in_range": 0.6964285714285696,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": true,
          "is_spinning_top": false,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": true,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "LONG_LOWER_SHADOW_REJECTION",
            "description": "Extended lower shadow provides rejection evidence",
            "contribution": 0.05,
            "metadata": {
              "timestamp": "2026-07-08T13:45:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T13:45:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "DOJI_INDECISION",
            "description": "Doji morphology provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T13:45:00Z"
            }
          }
        ],
        "reason_codes": [
          "LONG_LOWER_SHADOW_REJECTION",
          "SMALL_BODY_INDECISION",
          "DOJI_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T14:00:00Z",
        "morphology": {
          "timestamp": "2026-07-08T14:00:00Z",
          "open": 77.3,
          "high": 77.42,
          "low": 77.11,
          "close": 77.25,
          "volume": 29004.17,
          "real_body_size": 0.04999999999999716,
          "full_range_size": 0.3100000000000023,
          "upper_shadow_size": 0.12000000000000455,
          "lower_shadow_size": 0.14000000000000057,
          "body_to_range_ratio": 0.1612903225806348,
          "upper_shadow_to_range_ratio": 0.3870967741935602,
          "lower_shadow_to_range_ratio": 0.451612903225805,
          "close_position_in_range": 0.451612903225805,
          "open_position_in_range": 0.6129032258064397,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": true,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T14:00:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SPINNING_TOP_INDECISION",
            "description": "Spinning-top morphology provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T14:00:00Z"
            }
          }
        ],
        "reason_codes": [
          "SMALL_BODY_INDECISION",
          "SPINNING_TOP_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T14:15:00Z",
        "morphology": {
          "timestamp": "2026-07-08T14:15:00Z",
          "open": 77.24,
          "high": 77.41,
          "low": 76.88,
          "close": 77.1,
          "volume": 23276.555,
          "real_body_size": 0.14000000000000057,
          "full_range_size": 0.5300000000000011,
          "upper_shadow_size": 0.1700000000000017,
          "lower_shadow_size": 0.21999999999999886,
          "body_to_range_ratio": 0.2641509433962269,
          "upper_shadow_to_range_ratio": 0.3207547169811346,
          "lower_shadow_to_range_ratio": 0.4150943396226385,
          "close_position_in_range": 0.4150943396226385,
          "open_position_in_range": 0.6792452830188654,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T14:15:00Z"
            }
          }
        ],
        "reason_codes": [
          "SMALL_BODY_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T14:30:00Z",
        "morphology": {
          "timestamp": "2026-07-08T14:30:00Z",
          "open": 77.09,
          "high": 77.14,
          "low": 76.9,
          "close": 76.98,
          "volume": 25115.316,
          "real_body_size": 0.10999999999999943,
          "full_range_size": 0.23999999999999488,
          "upper_shadow_size": 0.04999999999999716,
          "lower_shadow_size": 0.0799999999999983,
          "body_to_range_ratio": 0.45833333333334075,
          "upper_shadow_to_range_ratio": 0.20833333333332593,
          "lower_shadow_to_range_ratio": 0.3333333333333333,
          "close_position_in_range": 0.3333333333333333,
          "open_position_in_range": 0.7916666666666741,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [],
        "reason_codes": []
      },
      {
        "timestamp": "2026-07-08T14:45:00Z",
        "morphology": {
          "timestamp": "2026-07-08T14:45:00Z",
          "open": 76.99,
          "high": 77.23,
          "low": 76.71,
          "close": 77.11,
          "volume": 35996.148,
          "real_body_size": 0.12000000000000455,
          "full_range_size": 0.5200000000000102,
          "upper_shadow_size": 0.12000000000000455,
          "lower_shadow_size": 0.28000000000000114,
          "body_to_range_ratio": 0.23076923076923497,
          "upper_shadow_to_range_ratio": 0.23076923076923497,
          "lower_shadow_to_range_ratio": 0.53846153846153,
          "close_position_in_range": 0.769230769230765,
          "open_position_in_range": 0.53846153846153,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": true,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": true,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T14:45:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_HIGH",
            "description": "Close is near the candle high",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T14:45:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SPINNING_TOP_INDECISION",
            "description": "Spinning-top morphology provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T14:45:00Z"
            }
          }
        ],
        "reason_codes": [
          "SMALL_BODY_INDECISION",
          "CLOSE_NEAR_HIGH",
          "SPINNING_TOP_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T15:00:00Z",
        "morphology": {
          "timestamp": "2026-07-08T15:00:00Z",
          "open": 77.11,
          "high": 77.15,
          "low": 76.72,
          "close": 76.73,
          "volume": 26444.617,
          "real_body_size": 0.37999999999999545,
          "full_range_size": 0.4300000000000068,
          "upper_shadow_size": 0.04000000000000625,
          "lower_shadow_size": 0.010000000000005116,
          "body_to_range_ratio": 0.8837209302325335,
          "upper_shadow_to_range_ratio": 0.09302325581396656,
          "lower_shadow_to_range_ratio": 0.0232558139534999,
          "close_position_in_range": 0.0232558139534999,
          "open_position_in_range": 0.9069767441860335,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": true,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": true,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": true
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "STRONG_BEARISH_CANDLE_BODY",
            "description": "Strong bearish real body",
            "contribution": -0.1,
            "metadata": {
              "timestamp": "2026-07-08T15:00:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_LOW",
            "description": "Close is near the candle low",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T15:00:00Z"
            }
          }
        ],
        "reason_codes": [
          "STRONG_BEARISH_CANDLE_BODY",
          "CLOSE_NEAR_LOW"
        ]
      },
      {
        "timestamp": "2026-07-08T15:15:00Z",
        "morphology": {
          "timestamp": "2026-07-08T15:15:00Z",
          "open": 76.72,
          "high": 76.82,
          "low": 76.29,
          "close": 76.41,
          "volume": 43210.928,
          "real_body_size": 0.3100000000000023,
          "full_range_size": 0.5299999999999869,
          "upper_shadow_size": 0.09999999999999432,
          "lower_shadow_size": 0.11999999999999034,
          "body_to_range_ratio": 0.5849056603773772,
          "upper_shadow_to_range_ratio": 0.1886792452830128,
          "lower_shadow_to_range_ratio": 0.22641509433961,
          "close_position_in_range": 0.22641509433961,
          "open_position_in_range": 0.8113207547169872,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": true
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_LOW",
            "description": "Close is near the candle low",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T15:15:00Z"
            }
          }
        ],
        "reason_codes": [
          "CLOSE_NEAR_LOW"
        ]
      },
      {
        "timestamp": "2026-07-08T15:30:00Z",
        "morphology": {
          "timestamp": "2026-07-08T15:30:00Z",
          "open": 76.4,
          "high": 76.68,
          "low": 76.33,
          "close": 76.52,
          "volume": 21043.213,
          "real_body_size": 0.11999999999999034,
          "full_range_size": 0.3500000000000085,
          "upper_shadow_size": 0.1600000000000108,
          "lower_shadow_size": 0.07000000000000739,
          "body_to_range_ratio": 0.3428571428571069,
          "upper_shadow_to_range_ratio": 0.4571428571428769,
          "lower_shadow_to_range_ratio": 0.20000000000001625,
          "close_position_in_range": 0.5428571428571232,
          "open_position_in_range": 0.20000000000001625,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [],
        "reason_codes": []
      },
      {
        "timestamp": "2026-07-08T15:45:00Z",
        "morphology": {
          "timestamp": "2026-07-08T15:45:00Z",
          "open": 76.51,
          "high": 76.79,
          "low": 76.46,
          "close": 76.75,
          "volume": 13738.726,
          "real_body_size": 0.23999999999999488,
          "full_range_size": 0.3300000000000125,
          "upper_shadow_size": 0.04000000000000625,
          "lower_shadow_size": 0.05000000000001137,
          "body_to_range_ratio": 0.7272727272726842,
          "upper_shadow_to_range_ratio": 0.12121212121213557,
          "lower_shadow_to_range_ratio": 0.15151515151518022,
          "close_position_in_range": 0.8787878787878645,
          "open_position_in_range": 0.15151515151518022,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": true,
          "is_strong_bullish_body": true,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": true,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "STRONG_BULLISH_CANDLE_BODY",
            "description": "Strong bullish real body",
            "contribution": 0.1,
            "metadata": {
              "timestamp": "2026-07-08T15:45:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_HIGH",
            "description": "Close is near the candle high",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T15:45:00Z"
            }
          }
        ],
        "reason_codes": [
          "STRONG_BULLISH_CANDLE_BODY",
          "CLOSE_NEAR_HIGH"
        ]
      },
      {
        "timestamp": "2026-07-08T16:00:00Z",
        "morphology": {
          "timestamp": "2026-07-08T16:00:00Z",
          "open": 76.76,
          "high": 77.0,
          "low": 76.76,
          "close": 76.97,
          "volume": 19382.204,
          "real_body_size": 0.20999999999999375,
          "full_range_size": 0.23999999999999488,
          "upper_shadow_size": 0.030000000000001137,
          "lower_shadow_size": 0.0,
          "body_to_range_ratio": 0.8749999999999926,
          "upper_shadow_to_range_ratio": 0.1250000000000074,
          "lower_shadow_to_range_ratio": 0.0,
          "close_position_in_range": 0.8749999999999926,
          "open_position_in_range": 0.0,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": true,
          "is_strong_bullish_body": true,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": true,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "STRONG_BULLISH_CANDLE_BODY",
            "description": "Strong bullish real body",
            "contribution": 0.1,
            "metadata": {
              "timestamp": "2026-07-08T16:00:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_HIGH",
            "description": "Close is near the candle high",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T16:00:00Z"
            }
          }
        ],
        "reason_codes": [
          "STRONG_BULLISH_CANDLE_BODY",
          "CLOSE_NEAR_HIGH"
        ]
      },
      {
        "timestamp": "2026-07-08T16:15:00Z",
        "morphology": {
          "timestamp": "2026-07-08T16:15:00Z",
          "open": 76.98,
          "high": 77.18,
          "low": 76.87,
          "close": 77.04,
          "volume": 13109.443,
          "real_body_size": 0.060000000000002274,
          "full_range_size": 0.3100000000000023,
          "upper_shadow_size": 0.14000000000000057,
          "lower_shadow_size": 0.10999999999999943,
          "body_to_range_ratio": 0.1935483870967801,
          "upper_shadow_to_range_ratio": 0.451612903225805,
          "lower_shadow_to_range_ratio": 0.35483870967741493,
          "close_position_in_range": 0.5483870967741951,
          "open_position_in_range": 0.35483870967741493,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": true,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T16:15:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SPINNING_TOP_INDECISION",
            "description": "Spinning-top morphology provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T16:15:00Z"
            }
          }
        ],
        "reason_codes": [
          "SMALL_BODY_INDECISION",
          "SPINNING_TOP_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T16:30:00Z",
        "morphology": {
          "timestamp": "2026-07-08T16:30:00Z",
          "open": 77.03,
          "high": 77.33,
          "low": 76.84,
          "close": 77.29,
          "volume": 26471.382,
          "real_body_size": 0.2600000000000051,
          "full_range_size": 0.4899999999999949,
          "upper_shadow_size": 0.03999999999999204,
          "lower_shadow_size": 0.18999999999999773,
          "body_to_range_ratio": 0.5306122448979752,
          "upper_shadow_to_range_ratio": 0.0816326530612091,
          "lower_shadow_to_range_ratio": 0.38775510204081576,
          "close_position_in_range": 0.9183673469387909,
          "open_position_in_range": 0.38775510204081576,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": true,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_HIGH",
            "description": "Close is near the candle high",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T16:30:00Z"
            }
          }
        ],
        "reason_codes": [
          "CLOSE_NEAR_HIGH"
        ]
      },
      {
        "timestamp": "2026-07-08T16:45:00Z",
        "morphology": {
          "timestamp": "2026-07-08T16:45:00Z",
          "open": 77.28,
          "high": 77.36,
          "low": 77.21,
          "close": 77.29,
          "volume": 16719.944,
          "real_body_size": 0.010000000000005116,
          "full_range_size": 0.15000000000000568,
          "upper_shadow_size": 0.06999999999999318,
          "lower_shadow_size": 0.07000000000000739,
          "body_to_range_ratio": 0.06666666666669825,
          "upper_shadow_to_range_ratio": 0.4666666666666035,
          "lower_shadow_to_range_ratio": 0.46666666666669826,
          "close_position_in_range": 0.5333333333333965,
          "open_position_in_range": 0.46666666666669826,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": true,
          "is_spinning_top": false,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T16:45:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "DOJI_INDECISION",
            "description": "Doji morphology provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T16:45:00Z"
            }
          }
        ],
        "reason_codes": [
          "SMALL_BODY_INDECISION",
          "DOJI_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T17:00:00Z",
        "morphology": {
          "timestamp": "2026-07-08T17:00:00Z",
          "open": 77.29,
          "high": 77.32,
          "low": 77.1,
          "close": 77.1,
          "volume": 25816.541,
          "real_body_size": 0.19000000000001194,
          "full_range_size": 0.21999999999999886,
          "upper_shadow_size": 0.029999999999986926,
          "lower_shadow_size": 0.0,
          "body_to_range_ratio": 0.8636363636364224,
          "upper_shadow_to_range_ratio": 0.13636363636357765,
          "lower_shadow_to_range_ratio": 0.0,
          "close_position_in_range": 0.0,
          "open_position_in_range": 0.8636363636364224,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": true,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": true,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": true
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "STRONG_BEARISH_CANDLE_BODY",
            "description": "Strong bearish real body",
            "contribution": -0.1,
            "metadata": {
              "timestamp": "2026-07-08T17:00:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_LOW",
            "description": "Close is near the candle low",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T17:00:00Z"
            }
          }
        ],
        "reason_codes": [
          "STRONG_BEARISH_CANDLE_BODY",
          "CLOSE_NEAR_LOW"
        ]
      },
      {
        "timestamp": "2026-07-08T17:15:00Z",
        "morphology": {
          "timestamp": "2026-07-08T17:15:00Z",
          "open": 77.09,
          "high": 77.61,
          "low": 77.09,
          "close": 77.6,
          "volume": 19973.631,
          "real_body_size": 0.5099999999999909,
          "full_range_size": 0.519999999999996,
          "upper_shadow_size": 0.010000000000005116,
          "lower_shadow_size": 0.0,
          "body_to_range_ratio": 0.9807692307692207,
          "upper_shadow_to_range_ratio": 0.019230769230779217,
          "lower_shadow_to_range_ratio": 0.0,
          "close_position_in_range": 0.9807692307692207,
          "open_position_in_range": 0.0,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": true,
          "is_strong_bullish_body": true,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": true,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "STRONG_BULLISH_CANDLE_BODY",
            "description": "Strong bullish real body",
            "contribution": 0.1,
            "metadata": {
              "timestamp": "2026-07-08T17:15:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_HIGH",
            "description": "Close is near the candle high",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T17:15:00Z"
            }
          }
        ],
        "reason_codes": [
          "STRONG_BULLISH_CANDLE_BODY",
          "CLOSE_NEAR_HIGH"
        ]
      },
      {
        "timestamp": "2026-07-08T17:30:00Z",
        "morphology": {
          "timestamp": "2026-07-08T17:30:00Z",
          "open": 77.6,
          "high": 77.68,
          "low": 77.37,
          "close": 77.41,
          "volume": 20368.703,
          "real_body_size": 0.18999999999999773,
          "full_range_size": 0.3100000000000023,
          "upper_shadow_size": 0.0800000000000125,
          "lower_shadow_size": 0.03999999999999204,
          "body_to_range_ratio": 0.6129032258064397,
          "upper_shadow_to_range_ratio": 0.2580645161290707,
          "lower_shadow_to_range_ratio": 0.1290322580644895,
          "close_position_in_range": 0.1290322580644895,
          "open_position_in_range": 0.7419354838709293,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": true,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": true
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_LOW",
            "description": "Close is near the candle low",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T17:30:00Z"
            }
          }
        ],
        "reason_codes": [
          "CLOSE_NEAR_LOW"
        ]
      },
      {
        "timestamp": "2026-07-08T17:45:00Z",
        "morphology": {
          "timestamp": "2026-07-08T17:45:00Z",
          "open": 77.41,
          "high": 77.42,
          "low": 77.04,
          "close": 77.13,
          "volume": 11014.22,
          "real_body_size": 0.28000000000000114,
          "full_range_size": 0.37999999999999545,
          "upper_shadow_size": 0.010000000000005116,
          "lower_shadow_size": 0.0899999999999892,
          "body_to_range_ratio": 0.7368421052631697,
          "upper_shadow_to_range_ratio": 0.02631578947369799,
          "lower_shadow_to_range_ratio": 0.23684210526313232,
          "close_position_in_range": 0.23684210526313232,
          "open_position_in_range": 0.973684210526302,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": true,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": true,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": true
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "STRONG_BEARISH_CANDLE_BODY",
            "description": "Strong bearish real body",
            "contribution": -0.1,
            "metadata": {
              "timestamp": "2026-07-08T17:45:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_LOW",
            "description": "Close is near the candle low",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T17:45:00Z"
            }
          }
        ],
        "reason_codes": [
          "STRONG_BEARISH_CANDLE_BODY",
          "CLOSE_NEAR_LOW"
        ]
      },
      {
        "timestamp": "2026-07-08T18:00:00Z",
        "morphology": {
          "timestamp": "2026-07-08T18:00:00Z",
          "open": 77.13,
          "high": 77.36,
          "low": 77.09,
          "close": 77.3,
          "volume": 11471.402,
          "real_body_size": 0.1700000000000017,
          "full_range_size": 0.269999999999996,
          "upper_shadow_size": 0.060000000000002274,
          "lower_shadow_size": 0.03999999999999204,
          "body_to_range_ratio": 0.6296296296296452,
          "upper_shadow_to_range_ratio": 0.22222222222223392,
          "lower_shadow_to_range_ratio": 0.14814814814812086,
          "close_position_in_range": 0.7777777777777661,
          "open_position_in_range": 0.14814814814812086,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": true,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": true,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_HIGH",
            "description": "Close is near the candle high",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T18:00:00Z"
            }
          }
        ],
        "reason_codes": [
          "CLOSE_NEAR_HIGH"
        ]
      },
      {
        "timestamp": "2026-07-08T18:15:00Z",
        "morphology": {
          "timestamp": "2026-07-08T18:15:00Z",
          "open": 77.31,
          "high": 77.32,
          "low": 77.09,
          "close": 77.12,
          "volume": 7962.595,
          "real_body_size": 0.18999999999999773,
          "full_range_size": 0.22999999999998977,
          "upper_shadow_size": 0.009999999999990905,
          "lower_shadow_size": 0.030000000000001137,
          "body_to_range_ratio": 0.826086956521766,
          "upper_shadow_to_range_ratio": 0.04347826086952761,
          "lower_shadow_to_range_ratio": 0.1304347826087064,
          "close_position_in_range": 0.1304347826087064,
          "open_position_in_range": 0.9565217391304723,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": true,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": true,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": true
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "STRONG_BEARISH_CANDLE_BODY",
            "description": "Strong bearish real body",
            "contribution": -0.1,
            "metadata": {
              "timestamp": "2026-07-08T18:15:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_LOW",
            "description": "Close is near the candle low",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T18:15:00Z"
            }
          }
        ],
        "reason_codes": [
          "STRONG_BEARISH_CANDLE_BODY",
          "CLOSE_NEAR_LOW"
        ]
      },
      {
        "timestamp": "2026-07-08T18:30:00Z",
        "morphology": {
          "timestamp": "2026-07-08T18:30:00Z",
          "open": 77.13,
          "high": 77.13,
          "low": 76.82,
          "close": 76.99,
          "volume": 13185.835,
          "real_body_size": 0.14000000000000057,
          "full_range_size": 0.3100000000000023,
          "upper_shadow_size": 0.0,
          "lower_shadow_size": 0.1700000000000017,
          "body_to_range_ratio": 0.451612903225805,
          "upper_shadow_to_range_ratio": 0.0,
          "lower_shadow_to_range_ratio": 0.5483870967741951,
          "close_position_in_range": 0.5483870967741951,
          "open_position_in_range": 1.0,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [],
        "reason_codes": []
      },
      {
        "timestamp": "2026-07-08T18:45:00Z",
        "morphology": {
          "timestamp": "2026-07-08T18:45:00Z",
          "open": 76.99,
          "high": 77.33,
          "low": 76.95,
          "close": 77.14,
          "volume": 7565.505,
          "real_body_size": 0.15000000000000568,
          "full_range_size": 0.37999999999999545,
          "upper_shadow_size": 0.18999999999999773,
          "lower_shadow_size": 0.03999999999999204,
          "body_to_range_ratio": 0.3947368421052828,
          "upper_shadow_to_range_ratio": 0.5,
          "lower_shadow_to_range_ratio": 0.10526315789471716,
          "close_position_in_range": 0.5,
          "open_position_in_range": 0.10526315789471716,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [],
        "reason_codes": []
      },
      {
        "timestamp": "2026-07-08T19:00:00Z",
        "morphology": {
          "timestamp": "2026-07-08T19:00:00Z",
          "open": 77.15,
          "high": 77.27,
          "low": 77.01,
          "close": 77.01,
          "volume": 8555.506,
          "real_body_size": 0.14000000000000057,
          "full_range_size": 0.2599999999999909,
          "upper_shadow_size": 0.11999999999999034,
          "lower_shadow_size": 0.0,
          "body_to_range_ratio": 0.5384615384615595,
          "upper_shadow_to_range_ratio": 0.4615384615384405,
          "lower_shadow_to_range_ratio": 0.0,
          "close_position_in_range": 0.0,
          "open_position_in_range": 0.5384615384615595,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": true
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_LOW",
            "description": "Close is near the candle low",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T19:00:00Z"
            }
          }
        ],
        "reason_codes": [
          "CLOSE_NEAR_LOW"
        ]
      },
      {
        "timestamp": "2026-07-08T19:15:00Z",
        "morphology": {
          "timestamp": "2026-07-08T19:15:00Z",
          "open": 77.02,
          "high": 77.25,
          "low": 76.95,
          "close": 77.14,
          "volume": 15072.029,
          "real_body_size": 0.12000000000000455,
          "full_range_size": 0.29999999999999716,
          "upper_shadow_size": 0.10999999999999943,
          "lower_shadow_size": 0.06999999999999318,
          "body_to_range_ratio": 0.40000000000001895,
          "upper_shadow_to_range_ratio": 0.36666666666666825,
          "lower_shadow_to_range_ratio": 0.2333333333333128,
          "close_position_in_range": 0.6333333333333317,
          "open_position_in_range": 0.2333333333333128,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [],
        "reason_codes": []
      },
      {
        "timestamp": "2026-07-08T19:30:00Z",
        "morphology": {
          "timestamp": "2026-07-08T19:30:00Z",
          "open": 77.14,
          "high": 77.35,
          "low": 77.12,
          "close": 77.34,
          "volume": 7299.14,
          "real_body_size": 0.20000000000000284,
          "full_range_size": 0.22999999999998977,
          "upper_shadow_size": 0.009999999999990905,
          "lower_shadow_size": 0.01999999999999602,
          "body_to_range_ratio": 0.8695652173913554,
          "upper_shadow_to_range_ratio": 0.04347826086952761,
          "lower_shadow_to_range_ratio": 0.086956521739117,
          "close_position_in_range": 0.9565217391304723,
          "open_position_in_range": 0.086956521739117,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": true,
          "is_strong_bullish_body": true,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": true,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "STRONG_BULLISH_CANDLE_BODY",
            "description": "Strong bullish real body",
            "contribution": 0.1,
            "metadata": {
              "timestamp": "2026-07-08T19:30:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_HIGH",
            "description": "Close is near the candle high",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T19:30:00Z"
            }
          }
        ],
        "reason_codes": [
          "STRONG_BULLISH_CANDLE_BODY",
          "CLOSE_NEAR_HIGH"
        ]
      },
      {
        "timestamp": "2026-07-08T19:45:00Z",
        "morphology": {
          "timestamp": "2026-07-08T19:45:00Z",
          "open": 77.34,
          "high": 77.49,
          "low": 77.14,
          "close": 77.42,
          "volume": 18843.83,
          "real_body_size": 0.0799999999999983,
          "full_range_size": 0.3499999999999943,
          "upper_shadow_size": 0.06999999999999318,
          "lower_shadow_size": 0.20000000000000284,
          "body_to_range_ratio": 0.2285714285714274,
          "upper_shadow_to_range_ratio": 0.19999999999998375,
          "lower_shadow_to_range_ratio": 0.5714285714285888,
          "close_position_in_range": 0.8000000000000163,
          "open_position_in_range": 0.5714285714285888,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": true,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": true,
          "close_near_high": true,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "LONG_LOWER_SHADOW_REJECTION",
            "description": "Extended lower shadow provides rejection evidence",
            "contribution": 0.05,
            "metadata": {
              "timestamp": "2026-07-08T19:45:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T19:45:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_HIGH",
            "description": "Close is near the candle high",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T19:45:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SPINNING_TOP_INDECISION",
            "description": "Spinning-top morphology provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T19:45:00Z"
            }
          }
        ],
        "reason_codes": [
          "LONG_LOWER_SHADOW_REJECTION",
          "SMALL_BODY_INDECISION",
          "CLOSE_NEAR_HIGH",
          "SPINNING_TOP_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T20:00:00Z",
        "morphology": {
          "timestamp": "2026-07-08T20:00:00Z",
          "open": 77.42,
          "high": 77.57,
          "low": 77.31,
          "close": 77.44,
          "volume": 8808.259,
          "real_body_size": 0.01999999999999602,
          "full_range_size": 0.2599999999999909,
          "upper_shadow_size": 0.12999999999999545,
          "lower_shadow_size": 0.10999999999999943,
          "body_to_range_ratio": 0.07692307692306431,
          "upper_shadow_to_range_ratio": 0.5,
          "lower_shadow_to_range_ratio": 0.4230769230769357,
          "close_position_in_range": 0.5,
          "open_position_in_range": 0.4230769230769357,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": true,
          "is_spinning_top": false,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T20:00:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "DOJI_INDECISION",
            "description": "Doji morphology provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T20:00:00Z"
            }
          }
        ],
        "reason_codes": [
          "SMALL_BODY_INDECISION",
          "DOJI_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T20:15:00Z",
        "morphology": {
          "timestamp": "2026-07-08T20:15:00Z",
          "open": 77.45,
          "high": 77.45,
          "low": 77.3,
          "close": 77.38,
          "volume": 4428.785,
          "real_body_size": 0.07000000000000739,
          "full_range_size": 0.15000000000000568,
          "upper_shadow_size": 0.0,
          "lower_shadow_size": 0.0799999999999983,
          "body_to_range_ratio": 0.46666666666669826,
          "upper_shadow_to_range_ratio": 0.0,
          "lower_shadow_to_range_ratio": 0.5333333333333018,
          "close_position_in_range": 0.5333333333333018,
          "open_position_in_range": 1.0,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [],
        "reason_codes": []
      },
      {
        "timestamp": "2026-07-08T20:30:00Z",
        "morphology": {
          "timestamp": "2026-07-08T20:30:00Z",
          "open": 77.38,
          "high": 77.4,
          "low": 77.08,
          "close": 77.15,
          "volume": 13356.301,
          "real_body_size": 0.22999999999998977,
          "full_range_size": 0.3200000000000074,
          "upper_shadow_size": 0.020000000000010232,
          "lower_shadow_size": 0.07000000000000739,
          "body_to_range_ratio": 0.7187499999999515,
          "upper_shadow_to_range_ratio": 0.06250000000003053,
          "lower_shadow_to_range_ratio": 0.21875000000001804,
          "close_position_in_range": 0.21875000000001804,
          "open_position_in_range": 0.9374999999999695,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": true,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": true,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": true
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "STRONG_BEARISH_CANDLE_BODY",
            "description": "Strong bearish real body",
            "contribution": -0.1,
            "metadata": {
              "timestamp": "2026-07-08T20:30:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_LOW",
            "description": "Close is near the candle low",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T20:30:00Z"
            }
          }
        ],
        "reason_codes": [
          "STRONG_BEARISH_CANDLE_BODY",
          "CLOSE_NEAR_LOW"
        ]
      },
      {
        "timestamp": "2026-07-08T20:45:00Z",
        "morphology": {
          "timestamp": "2026-07-08T20:45:00Z",
          "open": 77.15,
          "high": 77.23,
          "low": 77.05,
          "close": 77.17,
          "volume": 10549.084,
          "real_body_size": 0.01999999999999602,
          "full_range_size": 0.18000000000000682,
          "upper_shadow_size": 0.060000000000002274,
          "lower_shadow_size": 0.10000000000000853,
          "body_to_range_ratio": 0.11111111111108479,
          "upper_shadow_to_range_ratio": 0.3333333333333333,
          "lower_shadow_to_range_ratio": 0.5555555555555819,
          "close_position_in_range": 0.6666666666666666,
          "open_position_in_range": 0.5555555555555819,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": true,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": true,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "LONG_LOWER_SHADOW_REJECTION",
            "description": "Extended lower shadow provides rejection evidence",
            "contribution": 0.05,
            "metadata": {
              "timestamp": "2026-07-08T20:45:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T20:45:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SPINNING_TOP_INDECISION",
            "description": "Spinning-top morphology provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T20:45:00Z"
            }
          }
        ],
        "reason_codes": [
          "LONG_LOWER_SHADOW_REJECTION",
          "SMALL_BODY_INDECISION",
          "SPINNING_TOP_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T21:00:00Z",
        "morphology": {
          "timestamp": "2026-07-08T21:00:00Z",
          "open": 77.18,
          "high": 77.18,
          "low": 76.95,
          "close": 76.99,
          "volume": 4760.783,
          "real_body_size": 0.19000000000001194,
          "full_range_size": 0.23000000000000398,
          "upper_shadow_size": 0.0,
          "lower_shadow_size": 0.03999999999999204,
          "body_to_range_ratio": 0.8260869565217768,
          "upper_shadow_to_range_ratio": 0.0,
          "lower_shadow_to_range_ratio": 0.17391304347822326,
          "close_position_in_range": 0.17391304347822326,
          "open_position_in_range": 1.0,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": true,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": true,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": true
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "STRONG_BEARISH_CANDLE_BODY",
            "description": "Strong bearish real body",
            "contribution": -0.1,
            "metadata": {
              "timestamp": "2026-07-08T21:00:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_LOW",
            "description": "Close is near the candle low",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T21:00:00Z"
            }
          }
        ],
        "reason_codes": [
          "STRONG_BEARISH_CANDLE_BODY",
          "CLOSE_NEAR_LOW"
        ]
      },
      {
        "timestamp": "2026-07-08T21:15:00Z",
        "morphology": {
          "timestamp": "2026-07-08T21:15:00Z",
          "open": 77.0,
          "high": 77.14,
          "low": 76.93,
          "close": 77.12,
          "volume": 7458.744,
          "real_body_size": 0.12000000000000455,
          "full_range_size": 0.20999999999999375,
          "upper_shadow_size": 0.01999999999999602,
          "lower_shadow_size": 0.06999999999999318,
          "body_to_range_ratio": 0.5714285714286101,
          "upper_shadow_to_range_ratio": 0.09523809523807912,
          "lower_shadow_to_range_ratio": 0.3333333333333108,
          "close_position_in_range": 0.9047619047619209,
          "open_position_in_range": 0.3333333333333108,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": true,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_HIGH",
            "description": "Close is near the candle high",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T21:15:00Z"
            }
          }
        ],
        "reason_codes": [
          "CLOSE_NEAR_HIGH"
        ]
      },
      {
        "timestamp": "2026-07-08T21:30:00Z",
        "morphology": {
          "timestamp": "2026-07-08T21:30:00Z",
          "open": 77.12,
          "high": 77.25,
          "low": 77.02,
          "close": 77.2,
          "volume": 10382.754,
          "real_body_size": 0.0799999999999983,
          "full_range_size": 0.23000000000000398,
          "upper_shadow_size": 0.04999999999999716,
          "lower_shadow_size": 0.10000000000000853,
          "body_to_range_ratio": 0.3478260869565083,
          "upper_shadow_to_range_ratio": 0.21739130434780995,
          "lower_shadow_to_range_ratio": 0.43478260869568175,
          "close_position_in_range": 0.78260869565219,
          "open_position_in_range": 0.43478260869568175,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": true,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_HIGH",
            "description": "Close is near the candle high",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T21:30:00Z"
            }
          }
        ],
        "reason_codes": [
          "CLOSE_NEAR_HIGH"
        ]
      },
      {
        "timestamp": "2026-07-08T21:45:00Z",
        "morphology": {
          "timestamp": "2026-07-08T21:45:00Z",
          "open": 77.19,
          "high": 77.35,
          "low": 77.17,
          "close": 77.26,
          "volume": 7755.336,
          "real_body_size": 0.07000000000000739,
          "full_range_size": 0.1799999999999926,
          "upper_shadow_size": 0.0899999999999892,
          "lower_shadow_size": 0.01999999999999602,
          "body_to_range_ratio": 0.3888888888889459,
          "upper_shadow_to_range_ratio": 0.49999999999996053,
          "lower_shadow_to_range_ratio": 0.11111111111109356,
          "close_position_in_range": 0.5000000000000395,
          "open_position_in_range": 0.11111111111109356,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [],
        "reason_codes": []
      },
      {
        "timestamp": "2026-07-08T22:00:00Z",
        "morphology": {
          "timestamp": "2026-07-08T22:00:00Z",
          "open": 77.26,
          "high": 77.48,
          "low": 77.2,
          "close": 77.26,
          "volume": 9190.331,
          "real_body_size": 0.0,
          "full_range_size": 0.28000000000000114,
          "upper_shadow_size": 0.21999999999999886,
          "lower_shadow_size": 0.060000000000002274,
          "body_to_range_ratio": 0.0,
          "upper_shadow_to_range_ratio": 0.7857142857142785,
          "lower_shadow_to_range_ratio": 0.21428571428572155,
          "close_position_in_range": 0.21428571428572155,
          "open_position_in_range": 0.21428571428572155,
          "direction": "NEUTRAL",
          "is_bullish": false,
          "is_bearish": false,
          "is_neutral": true,
          "is_doji": true,
          "is_spinning_top": false,
          "is_small_body": true,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": true,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": true
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "LONG_UPPER_SHADOW_REJECTION",
            "description": "Extended upper shadow provides rejection evidence",
            "contribution": -0.05,
            "metadata": {
              "timestamp": "2026-07-08T22:00:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "SMALL_BODY_INDECISION",
            "description": "Small real body provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T22:00:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_LOW",
            "description": "Close is near the candle low",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T22:00:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "DOJI_INDECISION",
            "description": "Doji morphology provides indecision evidence",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T22:00:00Z"
            }
          }
        ],
        "reason_codes": [
          "LONG_UPPER_SHADOW_REJECTION",
          "SMALL_BODY_INDECISION",
          "CLOSE_NEAR_LOW",
          "DOJI_INDECISION"
        ]
      },
      {
        "timestamp": "2026-07-08T22:15:00Z",
        "morphology": {
          "timestamp": "2026-07-08T22:15:00Z",
          "open": 77.27,
          "high": 77.41,
          "low": 77.18,
          "close": 77.4,
          "volume": 11105.202,
          "real_body_size": 0.13000000000000966,
          "full_range_size": 0.22999999999998977,
          "upper_shadow_size": 0.009999999999990905,
          "lower_shadow_size": 0.0899999999999892,
          "body_to_range_ratio": 0.565217391304415,
          "upper_shadow_to_range_ratio": 0.04347826086952761,
          "lower_shadow_to_range_ratio": 0.3913043478260574,
          "close_position_in_range": 0.9565217391304723,
          "open_position_in_range": 0.3913043478260574,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": true,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_HIGH",
            "description": "Close is near the candle high",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T22:15:00Z"
            }
          }
        ],
        "reason_codes": [
          "CLOSE_NEAR_HIGH"
        ]
      },
      {
        "timestamp": "2026-07-08T22:30:00Z",
        "morphology": {
          "timestamp": "2026-07-08T22:30:00Z",
          "open": 77.4,
          "high": 77.47,
          "low": 77.3,
          "close": 77.46,
          "volume": 10103.83,
          "real_body_size": 0.05999999999998806,
          "full_range_size": 0.1700000000000017,
          "upper_shadow_size": 0.010000000000005116,
          "lower_shadow_size": 0.10000000000000853,
          "body_to_range_ratio": 0.3529411764705145,
          "upper_shadow_to_range_ratio": 0.05882352941179421,
          "lower_shadow_to_range_ratio": 0.5882352941176913,
          "close_position_in_range": 0.9411764705882057,
          "open_position_in_range": 0.5882352941176913,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": true,
          "close_near_high": true,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "LONG_LOWER_SHADOW_REJECTION",
            "description": "Extended lower shadow provides rejection evidence",
            "contribution": 0.05,
            "metadata": {
              "timestamp": "2026-07-08T22:30:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_HIGH",
            "description": "Close is near the candle high",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T22:30:00Z"
            }
          }
        ],
        "reason_codes": [
          "LONG_LOWER_SHADOW_REJECTION",
          "CLOSE_NEAR_HIGH"
        ]
      },
      {
        "timestamp": "2026-07-08T22:45:00Z",
        "morphology": {
          "timestamp": "2026-07-08T22:45:00Z",
          "open": 77.45,
          "high": 77.59,
          "low": 77.44,
          "close": 77.55,
          "volume": 13018.08,
          "real_body_size": 0.09999999999999432,
          "full_range_size": 0.15000000000000568,
          "upper_shadow_size": 0.04000000000000625,
          "lower_shadow_size": 0.010000000000005116,
          "body_to_range_ratio": 0.6666666666666035,
          "upper_shadow_to_range_ratio": 0.26666666666669825,
          "lower_shadow_to_range_ratio": 0.06666666666669825,
          "close_position_in_range": 0.7333333333333018,
          "open_position_in_range": 0.06666666666669825,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": true,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [],
        "reason_codes": []
      },
      {
        "timestamp": "2026-07-08T23:00:00Z",
        "morphology": {
          "timestamp": "2026-07-08T23:00:00Z",
          "open": 77.54,
          "high": 77.66,
          "low": 77.47,
          "close": 77.63,
          "volume": 5802.773,
          "real_body_size": 0.0899999999999892,
          "full_range_size": 0.18999999999999773,
          "upper_shadow_size": 0.030000000000001137,
          "lower_shadow_size": 0.07000000000000739,
          "body_to_range_ratio": 0.47368421052626464,
          "upper_shadow_to_range_ratio": 0.15789473684211314,
          "lower_shadow_to_range_ratio": 0.3684210526316222,
          "close_position_in_range": 0.8421052631578869,
          "open_position_in_range": 0.3684210526316222,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": true,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_HIGH",
            "description": "Close is near the candle high",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T23:00:00Z"
            }
          }
        ],
        "reason_codes": [
          "CLOSE_NEAR_HIGH"
        ]
      },
      {
        "timestamp": "2026-07-08T23:15:00Z",
        "morphology": {
          "timestamp": "2026-07-08T23:15:00Z",
          "open": 77.63,
          "high": 77.63,
          "low": 77.47,
          "close": 77.56,
          "volume": 6988.86,
          "real_body_size": 0.06999999999999318,
          "full_range_size": 0.1599999999999966,
          "upper_shadow_size": 0.0,
          "lower_shadow_size": 0.09000000000000341,
          "body_to_range_ratio": 0.4374999999999667,
          "upper_shadow_to_range_ratio": 0.0,
          "lower_shadow_to_range_ratio": 0.5625000000000333,
          "close_position_in_range": 0.5625000000000333,
          "open_position_in_range": 1.0,
          "direction": "BEARISH",
          "is_bullish": false,
          "is_bearish": true,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": true,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "LONG_LOWER_SHADOW_REJECTION",
            "description": "Extended lower shadow provides rejection evidence",
            "contribution": 0.05,
            "metadata": {
              "timestamp": "2026-07-08T23:15:00Z"
            }
          }
        ],
        "reason_codes": [
          "LONG_LOWER_SHADOW_REJECTION"
        ]
      },
      {
        "timestamp": "2026-07-08T23:30:00Z",
        "morphology": {
          "timestamp": "2026-07-08T23:30:00Z",
          "open": 77.56,
          "high": 77.63,
          "low": 77.43,
          "close": 77.62,
          "volume": 8679.401,
          "real_body_size": 0.060000000000002274,
          "full_range_size": 0.19999999999998863,
          "upper_shadow_size": 0.009999999999990905,
          "lower_shadow_size": 0.12999999999999545,
          "body_to_range_ratio": 0.3000000000000284,
          "upper_shadow_to_range_ratio": 0.04999999999995737,
          "lower_shadow_to_range_ratio": 0.6500000000000142,
          "close_position_in_range": 0.9500000000000426,
          "open_position_in_range": 0.6500000000000142,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": true,
          "close_near_high": true,
          "close_near_low": false
        },
        "evidence": [
          {
            "source": "NISON",
            "code": "LONG_LOWER_SHADOW_REJECTION",
            "description": "Extended lower shadow provides rejection evidence",
            "contribution": 0.05,
            "metadata": {
              "timestamp": "2026-07-08T23:30:00Z"
            }
          },
          {
            "source": "NISON",
            "code": "CLOSE_NEAR_HIGH",
            "description": "Close is near the candle high",
            "contribution": 0.0,
            "metadata": {
              "timestamp": "2026-07-08T23:30:00Z"
            }
          }
        ],
        "reason_codes": [
          "LONG_LOWER_SHADOW_REJECTION",
          "CLOSE_NEAR_HIGH"
        ]
      },
      {
        "timestamp": "2026-07-08T23:45:00Z",
        "morphology": {
          "timestamp": "2026-07-08T23:45:00Z",
          "open": 77.61,
          "high": 77.95,
          "low": 77.55,
          "close": 77.83,
          "volume": 16187.387,
          "real_body_size": 0.21999999999999886,
          "full_range_size": 0.4000000000000057,
          "upper_shadow_size": 0.12000000000000455,
          "lower_shadow_size": 0.060000000000002274,
          "body_to_range_ratio": 0.5499999999999894,
          "upper_shadow_to_range_ratio": 0.3000000000000071,
          "lower_shadow_to_range_ratio": 0.15000000000000355,
          "close_position_in_range": 0.6999999999999929,
          "open_position_in_range": 0.15000000000000355,
          "direction": "BULLISH",
          "is_bullish": true,
          "is_bearish": false,
          "is_neutral": false,
          "is_doji": false,
          "is_spinning_top": false,
          "is_small_body": false,
          "is_long_body": false,
          "is_strong_bullish_body": false,
          "is_strong_bearish_body": false,
          "has_long_upper_shadow": false,
          "has_long_lower_shadow": false,
          "close_near_high": false,
          "close_near_low": false
        },
        "evidence": [],
        "reason_codes": []
      }
    ]
  }
}
```

## Hypotheses

```json
[
  {
    "hypothesis_id": "hypothesis:confirmed_range",
    "hypothesis_type": "CONFIRMED_RANGE",
    "direction": "FLAT",
    "status": "CONFIRMED",
    "score": 0.6230769230769231,
    "trigger_index": 92,
    "confirmation_index": null,
    "supporting_event_ids": [],
    "reason_codes": [
      "HYPOTHESIS_RANGE_STRUCTURE_CONFIRMED",
      "HYPOTHESIS_SECONDARY_FLAT_CONTEXT_CONFIRMED",
      "HYPOTHESIS_RANGE_BOUNDARIES_HELD"
    ],
    "confidence": 0.6230769230769231,
    "confidence_note": "Model exports score, not a separate per-hypothesis confidence; score is repeated as the available confidence proxy.",
    "evidence": {
      "reason_codes": [
        "HYPOTHESIS_RANGE_STRUCTURE_CONFIRMED",
        "HYPOTHESIS_SECONDARY_FLAT_CONTEXT_CONFIRMED",
        "HYPOTHESIS_RANGE_BOUNDARIES_HELD"
      ],
      "supporting_events": []
    },
    "missing_evidence": [],
    "rejection_reason": null,
    "pending_reason": null,
    "conflict_reason": null
  }
]
```

## Safety audit

```json
{
  "main_period": {
    "safety_violation": false,
    "violations": [],
    "checks": {
      "false_up_after_declining_window": false,
      "down_without_sufficient_confirmation": false,
      "forced_answer_where_unknown_expected": false,
      "opposite_directional_conflicts": false
    },
    "selected_hypothesis_confirmed_and_aligned": true,
    "opposite_confirmed_hypotheses": [],
    "window_return": -0.03412757508066522,
    "engine_safety_contract": {
      "trade_signal": "NOT_EVALUATED",
      "safe_for_runtime_trading": false,
      "live_trading_connected": false
    }
  },
  "windows": {
    "SOLUSDT_2026_07_08_06_00": {
      "safety_violation": false,
      "violations": [],
      "checks": {
        "false_up_after_declining_window": false,
        "down_without_sufficient_confirmation": false,
        "forced_answer_where_unknown_expected": false,
        "opposite_directional_conflicts": false
      },
      "selected_hypothesis_confirmed_and_aligned": true,
      "opposite_confirmed_hypotheses": [],
      "window_return": -0.03175583837884599,
      "engine_safety_contract": {
        "trade_signal": "NOT_EVALUATED",
        "safe_for_runtime_trading": false,
        "live_trading_connected": false
      }
    },
    "SOLUSDT_2026_07_08_11_30": {
      "safety_violation": false,
      "violations": [],
      "checks": {
        "false_up_after_declining_window": false,
        "down_without_sufficient_confirmation": false,
        "forced_answer_where_unknown_expected": false,
        "opposite_directional_conflicts": false
      },
      "selected_hypothesis_confirmed_and_aligned": false,
      "opposite_confirmed_hypotheses": [],
      "window_return": -0.04448003942828982,
      "engine_safety_contract": {
        "trade_signal": "NOT_EVALUATED",
        "safe_for_runtime_trading": false,
        "live_trading_connected": false
      }
    },
    "SOLUSDT_2026_07_08_18_30": {
      "safety_violation": false,
      "violations": [],
      "checks": {
        "false_up_after_declining_window": false,
        "down_without_sufficient_confirmation": false,
        "forced_answer_where_unknown_expected": false,
        "opposite_directional_conflicts": false
      },
      "selected_hypothesis_confirmed_and_aligned": false,
      "opposite_confirmed_hypotheses": [],
      "window_return": -0.06395136778115507,
      "engine_safety_contract": {
        "trade_signal": "NOT_EVALUATED",
        "safe_for_runtime_trading": false,
        "live_trading_connected": false
      }
    },
    "SOLUSDT_2026_07_08_23_45": {
      "safety_violation": false,
      "violations": [],
      "checks": {
        "false_up_after_declining_window": false,
        "down_without_sufficient_confirmation": false,
        "forced_answer_where_unknown_expected": false,
        "opposite_directional_conflicts": false
      },
      "selected_hypothesis_confirmed_and_aligned": true,
      "opposite_confirmed_hypotheses": [],
      "window_return": -0.03412757508066522,
      "engine_safety_contract": {
        "trade_signal": "NOT_EVALUATED",
        "safe_for_runtime_trading": false,
        "live_trading_connected": false
      }
    }
  },
  "any_safety_violation": false
}
```
