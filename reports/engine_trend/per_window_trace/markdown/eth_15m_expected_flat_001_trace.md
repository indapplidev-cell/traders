# eth_15m_expected_flat_001 вЂ” Market Evidence Trace

## Window
- Symbol: ETHUSDT
- Interval: 15m
- Period: 2025-09-08T00:00:00+00:00 вЂ” 2025-09-08T23:45:00+00:00
- Reference label: EXPECTED_FLAT
- Selection reason: deterministic expected_flat OHLC rule

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
    "timestamp": "2025-09-08 00:00:00+00:00",
    "candle_index": 0,
    "open": 4306.19,
    "high": 4314.34,
    "low": 4301.03,
    "close": 4304.17,
    "body_pct": 0.1517655897820786,
    "upper_shadow_pct": 0.6123215627348084,
    "lower_shadow_pct": 0.23591284748311292,
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
    "timestamp": "2025-09-08 00:15:00+00:00",
    "candle_index": 1,
    "open": 4304.17,
    "high": 4317.33,
    "low": 4292.5,
    "close": 4316.97,
    "body_pct": 0.5155054369714144,
    "upper_shadow_pct": 0.014498590414807637,
    "lower_shadow_pct": 0.46999597261377796,
    "position_in_window": 0.0105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-09-08 00:45:00+00:00",
    "candle_index": 3,
    "open": 4312.52,
    "high": 4312.92,
    "low": 4295.55,
    "close": 4298.86,
    "body_pct": 0.7864133563615918,
    "upper_shadow_pct": 0.023028209556686167,
    "lower_shadow_pct": 0.19055843408172202,
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
    "timestamp": "2025-09-08 01:00:00+00:00",
    "candle_index": 4,
    "open": 4298.85,
    "high": 4302.25,
    "low": 4292.17,
    "close": 4294.07,
    "body_pct": 0.4742063492064176,
    "upper_shadow_pct": 0.33730158730155363,
    "lower_shadow_pct": 0.18849206349202877,
    "position_in_window": 0.0421,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-09-08 01:15:00+00:00",
    "candle_index": 5,
    "open": 4294.07,
    "high": 4297.86,
    "low": 4285.0,
    "close": 4287.84,
    "body_pct": 0.48444790046654135,
    "upper_shadow_pct": 0.2947122861586361,
    "lower_shadow_pct": 0.22083981337482253,
    "position_in_window": 0.0526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-09-08 01:30:00+00:00",
    "candle_index": 6,
    "open": 4287.84,
    "high": 4298.79,
    "low": 4286.86,
    "close": 4291.63,
    "body_pct": 0.3176865046102155,
    "upper_shadow_pct": 0.600167644593435,
    "lower_shadow_pct": 0.08214585079634945,
    "position_in_window": 0.0632,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2025-09-08 01:45:00+00:00",
    "candle_index": 7,
    "open": 4291.61,
    "high": 4295.02,
    "low": 4288.87,
    "close": 4292.4,
    "body_pct": 0.1284552845528282,
    "upper_shadow_pct": 0.42601626016269395,
    "lower_shadow_pct": 0.4455284552844778,
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
    "timestamp": "2025-09-08 02:00:00+00:00",
    "candle_index": 8,
    "open": 4292.41,
    "high": 4294.66,
    "low": 4284.63,
    "close": 4291.36,
    "body_pct": 0.10468594217350036,
    "upper_shadow_pct": 0.2243270189431762,
    "lower_shadow_pct": 0.6709870388833235,
    "position_in_window": 0.0842,
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
    "timestamp": "2025-09-08 02:15:00+00:00",
    "candle_index": 9,
    "open": 4291.35,
    "high": 4296.0,
    "low": 4279.0,
    "close": 4286.98,
    "body_pct": 0.25705882352945886,
    "upper_shadow_pct": 0.2735294117646845,
    "lower_shadow_pct": 0.46941176470585666,
    "position_in_window": 0.0947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION"
    ]
  },
  {
    "timestamp": "2025-09-08 02:30:00+00:00",
    "candle_index": 10,
    "open": 4286.98,
    "high": 4308.72,
    "low": 4285.69,
    "close": 4303.14,
    "body_pct": 0.7016934433347939,
    "upper_shadow_pct": 0.24229266174553923,
    "lower_shadow_pct": 0.05601389491966682,
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
    "timestamp": "2025-09-08 02:45:00+00:00",
    "candle_index": 11,
    "open": 4303.14,
    "high": 4309.22,
    "low": 4300.0,
    "close": 4309.1,
    "body_pct": 0.6464208242949969,
    "upper_shadow_pct": 0.013015184381766545,
    "lower_shadow_pct": 0.3405639913232365,
    "position_in_window": 0.1158,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-09-08 03:00:00+00:00",
    "candle_index": 12,
    "open": 4309.1,
    "high": 4311.94,
    "low": 4304.03,
    "close": 4307.97,
    "body_pct": 0.14285714285715928,
    "upper_shadow_pct": 0.359039190897508,
    "lower_shadow_pct": 0.4981036662453327,
    "position_in_window": 0.1263,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2025-09-08 03:15:00+00:00",
    "candle_index": 13,
    "open": 4307.97,
    "high": 4311.07,
    "low": 4304.77,
    "close": 4308.97,
    "body_pct": 0.15873015873017707,
    "upper_shadow_pct": 0.3333333333332852,
    "lower_shadow_pct": 0.5079365079365378,
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
    "timestamp": "2025-09-08 03:30:00+00:00",
    "candle_index": 14,
    "open": 4308.98,
    "high": 4330.97,
    "low": 4308.97,
    "close": 4317.79,
    "body_pct": 0.40045454545456366,
    "upper_shadow_pct": 0.5990909090909223,
    "lower_shadow_pct": 0.0004545454545140356,
    "position_in_window": 0.1474,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2025-09-08 04:15:00+00:00",
    "candle_index": 17,
    "open": 4304.81,
    "high": 4307.82,
    "low": 4300.61,
    "close": 4305.95,
    "body_pct": 0.15811373092918338,
    "upper_shadow_pct": 0.25936199722605846,
    "lower_shadow_pct": 0.5825242718447582,
    "position_in_window": 0.1789,
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
    "timestamp": "2025-09-08 05:00:00+00:00",
    "candle_index": 20,
    "open": 4298.15,
    "high": 4302.96,
    "low": 4295.58,
    "close": 4296.49,
    "body_pct": 0.2249322493224702,
    "upper_shadow_pct": 0.6517615176152207,
    "lower_shadow_pct": 0.12330623306230908,
    "position_in_window": 0.2105,
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
    "timestamp": "2025-09-08 05:15:00+00:00",
    "candle_index": 21,
    "open": 4296.48,
    "high": 4304.34,
    "low": 4293.49,
    "close": 4297.04,
    "body_pct": 0.051612903225841604,
    "upper_shadow_pct": 0.6728110599078283,
    "lower_shadow_pct": 0.2755760368663301,
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
    "timestamp": "2025-09-08 05:30:00+00:00",
    "candle_index": 22,
    "open": 4297.04,
    "high": 4297.63,
    "low": 4289.7,
    "close": 4289.86,
    "body_pct": 0.9054224464060564,
    "upper_shadow_pct": 0.07440100882725395,
    "lower_shadow_pct": 0.02017654476668961,
    "position_in_window": 0.2316,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-09-08 05:45:00+00:00",
    "candle_index": 23,
    "open": 4289.85,
    "high": 4299.17,
    "low": 4289.68,
    "close": 4297.05,
    "body_pct": 0.7586933614330857,
    "upper_shadow_pct": 0.22339304531084717,
    "lower_shadow_pct": 0.01791359325606709,
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
    "timestamp": "2025-09-08 06:15:00+00:00",
    "candle_index": 25,
    "open": 4293.85,
    "high": 4302.33,
    "low": 4291.96,
    "close": 4301.98,
    "body_pct": 0.7839922854386967,
    "upper_shadow_pct": 0.0337512054002283,
    "lower_shadow_pct": 0.18225650916107497,
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
    "timestamp": "2025-09-08 06:45:00+00:00",
    "candle_index": 27,
    "open": 4300.13,
    "high": 4300.14,
    "low": 4292.15,
    "close": 4292.21,
    "body_pct": 0.9912390488109372,
    "upper_shadow_pct": 0.0012515644555966725,
    "lower_shadow_pct": 0.007509386733466206,
    "position_in_window": 0.2842,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-09-08 07:00:00+00:00",
    "candle_index": 28,
    "open": 4292.22,
    "high": 4298.71,
    "low": 4290.46,
    "close": 4298.7,
    "body_pct": 0.7854545454544926,
    "upper_shadow_pct": 0.0012121212121476701,
    "lower_shadow_pct": 0.2133333333333598,
    "position_in_window": 0.2947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-09-08 07:30:00+00:00",
    "candle_index": 30,
    "open": 4305.25,
    "high": 4311.67,
    "low": 4290.95,
    "close": 4294.99,
    "body_pct": 0.4951737451737496,
    "upper_shadow_pct": 0.30984555984555956,
    "lower_shadow_pct": 0.19498069498069082,
    "position_in_window": 0.3158,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-09-08 08:00:00+00:00",
    "candle_index": 32,
    "open": 4291.78,
    "high": 4294.96,
    "low": 4288.3,
    "close": 4292.08,
    "body_pct": 0.04504504504507334,
    "upper_shadow_pct": 0.43243243243245827,
    "lower_shadow_pct": 0.5225225225224683,
    "position_in_window": 0.3368,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "DOJI_INDECISION"
    ]
  },
  {
    "timestamp": "2025-09-08 08:15:00+00:00",
    "candle_index": 33,
    "open": 4292.09,
    "high": 4298.9,
    "low": 4289.12,
    "close": 4294.49,
    "body_pct": 0.24539877300610416,
    "upper_shadow_pct": 0.45092024539876985,
    "lower_shadow_pct": 0.30368098159512597,
    "position_in_window": 0.3474,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2025-09-08 08:30:00+00:00",
    "candle_index": 34,
    "open": 4294.48,
    "high": 4304.69,
    "low": 4293.74,
    "close": 4302.0,
    "body_pct": 0.6867579908676312,
    "upper_shadow_pct": 0.24566210045658854,
    "lower_shadow_pct": 0.06757990867578027,
    "position_in_window": 0.3579,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-09-08 08:45:00+00:00",
    "candle_index": 35,
    "open": 4301.99,
    "high": 4304.65,
    "low": 4295.3,
    "close": 4301.79,
    "body_pct": 0.021390374331532597,
    "upper_shadow_pct": 0.2844919786096267,
    "lower_shadow_pct": 0.6941176470588407,
    "position_in_window": 0.3684,
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
    "timestamp": "2025-09-08 09:00:00+00:00",
    "candle_index": 36,
    "open": 4301.79,
    "high": 4317.99,
    "low": 4297.39,
    "close": 4317.37,
    "body_pct": 0.756310679611667,
    "upper_shadow_pct": 0.030097087378636277,
    "lower_shadow_pct": 0.21359223300969674,
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
    "timestamp": "2025-09-08 09:15:00+00:00",
    "candle_index": 37,
    "open": 4317.36,
    "high": 4334.98,
    "low": 4316.99,
    "close": 4320.0,
    "body_pct": 0.14674819344082043,
    "upper_shadow_pct": 0.8326848249027096,
    "lower_shadow_pct": 0.02056698165647,
    "position_in_window": 0.3895,
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
    "timestamp": "2025-09-08 09:45:00+00:00",
    "candle_index": 39,
    "open": 4312.53,
    "high": 4319.31,
    "low": 4309.78,
    "close": 4318.93,
    "body_pct": 0.671563483735583,
    "upper_shadow_pct": 0.039874081846808296,
    "lower_shadow_pct": 0.2885624344176087,
    "position_in_window": 0.4105,
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
  "doji_count": 6,
  "doji_ratio": 0.0625,
  "small_body_count": 27,
  "small_body_ratio": 0.28125,
  "bullish_body_total": 335.6100000000006,
  "bearish_body_total": 335.4900000000025
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
      "previous_timestamp": "2025-09-08 00:00:00+00:00",
      "timestamp": "2025-09-08 00:15:00+00:00",
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
      "previous_timestamp": "2025-09-08 00:00:00+00:00",
      "timestamp": "2025-09-08 00:15:00+00:00",
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
      "previous_timestamp": "2025-09-08 01:45:00+00:00",
      "timestamp": "2025-09-08 02:00:00+00:00",
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
      "previous_timestamp": "2025-09-08 01:45:00+00:00",
      "timestamp": "2025-09-08 02:00:00+00:00",
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
      "previous_timestamp": "2025-09-08 02:15:00+00:00",
      "timestamp": "2025-09-08 02:30:00+00:00",
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
      "previous_timestamp": "2025-09-08 02:15:00+00:00",
      "timestamp": "2025-09-08 02:30:00+00:00",
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
      "previous_timestamp": "2025-09-08 04:15:00+00:00",
      "timestamp": "2025-09-08 04:30:00+00:00",
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
      "previous_timestamp": "2025-09-08 04:15:00+00:00",
      "timestamp": "2025-09-08 04:30:00+00:00",
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
      "previous_timestamp": "2025-09-08 05:15:00+00:00",
      "timestamp": "2025-09-08 05:30:00+00:00",
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
      "previous_timestamp": "2025-09-08 05:15:00+00:00",
      "timestamp": "2025-09-08 05:30:00+00:00",
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
      "previous_timestamp": "2025-09-08 05:30:00+00:00",
      "timestamp": "2025-09-08 05:45:00+00:00",
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
      "previous_timestamp": "2025-09-08 05:30:00+00:00",
      "timestamp": "2025-09-08 05:45:00+00:00",
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
      "previous_timestamp": "2025-09-08 06:00:00+00:00",
      "timestamp": "2025-09-08 06:15:00+00:00",
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
      "previous_timestamp": "2025-09-08 06:00:00+00:00",
      "timestamp": "2025-09-08 06:15:00+00:00",
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
      "previous_timestamp": "2025-09-08 07:15:00+00:00",
      "timestamp": "2025-09-08 07:30:00+00:00",
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
      "previous_timestamp": "2025-09-08 07:15:00+00:00",
      "timestamp": "2025-09-08 07:30:00+00:00",
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
      "previous_timestamp": "2025-09-08 08:45:00+00:00",
      "timestamp": "2025-09-08 09:00:00+00:00",
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
      "previous_timestamp": "2025-09-08 08:45:00+00:00",
      "timestamp": "2025-09-08 09:00:00+00:00",
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
      "previous_timestamp": "2025-09-08 09:15:00+00:00",
      "timestamp": "2025-09-08 09:30:00+00:00",
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
      "previous_timestamp": "2025-09-08 09:15:00+00:00",
      "timestamp": "2025-09-08 09:30:00+00:00",
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
LONG_UPPER_SHADOW_REJECTION, SMALL_BODY_INDECISION, CLOSE_NEAR_LOW, SPINNING_TOP_INDECISION, CLOSE_NEAR_HIGH, STRONG_BEARISH_CANDLE_BODY, LONG_LOWER_SHADOW_REJECTION, STRONG_BULLISH_CANDLE_BODY, DOJI_INDECISION, SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED, CANDLE_PATTERN_NEEDS_TREND_CONTEXT, HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED, BULLISH_ENGULFING_CONTEXT, ENGULFING_WITHOUT_FOLLOW_THROUGH, BEARISH_ENGULFING_CONTEXT, BEARISH_BELT_HOLD_CONTEXT_REQUIRED, BULLISH_BELT_HOLD_CONTEXT_REQUIRED, LONG_LEGGED_DOJI_CONTEXT, RICKSHAW_MAN_DOJI_CONTEXT, INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED, REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH, HANGING_MAN_LIKE_CONTEXT_REQUIRED, DRAGONFLY_DOJI_CONTEXT, TWEEZERS_TOP_CONTEXT_REQUIRED, BEARISH_HARAMI_CONTEXT, TWEEZERS_BOTTOM_CONTEXT_REQUIRED, HARAMI_CROSS_CONTEXT, DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT, DOJI_TOP_CONTEXT_REQUIRED, BULLISH_SEPARATING_LINES_CONTEXT, THREE_ADVANCING_WHITE_SOLDIERS_CONTEXT

## 2. Altunina trend context
### Swing structure
```json
[
  {
    "index": 1,
    "timestamp": "2025-09-08 00:15:00+00:00",
    "price": 4292.5,
    "point_type": "LOW"
  },
  {
    "index": 2,
    "timestamp": "2025-09-08 00:30:00+00:00",
    "price": 4318.74,
    "point_type": "HIGH"
  },
  {
    "index": 5,
    "timestamp": "2025-09-08 01:15:00+00:00",
    "price": 4285.0,
    "point_type": "LOW"
  },
  {
    "index": 6,
    "timestamp": "2025-09-08 01:30:00+00:00",
    "price": 4298.79,
    "point_type": "HIGH"
  },
  {
    "index": 9,
    "timestamp": "2025-09-08 02:15:00+00:00",
    "price": 4279.0,
    "point_type": "LOW"
  },
  {
    "index": 14,
    "timestamp": "2025-09-08 03:30:00+00:00",
    "price": 4330.97,
    "point_type": "HIGH"
  },
  {
    "index": 16,
    "timestamp": "2025-09-08 04:00:00+00:00",
    "price": 4297.17,
    "point_type": "LOW"
  },
  {
    "index": 18,
    "timestamp": "2025-09-08 04:30:00+00:00",
    "price": 4309.96,
    "point_type": "HIGH"
  },
  {
    "index": 24,
    "timestamp": "2025-09-08 06:00:00+00:00",
    "price": 4289.56,
    "point_type": "LOW"
  },
  {
    "index": 26,
    "timestamp": "2025-09-08 06:30:00+00:00",
    "price": 4303.19,
    "point_type": "HIGH"
  },
  {
    "index": 28,
    "timestamp": "2025-09-08 07:00:00+00:00",
    "price": 4290.46,
    "point_type": "LOW"
  },
  {
    "index": 30,
    "timestamp": "2025-09-08 07:30:00+00:00",
    "price": 4311.67,
    "point_type": "HIGH"
  },
  {
    "index": 31,
    "timestamp": "2025-09-08 07:45:00+00:00",
    "price": 4287.68,
    "point_type": "LOW"
  },
  {
    "index": 37,
    "timestamp": "2025-09-08 09:15:00+00:00",
    "price": 4334.98,
    "point_type": "HIGH"
  },
  {
    "index": 38,
    "timestamp": "2025-09-08 09:30:00+00:00",
    "price": 4307.08,
    "point_type": "LOW"
  },
  {
    "index": 43,
    "timestamp": "2025-09-08 10:45:00+00:00",
    "price": 4337.77,
    "point_type": "HIGH"
  },
  {
    "index": 46,
    "timestamp": "2025-09-08 11:30:00+00:00",
    "price": 4300.0,
    "point_type": "LOW"
  },
  {
    "index": 52,
    "timestamp": "2025-09-08 13:00:00+00:00",
    "price": 4362.88,
    "point_type": "HIGH"
  },
  {
    "index": 56,
    "timestamp": "2025-09-08 14:00:00+00:00",
    "price": 4315.0,
    "point_type": "LOW"
  },
  {
    "index": 61,
    "timestamp": "2025-09-08 15:15:00+00:00",
    "price": 4384.06,
    "point_type": "HIGH"
  },
  {
    "index": 68,
    "timestamp": "2025-09-08 17:00:00+00:00",
    "price": 4328.29,
    "point_type": "LOW"
  },
  {
    "index": 69,
    "timestamp": "2025-09-08 17:15:00+00:00",
    "price": 4343.29,
    "point_type": "HIGH"
  },
  {
    "index": 71,
    "timestamp": "2025-09-08 17:45:00+00:00",
    "price": 4300.16,
    "point_type": "LOW"
  },
  {
    "index": 75,
    "timestamp": "2025-09-08 18:45:00+00:00",
    "price": 4336.16,
    "point_type": "HIGH"
  },
  {
    "index": 81,
    "timestamp": "2025-09-08 20:15:00+00:00",
    "price": 4281.8,
    "point_type": "LOW"
  },
  {
    "index": 88,
    "timestamp": "2025-09-08 22:00:00+00:00",
    "price": 4332.5,
    "point_type": "HIGH"
  },
  {
    "index": 93,
    "timestamp": "2025-09-08 23:15:00+00:00",
    "price": 4296.55,
    "point_type": "LOW"
  }
]
```
### Higher highs / lower highs
```json
{
  "raw_swing_count": 38,
  "swing_count": 27,
  "leg_count": 26,
  "structure_direction": "SIDEWAYS_STRUCTURE",
  "total_movement": 898.4699999999984,
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
    "lower_price": 4279.0,
    "upper_price": 4307.59,
    "mid_price": 4296.061428571428,
    "touch_count": 21,
    "source_indexes": [
      1,
      5,
      6,
      9,
      16,
      21,
      23,
      24,
      26,
      28,
      31,
      34,
      38,
      46,
      49,
      71,
      78,
      81,
      82,
      91,
      93
    ],
    "zone_width": 28.590000000000146,
    "zone_width_ratio": 0.00665493277397274,
    "formed_at_index": 93,
    "first_touch_index": 1,
    "last_touch_index": 93,
    "source_point_types": [
      "LOW",
      "LOW",
      "HIGH",
      "LOW",
      "LOW",
      "HIGH",
      "HIGH",
      "LOW",
      "HIGH",
      "LOW",
      "LOW",
      "HIGH",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "HIGH",
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
    "lower_price": 4309.96,
    "upper_price": 4328.29,
    "mid_price": 4317.17,
    "touch_count": 8,
    "source_indexes": [
      2,
      12,
      18,
      30,
      42,
      56,
      68,
      93
    ],
    "zone_width": 18.329999999999927,
    "zone_width_ratio": 0.004245836971905189,
    "formed_at_index": 93,
    "first_touch_index": 2,
    "last_touch_index": 93,
    "source_point_types": [
      "HIGH",
      "HIGH",
      "HIGH",
      "HIGH",
      "LOW",
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
  "is_detected": true,
  "lower_boundary": 4279.0,
  "upper_boundary": 4328.29,
  "midline": 4303.645,
  "width": 49.289999999999964,
  "width_ratio": 0.011453082212868384,
  "touch_count": 29,
  "inside_close_ratio": 0.7741935483870968,
  "formed_at_index": 93,
  "first_touch_index": 1,
  "duration_candles": 93,
  "boundary_alternation_count": 14
}
```
### Range high / low
See trading range object above.
### Price position inside range
```json
{
  "swing_count": 38,
  "zone_count": 5,
  "range_detected": true,
  "range_formed_at_index": 93,
  "range_duration_candles": 93,
  "inside_close_ratio": 0.7741935483870968,
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
  "analysis_start_index": 94,
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
SCHWAGER_SUPPORT_ZONE_IDENTIFIED, SCHWAGER_SUPPORT_ZONE_HELD, SCHWAGER_ZONE_TOO_WIDE, SCHWAGER_RESISTANCE_ZONE_IDENTIFIED, SCHWAGER_RESISTANCE_ZONE_HELD, SCHWAGER_PREVIOUS_EXTREME_ZONE_IDENTIFIED, SCHWAGER_TRADING_RANGE_DETECTED, SCHWAGER_PRICE_INSIDE_RANGE, SCHWAGER_RANGE_UPPER_BOUNDARY_HELD, SCHWAGER_RANGE_LOWER_BOUNDARY_HELD, SCHWAGER_RANGE_DURATION_CONFIRMED, SCHWAGER_RANGE_BOUNDARY_ALTERNATION_CONFIRMED

## 4. BookEvidenceMatrix
### Bullish evidence
Count: 30
### Bearish evidence
Count: 32
### Neutral/range evidence
Count: 311
### Conflict
```json
{
  "agreement_state": "MIXED_LOW_CONFLICT",
  "conflict_level": "LOW",
  "coverage_level": "HIGH",
  "aligned_sources": [
    "ALTUNINA",
    "SCHWAGER"
  ],
  "conflicting_sources": [
    "NISON"
  ],
  "missing_sources": [],
  "confluence_score": 0.6666666666666666,
  "conflict_score": 1.0,
  "coverage_score": 1.0,
  "reason_codes": [
    "MATRIX_HIGH_EVIDENCE_COVERAGE",
    "MATRIX_NEUTRAL_CONFLUENCE",
    "MATRIX_ALTUNINA_SCHWAGER_ALIGNED",
    "MATRIX_DIRECTIONAL_CONFLICT_LOW",
    "MATRIX_MIXED_BOOK_CONTEXT",
    "MATRIX_READY_FOR_REGIME_COMPOSER"
  ]
}
```
### Coverage
```json
{
  "active_source_count": 3,
  "total_evidence_count": 373,
  "dominant_direction": "MIXED",
  "agreement_state": "MIXED_LOW_CONFLICT",
  "conflict_level": "LOW",
  "coverage_level": "HIGH",
  "confluence_score": 0.6666666666666666,
  "conflict_score": 1.0,
  "coverage_score": 1.0,
  "ready_for_composer": true
}
```
### Matrix conclusion
MIXED_LOW_CONFLICT

## 5. Composer decision
### Raw scores
Not exposed by current trace.
### Clamped scores
```json
{
  "UP": 1.0,
  "DOWN": 1.0,
  "FLAT": 0.5548387096774194,
  "UNKNOWN": 0.1
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
    "score": 0.5548387096774194
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
The engine returned UNKNOWN because the composer status was FALLBACK_UNKNOWN and selected UNKNOWN. The strongest visible candidate scores after clamping were UP=1.000 and DOWN=1.000; fallback reason: COMPOSER_CONSERVATIVE_FALLBACK_UNKNOWN. The reference label is EXPECTED_FLAT and remains descriptive, not ground truth.
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
