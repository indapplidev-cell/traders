# ethusdt_15m_flat_002 вЂ” Market Evidence Trace

## Window
- Symbol: ETHUSDT
- Interval: 15m
- Period: 2025-12-20T00:00:00+00:00 вЂ” 2025-12-20T23:45:00+00:00
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
    "timestamp": "2025-12-20 00:00:00+00:00",
    "candle_index": 0,
    "open": 2979.49,
    "high": 2980.53,
    "low": 2970.98,
    "close": 2976.44,
    "body_pct": 0.31937172774865646,
    "upper_shadow_pct": 0.10890052356025116,
    "lower_shadow_pct": 0.5717277486910924,
    "position_in_window": 0.0,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2025-12-20 00:15:00+00:00",
    "candle_index": 1,
    "open": 2976.44,
    "high": 2980.66,
    "low": 2974.55,
    "close": 2979.5,
    "body_pct": 0.5008183306055826,
    "upper_shadow_pct": 0.1898527004909847,
    "lower_shadow_pct": 0.3093289689034327,
    "position_in_window": 0.0105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-12-20 00:30:00+00:00",
    "candle_index": 2,
    "open": 2979.49,
    "high": 2980.35,
    "low": 2974.91,
    "close": 2975.5,
    "body_pct": 0.7334558823528937,
    "upper_shadow_pct": 0.15808823529413946,
    "lower_shadow_pct": 0.10845588235296684,
    "position_in_window": 0.0211,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-12-20 00:45:00+00:00",
    "candle_index": 3,
    "open": 2975.5,
    "high": 2978.63,
    "low": 2971.16,
    "close": 2974.55,
    "body_pct": 0.12717536813919486,
    "upper_shadow_pct": 0.41900937081660006,
    "lower_shadow_pct": 0.45381526104420505,
    "position_in_window": 0.0316,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2025-12-20 01:00:00+00:00",
    "candle_index": 4,
    "open": 2974.55,
    "high": 2980.44,
    "low": 2973.23,
    "close": 2979.07,
    "body_pct": 0.6269070735090095,
    "upper_shadow_pct": 0.190013869625504,
    "lower_shadow_pct": 0.18307905686548642,
    "position_in_window": 0.0421,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-12-20 01:15:00+00:00",
    "candle_index": 5,
    "open": 2979.07,
    "high": 2982.82,
    "low": 2976.8,
    "close": 2979.32,
    "body_pct": 0.041528239202657934,
    "upper_shadow_pct": 0.5813953488372111,
    "lower_shadow_pct": 0.37707641196013103,
    "position_in_window": 0.0526,
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
    "timestamp": "2025-12-20 01:30:00+00:00",
    "candle_index": 6,
    "open": 2979.33,
    "high": 2979.8,
    "low": 2974.75,
    "close": 2975.99,
    "body_pct": 0.6613861386138664,
    "upper_shadow_pct": 0.09306930693074014,
    "lower_shadow_pct": 0.24554455445539347,
    "position_in_window": 0.0632,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-12-20 01:45:00+00:00",
    "candle_index": 7,
    "open": 2976.0,
    "high": 2978.61,
    "low": 2975.55,
    "close": 2976.2,
    "body_pct": 0.06535947712412472,
    "upper_shadow_pct": 0.7875816993465203,
    "lower_shadow_pct": 0.14705882352935495,
    "position_in_window": 0.0737,
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
    "timestamp": "2025-12-20 02:00:00+00:00",
    "candle_index": 8,
    "open": 2976.2,
    "high": 2976.93,
    "low": 2973.76,
    "close": 2976.13,
    "body_pct": 0.022082018927355646,
    "upper_shadow_pct": 0.23028391167195778,
    "lower_shadow_pct": 0.7476340694006866,
    "position_in_window": 0.0842,
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
    "timestamp": "2025-12-20 02:15:00+00:00",
    "candle_index": 9,
    "open": 2976.13,
    "high": 2980.58,
    "low": 2976.13,
    "close": 2978.07,
    "body_pct": 0.43595505617980534,
    "upper_shadow_pct": 0.5640449438201947,
    "lower_shadow_pct": 0.0,
    "position_in_window": 0.0947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2025-12-20 02:30:00+00:00",
    "candle_index": 10,
    "open": 2978.08,
    "high": 2990.0,
    "low": 2977.99,
    "close": 2989.28,
    "body_pct": 0.9325562031640358,
    "upper_shadow_pct": 0.05995004163195561,
    "lower_shadow_pct": 0.00749375520400865,
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
    "timestamp": "2025-12-20 02:45:00+00:00",
    "candle_index": 11,
    "open": 2989.29,
    "high": 2989.29,
    "low": 2981.91,
    "close": 2982.66,
    "body_pct": 0.8983739837398389,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.1016260162601611,
    "position_in_window": 0.1158,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-12-20 03:00:00+00:00",
    "candle_index": 12,
    "open": 2982.65,
    "high": 2985.8,
    "low": 2982.19,
    "close": 2982.46,
    "body_pct": 0.05263157894738168,
    "upper_shadow_pct": 0.872576177285313,
    "lower_shadow_pct": 0.07479224376730534,
    "position_in_window": 0.1263,
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
    "timestamp": "2025-12-20 03:15:00+00:00",
    "candle_index": 13,
    "open": 2982.46,
    "high": 2990.41,
    "low": 2982.45,
    "close": 2990.23,
    "body_pct": 0.9761306532663249,
    "upper_shadow_pct": 0.022613065326612496,
    "lower_shadow_pct": 0.0012562814070625921,
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
    "timestamp": "2025-12-20 03:30:00+00:00",
    "candle_index": 14,
    "open": 2990.24,
    "high": 2994.41,
    "low": 2990.24,
    "close": 2991.4,
    "body_pct": 0.27817745803364247,
    "upper_shadow_pct": 0.7218225419663575,
    "lower_shadow_pct": 0.0,
    "position_in_window": 0.1474,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED",
      "CANDLE_PATTERN_NEEDS_TREND_CONTEXT"
    ]
  },
  {
    "timestamp": "2025-12-20 04:00:00+00:00",
    "candle_index": 16,
    "open": 2989.42,
    "high": 2990.8,
    "low": 2964.17,
    "close": 2981.58,
    "body_pct": 0.29440480660909174,
    "upper_shadow_pct": 0.05182125422456266,
    "lower_shadow_pct": 0.6537739391663456,
    "position_in_window": 0.1684,
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
    "timestamp": "2025-12-20 04:15:00+00:00",
    "candle_index": 17,
    "open": 2981.58,
    "high": 2986.16,
    "low": 2981.48,
    "close": 2985.63,
    "body_pct": 0.8653846153846845,
    "upper_shadow_pct": 0.11324786324781279,
    "lower_shadow_pct": 0.02136752136750268,
    "position_in_window": 0.1789,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-12-20 04:30:00+00:00",
    "candle_index": 18,
    "open": 2985.63,
    "high": 2987.63,
    "low": 2985.15,
    "close": 2985.99,
    "body_pct": 0.14516129032244757,
    "upper_shadow_pct": 0.6612903225807724,
    "lower_shadow_pct": 0.1935483870967801,
    "position_in_window": 0.1895,
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
    "timestamp": "2025-12-20 05:00:00+00:00",
    "candle_index": 20,
    "open": 2984.31,
    "high": 2985.09,
    "low": 2981.99,
    "close": 2985.09,
    "body_pct": 0.25161290322584146,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.7483870967741585,
    "position_in_window": 0.2105,
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
    "timestamp": "2025-12-20 05:15:00+00:00",
    "candle_index": 21,
    "open": 2985.08,
    "high": 2988.74,
    "low": 2983.68,
    "close": 2987.93,
    "body_pct": 0.5632411067193557,
    "upper_shadow_pct": 0.16007905138339015,
    "lower_shadow_pct": 0.27667984189725414,
    "position_in_window": 0.2211,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-12-20 05:30:00+00:00",
    "candle_index": 22,
    "open": 2987.93,
    "high": 2989.5,
    "low": 2984.42,
    "close": 2986.54,
    "body_pct": 0.27362204724407335,
    "upper_shadow_pct": 0.30905511811027286,
    "lower_shadow_pct": 0.4173228346456538,
    "position_in_window": 0.2316,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION"
    ]
  },
  {
    "timestamp": "2025-12-20 05:45:00+00:00",
    "candle_index": 23,
    "open": 2986.54,
    "high": 2986.54,
    "low": 2979.81,
    "close": 2980.99,
    "body_pct": 0.8246656760772908,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.17533432392270923,
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
    "timestamp": "2025-12-20 06:00:00+00:00",
    "candle_index": 24,
    "open": 2980.99,
    "high": 2984.27,
    "low": 2980.76,
    "close": 2983.8,
    "body_pct": 0.8005698005699685,
    "upper_shadow_pct": 0.13390313390308592,
    "lower_shadow_pct": 0.06552706552694557,
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
    "timestamp": "2025-12-20 06:15:00+00:00",
    "candle_index": 25,
    "open": 2983.79,
    "high": 2985.39,
    "low": 2982.99,
    "close": 2983.76,
    "body_pct": 0.01249999999989342,
    "upper_shadow_pct": 0.6666666666666035,
    "lower_shadow_pct": 0.32083333333350306,
    "position_in_window": 0.2632,
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
    "timestamp": "2025-12-20 06:30:00+00:00",
    "candle_index": 26,
    "open": 2983.77,
    "high": 2984.5,
    "low": 2982.35,
    "close": 2982.59,
    "body_pct": 0.5488372093022262,
    "upper_shadow_pct": 0.33953488372092433,
    "lower_shadow_pct": 0.11162790697684945,
    "position_in_window": 0.2737,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-12-20 07:15:00+00:00",
    "candle_index": 29,
    "open": 2977.25,
    "high": 2980.5,
    "low": 2975.0,
    "close": 2980.25,
    "body_pct": 0.5454545454545454,
    "upper_shadow_pct": 0.045454545454545456,
    "lower_shadow_pct": 0.4090909090909091,
    "position_in_window": 0.3053,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-12-20 07:30:00+00:00",
    "candle_index": 30,
    "open": 2980.25,
    "high": 2984.66,
    "low": 2978.73,
    "close": 2980.49,
    "body_pct": 0.040472175379390955,
    "upper_shadow_pct": 0.7032040472175696,
    "lower_shadow_pct": 0.2563237774030394,
    "position_in_window": 0.3158,
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
    "timestamp": "2025-12-20 07:45:00+00:00",
    "candle_index": 31,
    "open": 2980.49,
    "high": 2987.18,
    "low": 2979.92,
    "close": 2981.24,
    "body_pct": 0.1033057851239703,
    "upper_shadow_pct": 0.8181818181818523,
    "lower_shadow_pct": 0.07851239669417734,
    "position_in_window": 0.3263,
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
    "timestamp": "2025-12-20 08:00:00+00:00",
    "candle_index": 32,
    "open": 2981.24,
    "high": 2987.11,
    "low": 2981.24,
    "close": 2983.61,
    "body_pct": 0.40374787052814415,
    "upper_shadow_pct": 0.5962521294718559,
    "lower_shadow_pct": 0.0,
    "position_in_window": 0.3368,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2025-12-20 08:15:00+00:00",
    "candle_index": 33,
    "open": 2983.62,
    "high": 2990.0,
    "low": 2983.62,
    "close": 2989.02,
    "body_pct": 0.8463949843260186,
    "upper_shadow_pct": 0.1536050156739814,
    "lower_shadow_pct": 0.0,
    "position_in_window": 0.3474,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  }
]
```
### Doji / spinning top / small body cluster
```json
{
  "doji_count": 9,
  "doji_ratio": 0.09375,
  "small_body_count": 28,
  "small_body_ratio": 0.2916666666666667,
  "bullish_body_total": 118.72000000000025,
  "bearish_body_total": 120.38999999999942
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
      "previous_timestamp": "2025-12-20 00:00:00+00:00",
      "timestamp": "2025-12-20 00:15:00+00:00",
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
      "previous_timestamp": "2025-12-20 00:00:00+00:00",
      "timestamp": "2025-12-20 00:15:00+00:00",
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
      "previous_timestamp": "2025-12-20 00:45:00+00:00",
      "timestamp": "2025-12-20 01:00:00+00:00",
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
      "previous_timestamp": "2025-12-20 00:45:00+00:00",
      "timestamp": "2025-12-20 01:00:00+00:00",
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
      "previous_timestamp": "2025-12-20 01:15:00+00:00",
      "timestamp": "2025-12-20 01:30:00+00:00",
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
      "previous_timestamp": "2025-12-20 01:15:00+00:00",
      "timestamp": "2025-12-20 01:30:00+00:00",
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
      "previous_timestamp": "2025-12-20 02:00:00+00:00",
      "timestamp": "2025-12-20 02:15:00+00:00",
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
      "previous_timestamp": "2025-12-20 02:00:00+00:00",
      "timestamp": "2025-12-20 02:15:00+00:00",
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
      "previous_timestamp": "2025-12-20 03:00:00+00:00",
      "timestamp": "2025-12-20 03:15:00+00:00",
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
      "previous_timestamp": "2025-12-20 03:00:00+00:00",
      "timestamp": "2025-12-20 03:15:00+00:00",
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
      "previous_timestamp": "2025-12-20 03:30:00+00:00",
      "timestamp": "2025-12-20 03:45:00+00:00",
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
      "previous_timestamp": "2025-12-20 03:30:00+00:00",
      "timestamp": "2025-12-20 03:45:00+00:00",
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
      "previous_timestamp": "2025-12-20 09:15:00+00:00",
      "timestamp": "2025-12-20 09:30:00+00:00",
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
      "previous_timestamp": "2025-12-20 09:15:00+00:00",
      "timestamp": "2025-12-20 09:30:00+00:00",
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
      "previous_timestamp": "2025-12-20 09:30:00+00:00",
      "timestamp": "2025-12-20 09:45:00+00:00",
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
      "previous_timestamp": "2025-12-20 09:30:00+00:00",
      "timestamp": "2025-12-20 09:45:00+00:00",
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
      "previous_timestamp": "2025-12-20 11:00:00+00:00",
      "timestamp": "2025-12-20 11:15:00+00:00",
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
      "previous_timestamp": "2025-12-20 11:00:00+00:00",
      "timestamp": "2025-12-20 11:15:00+00:00",
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
      "previous_timestamp": "2025-12-20 11:30:00+00:00",
      "timestamp": "2025-12-20 11:45:00+00:00",
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
      "previous_timestamp": "2025-12-20 11:30:00+00:00",
      "timestamp": "2025-12-20 11:45:00+00:00",
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
        "2025-12-20 02:45:00+00:00",
        "2025-12-20 03:00:00+00:00",
        "2025-12-20 03:15:00+00:00"
      ],
      "trend_context_evaluated": false,
      "follow_through_evaluated": false,
      "catalog_scope": "NISON_CHAPTERS_4_TO_8"
    }
  },
  {
    "source": "NISON",
    "code": "MORNING_DOJI_STAR_LIKE_CONTEXT",
    "description": "Morning doji-star-like geometry",
    "contribution": 0.0,
    "metadata": {
      "timestamps": [
        "2025-12-20 02:45:00+00:00",
        "2025-12-20 03:00:00+00:00",
        "2025-12-20 03:15:00+00:00"
      ],
      "trend_context_evaluated": false,
      "follow_through_evaluated": false,
      "catalog_scope": "NISON_CHAPTERS_4_TO_8"
    }
  }
]
```
### Candle context conclusion
LONG_LOWER_SHADOW_REJECTION, CLOSE_NEAR_HIGH, STRONG_BEARISH_CANDLE_BODY, CLOSE_NEAR_LOW, SMALL_BODY_INDECISION, SPINNING_TOP_INDECISION, LONG_UPPER_SHADOW_REJECTION, DOJI_INDECISION, STRONG_BULLISH_CANDLE_BODY, SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED, CANDLE_PATTERN_NEEDS_TREND_CONTEXT, HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED, BULLISH_ENGULFING_CONTEXT, ENGULFING_WITHOUT_FOLLOW_THROUGH, BEARISH_ENGULFING_CONTEXT, LONG_LEGGED_DOJI_CONTEXT, BEARISH_BELT_HOLD_CONTEXT_REQUIRED, BULLISH_BELT_HOLD_CONTEXT_REQUIRED, INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED, REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH, HANGING_MAN_LIKE_CONTEXT_REQUIRED, TWEEZERS_TOP_CONTEXT_REQUIRED, DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT, DOJI_TOP_CONTEXT_REQUIRED, BEARISH_SEPARATING_LINES_CONTEXT, BULLISH_HARAMI_CONTEXT, HARAMI_CROSS_CONTEXT, BULLISH_SEPARATING_LINES_CONTEXT, TWEEZERS_BOTTOM_CONTEXT_REQUIRED, BEARISH_HARAMI_CONTEXT, MORNING_STAR_LIKE_CONTEXT, MORNING_DOJI_STAR_LIKE_CONTEXT, THREE_BLACK_CROWS_CONTEXT

## 2. Altunina trend context
### Swing structure
```json
[
  {
    "index": 1,
    "timestamp": "2025-12-20 00:15:00+00:00",
    "price": 2980.66,
    "point_type": "HIGH"
  },
  {
    "index": 3,
    "timestamp": "2025-12-20 00:45:00+00:00",
    "price": 2971.16,
    "point_type": "LOW"
  },
  {
    "index": 5,
    "timestamp": "2025-12-20 01:15:00+00:00",
    "price": 2982.82,
    "point_type": "HIGH"
  },
  {
    "index": 8,
    "timestamp": "2025-12-20 02:00:00+00:00",
    "price": 2973.76,
    "point_type": "LOW"
  },
  {
    "index": 14,
    "timestamp": "2025-12-20 03:30:00+00:00",
    "price": 2994.41,
    "point_type": "HIGH"
  },
  {
    "index": 16,
    "timestamp": "2025-12-20 04:00:00+00:00",
    "price": 2964.17,
    "point_type": "LOW"
  },
  {
    "index": 18,
    "timestamp": "2025-12-20 04:30:00+00:00",
    "price": 2987.63,
    "point_type": "HIGH"
  },
  {
    "index": 20,
    "timestamp": "2025-12-20 05:00:00+00:00",
    "price": 2981.99,
    "point_type": "LOW"
  },
  {
    "index": 22,
    "timestamp": "2025-12-20 05:30:00+00:00",
    "price": 2989.5,
    "point_type": "HIGH"
  },
  {
    "index": 23,
    "timestamp": "2025-12-20 05:45:00+00:00",
    "price": 2979.81,
    "point_type": "LOW"
  },
  {
    "index": 25,
    "timestamp": "2025-12-20 06:15:00+00:00",
    "price": 2985.39,
    "point_type": "HIGH"
  },
  {
    "index": 29,
    "timestamp": "2025-12-20 07:15:00+00:00",
    "price": 2975.0,
    "point_type": "LOW"
  },
  {
    "index": 33,
    "timestamp": "2025-12-20 08:15:00+00:00",
    "price": 2990.0,
    "point_type": "HIGH"
  },
  {
    "index": 35,
    "timestamp": "2025-12-20 08:45:00+00:00",
    "price": 2982.18,
    "point_type": "LOW"
  },
  {
    "index": 38,
    "timestamp": "2025-12-20 09:30:00+00:00",
    "price": 2986.99,
    "point_type": "HIGH"
  },
  {
    "index": 42,
    "timestamp": "2025-12-20 10:30:00+00:00",
    "price": 2975.14,
    "point_type": "LOW"
  },
  {
    "index": 48,
    "timestamp": "2025-12-20 12:00:00+00:00",
    "price": 2993.8,
    "point_type": "HIGH"
  },
  {
    "index": 50,
    "timestamp": "2025-12-20 12:30:00+00:00",
    "price": 2987.49,
    "point_type": "LOW"
  },
  {
    "index": 52,
    "timestamp": "2025-12-20 13:00:00+00:00",
    "price": 2992.03,
    "point_type": "HIGH"
  },
  {
    "index": 53,
    "timestamp": "2025-12-20 13:15:00+00:00",
    "price": 2967.44,
    "point_type": "LOW"
  },
  {
    "index": 55,
    "timestamp": "2025-12-20 13:45:00+00:00",
    "price": 2982.89,
    "point_type": "HIGH"
  },
  {
    "index": 56,
    "timestamp": "2025-12-20 14:00:00+00:00",
    "price": 2969.28,
    "point_type": "LOW"
  },
  {
    "index": 59,
    "timestamp": "2025-12-20 14:45:00+00:00",
    "price": 2981.34,
    "point_type": "HIGH"
  },
  {
    "index": 61,
    "timestamp": "2025-12-20 15:15:00+00:00",
    "price": 2968.66,
    "point_type": "LOW"
  },
  {
    "index": 65,
    "timestamp": "2025-12-20 16:15:00+00:00",
    "price": 2979.84,
    "point_type": "HIGH"
  },
  {
    "index": 66,
    "timestamp": "2025-12-20 16:30:00+00:00",
    "price": 2974.34,
    "point_type": "LOW"
  },
  {
    "index": 69,
    "timestamp": "2025-12-20 17:15:00+00:00",
    "price": 2981.4,
    "point_type": "HIGH"
  },
  {
    "index": 74,
    "timestamp": "2025-12-20 18:30:00+00:00",
    "price": 2974.66,
    "point_type": "LOW"
  },
  {
    "index": 76,
    "timestamp": "2025-12-20 19:00:00+00:00",
    "price": 2981.4,
    "point_type": "HIGH"
  },
  {
    "index": 79,
    "timestamp": "2025-12-20 19:45:00+00:00",
    "price": 2977.5,
    "point_type": "LOW"
  },
  {
    "index": 82,
    "timestamp": "2025-12-20 20:30:00+00:00",
    "price": 2985.8,
    "point_type": "HIGH"
  },
  {
    "index": 89,
    "timestamp": "2025-12-20 22:15:00+00:00",
    "price": 2974.5,
    "point_type": "LOW"
  },
  {
    "index": 91,
    "timestamp": "2025-12-20 22:45:00+00:00",
    "price": 2980.46,
    "point_type": "HIGH"
  },
  {
    "index": 94,
    "timestamp": "2025-12-20 23:30:00+00:00",
    "price": 2972.85,
    "point_type": "LOW"
  }
]
```
### Higher highs / lower highs
```json
{
  "raw_swing_count": 48,
  "swing_count": 34,
  "leg_count": 33,
  "structure_direction": "SIDEWAYS_STRUCTURE",
  "total_movement": 365.05000000000246,
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
    "lower_price": 2964.17,
    "upper_price": 2985.94,
    "mid_price": 2977.3997297297296,
    "touch_count": 37,
    "source_indexes": [
      1,
      3,
      5,
      6,
      8,
      16,
      20,
      23,
      25,
      29,
      35,
      42,
      44,
      53,
      55,
      56,
      59,
      61,
      65,
      66,
      68,
      69,
      70,
      72,
      72,
      74,
      76,
      76,
      79,
      82,
      82,
      85,
      85,
      89,
      91,
      93,
      94
    ],
    "zone_width": 21.769999999999982,
    "zone_width_ratio": 0.007311749169123533,
    "formed_at_index": 94,
    "first_touch_index": 1,
    "last_touch_index": 94,
    "source_point_types": [
      "HIGH",
      "LOW",
      "HIGH",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "HIGH",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "HIGH",
      "LOW",
      "HIGH",
      "LOW",
      "HIGH",
      "LOW",
      "LOW",
      "HIGH",
      "LOW",
      "LOW",
      "HIGH",
      "LOW",
      "LOW",
      "HIGH",
      "LOW",
      "LOW",
      "HIGH",
      "LOW",
      "HIGH",
      "LOW",
      "HIGH",
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
    "lower_price": 2986.99,
    "upper_price": 2994.41,
    "mid_price": 2989.93,
    "touch_count": 11,
    "source_indexes": [
      10,
      14,
      18,
      22,
      31,
      33,
      38,
      45,
      48,
      50,
      52
    ],
    "zone_width": 7.420000000000073,
    "zone_width_ratio": 0.002481663450314915,
    "formed_at_index": 52,
    "first_touch_index": 10,
    "last_touch_index": 52,
    "source_point_types": [
      "HIGH",
      "HIGH",
      "HIGH",
      "HIGH",
      "HIGH",
      "HIGH",
      "HIGH",
      "HIGH",
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
  "lower_boundary": 2964.17,
  "upper_boundary": 2994.41,
  "midline": 2979.29,
  "width": 30.23999999999978,
  "width_ratio": 0.01015006931181583,
  "touch_count": 48,
  "inside_close_ratio": 1.0,
  "formed_at_index": 94,
  "first_touch_index": 1,
  "duration_candles": 94,
  "boundary_alternation_count": 12
}
```
### Range high / low
See trading range object above.
### Price position inside range
```json
{
  "swing_count": 48,
  "zone_count": 2,
  "range_detected": true,
  "range_formed_at_index": 94,
  "range_duration_candles": 94,
  "inside_close_ratio": 1.0,
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
Count: 32
### Bearish evidence
Count: 38
### Neutral/range evidence
Count: 321
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
  "total_evidence_count": 391,
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
  "FLAT": 0.6000000000000001,
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
    "score": 0.6000000000000001
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
