# solusdt_15m_down_003 вЂ” Market Evidence Trace

## Window
- Symbol: SOLUSDT
- Interval: 15m
- Period: 2026-02-05T00:00:00+00:00 вЂ” 2026-02-05T23:45:00+00:00
- Reference label: EXPECTED_DOWN
- Selection reason: ranked deterministic DOWN OHLC candidate

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
    "timestamp": "2026-02-05 00:00:00+00:00",
    "candle_index": 0,
    "open": 92.11,
    "high": 92.46,
    "low": 91.84,
    "close": 91.9,
    "body_pct": 0.33870967741935004,
    "upper_shadow_pct": 0.5645161290322577,
    "lower_shadow_pct": 0.09677419354839227,
    "position_in_window": 0.0,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-02-05 00:15:00+00:00",
    "candle_index": 1,
    "open": 91.9,
    "high": 92.76,
    "low": 91.9,
    "close": 92.62,
    "body_pct": 0.8372093023255807,
    "upper_shadow_pct": 0.16279069767441937,
    "lower_shadow_pct": 0.0,
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
    "timestamp": "2026-02-05 00:45:00+00:00",
    "candle_index": 3,
    "open": 91.96,
    "high": 92.11,
    "low": 91.65,
    "close": 91.74,
    "body_pct": 0.4782608695652214,
    "upper_shadow_pct": 0.3260869565217559,
    "lower_shadow_pct": 0.19565217391302267,
    "position_in_window": 0.0316,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-02-05 01:00:00+00:00",
    "candle_index": 4,
    "open": 91.75,
    "high": 92.59,
    "low": 91.6,
    "close": 92.37,
    "body_pct": 0.6262626262626251,
    "upper_shadow_pct": 0.22222222222221905,
    "lower_shadow_pct": 0.15151515151515588,
    "position_in_window": 0.0421,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-02-05 01:15:00+00:00",
    "candle_index": 5,
    "open": 92.36,
    "high": 92.77,
    "low": 90.52,
    "close": 92.52,
    "body_pct": 0.0711111111111096,
    "upper_shadow_pct": 0.1111111111111111,
    "lower_shadow_pct": 0.8177777777777793,
    "position_in_window": 0.0526,
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
    "timestamp": "2026-02-05 01:45:00+00:00",
    "candle_index": 7,
    "open": 92.06,
    "high": 92.3,
    "low": 91.73,
    "close": 91.94,
    "body_pct": 0.2105263157894842,
    "upper_shadow_pct": 0.42105263157894346,
    "lower_shadow_pct": 0.3684210526315724,
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
    "timestamp": "2026-02-05 02:00:00+00:00",
    "candle_index": 8,
    "open": 91.94,
    "high": 92.2,
    "low": 91.09,
    "close": 91.11,
    "body_pct": 0.7477477477477465,
    "upper_shadow_pct": 0.23423423423423897,
    "lower_shadow_pct": 0.01801801801801444,
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
    "timestamp": "2026-02-05 02:15:00+00:00",
    "candle_index": 9,
    "open": 91.11,
    "high": 91.83,
    "low": 90.7,
    "close": 91.77,
    "body_pct": 0.5840707964601763,
    "upper_shadow_pct": 0.05309734513274559,
    "lower_shadow_pct": 0.3628318584070781,
    "position_in_window": 0.0947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-02-05 02:45:00+00:00",
    "candle_index": 11,
    "open": 92.44,
    "high": 92.5,
    "low": 90.75,
    "close": 90.93,
    "body_pct": 0.8628571428571377,
    "upper_shadow_pct": 0.034285714285715585,
    "lower_shadow_pct": 0.10285714285714675,
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
    "timestamp": "2026-02-05 03:00:00+00:00",
    "candle_index": 12,
    "open": 90.92,
    "high": 91.66,
    "low": 90.32,
    "close": 90.84,
    "body_pct": 0.05970149253731201,
    "upper_shadow_pct": 0.5522388059701441,
    "lower_shadow_pct": 0.388059701492544,
    "position_in_window": 0.1263,
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
    "timestamp": "2026-02-05 03:15:00+00:00",
    "candle_index": 13,
    "open": 90.84,
    "high": 91.69,
    "low": 90.24,
    "close": 90.99,
    "body_pct": 0.10344827586206289,
    "upper_shadow_pct": 0.4827586206896562,
    "lower_shadow_pct": 0.4137931034482809,
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
    "timestamp": "2026-02-05 03:30:00+00:00",
    "candle_index": 14,
    "open": 90.98,
    "high": 91.35,
    "low": 90.68,
    "close": 91.06,
    "body_pct": 0.11940298507462654,
    "upper_shadow_pct": 0.4328358208955186,
    "lower_shadow_pct": 0.44776119402985487,
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
    "timestamp": "2026-02-05 03:45:00+00:00",
    "candle_index": 15,
    "open": 91.05,
    "high": 91.2,
    "low": 90.78,
    "close": 91.15,
    "body_pct": 0.23809523809525743,
    "upper_shadow_pct": 0.1190476190476118,
    "lower_shadow_pct": 0.6428571428571308,
    "position_in_window": 0.1579,
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
    "timestamp": "2026-02-05 04:00:00+00:00",
    "candle_index": 16,
    "open": 91.14,
    "high": 91.65,
    "low": 90.33,
    "close": 90.51,
    "body_pct": 0.47727272727272113,
    "upper_shadow_pct": 0.3863636363636381,
    "lower_shadow_pct": 0.13636363636364077,
    "position_in_window": 0.1684,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-02-05 04:30:00+00:00",
    "candle_index": 18,
    "open": 91.06,
    "high": 91.92,
    "low": 90.6,
    "close": 91.84,
    "body_pct": 0.5909090909090885,
    "upper_shadow_pct": 0.06060606060605898,
    "lower_shadow_pct": 0.34848484848485256,
    "position_in_window": 0.1895,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-02-05 05:15:00+00:00",
    "candle_index": 21,
    "open": 91.47,
    "high": 91.77,
    "low": 89.94,
    "close": 90.29,
    "body_pct": 0.6448087431693955,
    "upper_shadow_pct": 0.1639344262295068,
    "lower_shadow_pct": 0.19125683060109774,
    "position_in_window": 0.2211,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-02-05 05:30:00+00:00",
    "candle_index": 22,
    "open": 90.3,
    "high": 92.11,
    "low": 89.92,
    "close": 91.81,
    "body_pct": 0.6894977168949802,
    "upper_shadow_pct": 0.13698630136986187,
    "lower_shadow_pct": 0.17351598173515792,
    "position_in_window": 0.2316,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-02-05 05:45:00+00:00",
    "candle_index": 23,
    "open": 91.82,
    "high": 91.91,
    "low": 91.0,
    "close": 91.17,
    "body_pct": 0.7142857142857076,
    "upper_shadow_pct": 0.09890109890110302,
    "lower_shadow_pct": 0.1868131868131894,
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
    "timestamp": "2026-02-05 06:15:00+00:00",
    "candle_index": 25,
    "open": 90.35,
    "high": 90.57,
    "low": 89.76,
    "close": 89.92,
    "body_pct": 0.5308641975308629,
    "upper_shadow_pct": 0.27160493827160753,
    "lower_shadow_pct": 0.19753086419752958,
    "position_in_window": 0.2632,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-02-05 06:45:00+00:00",
    "candle_index": 27,
    "open": 90.22,
    "high": 90.5,
    "low": 89.68,
    "close": 90.21,
    "body_pct": 0.012195121951225853,
    "upper_shadow_pct": 0.3414634146341506,
    "lower_shadow_pct": 0.6463414634146236,
    "position_in_window": 0.2842,
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
    "timestamp": "2026-02-05 07:00:00+00:00",
    "candle_index": 28,
    "open": 90.22,
    "high": 91.63,
    "low": 90.16,
    "close": 90.8,
    "body_pct": 0.39455782312925086,
    "upper_shadow_pct": 0.5646258503401353,
    "lower_shadow_pct": 0.040816326530613824,
    "position_in_window": 0.2947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2026-02-05 07:15:00+00:00",
    "candle_index": 29,
    "open": 90.81,
    "high": 91.66,
    "low": 90.58,
    "close": 91.46,
    "body_pct": 0.6018518518518449,
    "upper_shadow_pct": 0.18518518518518812,
    "lower_shadow_pct": 0.212962962962967,
    "position_in_window": 0.3053,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-02-05 07:45:00+00:00",
    "candle_index": 31,
    "open": 91.21,
    "high": 91.3,
    "low": 90.37,
    "close": 90.54,
    "body_pct": 0.720430107526874,
    "upper_shadow_pct": 0.09677419354839153,
    "lower_shadow_pct": 0.18279569892473446,
    "position_in_window": 0.3263,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-02-05 08:15:00+00:00",
    "candle_index": 33,
    "open": 91.14,
    "high": 91.97,
    "low": 90.84,
    "close": 91.72,
    "body_pct": 0.5132743362831864,
    "upper_shadow_pct": 0.22123893805309824,
    "lower_shadow_pct": 0.2654867256637154,
    "position_in_window": 0.3474,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-02-05 08:30:00+00:00",
    "candle_index": 34,
    "open": 91.71,
    "high": 92.46,
    "low": 91.7,
    "close": 91.98,
    "body_pct": 0.35526315789475454,
    "upper_shadow_pct": 0.6315789473684151,
    "lower_shadow_pct": 0.013157894736830296,
    "position_in_window": 0.3579,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2026-02-05 08:45:00+00:00",
    "candle_index": 35,
    "open": 91.97,
    "high": 92.24,
    "low": 91.69,
    "close": 91.77,
    "body_pct": 0.3636363636363707,
    "upper_shadow_pct": 0.4909090909090862,
    "lower_shadow_pct": 0.14545454545454312,
    "position_in_window": 0.3684,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-02-05 09:00:00+00:00",
    "candle_index": 36,
    "open": 91.77,
    "high": 93.07,
    "low": 91.74,
    "close": 92.9,
    "body_pct": 0.8496240601503843,
    "upper_shadow_pct": 0.1278195488721712,
    "lower_shadow_pct": 0.022556390977444492,
    "position_in_window": 0.3789,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-02-05 09:15:00+00:00",
    "candle_index": 37,
    "open": 92.9,
    "high": 93.43,
    "low": 92.67,
    "close": 92.79,
    "body_pct": 0.14473684210526144,
    "upper_shadow_pct": 0.6973684210526284,
    "lower_shadow_pct": 0.1578947368421102,
    "position_in_window": 0.3895,
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
    "timestamp": "2026-02-05 09:30:00+00:00",
    "candle_index": 38,
    "open": 92.79,
    "high": 92.87,
    "low": 92.25,
    "close": 92.37,
    "body_pct": 0.6774193548387074,
    "upper_shadow_pct": 0.12903225806451243,
    "lower_shadow_pct": 0.1935483870967801,
    "position_in_window": 0.4,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-02-05 09:45:00+00:00",
    "candle_index": 39,
    "open": 92.38,
    "high": 92.71,
    "low": 92.26,
    "close": 92.5,
    "body_pct": 0.2666666666666835,
    "upper_shadow_pct": 0.46666666666666456,
    "lower_shadow_pct": 0.26666666666665195,
    "position_in_window": 0.4105,
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
  "doji_count": 7,
  "doji_ratio": 0.07291666666666667,
  "small_body_count": 25,
  "small_body_ratio": 0.2604166666666667,
  "bullish_body_total": 24.66000000000001,
  "bearish_body_total": 38.45999999999995
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
      "previous_timestamp": "2026-02-05 00:00:00+00:00",
      "timestamp": "2026-02-05 00:15:00+00:00",
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
      "previous_timestamp": "2026-02-05 00:00:00+00:00",
      "timestamp": "2026-02-05 00:15:00+00:00",
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
      "previous_timestamp": "2026-02-05 02:30:00+00:00",
      "timestamp": "2026-02-05 02:45:00+00:00",
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
      "previous_timestamp": "2026-02-05 02:30:00+00:00",
      "timestamp": "2026-02-05 02:45:00+00:00",
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
      "previous_timestamp": "2026-02-05 03:00:00+00:00",
      "timestamp": "2026-02-05 03:15:00+00:00",
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
      "previous_timestamp": "2026-02-05 03:00:00+00:00",
      "timestamp": "2026-02-05 03:15:00+00:00",
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
      "previous_timestamp": "2026-02-05 08:45:00+00:00",
      "timestamp": "2026-02-05 09:00:00+00:00",
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
      "previous_timestamp": "2026-02-05 08:45:00+00:00",
      "timestamp": "2026-02-05 09:00:00+00:00",
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
      "previous_timestamp": "2026-02-05 09:45:00+00:00",
      "timestamp": "2026-02-05 10:00:00+00:00",
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
      "previous_timestamp": "2026-02-05 09:45:00+00:00",
      "timestamp": "2026-02-05 10:00:00+00:00",
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
      "previous_timestamp": "2026-02-05 14:30:00+00:00",
      "timestamp": "2026-02-05 14:45:00+00:00",
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
      "previous_timestamp": "2026-02-05 14:30:00+00:00",
      "timestamp": "2026-02-05 14:45:00+00:00",
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
      "previous_timestamp": "2026-02-05 16:00:00+00:00",
      "timestamp": "2026-02-05 16:15:00+00:00",
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
      "previous_timestamp": "2026-02-05 16:00:00+00:00",
      "timestamp": "2026-02-05 16:15:00+00:00",
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
      "previous_timestamp": "2026-02-05 16:45:00+00:00",
      "timestamp": "2026-02-05 17:00:00+00:00",
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
      "previous_timestamp": "2026-02-05 16:45:00+00:00",
      "timestamp": "2026-02-05 17:00:00+00:00",
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
      "previous_timestamp": "2026-02-05 17:15:00+00:00",
      "timestamp": "2026-02-05 17:30:00+00:00",
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
      "previous_timestamp": "2026-02-05 17:15:00+00:00",
      "timestamp": "2026-02-05 17:30:00+00:00",
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
      "previous_timestamp": "2026-02-05 18:00:00+00:00",
      "timestamp": "2026-02-05 18:15:00+00:00",
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
      "previous_timestamp": "2026-02-05 18:00:00+00:00",
      "timestamp": "2026-02-05 18:15:00+00:00",
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
LONG_UPPER_SHADOW_REJECTION, CLOSE_NEAR_LOW, STRONG_BULLISH_CANDLE_BODY, CLOSE_NEAR_HIGH, LONG_LOWER_SHADOW_REJECTION, SMALL_BODY_INDECISION, DOJI_INDECISION, SPINNING_TOP_INDECISION, STRONG_BEARISH_CANDLE_BODY, SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED, CANDLE_PATTERN_NEEDS_TREND_CONTEXT, BULLISH_ENGULFING_CONTEXT, ENGULFING_WITHOUT_FOLLOW_THROUGH, BEARISH_ENGULFING_CONTEXT, BULLISH_BELT_HOLD_CONTEXT_REQUIRED, BEARISH_BELT_HOLD_CONTEXT_REQUIRED, LONG_LEGGED_DOJI_CONTEXT, RICKSHAW_MAN_DOJI_CONTEXT, INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED, REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH, DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT, DOJI_TOP_CONTEXT_REQUIRED, TWEEZERS_TOP_CONTEXT_REQUIRED, TWEEZERS_BOTTOM_CONTEXT_REQUIRED, BULLISH_SEPARATING_LINES_CONTEXT, BEARISH_HARAMI_CONTEXT, BULLISH_HARAMI_CONTEXT, HARAMI_CROSS_CONTEXT, THREE_BLACK_CROWS_CONTEXT, BEARISH_BODY_DOMINANCE

## 2. Altunina trend context
### Swing structure
```json
[
  {
    "index": 1,
    "timestamp": "2026-02-05 00:15:00+00:00",
    "price": 92.76,
    "point_type": "HIGH"
  },
  {
    "index": 5,
    "timestamp": "2026-02-05 01:15:00+00:00",
    "price": 90.52,
    "point_type": "LOW"
  },
  {
    "index": 6,
    "timestamp": "2026-02-05 01:30:00+00:00",
    "price": 92.89,
    "point_type": "HIGH"
  },
  {
    "index": 9,
    "timestamp": "2026-02-05 02:15:00+00:00",
    "price": 90.7,
    "point_type": "LOW"
  },
  {
    "index": 10,
    "timestamp": "2026-02-05 02:30:00+00:00",
    "price": 92.72,
    "point_type": "HIGH"
  },
  {
    "index": 13,
    "timestamp": "2026-02-05 03:15:00+00:00",
    "price": 90.24,
    "point_type": "LOW"
  },
  {
    "index": 16,
    "timestamp": "2026-02-05 04:00:00+00:00",
    "price": 91.65,
    "point_type": "HIGH"
  },
  {
    "index": 17,
    "timestamp": "2026-02-05 04:15:00+00:00",
    "price": 90.32,
    "point_type": "LOW"
  },
  {
    "index": 18,
    "timestamp": "2026-02-05 04:30:00+00:00",
    "price": 91.92,
    "point_type": "HIGH"
  },
  {
    "index": 27,
    "timestamp": "2026-02-05 06:45:00+00:00",
    "price": 89.68,
    "point_type": "LOW"
  },
  {
    "index": 29,
    "timestamp": "2026-02-05 07:15:00+00:00",
    "price": 91.66,
    "point_type": "HIGH"
  },
  {
    "index": 31,
    "timestamp": "2026-02-05 07:45:00+00:00",
    "price": 90.37,
    "point_type": "LOW"
  },
  {
    "index": 34,
    "timestamp": "2026-02-05 08:30:00+00:00",
    "price": 92.46,
    "point_type": "HIGH"
  },
  {
    "index": 35,
    "timestamp": "2026-02-05 08:45:00+00:00",
    "price": 91.69,
    "point_type": "LOW"
  },
  {
    "index": 37,
    "timestamp": "2026-02-05 09:15:00+00:00",
    "price": 93.43,
    "point_type": "HIGH"
  },
  {
    "index": 40,
    "timestamp": "2026-02-05 10:00:00+00:00",
    "price": 91.72,
    "point_type": "LOW"
  },
  {
    "index": 41,
    "timestamp": "2026-02-05 10:15:00+00:00",
    "price": 92.66,
    "point_type": "HIGH"
  },
  {
    "index": 45,
    "timestamp": "2026-02-05 11:15:00+00:00",
    "price": 88.66,
    "point_type": "LOW"
  },
  {
    "index": 46,
    "timestamp": "2026-02-05 11:30:00+00:00",
    "price": 90.82,
    "point_type": "HIGH"
  },
  {
    "index": 49,
    "timestamp": "2026-02-05 12:15:00+00:00",
    "price": 88.68,
    "point_type": "LOW"
  },
  {
    "index": 52,
    "timestamp": "2026-02-05 13:00:00+00:00",
    "price": 90.06,
    "point_type": "HIGH"
  },
  {
    "index": 55,
    "timestamp": "2026-02-05 13:45:00+00:00",
    "price": 88.2,
    "point_type": "LOW"
  },
  {
    "index": 58,
    "timestamp": "2026-02-05 14:30:00+00:00",
    "price": 91.43,
    "point_type": "HIGH"
  },
  {
    "index": 62,
    "timestamp": "2026-02-05 15:30:00+00:00",
    "price": 83.44,
    "point_type": "LOW"
  },
  {
    "index": 63,
    "timestamp": "2026-02-05 15:45:00+00:00",
    "price": 85.93,
    "point_type": "HIGH"
  },
  {
    "index": 64,
    "timestamp": "2026-02-05 16:00:00+00:00",
    "price": 83.69,
    "point_type": "LOW"
  },
  {
    "index": 67,
    "timestamp": "2026-02-05 16:45:00+00:00",
    "price": 86.2,
    "point_type": "HIGH"
  },
  {
    "index": 74,
    "timestamp": "2026-02-05 18:30:00+00:00",
    "price": 81.21,
    "point_type": "LOW"
  },
  {
    "index": 76,
    "timestamp": "2026-02-05 19:00:00+00:00",
    "price": 83.31,
    "point_type": "HIGH"
  },
  {
    "index": 77,
    "timestamp": "2026-02-05 19:15:00+00:00",
    "price": 81.71,
    "point_type": "LOW"
  },
  {
    "index": 80,
    "timestamp": "2026-02-05 20:00:00+00:00",
    "price": 82.3,
    "point_type": "HIGH"
  },
  {
    "index": 82,
    "timestamp": "2026-02-05 20:30:00+00:00",
    "price": 77.68,
    "point_type": "LOW"
  },
  {
    "index": 84,
    "timestamp": "2026-02-05 21:00:00+00:00",
    "price": 81.2,
    "point_type": "HIGH"
  },
  {
    "index": 85,
    "timestamp": "2026-02-05 21:15:00+00:00",
    "price": 78.62,
    "point_type": "LOW"
  },
  {
    "index": 86,
    "timestamp": "2026-02-05 21:30:00+00:00",
    "price": 80.85,
    "point_type": "HIGH"
  },
  {
    "index": 89,
    "timestamp": "2026-02-05 22:15:00+00:00",
    "price": 77.6,
    "point_type": "LOW"
  },
  {
    "index": 92,
    "timestamp": "2026-02-05 23:00:00+00:00",
    "price": 81.63,
    "point_type": "HIGH"
  }
]
```
### Higher highs / lower highs
```json
{
  "raw_swing_count": 47,
  "swing_count": 37,
  "leg_count": 36,
  "structure_direction": "SIDEWAYS_STRUCTURE",
  "total_movement": 87.91000000000004,
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
    "lower_price": 89.68,
    "upper_price": 89.92,
    "mid_price": 89.78250000000001,
    "touch_count": 4,
    "source_indexes": [
      22,
      24,
      27,
      43
    ],
    "zone_width": 0.23999999999999488,
    "zone_width_ratio": 0.002673126722913651,
    "formed_at_index": 43,
    "first_touch_index": 22,
    "last_touch_index": 43,
    "source_point_types": [
      "LOW",
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
    "lower_price": 91.37,
    "upper_price": 91.72,
    "mid_price": 91.60142857142857,
    "touch_count": 7,
    "source_indexes": [
      2,
      13,
      16,
      29,
      35,
      40,
      58
    ],
    "zone_width": 0.3499999999999943,
    "zone_width_ratio": 0.0038209011088410354,
    "formed_at_index": 58,
    "first_touch_index": 2,
    "last_touch_index": 58,
    "source_point_types": [
      "LOW",
      "HIGH",
      "HIGH",
      "HIGH",
      "LOW",
      "LOW",
      "HIGH"
    ],
    "original_zone_type": "RESISTANCE",
    "current_zone_type": "RESISTANCE",
    "role_changed_at_index": null,
    "is_significant_single_extreme": false,
    "positional_zone_type": "RESISTANCE"
  },
  "is_detected": false,
  "lower_boundary": 89.68,
  "upper_boundary": 91.72,
  "midline": 90.7,
  "width": 2.039999999999992,
  "width_ratio": 0.022491730981256803,
  "touch_count": 11,
  "inside_close_ratio": 0.5263157894736842,
  "formed_at_index": 58,
  "first_touch_index": 2,
  "duration_candles": 57,
  "boundary_alternation_count": 4
}
```
### Range high / low
See trading range object above.
### Price position inside range
```json
{
  "swing_count": 47,
  "zone_count": 13,
  "range_detected": false,
  "range_formed_at_index": 58,
  "range_duration_candles": 57,
  "inside_close_ratio": 0.5263157894736842,
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
SCHWAGER_SUPPORT_ZONE_IDENTIFIED, SCHWAGER_SUPPORT_ZONE_HELD, SCHWAGER_RESISTANCE_ZONE_IDENTIFIED, SCHWAGER_RESISTANCE_ZONE_HELD, SCHWAGER_ZONE_TOO_WIDE, SCHWAGER_PREVIOUS_EXTREME_ZONE_IDENTIFIED, SCHWAGER_RANGE_NOT_CONFIRMED

## 4. BookEvidenceMatrix
### Bullish evidence
Count: 17
### Bearish evidence
Count: 29
### Neutral/range evidence
Count: 292
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
  "total_evidence_count": 338,
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
