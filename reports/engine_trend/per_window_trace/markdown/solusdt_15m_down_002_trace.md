# solusdt_15m_down_002 вЂ” Market Evidence Trace

## Window
- Symbol: SOLUSDT
- Interval: 15m
- Period: 2025-02-24T00:00:00+00:00 вЂ” 2025-02-24T23:45:00+00:00
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
    "timestamp": "2025-02-24 00:00:00+00:00",
    "candle_index": 0,
    "open": 167.94,
    "high": 169.62,
    "low": 167.94,
    "close": 169.56,
    "body_pct": 0.9642857142857131,
    "upper_shadow_pct": 0.03571428571428692,
    "lower_shadow_pct": 0.0,
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
    "timestamp": "2025-02-24 00:30:00+00:00",
    "candle_index": 2,
    "open": 169.07,
    "high": 169.08,
    "low": 166.86,
    "close": 167.27,
    "body_pct": 0.8108108108108035,
    "upper_shadow_pct": 0.004504504504513213,
    "lower_shadow_pct": 0.18468468468468324,
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
    "timestamp": "2025-02-24 00:45:00+00:00",
    "candle_index": 3,
    "open": 167.27,
    "high": 167.61,
    "low": 166.58,
    "close": 166.62,
    "body_pct": 0.6310679611650534,
    "upper_shadow_pct": 0.33009708737864374,
    "lower_shadow_pct": 0.03883495145630291,
    "position_in_window": 0.0316,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-24 01:00:00+00:00",
    "candle_index": 4,
    "open": 166.62,
    "high": 166.77,
    "low": 164.89,
    "close": 165.21,
    "body_pct": 0.7499999999999887,
    "upper_shadow_pct": 0.07978723404255521,
    "lower_shadow_pct": 0.17021276595745613,
    "position_in_window": 0.0421,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-24 01:15:00+00:00",
    "candle_index": 5,
    "open": 165.22,
    "high": 165.85,
    "low": 164.76,
    "close": 164.83,
    "body_pct": 0.35779816513760104,
    "upper_shadow_pct": 0.5779816513761408,
    "lower_shadow_pct": 0.06422018348625814,
    "position_in_window": 0.0526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-24 01:45:00+00:00",
    "candle_index": 7,
    "open": 164.3,
    "high": 164.7,
    "low": 163.3,
    "close": 163.64,
    "body_pct": 0.47142857142859695,
    "upper_shadow_pct": 0.2857142857142741,
    "lower_shadow_pct": 0.24285714285712895,
    "position_in_window": 0.0737,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-24 02:45:00+00:00",
    "candle_index": 11,
    "open": 163.53,
    "high": 163.92,
    "low": 162.59,
    "close": 162.67,
    "body_pct": 0.6466165413534014,
    "upper_shadow_pct": 0.2932330827067602,
    "lower_shadow_pct": 0.06015037593983838,
    "position_in_window": 0.1158,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-24 03:30:00+00:00",
    "candle_index": 14,
    "open": 161.51,
    "high": 162.57,
    "low": 160.56,
    "close": 162.27,
    "body_pct": 0.37810945273632973,
    "upper_shadow_pct": 0.14925373134327577,
    "lower_shadow_pct": 0.47263681592039447,
    "position_in_window": 0.1474,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-02-24 03:45:00+00:00",
    "candle_index": 15,
    "open": 162.28,
    "high": 162.33,
    "low": 161.0,
    "close": 161.01,
    "body_pct": 0.9548872180451115,
    "upper_shadow_pct": 0.03759398496241421,
    "lower_shadow_pct": 0.007518796992474294,
    "position_in_window": 0.1579,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-24 04:00:00+00:00",
    "candle_index": 16,
    "open": 161.02,
    "high": 161.24,
    "low": 160.21,
    "close": 160.36,
    "body_pct": 0.6407766990291222,
    "upper_shadow_pct": 0.2135922330097074,
    "lower_shadow_pct": 0.1456310679611704,
    "position_in_window": 0.1684,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-24 04:15:00+00:00",
    "candle_index": 17,
    "open": 160.36,
    "high": 160.76,
    "low": 160.0,
    "close": 160.11,
    "body_pct": 0.32894736842105654,
    "upper_shadow_pct": 0.5263157894736606,
    "lower_shadow_pct": 0.14473684210528284,
    "position_in_window": 0.1789,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-24 04:30:00+00:00",
    "candle_index": 18,
    "open": 160.1,
    "high": 160.11,
    "low": 156.88,
    "close": 158.83,
    "body_pct": 0.39318885448915625,
    "upper_shadow_pct": 0.0030959752322041083,
    "lower_shadow_pct": 0.6037151702786396,
    "position_in_window": 0.1895,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2025-02-24 04:45:00+00:00",
    "candle_index": 19,
    "open": 158.83,
    "high": 159.87,
    "low": 158.72,
    "close": 158.79,
    "body_pct": 0.0347826086956698,
    "upper_shadow_pct": 0.9043478260869451,
    "lower_shadow_pct": 0.06086956521738507,
    "position_in_window": 0.2,
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
    "timestamp": "2025-02-24 05:00:00+00:00",
    "candle_index": 20,
    "open": 158.78,
    "high": 159.61,
    "low": 158.14,
    "close": 159.5,
    "body_pct": 0.4897959183673371,
    "upper_shadow_pct": 0.07482993197279701,
    "lower_shadow_pct": 0.4353741496598659,
    "position_in_window": 0.2105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-02-24 05:15:00+00:00",
    "candle_index": 21,
    "open": 159.49,
    "high": 160.24,
    "low": 159.09,
    "close": 159.56,
    "body_pct": 0.06086956521738507,
    "upper_shadow_pct": 0.59130434782609,
    "lower_shadow_pct": 0.34782608695652495,
    "position_in_window": 0.2211,
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
    "timestamp": "2025-02-24 05:30:00+00:00",
    "candle_index": 22,
    "open": 159.55,
    "high": 160.42,
    "low": 159.51,
    "close": 160.31,
    "body_pct": 0.8351648351648283,
    "upper_shadow_pct": 0.12087912087910509,
    "lower_shadow_pct": 0.04395604395606661,
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
    "timestamp": "2025-02-24 05:45:00+00:00",
    "candle_index": 23,
    "open": 160.31,
    "high": 160.51,
    "low": 159.7,
    "close": 159.86,
    "body_pct": 0.5555555555555399,
    "upper_shadow_pct": 0.24691358024689886,
    "lower_shadow_pct": 0.1975308641975612,
    "position_in_window": 0.2421,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-24 06:00:00+00:00",
    "candle_index": 24,
    "open": 159.86,
    "high": 159.91,
    "low": 159.07,
    "close": 159.08,
    "body_pct": 0.9285714285714262,
    "upper_shadow_pct": 0.05952380952378898,
    "lower_shadow_pct": 0.011904761904784865,
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
    "timestamp": "2025-02-24 06:15:00+00:00",
    "candle_index": 25,
    "open": 159.07,
    "high": 159.63,
    "low": 158.72,
    "close": 159.53,
    "body_pct": 0.5054945054945161,
    "upper_shadow_pct": 0.10989010989010406,
    "lower_shadow_pct": 0.3846153846153798,
    "position_in_window": 0.2632,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-02-24 07:00:00+00:00",
    "candle_index": 28,
    "open": 160.77,
    "high": 161.73,
    "low": 160.76,
    "close": 161.18,
    "body_pct": 0.422680412371131,
    "upper_shadow_pct": 0.5670103092783336,
    "lower_shadow_pct": 0.010309278350535401,
    "position_in_window": 0.2947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2025-02-24 07:15:00+00:00",
    "candle_index": 29,
    "open": 161.17,
    "high": 161.31,
    "low": 160.81,
    "close": 161.28,
    "body_pct": 0.22000000000002728,
    "upper_shadow_pct": 0.060000000000002274,
    "lower_shadow_pct": 0.7199999999999704,
    "position_in_window": 0.3053,
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
    "timestamp": "2025-02-24 07:30:00+00:00",
    "candle_index": 30,
    "open": 161.28,
    "high": 161.75,
    "low": 160.9,
    "close": 160.94,
    "body_pct": 0.4000000000000067,
    "upper_shadow_pct": 0.5529411764705906,
    "lower_shadow_pct": 0.047058823529402716,
    "position_in_window": 0.3158,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-24 07:45:00+00:00",
    "candle_index": 31,
    "open": 160.94,
    "high": 161.6,
    "low": 160.9,
    "close": 160.99,
    "body_pct": 0.07142857142858883,
    "upper_shadow_pct": 0.8714285714285644,
    "lower_shadow_pct": 0.057142857142846705,
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
    "timestamp": "2025-02-24 08:00:00+00:00",
    "candle_index": 32,
    "open": 160.99,
    "high": 161.1,
    "low": 159.74,
    "close": 159.78,
    "body_pct": 0.8897058823529567,
    "upper_shadow_pct": 0.08088235294116648,
    "lower_shadow_pct": 0.029411764705876822,
    "position_in_window": 0.3368,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-24 08:15:00+00:00",
    "candle_index": 33,
    "open": 159.79,
    "high": 159.89,
    "low": 158.27,
    "close": 158.36,
    "body_pct": 0.8827160493827158,
    "upper_shadow_pct": 0.061728395061725796,
    "lower_shadow_pct": 0.05555555555555848,
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
    "timestamp": "2025-02-24 08:30:00+00:00",
    "candle_index": 34,
    "open": 158.36,
    "high": 158.92,
    "low": 157.81,
    "close": 158.18,
    "body_pct": 0.16216216216217047,
    "upper_shadow_pct": 0.5045045045044877,
    "lower_shadow_pct": 0.33333333333334186,
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
    "timestamp": "2025-02-24 08:45:00+00:00",
    "candle_index": 35,
    "open": 158.18,
    "high": 158.68,
    "low": 157.72,
    "close": 157.94,
    "body_pct": 0.2500000000000074,
    "upper_shadow_pct": 0.520833333333329,
    "lower_shadow_pct": 0.22916666666666358,
    "position_in_window": 0.3684,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-02-24 09:00:00+00:00",
    "candle_index": 36,
    "open": 157.95,
    "high": 159.43,
    "low": 157.73,
    "close": 159.25,
    "body_pct": 0.7647058823529402,
    "upper_shadow_pct": 0.10588235294117943,
    "lower_shadow_pct": 0.1294117647058804,
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
    "timestamp": "2025-02-24 09:15:00+00:00",
    "candle_index": 37,
    "open": 159.24,
    "high": 160.37,
    "low": 158.85,
    "close": 160.02,
    "body_pct": 0.5131578947368394,
    "upper_shadow_pct": 0.23026315789473156,
    "lower_shadow_pct": 0.25657894736842907,
    "position_in_window": 0.3895,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-02-24 09:30:00+00:00",
    "candle_index": 38,
    "open": 160.01,
    "high": 160.34,
    "low": 159.26,
    "close": 159.26,
    "body_pct": 0.6944444444444364,
    "upper_shadow_pct": 0.3055555555555636,
    "lower_shadow_pct": 0.0,
    "position_in_window": 0.4,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  }
]
```
### Doji / spinning top / small body cluster
```json
{
  "doji_count": 4,
  "doji_ratio": 0.041666666666666664,
  "small_body_count": 23,
  "small_body_ratio": 0.23958333333333334,
  "bullish_body_total": 30.80000000000004,
  "bearish_body_total": 56.95999999999995
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
      "previous_timestamp": "2025-02-24 01:45:00+00:00",
      "timestamp": "2025-02-24 02:00:00+00:00",
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
      "previous_timestamp": "2025-02-24 01:45:00+00:00",
      "timestamp": "2025-02-24 02:00:00+00:00",
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
      "previous_timestamp": "2025-02-24 03:30:00+00:00",
      "timestamp": "2025-02-24 03:45:00+00:00",
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
      "previous_timestamp": "2025-02-24 03:30:00+00:00",
      "timestamp": "2025-02-24 03:45:00+00:00",
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
      "previous_timestamp": "2025-02-24 04:45:00+00:00",
      "timestamp": "2025-02-24 05:00:00+00:00",
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
      "previous_timestamp": "2025-02-24 04:45:00+00:00",
      "timestamp": "2025-02-24 05:00:00+00:00",
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
      "previous_timestamp": "2025-02-24 07:15:00+00:00",
      "timestamp": "2025-02-24 07:30:00+00:00",
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
      "previous_timestamp": "2025-02-24 07:15:00+00:00",
      "timestamp": "2025-02-24 07:30:00+00:00",
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
      "previous_timestamp": "2025-02-24 07:45:00+00:00",
      "timestamp": "2025-02-24 08:00:00+00:00",
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
      "previous_timestamp": "2025-02-24 07:45:00+00:00",
      "timestamp": "2025-02-24 08:00:00+00:00",
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
      "previous_timestamp": "2025-02-24 11:30:00+00:00",
      "timestamp": "2025-02-24 11:45:00+00:00",
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
      "previous_timestamp": "2025-02-24 11:30:00+00:00",
      "timestamp": "2025-02-24 11:45:00+00:00",
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
      "previous_timestamp": "2025-02-24 12:00:00+00:00",
      "timestamp": "2025-02-24 12:15:00+00:00",
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
      "previous_timestamp": "2025-02-24 12:00:00+00:00",
      "timestamp": "2025-02-24 12:15:00+00:00",
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
      "previous_timestamp": "2025-02-24 12:45:00+00:00",
      "timestamp": "2025-02-24 13:00:00+00:00",
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
      "previous_timestamp": "2025-02-24 12:45:00+00:00",
      "timestamp": "2025-02-24 13:00:00+00:00",
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
      "previous_timestamp": "2025-02-24 17:30:00+00:00",
      "timestamp": "2025-02-24 17:45:00+00:00",
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
      "previous_timestamp": "2025-02-24 17:30:00+00:00",
      "timestamp": "2025-02-24 17:45:00+00:00",
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
      "previous_timestamp": "2025-02-24 18:30:00+00:00",
      "timestamp": "2025-02-24 18:45:00+00:00",
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
      "previous_timestamp": "2025-02-24 18:30:00+00:00",
      "timestamp": "2025-02-24 18:45:00+00:00",
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
STRONG_BULLISH_CANDLE_BODY, CLOSE_NEAR_HIGH, STRONG_BEARISH_CANDLE_BODY, CLOSE_NEAR_LOW, LONG_UPPER_SHADOW_REJECTION, LONG_LOWER_SHADOW_REJECTION, SMALL_BODY_INDECISION, DOJI_INDECISION, SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED, CANDLE_PATTERN_NEEDS_TREND_CONTEXT, SPINNING_TOP_INDECISION, HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED, BULLISH_ENGULFING_CONTEXT, ENGULFING_WITHOUT_FOLLOW_THROUGH, BEARISH_ENGULFING_CONTEXT, BULLISH_BELT_HOLD_CONTEXT_REQUIRED, BEARISH_BELT_HOLD_CONTEXT_REQUIRED, INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED, REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH, GRAVESTONE_DOJI_CONTEXT, HANGING_MAN_LIKE_CONTEXT_REQUIRED, LONG_LEGGED_DOJI_CONTEXT, RICKSHAW_MAN_DOJI_CONTEXT, TWEEZERS_TOP_CONTEXT_REQUIRED, TWEEZERS_BOTTOM_CONTEXT_REQUIRED, BULLISH_SEPARATING_LINES_CONTEXT, BEARISH_SEPARATING_LINES_CONTEXT, BULLISH_HARAMI_CONTEXT, BEARISH_HARAMI_CONTEXT, HARAMI_CROSS_CONTEXT, DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT, DOJI_TOP_CONTEXT_REQUIRED, THREE_BLACK_CROWS_CONTEXT, BEARISH_BODY_DOMINANCE

## 2. Altunina trend context
### Swing structure
```json
[
  {
    "index": 1,
    "timestamp": "2025-02-24 00:15:00+00:00",
    "price": 169.69,
    "point_type": "HIGH"
  },
  {
    "index": 7,
    "timestamp": "2025-02-24 01:45:00+00:00",
    "price": 163.3,
    "point_type": "LOW"
  },
  {
    "index": 8,
    "timestamp": "2025-02-24 02:00:00+00:00",
    "price": 164.99,
    "point_type": "HIGH"
  },
  {
    "index": 18,
    "timestamp": "2025-02-24 04:30:00+00:00",
    "price": 156.88,
    "point_type": "LOW"
  },
  {
    "index": 23,
    "timestamp": "2025-02-24 05:45:00+00:00",
    "price": 160.51,
    "point_type": "HIGH"
  },
  {
    "index": 25,
    "timestamp": "2025-02-24 06:15:00+00:00",
    "price": 158.72,
    "point_type": "LOW"
  },
  {
    "index": 30,
    "timestamp": "2025-02-24 07:30:00+00:00",
    "price": 161.75,
    "point_type": "HIGH"
  },
  {
    "index": 35,
    "timestamp": "2025-02-24 08:45:00+00:00",
    "price": 157.72,
    "point_type": "LOW"
  },
  {
    "index": 37,
    "timestamp": "2025-02-24 09:15:00+00:00",
    "price": 160.37,
    "point_type": "HIGH"
  },
  {
    "index": 42,
    "timestamp": "2025-02-24 10:30:00+00:00",
    "price": 155.38,
    "point_type": "LOW"
  },
  {
    "index": 43,
    "timestamp": "2025-02-24 10:45:00+00:00",
    "price": 157.29,
    "point_type": "HIGH"
  },
  {
    "index": 44,
    "timestamp": "2025-02-24 11:00:00+00:00",
    "price": 155.95,
    "point_type": "LOW"
  },
  {
    "index": 50,
    "timestamp": "2025-02-24 12:30:00+00:00",
    "price": 159.77,
    "point_type": "HIGH"
  },
  {
    "index": 52,
    "timestamp": "2025-02-24 13:00:00+00:00",
    "price": 158.0,
    "point_type": "LOW"
  },
  {
    "index": 54,
    "timestamp": "2025-02-24 13:30:00+00:00",
    "price": 160.41,
    "point_type": "HIGH"
  },
  {
    "index": 63,
    "timestamp": "2025-02-24 15:45:00+00:00",
    "price": 150.65,
    "point_type": "LOW"
  },
  {
    "index": 64,
    "timestamp": "2025-02-24 16:00:00+00:00",
    "price": 154.17,
    "point_type": "HIGH"
  },
  {
    "index": 65,
    "timestamp": "2025-02-24 16:15:00+00:00",
    "price": 151.95,
    "point_type": "LOW"
  },
  {
    "index": 66,
    "timestamp": "2025-02-24 16:30:00+00:00",
    "price": 154.14,
    "point_type": "HIGH"
  },
  {
    "index": 68,
    "timestamp": "2025-02-24 17:00:00+00:00",
    "price": 152.6,
    "point_type": "LOW"
  },
  {
    "index": 71,
    "timestamp": "2025-02-24 17:45:00+00:00",
    "price": 155.15,
    "point_type": "HIGH"
  },
  {
    "index": 76,
    "timestamp": "2025-02-24 19:00:00+00:00",
    "price": 151.06,
    "point_type": "LOW"
  },
  {
    "index": 77,
    "timestamp": "2025-02-24 19:15:00+00:00",
    "price": 152.55,
    "point_type": "HIGH"
  },
  {
    "index": 78,
    "timestamp": "2025-02-24 19:30:00+00:00",
    "price": 147.86,
    "point_type": "LOW"
  },
  {
    "index": 83,
    "timestamp": "2025-02-24 20:45:00+00:00",
    "price": 152.68,
    "point_type": "HIGH"
  },
  {
    "index": 84,
    "timestamp": "2025-02-24 21:00:00+00:00",
    "price": 149.48,
    "point_type": "LOW"
  },
  {
    "index": 86,
    "timestamp": "2025-02-24 21:30:00+00:00",
    "price": 152.53,
    "point_type": "HIGH"
  },
  {
    "index": 88,
    "timestamp": "2025-02-24 22:00:00+00:00",
    "price": 141.1,
    "point_type": "LOW"
  },
  {
    "index": 90,
    "timestamp": "2025-02-24 22:30:00+00:00",
    "price": 147.78,
    "point_type": "HIGH"
  },
  {
    "index": 91,
    "timestamp": "2025-02-24 22:45:00+00:00",
    "price": 138.0,
    "point_type": "LOW"
  }
]
```
### Higher highs / lower highs
```json
{
  "raw_swing_count": 39,
  "swing_count": 30,
  "leg_count": 29,
  "structure_direction": "SIDEWAYS_STRUCTURE",
  "total_movement": 118.57000000000005,
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
    "lower_price": 157.72,
    "upper_price": 158.14,
    "mid_price": 157.95333333333335,
    "touch_count": 3,
    "source_indexes": [
      20,
      35,
      52
    ],
    "zone_width": 0.4199999999999875,
    "zone_width_ratio": 0.0026590132106528563,
    "formed_at_index": 52,
    "first_touch_index": 20,
    "last_touch_index": 52,
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
    "lower_price": 160.37,
    "upper_price": 160.56,
    "mid_price": 160.46249999999998,
    "touch_count": 4,
    "source_indexes": [
      14,
      23,
      37,
      54
    ],
    "zone_width": 0.18999999999999773,
    "zone_width_ratio": 0.0011840772766222498,
    "formed_at_index": 54,
    "first_touch_index": 14,
    "last_touch_index": 54,
    "source_point_types": [
      "LOW",
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
  "lower_boundary": 157.72,
  "upper_boundary": 160.56,
  "midline": 159.14,
  "width": 2.8400000000000034,
  "width_ratio": 0.01784592182983539,
  "touch_count": 7,
  "inside_close_ratio": 0.7073170731707317,
  "formed_at_index": 54,
  "first_touch_index": 14,
  "duration_candles": 41,
  "boundary_alternation_count": 6
}
```
### Range high / low
See trading range object above.
### Price position inside range
```json
{
  "swing_count": 39,
  "zone_count": 14,
  "range_detected": true,
  "range_formed_at_index": 54,
  "range_duration_candles": 41,
  "inside_close_ratio": 0.7073170731707317,
  "breakout_direction": "DOWNWARD",
  "breakout_status": "CONFIRMED",
  "polarity_status": "SUPPORT_TO_RESISTANCE"
}
```
### Breakout / breakdown attempts
```json
{
  "direction": "DOWNWARD",
  "status": "CONFIRMED",
  "breakout_index": 57,
  "boundary_price": 157.72,
  "breakout_close": 157.08,
  "distance_ratio": 0.004057823991884265,
  "returned_to_range": false,
  "follow_through_count": 5,
  "evidence": [
    {
      "source": "SCHWAGER",
      "code": "SCHWAGER_BEARISH_RANGE_BREAKDOWN_CONTEXT",
      "description": "Closing price moved below the range boundary",
      "contribution": -0.12,
      "metadata": {
        "breakout_index": 57
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
        "distance_ratio": 0.03899315242201373
      }
    }
  ],
  "analysis_start_index": 55,
  "confirmation_method": "CLOSE_COUNT_AND_DISTANCE",
  "confirmation_close_count": 6,
  "extreme_index": 61,
  "extreme_price": 151.57,
  "maximum_distance_ratio": 0.03899315242201373,
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
SCHWAGER_SUPPORT_ZONE_IDENTIFIED, SCHWAGER_PREVIOUS_EXTREME_ZONE_IDENTIFIED, SCHWAGER_RESISTANCE_ZONE_IDENTIFIED, SCHWAGER_RESISTANCE_ZONE_HELD, SCHWAGER_SUPPORT_ZONE_HELD, SCHWAGER_TRADING_RANGE_DETECTED, SCHWAGER_PRICE_INSIDE_RANGE, SCHWAGER_RANGE_UPPER_BOUNDARY_HELD, SCHWAGER_RANGE_LOWER_BOUNDARY_HELD, SCHWAGER_RANGE_DURATION_CONFIRMED, SCHWAGER_RANGE_BOUNDARY_ALTERNATION_CONFIRMED, SCHWAGER_BEARISH_RANGE_BREAKDOWN_CONTEXT, SCHWAGER_BREAKOUT_REQUIRES_CONFIRMATION, SCHWAGER_BREAKOUT_FOLLOW_THROUGH_CONFIRMED, SCHWAGER_BREAKOUT_CONFIRMED_BY_CLOSE_COUNT, SCHWAGER_BREAKOUT_CONFIRMED_BY_DISTANCE, SCHWAGER_BREAKOUT_RETEST_HELD, SCHWAGER_SUPPORT_TURNED_RESISTANCE, SCHWAGER_POLARITY_FLIP_CONFIRMED

## 4. BookEvidenceMatrix
### Bullish evidence
Count: 19
### Bearish evidence
Count: 35
### Neutral/range evidence
Count: 328
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
  "total_evidence_count": 382,
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
  "FLAT": 0.5414634146341464,
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
    "score": 0.5414634146341464
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
