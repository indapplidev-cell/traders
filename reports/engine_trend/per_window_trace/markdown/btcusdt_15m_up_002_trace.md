# btcusdt_15m_up_002 вЂ” Market Evidence Trace

## Window
- Symbol: BTCUSDT
- Interval: 15m
- Period: 2025-03-02T00:00:00+00:00 вЂ” 2025-03-02T23:45:00+00:00
- Reference label: EXPECTED_UP
- Selection reason: ranked deterministic UP OHLC candidate

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
    "timestamp": "2025-03-02 00:00:00+00:00",
    "candle_index": 0,
    "open": 86064.54,
    "high": 86300.0,
    "low": 85967.77,
    "close": 86026.01,
    "body_pct": 0.1159738735213536,
    "upper_shadow_pct": 0.7087258826716711,
    "lower_shadow_pct": 0.1753002438069753,
    "position_in_window": 0.0,
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
    "timestamp": "2025-03-02 00:15:00+00:00",
    "candle_index": 1,
    "open": 86026.0,
    "high": 86098.05,
    "low": 85801.0,
    "close": 85966.88,
    "body_pct": 0.19902373337820153,
    "upper_shadow_pct": 0.24255175896314493,
    "lower_shadow_pct": 0.5584245076586535,
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
    "timestamp": "2025-03-02 00:30:00+00:00",
    "candle_index": 2,
    "open": 85966.88,
    "high": 86286.54,
    "low": 85932.0,
    "close": 86214.0,
    "body_pct": 0.6970158515259204,
    "upper_shadow_pct": 0.2046031477407201,
    "lower_shadow_pct": 0.09838100073335952,
    "position_in_window": 0.0211,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-03-02 00:45:00+00:00",
    "candle_index": 3,
    "open": 86214.0,
    "high": 86318.18,
    "low": 85981.88,
    "close": 86026.62,
    "body_pct": 0.5571810883140385,
    "upper_shadow_pct": 0.30978293190602624,
    "lower_shadow_pct": 0.13303597977993528,
    "position_in_window": 0.0316,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-03-02 01:00:00+00:00",
    "candle_index": 4,
    "open": 86026.62,
    "high": 86334.14,
    "low": 86026.62,
    "close": 86334.13,
    "body_pct": 0.9999674817898193,
    "upper_shadow_pct": 3.2518210180675005e-05,
    "lower_shadow_pct": 0.0,
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
    "open": 86334.13,
    "high": 86377.44,
    "low": 86165.29,
    "close": 86200.0,
    "body_pct": 0.6322413386754614,
    "upper_shadow_pct": 0.20414800848454343,
    "lower_shadow_pct": 0.16361065283999515,
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
    "open": 86200.01,
    "high": 86346.88,
    "low": 85990.0,
    "close": 86200.0,
    "body_pct": 2.8020623163979992e-05,
    "upper_shadow_pct": 0.4115388926249943,
    "lower_shadow_pct": 0.5884330867518417,
    "position_in_window": 0.0632,
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
    "timestamp": "2025-03-02 01:45:00+00:00",
    "candle_index": 7,
    "open": 86200.01,
    "high": 86368.85,
    "low": 86097.12,
    "close": 86354.93,
    "body_pct": 0.5701247561917796,
    "upper_shadow_pct": 0.05122732123803875,
    "lower_shadow_pct": 0.3786479225701816,
    "position_in_window": 0.0737,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-03-02 02:00:00+00:00",
    "candle_index": 8,
    "open": 86354.94,
    "high": 86498.0,
    "low": 86250.0,
    "close": 86258.98,
    "body_pct": 0.3869354838709936,
    "upper_shadow_pct": 0.576854838709668,
    "lower_shadow_pct": 0.03620967741933841,
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
    "timestamp": "2025-03-02 02:15:00+00:00",
    "candle_index": 9,
    "open": 86258.97,
    "high": 86382.62,
    "low": 85950.99,
    "close": 86006.0,
    "body_pct": 0.5860806709450385,
    "upper_shadow_pct": 0.28647220999466444,
    "lower_shadow_pct": 0.12744711906029707,
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
    "open": 85816.54,
    "high": 85899.0,
    "low": 85611.79,
    "close": 85774.01,
    "body_pct": 0.14807980223529085,
    "upper_shadow_pct": 0.2871069948818097,
    "lower_shadow_pct": 0.5648132028828995,
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
    "open": 85774.01,
    "high": 86032.0,
    "low": 85774.01,
    "close": 85984.02,
    "body_pct": 0.8140237993720882,
    "upper_shadow_pct": 0.18597620062791176,
    "lower_shadow_pct": 0.0,
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
    "open": 85984.01,
    "high": 86027.61,
    "low": 85773.59,
    "close": 85946.43,
    "body_pct": 0.14794110699945337,
    "upper_shadow_pct": 0.17164002834424502,
    "lower_shadow_pct": 0.6804188646563016,
    "position_in_window": 0.1368,
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
    "timestamp": "2025-03-02 03:30:00+00:00",
    "candle_index": 14,
    "open": 85946.43,
    "high": 85955.89,
    "low": 85826.28,
    "close": 85949.29,
    "body_pct": 0.022066198595791755,
    "upper_shadow_pct": 0.05092199675955398,
    "lower_shadow_pct": 0.9270118046446543,
    "position_in_window": 0.1474,
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
    "timestamp": "2025-03-02 03:45:00+00:00",
    "candle_index": 15,
    "open": 85949.28,
    "high": 86219.82,
    "low": 85867.92,
    "close": 85873.07,
    "body_pct": 0.2165672065927535,
    "upper_shadow_pct": 0.7687979539641985,
    "lower_shadow_pct": 0.014634839443048034,
    "position_in_window": 0.1579,
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
    "timestamp": "2025-03-02 04:15:00+00:00",
    "candle_index": 17,
    "open": 85766.26,
    "high": 85766.27,
    "low": 85552.99,
    "close": 85704.86,
    "body_pct": 0.2878844711177537,
    "upper_shadow_pct": 4.688672172408703e-05,
    "lower_shadow_pct": 0.7120686421605222,
    "position_in_window": 0.1789,
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
    "timestamp": "2025-03-02 04:30:00+00:00",
    "candle_index": 18,
    "open": 85704.86,
    "high": 85787.64,
    "low": 85531.87,
    "close": 85787.64,
    "body_pct": 0.32365015443561607,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.6763498455643839,
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
    "timestamp": "2025-03-02 04:45:00+00:00",
    "candle_index": 19,
    "open": 85787.64,
    "high": 85857.38,
    "low": 85688.01,
    "close": 85752.8,
    "body_pct": 0.20570348940186853,
    "upper_shadow_pct": 0.4117612328039273,
    "lower_shadow_pct": 0.3825352777942042,
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
    "timestamp": "2025-03-02 05:00:00+00:00",
    "candle_index": 20,
    "open": 85752.8,
    "high": 85940.0,
    "low": 85672.84,
    "close": 85940.0,
    "body_pct": 0.7007036981583868,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.2992963018416131,
    "position_in_window": 0.2105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-03-02 05:15:00+00:00",
    "candle_index": 21,
    "open": 85939.99,
    "high": 85988.02,
    "low": 85849.93,
    "close": 85942.5,
    "body_pct": 0.018176551524328774,
    "upper_shadow_pct": 0.3296400897965126,
    "lower_shadow_pct": 0.6521833586791586,
    "position_in_window": 0.2211,
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
    "timestamp": "2025-03-02 05:30:00+00:00",
    "candle_index": 22,
    "open": 85942.5,
    "high": 86048.61,
    "low": 85883.34,
    "close": 85914.56,
    "body_pct": 0.16905669510498966,
    "upper_shadow_pct": 0.6420402976946691,
    "lower_shadow_pct": 0.18890300720034123,
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
    "timestamp": "2025-03-02 05:45:00+00:00",
    "candle_index": 23,
    "open": 85914.56,
    "high": 85969.82,
    "low": 85857.02,
    "close": 85957.51,
    "body_pct": 0.3807624113474821,
    "upper_shadow_pct": 0.10913120567386442,
    "lower_shadow_pct": 0.5101063829786535,
    "position_in_window": 0.2421,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-03-02 06:00:00+00:00",
    "candle_index": 24,
    "open": 85957.51,
    "high": 86169.09,
    "low": 85957.5,
    "close": 86005.29,
    "body_pct": 0.22581407438914705,
    "upper_shadow_pct": 0.774138664398155,
    "lower_shadow_pct": 4.726121269796056e-05,
    "position_in_window": 0.2526,
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
    "timestamp": "2025-03-02 06:15:00+00:00",
    "candle_index": 25,
    "open": 86005.29,
    "high": 86369.48,
    "low": 85923.58,
    "close": 86369.47,
    "body_pct": 0.8167302085669709,
    "upper_shadow_pct": 2.2426553027049656e-05,
    "lower_shadow_pct": 0.18324736488000207,
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
    "timestamp": "2025-03-02 06:30:00+00:00",
    "candle_index": 26,
    "open": 86369.48,
    "high": 86374.91,
    "low": 86230.22,
    "close": 86350.0,
    "body_pct": 0.1346326629345194,
    "upper_shadow_pct": 0.037528509226674125,
    "lower_shadow_pct": 0.8278388278388065,
    "position_in_window": 0.2737,
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
    "timestamp": "2025-03-02 06:45:00+00:00",
    "candle_index": 27,
    "open": 86349.99,
    "high": 86589.97,
    "low": 86250.82,
    "close": 86277.65,
    "body_pct": 0.21329795075928734,
    "upper_shadow_pct": 0.707592510688486,
    "lower_shadow_pct": 0.0791095385522266,
    "position_in_window": 0.2842,
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
    "timestamp": "2025-03-02 07:00:00+00:00",
    "candle_index": 28,
    "open": 86277.66,
    "high": 86350.0,
    "low": 86135.32,
    "close": 86172.68,
    "body_pct": 0.48900689398180497,
    "upper_shadow_pct": 0.3369666480342783,
    "lower_shadow_pct": 0.17402645798391675,
    "position_in_window": 0.2947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-03-02 07:15:00+00:00",
    "candle_index": 29,
    "open": 86172.69,
    "high": 86250.0,
    "low": 86075.09,
    "close": 86244.12,
    "body_pct": 0.4083814533188016,
    "upper_shadow_pct": 0.03361728889145583,
    "lower_shadow_pct": 0.5580012577897425,
    "position_in_window": 0.3053,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-03-02 08:00:00+00:00",
    "candle_index": 32,
    "open": 86232.42,
    "high": 86263.23,
    "low": 85750.0,
    "close": 85766.0,
    "body_pct": 0.9087933285271749,
    "upper_shadow_pct": 0.060031564795506726,
    "lower_shadow_pct": 0.031175106677318407,
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
    "timestamp": "2025-03-02 08:15:00+00:00",
    "candle_index": 33,
    "open": 85766.01,
    "high": 85886.98,
    "low": 85721.08,
    "close": 85750.01,
    "body_pct": 0.0964436407474416,
    "upper_shadow_pct": 0.7291742013261326,
    "lower_shadow_pct": 0.17438215792642575,
    "position_in_window": 0.3474,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "CLOSE_NEAR_LOW",
      "DOJI_INDECISION"
    ]
  }
]
```
### Doji / spinning top / small body cluster
```json
{
  "doji_count": 8,
  "doji_ratio": 0.08333333333333333,
  "small_body_count": 35,
  "small_body_ratio": 0.3645833333333333,
  "bullish_body_total": 15872.400000000009,
  "bearish_body_total": 7667.009999999995
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
      "previous_timestamp": "2025-03-02 00:15:00+00:00",
      "timestamp": "2025-03-02 00:30:00+00:00",
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
      "previous_timestamp": "2025-03-02 00:15:00+00:00",
      "timestamp": "2025-03-02 00:30:00+00:00",
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
      "previous_timestamp": "2025-03-02 00:45:00+00:00",
      "timestamp": "2025-03-02 01:00:00+00:00",
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
      "previous_timestamp": "2025-03-02 00:45:00+00:00",
      "timestamp": "2025-03-02 01:00:00+00:00",
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
    "code": "BULLISH_ENGULFING_CONTEXT",
    "description": "Bullish body engulfs the preceding bearish body",
    "contribution": 0.1,
    "metadata": {
      "previous_timestamp": "2025-03-02 04:15:00+00:00",
      "timestamp": "2025-03-02 04:30:00+00:00",
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
      "previous_timestamp": "2025-03-02 04:15:00+00:00",
      "timestamp": "2025-03-02 04:30:00+00:00",
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
      "previous_timestamp": "2025-03-02 04:45:00+00:00",
      "timestamp": "2025-03-02 05:00:00+00:00",
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
      "previous_timestamp": "2025-03-02 04:45:00+00:00",
      "timestamp": "2025-03-02 05:00:00+00:00",
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
      "previous_timestamp": "2025-03-02 05:15:00+00:00",
      "timestamp": "2025-03-02 05:30:00+00:00",
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
      "previous_timestamp": "2025-03-02 05:15:00+00:00",
      "timestamp": "2025-03-02 05:30:00+00:00",
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
      "previous_timestamp": "2025-03-02 05:30:00+00:00",
      "timestamp": "2025-03-02 05:45:00+00:00",
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
      "previous_timestamp": "2025-03-02 05:30:00+00:00",
      "timestamp": "2025-03-02 05:45:00+00:00",
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
      "previous_timestamp": "2025-03-02 07:30:00+00:00",
      "timestamp": "2025-03-02 07:45:00+00:00",
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
      "previous_timestamp": "2025-03-02 07:30:00+00:00",
      "timestamp": "2025-03-02 07:45:00+00:00",
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
      "previous_timestamp": "2025-03-02 08:15:00+00:00",
      "timestamp": "2025-03-02 08:30:00+00:00",
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
      "previous_timestamp": "2025-03-02 08:15:00+00:00",
      "timestamp": "2025-03-02 08:30:00+00:00",
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
      "previous_timestamp": "2025-03-02 13:45:00+00:00",
      "timestamp": "2025-03-02 14:00:00+00:00",
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
      "previous_timestamp": "2025-03-02 13:45:00+00:00",
      "timestamp": "2025-03-02 14:00:00+00:00",
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
LONG_UPPER_SHADOW_REJECTION, SMALL_BODY_INDECISION, CLOSE_NEAR_LOW, SPINNING_TOP_INDECISION, LONG_LOWER_SHADOW_REJECTION, CLOSE_NEAR_HIGH, STRONG_BULLISH_CANDLE_BODY, DOJI_INDECISION, HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED, CANDLE_PATTERN_NEEDS_TREND_CONTEXT, SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED, STRONG_BEARISH_CANDLE_BODY, BULLISH_ENGULFING_CONTEXT, ENGULFING_WITHOUT_FOLLOW_THROUGH, BEARISH_ENGULFING_CONTEXT, BULLISH_BELT_HOLD_CONTEXT_REQUIRED, LONG_LEGGED_DOJI_CONTEXT, RICKSHAW_MAN_DOJI_CONTEXT, HANGING_MAN_LIKE_CONTEXT_REQUIRED, REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH, DRAGONFLY_DOJI_CONTEXT, INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED, BEARISH_BELT_HOLD_CONTEXT_REQUIRED, TWEEZERS_TOP_CONTEXT_REQUIRED, BULLISH_HARAMI_CONTEXT, HARAMI_CROSS_CONTEXT, BULLISH_SEPARATING_LINES_CONTEXT, BEARISH_HARAMI_CONTEXT, TWEEZERS_BOTTOM_CONTEXT_REQUIRED, BEARISH_SEPARATING_LINES_CONTEXT, DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT, DOJI_TOP_CONTEXT_REQUIRED, THREE_ADVANCING_WHITE_SOLDIERS_CONTEXT, THREE_MOUNTAINS_CONTEXT_REQUIRED, THREE_RIVERS_CONTEXT_REQUIRED, SMALL_BODY_CLUSTER, LOW_DIRECTIONAL_PROGRESS, BULLISH_BODY_DOMINANCE

## 2. Altunina trend context
### Swing structure
```json
[
  {
    "index": 1,
    "timestamp": "2025-03-02 00:15:00+00:00",
    "price": 85801.0,
    "point_type": "LOW"
  },
  {
    "index": 5,
    "timestamp": "2025-03-02 01:15:00+00:00",
    "price": 86377.44,
    "point_type": "HIGH"
  },
  {
    "index": 6,
    "timestamp": "2025-03-02 01:30:00+00:00",
    "price": 85990.0,
    "point_type": "LOW"
  },
  {
    "index": 8,
    "timestamp": "2025-03-02 02:00:00+00:00",
    "price": 86498.0,
    "point_type": "HIGH"
  },
  {
    "index": 11,
    "timestamp": "2025-03-02 02:45:00+00:00",
    "price": 85611.79,
    "point_type": "LOW"
  },
  {
    "index": 12,
    "timestamp": "2025-03-02 03:00:00+00:00",
    "price": 86032.0,
    "point_type": "HIGH"
  },
  {
    "index": 13,
    "timestamp": "2025-03-02 03:15:00+00:00",
    "price": 85773.59,
    "point_type": "LOW"
  },
  {
    "index": 15,
    "timestamp": "2025-03-02 03:45:00+00:00",
    "price": 86219.82,
    "point_type": "HIGH"
  },
  {
    "index": 18,
    "timestamp": "2025-03-02 04:30:00+00:00",
    "price": 85531.87,
    "point_type": "LOW"
  },
  {
    "index": 22,
    "timestamp": "2025-03-02 05:30:00+00:00",
    "price": 86048.61,
    "point_type": "HIGH"
  },
  {
    "index": 23,
    "timestamp": "2025-03-02 05:45:00+00:00",
    "price": 85857.02,
    "point_type": "LOW"
  },
  {
    "index": 27,
    "timestamp": "2025-03-02 06:45:00+00:00",
    "price": 86589.97,
    "point_type": "HIGH"
  },
  {
    "index": 29,
    "timestamp": "2025-03-02 07:15:00+00:00",
    "price": 86075.09,
    "point_type": "LOW"
  },
  {
    "index": 30,
    "timestamp": "2025-03-02 07:30:00+00:00",
    "price": 86350.0,
    "point_type": "HIGH"
  },
  {
    "index": 33,
    "timestamp": "2025-03-02 08:15:00+00:00",
    "price": 85721.08,
    "point_type": "LOW"
  },
  {
    "index": 35,
    "timestamp": "2025-03-02 08:45:00+00:00",
    "price": 85947.84,
    "point_type": "HIGH"
  },
  {
    "index": 36,
    "timestamp": "2025-03-02 09:00:00+00:00",
    "price": 85633.13,
    "point_type": "LOW"
  },
  {
    "index": 39,
    "timestamp": "2025-03-02 09:45:00+00:00",
    "price": 86120.0,
    "point_type": "HIGH"
  },
  {
    "index": 41,
    "timestamp": "2025-03-02 10:15:00+00:00",
    "price": 85792.45,
    "point_type": "LOW"
  },
  {
    "index": 46,
    "timestamp": "2025-03-02 11:30:00+00:00",
    "price": 86220.22,
    "point_type": "HIGH"
  },
  {
    "index": 49,
    "timestamp": "2025-03-02 12:15:00+00:00",
    "price": 85750.0,
    "point_type": "LOW"
  },
  {
    "index": 51,
    "timestamp": "2025-03-02 12:45:00+00:00",
    "price": 86024.59,
    "point_type": "HIGH"
  },
  {
    "index": 55,
    "timestamp": "2025-03-02 13:45:00+00:00",
    "price": 85477.81,
    "point_type": "LOW"
  },
  {
    "index": 56,
    "timestamp": "2025-03-02 14:00:00+00:00",
    "price": 85911.84,
    "point_type": "HIGH"
  },
  {
    "index": 57,
    "timestamp": "2025-03-02 14:15:00+00:00",
    "price": 85075.47,
    "point_type": "LOW"
  },
  {
    "index": 58,
    "timestamp": "2025-03-02 14:30:00+00:00",
    "price": 85633.75,
    "point_type": "HIGH"
  },
  {
    "index": 59,
    "timestamp": "2025-03-02 14:45:00+00:00",
    "price": 85050.6,
    "point_type": "LOW"
  },
  {
    "index": 67,
    "timestamp": "2025-03-02 16:45:00+00:00",
    "price": 91959.99,
    "point_type": "HIGH"
  },
  {
    "index": 68,
    "timestamp": "2025-03-02 17:00:00+00:00",
    "price": 90636.0,
    "point_type": "LOW"
  },
  {
    "index": 71,
    "timestamp": "2025-03-02 17:45:00+00:00",
    "price": 95000.0,
    "point_type": "HIGH"
  },
  {
    "index": 74,
    "timestamp": "2025-03-02 18:30:00+00:00",
    "price": 92364.39,
    "point_type": "LOW"
  },
  {
    "index": 83,
    "timestamp": "2025-03-02 20:45:00+00:00",
    "price": 94446.27,
    "point_type": "HIGH"
  },
  {
    "index": 86,
    "timestamp": "2025-03-02 21:30:00+00:00",
    "price": 93670.72,
    "point_type": "LOW"
  },
  {
    "index": 88,
    "timestamp": "2025-03-02 22:00:00+00:00",
    "price": 94479.21,
    "point_type": "HIGH"
  },
  {
    "index": 90,
    "timestamp": "2025-03-02 22:30:00+00:00",
    "price": 94042.02,
    "point_type": "LOW"
  },
  {
    "index": 92,
    "timestamp": "2025-03-02 23:00:00+00:00",
    "price": 94883.51,
    "point_type": "HIGH"
  },
  {
    "index": 94,
    "timestamp": "2025-03-02 23:30:00+00:00",
    "price": 93800.0,
    "point_type": "LOW"
  }
]
```
### Higher highs / lower highs
```json
{
  "raw_swing_count": 42,
  "swing_count": 37,
  "leg_count": 36,
  "structure_direction": "SIDEWAYS_STRUCTURE",
  "total_movement": 33779.06000000003,
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
    "lower_price": 85477.81,
    "upper_price": 85990.0,
    "mid_price": 85751.849375,
    "touch_count": 16,
    "source_indexes": [
      1,
      6,
      11,
      13,
      18,
      20,
      23,
      25,
      33,
      35,
      36,
      41,
      49,
      55,
      56,
      58
    ],
    "zone_width": 512.1900000000023,
    "zone_width_ratio": 0.005972932405925762,
    "formed_at_index": 58,
    "first_touch_index": 1,
    "last_touch_index": 58,
    "source_point_types": [
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "HIGH",
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
    "lower_price": 86024.59,
    "upper_price": 86377.44,
    "mid_price": 86163.08555555556,
    "touch_count": 9,
    "source_indexes": [
      5,
      12,
      15,
      22,
      29,
      30,
      39,
      46,
      51
    ],
    "zone_width": 352.8500000000058,
    "zone_width_ratio": 0.004095141181689669,
    "formed_at_index": 51,
    "first_touch_index": 5,
    "last_touch_index": 51,
    "source_point_types": [
      "HIGH",
      "HIGH",
      "HIGH",
      "HIGH",
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
    "positional_zone_type": "SUPPORT"
  },
  "is_detected": true,
  "lower_boundary": 85477.81,
  "upper_boundary": 86377.44,
  "midline": 85927.625,
  "width": 899.6300000000047,
  "width_ratio": 0.010469624873258218,
  "touch_count": 25,
  "inside_close_ratio": 0.9655172413793104,
  "formed_at_index": 58,
  "first_touch_index": 1,
  "duration_candles": 58,
  "boundary_alternation_count": 16
}
```
### Range high / low
See trading range object above.
### Price position inside range
```json
{
  "swing_count": 42,
  "zone_count": 7,
  "range_detected": true,
  "range_formed_at_index": 58,
  "range_duration_candles": 58,
  "inside_close_ratio": 0.9655172413793104,
  "breakout_direction": "DOWNWARD",
  "breakout_status": "NO_FOLLOW_THROUGH",
  "polarity_status": "NONE"
}
```
### Breakout / breakdown attempts
```json
{
  "direction": "DOWNWARD",
  "status": "NO_FOLLOW_THROUGH",
  "breakout_index": 59,
  "boundary_price": 85477.81,
  "breakout_close": 85107.45,
  "distance_ratio": 0.004332820412689569,
  "returned_to_range": false,
  "follow_through_count": 1,
  "evidence": [
    {
      "source": "SCHWAGER",
      "code": "SCHWAGER_BEARISH_RANGE_BREAKDOWN_CONTEXT",
      "description": "Closing price moved below the range boundary",
      "contribution": -0.12,
      "metadata": {
        "breakout_index": 59
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
      "code": "SCHWAGER_BREAKOUT_NO_FOLLOW_THROUGH",
      "description": "Boundary movement lacks follow-through",
      "contribution": 0.0,
      "metadata": {
        "count": 1
      }
    }
  ],
  "analysis_start_index": 59,
  "confirmation_method": "NONE",
  "confirmation_close_count": 2,
  "extreme_index": 59,
  "extreme_price": 85050.6,
  "maximum_distance_ratio": 0.004997905304312217,
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
SCHWAGER_SUPPORT_ZONE_IDENTIFIED, SCHWAGER_SUPPORT_ZONE_HELD, SCHWAGER_ZONE_TOO_WIDE, SCHWAGER_RESISTANCE_ZONE_IDENTIFIED, SCHWAGER_RESISTANCE_ZONE_HELD, SCHWAGER_TRADING_RANGE_DETECTED, SCHWAGER_PRICE_INSIDE_RANGE, SCHWAGER_RANGE_UPPER_BOUNDARY_HELD, SCHWAGER_RANGE_LOWER_BOUNDARY_HELD, SCHWAGER_RANGE_DURATION_CONFIRMED, SCHWAGER_RANGE_BOUNDARY_ALTERNATION_CONFIRMED, SCHWAGER_BEARISH_RANGE_BREAKDOWN_CONTEXT, SCHWAGER_BREAKOUT_REQUIRES_CONFIRMATION, SCHWAGER_BREAKOUT_NO_FOLLOW_THROUGH

## 4. BookEvidenceMatrix
### Bullish evidence
Count: 42
### Bearish evidence
Count: 25
### Neutral/range evidence
Count: 319
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
  "total_evidence_count": 386,
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
  "FLAT": 0.8431034482758621,
  "UNKNOWN": 0.3
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
    "score": 0.8431034482758621
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
