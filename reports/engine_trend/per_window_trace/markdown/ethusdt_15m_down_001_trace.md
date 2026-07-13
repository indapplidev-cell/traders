# ethusdt_15m_down_001 вЂ” Market Evidence Trace

## Window
- Symbol: ETHUSDT
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
    "open": 2148.25,
    "high": 2148.39,
    "low": 2136.81,
    "close": 2137.48,
    "body_pct": 0.9300518134715069,
    "upper_shadow_pct": 0.012089810017260238,
    "lower_shadow_pct": 0.0578583765112329,
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
    "open": 2137.49,
    "high": 2164.15,
    "low": 2136.85,
    "close": 2161.99,
    "body_pct": 0.8974358974358915,
    "upper_shadow_pct": 0.07912087912088991,
    "lower_shadow_pct": 0.023443223443218624,
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
    "open": 2161.99,
    "high": 2162.21,
    "low": 2145.62,
    "close": 2156.11,
    "body_pct": 0.3544303797468115,
    "upper_shadow_pct": 0.013261000602787988,
    "lower_shadow_pct": 0.6323086196504005,
    "position_in_window": 0.0211,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2026-02-05 01:00:00+00:00",
    "candle_index": 4,
    "open": 2149.78,
    "high": 2169.83,
    "low": 2148.42,
    "close": 2165.91,
    "body_pct": 0.7533862680990081,
    "upper_shadow_pct": 0.18309201307800557,
    "lower_shadow_pct": 0.0635217188229863,
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
    "timestamp": "2026-02-05 01:15:00+00:00",
    "candle_index": 5,
    "open": 2165.91,
    "high": 2169.38,
    "low": 2123.04,
    "close": 2163.53,
    "body_pct": 0.05135951661630658,
    "upper_shadow_pct": 0.07488131204143815,
    "lower_shadow_pct": 0.8737591713422552,
    "position_in_window": 0.0526,
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
    "timestamp": "2026-02-05 01:30:00+00:00",
    "candle_index": 6,
    "open": 2163.53,
    "high": 2173.77,
    "low": 2142.67,
    "close": 2156.62,
    "body_pct": 0.22218649517685946,
    "upper_shadow_pct": 0.32926045016076566,
    "lower_shadow_pct": 0.4485530546623749,
    "position_in_window": 0.0632,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2026-02-05 01:45:00+00:00",
    "candle_index": 7,
    "open": 2156.62,
    "high": 2161.06,
    "low": 2146.34,
    "close": 2148.55,
    "body_pct": 0.5482336956521616,
    "upper_shadow_pct": 0.30163043478261653,
    "lower_shadow_pct": 0.1501358695652219,
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
    "open": 2148.54,
    "high": 2153.44,
    "low": 2125.34,
    "close": 2126.62,
    "body_pct": 0.7800711743772293,
    "upper_shadow_pct": 0.17437722419929205,
    "lower_shadow_pct": 0.04555160142347863,
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
    "open": 2126.63,
    "high": 2139.79,
    "low": 2113.32,
    "close": 2137.73,
    "body_pct": 0.4193426520589344,
    "upper_shadow_pct": 0.07782395164336837,
    "lower_shadow_pct": 0.5028333962976972,
    "position_in_window": 0.0947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-02-05 02:30:00+00:00",
    "candle_index": 10,
    "open": 2137.73,
    "high": 2163.67,
    "low": 2136.07,
    "close": 2158.32,
    "body_pct": 0.746014492753631,
    "upper_shadow_pct": 0.19384057971014226,
    "lower_shadow_pct": 0.06014492753622681,
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
    "timestamp": "2026-02-05 02:45:00+00:00",
    "candle_index": 11,
    "open": 2158.32,
    "high": 2159.62,
    "low": 2120.0,
    "close": 2124.31,
    "body_pct": 0.8584048460373628,
    "upper_shadow_pct": 0.03281171125693414,
    "lower_shadow_pct": 0.10878344270570312,
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
    "open": 2124.3,
    "high": 2136.68,
    "low": 2112.85,
    "close": 2117.85,
    "body_pct": 0.27066722618549277,
    "upper_shadow_pct": 0.5195132186319635,
    "lower_shadow_pct": 0.20981955518254367,
    "position_in_window": 0.1263,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-02-05 03:15:00+00:00",
    "candle_index": 13,
    "open": 2117.83,
    "high": 2127.09,
    "low": 2097.94,
    "close": 2112.92,
    "body_pct": 0.16843910806174406,
    "upper_shadow_pct": 0.3176672384219619,
    "lower_shadow_pct": 0.513893653516294,
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
    "open": 2112.92,
    "high": 2118.4,
    "low": 2104.25,
    "close": 2114.93,
    "body_pct": 0.14204946996464668,
    "upper_shadow_pct": 0.245229681978815,
    "lower_shadow_pct": 0.6127208480565383,
    "position_in_window": 0.1474,
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
    "timestamp": "2026-02-05 04:15:00+00:00",
    "candle_index": 17,
    "open": 2092.29,
    "high": 2107.6,
    "low": 2078.32,
    "close": 2097.72,
    "body_pct": 0.18545081967212718,
    "upper_shadow_pct": 0.3374316939890777,
    "lower_shadow_pct": 0.47711748633879514,
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
    "open": 2097.7,
    "high": 2125.26,
    "low": 2092.43,
    "close": 2122.7,
    "body_pct": 0.7614986293024584,
    "upper_shadow_pct": 0.07797745964058393,
    "lower_shadow_pct": 0.16052391105695768,
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
    "timestamp": "2026-02-05 05:00:00+00:00",
    "candle_index": 20,
    "open": 2104.03,
    "high": 2115.95,
    "low": 2096.06,
    "close": 2108.79,
    "body_pct": 0.23931623931622895,
    "upper_shadow_pct": 0.3599798893916491,
    "lower_shadow_pct": 0.4007038712921219,
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
    "open": 2094.81,
    "high": 2124.55,
    "low": 2084.84,
    "close": 2119.27,
    "body_pct": 0.615965751699824,
    "upper_shadow_pct": 0.1329639889196725,
    "lower_shadow_pct": 0.2510702593805034,
    "position_in_window": 0.2316,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-02-05 06:00:00+00:00",
    "candle_index": 24,
    "open": 2101.42,
    "high": 2107.72,
    "low": 2079.1,
    "close": 2093.24,
    "body_pct": 0.2858141160028065,
    "upper_shadow_pct": 0.22012578616351333,
    "lower_shadow_pct": 0.49406009783368016,
    "position_in_window": 0.2526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION"
    ]
  },
  {
    "timestamp": "2026-02-05 06:15:00+00:00",
    "candle_index": 25,
    "open": 2093.24,
    "high": 2099.0,
    "low": 2076.43,
    "close": 2080.21,
    "body_pct": 0.5773150199379553,
    "upper_shadow_pct": 0.2552060256978368,
    "lower_shadow_pct": 0.16747895436420793,
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
    "open": 2089.37,
    "high": 2098.48,
    "low": 2068.2,
    "close": 2087.57,
    "body_pct": 0.0594451783355256,
    "upper_shadow_pct": 0.30085865257595995,
    "lower_shadow_pct": 0.6396961690885145,
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
    "timestamp": "2026-02-05 07:45:00+00:00",
    "candle_index": 31,
    "open": 2103.3,
    "high": 2106.19,
    "low": 2086.75,
    "close": 2091.4,
    "body_pct": 0.6121399176954763,
    "upper_shadow_pct": 0.14866255144032225,
    "lower_shadow_pct": 0.23919753086420154,
    "position_in_window": 0.3263,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-02-05 08:00:00+00:00",
    "candle_index": 32,
    "open": 2091.5,
    "high": 2105.74,
    "low": 2091.32,
    "close": 2103.4,
    "body_pct": 0.8252427184466301,
    "upper_shadow_pct": 0.16227461858528106,
    "lower_shadow_pct": 0.012482662968088839,
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
    "open": 2112.76,
    "high": 2121.27,
    "low": 2109.01,
    "close": 2115.05,
    "body_pct": 0.18678629690049003,
    "upper_shadow_pct": 0.5073409461663883,
    "lower_shadow_pct": 0.3058727569331217,
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
    "timestamp": "2026-02-05 08:45:00+00:00",
    "candle_index": 35,
    "open": 2115.05,
    "high": 2120.98,
    "low": 2108.99,
    "close": 2111.76,
    "body_pct": 0.27439532944119255,
    "upper_shadow_pct": 0.4945788156797097,
    "lower_shadow_pct": 0.23102585487909774,
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
    "timestamp": "2026-02-05 09:00:00+00:00",
    "candle_index": 36,
    "open": 2111.8,
    "high": 2146.05,
    "low": 2111.16,
    "close": 2139.39,
    "body_pct": 0.7907709945542972,
    "upper_shadow_pct": 0.19088564058470184,
    "lower_shadow_pct": 0.0183433648610009,
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
    "open": 2139.4,
    "high": 2149.75,
    "low": 2134.46,
    "close": 2137.96,
    "body_pct": 0.09417920209287495,
    "upper_shadow_pct": 0.6769130150425071,
    "lower_shadow_pct": 0.22890778286461794,
    "position_in_window": 0.3895,
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
    "timestamp": "2026-02-05 09:30:00+00:00",
    "candle_index": 38,
    "open": 2137.96,
    "high": 2143.3,
    "low": 2128.84,
    "close": 2130.2,
    "body_pct": 0.5366528354080359,
    "upper_shadow_pct": 0.36929460580913775,
    "lower_shadow_pct": 0.09405255878282635,
    "position_in_window": 0.4,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-02-05 10:00:00+00:00",
    "candle_index": 40,
    "open": 2133.46,
    "high": 2136.96,
    "low": 2121.58,
    "close": 2131.49,
    "body_pct": 0.12808842652797403,
    "upper_shadow_pct": 0.22756827048114273,
    "lower_shadow_pct": 0.6443433029908833,
    "position_in_window": 0.4211,
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
    "timestamp": "2026-02-05 10:15:00+00:00",
    "candle_index": 41,
    "open": 2131.5,
    "high": 2140.5,
    "low": 2129.76,
    "close": 2139.01,
    "body_pct": 0.699255121042865,
    "upper_shadow_pct": 0.13873370577279442,
    "lower_shadow_pct": 0.16201117318434052,
    "position_in_window": 0.4316,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  }
]
```
### Doji / spinning top / small body cluster
```json
{
  "doji_count": 10,
  "doji_ratio": 0.10416666666666667,
  "small_body_count": 34,
  "small_body_ratio": 0.3541666666666667,
  "bullish_body_total": 489.9099999999987,
  "bearish_body_total": 811.3999999999996
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
      "previous_timestamp": "2026-02-05 05:00:00+00:00",
      "timestamp": "2026-02-05 05:15:00+00:00",
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
      "previous_timestamp": "2026-02-05 05:00:00+00:00",
      "timestamp": "2026-02-05 05:15:00+00:00",
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
      "previous_timestamp": "2026-02-05 06:45:00+00:00",
      "timestamp": "2026-02-05 07:00:00+00:00",
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
      "previous_timestamp": "2026-02-05 06:45:00+00:00",
      "timestamp": "2026-02-05 07:00:00+00:00",
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
      "previous_timestamp": "2026-02-05 08:30:00+00:00",
      "timestamp": "2026-02-05 08:45:00+00:00",
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
      "previous_timestamp": "2026-02-05 08:30:00+00:00",
      "timestamp": "2026-02-05 08:45:00+00:00",
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
  },
  {
    "source": "NISON",
    "code": "BULLISH_ENGULFING_CONTEXT",
    "description": "Bullish body engulfs the preceding bearish body",
    "contribution": 0.1,
    "metadata": {
      "previous_timestamp": "2026-02-05 16:30:00+00:00",
      "timestamp": "2026-02-05 16:45:00+00:00",
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
      "previous_timestamp": "2026-02-05 16:30:00+00:00",
      "timestamp": "2026-02-05 16:45:00+00:00",
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
      "previous_timestamp": "2026-02-05 18:30:00+00:00",
      "timestamp": "2026-02-05 18:45:00+00:00",
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
      "previous_timestamp": "2026-02-05 18:30:00+00:00",
      "timestamp": "2026-02-05 18:45:00+00:00",
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
STRONG_BEARISH_CANDLE_BODY, CLOSE_NEAR_LOW, STRONG_BULLISH_CANDLE_BODY, CLOSE_NEAR_HIGH, LONG_LOWER_SHADOW_REJECTION, SMALL_BODY_INDECISION, DOJI_INDECISION, HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED, CANDLE_PATTERN_NEEDS_TREND_CONTEXT, SPINNING_TOP_INDECISION, LONG_UPPER_SHADOW_REJECTION, SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED, BULLISH_ENGULFING_CONTEXT, ENGULFING_WITHOUT_FOLLOW_THROUGH, BEARISH_ENGULFING_CONTEXT, BEARISH_BELT_HOLD_CONTEXT_REQUIRED, BULLISH_BELT_HOLD_CONTEXT_REQUIRED, HANGING_MAN_LIKE_CONTEXT_REQUIRED, REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH, DRAGONFLY_DOJI_CONTEXT, INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED, LONG_LEGGED_DOJI_CONTEXT, RICKSHAW_MAN_DOJI_CONTEXT, TWEEZERS_BOTTOM_CONTEXT_REQUIRED, BEARISH_HARAMI_CONTEXT, HARAMI_CROSS_CONTEXT, TWEEZERS_TOP_CONTEXT_REQUIRED, DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT, DOJI_TOP_CONTEXT_REQUIRED, BULLISH_HARAMI_CONTEXT, BULLISH_SEPARATING_LINES_CONTEXT, BEARISH_SEPARATING_LINES_CONTEXT, SMALL_BODY_CLUSTER, LOW_DIRECTIONAL_PROGRESS, BEARISH_BODY_DOMINANCE

## 2. Altunina trend context
### Swing structure
```json
[
  {
    "index": 4,
    "timestamp": "2026-02-05 01:00:00+00:00",
    "price": 2169.83,
    "point_type": "HIGH"
  },
  {
    "index": 5,
    "timestamp": "2026-02-05 01:15:00+00:00",
    "price": 2123.04,
    "point_type": "LOW"
  },
  {
    "index": 6,
    "timestamp": "2026-02-05 01:30:00+00:00",
    "price": 2173.77,
    "point_type": "HIGH"
  },
  {
    "index": 9,
    "timestamp": "2026-02-05 02:15:00+00:00",
    "price": 2113.32,
    "point_type": "LOW"
  },
  {
    "index": 10,
    "timestamp": "2026-02-05 02:30:00+00:00",
    "price": 2163.67,
    "point_type": "HIGH"
  },
  {
    "index": 17,
    "timestamp": "2026-02-05 04:15:00+00:00",
    "price": 2078.32,
    "point_type": "LOW"
  },
  {
    "index": 18,
    "timestamp": "2026-02-05 04:30:00+00:00",
    "price": 2125.26,
    "point_type": "HIGH"
  },
  {
    "index": 21,
    "timestamp": "2026-02-05 05:15:00+00:00",
    "price": 2077.7,
    "point_type": "LOW"
  },
  {
    "index": 22,
    "timestamp": "2026-02-05 05:30:00+00:00",
    "price": 2124.55,
    "point_type": "HIGH"
  },
  {
    "index": 27,
    "timestamp": "2026-02-05 06:45:00+00:00",
    "price": 2068.2,
    "point_type": "LOW"
  },
  {
    "index": 29,
    "timestamp": "2026-02-05 07:15:00+00:00",
    "price": 2124.32,
    "point_type": "HIGH"
  },
  {
    "index": 31,
    "timestamp": "2026-02-05 07:45:00+00:00",
    "price": 2086.75,
    "point_type": "LOW"
  },
  {
    "index": 34,
    "timestamp": "2026-02-05 08:30:00+00:00",
    "price": 2121.27,
    "point_type": "HIGH"
  },
  {
    "index": 35,
    "timestamp": "2026-02-05 08:45:00+00:00",
    "price": 2108.99,
    "point_type": "LOW"
  },
  {
    "index": 37,
    "timestamp": "2026-02-05 09:15:00+00:00",
    "price": 2149.75,
    "point_type": "HIGH"
  },
  {
    "index": 40,
    "timestamp": "2026-02-05 10:00:00+00:00",
    "price": 2121.58,
    "point_type": "LOW"
  },
  {
    "index": 41,
    "timestamp": "2026-02-05 10:15:00+00:00",
    "price": 2140.5,
    "point_type": "HIGH"
  },
  {
    "index": 45,
    "timestamp": "2026-02-05 11:15:00+00:00",
    "price": 2061.96,
    "point_type": "LOW"
  },
  {
    "index": 46,
    "timestamp": "2026-02-05 11:30:00+00:00",
    "price": 2098.13,
    "point_type": "HIGH"
  },
  {
    "index": 51,
    "timestamp": "2026-02-05 12:45:00+00:00",
    "price": 2043.16,
    "point_type": "LOW"
  },
  {
    "index": 52,
    "timestamp": "2026-02-05 13:00:00+00:00",
    "price": 2080.76,
    "point_type": "HIGH"
  },
  {
    "index": 54,
    "timestamp": "2026-02-05 13:30:00+00:00",
    "price": 2048.38,
    "point_type": "LOW"
  },
  {
    "index": 56,
    "timestamp": "2026-02-05 14:00:00+00:00",
    "price": 2085.02,
    "point_type": "HIGH"
  },
  {
    "index": 57,
    "timestamp": "2026-02-05 14:15:00+00:00",
    "price": 2055.08,
    "point_type": "LOW"
  },
  {
    "index": 58,
    "timestamp": "2026-02-05 14:30:00+00:00",
    "price": 2106.51,
    "point_type": "HIGH"
  },
  {
    "index": 62,
    "timestamp": "2026-02-05 15:30:00+00:00",
    "price": 1927.33,
    "point_type": "LOW"
  },
  {
    "index": 63,
    "timestamp": "2026-02-05 15:45:00+00:00",
    "price": 1985.59,
    "point_type": "HIGH"
  },
  {
    "index": 75,
    "timestamp": "2026-02-05 18:45:00+00:00",
    "price": 1913.76,
    "point_type": "LOW"
  },
  {
    "index": 80,
    "timestamp": "2026-02-05 20:00:00+00:00",
    "price": 1943.06,
    "point_type": "HIGH"
  },
  {
    "index": 83,
    "timestamp": "2026-02-05 20:45:00+00:00",
    "price": 1825.06,
    "point_type": "LOW"
  },
  {
    "index": 84,
    "timestamp": "2026-02-05 21:00:00+00:00",
    "price": 1912.35,
    "point_type": "HIGH"
  },
  {
    "index": 89,
    "timestamp": "2026-02-05 22:15:00+00:00",
    "price": 1818.18,
    "point_type": "LOW"
  },
  {
    "index": 90,
    "timestamp": "2026-02-05 22:30:00+00:00",
    "price": 1890.17,
    "point_type": "HIGH"
  },
  {
    "index": 92,
    "timestamp": "2026-02-05 23:00:00+00:00",
    "price": 1862.5,
    "point_type": "LOW"
  }
]
```
### Higher highs / lower highs
```json
{
  "raw_swing_count": 46,
  "swing_count": 34,
  "leg_count": 33,
  "structure_direction": "SIDEWAYS_STRUCTURE",
  "total_movement": 1815.0700000000024,
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
    "lower_price": 2076.43,
    "upper_price": 2080.76,
    "mid_price": 2078.3025,
    "touch_count": 4,
    "source_indexes": [
      17,
      21,
      25,
      52
    ],
    "zone_width": 4.330000000000382,
    "zone_width_ratio": 0.0020834310693464415,
    "formed_at_index": 52,
    "first_touch_index": 17,
    "last_touch_index": 52,
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
    "lower_price": 2121.27,
    "upper_price": 2125.26,
    "mid_price": 2123.336666666667,
    "touch_count": 6,
    "source_indexes": [
      5,
      18,
      22,
      29,
      34,
      40
    ],
    "zone_width": 3.9900000000002365,
    "zone_width_ratio": 0.001879117929171337,
    "formed_at_index": 40,
    "first_touch_index": 5,
    "last_touch_index": 40,
    "source_point_types": [
      "LOW",
      "HIGH",
      "HIGH",
      "HIGH",
      "HIGH",
      "LOW"
    ],
    "original_zone_type": "RESISTANCE",
    "current_zone_type": "RESISTANCE",
    "role_changed_at_index": null,
    "is_significant_single_extreme": false,
    "positional_zone_type": "RESISTANCE"
  },
  "is_detected": true,
  "lower_boundary": 2076.43,
  "upper_boundary": 2125.26,
  "midline": 2100.8450000000003,
  "width": 48.83000000000038,
  "width_ratio": 0.02324302840047713,
  "touch_count": 10,
  "inside_close_ratio": 0.625,
  "formed_at_index": 52,
  "first_touch_index": 5,
  "duration_candles": 48,
  "boundary_alternation_count": 7
}
```
### Range high / low
See trading range object above.
### Price position inside range
```json
{
  "swing_count": 46,
  "zone_count": 14,
  "range_detected": true,
  "range_formed_at_index": 52,
  "range_duration_candles": 48,
  "inside_close_ratio": 0.625,
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
  "breakout_index": 53,
  "boundary_price": 2076.43,
  "breakout_close": 2053.38,
  "distance_ratio": 0.011100783556392331,
  "returned_to_range": false,
  "follow_through_count": 3,
  "evidence": [
    {
      "source": "SCHWAGER",
      "code": "SCHWAGER_BEARISH_RANGE_BREAKDOWN_CONTEXT",
      "description": "Closing price moved below the range boundary",
      "contribution": -0.12,
      "metadata": {
        "breakout_index": 53
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
        "count": 3
      }
    },
    {
      "source": "SCHWAGER",
      "code": "SCHWAGER_BREAKOUT_CONFIRMED_BY_CLOSE_COUNT",
      "description": "Multiple closes beyond the boundary confirm the movement",
      "contribution": 0.0,
      "metadata": {
        "count": 4
      }
    },
    {
      "source": "SCHWAGER",
      "code": "SCHWAGER_BREAKOUT_CONFIRMED_BY_DISTANCE",
      "description": "Movement depth beyond the boundary confirms the movement",
      "contribution": 0.0,
      "metadata": {
        "distance_ratio": 0.01350876263587009
      }
    }
  ],
  "analysis_start_index": 53,
  "confirmation_method": "CLOSE_COUNT_AND_DISTANCE",
  "confirmation_close_count": 4,
  "extreme_index": 54,
  "extreme_price": 2048.38,
  "maximum_distance_ratio": 0.01350876263587009,
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
SCHWAGER_SUPPORT_ZONE_IDENTIFIED, SCHWAGER_PREVIOUS_EXTREME_ZONE_IDENTIFIED, SCHWAGER_RESISTANCE_ZONE_IDENTIFIED, SCHWAGER_RESISTANCE_ZONE_HELD, SCHWAGER_ZONE_TOO_WIDE, SCHWAGER_SUPPORT_ZONE_HELD, SCHWAGER_TRADING_RANGE_DETECTED, SCHWAGER_PRICE_INSIDE_RANGE, SCHWAGER_RANGE_UPPER_BOUNDARY_HELD, SCHWAGER_RANGE_LOWER_BOUNDARY_HELD, SCHWAGER_RANGE_DURATION_CONFIRMED, SCHWAGER_RANGE_BOUNDARY_ALTERNATION_CONFIRMED, SCHWAGER_BEARISH_RANGE_BREAKDOWN_CONTEXT, SCHWAGER_BREAKOUT_REQUIRES_CONFIRMATION, SCHWAGER_BREAKOUT_FOLLOW_THROUGH_CONFIRMED, SCHWAGER_BREAKOUT_CONFIRMED_BY_CLOSE_COUNT, SCHWAGER_BREAKOUT_CONFIRMED_BY_DISTANCE, SCHWAGER_BREAKOUT_RETEST_HELD, SCHWAGER_SUPPORT_TURNED_RESISTANCE, SCHWAGER_POLARITY_FLIP_CONFIRMED

## 4. BookEvidenceMatrix
### Bullish evidence
Count: 26
### Bearish evidence
Count: 24
### Neutral/range evidence
Count: 314
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
  "total_evidence_count": 364,
  "dominant_direction": "BEARISH",
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
  "FLAT": 0.625,
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
    "score": 0.625
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
