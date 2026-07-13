# solusdt_15m_mixed_001 вЂ” Market Evidence Trace

## Window
- Symbol: SOLUSDT
- Interval: 15m
- Period: 2025-01-24T00:00:00+00:00 вЂ” 2025-01-24T23:45:00+00:00
- Reference label: EXPECTED_UNKNOWN_OR_MIXED
- Selection reason: top deterministic MIXED OHLC candidate

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
    "timestamp": "2025-01-24 00:15:00+00:00",
    "candle_index": 1,
    "open": 254.75,
    "high": 256.39,
    "low": 253.95,
    "close": 256.19,
    "body_pct": 0.5901639344262292,
    "upper_shadow_pct": 0.08196721311474951,
    "lower_shadow_pct": 0.32786885245902136,
    "position_in_window": 0.0105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-01-24 00:30:00+00:00",
    "candle_index": 2,
    "open": 256.19,
    "high": 256.46,
    "low": 253.97,
    "close": 254.05,
    "body_pct": 0.8594377510040172,
    "upper_shadow_pct": 0.10843373493975257,
    "lower_shadow_pct": 0.03212851405623017,
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
    "timestamp": "2025-01-24 00:45:00+00:00",
    "candle_index": 3,
    "open": 254.06,
    "high": 255.0,
    "low": 252.27,
    "close": 252.73,
    "body_pct": 0.4871794871794936,
    "upper_shadow_pct": 0.34432234432234476,
    "lower_shadow_pct": 0.16849816849816163,
    "position_in_window": 0.0316,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-01-24 01:00:00+00:00",
    "candle_index": 4,
    "open": 252.74,
    "high": 253.05,
    "low": 250.92,
    "close": 251.09,
    "body_pct": 0.7746478873239376,
    "upper_shadow_pct": 0.14553990610328582,
    "lower_shadow_pct": 0.07981220657277653,
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
    "timestamp": "2025-01-24 01:15:00+00:00",
    "candle_index": 5,
    "open": 251.09,
    "high": 252.74,
    "low": 250.31,
    "close": 252.69,
    "body_pct": 0.6584362139917653,
    "upper_shadow_pct": 0.02057613168724742,
    "lower_shadow_pct": 0.32098765432098725,
    "position_in_window": 0.0526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-01-24 01:30:00+00:00",
    "candle_index": 6,
    "open": 252.69,
    "high": 252.8,
    "low": 250.6,
    "close": 250.82,
    "body_pct": 0.8499999999999954,
    "upper_shadow_pct": 0.05000000000000581,
    "lower_shadow_pct": 0.09999999999999871,
    "position_in_window": 0.0632,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-01-24 02:30:00+00:00",
    "candle_index": 10,
    "open": 250.17,
    "high": 251.08,
    "low": 249.34,
    "close": 249.83,
    "body_pct": 0.19540229885055932,
    "upper_shadow_pct": 0.5229885057471381,
    "lower_shadow_pct": 0.2816091954023026,
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
    "timestamp": "2025-01-24 03:00:00+00:00",
    "candle_index": 12,
    "open": 248.69,
    "high": 250.97,
    "low": 248.51,
    "close": 249.02,
    "body_pct": 0.13414634146341928,
    "upper_shadow_pct": 0.7926829268292611,
    "lower_shadow_pct": 0.07317073170731961,
    "position_in_window": 0.1263,
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
    "timestamp": "2025-01-24 03:15:00+00:00",
    "candle_index": 13,
    "open": 249.02,
    "high": 251.65,
    "low": 247.18,
    "close": 250.21,
    "body_pct": 0.26621923937360137,
    "upper_shadow_pct": 0.322147651006711,
    "lower_shadow_pct": 0.4116331096196877,
    "position_in_window": 0.1368,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION"
    ]
  },
  {
    "timestamp": "2025-01-24 03:30:00+00:00",
    "candle_index": 14,
    "open": 250.21,
    "high": 253.59,
    "low": 250.17,
    "close": 253.2,
    "body_pct": 0.8742690058479435,
    "upper_shadow_pct": 0.11403508771930204,
    "lower_shadow_pct": 0.011695906432754467,
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
    "timestamp": "2025-01-24 04:00:00+00:00",
    "candle_index": 16,
    "open": 252.23,
    "high": 253.14,
    "low": 251.31,
    "close": 252.86,
    "body_pct": 0.34426229508198325,
    "upper_shadow_pct": 0.15300546448086075,
    "lower_shadow_pct": 0.502732240437156,
    "position_in_window": 0.1684,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-01-24 04:15:00+00:00",
    "candle_index": 17,
    "open": 252.86,
    "high": 252.88,
    "low": 250.95,
    "close": 251.29,
    "body_pct": 0.8134715025906819,
    "upper_shadow_pct": 0.010362694300508674,
    "lower_shadow_pct": 0.17616580310880944,
    "position_in_window": 0.1789,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-01-24 04:30:00+00:00",
    "candle_index": 18,
    "open": 251.3,
    "high": 253.3,
    "low": 250.6,
    "close": 253.07,
    "body_pct": 0.6555555555555447,
    "upper_shadow_pct": 0.08518518518519139,
    "lower_shadow_pct": 0.25925925925926396,
    "position_in_window": 0.1895,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-01-24 04:45:00+00:00",
    "candle_index": 19,
    "open": 253.08,
    "high": 255.39,
    "low": 253.08,
    "close": 255.31,
    "body_pct": 0.9653679653679719,
    "upper_shadow_pct": 0.03463203463202814,
    "lower_shadow_pct": 0.0,
    "position_in_window": 0.2,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-01-24 05:00:00+00:00",
    "candle_index": 20,
    "open": 255.3,
    "high": 259.53,
    "low": 254.55,
    "close": 258.57,
    "body_pct": 0.6566265060240978,
    "upper_shadow_pct": 0.19277108433734677,
    "lower_shadow_pct": 0.1506024096385554,
    "position_in_window": 0.2105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-01-24 05:15:00+00:00",
    "candle_index": 21,
    "open": 258.57,
    "high": 260.72,
    "low": 258.49,
    "close": 259.46,
    "body_pct": 0.3991031390134435,
    "upper_shadow_pct": 0.5650224215246805,
    "lower_shadow_pct": 0.035874439461875976,
    "position_in_window": 0.2211,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2025-01-24 05:30:00+00:00",
    "candle_index": 22,
    "open": 259.46,
    "high": 260.33,
    "low": 258.91,
    "close": 259.22,
    "body_pct": 0.1690140845070135,
    "upper_shadow_pct": 0.612676056338049,
    "lower_shadow_pct": 0.21830985915493747,
    "position_in_window": 0.2316,
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
    "timestamp": "2025-01-24 05:45:00+00:00",
    "candle_index": 23,
    "open": 259.23,
    "high": 261.39,
    "low": 258.58,
    "close": 261.31,
    "body_pct": 0.7402135231316663,
    "upper_shadow_pct": 0.028469750889674027,
    "lower_shadow_pct": 0.23131672597865963,
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
    "timestamp": "2025-01-24 06:15:00+00:00",
    "candle_index": 25,
    "open": 260.51,
    "high": 262.29,
    "low": 260.07,
    "close": 260.15,
    "body_pct": 0.1621621621621663,
    "upper_shadow_pct": 0.8018018018018053,
    "lower_shadow_pct": 0.036036036036028424,
    "position_in_window": 0.2632,
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
    "timestamp": "2025-01-24 06:45:00+00:00",
    "candle_index": 27,
    "open": 261.45,
    "high": 264.18,
    "low": 261.45,
    "close": 263.61,
    "body_pct": 0.7912087912087951,
    "upper_shadow_pct": 0.2087912087912049,
    "lower_shadow_pct": 0.0,
    "position_in_window": 0.2842,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-01-24 07:00:00+00:00",
    "candle_index": 28,
    "open": 263.62,
    "high": 264.44,
    "low": 261.23,
    "close": 261.67,
    "body_pct": 0.607476635514019,
    "upper_shadow_pct": 0.25545171339563816,
    "lower_shadow_pct": 0.13707165109034283,
    "position_in_window": 0.2947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-01-24 07:15:00+00:00",
    "candle_index": 29,
    "open": 261.66,
    "high": 262.55,
    "low": 261.34,
    "close": 261.55,
    "body_pct": 0.09090909090909945,
    "upper_shadow_pct": 0.7355371900826112,
    "lower_shadow_pct": 0.1735537190082893,
    "position_in_window": 0.3053,
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
    "timestamp": "2025-01-24 07:30:00+00:00",
    "candle_index": 30,
    "open": 261.55,
    "high": 261.78,
    "low": 259.8,
    "close": 260.21,
    "body_pct": 0.6767676767677061,
    "upper_shadow_pct": 0.11616161616159891,
    "lower_shadow_pct": 0.20707070707069503,
    "position_in_window": 0.3158,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-01-24 07:45:00+00:00",
    "candle_index": 31,
    "open": 260.21,
    "high": 260.8,
    "low": 259.58,
    "close": 259.7,
    "body_pct": 0.4180327868852291,
    "upper_shadow_pct": 0.4836065573770645,
    "lower_shadow_pct": 0.09836065573770644,
    "position_in_window": 0.3263,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-01-24 08:00:00+00:00",
    "candle_index": 32,
    "open": 259.7,
    "high": 261.94,
    "low": 259.68,
    "close": 261.59,
    "body_pct": 0.8362831858407053,
    "upper_shadow_pct": 0.15486725663717882,
    "lower_shadow_pct": 0.008849557522115881,
    "position_in_window": 0.3368,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-01-24 08:15:00+00:00",
    "candle_index": 33,
    "open": 261.58,
    "high": 263.8,
    "low": 261.28,
    "close": 263.76,
    "body_pct": 0.8650793650793546,
    "upper_shadow_pct": 0.01587301587302375,
    "lower_shadow_pct": 0.11904761904762173,
    "position_in_window": 0.3474,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-01-24 08:45:00+00:00",
    "candle_index": 35,
    "open": 264.52,
    "high": 265.1,
    "low": 263.82,
    "close": 264.29,
    "body_pct": 0.17968749999996567,
    "upper_shadow_pct": 0.4531250000000215,
    "lower_shadow_pct": 0.3671875000000128,
    "position_in_window": 0.3684,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2025-01-24 09:00:00+00:00",
    "candle_index": 36,
    "open": 264.29,
    "high": 265.3,
    "low": 263.53,
    "close": 264.1,
    "body_pct": 0.10734463276835796,
    "upper_shadow_pct": 0.5706214689265361,
    "lower_shadow_pct": 0.322033898305106,
    "position_in_window": 0.3789,
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
    "timestamp": "2025-01-24 09:15:00+00:00",
    "candle_index": 37,
    "open": 264.1,
    "high": 264.25,
    "low": 263.01,
    "close": 263.2,
    "body_pct": 0.7258064516129255,
    "upper_shadow_pct": 0.12096774193546465,
    "lower_shadow_pct": 0.15322580645160994,
    "position_in_window": 0.3895,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-01-24 09:45:00+00:00",
    "candle_index": 39,
    "open": 263.77,
    "high": 264.55,
    "low": 263.24,
    "close": 263.82,
    "body_pct": 0.03816793893130632,
    "upper_shadow_pct": 0.5572519083969595,
    "lower_shadow_pct": 0.4045801526717342,
    "position_in_window": 0.4105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "DOJI_INDECISION"
    ]
  }
]
```
### Doji / spinning top / small body cluster
```json
{
  "doji_count": 6,
  "doji_ratio": 0.0625,
  "small_body_count": 28,
  "small_body_ratio": 0.2916666666666667,
  "bullish_body_total": 51.82999999999984,
  "bearish_body_total": 51.63000000000011
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
      "previous_timestamp": "2025-01-24 00:15:00+00:00",
      "timestamp": "2025-01-24 00:30:00+00:00",
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
      "previous_timestamp": "2025-01-24 00:15:00+00:00",
      "timestamp": "2025-01-24 00:30:00+00:00",
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
      "previous_timestamp": "2025-01-24 01:15:00+00:00",
      "timestamp": "2025-01-24 01:30:00+00:00",
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
      "previous_timestamp": "2025-01-24 01:15:00+00:00",
      "timestamp": "2025-01-24 01:30:00+00:00",
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
      "previous_timestamp": "2025-01-24 02:00:00+00:00",
      "timestamp": "2025-01-24 02:15:00+00:00",
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
      "previous_timestamp": "2025-01-24 02:00:00+00:00",
      "timestamp": "2025-01-24 02:15:00+00:00",
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
      "previous_timestamp": "2025-01-24 04:00:00+00:00",
      "timestamp": "2025-01-24 04:15:00+00:00",
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
      "previous_timestamp": "2025-01-24 04:00:00+00:00",
      "timestamp": "2025-01-24 04:15:00+00:00",
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
      "previous_timestamp": "2025-01-24 07:45:00+00:00",
      "timestamp": "2025-01-24 08:00:00+00:00",
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
      "previous_timestamp": "2025-01-24 07:45:00+00:00",
      "timestamp": "2025-01-24 08:00:00+00:00",
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
      "previous_timestamp": "2025-01-24 09:45:00+00:00",
      "timestamp": "2025-01-24 10:00:00+00:00",
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
      "previous_timestamp": "2025-01-24 09:45:00+00:00",
      "timestamp": "2025-01-24 10:00:00+00:00",
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
      "previous_timestamp": "2025-01-24 10:15:00+00:00",
      "timestamp": "2025-01-24 10:30:00+00:00",
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
      "previous_timestamp": "2025-01-24 10:15:00+00:00",
      "timestamp": "2025-01-24 10:30:00+00:00",
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
      "previous_timestamp": "2025-01-24 11:15:00+00:00",
      "timestamp": "2025-01-24 11:30:00+00:00",
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
      "previous_timestamp": "2025-01-24 11:15:00+00:00",
      "timestamp": "2025-01-24 11:30:00+00:00",
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
      "previous_timestamp": "2025-01-24 11:45:00+00:00",
      "timestamp": "2025-01-24 12:00:00+00:00",
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
      "previous_timestamp": "2025-01-24 11:45:00+00:00",
      "timestamp": "2025-01-24 12:00:00+00:00",
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
      "previous_timestamp": "2025-01-24 14:30:00+00:00",
      "timestamp": "2025-01-24 14:45:00+00:00",
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
      "previous_timestamp": "2025-01-24 14:30:00+00:00",
      "timestamp": "2025-01-24 14:45:00+00:00",
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
CLOSE_NEAR_HIGH, STRONG_BEARISH_CANDLE_BODY, CLOSE_NEAR_LOW, SMALL_BODY_INDECISION, SPINNING_TOP_INDECISION, LONG_UPPER_SHADOW_REJECTION, SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED, CANDLE_PATTERN_NEEDS_TREND_CONTEXT, STRONG_BULLISH_CANDLE_BODY, DOJI_INDECISION, LONG_LOWER_SHADOW_REJECTION, HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED, BEARISH_ENGULFING_CONTEXT, ENGULFING_WITHOUT_FOLLOW_THROUGH, BULLISH_ENGULFING_CONTEXT, BEARISH_BELT_HOLD_CONTEXT_REQUIRED, BULLISH_BELT_HOLD_CONTEXT_REQUIRED, INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED, REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH, LONG_LEGGED_DOJI_CONTEXT, RICKSHAW_MAN_DOJI_CONTEXT, HANGING_MAN_LIKE_CONTEXT_REQUIRED, TWEEZERS_TOP_CONTEXT_REQUIRED, TWEEZERS_BOTTOM_CONTEXT_REQUIRED, BEARISH_HARAMI_CONTEXT, BEARISH_SEPARATING_LINES_CONTEXT, BULLISH_HARAMI_CONTEXT, HARAMI_CROSS_CONTEXT, DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT, DOJI_TOP_CONTEXT_REQUIRED, BULLISH_SEPARATING_LINES_CONTEXT, THREE_ADVANCING_WHITE_SOLDIERS_CONTEXT

## 2. Altunina trend context
### Swing structure
```json
[
  {
    "index": 2,
    "timestamp": "2025-01-24 00:30:00+00:00",
    "price": 256.46,
    "point_type": "HIGH"
  },
  {
    "index": 5,
    "timestamp": "2025-01-24 01:15:00+00:00",
    "price": 250.31,
    "point_type": "LOW"
  },
  {
    "index": 6,
    "timestamp": "2025-01-24 01:30:00+00:00",
    "price": 252.8,
    "point_type": "HIGH"
  },
  {
    "index": 8,
    "timestamp": "2025-01-24 02:00:00+00:00",
    "price": 248.33,
    "point_type": "LOW"
  },
  {
    "index": 10,
    "timestamp": "2025-01-24 02:30:00+00:00",
    "price": 251.08,
    "point_type": "HIGH"
  },
  {
    "index": 13,
    "timestamp": "2025-01-24 03:15:00+00:00",
    "price": 247.18,
    "point_type": "LOW"
  },
  {
    "index": 14,
    "timestamp": "2025-01-24 03:30:00+00:00",
    "price": 253.59,
    "point_type": "HIGH"
  },
  {
    "index": 18,
    "timestamp": "2025-01-24 04:30:00+00:00",
    "price": 250.6,
    "point_type": "LOW"
  },
  {
    "index": 21,
    "timestamp": "2025-01-24 05:15:00+00:00",
    "price": 260.72,
    "point_type": "HIGH"
  },
  {
    "index": 23,
    "timestamp": "2025-01-24 05:45:00+00:00",
    "price": 258.58,
    "point_type": "LOW"
  },
  {
    "index": 28,
    "timestamp": "2025-01-24 07:00:00+00:00",
    "price": 264.44,
    "point_type": "HIGH"
  },
  {
    "index": 31,
    "timestamp": "2025-01-24 07:45:00+00:00",
    "price": 259.58,
    "point_type": "LOW"
  },
  {
    "index": 36,
    "timestamp": "2025-01-24 09:00:00+00:00",
    "price": 265.3,
    "point_type": "HIGH"
  },
  {
    "index": 40,
    "timestamp": "2025-01-24 10:00:00+00:00",
    "price": 262.6,
    "point_type": "LOW"
  },
  {
    "index": 42,
    "timestamp": "2025-01-24 10:30:00+00:00",
    "price": 266.79,
    "point_type": "HIGH"
  },
  {
    "index": 46,
    "timestamp": "2025-01-24 11:30:00+00:00",
    "price": 264.64,
    "point_type": "LOW"
  },
  {
    "index": 48,
    "timestamp": "2025-01-24 12:00:00+00:00",
    "price": 267.7,
    "point_type": "HIGH"
  },
  {
    "index": 49,
    "timestamp": "2025-01-24 12:15:00+00:00",
    "price": 264.27,
    "point_type": "LOW"
  },
  {
    "index": 51,
    "timestamp": "2025-01-24 12:45:00+00:00",
    "price": 266.1,
    "point_type": "HIGH"
  },
  {
    "index": 52,
    "timestamp": "2025-01-24 13:00:00+00:00",
    "price": 263.63,
    "point_type": "LOW"
  },
  {
    "index": 59,
    "timestamp": "2025-01-24 14:45:00+00:00",
    "price": 270.18,
    "point_type": "HIGH"
  },
  {
    "index": 62,
    "timestamp": "2025-01-24 15:30:00+00:00",
    "price": 260.84,
    "point_type": "LOW"
  },
  {
    "index": 65,
    "timestamp": "2025-01-24 16:15:00+00:00",
    "price": 264.82,
    "point_type": "HIGH"
  },
  {
    "index": 68,
    "timestamp": "2025-01-24 17:00:00+00:00",
    "price": 261.37,
    "point_type": "LOW"
  },
  {
    "index": 72,
    "timestamp": "2025-01-24 18:00:00+00:00",
    "price": 265.49,
    "point_type": "HIGH"
  },
  {
    "index": 79,
    "timestamp": "2025-01-24 19:45:00+00:00",
    "price": 260.45,
    "point_type": "LOW"
  },
  {
    "index": 80,
    "timestamp": "2025-01-24 20:00:00+00:00",
    "price": 262.39,
    "point_type": "HIGH"
  },
  {
    "index": 81,
    "timestamp": "2025-01-24 20:15:00+00:00",
    "price": 258.04,
    "point_type": "LOW"
  },
  {
    "index": 84,
    "timestamp": "2025-01-24 21:00:00+00:00",
    "price": 259.29,
    "point_type": "HIGH"
  },
  {
    "index": 85,
    "timestamp": "2025-01-24 21:15:00+00:00",
    "price": 256.33,
    "point_type": "LOW"
  },
  {
    "index": 86,
    "timestamp": "2025-01-24 21:30:00+00:00",
    "price": 261.43,
    "point_type": "HIGH"
  },
  {
    "index": 89,
    "timestamp": "2025-01-24 22:15:00+00:00",
    "price": 255.0,
    "point_type": "LOW"
  },
  {
    "index": 90,
    "timestamp": "2025-01-24 22:30:00+00:00",
    "price": 256.85,
    "point_type": "HIGH"
  },
  {
    "index": 93,
    "timestamp": "2025-01-24 23:15:00+00:00",
    "price": 252.81,
    "point_type": "LOW"
  }
]
```
### Higher highs / lower highs
```json
{
  "raw_swing_count": 44,
  "swing_count": 34,
  "leg_count": 33,
  "structure_direction": "SIDEWAYS_STRUCTURE",
  "total_movement": 138.09000000000037,
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
    "lower_price": 260.45,
    "upper_price": 261.43,
    "mid_price": 261.0066666666667,
    "touch_count": 6,
    "source_indexes": [
      21,
      28,
      62,
      68,
      79,
      86
    ],
    "zone_width": 0.9800000000000182,
    "zone_width_ratio": 0.0037546933667084543,
    "formed_at_index": 86,
    "first_touch_index": 21,
    "last_touch_index": 86,
    "source_point_types": [
      "HIGH",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
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
    "lower_price": 265.18,
    "upper_price": 266.1,
    "mid_price": 265.58,
    "touch_count": 6,
    "source_indexes": [
      34,
      36,
      40,
      45,
      51,
      72
    ],
    "zone_width": 0.9200000000000159,
    "zone_width_ratio": 0.0034641162738158595,
    "formed_at_index": 72,
    "first_touch_index": 34,
    "last_touch_index": 72,
    "source_point_types": [
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
  "lower_boundary": 260.45,
  "upper_boundary": 266.1,
  "midline": 263.275,
  "width": 5.650000000000034,
  "width_ratio": 0.021460450099705763,
  "touch_count": 12,
  "inside_close_ratio": 0.7272727272727273,
  "formed_at_index": 86,
  "first_touch_index": 21,
  "duration_candles": 66,
  "boundary_alternation_count": 4
}
```
### Range high / low
See trading range object above.
### Price position inside range
```json
{
  "swing_count": 44,
  "zone_count": 12,
  "range_detected": true,
  "range_formed_at_index": 86,
  "range_duration_candles": 66,
  "inside_close_ratio": 0.7272727272727273,
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
  "breakout_index": 87,
  "boundary_price": 260.45,
  "breakout_close": 257.61,
  "distance_ratio": 0.010904204261854388,
  "returned_to_range": false,
  "follow_through_count": 5,
  "evidence": [
    {
      "source": "SCHWAGER",
      "code": "SCHWAGER_BEARISH_RANGE_BREAKDOWN_CONTEXT",
      "description": "Closing price moved below the range boundary",
      "contribution": -0.12,
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
        "distance_ratio": 0.02837396813207904
      }
    }
  ],
  "analysis_start_index": 87,
  "confirmation_method": "CLOSE_COUNT_AND_DISTANCE",
  "confirmation_close_count": 6,
  "extreme_index": 92,
  "extreme_price": 253.06,
  "maximum_distance_ratio": 0.02837396813207904,
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
SCHWAGER_SUPPORT_ZONE_IDENTIFIED, SCHWAGER_SUPPORT_ZONE_HELD, SCHWAGER_ZONE_TOO_WIDE, SCHWAGER_RESISTANCE_ZONE_IDENTIFIED, SCHWAGER_RESISTANCE_ZONE_HELD, SCHWAGER_PREVIOUS_EXTREME_ZONE_IDENTIFIED, SCHWAGER_TRADING_RANGE_DETECTED, SCHWAGER_PRICE_INSIDE_RANGE, SCHWAGER_RANGE_UPPER_BOUNDARY_HELD, SCHWAGER_RANGE_LOWER_BOUNDARY_HELD, SCHWAGER_RANGE_DURATION_CONFIRMED, SCHWAGER_RANGE_BOUNDARY_ALTERNATION_CONFIRMED, SCHWAGER_BEARISH_RANGE_BREAKDOWN_CONTEXT, SCHWAGER_BREAKOUT_REQUIRES_CONFIRMATION, SCHWAGER_BREAKOUT_FOLLOW_THROUGH_CONFIRMED, SCHWAGER_BREAKOUT_CONFIRMED_BY_CLOSE_COUNT, SCHWAGER_BREAKOUT_CONFIRMED_BY_DISTANCE

## 4. BookEvidenceMatrix
### Bullish evidence
Count: 24
### Bearish evidence
Count: 40
### Neutral/range evidence
Count: 313
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
  "total_evidence_count": 377,
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
  "FLAT": 0.5454545454545454,
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
    "score": 0.5454545454545454
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
