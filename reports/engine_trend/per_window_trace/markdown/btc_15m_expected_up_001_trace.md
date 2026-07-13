# btc_15m_expected_up_001 вЂ” Market Evidence Trace

## Window
- Symbol: BTCUSDT
- Interval: 15m
- Period: 2026-02-06T00:00:00+00:00 вЂ” 2026-02-06T23:45:00+00:00
- Reference label: EXPECTED_UP
- Selection reason: deterministic expected_up OHLC rule

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
    "timestamp": "2026-02-06 00:00:00+00:00",
    "candle_index": 0,
    "open": 62909.87,
    "high": 63074.76,
    "low": 60100.0,
    "close": 60255.65,
    "body_pct": 0.8922467694872861,
    "upper_shadow_pct": 0.055429681722222734,
    "lower_shadow_pct": 0.052323548790491115,
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
    "timestamp": "2026-02-06 00:15:00+00:00",
    "candle_index": 1,
    "open": 60255.65,
    "high": 61812.76,
    "low": 60000.0,
    "close": 61373.3,
    "body_pct": 0.6165460402921513,
    "upper_shadow_pct": 0.2424259140757732,
    "lower_shadow_pct": 0.1410280456320755,
    "position_in_window": 0.0105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-02-06 00:30:00+00:00",
    "candle_index": 2,
    "open": 61373.29,
    "high": 63415.44,
    "low": 61331.75,
    "close": 62965.51,
    "body_pct": 0.7641347801256422,
    "upper_shadow_pct": 0.21592943288109065,
    "lower_shadow_pct": 0.01993578699326715,
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
    "timestamp": "2026-02-06 01:15:00+00:00",
    "candle_index": 5,
    "open": 64325.17,
    "high": 64509.6,
    "low": 63999.99,
    "close": 64112.75,
    "body_pct": 0.41682855516963563,
    "upper_shadow_pct": 0.3619042012519379,
    "lower_shadow_pct": 0.22126724357842645,
    "position_in_window": 0.0526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-02-06 01:30:00+00:00",
    "candle_index": 6,
    "open": 64112.75,
    "high": 64799.9,
    "low": 64019.94,
    "close": 64731.0,
    "body_pct": 0.7926688548130683,
    "upper_shadow_pct": 0.08833786348018044,
    "lower_shadow_pct": 0.11899328170675134,
    "position_in_window": 0.0632,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-02-06 01:45:00+00:00",
    "candle_index": 7,
    "open": 64730.99,
    "high": 65760.0,
    "low": 64580.34,
    "close": 65714.96,
    "body_pct": 0.8341132190631245,
    "upper_shadow_pct": 0.03818049268432723,
    "lower_shadow_pct": 0.1277062882525482,
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
    "timestamp": "2026-02-06 02:00:00+00:00",
    "candle_index": 8,
    "open": 65714.96,
    "high": 66010.0,
    "low": 64715.79,
    "close": 64854.12,
    "body_pct": 0.6651470781403361,
    "upper_shadow_pct": 0.22796918583536968,
    "lower_shadow_pct": 0.10688373602429423,
    "position_in_window": 0.0842,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-02-06 02:15:00+00:00",
    "candle_index": 9,
    "open": 64856.88,
    "high": 65130.0,
    "low": 64201.28,
    "close": 64612.73,
    "body_pct": 0.2628887070376366,
    "upper_shadow_pct": 0.2940821776208139,
    "lower_shadow_pct": 0.4430291153415495,
    "position_in_window": 0.0947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION"
    ]
  },
  {
    "timestamp": "2026-02-06 02:30:00+00:00",
    "candle_index": 10,
    "open": 64612.73,
    "high": 65410.44,
    "low": 64450.5,
    "close": 65189.82,
    "body_pct": 0.6011729899785352,
    "upper_shadow_pct": 0.22982686417901335,
    "lower_shadow_pct": 0.1690001458424514,
    "position_in_window": 0.1053,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-02-06 03:00:00+00:00",
    "candle_index": 12,
    "open": 64990.11,
    "high": 65172.13,
    "low": 64368.73,
    "close": 64424.31,
    "body_pct": 0.704256908140412,
    "upper_shadow_pct": 0.2265621110281281,
    "lower_shadow_pct": 0.06918098083145989,
    "position_in_window": 0.1263,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-02-06 03:30:00+00:00",
    "candle_index": 14,
    "open": 64700.0,
    "high": 64937.15,
    "low": 64450.61,
    "close": 64492.28,
    "body_pct": 0.4269330373658914,
    "upper_shadow_pct": 0.48742138364780085,
    "lower_shadow_pct": 0.08564557898630776,
    "position_in_window": 0.1474,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-02-06 04:00:00+00:00",
    "candle_index": 16,
    "open": 64168.33,
    "high": 64569.58,
    "low": 63914.62,
    "close": 64487.44,
    "body_pct": 0.48722059362403963,
    "upper_shadow_pct": 0.12541223891535289,
    "lower_shadow_pct": 0.38736716746060745,
    "position_in_window": 0.1684,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-02-06 04:15:00+00:00",
    "candle_index": 17,
    "open": 64487.45,
    "high": 65000.0,
    "low": 64420.51,
    "close": 64911.47,
    "body_pct": 0.7317123677716709,
    "upper_shadow_pct": 0.15277226526773396,
    "lower_shadow_pct": 0.11551536696059515,
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
    "timestamp": "2026-02-06 04:30:00+00:00",
    "candle_index": 18,
    "open": 64911.46,
    "high": 64931.98,
    "low": 64552.68,
    "close": 64769.63,
    "body_pct": 0.3739256525177977,
    "upper_shadow_pct": 0.054099657263390236,
    "lower_shadow_pct": 0.5719746902188121,
    "position_in_window": 0.1895,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2026-02-06 05:00:00+00:00",
    "candle_index": 20,
    "open": 64905.54,
    "high": 65599.39,
    "low": 64800.01,
    "close": 65526.06,
    "body_pct": 0.7762515949861127,
    "upper_shadow_pct": 0.09173359353499211,
    "lower_shadow_pct": 0.13201481147889513,
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
    "timestamp": "2026-02-06 05:15:00+00:00",
    "candle_index": 21,
    "open": 65526.05,
    "high": 65717.95,
    "low": 65303.03,
    "close": 65466.12,
    "body_pct": 0.14443748192422767,
    "upper_shadow_pct": 0.46249879494841173,
    "lower_shadow_pct": 0.3930637231273606,
    "position_in_window": 0.2211,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2026-02-06 05:30:00+00:00",
    "candle_index": 22,
    "open": 65466.12,
    "high": 65994.3,
    "low": 65385.69,
    "close": 65978.41,
    "body_pct": 0.8417377302377556,
    "upper_shadow_pct": 0.026108673863392655,
    "lower_shadow_pct": 0.13215359589885184,
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
    "timestamp": "2026-02-06 06:00:00+00:00",
    "candle_index": 24,
    "open": 66408.11,
    "high": 66800.0,
    "low": 66161.43,
    "close": 66176.69,
    "body_pct": 0.3624034953098262,
    "upper_shadow_pct": 0.6136993595063894,
    "lower_shadow_pct": 0.02389714518378431,
    "position_in_window": 0.2526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-02-06 06:30:00+00:00",
    "candle_index": 26,
    "open": 65841.59,
    "high": 65850.19,
    "low": 64954.54,
    "close": 65082.62,
    "body_pct": 0.8473957461061716,
    "upper_shadow_pct": 0.009601965053319719,
    "lower_shadow_pct": 0.1430022888405086,
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
    "timestamp": "2026-02-06 06:45:00+00:00",
    "candle_index": 27,
    "open": 65082.62,
    "high": 65248.32,
    "low": 64856.88,
    "close": 64988.26,
    "body_pct": 0.2410586552217454,
    "upper_shadow_pct": 0.4233088085019316,
    "lower_shadow_pct": 0.335632536276323,
    "position_in_window": 0.2842,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2026-02-06 07:00:00+00:00",
    "candle_index": 28,
    "open": 64988.26,
    "high": 65080.0,
    "low": 64654.11,
    "close": 65040.06,
    "body_pct": 0.12162765033223533,
    "upper_shadow_pct": 0.09378008405926973,
    "lower_shadow_pct": 0.7845922656084949,
    "position_in_window": 0.2947,
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
    "timestamp": "2026-02-06 07:15:00+00:00",
    "candle_index": 29,
    "open": 65040.06,
    "high": 65339.2,
    "low": 64802.63,
    "close": 64998.22,
    "body_pct": 0.07797677842592118,
    "upper_shadow_pct": 0.557504146709655,
    "lower_shadow_pct": 0.3645190748644238,
    "position_in_window": 0.3053,
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
    "timestamp": "2026-02-06 08:00:00+00:00",
    "candle_index": 32,
    "open": 64856.0,
    "high": 65205.18,
    "low": 64500.0,
    "close": 65108.9,
    "body_pct": 0.358631838679488,
    "upper_shadow_pct": 0.13653251652060297,
    "lower_shadow_pct": 0.5048356447999091,
    "position_in_window": 0.3368,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-02-06 08:15:00+00:00",
    "candle_index": 33,
    "open": 65108.9,
    "high": 65206.11,
    "low": 64760.0,
    "close": 64821.21,
    "body_pct": 0.6448857905001053,
    "upper_shadow_pct": 0.21790589764855978,
    "lower_shadow_pct": 0.13720831185133497,
    "position_in_window": 0.3474,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2026-02-06 08:30:00+00:00",
    "candle_index": 34,
    "open": 64821.21,
    "high": 64920.0,
    "low": 64516.62,
    "close": 64769.27,
    "body_pct": 0.12876196142595733,
    "upper_shadow_pct": 0.2449055481184033,
    "lower_shadow_pct": 0.6263324904556394,
    "position_in_window": 0.3579,
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
    "timestamp": "2026-02-06 08:45:00+00:00",
    "candle_index": 35,
    "open": 64769.26,
    "high": 65136.0,
    "low": 64713.0,
    "close": 64895.05,
    "body_pct": 0.2973758865248248,
    "upper_shadow_pct": 0.5696217494089766,
    "lower_shadow_pct": 0.13300236406619867,
    "position_in_window": 0.3684,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION"
    ]
  },
  {
    "timestamp": "2026-02-06 09:00:00+00:00",
    "candle_index": 36,
    "open": 64895.04,
    "high": 65210.0,
    "low": 64764.7,
    "close": 65114.44,
    "body_pct": 0.4927015495171795,
    "upper_shadow_pct": 0.2145969009656345,
    "lower_shadow_pct": 0.292701549517186,
    "position_in_window": 0.3789,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-02-06 09:15:00+00:00",
    "candle_index": 37,
    "open": 65114.44,
    "high": 65699.32,
    "low": 65010.87,
    "close": 65631.89,
    "body_pct": 0.7516159488706424,
    "upper_shadow_pct": 0.09794465829037279,
    "lower_shadow_pct": 0.15043939283898475,
    "position_in_window": 0.3895,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2026-02-06 09:45:00+00:00",
    "candle_index": 39,
    "open": 65867.64,
    "high": 66163.0,
    "low": 65614.24,
    "close": 65799.55,
    "body_pct": 0.124079743421527,
    "upper_shadow_pct": 0.5382316495371445,
    "lower_shadow_pct": 0.3376886070413285,
    "position_in_window": 0.4105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2026-02-06 10:00:00+00:00",
    "candle_index": 40,
    "open": 65799.55,
    "high": 65944.35,
    "low": 65550.0,
    "close": 65833.57,
    "body_pct": 0.08626854317231793,
    "upper_shadow_pct": 0.2809179662736077,
    "lower_shadow_pct": 0.6328134905540743,
    "position_in_window": 0.4211,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "DOJI_INDECISION"
    ]
  }
]
```
### Doji / spinning top / small body cluster
```json
{
  "doji_count": 4,
  "doji_ratio": 0.041666666666666664,
  "small_body_count": 27,
  "small_body_ratio": 0.28125,
  "bullish_body_total": 20128.139999999985,
  "bearish_body_total": 12461.120000000032
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
      "previous_timestamp": "2026-02-06 01:15:00+00:00",
      "timestamp": "2026-02-06 01:30:00+00:00",
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
      "previous_timestamp": "2026-02-06 01:15:00+00:00",
      "timestamp": "2026-02-06 01:30:00+00:00",
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
      "previous_timestamp": "2026-02-06 02:15:00+00:00",
      "timestamp": "2026-02-06 02:30:00+00:00",
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
      "previous_timestamp": "2026-02-06 02:15:00+00:00",
      "timestamp": "2026-02-06 02:30:00+00:00",
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
      "previous_timestamp": "2026-02-06 05:15:00+00:00",
      "timestamp": "2026-02-06 05:30:00+00:00",
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
      "previous_timestamp": "2026-02-06 05:15:00+00:00",
      "timestamp": "2026-02-06 05:30:00+00:00",
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
      "previous_timestamp": "2026-02-06 07:15:00+00:00",
      "timestamp": "2026-02-06 07:30:00+00:00",
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
      "previous_timestamp": "2026-02-06 07:15:00+00:00",
      "timestamp": "2026-02-06 07:30:00+00:00",
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
      "previous_timestamp": "2026-02-06 07:30:00+00:00",
      "timestamp": "2026-02-06 07:45:00+00:00",
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
      "previous_timestamp": "2026-02-06 07:30:00+00:00",
      "timestamp": "2026-02-06 07:45:00+00:00",
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
      "previous_timestamp": "2026-02-06 08:00:00+00:00",
      "timestamp": "2026-02-06 08:15:00+00:00",
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
      "previous_timestamp": "2026-02-06 08:00:00+00:00",
      "timestamp": "2026-02-06 08:15:00+00:00",
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
      "previous_timestamp": "2026-02-06 08:30:00+00:00",
      "timestamp": "2026-02-06 08:45:00+00:00",
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
      "previous_timestamp": "2026-02-06 08:30:00+00:00",
      "timestamp": "2026-02-06 08:45:00+00:00",
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
      "previous_timestamp": "2026-02-06 10:30:00+00:00",
      "timestamp": "2026-02-06 10:45:00+00:00",
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
      "previous_timestamp": "2026-02-06 10:30:00+00:00",
      "timestamp": "2026-02-06 10:45:00+00:00",
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
      "previous_timestamp": "2026-02-06 12:30:00+00:00",
      "timestamp": "2026-02-06 12:45:00+00:00",
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
      "previous_timestamp": "2026-02-06 12:30:00+00:00",
      "timestamp": "2026-02-06 12:45:00+00:00",
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
      "previous_timestamp": "2026-02-06 13:15:00+00:00",
      "timestamp": "2026-02-06 13:30:00+00:00",
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
      "previous_timestamp": "2026-02-06 13:15:00+00:00",
      "timestamp": "2026-02-06 13:30:00+00:00",
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
STRONG_BEARISH_CANDLE_BODY, CLOSE_NEAR_LOW, CLOSE_NEAR_HIGH, STRONG_BULLISH_CANDLE_BODY, SMALL_BODY_INDECISION, LONG_LOWER_SHADOW_REJECTION, SPINNING_TOP_INDECISION, LONG_UPPER_SHADOW_REJECTION, HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED, CANDLE_PATTERN_NEEDS_TREND_CONTEXT, DOJI_INDECISION, SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED, BULLISH_ENGULFING_CONTEXT, ENGULFING_WITHOUT_FOLLOW_THROUGH, BEARISH_ENGULFING_CONTEXT, BEARISH_BELT_HOLD_CONTEXT_REQUIRED, BULLISH_BELT_HOLD_CONTEXT_REQUIRED, HANGING_MAN_LIKE_CONTEXT_REQUIRED, REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH, LONG_LEGGED_DOJI_CONTEXT, RICKSHAW_MAN_DOJI_CONTEXT, INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED, TWEEZERS_BOTTOM_CONTEXT_REQUIRED, TWEEZERS_TOP_CONTEXT_REQUIRED, BEARISH_HARAMI_CONTEXT, BULLISH_HARAMI_CONTEXT, BULLISH_BODY_DOMINANCE

## 2. Altunina trend context
### Swing structure
```json
[
  {
    "index": 1,
    "timestamp": "2026-02-06 00:15:00+00:00",
    "price": 60000.0,
    "point_type": "LOW"
  },
  {
    "index": 8,
    "timestamp": "2026-02-06 02:00:00+00:00",
    "price": 66010.0,
    "point_type": "HIGH"
  },
  {
    "index": 9,
    "timestamp": "2026-02-06 02:15:00+00:00",
    "price": 64201.28,
    "point_type": "LOW"
  },
  {
    "index": 10,
    "timestamp": "2026-02-06 02:30:00+00:00",
    "price": 65410.44,
    "point_type": "HIGH"
  },
  {
    "index": 12,
    "timestamp": "2026-02-06 03:00:00+00:00",
    "price": 64368.73,
    "point_type": "LOW"
  },
  {
    "index": 14,
    "timestamp": "2026-02-06 03:30:00+00:00",
    "price": 64937.15,
    "point_type": "HIGH"
  },
  {
    "index": 15,
    "timestamp": "2026-02-06 03:45:00+00:00",
    "price": 63770.17,
    "point_type": "LOW"
  },
  {
    "index": 23,
    "timestamp": "2026-02-06 05:45:00+00:00",
    "price": 66826.5,
    "point_type": "HIGH"
  },
  {
    "index": 28,
    "timestamp": "2026-02-06 07:00:00+00:00",
    "price": 64654.11,
    "point_type": "LOW"
  },
  {
    "index": 30,
    "timestamp": "2026-02-06 07:30:00+00:00",
    "price": 65543.79,
    "point_type": "HIGH"
  },
  {
    "index": 32,
    "timestamp": "2026-02-06 08:00:00+00:00",
    "price": 64500.0,
    "point_type": "LOW"
  },
  {
    "index": 33,
    "timestamp": "2026-02-06 08:15:00+00:00",
    "price": 65206.11,
    "point_type": "HIGH"
  },
  {
    "index": 34,
    "timestamp": "2026-02-06 08:30:00+00:00",
    "price": 64516.62,
    "point_type": "LOW"
  },
  {
    "index": 39,
    "timestamp": "2026-02-06 09:45:00+00:00",
    "price": 66163.0,
    "point_type": "HIGH"
  },
  {
    "index": 40,
    "timestamp": "2026-02-06 10:00:00+00:00",
    "price": 65550.0,
    "point_type": "LOW"
  },
  {
    "index": 41,
    "timestamp": "2026-02-06 10:15:00+00:00",
    "price": 66220.0,
    "point_type": "HIGH"
  },
  {
    "index": 44,
    "timestamp": "2026-02-06 11:00:00+00:00",
    "price": 65772.17,
    "point_type": "LOW"
  },
  {
    "index": 47,
    "timestamp": "2026-02-06 11:45:00+00:00",
    "price": 66755.13,
    "point_type": "HIGH"
  },
  {
    "index": 50,
    "timestamp": "2026-02-06 12:30:00+00:00",
    "price": 66114.49,
    "point_type": "LOW"
  },
  {
    "index": 53,
    "timestamp": "2026-02-06 13:15:00+00:00",
    "price": 67499.97,
    "point_type": "HIGH"
  },
  {
    "index": 54,
    "timestamp": "2026-02-06 13:30:00+00:00",
    "price": 66804.12,
    "point_type": "LOW"
  },
  {
    "index": 55,
    "timestamp": "2026-02-06 13:45:00+00:00",
    "price": 67690.7,
    "point_type": "HIGH"
  },
  {
    "index": 57,
    "timestamp": "2026-02-06 14:15:00+00:00",
    "price": 66629.36,
    "point_type": "LOW"
  },
  {
    "index": 59,
    "timestamp": "2026-02-06 14:45:00+00:00",
    "price": 68647.45,
    "point_type": "HIGH"
  },
  {
    "index": 60,
    "timestamp": "2026-02-06 15:00:00+00:00",
    "price": 67772.0,
    "point_type": "LOW"
  },
  {
    "index": 70,
    "timestamp": "2026-02-06 17:30:00+00:00",
    "price": 71500.0,
    "point_type": "HIGH"
  },
  {
    "index": 73,
    "timestamp": "2026-02-06 18:15:00+00:00",
    "price": 69340.91,
    "point_type": "LOW"
  },
  {
    "index": 74,
    "timestamp": "2026-02-06 18:30:00+00:00",
    "price": 70295.97,
    "point_type": "HIGH"
  },
  {
    "index": 77,
    "timestamp": "2026-02-06 19:15:00+00:00",
    "price": 69662.22,
    "point_type": "LOW"
  },
  {
    "index": 82,
    "timestamp": "2026-02-06 20:30:00+00:00",
    "price": 70996.77,
    "point_type": "HIGH"
  },
  {
    "index": 84,
    "timestamp": "2026-02-06 21:00:00+00:00",
    "price": 69837.35,
    "point_type": "LOW"
  },
  {
    "index": 92,
    "timestamp": "2026-02-06 23:00:00+00:00",
    "price": 71751.33,
    "point_type": "HIGH"
  },
  {
    "index": 93,
    "timestamp": "2026-02-06 23:15:00+00:00",
    "price": 70541.3,
    "point_type": "LOW"
  }
]
```
### Higher highs / lower highs
```json
{
  "raw_swing_count": 38,
  "swing_count": 33,
  "leg_count": 32,
  "structure_direction": "SIDEWAYS_STRUCTURE",
  "total_movement": 45380.25999999998,
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
    "lower_price": 66629.36,
    "upper_price": 66826.5,
    "mid_price": 66753.7775,
    "touch_count": 4,
    "source_indexes": [
      23,
      47,
      54,
      57
    ],
    "zone_width": 197.13999999999942,
    "zone_width_ratio": 0.0029532411105873285,
    "formed_at_index": 57,
    "first_touch_index": 23,
    "last_touch_index": 57,
    "source_point_types": [
      "HIGH",
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
    "lower_price": 67499.97,
    "upper_price": 67772.0,
    "mid_price": 67654.22333333333,
    "touch_count": 3,
    "source_indexes": [
      53,
      55,
      60
    ],
    "zone_width": 272.02999999999884,
    "zone_width_ratio": 0.004020887190733136,
    "formed_at_index": 60,
    "first_touch_index": 53,
    "last_touch_index": 60,
    "source_point_types": [
      "HIGH",
      "HIGH",
      "LOW"
    ],
    "original_zone_type": "RESISTANCE",
    "current_zone_type": "RESISTANCE",
    "role_changed_at_index": null,
    "is_significant_single_extreme": false,
    "positional_zone_type": "SUPPORT"
  },
  "is_detected": false,
  "lower_boundary": 66629.36,
  "upper_boundary": 67772.0,
  "midline": 67200.68,
  "width": 1142.6399999999994,
  "width_ratio": 0.017003399370363506,
  "touch_count": 7,
  "inside_close_ratio": 0.18421052631578946,
  "formed_at_index": 60,
  "first_touch_index": 23,
  "duration_candles": 38,
  "boundary_alternation_count": 5
}
```
### Range high / low
See trading range object above.
### Price position inside range
```json
{
  "swing_count": 38,
  "zone_count": 12,
  "range_detected": false,
  "range_formed_at_index": 60,
  "range_duration_candles": 38,
  "inside_close_ratio": 0.18421052631578946,
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
SCHWAGER_SUPPORT_ZONE_IDENTIFIED, SCHWAGER_PREVIOUS_EXTREME_ZONE_IDENTIFIED, SCHWAGER_SUPPORT_ZONE_HELD, SCHWAGER_RESISTANCE_ZONE_IDENTIFIED, SCHWAGER_RESISTANCE_ZONE_HELD, SCHWAGER_ZONE_TOO_WIDE, SCHWAGER_RANGE_NOT_CONFIRMED

## 4. BookEvidenceMatrix
### Bullish evidence
Count: 36
### Bearish evidence
Count: 22
### Neutral/range evidence
Count: 272
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
  "total_evidence_count": 330,
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
