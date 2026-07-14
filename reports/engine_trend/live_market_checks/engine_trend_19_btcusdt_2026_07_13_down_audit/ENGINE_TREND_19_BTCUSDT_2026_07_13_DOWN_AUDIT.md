# ENGINE-TREND-19 BTCUSDT 2026-07-13 DOWN audit

**Итоговый статус:** `DOWN_RECALL_GAP_TREND_ONLY_CONTINUATION_MISSING`.

Модель вернула `UNKNOWN`, потому что `DOWN_CONTINUATION` не был даже создан как runtime candidate. Полная 96-свечная Altunina-структура классифицирована как `SIDEWAYS_STRUCTURE`; Schwager range не подтверждён и потому breakdown не вычисляется; единственный bearish continuation candle-event отклонён контекстом; падение последних 24 свечей составило только `-0.891870%` при требовании `-1.000000%`. Bearish indicators (`4` против `1`) являются лишь одним методом и не могут самостоятельно seed-ить hypothesis.

## 1. Data coverage / quality

DB содержит ровно `96` свечей, first `2026-07-12T16:15:00Z`, last `2026-07-13T16:00:00Z`. Missing: `0`, duplicates: `0`, quality: `PASS`. Audit читал БД и не делал backfill.

## 2. Raw candle diagnostics

Window OHLC: `{'open': 64061.22, 'high': 64425.0, 'low': 62101.0, 'close': 62537.23}`. Total return: `-2.3790%`; max close drawdown: `-3.0749%`; close position in high-low range: `0.188`.

Impulse: `2026-07-13T00:15:00Z` 64425.00 → `2026-07-13T14:15:00Z` 62101.00 (`-3.6073%`). Rebound reached 62983.83 at `2026-07-13T15:15:00Z`.

Volume spikes (≥2× median) inside the broad impulse segment: `10`; on the post-low rebound: `1`. The two largest down-candle spikes were 860.81 (5.93× median) at `2026-07-13T13:45:00Z` and 803.52 (5.53×) at `2026-07-13T13:30:00Z`; rebound spike 423.91 (2.92×) at `2026-07-13T14:30:00Z`.

## 3. Altunina structure

Structural pivots: `15`; LL: `True`; LH after LL: `True`; engine direction: `SIDEWAYS_STRUCTURE`. Low sequence is bearish, but material lower-high changes are below the required two-thirds majority; the full 96-candle structure is therefore SIDEWAYS_STRUCTURE. The decision-window did not remove pivots.

| index | timestamp | price | type | label |
|---:|---|---:|---|---|
| 5 | 2026-07-12T17:30:00Z | 64177.74 | swing_high | UNKNOWN |
| 8 | 2026-07-12T18:15:00Z | 64018.69 | swing_low | UNKNOWN |
| 11 | 2026-07-12T19:00:00Z | 64232.56 | swing_high | UNKNOWN |
| 13 | 2026-07-12T19:30:00Z | 64147.30 | swing_low | HL |
| 14 | 2026-07-12T19:45:00Z | 64270.00 | swing_high | UNKNOWN |
| 24 | 2026-07-12T22:15:00Z | 63668.00 | swing_low | LL |
| 32 | 2026-07-13T00:15:00Z | 64425.00 | swing_high | HH |
| 39 | 2026-07-13T02:00:00Z | 63237.26 | swing_low | LL |
| 48 | 2026-07-13T04:15:00Z | 62911.94 | swing_high | LH |
| 51 | 2026-07-13T05:00:00Z | 62500.76 | swing_low | LL |
| 66 | 2026-07-13T08:45:00Z | 63302.88 | swing_high | HH |
| 74 | 2026-07-13T10:45:00Z | 62862.28 | swing_low | HL |
| 75 | 2026-07-13T11:00:00Z | 63135.55 | swing_high | LH |
| 88 | 2026-07-13T14:15:00Z | 62101.00 | swing_low | LL |
| 92 | 2026-07-13T15:15:00Z | 62983.83 | swing_high | LH |

## 4. Schwager range / breakdown

Range detected: `False`. No support zone has the required two touches, so no support/resistance pair can form a range. Breakdown status: `NO_BREAKOUT` / `NONE`; retest and polarity flip are absent.

Range candidates: support 62101.00 had only 1 touch; resistance candidates were 62862.28–62983.83 (3 touches), 63135.55–63302.88 (3), 64018.69–64270.00 (5), and 64425.00 (1). Since a range pair was never formed, boundaries are `null`, inside_close_ratio is `0.0`, and no breakdown/false-breakout/polarity event can be evaluated.

Критичный ответ: **NO** — `range_detected=false` не делает DOWN почти невозможным. Без range недоступен только breakdown seed; structure, candle continuation или decision progress также могут создать continuation candidate.

## 5. Technical indicators

```json
{
  "values": {
    "sma20": 62660.859,
    "sma50_diagnostic_only": 62823.174599999984,
    "sma99_diagnostic_only": null,
    "ema12": 62645.685133917636,
    "ema26": 62728.675465691704,
    "vwap": 63051.37467528763,
    "rsi14": 40.33064419534861,
    "macd": -82.99033177406818,
    "macd_signal": -101.32154167991187,
    "macd_histogram": 18.331209905843693,
    "atr14": 230.99500000000054,
    "atr_ratio": 0.0036937197250342,
    "adx14": 26.057259702885887,
    "bollinger_mid": 62660.859,
    "bollinger_upper": 63045.29833804438,
    "bollinger_lower": 62276.41966195562,
    "bollinger_percent_b": 0.33920870243288975
  },
  "price_relation": {
    "sma20": "BELOW",
    "sma50_diagnostic_only": "BELOW",
    "sma99_diagnostic_only": null,
    "ema12": "BELOW",
    "ema26": "BELOW",
    "vwap": "BELOW"
  },
  "votes": {
    "bullish": 1,
    "bearish": 4,
    "neutral_or_conflicted": 0,
    "direction": "BEARISH",
    "supporting_down": [
      "INDICATOR_EMA_BEARISH",
      "INDICATOR_RSI_BEARISH",
      "INDICATOR_PRICE_BELOW_SMA20",
      "INDICATOR_PRICE_BELOW_VWAP"
    ],
    "blocking_down": [
      "INDICATOR_MACD_BULLISH"
    ],
    "reason_codes": [
      "INDICATOR_EMA_BEARISH",
      "INDICATOR_MACD_BULLISH",
      "INDICATOR_RSI_BEARISH",
      "INDICATOR_PRICE_BELOW_SMA20",
      "INDICATOR_PRICE_BELOW_VWAP",
      "INDICATOR_ADX_TRENDING"
    ]
  }
}
```

## 6. Nison candle layer

The bearish separating-lines event at indexes 84-85 was CONTEXT_REJECTED: prior structure was sideways, there was no causal zone, and follow-through was still pending. All reversal-like events were also context-rejected.

## 7. Hypothesis generation

Runtime hypotheses: `0`. DOWN_CONTINUATION candidate exists: `False`; BEARISH_REVERSAL: `False`; BEAR_TRAP: `False`; CONFIRMED_RANGE: `False`.

Exact failed DOWN conditions: `structure_matches=false`, `breakdown_matches=false`, `confirmed_bearish_continuation_event=false`, `decision_window_progress_matches=false`. `indicator_matches=true`, but it is not a seed and gives only one independent method.

## 8. Composer trace

Confirmed/Pending/Conflicted: `0/0/0`. DOWN score `0.0`, UNKNOWN score `0.25`. `No runtime hypothesis reached the composer, so DOWN scored 0.0 and UNKNOWN floor scored 0.25; conservative fallback selected UNKNOWN.` Minimal missing condition: Any one additional bearish seed would combine with already-bearish indicators to reach the two-method confirmation contract. Numerically closest: decision-window progress missed -1.0% by about 0.108 percentage points.

## 9. Decision-window sweep

| end | start | regime | selected hypothesis | confirmed | pending | conflicted |
|---|---|---|---|---:|---:|---:|
| 2026-07-13T09:00:00Z | 2026-07-12T09:15:00Z | UNKNOWN | NONE | 0 | 0 | 1 |
| 2026-07-13T12:00:00Z | 2026-07-12T12:15:00Z | UNKNOWN | NONE | 0 | 0 | 0 |
| 2026-07-13T14:15:00Z | 2026-07-12T14:30:00Z | UNKNOWN | NONE | 0 | 0 | 0 |
| 2026-07-13T16:00:00Z | 2026-07-12T16:15:00Z | UNKNOWN | NONE | 0 | 0 | 0 |

Latest available closed candle: `2026-07-13T16:00:00Z`; after 16:00 data exists: `False`. Ни одно подокно не дало DOWN или FLAT.

At 09:00 a range and downward breakout existed, but the breakout trigger was index 52 while the decision-window started at 72. Therefore the old breakdown could not seed a current DOWN_CONTINUATION; the range hypothesis was CONFLICTED. The other three windows had no detected range and no hypotheses.

## 10. Diagnostic-only counterfactual

- `LL_LH_present`: `True`
- `price_below_SMA20_EMA12_EMA26_VWAP`: `True`
- `ADX_gt_25`: `True`
- `bearish_technical_votes_gte_3`: `True`
- `failed_rebound_lower_high_after_low`: `True`
- `no_confirmed_active_range`: `True`
- `no_bullish_reversal_confirmation`: `True`

Hypothetical trend-only DOWN_CONTINUATION: `True`. Риск false DOWN: `MEDIUM_TO_HIGH`; это требует отдельной OOS-задачи, а не изменения текущего runtime.

## 11. Safety audit

`UNKNOWN` safety-safe; ложного `UP` не было; formal directional conflicts и safety violations отсутствуют. Не выдавать `UP` после отскока было корректно. Поведение соответствует коду, поэтому это не execution bug, а missing coverage.

## 12. Conclusion

- Status: `DOWN_RECALL_GAP_TREND_ONLY_CONTINUATION_MISSING`
- Bug or missing coverage: `MISSING_COVERAGE`, not a runtime bug.
- Change runtime now: `NO`.
- Separate ENGINE-TREND-20: `YES` — validate a trend-only continuation contract out of sample, with explicit range false-positive controls.
- Runtime/trading runtime/thresholds/composer changed: `NO/NO/NO/NO`.
