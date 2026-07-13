# sol_15m_expected_flat_001 вЂ” Market Evidence Trace

## Window
- Symbol: SOLUSDT
- Interval: 15m
- Period: 2026-04-25T00:00:00+00:00 вЂ” 2026-04-25T23:45:00+00:00
- Reference label: EXPECTED_FLAT
- Selection reason: deterministic expected_flat OHLC rule

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
    "timestamp": "2026-04-25 00:00:00+00:00",
    "candle_index": 0,
    "open": 86.18,
    "high": 86.22,
    "low": 86.09,
    "close": 86.11,
    "body_pct": 0.5384615384616142,
    "upper_shadow_pct": 0.30769230769225725,
    "lower_shadow_pct": 0.15384615384612862,
    "position_in_window": 0.0,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-04-25 00:15:00+00:00",
    "candle_index": 1,
    "open": 86.11,
    "high": 86.15,
    "low": 86.03,
    "close": 86.04,
    "body_pct": 0.5833333333332544,
    "upper_shadow_pct": 0.3333333333333728,
    "lower_shadow_pct": 0.08333333333337281,
    "position_in_window": 0.0105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-04-25 00:45:00+00:00",
    "candle_index": 3,
    "open": 86.15,
    "high": 86.26,
    "low": 86.14,
    "close": 86.23,
    "body_pct": 0.6666666666666272,
    "upper_shadow_pct": 0.25,
    "lower_shadow_pct": 0.08333333333337281,
    "position_in_window": 0.0316,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-04-25 01:00:00+00:00",
    "candle_index": 4,
    "open": 86.23,
    "high": 86.29,
    "low": 86.15,
    "close": 86.27,
    "body_pct": 0.2857142857142277,
    "upper_shadow_pct": 0.14285714285721537,
    "lower_shadow_pct": 0.571428571428557,
    "position_in_window": 0.0421,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-04-25 01:15:00+00:00",
    "candle_index": 5,
    "open": 86.27,
    "high": 86.34,
    "low": 86.13,
    "close": 86.18,
    "body_pct": 0.4285714285713609,
    "upper_shadow_pct": 0.3333333333333559,
    "lower_shadow_pct": 0.2380952380952832,
    "position_in_window": 0.0526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-04-25 01:30:00+00:00",
    "candle_index": 6,
    "open": 86.19,
    "high": 86.32,
    "low": 86.18,
    "close": 86.3,
    "body_pct": 0.7857142857143582,
    "upper_shadow_pct": 0.14285714285712836,
    "lower_shadow_pct": 0.07142857142851343,
    "position_in_window": 0.0632,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-04-25 01:45:00+00:00",
    "candle_index": 7,
    "open": 86.3,
    "high": 86.36,
    "low": 86.26,
    "close": 86.27,
    "body_pct": 0.3000000000000284,
    "upper_shadow_pct": 0.6000000000000568,
    "lower_shadow_pct": 0.09999999999991474,
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
    "timestamp": "2026-04-25 02:00:00+00:00",
    "candle_index": 8,
    "open": 86.28,
    "high": 86.4,
    "low": 86.2,
    "close": 86.31,
    "body_pct": 0.15000000000000355,
    "upper_shadow_pct": 0.45000000000001067,
    "lower_shadow_pct": 0.3999999999999858,
    "position_in_window": 0.0842,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2026-04-25 02:15:00+00:00",
    "candle_index": 9,
    "open": 86.31,
    "high": 86.33,
    "low": 86.16,
    "close": 86.29,
    "body_pct": 0.11764705882350482,
    "upper_shadow_pct": 0.11764705882350482,
    "lower_shadow_pct": 0.7647058823529903,
    "position_in_window": 0.0947,
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
    "timestamp": "2026-04-25 02:30:00+00:00",
    "candle_index": 10,
    "open": 86.3,
    "high": 86.32,
    "low": 86.25,
    "close": 86.26,
    "body_pct": 0.5714285714285134,
    "upper_shadow_pct": 0.2857142857142567,
    "lower_shadow_pct": 0.14285714285722986,
    "position_in_window": 0.1053,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-04-25 02:45:00+00:00",
    "candle_index": 11,
    "open": 86.27,
    "high": 86.3,
    "low": 86.25,
    "close": 86.29,
    "body_pct": 0.4000000000002274,
    "upper_shadow_pct": 0.19999999999982948,
    "lower_shadow_pct": 0.3999999999999432,
    "position_in_window": 0.1158,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-04-25 03:00:00+00:00",
    "candle_index": 12,
    "open": 86.28,
    "high": 86.4,
    "low": 86.27,
    "close": 86.31,
    "body_pct": 0.23076923076922237,
    "upper_shadow_pct": 0.6923076923076671,
    "lower_shadow_pct": 0.07692307692311055,
    "position_in_window": 0.1263,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION",
      "SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED",
      "CANDLE_PATTERN_NEEDS_TREND_CONTEXT"
    ]
  },
  {
    "timestamp": "2026-04-25 03:15:00+00:00",
    "candle_index": 13,
    "open": 86.31,
    "high": 86.42,
    "low": 86.3,
    "close": 86.34,
    "body_pct": 0.25,
    "upper_shadow_pct": 0.6666666666666272,
    "lower_shadow_pct": 0.08333333333337281,
    "position_in_window": 0.1368,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION",
      "SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED",
      "CANDLE_PATTERN_NEEDS_TREND_CONTEXT"
    ]
  },
  {
    "timestamp": "2026-04-25 03:30:00+00:00",
    "candle_index": 14,
    "open": 86.34,
    "high": 86.43,
    "low": 86.33,
    "close": 86.41,
    "body_pct": 0.6999999999998721,
    "upper_shadow_pct": 0.20000000000008528,
    "lower_shadow_pct": 0.10000000000004264,
    "position_in_window": 0.1474,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-04-25 04:00:00+00:00",
    "candle_index": 16,
    "open": 86.46,
    "high": 86.51,
    "low": 86.4,
    "close": 86.46,
    "body_pct": 0.0,
    "upper_shadow_pct": 0.4545454545455602,
    "lower_shadow_pct": 0.5454545454544397,
    "position_in_window": 0.1684,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "DOJI_INDECISION"
    ]
  },
  {
    "timestamp": "2026-04-25 04:15:00+00:00",
    "candle_index": 17,
    "open": 86.46,
    "high": 86.47,
    "low": 86.32,
    "close": 86.35,
    "body_pct": 0.7333333333333018,
    "upper_shadow_pct": 0.06666666666669825,
    "lower_shadow_pct": 0.2,
    "position_in_window": 0.1789,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-04-25 05:00:00+00:00",
    "candle_index": 20,
    "open": 86.34,
    "high": 86.34,
    "low": 86.15,
    "close": 86.17,
    "body_pct": 0.8947368421052828,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.10526315789471716,
    "position_in_window": 0.2105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-04-25 05:15:00+00:00",
    "candle_index": 21,
    "open": 86.17,
    "high": 86.18,
    "low": 86.13,
    "close": 86.13,
    "body_pct": 0.7999999999999432,
    "upper_shadow_pct": 0.20000000000005685,
    "lower_shadow_pct": 0.0,
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
    "timestamp": "2026-04-25 06:00:00+00:00",
    "candle_index": 24,
    "open": 86.2,
    "high": 86.35,
    "low": 86.19,
    "close": 86.35,
    "body_pct": 0.9374999999999667,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.0625000000000333,
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
    "timestamp": "2026-04-25 06:30:00+00:00",
    "candle_index": 26,
    "open": 86.26,
    "high": 86.46,
    "low": 86.26,
    "close": 86.42,
    "body_pct": 0.8000000000000285,
    "upper_shadow_pct": 0.1999999999999716,
    "lower_shadow_pct": 0.0,
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
    "timestamp": "2026-04-25 06:45:00+00:00",
    "candle_index": 27,
    "open": 86.42,
    "high": 86.66,
    "low": 86.41,
    "close": 86.45,
    "body_pct": 0.12000000000000455,
    "upper_shadow_pct": 0.839999999999975,
    "lower_shadow_pct": 0.040000000000020464,
    "position_in_window": 0.2842,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
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
    "timestamp": "2026-04-25 07:15:00+00:00",
    "candle_index": 29,
    "open": 86.35,
    "high": 86.39,
    "low": 86.25,
    "close": 86.32,
    "body_pct": 0.21428571428572155,
    "upper_shadow_pct": 0.2857142857143292,
    "lower_shadow_pct": 0.49999999999994926,
    "position_in_window": 0.3053,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2026-04-25 07:45:00+00:00",
    "candle_index": 31,
    "open": 86.39,
    "high": 86.45,
    "low": 86.34,
    "close": 86.36,
    "body_pct": 0.2727272727272845,
    "upper_shadow_pct": 0.545454545454569,
    "lower_shadow_pct": 0.18181818181814657,
    "position_in_window": 0.3263,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-04-25 08:00:00+00:00",
    "candle_index": 32,
    "open": 86.36,
    "high": 86.45,
    "low": 86.3,
    "close": 86.44,
    "body_pct": 0.5333333333333018,
    "upper_shadow_pct": 0.06666666666669825,
    "lower_shadow_pct": 0.4,
    "position_in_window": 0.3368,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-04-25 08:15:00+00:00",
    "candle_index": 33,
    "open": 86.44,
    "high": 86.59,
    "low": 86.43,
    "close": 86.59,
    "body_pct": 0.9375000000000555,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.06249999999994449,
    "position_in_window": 0.3474,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-04-25 08:30:00+00:00",
    "candle_index": 34,
    "open": 86.59,
    "high": 86.8,
    "low": 86.55,
    "close": 86.62,
    "body_pct": 0.12000000000000455,
    "upper_shadow_pct": 0.7199999999999704,
    "lower_shadow_pct": 0.160000000000025,
    "position_in_window": 0.3579,
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
    "timestamp": "2026-04-25 08:45:00+00:00",
    "candle_index": 35,
    "open": 86.63,
    "high": 86.63,
    "low": 86.57,
    "close": 86.63,
    "body_pct": 0.0,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 1.0,
    "position_in_window": 0.3684,
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
    "timestamp": "2026-04-25 09:00:00+00:00",
    "candle_index": 36,
    "open": 86.62,
    "high": 86.67,
    "low": 86.57,
    "close": 86.67,
    "body_pct": 0.49999999999992895,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.500000000000071,
    "position_in_window": 0.3789,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-04-25 09:15:00+00:00",
    "candle_index": 37,
    "open": 86.66,
    "high": 86.69,
    "low": 86.58,
    "close": 86.58,
    "body_pct": 0.7272727272727155,
    "upper_shadow_pct": 0.2727272727272845,
    "lower_shadow_pct": 0.0,
    "position_in_window": 0.3895,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-04-25 09:45:00+00:00",
    "candle_index": 39,
    "open": 86.72,
    "high": 86.76,
    "low": 86.57,
    "close": 86.58,
    "body_pct": 0.7368421052631146,
    "upper_shadow_pct": 0.21052631578949338,
    "lower_shadow_pct": 0.05263157894739204,
    "position_in_window": 0.4105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  }
]
```
### Doji / spinning top / small body cluster
```json
{
  "doji_count": 11,
  "doji_ratio": 0.11458333333333333,
  "small_body_count": 33,
  "small_body_ratio": 0.34375,
  "bullish_body_total": 3.2699999999999534,
  "bearish_body_total": 3.279999999999987
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
      "previous_timestamp": "2026-04-25 00:15:00+00:00",
      "timestamp": "2026-04-25 00:30:00+00:00",
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
      "previous_timestamp": "2026-04-25 00:15:00+00:00",
      "timestamp": "2026-04-25 00:30:00+00:00",
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
      "previous_timestamp": "2026-04-25 01:00:00+00:00",
      "timestamp": "2026-04-25 01:15:00+00:00",
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
      "previous_timestamp": "2026-04-25 01:00:00+00:00",
      "timestamp": "2026-04-25 01:15:00+00:00",
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
      "previous_timestamp": "2026-04-25 04:45:00+00:00",
      "timestamp": "2026-04-25 05:00:00+00:00",
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
      "previous_timestamp": "2026-04-25 04:45:00+00:00",
      "timestamp": "2026-04-25 05:00:00+00:00",
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
      "previous_timestamp": "2026-04-25 05:45:00+00:00",
      "timestamp": "2026-04-25 06:00:00+00:00",
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
      "previous_timestamp": "2026-04-25 05:45:00+00:00",
      "timestamp": "2026-04-25 06:00:00+00:00",
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
      "previous_timestamp": "2026-04-25 06:45:00+00:00",
      "timestamp": "2026-04-25 07:00:00+00:00",
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
      "previous_timestamp": "2026-04-25 06:45:00+00:00",
      "timestamp": "2026-04-25 07:00:00+00:00",
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
      "previous_timestamp": "2026-04-25 07:15:00+00:00",
      "timestamp": "2026-04-25 07:30:00+00:00",
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
      "previous_timestamp": "2026-04-25 07:15:00+00:00",
      "timestamp": "2026-04-25 07:30:00+00:00",
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
      "previous_timestamp": "2026-04-25 07:45:00+00:00",
      "timestamp": "2026-04-25 08:00:00+00:00",
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
      "previous_timestamp": "2026-04-25 07:45:00+00:00",
      "timestamp": "2026-04-25 08:00:00+00:00",
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
      "previous_timestamp": "2026-04-25 09:30:00+00:00",
      "timestamp": "2026-04-25 09:45:00+00:00",
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
      "previous_timestamp": "2026-04-25 09:30:00+00:00",
      "timestamp": "2026-04-25 09:45:00+00:00",
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
      "previous_timestamp": "2026-04-25 10:45:00+00:00",
      "timestamp": "2026-04-25 11:00:00+00:00",
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
      "previous_timestamp": "2026-04-25 10:45:00+00:00",
      "timestamp": "2026-04-25 11:00:00+00:00",
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
      "previous_timestamp": "2026-04-25 11:45:00+00:00",
      "timestamp": "2026-04-25 12:00:00+00:00",
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
      "previous_timestamp": "2026-04-25 11:45:00+00:00",
      "timestamp": "2026-04-25 12:00:00+00:00",
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
CLOSE_NEAR_LOW, CLOSE_NEAR_HIGH, LONG_LOWER_SHADOW_REJECTION, SMALL_BODY_INDECISION, STRONG_BULLISH_CANDLE_BODY, LONG_UPPER_SHADOW_REJECTION, SPINNING_TOP_INDECISION, SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED, CANDLE_PATTERN_NEEDS_TREND_CONTEXT, DOJI_INDECISION, STRONG_BEARISH_CANDLE_BODY, BULLISH_ENGULFING_CONTEXT, ENGULFING_WITHOUT_FOLLOW_THROUGH, BEARISH_ENGULFING_CONTEXT, BULLISH_BELT_HOLD_CONTEXT_REQUIRED, INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED, REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH, LONG_LEGGED_DOJI_CONTEXT, RICKSHAW_MAN_DOJI_CONTEXT, BEARISH_BELT_HOLD_CONTEXT_REQUIRED, DRAGONFLY_DOJI_CONTEXT, GRAVESTONE_DOJI_CONTEXT, TWEEZERS_BOTTOM_CONTEXT_REQUIRED, TWEEZERS_TOP_CONTEXT_REQUIRED, BULLISH_HARAMI_CONTEXT, BEARISH_SEPARATING_LINES_CONTEXT, BEARISH_HARAMI_CONTEXT, THREE_ADVANCING_WHITE_SOLDIERS_CONTEXT, FALLING_THREE_METHODS_CONTEXT

## 2. Altunina trend context
### Swing structure
```json
[
  {
    "index": 5,
    "timestamp": "2026-04-25 01:15:00+00:00",
    "price": 86.13,
    "point_type": "LOW"
  },
  {
    "index": 8,
    "timestamp": "2026-04-25 02:00:00+00:00",
    "price": 86.4,
    "point_type": "HIGH"
  },
  {
    "index": 9,
    "timestamp": "2026-04-25 02:15:00+00:00",
    "price": 86.16,
    "point_type": "LOW"
  },
  {
    "index": 16,
    "timestamp": "2026-04-25 04:00:00+00:00",
    "price": 86.51,
    "point_type": "HIGH"
  },
  {
    "index": 22,
    "timestamp": "2026-04-25 05:30:00+00:00",
    "price": 86.11,
    "point_type": "LOW"
  },
  {
    "index": 27,
    "timestamp": "2026-04-25 06:45:00+00:00",
    "price": 86.66,
    "point_type": "HIGH"
  },
  {
    "index": 29,
    "timestamp": "2026-04-25 07:15:00+00:00",
    "price": 86.25,
    "point_type": "LOW"
  },
  {
    "index": 30,
    "timestamp": "2026-04-25 07:30:00+00:00",
    "price": 86.51,
    "point_type": "HIGH"
  },
  {
    "index": 32,
    "timestamp": "2026-04-25 08:00:00+00:00",
    "price": 86.3,
    "point_type": "LOW"
  },
  {
    "index": 34,
    "timestamp": "2026-04-25 08:30:00+00:00",
    "price": 86.8,
    "point_type": "HIGH"
  },
  {
    "index": 48,
    "timestamp": "2026-04-25 12:00:00+00:00",
    "price": 86.23,
    "point_type": "LOW"
  },
  {
    "index": 55,
    "timestamp": "2026-04-25 13:45:00+00:00",
    "price": 86.67,
    "point_type": "HIGH"
  },
  {
    "index": 60,
    "timestamp": "2026-04-25 15:00:00+00:00",
    "price": 86.42,
    "point_type": "LOW"
  },
  {
    "index": 61,
    "timestamp": "2026-04-25 15:15:00+00:00",
    "price": 86.64,
    "point_type": "HIGH"
  },
  {
    "index": 66,
    "timestamp": "2026-04-25 16:30:00+00:00",
    "price": 85.61,
    "point_type": "LOW"
  },
  {
    "index": 72,
    "timestamp": "2026-04-25 18:00:00+00:00",
    "price": 85.78,
    "point_type": "HIGH"
  },
  {
    "index": 73,
    "timestamp": "2026-04-25 18:15:00+00:00",
    "price": 85.53,
    "point_type": "LOW"
  },
  {
    "index": 75,
    "timestamp": "2026-04-25 18:45:00+00:00",
    "price": 85.82,
    "point_type": "HIGH"
  },
  {
    "index": 77,
    "timestamp": "2026-04-25 19:15:00+00:00",
    "price": 85.55,
    "point_type": "LOW"
  },
  {
    "index": 85,
    "timestamp": "2026-04-25 21:15:00+00:00",
    "price": 86.11,
    "point_type": "HIGH"
  },
  {
    "index": 86,
    "timestamp": "2026-04-25 21:30:00+00:00",
    "price": 85.74,
    "point_type": "LOW"
  },
  {
    "index": 90,
    "timestamp": "2026-04-25 22:30:00+00:00",
    "price": 86.18,
    "point_type": "HIGH"
  },
  {
    "index": 93,
    "timestamp": "2026-04-25 23:15:00+00:00",
    "price": 86.04,
    "point_type": "LOW"
  },
  {
    "index": 94,
    "timestamp": "2026-04-25 23:30:00+00:00",
    "price": 86.2,
    "point_type": "HIGH"
  }
]
```
### Higher highs / lower highs
```json
{
  "raw_swing_count": 31,
  "swing_count": 24,
  "leg_count": 23,
  "structure_direction": "SIDEWAYS_STRUCTURE",
  "total_movement": 8.350000000000037,
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
    "lower_price": 86.04,
    "upper_price": 86.42,
    "mid_price": 86.218125,
    "touch_count": 16,
    "source_indexes": [
      5,
      5,
      8,
      9,
      22,
      22,
      29,
      32,
      48,
      50,
      60,
      63,
      85,
      90,
      93,
      94
    ],
    "zone_width": 0.37999999999999545,
    "zone_width_ratio": 0.004407425932772204,
    "formed_at_index": 94,
    "first_touch_index": 5,
    "last_touch_index": 94,
    "source_point_types": [
      "LOW",
      "HIGH",
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
      "HIGH",
      "HIGH",
      "LOW",
      "HIGH"
    ],
    "original_zone_type": "SUPPORT",
    "current_zone_type": "SUPPORT",
    "role_changed_at_index": null,
    "is_significant_single_extreme": false,
    "positional_zone_type": "RESISTANCE"
  },
  "resistance_zone": {
    "zone_type": "RESISTANCE",
    "lower_price": 86.5,
    "upper_price": 86.8,
    "mid_price": 86.62999999999998,
    "touch_count": 9,
    "source_indexes": [
      16,
      27,
      30,
      34,
      38,
      42,
      55,
      56,
      61
    ],
    "zone_width": 0.29999999999999716,
    "zone_width_ratio": 0.003463003578436999,
    "formed_at_index": 61,
    "first_touch_index": 16,
    "last_touch_index": 61,
    "source_point_types": [
      "HIGH",
      "HIGH",
      "HIGH",
      "HIGH",
      "HIGH",
      "LOW",
      "HIGH",
      "LOW",
      "HIGH"
    ],
    "original_zone_type": "RESISTANCE",
    "current_zone_type": "RESISTANCE",
    "role_changed_at_index": null,
    "is_significant_single_extreme": false,
    "positional_zone_type": "RESISTANCE"
  },
  "is_detected": true,
  "lower_boundary": 86.04,
  "upper_boundary": 86.8,
  "midline": 86.42,
  "width": 0.7599999999999909,
  "width_ratio": 0.008794260587826787,
  "touch_count": 25,
  "inside_close_ratio": 0.7555555555555555,
  "formed_at_index": 94,
  "first_touch_index": 5,
  "duration_candles": 90,
  "boundary_alternation_count": 12
}
```
### Range high / low
See trading range object above.
### Price position inside range
```json
{
  "swing_count": 31,
  "zone_count": 3,
  "range_detected": true,
  "range_formed_at_index": 94,
  "range_duration_candles": 90,
  "inside_close_ratio": 0.7555555555555555,
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
  "analysis_start_index": 95,
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
SCHWAGER_SUPPORT_ZONE_IDENTIFIED, SCHWAGER_SUPPORT_ZONE_HELD, SCHWAGER_ZONE_TOO_WIDE, SCHWAGER_RESISTANCE_ZONE_IDENTIFIED, SCHWAGER_RESISTANCE_ZONE_HELD, SCHWAGER_TRADING_RANGE_DETECTED, SCHWAGER_PRICE_INSIDE_RANGE, SCHWAGER_RANGE_UPPER_BOUNDARY_HELD, SCHWAGER_RANGE_LOWER_BOUNDARY_HELD, SCHWAGER_RANGE_DURATION_CONFIRMED, SCHWAGER_RANGE_BOUNDARY_ALTERNATION_CONFIRMED

## 4. BookEvidenceMatrix
### Bullish evidence
Count: 26
### Bearish evidence
Count: 31
### Neutral/range evidence
Count: 312
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
  "total_evidence_count": 369,
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
  "FLAT": 0.5511111111111111,
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
    "score": 0.5511111111111111
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
