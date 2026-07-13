# ethusdt_15m_up_001 вЂ” Market Evidence Trace

## Window
- Symbol: ETHUSDT
- Interval: 15m
- Period: 2025-05-08T00:00:00+00:00 вЂ” 2025-05-08T23:45:00+00:00
- Reference label: EXPECTED_UP
- Selection reason: top deterministic UP OHLC candidate

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
    "timestamp": "2025-05-08 00:00:00+00:00",
    "candle_index": 0,
    "open": 1811.11,
    "high": 1815.21,
    "low": 1809.93,
    "close": 1814.04,
    "body_pct": 0.5549242424242573,
    "upper_shadow_pct": 0.22159090909092402,
    "lower_shadow_pct": 0.22348484848481864,
    "position_in_window": 0.0,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-05-08 00:15:00+00:00",
    "candle_index": 1,
    "open": 1814.04,
    "high": 1816.67,
    "low": 1812.7,
    "close": 1816.16,
    "body_pct": 0.5340050377834015,
    "upper_shadow_pct": 0.1284634760705258,
    "lower_shadow_pct": 0.33753148614607276,
    "position_in_window": 0.0105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-05-08 00:30:00+00:00",
    "candle_index": 2,
    "open": 1816.15,
    "high": 1816.49,
    "low": 1808.71,
    "close": 1810.22,
    "body_pct": 0.7622107969151779,
    "upper_shadow_pct": 0.04370179948585082,
    "lower_shadow_pct": 0.19408740359897123,
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
    "timestamp": "2025-05-08 00:45:00+00:00",
    "candle_index": 3,
    "open": 1810.21,
    "high": 1828.29,
    "low": 1808.88,
    "close": 1827.13,
    "body_pct": 0.8717156105100566,
    "upper_shadow_pct": 0.059763008758364926,
    "lower_shadow_pct": 0.06852138073157843,
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
    "timestamp": "2025-05-08 01:00:00+00:00",
    "candle_index": 4,
    "open": 1827.12,
    "high": 1837.2,
    "low": 1822.59,
    "close": 1825.56,
    "body_pct": 0.10677618069814729,
    "upper_shadow_pct": 0.6899383983572941,
    "lower_shadow_pct": 0.20328542094455862,
    "position_in_window": 0.0421,
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
    "timestamp": "2025-05-08 01:15:00+00:00",
    "candle_index": 5,
    "open": 1825.56,
    "high": 1832.4,
    "low": 1820.5,
    "close": 1828.61,
    "body_pct": 0.25630252100839757,
    "upper_shadow_pct": 0.3184873949579968,
    "lower_shadow_pct": 0.4252100840336056,
    "position_in_window": 0.0526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION"
    ]
  },
  {
    "timestamp": "2025-05-08 01:30:00+00:00",
    "candle_index": 6,
    "open": 1828.6,
    "high": 1830.99,
    "low": 1825.0,
    "close": 1825.86,
    "body_pct": 0.4574290484140242,
    "upper_shadow_pct": 0.3989983305509343,
    "lower_shadow_pct": 0.1435726210350415,
    "position_in_window": 0.0632,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-05-08 02:00:00+00:00",
    "candle_index": 8,
    "open": 1822.91,
    "high": 1829.35,
    "low": 1822.91,
    "close": 1829.18,
    "body_pct": 0.973602484472073,
    "upper_shadow_pct": 0.02639751552792701,
    "lower_shadow_pct": 0.0,
    "position_in_window": 0.0842,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-05-08 02:15:00+00:00",
    "candle_index": 9,
    "open": 1829.17,
    "high": 1841.0,
    "low": 1829.0,
    "close": 1840.09,
    "body_pct": 0.9099999999999872,
    "upper_shadow_pct": 0.07583333333334015,
    "lower_shadow_pct": 0.01416666666667273,
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
    "timestamp": "2025-05-08 02:30:00+00:00",
    "candle_index": 10,
    "open": 1840.08,
    "high": 1847.75,
    "low": 1838.3,
    "close": 1840.6,
    "body_pct": 0.055026455026452835,
    "upper_shadow_pct": 0.7566137566137626,
    "lower_shadow_pct": 0.18835978835978456,
    "position_in_window": 0.1053,
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
    "timestamp": "2025-05-08 02:45:00+00:00",
    "candle_index": 11,
    "open": 1840.6,
    "high": 1845.47,
    "low": 1840.3,
    "close": 1841.56,
    "body_pct": 0.18568665377176458,
    "upper_shadow_pct": 0.75628626692457,
    "lower_shadow_pct": 0.058027079303665435,
    "position_in_window": 0.1158,
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
    "timestamp": "2025-05-08 03:30:00+00:00",
    "candle_index": 14,
    "open": 1864.18,
    "high": 1888.84,
    "low": 1860.75,
    "close": 1888.19,
    "body_pct": 0.8547525809896782,
    "upper_shadow_pct": 0.02313990744036545,
    "lower_shadow_pct": 0.12210751156995635,
    "position_in_window": 0.1474,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-05-08 03:45:00+00:00",
    "candle_index": 15,
    "open": 1888.19,
    "high": 1906.77,
    "low": 1883.07,
    "close": 1901.1,
    "body_pct": 0.5447257383966173,
    "upper_shadow_pct": 0.23924050632911653,
    "lower_shadow_pct": 0.2160337552742662,
    "position_in_window": 0.1579,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-05-08 04:00:00+00:00",
    "candle_index": 16,
    "open": 1901.09,
    "high": 1916.59,
    "low": 1900.59,
    "close": 1907.38,
    "body_pct": 0.39312500000001194,
    "upper_shadow_pct": 0.5756249999999881,
    "lower_shadow_pct": 0.03125,
    "position_in_window": 0.1684,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2025-05-08 04:15:00+00:00",
    "candle_index": 17,
    "open": 1907.39,
    "high": 1914.8,
    "low": 1905.45,
    "close": 1905.89,
    "body_pct": 0.16042780748663257,
    "upper_shadow_pct": 0.7925133689839494,
    "lower_shadow_pct": 0.04705882352941806,
    "position_in_window": 0.1789,
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
    "timestamp": "2025-05-08 04:30:00+00:00",
    "candle_index": 18,
    "open": 1905.9,
    "high": 1907.6,
    "low": 1898.6,
    "close": 1898.99,
    "body_pct": 0.7677777777777869,
    "upper_shadow_pct": 0.18888888888886868,
    "lower_shadow_pct": 0.04333333333334445,
    "position_in_window": 0.1895,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BEARISH_CANDLE_BODY",
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-05-08 04:45:00+00:00",
    "candle_index": 19,
    "open": 1899.0,
    "high": 1901.68,
    "low": 1892.91,
    "close": 1893.81,
    "body_pct": 0.5917901938426529,
    "upper_shadow_pct": 0.3055872291904298,
    "lower_shadow_pct": 0.10262257696691739,
    "position_in_window": 0.2,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-05-08 05:00:00+00:00",
    "candle_index": 20,
    "open": 1893.81,
    "high": 1905.4,
    "low": 1893.81,
    "close": 1898.92,
    "body_pct": 0.4408973252804196,
    "upper_shadow_pct": 0.5591026747195804,
    "lower_shadow_pct": 0.0,
    "position_in_window": 0.2105,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2025-05-08 05:15:00+00:00",
    "candle_index": 21,
    "open": 1898.91,
    "high": 1899.57,
    "low": 1892.2,
    "close": 1897.8,
    "body_pct": 0.15061058344642386,
    "upper_shadow_pct": 0.08955223880595173,
    "lower_shadow_pct": 0.7598371777476244,
    "position_in_window": 0.2211,
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
    "timestamp": "2025-05-08 05:30:00+00:00",
    "candle_index": 22,
    "open": 1897.81,
    "high": 1901.34,
    "low": 1896.71,
    "close": 1901.1,
    "body_pct": 0.7105831533477425,
    "upper_shadow_pct": 0.05183585313175275,
    "lower_shadow_pct": 0.23758099352050477,
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
    "timestamp": "2025-05-08 05:45:00+00:00",
    "candle_index": 23,
    "open": 1901.1,
    "high": 1903.53,
    "low": 1896.3,
    "close": 1896.77,
    "body_pct": 0.5988934993084255,
    "upper_shadow_pct": 0.33609958506224863,
    "lower_shadow_pct": 0.06500691562932588,
    "position_in_window": 0.2421,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-05-08 06:00:00+00:00",
    "candle_index": 24,
    "open": 1896.77,
    "high": 1903.09,
    "low": 1896.0,
    "close": 1902.79,
    "body_pct": 0.8490832157969043,
    "upper_shadow_pct": 0.04231311706628463,
    "lower_shadow_pct": 0.1086036671368111,
    "position_in_window": 0.2526,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-05-08 06:15:00+00:00",
    "candle_index": 25,
    "open": 1902.8,
    "high": 1906.13,
    "low": 1900.24,
    "close": 1904.21,
    "body_pct": 0.23938879456707265,
    "upper_shadow_pct": 0.325976230899837,
    "lower_shadow_pct": 0.4346349745330903,
    "position_in_window": 0.2632,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "SMALL_BODY_INDECISION",
      "SPINNING_TOP_INDECISION"
    ]
  },
  {
    "timestamp": "2025-05-08 06:30:00+00:00",
    "candle_index": 26,
    "open": 1904.21,
    "high": 1907.52,
    "low": 1902.31,
    "close": 1907.52,
    "body_pct": 0.635316698656415,
    "upper_shadow_pct": 0.0,
    "lower_shadow_pct": 0.36468330134358495,
    "position_in_window": 0.2737,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-05-08 06:45:00+00:00",
    "candle_index": 27,
    "open": 1907.52,
    "high": 1912.35,
    "low": 1905.07,
    "close": 1911.29,
    "body_pct": 0.5178571428571423,
    "upper_shadow_pct": 0.14560439560438865,
    "lower_shadow_pct": 0.33653846153846906,
    "position_in_window": 0.2842,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-05-08 07:00:00+00:00",
    "candle_index": 28,
    "open": 1911.29,
    "high": 1914.38,
    "low": 1908.37,
    "close": 1909.39,
    "body_pct": 0.3161397670548743,
    "upper_shadow_pct": 0.5141430948419357,
    "lower_shadow_pct": 0.16971713810319003,
    "position_in_window": 0.2947,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "CLOSE_NEAR_LOW"
    ]
  },
  {
    "timestamp": "2025-05-08 07:15:00+00:00",
    "candle_index": 29,
    "open": 1909.38,
    "high": 1915.91,
    "low": 1908.81,
    "close": 1914.93,
    "body_pct": 0.781690140845049,
    "upper_shadow_pct": 0.1380281690140844,
    "lower_shadow_pct": 0.08028169014086659,
    "position_in_window": 0.3053,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "STRONG_BULLISH_CANDLE_BODY",
      "CLOSE_NEAR_HIGH"
    ]
  },
  {
    "timestamp": "2025-05-08 08:00:00+00:00",
    "candle_index": 32,
    "open": 1928.4,
    "high": 1932.91,
    "low": 1925.9,
    "close": 1928.9,
    "body_pct": 0.07132667617689024,
    "upper_shadow_pct": 0.5720399429386585,
    "lower_shadow_pct": 0.35663338088445123,
    "position_in_window": 0.3368,
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
    "timestamp": "2025-05-08 08:15:00+00:00",
    "candle_index": 33,
    "open": 1928.89,
    "high": 1934.8,
    "low": 1927.99,
    "close": 1930.97,
    "body_pct": 0.305433186490447,
    "upper_shadow_pct": 0.5624082232011686,
    "lower_shadow_pct": 0.13215859030838445,
    "position_in_window": 0.3474,
    "local_context": "Trend context is not joined to candle morphology by the current Nison trace.",
    "confirmation_status": "NOT_EVALUATED",
    "quality_score": null,
    "reason_codes": [
      "LONG_UPPER_SHADOW_REJECTION"
    ]
  },
  {
    "timestamp": "2025-05-08 08:30:00+00:00",
    "candle_index": 34,
    "open": 1930.97,
    "high": 1938.31,
    "low": 1929.7,
    "close": 1937.1,
    "body_pct": 0.711962833914048,
    "upper_shadow_pct": 0.14053426248548787,
    "lower_shadow_pct": 0.14750290360046417,
    "position_in_window": 0.3579,
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
  "doji_count": 6,
  "doji_ratio": 0.0625,
  "small_body_count": 28,
  "small_body_ratio": 0.2916666666666667,
  "bullish_body_total": 545.1700000000001,
  "bearish_body_total": 148.90999999999985
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
      "previous_timestamp": "2025-05-08 00:30:00+00:00",
      "timestamp": "2025-05-08 00:45:00+00:00",
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
      "previous_timestamp": "2025-05-08 00:30:00+00:00",
      "timestamp": "2025-05-08 00:45:00+00:00",
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
      "previous_timestamp": "2025-05-08 01:00:00+00:00",
      "timestamp": "2025-05-08 01:15:00+00:00",
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
      "previous_timestamp": "2025-05-08 01:00:00+00:00",
      "timestamp": "2025-05-08 01:15:00+00:00",
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
      "previous_timestamp": "2025-05-08 05:30:00+00:00",
      "timestamp": "2025-05-08 05:45:00+00:00",
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
      "previous_timestamp": "2025-05-08 05:30:00+00:00",
      "timestamp": "2025-05-08 05:45:00+00:00",
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
      "previous_timestamp": "2025-05-08 05:45:00+00:00",
      "timestamp": "2025-05-08 06:00:00+00:00",
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
      "previous_timestamp": "2025-05-08 05:45:00+00:00",
      "timestamp": "2025-05-08 06:00:00+00:00",
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
      "previous_timestamp": "2025-05-08 07:00:00+00:00",
      "timestamp": "2025-05-08 07:15:00+00:00",
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
      "previous_timestamp": "2025-05-08 07:00:00+00:00",
      "timestamp": "2025-05-08 07:15:00+00:00",
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
      "previous_timestamp": "2025-05-08 09:15:00+00:00",
      "timestamp": "2025-05-08 09:30:00+00:00",
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
      "previous_timestamp": "2025-05-08 09:15:00+00:00",
      "timestamp": "2025-05-08 09:30:00+00:00",
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
      "previous_timestamp": "2025-05-08 10:00:00+00:00",
      "timestamp": "2025-05-08 10:15:00+00:00",
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
      "previous_timestamp": "2025-05-08 10:00:00+00:00",
      "timestamp": "2025-05-08 10:15:00+00:00",
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
      "previous_timestamp": "2025-05-08 12:15:00+00:00",
      "timestamp": "2025-05-08 12:30:00+00:00",
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
      "previous_timestamp": "2025-05-08 12:15:00+00:00",
      "timestamp": "2025-05-08 12:30:00+00:00",
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
      "previous_timestamp": "2025-05-08 14:00:00+00:00",
      "timestamp": "2025-05-08 14:15:00+00:00",
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
      "previous_timestamp": "2025-05-08 14:00:00+00:00",
      "timestamp": "2025-05-08 14:15:00+00:00",
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
      "previous_timestamp": "2025-05-08 16:00:00+00:00",
      "timestamp": "2025-05-08 16:15:00+00:00",
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
      "previous_timestamp": "2025-05-08 16:00:00+00:00",
      "timestamp": "2025-05-08 16:15:00+00:00",
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
CLOSE_NEAR_HIGH, STRONG_BEARISH_CANDLE_BODY, CLOSE_NEAR_LOW, STRONG_BULLISH_CANDLE_BODY, LONG_UPPER_SHADOW_REJECTION, SMALL_BODY_INDECISION, SPINNING_TOP_INDECISION, DOJI_INDECISION, SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED, CANDLE_PATTERN_NEEDS_TREND_CONTEXT, LONG_LOWER_SHADOW_REJECTION, HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED, BULLISH_ENGULFING_CONTEXT, ENGULFING_WITHOUT_FOLLOW_THROUGH, BEARISH_ENGULFING_CONTEXT, BEARISH_BELT_HOLD_CONTEXT_REQUIRED, BULLISH_BELT_HOLD_CONTEXT_REQUIRED, INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED, REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH, HANGING_MAN_LIKE_CONTEXT_REQUIRED, LONG_LEGGED_DOJI_CONTEXT, DRAGONFLY_DOJI_CONTEXT, TWEEZERS_TOP_CONTEXT_REQUIRED, TWEEZERS_BOTTOM_CONTEXT_REQUIRED, BEARISH_HARAMI_CONTEXT, DOJI_AFTER_LONG_BULLISH_BODY_CONTEXT, DOJI_TOP_CONTEXT_REQUIRED, HARAMI_CROSS_CONTEXT, BULLISH_SEPARATING_LINES_CONTEXT, THREE_BUDDHA_TOP_CONTEXT_REQUIRED, BULLISH_BODY_DOMINANCE

## 2. Altunina trend context
### Swing structure
```json
[
  {
    "index": 1,
    "timestamp": "2025-05-08 00:15:00+00:00",
    "price": 1816.67,
    "point_type": "HIGH"
  },
  {
    "index": 2,
    "timestamp": "2025-05-08 00:30:00+00:00",
    "price": 1808.71,
    "point_type": "LOW"
  },
  {
    "index": 4,
    "timestamp": "2025-05-08 01:00:00+00:00",
    "price": 1837.2,
    "point_type": "HIGH"
  },
  {
    "index": 7,
    "timestamp": "2025-05-08 01:45:00+00:00",
    "price": 1820.0,
    "point_type": "LOW"
  },
  {
    "index": 10,
    "timestamp": "2025-05-08 02:30:00+00:00",
    "price": 1847.75,
    "point_type": "HIGH"
  },
  {
    "index": 12,
    "timestamp": "2025-05-08 03:00:00+00:00",
    "price": 1839.0,
    "point_type": "LOW"
  },
  {
    "index": 16,
    "timestamp": "2025-05-08 04:00:00+00:00",
    "price": 1916.59,
    "point_type": "HIGH"
  },
  {
    "index": 19,
    "timestamp": "2025-05-08 04:45:00+00:00",
    "price": 1892.91,
    "point_type": "LOW"
  },
  {
    "index": 20,
    "timestamp": "2025-05-08 05:00:00+00:00",
    "price": 1905.4,
    "point_type": "HIGH"
  },
  {
    "index": 21,
    "timestamp": "2025-05-08 05:15:00+00:00",
    "price": 1892.2,
    "point_type": "LOW"
  },
  {
    "index": 23,
    "timestamp": "2025-05-08 05:45:00+00:00",
    "price": 1903.53,
    "point_type": "HIGH"
  },
  {
    "index": 24,
    "timestamp": "2025-05-08 06:00:00+00:00",
    "price": 1896.0,
    "point_type": "LOW"
  },
  {
    "index": 35,
    "timestamp": "2025-05-08 08:45:00+00:00",
    "price": 1947.0,
    "point_type": "HIGH"
  },
  {
    "index": 36,
    "timestamp": "2025-05-08 09:00:00+00:00",
    "price": 1929.81,
    "point_type": "LOW"
  },
  {
    "index": 37,
    "timestamp": "2025-05-08 09:15:00+00:00",
    "price": 1942.0,
    "point_type": "HIGH"
  },
  {
    "index": 38,
    "timestamp": "2025-05-08 09:30:00+00:00",
    "price": 1932.08,
    "point_type": "LOW"
  },
  {
    "index": 43,
    "timestamp": "2025-05-08 10:45:00+00:00",
    "price": 1968.72,
    "point_type": "HIGH"
  },
  {
    "index": 46,
    "timestamp": "2025-05-08 11:30:00+00:00",
    "price": 1945.21,
    "point_type": "LOW"
  },
  {
    "index": 49,
    "timestamp": "2025-05-08 12:15:00+00:00",
    "price": 1977.26,
    "point_type": "HIGH"
  },
  {
    "index": 50,
    "timestamp": "2025-05-08 12:30:00+00:00",
    "price": 1954.27,
    "point_type": "LOW"
  },
  {
    "index": 54,
    "timestamp": "2025-05-08 13:30:00+00:00",
    "price": 1984.75,
    "point_type": "HIGH"
  },
  {
    "index": 55,
    "timestamp": "2025-05-08 13:45:00+00:00",
    "price": 1962.5,
    "point_type": "LOW"
  },
  {
    "index": 62,
    "timestamp": "2025-05-08 15:30:00+00:00",
    "price": 2075.65,
    "point_type": "HIGH"
  },
  {
    "index": 66,
    "timestamp": "2025-05-08 16:30:00+00:00",
    "price": 2036.64,
    "point_type": "LOW"
  },
  {
    "index": 67,
    "timestamp": "2025-05-08 16:45:00+00:00",
    "price": 2054.87,
    "point_type": "HIGH"
  },
  {
    "index": 68,
    "timestamp": "2025-05-08 17:00:00+00:00",
    "price": 2043.1,
    "point_type": "LOW"
  },
  {
    "index": 69,
    "timestamp": "2025-05-08 17:15:00+00:00",
    "price": 2057.39,
    "point_type": "HIGH"
  },
  {
    "index": 71,
    "timestamp": "2025-05-08 17:45:00+00:00",
    "price": 2036.71,
    "point_type": "LOW"
  },
  {
    "index": 74,
    "timestamp": "2025-05-08 18:30:00+00:00",
    "price": 2074.2,
    "point_type": "HIGH"
  },
  {
    "index": 76,
    "timestamp": "2025-05-08 19:00:00+00:00",
    "price": 2061.28,
    "point_type": "LOW"
  },
  {
    "index": 79,
    "timestamp": "2025-05-08 19:45:00+00:00",
    "price": 2140.0,
    "point_type": "HIGH"
  },
  {
    "index": 81,
    "timestamp": "2025-05-08 20:15:00+00:00",
    "price": 2111.6,
    "point_type": "LOW"
  },
  {
    "index": 85,
    "timestamp": "2025-05-08 21:15:00+00:00",
    "price": 2226.0,
    "point_type": "HIGH"
  },
  {
    "index": 87,
    "timestamp": "2025-05-08 21:45:00+00:00",
    "price": 2160.24,
    "point_type": "LOW"
  },
  {
    "index": 91,
    "timestamp": "2025-05-08 22:45:00+00:00",
    "price": 2196.77,
    "point_type": "HIGH"
  },
  {
    "index": 92,
    "timestamp": "2025-05-08 23:00:00+00:00",
    "price": 2166.29,
    "point_type": "LOW"
  }
]
```
### Higher highs / lower highs
```json
{
  "raw_swing_count": 44,
  "swing_count": 36,
  "leg_count": 35,
  "structure_direction": "SIDEWAYS_STRUCTURE",
  "total_movement": 1116.0199999999995,
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
    "lower_price": 1816.67,
    "upper_price": 1820.5,
    "mid_price": 1819.0566666666666,
    "touch_count": 3,
    "source_indexes": [
      1,
      5,
      7
    ],
    "zone_width": 3.8299999999999272,
    "zone_width_ratio": 0.002105486909881822,
    "formed_at_index": 7,
    "first_touch_index": 1,
    "last_touch_index": 7,
    "source_point_types": [
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
    "lower_price": 1942.0,
    "upper_price": 1947.0,
    "mid_price": 1944.51,
    "touch_count": 4,
    "source_indexes": [
      30,
      35,
      37,
      46
    ],
    "zone_width": 5.0,
    "zone_width_ratio": 0.0025713418804737443,
    "formed_at_index": 46,
    "first_touch_index": 30,
    "last_touch_index": 46,
    "source_point_types": [
      "HIGH",
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
  "lower_boundary": 1816.67,
  "upper_boundary": 1947.0,
  "midline": 1881.835,
  "width": 130.32999999999993,
  "width_ratio": 0.06925686896034983,
  "touch_count": 7,
  "inside_close_ratio": 0.8478260869565217,
  "formed_at_index": 46,
  "first_touch_index": 1,
  "duration_candles": 46,
  "boundary_alternation_count": 1
}
```
### Range high / low
See trading range object above.
### Price position inside range
```json
{
  "swing_count": 44,
  "zone_count": 14,
  "range_detected": false,
  "range_formed_at_index": 46,
  "range_duration_candles": 46,
  "inside_close_ratio": 0.8478260869565217,
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
Count: 30
### Bearish evidence
Count: 32
### Neutral/range evidence
Count: 322
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
  "total_evidence_count": 384,
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
