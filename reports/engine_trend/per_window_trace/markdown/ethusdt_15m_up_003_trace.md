# ethusdt_15m_up_003 вЂ” Market Evidence Trace

## Window
- Symbol: ETHUSDT
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
    "open": 2217.4,
    "high": 2221.3,
    "low": 2212.1,
    "close": 2212.45,
    "body_pct": 0.5380434782608833,
    "upper_shadow_pct": 0.4239130434782582,
    "lower_shadow_pct": 0.03804347826085855,
    "position_in_window": 0.0,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-03-02 00:15:00+00:00",
    "candle_index": 1,
    "open": 2212.46,
    "high": 2217.57,
    "low": 2203.51,
    "close": 2210.3,
    "body_pct": 0.15362731152203862,
    "upper_shadow_pct": 0.3634423897581897,
    "lower_shadow_pct": 0.48293029871977167,
    "position_in_window": 0.0105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2025-03-02 00:45:00+00:00",
    "candle_index": 3,
    "open": 2218.89,
    "high": 2224.35,
    "low": 2214.57,
    "close": 2215.49,
    "body_pct": 0.34764826175870955,
    "upper_shadow_pct": 0.5582822085889753,
    "lower_shadow_pct": 0.09406952965231513,
    "position_in_window": 0.0316,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-03-02 01:00:00+00:00",
    "candle_index": 4,
    "open": 2215.5,
    "high": 2225.33,
    "low": 2215.0,
    "close": 2224.51,
    "body_pct": 0.8722168441432993,
    "upper_shadow_pct": 0.07938044530490947,
    "lower_shadow_pct": 0.04840271055179124,
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
    "open": 2224.51,
    "high": 2226.53,
    "low": 2218.71,
    "close": 2218.71,
    "body_pct": 0.7416879795396497,
    "upper_shadow_pct": 0.25831202046035034,
    "lower_shadow_pct": 0.0,
    "position_in_window": 0.0526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-03-02 01:45:00+00:00",
    "candle_index": 7,
    "open": 2214.29,
    "high": 2221.61,
    "low": 2211.29,
    "close": 2220.53,
    "body_pct": 0.604651162790711,
    "upper_shadow_pct": 0.10465116279068896,
    "lower_shadow_pct": 0.29069767441860006,
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
    "open": 2220.53,
    "high": 2228.16,
    "low": 2216.58,
    "close": 2222.4,
    "body_pct": 0.1614853195163992,
    "upper_shadow_pct": 0.4974093264248532,
    "lower_shadow_pct": 0.34110535405874765,
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
    "open": 2222.41,
    "high": 2224.23,
    "low": 2212.1,
    "close": 2213.31,
    "body_pct": 0.7502061005770674,
    "upper_shadow_pct": 0.15004122011542848,
    "lower_shadow_pct": 0.09975267930750416,
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
    "timestamp": "2025-03-02 02:30:00+00:00",
    "candle_index": 10,
    "open": 2213.31,
    "high": 2213.31,
    "low": 2201.1,
    "close": 2208.29,
    "body_pct": 0.41113841113840843,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.5888615888615916,
    "position_in_window": 0.1053,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2025-03-02 02:45:00+00:00",
    "candle_index": 11,
    "open": 2208.3,
    "high": 2211.99,
    "low": 2205.1,
    "close": 2209.81,
    "body_pct": 0.2191582002902455,
    "upper_shadow_pct": 0.31640058055150605,
    "lower_shadow_pct": 0.4644412191582485,
    "position_in_window": 0.1158,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2025-03-02 03:00:00+00:00",
    "candle_index": 12,
    "open": 2209.8,
    "high": 2226.5,
    "low": 2209.8,
    "close": 2223.71,
    "body_pct": 0.8329341317365273,
    "upper_shadow_pct": 0.1670658682634727,
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
    "timestamp": "2025-03-02 03:30:00+00:00",
    "candle_index": 14,
    "open": 2219.57,
    "high": 2226.8,
    "low": 2215.91,
    "close": 2224.7,
    "body_pct": 0.47107438016524333,
    "upper_shadow_pct": 0.19283746556476591,
    "lower_shadow_pct": 0.3360881542699907,
    "position_in_window": 0.1474,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-03-02 03:45:00+00:00",
    "candle_index": 15,
    "open": 2224.69,
    "high": 2230.82,
    "low": 2219.41,
    "close": 2220.18,
    "body_pct": 0.39526730937774723,
    "upper_shadow_pct": 0.537248028045569,
    "lower_shadow_pct": 0.06748466257668369,
    "position_in_window": 0.1579,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-03-02 04:15:00+00:00",
    "candle_index": 17,
    "open": 2225.59,
    "high": 2234.48,
    "low": 2219.1,
    "close": 2233.62,
    "body_pct": 0.5221066319895766,
    "upper_shadow_pct": 0.055916775032517636,
    "lower_shadow_pct": 0.42197659297790574,
    "position_in_window": 0.1789,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-03-02 04:45:00+00:00",
    "candle_index": 19,
    "open": 2228.4,
    "high": 2230.29,
    "low": 2224.19,
    "close": 2227.11,
    "body_pct": 0.21147540983606275,
    "upper_shadow_pct": 0.30983606557375426,
    "lower_shadow_pct": 0.478688524590183,
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
    "open": 2227.11,
    "high": 2228.65,
    "low": 2224.66,
    "close": 2228.4,
    "body_pct": 0.32330827067666346,
    "upper_shadow_pct": 0.06265664160400632,
    "lower_shadow_pct": 0.6140350877193302,
    "position_in_window": 0.2105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-03-02 05:15:00+00:00",
    "candle_index": 21,
    "open": 2228.41,
    "high": 2229.8,
    "low": 2224.0,
    "close": 2228.64,
    "body_pct": 0.039655172413794994,
    "upper_shadow_pct": 0.20000000000004703,
    "lower_shadow_pct": 0.760344827586158,
    "position_in_window": 0.2211,
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
    "open": 2228.65,
    "high": 2234.51,
    "low": 2227.3,
    "close": 2229.17,
    "body_pct": 0.07212205270457409,
    "upper_shadow_pct": 0.7406380027739415,
    "lower_shadow_pct": 0.18723994452148435,
    "position_in_window": 0.2316,
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
    "timestamp": "2025-03-02 05:45:00+00:00",
    "candle_index": 23,
    "open": 2229.18,
    "high": 2230.9,
    "low": 2226.7,
    "close": 2229.5,
    "body_pct": 0.07619047619051023,
    "upper_shadow_pct": 0.3333333333333333,
    "lower_shadow_pct": 0.5904761904761564,
    "position_in_window": 0.2421,
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
    "timestamp": "2025-03-02 06:00:00+00:00",
    "candle_index": 24,
    "open": 2229.5,
    "high": 2233.0,
    "low": 2223.49,
    "close": 2223.69,
    "body_pct": 0.6109358569926195,
    "upper_shadow_pct": 0.36803364879073813,
    "lower_shadow_pct": 0.021030494216642298,
    "position_in_window": 0.2526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-03-02 06:15:00+00:00",
    "candle_index": 25,
    "open": 2223.68,
    "high": 2231.27,
    "low": 2218.2,
    "close": 2230.88,
    "body_pct": 0.5508798775822634,
    "upper_shadow_pct": 0.029839326702361727,
    "lower_shadow_pct": 0.41928079571537485,
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
    "open": 2230.88,
    "high": 2233.67,
    "low": 2225.62,
    "close": 2229.12,
    "body_pct": 0.21863354037269297,
    "upper_shadow_pct": 0.34658385093166466,
    "lower_shadow_pct": 0.43478260869564234,
    "position_in_window": 0.2737,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2025-03-02 06:45:00+00:00",
    "candle_index": 27,
    "open": 2229.12,
    "high": 2233.2,
    "low": 2222.11,
    "close": 2222.96,
    "body_pct": 0.5554553651938707,
    "upper_shadow_pct": 0.367899008115423,
    "lower_shadow_pct": 0.07664562669070629,
    "position_in_window": 0.2842,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-03-02 07:00:00+00:00",
    "candle_index": 28,
    "open": 2222.95,
    "high": 2226.9,
    "low": 2218.59,
    "close": 2224.28,
    "body_pct": 0.16004813477742366,
    "upper_shadow_pct": 0.3152827918170768,
    "lower_shadow_pct": 0.5246690734054995,
    "position_in_window": 0.2947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2025-03-02 07:15:00+00:00",
    "candle_index": 29,
    "open": 2224.29,
    "high": 2225.0,
    "low": 2220.6,
    "close": 2223.49,
    "body_pct": 0.1818181818182194,
    "upper_shadow_pct": 0.1613636363636413,
    "lower_shadow_pct": 0.6568181818181393,
    "position_in_window": 0.3053,
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
    "timestamp": "2025-03-02 07:30:00+00:00",
    "candle_index": 30,
    "open": 2223.49,
    "high": 2225.8,
    "low": 2221.6,
    "close": 2223.99,
    "body_pct": 0.11904761904761131,
    "upper_shadow_pct": 0.43095238095244826,
    "lower_shadow_pct": 0.44999999999994045,
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
    "timestamp": "2025-03-02 07:45:00+00:00",
    "candle_index": 31,
    "open": 2224.0,
    "high": 2225.98,
    "low": 2220.4,
    "close": 2221.4,
    "body_pct": 0.46594982078852026,
    "upper_shadow_pct": 0.35483870967742726,
    "lower_shadow_pct": 0.1792114695340525,
    "position_in_window": 0.3263,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-03-02 08:00:00+00:00",
    "candle_index": 32,
    "open": 2221.4,
    "high": 2223.07,
    "low": 2210.8,
    "close": 2211.81,
    "body_pct": 0.7815810920945525,
    "upper_shadow_pct": 0.13610431947840873,
    "lower_shadow_pct": 0.08231458842703872,
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
    "open": 2211.81,
    "high": 2217.37,
    "low": 2211.55,
    "close": 2212.7,
    "body_pct": 0.1529209621992985,
    "upper_shadow_pct": 0.8024054982818396,
    "lower_shadow_pct": 0.044673539518861945,
    "position_in_window": 0.3474,
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
    "timestamp": "2025-03-02 08:30:00+00:00",
    "candle_index": 34,
    "open": 2212.7,
    "high": 2213.55,
    "low": 2208.06,
    "close": 2211.99,
    "body_pct": 0.1293260473588353,
    "upper_shadow_pct": 0.15482695810570624,
    "lower_shadow_pct": 0.7158469945354585,
    "position_in_window": 0.3579,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  }
]
```
### Doji / spinning top / small body cluster
```json
{
  "doji_count": 7,
  "doji_ratio": 0.07291666666666667,
  "small_body_count": 33,
  "small_body_ratio": 0.34375,
  "bullish_body_total": 646.06,
  "bearish_body_total": 345.3800000000001
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
      "previous_timestamp": "2025-03-02 01:30:00+00:00",
      "timestamp": "2025-03-02 01:45:00+00:00",
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
      "previous_timestamp": "2025-03-02 01:30:00+00:00",
      "timestamp": "2025-03-02 01:45:00+00:00",
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
      "previous_timestamp": "2025-03-02 02:00:00+00:00",
      "timestamp": "2025-03-02 02:15:00+00:00",
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
      "previous_timestamp": "2025-03-02 02:00:00+00:00",
      "timestamp": "2025-03-02 02:15:00+00:00",
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
      "previous_timestamp": "2025-03-02 05:45:00+00:00",
      "timestamp": "2025-03-02 06:00:00+00:00",
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
      "previous_timestamp": "2025-03-02 05:45:00+00:00",
      "timestamp": "2025-03-02 06:00:00+00:00",
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
      "previous_timestamp": "2025-03-02 10:15:00+00:00",
      "timestamp": "2025-03-02 10:30:00+00:00",
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
      "previous_timestamp": "2025-03-02 10:15:00+00:00",
      "timestamp": "2025-03-02 10:30:00+00:00",
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
    "code": "BULLISH_ENGULFING_CONTEXT",
    "description": "Bullish body engulfs the preceding bearish body",
    "contribution": 0.1,
    "metadata": {
      "previous_timestamp": "2025-03-02 14:30:00+00:00",
      "timestamp": "2025-03-02 14:45:00+00:00",
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
      "previous_timestamp": "2025-03-02 14:30:00+00:00",
      "timestamp": "2025-03-02 14:45:00+00:00",
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
      "previous_timestamp": "2025-03-02 15:30:00+00:00",
      "timestamp": "2025-03-02 15:45:00+00:00",
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
      "previous_timestamp": "2025-03-02 15:30:00+00:00",
      "timestamp": "2025-03-02 15:45:00+00:00",
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
CLOSE_NEAR_LOW, SMALL_BODY_INDECISION, SPINNING_TOP_INDECISION, LONG_UPPER_SHADOW_REJECTION, STRONG_BULLISH_CANDLE_BODY, CLOSE_NEAR_HIGH, STRONG_BEARISH_CANDLE_BODY, LONG_LOWER_SHADOW_REJECTION, DOJI_INDECISION, SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED, CANDLE_PATTERN_NEEDS_TREND_CONTEXT, HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED, BULLISH_ENGULFING_CONTEXT, ENGULFING_WITHOUT_FOLLOW_THROUGH, BEARISH_ENGULFING_CONTEXT, BULLISH_BELT_HOLD_CONTEXT_REQUIRED, INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED, REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH, BEARISH_BELT_HOLD_CONTEXT_REQUIRED, HANGING_MAN_LIKE_CONTEXT_REQUIRED, TWEEZERS_TOP_CONTEXT_REQUIRED, TWEEZERS_BOTTOM_CONTEXT_REQUIRED, BEARISH_SEPARATING_LINES_CONTEXT, BULLISH_HARAMI_CONTEXT, DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT, DOJI_TOP_CONTEXT_REQUIRED, BEARISH_HARAMI_CONTEXT, BULLISH_SEPARATING_LINES_CONTEXT, THREE_ADVANCING_WHITE_SOLDIERS_CONTEXT, THREE_MOUNTAINS_CONTEXT_REQUIRED, THREE_RIVERS_CONTEXT_REQUIRED, BULLISH_BODY_DOMINANCE

## 2. Altunina trend context
### Swing structure
```json
[
  {
    "index": 1,
    "timestamp": "2025-03-02 00:15:00+00:00",
    "price": 2203.51,
    "point_type": "LOW"
  },
  {
    "index": 5,
    "timestamp": "2025-03-02 01:15:00+00:00",
    "price": 2226.53,
    "point_type": "HIGH"
  },
  {
    "index": 6,
    "timestamp": "2025-03-02 01:30:00+00:00",
    "price": 2209.13,
    "point_type": "LOW"
  },
  {
    "index": 8,
    "timestamp": "2025-03-02 02:00:00+00:00",
    "price": 2228.16,
    "point_type": "HIGH"
  },
  {
    "index": 10,
    "timestamp": "2025-03-02 02:30:00+00:00",
    "price": 2201.1,
    "point_type": "LOW"
  },
  {
    "index": 15,
    "timestamp": "2025-03-02 03:45:00+00:00",
    "price": 2230.82,
    "point_type": "HIGH"
  },
  {
    "index": 17,
    "timestamp": "2025-03-02 04:15:00+00:00",
    "price": 2219.1,
    "point_type": "LOW"
  },
  {
    "index": 18,
    "timestamp": "2025-03-02 04:30:00+00:00",
    "price": 2235.6,
    "point_type": "HIGH"
  },
  {
    "index": 21,
    "timestamp": "2025-03-02 05:15:00+00:00",
    "price": 2224.0,
    "point_type": "LOW"
  },
  {
    "index": 22,
    "timestamp": "2025-03-02 05:30:00+00:00",
    "price": 2234.51,
    "point_type": "HIGH"
  },
  {
    "index": 25,
    "timestamp": "2025-03-02 06:15:00+00:00",
    "price": 2218.2,
    "point_type": "LOW"
  },
  {
    "index": 26,
    "timestamp": "2025-03-02 06:30:00+00:00",
    "price": 2233.67,
    "point_type": "HIGH"
  },
  {
    "index": 28,
    "timestamp": "2025-03-02 07:00:00+00:00",
    "price": 2218.59,
    "point_type": "LOW"
  },
  {
    "index": 31,
    "timestamp": "2025-03-02 07:45:00+00:00",
    "price": 2225.98,
    "point_type": "HIGH"
  },
  {
    "index": 34,
    "timestamp": "2025-03-02 08:30:00+00:00",
    "price": 2208.06,
    "point_type": "LOW"
  },
  {
    "index": 38,
    "timestamp": "2025-03-02 09:30:00+00:00",
    "price": 2255.1,
    "point_type": "HIGH"
  },
  {
    "index": 40,
    "timestamp": "2025-03-02 10:00:00+00:00",
    "price": 2240.0,
    "point_type": "LOW"
  },
  {
    "index": 42,
    "timestamp": "2025-03-02 10:30:00+00:00",
    "price": 2260.84,
    "point_type": "HIGH"
  },
  {
    "index": 49,
    "timestamp": "2025-03-02 12:15:00+00:00",
    "price": 2223.0,
    "point_type": "LOW"
  },
  {
    "index": 51,
    "timestamp": "2025-03-02 12:45:00+00:00",
    "price": 2233.36,
    "point_type": "HIGH"
  },
  {
    "index": 57,
    "timestamp": "2025-03-02 14:15:00+00:00",
    "price": 2172.04,
    "point_type": "LOW"
  },
  {
    "index": 62,
    "timestamp": "2025-03-02 15:30:00+00:00",
    "price": 2291.76,
    "point_type": "HIGH"
  },
  {
    "index": 64,
    "timestamp": "2025-03-02 16:00:00+00:00",
    "price": 2212.35,
    "point_type": "LOW"
  },
  {
    "index": 66,
    "timestamp": "2025-03-02 16:30:00+00:00",
    "price": 2500.0,
    "point_type": "HIGH"
  },
  {
    "index": 68,
    "timestamp": "2025-03-02 17:00:00+00:00",
    "price": 2395.36,
    "point_type": "LOW"
  },
  {
    "index": 70,
    "timestamp": "2025-03-02 17:30:00+00:00",
    "price": 2510.82,
    "point_type": "HIGH"
  },
  {
    "index": 71,
    "timestamp": "2025-03-02 17:45:00+00:00",
    "price": 2452.71,
    "point_type": "LOW"
  },
  {
    "index": 73,
    "timestamp": "2025-03-02 18:15:00+00:00",
    "price": 2518.0,
    "point_type": "HIGH"
  },
  {
    "index": 74,
    "timestamp": "2025-03-02 18:30:00+00:00",
    "price": 2454.02,
    "point_type": "LOW"
  },
  {
    "index": 76,
    "timestamp": "2025-03-02 19:00:00+00:00",
    "price": 2485.28,
    "point_type": "HIGH"
  },
  {
    "index": 80,
    "timestamp": "2025-03-02 20:00:00+00:00",
    "price": 2480.19,
    "point_type": "LOW"
  },
  {
    "index": 81,
    "timestamp": "2025-03-02 20:15:00+00:00",
    "price": 2520.92,
    "point_type": "HIGH"
  },
  {
    "index": 82,
    "timestamp": "2025-03-02 20:30:00+00:00",
    "price": 2484.47,
    "point_type": "LOW"
  },
  {
    "index": 86,
    "timestamp": "2025-03-02 21:30:00+00:00",
    "price": 2540.86,
    "point_type": "HIGH"
  },
  {
    "index": 88,
    "timestamp": "2025-03-02 22:00:00+00:00",
    "price": 2507.18,
    "point_type": "LOW"
  },
  {
    "index": 92,
    "timestamp": "2025-03-02 23:00:00+00:00",
    "price": 2550.58,
    "point_type": "HIGH"
  },
  {
    "index": 94,
    "timestamp": "2025-03-02 23:30:00+00:00",
    "price": 2508.39,
    "point_type": "LOW"
  }
]
```
### Higher highs / lower highs
```json
{
  "raw_swing_count": 44,
  "swing_count": 37,
  "leg_count": 36,
  "structure_direction": "SIDEWAYS_STRUCTURE",
  "total_movement": 1614.6800000000035,
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
    "lower_price": 2218.2,
    "upper_price": 2228.16,
    "mid_price": 2223.513,
    "touch_count": 10,
    "source_indexes": [
      2,
      5,
      8,
      12,
      17,
      21,
      25,
      28,
      31,
      49
    ],
    "zone_width": 9.960000000000036,
    "zone_width_ratio": 0.004479398141589474,
    "formed_at_index": 49,
    "first_touch_index": 2,
    "last_touch_index": 49,
    "source_point_types": [
      "HIGH",
      "HIGH",
      "HIGH",
      "HIGH",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "HIGH",
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
    "lower_price": 2230.82,
    "upper_price": 2240.0,
    "mid_price": 2234.6850000000004,
    "touch_count": 8,
    "source_indexes": [
      15,
      18,
      22,
      24,
      26,
      40,
      45,
      51
    ],
    "zone_width": 9.179999999999836,
    "zone_width_ratio": 0.004107961524778586,
    "formed_at_index": 51,
    "first_touch_index": 15,
    "last_touch_index": 51,
    "source_point_types": [
      "HIGH",
      "HIGH",
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
    "positional_zone_type": "SUPPORT"
  },
  "is_detected": true,
  "lower_boundary": 2218.2,
  "upper_boundary": 2240.0,
  "midline": 2229.1,
  "width": 21.800000000000182,
  "width_ratio": 0.00977973173029482,
  "touch_count": 18,
  "inside_close_ratio": 0.64,
  "formed_at_index": 51,
  "first_touch_index": 2,
  "duration_candles": 50,
  "boundary_alternation_count": 11
}
```
### Range high / low
See trading range object above.
### Price position inside range
```json
{
  "swing_count": 44,
  "zone_count": 11,
  "range_detected": true,
  "range_formed_at_index": 51,
  "range_duration_candles": 50,
  "inside_close_ratio": 0.64,
  "breakout_direction": "DOWNWARD",
  "breakout_status": "CONFIRMED",
  "polarity_status": "FAILED"
}
```
### Breakout / breakdown attempts
```json
{
  "direction": "DOWNWARD",
  "status": "CONFIRMED",
  "breakout_index": 54,
  "boundary_price": 2218.2,
  "breakout_close": 2214.21,
  "distance_ratio": 0.0017987557479036075,
  "returned_to_range": false,
  "follow_through_count": 5,
  "evidence": [
    {
      "source": "SCHWAGER",
      "code": "SCHWAGER_BEARISH_RANGE_BREAKDOWN_CONTEXT",
      "description": "Closing price moved below the range boundary",
      "contribution": -0.12,
      "metadata": {
        "breakout_index": 54
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
        "distance_ratio": 0.020809665494545063
      }
    }
  ],
  "analysis_start_index": 52,
  "confirmation_method": "CLOSE_COUNT_AND_DISTANCE",
  "confirmation_close_count": 6,
  "extreme_index": 57,
  "extreme_price": 2172.04,
  "maximum_distance_ratio": 0.020809665494545063,
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
SCHWAGER_SUPPORT_ZONE_IDENTIFIED, SCHWAGER_PREVIOUS_EXTREME_ZONE_IDENTIFIED, SCHWAGER_SUPPORT_ZONE_HELD, SCHWAGER_ZONE_TOO_WIDE, SCHWAGER_RESISTANCE_ZONE_IDENTIFIED, SCHWAGER_RESISTANCE_ZONE_HELD, SCHWAGER_TRADING_RANGE_DETECTED, SCHWAGER_PRICE_INSIDE_RANGE, SCHWAGER_RANGE_UPPER_BOUNDARY_HELD, SCHWAGER_RANGE_LOWER_BOUNDARY_HELD, SCHWAGER_RANGE_DURATION_CONFIRMED, SCHWAGER_RANGE_BOUNDARY_ALTERNATION_CONFIRMED, SCHWAGER_BEARISH_RANGE_BREAKDOWN_CONTEXT, SCHWAGER_BREAKOUT_REQUIRES_CONFIRMATION, SCHWAGER_BREAKOUT_FOLLOW_THROUGH_CONFIRMED, SCHWAGER_BREAKOUT_CONFIRMED_BY_CLOSE_COUNT, SCHWAGER_BREAKOUT_CONFIRMED_BY_DISTANCE, SCHWAGER_BREAKOUT_RETEST_FAILED, SCHWAGER_POLARITY_FLIP_FAILED

## 4. BookEvidenceMatrix
### Bullish evidence
Count: 27
### Bearish evidence
Count: 26
### Neutral/range evidence
Count: 308
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
  "total_evidence_count": 361,
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
  "FLAT": 0.528,
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
    "score": 0.528
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
