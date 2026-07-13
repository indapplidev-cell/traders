# solusdt_15m_up_004 вЂ” Market Evidence Trace

## Window
- Symbol: SOLUSDT
- Interval: 15m
- Period: 2025-05-08T00:00:00+00:00 вЂ” 2025-05-08T23:45:00+00:00
- Reference label: EXPECTED_UP
- Selection reason: ranked deterministic UP OHLC candidate

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
    "timestamp": "2025-05-08 00:15:00+00:00",
    "candle_index": 1,
    "open": 147.45,
    "high": 147.64,
    "low": 147.26,
    "close": 147.59,
    "body_pct": 0.3684210526316222,
    "upper_shadow_pct": 0.13157894736837775,
    "lower_shadow_pct": 0.5,
    "position_in_window": 0.0105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-05-08 00:30:00+00:00",
    "candle_index": 2,
    "open": 147.59,
    "high": 147.64,
    "low": 147.08,
    "close": 147.22,
    "body_pct": 0.6607142857143247,
    "upper_shadow_pct": 0.089285714285688,
    "lower_shadow_pct": 0.24999999999998732,
    "position_in_window": 0.0211,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-05-08 00:45:00+00:00",
    "candle_index": 3,
    "open": 147.22,
    "high": 148.9,
    "low": 147.11,
    "close": 148.83,
    "body_pct": 0.8994413407821346,
    "upper_shadow_pct": 0.03910614525139301,
    "lower_shadow_pct": 0.061452513966472465,
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
    "timestamp": "2025-05-08 01:00:00+00:00",
    "candle_index": 4,
    "open": 148.83,
    "high": 149.99,
    "low": 148.65,
    "close": 148.86,
    "body_pct": 0.022388059701493327,
    "upper_shadow_pct": 0.8432835820895467,
    "lower_shadow_pct": 0.13432835820895997,
    "position_in_window": 0.0421,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "CLOSE_NEAR_LOW",
      "DOJI_INDECISION"
    ]
  },
  {
    "timestamp": "2025-05-08 01:15:00+00:00",
    "candle_index": 5,
    "open": 148.86,
    "high": 149.0,
    "low": 148.35,
    "close": 148.86,
    "body_pct": 0.0,
    "upper_shadow_pct": 0.21538461538459253,
    "lower_shadow_pct": 0.7846153846154075,
    "position_in_window": 0.0526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "CLOSE_NEAR_HIGH",
      "DOJI_INDECISION"
    ]
  },
  {
    "timestamp": "2025-05-08 01:45:00+00:00",
    "candle_index": 7,
    "open": 148.54,
    "high": 148.75,
    "low": 147.93,
    "close": 148.12,
    "body_pct": 0.5121951219512085,
    "upper_shadow_pct": 0.2560975609756216,
    "lower_shadow_pct": 0.23170731707316988,
    "position_in_window": 0.0737,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-05-08 02:00:00+00:00",
    "candle_index": 8,
    "open": 148.13,
    "high": 148.9,
    "low": 148.04,
    "close": 148.87,
    "body_pct": 0.8604651162790667,
    "upper_shadow_pct": 0.03488372093023333,
    "lower_shadow_pct": 0.10465116279069998,
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
    "timestamp": "2025-05-08 02:15:00+00:00",
    "candle_index": 9,
    "open": 148.86,
    "high": 149.94,
    "low": 148.74,
    "close": 149.9,
    "body_pct": 0.8666666666666683,
    "upper_shadow_pct": 0.03333333333332702,
    "lower_shadow_pct": 0.10000000000000474,
    "position_in_window": 0.0947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-05-08 02:30:00+00:00",
    "candle_index": 10,
    "open": 149.89,
    "high": 150.32,
    "low": 149.67,
    "close": 149.91,
    "body_pct": 0.03076923076924624,
    "upper_shadow_pct": 0.63076923076922,
    "lower_shadow_pct": 0.33846153846153376,
    "position_in_window": 0.1053,
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
    "timestamp": "2025-05-08 02:45:00+00:00",
    "candle_index": 11,
    "open": 149.9,
    "high": 150.3,
    "low": 149.75,
    "close": 149.82,
    "body_pct": 0.14545454545456518,
    "upper_shadow_pct": 0.7272727272727226,
    "lower_shadow_pct": 0.12727272727271224,
    "position_in_window": 0.1158,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "CLOSE_NEAR_LOW",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2025-05-08 03:15:00+00:00",
    "candle_index": 13,
    "open": 150.16,
    "high": 150.45,
    "low": 149.96,
    "close": 150.15,
    "body_pct": 0.020408163265288368,
    "upper_shadow_pct": 0.5918367346938846,
    "lower_shadow_pct": 0.38775510204082697,
    "position_in_window": 0.1368,
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
    "timestamp": "2025-05-08 03:30:00+00:00",
    "candle_index": 14,
    "open": 150.16,
    "high": 150.95,
    "low": 149.87,
    "close": 150.95,
    "body_pct": 0.7314814814814848,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.2685185185185151,
    "position_in_window": 0.1474,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-05-08 03:45:00+00:00",
    "candle_index": 15,
    "open": 150.95,
    "high": 151.19,
    "low": 150.28,
    "close": 150.87,
    "body_pct": 0.08791208791207075,
    "upper_shadow_pct": 0.26373626373627473,
    "lower_shadow_pct": 0.6483516483516545,
    "position_in_window": 0.1579,
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
    "timestamp": "2025-05-08 04:30:00+00:00",
    "candle_index": 18,
    "open": 151.66,
    "high": 151.75,
    "low": 151.19,
    "close": 151.22,
    "body_pct": 0.7857142857142785,
    "upper_shadow_pct": 0.16071428571429114,
    "lower_shadow_pct": 0.053571428571430386,
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
    "timestamp": "2025-05-08 04:45:00+00:00",
    "candle_index": 19,
    "open": 151.22,
    "high": 151.39,
    "low": 150.86,
    "close": 150.87,
    "body_pct": 0.6603773584905893,
    "upper_shadow_pct": 0.320754716981125,
    "lower_shadow_pct": 0.018867924528285698,
    "position_in_window": 0.2,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-05-08 05:00:00+00:00",
    "candle_index": 20,
    "open": 150.87,
    "high": 151.33,
    "low": 150.54,
    "close": 150.55,
    "body_pct": 0.4050632911392214,
    "upper_shadow_pct": 0.5822784810126532,
    "lower_shadow_pct": 0.012658227848125403,
    "position_in_window": 0.2105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-05-08 05:15:00+00:00",
    "candle_index": 21,
    "open": 150.56,
    "high": 150.57,
    "low": 149.97,
    "close": 150.41,
    "body_pct": 0.2500000000000118,
    "upper_shadow_pct": 0.016666666666651668,
    "lower_shadow_pct": 0.7333333333333365,
    "position_in_window": 0.2211,
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
    "timestamp": "2025-05-08 05:30:00+00:00",
    "candle_index": 22,
    "open": 150.41,
    "high": 150.57,
    "low": 150.22,
    "close": 150.44,
    "body_pct": 0.08571428571429035,
    "upper_shadow_pct": 0.37142857142856445,
    "lower_shadow_pct": 0.5428571428571451,
    "position_in_window": 0.2316,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "DOJI_INDECISION"
    ]
  },
  {
    "timestamp": "2025-05-08 05:45:00+00:00",
    "candle_index": 23,
    "open": 150.45,
    "high": 150.49,
    "low": 150.12,
    "close": 150.16,
    "body_pct": 0.7837837837837527,
    "upper_shadow_pct": 0.10810810810816208,
    "lower_shadow_pct": 0.10810810810808527,
    "position_in_window": 0.2421,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-05-08 06:00:00+00:00",
    "candle_index": 24,
    "open": 150.15,
    "high": 150.46,
    "low": 150.1,
    "close": 150.45,
    "body_pct": 0.8333333333332544,
    "upper_shadow_pct": 0.02777777777783041,
    "lower_shadow_pct": 0.1388888888889152,
    "position_in_window": 0.2526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-05-08 06:30:00+00:00",
    "candle_index": 26,
    "open": 150.37,
    "high": 150.51,
    "low": 150.3,
    "close": 150.47,
    "body_pct": 0.47619047619049554,
    "upper_shadow_pct": 0.19047619047617115,
    "lower_shadow_pct": 0.3333333333333333,
    "position_in_window": 0.2737,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-05-08 07:00:00+00:00",
    "candle_index": 28,
    "open": 150.63,
    "high": 151.07,
    "low": 150.55,
    "close": 150.97,
    "body_pct": 0.6538461538461833,
    "upper_shadow_pct": 0.1923076923076881,
    "lower_shadow_pct": 0.15384615384612862,
    "position_in_window": 0.2947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-05-08 07:15:00+00:00",
    "candle_index": 29,
    "open": 150.97,
    "high": 151.48,
    "low": 150.92,
    "close": 151.48,
    "body_pct": 0.9107142857142658,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.08928571428573423,
    "position_in_window": 0.3053,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-05-08 07:45:00+00:00",
    "candle_index": 31,
    "open": 151.76,
    "high": 151.95,
    "low": 151.55,
    "close": 151.57,
    "body_pct": 0.4750000000000213,
    "upper_shadow_pct": 0.4750000000000213,
    "lower_shadow_pct": 0.04999999999995737,
    "position_in_window": 0.3263,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-05-08 08:30:00+00:00",
    "candle_index": 34,
    "open": 152.33,
    "high": 152.99,
    "low": 152.16,
    "close": 152.94,
    "body_pct": 0.7349397590361157,
    "upper_shadow_pct": 0.060240963855434475,
    "lower_shadow_pct": 0.20481927710844983,
    "position_in_window": 0.3579,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-05-08 08:45:00+00:00",
    "candle_index": 35,
    "open": 152.95,
    "high": 153.34,
    "low": 152.7,
    "close": 152.84,
    "body_pct": 0.17187499999997294,
    "upper_shadow_pct": 0.609375000000009,
    "lower_shadow_pct": 0.21875000000001804,
    "position_in_window": 0.3684,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "CLOSE_NEAR_LOW",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2025-05-08 09:15:00+00:00",
    "candle_index": 37,
    "open": 152.64,
    "high": 153.1,
    "low": 152.58,
    "close": 152.76,
    "body_pct": 0.23076923076924757,
    "upper_shadow_pct": 0.6538461538461833,
    "lower_shadow_pct": 0.11538461538456914,
    "position_in_window": 0.3895,
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
    "timestamp": "2025-05-08 09:30:00+00:00",
    "candle_index": 38,
    "open": 152.75,
    "high": 153.29,
    "low": 152.72,
    "close": 153.29,
    "body_pct": 0.947368421052629,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.05263157894737105,
    "position_in_window": 0.4,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-05-08 09:45:00+00:00",
    "candle_index": 39,
    "open": 153.29,
    "high": 154.89,
    "low": 153.29,
    "close": 154.64,
    "body_pct": 0.8437499999999994,
    "upper_shadow_pct": 0.15625000000000056,
    "lower_shadow_pct": 0.0,
    "position_in_window": 0.4105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-05-08 10:00:00+00:00",
    "candle_index": 40,
    "open": 154.64,
    "high": 155.19,
    "low": 154.37,
    "close": 154.59,
    "body_pct": 0.06097560975607727,
    "upper_shadow_pct": 0.6707317073170926,
    "lower_shadow_pct": 0.2682926829268301,
    "position_in_window": 0.4211,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "DOJI_INDECISION"
    ]
  }
]
```
### Doji / spinning top / small body cluster
```json
{
  "doji_count": 11,
  "doji_ratio": 0.11458333333333333,
  "small_body_count": 26,
  "small_body_ratio": 0.2708333333333333,
  "bullish_body_total": 30.990000000000038,
  "bearish_body_total": 13.979999999999905
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
    "code": "BEARISH_ENGULFING_CONTEXT",
    "description": "Bearish body engulfs the preceding bullish body",
    "contribution": -0.1,
    "metadata": {
      "previous_timestamp": "2025-05-08 00:15:00+00:00",
      "timestamp": "2025-05-08 00:30:00+00:00",
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
      "previous_timestamp": "2025-05-08 00:15:00+00:00",
      "timestamp": "2025-05-08 00:30:00+00:00",
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
      "previous_timestamp": "2025-05-08 00:30:00+00:00",
      "timestamp": "2025-05-08 00:45:00+00:00",
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
      "previous_timestamp": "2025-05-08 00:30:00+00:00",
      "timestamp": "2025-05-08 00:45:00+00:00",
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
      "previous_timestamp": "2025-05-08 02:45:00+00:00",
      "timestamp": "2025-05-08 03:00:00+00:00",
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
      "previous_timestamp": "2025-05-08 02:45:00+00:00",
      "timestamp": "2025-05-08 03:00:00+00:00",
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
      "previous_timestamp": "2025-05-08 04:15:00+00:00",
      "timestamp": "2025-05-08 04:30:00+00:00",
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
      "previous_timestamp": "2025-05-08 04:15:00+00:00",
      "timestamp": "2025-05-08 04:30:00+00:00",
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
      "previous_timestamp": "2025-05-08 05:30:00+00:00",
      "timestamp": "2025-05-08 05:45:00+00:00",
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
      "previous_timestamp": "2025-05-08 05:30:00+00:00",
      "timestamp": "2025-05-08 05:45:00+00:00",
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
      "previous_timestamp": "2025-05-08 05:45:00+00:00",
      "timestamp": "2025-05-08 06:00:00+00:00",
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
      "previous_timestamp": "2025-05-08 05:45:00+00:00",
      "timestamp": "2025-05-08 06:00:00+00:00",
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
      "previous_timestamp": "2025-05-08 06:15:00+00:00",
      "timestamp": "2025-05-08 06:30:00+00:00",
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
      "previous_timestamp": "2025-05-08 06:15:00+00:00",
      "timestamp": "2025-05-08 06:30:00+00:00",
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
      "previous_timestamp": "2025-05-08 07:45:00+00:00",
      "timestamp": "2025-05-08 08:00:00+00:00",
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
      "previous_timestamp": "2025-05-08 07:45:00+00:00",
      "timestamp": "2025-05-08 08:00:00+00:00",
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
      "previous_timestamp": "2025-05-08 10:00:00+00:00",
      "timestamp": "2025-05-08 10:15:00+00:00",
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
      "previous_timestamp": "2025-05-08 10:00:00+00:00",
      "timestamp": "2025-05-08 10:15:00+00:00",
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
      "previous_timestamp": "2025-05-08 12:00:00+00:00",
      "timestamp": "2025-05-08 12:15:00+00:00",
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
      "previous_timestamp": "2025-05-08 12:00:00+00:00",
      "timestamp": "2025-05-08 12:15:00+00:00",
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
CLOSE_NEAR_HIGH, CLOSE_NEAR_LOW, STRONG_BULLISH_CANDLE_BODY, LONG_UPPER_SHADOW_REJECTION, SMALL_BODY_INDECISION, DOJI_INDECISION, LONG_LOWER_SHADOW_REJECTION, SPINNING_TOP_INDECISION, STRONG_BEARISH_CANDLE_BODY, HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED, CANDLE_PATTERN_NEEDS_TREND_CONTEXT, SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED, BEARISH_ENGULFING_CONTEXT, ENGULFING_WITHOUT_FOLLOW_THROUGH, BULLISH_ENGULFING_CONTEXT, DARK_CLOUD_BEARISH_CONTEXT, REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH, BEARISH_BELT_HOLD_CONTEXT_REQUIRED, BULLISH_BELT_HOLD_CONTEXT_REQUIRED, LONG_LEGGED_DOJI_CONTEXT, RICKSHAW_MAN_DOJI_CONTEXT, HANGING_MAN_LIKE_CONTEXT_REQUIRED, INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED, TWEEZERS_BOTTOM_CONTEXT_REQUIRED, TWEEZERS_TOP_CONTEXT_REQUIRED, DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT, DOJI_TOP_CONTEXT_REQUIRED, BEARISH_SEPARATING_LINES_CONTEXT, BULLISH_SEPARATING_LINES_CONTEXT, BEARISH_HARAMI_CONTEXT, HARAMI_CROSS_CONTEXT, BULLISH_BODY_DOMINANCE

## 2. Altunina trend context
### Swing structure
```json
[
  {
    "index": 2,
    "timestamp": "2025-05-08 00:30:00+00:00",
    "price": 147.08,
    "point_type": "LOW"
  },
  {
    "index": 4,
    "timestamp": "2025-05-08 01:00:00+00:00",
    "price": 149.99,
    "point_type": "HIGH"
  },
  {
    "index": 7,
    "timestamp": "2025-05-08 01:45:00+00:00",
    "price": 147.93,
    "point_type": "LOW"
  },
  {
    "index": 10,
    "timestamp": "2025-05-08 02:30:00+00:00",
    "price": 150.32,
    "point_type": "HIGH"
  },
  {
    "index": 12,
    "timestamp": "2025-05-08 03:00:00+00:00",
    "price": 149.57,
    "point_type": "LOW"
  },
  {
    "index": 17,
    "timestamp": "2025-05-08 04:15:00+00:00",
    "price": 151.97,
    "point_type": "HIGH"
  },
  {
    "index": 21,
    "timestamp": "2025-05-08 05:15:00+00:00",
    "price": 149.97,
    "point_type": "LOW"
  },
  {
    "index": 35,
    "timestamp": "2025-05-08 08:45:00+00:00",
    "price": 153.34,
    "point_type": "HIGH"
  },
  {
    "index": 36,
    "timestamp": "2025-05-08 09:00:00+00:00",
    "price": 152.53,
    "point_type": "LOW"
  },
  {
    "index": 41,
    "timestamp": "2025-05-08 10:15:00+00:00",
    "price": 155.28,
    "point_type": "HIGH"
  },
  {
    "index": 46,
    "timestamp": "2025-05-08 11:30:00+00:00",
    "price": 153.71,
    "point_type": "LOW"
  },
  {
    "index": 50,
    "timestamp": "2025-05-08 12:30:00+00:00",
    "price": 155.85,
    "point_type": "HIGH"
  },
  {
    "index": 51,
    "timestamp": "2025-05-08 12:45:00+00:00",
    "price": 154.47,
    "point_type": "LOW"
  },
  {
    "index": 54,
    "timestamp": "2025-05-08 13:30:00+00:00",
    "price": 155.67,
    "point_type": "HIGH"
  },
  {
    "index": 56,
    "timestamp": "2025-05-08 14:00:00+00:00",
    "price": 154.26,
    "point_type": "LOW"
  },
  {
    "index": 62,
    "timestamp": "2025-05-08 15:30:00+00:00",
    "price": 163.18,
    "point_type": "HIGH"
  },
  {
    "index": 64,
    "timestamp": "2025-05-08 16:00:00+00:00",
    "price": 159.44,
    "point_type": "LOW"
  },
  {
    "index": 65,
    "timestamp": "2025-05-08 16:15:00+00:00",
    "price": 161.07,
    "point_type": "HIGH"
  },
  {
    "index": 68,
    "timestamp": "2025-05-08 17:00:00+00:00",
    "price": 159.33,
    "point_type": "LOW"
  },
  {
    "index": 69,
    "timestamp": "2025-05-08 17:15:00+00:00",
    "price": 160.26,
    "point_type": "HIGH"
  },
  {
    "index": 71,
    "timestamp": "2025-05-08 17:45:00+00:00",
    "price": 158.52,
    "point_type": "LOW"
  },
  {
    "index": 74,
    "timestamp": "2025-05-08 18:30:00+00:00",
    "price": 160.38,
    "point_type": "HIGH"
  },
  {
    "index": 75,
    "timestamp": "2025-05-08 18:45:00+00:00",
    "price": 159.76,
    "point_type": "LOW"
  },
  {
    "index": 77,
    "timestamp": "2025-05-08 19:15:00+00:00",
    "price": 160.75,
    "point_type": "HIGH"
  },
  {
    "index": 78,
    "timestamp": "2025-05-08 19:30:00+00:00",
    "price": 159.7,
    "point_type": "LOW"
  },
  {
    "index": 80,
    "timestamp": "2025-05-08 20:00:00+00:00",
    "price": 161.39,
    "point_type": "HIGH"
  },
  {
    "index": 81,
    "timestamp": "2025-05-08 20:15:00+00:00",
    "price": 159.75,
    "point_type": "LOW"
  },
  {
    "index": 83,
    "timestamp": "2025-05-08 20:45:00+00:00",
    "price": 163.45,
    "point_type": "HIGH"
  },
  {
    "index": 84,
    "timestamp": "2025-05-08 21:00:00+00:00",
    "price": 160.96,
    "point_type": "LOW"
  },
  {
    "index": 85,
    "timestamp": "2025-05-08 21:15:00+00:00",
    "price": 164.0,
    "point_type": "HIGH"
  },
  {
    "index": 87,
    "timestamp": "2025-05-08 21:45:00+00:00",
    "price": 160.18,
    "point_type": "LOW"
  }
]
```
### Higher highs / lower highs
```json
{
  "raw_swing_count": 38,
  "swing_count": 31,
  "leg_count": 30,
  "structure_direction": "SIDEWAYS_STRUCTURE",
  "total_movement": 66.73999999999987,
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
    "lower_price": 149.57,
    "upper_price": 150.32,
    "mid_price": 149.97,
    "touch_count": 6,
    "source_indexes": [
      4,
      10,
      12,
      14,
      21,
      24
    ],
    "zone_width": 0.75,
    "zone_width_ratio": 0.005001000200040008,
    "formed_at_index": 24,
    "first_touch_index": 4,
    "last_touch_index": 24,
    "source_point_types": [
      "HIGH",
      "HIGH",
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
    "lower_price": 160.18,
    "upper_price": 160.75,
    "mid_price": 160.39249999999998,
    "touch_count": 4,
    "source_indexes": [
      69,
      74,
      77,
      87
    ],
    "zone_width": 0.5699999999999932,
    "zone_width_ratio": 0.003553782128216676,
    "formed_at_index": 87,
    "first_touch_index": 69,
    "last_touch_index": 87,
    "source_point_types": [
      "HIGH",
      "HIGH",
      "HIGH",
      "LOW"
    ],
    "original_zone_type": "RESISTANCE",
    "current_zone_type": "RESISTANCE",
    "role_changed_at_index": null,
    "is_significant_single_extreme": false,
    "positional_zone_type": "SUPPORT"
  },
  "is_detected": false,
  "lower_boundary": 149.57,
  "upper_boundary": 160.75,
  "midline": 155.16,
  "width": 11.180000000000007,
  "width_ratio": 0.07205465326114982,
  "touch_count": 10,
  "inside_close_ratio": 0.8452380952380952,
  "formed_at_index": 87,
  "first_touch_index": 4,
  "duration_candles": 84,
  "boundary_alternation_count": 1
}
```
### Range high / low
See trading range object above.
### Price position inside range
```json
{
  "swing_count": 38,
  "zone_count": 12,
  "range_detected": false,
  "range_formed_at_index": 87,
  "range_duration_candles": 84,
  "inside_close_ratio": 0.8452380952380952,
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
  "analysis_start_index": 0,
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
SCHWAGER_SUPPORT_ZONE_IDENTIFIED, SCHWAGER_PREVIOUS_EXTREME_ZONE_IDENTIFIED, SCHWAGER_SUPPORT_ZONE_HELD, SCHWAGER_ZONE_TOO_WIDE, SCHWAGER_RESISTANCE_ZONE_IDENTIFIED, SCHWAGER_RESISTANCE_ZONE_HELD, SCHWAGER_RANGE_NOT_CONFIRMED

## 4. BookEvidenceMatrix
### Bullish evidence
Count: 42
### Bearish evidence
Count: 26
### Neutral/range evidence
Count: 323
### Conflict
```json
{
  "agreement_state": "ALIGNED_BULLISH",
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
  "total_evidence_count": 391,
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
  "FLAT": 0.2,
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
    "score": 0.2
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
The engine returned UNKNOWN because the composer status was FALLBACK_UNKNOWN and selected UNKNOWN. The strongest visible candidate scores after clamping were UP=1.000 and DOWN=1.000; fallback reason: COMPOSER_CONSERVATIVE_FALLBACK_UNKNOWN. The reference label is EXPECTED_UP and remains descriptive, not ground truth.
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
