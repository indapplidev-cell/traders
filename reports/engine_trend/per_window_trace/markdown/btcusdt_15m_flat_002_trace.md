# btcusdt_15m_flat_002 вЂ” Market Evidence Trace

## Window
- Symbol: BTCUSDT
- Interval: 15m
- Period: 2025-06-10T00:00:00+00:00 вЂ” 2025-06-10T23:45:00+00:00
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
    "timestamp": "2025-06-10 00:00:00+00:00",
    "candle_index": 0,
    "open": 110263.02,
    "high": 110276.92,
    "low": 109943.77,
    "close": 109971.01,
    "body_pct": 0.876512081644948,
    "upper_shadow_pct": 0.04172294762117491,
    "lower_shadow_pct": 0.08176497073387712,
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
    "timestamp": "2025-06-10 00:15:00+00:00",
    "candle_index": 1,
    "open": 109971.01,
    "high": 110311.82,
    "low": 109964.0,
    "close": 110277.53,
    "body_pct": 0.88126042205738,
    "upper_shadow_pct": 0.09858547524583824,
    "lower_shadow_pct": 0.020154102696781726,
    "position_in_window": 0.0105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-06-10 00:45:00+00:00",
    "candle_index": 3,
    "open": 110133.95,
    "high": 110148.0,
    "low": 109909.54,
    "close": 109913.91,
    "body_pct": 0.9227543403505313,
    "upper_shadow_pct": 0.058919734966042664,
    "lower_shadow_pct": 0.01832592468342606,
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
    "timestamp": "2025-06-10 01:00:00+00:00",
    "candle_index": 4,
    "open": 109913.91,
    "high": 109953.98,
    "low": 109722.75,
    "close": 109764.26,
    "body_pct": 0.6471911084202369,
    "upper_shadow_pct": 0.17329066297622772,
    "lower_shadow_pct": 0.17951822860353542,
    "position_in_window": 0.0421,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-06-10 01:30:00+00:00",
    "candle_index": 6,
    "open": 109844.05,
    "high": 109872.69,
    "low": 109745.28,
    "close": 109870.0,
    "body_pct": 0.20367318106896146,
    "upper_shadow_pct": 0.021112942469211637,
    "lower_shadow_pct": 0.7752138764618269,
    "position_in_window": 0.0632,
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
    "timestamp": "2025-06-10 01:45:00+00:00",
    "candle_index": 7,
    "open": 109870.01,
    "high": 109886.25,
    "low": 109648.29,
    "close": 109788.57,
    "body_pct": 0.34224239367954945,
    "upper_shadow_pct": 0.06824676416206422,
    "lower_shadow_pct": 0.5895108421583863,
    "position_in_window": 0.0737,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2025-06-10 02:00:00+00:00",
    "candle_index": 8,
    "open": 109788.58,
    "high": 109788.58,
    "low": 109381.24,
    "close": 109610.74,
    "body_pct": 0.43658859920459087,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.5634114007954092,
    "position_in_window": 0.0842,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2025-06-10 02:15:00+00:00",
    "candle_index": 9,
    "open": 109610.74,
    "high": 109678.0,
    "low": 109473.93,
    "close": 109647.72,
    "body_pct": 0.1812123291027327,
    "upper_shadow_pct": 0.14838045768607733,
    "lower_shadow_pct": 0.67040721321119,
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
    "timestamp": "2025-06-10 02:30:00+00:00",
    "candle_index": 10,
    "open": 109647.71,
    "high": 109698.12,
    "low": 109571.5,
    "close": 109627.88,
    "body_pct": 0.1566103301216433,
    "upper_shadow_pct": 0.39812036013260776,
    "lower_shadow_pct": 0.4452693097457489,
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
    "timestamp": "2025-06-10 02:45:00+00:00",
    "candle_index": 11,
    "open": 109627.88,
    "high": 109750.0,
    "low": 109575.95,
    "close": 109650.94,
    "body_pct": 0.1324906636023975,
    "upper_shadow_pct": 0.5691467968974203,
    "lower_shadow_pct": 0.2983625395001821,
    "position_in_window": 0.1158,
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
    "timestamp": "2025-06-10 03:00:00+00:00",
    "candle_index": 12,
    "open": 109650.95,
    "high": 109684.89,
    "low": 109388.0,
    "close": 109400.14,
    "body_pct": 0.8447910000336764,
    "upper_shadow_pct": 0.11431843443700493,
    "lower_shadow_pct": 0.040890565529318745,
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
    "timestamp": "2025-06-10 03:30:00+00:00",
    "candle_index": 14,
    "open": 109469.84,
    "high": 109508.98,
    "low": 109382.38,
    "close": 109458.89,
    "body_pct": 0.08649289099524364,
    "upper_shadow_pct": 0.309162717219606,
    "lower_shadow_pct": 0.6043443917851504,
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
    "timestamp": "2025-06-10 03:45:00+00:00",
    "candle_index": 15,
    "open": 109458.89,
    "high": 109613.54,
    "low": 109425.41,
    "close": 109568.02,
    "body_pct": 0.5800776059108617,
    "upper_shadow_pct": 0.24196034656881898,
    "lower_shadow_pct": 0.17796204752031938,
    "position_in_window": 0.1579,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-06-10 04:00:00+00:00",
    "candle_index": 16,
    "open": 109568.03,
    "high": 109649.98,
    "low": 109415.09,
    "close": 109415.09,
    "body_pct": 0.6511132870705552,
    "upper_shadow_pct": 0.34888671292944484,
    "lower_shadow_pct": 0.0,
    "position_in_window": 0.1684,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-06-10 04:45:00+00:00",
    "candle_index": 19,
    "open": 109496.9,
    "high": 109542.97,
    "low": 109449.28,
    "close": 109528.55,
    "body_pct": 0.3378162023696013,
    "upper_shadow_pct": 0.1539118369089326,
    "lower_shadow_pct": 0.5082719607214661,
    "position_in_window": 0.2,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-06-10 05:00:00+00:00",
    "candle_index": 20,
    "open": 109528.55,
    "high": 109556.61,
    "low": 109452.85,
    "close": 109515.68,
    "body_pct": 0.12403623747118875,
    "upper_shadow_pct": 0.2704317656129442,
    "lower_shadow_pct": 0.605531996915867,
    "position_in_window": 0.2105,
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
    "timestamp": "2025-06-10 05:15:00+00:00",
    "candle_index": 21,
    "open": 109515.69,
    "high": 109737.68,
    "low": 109396.75,
    "close": 109415.09,
    "body_pct": 0.2950752353855861,
    "upper_shadow_pct": 0.6511307306485062,
    "lower_shadow_pct": 0.053794033965907616,
    "position_in_window": 0.2211,
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
    "timestamp": "2025-06-10 05:30:00+00:00",
    "candle_index": 22,
    "open": 109415.1,
    "high": 109450.26,
    "low": 109200.0,
    "close": 109394.88,
    "body_pct": 0.08079597218892987,
    "upper_shadow_pct": 0.14049388635814625,
    "lower_shadow_pct": 0.7787101414529239,
    "position_in_window": 0.2316,
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
    "timestamp": "2025-06-10 06:00:00+00:00",
    "candle_index": 24,
    "open": 109310.49,
    "high": 109408.98,
    "low": 109161.0,
    "close": 109200.0,
    "body_pct": 0.4455601258166266,
    "upper_shadow_pct": 0.3971691265424321,
    "lower_shadow_pct": 0.15727074764094137,
    "position_in_window": 0.2526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-06-10 06:15:00+00:00",
    "candle_index": 25,
    "open": 109200.0,
    "high": 109411.69,
    "low": 109199.99,
    "close": 109400.01,
    "body_pct": 0.94478034955124,
    "upper_shadow_pct": 0.05517241379313995,
    "lower_shadow_pct": 4.723665562003518e-05,
    "position_in_window": 0.2632,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-06-10 06:45:00+00:00",
    "candle_index": 27,
    "open": 109570.31,
    "high": 109634.3,
    "low": 109502.68,
    "close": 109502.68,
    "body_pct": 0.513827685762039,
    "upper_shadow_pct": 0.48617231423796103,
    "lower_shadow_pct": 0.0,
    "position_in_window": 0.2842,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-06-10 07:15:00+00:00",
    "candle_index": 29,
    "open": 109394.36,
    "high": 109517.16,
    "low": 109291.41,
    "close": 109459.15,
    "body_pct": 0.28699889258025957,
    "upper_shadow_pct": 0.2569656699889671,
    "lower_shadow_pct": 0.45603543743077335,
    "position_in_window": 0.3053,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION"
    ]
  },
  {
    "timestamp": "2025-06-10 07:30:00+00:00",
    "candle_index": 30,
    "open": 109459.14,
    "high": 109505.95,
    "low": 109151.6,
    "close": 109161.01,
    "body_pct": 0.8413433046423366,
    "upper_shadow_pct": 0.13210103005502702,
    "lower_shadow_pct": 0.026555665302636297,
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
    "timestamp": "2025-06-10 07:45:00+00:00",
    "candle_index": 31,
    "open": 109161.0,
    "high": 109270.63,
    "low": 109095.67,
    "close": 109205.14,
    "body_pct": 0.25228623685412555,
    "upper_shadow_pct": 0.3743141289437748,
    "lower_shadow_pct": 0.37339963420209965,
    "position_in_window": 0.3263,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION"
    ]
  },
  {
    "timestamp": "2025-06-10 08:00:00+00:00",
    "candle_index": 32,
    "open": 109205.14,
    "high": 109415.1,
    "low": 109166.0,
    "close": 109249.08,
    "body_pct": 0.17639502207949137,
    "upper_shadow_pct": 0.6664793255720602,
    "lower_shadow_pct": 0.15712565234844844,
    "position_in_window": 0.3368,
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
    "timestamp": "2025-06-10 08:15:00+00:00",
    "candle_index": 33,
    "open": 109249.07,
    "high": 109324.29,
    "low": 109190.75,
    "close": 109195.39,
    "body_pct": 0.4019769357496641,
    "upper_shadow_pct": 0.563276920772729,
    "lower_shadow_pct": 0.03474614347760701,
    "position_in_window": 0.3474,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-06-10 08:30:00+00:00",
    "candle_index": 34,
    "open": 109195.39,
    "high": 109333.07,
    "low": 109108.17,
    "close": 109246.53,
    "body_pct": 0.22738995108936164,
    "upper_shadow_pct": 0.38479324144066157,
    "lower_shadow_pct": 0.38781680746997677,
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
    "timestamp": "2025-06-10 08:45:00+00:00",
    "candle_index": 35,
    "open": 109246.53,
    "high": 109271.09,
    "low": 109056.9,
    "close": 109082.65,
    "body_pct": 0.765115084737863,
    "upper_shadow_pct": 0.11466455016572859,
    "lower_shadow_pct": 0.12022036509640842,
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
    "timestamp": "2025-06-10 09:30:00+00:00",
    "candle_index": 38,
    "open": 109291.96,
    "high": 109478.66,
    "low": 109290.69,
    "close": 109355.59,
    "body_pct": 0.3385114645953594,
    "upper_shadow_pct": 0.6547321381071779,
    "lower_shadow_pct": 0.006756397297462716,
    "position_in_window": 0.4,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2025-06-10 09:45:00+00:00",
    "candle_index": 39,
    "open": 109355.6,
    "high": 109521.84,
    "low": 109352.43,
    "close": 109508.78,
    "body_pct": 0.9041969187178435,
    "upper_shadow_pct": 0.07709108080985422,
    "lower_shadow_pct": 0.018712000472302346,
    "position_in_window": 0.4105,
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
  "doji_count": 7,
  "doji_ratio": 0.07291666666666667,
  "small_body_count": 26,
  "small_body_ratio": 0.2708333333333333,
  "bullish_body_total": 6701.1000000000495,
  "bearish_body_total": 6690.380000000063
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
      "previous_timestamp": "2025-06-10 00:00:00+00:00",
      "timestamp": "2025-06-10 00:15:00+00:00",
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
      "previous_timestamp": "2025-06-10 00:00:00+00:00",
      "timestamp": "2025-06-10 00:15:00+00:00",
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
      "previous_timestamp": "2025-06-10 01:30:00+00:00",
      "timestamp": "2025-06-10 01:45:00+00:00",
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
      "previous_timestamp": "2025-06-10 01:30:00+00:00",
      "timestamp": "2025-06-10 01:45:00+00:00",
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
      "previous_timestamp": "2025-06-10 02:30:00+00:00",
      "timestamp": "2025-06-10 02:45:00+00:00",
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
      "previous_timestamp": "2025-06-10 02:30:00+00:00",
      "timestamp": "2025-06-10 02:45:00+00:00",
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
      "previous_timestamp": "2025-06-10 02:45:00+00:00",
      "timestamp": "2025-06-10 03:00:00+00:00",
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
      "previous_timestamp": "2025-06-10 02:45:00+00:00",
      "timestamp": "2025-06-10 03:00:00+00:00",
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
      "previous_timestamp": "2025-06-10 03:30:00+00:00",
      "timestamp": "2025-06-10 03:45:00+00:00",
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
      "previous_timestamp": "2025-06-10 03:30:00+00:00",
      "timestamp": "2025-06-10 03:45:00+00:00",
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
      "previous_timestamp": "2025-06-10 03:45:00+00:00",
      "timestamp": "2025-06-10 04:00:00+00:00",
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
      "previous_timestamp": "2025-06-10 03:45:00+00:00",
      "timestamp": "2025-06-10 04:00:00+00:00",
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
      "previous_timestamp": "2025-06-10 04:15:00+00:00",
      "timestamp": "2025-06-10 04:30:00+00:00",
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
      "previous_timestamp": "2025-06-10 04:15:00+00:00",
      "timestamp": "2025-06-10 04:30:00+00:00",
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
      "previous_timestamp": "2025-06-10 06:00:00+00:00",
      "timestamp": "2025-06-10 06:15:00+00:00",
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
      "previous_timestamp": "2025-06-10 06:00:00+00:00",
      "timestamp": "2025-06-10 06:15:00+00:00",
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
      "previous_timestamp": "2025-06-10 08:30:00+00:00",
      "timestamp": "2025-06-10 08:45:00+00:00",
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
      "previous_timestamp": "2025-06-10 08:30:00+00:00",
      "timestamp": "2025-06-10 08:45:00+00:00",
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
      "previous_timestamp": "2025-06-10 16:00:00+00:00",
      "timestamp": "2025-06-10 16:15:00+00:00",
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
      "previous_timestamp": "2025-06-10 16:00:00+00:00",
      "timestamp": "2025-06-10 16:15:00+00:00",
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
STRONG_BEARISH_CANDLE_BODY, CLOSE_NEAR_LOW, STRONG_BULLISH_CANDLE_BODY, CLOSE_NEAR_HIGH, LONG_LOWER_SHADOW_REJECTION, SMALL_BODY_INDECISION, SPINNING_TOP_INDECISION, HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED, CANDLE_PATTERN_NEEDS_TREND_CONTEXT, LONG_UPPER_SHADOW_REJECTION, DOJI_INDECISION, SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED, BULLISH_ENGULFING_CONTEXT, ENGULFING_WITHOUT_FOLLOW_THROUGH, BEARISH_ENGULFING_CONTEXT, BEARISH_BELT_HOLD_CONTEXT_REQUIRED, BULLISH_BELT_HOLD_CONTEXT_REQUIRED, HANGING_MAN_LIKE_CONTEXT_REQUIRED, REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH, INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED, LONG_LEGGED_DOJI_CONTEXT, RICKSHAW_MAN_DOJI_CONTEXT, TWEEZERS_TOP_CONTEXT_REQUIRED, TWEEZERS_BOTTOM_CONTEXT_REQUIRED, BULLISH_HARAMI_CONTEXT, BEARISH_HARAMI_CONTEXT, HARAMI_CROSS_CONTEXT, DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT, DOJI_TOP_CONTEXT_REQUIRED, BULLISH_SEPARATING_LINES_CONTEXT, THREE_ADVANCING_WHITE_SOLDIERS_CONTEXT, THREE_BUDDHA_TOP_CONTEXT_REQUIRED

## 2. Altunina trend context
### Swing structure
```json
[
  {
    "index": 1,
    "timestamp": "2025-06-10 00:15:00+00:00",
    "price": 110311.82,
    "point_type": "HIGH"
  },
  {
    "index": 4,
    "timestamp": "2025-06-10 01:00:00+00:00",
    "price": 109722.75,
    "point_type": "LOW"
  },
  {
    "index": 7,
    "timestamp": "2025-06-10 01:45:00+00:00",
    "price": 109886.25,
    "point_type": "HIGH"
  },
  {
    "index": 8,
    "timestamp": "2025-06-10 02:00:00+00:00",
    "price": 109381.24,
    "point_type": "LOW"
  },
  {
    "index": 11,
    "timestamp": "2025-06-10 02:45:00+00:00",
    "price": 109750.0,
    "point_type": "HIGH"
  },
  {
    "index": 14,
    "timestamp": "2025-06-10 03:30:00+00:00",
    "price": 109382.38,
    "point_type": "LOW"
  },
  {
    "index": 16,
    "timestamp": "2025-06-10 04:00:00+00:00",
    "price": 109649.98,
    "point_type": "HIGH"
  },
  {
    "index": 17,
    "timestamp": "2025-06-10 04:15:00+00:00",
    "price": 109366.0,
    "point_type": "LOW"
  },
  {
    "index": 21,
    "timestamp": "2025-06-10 05:15:00+00:00",
    "price": 109737.68,
    "point_type": "HIGH"
  },
  {
    "index": 24,
    "timestamp": "2025-06-10 06:00:00+00:00",
    "price": 109161.0,
    "point_type": "LOW"
  },
  {
    "index": 26,
    "timestamp": "2025-06-10 06:30:00+00:00",
    "price": 109650.0,
    "point_type": "HIGH"
  },
  {
    "index": 31,
    "timestamp": "2025-06-10 07:45:00+00:00",
    "price": 109095.67,
    "point_type": "LOW"
  },
  {
    "index": 32,
    "timestamp": "2025-06-10 08:00:00+00:00",
    "price": 109415.1,
    "point_type": "HIGH"
  },
  {
    "index": 35,
    "timestamp": "2025-06-10 08:45:00+00:00",
    "price": 109056.9,
    "point_type": "LOW"
  },
  {
    "index": 41,
    "timestamp": "2025-06-10 10:15:00+00:00",
    "price": 109573.3,
    "point_type": "HIGH"
  },
  {
    "index": 44,
    "timestamp": "2025-06-10 11:00:00+00:00",
    "price": 109199.81,
    "point_type": "LOW"
  },
  {
    "index": 46,
    "timestamp": "2025-06-10 11:30:00+00:00",
    "price": 109851.8,
    "point_type": "HIGH"
  },
  {
    "index": 48,
    "timestamp": "2025-06-10 12:00:00+00:00",
    "price": 109415.62,
    "point_type": "LOW"
  },
  {
    "index": 53,
    "timestamp": "2025-06-10 13:15:00+00:00",
    "price": 109900.81,
    "point_type": "HIGH"
  },
  {
    "index": 55,
    "timestamp": "2025-06-10 13:45:00+00:00",
    "price": 108888.88,
    "point_type": "LOW"
  },
  {
    "index": 56,
    "timestamp": "2025-06-10 14:00:00+00:00",
    "price": 109332.45,
    "point_type": "HIGH"
  },
  {
    "index": 59,
    "timestamp": "2025-06-10 14:45:00+00:00",
    "price": 108468.29,
    "point_type": "LOW"
  },
  {
    "index": 61,
    "timestamp": "2025-06-10 15:15:00+00:00",
    "price": 109199.99,
    "point_type": "HIGH"
  },
  {
    "index": 62,
    "timestamp": "2025-06-10 15:30:00+00:00",
    "price": 108331.03,
    "point_type": "LOW"
  },
  {
    "index": 64,
    "timestamp": "2025-06-10 16:00:00+00:00",
    "price": 109251.41,
    "point_type": "HIGH"
  },
  {
    "index": 67,
    "timestamp": "2025-06-10 16:45:00+00:00",
    "price": 108690.59,
    "point_type": "LOW"
  },
  {
    "index": 69,
    "timestamp": "2025-06-10 17:15:00+00:00",
    "price": 109064.06,
    "point_type": "HIGH"
  },
  {
    "index": 72,
    "timestamp": "2025-06-10 18:00:00+00:00",
    "price": 108518.86,
    "point_type": "LOW"
  },
  {
    "index": 78,
    "timestamp": "2025-06-10 19:30:00+00:00",
    "price": 110400.0,
    "point_type": "HIGH"
  },
  {
    "index": 81,
    "timestamp": "2025-06-10 20:15:00+00:00",
    "price": 109239.68,
    "point_type": "LOW"
  },
  {
    "index": 83,
    "timestamp": "2025-06-10 20:45:00+00:00",
    "price": 110018.07,
    "point_type": "HIGH"
  },
  {
    "index": 85,
    "timestamp": "2025-06-10 21:15:00+00:00",
    "price": 109420.0,
    "point_type": "LOW"
  },
  {
    "index": 86,
    "timestamp": "2025-06-10 21:30:00+00:00",
    "price": 109940.89,
    "point_type": "HIGH"
  },
  {
    "index": 87,
    "timestamp": "2025-06-10 21:45:00+00:00",
    "price": 109710.33,
    "point_type": "LOW"
  },
  {
    "index": 88,
    "timestamp": "2025-06-10 22:00:00+00:00",
    "price": 110181.1,
    "point_type": "HIGH"
  },
  {
    "index": 92,
    "timestamp": "2025-06-10 23:00:00+00:00",
    "price": 109600.0,
    "point_type": "LOW"
  }
]
```
### Higher highs / lower highs
```json
{
  "raw_swing_count": 43,
  "swing_count": 36,
  "leg_count": 35,
  "structure_direction": "SIDEWAYS_STRUCTURE",
  "total_movement": 20219.540000000066,
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
    "lower_price": 108888.88,
    "upper_price": 109600.0,
    "mid_price": 109300.46608695653,
    "touch_count": 23,
    "source_indexes": [
      8,
      12,
      14,
      17,
      22,
      24,
      29,
      31,
      32,
      34,
      35,
      41,
      44,
      48,
      50,
      55,
      56,
      61,
      64,
      69,
      81,
      85,
      92
    ],
    "zone_width": 711.1199999999953,
    "zone_width_ratio": 0.006506102173747798,
    "formed_at_index": 92,
    "first_touch_index": 8,
    "last_touch_index": 92,
    "source_point_types": [
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "HIGH",
      "LOW",
      "HIGH",
      "HIGH",
      "LOW",
      "HIGH",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "HIGH",
      "HIGH",
      "HIGH",
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
    "lower_price": 109649.98,
    "upper_price": 110018.07,
    "mid_price": 109811.01000000001,
    "touch_count": 12,
    "source_indexes": [
      4,
      7,
      11,
      16,
      21,
      26,
      46,
      53,
      83,
      86,
      87,
      92
    ],
    "zone_width": 368.09000000001106,
    "zone_width_ratio": 0.0033520318226743476,
    "formed_at_index": 92,
    "first_touch_index": 4,
    "last_touch_index": 92,
    "source_point_types": [
      "LOW",
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
    "positional_zone_type": "SUPPORT"
  },
  "is_detected": true,
  "lower_boundary": 108888.88,
  "upper_boundary": 110018.07,
  "midline": 109453.475,
  "width": 1129.1900000000023,
  "width_ratio": 0.010316620829078312,
  "touch_count": 35,
  "inside_close_ratio": 0.8876404494382022,
  "formed_at_index": 92,
  "first_touch_index": 4,
  "duration_candles": 89,
  "boundary_alternation_count": 17
}
```
### Range high / low
See trading range object above.
### Price position inside range
```json
{
  "swing_count": 43,
  "zone_count": 4,
  "range_detected": true,
  "range_formed_at_index": 92,
  "range_duration_candles": 89,
  "inside_close_ratio": 0.8876404494382022,
  "breakout_direction": "UPWARD",
  "breakout_status": "ATTEMPT",
  "polarity_status": "NONE"
}
```
### Breakout / breakdown attempts
```json
{
  "direction": "UPWARD",
  "status": "ATTEMPT",
  "breakout_index": 94,
  "boundary_price": 110018.07,
  "breakout_close": 110169.77,
  "distance_ratio": 0.0013788643992754743,
  "returned_to_range": false,
  "follow_through_count": 1,
  "evidence": [
    {
      "source": "SCHWAGER",
      "code": "SCHWAGER_BULLISH_RANGE_BREAKOUT_CONTEXT",
      "description": "Closing price moved above the range boundary",
      "contribution": 0.12,
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
  "analysis_start_index": 93,
  "confirmation_method": "NONE",
  "confirmation_close_count": 2,
  "extreme_index": 95,
  "extreme_price": 110299.73,
  "maximum_distance_ratio": 0.0025601248958465545,
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
SCHWAGER_SUPPORT_ZONE_IDENTIFIED, SCHWAGER_SUPPORT_ZONE_HELD, SCHWAGER_ZONE_TOO_WIDE, SCHWAGER_RESISTANCE_ZONE_IDENTIFIED, SCHWAGER_RESISTANCE_ZONE_HELD, SCHWAGER_TRADING_RANGE_DETECTED, SCHWAGER_PRICE_INSIDE_RANGE, SCHWAGER_RANGE_UPPER_BOUNDARY_HELD, SCHWAGER_RANGE_LOWER_BOUNDARY_HELD, SCHWAGER_RANGE_DURATION_CONFIRMED, SCHWAGER_RANGE_BOUNDARY_ALTERNATION_CONFIRMED, SCHWAGER_BULLISH_RANGE_BREAKOUT_CONTEXT, SCHWAGER_BREAKOUT_REQUIRES_CONFIRMATION

## 4. BookEvidenceMatrix
### Bullish evidence
Count: 35
### Bearish evidence
Count: 28
### Neutral/range evidence
Count: 318
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
  "total_evidence_count": 381,
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
  "FLAT": 0.5775280898876405,
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
    "score": 0.5775280898876405
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
