# solusdt_15m_flat_002 вЂ” Market Evidence Trace

## Window
- Symbol: SOLUSDT
- Interval: 15m
- Period: 2026-04-30T00:00:00+00:00 вЂ” 2026-04-30T23:45:00+00:00
- Reference label: EXPECTED_FLAT
- Selection reason: ranked deterministic FLAT OHLC candidate

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
    "timestamp": "2026-04-30 00:15:00+00:00",
    "candle_index": 1,
    "open": 83.21,
    "high": 83.35,
    "low": 83.1,
    "close": 83.27,
    "body_pct": 0.2400000000000091,
    "upper_shadow_pct": 0.3199999999999932,
    "lower_shadow_pct": 0.4399999999999977,
    "position_in_window": 0.0105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2026-04-30 01:00:00+00:00",
    "candle_index": 4,
    "open": 83.8,
    "high": 83.94,
    "low": 83.66,
    "close": 83.94,
    "body_pct": 0.5,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.5,
    "position_in_window": 0.0421,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-04-30 01:15:00+00:00",
    "candle_index": 5,
    "open": 83.93,
    "high": 83.98,
    "low": 83.76,
    "close": 83.87,
    "body_pct": 0.2727272727272845,
    "upper_shadow_pct": 0.22727272727271552,
    "lower_shadow_pct": 0.5,
    "position_in_window": 0.0526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION"
    ]
  },
  {
    "timestamp": "2026-04-30 01:30:00+00:00",
    "candle_index": 6,
    "open": 83.87,
    "high": 84.0,
    "low": 83.7,
    "close": 83.82,
    "body_pct": 0.16666666666670615,
    "upper_shadow_pct": 0.4333333333333223,
    "lower_shadow_pct": 0.3999999999999716,
    "position_in_window": 0.0632,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2026-04-30 01:45:00+00:00",
    "candle_index": 7,
    "open": 83.82,
    "high": 83.96,
    "low": 83.73,
    "close": 83.75,
    "body_pct": 0.3043478260869404,
    "upper_shadow_pct": 0.6086956521739426,
    "lower_shadow_pct": 0.086956521739117,
    "position_in_window": 0.0737,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-04-30 02:15:00+00:00",
    "candle_index": 9,
    "open": 83.87,
    "high": 83.9,
    "low": 83.52,
    "close": 83.55,
    "body_pct": 0.8421052631578928,
    "upper_shadow_pct": 0.07894736842105361,
    "lower_shadow_pct": 0.07894736842105361,
    "position_in_window": 0.0947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-04-30 02:30:00+00:00",
    "candle_index": 10,
    "open": 83.55,
    "high": 83.56,
    "low": 82.7,
    "close": 82.88,
    "body_pct": 0.779069767441863,
    "upper_shadow_pct": 0.011627906976750143,
    "lower_shadow_pct": 0.2093023255813869,
    "position_in_window": 0.1053,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-04-30 02:45:00+00:00",
    "candle_index": 11,
    "open": 82.89,
    "high": 83.07,
    "low": 82.71,
    "close": 82.98,
    "body_pct": 0.2500000000000099,
    "upper_shadow_pct": 0.24999999999997038,
    "lower_shadow_pct": 0.5000000000000198,
    "position_in_window": 0.1158,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-04-30 03:00:00+00:00",
    "candle_index": 12,
    "open": 82.98,
    "high": 83.07,
    "low": 82.92,
    "close": 82.97,
    "body_pct": 0.06666666666670457,
    "upper_shadow_pct": 0.5999999999999621,
    "lower_shadow_pct": 0.3333333333333333,
    "position_in_window": 0.1263,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "DOJI_INDECISION"
    ]
  },
  {
    "timestamp": "2026-04-30 03:15:00+00:00",
    "candle_index": 13,
    "open": 82.98,
    "high": 83.07,
    "low": 82.86,
    "close": 83.07,
    "body_pct": 0.4285714285713899,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.5714285714286101,
    "position_in_window": 0.1368,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-04-30 03:30:00+00:00",
    "candle_index": 14,
    "open": 83.07,
    "high": 83.24,
    "low": 82.95,
    "close": 83.18,
    "body_pct": 0.37931034482764364,
    "upper_shadow_pct": 0.20689655172410246,
    "lower_shadow_pct": 0.4137931034482539,
    "position_in_window": 0.1474,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-04-30 03:45:00+00:00",
    "candle_index": 15,
    "open": 83.18,
    "high": 83.18,
    "low": 83.05,
    "close": 83.06,
    "body_pct": 0.9230769230768895,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.07692307692311055,
    "position_in_window": 0.1579,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-04-30 04:30:00+00:00",
    "candle_index": 18,
    "open": 82.75,
    "high": 82.77,
    "low": 82.37,
    "close": 82.39,
    "body_pct": 0.9000000000000178,
    "upper_shadow_pct": 0.04999999999999112,
    "lower_shadow_pct": 0.04999999999999112,
    "position_in_window": 0.1895,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-04-30 04:45:00+00:00",
    "candle_index": 19,
    "open": 82.38,
    "high": 82.5,
    "low": 82.37,
    "close": 82.39,
    "body_pct": 0.07692307692311896,
    "upper_shadow_pct": 0.8461538461538713,
    "lower_shadow_pct": 0.07692307692300965,
    "position_in_window": 0.2,
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
    "timestamp": "2026-04-30 05:00:00+00:00",
    "candle_index": 20,
    "open": 82.4,
    "high": 82.57,
    "low": 82.32,
    "close": 82.52,
    "body_pct": 0.47999999999996135,
    "upper_shadow_pct": 0.19999999999998863,
    "lower_shadow_pct": 0.32000000000005,
    "position_in_window": 0.2105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-04-30 05:30:00+00:00",
    "candle_index": 22,
    "open": 82.32,
    "high": 82.79,
    "low": 82.31,
    "close": 82.7,
    "body_pct": 0.7916666666666803,
    "upper_shadow_pct": 0.18750000000000555,
    "lower_shadow_pct": 0.020833333333314212,
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
    "timestamp": "2026-04-30 05:45:00+00:00",
    "candle_index": 23,
    "open": 82.7,
    "high": 82.76,
    "low": 82.57,
    "close": 82.57,
    "body_pct": 0.6842105263157974,
    "upper_shadow_pct": 0.3157894736842026,
    "lower_shadow_pct": 0.0,
    "position_in_window": 0.2421,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-04-30 06:00:00+00:00",
    "candle_index": 24,
    "open": 82.57,
    "high": 82.68,
    "low": 82.53,
    "close": 82.6,
    "body_pct": 0.2,
    "upper_shadow_pct": 0.5333333333333965,
    "lower_shadow_pct": 0.2666666666666035,
    "position_in_window": 0.2526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2026-04-30 06:15:00+00:00",
    "candle_index": 25,
    "open": 82.61,
    "high": 82.77,
    "low": 82.61,
    "close": 82.77,
    "body_pct": 1.0,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.0,
    "position_in_window": 0.2632,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-04-30 06:30:00+00:00",
    "candle_index": 26,
    "open": 82.77,
    "high": 83.05,
    "low": 82.77,
    "close": 82.89,
    "body_pct": 0.4285714285714431,
    "upper_shadow_pct": 0.571428571428557,
    "lower_shadow_pct": 0.0,
    "position_in_window": 0.2737,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2026-04-30 06:45:00+00:00",
    "candle_index": 27,
    "open": 82.9,
    "high": 82.99,
    "low": 82.82,
    "close": 82.94,
    "body_pct": 0.23529411764700964,
    "upper_shadow_pct": 0.29411764705880383,
    "lower_shadow_pct": 0.4705882352941865,
    "position_in_window": 0.2842,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2026-04-30 07:00:00+00:00",
    "candle_index": 28,
    "open": 82.95,
    "high": 83.09,
    "low": 82.9,
    "close": 83.06,
    "body_pct": 0.5789473684210565,
    "upper_shadow_pct": 0.15789473684211314,
    "lower_shadow_pct": 0.2631578947368303,
    "position_in_window": 0.2947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-04-30 07:15:00+00:00",
    "candle_index": 29,
    "open": 83.06,
    "high": 83.1,
    "low": 83.01,
    "close": 83.07,
    "body_pct": 0.11111111111102338,
    "upper_shadow_pct": 0.33333333333338594,
    "lower_shadow_pct": 0.5555555555555907,
    "position_in_window": 0.3053,
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
    "timestamp": "2026-04-30 07:45:00+00:00",
    "candle_index": 31,
    "open": 83.22,
    "high": 83.39,
    "low": 83.2,
    "close": 83.35,
    "body_pct": 0.6842105263157737,
    "upper_shadow_pct": 0.21052631578950912,
    "lower_shadow_pct": 0.10526315789471716,
    "position_in_window": 0.3263,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-04-30 08:00:00+00:00",
    "candle_index": 32,
    "open": 83.35,
    "high": 83.43,
    "low": 83.23,
    "close": 83.3,
    "body_pct": 0.24999999999998224,
    "upper_shadow_pct": 0.40000000000005687,
    "lower_shadow_pct": 0.3499999999999609,
    "position_in_window": 0.3368,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2026-04-30 08:15:00+00:00",
    "candle_index": 33,
    "open": 83.3,
    "high": 83.39,
    "low": 83.2,
    "close": 83.25,
    "body_pct": 0.2631578947368303,
    "upper_shadow_pct": 0.4736842105263394,
    "lower_shadow_pct": 0.2631578947368303,
    "position_in_window": 0.3474,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION"
    ]
  },
  {
    "timestamp": "2026-04-30 08:30:00+00:00",
    "candle_index": 34,
    "open": 83.24,
    "high": 83.25,
    "low": 83.14,
    "close": 83.23,
    "body_pct": 0.0909090909090087,
    "upper_shadow_pct": 0.09090909090913789,
    "lower_shadow_pct": 0.8181818181818534,
    "position_in_window": 0.3579,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
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
    "timestamp": "2026-04-30 08:45:00+00:00",
    "candle_index": 35,
    "open": 83.23,
    "high": 83.26,
    "low": 83.12,
    "close": 83.13,
    "body_pct": 0.7142857142857723,
    "upper_shadow_pct": 0.21428571428572155,
    "lower_shadow_pct": 0.07142857142850617,
    "position_in_window": 0.3684,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-04-30 09:00:00+00:00",
    "candle_index": 36,
    "open": 83.12,
    "high": 83.18,
    "low": 83.08,
    "close": 83.14,
    "body_pct": 0.19999999999994317,
    "upper_shadow_pct": 0.40000000000002844,
    "lower_shadow_pct": 0.40000000000002844,
    "position_in_window": 0.3789,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2026-04-30 09:15:00+00:00",
    "candle_index": 37,
    "open": 83.13,
    "high": 83.32,
    "low": 83.06,
    "close": 83.31,
    "body_pct": 0.6923076923077428,
    "upper_shadow_pct": 0.038461538461504824,
    "lower_shadow_pct": 0.2692307692307524,
    "position_in_window": 0.3895,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  }
]
```
### Doji / spinning top / small body cluster
```json
{
  "doji_count": 6,
  "doji_ratio": 0.0625,
  "small_body_count": 32,
  "small_body_ratio": 0.3333333333333333,
  "bullish_body_total": 5.640000000000057,
  "bearish_body_total": 5.600000000000051
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
      "previous_timestamp": "2026-04-30 01:45:00+00:00",
      "timestamp": "2026-04-30 02:00:00+00:00",
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
      "previous_timestamp": "2026-04-30 01:45:00+00:00",
      "timestamp": "2026-04-30 02:00:00+00:00",
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
      "previous_timestamp": "2026-04-30 03:30:00+00:00",
      "timestamp": "2026-04-30 03:45:00+00:00",
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
      "previous_timestamp": "2026-04-30 03:30:00+00:00",
      "timestamp": "2026-04-30 03:45:00+00:00",
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
      "previous_timestamp": "2026-04-30 05:00:00+00:00",
      "timestamp": "2026-04-30 05:15:00+00:00",
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
      "previous_timestamp": "2026-04-30 05:00:00+00:00",
      "timestamp": "2026-04-30 05:15:00+00:00",
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
      "previous_timestamp": "2026-04-30 11:15:00+00:00",
      "timestamp": "2026-04-30 11:30:00+00:00",
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
      "previous_timestamp": "2026-04-30 11:15:00+00:00",
      "timestamp": "2026-04-30 11:30:00+00:00",
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
      "previous_timestamp": "2026-04-30 12:45:00+00:00",
      "timestamp": "2026-04-30 13:00:00+00:00",
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
      "previous_timestamp": "2026-04-30 12:45:00+00:00",
      "timestamp": "2026-04-30 13:00:00+00:00",
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
      "previous_timestamp": "2026-04-30 13:15:00+00:00",
      "timestamp": "2026-04-30 13:30:00+00:00",
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
      "previous_timestamp": "2026-04-30 13:15:00+00:00",
      "timestamp": "2026-04-30 13:30:00+00:00",
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
      "previous_timestamp": "2026-04-30 15:15:00+00:00",
      "timestamp": "2026-04-30 15:30:00+00:00",
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
      "previous_timestamp": "2026-04-30 15:15:00+00:00",
      "timestamp": "2026-04-30 15:30:00+00:00",
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
      "previous_timestamp": "2026-04-30 18:45:00+00:00",
      "timestamp": "2026-04-30 19:00:00+00:00",
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
      "previous_timestamp": "2026-04-30 18:45:00+00:00",
      "timestamp": "2026-04-30 19:00:00+00:00",
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
      "previous_timestamp": "2026-04-30 19:15:00+00:00",
      "timestamp": "2026-04-30 19:30:00+00:00",
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
      "previous_timestamp": "2026-04-30 19:15:00+00:00",
      "timestamp": "2026-04-30 19:30:00+00:00",
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
      "previous_timestamp": "2026-04-30 20:30:00+00:00",
      "timestamp": "2026-04-30 20:45:00+00:00",
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
      "previous_timestamp": "2026-04-30 20:30:00+00:00",
      "timestamp": "2026-04-30 20:45:00+00:00",
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
SMALL_BODY_INDECISION, SPINNING_TOP_INDECISION, CLOSE_NEAR_HIGH, LONG_UPPER_SHADOW_REJECTION, CLOSE_NEAR_LOW, STRONG_BEARISH_CANDLE_BODY, DOJI_INDECISION, LONG_LOWER_SHADOW_REJECTION, SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED, CANDLE_PATTERN_NEEDS_TREND_CONTEXT, STRONG_BULLISH_CANDLE_BODY, HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED, BULLISH_ENGULFING_CONTEXT, ENGULFING_WITHOUT_FOLLOW_THROUGH, BEARISH_ENGULFING_CONTEXT, BULLISH_BELT_HOLD_CONTEXT_REQUIRED, BEARISH_BELT_HOLD_CONTEXT_REQUIRED, INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED, REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH, GRAVESTONE_DOJI_CONTEXT, HANGING_MAN_LIKE_CONTEXT_REQUIRED, DRAGONFLY_DOJI_CONTEXT, LONG_LEGGED_DOJI_CONTEXT, RICKSHAW_MAN_DOJI_CONTEXT, TWEEZERS_TOP_CONTEXT_REQUIRED, BULLISH_HARAMI_CONTEXT, TWEEZERS_BOTTOM_CONTEXT_REQUIRED, BULLISH_SEPARATING_LINES_CONTEXT, BEARISH_HARAMI_CONTEXT, HARAMI_CROSS_CONTEXT, DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT, DOJI_TOP_CONTEXT_REQUIRED, BEARISH_SEPARATING_LINES_CONTEXT

## 2. Altunina trend context
### Swing structure
```json
[
  {
    "index": 3,
    "timestamp": "2026-04-30 00:45:00+00:00",
    "price": 84.01,
    "point_type": "HIGH"
  },
  {
    "index": 10,
    "timestamp": "2026-04-30 02:30:00+00:00",
    "price": 82.7,
    "point_type": "LOW"
  },
  {
    "index": 14,
    "timestamp": "2026-04-30 03:30:00+00:00",
    "price": 83.24,
    "point_type": "HIGH"
  },
  {
    "index": 21,
    "timestamp": "2026-04-30 05:15:00+00:00",
    "price": 82.16,
    "point_type": "LOW"
  },
  {
    "index": 22,
    "timestamp": "2026-04-30 05:30:00+00:00",
    "price": 82.79,
    "point_type": "HIGH"
  },
  {
    "index": 24,
    "timestamp": "2026-04-30 06:00:00+00:00",
    "price": 82.53,
    "point_type": "LOW"
  },
  {
    "index": 32,
    "timestamp": "2026-04-30 08:00:00+00:00",
    "price": 83.43,
    "point_type": "HIGH"
  },
  {
    "index": 37,
    "timestamp": "2026-04-30 09:15:00+00:00",
    "price": 83.06,
    "point_type": "LOW"
  },
  {
    "index": 38,
    "timestamp": "2026-04-30 09:30:00+00:00",
    "price": 83.55,
    "point_type": "HIGH"
  },
  {
    "index": 41,
    "timestamp": "2026-04-30 10:15:00+00:00",
    "price": 82.92,
    "point_type": "LOW"
  },
  {
    "index": 44,
    "timestamp": "2026-04-30 11:00:00+00:00",
    "price": 83.39,
    "point_type": "HIGH"
  },
  {
    "index": 47,
    "timestamp": "2026-04-30 11:45:00+00:00",
    "price": 82.79,
    "point_type": "LOW"
  },
  {
    "index": 49,
    "timestamp": "2026-04-30 12:15:00+00:00",
    "price": 83.48,
    "point_type": "HIGH"
  },
  {
    "index": 54,
    "timestamp": "2026-04-30 13:30:00+00:00",
    "price": 82.88,
    "point_type": "LOW"
  },
  {
    "index": 55,
    "timestamp": "2026-04-30 13:45:00+00:00",
    "price": 83.56,
    "point_type": "HIGH"
  },
  {
    "index": 57,
    "timestamp": "2026-04-30 14:15:00+00:00",
    "price": 82.69,
    "point_type": "LOW"
  },
  {
    "index": 59,
    "timestamp": "2026-04-30 14:45:00+00:00",
    "price": 83.38,
    "point_type": "HIGH"
  },
  {
    "index": 60,
    "timestamp": "2026-04-30 15:00:00+00:00",
    "price": 83.03,
    "point_type": "LOW"
  },
  {
    "index": 62,
    "timestamp": "2026-04-30 15:30:00+00:00",
    "price": 83.83,
    "point_type": "HIGH"
  },
  {
    "index": 69,
    "timestamp": "2026-04-30 17:15:00+00:00",
    "price": 82.87,
    "point_type": "LOW"
  },
  {
    "index": 72,
    "timestamp": "2026-04-30 18:00:00+00:00",
    "price": 83.31,
    "point_type": "HIGH"
  },
  {
    "index": 74,
    "timestamp": "2026-04-30 18:30:00+00:00",
    "price": 82.98,
    "point_type": "LOW"
  },
  {
    "index": 78,
    "timestamp": "2026-04-30 19:30:00+00:00",
    "price": 83.29,
    "point_type": "HIGH"
  },
  {
    "index": 80,
    "timestamp": "2026-04-30 20:00:00+00:00",
    "price": 82.97,
    "point_type": "LOW"
  },
  {
    "index": 82,
    "timestamp": "2026-04-30 20:30:00+00:00",
    "price": 83.19,
    "point_type": "HIGH"
  },
  {
    "index": 88,
    "timestamp": "2026-04-30 22:00:00+00:00",
    "price": 82.79,
    "point_type": "LOW"
  },
  {
    "index": 90,
    "timestamp": "2026-04-30 22:30:00+00:00",
    "price": 83.04,
    "point_type": "HIGH"
  },
  {
    "index": 91,
    "timestamp": "2026-04-30 22:45:00+00:00",
    "price": 82.78,
    "point_type": "LOW"
  }
]
```
### Higher highs / lower highs
```json
{
  "raw_swing_count": 39,
  "swing_count": 28,
  "leg_count": 27,
  "structure_direction": "SIDEWAYS_STRUCTURE",
  "total_movement": 15.450000000000003,
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
    "lower_price": 82.53,
    "upper_price": 83.1,
    "mid_price": 82.89761904761903,
    "touch_count": 21,
    "source_indexes": [
      10,
      13,
      22,
      24,
      26,
      37,
      41,
      42,
      47,
      54,
      57,
      60,
      65,
      69,
      74,
      76,
      80,
      85,
      88,
      90,
      91
    ],
    "zone_width": 0.5699999999999932,
    "zone_width_ratio": 0.006875951403050153,
    "formed_at_index": 91,
    "first_touch_index": 10,
    "last_touch_index": 91,
    "source_point_types": [
      "LOW",
      "LOW",
      "HIGH",
      "LOW",
      "HIGH",
      "LOW",
      "LOW",
      "HIGH",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "HIGH",
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
    "lower_price": 83.16,
    "upper_price": 83.56,
    "mid_price": 83.34692307692308,
    "touch_count": 13,
    "source_indexes": [
      14,
      32,
      35,
      38,
      44,
      49,
      55,
      59,
      63,
      72,
      76,
      78,
      82
    ],
    "zone_width": 0.4000000000000057,
    "zone_width_ratio": 0.004799217358400083,
    "formed_at_index": 82,
    "first_touch_index": 14,
    "last_touch_index": 82,
    "source_point_types": [
      "HIGH",
      "HIGH",
      "HIGH",
      "HIGH",
      "HIGH",
      "HIGH",
      "HIGH",
      "HIGH",
      "LOW",
      "HIGH",
      "HIGH",
      "HIGH",
      "HIGH"
    ],
    "original_zone_type": "RESISTANCE",
    "current_zone_type": "RESISTANCE",
    "role_changed_at_index": null,
    "is_significant_single_extreme": false,
    "positional_zone_type": "RESISTANCE"
  },
  "is_detected": true,
  "lower_boundary": 82.53,
  "upper_boundary": 83.56,
  "midline": 83.045,
  "width": 1.0300000000000011,
  "width_ratio": 0.012402914082726247,
  "touch_count": 34,
  "inside_close_ratio": 0.9512195121951219,
  "formed_at_index": 91,
  "first_touch_index": 10,
  "duration_candles": 82,
  "boundary_alternation_count": 24
}
```
### Range high / low
See trading range object above.
### Price position inside range
```json
{
  "swing_count": 39,
  "zone_count": 4,
  "range_detected": true,
  "range_formed_at_index": 91,
  "range_duration_candles": 82,
  "inside_close_ratio": 0.9512195121951219,
  "breakout_direction": "NONE",
  "breakout_status": "NO_BREAKOUT",
  "polarity_status": "NONE"
}
```
### Breakout / breakdown attempts
```json
{
  "direction": "NONE",
  "status": "NO_BREAKOUT",
  "breakout_index": null,
  "boundary_price": null,
  "breakout_close": null,
  "distance_ratio": 0.0,
  "returned_to_range": false,
  "follow_through_count": 0,
  "evidence": [],
  "analysis_start_index": 92,
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
}
```
### False breakout / failed breakout
See breakout context above.
### Range context conclusion
SCHWAGER_SUPPORT_ZONE_IDENTIFIED, SCHWAGER_PREVIOUS_EXTREME_ZONE_IDENTIFIED, SCHWAGER_SUPPORT_ZONE_HELD, SCHWAGER_ZONE_TOO_WIDE, SCHWAGER_RESISTANCE_ZONE_IDENTIFIED, SCHWAGER_RESISTANCE_ZONE_HELD, SCHWAGER_TRADING_RANGE_DETECTED, SCHWAGER_PRICE_INSIDE_RANGE, SCHWAGER_RANGE_UPPER_BOUNDARY_HELD, SCHWAGER_RANGE_LOWER_BOUNDARY_HELD, SCHWAGER_RANGE_DURATION_CONFIRMED, SCHWAGER_RANGE_BOUNDARY_ALTERNATION_CONFIRMED

## 4. BookEvidenceMatrix
### Bullish evidence
Count: 23
### Bearish evidence
Count: 29
### Neutral/range evidence
Count: 308
### Conflict
```json
{
  "agreement_state": "ALIGNED_BEARISH",
  "conflict_level": "NONE",
  "coverage_level": "HIGH",
  "aligned_sources": [
    "ALTUNINA",
    "SCHWAGER"
  ],
  "conflicting_sources": [],
  "missing_sources": [],
  "confluence_score": 0.6666666666666666,
  "conflict_score": 0.0,
  "coverage_score": 1.0,
  "reason_codes": [
    "MATRIX_HIGH_EVIDENCE_COVERAGE",
    "MATRIX_NEUTRAL_CONFLUENCE",
    "MATRIX_ALTUNINA_SCHWAGER_ALIGNED",
    "MATRIX_READY_FOR_REGIME_COMPOSER"
  ]
}
```
### Coverage
```json
{
  "active_source_count": 3,
  "total_evidence_count": 360,
  "dominant_direction": "BEARISH",
  "agreement_state": "ALIGNED_BEARISH",
  "conflict_level": "NONE",
  "coverage_level": "HIGH",
  "confluence_score": 0.6666666666666666,
  "conflict_score": 0.0,
  "coverage_score": 1.0,
  "ready_for_composer": true
}
```
### Matrix conclusion
ALIGNED_BEARISH

## 5. Composer decision
### Raw scores
Not exposed by current trace.
### Clamped scores
```json
{
  "UP": 1.0,
  "DOWN": 1.0,
  "FLAT": 0.5902439024390245,
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
    "score": 0.5902439024390245
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
The engine returned UNKNOWN because the composer status was FALLBACK_UNKNOWN and selected UNKNOWN. The strongest visible candidate scores after clamping were UP=1.000 and DOWN=1.000; fallback reason: COMPOSER_CONSERVATIVE_FALLBACK_UNKNOWN. The reference label is EXPECTED_FLAT and remains descriptive, not ground truth.
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
