# btcusdt_15m_mixed_003 вЂ” Market Evidence Trace

## Window
- Symbol: BTCUSDT
- Interval: 15m
- Period: 2025-02-28T00:00:00+00:00 вЂ” 2025-02-28T23:45:00+00:00
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
    "timestamp": "2025-02-28 00:00:00+00:00",
    "candle_index": 0,
    "open": 84708.57,
    "high": 84892.85,
    "low": 84531.54,
    "close": 84560.58,
    "body_pct": 0.4095928703883098,
    "upper_shadow_pct": 0.5100329357061598,
    "lower_shadow_pct": 0.08037419390553034,
    "position_in_window": 0.0,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-28 00:15:00+00:00",
    "candle_index": 1,
    "open": 84560.58,
    "high": 84788.01,
    "low": 84544.02,
    "close": 84547.16,
    "body_pct": 0.055002254190740466,
    "upper_shadow_pct": 0.9321283659166428,
    "lower_shadow_pct": 0.012869379892616656,
    "position_in_window": 0.0105,
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
    "timestamp": "2025-02-28 00:30:00+00:00",
    "candle_index": 2,
    "open": 84547.17,
    "high": 84689.17,
    "low": 84425.0,
    "close": 84471.7,
    "body_pct": 0.2856872468486265,
    "upper_shadow_pct": 0.5375326494302947,
    "lower_shadow_pct": 0.17678010372107886,
    "position_in_window": 0.0211,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-28 00:45:00+00:00",
    "candle_index": 3,
    "open": 84471.71,
    "high": 84471.71,
    "low": 84214.43,
    "close": 84258.65,
    "body_pct": 0.8281250000000044,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.1718749999999956,
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
    "timestamp": "2025-02-28 01:00:00+00:00",
    "candle_index": 4,
    "open": 84258.65,
    "high": 84405.17,
    "low": 84222.97,
    "close": 84281.72,
    "body_pct": 0.12661909989027087,
    "upper_shadow_pct": 0.6775521405049345,
    "lower_shadow_pct": 0.19582875960479465,
    "position_in_window": 0.0421,
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
    "timestamp": "2025-02-28 01:15:00+00:00",
    "candle_index": 5,
    "open": 84281.71,
    "high": 84283.02,
    "low": 83037.74,
    "close": 83177.26,
    "body_pct": 0.8869089682641756,
    "upper_shadow_pct": 0.001051972247203579,
    "lower_shadow_pct": 0.11203905948862075,
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
    "timestamp": "2025-02-28 01:30:00+00:00",
    "candle_index": 6,
    "open": 83177.27,
    "high": 83242.1,
    "low": 81111.0,
    "close": 82528.0,
    "body_pct": 0.3046642578949849,
    "upper_shadow_pct": 0.030420909389517886,
    "lower_shadow_pct": 0.6649148327154972,
    "position_in_window": 0.0632,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2025-02-28 01:45:00+00:00",
    "candle_index": 7,
    "open": 82528.01,
    "high": 82940.04,
    "low": 81641.26,
    "close": 81661.55,
    "body_pct": 0.6671337716934297,
    "upper_shadow_pct": 0.3172438750211731,
    "lower_shadow_pct": 0.015622353285397194,
    "position_in_window": 0.0737,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-28 02:30:00+00:00",
    "candle_index": 10,
    "open": 81959.76,
    "high": 81975.61,
    "low": 79555.0,
    "close": 80074.41,
    "body_pct": 0.7788739202101912,
    "upper_shadow_pct": 0.006547936264001974,
    "lower_shadow_pct": 0.21457814352580687,
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
    "timestamp": "2025-02-28 02:45:00+00:00",
    "candle_index": 11,
    "open": 80074.41,
    "high": 80836.48,
    "low": 79532.0,
    "close": 80805.5,
    "body_pct": 0.5604455415184585,
    "upper_shadow_pct": 0.023748926775417043,
    "lower_shadow_pct": 0.41580553170612444,
    "position_in_window": 0.1158,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-02-28 03:00:00+00:00",
    "candle_index": 12,
    "open": 80805.5,
    "high": 81539.25,
    "low": 80651.4,
    "close": 81043.44,
    "body_pct": 0.26799571999774824,
    "upper_shadow_pct": 0.5584389254941651,
    "lower_shadow_pct": 0.17356535450808674,
    "position_in_window": 0.1263,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION"
    ]
  },
  {
    "timestamp": "2025-02-28 03:15:00+00:00",
    "candle_index": 13,
    "open": 81043.45,
    "high": 81426.05,
    "low": 80751.72,
    "close": 80928.48,
    "body_pct": 0.17049515815698674,
    "upper_shadow_pct": 0.5673779900049009,
    "lower_shadow_pct": 0.26212685183811235,
    "position_in_window": 0.1368,
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
    "timestamp": "2025-02-28 03:30:00+00:00",
    "candle_index": 14,
    "open": 80928.48,
    "high": 81067.83,
    "low": 80417.86,
    "close": 80957.99,
    "body_pct": 0.045402095481344155,
    "upper_shadow_pct": 0.16899241503453438,
    "lower_shadow_pct": 0.7856054894841215,
    "position_in_window": 0.1474,
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
    "timestamp": "2025-02-28 04:30:00+00:00",
    "candle_index": 18,
    "open": 80337.34,
    "high": 80718.47,
    "low": 79542.02,
    "close": 80716.43,
    "body_pct": 0.3222321390624314,
    "upper_shadow_pct": 0.001734030345537978,
    "lower_shadow_pct": 0.6760338305920306,
    "position_in_window": 0.1895,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-02-28 04:45:00+00:00",
    "candle_index": 19,
    "open": 80716.43,
    "high": 80969.69,
    "low": 80286.78,
    "close": 80410.5,
    "body_pct": 0.44797996807777224,
    "upper_shadow_pct": 0.3708541389055776,
    "lower_shadow_pct": 0.18116589301665012,
    "position_in_window": 0.2,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-28 05:00:00+00:00",
    "candle_index": 20,
    "open": 80410.49,
    "high": 80547.32,
    "low": 79836.0,
    "close": 79840.63,
    "body_pct": 0.8011302929764311,
    "upper_shadow_pct": 0.19236068154979533,
    "lower_shadow_pct": 0.006509025473773564,
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
    "timestamp": "2025-02-28 05:15:00+00:00",
    "candle_index": 21,
    "open": 79840.63,
    "high": 80301.81,
    "low": 79617.99,
    "close": 79781.92,
    "body_pct": 0.08585592699834321,
    "upper_shadow_pct": 0.6744172443040539,
    "lower_shadow_pct": 0.23972682869760292,
    "position_in_window": 0.2211,
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
    "timestamp": "2025-02-28 05:30:00+00:00",
    "candle_index": 22,
    "open": 79782.0,
    "high": 80092.4,
    "low": 79509.0,
    "close": 79889.18,
    "body_pct": 0.1837161467260783,
    "upper_shadow_pct": 0.3483373328762482,
    "lower_shadow_pct": 0.4679465203976735,
    "position_in_window": 0.2316,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2025-02-28 05:45:00+00:00",
    "candle_index": 23,
    "open": 79889.18,
    "high": 79973.8,
    "low": 79152.0,
    "close": 79973.79,
    "body_pct": 0.1029569238257487,
    "upper_shadow_pct": 1.2168410816881469e-05,
    "lower_shadow_pct": 0.8970309077634344,
    "position_in_window": 0.2421,
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
    "timestamp": "2025-02-28 06:00:00+00:00",
    "candle_index": 24,
    "open": 79973.79,
    "high": 80440.44,
    "low": 79566.03,
    "close": 79566.04,
    "body_pct": 0.46631442915794463,
    "upper_shadow_pct": 0.5336741345593107,
    "lower_shadow_pct": 1.1436282744663567e-05,
    "position_in_window": 0.2526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-28 06:15:00+00:00",
    "candle_index": 25,
    "open": 79566.04,
    "high": 79881.27,
    "low": 79222.63,
    "close": 79490.57,
    "body_pct": 0.11458459856672337,
    "upper_shadow_pct": 0.4786074334993483,
    "lower_shadow_pct": 0.40680796793392837,
    "position_in_window": 0.2632,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2025-02-28 06:30:00+00:00",
    "candle_index": 26,
    "open": 79490.57,
    "high": 79859.97,
    "low": 79306.0,
    "close": 79348.0,
    "body_pct": 0.25736050688666656,
    "upper_shadow_pct": 0.6668231131649609,
    "lower_shadow_pct": 0.0758163799483725,
    "position_in_window": 0.2737,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "CLOSE_NEAR_LOW",
      "SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED",
      "CANDLE_PATTERN_NEEDS_TREND_CONTEXT"
    ]
  },
  {
    "timestamp": "2025-02-28 06:45:00+00:00",
    "candle_index": 27,
    "open": 79348.0,
    "high": 79600.0,
    "low": 79034.97,
    "close": 79344.56,
    "body_pct": 0.00608817230943903,
    "upper_shadow_pct": 0.4459940180167434,
    "lower_shadow_pct": 0.5479178096738175,
    "position_in_window": 0.2842,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "DOJI_INDECISION"
    ]
  },
  {
    "timestamp": "2025-02-28 07:15:00+00:00",
    "candle_index": 29,
    "open": 79745.84,
    "high": 80275.72,
    "low": 79388.18,
    "close": 79500.01,
    "body_pct": 0.2769790657322481,
    "upper_shadow_pct": 0.5970209793361424,
    "lower_shadow_pct": 0.12599995493160954,
    "position_in_window": 0.3053,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-28 07:45:00+00:00",
    "candle_index": 31,
    "open": 79242.97,
    "high": 79270.0,
    "low": 78820.06,
    "close": 79204.59,
    "body_pct": 0.08530026225719975,
    "upper_shadow_pct": 0.06007467662354691,
    "lower_shadow_pct": 0.8546250611192533,
    "position_in_window": 0.3263,
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
    "timestamp": "2025-02-28 08:00:00+00:00",
    "candle_index": 32,
    "open": 79204.6,
    "high": 79438.33,
    "low": 78646.13,
    "close": 78786.02,
    "body_pct": 0.5283766725574391,
    "upper_shadow_pct": 0.29503913153243727,
    "lower_shadow_pct": 0.17658419591012361,
    "position_in_window": 0.3368,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-28 08:15:00+00:00",
    "candle_index": 33,
    "open": 78786.02,
    "high": 78925.35,
    "low": 78371.64,
    "close": 78862.01,
    "body_pct": 0.13723790431812646,
    "upper_shadow_pct": 0.11439201025809598,
    "lower_shadow_pct": 0.7483700854237776,
    "position_in_window": 0.3474,
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
    "timestamp": "2025-02-28 08:30:00+00:00",
    "candle_index": 34,
    "open": 78862.0,
    "high": 79239.72,
    "low": 78487.0,
    "close": 78487.01,
    "body_pct": 0.4981799341056497,
    "upper_shadow_pct": 0.5018067807418437,
    "lower_shadow_pct": 1.3285152506591156e-05,
    "position_in_window": 0.3579,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-28 08:45:00+00:00",
    "candle_index": 35,
    "open": 78487.01,
    "high": 79100.0,
    "low": 78258.52,
    "close": 78975.99,
    "body_pct": 0.5810952131958131,
    "upper_shadow_pct": 0.14737129818889974,
    "lower_shadow_pct": 0.2715334886152871,
    "position_in_window": 0.3684,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-02-28 09:15:00+00:00",
    "candle_index": 37,
    "open": 79155.99,
    "high": 80494.83,
    "low": 79134.0,
    "close": 80419.19,
    "body_pct": 0.928257019613027,
    "upper_shadow_pct": 0.055583724638639156,
    "lower_shadow_pct": 0.016159255748333892,
    "position_in_window": 0.3895,
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
  "doji_count": 20,
  "doji_ratio": 0.20833333333333334,
  "small_body_count": 38,
  "small_body_ratio": 0.3958333333333333,
  "bullish_body_total": 14406.69000000006,
  "bearish_body_total": 14765.840000000084
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
      "previous_timestamp": "2025-02-28 03:30:00+00:00",
      "timestamp": "2025-02-28 03:45:00+00:00",
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
      "previous_timestamp": "2025-02-28 03:30:00+00:00",
      "timestamp": "2025-02-28 03:45:00+00:00",
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
      "previous_timestamp": "2025-02-28 05:45:00+00:00",
      "timestamp": "2025-02-28 06:00:00+00:00",
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
      "previous_timestamp": "2025-02-28 05:45:00+00:00",
      "timestamp": "2025-02-28 06:00:00+00:00",
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
      "previous_timestamp": "2025-02-28 06:45:00+00:00",
      "timestamp": "2025-02-28 07:00:00+00:00",
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
      "previous_timestamp": "2025-02-28 06:45:00+00:00",
      "timestamp": "2025-02-28 07:00:00+00:00",
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
      "previous_timestamp": "2025-02-28 08:30:00+00:00",
      "timestamp": "2025-02-28 08:45:00+00:00",
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
      "previous_timestamp": "2025-02-28 08:30:00+00:00",
      "timestamp": "2025-02-28 08:45:00+00:00",
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
      "previous_timestamp": "2025-02-28 09:45:00+00:00",
      "timestamp": "2025-02-28 10:00:00+00:00",
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
      "previous_timestamp": "2025-02-28 09:45:00+00:00",
      "timestamp": "2025-02-28 10:00:00+00:00",
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
      "previous_timestamp": "2025-02-28 10:15:00+00:00",
      "timestamp": "2025-02-28 10:30:00+00:00",
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
      "previous_timestamp": "2025-02-28 10:15:00+00:00",
      "timestamp": "2025-02-28 10:30:00+00:00",
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
      "previous_timestamp": "2025-02-28 10:30:00+00:00",
      "timestamp": "2025-02-28 10:45:00+00:00",
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
      "previous_timestamp": "2025-02-28 10:30:00+00:00",
      "timestamp": "2025-02-28 10:45:00+00:00",
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
      "previous_timestamp": "2025-02-28 12:30:00+00:00",
      "timestamp": "2025-02-28 12:45:00+00:00",
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
      "previous_timestamp": "2025-02-28 12:30:00+00:00",
      "timestamp": "2025-02-28 12:45:00+00:00",
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
      "previous_timestamp": "2025-02-28 13:00:00+00:00",
      "timestamp": "2025-02-28 13:15:00+00:00",
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
      "previous_timestamp": "2025-02-28 13:00:00+00:00",
      "timestamp": "2025-02-28 13:15:00+00:00",
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
      "previous_timestamp": "2025-02-28 13:15:00+00:00",
      "timestamp": "2025-02-28 13:30:00+00:00",
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
      "previous_timestamp": "2025-02-28 13:15:00+00:00",
      "timestamp": "2025-02-28 13:30:00+00:00",
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
CLOSE_NEAR_LOW, LONG_UPPER_SHADOW_REJECTION, SMALL_BODY_INDECISION, DOJI_INDECISION, SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED, CANDLE_PATTERN_NEEDS_TREND_CONTEXT, STRONG_BEARISH_CANDLE_BODY, SPINNING_TOP_INDECISION, LONG_LOWER_SHADOW_REJECTION, CLOSE_NEAR_HIGH, HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED, STRONG_BULLISH_CANDLE_BODY, BEARISH_ENGULFING_CONTEXT, ENGULFING_WITHOUT_FOLLOW_THROUGH, BULLISH_ENGULFING_CONTEXT, INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED, REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH, GRAVESTONE_DOJI_CONTEXT, BEARISH_BELT_HOLD_CONTEXT_REQUIRED, HANGING_MAN_LIKE_CONTEXT_REQUIRED, LONG_LEGGED_DOJI_CONTEXT, RICKSHAW_MAN_DOJI_CONTEXT, DRAGONFLY_DOJI_CONTEXT, BULLISH_BELT_HOLD_CONTEXT_REQUIRED, TWEEZERS_BOTTOM_CONTEXT_REQUIRED, BULLISH_HARAMI_CONTEXT, BEARISH_SEPARATING_LINES_CONTEXT, TWEEZERS_TOP_CONTEXT_REQUIRED, BULLISH_SEPARATING_LINES_CONTEXT, DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT, DOJI_TOP_CONTEXT_REQUIRED, HARAMI_CROSS_CONTEXT, BEARISH_HARAMI_CONTEXT, THREE_MOUNTAINS_CONTEXT_REQUIRED, SMALL_BODY_CLUSTER, LOW_DIRECTIONAL_PROGRESS

## 2. Altunina trend context
### Swing structure
```json
[
  {
    "index": 11,
    "timestamp": "2025-02-28 02:45:00+00:00",
    "price": 79532.0,
    "point_type": "LOW"
  },
  {
    "index": 12,
    "timestamp": "2025-02-28 03:00:00+00:00",
    "price": 81539.25,
    "point_type": "HIGH"
  },
  {
    "index": 16,
    "timestamp": "2025-02-28 04:00:00+00:00",
    "price": 79400.0,
    "point_type": "LOW"
  },
  {
    "index": 19,
    "timestamp": "2025-02-28 04:45:00+00:00",
    "price": 80969.69,
    "point_type": "HIGH"
  },
  {
    "index": 23,
    "timestamp": "2025-02-28 05:45:00+00:00",
    "price": 79152.0,
    "point_type": "LOW"
  },
  {
    "index": 24,
    "timestamp": "2025-02-28 06:00:00+00:00",
    "price": 80440.44,
    "point_type": "HIGH"
  },
  {
    "index": 27,
    "timestamp": "2025-02-28 06:45:00+00:00",
    "price": 79034.97,
    "point_type": "LOW"
  },
  {
    "index": 29,
    "timestamp": "2025-02-28 07:15:00+00:00",
    "price": 80275.72,
    "point_type": "HIGH"
  },
  {
    "index": 33,
    "timestamp": "2025-02-28 08:15:00+00:00",
    "price": 78371.64,
    "point_type": "LOW"
  },
  {
    "index": 34,
    "timestamp": "2025-02-28 08:30:00+00:00",
    "price": 79239.72,
    "point_type": "HIGH"
  },
  {
    "index": 35,
    "timestamp": "2025-02-28 08:45:00+00:00",
    "price": 78258.52,
    "point_type": "LOW"
  },
  {
    "index": 38,
    "timestamp": "2025-02-28 09:30:00+00:00",
    "price": 80729.91,
    "point_type": "HIGH"
  },
  {
    "index": 41,
    "timestamp": "2025-02-28 10:15:00+00:00",
    "price": 79544.71,
    "point_type": "LOW"
  },
  {
    "index": 46,
    "timestamp": "2025-02-28 11:30:00+00:00",
    "price": 80854.46,
    "point_type": "HIGH"
  },
  {
    "index": 50,
    "timestamp": "2025-02-28 12:30:00+00:00",
    "price": 80075.47,
    "point_type": "LOW"
  },
  {
    "index": 52,
    "timestamp": "2025-02-28 13:00:00+00:00",
    "price": 81405.18,
    "point_type": "HIGH"
  },
  {
    "index": 53,
    "timestamp": "2025-02-28 13:15:00+00:00",
    "price": 80621.1,
    "point_type": "LOW"
  },
  {
    "index": 56,
    "timestamp": "2025-02-28 14:00:00+00:00",
    "price": 82380.51,
    "point_type": "HIGH"
  },
  {
    "index": 58,
    "timestamp": "2025-02-28 14:30:00+00:00",
    "price": 81072.23,
    "point_type": "LOW"
  },
  {
    "index": 62,
    "timestamp": "2025-02-28 15:30:00+00:00",
    "price": 84425.89,
    "point_type": "HIGH"
  },
  {
    "index": 65,
    "timestamp": "2025-02-28 16:15:00+00:00",
    "price": 83426.0,
    "point_type": "LOW"
  },
  {
    "index": 66,
    "timestamp": "2025-02-28 16:30:00+00:00",
    "price": 84920.0,
    "point_type": "HIGH"
  },
  {
    "index": 73,
    "timestamp": "2025-02-28 18:15:00+00:00",
    "price": 83196.71,
    "point_type": "LOW"
  },
  {
    "index": 75,
    "timestamp": "2025-02-28 18:45:00+00:00",
    "price": 85120.0,
    "point_type": "HIGH"
  },
  {
    "index": 76,
    "timestamp": "2025-02-28 19:00:00+00:00",
    "price": 84209.84,
    "point_type": "LOW"
  },
  {
    "index": 78,
    "timestamp": "2025-02-28 19:30:00+00:00",
    "price": 84810.35,
    "point_type": "HIGH"
  },
  {
    "index": 79,
    "timestamp": "2025-02-28 19:45:00+00:00",
    "price": 84314.33,
    "point_type": "LOW"
  },
  {
    "index": 80,
    "timestamp": "2025-02-28 20:00:00+00:00",
    "price": 84795.03,
    "point_type": "HIGH"
  },
  {
    "index": 81,
    "timestamp": "2025-02-28 20:15:00+00:00",
    "price": 83600.0,
    "point_type": "LOW"
  },
  {
    "index": 85,
    "timestamp": "2025-02-28 21:15:00+00:00",
    "price": 84596.0,
    "point_type": "HIGH"
  },
  {
    "index": 86,
    "timestamp": "2025-02-28 21:30:00+00:00",
    "price": 84000.17,
    "point_type": "LOW"
  },
  {
    "index": 88,
    "timestamp": "2025-02-28 22:00:00+00:00",
    "price": 84481.14,
    "point_type": "HIGH"
  },
  {
    "index": 90,
    "timestamp": "2025-02-28 22:30:00+00:00",
    "price": 83888.0,
    "point_type": "LOW"
  },
  {
    "index": 92,
    "timestamp": "2025-02-28 23:00:00+00:00",
    "price": 84279.22,
    "point_type": "HIGH"
  }
]
```
### Higher highs / lower highs
```json
{
  "raw_swing_count": 43,
  "swing_count": 34,
  "leg_count": 33,
  "structure_direction": "SIDEWAYS_STRUCTURE",
  "total_movement": 42382.419999999984,
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
    "lower_price": 79034.97,
    "upper_price": 79438.33,
    "mid_price": 79247.94166666667,
    "touch_count": 6,
    "source_indexes": [
      16,
      23,
      25,
      27,
      32,
      34
    ],
    "zone_width": 403.3600000000006,
    "zone_width_ratio": 0.005089848285228867,
    "formed_at_index": 34,
    "first_touch_index": 16,
    "last_touch_index": 34,
    "source_point_types": [
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "HIGH",
      "HIGH"
    ],
    "original_zone_type": "SUPPORT",
    "current_zone_type": "SUPPORT",
    "role_changed_at_index": null,
    "is_significant_single_extreme": false,
    "positional_zone_type": "SUPPORT"
  },
  "resistance_zone": {
    "zone_type": "RESISTANCE",
    "lower_price": 84596.0,
    "upper_price": 84920.0,
    "mid_price": 84780.345,
    "touch_count": 4,
    "source_indexes": [
      66,
      78,
      80,
      85
    ],
    "zone_width": 324.0,
    "zone_width_ratio": 0.0038216404993397938,
    "formed_at_index": 85,
    "first_touch_index": 66,
    "last_touch_index": 85,
    "source_point_types": [
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
  "lower_boundary": 79034.97,
  "upper_boundary": 84920.0,
  "midline": 81977.485,
  "width": 5885.029999999999,
  "width_ratio": 0.07178836969687469,
  "touch_count": 10,
  "inside_close_ratio": 0.9428571428571428,
  "formed_at_index": 85,
  "first_touch_index": 16,
  "duration_candles": 70,
  "boundary_alternation_count": 1
}
```
### Range high / low
See trading range object above.
### Price position inside range
```json
{
  "swing_count": 43,
  "zone_count": 13,
  "range_detected": false,
  "range_formed_at_index": 85,
  "range_duration_candles": 70,
  "inside_close_ratio": 0.9428571428571428,
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
SCHWAGER_SUPPORT_ZONE_IDENTIFIED, SCHWAGER_SUPPORT_ZONE_HELD, SCHWAGER_ZONE_TOO_WIDE, SCHWAGER_RESISTANCE_ZONE_IDENTIFIED, SCHWAGER_RESISTANCE_ZONE_HELD, SCHWAGER_PREVIOUS_EXTREME_ZONE_IDENTIFIED, SCHWAGER_RANGE_NOT_CONFIRMED

## 4. BookEvidenceMatrix
### Bullish evidence
Count: 36
### Bearish evidence
Count: 34
### Neutral/range evidence
Count: 373
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
  "total_evidence_count": 443,
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
  "FLAT": 0.30000000000000004,
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
    "score": 0.30000000000000004
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
