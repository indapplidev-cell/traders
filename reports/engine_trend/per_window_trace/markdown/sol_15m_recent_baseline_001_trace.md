# sol_15m_recent_baseline_001 вЂ” Market Evidence Trace

## Window
- Symbol: SOLUSDT
- Interval: 15m
- Period: 2026-06-14T20:30:00+00:00 вЂ” 2026-06-15T20:15:00+00:00
- Reference label: EXPECTED_UNKNOWN_OR_MIXED
- Selection reason: latest 96 candles; provisional neutral reference, not selected from engine output

## Final engine result
- Market regime: UNKNOWN
- Confidence: 0.3
- Boundary status: READY
- Safety: NOT_EVALUATED; runtime false; live false

## 1. Nison candle context
### Important candle events
```json
[
  {
    "timestamp": "2026-06-14 20:45:00+00:00",
    "candle_index": 1,
    "open": 67.92,
    "high": 67.97,
    "low": 67.79,
    "close": 67.81,
    "body_pct": 0.611111111111133,
    "upper_shadow_pct": 0.2777777777777734,
    "lower_shadow_pct": 0.11111111111109356,
    "position_in_window": 0.0105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-06-14 21:00:00+00:00",
    "candle_index": 2,
    "open": 67.8,
    "high": 68.04,
    "low": 67.8,
    "close": 68.02,
    "body_pct": 0.9166666666666272,
    "upper_shadow_pct": 0.08333333333337281,
    "lower_shadow_pct": 0.0,
    "position_in_window": 0.0211,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-06-14 21:15:00+00:00",
    "candle_index": 3,
    "open": 68.03,
    "high": 69.49,
    "low": 68.03,
    "close": 69.27,
    "body_pct": 0.8493150684931509,
    "upper_shadow_pct": 0.15068493150684917,
    "lower_shadow_pct": 0.0,
    "position_in_window": 0.0316,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-06-14 21:30:00+00:00",
    "candle_index": 4,
    "open": 69.27,
    "high": 70.38,
    "low": 69.27,
    "close": 70.23,
    "body_pct": 0.8648648648648725,
    "upper_shadow_pct": 0.1351351351351275,
    "lower_shadow_pct": 0.0,
    "position_in_window": 0.0421,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-06-14 21:45:00+00:00",
    "candle_index": 5,
    "open": 70.23,
    "high": 70.55,
    "low": 69.98,
    "close": 70.16,
    "body_pct": 0.12280701754387409,
    "upper_shadow_pct": 0.5614035087719246,
    "lower_shadow_pct": 0.31578947368420135,
    "position_in_window": 0.0526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2026-06-14 22:00:00+00:00",
    "candle_index": 6,
    "open": 70.16,
    "high": 70.52,
    "low": 69.68,
    "close": 70.17,
    "body_pct": 0.011904761904768147,
    "upper_shadow_pct": 0.41666666666666524,
    "lower_shadow_pct": 0.5714285714285666,
    "position_in_window": 0.0632,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "DOJI_INDECISION"
    ]
  },
  {
    "timestamp": "2026-06-14 22:15:00+00:00",
    "candle_index": 7,
    "open": 70.16,
    "high": 70.44,
    "low": 69.92,
    "close": 70.18,
    "body_pct": 0.038461538461558434,
    "upper_shadow_pct": 0.49999999999998634,
    "lower_shadow_pct": 0.46153846153845524,
    "position_in_window": 0.0737,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "DOJI_INDECISION"
    ]
  },
  {
    "timestamp": "2026-06-14 22:30:00+00:00",
    "candle_index": 8,
    "open": 70.17,
    "high": 70.73,
    "low": 70.13,
    "close": 70.6,
    "body_pct": 0.7166666666666441,
    "upper_shadow_pct": 0.2166666666666797,
    "lower_shadow_pct": 0.06666666666667614,
    "position_in_window": 0.0842,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-06-14 23:00:00+00:00",
    "candle_index": 10,
    "open": 70.45,
    "high": 70.68,
    "low": 70.15,
    "close": 70.58,
    "body_pct": 0.24528301886791543,
    "upper_shadow_pct": 0.18867924528303456,
    "lower_shadow_pct": 0.56603773584905,
    "position_in_window": 0.1053,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "CLOSE_NEAR_HIGH",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2026-06-14 23:15:00+00:00",
    "candle_index": 11,
    "open": 70.59,
    "high": 70.89,
    "low": 70.42,
    "close": 70.79,
    "body_pct": 0.4255319148936241,
    "upper_shadow_pct": 0.21276595744679694,
    "lower_shadow_pct": 0.361702127659579,
    "position_in_window": 0.1158,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-06-14 23:30:00+00:00",
    "candle_index": 12,
    "open": 70.79,
    "high": 70.89,
    "low": 70.56,
    "close": 70.71,
    "body_pct": 0.24242424242428157,
    "upper_shadow_pct": 0.3030303030302874,
    "lower_shadow_pct": 0.45454545454543105,
    "position_in_window": 0.1263,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2026-06-14 23:45:00+00:00",
    "candle_index": 13,
    "open": 70.71,
    "high": 71.29,
    "low": 70.7,
    "close": 71.28,
    "body_pct": 0.9661016949152612,
    "upper_shadow_pct": 0.016949152542381454,
    "lower_shadow_pct": 0.01694915254235737,
    "position_in_window": 0.1368,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-06-15 00:00:00+00:00",
    "candle_index": 14,
    "open": 71.29,
    "high": 71.73,
    "low": 71.14,
    "close": 71.68,
    "body_pct": 0.6610169491525395,
    "upper_shadow_pct": 0.0847457627118591,
    "lower_shadow_pct": 0.25423728813560137,
    "position_in_window": 0.1474,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-06-15 00:15:00+00:00",
    "candle_index": 15,
    "open": 71.69,
    "high": 71.72,
    "low": 71.3,
    "close": 71.6,
    "body_pct": 0.21428571428572155,
    "upper_shadow_pct": 0.07142857142857384,
    "lower_shadow_pct": 0.7142857142857046,
    "position_in_window": 0.1579,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION",
      "HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED",
      "CANDLE_PATTERN_NEEDS_TREND_CONTEXT"
    ]
  },
  {
    "timestamp": "2026-06-15 00:30:00+00:00",
    "candle_index": 16,
    "open": 71.6,
    "high": 71.6,
    "low": 70.94,
    "close": 71.04,
    "body_pct": 0.8484848484848347,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.15151515151516523,
    "position_in_window": 0.1684,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-06-15 01:00:00+00:00",
    "candle_index": 18,
    "open": 71.13,
    "high": 71.14,
    "low": 70.66,
    "close": 70.99,
    "body_pct": 0.2916666666666654,
    "upper_shadow_pct": 0.02083333333334382,
    "lower_shadow_pct": 0.6874999999999908,
    "position_in_window": 0.1895,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED",
      "CANDLE_PATTERN_NEEDS_TREND_CONTEXT"
    ]
  },
  {
    "timestamp": "2026-06-15 01:30:00+00:00",
    "candle_index": 20,
    "open": 70.8,
    "high": 71.33,
    "low": 70.74,
    "close": 71.33,
    "body_pct": 0.8983050847457594,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.10169491525424056,
    "position_in_window": 0.2105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-06-15 01:45:00+00:00",
    "candle_index": 21,
    "open": 71.33,
    "high": 71.35,
    "low": 70.91,
    "close": 71.01,
    "body_pct": 0.7272727272727155,
    "upper_shadow_pct": 0.04545454545453664,
    "lower_shadow_pct": 0.22727272727274783,
    "position_in_window": 0.2211,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-06-15 02:00:00+00:00",
    "candle_index": 22,
    "open": 71.0,
    "high": 71.33,
    "low": 70.92,
    "close": 71.29,
    "body_pct": 0.7073170731707529,
    "upper_shadow_pct": 0.0975609756097375,
    "lower_shadow_pct": 0.19512195121950965,
    "position_in_window": 0.2316,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-06-15 02:15:00+00:00",
    "candle_index": 23,
    "open": 71.3,
    "high": 71.59,
    "low": 71.26,
    "close": 71.28,
    "body_pct": 0.06060606060604886,
    "upper_shadow_pct": 0.8787878787879023,
    "lower_shadow_pct": 0.06060606060604886,
    "position_in_window": 0.2421,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "CLOSE_NEAR_LOW",
      "DOJI_INDECISION",
      "SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED",
      "CANDLE_PATTERN_NEEDS_TREND_CONTEXT"
    ]
  },
  {
    "timestamp": "2026-06-15 02:30:00+00:00",
    "candle_index": 24,
    "open": 71.27,
    "high": 71.32,
    "low": 71.15,
    "close": 71.15,
    "body_pct": 0.7058823529411715,
    "upper_shadow_pct": 0.2941176470588284,
    "lower_shadow_pct": 0.0,
    "position_in_window": 0.2526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-06-15 03:00:00+00:00",
    "candle_index": 26,
    "open": 70.98,
    "high": 71.25,
    "low": 70.91,
    "close": 71.23,
    "body_pct": 0.7352941176470514,
    "upper_shadow_pct": 0.05882352941175241,
    "lower_shadow_pct": 0.20588235294119614,
    "position_in_window": 0.2737,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-06-15 03:15:00+00:00",
    "candle_index": 27,
    "open": 71.23,
    "high": 71.25,
    "low": 71.12,
    "close": 71.2,
    "body_pct": 0.23076923076924757,
    "upper_shadow_pct": 0.15384615384612862,
    "lower_shadow_pct": 0.6153846153846237,
    "position_in_window": 0.2842,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2026-06-15 03:30:00+00:00",
    "candle_index": 28,
    "open": 71.21,
    "high": 71.36,
    "low": 71.07,
    "close": 71.35,
    "body_pct": 0.4827586206896467,
    "upper_shadow_pct": 0.03448275862070655,
    "lower_shadow_pct": 0.4827586206896467,
    "position_in_window": 0.2947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-06-15 03:45:00+00:00",
    "candle_index": 29,
    "open": 71.34,
    "high": 71.37,
    "low": 71.21,
    "close": 71.24,
    "body_pct": 0.6250000000000111,
    "upper_shadow_pct": 0.18749999999999445,
    "lower_shadow_pct": 0.18749999999999445,
    "position_in_window": 0.3053,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-06-15 04:00:00+00:00",
    "candle_index": 30,
    "open": 71.24,
    "high": 71.24,
    "low": 71.07,
    "close": 71.19,
    "body_pct": 0.29411764705880383,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.7058823529411962,
    "position_in_window": 0.3158,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED",
      "CANDLE_PATTERN_NEEDS_TREND_CONTEXT"
    ]
  },
  {
    "timestamp": "2026-06-15 04:15:00+00:00",
    "candle_index": 31,
    "open": 71.2,
    "high": 71.27,
    "low": 71.07,
    "close": 71.09,
    "body_pct": 0.5499999999999894,
    "upper_shadow_pct": 0.3499999999999609,
    "lower_shadow_pct": 0.10000000000004974,
    "position_in_window": 0.3263,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-06-15 04:30:00+00:00",
    "candle_index": 32,
    "open": 71.09,
    "high": 71.14,
    "low": 70.9,
    "close": 70.94,
    "body_pct": 0.625000000000037,
    "upper_shadow_pct": 0.20833333333332593,
    "lower_shadow_pct": 0.16666666666663707,
    "position_in_window": 0.3368,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-06-15 04:45:00+00:00",
    "candle_index": 33,
    "open": 70.95,
    "high": 71.04,
    "low": 70.88,
    "close": 70.93,
    "body_pct": 0.1249999999999667,
    "upper_shadow_pct": 0.5624999999999833,
    "lower_shadow_pct": 0.31250000000004996,
    "position_in_window": 0.3474,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2026-06-15 05:00:00+00:00",
    "candle_index": 34,
    "open": 70.92,
    "high": 71.03,
    "low": 70.81,
    "close": 70.97,
    "body_pct": 0.22727272727271552,
    "upper_shadow_pct": 0.2727272727272845,
    "lower_shadow_pct": 0.5,
    "position_in_window": 0.3579,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  }
]
```
### Doji / spinning top / small body cluster
```json
{
  "doji_count": 8,
  "doji_ratio": 0.08333333333333333,
  "small_body_count": 33,
  "small_body_ratio": 0.34375,
  "bullish_body_total": 14.0,
  "bearish_body_total": 6.680000000000035
}
```
### Hammer / hanging man candidates
See important events and reason codes; each shape requires context and is not a signal.
### Shooting star / inverted hammer candidates
See important events and reason codes.
### Engulfing / outside bar candidates
```json
[
  {
    "source": "NISON",
    "code": "BULLISH_ENGULFING_CONTEXT",
    "description": "Bullish body engulfs the preceding bearish body",
    "contribution": 0.1,
    "metadata": {
      "previous_timestamp": "2026-06-14 20:45:00+00:00",
      "timestamp": "2026-06-14 21:00:00+00:00",
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
      "previous_timestamp": "2026-06-14 20:45:00+00:00",
      "timestamp": "2026-06-14 21:00:00+00:00",
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
      "previous_timestamp": "2026-06-14 23:30:00+00:00",
      "timestamp": "2026-06-14 23:45:00+00:00",
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
      "previous_timestamp": "2026-06-14 23:30:00+00:00",
      "timestamp": "2026-06-14 23:45:00+00:00",
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
      "previous_timestamp": "2026-06-15 00:45:00+00:00",
      "timestamp": "2026-06-15 01:00:00+00:00",
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
      "previous_timestamp": "2026-06-15 00:45:00+00:00",
      "timestamp": "2026-06-15 01:00:00+00:00",
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
      "previous_timestamp": "2026-06-15 01:15:00+00:00",
      "timestamp": "2026-06-15 01:30:00+00:00",
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
      "previous_timestamp": "2026-06-15 01:15:00+00:00",
      "timestamp": "2026-06-15 01:30:00+00:00",
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
      "previous_timestamp": "2026-06-15 02:45:00+00:00",
      "timestamp": "2026-06-15 03:00:00+00:00",
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
      "previous_timestamp": "2026-06-15 02:45:00+00:00",
      "timestamp": "2026-06-15 03:00:00+00:00",
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
      "previous_timestamp": "2026-06-15 04:45:00+00:00",
      "timestamp": "2026-06-15 05:00:00+00:00",
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
      "previous_timestamp": "2026-06-15 04:45:00+00:00",
      "timestamp": "2026-06-15 05:00:00+00:00",
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
      "previous_timestamp": "2026-06-15 05:30:00+00:00",
      "timestamp": "2026-06-15 05:45:00+00:00",
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
      "previous_timestamp": "2026-06-15 05:30:00+00:00",
      "timestamp": "2026-06-15 05:45:00+00:00",
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
      "previous_timestamp": "2026-06-15 06:00:00+00:00",
      "timestamp": "2026-06-15 06:15:00+00:00",
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
      "previous_timestamp": "2026-06-15 06:00:00+00:00",
      "timestamp": "2026-06-15 06:15:00+00:00",
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
      "previous_timestamp": "2026-06-15 07:45:00+00:00",
      "timestamp": "2026-06-15 08:00:00+00:00",
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
      "previous_timestamp": "2026-06-15 07:45:00+00:00",
      "timestamp": "2026-06-15 08:00:00+00:00",
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
      "previous_timestamp": "2026-06-15 09:30:00+00:00",
      "timestamp": "2026-06-15 09:45:00+00:00",
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
      "previous_timestamp": "2026-06-15 09:30:00+00:00",
      "timestamp": "2026-06-15 09:45:00+00:00",
      "trend_context_evaluated": false,
      "follow_through_evaluated": false
    }
  }
]
```
### Morning/evening star candidates
```json
[]
```
### Candle context conclusion
CLOSE_NEAR_LOW, STRONG_BULLISH_CANDLE_BODY, CLOSE_NEAR_HIGH, LONG_UPPER_SHADOW_REJECTION, SMALL_BODY_INDECISION, SPINNING_TOP_INDECISION, LONG_LOWER_SHADOW_REJECTION, DOJI_INDECISION, HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED, CANDLE_PATTERN_NEEDS_TREND_CONTEXT, STRONG_BEARISH_CANDLE_BODY, SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED, BULLISH_ENGULFING_CONTEXT, ENGULFING_WITHOUT_FOLLOW_THROUGH, BEARISH_ENGULFING_CONTEXT, BULLISH_BELT_HOLD_CONTEXT_REQUIRED, LONG_LEGGED_DOJI_CONTEXT, RICKSHAW_MAN_DOJI_CONTEXT, HANGING_MAN_LIKE_CONTEXT_REQUIRED, REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH, BEARISH_BELT_HOLD_CONTEXT_REQUIRED, INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED, TWEEZERS_BOTTOM_CONTEXT_REQUIRED, BEARISH_HARAMI_CONTEXT, TWEEZERS_TOP_CONTEXT_REQUIRED, DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT, DOJI_TOP_CONTEXT_REQUIRED, HARAMI_CROSS_CONTEXT, BULLISH_SEPARATING_LINES_CONTEXT, THREE_ADVANCING_WHITE_SOLDIERS_CONTEXT, THREE_BUDDHA_TOP_CONTEXT_REQUIRED, BULLISH_BODY_DOMINANCE

## 2. Altunina trend context
### Swing structure
```json
[
  {
    "index": 5,
    "timestamp": "2026-06-14 21:45:00+00:00",
    "price": 70.55,
    "point_type": "HIGH"
  },
  {
    "index": 6,
    "timestamp": "2026-06-14 22:00:00+00:00",
    "price": 69.68,
    "point_type": "LOW"
  },
  {
    "index": 8,
    "timestamp": "2026-06-14 22:30:00+00:00",
    "price": 70.73,
    "point_type": "HIGH"
  },
  {
    "index": 10,
    "timestamp": "2026-06-14 23:00:00+00:00",
    "price": 70.15,
    "point_type": "LOW"
  },
  {
    "index": 14,
    "timestamp": "2026-06-15 00:00:00+00:00",
    "price": 71.73,
    "point_type": "HIGH"
  },
  {
    "index": 18,
    "timestamp": "2026-06-15 01:00:00+00:00",
    "price": 70.66,
    "point_type": "LOW"
  },
  {
    "index": 23,
    "timestamp": "2026-06-15 02:15:00+00:00",
    "price": 71.59,
    "point_type": "HIGH"
  },
  {
    "index": 25,
    "timestamp": "2026-06-15 02:45:00+00:00",
    "price": 70.9,
    "point_type": "LOW"
  },
  {
    "index": 29,
    "timestamp": "2026-06-15 03:45:00+00:00",
    "price": 71.37,
    "point_type": "HIGH"
  },
  {
    "index": 34,
    "timestamp": "2026-06-15 05:00:00+00:00",
    "price": 70.81,
    "point_type": "LOW"
  },
  {
    "index": 41,
    "timestamp": "2026-06-15 06:45:00+00:00",
    "price": 71.5,
    "point_type": "HIGH"
  },
  {
    "index": 42,
    "timestamp": "2026-06-15 07:00:00+00:00",
    "price": 71.12,
    "point_type": "LOW"
  },
  {
    "index": 43,
    "timestamp": "2026-06-15 07:15:00+00:00",
    "price": 71.5,
    "point_type": "HIGH"
  },
  {
    "index": 44,
    "timestamp": "2026-06-15 07:30:00+00:00",
    "price": 71.14,
    "point_type": "LOW"
  },
  {
    "index": 47,
    "timestamp": "2026-06-15 08:15:00+00:00",
    "price": 71.62,
    "point_type": "HIGH"
  },
  {
    "index": 52,
    "timestamp": "2026-06-15 09:30:00+00:00",
    "price": 70.8,
    "point_type": "LOW"
  },
  {
    "index": 59,
    "timestamp": "2026-06-15 11:15:00+00:00",
    "price": 72.82,
    "point_type": "HIGH"
  },
  {
    "index": 63,
    "timestamp": "2026-06-15 12:15:00+00:00",
    "price": 72.31,
    "point_type": "LOW"
  },
  {
    "index": 64,
    "timestamp": "2026-06-15 12:30:00+00:00",
    "price": 73.0,
    "point_type": "HIGH"
  },
  {
    "index": 66,
    "timestamp": "2026-06-15 13:00:00+00:00",
    "price": 72.72,
    "point_type": "LOW"
  },
  {
    "index": 67,
    "timestamp": "2026-06-15 13:15:00+00:00",
    "price": 74.23,
    "point_type": "HIGH"
  },
  {
    "index": 70,
    "timestamp": "2026-06-15 14:00:00+00:00",
    "price": 73.2,
    "point_type": "LOW"
  },
  {
    "index": 80,
    "timestamp": "2026-06-15 16:30:00+00:00",
    "price": 76.09,
    "point_type": "HIGH"
  },
  {
    "index": 84,
    "timestamp": "2026-06-15 17:30:00+00:00",
    "price": 74.65,
    "point_type": "LOW"
  },
  {
    "index": 88,
    "timestamp": "2026-06-15 18:30:00+00:00",
    "price": 75.69,
    "point_type": "HIGH"
  },
  {
    "index": 91,
    "timestamp": "2026-06-15 19:15:00+00:00",
    "price": 74.58,
    "point_type": "LOW"
  },
  {
    "index": 93,
    "timestamp": "2026-06-15 19:45:00+00:00",
    "price": 75.55,
    "point_type": "HIGH"
  }
]
```
### Higher highs / lower highs
```json
{
  "raw_swing_count": 39,
  "swing_count": 27,
  "leg_count": 26,
  "structure_direction": "SIDEWAYS_STRUCTURE",
  "total_movement": 24.399999999999977,
  "directional_progress": 0.0,
  "score_method_origin": "ENGINE_TREND_DERIVED_HEURISTIC",
  "swing_method_origin": "ENGINE_TREND_DERIVED_HEURISTIC"
}
```
### Higher lows / lower lows
See swing structure above.
### Directional progress
0.0
### Trend strength / weakness
strength=0.0, consistency=0.0
### Trend context conclusion
SIDEWAYS_STRUCTURE; ALTUNINA_PRICE_LEGS_BUILT, ALTUNINA_SIDEWAYS_STRUCTURE, ALTUNINA_TREND_NOT_CONFIRMED

## 3. Schwager range context
### Range detection
```json
{
  "support_zone": {
    "zone_type": "SUPPORT",
    "lower_price": 70.55,
    "upper_price": 70.94,
    "mid_price": 70.78625,
    "touch_count": 8,
    "source_indexes": [
      5,
      8,
      16,
      18,
      25,
      34,
      36,
      52
    ],
    "zone_width": 0.39000000000000057,
    "zone_width_ratio": 0.005509544579632352,
    "formed_at_index": 52,
    "first_touch_index": 5,
    "last_touch_index": 52,
    "source_point_types": [
      "HIGH",
      "HIGH",
      "LOW",
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
    "lower_price": 71.48,
    "upper_price": 71.73,
    "mid_price": 71.57000000000001,
    "touch_count": 6,
    "source_indexes": [
      14,
      23,
      41,
      43,
      47,
      51
    ],
    "zone_width": 0.25,
    "zone_width_ratio": 0.0034930836942853147,
    "formed_at_index": 51,
    "first_touch_index": 14,
    "last_touch_index": 51,
    "source_point_types": [
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
  "lower_boundary": 70.55,
  "upper_boundary": 71.73,
  "midline": 71.14,
  "width": 1.1800000000000068,
  "width_ratio": 0.016587011526567427,
  "touch_count": 14,
  "inside_close_ratio": 0.9166666666666666,
  "formed_at_index": 52,
  "first_touch_index": 5,
  "duration_candles": 48,
  "boundary_alternation_count": 6
}
```
### Range high / low
See trading range object above.
### Price position inside range
```json
{
  "swing_count": 39,
  "zone_count": 8,
  "range_detected": true,
  "range_formed_at_index": 52,
  "range_duration_candles": 48,
  "inside_close_ratio": 0.9166666666666666,
  "breakout_direction": "UPWARD",
  "breakout_status": "CONFIRMED",
  "polarity_status": "NONE"
}
```
### Breakout / breakdown attempts
```json
{
  "direction": "UPWARD",
  "status": "CONFIRMED",
  "breakout_index": 57,
  "boundary_price": 71.73,
  "breakout_close": 71.88,
  "distance_ratio": 0.0020911752404850336,
  "returned_to_range": false,
  "follow_through_count": 5,
  "evidence": [
    {
      "source": "SCHWAGER",
      "code": "SCHWAGER_BULLISH_RANGE_BREAKOUT_CONTEXT",
      "description": "Closing price moved above the range boundary",
      "contribution": 0.12,
      "metadata": {
        "breakout_index": 57
      }
    },
    {
      "source": "SCHWAGER",
      "code": "SCHWAGER_BREAKOUT_REQUIRES_CONFIRMATION",
      "description": "Boundary movement requires confirmation",
      "contribution": 0.0,
      "metadata": {}
    },
    {
      "source": "SCHWAGER",
      "code": "SCHWAGER_BREAKOUT_FOLLOW_THROUGH_CONFIRMED",
      "description": "Closing prices confirm follow-through",
      "contribution": 0.08,
      "metadata": {
        "count": 5
      }
    },
    {
      "source": "SCHWAGER",
      "code": "SCHWAGER_BREAKOUT_CONFIRMED_BY_CLOSE_COUNT",
      "description": "Multiple closes beyond the boundary confirm the movement",
      "contribution": 0.0,
      "metadata": {
        "count": 6
      }
    },
    {
      "source": "SCHWAGER",
      "code": "SCHWAGER_BREAKOUT_CONFIRMED_BY_DISTANCE",
      "description": "Movement depth beyond the boundary confirms the movement",
      "contribution": 0.0,
      "metadata": {
        "distance_ratio": 0.015195873414191957
      }
    }
  ],
  "analysis_start_index": 53,
  "confirmation_method": "CLOSE_COUNT_AND_DISTANCE",
  "confirmation_close_count": 6,
  "extreme_index": 59,
  "extreme_price": 72.82,
  "maximum_distance_ratio": 0.015195873414191957,
  "return_index": null,
  "return_depth_ratio": 0.0,
  "reversal_candle_count": 0,
  "false_breakout_confirmation": "NONE",
  "false_breakout_invalidated": false
}
```
### False breakout / failed breakout
See breakout context above.
### Range context conclusion
SCHWAGER_SUPPORT_ZONE_IDENTIFIED, SCHWAGER_SUPPORT_ZONE_HELD, SCHWAGER_ZONE_TOO_WIDE, SCHWAGER_RESISTANCE_ZONE_IDENTIFIED, SCHWAGER_RESISTANCE_ZONE_HELD, SCHWAGER_TRADING_RANGE_DETECTED, SCHWAGER_PRICE_INSIDE_RANGE, SCHWAGER_RANGE_UPPER_BOUNDARY_HELD, SCHWAGER_RANGE_LOWER_BOUNDARY_HELD, SCHWAGER_RANGE_DURATION_CONFIRMED, SCHWAGER_RANGE_BOUNDARY_ALTERNATION_CONFIRMED, SCHWAGER_BULLISH_RANGE_BREAKOUT_CONTEXT, SCHWAGER_BREAKOUT_REQUIRES_CONFIRMATION, SCHWAGER_BREAKOUT_FOLLOW_THROUGH_CONFIRMED, SCHWAGER_BREAKOUT_CONFIRMED_BY_CLOSE_COUNT, SCHWAGER_BREAKOUT_CONFIRMED_BY_DISTANCE

## 4. BookEvidenceMatrix
### Bullish evidence
Count: 47
### Bearish evidence
Count: 18
### Neutral/range evidence
Count: 346
### Conflict
```json
{
  "agreement_state": "ALIGNED_BULLISH",
  "conflict_level": "NONE",
  "coverage_level": "HIGH",
  "aligned_sources": [
    "NISON",
    "SCHWAGER"
  ],
  "conflicting_sources": [],
  "missing_sources": [],
  "confluence_score": 0.6666666666666666,
  "conflict_score": 0.0,
  "coverage_score": 1.0,
  "reason_codes": [
    "MATRIX_HIGH_EVIDENCE_COVERAGE",
    "MATRIX_BULLISH_CONFLUENCE",
    "MATRIX_NISON_SCHWAGER_ALIGNED",
    "MATRIX_READY_FOR_REGIME_COMPOSER"
  ]
}
```
### Coverage
```json
{
  "active_source_count": 3,
  "total_evidence_count": 411,
  "dominant_direction": "BULLISH",
  "agreement_state": "ALIGNED_BULLISH",
  "conflict_level": "NONE",
  "coverage_level": "HIGH",
  "confluence_score": 0.6666666666666666,
  "conflict_score": 0.0,
  "coverage_score": 1.0,
  "ready_for_composer": true
}
```
### Matrix conclusion
ALIGNED_BULLISH

## 5. Composer decision
### Raw scores
Not exposed by current trace.
### Clamped scores
```json
{
  "UP": 1.0,
  "DOWN": 1.0,
  "FLAT": 0.5833333333333334,
  "UNKNOWN": 0.0
}
```
### Ranking
```json
[
  {
    "regime": "UP",
    "score": 1.0
  },
  {
    "regime": "DOWN",
    "score": 1.0
  },
  {
    "regime": "FLAT",
    "score": 0.5833333333333334
  }
]
```
### Score gap
clamped top-2: 0.0; raw top-2: Not exposed by current trace.
### Fallback trigger
True: COMPOSER_CONSERVATIVE_FALLBACK_UNKNOWN
### Confidence path
Final 0.3; base/adjustments not exposed.
### Composer conclusion
Selected after fallback: UNKNOWN.

## 6. Human-readable explanation
### Why result is UNKNOWN / UP / DOWN / FLAT
The engine returned UNKNOWN because the composer status was FALLBACK_UNKNOWN and selected UNKNOWN. The strongest visible candidate scores after clamping were UP=1.000 and DOWN=1.000; fallback reason: COMPOSER_CONSERVATIVE_FALLBACK_UNKNOWN. The reference label is EXPECTED_UNKNOWN_OR_MIXED and remains descriptive, not ground truth.
### What evidence supported the result
See layer sections above.
### What evidence blocked alternative regimes
Composer fallback and visible conflict/coverage fields above.
### What should be checked before tuning
Review conflicting layer evidence and add trace-only pre-clamp score exposure before another tuning proposal.

## 7. Trace completeness
```json
{
  "available": true,
  "missing_fields": [
    "composer.raw_scores",
    "composer.ranking_before_clamp",
    "composer.score_gap_raw_top2",
    "composer.confidence_adjustments"
  ],
  "missing_field_count": 4,
  "completeness_pct": 80
}
```
