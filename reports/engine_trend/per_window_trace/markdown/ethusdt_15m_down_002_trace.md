# ethusdt_15m_down_002 вЂ” Market Evidence Trace

## Window
- Symbol: ETHUSDT
- Interval: 15m
- Period: 2025-03-03T00:00:00+00:00 вЂ” 2025-03-03T23:45:00+00:00
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
    "timestamp": "2025-03-03 00:00:00+00:00",
    "candle_index": 0,
    "open": 2518.12,
    "high": 2523.56,
    "low": 2480.48,
    "close": 2482.02,
    "body_pct": 0.837975858867223,
    "upper_shadow_pct": 0.12627669452182136,
    "lower_shadow_pct": 0.03574744661095557,
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
    "timestamp": "2025-03-03 00:45:00+00:00",
    "candle_index": 3,
    "open": 2479.81,
    "high": 2484.75,
    "low": 2464.27,
    "close": 2465.52,
    "body_pct": 0.6977539062499976,
    "upper_shadow_pct": 0.24121093750000244,
    "lower_shadow_pct": 0.061035156249999944,
    "position_in_window": 0.0316,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-03-03 01:00:00+00:00",
    "candle_index": 4,
    "open": 2465.52,
    "high": 2476.13,
    "low": 2460.89,
    "close": 2461.69,
    "body_pct": 0.25131233595799657,
    "upper_shadow_pct": 0.6961942257217824,
    "lower_shadow_pct": 0.052493438320221096,
    "position_in_window": 0.0421,
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
    "timestamp": "2025-03-03 01:15:00+00:00",
    "candle_index": 5,
    "open": 2461.69,
    "high": 2467.48,
    "low": 2451.56,
    "close": 2460.54,
    "body_pct": 0.07223618090452799,
    "upper_shadow_pct": 0.36369346733667945,
    "lower_shadow_pct": 0.5640703517587925,
    "position_in_window": 0.0526,
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
    "timestamp": "2025-03-03 01:30:00+00:00",
    "candle_index": 6,
    "open": 2460.55,
    "high": 2470.0,
    "low": 2450.52,
    "close": 2467.96,
    "body_pct": 0.3803901437371585,
    "upper_shadow_pct": 0.10472279260780092,
    "lower_shadow_pct": 0.5148870636550406,
    "position_in_window": 0.0632,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-03-03 01:45:00+00:00",
    "candle_index": 7,
    "open": 2467.97,
    "high": 2467.99,
    "low": 2457.09,
    "close": 2458.8,
    "body_pct": 0.8412844036697178,
    "upper_shadow_pct": 0.0018348623853194934,
    "lower_shadow_pct": 0.1568807339449627,
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
    "open": 2458.8,
    "high": 2461.5,
    "low": 2436.48,
    "close": 2442.48,
    "body_pct": 0.6522781774580406,
    "upper_shadow_pct": 0.10791366906474101,
    "lower_shadow_pct": 0.2398081534772184,
    "position_in_window": 0.0842,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-03-03 02:15:00+00:00",
    "candle_index": 9,
    "open": 2442.48,
    "high": 2445.0,
    "low": 2418.67,
    "close": 2420.7,
    "body_pct": 0.8271933156095808,
    "upper_shadow_pct": 0.09570831750854496,
    "lower_shadow_pct": 0.07709836688187433,
    "position_in_window": 0.0947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-03-03 02:30:00+00:00",
    "candle_index": 10,
    "open": 2420.7,
    "high": 2443.73,
    "low": 2420.62,
    "close": 2439.41,
    "body_pct": 0.8096062310687985,
    "upper_shadow_pct": 0.18693206404154653,
    "lower_shadow_pct": 0.0034617048896549893,
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
    "open": 2447.49,
    "high": 2455.7,
    "low": 2437.36,
    "close": 2439.4,
    "body_pct": 0.4411123227917027,
    "upper_shadow_pct": 0.447655398037087,
    "lower_shadow_pct": 0.11123227917121035,
    "position_in_window": 0.1263,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-03-03 03:30:00+00:00",
    "candle_index": 14,
    "open": 2432.53,
    "high": 2440.69,
    "low": 2426.67,
    "close": 2428.95,
    "body_pct": 0.2553495007132943,
    "upper_shadow_pct": 0.5820256776034141,
    "lower_shadow_pct": 0.1626248216832916,
    "position_in_window": 0.1474,
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
    "timestamp": "2025-03-03 03:45:00+00:00",
    "candle_index": 15,
    "open": 2429.01,
    "high": 2442.22,
    "low": 2426.95,
    "close": 2441.15,
    "body_pct": 0.7950229207596521,
    "upper_shadow_pct": 0.07007203667319647,
    "lower_shadow_pct": 0.13490504256715144,
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
    "timestamp": "2025-03-03 04:00:00+00:00",
    "candle_index": 16,
    "open": 2441.16,
    "high": 2442.64,
    "low": 2436.21,
    "close": 2437.6,
    "body_pct": 0.5536547433903634,
    "upper_shadow_pct": 0.2301710730948765,
    "lower_shadow_pct": 0.2161741835147602,
    "position_in_window": 0.1684,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-03-03 04:30:00+00:00",
    "candle_index": 18,
    "open": 2443.21,
    "high": 2448.72,
    "low": 2438.83,
    "close": 2448.71,
    "body_pct": 0.5561172901921204,
    "upper_shadow_pct": 0.0010111223457799454,
    "lower_shadow_pct": 0.44287158746209965,
    "position_in_window": 0.1895,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-03-03 04:45:00+00:00",
    "candle_index": 19,
    "open": 2448.71,
    "high": 2452.9,
    "low": 2447.2,
    "close": 2450.32,
    "body_pct": 0.282456140350886,
    "upper_shadow_pct": 0.45263157894733397,
    "lower_shadow_pct": 0.26491228070178,
    "position_in_window": 0.2,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION"
    ]
  },
  {
    "timestamp": "2025-03-03 05:00:00+00:00",
    "candle_index": 20,
    "open": 2450.32,
    "high": 2457.25,
    "low": 2446.68,
    "close": 2447.71,
    "body_pct": 0.2469252601703015,
    "upper_shadow_pct": 0.655629139072822,
    "lower_shadow_pct": 0.09744560075687646,
    "position_in_window": 0.2105,
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
    "timestamp": "2025-03-03 05:15:00+00:00",
    "candle_index": 21,
    "open": 2447.71,
    "high": 2449.6,
    "low": 2440.67,
    "close": 2442.03,
    "body_pct": 0.636058230683084,
    "upper_shadow_pct": 0.21164613661813073,
    "lower_shadow_pct": 0.15229563269878524,
    "position_in_window": 0.2211,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-03-03 05:45:00+00:00",
    "candle_index": 23,
    "open": 2445.16,
    "high": 2451.0,
    "low": 2443.81,
    "close": 2449.94,
    "body_pct": 0.6648122392211633,
    "upper_shadow_pct": 0.14742698191932369,
    "lower_shadow_pct": 0.18776077885951303,
    "position_in_window": 0.2421,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-03-03 06:00:00+00:00",
    "candle_index": 24,
    "open": 2449.94,
    "high": 2450.0,
    "low": 2430.23,
    "close": 2434.76,
    "body_pct": 0.7678300455235129,
    "upper_shadow_pct": 0.0030349013657028573,
    "lower_shadow_pct": 0.22913505311078422,
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
    "timestamp": "2025-03-03 06:30:00+00:00",
    "candle_index": 26,
    "open": 2425.89,
    "high": 2425.89,
    "low": 2380.5,
    "close": 2388.81,
    "body_pct": 0.816920026437542,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.183079973562458,
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
    "open": 2372.68,
    "high": 2383.22,
    "low": 2352.79,
    "close": 2374.49,
    "body_pct": 0.05948077555044217,
    "upper_shadow_pct": 0.2868879395333574,
    "lower_shadow_pct": 0.6536312849162005,
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
    "open": 2374.49,
    "high": 2384.6,
    "low": 2369.8,
    "close": 2376.39,
    "body_pct": 0.1283783783783869,
    "upper_shadow_pct": 0.5547297297297424,
    "lower_shadow_pct": 0.31689189189187067,
    "position_in_window": 0.3053,
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
    "timestamp": "2025-03-03 07:30:00+00:00",
    "candle_index": 30,
    "open": 2376.39,
    "high": 2384.06,
    "low": 2371.31,
    "close": 2378.77,
    "body_pct": 0.18666666666667522,
    "upper_shadow_pct": 0.41490196078431085,
    "lower_shadow_pct": 0.3984313725490139,
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
    "open": 2387.01,
    "high": 2388.11,
    "low": 2380.4,
    "close": 2380.72,
    "body_pct": 0.8158236057069246,
    "upper_shadow_pct": 0.14267185473409907,
    "lower_shadow_pct": 0.041504539558976324,
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
    "timestamp": "2025-03-03 08:30:00+00:00",
    "candle_index": 34,
    "open": 2366.69,
    "high": 2375.29,
    "low": 2358.0,
    "close": 2368.94,
    "body_pct": 0.13013302486986725,
    "upper_shadow_pct": 0.3672643146327312,
    "lower_shadow_pct": 0.5026026604974015,
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
    "timestamp": "2025-03-03 09:00:00+00:00",
    "candle_index": 36,
    "open": 2345.41,
    "high": 2355.33,
    "low": 2334.22,
    "close": 2344.24,
    "body_pct": 0.055423969682617986,
    "upper_shadow_pct": 0.4699194694457609,
    "lower_shadow_pct": 0.4746565608716211,
    "position_in_window": 0.3789,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "DOJI_INDECISION"
    ]
  },
  {
    "timestamp": "2025-03-03 09:15:00+00:00",
    "candle_index": 37,
    "open": 2344.24,
    "high": 2351.38,
    "low": 2322.01,
    "close": 2351.0,
    "body_pct": 0.23016683690841824,
    "upper_shadow_pct": 0.012938372488938052,
    "lower_shadow_pct": 0.7568947906026438,
    "position_in_window": 0.3895,
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
    "timestamp": "2025-03-03 09:30:00+00:00",
    "candle_index": 38,
    "open": 2351.0,
    "high": 2356.69,
    "low": 2344.04,
    "close": 2347.67,
    "body_pct": 0.26324110671935996,
    "upper_shadow_pct": 0.44980237154150304,
    "lower_shadow_pct": 0.286956521739137,
    "position_in_window": 0.4,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION"
    ]
  },
  {
    "timestamp": "2025-03-03 09:45:00+00:00",
    "candle_index": 39,
    "open": 2347.67,
    "high": 2352.5,
    "low": 2338.85,
    "close": 2347.51,
    "body_pct": 0.011721611721600982,
    "upper_shadow_pct": 0.35384615384614615,
    "lower_shadow_pct": 0.6344322344322528,
    "position_in_window": 0.4105,
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
    "timestamp": "2025-03-03 10:00:00+00:00",
    "candle_index": 40,
    "open": 2347.5,
    "high": 2352.08,
    "low": 2340.79,
    "close": 2349.49,
    "body_pct": 0.17626217891937893,
    "upper_shadow_pct": 0.22940655447299857,
    "lower_shadow_pct": 0.5943312666076225,
    "position_in_window": 0.4211,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "CLOSE_NEAR_HIGH",
      "SPINNING_TOP_INDECISION"
    ]
  }
]
```
### Doji / spinning top / small body cluster
```json
{
  "doji_count": 10,
  "doji_ratio": 0.10416666666666667,
  "small_body_count": 26,
  "small_body_ratio": 0.2708333333333333,
  "bullish_body_total": 353.94999999999754,
  "bearish_body_total": 723.2699999999986
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
    "code": "BEARISH_ENGULFING_CONTEXT",
    "description": "Bearish body engulfs the preceding bullish body",
    "contribution": -0.1,
    "metadata": {
      "previous_timestamp": "2025-03-03 01:30:00+00:00",
      "timestamp": "2025-03-03 01:45:00+00:00",
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
      "previous_timestamp": "2025-03-03 01:30:00+00:00",
      "timestamp": "2025-03-03 01:45:00+00:00",
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
      "previous_timestamp": "2025-03-03 02:45:00+00:00",
      "timestamp": "2025-03-03 03:00:00+00:00",
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
      "previous_timestamp": "2025-03-03 02:45:00+00:00",
      "timestamp": "2025-03-03 03:00:00+00:00",
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
    "code": "BEARISH_ENGULFING_CONTEXT",
    "description": "Bearish body engulfs the preceding bullish body",
    "contribution": -0.1,
    "metadata": {
      "previous_timestamp": "2025-03-03 05:45:00+00:00",
      "timestamp": "2025-03-03 06:00:00+00:00",
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
      "previous_timestamp": "2025-03-03 05:45:00+00:00",
      "timestamp": "2025-03-03 06:00:00+00:00",
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
      "previous_timestamp": "2025-03-03 08:30:00+00:00",
      "timestamp": "2025-03-03 08:45:00+00:00",
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
      "previous_timestamp": "2025-03-03 08:30:00+00:00",
      "timestamp": "2025-03-03 08:45:00+00:00",
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
      "previous_timestamp": "2025-03-03 09:00:00+00:00",
      "timestamp": "2025-03-03 09:15:00+00:00",
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
      "previous_timestamp": "2025-03-03 09:00:00+00:00",
      "timestamp": "2025-03-03 09:15:00+00:00",
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
      "previous_timestamp": "2025-03-03 09:45:00+00:00",
      "timestamp": "2025-03-03 10:00:00+00:00",
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
      "previous_timestamp": "2025-03-03 09:45:00+00:00",
      "timestamp": "2025-03-03 10:00:00+00:00",
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
      "previous_timestamp": "2025-03-03 11:15:00+00:00",
      "timestamp": "2025-03-03 11:30:00+00:00",
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
      "previous_timestamp": "2025-03-03 11:15:00+00:00",
      "timestamp": "2025-03-03 11:30:00+00:00",
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
      "previous_timestamp": "2025-03-03 11:45:00+00:00",
      "timestamp": "2025-03-03 12:00:00+00:00",
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
      "previous_timestamp": "2025-03-03 11:45:00+00:00",
      "timestamp": "2025-03-03 12:00:00+00:00",
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
STRONG_BEARISH_CANDLE_BODY, CLOSE_NEAR_LOW, LONG_UPPER_SHADOW_REJECTION, SMALL_BODY_INDECISION, SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED, CANDLE_PATTERN_NEEDS_TREND_CONTEXT, LONG_LOWER_SHADOW_REJECTION, DOJI_INDECISION, CLOSE_NEAR_HIGH, STRONG_BULLISH_CANDLE_BODY, SPINNING_TOP_INDECISION, HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED, BEARISH_ENGULFING_CONTEXT, ENGULFING_WITHOUT_FOLLOW_THROUGH, BULLISH_ENGULFING_CONTEXT, INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED, REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH, LONG_LEGGED_DOJI_CONTEXT, BEARISH_BELT_HOLD_CONTEXT_REQUIRED, BULLISH_BELT_HOLD_CONTEXT_REQUIRED, RICKSHAW_MAN_DOJI_CONTEXT, HANGING_MAN_LIKE_CONTEXT_REQUIRED, TWEEZERS_TOP_CONTEXT_REQUIRED, TWEEZERS_BOTTOM_CONTEXT_REQUIRED, BULLISH_SEPARATING_LINES_CONTEXT, BULLISH_HARAMI_CONTEXT, THREE_BLACK_CROWS_CONTEXT, BEARISH_BODY_DOMINANCE

## 2. Altunina trend context
### Swing structure
```json
[
  {
    "index": 2,
    "timestamp": "2025-03-03 00:30:00+00:00",
    "price": 2493.26,
    "point_type": "HIGH"
  },
  {
    "index": 9,
    "timestamp": "2025-03-03 02:15:00+00:00",
    "price": 2418.67,
    "point_type": "LOW"
  },
  {
    "index": 12,
    "timestamp": "2025-03-03 03:00:00+00:00",
    "price": 2455.7,
    "point_type": "HIGH"
  },
  {
    "index": 13,
    "timestamp": "2025-03-03 03:15:00+00:00",
    "price": 2425.17,
    "point_type": "LOW"
  },
  {
    "index": 20,
    "timestamp": "2025-03-03 05:00:00+00:00",
    "price": 2457.25,
    "point_type": "HIGH"
  },
  {
    "index": 21,
    "timestamp": "2025-03-03 05:15:00+00:00",
    "price": 2440.67,
    "point_type": "LOW"
  },
  {
    "index": 23,
    "timestamp": "2025-03-03 05:45:00+00:00",
    "price": 2451.0,
    "point_type": "HIGH"
  },
  {
    "index": 28,
    "timestamp": "2025-03-03 07:00:00+00:00",
    "price": 2352.79,
    "point_type": "LOW"
  },
  {
    "index": 31,
    "timestamp": "2025-03-03 07:45:00+00:00",
    "price": 2391.46,
    "point_type": "HIGH"
  },
  {
    "index": 37,
    "timestamp": "2025-03-03 09:15:00+00:00",
    "price": 2322.01,
    "point_type": "LOW"
  },
  {
    "index": 38,
    "timestamp": "2025-03-03 09:30:00+00:00",
    "price": 2356.69,
    "point_type": "HIGH"
  },
  {
    "index": 39,
    "timestamp": "2025-03-03 09:45:00+00:00",
    "price": 2338.85,
    "point_type": "LOW"
  },
  {
    "index": 41,
    "timestamp": "2025-03-03 10:15:00+00:00",
    "price": 2366.29,
    "point_type": "HIGH"
  },
  {
    "index": 43,
    "timestamp": "2025-03-03 10:45:00+00:00",
    "price": 2349.71,
    "point_type": "LOW"
  },
  {
    "index": 44,
    "timestamp": "2025-03-03 11:00:00+00:00",
    "price": 2363.89,
    "point_type": "HIGH"
  },
  {
    "index": 45,
    "timestamp": "2025-03-03 11:15:00+00:00",
    "price": 2344.4,
    "point_type": "LOW"
  },
  {
    "index": 48,
    "timestamp": "2025-03-03 12:00:00+00:00",
    "price": 2376.78,
    "point_type": "HIGH"
  },
  {
    "index": 49,
    "timestamp": "2025-03-03 12:15:00+00:00",
    "price": 2352.26,
    "point_type": "LOW"
  },
  {
    "index": 52,
    "timestamp": "2025-03-03 13:00:00+00:00",
    "price": 2376.54,
    "point_type": "HIGH"
  },
  {
    "index": 53,
    "timestamp": "2025-03-03 13:15:00+00:00",
    "price": 2361.3,
    "point_type": "LOW"
  },
  {
    "index": 54,
    "timestamp": "2025-03-03 13:30:00+00:00",
    "price": 2389.0,
    "point_type": "HIGH"
  },
  {
    "index": 59,
    "timestamp": "2025-03-03 14:45:00+00:00",
    "price": 2266.97,
    "point_type": "LOW"
  },
  {
    "index": 61,
    "timestamp": "2025-03-03 15:15:00+00:00",
    "price": 2309.48,
    "point_type": "HIGH"
  },
  {
    "index": 64,
    "timestamp": "2025-03-03 16:00:00+00:00",
    "price": 2258.0,
    "point_type": "LOW"
  },
  {
    "index": 65,
    "timestamp": "2025-03-03 16:15:00+00:00",
    "price": 2296.63,
    "point_type": "HIGH"
  },
  {
    "index": 68,
    "timestamp": "2025-03-03 17:00:00+00:00",
    "price": 2265.33,
    "point_type": "LOW"
  },
  {
    "index": 70,
    "timestamp": "2025-03-03 17:30:00+00:00",
    "price": 2297.0,
    "point_type": "HIGH"
  },
  {
    "index": 77,
    "timestamp": "2025-03-03 19:15:00+00:00",
    "price": 2150.0,
    "point_type": "LOW"
  },
  {
    "index": 78,
    "timestamp": "2025-03-03 19:30:00+00:00",
    "price": 2194.08,
    "point_type": "HIGH"
  },
  {
    "index": 79,
    "timestamp": "2025-03-03 19:45:00+00:00",
    "price": 2100.0,
    "point_type": "LOW"
  },
  {
    "index": 81,
    "timestamp": "2025-03-03 20:15:00+00:00",
    "price": 2140.4,
    "point_type": "HIGH"
  },
  {
    "index": 82,
    "timestamp": "2025-03-03 20:30:00+00:00",
    "price": 2097.91,
    "point_type": "LOW"
  },
  {
    "index": 86,
    "timestamp": "2025-03-03 21:30:00+00:00",
    "price": 2146.92,
    "point_type": "HIGH"
  },
  {
    "index": 87,
    "timestamp": "2025-03-03 21:45:00+00:00",
    "price": 2103.76,
    "point_type": "LOW"
  },
  {
    "index": 91,
    "timestamp": "2025-03-03 22:45:00+00:00",
    "price": 2173.29,
    "point_type": "HIGH"
  },
  {
    "index": 93,
    "timestamp": "2025-03-03 23:15:00+00:00",
    "price": 2145.96,
    "point_type": "LOW"
  }
]
```
### Higher highs / lower highs
```json
{
  "raw_swing_count": 45,
  "swing_count": 36,
  "leg_count": 35,
  "structure_direction": "SIDEWAYS_STRUCTURE",
  "total_movement": 1536.499999999999,
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
    "lower_price": 2344.4,
    "upper_price": 2357.64,
    "mid_price": 2352.07,
    "touch_count": 7,
    "source_indexes": [
      28,
      33,
      38,
      43,
      45,
      47,
      49
    ],
    "zone_width": 13.239999999999782,
    "zone_width_ratio": 0.005629084168413262,
    "formed_at_index": 49,
    "first_touch_index": 28,
    "last_touch_index": 49,
    "source_point_types": [
      "LOW",
      "LOW",
      "HIGH",
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
    "lower_price": 2449.34,
    "upper_price": 2457.25,
    "mid_price": 2452.762,
    "touch_count": 5,
    "source_indexes": [
      6,
      12,
      17,
      20,
      23
    ],
    "zone_width": 7.9099999999998545,
    "zone_width_ratio": 0.0032249358070615304,
    "formed_at_index": 23,
    "first_touch_index": 6,
    "last_touch_index": 23,
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
  "is_detected": false,
  "lower_boundary": 2344.4,
  "upper_boundary": 2457.25,
  "midline": 2400.825,
  "width": 112.84999999999991,
  "width_ratio": 0.047004675476138374,
  "touch_count": 12,
  "inside_close_ratio": 0.9318181818181818,
  "formed_at_index": 49,
  "first_touch_index": 6,
  "duration_candles": 44,
  "boundary_alternation_count": 1
}
```
### Range high / low
See trading range object above.
### Price position inside range
```json
{
  "swing_count": 45,
  "zone_count": 11,
  "range_detected": false,
  "range_formed_at_index": 49,
  "range_duration_candles": 44,
  "inside_close_ratio": 0.9318181818181818,
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
SCHWAGER_SUPPORT_ZONE_IDENTIFIED, SCHWAGER_SUPPORT_ZONE_HELD, SCHWAGER_ZONE_TOO_WIDE, SCHWAGER_RESISTANCE_ZONE_IDENTIFIED, SCHWAGER_RESISTANCE_ZONE_HELD, SCHWAGER_RANGE_NOT_CONFIRMED

## 4. BookEvidenceMatrix
### Bullish evidence
Count: 24
### Bearish evidence
Count: 31
### Neutral/range evidence
Count: 321
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
  "total_evidence_count": 376,
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
