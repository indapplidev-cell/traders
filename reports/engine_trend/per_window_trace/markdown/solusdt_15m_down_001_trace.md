# solusdt_15m_down_001 вЂ” Market Evidence Trace

## Window
- Symbol: SOLUSDT
- Interval: 15m
- Period: 2025-03-03T00:00:00+00:00 вЂ” 2025-03-03T23:45:00+00:00
- Reference label: EXPECTED_DOWN
- Selection reason: top deterministic DOWN OHLC candidate

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
    "timestamp": "2025-03-03 00:00:00+00:00",
    "candle_index": 0,
    "open": 178.72,
    "high": 179.47,
    "low": 175.11,
    "close": 175.84,
    "body_pct": 0.6605504587155975,
    "upper_shadow_pct": 0.1720183486238538,
    "lower_shadow_pct": 0.16743119266054868,
    "position_in_window": 0.0,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-03-03 00:15:00+00:00",
    "candle_index": 1,
    "open": 175.83,
    "high": 177.79,
    "low": 175.61,
    "close": 176.51,
    "body_pct": 0.31192660550458035,
    "upper_shadow_pct": 0.5871559633027587,
    "lower_shadow_pct": 0.10091743119266103,
    "position_in_window": 0.0105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2025-03-03 00:45:00+00:00",
    "candle_index": 3,
    "open": 175.15,
    "high": 175.19,
    "low": 174.11,
    "close": 174.35,
    "body_pct": 0.7407407407407622,
    "upper_shadow_pct": 0.037037037037030214,
    "lower_shadow_pct": 0.2222222222222076,
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
    "timestamp": "2025-03-03 01:00:00+00:00",
    "candle_index": 4,
    "open": 174.35,
    "high": 176.36,
    "low": 174.26,
    "close": 174.44,
    "body_pct": 0.042857142857144016,
    "upper_shadow_pct": 0.9142857142857119,
    "lower_shadow_pct": 0.042857142857144016,
    "position_in_window": 0.0421,
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
    "timestamp": "2025-03-03 01:15:00+00:00",
    "candle_index": 5,
    "open": 174.43,
    "high": 174.57,
    "low": 172.66,
    "close": 173.85,
    "body_pct": 0.3036649214659757,
    "upper_shadow_pct": 0.07329842931936471,
    "lower_shadow_pct": 0.6230366492146596,
    "position_in_window": 0.0526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2025-03-03 01:30:00+00:00",
    "candle_index": 6,
    "open": 173.86,
    "high": 174.26,
    "low": 172.61,
    "close": 173.5,
    "body_pct": 0.21818181818182947,
    "upper_shadow_pct": 0.242424242424232,
    "lower_shadow_pct": 0.5393939393939385,
    "position_in_window": 0.0632,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2025-03-03 01:45:00+00:00",
    "candle_index": 7,
    "open": 173.51,
    "high": 173.51,
    "low": 172.2,
    "close": 172.45,
    "body_pct": 0.8091603053435118,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.19083969465648823,
    "position_in_window": 0.0737,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-03-03 02:00:00+00:00",
    "candle_index": 8,
    "open": 172.44,
    "high": 172.9,
    "low": 170.41,
    "close": 170.52,
    "body_pct": 0.7710843373493897,
    "upper_shadow_pct": 0.1847389558232957,
    "lower_shadow_pct": 0.04417670682731455,
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
    "timestamp": "2025-03-03 02:15:00+00:00",
    "candle_index": 9,
    "open": 170.52,
    "high": 171.5,
    "low": 168.95,
    "close": 169.07,
    "body_pct": 0.5686274509803964,
    "upper_shadow_pct": 0.3843137254901903,
    "lower_shadow_pct": 0.04705882352941334,
    "position_in_window": 0.0947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-03-03 02:30:00+00:00",
    "candle_index": 10,
    "open": 169.07,
    "high": 171.5,
    "low": 169.0,
    "close": 170.94,
    "body_pct": 0.7480000000000018,
    "upper_shadow_pct": 0.22400000000000092,
    "lower_shadow_pct": 0.02799999999999727,
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
    "timestamp": "2025-03-03 03:00:00+00:00",
    "candle_index": 12,
    "open": 171.47,
    "high": 171.82,
    "low": 169.5,
    "close": 169.82,
    "body_pct": 0.7112068965517286,
    "upper_shadow_pct": 0.15086206896551524,
    "lower_shadow_pct": 0.1379310344827561,
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
    "timestamp": "2025-03-03 03:30:00+00:00",
    "candle_index": 14,
    "open": 168.83,
    "high": 169.75,
    "low": 168.11,
    "close": 168.45,
    "body_pct": 0.23170731707318723,
    "upper_shadow_pct": 0.5609756097560946,
    "lower_shadow_pct": 0.20731707317071818,
    "position_in_window": 0.1474,
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
    "timestamp": "2025-03-03 03:45:00+00:00",
    "candle_index": 15,
    "open": 168.45,
    "high": 170.26,
    "low": 168.28,
    "close": 169.88,
    "body_pct": 0.7222222222222294,
    "upper_shadow_pct": 0.1919191919191906,
    "lower_shadow_pct": 0.08585858585857999,
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
    "timestamp": "2025-03-03 04:15:00+00:00",
    "candle_index": 17,
    "open": 170.12,
    "high": 170.57,
    "low": 169.88,
    "close": 169.89,
    "body_pct": 0.3333333333333608,
    "upper_shadow_pct": 0.652173913043464,
    "lower_shadow_pct": 0.014492753623175272,
    "position_in_window": 0.1789,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-03-03 04:30:00+00:00",
    "candle_index": 18,
    "open": 169.9,
    "high": 170.31,
    "low": 169.31,
    "close": 169.63,
    "body_pct": 0.27000000000001023,
    "upper_shadow_pct": 0.4099999999999966,
    "lower_shadow_pct": 0.3199999999999932,
    "position_in_window": 0.1895,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION"
    ]
  },
  {
    "timestamp": "2025-03-03 04:45:00+00:00",
    "candle_index": 19,
    "open": 169.63,
    "high": 169.82,
    "low": 169.2,
    "close": 169.5,
    "body_pct": 0.20967741935482984,
    "upper_shadow_pct": 0.30645161290321987,
    "lower_shadow_pct": 0.48387096774195026,
    "position_in_window": 0.2,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2025-03-03 05:00:00+00:00",
    "candle_index": 20,
    "open": 169.5,
    "high": 170.35,
    "low": 169.37,
    "close": 170.14,
    "body_pct": 0.6530612244897888,
    "upper_shadow_pct": 0.21428571428572465,
    "lower_shadow_pct": 0.13265306122448653,
    "position_in_window": 0.2105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-03-03 05:15:00+00:00",
    "candle_index": 21,
    "open": 170.13,
    "high": 170.46,
    "low": 169.24,
    "close": 169.29,
    "body_pct": 0.6885245901639379,
    "upper_shadow_pct": 0.27049180327869904,
    "lower_shadow_pct": 0.04098360655736311,
    "position_in_window": 0.2211,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-03-03 05:30:00+00:00",
    "candle_index": 22,
    "open": 169.29,
    "high": 170.33,
    "low": 169.17,
    "close": 170.14,
    "body_pct": 0.7327586206896345,
    "upper_shadow_pct": 0.16379310344829487,
    "lower_shadow_pct": 0.10344827586207066,
    "position_in_window": 0.2316,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-03-03 06:00:00+00:00",
    "candle_index": 24,
    "open": 169.8,
    "high": 169.8,
    "low": 168.27,
    "close": 168.41,
    "body_pct": 0.9084967320261528,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.09150326797384722,
    "position_in_window": 0.2526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-03-03 06:15:00+00:00",
    "candle_index": 25,
    "open": 168.41,
    "high": 168.48,
    "low": 166.79,
    "close": 166.8,
    "body_pct": 0.9526627218934837,
    "upper_shadow_pct": 0.04142011834319129,
    "lower_shadow_pct": 0.005917159763325053,
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
    "timestamp": "2025-03-03 06:30:00+00:00",
    "candle_index": 26,
    "open": 166.8,
    "high": 166.8,
    "low": 163.14,
    "close": 163.56,
    "body_pct": 0.8852459016393407,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.1147540983606593,
    "position_in_window": 0.2737,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-03-03 07:00:00+00:00",
    "candle_index": 28,
    "open": 161.82,
    "high": 162.55,
    "low": 159.8,
    "close": 161.69,
    "body_pct": 0.04727272727272562,
    "upper_shadow_pct": 0.26545454545455205,
    "lower_shadow_pct": 0.6872727272727223,
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
    "timestamp": "2025-03-03 07:15:00+00:00",
    "candle_index": 29,
    "open": 161.69,
    "high": 162.41,
    "low": 160.1,
    "close": 161.82,
    "body_pct": 0.05627705627705425,
    "upper_shadow_pct": 0.25541125541125664,
    "lower_shadow_pct": 0.6883116883116891,
    "position_in_window": 0.3053,
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
    "timestamp": "2025-03-03 07:30:00+00:00",
    "candle_index": 30,
    "open": 161.82,
    "high": 162.62,
    "low": 160.9,
    "close": 161.55,
    "body_pct": 0.15697674418603605,
    "upper_shadow_pct": 0.4651162790697744,
    "lower_shadow_pct": 0.3779069767441896,
    "position_in_window": 0.3158,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2025-03-03 08:00:00+00:00",
    "candle_index": 32,
    "open": 162.27,
    "high": 163.37,
    "low": 162.14,
    "close": 162.66,
    "body_pct": 0.31707317073169156,
    "upper_shadow_pct": 0.5772357723577215,
    "lower_shadow_pct": 0.10569105691058696,
    "position_in_window": 0.3368,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2025-03-03 09:00:00+00:00",
    "candle_index": 36,
    "open": 158.55,
    "high": 159.94,
    "low": 157.5,
    "close": 158.81,
    "body_pct": 0.1065573770491767,
    "upper_shadow_pct": 0.4631147540983592,
    "lower_shadow_pct": 0.4303278688524641,
    "position_in_window": 0.3789,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2025-03-03 09:15:00+00:00",
    "candle_index": 37,
    "open": 158.81,
    "high": 159.99,
    "low": 156.83,
    "close": 159.92,
    "body_pct": 0.35126582278480584,
    "upper_shadow_pct": 0.022151898734184074,
    "lower_shadow_pct": 0.6265822784810101,
    "position_in_window": 0.3895,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-03-03 09:30:00+00:00",
    "candle_index": 38,
    "open": 159.92,
    "high": 160.58,
    "low": 159.28,
    "close": 159.97,
    "body_pct": 0.038461538461546874,
    "upper_shadow_pct": 0.4692307692307756,
    "lower_shadow_pct": 0.4923076923076775,
    "position_in_window": 0.4,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "DOJI_INDECISION"
    ]
  },
  {
    "timestamp": "2025-03-03 09:45:00+00:00",
    "candle_index": 39,
    "open": 159.97,
    "high": 160.8,
    "low": 158.82,
    "close": 159.93,
    "body_pct": 0.020202020202016,
    "upper_shadow_pct": 0.41919191919192167,
    "lower_shadow_pct": 0.5606060606060623,
    "position_in_window": 0.4105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "DOJI_INDECISION"
    ]
  }
]
```
### Doji / spinning top / small body cluster
```json
{
  "doji_count": 12,
  "doji_ratio": 0.125,
  "small_body_count": 26,
  "small_body_ratio": 0.2708333333333333,
  "bullish_body_total": 35.589999999999975,
  "bearish_body_total": 72.18999999999997
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
      "previous_timestamp": "2025-03-03 00:15:00+00:00",
      "timestamp": "2025-03-03 00:30:00+00:00",
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
      "previous_timestamp": "2025-03-03 00:15:00+00:00",
      "timestamp": "2025-03-03 00:30:00+00:00",
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
      "previous_timestamp": "2025-03-03 02:15:00+00:00",
      "timestamp": "2025-03-03 02:30:00+00:00",
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
      "previous_timestamp": "2025-03-03 02:15:00+00:00",
      "timestamp": "2025-03-03 02:30:00+00:00",
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
      "previous_timestamp": "2025-03-03 03:30:00+00:00",
      "timestamp": "2025-03-03 03:45:00+00:00",
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
      "previous_timestamp": "2025-03-03 03:30:00+00:00",
      "timestamp": "2025-03-03 03:45:00+00:00",
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
      "previous_timestamp": "2025-03-03 04:00:00+00:00",
      "timestamp": "2025-03-03 04:15:00+00:00",
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
      "previous_timestamp": "2025-03-03 04:00:00+00:00",
      "timestamp": "2025-03-03 04:15:00+00:00",
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
      "previous_timestamp": "2025-03-03 04:45:00+00:00",
      "timestamp": "2025-03-03 05:00:00+00:00",
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
      "previous_timestamp": "2025-03-03 04:45:00+00:00",
      "timestamp": "2025-03-03 05:00:00+00:00",
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
      "previous_timestamp": "2025-03-03 05:15:00+00:00",
      "timestamp": "2025-03-03 05:30:00+00:00",
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
      "previous_timestamp": "2025-03-03 05:15:00+00:00",
      "timestamp": "2025-03-03 05:30:00+00:00",
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
      "previous_timestamp": "2025-03-03 07:00:00+00:00",
      "timestamp": "2025-03-03 07:15:00+00:00",
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
      "previous_timestamp": "2025-03-03 07:00:00+00:00",
      "timestamp": "2025-03-03 07:15:00+00:00",
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
      "previous_timestamp": "2025-03-03 07:15:00+00:00",
      "timestamp": "2025-03-03 07:30:00+00:00",
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
      "previous_timestamp": "2025-03-03 07:15:00+00:00",
      "timestamp": "2025-03-03 07:30:00+00:00",
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
      "previous_timestamp": "2025-03-03 07:30:00+00:00",
      "timestamp": "2025-03-03 07:45:00+00:00",
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
      "previous_timestamp": "2025-03-03 07:30:00+00:00",
      "timestamp": "2025-03-03 07:45:00+00:00",
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
      "previous_timestamp": "2025-03-03 08:00:00+00:00",
      "timestamp": "2025-03-03 08:15:00+00:00",
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
      "previous_timestamp": "2025-03-03 08:00:00+00:00",
      "timestamp": "2025-03-03 08:15:00+00:00",
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
CLOSE_NEAR_LOW, LONG_UPPER_SHADOW_REJECTION, STRONG_BEARISH_CANDLE_BODY, SMALL_BODY_INDECISION, DOJI_INDECISION, SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED, CANDLE_PATTERN_NEEDS_TREND_CONTEXT, LONG_LOWER_SHADOW_REJECTION, SPINNING_TOP_INDECISION, STRONG_BULLISH_CANDLE_BODY, CLOSE_NEAR_HIGH, HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED, BEARISH_ENGULFING_CONTEXT, ENGULFING_WITHOUT_FOLLOW_THROUGH, BULLISH_ENGULFING_CONTEXT, BEARISH_BELT_HOLD_CONTEXT_REQUIRED, INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED, REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH, GRAVESTONE_DOJI_CONTEXT, BULLISH_BELT_HOLD_CONTEXT_REQUIRED, LONG_LEGGED_DOJI_CONTEXT, RICKSHAW_MAN_DOJI_CONTEXT, HANGING_MAN_LIKE_CONTEXT_REQUIRED, BULLISH_HARAMI_CONTEXT, HARAMI_CROSS_CONTEXT, BEARISH_SEPARATING_LINES_CONTEXT, TWEEZERS_BOTTOM_CONTEXT_REQUIRED, TWEEZERS_TOP_CONTEXT_REQUIRED, BULLISH_SEPARATING_LINES_CONTEXT, DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT, DOJI_TOP_CONTEXT_REQUIRED, BEARISH_HARAMI_CONTEXT, THREE_BLACK_CROWS_CONTEXT, THREE_ADVANCING_WHITE_SOLDIERS_CONTEXT, INVERTED_THREE_BUDDHA_BOTTOM_CONTEXT_REQUIRED, BEARISH_BODY_DOMINANCE

## 2. Altunina trend context
### Swing structure
```json
[
  {
    "index": 3,
    "timestamp": "2025-03-03 00:45:00+00:00",
    "price": 174.11,
    "point_type": "LOW"
  },
  {
    "index": 4,
    "timestamp": "2025-03-03 01:00:00+00:00",
    "price": 176.36,
    "point_type": "HIGH"
  },
  {
    "index": 9,
    "timestamp": "2025-03-03 02:15:00+00:00",
    "price": 168.95,
    "point_type": "LOW"
  },
  {
    "index": 11,
    "timestamp": "2025-03-03 02:45:00+00:00",
    "price": 171.96,
    "point_type": "HIGH"
  },
  {
    "index": 14,
    "timestamp": "2025-03-03 03:30:00+00:00",
    "price": 168.11,
    "point_type": "LOW"
  },
  {
    "index": 17,
    "timestamp": "2025-03-03 04:15:00+00:00",
    "price": 170.57,
    "point_type": "HIGH"
  },
  {
    "index": 19,
    "timestamp": "2025-03-03 04:45:00+00:00",
    "price": 169.2,
    "point_type": "LOW"
  },
  {
    "index": 21,
    "timestamp": "2025-03-03 05:15:00+00:00",
    "price": 170.46,
    "point_type": "HIGH"
  },
  {
    "index": 28,
    "timestamp": "2025-03-03 07:00:00+00:00",
    "price": 159.8,
    "point_type": "LOW"
  },
  {
    "index": 32,
    "timestamp": "2025-03-03 08:00:00+00:00",
    "price": 163.37,
    "point_type": "HIGH"
  },
  {
    "index": 37,
    "timestamp": "2025-03-03 09:15:00+00:00",
    "price": 156.83,
    "point_type": "LOW"
  },
  {
    "index": 44,
    "timestamp": "2025-03-03 11:00:00+00:00",
    "price": 161.92,
    "point_type": "HIGH"
  },
  {
    "index": 45,
    "timestamp": "2025-03-03 11:15:00+00:00",
    "price": 160.25,
    "point_type": "LOW"
  },
  {
    "index": 46,
    "timestamp": "2025-03-03 11:30:00+00:00",
    "price": 161.91,
    "point_type": "HIGH"
  },
  {
    "index": 47,
    "timestamp": "2025-03-03 11:45:00+00:00",
    "price": 160.45,
    "point_type": "LOW"
  },
  {
    "index": 48,
    "timestamp": "2025-03-03 12:00:00+00:00",
    "price": 164.13,
    "point_type": "HIGH"
  },
  {
    "index": 50,
    "timestamp": "2025-03-03 12:30:00+00:00",
    "price": 161.22,
    "point_type": "LOW"
  },
  {
    "index": 54,
    "timestamp": "2025-03-03 13:30:00+00:00",
    "price": 167.07,
    "point_type": "HIGH"
  },
  {
    "index": 59,
    "timestamp": "2025-03-03 14:45:00+00:00",
    "price": 154.07,
    "point_type": "LOW"
  },
  {
    "index": 62,
    "timestamp": "2025-03-03 15:30:00+00:00",
    "price": 159.64,
    "point_type": "HIGH"
  },
  {
    "index": 64,
    "timestamp": "2025-03-03 16:00:00+00:00",
    "price": 155.87,
    "point_type": "LOW"
  },
  {
    "index": 65,
    "timestamp": "2025-03-03 16:15:00+00:00",
    "price": 159.29,
    "point_type": "HIGH"
  },
  {
    "index": 71,
    "timestamp": "2025-03-03 17:45:00+00:00",
    "price": 154.72,
    "point_type": "LOW"
  },
  {
    "index": 78,
    "timestamp": "2025-03-03 19:30:00+00:00",
    "price": 148.04,
    "point_type": "HIGH"
  },
  {
    "index": 79,
    "timestamp": "2025-03-03 19:45:00+00:00",
    "price": 140.05,
    "point_type": "LOW"
  },
  {
    "index": 81,
    "timestamp": "2025-03-03 20:15:00+00:00",
    "price": 144.78,
    "point_type": "HIGH"
  },
  {
    "index": 82,
    "timestamp": "2025-03-03 20:30:00+00:00",
    "price": 141.57,
    "point_type": "LOW"
  },
  {
    "index": 84,
    "timestamp": "2025-03-03 21:00:00+00:00",
    "price": 144.97,
    "point_type": "HIGH"
  },
  {
    "index": 87,
    "timestamp": "2025-03-03 21:45:00+00:00",
    "price": 139.21,
    "point_type": "LOW"
  },
  {
    "index": 91,
    "timestamp": "2025-03-03 22:45:00+00:00",
    "price": 143.79,
    "point_type": "HIGH"
  },
  {
    "index": 92,
    "timestamp": "2025-03-03 23:00:00+00:00",
    "price": 141.95,
    "point_type": "LOW"
  },
  {
    "index": 94,
    "timestamp": "2025-03-03 23:30:00+00:00",
    "price": 144.21,
    "point_type": "HIGH"
  }
]
```
### Higher highs / lower highs
```json
{
  "raw_swing_count": 41,
  "swing_count": 32,
  "leg_count": 31,
  "structure_direction": "SIDEWAYS_STRUCTURE",
  "total_movement": 135.47999999999993,
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
    "lower_price": 141.57,
    "upper_price": 141.95,
    "mid_price": 141.73333333333332,
    "touch_count": 3,
    "source_indexes": [
      82,
      85,
      92
    ],
    "zone_width": 0.37999999999999545,
    "zone_width_ratio": 0.0026810912511758852,
    "formed_at_index": 92,
    "first_touch_index": 82,
    "last_touch_index": 92,
    "source_point_types": [
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
    "lower_price": 159.61,
    "upper_price": 159.8,
    "mid_price": 159.68333333333334,
    "touch_count": 3,
    "source_indexes": [
      28,
      62,
      71
    ],
    "zone_width": 0.18999999999999773,
    "zone_width_ratio": 0.0011898549211981906,
    "formed_at_index": 71,
    "first_touch_index": 28,
    "last_touch_index": 71,
    "source_point_types": [
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
  "is_detected": false,
  "lower_boundary": 141.57,
  "upper_boundary": 159.8,
  "midline": 150.685,
  "width": 18.230000000000018,
  "width_ratio": 0.12098085409961189,
  "touch_count": 6,
  "inside_close_ratio": 0.5230769230769231,
  "formed_at_index": 92,
  "first_touch_index": 28,
  "duration_candles": 65,
  "boundary_alternation_count": 1
}
```
### Range high / low
See trading range object above.
### Price position inside range
```json
{
  "swing_count": 41,
  "zone_count": 12,
  "range_detected": false,
  "range_formed_at_index": 92,
  "range_duration_candles": 65,
  "inside_close_ratio": 0.5230769230769231,
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
SCHWAGER_SUPPORT_ZONE_IDENTIFIED, SCHWAGER_PREVIOUS_EXTREME_ZONE_IDENTIFIED, SCHWAGER_SUPPORT_ZONE_HELD, SCHWAGER_RESISTANCE_ZONE_IDENTIFIED, SCHWAGER_RESISTANCE_ZONE_HELD, SCHWAGER_ZONE_TOO_WIDE, SCHWAGER_RANGE_NOT_CONFIRMED

## 4. BookEvidenceMatrix
### Bullish evidence
Count: 35
### Bearish evidence
Count: 37
### Neutral/range evidence
Count: 331
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
  "total_evidence_count": 403,
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
The engine returned UNKNOWN because the composer status was FALLBACK_UNKNOWN and selected UNKNOWN. The strongest visible candidate scores after clamping were UP=1.000 and DOWN=1.000; fallback reason: COMPOSER_CONSERVATIVE_FALLBACK_UNKNOWN. The reference label is EXPECTED_DOWN and remains descriptive, not ground truth.
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
