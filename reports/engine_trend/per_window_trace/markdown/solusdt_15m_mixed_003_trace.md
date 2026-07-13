# solusdt_15m_mixed_003 вЂ” Market Evidence Trace

## Window
- Symbol: SOLUSDT
- Interval: 15m
- Period: 2025-12-31T00:00:00+00:00 вЂ” 2025-12-31T23:45:00+00:00
- Reference label: EXPECTED_UNKNOWN_OR_MIXED
- Selection reason: ranked deterministic MIXED OHLC candidate

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
    "timestamp": "2025-12-31 00:15:00+00:00",
    "candle_index": 1,
    "open": 124.84,
    "high": 124.94,
    "low": 124.55,
    "close": 124.74,
    "body_pct": 0.2564102564102779,
    "upper_shadow_pct": 0.25641025641024145,
    "lower_shadow_pct": 0.4871794871794806,
    "position_in_window": 0.0105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION"
    ]
  },
  {
    "timestamp": "2025-12-31 00:30:00+00:00",
    "candle_index": 2,
    "open": 124.75,
    "high": 125.07,
    "low": 124.41,
    "close": 124.97,
    "body_pct": 0.3333333333333333,
    "upper_shadow_pct": 0.1515151515151437,
    "lower_shadow_pct": 0.515151515151523,
    "position_in_window": 0.0211,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-12-31 00:45:00+00:00",
    "candle_index": 3,
    "open": 124.96,
    "high": 125.02,
    "low": 124.83,
    "close": 124.95,
    "body_pct": 0.052631578947321185,
    "upper_shadow_pct": 0.3157894736842263,
    "lower_shadow_pct": 0.6315789473684525,
    "position_in_window": 0.0316,
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
    "timestamp": "2025-12-31 01:00:00+00:00",
    "candle_index": 4,
    "open": 124.94,
    "high": 125.35,
    "low": 124.83,
    "close": 125.32,
    "body_pct": 0.7307692307692276,
    "upper_shadow_pct": 0.05769230769231032,
    "lower_shadow_pct": 0.21153846153846206,
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
    "timestamp": "2025-12-31 01:15:00+00:00",
    "candle_index": 5,
    "open": 125.32,
    "high": 125.77,
    "low": 125.31,
    "close": 125.66,
    "body_pct": 0.7391304347826262,
    "upper_shadow_pct": 0.2391304347826107,
    "lower_shadow_pct": 0.021739130434763134,
    "position_in_window": 0.0526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-12-31 01:30:00+00:00",
    "candle_index": 6,
    "open": 125.67,
    "high": 125.95,
    "low": 125.55,
    "close": 125.71,
    "body_pct": 0.09999999999997869,
    "upper_shadow_pct": 0.6000000000000142,
    "lower_shadow_pct": 0.3000000000000071,
    "position_in_window": 0.0632,
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
    "timestamp": "2025-12-31 02:00:00+00:00",
    "candle_index": 8,
    "open": 125.53,
    "high": 125.94,
    "low": 125.32,
    "close": 125.94,
    "body_pct": 0.6612903225806348,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.3387096774193652,
    "position_in_window": 0.0842,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-12-31 02:30:00+00:00",
    "candle_index": 10,
    "open": 125.64,
    "high": 125.78,
    "low": 125.32,
    "close": 125.53,
    "body_pct": 0.23913043478260332,
    "upper_shadow_pct": 0.3043478260869525,
    "lower_shadow_pct": 0.4565217391304442,
    "position_in_window": 0.1053,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2025-12-31 02:45:00+00:00",
    "candle_index": 11,
    "open": 125.54,
    "high": 126.09,
    "low": 125.49,
    "close": 126.01,
    "body_pct": 0.7833333333333203,
    "upper_shadow_pct": 0.13333333333332859,
    "lower_shadow_pct": 0.08333333333335109,
    "position_in_window": 0.1158,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-12-31 03:00:00+00:00",
    "candle_index": 12,
    "open": 126.02,
    "high": 126.09,
    "low": 125.79,
    "close": 125.79,
    "body_pct": 0.7666666666666399,
    "upper_shadow_pct": 0.23333333333336018,
    "lower_shadow_pct": 0.0,
    "position_in_window": 0.1263,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-12-31 03:15:00+00:00",
    "candle_index": 13,
    "open": 125.79,
    "high": 125.81,
    "low": 125.45,
    "close": 125.52,
    "body_pct": 0.7500000000000296,
    "upper_shadow_pct": 0.05555555555554459,
    "lower_shadow_pct": 0.1944444444444258,
    "position_in_window": 0.1368,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-12-31 03:30:00+00:00",
    "candle_index": 14,
    "open": 125.51,
    "high": 125.57,
    "low": 125.17,
    "close": 125.41,
    "body_pct": 0.25000000000002665,
    "upper_shadow_pct": 0.14999999999997335,
    "lower_shadow_pct": 0.6,
    "position_in_window": 0.1474,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION"
    ]
  },
  {
    "timestamp": "2025-12-31 03:45:00+00:00",
    "candle_index": 15,
    "open": 125.41,
    "high": 125.85,
    "low": 125.33,
    "close": 125.82,
    "body_pct": 0.7884615384615379,
    "upper_shadow_pct": 0.05769230769231032,
    "lower_shadow_pct": 0.15384615384615175,
    "position_in_window": 0.1579,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-12-31 04:00:00+00:00",
    "candle_index": 16,
    "open": 125.81,
    "high": 125.96,
    "low": 125.38,
    "close": 125.5,
    "body_pct": 0.5344827586206952,
    "upper_shadow_pct": 0.2586206896551585,
    "lower_shadow_pct": 0.2068965517241464,
    "position_in_window": 0.1684,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-12-31 04:30:00+00:00",
    "candle_index": 18,
    "open": 125.61,
    "high": 125.8,
    "low": 125.61,
    "close": 125.76,
    "body_pct": 0.7894736842105656,
    "upper_shadow_pct": 0.21052631578943432,
    "lower_shadow_pct": 0.0,
    "position_in_window": 0.1895,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-12-31 04:45:00+00:00",
    "candle_index": 19,
    "open": 125.76,
    "high": 125.77,
    "low": 125.45,
    "close": 125.46,
    "body_pct": 0.9375000000000555,
    "upper_shadow_pct": 0.031249999999972244,
    "lower_shadow_pct": 0.031249999999972244,
    "position_in_window": 0.2,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-12-31 05:15:00+00:00",
    "candle_index": 21,
    "open": 125.59,
    "high": 125.66,
    "low": 125.44,
    "close": 125.66,
    "body_pct": 0.3181818181817888,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.6818181818182112,
    "position_in_window": 0.2211,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-12-31 05:30:00+00:00",
    "candle_index": 22,
    "open": 125.66,
    "high": 125.75,
    "low": 125.47,
    "close": 125.73,
    "body_pct": 0.25000000000002537,
    "upper_shadow_pct": 0.07142857142855692,
    "lower_shadow_pct": 0.6785714285714177,
    "position_in_window": 0.2316,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "CLOSE_NEAR_HIGH",
      "HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED",
      "CANDLE_PATTERN_NEEDS_TREND_CONTEXT"
    ]
  },
  {
    "timestamp": "2025-12-31 06:00:00+00:00",
    "candle_index": 24,
    "open": 125.65,
    "high": 125.86,
    "low": 125.6,
    "close": 125.8,
    "body_pct": 0.5769230769230328,
    "upper_shadow_pct": 0.23076923076923497,
    "lower_shadow_pct": 0.19230769230773226,
    "position_in_window": 0.2526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-12-31 06:15:00+00:00",
    "candle_index": 25,
    "open": 125.79,
    "high": 125.98,
    "low": 125.67,
    "close": 125.94,
    "body_pct": 0.4838709677419044,
    "upper_shadow_pct": 0.12903225806453536,
    "lower_shadow_pct": 0.3870967741935602,
    "position_in_window": 0.2632,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-12-31 06:30:00+00:00",
    "candle_index": 26,
    "open": 125.95,
    "high": 125.99,
    "low": 125.87,
    "close": 125.98,
    "body_pct": 0.2500000000000296,
    "upper_shadow_pct": 0.08333333333326426,
    "lower_shadow_pct": 0.6666666666667062,
    "position_in_window": 0.2737,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "CLOSE_NEAR_HIGH",
      "HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED",
      "CANDLE_PATTERN_NEEDS_TREND_CONTEXT"
    ]
  },
  {
    "timestamp": "2025-12-31 06:45:00+00:00",
    "candle_index": 27,
    "open": 125.97,
    "high": 126.1,
    "low": 125.84,
    "close": 125.89,
    "body_pct": 0.3076923076923119,
    "upper_shadow_pct": 0.5,
    "lower_shadow_pct": 0.1923076923076881,
    "position_in_window": 0.2842,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-12-31 07:00:00+00:00",
    "candle_index": 28,
    "open": 125.9,
    "high": 125.92,
    "low": 125.78,
    "close": 125.88,
    "body_pct": 0.14285714285721537,
    "upper_shadow_pct": 0.14285714285711384,
    "lower_shadow_pct": 0.7142857142856708,
    "position_in_window": 0.2947,
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
    "timestamp": "2025-12-31 07:15:00+00:00",
    "candle_index": 29,
    "open": 125.88,
    "high": 125.93,
    "low": 125.65,
    "close": 125.87,
    "body_pct": 0.035714285714253086,
    "upper_shadow_pct": 0.17857142857146846,
    "lower_shadow_pct": 0.7857142857142785,
    "position_in_window": 0.3053,
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
    "timestamp": "2025-12-31 07:30:00+00:00",
    "candle_index": 30,
    "open": 125.87,
    "high": 126.05,
    "low": 125.67,
    "close": 125.88,
    "body_pct": 0.026315789473660593,
    "upper_shadow_pct": 0.4473684210526414,
    "lower_shadow_pct": 0.526315789473698,
    "position_in_window": 0.3158,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "DOJI_INDECISION"
    ]
  },
  {
    "timestamp": "2025-12-31 07:45:00+00:00",
    "candle_index": 31,
    "open": 125.89,
    "high": 126.02,
    "low": 125.75,
    "close": 125.99,
    "body_pct": 0.37037037037035475,
    "upper_shadow_pct": 0.11111111111111696,
    "lower_shadow_pct": 0.5185185185185283,
    "position_in_window": 0.3263,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-12-31 08:30:00+00:00",
    "candle_index": 34,
    "open": 126.01,
    "high": 126.01,
    "low": 125.46,
    "close": 125.57,
    "body_pct": 0.8000000000000052,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.19999999999999482,
    "position_in_window": 0.3579,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-12-31 08:45:00+00:00",
    "candle_index": 35,
    "open": 125.57,
    "high": 125.63,
    "low": 125.44,
    "close": 125.57,
    "body_pct": 0.0,
    "upper_shadow_pct": 0.3157894736842263,
    "lower_shadow_pct": 0.6842105263157737,
    "position_in_window": 0.3684,
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
    "timestamp": "2025-12-31 09:15:00+00:00",
    "candle_index": 37,
    "open": 125.81,
    "high": 125.89,
    "low": 125.71,
    "close": 125.78,
    "body_pct": 0.16666666666666666,
    "upper_shadow_pct": 0.4444444444444181,
    "lower_shadow_pct": 0.3888888888889152,
    "position_in_window": 0.3895,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2025-12-31 09:30:00+00:00",
    "candle_index": 38,
    "open": 125.78,
    "high": 126.03,
    "low": 125.71,
    "close": 125.98,
    "body_pct": 0.6249999999999944,
    "upper_shadow_pct": 0.1562499999999875,
    "lower_shadow_pct": 0.21875000000001804,
    "position_in_window": 0.4,
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
  "doji_count": 15,
  "doji_ratio": 0.15625,
  "small_body_count": 27,
  "small_body_ratio": 0.28125,
  "bullish_body_total": 9.549999999999983,
  "bearish_body_total": 9.859999999999985
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
      "previous_timestamp": "2025-12-31 00:45:00+00:00",
      "timestamp": "2025-12-31 01:00:00+00:00",
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
      "previous_timestamp": "2025-12-31 00:45:00+00:00",
      "timestamp": "2025-12-31 01:00:00+00:00",
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
      "previous_timestamp": "2025-12-31 01:30:00+00:00",
      "timestamp": "2025-12-31 01:45:00+00:00",
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
      "previous_timestamp": "2025-12-31 01:30:00+00:00",
      "timestamp": "2025-12-31 01:45:00+00:00",
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
      "previous_timestamp": "2025-12-31 01:45:00+00:00",
      "timestamp": "2025-12-31 02:00:00+00:00",
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
      "previous_timestamp": "2025-12-31 01:45:00+00:00",
      "timestamp": "2025-12-31 02:00:00+00:00",
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
      "previous_timestamp": "2025-12-31 03:30:00+00:00",
      "timestamp": "2025-12-31 03:45:00+00:00",
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
      "previous_timestamp": "2025-12-31 03:30:00+00:00",
      "timestamp": "2025-12-31 03:45:00+00:00",
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
      "previous_timestamp": "2025-12-31 04:30:00+00:00",
      "timestamp": "2025-12-31 04:45:00+00:00",
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
      "previous_timestamp": "2025-12-31 04:30:00+00:00",
      "timestamp": "2025-12-31 04:45:00+00:00",
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
      "previous_timestamp": "2025-12-31 05:30:00+00:00",
      "timestamp": "2025-12-31 05:45:00+00:00",
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
      "previous_timestamp": "2025-12-31 05:30:00+00:00",
      "timestamp": "2025-12-31 05:45:00+00:00",
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
      "previous_timestamp": "2025-12-31 07:15:00+00:00",
      "timestamp": "2025-12-31 07:30:00+00:00",
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
      "previous_timestamp": "2025-12-31 07:15:00+00:00",
      "timestamp": "2025-12-31 07:30:00+00:00",
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
      "previous_timestamp": "2025-12-31 09:15:00+00:00",
      "timestamp": "2025-12-31 09:30:00+00:00",
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
      "previous_timestamp": "2025-12-31 09:15:00+00:00",
      "timestamp": "2025-12-31 09:30:00+00:00",
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
      "previous_timestamp": "2025-12-31 11:00:00+00:00",
      "timestamp": "2025-12-31 11:15:00+00:00",
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
      "previous_timestamp": "2025-12-31 11:00:00+00:00",
      "timestamp": "2025-12-31 11:15:00+00:00",
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
      "previous_timestamp": "2025-12-31 13:15:00+00:00",
      "timestamp": "2025-12-31 13:30:00+00:00",
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
      "previous_timestamp": "2025-12-31 13:15:00+00:00",
      "timestamp": "2025-12-31 13:30:00+00:00",
      "trend_context_evaluated": false,
      "follow_through_evaluated": false
    }
  }
]
```
### Morning/evening star candidates
```json
[
  {
    "source": "NISON",
    "code": "MORNING_STAR_LIKE_CONTEXT",
    "description": "Morning-star-like three-candle geometry",
    "contribution": 0.0,
    "metadata": {
      "timestamps": [
        "2025-12-31 03:15:00+00:00",
        "2025-12-31 03:30:00+00:00",
        "2025-12-31 03:45:00+00:00"
      ],
      "trend_context_evaluated": false,
      "follow_through_evaluated": false,
      "catalog_scope": "NISON_CHAPTERS_4_TO_8"
    }
  }
]
```
### Candle context conclusion
SMALL_BODY_INDECISION, CLOSE_NEAR_HIGH, LONG_LOWER_SHADOW_REJECTION, DOJI_INDECISION, STRONG_BULLISH_CANDLE_BODY, LONG_UPPER_SHADOW_REJECTION, SPINNING_TOP_INDECISION, STRONG_BEARISH_CANDLE_BODY, CLOSE_NEAR_LOW, HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED, CANDLE_PATTERN_NEEDS_TREND_CONTEXT, SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED, BULLISH_ENGULFING_CONTEXT, ENGULFING_WITHOUT_FOLLOW_THROUGH, BEARISH_ENGULFING_CONTEXT, BULLISH_BELT_HOLD_CONTEXT_REQUIRED, BEARISH_BELT_HOLD_CONTEXT_REQUIRED, HANGING_MAN_LIKE_CONTEXT_REQUIRED, REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH, LONG_LEGGED_DOJI_CONTEXT, RICKSHAW_MAN_DOJI_CONTEXT, INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED, GRAVESTONE_DOJI_CONTEXT, TWEEZERS_BOTTOM_CONTEXT_REQUIRED, BULLISH_SEPARATING_LINES_CONTEXT, DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT, DOJI_TOP_CONTEXT_REQUIRED, TWEEZERS_TOP_CONTEXT_REQUIRED, BULLISH_HARAMI_CONTEXT, HARAMI_CROSS_CONTEXT, BEARISH_HARAMI_CONTEXT, BEARISH_SEPARATING_LINES_CONTEXT, MORNING_STAR_LIKE_CONTEXT, THREE_ADVANCING_WHITE_SOLDIERS_CONTEXT, THREE_MOUNTAINS_CONTEXT_REQUIRED, THREE_BUDDHA_TOP_CONTEXT_REQUIRED

## 2. Altunina trend context
### Swing structure
```json
[
  {
    "index": 2,
    "timestamp": "2025-12-31 00:30:00+00:00",
    "price": 124.41,
    "point_type": "LOW"
  },
  {
    "index": 6,
    "timestamp": "2025-12-31 01:30:00+00:00",
    "price": 125.95,
    "point_type": "HIGH"
  },
  {
    "index": 8,
    "timestamp": "2025-12-31 02:00:00+00:00",
    "price": 125.32,
    "point_type": "LOW"
  },
  {
    "index": 9,
    "timestamp": "2025-12-31 02:15:00+00:00",
    "price": 125.95,
    "point_type": "HIGH"
  },
  {
    "index": 14,
    "timestamp": "2025-12-31 03:30:00+00:00",
    "price": 125.17,
    "point_type": "LOW"
  },
  {
    "index": 16,
    "timestamp": "2025-12-31 04:00:00+00:00",
    "price": 125.96,
    "point_type": "HIGH"
  },
  {
    "index": 20,
    "timestamp": "2025-12-31 05:00:00+00:00",
    "price": 125.41,
    "point_type": "LOW"
  },
  {
    "index": 27,
    "timestamp": "2025-12-31 06:45:00+00:00",
    "price": 126.1,
    "point_type": "HIGH"
  },
  {
    "index": 29,
    "timestamp": "2025-12-31 07:15:00+00:00",
    "price": 125.65,
    "point_type": "LOW"
  },
  {
    "index": 32,
    "timestamp": "2025-12-31 08:00:00+00:00",
    "price": 126.3,
    "point_type": "HIGH"
  },
  {
    "index": 35,
    "timestamp": "2025-12-31 08:45:00+00:00",
    "price": 125.44,
    "point_type": "LOW"
  },
  {
    "index": 40,
    "timestamp": "2025-12-31 10:00:00+00:00",
    "price": 126.42,
    "point_type": "HIGH"
  },
  {
    "index": 41,
    "timestamp": "2025-12-31 10:15:00+00:00",
    "price": 126.0,
    "point_type": "LOW"
  },
  {
    "index": 46,
    "timestamp": "2025-12-31 11:30:00+00:00",
    "price": 126.85,
    "point_type": "HIGH"
  },
  {
    "index": 52,
    "timestamp": "2025-12-31 13:00:00+00:00",
    "price": 126.03,
    "point_type": "LOW"
  },
  {
    "index": 53,
    "timestamp": "2025-12-31 13:15:00+00:00",
    "price": 126.51,
    "point_type": "HIGH"
  },
  {
    "index": 54,
    "timestamp": "2025-12-31 13:30:00+00:00",
    "price": 125.95,
    "point_type": "LOW"
  },
  {
    "index": 56,
    "timestamp": "2025-12-31 14:00:00+00:00",
    "price": 127.44,
    "point_type": "HIGH"
  },
  {
    "index": 62,
    "timestamp": "2025-12-31 15:30:00+00:00",
    "price": 125.01,
    "point_type": "LOW"
  },
  {
    "index": 63,
    "timestamp": "2025-12-31 15:45:00+00:00",
    "price": 125.82,
    "point_type": "HIGH"
  },
  {
    "index": 66,
    "timestamp": "2025-12-31 16:30:00+00:00",
    "price": 124.31,
    "point_type": "LOW"
  },
  {
    "index": 73,
    "timestamp": "2025-12-31 18:15:00+00:00",
    "price": 125.53,
    "point_type": "HIGH"
  },
  {
    "index": 75,
    "timestamp": "2025-12-31 18:45:00+00:00",
    "price": 124.64,
    "point_type": "LOW"
  },
  {
    "index": 81,
    "timestamp": "2025-12-31 20:15:00+00:00",
    "price": 132.75,
    "point_type": "HIGH"
  },
  {
    "index": 82,
    "timestamp": "2025-12-31 20:30:00+00:00",
    "price": 122.99,
    "point_type": "LOW"
  },
  {
    "index": 84,
    "timestamp": "2025-12-31 21:00:00+00:00",
    "price": 124.48,
    "point_type": "HIGH"
  },
  {
    "index": 86,
    "timestamp": "2025-12-31 21:30:00+00:00",
    "price": 123.98,
    "point_type": "LOW"
  },
  {
    "index": 89,
    "timestamp": "2025-12-31 22:15:00+00:00",
    "price": 125.16,
    "point_type": "HIGH"
  },
  {
    "index": 91,
    "timestamp": "2025-12-31 22:45:00+00:00",
    "price": 124.73,
    "point_type": "LOW"
  },
  {
    "index": 93,
    "timestamp": "2025-12-31 23:15:00+00:00",
    "price": 125.05,
    "point_type": "HIGH"
  }
]
```
### Higher highs / lower highs
```json
{
  "raw_swing_count": 39,
  "swing_count": 30,
  "leg_count": 29,
  "structure_direction": "SIDEWAYS_STRUCTURE",
  "total_movement": 41.81999999999995,
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
    "lower_price": 125.01,
    "upper_price": 125.53,
    "mid_price": 125.22833333333334,
    "touch_count": 12,
    "source_indexes": [
      2,
      8,
      10,
      14,
      20,
      35,
      60,
      62,
      69,
      73,
      89,
      93
    ],
    "zone_width": 0.519999999999996,
    "zone_width_ratio": 0.004152414922075643,
    "formed_at_index": 93,
    "first_touch_index": 2,
    "last_touch_index": 93,
    "source_point_types": [
      "HIGH",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "HIGH",
      "HIGH",
      "HIGH",
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
    "lower_price": 125.65,
    "upper_price": 126.3,
    "mid_price": 125.96384615384615,
    "touch_count": 13,
    "source_indexes": [
      6,
      9,
      16,
      18,
      27,
      29,
      30,
      32,
      36,
      41,
      52,
      54,
      63
    ],
    "zone_width": 0.6499999999999915,
    "zone_width_ratio": 0.005160210805298156,
    "formed_at_index": 63,
    "first_touch_index": 6,
    "last_touch_index": 63,
    "source_point_types": [
      "HIGH",
      "HIGH",
      "HIGH",
      "HIGH",
      "HIGH",
      "LOW",
      "HIGH",
      "HIGH",
      "HIGH",
      "LOW",
      "LOW",
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
  "lower_boundary": 125.01,
  "upper_boundary": 126.3,
  "midline": 125.655,
  "width": 1.289999999999992,
  "width_ratio": 0.010266205085352689,
  "touch_count": 25,
  "inside_close_ratio": 0.6304347826086957,
  "formed_at_index": 93,
  "first_touch_index": 2,
  "duration_candles": 92,
  "boundary_alternation_count": 12
}
```
### Range high / low
See trading range object above.
### Price position inside range
```json
{
  "swing_count": 39,
  "zone_count": 6,
  "range_detected": true,
  "range_formed_at_index": 93,
  "range_duration_candles": 92,
  "inside_close_ratio": 0.6304347826086957,
  "breakout_direction": "DOWNWARD",
  "breakout_status": "ATTEMPT",
  "polarity_status": "NONE"
}
```
### Breakout / breakdown attempts
```json
{
  "direction": "DOWNWARD",
  "status": "ATTEMPT",
  "breakout_index": 94,
  "boundary_price": 125.01,
  "breakout_close": 124.79,
  "distance_ratio": 0.0017598592112630898,
  "returned_to_range": false,
  "follow_through_count": 1,
  "evidence": [
    {
      "source": "SCHWAGER",
      "code": "SCHWAGER_BEARISH_RANGE_BREAKDOWN_CONTEXT",
      "description": "Closing price moved below the range boundary",
      "contribution": -0.12,
      "metadata": {
        "breakout_index": 94
      }
    },
    {
      "source": "SCHWAGER",
      "code": "SCHWAGER_BREAKOUT_REQUIRES_CONFIRMATION",
      "description": "Boundary movement requires confirmation",
      "contribution": 0.0,
      "metadata": {}
    }
  ],
  "analysis_start_index": 94,
  "confirmation_method": "NONE",
  "confirmation_close_count": 2,
  "extreme_index": 95,
  "extreme_price": 124.6,
  "maximum_distance_ratio": 0.003279737620990407,
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
SCHWAGER_SUPPORT_ZONE_IDENTIFIED, SCHWAGER_PREVIOUS_EXTREME_ZONE_IDENTIFIED, SCHWAGER_SUPPORT_ZONE_HELD, SCHWAGER_ZONE_TOO_WIDE, SCHWAGER_RESISTANCE_ZONE_IDENTIFIED, SCHWAGER_RESISTANCE_ZONE_HELD, SCHWAGER_TRADING_RANGE_DETECTED, SCHWAGER_PRICE_INSIDE_RANGE, SCHWAGER_RANGE_UPPER_BOUNDARY_HELD, SCHWAGER_RANGE_LOWER_BOUNDARY_HELD, SCHWAGER_RANGE_DURATION_CONFIRMED, SCHWAGER_RANGE_BOUNDARY_ALTERNATION_CONFIRMED, SCHWAGER_BEARISH_RANGE_BREAKDOWN_CONTEXT, SCHWAGER_BREAKOUT_REQUIRES_CONFIRMATION

## 4. BookEvidenceMatrix
### Bullish evidence
Count: 33
### Bearish evidence
Count: 25
### Neutral/range evidence
Count: 316
### Conflict
```json
{
  "agreement_state": "MIXED_WITH_CONFLICT",
  "conflict_level": "MEDIUM",
  "coverage_level": "HIGH",
  "aligned_sources": [],
  "conflicting_sources": [
    "NISON",
    "SCHWAGER"
  ],
  "missing_sources": [],
  "confluence_score": 0.0,
  "conflict_score": 1.0,
  "coverage_score": 1.0,
  "reason_codes": [
    "MATRIX_HIGH_EVIDENCE_COVERAGE",
    "MATRIX_NISON_SCHWAGER_CONFLICT",
    "MATRIX_DIRECTIONAL_CONFLICT_MEDIUM",
    "MATRIX_MIXED_BOOK_CONTEXT",
    "MATRIX_READY_FOR_REGIME_COMPOSER"
  ]
}
```
### Coverage
```json
{
  "active_source_count": 3,
  "total_evidence_count": 374,
  "dominant_direction": "BULLISH",
  "agreement_state": "MIXED_WITH_CONFLICT",
  "conflict_level": "MEDIUM",
  "coverage_level": "HIGH",
  "confluence_score": 0.0,
  "conflict_score": 1.0,
  "coverage_score": 1.0,
  "ready_for_composer": true
}
```
### Matrix conclusion
MIXED_WITH_CONFLICT

## 5. Composer decision
### Raw scores
Not exposed by current trace.
### Clamped scores
```json
{
  "UP": 1.0,
  "DOWN": 1.0,
  "FLAT": 0.5260869565217392,
  "UNKNOWN": 0.25
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
    "score": 0.5260869565217392
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
