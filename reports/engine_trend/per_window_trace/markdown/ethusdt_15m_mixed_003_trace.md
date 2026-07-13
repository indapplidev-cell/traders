# ethusdt_15m_mixed_003 вЂ” Market Evidence Trace

## Window
- Symbol: ETHUSDT
- Interval: 15m
- Period: 2025-02-25T00:00:00+00:00 вЂ” 2025-02-25T23:45:00+00:00
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
    "timestamp": "2025-02-25 00:00:00+00:00",
    "candle_index": 0,
    "open": 2513.52,
    "high": 2530.6,
    "low": 2458.27,
    "close": 2468.17,
    "body_pct": 0.6269874187750581,
    "upper_shadow_pct": 0.23613991428176337,
    "lower_shadow_pct": 0.1368726669431785,
    "position_in_window": 0.0,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-25 00:30:00+00:00",
    "candle_index": 2,
    "open": 2504.37,
    "high": 2518.66,
    "low": 2484.81,
    "close": 2489.4,
    "body_pct": 0.4422451994091533,
    "upper_shadow_pct": 0.42215657311669136,
    "lower_shadow_pct": 0.13559822747415534,
    "position_in_window": 0.0211,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-25 00:45:00+00:00",
    "candle_index": 3,
    "open": 2489.39,
    "high": 2512.99,
    "low": 2479.99,
    "close": 2499.1,
    "body_pct": 0.29424242424242536,
    "upper_shadow_pct": 0.42090909090908707,
    "lower_shadow_pct": 0.2848484848484876,
    "position_in_window": 0.0316,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION"
    ]
  },
  {
    "timestamp": "2025-02-25 01:00:00+00:00",
    "candle_index": 4,
    "open": 2499.1,
    "high": 2499.1,
    "low": 2470.5,
    "close": 2494.69,
    "body_pct": 0.1541958041957996,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.8458041958042004,
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
    "timestamp": "2025-02-25 01:15:00+00:00",
    "candle_index": 5,
    "open": 2494.69,
    "high": 2510.0,
    "low": 2482.83,
    "close": 2495.22,
    "body_pct": 0.019506808980483768,
    "upper_shadow_pct": 0.5439823334560235,
    "lower_shadow_pct": 0.43651085756349267,
    "position_in_window": 0.0526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "DOJI_INDECISION"
    ]
  },
  {
    "timestamp": "2025-02-25 02:00:00+00:00",
    "candle_index": 8,
    "open": 2494.91,
    "high": 2509.68,
    "low": 2485.16,
    "close": 2486.5,
    "body_pct": 0.34298531810766153,
    "upper_shadow_pct": 0.6023654159869491,
    "lower_shadow_pct": 0.054649265905389335,
    "position_in_window": 0.0842,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-25 02:15:00+00:00",
    "candle_index": 9,
    "open": 2486.49,
    "high": 2496.0,
    "low": 2475.0,
    "close": 2495.4,
    "body_pct": 0.42428571428572903,
    "upper_shadow_pct": 0.02857142857142424,
    "lower_shadow_pct": 0.5471428571428467,
    "position_in_window": 0.0947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-02-25 02:30:00+00:00",
    "candle_index": 10,
    "open": 2495.4,
    "high": 2515.22,
    "low": 2490.0,
    "close": 2513.11,
    "body_pct": 0.7022204599524258,
    "upper_shadow_pct": 0.08366375892147856,
    "lower_shadow_pct": 0.21411578112609572,
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
    "timestamp": "2025-02-25 02:45:00+00:00",
    "candle_index": 11,
    "open": 2513.1,
    "high": 2524.34,
    "low": 2512.57,
    "close": 2513.54,
    "body_pct": 0.03738317757009815,
    "upper_shadow_pct": 0.9175870858114018,
    "lower_shadow_pct": 0.0450297366185001,
    "position_in_window": 0.1158,
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
    "timestamp": "2025-02-25 03:00:00+00:00",
    "candle_index": 12,
    "open": 2513.55,
    "high": 2517.59,
    "low": 2498.81,
    "close": 2498.81,
    "body_pct": 0.7848775292864792,
    "upper_shadow_pct": 0.2151224707135208,
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
    "timestamp": "2025-02-25 03:30:00+00:00",
    "candle_index": 14,
    "open": 2494.1,
    "high": 2503.5,
    "low": 2486.67,
    "close": 2500.01,
    "body_pct": 0.35115864527631224,
    "upper_shadow_pct": 0.20736779560307764,
    "lower_shadow_pct": 0.44147355912061015,
    "position_in_window": 0.1474,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-02-25 03:45:00+00:00",
    "candle_index": 15,
    "open": 2500.0,
    "high": 2513.8,
    "low": 2492.6,
    "close": 2495.21,
    "body_pct": 0.22594339622641046,
    "upper_shadow_pct": 0.6509433962264153,
    "lower_shadow_pct": 0.12311320754717424,
    "position_in_window": 0.1579,
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
    "timestamp": "2025-02-25 04:00:00+00:00",
    "candle_index": 16,
    "open": 2495.22,
    "high": 2495.9,
    "low": 2479.4,
    "close": 2492.91,
    "body_pct": 0.13999999999999668,
    "upper_shadow_pct": 0.04121212121213885,
    "lower_shadow_pct": 0.8187878787878644,
    "position_in_window": 0.1684,
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
    "timestamp": "2025-02-25 04:30:00+00:00",
    "candle_index": 18,
    "open": 2500.84,
    "high": 2501.49,
    "low": 2480.2,
    "close": 2496.0,
    "body_pct": 0.22733677782997436,
    "upper_shadow_pct": 0.030530765617643837,
    "lower_shadow_pct": 0.7421324565523818,
    "position_in_window": 0.1895,
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
    "timestamp": "2025-02-25 05:00:00+00:00",
    "candle_index": 20,
    "open": 2491.8,
    "high": 2503.4,
    "low": 2483.3,
    "close": 2500.89,
    "body_pct": 0.45223880597013594,
    "upper_shadow_pct": 0.12487562189055869,
    "lower_shadow_pct": 0.4228855721393054,
    "position_in_window": 0.2105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-02-25 05:15:00+00:00",
    "candle_index": 21,
    "open": 2500.89,
    "high": 2512.9,
    "low": 2498.5,
    "close": 2503.09,
    "body_pct": 0.15277777777779575,
    "upper_shadow_pct": 0.6812499999999919,
    "lower_shadow_pct": 0.16597222222221233,
    "position_in_window": 0.2211,
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
    "timestamp": "2025-02-25 05:45:00+00:00",
    "candle_index": 23,
    "open": 2506.11,
    "high": 2508.2,
    "low": 2501.7,
    "close": 2506.05,
    "body_pct": 0.009230769230760836,
    "upper_shadow_pct": 0.321538461538414,
    "lower_shadow_pct": 0.6692307692308253,
    "position_in_window": 0.2421,
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
    "timestamp": "2025-02-25 06:00:00+00:00",
    "candle_index": 24,
    "open": 2506.06,
    "high": 2509.29,
    "low": 2490.42,
    "close": 2493.2,
    "body_pct": 0.6815050344462216,
    "upper_shadow_pct": 0.17117117117117311,
    "lower_shadow_pct": 0.14732379438260526,
    "position_in_window": 0.2526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-25 06:15:00+00:00",
    "candle_index": 25,
    "open": 2493.21,
    "high": 2503.77,
    "low": 2490.4,
    "close": 2493.21,
    "body_pct": 0.0,
    "upper_shadow_pct": 0.7898279730740487,
    "lower_shadow_pct": 0.21017202692595127,
    "position_in_window": 0.2632,
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
    "timestamp": "2025-02-25 06:30:00+00:00",
    "candle_index": 26,
    "open": 2493.21,
    "high": 2497.38,
    "low": 2487.51,
    "close": 2494.49,
    "body_pct": 0.1296859169199351,
    "upper_shadow_pct": 0.2928064842958824,
    "lower_shadow_pct": 0.5775075987841825,
    "position_in_window": 0.2737,
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
    "timestamp": "2025-02-25 06:45:00+00:00",
    "candle_index": 27,
    "open": 2494.49,
    "high": 2496.82,
    "low": 2479.4,
    "close": 2480.71,
    "body_pct": 0.7910447761193851,
    "upper_shadow_pct": 0.13375430539611782,
    "lower_shadow_pct": 0.07520091848449713,
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
    "timestamp": "2025-02-25 07:00:00+00:00",
    "candle_index": 28,
    "open": 2480.72,
    "high": 2485.0,
    "low": 2408.7,
    "close": 2425.3,
    "body_pct": 0.7263433813892463,
    "upper_shadow_pct": 0.05609436435124757,
    "lower_shadow_pct": 0.2175622542595062,
    "position_in_window": 0.2947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-25 07:30:00+00:00",
    "candle_index": 30,
    "open": 2366.19,
    "high": 2382.36,
    "low": 2327.9,
    "close": 2368.71,
    "body_pct": 0.04627249357326442,
    "upper_shadow_pct": 0.2506426735218524,
    "lower_shadow_pct": 0.7030848329048832,
    "position_in_window": 0.3158,
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
    "timestamp": "2025-02-25 07:45:00+00:00",
    "candle_index": 31,
    "open": 2368.71,
    "high": 2391.69,
    "low": 2361.2,
    "close": 2368.11,
    "body_pct": 0.01967858314201064,
    "upper_shadow_pct": 0.7536897343391223,
    "lower_shadow_pct": 0.22663168251886703,
    "position_in_window": 0.3263,
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
    "timestamp": "2025-02-25 08:00:00+00:00",
    "candle_index": 32,
    "open": 2368.12,
    "high": 2392.98,
    "low": 2357.9,
    "close": 2388.79,
    "body_pct": 0.5892246294184753,
    "upper_shadow_pct": 0.11944127708095961,
    "lower_shadow_pct": 0.29133409350056505,
    "position_in_window": 0.3368,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-02-25 08:45:00+00:00",
    "candle_index": 35,
    "open": 2412.5,
    "high": 2415.8,
    "low": 2396.0,
    "close": 2396.99,
    "body_pct": 0.7833333333333372,
    "upper_shadow_pct": 0.16666666666667432,
    "lower_shadow_pct": 0.04999999999998852,
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
    "timestamp": "2025-02-25 09:00:00+00:00",
    "candle_index": 36,
    "open": 2397.0,
    "high": 2409.66,
    "low": 2395.36,
    "close": 2398.0,
    "body_pct": 0.06993006993007127,
    "upper_shadow_pct": 0.8153846153846208,
    "lower_shadow_pct": 0.11468531468530797,
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
    "timestamp": "2025-02-25 09:15:00+00:00",
    "candle_index": 37,
    "open": 2398.01,
    "high": 2401.6,
    "low": 2378.01,
    "close": 2383.68,
    "body_pct": 0.6074607884697147,
    "upper_shadow_pct": 0.15218312844424492,
    "lower_shadow_pct": 0.24035608308604037,
    "position_in_window": 0.3895,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-25 09:45:00+00:00",
    "candle_index": 39,
    "open": 2392.8,
    "high": 2399.4,
    "low": 2381.17,
    "close": 2383.54,
    "body_pct": 0.5079539221064294,
    "upper_shadow_pct": 0.362040592430055,
    "lower_shadow_pct": 0.13000548546351556,
    "position_in_window": 0.4105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-25 10:00:00+00:00",
    "candle_index": 40,
    "open": 2383.53,
    "high": 2406.96,
    "low": 2366.26,
    "close": 2376.31,
    "body_pct": 0.17739557739558445,
    "upper_shadow_pct": 0.5756756756756742,
    "lower_shadow_pct": 0.24692874692874134,
    "position_in_window": 0.4211,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "CLOSE_NEAR_LOW",
      "SPINNING_TOP_INDECISION"
    ]
  }
]
```
### Doji / spinning top / small body cluster
```json
{
  "doji_count": 9,
  "doji_ratio": 0.09375,
  "small_body_count": 35,
  "small_body_ratio": 0.3645833333333333,
  "bullish_body_total": 520.8299999999995,
  "bearish_body_total": 538.4699999999998
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
      "previous_timestamp": "2025-02-25 01:30:00+00:00",
      "timestamp": "2025-02-25 01:45:00+00:00",
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
      "previous_timestamp": "2025-02-25 01:30:00+00:00",
      "timestamp": "2025-02-25 01:45:00+00:00",
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
      "previous_timestamp": "2025-02-25 02:00:00+00:00",
      "timestamp": "2025-02-25 02:15:00+00:00",
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
      "previous_timestamp": "2025-02-25 02:00:00+00:00",
      "timestamp": "2025-02-25 02:15:00+00:00",
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
      "previous_timestamp": "2025-02-25 02:45:00+00:00",
      "timestamp": "2025-02-25 03:00:00+00:00",
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
      "previous_timestamp": "2025-02-25 02:45:00+00:00",
      "timestamp": "2025-02-25 03:00:00+00:00",
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
      "previous_timestamp": "2025-02-25 03:15:00+00:00",
      "timestamp": "2025-02-25 03:30:00+00:00",
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
      "previous_timestamp": "2025-02-25 03:15:00+00:00",
      "timestamp": "2025-02-25 03:30:00+00:00",
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
      "previous_timestamp": "2025-02-25 06:30:00+00:00",
      "timestamp": "2025-02-25 06:45:00+00:00",
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
      "previous_timestamp": "2025-02-25 06:30:00+00:00",
      "timestamp": "2025-02-25 06:45:00+00:00",
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
      "previous_timestamp": "2025-02-25 08:30:00+00:00",
      "timestamp": "2025-02-25 08:45:00+00:00",
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
      "previous_timestamp": "2025-02-25 08:30:00+00:00",
      "timestamp": "2025-02-25 08:45:00+00:00",
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
      "previous_timestamp": "2025-02-25 09:00:00+00:00",
      "timestamp": "2025-02-25 09:15:00+00:00",
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
      "previous_timestamp": "2025-02-25 09:00:00+00:00",
      "timestamp": "2025-02-25 09:15:00+00:00",
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
      "previous_timestamp": "2025-02-25 10:00:00+00:00",
      "timestamp": "2025-02-25 10:15:00+00:00",
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
      "previous_timestamp": "2025-02-25 10:00:00+00:00",
      "timestamp": "2025-02-25 10:15:00+00:00",
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
      "previous_timestamp": "2025-02-25 11:15:00+00:00",
      "timestamp": "2025-02-25 11:30:00+00:00",
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
      "previous_timestamp": "2025-02-25 11:15:00+00:00",
      "timestamp": "2025-02-25 11:30:00+00:00",
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
      "previous_timestamp": "2025-02-25 12:30:00+00:00",
      "timestamp": "2025-02-25 12:45:00+00:00",
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
      "previous_timestamp": "2025-02-25 12:30:00+00:00",
      "timestamp": "2025-02-25 12:45:00+00:00",
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
        "2025-02-25 11:00:00+00:00",
        "2025-02-25 11:15:00+00:00",
        "2025-02-25 11:30:00+00:00"
      ],
      "trend_context_evaluated": false,
      "follow_through_evaluated": false,
      "catalog_scope": "NISON_CHAPTERS_4_TO_8"
    }
  }
]
```
### Candle context conclusion
CLOSE_NEAR_LOW, SMALL_BODY_INDECISION, LONG_LOWER_SHADOW_REJECTION, CLOSE_NEAR_HIGH, SPINNING_TOP_INDECISION, HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED, CANDLE_PATTERN_NEEDS_TREND_CONTEXT, DOJI_INDECISION, LONG_UPPER_SHADOW_REJECTION, STRONG_BULLISH_CANDLE_BODY, SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED, STRONG_BEARISH_CANDLE_BODY, BEARISH_ENGULFING_CONTEXT, ENGULFING_WITHOUT_FOLLOW_THROUGH, BULLISH_ENGULFING_CONTEXT, BULLISH_BELT_HOLD_CONTEXT_REQUIRED, HANGING_MAN_LIKE_CONTEXT_REQUIRED, REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH, LONG_LEGGED_DOJI_CONTEXT, RICKSHAW_MAN_DOJI_CONTEXT, INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED, GRAVESTONE_DOJI_CONTEXT, BEARISH_BELT_HOLD_CONTEXT_REQUIRED, DRAGONFLY_DOJI_CONTEXT, TWEEZERS_TOP_CONTEXT_REQUIRED, TWEEZERS_BOTTOM_CONTEXT_REQUIRED, DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT, DOJI_TOP_CONTEXT_REQUIRED, BEARISH_SEPARATING_LINES_CONTEXT, BULLISH_HARAMI_CONTEXT, HARAMI_CROSS_CONTEXT, BULLISH_SEPARATING_LINES_CONTEXT, BEARISH_HARAMI_CONTEXT, MORNING_STAR_LIKE_CONTEXT, THREE_ADVANCING_WHITE_SOLDIERS_CONTEXT, THREE_MOUNTAINS_CONTEXT_REQUIRED, THREE_BUDDHA_TOP_CONTEXT_REQUIRED, THREE_RIVERS_CONTEXT_REQUIRED, SMALL_BODY_CLUSTER, LOW_DIRECTIONAL_PROGRESS

## 2. Altunina trend context
### Swing structure
```json
[
  {
    "index": 4,
    "timestamp": "2025-02-25 01:00:00+00:00",
    "price": 2470.5,
    "point_type": "LOW"
  },
  {
    "index": 6,
    "timestamp": "2025-02-25 01:30:00+00:00",
    "price": 2513.2,
    "point_type": "HIGH"
  },
  {
    "index": 9,
    "timestamp": "2025-02-25 02:15:00+00:00",
    "price": 2475.0,
    "point_type": "LOW"
  },
  {
    "index": 11,
    "timestamp": "2025-02-25 02:45:00+00:00",
    "price": 2524.34,
    "point_type": "HIGH"
  },
  {
    "index": 14,
    "timestamp": "2025-02-25 03:30:00+00:00",
    "price": 2486.67,
    "point_type": "LOW"
  },
  {
    "index": 15,
    "timestamp": "2025-02-25 03:45:00+00:00",
    "price": 2513.8,
    "point_type": "HIGH"
  },
  {
    "index": 16,
    "timestamp": "2025-02-25 04:00:00+00:00",
    "price": 2479.4,
    "point_type": "LOW"
  },
  {
    "index": 17,
    "timestamp": "2025-02-25 04:15:00+00:00",
    "price": 2505.1,
    "point_type": "HIGH"
  },
  {
    "index": 18,
    "timestamp": "2025-02-25 04:30:00+00:00",
    "price": 2480.2,
    "point_type": "LOW"
  },
  {
    "index": 21,
    "timestamp": "2025-02-25 05:15:00+00:00",
    "price": 2512.9,
    "point_type": "HIGH"
  },
  {
    "index": 29,
    "timestamp": "2025-02-25 07:15:00+00:00",
    "price": 2313.49,
    "point_type": "LOW"
  },
  {
    "index": 34,
    "timestamp": "2025-02-25 08:30:00+00:00",
    "price": 2417.33,
    "point_type": "HIGH"
  },
  {
    "index": 37,
    "timestamp": "2025-02-25 09:15:00+00:00",
    "price": 2378.01,
    "point_type": "LOW"
  },
  {
    "index": 40,
    "timestamp": "2025-02-25 10:00:00+00:00",
    "price": 2406.96,
    "point_type": "HIGH"
  },
  {
    "index": 41,
    "timestamp": "2025-02-25 10:15:00+00:00",
    "price": 2357.05,
    "point_type": "LOW"
  },
  {
    "index": 42,
    "timestamp": "2025-02-25 10:30:00+00:00",
    "price": 2411.8,
    "point_type": "HIGH"
  },
  {
    "index": 45,
    "timestamp": "2025-02-25 11:15:00+00:00",
    "price": 2368.88,
    "point_type": "LOW"
  },
  {
    "index": 48,
    "timestamp": "2025-02-25 12:00:00+00:00",
    "price": 2448.95,
    "point_type": "HIGH"
  },
  {
    "index": 50,
    "timestamp": "2025-02-25 12:30:00+00:00",
    "price": 2419.56,
    "point_type": "LOW"
  },
  {
    "index": 52,
    "timestamp": "2025-02-25 13:00:00+00:00",
    "price": 2443.51,
    "point_type": "HIGH"
  },
  {
    "index": 54,
    "timestamp": "2025-02-25 13:30:00+00:00",
    "price": 2412.03,
    "point_type": "LOW"
  },
  {
    "index": 57,
    "timestamp": "2025-02-25 14:15:00+00:00",
    "price": 2429.3,
    "point_type": "HIGH"
  },
  {
    "index": 60,
    "timestamp": "2025-02-25 15:00:00+00:00",
    "price": 2361.89,
    "point_type": "LOW"
  },
  {
    "index": 63,
    "timestamp": "2025-02-25 15:45:00+00:00",
    "price": 2427.67,
    "point_type": "HIGH"
  },
  {
    "index": 66,
    "timestamp": "2025-02-25 16:30:00+00:00",
    "price": 2383.4,
    "point_type": "LOW"
  },
  {
    "index": 67,
    "timestamp": "2025-02-25 16:45:00+00:00",
    "price": 2435.39,
    "point_type": "HIGH"
  },
  {
    "index": 68,
    "timestamp": "2025-02-25 17:00:00+00:00",
    "price": 2411.23,
    "point_type": "LOW"
  },
  {
    "index": 70,
    "timestamp": "2025-02-25 17:30:00+00:00",
    "price": 2443.0,
    "point_type": "HIGH"
  },
  {
    "index": 71,
    "timestamp": "2025-02-25 17:45:00+00:00",
    "price": 2413.28,
    "point_type": "LOW"
  },
  {
    "index": 72,
    "timestamp": "2025-02-25 18:00:00+00:00",
    "price": 2435.9,
    "point_type": "HIGH"
  },
  {
    "index": 74,
    "timestamp": "2025-02-25 18:30:00+00:00",
    "price": 2404.04,
    "point_type": "LOW"
  },
  {
    "index": 76,
    "timestamp": "2025-02-25 19:00:00+00:00",
    "price": 2435.19,
    "point_type": "HIGH"
  },
  {
    "index": 77,
    "timestamp": "2025-02-25 19:15:00+00:00",
    "price": 2411.78,
    "point_type": "LOW"
  },
  {
    "index": 82,
    "timestamp": "2025-02-25 20:30:00+00:00",
    "price": 2516.87,
    "point_type": "HIGH"
  },
  {
    "index": 84,
    "timestamp": "2025-02-25 21:00:00+00:00",
    "price": 2481.65,
    "point_type": "LOW"
  },
  {
    "index": 88,
    "timestamp": "2025-02-25 22:00:00+00:00",
    "price": 2533.49,
    "point_type": "HIGH"
  },
  {
    "index": 91,
    "timestamp": "2025-02-25 22:45:00+00:00",
    "price": 2499.09,
    "point_type": "LOW"
  },
  {
    "index": 92,
    "timestamp": "2025-02-25 23:00:00+00:00",
    "price": 2522.24,
    "point_type": "HIGH"
  },
  {
    "index": 94,
    "timestamp": "2025-02-25 23:30:00+00:00",
    "price": 2494.17,
    "point_type": "LOW"
  }
]
```
### Higher highs / lower highs
```json
{
  "raw_swing_count": 46,
  "swing_count": 39,
  "leg_count": 38,
  "structure_direction": "SIDEWAYS_STRUCTURE",
  "total_movement": 1715.909999999998,
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
    "lower_price": 2404.04,
    "upper_price": 2417.33,
    "mid_price": 2411.0562500000005,
    "touch_count": 8,
    "source_indexes": [
      34,
      40,
      42,
      54,
      68,
      71,
      74,
      77
    ],
    "zone_width": 13.289999999999964,
    "zone_width_ratio": 0.00551210698630526,
    "formed_at_index": 77,
    "first_touch_index": 34,
    "last_touch_index": 77,
    "source_point_types": [
      "HIGH",
      "HIGH",
      "HIGH",
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
    "lower_price": 2505.1,
    "upper_price": 2516.87,
    "mid_price": 2511.548571428571,
    "touch_count": 7,
    "source_indexes": [
      6,
      8,
      15,
      17,
      21,
      24,
      82
    ],
    "zone_width": 11.769999999999982,
    "zone_width_ratio": 0.004686351732909229,
    "formed_at_index": 82,
    "first_touch_index": 6,
    "last_touch_index": 82,
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
  "lower_boundary": 2404.04,
  "upper_boundary": 2516.87,
  "midline": 2460.455,
  "width": 112.82999999999993,
  "width_ratio": 0.04585737190885423,
  "touch_count": 15,
  "inside_close_ratio": 0.7142857142857143,
  "formed_at_index": 82,
  "first_touch_index": 6,
  "duration_candles": 77,
  "boundary_alternation_count": 2
}
```
### Range high / low
See trading range object above.
### Price position inside range
```json
{
  "swing_count": 46,
  "zone_count": 12,
  "range_detected": true,
  "range_formed_at_index": 82,
  "range_duration_candles": 77,
  "inside_close_ratio": 0.7142857142857143,
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
  "analysis_start_index": 83,
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
Count: 30
### Bearish evidence
Count: 34
### Neutral/range evidence
Count: 362
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
  "total_evidence_count": 426,
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
  "FLAT": 0.6428571428571429,
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
    "score": 0.6428571428571429
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
