# solusdt_15m_flat_003 вЂ” Market Evidence Trace

## Window
- Symbol: SOLUSDT
- Interval: 15m
- Period: 2026-04-24T00:00:00+00:00 вЂ” 2026-04-24T23:45:00+00:00
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
    "timestamp": "2026-04-24 00:00:00+00:00",
    "candle_index": 0,
    "open": 86.12,
    "high": 86.18,
    "low": 86.04,
    "close": 86.09,
    "body_pct": 0.21428571428572155,
    "upper_shadow_pct": 0.4285714285714431,
    "lower_shadow_pct": 0.3571428571428354,
    "position_in_window": 0.0,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2026-04-24 00:30:00+00:00",
    "candle_index": 2,
    "open": 86.21,
    "high": 86.33,
    "low": 86.15,
    "close": 86.15,
    "body_pct": 0.3333333333332807,
    "upper_shadow_pct": 0.6666666666667193,
    "lower_shadow_pct": 0.0,
    "position_in_window": 0.0211,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-04-24 00:45:00+00:00",
    "candle_index": 3,
    "open": 86.15,
    "high": 86.29,
    "low": 86.12,
    "close": 86.19,
    "body_pct": 0.23529411764700964,
    "upper_shadow_pct": 0.5882352941176913,
    "lower_shadow_pct": 0.17647058823529904,
    "position_in_window": 0.0316,
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
    "timestamp": "2026-04-24 01:00:00+00:00",
    "candle_index": 4,
    "open": 86.19,
    "high": 86.2,
    "low": 85.87,
    "close": 85.93,
    "body_pct": 0.7878787878787644,
    "upper_shadow_pct": 0.03030303030304596,
    "lower_shadow_pct": 0.18181818181818965,
    "position_in_window": 0.0421,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-04-24 01:15:00+00:00",
    "candle_index": 5,
    "open": 85.93,
    "high": 85.97,
    "low": 85.83,
    "close": 85.93,
    "body_pct": 0.0,
    "upper_shadow_pct": 0.2857142857142277,
    "lower_shadow_pct": 0.7142857142857723,
    "position_in_window": 0.0526,
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
    "timestamp": "2026-04-24 01:30:00+00:00",
    "candle_index": 6,
    "open": 85.92,
    "high": 86.02,
    "low": 85.82,
    "close": 85.92,
    "body_pct": 0.0,
    "upper_shadow_pct": 0.4999999999999645,
    "lower_shadow_pct": 0.5000000000000355,
    "position_in_window": 0.0632,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "DOJI_INDECISION"
    ]
  },
  {
    "timestamp": "2026-04-24 01:45:00+00:00",
    "candle_index": 7,
    "open": 85.92,
    "high": 86.32,
    "low": 85.91,
    "close": 86.28,
    "body_pct": 0.8780487804878108,
    "upper_shadow_pct": 0.0975609756097375,
    "lower_shadow_pct": 0.024390243902451706,
    "position_in_window": 0.0737,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-04-24 02:00:00+00:00",
    "candle_index": 8,
    "open": 86.28,
    "high": 86.36,
    "low": 86.1,
    "close": 86.15,
    "body_pct": 0.4999999999999727,
    "upper_shadow_pct": 0.30769230769229505,
    "lower_shadow_pct": 0.19230769230773226,
    "position_in_window": 0.0842,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-04-24 02:15:00+00:00",
    "candle_index": 9,
    "open": 86.15,
    "high": 86.2,
    "low": 86.01,
    "close": 86.02,
    "body_pct": 0.6842105263158486,
    "upper_shadow_pct": 0.2631578947368303,
    "lower_shadow_pct": 0.052631578947321185,
    "position_in_window": 0.0947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-04-24 02:30:00+00:00",
    "candle_index": 10,
    "open": 86.03,
    "high": 86.11,
    "low": 86.02,
    "close": 86.1,
    "body_pct": 0.7777777777776725,
    "upper_shadow_pct": 0.11111111111116374,
    "lower_shadow_pct": 0.11111111111116374,
    "position_in_window": 0.1053,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-04-24 03:00:00+00:00",
    "candle_index": 12,
    "open": 85.89,
    "high": 85.94,
    "low": 85.83,
    "close": 85.89,
    "body_pct": 0.0,
    "upper_shadow_pct": 0.45454545454543105,
    "lower_shadow_pct": 0.545454545454569,
    "position_in_window": 0.1263,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "DOJI_INDECISION"
    ]
  },
  {
    "timestamp": "2026-04-24 03:45:00+00:00",
    "candle_index": 15,
    "open": 85.49,
    "high": 85.72,
    "low": 85.48,
    "close": 85.69,
    "body_pct": 0.8333333333333629,
    "upper_shadow_pct": 0.1250000000000074,
    "lower_shadow_pct": 0.04166666666662966,
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
    "timestamp": "2026-04-24 04:15:00+00:00",
    "candle_index": 17,
    "open": 85.6,
    "high": 85.71,
    "low": 85.41,
    "close": 85.45,
    "body_pct": 0.4999999999999763,
    "upper_shadow_pct": 0.36666666666666825,
    "lower_shadow_pct": 0.13333333333335545,
    "position_in_window": 0.1789,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-04-24 04:45:00+00:00",
    "candle_index": 19,
    "open": 85.33,
    "high": 85.46,
    "low": 85.3,
    "close": 85.32,
    "body_pct": 0.0625000000000333,
    "upper_shadow_pct": 0.8124999999999889,
    "lower_shadow_pct": 0.1249999999999778,
    "position_in_window": 0.2,
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
    "timestamp": "2026-04-24 05:00:00+00:00",
    "candle_index": 20,
    "open": 85.31,
    "high": 85.4,
    "low": 85.15,
    "close": 85.34,
    "body_pct": 0.12000000000000455,
    "upper_shadow_pct": 0.2400000000000091,
    "lower_shadow_pct": 0.6399999999999864,
    "position_in_window": 0.2105,
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
    "timestamp": "2026-04-24 05:15:00+00:00",
    "candle_index": 21,
    "open": 85.34,
    "high": 85.42,
    "low": 85.16,
    "close": 85.35,
    "body_pct": 0.03846153846150272,
    "upper_shadow_pct": 0.26923076923079237,
    "lower_shadow_pct": 0.692307692307705,
    "position_in_window": 0.2211,
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
    "timestamp": "2026-04-24 05:30:00+00:00",
    "candle_index": 22,
    "open": 85.36,
    "high": 85.49,
    "low": 85.23,
    "close": 85.45,
    "body_pct": 0.3461538461538714,
    "upper_shadow_pct": 0.15384615384612862,
    "lower_shadow_pct": 0.5,
    "position_in_window": 0.2316,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-04-24 06:00:00+00:00",
    "candle_index": 24,
    "open": 85.7,
    "high": 85.73,
    "low": 85.59,
    "close": 85.69,
    "body_pct": 0.07142857142860769,
    "upper_shadow_pct": 0.21428571428572155,
    "lower_shadow_pct": 0.7142857142856708,
    "position_in_window": 0.2526,
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
    "timestamp": "2026-04-24 06:15:00+00:00",
    "candle_index": 25,
    "open": 85.68,
    "high": 85.7,
    "low": 85.49,
    "close": 85.64,
    "body_pct": 0.19047619047621303,
    "upper_shadow_pct": 0.09523809523807268,
    "lower_shadow_pct": 0.7142857142857143,
    "position_in_window": 0.2632,
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
    "timestamp": "2026-04-24 06:45:00+00:00",
    "candle_index": 27,
    "open": 85.43,
    "high": 85.54,
    "low": 85.39,
    "close": 85.44,
    "body_pct": 0.06666666666660351,
    "upper_shadow_pct": 0.6666666666666983,
    "lower_shadow_pct": 0.26666666666669825,
    "position_in_window": 0.2842,
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
    "timestamp": "2026-04-24 07:00:00+00:00",
    "candle_index": 28,
    "open": 85.44,
    "high": 85.62,
    "low": 85.42,
    "close": 85.5,
    "body_pct": 0.3000000000000071,
    "upper_shadow_pct": 0.6000000000000142,
    "lower_shadow_pct": 0.09999999999997869,
    "position_in_window": 0.2947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2026-04-24 07:30:00+00:00",
    "candle_index": 30,
    "open": 85.45,
    "high": 85.48,
    "low": 85.34,
    "close": 85.42,
    "body_pct": 0.21428571428572155,
    "upper_shadow_pct": 0.21428571428572155,
    "lower_shadow_pct": 0.571428571428557,
    "position_in_window": 0.3158,
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
    "timestamp": "2026-04-24 08:45:00+00:00",
    "candle_index": 35,
    "open": 85.41,
    "high": 85.52,
    "low": 85.31,
    "close": 85.34,
    "body_pct": 0.3333333333333108,
    "upper_shadow_pct": 0.5238095238095367,
    "lower_shadow_pct": 0.14285714285715254,
    "position_in_window": 0.3684,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-04-24 09:15:00+00:00",
    "candle_index": 37,
    "open": 85.13,
    "high": 85.22,
    "low": 85.05,
    "close": 85.17,
    "body_pct": 0.23529411764709324,
    "upper_shadow_pct": 0.29411764705880383,
    "lower_shadow_pct": 0.4705882352941029,
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
    "timestamp": "2026-04-24 09:30:00+00:00",
    "candle_index": 38,
    "open": 85.17,
    "high": 85.34,
    "low": 85.16,
    "close": 85.34,
    "body_pct": 0.9444444444444181,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.05555555555558187,
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
    "timestamp": "2026-04-24 09:45:00+00:00",
    "candle_index": 39,
    "open": 85.33,
    "high": 85.48,
    "low": 85.18,
    "close": 85.48,
    "body_pct": 0.5000000000000236,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.4999999999999763,
    "position_in_window": 0.4105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-04-24 10:30:00+00:00",
    "candle_index": 42,
    "open": 85.51,
    "high": 85.63,
    "low": 85.5,
    "close": 85.54,
    "body_pct": 0.23076923076924757,
    "upper_shadow_pct": 0.6923076923076334,
    "lower_shadow_pct": 0.07692307692311896,
    "position_in_window": 0.4421,
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
    "timestamp": "2026-04-24 10:45:00+00:00",
    "candle_index": 43,
    "open": 85.55,
    "high": 85.76,
    "low": 85.5,
    "close": 85.71,
    "body_pct": 0.6153846153845901,
    "upper_shadow_pct": 0.19230769230773226,
    "lower_shadow_pct": 0.19230769230767758,
    "position_in_window": 0.4526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-04-24 11:00:00+00:00",
    "candle_index": 44,
    "open": 85.72,
    "high": 86.15,
    "low": 85.71,
    "close": 86.07,
    "body_pct": 0.795454545454511,
    "upper_shadow_pct": 0.1818181818182053,
    "lower_shadow_pct": 0.022727272727283736,
    "position_in_window": 0.4632,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-04-24 11:15:00+00:00",
    "candle_index": 45,
    "open": 86.07,
    "high": 86.25,
    "low": 85.93,
    "close": 86.25,
    "body_pct": 0.5625000000000333,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.4374999999999667,
    "position_in_window": 0.4737,
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
  "doji_count": 11,
  "doji_ratio": 0.11458333333333333,
  "small_body_count": 33,
  "small_body_ratio": 0.34375,
  "bullish_body_total": 6.009999999999977,
  "bearish_body_total": 5.969999999999956
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
      "previous_timestamp": "2026-04-24 00:00:00+00:00",
      "timestamp": "2026-04-24 00:15:00+00:00",
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
      "previous_timestamp": "2026-04-24 00:00:00+00:00",
      "timestamp": "2026-04-24 00:15:00+00:00",
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
      "previous_timestamp": "2026-04-24 00:45:00+00:00",
      "timestamp": "2026-04-24 01:00:00+00:00",
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
      "previous_timestamp": "2026-04-24 00:45:00+00:00",
      "timestamp": "2026-04-24 01:00:00+00:00",
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
      "previous_timestamp": "2026-04-24 02:30:00+00:00",
      "timestamp": "2026-04-24 02:45:00+00:00",
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
      "previous_timestamp": "2026-04-24 02:30:00+00:00",
      "timestamp": "2026-04-24 02:45:00+00:00",
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
      "previous_timestamp": "2026-04-24 03:30:00+00:00",
      "timestamp": "2026-04-24 03:45:00+00:00",
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
      "previous_timestamp": "2026-04-24 03:30:00+00:00",
      "timestamp": "2026-04-24 03:45:00+00:00",
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
      "previous_timestamp": "2026-04-24 04:45:00+00:00",
      "timestamp": "2026-04-24 05:00:00+00:00",
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
      "previous_timestamp": "2026-04-24 04:45:00+00:00",
      "timestamp": "2026-04-24 05:00:00+00:00",
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
      "previous_timestamp": "2026-04-24 07:00:00+00:00",
      "timestamp": "2026-04-24 07:15:00+00:00",
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
      "previous_timestamp": "2026-04-24 07:00:00+00:00",
      "timestamp": "2026-04-24 07:15:00+00:00",
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
      "previous_timestamp": "2026-04-24 07:30:00+00:00",
      "timestamp": "2026-04-24 07:45:00+00:00",
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
      "previous_timestamp": "2026-04-24 07:30:00+00:00",
      "timestamp": "2026-04-24 07:45:00+00:00",
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
      "previous_timestamp": "2026-04-24 08:00:00+00:00",
      "timestamp": "2026-04-24 08:15:00+00:00",
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
      "previous_timestamp": "2026-04-24 08:00:00+00:00",
      "timestamp": "2026-04-24 08:15:00+00:00",
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
      "previous_timestamp": "2026-04-24 13:00:00+00:00",
      "timestamp": "2026-04-24 13:15:00+00:00",
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
      "previous_timestamp": "2026-04-24 13:00:00+00:00",
      "timestamp": "2026-04-24 13:15:00+00:00",
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
      "previous_timestamp": "2026-04-24 14:15:00+00:00",
      "timestamp": "2026-04-24 14:30:00+00:00",
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
      "previous_timestamp": "2026-04-24 14:15:00+00:00",
      "timestamp": "2026-04-24 14:30:00+00:00",
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
SMALL_BODY_INDECISION, SPINNING_TOP_INDECISION, LONG_UPPER_SHADOW_REJECTION, CLOSE_NEAR_LOW, STRONG_BEARISH_CANDLE_BODY, LONG_LOWER_SHADOW_REJECTION, DOJI_INDECISION, STRONG_BULLISH_CANDLE_BODY, CLOSE_NEAR_HIGH, HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED, CANDLE_PATTERN_NEEDS_TREND_CONTEXT, SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED, BULLISH_ENGULFING_CONTEXT, ENGULFING_WITHOUT_FOLLOW_THROUGH, BEARISH_ENGULFING_CONTEXT, BEARISH_BELT_HOLD_CONTEXT_REQUIRED, LONG_LEGGED_DOJI_CONTEXT, RICKSHAW_MAN_DOJI_CONTEXT, BULLISH_BELT_HOLD_CONTEXT_REQUIRED, HANGING_MAN_LIKE_CONTEXT_REQUIRED, REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH, INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED, TWEEZERS_BOTTOM_CONTEXT_REQUIRED, BULLISH_HARAMI_CONTEXT, HARAMI_CROSS_CONTEXT, BEARISH_HARAMI_CONTEXT, DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT, DOJI_TOP_CONTEXT_REQUIRED, TWEEZERS_TOP_CONTEXT_REQUIRED, THREE_ADVANCING_WHITE_SOLDIERS_CONTEXT

## 2. Altunina trend context
### Swing structure
```json
[
  {
    "index": 1,
    "timestamp": "2026-04-24 00:15:00+00:00",
    "price": 86.36,
    "point_type": "HIGH"
  },
  {
    "index": 6,
    "timestamp": "2026-04-24 01:30:00+00:00",
    "price": 85.82,
    "point_type": "LOW"
  },
  {
    "index": 8,
    "timestamp": "2026-04-24 02:00:00+00:00",
    "price": 86.36,
    "point_type": "HIGH"
  },
  {
    "index": 14,
    "timestamp": "2026-04-24 03:30:00+00:00",
    "price": 85.4,
    "point_type": "LOW"
  },
  {
    "index": 15,
    "timestamp": "2026-04-24 03:45:00+00:00",
    "price": 85.72,
    "point_type": "HIGH"
  },
  {
    "index": 18,
    "timestamp": "2026-04-24 04:30:00+00:00",
    "price": 85.14,
    "point_type": "LOW"
  },
  {
    "index": 23,
    "timestamp": "2026-04-24 05:45:00+00:00",
    "price": 85.82,
    "point_type": "HIGH"
  },
  {
    "index": 26,
    "timestamp": "2026-04-24 06:30:00+00:00",
    "price": 85.33,
    "point_type": "LOW"
  },
  {
    "index": 28,
    "timestamp": "2026-04-24 07:00:00+00:00",
    "price": 85.62,
    "point_type": "HIGH"
  },
  {
    "index": 30,
    "timestamp": "2026-04-24 07:30:00+00:00",
    "price": 85.34,
    "point_type": "LOW"
  },
  {
    "index": 31,
    "timestamp": "2026-04-24 07:45:00+00:00",
    "price": 85.56,
    "point_type": "HIGH"
  },
  {
    "index": 32,
    "timestamp": "2026-04-24 08:00:00+00:00",
    "price": 85.29,
    "point_type": "LOW"
  },
  {
    "index": 33,
    "timestamp": "2026-04-24 08:15:00+00:00",
    "price": 85.73,
    "point_type": "HIGH"
  },
  {
    "index": 36,
    "timestamp": "2026-04-24 09:00:00+00:00",
    "price": 84.92,
    "point_type": "LOW"
  },
  {
    "index": 46,
    "timestamp": "2026-04-24 11:30:00+00:00",
    "price": 86.28,
    "point_type": "HIGH"
  },
  {
    "index": 47,
    "timestamp": "2026-04-24 11:45:00+00:00",
    "price": 86.04,
    "point_type": "LOW"
  },
  {
    "index": 49,
    "timestamp": "2026-04-24 12:15:00+00:00",
    "price": 86.79,
    "point_type": "HIGH"
  },
  {
    "index": 51,
    "timestamp": "2026-04-24 12:45:00+00:00",
    "price": 86.06,
    "point_type": "LOW"
  },
  {
    "index": 52,
    "timestamp": "2026-04-24 13:00:00+00:00",
    "price": 86.6,
    "point_type": "HIGH"
  },
  {
    "index": 57,
    "timestamp": "2026-04-24 14:15:00+00:00",
    "price": 85.67,
    "point_type": "LOW"
  },
  {
    "index": 58,
    "timestamp": "2026-04-24 14:30:00+00:00",
    "price": 86.23,
    "point_type": "HIGH"
  },
  {
    "index": 60,
    "timestamp": "2026-04-24 15:00:00+00:00",
    "price": 85.53,
    "point_type": "LOW"
  },
  {
    "index": 64,
    "timestamp": "2026-04-24 16:00:00+00:00",
    "price": 86.58,
    "point_type": "HIGH"
  },
  {
    "index": 66,
    "timestamp": "2026-04-24 16:30:00+00:00",
    "price": 86.09,
    "point_type": "LOW"
  },
  {
    "index": 68,
    "timestamp": "2026-04-24 17:00:00+00:00",
    "price": 86.55,
    "point_type": "HIGH"
  },
  {
    "index": 70,
    "timestamp": "2026-04-24 17:30:00+00:00",
    "price": 86.12,
    "point_type": "LOW"
  },
  {
    "index": 71,
    "timestamp": "2026-04-24 17:45:00+00:00",
    "price": 86.56,
    "point_type": "HIGH"
  },
  {
    "index": 73,
    "timestamp": "2026-04-24 18:15:00+00:00",
    "price": 85.95,
    "point_type": "LOW"
  },
  {
    "index": 74,
    "timestamp": "2026-04-24 18:30:00+00:00",
    "price": 86.46,
    "point_type": "HIGH"
  },
  {
    "index": 78,
    "timestamp": "2026-04-24 19:30:00+00:00",
    "price": 86.25,
    "point_type": "LOW"
  },
  {
    "index": 80,
    "timestamp": "2026-04-24 20:00:00+00:00",
    "price": 86.55,
    "point_type": "HIGH"
  },
  {
    "index": 81,
    "timestamp": "2026-04-24 20:15:00+00:00",
    "price": 86.22,
    "point_type": "LOW"
  },
  {
    "index": 84,
    "timestamp": "2026-04-24 21:00:00+00:00",
    "price": 86.94,
    "point_type": "HIGH"
  },
  {
    "index": 93,
    "timestamp": "2026-04-24 23:15:00+00:00",
    "price": 86.15,
    "point_type": "LOW"
  },
  {
    "index": 94,
    "timestamp": "2026-04-24 23:30:00+00:00",
    "price": 86.3,
    "point_type": "HIGH"
  }
]
```
### Higher highs / lower highs
```json
{
  "raw_swing_count": 46,
  "swing_count": 35,
  "leg_count": 34,
  "structure_direction": "SIDEWAYS_STRUCTURE",
  "total_movement": 18.719999999999914,
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
    "lower_price": 86.01,
    "upper_price": 86.47,
    "mid_price": 86.23055555555555,
    "touch_count": 18,
    "source_indexes": [
      1,
      8,
      9,
      11,
      46,
      47,
      51,
      58,
      66,
      66,
      70,
      74,
      76,
      78,
      81,
      86,
      93,
      94
    ],
    "zone_width": 0.45999999999999375,
    "zone_width_ratio": 0.0053345359662403035,
    "formed_at_index": 94,
    "first_touch_index": 1,
    "last_touch_index": 94,
    "source_point_types": [
      "HIGH",
      "HIGH",
      "LOW",
      "HIGH",
      "HIGH",
      "LOW",
      "LOW",
      "HIGH",
      "LOW",
      "HIGH",
      "LOW",
      "HIGH",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
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
    "lower_price": 86.53,
    "upper_price": 86.79,
    "mid_price": 86.5942857142857,
    "touch_count": 7,
    "source_indexes": [
      49,
      52,
      64,
      68,
      71,
      76,
      80
    ],
    "zone_width": 0.2600000000000051,
    "zone_width_ratio": 0.0030025075887555037,
    "formed_at_index": 80,
    "first_touch_index": 49,
    "last_touch_index": 80,
    "source_point_types": [
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
    "positional_zone_type": "RESISTANCE"
  },
  "is_detected": false,
  "lower_boundary": 86.01,
  "upper_boundary": 86.79,
  "midline": 86.4,
  "width": 0.7800000000000011,
  "width_ratio": 0.00902777777777779,
  "touch_count": 25,
  "inside_close_ratio": 0.574468085106383,
  "formed_at_index": 94,
  "first_touch_index": 1,
  "duration_candles": 94,
  "boundary_alternation_count": 14
}
```
### Range high / low
See trading range object above.
### Price position inside range
```json
{
  "swing_count": 46,
  "zone_count": 5,
  "range_detected": false,
  "range_formed_at_index": 94,
  "range_duration_candles": 94,
  "inside_close_ratio": 0.574468085106383,
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
SCHWAGER_SUPPORT_ZONE_IDENTIFIED, SCHWAGER_SUPPORT_ZONE_HELD, SCHWAGER_ZONE_TOO_WIDE, SCHWAGER_RESISTANCE_ZONE_IDENTIFIED, SCHWAGER_RESISTANCE_ZONE_HELD, SCHWAGER_RANGE_NOT_CONFIRMED

## 4. BookEvidenceMatrix
### Bullish evidence
Count: 35
### Bearish evidence
Count: 25
### Neutral/range evidence
Count: 307
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
  "total_evidence_count": 367,
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
