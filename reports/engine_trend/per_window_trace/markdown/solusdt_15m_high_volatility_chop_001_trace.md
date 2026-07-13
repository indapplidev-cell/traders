# solusdt_15m_high_volatility_chop_001 вЂ” Market Evidence Trace

## Window
- Symbol: SOLUSDT
- Interval: 15m
- Period: 2025-01-19T00:00:00+00:00 вЂ” 2025-01-19T23:45:00+00:00
- Reference label: HIGH_VOLATILITY_CHOP
- Selection reason: top deterministic HIGH_VOLATILITY_CHOP OHLC candidate

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
    "timestamp": "2025-01-19 00:00:00+00:00",
    "candle_index": 0,
    "open": 261.97,
    "high": 262.22,
    "low": 258.32,
    "close": 260.6,
    "body_pct": 0.35128205128204937,
    "upper_shadow_pct": 0.06410256410256354,
    "lower_shadow_pct": 0.5846153846153871,
    "position_in_window": 0.0,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2025-01-19 00:30:00+00:00",
    "candle_index": 2,
    "open": 263.85,
    "high": 264.85,
    "low": 261.01,
    "close": 261.7,
    "body_pct": 0.5598958333333376,
    "upper_shadow_pct": 0.2604166666666645,
    "lower_shadow_pct": 0.17968749999999792,
    "position_in_window": 0.0211,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-01-19 00:45:00+00:00",
    "candle_index": 3,
    "open": 261.71,
    "high": 262.41,
    "low": 256.33,
    "close": 256.6,
    "body_pct": 0.8404605263157767,
    "upper_shadow_pct": 0.11513157894737512,
    "lower_shadow_pct": 0.04440789473684816,
    "position_in_window": 0.0316,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-01-19 01:00:00+00:00",
    "candle_index": 4,
    "open": 256.6,
    "high": 257.67,
    "low": 255.21,
    "close": 256.27,
    "body_pct": 0.13414634146343082,
    "upper_shadow_pct": 0.43495934959349175,
    "lower_shadow_pct": 0.4308943089430774,
    "position_in_window": 0.0421,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2025-01-19 01:15:00+00:00",
    "candle_index": 5,
    "open": 256.27,
    "high": 257.02,
    "low": 253.75,
    "close": 255.89,
    "body_pct": 0.11620795107033564,
    "upper_shadow_pct": 0.2293577981651389,
    "lower_shadow_pct": 0.6544342507645254,
    "position_in_window": 0.0526,
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
    "timestamp": "2025-01-19 01:45:00+00:00",
    "candle_index": 7,
    "open": 254.27,
    "high": 255.94,
    "low": 253.87,
    "close": 255.56,
    "body_pct": 0.6231884057970997,
    "upper_shadow_pct": 0.18357487922705154,
    "lower_shadow_pct": 0.1932367149758488,
    "position_in_window": 0.0737,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-01-19 02:00:00+00:00",
    "candle_index": 8,
    "open": 255.57,
    "high": 258.02,
    "low": 255.07,
    "close": 257.72,
    "body_pct": 0.7288135593220483,
    "upper_shadow_pct": 0.10169491525422227,
    "lower_shadow_pct": 0.16949152542372947,
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
    "timestamp": "2025-01-19 02:15:00+00:00",
    "candle_index": 9,
    "open": 257.72,
    "high": 259.08,
    "low": 257.23,
    "close": 258.76,
    "body_pct": 0.5621621621621529,
    "upper_shadow_pct": 0.17297297297297248,
    "lower_shadow_pct": 0.26486486486487465,
    "position_in_window": 0.0947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-01-19 02:45:00+00:00",
    "candle_index": 11,
    "open": 257.52,
    "high": 258.1,
    "low": 253.5,
    "close": 254.37,
    "body_pct": 0.6847826086956439,
    "upper_shadow_pct": 0.1260869565217474,
    "lower_shadow_pct": 0.18913043478260874,
    "position_in_window": 0.1158,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-01-19 03:15:00+00:00",
    "candle_index": 13,
    "open": 253.08,
    "high": 254.42,
    "low": 252.6,
    "close": 253.23,
    "body_pct": 0.08241758241757023,
    "upper_shadow_pct": 0.6538461538461551,
    "lower_shadow_pct": 0.26373626373627473,
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
    "timestamp": "2025-01-19 03:45:00+00:00",
    "candle_index": 15,
    "open": 254.73,
    "high": 258.88,
    "low": 254.6,
    "close": 255.6,
    "body_pct": 0.2032710280373842,
    "upper_shadow_pct": 0.766355140186916,
    "lower_shadow_pct": 0.030373831775699862,
    "position_in_window": 0.1579,
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
    "timestamp": "2025-01-19 04:00:00+00:00",
    "candle_index": 16,
    "open": 255.6,
    "high": 265.0,
    "low": 254.17,
    "close": 264.19,
    "body_pct": 0.7931671283471832,
    "upper_shadow_pct": 0.07479224376731314,
    "lower_shadow_pct": 0.13204062788550372,
    "position_in_window": 0.1684,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-01-19 04:15:00+00:00",
    "candle_index": 17,
    "open": 264.19,
    "high": 269.55,
    "low": 259.66,
    "close": 268.35,
    "body_pct": 0.4206268958544015,
    "upper_shadow_pct": 0.1213346814964601,
    "lower_shadow_pct": 0.4580384226491384,
    "position_in_window": 0.1789,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-01-19 04:30:00+00:00",
    "candle_index": 18,
    "open": 268.34,
    "high": 271.8,
    "low": 264.1,
    "close": 269.58,
    "body_pct": 0.16103896103896245,
    "upper_shadow_pct": 0.2883116883116923,
    "lower_shadow_pct": 0.5506493506493453,
    "position_in_window": 0.1895,
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
    "timestamp": "2025-01-19 04:45:00+00:00",
    "candle_index": 19,
    "open": 269.58,
    "high": 275.0,
    "low": 269.16,
    "close": 273.69,
    "body_pct": 0.7037671232876765,
    "upper_shadow_pct": 0.22431506849315203,
    "lower_shadow_pct": 0.07191780821917138,
    "position_in_window": 0.2,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-01-19 05:00:00+00:00",
    "candle_index": 20,
    "open": 273.68,
    "high": 274.3,
    "low": 269.1,
    "close": 269.44,
    "body_pct": 0.8153846153846189,
    "upper_shadow_pct": 0.11923076923077036,
    "lower_shadow_pct": 0.06538461538461071,
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
    "timestamp": "2025-01-19 05:15:00+00:00",
    "candle_index": 21,
    "open": 269.44,
    "high": 272.41,
    "low": 267.34,
    "close": 272.08,
    "body_pct": 0.5207100591715899,
    "upper_shadow_pct": 0.06508875739645713,
    "lower_shadow_pct": 0.41420118343195306,
    "position_in_window": 0.2211,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-01-19 05:30:00+00:00",
    "candle_index": 22,
    "open": 272.09,
    "high": 272.98,
    "low": 267.78,
    "close": 268.05,
    "body_pct": 0.7769230769230632,
    "upper_shadow_pct": 0.17115384615385296,
    "lower_shadow_pct": 0.0519230769230839,
    "position_in_window": 0.2316,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-01-19 06:15:00+00:00",
    "candle_index": 25,
    "open": 268.87,
    "high": 271.38,
    "low": 267.32,
    "close": 271.35,
    "body_pct": 0.6108374384236495,
    "upper_shadow_pct": 0.0073891625615696305,
    "lower_shadow_pct": 0.3817733990147809,
    "position_in_window": 0.2632,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-01-19 06:30:00+00:00",
    "candle_index": 26,
    "open": 271.35,
    "high": 272.14,
    "low": 269.06,
    "close": 271.98,
    "body_pct": 0.20454545454545411,
    "upper_shadow_pct": 0.05194805194804188,
    "lower_shadow_pct": 0.743506493506504,
    "position_in_window": 0.2737,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
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
    "timestamp": "2025-01-19 06:45:00+00:00",
    "candle_index": 27,
    "open": 271.98,
    "high": 274.9,
    "low": 270.16,
    "close": 274.68,
    "body_pct": 0.5696202531645603,
    "upper_shadow_pct": 0.04641350210969887,
    "lower_shadow_pct": 0.3839662447257408,
    "position_in_window": 0.2842,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-01-19 07:00:00+00:00",
    "candle_index": 28,
    "open": 274.68,
    "high": 276.79,
    "low": 271.85,
    "close": 274.7,
    "body_pct": 0.004048582995947737,
    "upper_shadow_pct": 0.42307692307692973,
    "lower_shadow_pct": 0.5728744939271225,
    "position_in_window": 0.2947,
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
    "timestamp": "2025-01-19 07:15:00+00:00",
    "candle_index": 29,
    "open": 274.7,
    "high": 277.99,
    "low": 272.82,
    "close": 275.42,
    "body_pct": 0.13926499032882497,
    "upper_shadow_pct": 0.4970986460348134,
    "lower_shadow_pct": 0.36363636363636165,
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
    "timestamp": "2025-01-19 07:30:00+00:00",
    "candle_index": 30,
    "open": 275.42,
    "high": 275.74,
    "low": 271.74,
    "close": 271.82,
    "body_pct": 0.9000000000000057,
    "upper_shadow_pct": 0.0799999999999983,
    "lower_shadow_pct": 0.01999999999999602,
    "position_in_window": 0.3158,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-01-19 07:45:00+00:00",
    "candle_index": 31,
    "open": 271.83,
    "high": 274.97,
    "low": 271.2,
    "close": 271.53,
    "body_pct": 0.07957559681697833,
    "upper_shadow_pct": 0.8328912466843531,
    "lower_shadow_pct": 0.08753315649866862,
    "position_in_window": 0.3263,
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
    "timestamp": "2025-01-19 08:00:00+00:00",
    "candle_index": 32,
    "open": 271.52,
    "high": 273.76,
    "low": 270.02,
    "close": 273.49,
    "body_pct": 0.5267379679144445,
    "upper_shadow_pct": 0.07219251336897892,
    "lower_shadow_pct": 0.4010695187165766,
    "position_in_window": 0.3368,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-01-19 08:15:00+00:00",
    "candle_index": 33,
    "open": 273.48,
    "high": 273.99,
    "low": 268.47,
    "close": 269.54,
    "body_pct": 0.7137681159420309,
    "upper_shadow_pct": 0.09239130434782475,
    "lower_shadow_pct": 0.19384057971014432,
    "position_in_window": 0.3474,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-01-19 08:30:00+00:00",
    "candle_index": 34,
    "open": 269.53,
    "high": 273.66,
    "low": 268.44,
    "close": 273.14,
    "body_pct": 0.6915708812260526,
    "upper_shadow_pct": 0.09961685823755477,
    "lower_shadow_pct": 0.2088122605363926,
    "position_in_window": 0.3579,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-01-19 08:45:00+00:00",
    "candle_index": 35,
    "open": 273.14,
    "high": 275.47,
    "low": 270.81,
    "close": 274.5,
    "body_pct": 0.2918454935622331,
    "upper_shadow_pct": 0.20815450643777297,
    "lower_shadow_pct": 0.4999999999999939,
    "position_in_window": 0.3684,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-01-19 09:00:00+00:00",
    "candle_index": 36,
    "open": 274.51,
    "high": 279.0,
    "low": 272.34,
    "close": 278.75,
    "body_pct": 0.6366366366366356,
    "upper_shadow_pct": 0.0375375375375374,
    "lower_shadow_pct": 0.325825825825827,
    "position_in_window": 0.3789,
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
  "doji_count": 7,
  "doji_ratio": 0.07291666666666667,
  "small_body_count": 18,
  "small_body_ratio": 0.1875,
  "bullish_body_total": 145.92000000000002,
  "bearish_body_total": 155.51000000000005
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
      "previous_timestamp": "2025-01-19 02:15:00+00:00",
      "timestamp": "2025-01-19 02:30:00+00:00",
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
      "previous_timestamp": "2025-01-19 02:15:00+00:00",
      "timestamp": "2025-01-19 02:30:00+00:00",
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
      "previous_timestamp": "2025-01-19 05:15:00+00:00",
      "timestamp": "2025-01-19 05:30:00+00:00",
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
      "previous_timestamp": "2025-01-19 05:15:00+00:00",
      "timestamp": "2025-01-19 05:30:00+00:00",
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
      "previous_timestamp": "2025-01-19 05:45:00+00:00",
      "timestamp": "2025-01-19 06:00:00+00:00",
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
      "previous_timestamp": "2025-01-19 05:45:00+00:00",
      "timestamp": "2025-01-19 06:00:00+00:00",
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
      "previous_timestamp": "2025-01-19 07:15:00+00:00",
      "timestamp": "2025-01-19 07:30:00+00:00",
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
      "previous_timestamp": "2025-01-19 07:15:00+00:00",
      "timestamp": "2025-01-19 07:30:00+00:00",
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
      "previous_timestamp": "2025-01-19 07:45:00+00:00",
      "timestamp": "2025-01-19 08:00:00+00:00",
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
      "previous_timestamp": "2025-01-19 07:45:00+00:00",
      "timestamp": "2025-01-19 08:00:00+00:00",
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
      "previous_timestamp": "2025-01-19 10:45:00+00:00",
      "timestamp": "2025-01-19 11:00:00+00:00",
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
      "previous_timestamp": "2025-01-19 10:45:00+00:00",
      "timestamp": "2025-01-19 11:00:00+00:00",
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
      "previous_timestamp": "2025-01-19 12:30:00+00:00",
      "timestamp": "2025-01-19 12:45:00+00:00",
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
      "previous_timestamp": "2025-01-19 12:30:00+00:00",
      "timestamp": "2025-01-19 12:45:00+00:00",
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
      "previous_timestamp": "2025-01-19 14:45:00+00:00",
      "timestamp": "2025-01-19 15:00:00+00:00",
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
      "previous_timestamp": "2025-01-19 14:45:00+00:00",
      "timestamp": "2025-01-19 15:00:00+00:00",
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
      "previous_timestamp": "2025-01-19 16:45:00+00:00",
      "timestamp": "2025-01-19 17:00:00+00:00",
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
      "previous_timestamp": "2025-01-19 16:45:00+00:00",
      "timestamp": "2025-01-19 17:00:00+00:00",
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
      "previous_timestamp": "2025-01-19 18:30:00+00:00",
      "timestamp": "2025-01-19 18:45:00+00:00",
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
      "previous_timestamp": "2025-01-19 18:30:00+00:00",
      "timestamp": "2025-01-19 18:45:00+00:00",
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
LONG_LOWER_SHADOW_REJECTION, CLOSE_NEAR_LOW, STRONG_BEARISH_CANDLE_BODY, SMALL_BODY_INDECISION, SPINNING_TOP_INDECISION, CLOSE_NEAR_HIGH, STRONG_BULLISH_CANDLE_BODY, LONG_UPPER_SHADOW_REJECTION, DOJI_INDECISION, SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED, CANDLE_PATTERN_NEEDS_TREND_CONTEXT, HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED, BEARISH_ENGULFING_CONTEXT, ENGULFING_WITHOUT_FOLLOW_THROUGH, BULLISH_ENGULFING_CONTEXT, BULLISH_BELT_HOLD_CONTEXT_REQUIRED, INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED, REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH, HANGING_MAN_LIKE_CONTEXT_REQUIRED, LONG_LEGGED_DOJI_CONTEXT, RICKSHAW_MAN_DOJI_CONTEXT, BEARISH_BELT_HOLD_CONTEXT_REQUIRED, TWEEZERS_TOP_CONTEXT_REQUIRED, TWEEZERS_BOTTOM_CONTEXT_REQUIRED, BEARISH_HARAMI_CONTEXT, HARAMI_CROSS_CONTEXT, DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT, DOJI_TOP_CONTEXT_REQUIRED, BULLISH_HARAMI_CONTEXT, THREE_ADVANCING_WHITE_SOLDIERS_CONTEXT

## 2. Altunina trend context
### Swing structure
```json
[
  {
    "index": 1,
    "timestamp": "2025-01-19 00:15:00+00:00",
    "price": 265.0,
    "point_type": "HIGH"
  },
  {
    "index": 6,
    "timestamp": "2025-01-19 01:30:00+00:00",
    "price": 253.15,
    "point_type": "LOW"
  },
  {
    "index": 9,
    "timestamp": "2025-01-19 02:15:00+00:00",
    "price": 259.08,
    "point_type": "HIGH"
  },
  {
    "index": 12,
    "timestamp": "2025-01-19 03:00:00+00:00",
    "price": 252.08,
    "point_type": "LOW"
  },
  {
    "index": 19,
    "timestamp": "2025-01-19 04:45:00+00:00",
    "price": 275.0,
    "point_type": "HIGH"
  },
  {
    "index": 21,
    "timestamp": "2025-01-19 05:15:00+00:00",
    "price": 267.34,
    "point_type": "LOW"
  },
  {
    "index": 22,
    "timestamp": "2025-01-19 05:30:00+00:00",
    "price": 272.98,
    "point_type": "HIGH"
  },
  {
    "index": 23,
    "timestamp": "2025-01-19 05:45:00+00:00",
    "price": 265.0,
    "point_type": "LOW"
  },
  {
    "index": 29,
    "timestamp": "2025-01-19 07:15:00+00:00",
    "price": 277.99,
    "point_type": "HIGH"
  },
  {
    "index": 34,
    "timestamp": "2025-01-19 08:30:00+00:00",
    "price": 268.44,
    "point_type": "LOW"
  },
  {
    "index": 37,
    "timestamp": "2025-01-19 09:15:00+00:00",
    "price": 279.23,
    "point_type": "HIGH"
  },
  {
    "index": 39,
    "timestamp": "2025-01-19 09:45:00+00:00",
    "price": 266.28,
    "point_type": "LOW"
  },
  {
    "index": 45,
    "timestamp": "2025-01-19 11:15:00+00:00",
    "price": 295.83,
    "point_type": "HIGH"
  },
  {
    "index": 49,
    "timestamp": "2025-01-19 12:15:00+00:00",
    "price": 277.29,
    "point_type": "LOW"
  },
  {
    "index": 50,
    "timestamp": "2025-01-19 12:30:00+00:00",
    "price": 283.9,
    "point_type": "HIGH"
  },
  {
    "index": 51,
    "timestamp": "2025-01-19 12:45:00+00:00",
    "price": 275.22,
    "point_type": "LOW"
  },
  {
    "index": 54,
    "timestamp": "2025-01-19 13:30:00+00:00",
    "price": 288.25,
    "point_type": "HIGH"
  },
  {
    "index": 58,
    "timestamp": "2025-01-19 14:30:00+00:00",
    "price": 267.38,
    "point_type": "LOW"
  },
  {
    "index": 60,
    "timestamp": "2025-01-19 15:00:00+00:00",
    "price": 272.98,
    "point_type": "HIGH"
  },
  {
    "index": 61,
    "timestamp": "2025-01-19 15:15:00+00:00",
    "price": 262.95,
    "point_type": "LOW"
  },
  {
    "index": 62,
    "timestamp": "2025-01-19 15:30:00+00:00",
    "price": 272.05,
    "point_type": "HIGH"
  },
  {
    "index": 66,
    "timestamp": "2025-01-19 16:30:00+00:00",
    "price": 264.04,
    "point_type": "LOW"
  },
  {
    "index": 67,
    "timestamp": "2025-01-19 16:45:00+00:00",
    "price": 269.19,
    "point_type": "HIGH"
  },
  {
    "index": 69,
    "timestamp": "2025-01-19 17:15:00+00:00",
    "price": 264.23,
    "point_type": "LOW"
  },
  {
    "index": 73,
    "timestamp": "2025-01-19 18:15:00+00:00",
    "price": 275.41,
    "point_type": "HIGH"
  },
  {
    "index": 76,
    "timestamp": "2025-01-19 19:00:00+00:00",
    "price": 270.32,
    "point_type": "LOW"
  },
  {
    "index": 77,
    "timestamp": "2025-01-19 19:15:00+00:00",
    "price": 272.98,
    "point_type": "HIGH"
  },
  {
    "index": 78,
    "timestamp": "2025-01-19 19:30:00+00:00",
    "price": 268.0,
    "point_type": "LOW"
  },
  {
    "index": 85,
    "timestamp": "2025-01-19 21:15:00+00:00",
    "price": 278.43,
    "point_type": "HIGH"
  },
  {
    "index": 88,
    "timestamp": "2025-01-19 22:00:00+00:00",
    "price": 244.38,
    "point_type": "LOW"
  },
  {
    "index": 89,
    "timestamp": "2025-01-19 22:15:00+00:00",
    "price": 259.39,
    "point_type": "HIGH"
  },
  {
    "index": 94,
    "timestamp": "2025-01-19 23:30:00+00:00",
    "price": 236.68,
    "point_type": "LOW"
  }
]
```
### Higher highs / lower highs
```json
{
  "raw_swing_count": 38,
  "swing_count": 32,
  "leg_count": 31,
  "structure_direction": "SIDEWAYS_STRUCTURE",
  "total_movement": 361.50000000000006,
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
    "lower_price": 267.34,
    "upper_price": 268.0,
    "mid_price": 267.5733333333333,
    "touch_count": 3,
    "source_indexes": [
      21,
      58,
      78
    ],
    "zone_width": 0.660000000000025,
    "zone_width_ratio": 0.0024666135140523162,
    "formed_at_index": 78,
    "first_touch_index": 21,
    "last_touch_index": 78,
    "source_point_types": [
      "LOW",
      "LOW",
      "LOW"
    ],
    "original_zone_type": "SUPPORT",
    "current_zone_type": "SUPPORT",
    "role_changed_at_index": null,
    "is_significant_single_extreme": false,
    "positional_zone_type": "RESISTANCE"
  },
  "resistance_zone": {
    "zone_type": "RESISTANCE",
    "lower_price": 277.03,
    "upper_price": 277.99,
    "mid_price": 277.5225,
    "touch_count": 4,
    "source_indexes": [
      29,
      49,
      81,
      83
    ],
    "zone_width": 0.9600000000000364,
    "zone_width_ratio": 0.0034591789854877945,
    "formed_at_index": 83,
    "first_touch_index": 29,
    "last_touch_index": 83,
    "source_point_types": [
      "HIGH",
      "LOW",
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
  "lower_boundary": 267.34,
  "upper_boundary": 277.99,
  "midline": 272.66499999999996,
  "width": 10.650000000000034,
  "width_ratio": 0.03905891845304691,
  "touch_count": 7,
  "inside_close_ratio": 0.6984126984126984,
  "formed_at_index": 83,
  "first_touch_index": 21,
  "duration_candles": 63,
  "boundary_alternation_count": 3
}
```
### Range high / low
See trading range object above.
### Price position inside range
```json
{
  "swing_count": 38,
  "zone_count": 11,
  "range_detected": true,
  "range_formed_at_index": 83,
  "range_duration_candles": 63,
  "inside_close_ratio": 0.6984126984126984,
  "breakout_direction": "DOWNWARD",
  "breakout_status": "RETURNED_TO_RANGE",
  "polarity_status": "FAILED"
}
```
### Breakout / breakdown attempts
```json
{
  "direction": "DOWNWARD",
  "status": "RETURNED_TO_RANGE",
  "breakout_index": 85,
  "boundary_price": 267.34,
  "breakout_close": 263.7,
  "distance_ratio": 0.013615620558090772,
  "returned_to_range": true,
  "follow_through_count": 0,
  "evidence": [
    {
      "source": "SCHWAGER",
      "code": "SCHWAGER_BEARISH_RANGE_BREAKDOWN_CONTEXT",
      "description": "Closing price moved below the range boundary",
      "contribution": -0.12,
      "metadata": {
        "breakout_index": 85
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
      "code": "SCHWAGER_PRICE_RETURNED_TO_RANGE",
      "description": "Closing price returned inside the range",
      "contribution": 0.0,
      "metadata": {
        "return_index": 86,
        "return_depth_ratio": 0.0009389671361547152
      }
    },
    {
      "source": "SCHWAGER",
      "code": "SCHWAGER_FALSE_BREAKOUT_INVALIDATED",
      "description": "Price revisited the post-breakout extreme",
      "contribution": 0.0,
      "metadata": {}
    }
  ],
  "analysis_start_index": 84,
  "confirmation_method": "DISTANCE",
  "confirmation_close_count": 1,
  "extreme_index": 85,
  "extreme_price": 262.0,
  "maximum_distance_ratio": 0.01997456422533095,
  "return_index": 86,
  "return_depth_ratio": 0.0009389671361547152,
  "reversal_candle_count": 1,
  "false_breakout_confirmation": "INVALIDATED",
  "false_breakout_invalidated": true
}
```
### False breakout / failed breakout
See breakout context above.
### Range context conclusion
SCHWAGER_SUPPORT_ZONE_IDENTIFIED, SCHWAGER_PREVIOUS_EXTREME_ZONE_IDENTIFIED, SCHWAGER_RESISTANCE_ZONE_IDENTIFIED, SCHWAGER_RESISTANCE_ZONE_HELD, SCHWAGER_SUPPORT_ZONE_HELD, SCHWAGER_ZONE_TOO_WIDE, SCHWAGER_TRADING_RANGE_DETECTED, SCHWAGER_PRICE_INSIDE_RANGE, SCHWAGER_RANGE_UPPER_BOUNDARY_HELD, SCHWAGER_RANGE_LOWER_BOUNDARY_HELD, SCHWAGER_RANGE_DURATION_CONFIRMED, SCHWAGER_RANGE_BOUNDARY_ALTERNATION_CONFIRMED, SCHWAGER_BEARISH_RANGE_BREAKDOWN_CONTEXT, SCHWAGER_BREAKOUT_REQUIRES_CONFIRMATION, SCHWAGER_PRICE_RETURNED_TO_RANGE, SCHWAGER_FALSE_BREAKOUT_INVALIDATED, SCHWAGER_BREAKOUT_RETEST_FAILED, SCHWAGER_POLARITY_FLIP_FAILED

## 4. BookEvidenceMatrix
### Bullish evidence
Count: 26
### Bearish evidence
Count: 33
### Neutral/range evidence
Count: 302
### Conflict
```json
{
  "agreement_state": "ALIGNED_BEARISH",
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
    "MATRIX_BEARISH_CONFLUENCE",
    "MATRIX_NISON_SCHWAGER_ALIGNED",
    "MATRIX_READY_FOR_REGIME_COMPOSER"
  ]
}
```
### Coverage
```json
{
  "active_source_count": 3,
  "total_evidence_count": 361,
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
  "FLAT": 0.6896825396825398,
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
    "score": 0.6896825396825398
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
The engine returned UNKNOWN because the composer status was FALLBACK_UNKNOWN and selected UNKNOWN. The strongest visible candidate scores after clamping were UP=1.000 and DOWN=1.000; fallback reason: COMPOSER_CONSERVATIVE_FALLBACK_UNKNOWN. The reference label is HIGH_VOLATILITY_CHOP and remains descriptive, not ground truth.
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
