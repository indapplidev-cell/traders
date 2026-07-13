# solusdt_15m_mixed_002 вЂ” Market Evidence Trace

## Window
- Symbol: SOLUSDT
- Interval: 15m
- Period: 2026-03-01T00:00:00+00:00 вЂ” 2026-03-01T23:45:00+00:00
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
    "timestamp": "2026-03-01 00:00:00+00:00",
    "candle_index": 0,
    "open": 84.35,
    "high": 84.77,
    "low": 84.34,
    "close": 84.7,
    "body_pct": 0.8139534883721269,
    "upper_shadow_pct": 0.16279069767440554,
    "lower_shadow_pct": 0.02325581395346762,
    "position_in_window": 0.0,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-03-01 00:15:00+00:00",
    "candle_index": 1,
    "open": 84.7,
    "high": 84.87,
    "low": 84.46,
    "close": 84.49,
    "body_pct": 0.5121951219512254,
    "upper_shadow_pct": 0.4146341463414567,
    "lower_shadow_pct": 0.07317073170731792,
    "position_in_window": 0.0105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-03-01 00:30:00+00:00",
    "candle_index": 2,
    "open": 84.48,
    "high": 84.7,
    "low": 84.32,
    "close": 84.56,
    "body_pct": 0.21052631578946385,
    "upper_shadow_pct": 0.3684210526315711,
    "lower_shadow_pct": 0.4210526315789651,
    "position_in_window": 0.0211,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2026-03-01 01:15:00+00:00",
    "candle_index": 5,
    "open": 84.52,
    "high": 84.98,
    "low": 84.25,
    "close": 84.8,
    "body_pct": 0.3835616438356159,
    "upper_shadow_pct": 0.24657534246576143,
    "lower_shadow_pct": 0.3698630136986227,
    "position_in_window": 0.0526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-03-01 02:00:00+00:00",
    "candle_index": 8,
    "open": 86.75,
    "high": 88.5,
    "low": 86.75,
    "close": 88.14,
    "body_pct": 0.7942857142857146,
    "upper_shadow_pct": 0.20571428571428538,
    "lower_shadow_pct": 0.0,
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
    "timestamp": "2026-03-01 02:15:00+00:00",
    "candle_index": 9,
    "open": 88.14,
    "high": 88.63,
    "low": 87.65,
    "close": 88.2,
    "body_pct": 0.06122448979592133,
    "upper_shadow_pct": 0.4387755102040787,
    "lower_shadow_pct": 0.5,
    "position_in_window": 0.0947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "DOJI_INDECISION"
    ]
  },
  {
    "timestamp": "2026-03-01 02:30:00+00:00",
    "candle_index": 10,
    "open": 88.2,
    "high": 88.9,
    "low": 87.86,
    "close": 88.66,
    "body_pct": 0.44230769230768363,
    "upper_shadow_pct": 0.23076923076923814,
    "lower_shadow_pct": 0.32692307692307826,
    "position_in_window": 0.1053,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-03-01 02:45:00+00:00",
    "candle_index": 11,
    "open": 88.65,
    "high": 88.67,
    "low": 87.77,
    "close": 87.97,
    "body_pct": 0.7555555555555583,
    "upper_shadow_pct": 0.02222222222221766,
    "lower_shadow_pct": 0.222222222222224,
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
    "timestamp": "2026-03-01 03:00:00+00:00",
    "candle_index": 12,
    "open": 87.96,
    "high": 88.19,
    "low": 87.88,
    "close": 87.93,
    "body_pct": 0.09677419354834421,
    "upper_shadow_pct": 0.7419354838709752,
    "lower_shadow_pct": 0.16129032258068066,
    "position_in_window": 0.1263,
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
    "timestamp": "2026-03-01 03:15:00+00:00",
    "candle_index": 13,
    "open": 87.93,
    "high": 88.19,
    "low": 87.7,
    "close": 88.16,
    "body_pct": 0.46938775510202485,
    "upper_shadow_pct": 0.06122448979592133,
    "lower_shadow_pct": 0.4693877551020538,
    "position_in_window": 0.1368,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-03-01 03:30:00+00:00",
    "candle_index": 14,
    "open": 88.15,
    "high": 88.33,
    "low": 87.95,
    "close": 88.08,
    "body_pct": 0.1842105263158111,
    "upper_shadow_pct": 0.473684210526302,
    "lower_shadow_pct": 0.34210526315788686,
    "position_in_window": 0.1474,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2026-03-01 03:45:00+00:00",
    "candle_index": 15,
    "open": 88.08,
    "high": 88.27,
    "low": 87.63,
    "close": 88.02,
    "body_pct": 0.09375000000000347,
    "upper_shadow_pct": 0.29687499999999617,
    "lower_shadow_pct": 0.6093750000000003,
    "position_in_window": 0.1579,
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
    "timestamp": "2026-03-01 04:00:00+00:00",
    "candle_index": 16,
    "open": 88.02,
    "high": 88.26,
    "low": 87.52,
    "close": 87.54,
    "body_pct": 0.6486486486486268,
    "upper_shadow_pct": 0.3243243243243326,
    "lower_shadow_pct": 0.02702702702704052,
    "position_in_window": 0.1684,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-03-01 04:15:00+00:00",
    "candle_index": 17,
    "open": 87.55,
    "high": 87.82,
    "low": 86.87,
    "close": 87.68,
    "body_pct": 0.1368421052631697,
    "upper_shadow_pct": 0.147368421052619,
    "lower_shadow_pct": 0.7157894736842113,
    "position_in_window": 0.1789,
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
    "timestamp": "2026-03-01 04:30:00+00:00",
    "candle_index": 18,
    "open": 87.68,
    "high": 87.82,
    "low": 87.49,
    "close": 87.7,
    "body_pct": 0.06060606060604886,
    "upper_shadow_pct": 0.3636363636363362,
    "lower_shadow_pct": 0.5757575757576149,
    "position_in_window": 0.1895,
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
    "timestamp": "2026-03-01 05:00:00+00:00",
    "candle_index": 20,
    "open": 87.55,
    "high": 87.92,
    "low": 87.48,
    "close": 87.64,
    "body_pct": 0.20454545454546336,
    "upper_shadow_pct": 0.6363636363636422,
    "lower_shadow_pct": 0.1590909090908944,
    "position_in_window": 0.2105,
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
    "timestamp": "2026-03-01 05:30:00+00:00",
    "candle_index": 22,
    "open": 87.83,
    "high": 87.91,
    "low": 87.5,
    "close": 87.52,
    "body_pct": 0.7560975609756216,
    "upper_shadow_pct": 0.19512195121950965,
    "lower_shadow_pct": 0.04878048780486875,
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
    "timestamp": "2026-03-01 05:45:00+00:00",
    "candle_index": 23,
    "open": 87.51,
    "high": 87.64,
    "low": 87.21,
    "close": 87.26,
    "body_pct": 0.5813953488372001,
    "upper_shadow_pct": 0.30232558139533344,
    "lower_shadow_pct": 0.11627906976746645,
    "position_in_window": 0.2421,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-03-01 06:15:00+00:00",
    "candle_index": 25,
    "open": 86.63,
    "high": 86.96,
    "low": 86.6,
    "close": 86.75,
    "body_pct": 0.33333333333334647,
    "upper_shadow_pct": 0.5833333333333169,
    "lower_shadow_pct": 0.08333333333333662,
    "position_in_window": 0.2632,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2026-03-01 06:45:00+00:00",
    "candle_index": 27,
    "open": 86.4,
    "high": 86.8,
    "low": 86.16,
    "close": 86.66,
    "body_pct": 0.40624999999998546,
    "upper_shadow_pct": 0.2187500000000007,
    "lower_shadow_pct": 0.3750000000000139,
    "position_in_window": 0.2842,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-03-01 07:00:00+00:00",
    "candle_index": 28,
    "open": 86.67,
    "high": 86.89,
    "low": 86.4,
    "close": 86.75,
    "body_pct": 0.1632653061224472,
    "upper_shadow_pct": 0.28571428571428986,
    "lower_shadow_pct": 0.5510204081632629,
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
    "timestamp": "2026-03-01 07:15:00+00:00",
    "candle_index": 29,
    "open": 86.75,
    "high": 86.88,
    "low": 86.42,
    "close": 86.5,
    "body_pct": 0.5434782608695726,
    "upper_shadow_pct": 0.2826086956521679,
    "lower_shadow_pct": 0.17391304347825953,
    "position_in_window": 0.3053,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-03-01 07:45:00+00:00",
    "candle_index": 31,
    "open": 86.64,
    "high": 86.73,
    "low": 86.53,
    "close": 86.63,
    "body_pct": 0.05000000000002487,
    "upper_shadow_pct": 0.45000000000001067,
    "lower_shadow_pct": 0.4999999999999645,
    "position_in_window": 0.3263,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "DOJI_INDECISION"
    ]
  },
  {
    "timestamp": "2026-03-01 08:00:00+00:00",
    "candle_index": 32,
    "open": 86.63,
    "high": 86.83,
    "low": 86.22,
    "close": 86.7,
    "body_pct": 0.11475409836066795,
    "upper_shadow_pct": 0.2131147540983534,
    "lower_shadow_pct": 0.6721311475409787,
    "position_in_window": 0.3368,
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
    "timestamp": "2026-03-01 08:30:00+00:00",
    "candle_index": 34,
    "open": 86.53,
    "high": 86.56,
    "low": 86.32,
    "close": 86.35,
    "body_pct": 0.75,
    "upper_shadow_pct": 0.125,
    "lower_shadow_pct": 0.125,
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
    "timestamp": "2026-03-01 08:45:00+00:00",
    "candle_index": 35,
    "open": 86.35,
    "high": 86.39,
    "low": 85.07,
    "close": 85.22,
    "body_pct": 0.8560606060605979,
    "upper_shadow_pct": 0.03030303030303487,
    "lower_shadow_pct": 0.11363636363636731,
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
    "timestamp": "2026-03-01 09:00:00+00:00",
    "candle_index": 36,
    "open": 85.22,
    "high": 85.5,
    "low": 84.93,
    "close": 85.42,
    "body_pct": 0.35087719298246534,
    "upper_shadow_pct": 0.14035087719298114,
    "lower_shadow_pct": 0.5087719298245535,
    "position_in_window": 0.3789,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-03-01 09:15:00+00:00",
    "candle_index": 37,
    "open": 85.43,
    "high": 85.86,
    "low": 85.37,
    "close": 85.55,
    "body_pct": 0.2448979591836563,
    "upper_shadow_pct": 0.632653061224501,
    "lower_shadow_pct": 0.12244897959184266,
    "position_in_window": 0.3895,
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
    "timestamp": "2026-03-01 09:30:00+00:00",
    "candle_index": 38,
    "open": 85.55,
    "high": 85.6,
    "low": 84.87,
    "close": 85.0,
    "body_pct": 0.7534246575342533,
    "upper_shadow_pct": 0.06849315068492857,
    "lower_shadow_pct": 0.1780821917808182,
    "position_in_window": 0.4,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-03-01 09:45:00+00:00",
    "candle_index": 39,
    "open": 85.0,
    "high": 85.09,
    "low": 84.81,
    "close": 85.0,
    "body_pct": 0.0,
    "upper_shadow_pct": 0.3214285714285823,
    "lower_shadow_pct": 0.6785714285714177,
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
  "doji_count": 7,
  "doji_ratio": 0.07291666666666667,
  "small_body_count": 31,
  "small_body_ratio": 0.3229166666666667,
  "bullish_body_total": 14.169999999999987,
  "bearish_body_total": 14.860000000000014
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
      "previous_timestamp": "2026-03-01 00:45:00+00:00",
      "timestamp": "2026-03-01 01:00:00+00:00",
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
      "previous_timestamp": "2026-03-01 00:45:00+00:00",
      "timestamp": "2026-03-01 01:00:00+00:00",
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
      "previous_timestamp": "2026-03-01 03:00:00+00:00",
      "timestamp": "2026-03-01 03:15:00+00:00",
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
      "previous_timestamp": "2026-03-01 03:00:00+00:00",
      "timestamp": "2026-03-01 03:15:00+00:00",
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
      "previous_timestamp": "2026-03-01 04:30:00+00:00",
      "timestamp": "2026-03-01 04:45:00+00:00",
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
      "previous_timestamp": "2026-03-01 04:30:00+00:00",
      "timestamp": "2026-03-01 04:45:00+00:00",
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
      "previous_timestamp": "2026-03-01 06:15:00+00:00",
      "timestamp": "2026-03-01 06:30:00+00:00",
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
      "previous_timestamp": "2026-03-01 06:15:00+00:00",
      "timestamp": "2026-03-01 06:30:00+00:00",
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
      "previous_timestamp": "2026-03-01 07:00:00+00:00",
      "timestamp": "2026-03-01 07:15:00+00:00",
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
      "previous_timestamp": "2026-03-01 07:00:00+00:00",
      "timestamp": "2026-03-01 07:15:00+00:00",
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
      "previous_timestamp": "2026-03-01 07:45:00+00:00",
      "timestamp": "2026-03-01 08:00:00+00:00",
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
      "previous_timestamp": "2026-03-01 07:45:00+00:00",
      "timestamp": "2026-03-01 08:00:00+00:00",
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
      "previous_timestamp": "2026-03-01 08:00:00+00:00",
      "timestamp": "2026-03-01 08:15:00+00:00",
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
      "previous_timestamp": "2026-03-01 08:00:00+00:00",
      "timestamp": "2026-03-01 08:15:00+00:00",
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
      "previous_timestamp": "2026-03-01 09:15:00+00:00",
      "timestamp": "2026-03-01 09:30:00+00:00",
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
      "previous_timestamp": "2026-03-01 09:15:00+00:00",
      "timestamp": "2026-03-01 09:30:00+00:00",
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
      "previous_timestamp": "2026-03-01 10:15:00+00:00",
      "timestamp": "2026-03-01 10:30:00+00:00",
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
      "previous_timestamp": "2026-03-01 10:15:00+00:00",
      "timestamp": "2026-03-01 10:30:00+00:00",
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
      "previous_timestamp": "2026-03-01 12:30:00+00:00",
      "timestamp": "2026-03-01 12:45:00+00:00",
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
      "previous_timestamp": "2026-03-01 12:30:00+00:00",
      "timestamp": "2026-03-01 12:45:00+00:00",
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
STRONG_BULLISH_CANDLE_BODY, CLOSE_NEAR_HIGH, CLOSE_NEAR_LOW, SMALL_BODY_INDECISION, SPINNING_TOP_INDECISION, DOJI_INDECISION, STRONG_BEARISH_CANDLE_BODY, LONG_UPPER_SHADOW_REJECTION, LONG_LOWER_SHADOW_REJECTION, SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED, CANDLE_PATTERN_NEEDS_TREND_CONTEXT, BEARISH_ENGULFING_CONTEXT, ENGULFING_WITHOUT_FOLLOW_THROUGH, BULLISH_ENGULFING_CONTEXT, BULLISH_BELT_HOLD_CONTEXT_REQUIRED, LONG_LEGGED_DOJI_CONTEXT, RICKSHAW_MAN_DOJI_CONTEXT, BEARISH_BELT_HOLD_CONTEXT_REQUIRED, INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED, REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH, DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT, DOJI_TOP_CONTEXT_REQUIRED, TWEEZERS_TOP_CONTEXT_REQUIRED, BULLISH_HARAMI_CONTEXT, TWEEZERS_BOTTOM_CONTEXT_REQUIRED, BULLISH_SEPARATING_LINES_CONTEXT, HARAMI_CROSS_CONTEXT, BEARISH_SEPARATING_LINES_CONTEXT

## 2. Altunina trend context
### Swing structure
```json
[
  {
    "index": 1,
    "timestamp": "2026-03-01 00:15:00+00:00",
    "price": 84.87,
    "point_type": "HIGH"
  },
  {
    "index": 2,
    "timestamp": "2026-03-01 00:30:00+00:00",
    "price": 84.32,
    "point_type": "LOW"
  },
  {
    "index": 3,
    "timestamp": "2026-03-01 00:45:00+00:00",
    "price": 85.01,
    "point_type": "HIGH"
  },
  {
    "index": 5,
    "timestamp": "2026-03-01 01:15:00+00:00",
    "price": 84.25,
    "point_type": "LOW"
  },
  {
    "index": 10,
    "timestamp": "2026-03-01 02:30:00+00:00",
    "price": 88.9,
    "point_type": "HIGH"
  },
  {
    "index": 13,
    "timestamp": "2026-03-01 03:15:00+00:00",
    "price": 87.7,
    "point_type": "LOW"
  },
  {
    "index": 14,
    "timestamp": "2026-03-01 03:30:00+00:00",
    "price": 88.33,
    "point_type": "HIGH"
  },
  {
    "index": 17,
    "timestamp": "2026-03-01 04:15:00+00:00",
    "price": 86.87,
    "point_type": "LOW"
  },
  {
    "index": 21,
    "timestamp": "2026-03-01 05:15:00+00:00",
    "price": 88.03,
    "point_type": "HIGH"
  },
  {
    "index": 27,
    "timestamp": "2026-03-01 06:45:00+00:00",
    "price": 86.16,
    "point_type": "LOW"
  },
  {
    "index": 28,
    "timestamp": "2026-03-01 07:00:00+00:00",
    "price": 86.89,
    "point_type": "HIGH"
  },
  {
    "index": 36,
    "timestamp": "2026-03-01 09:00:00+00:00",
    "price": 84.93,
    "point_type": "LOW"
  },
  {
    "index": 37,
    "timestamp": "2026-03-01 09:15:00+00:00",
    "price": 85.86,
    "point_type": "HIGH"
  },
  {
    "index": 40,
    "timestamp": "2026-03-01 10:00:00+00:00",
    "price": 84.71,
    "point_type": "LOW"
  },
  {
    "index": 42,
    "timestamp": "2026-03-01 10:30:00+00:00",
    "price": 85.66,
    "point_type": "HIGH"
  },
  {
    "index": 43,
    "timestamp": "2026-03-01 10:45:00+00:00",
    "price": 84.99,
    "point_type": "LOW"
  },
  {
    "index": 45,
    "timestamp": "2026-03-01 11:15:00+00:00",
    "price": 85.53,
    "point_type": "HIGH"
  },
  {
    "index": 46,
    "timestamp": "2026-03-01 11:30:00+00:00",
    "price": 84.97,
    "point_type": "LOW"
  },
  {
    "index": 49,
    "timestamp": "2026-03-01 12:15:00+00:00",
    "price": 85.4,
    "point_type": "HIGH"
  },
  {
    "index": 53,
    "timestamp": "2026-03-01 13:15:00+00:00",
    "price": 84.51,
    "point_type": "LOW"
  },
  {
    "index": 55,
    "timestamp": "2026-03-01 13:45:00+00:00",
    "price": 86.98,
    "point_type": "HIGH"
  },
  {
    "index": 58,
    "timestamp": "2026-03-01 14:30:00+00:00",
    "price": 85.44,
    "point_type": "LOW"
  },
  {
    "index": 62,
    "timestamp": "2026-03-01 15:30:00+00:00",
    "price": 86.68,
    "point_type": "HIGH"
  },
  {
    "index": 69,
    "timestamp": "2026-03-01 17:15:00+00:00",
    "price": 83.18,
    "point_type": "LOW"
  },
  {
    "index": 72,
    "timestamp": "2026-03-01 18:00:00+00:00",
    "price": 85.0,
    "point_type": "HIGH"
  },
  {
    "index": 82,
    "timestamp": "2026-03-01 20:30:00+00:00",
    "price": 81.69,
    "point_type": "LOW"
  },
  {
    "index": 88,
    "timestamp": "2026-03-01 22:00:00+00:00",
    "price": 84.12,
    "point_type": "HIGH"
  },
  {
    "index": 90,
    "timestamp": "2026-03-01 22:30:00+00:00",
    "price": 82.38,
    "point_type": "LOW"
  },
  {
    "index": 92,
    "timestamp": "2026-03-01 23:00:00+00:00",
    "price": 84.08,
    "point_type": "HIGH"
  },
  {
    "index": 94,
    "timestamp": "2026-03-01 23:30:00+00:00",
    "price": 83.36,
    "point_type": "LOW"
  }
]
```
### Higher highs / lower highs
```json
{
  "raw_swing_count": 41,
  "swing_count": 30,
  "leg_count": 29,
  "structure_direction": "SIDEWAYS_STRUCTURE",
  "total_movement": 42.25000000000007,
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
    "lower_price": 84.51,
    "upper_price": 85.06,
    "mid_price": 84.881,
    "touch_count": 10,
    "source_indexes": [
      1,
      3,
      36,
      40,
      43,
      46,
      50,
      53,
      53,
      72
    ],
    "zone_width": 0.5499999999999972,
    "zone_width_ratio": 0.006479659758956624,
    "formed_at_index": 72,
    "first_touch_index": 1,
    "last_touch_index": 72,
    "source_point_types": [
      "HIGH",
      "HIGH",
      "LOW",
      "LOW",
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
    "positional_zone_type": "RESISTANCE"
  },
  "resistance_zone": {
    "zone_type": "RESISTANCE",
    "lower_price": 86.68,
    "upper_price": 86.98,
    "mid_price": 86.85,
    "touch_count": 5,
    "source_indexes": [
      17,
      28,
      32,
      55,
      62
    ],
    "zone_width": 0.29999999999999716,
    "zone_width_ratio": 0.0034542314335060122,
    "formed_at_index": 62,
    "first_touch_index": 17,
    "last_touch_index": 62,
    "source_point_types": [
      "LOW",
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
  "lower_boundary": 84.51,
  "upper_boundary": 86.98,
  "midline": 85.745,
  "width": 2.469999999999999,
  "width_ratio": 0.02880634439325907,
  "touch_count": 15,
  "inside_close_ratio": 0.6805555555555556,
  "formed_at_index": 72,
  "first_touch_index": 1,
  "duration_candles": 72,
  "boundary_alternation_count": 4
}
```
### Range high / low
See trading range object above.
### Price position inside range
```json
{
  "swing_count": 41,
  "zone_count": 10,
  "range_detected": true,
  "range_formed_at_index": 72,
  "range_duration_candles": 72,
  "inside_close_ratio": 0.6805555555555556,
  "breakout_direction": "DOWNWARD",
  "breakout_status": "CONFIRMED",
  "polarity_status": "NONE"
}
```
### Breakout / breakdown attempts
```json
{
  "direction": "DOWNWARD",
  "status": "CONFIRMED",
  "breakout_index": 73,
  "boundary_price": 84.51,
  "breakout_close": 84.25,
  "distance_ratio": 0.0030765589871021783,
  "returned_to_range": false,
  "follow_through_count": 5,
  "evidence": [
    {
      "source": "SCHWAGER",
      "code": "SCHWAGER_BEARISH_RANGE_BREAKDOWN_CONTEXT",
      "description": "Closing price moved below the range boundary",
      "contribution": -0.12,
      "metadata": {
        "breakout_index": 73
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
      "contribution": -0.08,
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
        "distance_ratio": 0.01692107442906173
      }
    }
  ],
  "analysis_start_index": 73,
  "confirmation_method": "CLOSE_COUNT_AND_DISTANCE",
  "confirmation_close_count": 6,
  "extreme_index": 78,
  "extreme_price": 83.08,
  "maximum_distance_ratio": 0.01692107442906173,
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
SCHWAGER_SUPPORT_ZONE_IDENTIFIED, SCHWAGER_PREVIOUS_EXTREME_ZONE_IDENTIFIED, SCHWAGER_SUPPORT_ZONE_HELD, SCHWAGER_RESISTANCE_ZONE_IDENTIFIED, SCHWAGER_RESISTANCE_ZONE_HELD, SCHWAGER_ZONE_TOO_WIDE, SCHWAGER_TRADING_RANGE_DETECTED, SCHWAGER_PRICE_INSIDE_RANGE, SCHWAGER_RANGE_UPPER_BOUNDARY_HELD, SCHWAGER_RANGE_LOWER_BOUNDARY_HELD, SCHWAGER_RANGE_DURATION_CONFIRMED, SCHWAGER_RANGE_BOUNDARY_ALTERNATION_CONFIRMED, SCHWAGER_BEARISH_RANGE_BREAKDOWN_CONTEXT, SCHWAGER_BREAKOUT_REQUIRES_CONFIRMATION, SCHWAGER_BREAKOUT_FOLLOW_THROUGH_CONFIRMED, SCHWAGER_BREAKOUT_CONFIRMED_BY_CLOSE_COUNT, SCHWAGER_BREAKOUT_CONFIRMED_BY_DISTANCE

## 4. BookEvidenceMatrix
### Bullish evidence
Count: 20
### Bearish evidence
Count: 34
### Neutral/range evidence
Count: 275
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
  "total_evidence_count": 329,
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
  "FLAT": 0.5361111111111112,
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
    "score": 0.5361111111111112
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
