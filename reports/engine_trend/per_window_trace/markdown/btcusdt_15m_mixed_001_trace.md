# btcusdt_15m_mixed_001 вЂ” Market Evidence Trace

## Window
- Symbol: BTCUSDT
- Interval: 15m
- Period: 2025-01-20T00:00:00+00:00 вЂ” 2025-01-20T23:45:00+00:00
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
    "timestamp": "2025-01-20 00:00:00+00:00",
    "candle_index": 0,
    "open": 101331.57,
    "high": 101677.71,
    "low": 100654.8,
    "close": 101408.0,
    "body_pct": 0.07471820590276051,
    "upper_shadow_pct": 0.2636693355231697,
    "lower_shadow_pct": 0.6616124585740698,
    "position_in_window": 0.0,
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
    "timestamp": "2025-01-20 00:30:00+00:00",
    "candle_index": 2,
    "open": 101088.0,
    "high": 101232.66,
    "low": 99550.0,
    "close": 100762.71,
    "body_pct": 0.19331891172310087,
    "upper_shadow_pct": 0.08597102207219712,
    "lower_shadow_pct": 0.720710066204702,
    "position_in_window": 0.0211,
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
    "timestamp": "2025-01-20 00:45:00+00:00",
    "candle_index": 3,
    "open": 100762.71,
    "high": 100802.41,
    "low": 99652.0,
    "close": 99794.51,
    "body_pct": 0.8416129901513449,
    "upper_shadow_pct": 0.03450943576637631,
    "lower_shadow_pct": 0.12387757408227877,
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
    "timestamp": "2025-01-20 01:15:00+00:00",
    "candle_index": 5,
    "open": 100214.58,
    "high": 100518.05,
    "low": 99745.0,
    "close": 100320.0,
    "body_pct": 0.13636892827113103,
    "upper_shadow_pct": 0.25619300174633225,
    "lower_shadow_pct": 0.6074380699825367,
    "position_in_window": 0.0526,
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
    "timestamp": "2025-01-20 01:30:00+00:00",
    "candle_index": 6,
    "open": 100320.0,
    "high": 100999.99,
    "low": 99965.6,
    "close": 100082.26,
    "body_pct": 0.22983594195613394,
    "upper_shadow_pct": 0.6573826119742124,
    "lower_shadow_pct": 0.11278144606965362,
    "position_in_window": 0.0632,
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
    "timestamp": "2025-01-20 01:45:00+00:00",
    "candle_index": 7,
    "open": 100082.27,
    "high": 100724.0,
    "low": 100033.1,
    "close": 100692.82,
    "body_pct": 0.8837024171370792,
    "upper_shadow_pct": 0.04512954117816367,
    "lower_shadow_pct": 0.07116804168475709,
    "position_in_window": 0.0737,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-01-20 02:15:00+00:00",
    "candle_index": 9,
    "open": 101016.41,
    "high": 101713.59,
    "low": 100892.96,
    "close": 101713.58,
    "body_pct": 0.8495546104821986,
    "upper_shadow_pct": 1.2185759714806224e-05,
    "lower_shadow_pct": 0.15043320375808655,
    "position_in_window": 0.0947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-01-20 02:30:00+00:00",
    "candle_index": 10,
    "open": 101713.59,
    "high": 102321.42,
    "low": 101388.64,
    "close": 101657.32,
    "body_pct": 0.060325049850971924,
    "upper_shadow_pct": 0.6516327537039843,
    "lower_shadow_pct": 0.28804219644504375,
    "position_in_window": 0.1053,
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
    "timestamp": "2025-01-20 03:00:00+00:00",
    "candle_index": 12,
    "open": 101926.56,
    "high": 101984.88,
    "low": 101465.08,
    "close": 101795.9,
    "body_pct": 0.2513659099653766,
    "upper_shadow_pct": 0.11219699884572269,
    "lower_shadow_pct": 0.6364370911889007,
    "position_in_window": 0.1263,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION"
    ]
  },
  {
    "timestamp": "2025-01-20 03:15:00+00:00",
    "candle_index": 13,
    "open": 101795.9,
    "high": 102211.08,
    "low": 101495.17,
    "close": 101653.97,
    "body_pct": 0.19825117682389173,
    "upper_shadow_pct": 0.5799332318308245,
    "lower_shadow_pct": 0.2218155913452838,
    "position_in_window": 0.1368,
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
    "timestamp": "2025-01-20 03:30:00+00:00",
    "candle_index": 14,
    "open": 101653.97,
    "high": 101890.91,
    "low": 101487.42,
    "close": 101580.0,
    "body_pct": 0.18332548514213537,
    "upper_shadow_pct": 0.5872264492304623,
    "lower_shadow_pct": 0.22944806562740228,
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
    "timestamp": "2025-01-20 03:45:00+00:00",
    "candle_index": 15,
    "open": 101579.99,
    "high": 101958.65,
    "low": 101411.2,
    "close": 101891.93,
    "body_pct": 0.5698054616859795,
    "upper_shadow_pct": 0.12187414375742354,
    "lower_shadow_pct": 0.30832039455659704,
    "position_in_window": 0.1579,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-01-20 04:00:00+00:00",
    "candle_index": 16,
    "open": 101891.94,
    "high": 101899.94,
    "low": 101535.28,
    "close": 101789.32,
    "body_pct": 0.2814128229035111,
    "upper_shadow_pct": 0.02193824384358011,
    "lower_shadow_pct": 0.6966489332529088,
    "position_in_window": 0.1684,
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
    "timestamp": "2025-01-20 04:15:00+00:00",
    "candle_index": 17,
    "open": 101789.32,
    "high": 102070.57,
    "low": 101594.78,
    "close": 101768.23,
    "body_pct": 0.044326278400157,
    "upper_shadow_pct": 0.5911221337144438,
    "lower_shadow_pct": 0.36455158788539926,
    "position_in_window": 0.1789,
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
    "timestamp": "2025-01-20 04:30:00+00:00",
    "candle_index": 18,
    "open": 101768.24,
    "high": 102378.07,
    "low": 101678.31,
    "close": 102317.14,
    "body_pct": 0.7844117983308375,
    "upper_shadow_pct": 0.0870727106436589,
    "lower_shadow_pct": 0.12851549102550355,
    "position_in_window": 0.1895,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-01-20 04:45:00+00:00",
    "candle_index": 19,
    "open": 102317.13,
    "high": 102800.27,
    "low": 102232.33,
    "close": 102232.34,
    "body_pct": 0.14929393950066522,
    "upper_shadow_pct": 0.8506884530055947,
    "lower_shadow_pct": 1.760749374011563e-05,
    "position_in_window": 0.2,
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
    "timestamp": "2025-01-20 05:15:00+00:00",
    "candle_index": 21,
    "open": 102485.74,
    "high": 102825.73,
    "low": 102420.13,
    "close": 102480.01,
    "body_pct": 0.014127218934937378,
    "upper_shadow_pct": 0.8382396449704093,
    "lower_shadow_pct": 0.14763313609465334,
    "position_in_window": 0.2211,
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
    "timestamp": "2025-01-20 05:30:00+00:00",
    "candle_index": 22,
    "open": 102480.01,
    "high": 102615.57,
    "low": 102332.0,
    "close": 102615.56,
    "body_pct": 0.47801248369009264,
    "upper_shadow_pct": 3.5264661315770286e-05,
    "lower_shadow_pct": 0.5219522516485916,
    "position_in_window": 0.2316,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-01-20 05:45:00+00:00",
    "candle_index": 23,
    "open": 102615.56,
    "high": 102772.3,
    "low": 102297.86,
    "close": 102344.2,
    "body_pct": 0.5719585195177457,
    "upper_shadow_pct": 0.3303684343647342,
    "lower_shadow_pct": 0.09767304611752019,
    "position_in_window": 0.2421,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-01-20 06:30:00+00:00",
    "candle_index": 26,
    "open": 102640.0,
    "high": 104740.0,
    "low": 102606.03,
    "close": 104689.49,
    "body_pct": 0.9604118145990825,
    "upper_shadow_pct": 0.023669498633998948,
    "lower_shadow_pct": 0.015918686766918533,
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
    "timestamp": "2025-01-20 07:00:00+00:00",
    "candle_index": 28,
    "open": 107482.36,
    "high": 109499.99,
    "low": 107357.22,
    "close": 108975.42,
    "body_pct": 0.6967896694465551,
    "upper_shadow_pct": 0.24480928891108517,
    "lower_shadow_pct": 0.05840104164235974,
    "position_in_window": 0.2947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-01-20 07:15:00+00:00",
    "candle_index": 29,
    "open": 108975.43,
    "high": 109081.13,
    "low": 107701.01,
    "close": 108706.15,
    "body_pct": 0.19511346839405044,
    "upper_shadow_pct": 0.07658754311220103,
    "lower_shadow_pct": 0.7282989884937485,
    "position_in_window": 0.3053,
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
    "timestamp": "2025-01-20 07:30:00+00:00",
    "candle_index": 30,
    "open": 108706.15,
    "high": 108928.58,
    "low": 107801.63,
    "close": 107948.97,
    "body_pct": 0.6718842894538312,
    "upper_shadow_pct": 0.1973734415901399,
    "lower_shadow_pct": 0.130742268956029,
    "position_in_window": 0.3158,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-01-20 07:45:00+00:00",
    "candle_index": 31,
    "open": 107948.97,
    "high": 108080.0,
    "low": 106923.0,
    "close": 107120.65,
    "body_pct": 0.7159204840103777,
    "upper_shadow_pct": 0.11324978392394022,
    "lower_shadow_pct": 0.17082973206568208,
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
    "timestamp": "2025-01-20 08:00:00+00:00",
    "candle_index": 32,
    "open": 107120.65,
    "high": 108000.0,
    "low": 107093.33,
    "close": 107862.48,
    "body_pct": 0.8181918448829267,
    "upper_shadow_pct": 0.15167591295620717,
    "lower_shadow_pct": 0.03013224216086612,
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
    "timestamp": "2025-01-20 08:15:00+00:00",
    "candle_index": 33,
    "open": 107862.48,
    "high": 108288.0,
    "low": 107658.73,
    "close": 108038.55,
    "body_pct": 0.279800403642325,
    "upper_shadow_pct": 0.39641171516200596,
    "lower_shadow_pct": 0.3237878811956691,
    "position_in_window": 0.3474,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION"
    ]
  },
  {
    "timestamp": "2025-01-20 08:30:00+00:00",
    "candle_index": 34,
    "open": 108038.55,
    "high": 108300.0,
    "low": 107821.74,
    "close": 108228.21,
    "body_pct": 0.39656253920462836,
    "upper_shadow_pct": 0.15010663655750928,
    "lower_shadow_pct": 0.45333082423786236,
    "position_in_window": 0.3579,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-01-20 08:45:00+00:00",
    "candle_index": 35,
    "open": 108228.21,
    "high": 108381.92,
    "low": 107894.44,
    "close": 108320.01,
    "body_pct": 0.18831541806841126,
    "upper_shadow_pct": 0.12700008205465663,
    "lower_shadow_pct": 0.6846844998769321,
    "position_in_window": 0.3684,
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
    "timestamp": "2025-01-20 09:45:00+00:00",
    "candle_index": 39,
    "open": 107966.31,
    "high": 108200.0,
    "low": 107846.15,
    "close": 108132.05,
    "body_pct": 0.46839056097217047,
    "upper_shadow_pct": 0.19203052140736462,
    "lower_shadow_pct": 0.33957891762046494,
    "position_in_window": 0.4105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-01-20 10:00:00+00:00",
    "candle_index": 40,
    "open": 108132.05,
    "high": 108282.11,
    "low": 107911.29,
    "close": 108078.72,
    "body_pct": 0.1438164068820472,
    "upper_shadow_pct": 0.4046707297340889,
    "lower_shadow_pct": 0.4515128633838639,
    "position_in_window": 0.4211,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
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
  "small_body_count": 33,
  "small_body_ratio": 0.34375,
  "bullish_body_total": 23080.83999999994,
  "bearish_body_total": 22152.50000000003
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
      "previous_timestamp": "2025-01-20 01:15:00+00:00",
      "timestamp": "2025-01-20 01:30:00+00:00",
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
      "previous_timestamp": "2025-01-20 01:15:00+00:00",
      "timestamp": "2025-01-20 01:30:00+00:00",
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
      "previous_timestamp": "2025-01-20 03:30:00+00:00",
      "timestamp": "2025-01-20 03:45:00+00:00",
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
      "previous_timestamp": "2025-01-20 03:30:00+00:00",
      "timestamp": "2025-01-20 03:45:00+00:00",
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
      "previous_timestamp": "2025-01-20 04:45:00+00:00",
      "timestamp": "2025-01-20 05:00:00+00:00",
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
      "previous_timestamp": "2025-01-20 04:45:00+00:00",
      "timestamp": "2025-01-20 05:00:00+00:00",
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
      "previous_timestamp": "2025-01-20 05:15:00+00:00",
      "timestamp": "2025-01-20 05:30:00+00:00",
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
      "previous_timestamp": "2025-01-20 05:15:00+00:00",
      "timestamp": "2025-01-20 05:30:00+00:00",
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
      "previous_timestamp": "2025-01-20 05:30:00+00:00",
      "timestamp": "2025-01-20 05:45:00+00:00",
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
      "previous_timestamp": "2025-01-20 05:30:00+00:00",
      "timestamp": "2025-01-20 05:45:00+00:00",
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
      "previous_timestamp": "2025-01-20 09:00:00+00:00",
      "timestamp": "2025-01-20 09:15:00+00:00",
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
      "previous_timestamp": "2025-01-20 09:00:00+00:00",
      "timestamp": "2025-01-20 09:15:00+00:00",
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
      "previous_timestamp": "2025-01-20 10:00:00+00:00",
      "timestamp": "2025-01-20 10:15:00+00:00",
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
      "previous_timestamp": "2025-01-20 10:00:00+00:00",
      "timestamp": "2025-01-20 10:15:00+00:00",
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
      "previous_timestamp": "2025-01-20 11:45:00+00:00",
      "timestamp": "2025-01-20 12:00:00+00:00",
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
      "previous_timestamp": "2025-01-20 11:45:00+00:00",
      "timestamp": "2025-01-20 12:00:00+00:00",
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
      "previous_timestamp": "2025-01-20 12:30:00+00:00",
      "timestamp": "2025-01-20 12:45:00+00:00",
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
      "previous_timestamp": "2025-01-20 12:30:00+00:00",
      "timestamp": "2025-01-20 12:45:00+00:00",
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
      "previous_timestamp": "2025-01-20 13:45:00+00:00",
      "timestamp": "2025-01-20 14:00:00+00:00",
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
      "previous_timestamp": "2025-01-20 13:45:00+00:00",
      "timestamp": "2025-01-20 14:00:00+00:00",
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
LONG_LOWER_SHADOW_REJECTION, SMALL_BODY_INDECISION, DOJI_INDECISION, SPINNING_TOP_INDECISION, HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED, CANDLE_PATTERN_NEEDS_TREND_CONTEXT, STRONG_BEARISH_CANDLE_BODY, CLOSE_NEAR_LOW, LONG_UPPER_SHADOW_REJECTION, STRONG_BULLISH_CANDLE_BODY, CLOSE_NEAR_HIGH, SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED, BEARISH_ENGULFING_CONTEXT, ENGULFING_WITHOUT_FOLLOW_THROUGH, BULLISH_ENGULFING_CONTEXT, HANGING_MAN_LIKE_CONTEXT_REQUIRED, REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH, BEARISH_BELT_HOLD_CONTEXT_REQUIRED, BULLISH_BELT_HOLD_CONTEXT_REQUIRED, LONG_LEGGED_DOJI_CONTEXT, RICKSHAW_MAN_DOJI_CONTEXT, INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED, TWEEZERS_BOTTOM_CONTEXT_REQUIRED, TWEEZERS_TOP_CONTEXT_REQUIRED, DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT, DOJI_TOP_CONTEXT_REQUIRED, BULLISH_SEPARATING_LINES_CONTEXT, BEARISH_HARAMI_CONTEXT, HARAMI_CROSS_CONTEXT, BEARISH_SEPARATING_LINES_CONTEXT, THREE_MOUNTAINS_CONTEXT_REQUIRED

## 2. Altunina trend context
### Swing structure
```json
[
  {
    "index": 2,
    "timestamp": "2025-01-20 00:30:00+00:00",
    "price": 99550.0,
    "point_type": "LOW"
  },
  {
    "index": 10,
    "timestamp": "2025-01-20 02:30:00+00:00",
    "price": 102321.42,
    "point_type": "HIGH"
  },
  {
    "index": 12,
    "timestamp": "2025-01-20 03:00:00+00:00",
    "price": 101465.08,
    "point_type": "LOW"
  },
  {
    "index": 13,
    "timestamp": "2025-01-20 03:15:00+00:00",
    "price": 102211.08,
    "point_type": "HIGH"
  },
  {
    "index": 15,
    "timestamp": "2025-01-20 03:45:00+00:00",
    "price": 101411.2,
    "point_type": "LOW"
  },
  {
    "index": 19,
    "timestamp": "2025-01-20 04:45:00+00:00",
    "price": 102800.27,
    "point_type": "HIGH"
  },
  {
    "index": 20,
    "timestamp": "2025-01-20 05:00:00+00:00",
    "price": 102127.99,
    "point_type": "LOW"
  },
  {
    "index": 21,
    "timestamp": "2025-01-20 05:15:00+00:00",
    "price": 102825.73,
    "point_type": "HIGH"
  },
  {
    "index": 24,
    "timestamp": "2025-01-20 06:00:00+00:00",
    "price": 102220.8,
    "point_type": "LOW"
  },
  {
    "index": 27,
    "timestamp": "2025-01-20 06:45:00+00:00",
    "price": 109588.0,
    "point_type": "HIGH"
  },
  {
    "index": 31,
    "timestamp": "2025-01-20 07:45:00+00:00",
    "price": 106923.0,
    "point_type": "LOW"
  },
  {
    "index": 36,
    "timestamp": "2025-01-20 09:00:00+00:00",
    "price": 109193.23,
    "point_type": "HIGH"
  },
  {
    "index": 38,
    "timestamp": "2025-01-20 09:30:00+00:00",
    "price": 107548.0,
    "point_type": "LOW"
  },
  {
    "index": 41,
    "timestamp": "2025-01-20 10:15:00+00:00",
    "price": 108731.92,
    "point_type": "HIGH"
  },
  {
    "index": 43,
    "timestamp": "2025-01-20 10:45:00+00:00",
    "price": 107769.18,
    "point_type": "LOW"
  },
  {
    "index": 48,
    "timestamp": "2025-01-20 12:00:00+00:00",
    "price": 108700.01,
    "point_type": "HIGH"
  },
  {
    "index": 49,
    "timestamp": "2025-01-20 12:15:00+00:00",
    "price": 105472.95,
    "point_type": "LOW"
  },
  {
    "index": 51,
    "timestamp": "2025-01-20 12:45:00+00:00",
    "price": 107347.58,
    "point_type": "HIGH"
  },
  {
    "index": 58,
    "timestamp": "2025-01-20 14:30:00+00:00",
    "price": 107277.28,
    "point_type": "LOW"
  },
  {
    "index": 59,
    "timestamp": "2025-01-20 14:45:00+00:00",
    "price": 108075.6,
    "point_type": "HIGH"
  },
  {
    "index": 64,
    "timestamp": "2025-01-20 16:00:00+00:00",
    "price": 103708.0,
    "point_type": "LOW"
  },
  {
    "index": 66,
    "timestamp": "2025-01-20 16:30:00+00:00",
    "price": 107050.0,
    "point_type": "HIGH"
  },
  {
    "index": 70,
    "timestamp": "2025-01-20 17:30:00+00:00",
    "price": 100333.0,
    "point_type": "LOW"
  },
  {
    "index": 75,
    "timestamp": "2025-01-20 18:45:00+00:00",
    "price": 104469.15,
    "point_type": "HIGH"
  },
  {
    "index": 78,
    "timestamp": "2025-01-20 19:30:00+00:00",
    "price": 102733.77,
    "point_type": "LOW"
  },
  {
    "index": 82,
    "timestamp": "2025-01-20 20:30:00+00:00",
    "price": 104331.0,
    "point_type": "HIGH"
  },
  {
    "index": 84,
    "timestamp": "2025-01-20 21:00:00+00:00",
    "price": 103603.85,
    "point_type": "LOW"
  },
  {
    "index": 85,
    "timestamp": "2025-01-20 21:15:00+00:00",
    "price": 104080.0,
    "point_type": "HIGH"
  },
  {
    "index": 88,
    "timestamp": "2025-01-20 22:00:00+00:00",
    "price": 101846.15,
    "point_type": "LOW"
  },
  {
    "index": 91,
    "timestamp": "2025-01-20 22:45:00+00:00",
    "price": 103815.98,
    "point_type": "HIGH"
  },
  {
    "index": 93,
    "timestamp": "2025-01-20 23:15:00+00:00",
    "price": 102252.98,
    "point_type": "LOW"
  },
  {
    "index": 94,
    "timestamp": "2025-01-20 23:30:00+00:00",
    "price": 103383.77,
    "point_type": "HIGH"
  }
]
```
### Higher highs / lower highs
```json
{
  "raw_swing_count": 42,
  "swing_count": 32,
  "leg_count": 31,
  "structure_direction": "SIDEWAYS_STRUCTURE",
  "total_movement": 61529.249999999985,
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
    "lower_price": 101846.15,
    "upper_price": 102321.42,
    "mid_price": 102134.15285714286,
    "touch_count": 7,
    "source_indexes": [
      10,
      13,
      15,
      20,
      24,
      88,
      93
    ],
    "zone_width": 475.2700000000041,
    "zone_width_ratio": 0.004653389553881883,
    "formed_at_index": 93,
    "first_touch_index": 10,
    "last_touch_index": 93,
    "source_point_types": [
      "HIGH",
      "HIGH",
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
    "positional_zone_type": "SUPPORT"
  },
  "resistance_zone": {
    "zone_type": "RESISTANCE",
    "lower_price": 103383.77,
    "upper_price": 103815.98,
    "mid_price": 103627.9,
    "touch_count": 4,
    "source_indexes": [
      64,
      84,
      91,
      94
    ],
    "zone_width": 432.20999999999185,
    "zone_width_ratio": 0.004170787982772901,
    "formed_at_index": 94,
    "first_touch_index": 64,
    "last_touch_index": 94,
    "source_point_types": [
      "LOW",
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
  "lower_boundary": 101846.15,
  "upper_boundary": 103815.98,
  "midline": 102831.065,
  "width": 1969.8300000000017,
  "width_ratio": 0.019155981706500867,
  "touch_count": 11,
  "inside_close_ratio": 0.32941176470588235,
  "formed_at_index": 94,
  "first_touch_index": 10,
  "duration_candles": 85,
  "boundary_alternation_count": 5
}
```
### Range high / low
See trading range object above.
### Price position inside range
```json
{
  "swing_count": 42,
  "zone_count": 11,
  "range_detected": false,
  "range_formed_at_index": 94,
  "range_duration_candles": 85,
  "inside_close_ratio": 0.32941176470588235,
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
SCHWAGER_SUPPORT_ZONE_IDENTIFIED, SCHWAGER_SUPPORT_ZONE_HELD, SCHWAGER_ZONE_TOO_WIDE, SCHWAGER_RESISTANCE_ZONE_IDENTIFIED, SCHWAGER_RESISTANCE_ZONE_HELD, SCHWAGER_PREVIOUS_EXTREME_ZONE_IDENTIFIED, SCHWAGER_RANGE_NOT_CONFIRMED

## 4. BookEvidenceMatrix
### Bullish evidence
Count: 30
### Bearish evidence
Count: 26
### Neutral/range evidence
Count: 305
### Conflict
```json
{
  "agreement_state": "ALIGNED_BULLISH",
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
  "total_evidence_count": 361,
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
