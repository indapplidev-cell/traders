# btcusdt_15m_flat_001 вЂ” Market Evidence Trace

## Window
- Symbol: BTCUSDT
- Interval: 15m
- Period: 2025-09-27T00:00:00+00:00 вЂ” 2025-09-27T23:45:00+00:00
- Reference label: EXPECTED_FLAT
- Selection reason: top deterministic FLAT OHLC candidate

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
    "timestamp": "2025-09-27 00:00:00+00:00",
    "candle_index": 0,
    "open": 109643.46,
    "high": 109651.09,
    "low": 109580.0,
    "close": 109594.43,
    "body_pct": 0.6896891264596399,
    "upper_shadow_pct": 0.10732873821902489,
    "lower_shadow_pct": 0.20298213532133527,
    "position_in_window": 0.0,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-09-27 00:15:00+00:00",
    "candle_index": 1,
    "open": 109594.43,
    "high": 109660.88,
    "low": 109499.52,
    "close": 109590.42,
    "body_pct": 0.024851264253809784,
    "upper_shadow_pct": 0.4118120971740915,
    "lower_shadow_pct": 0.5633366385720987,
    "position_in_window": 0.0105,
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
    "timestamp": "2025-09-27 00:30:00+00:00",
    "candle_index": 2,
    "open": 109590.42,
    "high": 109602.65,
    "low": 109472.23,
    "close": 109475.49,
    "body_pct": 0.8812298727188664,
    "upper_shadow_pct": 0.0937739610488889,
    "lower_shadow_pct": 0.024996166232244724,
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
    "timestamp": "2025-09-27 00:45:00+00:00",
    "candle_index": 3,
    "open": 109475.5,
    "high": 109649.29,
    "low": 109475.49,
    "close": 109649.29,
    "body_pct": 0.9999424626007206,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 5.753739927941301e-05,
    "position_in_window": 0.0316,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-09-27 01:00:00+00:00",
    "candle_index": 4,
    "open": 109649.29,
    "high": 109657.45,
    "low": 109508.72,
    "close": 109526.5,
    "body_pct": 0.8255899952934644,
    "upper_shadow_pct": 0.05486451959929884,
    "lower_shadow_pct": 0.11954548510723675,
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
    "timestamp": "2025-09-27 01:30:00+00:00",
    "candle_index": 6,
    "open": 109480.0,
    "high": 109521.78,
    "low": 109330.08,
    "close": 109330.09,
    "body_pct": 0.7820031298904839,
    "upper_shadow_pct": 0.21794470526864618,
    "lower_shadow_pct": 5.216484086990852e-05,
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
    "timestamp": "2025-09-27 01:45:00+00:00",
    "candle_index": 7,
    "open": 109330.09,
    "high": 109431.93,
    "low": 109330.08,
    "close": 109431.92,
    "body_pct": 0.9998036327934263,
    "upper_shadow_pct": 9.81836032868156e-05,
    "lower_shadow_pct": 9.81836032868156e-05,
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
    "timestamp": "2025-09-27 02:00:00+00:00",
    "candle_index": 8,
    "open": 109431.92,
    "high": 109482.64,
    "low": 109381.0,
    "close": 109438.5,
    "body_pct": 0.06473829201103684,
    "upper_shadow_pct": 0.4342778433687492,
    "lower_shadow_pct": 0.5009838646202139,
    "position_in_window": 0.0842,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "DOJI_INDECISION"
    ]
  },
  {
    "timestamp": "2025-09-27 02:15:00+00:00",
    "candle_index": 9,
    "open": 109438.51,
    "high": 109450.88,
    "low": 109324.42,
    "close": 109342.44,
    "body_pct": 0.7596868575042509,
    "upper_shadow_pct": 0.09781749169705257,
    "lower_shadow_pct": 0.14249565079869653,
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
    "timestamp": "2025-09-27 02:30:00+00:00",
    "candle_index": 10,
    "open": 109342.45,
    "high": 109446.17,
    "low": 109340.0,
    "close": 109438.04,
    "body_pct": 0.900348497692362,
    "upper_shadow_pct": 0.07657530375816889,
    "lower_shadow_pct": 0.02307619854946906,
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
    "timestamp": "2025-09-27 03:15:00+00:00",
    "candle_index": 13,
    "open": 109446.45,
    "high": 109572.01,
    "low": 109446.44,
    "close": 109542.05,
    "body_pct": 0.7613283427571201,
    "upper_shadow_pct": 0.2385920203869846,
    "lower_shadow_pct": 7.963685589521314e-05,
    "position_in_window": 0.1368,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-09-27 03:45:00+00:00",
    "candle_index": 15,
    "open": 109635.99,
    "high": 109659.99,
    "low": 109521.62,
    "close": 109553.77,
    "body_pct": 0.5942039459420054,
    "upper_shadow_pct": 0.17344800173446762,
    "lower_shadow_pct": 0.232348052323527,
    "position_in_window": 0.1579,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-09-27 04:00:00+00:00",
    "candle_index": 16,
    "open": 109553.77,
    "high": 109638.96,
    "low": 109527.05,
    "close": 109550.0,
    "body_pct": 0.03368778482712856,
    "upper_shadow_pct": 0.761236708068981,
    "lower_shadow_pct": 0.2050755071038904,
    "position_in_window": 0.1684,
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
    "timestamp": "2025-09-27 04:15:00+00:00",
    "candle_index": 17,
    "open": 109550.01,
    "high": 109694.32,
    "low": 109514.63,
    "close": 109694.32,
    "body_pct": 0.8031053480995624,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.19689465190043767,
    "position_in_window": 0.1789,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-09-27 04:30:00+00:00",
    "candle_index": 18,
    "open": 109694.32,
    "high": 109742.27,
    "low": 109610.54,
    "close": 109610.55,
    "body_pct": 0.6359219615880772,
    "upper_shadow_pct": 0.3640021255598062,
    "lower_shadow_pct": 7.591285211654467e-05,
    "position_in_window": 0.1895,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-09-27 04:45:00+00:00",
    "candle_index": 19,
    "open": 109610.55,
    "high": 109662.2,
    "low": 109603.65,
    "close": 109654.99,
    "body_pct": 0.7590093936806169,
    "upper_shadow_pct": 0.12314261315100755,
    "lower_shadow_pct": 0.11784799316837555,
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
    "timestamp": "2025-09-27 05:15:00+00:00",
    "candle_index": 21,
    "open": 109611.04,
    "high": 109648.22,
    "low": 109601.34,
    "close": 109612.3,
    "body_pct": 0.026877133105998038,
    "upper_shadow_pct": 0.7662116040954497,
    "lower_shadow_pct": 0.20691126279855218,
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
    "timestamp": "2025-09-27 06:30:00+00:00",
    "candle_index": 26,
    "open": 109547.54,
    "high": 109547.54,
    "low": 109484.9,
    "close": 109484.9,
    "body_pct": 1.0,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.0,
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
    "timestamp": "2025-09-27 06:45:00+00:00",
    "candle_index": 27,
    "open": 109484.89,
    "high": 109541.36,
    "low": 109481.44,
    "close": 109541.36,
    "body_pct": 0.9424232309746797,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.05757676902532026,
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
    "timestamp": "2025-09-27 07:00:00+00:00",
    "candle_index": 28,
    "open": 109541.36,
    "high": 109567.86,
    "low": 109527.27,
    "close": 109559.99,
    "body_pct": 0.4589800443460522,
    "upper_shadow_pct": 0.19389012071929096,
    "lower_shadow_pct": 0.3471298349346568,
    "position_in_window": 0.2947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-09-27 07:15:00+00:00",
    "candle_index": 29,
    "open": 109560.0,
    "high": 109570.36,
    "low": 109494.18,
    "close": 109494.19,
    "body_pct": 0.8638750328168959,
    "upper_shadow_pct": 0.135993699133625,
    "lower_shadow_pct": 0.00013126804947902643,
    "position_in_window": 0.3053,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-09-27 07:30:00+00:00",
    "candle_index": 30,
    "open": 109494.19,
    "high": 109494.19,
    "low": 109385.51,
    "close": 109385.52,
    "body_pct": 0.9999079867500064,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 9.201324999367436e-05,
    "position_in_window": 0.3158,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-09-27 07:45:00+00:00",
    "candle_index": 31,
    "open": 109385.52,
    "high": 109411.2,
    "low": 109332.02,
    "close": 109411.2,
    "body_pct": 0.3243243243242647,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.6756756756757353,
    "position_in_window": 0.3263,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-09-27 08:00:00+00:00",
    "candle_index": 32,
    "open": 109411.19,
    "high": 109411.2,
    "low": 109260.76,
    "close": 109287.63,
    "body_pct": 0.821324115926587,
    "upper_shadow_pct": 6.647168302819167e-05,
    "lower_shadow_pct": 0.17860941239038475,
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
    "timestamp": "2025-09-27 08:15:00+00:00",
    "candle_index": 33,
    "open": 109287.64,
    "high": 109357.93,
    "low": 109267.44,
    "close": 109357.91,
    "body_pct": 0.7765498950161488,
    "upper_shadow_pct": 0.0002210188969999412,
    "lower_shadow_pct": 0.22322908608685124,
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
    "timestamp": "2025-09-27 08:30:00+00:00",
    "candle_index": 34,
    "open": 109357.92,
    "high": 109357.92,
    "low": 109300.35,
    "close": 109314.56,
    "body_pct": 0.7531700538475992,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.2468299461524009,
    "position_in_window": 0.3579,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-09-27 08:45:00+00:00",
    "candle_index": 35,
    "open": 109314.56,
    "high": 109330.6,
    "low": 109252.0,
    "close": 109252.01,
    "body_pct": 0.7958015267175353,
    "upper_shadow_pct": 0.20407124681942698,
    "lower_shadow_pct": 0.0001272264630376663,
    "position_in_window": 0.3684,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-09-27 09:00:00+00:00",
    "candle_index": 36,
    "open": 109252.01,
    "high": 109283.87,
    "low": 109161.0,
    "close": 109172.07,
    "body_pct": 0.6506063318954245,
    "upper_shadow_pct": 0.2592984455115308,
    "lower_shadow_pct": 0.09009522259304471,
    "position_in_window": 0.3789,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-09-27 09:15:00+00:00",
    "candle_index": 37,
    "open": 109172.06,
    "high": 109172.07,
    "low": 109064.4,
    "close": 109083.66,
    "body_pct": 0.8210272127796384,
    "upper_shadow_pct": 9.287638162266218e-05,
    "lower_shadow_pct": 0.17887991083873894,
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
    "timestamp": "2025-09-27 09:30:00+00:00",
    "candle_index": 38,
    "open": 109083.66,
    "high": 109285.74,
    "low": 109083.66,
    "close": 109276.27,
    "body_pct": 0.9531373713380785,
    "upper_shadow_pct": 0.04686262866192143,
    "lower_shadow_pct": 0.0,
    "position_in_window": 0.4,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  }
]
```
### Doji / spinning top / small body cluster
```json
{
  "doji_count": 8,
  "doji_ratio": 0.08333333333333333,
  "small_body_count": 19,
  "small_body_ratio": 0.19791666666666666,
  "bullish_body_total": 2510.6300000000338,
  "bearish_body_total": 2518.4800000000105
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
      "previous_timestamp": "2025-09-27 02:00:00+00:00",
      "timestamp": "2025-09-27 02:15:00+00:00",
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
      "previous_timestamp": "2025-09-27 02:00:00+00:00",
      "timestamp": "2025-09-27 02:15:00+00:00",
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
      "previous_timestamp": "2025-09-27 02:45:00+00:00",
      "timestamp": "2025-09-27 03:00:00+00:00",
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
      "previous_timestamp": "2025-09-27 02:45:00+00:00",
      "timestamp": "2025-09-27 03:00:00+00:00",
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
      "previous_timestamp": "2025-09-27 07:00:00+00:00",
      "timestamp": "2025-09-27 07:15:00+00:00",
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
      "previous_timestamp": "2025-09-27 07:00:00+00:00",
      "timestamp": "2025-09-27 07:15:00+00:00",
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
      "previous_timestamp": "2025-09-27 09:15:00+00:00",
      "timestamp": "2025-09-27 09:30:00+00:00",
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
      "previous_timestamp": "2025-09-27 09:15:00+00:00",
      "timestamp": "2025-09-27 09:30:00+00:00",
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
      "previous_timestamp": "2025-09-27 10:00:00+00:00",
      "timestamp": "2025-09-27 10:15:00+00:00",
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
      "previous_timestamp": "2025-09-27 10:00:00+00:00",
      "timestamp": "2025-09-27 10:15:00+00:00",
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
      "previous_timestamp": "2025-09-27 10:15:00+00:00",
      "timestamp": "2025-09-27 10:30:00+00:00",
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
      "previous_timestamp": "2025-09-27 10:15:00+00:00",
      "timestamp": "2025-09-27 10:30:00+00:00",
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
      "previous_timestamp": "2025-09-27 10:45:00+00:00",
      "timestamp": "2025-09-27 11:00:00+00:00",
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
      "previous_timestamp": "2025-09-27 10:45:00+00:00",
      "timestamp": "2025-09-27 11:00:00+00:00",
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
      "previous_timestamp": "2025-09-27 11:15:00+00:00",
      "timestamp": "2025-09-27 11:30:00+00:00",
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
      "previous_timestamp": "2025-09-27 11:15:00+00:00",
      "timestamp": "2025-09-27 11:30:00+00:00",
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
      "previous_timestamp": "2025-09-27 11:45:00+00:00",
      "timestamp": "2025-09-27 12:00:00+00:00",
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
      "previous_timestamp": "2025-09-27 11:45:00+00:00",
      "timestamp": "2025-09-27 12:00:00+00:00",
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
      "previous_timestamp": "2025-09-27 12:15:00+00:00",
      "timestamp": "2025-09-27 12:30:00+00:00",
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
      "previous_timestamp": "2025-09-27 12:15:00+00:00",
      "timestamp": "2025-09-27 12:30:00+00:00",
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
CLOSE_NEAR_LOW, LONG_LOWER_SHADOW_REJECTION, SMALL_BODY_INDECISION, DOJI_INDECISION, STRONG_BEARISH_CANDLE_BODY, STRONG_BULLISH_CANDLE_BODY, CLOSE_NEAR_HIGH, LONG_UPPER_SHADOW_REJECTION, SPINNING_TOP_INDECISION, HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED, CANDLE_PATTERN_NEEDS_TREND_CONTEXT, BEARISH_ENGULFING_CONTEXT, ENGULFING_WITHOUT_FOLLOW_THROUGH, BULLISH_ENGULFING_CONTEXT, PIERCING_BULLISH_CONTEXT, REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH, LONG_LEGGED_DOJI_CONTEXT, RICKSHAW_MAN_DOJI_CONTEXT, BEARISH_BELT_HOLD_CONTEXT_REQUIRED, BULLISH_BELT_HOLD_CONTEXT_REQUIRED, HANGING_MAN_LIKE_CONTEXT_REQUIRED, TWEEZERS_BOTTOM_CONTEXT_REQUIRED, TWEEZERS_TOP_CONTEXT_REQUIRED, DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT, DOJI_TOP_CONTEXT_REQUIRED, BULLISH_SEPARATING_LINES_CONTEXT, BULLISH_HARAMI_CONTEXT, HARAMI_CROSS_CONTEXT, BEARISH_SEPARATING_LINES_CONTEXT, BEARISH_HARAMI_CONTEXT, THREE_BLACK_CROWS_CONTEXT, THREE_ADVANCING_WHITE_SOLDIERS_CONTEXT

## 2. Altunina trend context
### Swing structure
```json
[
  {
    "index": 1,
    "timestamp": "2025-09-27 00:15:00+00:00",
    "price": 109660.88,
    "point_type": "HIGH"
  },
  {
    "index": 2,
    "timestamp": "2025-09-27 00:30:00+00:00",
    "price": 109472.23,
    "point_type": "LOW"
  },
  {
    "index": 4,
    "timestamp": "2025-09-27 01:00:00+00:00",
    "price": 109657.45,
    "point_type": "HIGH"
  },
  {
    "index": 9,
    "timestamp": "2025-09-27 02:15:00+00:00",
    "price": 109324.42,
    "point_type": "LOW"
  },
  {
    "index": 14,
    "timestamp": "2025-09-27 03:30:00+00:00",
    "price": 109743.91,
    "point_type": "HIGH"
  },
  {
    "index": 17,
    "timestamp": "2025-09-27 04:15:00+00:00",
    "price": 109514.63,
    "point_type": "LOW"
  },
  {
    "index": 18,
    "timestamp": "2025-09-27 04:30:00+00:00",
    "price": 109742.27,
    "point_type": "HIGH"
  },
  {
    "index": 20,
    "timestamp": "2025-09-27 05:00:00+00:00",
    "price": 109593.65,
    "point_type": "LOW"
  },
  {
    "index": 22,
    "timestamp": "2025-09-27 05:30:00+00:00",
    "price": 109684.29,
    "point_type": "HIGH"
  },
  {
    "index": 27,
    "timestamp": "2025-09-27 06:45:00+00:00",
    "price": 109481.44,
    "point_type": "LOW"
  },
  {
    "index": 29,
    "timestamp": "2025-09-27 07:15:00+00:00",
    "price": 109570.36,
    "point_type": "HIGH"
  },
  {
    "index": 37,
    "timestamp": "2025-09-27 09:15:00+00:00",
    "price": 109064.4,
    "point_type": "LOW"
  },
  {
    "index": 39,
    "timestamp": "2025-09-27 09:45:00+00:00",
    "price": 109347.59,
    "point_type": "HIGH"
  },
  {
    "index": 41,
    "timestamp": "2025-09-27 10:15:00+00:00",
    "price": 109256.07,
    "point_type": "LOW"
  },
  {
    "index": 42,
    "timestamp": "2025-09-27 10:30:00+00:00",
    "price": 109477.69,
    "point_type": "HIGH"
  },
  {
    "index": 50,
    "timestamp": "2025-09-27 12:30:00+00:00",
    "price": 109227.14,
    "point_type": "LOW"
  },
  {
    "index": 51,
    "timestamp": "2025-09-27 12:45:00+00:00",
    "price": 109477.59,
    "point_type": "HIGH"
  },
  {
    "index": 60,
    "timestamp": "2025-09-27 15:00:00+00:00",
    "price": 109193.0,
    "point_type": "LOW"
  },
  {
    "index": 63,
    "timestamp": "2025-09-27 15:45:00+00:00",
    "price": 109427.4,
    "point_type": "HIGH"
  },
  {
    "index": 65,
    "timestamp": "2025-09-27 16:15:00+00:00",
    "price": 109308.0,
    "point_type": "LOW"
  },
  {
    "index": 66,
    "timestamp": "2025-09-27 16:30:00+00:00",
    "price": 109427.76,
    "point_type": "HIGH"
  },
  {
    "index": 69,
    "timestamp": "2025-09-27 17:15:00+00:00",
    "price": 109243.89,
    "point_type": "LOW"
  },
  {
    "index": 77,
    "timestamp": "2025-09-27 19:15:00+00:00",
    "price": 109440.0,
    "point_type": "HIGH"
  },
  {
    "index": 78,
    "timestamp": "2025-09-27 19:30:00+00:00",
    "price": 109383.48,
    "point_type": "LOW"
  },
  {
    "index": 80,
    "timestamp": "2025-09-27 20:00:00+00:00",
    "price": 109435.0,
    "point_type": "HIGH"
  },
  {
    "index": 81,
    "timestamp": "2025-09-27 20:15:00+00:00",
    "price": 109362.72,
    "point_type": "LOW"
  },
  {
    "index": 86,
    "timestamp": "2025-09-27 21:30:00+00:00",
    "price": 109483.55,
    "point_type": "HIGH"
  },
  {
    "index": 91,
    "timestamp": "2025-09-27 22:45:00+00:00",
    "price": 109504.48,
    "point_type": "LOW"
  },
  {
    "index": 92,
    "timestamp": "2025-09-27 23:00:00+00:00",
    "price": 109640.0,
    "point_type": "HIGH"
  },
  {
    "index": 93,
    "timestamp": "2025-09-27 23:15:00+00:00",
    "price": 109461.53,
    "point_type": "LOW"
  }
]
```
### Higher highs / lower highs
```json
{
  "raw_swing_count": 43,
  "swing_count": 30,
  "leg_count": 29,
  "structure_direction": "SIDEWAYS_STRUCTURE",
  "total_movement": 5491.829999999987,
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
    "lower_price": 109064.4,
    "upper_price": 109684.29,
    "mid_price": 109411.29902439022,
    "touch_count": 41,
    "source_indexes": [
      1,
      2,
      4,
      8,
      9,
      12,
      15,
      17,
      20,
      22,
      27,
      29,
      32,
      37,
      39,
      41,
      42,
      48,
      48,
      50,
      51,
      56,
      58,
      60,
      62,
      63,
      65,
      66,
      69,
      71,
      72,
      75,
      77,
      78,
      80,
      81,
      82,
      86,
      91,
      92,
      93
    ],
    "zone_width": 619.8899999999994,
    "zone_width_ratio": 0.005665685404775352,
    "formed_at_index": 93,
    "first_touch_index": 1,
    "last_touch_index": 93,
    "source_point_types": [
      "HIGH",
      "LOW",
      "HIGH",
      "HIGH",
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
      "HIGH",
      "LOW",
      "HIGH",
      "LOW",
      "HIGH",
      "LOW",
      "HIGH",
      "HIGH",
      "HIGH",
      "LOW",
      "LOW",
      "HIGH",
      "LOW",
      "HIGH",
      "LOW",
      "LOW",
      "HIGH",
      "HIGH",
      "HIGH",
      "LOW",
      "HIGH",
      "LOW",
      "HIGH",
      "HIGH",
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
    "lower_price": 109742.27,
    "upper_price": 109743.91,
    "mid_price": 109743.09,
    "touch_count": 2,
    "source_indexes": [
      14,
      18
    ],
    "zone_width": 1.639999999999418,
    "zone_width_ratio": 1.4943993284674398e-05,
    "formed_at_index": 18,
    "first_touch_index": 14,
    "last_touch_index": 18,
    "source_point_types": [
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
  "lower_boundary": 109064.4,
  "upper_boundary": 109743.91,
  "midline": 109404.155,
  "width": 679.5100000000093,
  "width_ratio": 0.006211007251050103,
  "touch_count": 43,
  "inside_close_ratio": 1.0,
  "formed_at_index": 93,
  "first_touch_index": 1,
  "duration_candles": 93,
  "boundary_alternation_count": 4
}
```
### Range high / low
See trading range object above.
### Price position inside range
```json
{
  "swing_count": 43,
  "zone_count": 2,
  "range_detected": true,
  "range_formed_at_index": 93,
  "range_duration_candles": 93,
  "inside_close_ratio": 1.0,
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
SCHWAGER_SUPPORT_ZONE_IDENTIFIED, SCHWAGER_SUPPORT_ZONE_HELD, SCHWAGER_ZONE_TOO_WIDE, SCHWAGER_RESISTANCE_ZONE_IDENTIFIED, SCHWAGER_RESISTANCE_ZONE_HELD, SCHWAGER_TRADING_RANGE_DETECTED, SCHWAGER_PRICE_INSIDE_RANGE, SCHWAGER_RANGE_UPPER_BOUNDARY_HELD, SCHWAGER_RANGE_LOWER_BOUNDARY_HELD, SCHWAGER_RANGE_DURATION_CONFIRMED, SCHWAGER_RANGE_BOUNDARY_ALTERNATION_CONFIRMED

## 4. BookEvidenceMatrix
### Bullish evidence
Count: 38
### Bearish evidence
Count: 41
### Neutral/range evidence
Count: 349
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
  "total_evidence_count": 428,
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
  "FLAT": 0.6000000000000001,
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
    "score": 0.6000000000000001
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
