# ethusdt_15m_flat_003 вЂ” Market Evidence Trace

## Window
- Symbol: ETHUSDT
- Interval: 15m
- Period: 2026-01-03T00:00:00+00:00 вЂ” 2026-01-03T23:45:00+00:00
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
    "timestamp": "2026-01-03 00:15:00+00:00",
    "candle_index": 1,
    "open": 3128.99,
    "high": 3131.65,
    "low": 3122.26,
    "close": 3131.42,
    "body_pct": 0.2587859424920473,
    "upper_shadow_pct": 0.024494142705007594,
    "lower_shadow_pct": 0.7167199148029452,
    "position_in_window": 0.0105,
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
    "timestamp": "2026-01-03 00:30:00+00:00",
    "candle_index": 2,
    "open": 3131.42,
    "high": 3131.48,
    "low": 3127.5,
    "close": 3130.42,
    "body_pct": 0.25125628140703404,
    "upper_shadow_pct": 0.015075376884408331,
    "lower_shadow_pct": 0.7336683417085577,
    "position_in_window": 0.0211,
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
    "timestamp": "2026-01-03 00:45:00+00:00",
    "candle_index": 3,
    "open": 3130.42,
    "high": 3136.71,
    "low": 3129.73,
    "close": 3131.0,
    "body_pct": 0.08309455587391486,
    "upper_shadow_pct": 0.8180515759312351,
    "lower_shadow_pct": 0.09885386819484997,
    "position_in_window": 0.0316,
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
    "timestamp": "2026-01-03 01:00:00+00:00",
    "candle_index": 4,
    "open": 3130.99,
    "high": 3131.7,
    "low": 3127.04,
    "close": 3131.49,
    "body_pct": 0.10729613733905914,
    "upper_shadow_pct": 0.04506437768241265,
    "lower_shadow_pct": 0.8476394849785283,
    "position_in_window": 0.0421,
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
    "timestamp": "2026-01-03 01:15:00+00:00",
    "candle_index": 5,
    "open": 3131.48,
    "high": 3131.8,
    "low": 3123.43,
    "close": 3124.94,
    "body_pct": 0.7813620071684222,
    "upper_shadow_pct": 0.03823178016728202,
    "lower_shadow_pct": 0.18040621266429582,
    "position_in_window": 0.0526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-01-03 01:30:00+00:00",
    "candle_index": 6,
    "open": 3124.94,
    "high": 3130.75,
    "low": 3124.93,
    "close": 3129.97,
    "body_pct": 0.8642611683848117,
    "upper_shadow_pct": 0.13402061855673164,
    "lower_shadow_pct": 0.0017182130584567005,
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
    "timestamp": "2026-01-03 01:45:00+00:00",
    "candle_index": 7,
    "open": 3129.98,
    "high": 3131.85,
    "low": 3128.01,
    "close": 3130.81,
    "body_pct": 0.2161458333333318,
    "upper_shadow_pct": 0.2708333333333457,
    "lower_shadow_pct": 0.5130208333333225,
    "position_in_window": 0.0737,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2026-01-03 02:00:00+00:00",
    "candle_index": 8,
    "open": 3130.81,
    "high": 3130.81,
    "low": 3120.17,
    "close": 3122.0,
    "body_pct": 0.8280075187969973,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.17199248120300273,
    "position_in_window": 0.0842,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-01-03 02:15:00+00:00",
    "candle_index": 9,
    "open": 3122.0,
    "high": 3127.22,
    "low": 3120.28,
    "close": 3127.06,
    "body_pct": 0.7291066282421091,
    "upper_shadow_pct": 0.023054755043208027,
    "lower_shadow_pct": 0.24783861671468285,
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
    "timestamp": "2026-01-03 02:45:00+00:00",
    "candle_index": 11,
    "open": 3125.28,
    "high": 3129.27,
    "low": 3125.27,
    "close": 3126.27,
    "body_pct": 0.24749999999994543,
    "upper_shadow_pct": 0.75,
    "lower_shadow_pct": 0.0025000000000545697,
    "position_in_window": 0.1158,
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
    "timestamp": "2026-01-03 03:15:00+00:00",
    "candle_index": 13,
    "open": 3122.84,
    "high": 3126.64,
    "low": 3119.26,
    "close": 3121.37,
    "body_pct": 0.19918699186996253,
    "upper_shadow_pct": 0.5149051490514777,
    "lower_shadow_pct": 0.2859078590785598,
    "position_in_window": 0.1368,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2026-01-03 03:30:00+00:00",
    "candle_index": 14,
    "open": 3121.38,
    "high": 3124.76,
    "low": 3120.94,
    "close": 3124.75,
    "body_pct": 0.8821989528795148,
    "upper_shadow_pct": 0.0026178010471774476,
    "lower_shadow_pct": 0.11518324607330778,
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
    "timestamp": "2026-01-03 03:45:00+00:00",
    "candle_index": 15,
    "open": 3124.76,
    "high": 3127.35,
    "low": 3124.0,
    "close": 3125.56,
    "body_pct": 0.23880597014917876,
    "upper_shadow_pct": 0.5343283582089589,
    "lower_shadow_pct": 0.22686567164186236,
    "position_in_window": 0.1579,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2026-01-03 04:00:00+00:00",
    "candle_index": 16,
    "open": 3125.56,
    "high": 3127.79,
    "low": 3119.78,
    "close": 3119.79,
    "body_pct": 0.7203495630462112,
    "upper_shadow_pct": 0.2784019975031316,
    "lower_shadow_pct": 0.0012484394506571568,
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
    "timestamp": "2026-01-03 04:30:00+00:00",
    "candle_index": 18,
    "open": 3121.68,
    "high": 3121.68,
    "low": 3115.6,
    "close": 3115.65,
    "body_pct": 0.9917763157894437,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.008223684210556331,
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
    "timestamp": "2026-01-03 04:45:00+00:00",
    "candle_index": 19,
    "open": 3115.64,
    "high": 3118.43,
    "low": 3115.01,
    "close": 3116.61,
    "body_pct": 0.2836257309942582,
    "upper_shadow_pct": 0.5321637426900329,
    "lower_shadow_pct": 0.184210526315709,
    "position_in_window": 0.2,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION"
    ]
  },
  {
    "timestamp": "2026-01-03 05:00:00+00:00",
    "candle_index": 20,
    "open": 3116.61,
    "high": 3119.09,
    "low": 3114.57,
    "close": 3114.57,
    "body_pct": 0.45132743362831235,
    "upper_shadow_pct": 0.5486725663716876,
    "lower_shadow_pct": 0.0,
    "position_in_window": 0.2105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-01-03 05:15:00+00:00",
    "candle_index": 21,
    "open": 3114.57,
    "high": 3117.15,
    "low": 3111.2,
    "close": 3112.48,
    "body_pct": 0.35126050420168903,
    "upper_shadow_pct": 0.43361344537811913,
    "lower_shadow_pct": 0.21512605042019184,
    "position_in_window": 0.2211,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-01-03 05:45:00+00:00",
    "candle_index": 23,
    "open": 3107.33,
    "high": 3113.21,
    "low": 3105.66,
    "close": 3112.12,
    "body_pct": 0.6344370860926951,
    "upper_shadow_pct": 0.1443708609271681,
    "lower_shadow_pct": 0.22119205298013675,
    "position_in_window": 0.2421,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-01-03 06:15:00+00:00",
    "candle_index": 25,
    "open": 3115.44,
    "high": 3116.3,
    "low": 3108.0,
    "close": 3108.37,
    "body_pct": 0.8518072289156637,
    "upper_shadow_pct": 0.10361445783133837,
    "lower_shadow_pct": 0.04457831325299792,
    "position_in_window": 0.2632,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-01-03 06:30:00+00:00",
    "candle_index": 26,
    "open": 3108.36,
    "high": 3111.99,
    "low": 3102.58,
    "close": 3102.88,
    "body_pct": 0.5823591923485762,
    "upper_shadow_pct": 0.3857598299680883,
    "lower_shadow_pct": 0.03188097768333544,
    "position_in_window": 0.2737,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-01-03 06:45:00+00:00",
    "candle_index": 27,
    "open": 3102.88,
    "high": 3104.8,
    "low": 3098.34,
    "close": 3098.34,
    "body_pct": 0.7027863777089688,
    "upper_shadow_pct": 0.29721362229103127,
    "lower_shadow_pct": 0.0,
    "position_in_window": 0.2842,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-01-03 07:00:00+00:00",
    "candle_index": 28,
    "open": 3098.33,
    "high": 3105.31,
    "low": 3093.76,
    "close": 3095.48,
    "body_pct": 0.2467532467532447,
    "upper_shadow_pct": 0.6043290043290201,
    "lower_shadow_pct": 0.1489177489177351,
    "position_in_window": 0.2947,
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
    "timestamp": "2026-01-03 07:30:00+00:00",
    "candle_index": 30,
    "open": 3082.49,
    "high": 3096.39,
    "low": 3077.55,
    "close": 3091.98,
    "body_pct": 0.5037154989384497,
    "upper_shadow_pct": 0.23407643312101523,
    "lower_shadow_pct": 0.2622080679405351,
    "position_in_window": 0.3158,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-01-03 07:45:00+00:00",
    "candle_index": 31,
    "open": 3091.98,
    "high": 3094.07,
    "low": 3087.84,
    "close": 3090.5,
    "body_pct": 0.23756019261637462,
    "upper_shadow_pct": 0.3354735152488185,
    "lower_shadow_pct": 0.42696629213480686,
    "position_in_window": 0.3263,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2026-01-03 08:00:00+00:00",
    "candle_index": 32,
    "open": 3090.49,
    "high": 3097.29,
    "low": 3083.86,
    "close": 3090.99,
    "body_pct": 0.03723008190618065,
    "upper_shadow_pct": 0.4690990320178897,
    "lower_shadow_pct": 0.4936708860759296,
    "position_in_window": 0.3368,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "DOJI_INDECISION"
    ]
  },
  {
    "timestamp": "2026-01-03 08:30:00+00:00",
    "candle_index": 34,
    "open": 3100.22,
    "high": 3102.95,
    "low": 3097.18,
    "close": 3100.99,
    "body_pct": 0.1334488734835328,
    "upper_shadow_pct": 0.3396880415944615,
    "lower_shadow_pct": 0.5268630849220057,
    "position_in_window": 0.3579,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2026-01-03 08:45:00+00:00",
    "candle_index": 35,
    "open": 3101.0,
    "high": 3102.0,
    "low": 3094.66,
    "close": 3095.48,
    "body_pct": 0.7520435967302278,
    "upper_shadow_pct": 0.13623978201634607,
    "lower_shadow_pct": 0.11171662125342609,
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
    "timestamp": "2026-01-03 09:00:00+00:00",
    "candle_index": 36,
    "open": 3095.48,
    "high": 3098.5,
    "low": 3094.93,
    "close": 3095.65,
    "body_pct": 0.04761904761906582,
    "upper_shadow_pct": 0.7983193277310303,
    "lower_shadow_pct": 0.15406162464990383,
    "position_in_window": 0.3789,
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
    "timestamp": "2026-01-03 09:15:00+00:00",
    "candle_index": 37,
    "open": 3095.65,
    "high": 3100.89,
    "low": 3091.96,
    "close": 3099.58,
    "body_pct": 0.44008958566628315,
    "upper_shadow_pct": 0.1466965285554277,
    "lower_shadow_pct": 0.41321388577828916,
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
  "doji_count": 10,
  "doji_ratio": 0.10416666666666667,
  "small_body_count": 27,
  "small_body_ratio": 0.28125,
  "bullish_body_total": 157.4099999999985,
  "bearish_body_total": 155.70999999999913
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
      "previous_timestamp": "2026-01-03 01:45:00+00:00",
      "timestamp": "2026-01-03 02:00:00+00:00",
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
      "previous_timestamp": "2026-01-03 01:45:00+00:00",
      "timestamp": "2026-01-03 02:00:00+00:00",
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
      "previous_timestamp": "2026-01-03 03:45:00+00:00",
      "timestamp": "2026-01-03 04:00:00+00:00",
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
      "previous_timestamp": "2026-01-03 03:45:00+00:00",
      "timestamp": "2026-01-03 04:00:00+00:00",
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
      "previous_timestamp": "2026-01-03 04:15:00+00:00",
      "timestamp": "2026-01-03 04:30:00+00:00",
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
      "previous_timestamp": "2026-01-03 04:15:00+00:00",
      "timestamp": "2026-01-03 04:30:00+00:00",
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
      "previous_timestamp": "2026-01-03 04:45:00+00:00",
      "timestamp": "2026-01-03 05:00:00+00:00",
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
      "previous_timestamp": "2026-01-03 04:45:00+00:00",
      "timestamp": "2026-01-03 05:00:00+00:00",
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
      "previous_timestamp": "2026-01-03 08:30:00+00:00",
      "timestamp": "2026-01-03 08:45:00+00:00",
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
      "previous_timestamp": "2026-01-03 08:30:00+00:00",
      "timestamp": "2026-01-03 08:45:00+00:00",
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
      "previous_timestamp": "2026-01-03 10:00:00+00:00",
      "timestamp": "2026-01-03 10:15:00+00:00",
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
      "previous_timestamp": "2026-01-03 10:00:00+00:00",
      "timestamp": "2026-01-03 10:15:00+00:00",
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
      "previous_timestamp": "2026-01-03 10:30:00+00:00",
      "timestamp": "2026-01-03 10:45:00+00:00",
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
      "previous_timestamp": "2026-01-03 10:30:00+00:00",
      "timestamp": "2026-01-03 10:45:00+00:00",
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
      "previous_timestamp": "2026-01-03 11:15:00+00:00",
      "timestamp": "2026-01-03 11:30:00+00:00",
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
      "previous_timestamp": "2026-01-03 11:15:00+00:00",
      "timestamp": "2026-01-03 11:30:00+00:00",
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
      "previous_timestamp": "2026-01-03 12:00:00+00:00",
      "timestamp": "2026-01-03 12:15:00+00:00",
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
      "previous_timestamp": "2026-01-03 12:00:00+00:00",
      "timestamp": "2026-01-03 12:15:00+00:00",
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
      "previous_timestamp": "2026-01-03 12:30:00+00:00",
      "timestamp": "2026-01-03 12:45:00+00:00",
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
      "previous_timestamp": "2026-01-03 12:30:00+00:00",
      "timestamp": "2026-01-03 12:45:00+00:00",
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
    "code": "EVENING_STAR_LIKE_CONTEXT",
    "description": "Evening-star-like three-candle geometry",
    "contribution": 0.0,
    "metadata": {
      "timestamps": [
        "2026-01-03 01:30:00+00:00",
        "2026-01-03 01:45:00+00:00",
        "2026-01-03 02:00:00+00:00"
      ],
      "trend_context_evaluated": false,
      "follow_through_evaluated": false,
      "catalog_scope": "NISON_CHAPTERS_4_TO_8"
    }
  },
  {
    "source": "NISON",
    "code": "EVENING_STAR_LIKE_CONTEXT",
    "description": "Evening-star-like three-candle geometry",
    "contribution": 0.0,
    "metadata": {
      "timestamps": [
        "2026-01-03 03:30:00+00:00",
        "2026-01-03 03:45:00+00:00",
        "2026-01-03 04:00:00+00:00"
      ],
      "trend_context_evaluated": false,
      "follow_through_evaluated": false,
      "catalog_scope": "NISON_CHAPTERS_4_TO_8"
    }
  }
]
```
### Candle context conclusion
LONG_LOWER_SHADOW_REJECTION, SMALL_BODY_INDECISION, CLOSE_NEAR_HIGH, HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED, CANDLE_PATTERN_NEEDS_TREND_CONTEXT, LONG_UPPER_SHADOW_REJECTION, CLOSE_NEAR_LOW, DOJI_INDECISION, SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED, SPINNING_TOP_INDECISION, STRONG_BEARISH_CANDLE_BODY, STRONG_BULLISH_CANDLE_BODY, BEARISH_ENGULFING_CONTEXT, ENGULFING_WITHOUT_FOLLOW_THROUGH, BULLISH_ENGULFING_CONTEXT, HANGING_MAN_LIKE_CONTEXT_REQUIRED, REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH, INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED, GRAVESTONE_DOJI_CONTEXT, BEARISH_BELT_HOLD_CONTEXT_REQUIRED, BULLISH_BELT_HOLD_CONTEXT_REQUIRED, LONG_LEGGED_DOJI_CONTEXT, RICKSHAW_MAN_DOJI_CONTEXT, TWEEZERS_TOP_CONTEXT_REQUIRED, TWEEZERS_BOTTOM_CONTEXT_REQUIRED, BULLISH_HARAMI_CONTEXT, HARAMI_CROSS_CONTEXT, BULLISH_SEPARATING_LINES_CONTEXT, BEARISH_HARAMI_CONTEXT, DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT, DOJI_TOP_CONTEXT_REQUIRED, BEARISH_SEPARATING_LINES_CONTEXT, EVENING_STAR_LIKE_CONTEXT

## 2. Altunina trend context
### Swing structure
```json
[
  {
    "index": 1,
    "timestamp": "2026-01-03 00:15:00+00:00",
    "price": 3122.26,
    "point_type": "LOW"
  },
  {
    "index": 3,
    "timestamp": "2026-01-03 00:45:00+00:00",
    "price": 3136.71,
    "point_type": "HIGH"
  },
  {
    "index": 5,
    "timestamp": "2026-01-03 01:15:00+00:00",
    "price": 3123.43,
    "point_type": "LOW"
  },
  {
    "index": 7,
    "timestamp": "2026-01-03 01:45:00+00:00",
    "price": 3131.85,
    "point_type": "HIGH"
  },
  {
    "index": 8,
    "timestamp": "2026-01-03 02:00:00+00:00",
    "price": 3120.17,
    "point_type": "LOW"
  },
  {
    "index": 11,
    "timestamp": "2026-01-03 02:45:00+00:00",
    "price": 3129.27,
    "point_type": "HIGH"
  },
  {
    "index": 13,
    "timestamp": "2026-01-03 03:15:00+00:00",
    "price": 3119.26,
    "point_type": "LOW"
  },
  {
    "index": 16,
    "timestamp": "2026-01-03 04:00:00+00:00",
    "price": 3127.79,
    "point_type": "HIGH"
  },
  {
    "index": 22,
    "timestamp": "2026-01-03 05:30:00+00:00",
    "price": 3104.89,
    "point_type": "LOW"
  },
  {
    "index": 24,
    "timestamp": "2026-01-03 06:00:00+00:00",
    "price": 3117.76,
    "point_type": "HIGH"
  },
  {
    "index": 29,
    "timestamp": "2026-01-03 07:15:00+00:00",
    "price": 3076.0,
    "point_type": "LOW"
  },
  {
    "index": 33,
    "timestamp": "2026-01-03 08:15:00+00:00",
    "price": 3105.72,
    "point_type": "HIGH"
  },
  {
    "index": 37,
    "timestamp": "2026-01-03 09:15:00+00:00",
    "price": 3091.96,
    "point_type": "LOW"
  },
  {
    "index": 38,
    "timestamp": "2026-01-03 09:30:00+00:00",
    "price": 3110.56,
    "point_type": "HIGH"
  },
  {
    "index": 40,
    "timestamp": "2026-01-03 10:00:00+00:00",
    "price": 3097.42,
    "point_type": "LOW"
  },
  {
    "index": 42,
    "timestamp": "2026-01-03 10:30:00+00:00",
    "price": 3105.53,
    "point_type": "HIGH"
  },
  {
    "index": 46,
    "timestamp": "2026-01-03 11:30:00+00:00",
    "price": 3091.99,
    "point_type": "LOW"
  },
  {
    "index": 47,
    "timestamp": "2026-01-03 11:45:00+00:00",
    "price": 3100.22,
    "point_type": "HIGH"
  },
  {
    "index": 48,
    "timestamp": "2026-01-03 12:00:00+00:00",
    "price": 3093.47,
    "point_type": "LOW"
  },
  {
    "index": 57,
    "timestamp": "2026-01-03 14:15:00+00:00",
    "price": 3114.61,
    "point_type": "HIGH"
  },
  {
    "index": 60,
    "timestamp": "2026-01-03 15:00:00+00:00",
    "price": 3100.59,
    "point_type": "LOW"
  },
  {
    "index": 62,
    "timestamp": "2026-01-03 15:30:00+00:00",
    "price": 3107.5,
    "point_type": "HIGH"
  },
  {
    "index": 65,
    "timestamp": "2026-01-03 16:15:00+00:00",
    "price": 3098.33,
    "point_type": "LOW"
  },
  {
    "index": 67,
    "timestamp": "2026-01-03 16:45:00+00:00",
    "price": 3112.17,
    "point_type": "HIGH"
  },
  {
    "index": 68,
    "timestamp": "2026-01-03 17:00:00+00:00",
    "price": 3105.62,
    "point_type": "LOW"
  },
  {
    "index": 70,
    "timestamp": "2026-01-03 17:30:00+00:00",
    "price": 3110.42,
    "point_type": "HIGH"
  },
  {
    "index": 72,
    "timestamp": "2026-01-03 18:00:00+00:00",
    "price": 3105.08,
    "point_type": "LOW"
  },
  {
    "index": 73,
    "timestamp": "2026-01-03 18:15:00+00:00",
    "price": 3118.55,
    "point_type": "HIGH"
  },
  {
    "index": 77,
    "timestamp": "2026-01-03 19:15:00+00:00",
    "price": 3110.5,
    "point_type": "LOW"
  },
  {
    "index": 78,
    "timestamp": "2026-01-03 19:30:00+00:00",
    "price": 3115.04,
    "point_type": "HIGH"
  },
  {
    "index": 80,
    "timestamp": "2026-01-03 20:00:00+00:00",
    "price": 3107.49,
    "point_type": "LOW"
  },
  {
    "index": 83,
    "timestamp": "2026-01-03 20:45:00+00:00",
    "price": 3116.89,
    "point_type": "HIGH"
  },
  {
    "index": 84,
    "timestamp": "2026-01-03 21:00:00+00:00",
    "price": 3113.04,
    "point_type": "LOW"
  },
  {
    "index": 86,
    "timestamp": "2026-01-03 21:30:00+00:00",
    "price": 3129.22,
    "point_type": "HIGH"
  },
  {
    "index": 88,
    "timestamp": "2026-01-03 22:00:00+00:00",
    "price": 3113.92,
    "point_type": "LOW"
  },
  {
    "index": 90,
    "timestamp": "2026-01-03 22:30:00+00:00",
    "price": 3126.2,
    "point_type": "HIGH"
  },
  {
    "index": 91,
    "timestamp": "2026-01-03 22:45:00+00:00",
    "price": 3119.51,
    "point_type": "LOW"
  }
]
```
### Higher highs / lower highs
```json
{
  "raw_swing_count": 45,
  "swing_count": 37,
  "leg_count": 36,
  "structure_direction": "SIDEWAYS_STRUCTURE",
  "total_movement": 443.9300000000003,
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
    "lower_price": 3091.96,
    "upper_price": 3110.56,
    "mid_price": 3102.7625,
    "touch_count": 20,
    "source_indexes": [
      22,
      28,
      33,
      35,
      37,
      38,
      40,
      42,
      46,
      47,
      48,
      54,
      60,
      62,
      65,
      68,
      70,
      72,
      77,
      80
    ],
    "zone_width": 18.59999999999991,
    "zone_width_ratio": 0.0059946579862299836,
    "formed_at_index": 80,
    "first_touch_index": 22,
    "last_touch_index": 80,
    "source_point_types": [
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
      "HIGH",
      "LOW",
      "HIGH",
      "LOW",
      "LOW",
      "HIGH",
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
    "lower_price": 3127.79,
    "upper_price": 3136.71,
    "mid_price": 3131.184285714285,
    "touch_count": 7,
    "source_indexes": [
      1,
      3,
      5,
      7,
      11,
      16,
      86
    ],
    "zone_width": 8.920000000000073,
    "zone_width_ratio": 0.002848762380641944,
    "formed_at_index": 86,
    "first_touch_index": 1,
    "last_touch_index": 86,
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
  "is_detected": true,
  "lower_boundary": 3091.96,
  "upper_boundary": 3136.71,
  "midline": 3114.335,
  "width": 44.75,
  "width_ratio": 0.0143690386551222,
  "touch_count": 27,
  "inside_close_ratio": 0.9651162790697675,
  "formed_at_index": 86,
  "first_touch_index": 1,
  "duration_candles": 86,
  "boundary_alternation_count": 2
}
```
### Range high / low
See trading range object above.
### Price position inside range
```json
{
  "swing_count": 45,
  "zone_count": 4,
  "range_detected": true,
  "range_formed_at_index": 86,
  "range_duration_candles": 86,
  "inside_close_ratio": 0.9651162790697675,
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
  "analysis_start_index": 87,
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
Count: 30
### Bearish evidence
Count: 35
### Neutral/range evidence
Count: 348
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
  "total_evidence_count": 413,
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
  "FLAT": 0.5930232558139535,
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
    "score": 0.5930232558139535
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
