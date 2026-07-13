# solusdt_15m_up_001 вЂ” Market Evidence Trace

## Window
- Symbol: SOLUSDT
- Interval: 15m
- Period: 2025-03-02T00:00:00+00:00 вЂ” 2025-03-02T23:45:00+00:00
- Reference label: EXPECTED_UP
- Selection reason: top deterministic UP OHLC candidate

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
    "timestamp": "2025-03-02 00:15:00+00:00",
    "candle_index": 1,
    "open": 144.04,
    "high": 144.04,
    "low": 142.96,
    "close": 143.12,
    "body_pct": 0.8518518518518529,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.14814814814814717,
    "position_in_window": 0.0105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-03-02 00:30:00+00:00",
    "candle_index": 2,
    "open": 143.13,
    "high": 144.8,
    "low": 143.02,
    "close": 144.53,
    "body_pct": 0.786516853932587,
    "upper_shadow_pct": 0.1516853932584326,
    "lower_shadow_pct": 0.06179775280898042,
    "position_in_window": 0.0211,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-03-02 00:45:00+00:00",
    "candle_index": 3,
    "open": 144.53,
    "high": 145.59,
    "low": 144.5,
    "close": 144.75,
    "body_pct": 0.20183486238531942,
    "upper_shadow_pct": 0.7706422018348631,
    "lower_shadow_pct": 0.02752293577981747,
    "position_in_window": 0.0316,
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
    "timestamp": "2025-03-02 01:00:00+00:00",
    "candle_index": 4,
    "open": 144.75,
    "high": 145.75,
    "low": 144.64,
    "close": 145.63,
    "body_pct": 0.7927927927927789,
    "upper_shadow_pct": 0.10810810810811088,
    "lower_shadow_pct": 0.09909909909911017,
    "position_in_window": 0.0421,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-03-02 01:15:00+00:00",
    "candle_index": 5,
    "open": 145.62,
    "high": 146.01,
    "low": 144.75,
    "close": 144.83,
    "body_pct": 0.6269841269841252,
    "upper_shadow_pct": 0.30952380952380093,
    "lower_shadow_pct": 0.06349206349207387,
    "position_in_window": 0.0526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-03-02 01:30:00+00:00",
    "candle_index": 6,
    "open": 144.83,
    "high": 144.91,
    "low": 143.77,
    "close": 143.85,
    "body_pct": 0.8596491228070438,
    "upper_shadow_pct": 0.07017543859647811,
    "lower_shadow_pct": 0.07017543859647811,
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
    "timestamp": "2025-03-02 02:00:00+00:00",
    "candle_index": 8,
    "open": 144.54,
    "high": 145.21,
    "low": 143.96,
    "close": 144.31,
    "body_pct": 0.1839999999999918,
    "upper_shadow_pct": 0.5360000000000127,
    "lower_shadow_pct": 0.2799999999999955,
    "position_in_window": 0.0842,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2025-03-02 02:15:00+00:00",
    "candle_index": 9,
    "open": 144.32,
    "high": 144.71,
    "low": 143.6,
    "close": 143.72,
    "body_pct": 0.5405405405405288,
    "upper_shadow_pct": 0.35135135135136036,
    "lower_shadow_pct": 0.10810810810811088,
    "position_in_window": 0.0947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-03-02 02:45:00+00:00",
    "candle_index": 11,
    "open": 143.29,
    "high": 143.54,
    "low": 142.03,
    "close": 143.03,
    "body_pct": 0.17218543046357118,
    "upper_shadow_pct": 0.16556291390728575,
    "lower_shadow_pct": 0.662251655629143,
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
    "timestamp": "2025-03-02 03:00:00+00:00",
    "candle_index": 12,
    "open": 143.03,
    "high": 144.22,
    "low": 143.02,
    "close": 144.15,
    "body_pct": 0.933333333333346,
    "upper_shadow_pct": 0.0583333333333282,
    "lower_shadow_pct": 0.008333333333325834,
    "position_in_window": 0.1263,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-03-02 03:15:00+00:00",
    "candle_index": 13,
    "open": 144.16,
    "high": 144.65,
    "low": 143.74,
    "close": 144.38,
    "body_pct": 0.24175824175824143,
    "upper_shadow_pct": 0.2967032967033091,
    "lower_shadow_pct": 0.4615384615384495,
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
    "timestamp": "2025-03-02 03:30:00+00:00",
    "candle_index": 14,
    "open": 144.38,
    "high": 144.47,
    "low": 143.56,
    "close": 144.16,
    "body_pct": 0.24175824175824143,
    "upper_shadow_pct": 0.09890109890110302,
    "lower_shadow_pct": 0.6593406593406556,
    "position_in_window": 0.1474,
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
    "timestamp": "2025-03-02 03:45:00+00:00",
    "candle_index": 15,
    "open": 144.16,
    "high": 144.62,
    "low": 143.79,
    "close": 143.85,
    "body_pct": 0.37349397590361155,
    "upper_shadow_pct": 0.5542168674698807,
    "lower_shadow_pct": 0.07228915662650767,
    "position_in_window": 0.1579,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-03-02 04:00:00+00:00",
    "candle_index": 16,
    "open": 143.86,
    "high": 144.3,
    "low": 143.67,
    "close": 143.89,
    "body_pct": 0.04761904761900251,
    "upper_shadow_pct": 0.6507936507936658,
    "lower_shadow_pct": 0.30158730158733166,
    "position_in_window": 0.1684,
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
    "timestamp": "2025-03-02 04:30:00+00:00",
    "candle_index": 18,
    "open": 144.05,
    "high": 144.12,
    "low": 143.15,
    "close": 143.79,
    "body_pct": 0.2680412371134223,
    "upper_shadow_pct": 0.0721649484536013,
    "lower_shadow_pct": 0.6597938144329764,
    "position_in_window": 0.1895,
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
    "timestamp": "2025-03-02 04:45:00+00:00",
    "candle_index": 19,
    "open": 143.79,
    "high": 144.07,
    "low": 143.57,
    "close": 143.72,
    "body_pct": 0.13999999999998636,
    "upper_shadow_pct": 0.5600000000000023,
    "lower_shadow_pct": 0.30000000000001137,
    "position_in_window": 0.2,
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
    "timestamp": "2025-03-02 05:00:00+00:00",
    "candle_index": 20,
    "open": 143.72,
    "high": 143.82,
    "low": 143.26,
    "close": 143.74,
    "body_pct": 0.035714285714303844,
    "upper_shadow_pct": 0.14285714285711384,
    "lower_shadow_pct": 0.8214285714285823,
    "position_in_window": 0.2105,
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
    "timestamp": "2025-03-02 05:30:00+00:00",
    "candle_index": 22,
    "open": 143.37,
    "high": 143.81,
    "low": 142.87,
    "close": 143.07,
    "body_pct": 0.3191489361702256,
    "upper_shadow_pct": 0.46808510638297746,
    "lower_shadow_pct": 0.21276595744679694,
    "position_in_window": 0.2316,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-03-02 05:45:00+00:00",
    "candle_index": 23,
    "open": 143.07,
    "high": 143.15,
    "low": 142.56,
    "close": 142.99,
    "body_pct": 0.1355932203389553,
    "upper_shadow_pct": 0.13559322033900345,
    "lower_shadow_pct": 0.7288135593220413,
    "position_in_window": 0.2421,
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
    "timestamp": "2025-03-02 06:00:00+00:00",
    "candle_index": 24,
    "open": 142.99,
    "high": 143.63,
    "low": 142.93,
    "close": 142.95,
    "body_pct": 0.057142857142887304,
    "upper_shadow_pct": 0.9142857142857096,
    "lower_shadow_pct": 0.02857142857140305,
    "position_in_window": 0.2526,
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
    "timestamp": "2025-03-02 06:15:00+00:00",
    "candle_index": 25,
    "open": 142.95,
    "high": 143.61,
    "low": 142.23,
    "close": 143.6,
    "body_pct": 0.4710144927536192,
    "upper_shadow_pct": 0.0072463768116080825,
    "lower_shadow_pct": 0.5217391304347727,
    "position_in_window": 0.2632,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-03-02 06:30:00+00:00",
    "candle_index": 26,
    "open": 143.59,
    "high": 144.47,
    "low": 143.46,
    "close": 144.43,
    "body_pct": 0.8316831683168425,
    "upper_shadow_pct": 0.03960396039603208,
    "lower_shadow_pct": 0.12871287128712536,
    "position_in_window": 0.2737,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-03-02 06:45:00+00:00",
    "candle_index": 27,
    "open": 144.44,
    "high": 145.17,
    "low": 144.03,
    "close": 144.07,
    "body_pct": 0.3245614035087798,
    "upper_shadow_pct": 0.6403508771929811,
    "lower_shadow_pct": 0.035087719298239055,
    "position_in_window": 0.2842,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-03-02 07:30:00+00:00",
    "candle_index": 30,
    "open": 143.88,
    "high": 144.23,
    "low": 143.65,
    "close": 143.75,
    "body_pct": 0.22413793103448107,
    "upper_shadow_pct": 0.6034482758620757,
    "lower_shadow_pct": 0.1724137931034432,
    "position_in_window": 0.3158,
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
    "timestamp": "2025-03-02 07:45:00+00:00",
    "candle_index": 31,
    "open": 143.75,
    "high": 144.05,
    "low": 143.35,
    "close": 143.79,
    "body_pct": 0.05714285714284438,
    "upper_shadow_pct": 0.37142857142859,
    "lower_shadow_pct": 0.5714285714285656,
    "position_in_window": 0.3263,
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
    "timestamp": "2025-03-02 08:00:00+00:00",
    "candle_index": 32,
    "open": 143.78,
    "high": 143.9,
    "low": 142.63,
    "close": 142.69,
    "body_pct": 0.8582677165354289,
    "upper_shadow_pct": 0.09448818897638077,
    "lower_shadow_pct": 0.047244094488190384,
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
    "timestamp": "2025-03-02 09:00:00+00:00",
    "candle_index": 36,
    "open": 142.87,
    "high": 142.93,
    "low": 142.47,
    "close": 142.81,
    "body_pct": 0.13043478260869834,
    "upper_shadow_pct": 0.13043478260869834,
    "lower_shadow_pct": 0.7391304347826033,
    "position_in_window": 0.3789,
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
    "timestamp": "2025-03-02 09:15:00+00:00",
    "candle_index": 37,
    "open": 142.81,
    "high": 143.11,
    "low": 142.58,
    "close": 142.9,
    "body_pct": 0.16981132075472305,
    "upper_shadow_pct": 0.3962264150943538,
    "lower_shadow_pct": 0.43396226415092315,
    "position_in_window": 0.3895,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2025-03-02 09:30:00+00:00",
    "candle_index": 38,
    "open": 142.9,
    "high": 144.49,
    "low": 142.89,
    "close": 144.34,
    "body_pct": 0.8999999999999858,
    "upper_shadow_pct": 0.09375000000000222,
    "lower_shadow_pct": 0.006250000000011991,
    "position_in_window": 0.4,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-03-02 09:45:00+00:00",
    "candle_index": 39,
    "open": 144.35,
    "high": 144.88,
    "low": 143.83,
    "close": 143.97,
    "body_pct": 0.36190476190476345,
    "upper_shadow_pct": 0.5047619047619141,
    "lower_shadow_pct": 0.1333333333333225,
    "position_in_window": 0.4105,
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
  "doji_count": 11,
  "doji_ratio": 0.11458333333333333,
  "small_body_count": 35,
  "small_body_ratio": 0.3645833333333333,
  "bullish_body_total": 62.920000000000016,
  "bearish_body_total": 27.92999999999998
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
      "previous_timestamp": "2025-03-02 00:00:00+00:00",
      "timestamp": "2025-03-02 00:15:00+00:00",
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
      "previous_timestamp": "2025-03-02 00:00:00+00:00",
      "timestamp": "2025-03-02 00:15:00+00:00",
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
      "previous_timestamp": "2025-03-02 02:45:00+00:00",
      "timestamp": "2025-03-02 03:00:00+00:00",
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
      "previous_timestamp": "2025-03-02 02:45:00+00:00",
      "timestamp": "2025-03-02 03:00:00+00:00",
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
      "previous_timestamp": "2025-03-02 03:15:00+00:00",
      "timestamp": "2025-03-02 03:30:00+00:00",
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
      "previous_timestamp": "2025-03-02 03:15:00+00:00",
      "timestamp": "2025-03-02 03:30:00+00:00",
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
      "previous_timestamp": "2025-03-02 05:00:00+00:00",
      "timestamp": "2025-03-02 05:15:00+00:00",
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
      "previous_timestamp": "2025-03-02 05:00:00+00:00",
      "timestamp": "2025-03-02 05:15:00+00:00",
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
      "previous_timestamp": "2025-03-02 06:00:00+00:00",
      "timestamp": "2025-03-02 06:15:00+00:00",
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
      "previous_timestamp": "2025-03-02 06:00:00+00:00",
      "timestamp": "2025-03-02 06:15:00+00:00",
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
      "previous_timestamp": "2025-03-02 08:30:00+00:00",
      "timestamp": "2025-03-02 08:45:00+00:00",
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
      "previous_timestamp": "2025-03-02 08:30:00+00:00",
      "timestamp": "2025-03-02 08:45:00+00:00",
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
      "previous_timestamp": "2025-03-02 09:00:00+00:00",
      "timestamp": "2025-03-02 09:15:00+00:00",
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
      "previous_timestamp": "2025-03-02 09:00:00+00:00",
      "timestamp": "2025-03-02 09:15:00+00:00",
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
      "previous_timestamp": "2025-03-02 11:30:00+00:00",
      "timestamp": "2025-03-02 11:45:00+00:00",
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
      "previous_timestamp": "2025-03-02 11:30:00+00:00",
      "timestamp": "2025-03-02 11:45:00+00:00",
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
      "previous_timestamp": "2025-03-02 14:15:00+00:00",
      "timestamp": "2025-03-02 14:30:00+00:00",
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
      "previous_timestamp": "2025-03-02 14:15:00+00:00",
      "timestamp": "2025-03-02 14:30:00+00:00",
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
      "previous_timestamp": "2025-03-02 17:30:00+00:00",
      "timestamp": "2025-03-02 17:45:00+00:00",
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
      "previous_timestamp": "2025-03-02 17:30:00+00:00",
      "timestamp": "2025-03-02 17:45:00+00:00",
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
STRONG_BEARISH_CANDLE_BODY, CLOSE_NEAR_LOW, STRONG_BULLISH_CANDLE_BODY, CLOSE_NEAR_HIGH, LONG_UPPER_SHADOW_REJECTION, SMALL_BODY_INDECISION, SPINNING_TOP_INDECISION, SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED, CANDLE_PATTERN_NEEDS_TREND_CONTEXT, LONG_LOWER_SHADOW_REJECTION, HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED, DOJI_INDECISION, BEARISH_ENGULFING_CONTEXT, ENGULFING_WITHOUT_FOLLOW_THROUGH, BULLISH_ENGULFING_CONTEXT, BEARISH_BELT_HOLD_CONTEXT_REQUIRED, BULLISH_BELT_HOLD_CONTEXT_REQUIRED, INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED, REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH, HANGING_MAN_LIKE_CONTEXT_REQUIRED, GRAVESTONE_DOJI_CONTEXT, LONG_LEGGED_DOJI_CONTEXT, RICKSHAW_MAN_DOJI_CONTEXT, DRAGONFLY_DOJI_CONTEXT, TWEEZERS_BOTTOM_CONTEXT_REQUIRED, BEARISH_SEPARATING_LINES_CONTEXT, TWEEZERS_TOP_CONTEXT_REQUIRED, BULLISH_SEPARATING_LINES_CONTEXT, BEARISH_HARAMI_CONTEXT, THREE_ADVANCING_WHITE_SOLDIERS_CONTEXT, THREE_MOUNTAINS_CONTEXT_REQUIRED, THREE_RIVERS_CONTEXT_REQUIRED, SMALL_BODY_CLUSTER, LOW_DIRECTIONAL_PROGRESS, BULLISH_BODY_DOMINANCE

## 2. Altunina trend context
### Swing structure
```json
[
  {
    "index": 1,
    "timestamp": "2025-03-02 00:15:00+00:00",
    "price": 142.96,
    "point_type": "LOW"
  },
  {
    "index": 5,
    "timestamp": "2025-03-02 01:15:00+00:00",
    "price": 146.01,
    "point_type": "HIGH"
  },
  {
    "index": 7,
    "timestamp": "2025-03-02 01:45:00+00:00",
    "price": 143.68,
    "point_type": "LOW"
  },
  {
    "index": 8,
    "timestamp": "2025-03-02 02:00:00+00:00",
    "price": 145.21,
    "point_type": "HIGH"
  },
  {
    "index": 11,
    "timestamp": "2025-03-02 02:45:00+00:00",
    "price": 142.03,
    "point_type": "LOW"
  },
  {
    "index": 13,
    "timestamp": "2025-03-02 03:15:00+00:00",
    "price": 144.65,
    "point_type": "HIGH"
  },
  {
    "index": 14,
    "timestamp": "2025-03-02 03:30:00+00:00",
    "price": 143.56,
    "point_type": "LOW"
  },
  {
    "index": 15,
    "timestamp": "2025-03-02 03:45:00+00:00",
    "price": 144.62,
    "point_type": "HIGH"
  },
  {
    "index": 18,
    "timestamp": "2025-03-02 04:30:00+00:00",
    "price": 143.15,
    "point_type": "LOW"
  },
  {
    "index": 21,
    "timestamp": "2025-03-02 05:15:00+00:00",
    "price": 143.93,
    "point_type": "HIGH"
  },
  {
    "index": 23,
    "timestamp": "2025-03-02 05:45:00+00:00",
    "price": 142.56,
    "point_type": "LOW"
  },
  {
    "index": 24,
    "timestamp": "2025-03-02 06:00:00+00:00",
    "price": 143.63,
    "point_type": "HIGH"
  },
  {
    "index": 25,
    "timestamp": "2025-03-02 06:15:00+00:00",
    "price": 142.23,
    "point_type": "LOW"
  },
  {
    "index": 27,
    "timestamp": "2025-03-02 06:45:00+00:00",
    "price": 145.17,
    "point_type": "HIGH"
  },
  {
    "index": 33,
    "timestamp": "2025-03-02 08:15:00+00:00",
    "price": 142.5,
    "point_type": "LOW"
  },
  {
    "index": 35,
    "timestamp": "2025-03-02 08:45:00+00:00",
    "price": 143.27,
    "point_type": "HIGH"
  },
  {
    "index": 36,
    "timestamp": "2025-03-02 09:00:00+00:00",
    "price": 142.47,
    "point_type": "LOW"
  },
  {
    "index": 39,
    "timestamp": "2025-03-02 09:45:00+00:00",
    "price": 144.88,
    "point_type": "HIGH"
  },
  {
    "index": 41,
    "timestamp": "2025-03-02 10:15:00+00:00",
    "price": 143.36,
    "point_type": "LOW"
  },
  {
    "index": 43,
    "timestamp": "2025-03-02 10:45:00+00:00",
    "price": 144.61,
    "point_type": "HIGH"
  },
  {
    "index": 45,
    "timestamp": "2025-03-02 11:15:00+00:00",
    "price": 143.26,
    "point_type": "LOW"
  },
  {
    "index": 46,
    "timestamp": "2025-03-02 11:30:00+00:00",
    "price": 144.22,
    "point_type": "HIGH"
  },
  {
    "index": 49,
    "timestamp": "2025-03-02 12:15:00+00:00",
    "price": 142.18,
    "point_type": "LOW"
  },
  {
    "index": 51,
    "timestamp": "2025-03-02 12:45:00+00:00",
    "price": 143.34,
    "point_type": "HIGH"
  },
  {
    "index": 57,
    "timestamp": "2025-03-02 14:15:00+00:00",
    "price": 140.22,
    "point_type": "LOW"
  },
  {
    "index": 58,
    "timestamp": "2025-03-02 14:30:00+00:00",
    "price": 141.46,
    "point_type": "HIGH"
  },
  {
    "index": 59,
    "timestamp": "2025-03-02 14:45:00+00:00",
    "price": 140.04,
    "point_type": "LOW"
  },
  {
    "index": 66,
    "timestamp": "2025-03-02 16:30:00+00:00",
    "price": 179.85,
    "point_type": "HIGH"
  },
  {
    "index": 68,
    "timestamp": "2025-03-02 17:00:00+00:00",
    "price": 167.88,
    "point_type": "LOW"
  },
  {
    "index": 69,
    "timestamp": "2025-03-02 17:15:00+00:00",
    "price": 174.79,
    "point_type": "HIGH"
  },
  {
    "index": 74,
    "timestamp": "2025-03-02 18:30:00+00:00",
    "price": 165.32,
    "point_type": "LOW"
  },
  {
    "index": 85,
    "timestamp": "2025-03-02 21:15:00+00:00",
    "price": 177.81,
    "point_type": "HIGH"
  },
  {
    "index": 88,
    "timestamp": "2025-03-02 22:00:00+00:00",
    "price": 174.4,
    "point_type": "LOW"
  },
  {
    "index": 89,
    "timestamp": "2025-03-02 22:15:00+00:00",
    "price": 177.1,
    "point_type": "HIGH"
  },
  {
    "index": 90,
    "timestamp": "2025-03-02 22:30:00+00:00",
    "price": 174.5,
    "point_type": "LOW"
  },
  {
    "index": 93,
    "timestamp": "2025-03-02 23:15:00+00:00",
    "price": 179.32,
    "point_type": "HIGH"
  },
  {
    "index": 94,
    "timestamp": "2025-03-02 23:30:00+00:00",
    "price": 176.0,
    "point_type": "LOW"
  }
]
```
### Higher highs / lower highs
```json
{
  "raw_swing_count": 43,
  "swing_count": 37,
  "leg_count": 36,
  "structure_direction": "SIDEWAYS_STRUCTURE",
  "total_movement": 142.1,
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
    "lower_price": 142.96,
    "upper_price": 143.68,
    "mid_price": 143.40909090909093,
    "touch_count": 11,
    "source_indexes": [
      1,
      7,
      14,
      16,
      18,
      24,
      29,
      35,
      41,
      45,
      51
    ],
    "zone_width": 0.7199999999999989,
    "zone_width_ratio": 0.0050206022187004665,
    "formed_at_index": 51,
    "first_touch_index": 1,
    "last_touch_index": 51,
    "source_point_types": [
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "HIGH",
      "LOW",
      "HIGH",
      "LOW",
      "LOW",
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
    "lower_price": 144.61,
    "upper_price": 144.88,
    "mid_price": 144.69,
    "touch_count": 4,
    "source_indexes": [
      13,
      15,
      39,
      43
    ],
    "zone_width": 0.2699999999999818,
    "zone_width_ratio": 0.001866058469831929,
    "formed_at_index": 43,
    "first_touch_index": 13,
    "last_touch_index": 43,
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
    "positional_zone_type": "SUPPORT"
  },
  "is_detected": true,
  "lower_boundary": 142.96,
  "upper_boundary": 144.88,
  "midline": 143.92000000000002,
  "width": 1.9199999999999875,
  "width_ratio": 0.013340744858254497,
  "touch_count": 15,
  "inside_close_ratio": 0.803921568627451,
  "formed_at_index": 51,
  "first_touch_index": 1,
  "duration_candles": 51,
  "boundary_alternation_count": 8
}
```
### Range high / low
See trading range object above.
### Price position inside range
```json
{
  "swing_count": 43,
  "zone_count": 8,
  "range_detected": true,
  "range_formed_at_index": 51,
  "range_duration_candles": 51,
  "inside_close_ratio": 0.803921568627451,
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
  "breakout_index": 52,
  "boundary_price": 142.96,
  "breakout_close": 142.51,
  "distance_ratio": 0.0031477336317852337,
  "returned_to_range": false,
  "follow_through_count": 5,
  "evidence": [
    {
      "source": "SCHWAGER",
      "code": "SCHWAGER_BEARISH_RANGE_BREAKDOWN_CONTEXT",
      "description": "Closing price moved below the range boundary",
      "contribution": -0.12,
      "metadata": {
        "breakout_index": 52
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
        "distance_ratio": 0.01916620033575832
      }
    }
  ],
  "analysis_start_index": 52,
  "confirmation_method": "CLOSE_COUNT_AND_DISTANCE",
  "confirmation_close_count": 6,
  "extreme_index": 57,
  "extreme_price": 140.22,
  "maximum_distance_ratio": 0.01916620033575832,
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
SCHWAGER_SUPPORT_ZONE_IDENTIFIED, SCHWAGER_SUPPORT_ZONE_HELD, SCHWAGER_ZONE_TOO_WIDE, SCHWAGER_RESISTANCE_ZONE_IDENTIFIED, SCHWAGER_RESISTANCE_ZONE_HELD, SCHWAGER_TRADING_RANGE_DETECTED, SCHWAGER_PRICE_INSIDE_RANGE, SCHWAGER_RANGE_UPPER_BOUNDARY_HELD, SCHWAGER_RANGE_LOWER_BOUNDARY_HELD, SCHWAGER_RANGE_DURATION_CONFIRMED, SCHWAGER_RANGE_BOUNDARY_ALTERNATION_CONFIRMED, SCHWAGER_BEARISH_RANGE_BREAKDOWN_CONTEXT, SCHWAGER_BREAKOUT_REQUIRES_CONFIRMATION, SCHWAGER_BREAKOUT_FOLLOW_THROUGH_CONFIRMED, SCHWAGER_BREAKOUT_CONFIRMED_BY_CLOSE_COUNT, SCHWAGER_BREAKOUT_CONFIRMED_BY_DISTANCE

## 4. BookEvidenceMatrix
### Bullish evidence
Count: 38
### Bearish evidence
Count: 28
### Neutral/range evidence
Count: 309
### Conflict
```json
{
  "agreement_state": "MIXED_WITH_CONFLICT",
  "conflict_level": "MEDIUM",
  "coverage_level": "HIGH",
  "aligned_sources": [],
  "conflicting_sources": [
    "NISON",
    "SCHWAGER"
  ],
  "missing_sources": [],
  "confluence_score": 0.0,
  "conflict_score": 1.0,
  "coverage_score": 1.0,
  "reason_codes": [
    "MATRIX_HIGH_EVIDENCE_COVERAGE",
    "MATRIX_NISON_SCHWAGER_CONFLICT",
    "MATRIX_DIRECTIONAL_CONFLICT_MEDIUM",
    "MATRIX_MIXED_BOOK_CONTEXT",
    "MATRIX_READY_FOR_REGIME_COMPOSER"
  ]
}
```
### Coverage
```json
{
  "active_source_count": 3,
  "total_evidence_count": 375,
  "dominant_direction": "BULLISH",
  "agreement_state": "MIXED_WITH_CONFLICT",
  "conflict_level": "MEDIUM",
  "coverage_level": "HIGH",
  "confluence_score": 0.0,
  "conflict_score": 1.0,
  "coverage_score": 1.0,
  "ready_for_composer": true
}
```
### Matrix conclusion
MIXED_WITH_CONFLICT

## 5. Composer decision
### Raw scores
Not exposed by current trace.
### Clamped scores
```json
{
  "UP": 1.0,
  "DOWN": 1.0,
  "FLAT": 0.6607843137254902,
  "UNKNOWN": 0.25
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
    "score": 0.6607843137254902
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
The engine returned UNKNOWN because the composer status was FALLBACK_UNKNOWN and selected UNKNOWN. The strongest visible candidate scores after clamping were UP=1.000 and DOWN=1.000; fallback reason: COMPOSER_CONSERVATIVE_FALLBACK_UNKNOWN. The reference label is EXPECTED_UP and remains descriptive, not ground truth.
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
