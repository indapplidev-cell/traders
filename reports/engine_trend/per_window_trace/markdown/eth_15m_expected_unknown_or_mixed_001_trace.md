# eth_15m_expected_unknown_or_mixed_001 вЂ” Market Evidence Trace

## Window
- Symbol: ETHUSDT
- Interval: 15m
- Period: 2025-02-03T00:00:00+00:00 вЂ” 2025-02-03T23:45:00+00:00
- Reference label: EXPECTED_UNKNOWN_OR_MIXED
- Selection reason: deterministic expected_unknown_or_mixed OHLC rule

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
    "timestamp": "2025-02-03 00:00:00+00:00",
    "candle_index": 0,
    "open": 2869.68,
    "high": 2872.75,
    "low": 2849.86,
    "close": 2851.77,
    "body_pct": 0.7824377457404961,
    "upper_shadow_pct": 0.13411970292705028,
    "lower_shadow_pct": 0.0834425513324537,
    "position_in_window": 0.0,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-03 00:15:00+00:00",
    "candle_index": 1,
    "open": 2851.77,
    "high": 2858.73,
    "low": 2801.0,
    "close": 2839.26,
    "body_pct": 0.2166984236965141,
    "upper_shadow_pct": 0.12056123332755991,
    "lower_shadow_pct": 0.662740342975926,
    "position_in_window": 0.0105,
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
    "timestamp": "2025-02-03 00:30:00+00:00",
    "candle_index": 2,
    "open": 2839.25,
    "high": 2842.47,
    "low": 2768.55,
    "close": 2781.16,
    "body_pct": 0.7858495670995731,
    "upper_shadow_pct": 0.04356060606060358,
    "lower_shadow_pct": 0.1705898268398233,
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
    "timestamp": "2025-02-03 01:00:00+00:00",
    "candle_index": 4,
    "open": 2823.5,
    "high": 2844.28,
    "low": 2813.24,
    "close": 2813.93,
    "body_pct": 0.3083118556701042,
    "upper_shadow_pct": 0.6694587628865953,
    "lower_shadow_pct": 0.022229381443300427,
    "position_in_window": 0.0421,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-03 01:15:00+00:00",
    "candle_index": 5,
    "open": 2813.92,
    "high": 2816.17,
    "low": 2780.08,
    "close": 2784.77,
    "body_pct": 0.807702964810196,
    "upper_shadow_pct": 0.062344139650872564,
    "lower_shadow_pct": 0.12995289553893144,
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
    "timestamp": "2025-02-03 01:30:00+00:00",
    "candle_index": 6,
    "open": 2784.78,
    "high": 2802.89,
    "low": 2733.7,
    "close": 2749.77,
    "body_pct": 0.5059979765862146,
    "upper_shadow_pct": 0.26174302644890385,
    "lower_shadow_pct": 0.2322589969648815,
    "position_in_window": 0.0632,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-03 02:00:00+00:00",
    "candle_index": 8,
    "open": 2493.89,
    "high": 2563.57,
    "low": 2125.01,
    "close": 2452.71,
    "body_pct": 0.0938982123312656,
    "upper_shadow_pct": 0.1588836191171112,
    "lower_shadow_pct": 0.7472181685516232,
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
    "timestamp": "2025-02-03 02:15:00+00:00",
    "candle_index": 9,
    "open": 2452.59,
    "high": 2511.8,
    "low": 2420.0,
    "close": 2462.92,
    "body_pct": 0.11252723311546739,
    "upper_shadow_pct": 0.5324618736383444,
    "lower_shadow_pct": 0.35501089324618823,
    "position_in_window": 0.0947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2025-02-03 02:30:00+00:00",
    "candle_index": 10,
    "open": 2462.91,
    "high": 2514.96,
    "low": 2436.21,
    "close": 2498.52,
    "body_pct": 0.4521904761904778,
    "upper_shadow_pct": 0.20876190476190545,
    "lower_shadow_pct": 0.3390476190476167,
    "position_in_window": 0.1053,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-02-03 02:45:00+00:00",
    "candle_index": 11,
    "open": 2498.54,
    "high": 2505.57,
    "low": 2455.18,
    "close": 2486.64,
    "body_pct": 0.23615796785076432,
    "upper_shadow_pct": 0.1395118078983956,
    "lower_shadow_pct": 0.6243302242508401,
    "position_in_window": 0.1158,
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
    "timestamp": "2025-02-03 03:15:00+00:00",
    "candle_index": 13,
    "open": 2507.8,
    "high": 2544.35,
    "low": 2504.36,
    "close": 2516.58,
    "body_pct": 0.21955488872217538,
    "upper_shadow_pct": 0.6944236059014787,
    "lower_shadow_pct": 0.08602150537634592,
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
    "timestamp": "2025-02-03 03:30:00+00:00",
    "candle_index": 14,
    "open": 2516.58,
    "high": 2522.35,
    "low": 2502.49,
    "close": 2515.61,
    "body_pct": 0.048841893252759,
    "upper_shadow_pct": 0.2905337361530687,
    "lower_shadow_pct": 0.6606243705941722,
    "position_in_window": 0.1474,
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
    "timestamp": "2025-02-03 03:45:00+00:00",
    "candle_index": 15,
    "open": 2515.62,
    "high": 2543.08,
    "low": 2514.67,
    "close": 2527.12,
    "body_pct": 0.404787046814504,
    "upper_shadow_pct": 0.5617740232312608,
    "lower_shadow_pct": 0.03343892995423523,
    "position_in_window": 0.1579,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2025-02-03 04:00:00+00:00",
    "candle_index": 16,
    "open": 2527.2,
    "high": 2565.5,
    "low": 2506.0,
    "close": 2513.91,
    "body_pct": 0.2233613445378145,
    "upper_shadow_pct": 0.6436974789915997,
    "lower_shadow_pct": 0.1329411764705858,
    "position_in_window": 0.1684,
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
    "timestamp": "2025-02-03 04:15:00+00:00",
    "candle_index": 17,
    "open": 2513.9,
    "high": 2521.95,
    "low": 2487.44,
    "close": 2489.88,
    "body_pct": 0.6960301361924123,
    "upper_shadow_pct": 0.23326572008112959,
    "lower_shadow_pct": 0.07070414372645817,
    "position_in_window": 0.1789,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-03 04:45:00+00:00",
    "candle_index": 19,
    "open": 2473.81,
    "high": 2485.71,
    "low": 2448.97,
    "close": 2452.65,
    "body_pct": 0.5759390310288437,
    "upper_shadow_pct": 0.3238976592270009,
    "lower_shadow_pct": 0.10016330974415534,
    "position_in_window": 0.2,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-03 05:45:00+00:00",
    "candle_index": 23,
    "open": 2477.81,
    "high": 2521.88,
    "low": 2474.95,
    "close": 2515.01,
    "body_pct": 0.7926699339441731,
    "upper_shadow_pct": 0.14638823780097696,
    "lower_shadow_pct": 0.06094182825484998,
    "position_in_window": 0.2421,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-02-03 06:00:00+00:00",
    "candle_index": 24,
    "open": 2515.0,
    "high": 2515.1,
    "low": 2483.91,
    "close": 2501.91,
    "body_pct": 0.419685796729725,
    "upper_shadow_pct": 0.0032061558191698904,
    "lower_shadow_pct": 0.5771080474511051,
    "position_in_window": 0.2526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2025-02-03 06:15:00+00:00",
    "candle_index": 25,
    "open": 2501.91,
    "high": 2530.17,
    "low": 2492.25,
    "close": 2522.51,
    "body_pct": 0.5432489451476878,
    "upper_shadow_pct": 0.20200421940927848,
    "lower_shadow_pct": 0.25474683544303367,
    "position_in_window": 0.2632,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-02-03 06:30:00+00:00",
    "candle_index": 26,
    "open": 2522.5,
    "high": 2537.62,
    "low": 2508.76,
    "close": 2511.1,
    "body_pct": 0.39501039501040264,
    "upper_shadow_pct": 0.523908523908526,
    "lower_shadow_pct": 0.08108108108107129,
    "position_in_window": 0.2737,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-03 06:45:00+00:00",
    "candle_index": 27,
    "open": 2511.1,
    "high": 2529.88,
    "low": 2508.02,
    "close": 2525.63,
    "body_pct": 0.6646843549862815,
    "upper_shadow_pct": 0.1944190301921306,
    "lower_shadow_pct": 0.1408966148215878,
    "position_in_window": 0.2842,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-02-03 07:00:00+00:00",
    "candle_index": 28,
    "open": 2525.62,
    "high": 2548.18,
    "low": 2520.99,
    "close": 2544.49,
    "body_pct": 0.6940051489518151,
    "upper_shadow_pct": 0.1357116586980525,
    "lower_shadow_pct": 0.1702831923501324,
    "position_in_window": 0.2947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-02-03 07:15:00+00:00",
    "candle_index": 29,
    "open": 2544.5,
    "high": 2570.79,
    "low": 2543.74,
    "close": 2566.65,
    "body_pct": 0.8188539741219941,
    "upper_shadow_pct": 0.1530499075785525,
    "lower_shadow_pct": 0.02809611829945335,
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
    "timestamp": "2025-02-03 07:45:00+00:00",
    "candle_index": 31,
    "open": 2586.89,
    "high": 2632.8,
    "low": 2583.77,
    "close": 2622.35,
    "body_pct": 0.7232306750968772,
    "upper_shadow_pct": 0.21313481541913584,
    "lower_shadow_pct": 0.06363450948398691,
    "position_in_window": 0.3263,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-02-03 08:15:00+00:00",
    "candle_index": 33,
    "open": 2600.0,
    "high": 2607.06,
    "low": 2558.12,
    "close": 2561.76,
    "body_pct": 0.7813649366571258,
    "upper_shadow_pct": 0.14425827543931216,
    "lower_shadow_pct": 0.07437678790356198,
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
    "timestamp": "2025-02-03 08:45:00+00:00",
    "candle_index": 35,
    "open": 2541.58,
    "high": 2573.76,
    "low": 2541.36,
    "close": 2572.8,
    "body_pct": 0.9635802469135853,
    "upper_shadow_pct": 0.029629629629630668,
    "lower_shadow_pct": 0.006790123456783929,
    "position_in_window": 0.3684,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-02-03 09:15:00+00:00",
    "candle_index": 37,
    "open": 2600.54,
    "high": 2600.92,
    "low": 2563.55,
    "close": 2587.44,
    "body_pct": 0.35054856837034915,
    "upper_shadow_pct": 0.010168584426013118,
    "lower_shadow_pct": 0.6392828472036377,
    "position_in_window": 0.3895,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2025-02-03 09:30:00+00:00",
    "candle_index": 38,
    "open": 2587.45,
    "high": 2601.31,
    "low": 2579.0,
    "close": 2588.41,
    "body_pct": 0.04303003137606628,
    "upper_shadow_pct": 0.5782160466158728,
    "lower_shadow_pct": 0.3787539220080609,
    "position_in_window": 0.4,
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
    "timestamp": "2025-02-03 10:00:00+00:00",
    "candle_index": 40,
    "open": 2570.91,
    "high": 2580.96,
    "low": 2562.31,
    "close": 2578.99,
    "body_pct": 0.43324396782841224,
    "upper_shadow_pct": 0.10563002680966461,
    "lower_shadow_pct": 0.46112600536192316,
    "position_in_window": 0.4211,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-02-03 10:15:00+00:00",
    "candle_index": 41,
    "open": 2579.0,
    "high": 2594.19,
    "low": 2566.72,
    "close": 2586.96,
    "body_pct": 0.2897706589006175,
    "upper_shadow_pct": 0.26319621405169097,
    "lower_shadow_pct": 0.44703312704769155,
    "position_in_window": 0.4316,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION"
    ]
  }
]
```
### Doji / spinning top / small body cluster
```json
{
  "doji_count": 9,
  "doji_ratio": 0.09375,
  "small_body_count": 25,
  "small_body_ratio": 0.2604166666666667,
  "bullish_body_total": 1017.0000000000014,
  "bearish_body_total": 1008.9600000000005
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
      "previous_timestamp": "2025-02-03 03:45:00+00:00",
      "timestamp": "2025-02-03 04:00:00+00:00",
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
      "previous_timestamp": "2025-02-03 03:45:00+00:00",
      "timestamp": "2025-02-03 04:00:00+00:00",
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
      "previous_timestamp": "2025-02-03 05:30:00+00:00",
      "timestamp": "2025-02-03 05:45:00+00:00",
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
      "previous_timestamp": "2025-02-03 05:30:00+00:00",
      "timestamp": "2025-02-03 05:45:00+00:00",
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
      "previous_timestamp": "2025-02-03 06:00:00+00:00",
      "timestamp": "2025-02-03 06:15:00+00:00",
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
      "previous_timestamp": "2025-02-03 06:00:00+00:00",
      "timestamp": "2025-02-03 06:15:00+00:00",
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
      "previous_timestamp": "2025-02-03 06:30:00+00:00",
      "timestamp": "2025-02-03 06:45:00+00:00",
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
      "previous_timestamp": "2025-02-03 06:30:00+00:00",
      "timestamp": "2025-02-03 06:45:00+00:00",
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
      "previous_timestamp": "2025-02-03 08:30:00+00:00",
      "timestamp": "2025-02-03 08:45:00+00:00",
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
      "previous_timestamp": "2025-02-03 08:30:00+00:00",
      "timestamp": "2025-02-03 08:45:00+00:00",
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
      "previous_timestamp": "2025-02-03 11:15:00+00:00",
      "timestamp": "2025-02-03 11:30:00+00:00",
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
      "previous_timestamp": "2025-02-03 11:15:00+00:00",
      "timestamp": "2025-02-03 11:30:00+00:00",
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
      "previous_timestamp": "2025-02-03 11:45:00+00:00",
      "timestamp": "2025-02-03 12:00:00+00:00",
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
      "previous_timestamp": "2025-02-03 11:45:00+00:00",
      "timestamp": "2025-02-03 12:00:00+00:00",
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
      "previous_timestamp": "2025-02-03 13:15:00+00:00",
      "timestamp": "2025-02-03 13:30:00+00:00",
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
      "previous_timestamp": "2025-02-03 13:15:00+00:00",
      "timestamp": "2025-02-03 13:30:00+00:00",
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
      "previous_timestamp": "2025-02-03 17:30:00+00:00",
      "timestamp": "2025-02-03 17:45:00+00:00",
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
      "previous_timestamp": "2025-02-03 17:30:00+00:00",
      "timestamp": "2025-02-03 17:45:00+00:00",
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
      "previous_timestamp": "2025-02-03 18:00:00+00:00",
      "timestamp": "2025-02-03 18:15:00+00:00",
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
      "previous_timestamp": "2025-02-03 18:00:00+00:00",
      "timestamp": "2025-02-03 18:15:00+00:00",
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
STRONG_BEARISH_CANDLE_BODY, CLOSE_NEAR_LOW, LONG_LOWER_SHADOW_REJECTION, SMALL_BODY_INDECISION, SPINNING_TOP_INDECISION, LONG_UPPER_SHADOW_REJECTION, DOJI_INDECISION, CLOSE_NEAR_HIGH, SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED, CANDLE_PATTERN_NEEDS_TREND_CONTEXT, STRONG_BULLISH_CANDLE_BODY, BEARISH_ENGULFING_CONTEXT, ENGULFING_WITHOUT_FOLLOW_THROUGH, BULLISH_ENGULFING_CONTEXT, BEARISH_BELT_HOLD_CONTEXT_REQUIRED, BULLISH_BELT_HOLD_CONTEXT_REQUIRED, INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED, REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH, LONG_LEGGED_DOJI_CONTEXT, RICKSHAW_MAN_DOJI_CONTEXT, TWEEZERS_TOP_CONTEXT_REQUIRED, TWEEZERS_BOTTOM_CONTEXT_REQUIRED, BULLISH_SEPARATING_LINES_CONTEXT, BEARISH_SEPARATING_LINES_CONTEXT, BULLISH_HARAMI_CONTEXT, BEARISH_HARAMI_CONTEXT, HARAMI_CROSS_CONTEXT, DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT, DOJI_TOP_CONTEXT_REQUIRED, THREE_ADVANCING_WHITE_SOLDIERS_CONTEXT, RISING_THREE_METHODS_CONTEXT

## 2. Altunina trend context
### Swing structure
```json
[
  {
    "index": 2,
    "timestamp": "2025-02-03 00:30:00+00:00",
    "price": 2768.55,
    "point_type": "LOW"
  },
  {
    "index": 3,
    "timestamp": "2025-02-03 00:45:00+00:00",
    "price": 2845.91,
    "point_type": "HIGH"
  },
  {
    "index": 8,
    "timestamp": "2025-02-03 02:00:00+00:00",
    "price": 2125.01,
    "point_type": "LOW"
  },
  {
    "index": 13,
    "timestamp": "2025-02-03 03:15:00+00:00",
    "price": 2544.35,
    "point_type": "HIGH"
  },
  {
    "index": 14,
    "timestamp": "2025-02-03 03:30:00+00:00",
    "price": 2502.49,
    "point_type": "LOW"
  },
  {
    "index": 16,
    "timestamp": "2025-02-03 04:00:00+00:00",
    "price": 2565.5,
    "point_type": "HIGH"
  },
  {
    "index": 20,
    "timestamp": "2025-02-03 05:00:00+00:00",
    "price": 2447.25,
    "point_type": "LOW"
  },
  {
    "index": 26,
    "timestamp": "2025-02-03 06:30:00+00:00",
    "price": 2537.62,
    "point_type": "HIGH"
  },
  {
    "index": 27,
    "timestamp": "2025-02-03 06:45:00+00:00",
    "price": 2508.02,
    "point_type": "LOW"
  },
  {
    "index": 31,
    "timestamp": "2025-02-03 07:45:00+00:00",
    "price": 2632.8,
    "point_type": "HIGH"
  },
  {
    "index": 34,
    "timestamp": "2025-02-03 08:30:00+00:00",
    "price": 2526.16,
    "point_type": "LOW"
  },
  {
    "index": 36,
    "timestamp": "2025-02-03 09:00:00+00:00",
    "price": 2616.5,
    "point_type": "HIGH"
  },
  {
    "index": 37,
    "timestamp": "2025-02-03 09:15:00+00:00",
    "price": 2563.55,
    "point_type": "LOW"
  },
  {
    "index": 38,
    "timestamp": "2025-02-03 09:30:00+00:00",
    "price": 2601.31,
    "point_type": "HIGH"
  },
  {
    "index": 39,
    "timestamp": "2025-02-03 09:45:00+00:00",
    "price": 2557.87,
    "point_type": "LOW"
  },
  {
    "index": 43,
    "timestamp": "2025-02-03 10:45:00+00:00",
    "price": 2614.8,
    "point_type": "HIGH"
  },
  {
    "index": 47,
    "timestamp": "2025-02-03 11:45:00+00:00",
    "price": 2577.1,
    "point_type": "LOW"
  },
  {
    "index": 49,
    "timestamp": "2025-02-03 12:15:00+00:00",
    "price": 2636.27,
    "point_type": "HIGH"
  },
  {
    "index": 54,
    "timestamp": "2025-02-03 13:30:00+00:00",
    "price": 2547.22,
    "point_type": "LOW"
  },
  {
    "index": 55,
    "timestamp": "2025-02-03 13:45:00+00:00",
    "price": 2581.78,
    "point_type": "HIGH"
  },
  {
    "index": 57,
    "timestamp": "2025-02-03 14:15:00+00:00",
    "price": 2529.39,
    "point_type": "LOW"
  },
  {
    "index": 63,
    "timestamp": "2025-02-03 15:45:00+00:00",
    "price": 2728.0,
    "point_type": "HIGH"
  },
  {
    "index": 64,
    "timestamp": "2025-02-03 16:00:00+00:00",
    "price": 2678.39,
    "point_type": "LOW"
  },
  {
    "index": 67,
    "timestamp": "2025-02-03 16:45:00+00:00",
    "price": 2733.9,
    "point_type": "HIGH"
  },
  {
    "index": 70,
    "timestamp": "2025-02-03 17:30:00+00:00",
    "price": 2668.06,
    "point_type": "LOW"
  },
  {
    "index": 79,
    "timestamp": "2025-02-03 19:45:00+00:00",
    "price": 2770.26,
    "point_type": "HIGH"
  },
  {
    "index": 83,
    "timestamp": "2025-02-03 20:45:00+00:00",
    "price": 2695.61,
    "point_type": "LOW"
  },
  {
    "index": 90,
    "timestamp": "2025-02-03 22:30:00+00:00",
    "price": 2921.0,
    "point_type": "HIGH"
  },
  {
    "index": 91,
    "timestamp": "2025-02-03 22:45:00+00:00",
    "price": 2853.52,
    "point_type": "LOW"
  },
  {
    "index": 93,
    "timestamp": "2025-02-03 23:15:00+00:00",
    "price": 2894.0,
    "point_type": "HIGH"
  },
  {
    "index": 94,
    "timestamp": "2025-02-03 23:30:00+00:00",
    "price": 2852.61,
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
  "total_movement": 3267.5600000000018,
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
    "lower_price": 2557.87,
    "upper_price": 2565.5,
    "mid_price": 2562.306666666667,
    "touch_count": 3,
    "source_indexes": [
      16,
      37,
      39
    ],
    "zone_width": 7.630000000000109,
    "zone_width_ratio": 0.002977785641063043,
    "formed_at_index": 39,
    "first_touch_index": 16,
    "last_touch_index": 39,
    "source_point_types": [
      "HIGH",
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
    "lower_price": 2763.62,
    "upper_price": 2770.26,
    "mid_price": 2767.476666666667,
    "touch_count": 3,
    "source_indexes": [
      2,
      77,
      79
    ],
    "zone_width": 6.640000000000327,
    "zone_width_ratio": 0.002399297555053277,
    "formed_at_index": 79,
    "first_touch_index": 2,
    "last_touch_index": 79,
    "source_point_types": [
      "LOW",
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
  "lower_boundary": 2557.87,
  "upper_boundary": 2770.26,
  "midline": 2664.065,
  "width": 212.39000000000033,
  "width_ratio": 0.07972403075750792,
  "touch_count": 6,
  "inside_close_ratio": 0.6153846153846154,
  "formed_at_index": 79,
  "first_touch_index": 2,
  "duration_candles": 78,
  "boundary_alternation_count": 2
}
```
### Range high / low
See trading range object above.
### Price position inside range
```json
{
  "swing_count": 38,
  "zone_count": 13,
  "range_detected": true,
  "range_formed_at_index": 79,
  "range_duration_candles": 78,
  "inside_close_ratio": 0.6153846153846154,
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
  "breakout_index": 87,
  "boundary_price": 2770.26,
  "breakout_close": 2817.69,
  "distance_ratio": 0.01712113664421384,
  "returned_to_range": false,
  "follow_through_count": 5,
  "evidence": [
    {
      "source": "SCHWAGER",
      "code": "SCHWAGER_BULLISH_RANGE_BREAKOUT_CONTEXT",
      "description": "Closing price moved above the range boundary",
      "contribution": 0.12,
      "metadata": {
        "breakout_index": 87
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
        "distance_ratio": 0.054413665143343865
      }
    }
  ],
  "analysis_start_index": 80,
  "confirmation_method": "CLOSE_COUNT_AND_DISTANCE",
  "confirmation_close_count": 6,
  "extreme_index": 90,
  "extreme_price": 2921.0,
  "maximum_distance_ratio": 0.054413665143343865,
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
SCHWAGER_SUPPORT_ZONE_IDENTIFIED, SCHWAGER_PREVIOUS_EXTREME_ZONE_IDENTIFIED, SCHWAGER_SUPPORT_ZONE_HELD, SCHWAGER_RESISTANCE_ZONE_IDENTIFIED, SCHWAGER_RESISTANCE_ZONE_HELD, SCHWAGER_ZONE_TOO_WIDE, SCHWAGER_TRADING_RANGE_DETECTED, SCHWAGER_PRICE_INSIDE_RANGE, SCHWAGER_RANGE_UPPER_BOUNDARY_HELD, SCHWAGER_RANGE_LOWER_BOUNDARY_HELD, SCHWAGER_RANGE_DURATION_CONFIRMED, SCHWAGER_RANGE_BOUNDARY_ALTERNATION_CONFIRMED, SCHWAGER_BULLISH_RANGE_BREAKOUT_CONTEXT, SCHWAGER_BREAKOUT_REQUIRES_CONFIRMATION, SCHWAGER_BREAKOUT_FOLLOW_THROUGH_CONFIRMED, SCHWAGER_BREAKOUT_CONFIRMED_BY_CLOSE_COUNT, SCHWAGER_BREAKOUT_CONFIRMED_BY_DISTANCE

## 4. BookEvidenceMatrix
### Bullish evidence
Count: 32
### Bearish evidence
Count: 21
### Neutral/range evidence
Count: 298
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
  "total_evidence_count": 351,
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
  "FLAT": 0.5230769230769231,
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
    "score": 0.5230769230769231
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
