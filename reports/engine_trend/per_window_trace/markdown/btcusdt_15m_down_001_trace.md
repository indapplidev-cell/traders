# btcusdt_15m_down_001 вЂ” Market Evidence Trace

## Window
- Symbol: BTCUSDT
- Interval: 15m
- Period: 2026-02-05T00:00:00+00:00 вЂ” 2026-02-05T23:45:00+00:00
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
    "timestamp": "2026-02-05 00:00:00+00:00",
    "candle_index": 0,
    "open": 73165.84,
    "high": 73217.88,
    "low": 72762.99,
    "close": 72778.45,
    "body_pct": 0.8516124777418714,
    "upper_shadow_pct": 0.1144012838268773,
    "lower_shadow_pct": 0.033986238431251224,
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
    "timestamp": "2026-02-05 00:15:00+00:00",
    "candle_index": 1,
    "open": 72778.44,
    "high": 73325.6,
    "low": 72754.21,
    "close": 73252.79,
    "body_pct": 0.8301685363761909,
    "upper_shadow_pct": 0.1274261012618567,
    "lower_shadow_pct": 0.042405362361952345,
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
    "timestamp": "2026-02-05 00:30:00+00:00",
    "candle_index": 2,
    "open": 73252.78,
    "high": 73252.78,
    "low": 72899.47,
    "close": 73103.03,
    "body_pct": 0.42384874472842826,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.5761512552715717,
    "position_in_window": 0.0211,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2026-02-05 00:45:00+00:00",
    "candle_index": 3,
    "open": 73103.03,
    "high": 73170.0,
    "low": 72819.9,
    "close": 72868.02,
    "body_pct": 0.6712653527563291,
    "upper_shadow_pct": 0.19128820337046573,
    "lower_shadow_pct": 0.13744644387320507,
    "position_in_window": 0.0316,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-02-05 01:15:00+00:00",
    "candle_index": 5,
    "open": 73170.72,
    "high": 73170.72,
    "low": 71995.09,
    "close": 72967.15,
    "body_pct": 0.17315822154930222,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.8268417784506977,
    "position_in_window": 0.0526,
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
    "timestamp": "2026-02-05 01:45:00+00:00",
    "candle_index": 7,
    "open": 72635.06,
    "high": 72797.64,
    "low": 72410.85,
    "close": 72421.26,
    "body_pct": 0.5527547247860763,
    "upper_shadow_pct": 0.4203314460043032,
    "lower_shadow_pct": 0.0269138292096205,
    "position_in_window": 0.0737,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-02-05 02:00:00+00:00",
    "candle_index": 8,
    "open": 72421.26,
    "high": 72563.95,
    "low": 72028.75,
    "close": 72044.96,
    "body_pct": 0.7031016442451241,
    "upper_shadow_pct": 0.26661061285501325,
    "lower_shadow_pct": 0.030287742899862653,
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
    "open": 72044.96,
    "high": 72380.38,
    "low": 71680.0,
    "close": 72325.59,
    "body_pct": 0.40068248665008743,
    "upper_shadow_pct": 0.07822896142095404,
    "lower_shadow_pct": 0.5210885519289585,
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
    "open": 72588.0,
    "high": 72618.77,
    "low": 71305.55,
    "close": 71454.44,
    "body_pct": 0.8631912398531828,
    "upper_shadow_pct": 0.023430955970822898,
    "lower_shadow_pct": 0.11337780417599434,
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
    "open": 71454.44,
    "high": 71884.47,
    "low": 71345.95,
    "close": 71525.52,
    "body_pct": 0.13199138379261904,
    "upper_shadow_pct": 0.6665490603877189,
    "lower_shadow_pct": 0.20145955581966207,
    "position_in_window": 0.1263,
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
    "timestamp": "2026-02-05 03:15:00+00:00",
    "candle_index": 13,
    "open": 71525.52,
    "high": 71768.0,
    "low": 71280.0,
    "close": 71515.6,
    "body_pct": 0.02032786885245544,
    "upper_shadow_pct": 0.49688524590163097,
    "lower_shadow_pct": 0.48278688524591357,
    "position_in_window": 0.1368,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "DOJI_INDECISION"
    ]
  },
  {
    "timestamp": "2026-02-05 03:30:00+00:00",
    "candle_index": 14,
    "open": 71515.6,
    "high": 71611.58,
    "low": 71288.02,
    "close": 71446.0,
    "body_pct": 0.21510693534431427,
    "upper_shadow_pct": 0.29663740882679135,
    "lower_shadow_pct": 0.48825565582889435,
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
    "open": 71445.99,
    "high": 71520.97,
    "low": 71152.78,
    "close": 71223.25,
    "body_pct": 0.6049593959640507,
    "upper_shadow_pct": 0.20364485727476425,
    "lower_shadow_pct": 0.19139574676118504,
    "position_in_window": 0.1579,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-02-05 04:15:00+00:00",
    "candle_index": 17,
    "open": 70950.64,
    "high": 71353.83,
    "low": 70701.0,
    "close": 71028.32,
    "body_pct": 0.11898962976580023,
    "upper_shadow_pct": 0.4986137279230334,
    "lower_shadow_pct": 0.3823966423111664,
    "position_in_window": 0.1789,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2026-02-05 04:30:00+00:00",
    "candle_index": 18,
    "open": 71028.32,
    "high": 71400.0,
    "low": 70873.97,
    "close": 71354.81,
    "body_pct": 0.6206680227363295,
    "upper_shadow_pct": 0.08590764785278868,
    "lower_shadow_pct": 0.2934243294108818,
    "position_in_window": 0.1895,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-02-05 05:00:00+00:00",
    "candle_index": 20,
    "open": 70888.09,
    "high": 71080.0,
    "low": 70672.0,
    "close": 70843.37,
    "body_pct": 0.10960784313725776,
    "upper_shadow_pct": 0.4703676470588321,
    "lower_shadow_pct": 0.42002450980391015,
    "position_in_window": 0.2105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2026-02-05 05:30:00+00:00",
    "candle_index": 22,
    "open": 70433.11,
    "high": 71150.16,
    "low": 70339.9,
    "close": 71019.55,
    "body_pct": 0.7237676795102752,
    "upper_shadow_pct": 0.16119517192012328,
    "lower_shadow_pct": 0.11503714856960152,
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
    "timestamp": "2026-02-05 06:00:00+00:00",
    "candle_index": 24,
    "open": 70732.73,
    "high": 70918.05,
    "low": 70473.59,
    "close": 70665.79,
    "body_pct": 0.15060972865949998,
    "upper_shadow_pct": 0.41695540656078006,
    "lower_shadow_pct": 0.43243486477971993,
    "position_in_window": 0.2526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2026-02-05 06:15:00+00:00",
    "candle_index": 25,
    "open": 70665.79,
    "high": 70839.59,
    "low": 70434.05,
    "close": 70527.13,
    "body_pct": 0.34191448439116023,
    "upper_shadow_pct": 0.4285643832914279,
    "lower_shadow_pct": 0.2295211323174119,
    "position_in_window": 0.2632,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-02-05 06:30:00+00:00",
    "candle_index": 26,
    "open": 70527.13,
    "high": 70984.62,
    "low": 70525.56,
    "close": 70884.57,
    "body_pct": 0.778634601141472,
    "upper_shadow_pct": 0.21794536661871838,
    "lower_shadow_pct": 0.0034200322398095953,
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
    "timestamp": "2026-02-05 06:45:00+00:00",
    "candle_index": 27,
    "open": 70885.79,
    "high": 70984.4,
    "low": 70580.65,
    "close": 70951.51,
    "body_pct": 0.1627739938080524,
    "upper_shadow_pct": 0.08146130030959609,
    "lower_shadow_pct": 0.7557647058823515,
    "position_in_window": 0.2842,
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
    "timestamp": "2026-02-05 07:00:00+00:00",
    "candle_index": 28,
    "open": 70951.51,
    "high": 71622.82,
    "low": 70900.0,
    "close": 71098.99,
    "body_pct": 0.2040341993857517,
    "upper_shadow_pct": 0.7247032456213119,
    "lower_shadow_pct": 0.07126255499293636,
    "position_in_window": 0.2947,
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
    "timestamp": "2026-02-05 07:45:00+00:00",
    "candle_index": 31,
    "open": 71161.08,
    "high": 71214.23,
    "low": 70644.73,
    "close": 70756.85,
    "body_pct": 0.7097980684811166,
    "upper_shadow_pct": 0.09332748024581945,
    "lower_shadow_pct": 0.1968744512730639,
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
    "timestamp": "2026-02-05 08:00:00+00:00",
    "candle_index": 32,
    "open": 70756.86,
    "high": 71105.93,
    "low": 70683.58,
    "close": 71079.99,
    "body_pct": 0.7650763584704897,
    "upper_shadow_pct": 0.06141825500174811,
    "lower_shadow_pct": 0.17350538652776218,
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
    "timestamp": "2026-02-05 08:30:00+00:00",
    "candle_index": 34,
    "open": 71344.76,
    "high": 71550.0,
    "low": 71237.3,
    "close": 71252.73,
    "body_pct": 0.2943076431084096,
    "upper_shadow_pct": 0.656347937320138,
    "lower_shadow_pct": 0.04934441957145238,
    "position_in_window": 0.3579,
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
    "timestamp": "2026-02-05 08:45:00+00:00",
    "candle_index": 35,
    "open": 71252.73,
    "high": 71335.17,
    "low": 71045.0,
    "close": 71054.99,
    "body_pct": 0.6814625908949646,
    "upper_shadow_pct": 0.28410931522901345,
    "lower_shadow_pct": 0.034428093876021984,
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
    "open": 71054.99,
    "high": 71864.85,
    "low": 71049.35,
    "close": 71823.45,
    "body_pct": 0.9423175965665136,
    "upper_shadow_pct": 0.05076640098100396,
    "lower_shadow_pct": 0.006916002452482426,
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
    "open": 71823.44,
    "high": 71978.58,
    "low": 71624.76,
    "close": 71736.95,
    "body_pct": 0.2444463286416922,
    "upper_shadow_pct": 0.43847153920071325,
    "lower_shadow_pct": 0.31708213215759457,
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
    "timestamp": "2026-02-05 09:30:00+00:00",
    "candle_index": 38,
    "open": 71736.94,
    "high": 71811.01,
    "low": 71463.54,
    "close": 71483.39,
    "body_pct": 0.7297032837367314,
    "upper_shadow_pct": 0.2131694822574386,
    "lower_shadow_pct": 0.05712723400583001,
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
    "timestamp": "2026-02-05 09:45:00+00:00",
    "candle_index": 39,
    "open": 71483.39,
    "high": 71728.48,
    "low": 71439.72,
    "close": 71550.0,
    "body_pct": 0.2306759939049792,
    "upper_shadow_pct": 0.6180911483584955,
    "lower_shadow_pct": 0.1512328577365253,
    "position_in_window": 0.4105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  }
]
```
### Doji / spinning top / small body cluster
```json
{
  "doji_count": 6,
  "doji_ratio": 0.0625,
  "small_body_count": 30,
  "small_body_ratio": 0.3125,
  "bullish_body_total": 12147.0,
  "bearish_body_total": 22404.739999999976
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
    "code": "BULLISH_ENGULFING_CONTEXT",
    "description": "Bullish body engulfs the preceding bearish body",
    "contribution": 0.1,
    "metadata": {
      "previous_timestamp": "2026-02-05 00:45:00+00:00",
      "timestamp": "2026-02-05 01:00:00+00:00",
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
      "previous_timestamp": "2026-02-05 00:45:00+00:00",
      "timestamp": "2026-02-05 01:00:00+00:00",
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
    "code": "BEARISH_ENGULFING_CONTEXT",
    "description": "Bearish body engulfs the preceding bullish body",
    "contribution": -0.1,
    "metadata": {
      "previous_timestamp": "2026-02-05 04:30:00+00:00",
      "timestamp": "2026-02-05 04:45:00+00:00",
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
      "previous_timestamp": "2026-02-05 04:30:00+00:00",
      "timestamp": "2026-02-05 04:45:00+00:00",
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
      "previous_timestamp": "2026-02-05 05:15:00+00:00",
      "timestamp": "2026-02-05 05:30:00+00:00",
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
      "previous_timestamp": "2026-02-05 05:15:00+00:00",
      "timestamp": "2026-02-05 05:30:00+00:00",
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
      "previous_timestamp": "2026-02-05 06:15:00+00:00",
      "timestamp": "2026-02-05 06:30:00+00:00",
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
      "previous_timestamp": "2026-02-05 06:15:00+00:00",
      "timestamp": "2026-02-05 06:30:00+00:00",
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
    "code": "BULLISH_ENGULFING_CONTEXT",
    "description": "Bullish body engulfs the preceding bearish body",
    "contribution": 0.1,
    "metadata": {
      "previous_timestamp": "2026-02-05 10:00:00+00:00",
      "timestamp": "2026-02-05 10:15:00+00:00",
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
      "previous_timestamp": "2026-02-05 10:00:00+00:00",
      "timestamp": "2026-02-05 10:15:00+00:00",
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
      "previous_timestamp": "2026-02-05 10:15:00+00:00",
      "timestamp": "2026-02-05 10:30:00+00:00",
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
      "previous_timestamp": "2026-02-05 10:15:00+00:00",
      "timestamp": "2026-02-05 10:30:00+00:00",
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
  }
]
```
### Morning/evening star candidates
```json
[]
```
### Candle context conclusion
STRONG_BEARISH_CANDLE_BODY, CLOSE_NEAR_LOW, STRONG_BULLISH_CANDLE_BODY, CLOSE_NEAR_HIGH, LONG_LOWER_SHADOW_REJECTION, SMALL_BODY_INDECISION, SPINNING_TOP_INDECISION, HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED, CANDLE_PATTERN_NEEDS_TREND_CONTEXT, LONG_UPPER_SHADOW_REJECTION, DOJI_INDECISION, SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED, BULLISH_ENGULFING_CONTEXT, ENGULFING_WITHOUT_FOLLOW_THROUGH, BEARISH_ENGULFING_CONTEXT, BULLISH_BELT_HOLD_CONTEXT_REQUIRED, HANGING_MAN_LIKE_CONTEXT_REQUIRED, REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH, BEARISH_BELT_HOLD_CONTEXT_REQUIRED, LONG_LEGGED_DOJI_CONTEXT, RICKSHAW_MAN_DOJI_CONTEXT, INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED, GRAVESTONE_DOJI_CONTEXT, TWEEZERS_BOTTOM_CONTEXT_REQUIRED, TWEEZERS_TOP_CONTEXT_REQUIRED, BULLISH_HARAMI_CONTEXT, BEARISH_HARAMI_CONTEXT, DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT, DOJI_TOP_CONTEXT_REQUIRED, HARAMI_CROSS_CONTEXT, BEARISH_BODY_DOMINANCE

## 2. Altunina trend context
### Swing structure
```json
[
  {
    "index": 1,
    "timestamp": "2026-02-05 00:15:00+00:00",
    "price": 72754.21,
    "point_type": "LOW"
  },
  {
    "index": 4,
    "timestamp": "2026-02-05 01:00:00+00:00",
    "price": 73341.18,
    "point_type": "HIGH"
  },
  {
    "index": 5,
    "timestamp": "2026-02-05 01:15:00+00:00",
    "price": 71995.09,
    "point_type": "LOW"
  },
  {
    "index": 6,
    "timestamp": "2026-02-05 01:30:00+00:00",
    "price": 73187.6,
    "point_type": "HIGH"
  },
  {
    "index": 9,
    "timestamp": "2026-02-05 02:15:00+00:00",
    "price": 71680.0,
    "point_type": "LOW"
  },
  {
    "index": 10,
    "timestamp": "2026-02-05 02:30:00+00:00",
    "price": 72854.39,
    "point_type": "HIGH"
  },
  {
    "index": 17,
    "timestamp": "2026-02-05 04:15:00+00:00",
    "price": 70701.0,
    "point_type": "LOW"
  },
  {
    "index": 18,
    "timestamp": "2026-02-05 04:30:00+00:00",
    "price": 71400.0,
    "point_type": "HIGH"
  },
  {
    "index": 21,
    "timestamp": "2026-02-05 05:15:00+00:00",
    "price": 70140.0,
    "point_type": "LOW"
  },
  {
    "index": 22,
    "timestamp": "2026-02-05 05:30:00+00:00",
    "price": 71150.16,
    "point_type": "HIGH"
  },
  {
    "index": 25,
    "timestamp": "2026-02-05 06:15:00+00:00",
    "price": 70434.05,
    "point_type": "LOW"
  },
  {
    "index": 28,
    "timestamp": "2026-02-05 07:00:00+00:00",
    "price": 71622.82,
    "point_type": "HIGH"
  },
  {
    "index": 31,
    "timestamp": "2026-02-05 07:45:00+00:00",
    "price": 70644.73,
    "point_type": "LOW"
  },
  {
    "index": 34,
    "timestamp": "2026-02-05 08:30:00+00:00",
    "price": 71550.0,
    "point_type": "HIGH"
  },
  {
    "index": 35,
    "timestamp": "2026-02-05 08:45:00+00:00",
    "price": 71045.0,
    "point_type": "LOW"
  },
  {
    "index": 37,
    "timestamp": "2026-02-05 09:15:00+00:00",
    "price": 71978.58,
    "point_type": "HIGH"
  },
  {
    "index": 40,
    "timestamp": "2026-02-05 10:00:00+00:00",
    "price": 71311.44,
    "point_type": "LOW"
  },
  {
    "index": 42,
    "timestamp": "2026-02-05 10:30:00+00:00",
    "price": 71726.79,
    "point_type": "HIGH"
  },
  {
    "index": 46,
    "timestamp": "2026-02-05 11:30:00+00:00",
    "price": 69922.0,
    "point_type": "LOW"
  },
  {
    "index": 48,
    "timestamp": "2026-02-05 12:00:00+00:00",
    "price": 70603.49,
    "point_type": "HIGH"
  },
  {
    "index": 49,
    "timestamp": "2026-02-05 12:15:00+00:00",
    "price": 69163.0,
    "point_type": "LOW"
  },
  {
    "index": 52,
    "timestamp": "2026-02-05 13:00:00+00:00",
    "price": 69831.85,
    "point_type": "HIGH"
  },
  {
    "index": 53,
    "timestamp": "2026-02-05 13:15:00+00:00",
    "price": 69261.11,
    "point_type": "LOW"
  },
  {
    "index": 56,
    "timestamp": "2026-02-05 14:00:00+00:00",
    "price": 70312.62,
    "point_type": "HIGH"
  },
  {
    "index": 57,
    "timestamp": "2026-02-05 14:15:00+00:00",
    "price": 69492.25,
    "point_type": "LOW"
  },
  {
    "index": 58,
    "timestamp": "2026-02-05 14:30:00+00:00",
    "price": 70872.04,
    "point_type": "HIGH"
  },
  {
    "index": 62,
    "timestamp": "2026-02-05 15:30:00+00:00",
    "price": 66720.15,
    "point_type": "LOW"
  },
  {
    "index": 63,
    "timestamp": "2026-02-05 15:45:00+00:00",
    "price": 68273.15,
    "point_type": "HIGH"
  },
  {
    "index": 64,
    "timestamp": "2026-02-05 16:00:00+00:00",
    "price": 66955.34,
    "point_type": "LOW"
  },
  {
    "index": 67,
    "timestamp": "2026-02-05 16:45:00+00:00",
    "price": 68681.81,
    "point_type": "HIGH"
  },
  {
    "index": 75,
    "timestamp": "2026-02-05 18:45:00+00:00",
    "price": 65385.0,
    "point_type": "LOW"
  },
  {
    "index": 76,
    "timestamp": "2026-02-05 19:00:00+00:00",
    "price": 66637.46,
    "point_type": "HIGH"
  },
  {
    "index": 83,
    "timestamp": "2026-02-05 20:45:00+00:00",
    "price": 62345.0,
    "point_type": "LOW"
  },
  {
    "index": 84,
    "timestamp": "2026-02-05 21:00:00+00:00",
    "price": 64775.0,
    "point_type": "HIGH"
  },
  {
    "index": 85,
    "timestamp": "2026-02-05 21:15:00+00:00",
    "price": 62888.34,
    "point_type": "LOW"
  },
  {
    "index": 86,
    "timestamp": "2026-02-05 21:30:00+00:00",
    "price": 64248.71,
    "point_type": "HIGH"
  },
  {
    "index": 89,
    "timestamp": "2026-02-05 22:15:00+00:00",
    "price": 62690.9,
    "point_type": "LOW"
  },
  {
    "index": 92,
    "timestamp": "2026-02-05 23:00:00+00:00",
    "price": 64908.0,
    "point_type": "HIGH"
  }
]
```
### Higher highs / lower highs
```json
{
  "raw_swing_count": 50,
  "swing_count": 38,
  "leg_count": 37,
  "structure_direction": "SIDEWAYS_STRUCTURE",
  "total_movement": 52700.29000000002,
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
    "lower_price": 70603.49,
    "upper_price": 70701.0,
    "mid_price": 70651.4525,
    "touch_count": 4,
    "source_indexes": [
      17,
      31,
      43,
      48
    ],
    "zone_width": 97.50999999999476,
    "zone_width_ratio": 0.001380155630912114,
    "formed_at_index": 48,
    "first_touch_index": 17,
    "last_touch_index": 48,
    "source_point_types": [
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
    "lower_price": 71550.0,
    "upper_price": 71726.79,
    "mid_price": 71644.9025,
    "touch_count": 4,
    "source_indexes": [
      9,
      28,
      34,
      42
    ],
    "zone_width": 176.7899999999936,
    "zone_width_ratio": 0.00246758658091542,
    "formed_at_index": 42,
    "first_touch_index": 9,
    "last_touch_index": 42,
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
  "lower_boundary": 70603.49,
  "upper_boundary": 71726.79,
  "midline": 71165.14,
  "width": 1123.2999999999884,
  "width_ratio": 0.015784413548543406,
  "touch_count": 8,
  "inside_close_ratio": 0.75,
  "formed_at_index": 48,
  "first_touch_index": 9,
  "duration_candles": 40,
  "boundary_alternation_count": 5
}
```
### Range high / low
See trading range object above.
### Price position inside range
```json
{
  "swing_count": 50,
  "zone_count": 14,
  "range_detected": true,
  "range_formed_at_index": 48,
  "range_duration_candles": 40,
  "inside_close_ratio": 0.75,
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
  "breakout_index": 49,
  "boundary_price": 70603.49,
  "breakout_close": 69640.86,
  "distance_ratio": 0.013634311844924444,
  "returned_to_range": false,
  "follow_through_count": 5,
  "evidence": [
    {
      "source": "SCHWAGER",
      "code": "SCHWAGER_BEARISH_RANGE_BREAKDOWN_CONTEXT",
      "description": "Closing price moved below the range boundary",
      "contribution": -0.12,
      "metadata": {
        "breakout_index": 49
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
        "distance_ratio": 0.02040253250937036
      }
    }
  ],
  "analysis_start_index": 49,
  "confirmation_method": "CLOSE_COUNT_AND_DISTANCE",
  "confirmation_close_count": 6,
  "extreme_index": 49,
  "extreme_price": 69163.0,
  "maximum_distance_ratio": 0.02040253250937036,
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
SCHWAGER_SUPPORT_ZONE_IDENTIFIED, SCHWAGER_PREVIOUS_EXTREME_ZONE_IDENTIFIED, SCHWAGER_RESISTANCE_ZONE_IDENTIFIED, SCHWAGER_RESISTANCE_ZONE_HELD, SCHWAGER_SUPPORT_ZONE_HELD, SCHWAGER_ZONE_TOO_WIDE, SCHWAGER_TRADING_RANGE_DETECTED, SCHWAGER_PRICE_INSIDE_RANGE, SCHWAGER_RANGE_UPPER_BOUNDARY_HELD, SCHWAGER_RANGE_LOWER_BOUNDARY_HELD, SCHWAGER_RANGE_DURATION_CONFIRMED, SCHWAGER_RANGE_BOUNDARY_ALTERNATION_CONFIRMED, SCHWAGER_BEARISH_RANGE_BREAKDOWN_CONTEXT, SCHWAGER_BREAKOUT_REQUIRES_CONFIRMATION, SCHWAGER_BREAKOUT_FOLLOW_THROUGH_CONFIRMED, SCHWAGER_BREAKOUT_CONFIRMED_BY_CLOSE_COUNT, SCHWAGER_BREAKOUT_CONFIRMED_BY_DISTANCE

## 4. BookEvidenceMatrix
### Bullish evidence
Count: 26
### Bearish evidence
Count: 31
### Neutral/range evidence
Count: 343
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
  "total_evidence_count": 400,
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
  "FLAT": 0.55,
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
    "score": 0.55
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
