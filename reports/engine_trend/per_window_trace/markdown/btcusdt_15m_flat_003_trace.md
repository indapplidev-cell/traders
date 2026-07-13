# btcusdt_15m_flat_003 вЂ” Market Evidence Trace

## Window
- Symbol: BTCUSDT
- Interval: 15m
- Period: 2025-04-26T00:00:00+00:00 вЂ” 2025-04-26T23:45:00+00:00
- Reference label: EXPECTED_FLAT
- Selection reason: ranked deterministic FLAT OHLC candidate

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
    "timestamp": "2025-04-26 00:00:00+00:00",
    "candle_index": 0,
    "open": 94638.68,
    "high": 94800.0,
    "low": 94627.15,
    "close": 94795.91,
    "body_pct": 0.9096326294475278,
    "upper_shadow_pct": 0.023662134798937633,
    "lower_shadow_pct": 0.06670523575353456,
    "position_in_window": 0.0,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-04-26 00:30:00+00:00",
    "candle_index": 2,
    "open": 94705.99,
    "high": 94728.77,
    "low": 94539.5,
    "close": 94542.0,
    "body_pct": 0.866434194536914,
    "upper_shadow_pct": 0.12035716172662517,
    "lower_shadow_pct": 0.013208643736460857,
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
    "timestamp": "2025-04-26 00:45:00+00:00",
    "candle_index": 3,
    "open": 94541.8,
    "high": 94935.97,
    "low": 94527.84,
    "close": 94880.69,
    "body_pct": 0.8303481733761192,
    "upper_shadow_pct": 0.1354470389336687,
    "lower_shadow_pct": 0.03420478769021205,
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
    "timestamp": "2025-04-26 01:00:00+00:00",
    "candle_index": 4,
    "open": 94880.68,
    "high": 94956.54,
    "low": 94751.12,
    "close": 94882.6,
    "body_pct": 0.009346704313177013,
    "upper_shadow_pct": 0.35994547755811707,
    "lower_shadow_pct": 0.6307078181287059,
    "position_in_window": 0.0421,
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
    "timestamp": "2025-04-26 01:30:00+00:00",
    "candle_index": 6,
    "open": 95004.01,
    "high": 95199.0,
    "low": 95004.0,
    "close": 95043.46,
    "body_pct": 0.202307692307752,
    "upper_shadow_pct": 0.7976410256409928,
    "lower_shadow_pct": 5.1282051255186206e-05,
    "position_in_window": 0.0632,
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
    "timestamp": "2025-04-26 01:45:00+00:00",
    "candle_index": 7,
    "open": 95043.45,
    "high": 95119.1,
    "low": 94990.8,
    "close": 95013.14,
    "body_pct": 0.23624318004674189,
    "upper_shadow_pct": 0.589633671083453,
    "lower_shadow_pct": 0.17412314886980515,
    "position_in_window": 0.0737,
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
    "timestamp": "2025-04-26 02:00:00+00:00",
    "candle_index": 8,
    "open": 95013.15,
    "high": 95013.15,
    "low": 94770.74,
    "close": 94772.64,
    "body_pct": 0.9921620395198455,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.007837960480154556,
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
    "timestamp": "2025-04-26 02:15:00+00:00",
    "candle_index": 9,
    "open": 94772.63,
    "high": 94900.6,
    "low": 94699.11,
    "close": 94881.31,
    "body_pct": 0.5393816070275954,
    "upper_shadow_pct": 0.09573676112962255,
    "lower_shadow_pct": 0.3648816318427821,
    "position_in_window": 0.0947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-04-26 02:30:00+00:00",
    "candle_index": 10,
    "open": 94881.31,
    "high": 95157.73,
    "low": 94839.85,
    "close": 95086.95,
    "body_pct": 0.6469107839436449,
    "upper_shadow_pct": 0.22266263998993657,
    "lower_shadow_pct": 0.13042657606641858,
    "position_in_window": 0.1053,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-04-26 03:00:00+00:00",
    "candle_index": 12,
    "open": 95000.0,
    "high": 95059.67,
    "low": 94913.04,
    "close": 94996.6,
    "body_pct": 0.023187615085549146,
    "upper_shadow_pct": 0.40694264475207226,
    "lower_shadow_pct": 0.5698697401623786,
    "position_in_window": 0.1263,
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
    "timestamp": "2025-04-26 03:15:00+00:00",
    "candle_index": 13,
    "open": 94996.59,
    "high": 94996.6,
    "low": 94758.43,
    "close": 94793.34,
    "body_pct": 0.8533820380400096,
    "upper_shadow_pct": 4.198681617883314e-05,
    "lower_shadow_pct": 0.14657597514381163,
    "position_in_window": 0.1368,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-04-26 03:30:00+00:00",
    "candle_index": 14,
    "open": 94793.34,
    "high": 94793.35,
    "low": 94739.13,
    "close": 94739.15,
    "body_pct": 0.9994466986352114,
    "upper_shadow_pct": 0.00018443378844177445,
    "lower_shadow_pct": 0.00036886757634677596,
    "position_in_window": 0.1474,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-04-26 03:45:00+00:00",
    "candle_index": 15,
    "open": 94739.14,
    "high": 94798.43,
    "low": 94710.0,
    "close": 94739.99,
    "body_pct": 0.009612122582900463,
    "upper_shadow_pct": 0.6608616985185163,
    "lower_shadow_pct": 0.32952617889858327,
    "position_in_window": 0.1579,
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
    "timestamp": "2025-04-26 04:00:00+00:00",
    "candle_index": 16,
    "open": 94739.99,
    "high": 94830.93,
    "low": 94700.0,
    "close": 94730.32,
    "body_pct": 0.07385625906972253,
    "upper_shadow_pct": 0.6945696173527276,
    "lower_shadow_pct": 0.23157412357754986,
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
    "timestamp": "2025-04-26 04:15:00+00:00",
    "candle_index": 17,
    "open": 94730.32,
    "high": 94739.13,
    "low": 94613.91,
    "close": 94625.54,
    "body_pct": 0.8367672895704553,
    "upper_shadow_pct": 0.07035617313526266,
    "lower_shadow_pct": 0.09287653729428204,
    "position_in_window": 0.1789,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-04-26 04:30:00+00:00",
    "candle_index": 18,
    "open": 94625.54,
    "high": 94683.83,
    "low": 94545.24,
    "close": 94682.38,
    "body_pct": 0.4101306010535572,
    "upper_shadow_pct": 0.010462515332975873,
    "lower_shadow_pct": 0.5794068836134669,
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
    "timestamp": "2025-04-26 04:45:00+00:00",
    "candle_index": 19,
    "open": 94682.39,
    "high": 94700.0,
    "low": 94533.92,
    "close": 94536.99,
    "body_pct": 0.8754816955683565,
    "upper_shadow_pct": 0.10603323699422204,
    "lower_shadow_pct": 0.01848506743742144,
    "position_in_window": 0.2,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-04-26 05:00:00+00:00",
    "candle_index": 20,
    "open": 94537.0,
    "high": 94650.47,
    "low": 94505.07,
    "close": 94505.08,
    "body_pct": 0.21953232462172992,
    "upper_shadow_pct": 0.7803988995873845,
    "lower_shadow_pct": 6.877579088556885e-05,
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
    "timestamp": "2025-04-26 05:15:00+00:00",
    "candle_index": 21,
    "open": 94505.08,
    "high": 94587.99,
    "low": 94380.72,
    "close": 94550.35,
    "body_pct": 0.21841076856275962,
    "upper_shadow_pct": 0.1815988806870202,
    "lower_shadow_pct": 0.5999903507502202,
    "position_in_window": 0.2211,
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
    "timestamp": "2025-04-26 05:45:00+00:00",
    "candle_index": 23,
    "open": 94632.16,
    "high": 94706.6,
    "low": 94599.63,
    "close": 94626.47,
    "body_pct": 0.05319248387400455,
    "upper_shadow_pct": 0.6958960456202815,
    "lower_shadow_pct": 0.2509114705057139,
    "position_in_window": 0.2421,
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
    "timestamp": "2025-04-26 06:00:00+00:00",
    "candle_index": 24,
    "open": 94626.47,
    "high": 94699.0,
    "low": 94583.91,
    "close": 94698.99,
    "body_pct": 0.6301155617343495,
    "upper_shadow_pct": 8.688852198072477e-05,
    "lower_shadow_pct": 0.36979754974366985,
    "position_in_window": 0.2526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-04-26 06:15:00+00:00",
    "candle_index": 25,
    "open": 94699.0,
    "high": 94699.0,
    "low": 94602.34,
    "close": 94608.71,
    "body_pct": 0.9340989033725464,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.0659010966274536,
    "position_in_window": 0.2632,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-04-26 06:30:00+00:00",
    "candle_index": 26,
    "open": 94608.71,
    "high": 94692.0,
    "low": 94608.71,
    "close": 94635.32,
    "body_pct": 0.31948613278908183,
    "upper_shadow_pct": 0.6805138672109181,
    "lower_shadow_pct": 0.0,
    "position_in_window": 0.2737,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2025-04-26 06:45:00+00:00",
    "candle_index": 27,
    "open": 94635.32,
    "high": 94743.88,
    "low": 94630.41,
    "close": 94630.42,
    "body_pct": 0.0431832202344997,
    "upper_shadow_pct": 0.9567286507446598,
    "lower_shadow_pct": 8.812902084040898e-05,
    "position_in_window": 0.2842,
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
    "timestamp": "2025-04-26 07:00:00+00:00",
    "candle_index": 28,
    "open": 94630.42,
    "high": 94735.39,
    "low": 94630.41,
    "close": 94735.39,
    "body_pct": 0.9999047437607662,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 9.525623923377499e-05,
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
    "timestamp": "2025-04-26 07:30:00+00:00",
    "candle_index": 30,
    "open": 94702.06,
    "high": 94794.17,
    "low": 94650.0,
    "close": 94774.2,
    "body_pct": 0.5003814940695033,
    "upper_shadow_pct": 0.13851702850802114,
    "lower_shadow_pct": 0.36110147742247556,
    "position_in_window": 0.3158,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-04-26 07:45:00+00:00",
    "candle_index": 31,
    "open": 94774.2,
    "high": 94774.21,
    "low": 94570.31,
    "close": 94570.31,
    "body_pct": 0.9999509563511069,
    "upper_shadow_pct": 4.904364889314761e-05,
    "lower_shadow_pct": 0.0,
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
    "timestamp": "2025-04-26 08:00:00+00:00",
    "candle_index": 32,
    "open": 94570.31,
    "high": 94627.36,
    "low": 94408.81,
    "close": 94596.0,
    "body_pct": 0.11754747197438566,
    "upper_shadow_pct": 0.14349119194692364,
    "lower_shadow_pct": 0.7389613360786906,
    "position_in_window": 0.3368,
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
    "timestamp": "2025-04-26 08:30:00+00:00",
    "candle_index": 34,
    "open": 94660.0,
    "high": 94687.31,
    "low": 94350.0,
    "close": 94387.25,
    "body_pct": 0.8086033618926266,
    "upper_shadow_pct": 0.08096409830718881,
    "lower_shadow_pct": 0.11043253980018457,
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
    "timestamp": "2025-04-26 09:00:00+00:00",
    "candle_index": 36,
    "open": 94318.03,
    "high": 94359.24,
    "low": 94217.32,
    "close": 94355.96,
    "body_pct": 0.26726324689971837,
    "upper_shadow_pct": 0.02311161217586581,
    "lower_shadow_pct": 0.7096251409244158,
    "position_in_window": 0.3789,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_LOWER_SHADOW_REJECTION",
      "SMALL_BODY_INDECISION",
      "CLOSE_NEAR_HIGH",
      "HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED",
      "CANDLE_PATTERN_NEEDS_TREND_CONTEXT"
    ]
  }
]
```
### Doji / spinning top / small body cluster
```json
{
  "doji_count": 12,
  "doji_ratio": 0.125,
  "small_body_count": 27,
  "small_body_ratio": 0.28125,
  "bullish_body_total": 3978.3100000000413,
  "bearish_body_total": 3988.880000000019
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
      "previous_timestamp": "2025-04-26 00:30:00+00:00",
      "timestamp": "2025-04-26 00:45:00+00:00",
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
      "previous_timestamp": "2025-04-26 00:30:00+00:00",
      "timestamp": "2025-04-26 00:45:00+00:00",
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
      "previous_timestamp": "2025-04-26 03:45:00+00:00",
      "timestamp": "2025-04-26 04:00:00+00:00",
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
      "previous_timestamp": "2025-04-26 03:45:00+00:00",
      "timestamp": "2025-04-26 04:00:00+00:00",
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
      "previous_timestamp": "2025-04-26 04:30:00+00:00",
      "timestamp": "2025-04-26 04:45:00+00:00",
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
      "previous_timestamp": "2025-04-26 04:30:00+00:00",
      "timestamp": "2025-04-26 04:45:00+00:00",
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
      "previous_timestamp": "2025-04-26 05:00:00+00:00",
      "timestamp": "2025-04-26 05:15:00+00:00",
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
      "previous_timestamp": "2025-04-26 05:00:00+00:00",
      "timestamp": "2025-04-26 05:15:00+00:00",
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
      "previous_timestamp": "2025-04-26 05:45:00+00:00",
      "timestamp": "2025-04-26 06:00:00+00:00",
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
      "previous_timestamp": "2025-04-26 05:45:00+00:00",
      "timestamp": "2025-04-26 06:00:00+00:00",
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
      "previous_timestamp": "2025-04-26 06:00:00+00:00",
      "timestamp": "2025-04-26 06:15:00+00:00",
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
      "previous_timestamp": "2025-04-26 06:00:00+00:00",
      "timestamp": "2025-04-26 06:15:00+00:00",
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
      "previous_timestamp": "2025-04-26 06:45:00+00:00",
      "timestamp": "2025-04-26 07:00:00+00:00",
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
      "previous_timestamp": "2025-04-26 06:45:00+00:00",
      "timestamp": "2025-04-26 07:00:00+00:00",
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
      "previous_timestamp": "2025-04-26 07:15:00+00:00",
      "timestamp": "2025-04-26 07:30:00+00:00",
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
      "previous_timestamp": "2025-04-26 07:15:00+00:00",
      "timestamp": "2025-04-26 07:30:00+00:00",
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
      "previous_timestamp": "2025-04-26 07:30:00+00:00",
      "timestamp": "2025-04-26 07:45:00+00:00",
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
      "previous_timestamp": "2025-04-26 07:30:00+00:00",
      "timestamp": "2025-04-26 07:45:00+00:00",
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
      "previous_timestamp": "2025-04-26 08:15:00+00:00",
      "timestamp": "2025-04-26 08:30:00+00:00",
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
      "previous_timestamp": "2025-04-26 08:15:00+00:00",
      "timestamp": "2025-04-26 08:30:00+00:00",
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
STRONG_BULLISH_CANDLE_BODY, CLOSE_NEAR_HIGH, STRONG_BEARISH_CANDLE_BODY, CLOSE_NEAR_LOW, LONG_LOWER_SHADOW_REJECTION, SMALL_BODY_INDECISION, DOJI_INDECISION, LONG_UPPER_SHADOW_REJECTION, SPINNING_TOP_INDECISION, SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED, CANDLE_PATTERN_NEEDS_TREND_CONTEXT, HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED, BULLISH_ENGULFING_CONTEXT, ENGULFING_WITHOUT_FOLLOW_THROUGH, BEARISH_ENGULFING_CONTEXT, BULLISH_BELT_HOLD_CONTEXT_REQUIRED, LONG_LEGGED_DOJI_CONTEXT, INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED, REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH, BEARISH_BELT_HOLD_CONTEXT_REQUIRED, RICKSHAW_MAN_DOJI_CONTEXT, GRAVESTONE_DOJI_CONTEXT, HANGING_MAN_LIKE_CONTEXT_REQUIRED, TWEEZERS_BOTTOM_CONTEXT_REQUIRED, DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT, DOJI_TOP_CONTEXT_REQUIRED, BEARISH_SEPARATING_LINES_CONTEXT, BULLISH_SEPARATING_LINES_CONTEXT, TWEEZERS_TOP_CONTEXT_REQUIRED, BULLISH_HARAMI_CONTEXT, BEARISH_HARAMI_CONTEXT, HARAMI_CROSS_CONTEXT, THREE_ADVANCING_WHITE_SOLDIERS_CONTEXT

## 2. Altunina trend context
### Swing structure
```json
[
  {
    "index": 1,
    "timestamp": "2025-04-26 00:15:00+00:00",
    "price": 94810.0,
    "point_type": "HIGH"
  },
  {
    "index": 3,
    "timestamp": "2025-04-26 00:45:00+00:00",
    "price": 94527.84,
    "point_type": "LOW"
  },
  {
    "index": 6,
    "timestamp": "2025-04-26 01:30:00+00:00",
    "price": 95199.0,
    "point_type": "HIGH"
  },
  {
    "index": 9,
    "timestamp": "2025-04-26 02:15:00+00:00",
    "price": 94699.11,
    "point_type": "LOW"
  },
  {
    "index": 10,
    "timestamp": "2025-04-26 02:30:00+00:00",
    "price": 95157.73,
    "point_type": "HIGH"
  },
  {
    "index": 21,
    "timestamp": "2025-04-26 05:15:00+00:00",
    "price": 94380.72,
    "point_type": "LOW"
  },
  {
    "index": 23,
    "timestamp": "2025-04-26 05:45:00+00:00",
    "price": 94706.6,
    "point_type": "HIGH"
  },
  {
    "index": 24,
    "timestamp": "2025-04-26 06:00:00+00:00",
    "price": 94583.91,
    "point_type": "LOW"
  },
  {
    "index": 30,
    "timestamp": "2025-04-26 07:30:00+00:00",
    "price": 94794.17,
    "point_type": "HIGH"
  },
  {
    "index": 32,
    "timestamp": "2025-04-26 08:00:00+00:00",
    "price": 94408.81,
    "point_type": "LOW"
  },
  {
    "index": 33,
    "timestamp": "2025-04-26 08:15:00+00:00",
    "price": 94733.54,
    "point_type": "HIGH"
  },
  {
    "index": 36,
    "timestamp": "2025-04-26 09:00:00+00:00",
    "price": 94217.32,
    "point_type": "LOW"
  },
  {
    "index": 37,
    "timestamp": "2025-04-26 09:15:00+00:00",
    "price": 94423.77,
    "point_type": "HIGH"
  },
  {
    "index": 38,
    "timestamp": "2025-04-26 09:30:00+00:00",
    "price": 94120.5,
    "point_type": "LOW"
  },
  {
    "index": 43,
    "timestamp": "2025-04-26 10:45:00+00:00",
    "price": 94394.44,
    "point_type": "HIGH"
  },
  {
    "index": 47,
    "timestamp": "2025-04-26 11:45:00+00:00",
    "price": 93990.6,
    "point_type": "LOW"
  },
  {
    "index": 49,
    "timestamp": "2025-04-26 12:15:00+00:00",
    "price": 94320.0,
    "point_type": "HIGH"
  },
  {
    "index": 51,
    "timestamp": "2025-04-26 12:45:00+00:00",
    "price": 94123.6,
    "point_type": "LOW"
  },
  {
    "index": 52,
    "timestamp": "2025-04-26 13:00:00+00:00",
    "price": 94300.95,
    "point_type": "HIGH"
  },
  {
    "index": 55,
    "timestamp": "2025-04-26 13:45:00+00:00",
    "price": 93870.69,
    "point_type": "LOW"
  },
  {
    "index": 56,
    "timestamp": "2025-04-26 14:00:00+00:00",
    "price": 94211.73,
    "point_type": "HIGH"
  },
  {
    "index": 61,
    "timestamp": "2025-04-26 15:15:00+00:00",
    "price": 94184.23,
    "point_type": "LOW"
  },
  {
    "index": 63,
    "timestamp": "2025-04-26 15:45:00+00:00",
    "price": 94394.0,
    "point_type": "HIGH"
  },
  {
    "index": 66,
    "timestamp": "2025-04-26 16:30:00+00:00",
    "price": 94041.0,
    "point_type": "LOW"
  },
  {
    "index": 67,
    "timestamp": "2025-04-26 16:45:00+00:00",
    "price": 94358.9,
    "point_type": "HIGH"
  },
  {
    "index": 69,
    "timestamp": "2025-04-26 17:15:00+00:00",
    "price": 94222.33,
    "point_type": "LOW"
  },
  {
    "index": 72,
    "timestamp": "2025-04-26 18:00:00+00:00",
    "price": 94372.0,
    "point_type": "HIGH"
  },
  {
    "index": 76,
    "timestamp": "2025-04-26 19:00:00+00:00",
    "price": 94095.23,
    "point_type": "LOW"
  },
  {
    "index": 92,
    "timestamp": "2025-04-26 23:00:00+00:00",
    "price": 94888.0,
    "point_type": "HIGH"
  },
  {
    "index": 94,
    "timestamp": "2025-04-26 23:30:00+00:00",
    "price": 94555.0,
    "point_type": "LOW"
  }
]
```
### Higher highs / lower highs
```json
{
  "raw_swing_count": 40,
  "swing_count": 30,
  "leg_count": 29,
  "structure_direction": "SIDEWAYS_STRUCTURE",
  "total_movement": 9832.879999999946,
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
    "lower_price": 93870.69,
    "upper_price": 94527.84,
    "mid_price": 94265.97259259257,
    "touch_count": 27,
    "source_indexes": [
      3,
      21,
      32,
      36,
      37,
      38,
      43,
      45,
      47,
      49,
      51,
      52,
      55,
      56,
      61,
      61,
      63,
      63,
      66,
      67,
      69,
      69,
      72,
      73,
      76,
      80,
      86
    ],
    "zone_width": 657.1499999999942,
    "zone_width_ratio": 0.006971232375017505,
    "formed_at_index": 86,
    "first_touch_index": 3,
    "last_touch_index": 86,
    "source_point_types": [
      "LOW",
      "LOW",
      "LOW",
      "LOW",
      "HIGH",
      "LOW",
      "HIGH",
      "HIGH",
      "LOW",
      "HIGH",
      "LOW",
      "HIGH",
      "LOW",
      "HIGH",
      "LOW",
      "HIGH",
      "LOW",
      "HIGH",
      "LOW",
      "HIGH",
      "LOW",
      "HIGH",
      "HIGH",
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
    "lower_price": 94555.0,
    "upper_price": 94888.0,
    "mid_price": 94731.37636363637,
    "touch_count": 11,
    "source_indexes": [
      1,
      9,
      16,
      19,
      23,
      24,
      27,
      30,
      33,
      92,
      94
    ],
    "zone_width": 333.0,
    "zone_width_ratio": 0.0035152028058976405,
    "formed_at_index": 94,
    "first_touch_index": 1,
    "last_touch_index": 94,
    "source_point_types": [
      "HIGH",
      "LOW",
      "HIGH",
      "HIGH",
      "HIGH",
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
  "lower_boundary": 93870.69,
  "upper_boundary": 94888.0,
  "midline": 94379.345,
  "width": 1017.3099999999977,
  "width_ratio": 0.010778947448724058,
  "touch_count": 38,
  "inside_close_ratio": 0.9361702127659575,
  "formed_at_index": 94,
  "first_touch_index": 1,
  "duration_candles": 94,
  "boundary_alternation_count": 8
}
```
### Range high / low
See trading range object above.
### Price position inside range
```json
{
  "swing_count": 40,
  "zone_count": 3,
  "range_detected": true,
  "range_formed_at_index": 94,
  "range_duration_candles": 94,
  "inside_close_ratio": 0.9361702127659575,
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
  "analysis_start_index": 95,
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
Count: 30
### Bearish evidence
Count: 40
### Neutral/range evidence
Count: 361
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
  "total_evidence_count": 431,
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
  "FLAT": 0.5872340425531914,
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
    "score": 0.5872340425531914
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
