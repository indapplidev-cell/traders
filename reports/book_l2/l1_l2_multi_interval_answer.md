# L1-L2 Multi-Interval Answer Smoke

## Status

`FAIL`

## Request

| Field | Value |
|---|---|
| Symbols | BTCUSDT, ETHUSDT, SOLUSDT |
| Intervals | 15m, 1h, 4h |
| Window size | `300` |
| Window count | `4` |
| Min candles | `50` |

## Interval Summary

| Interval | Status | Overall State | Observation Candidates | Skip Candidates | Safety |
|---|---|---|---|---|---|
| 15m | PASS | UNKNOWN | none | SOLUSDT, BTCUSDT, ETHUSDT | LOCKED |
| 1h | FAIL | UNKNOWN | none | BTCUSDT, ETHUSDT, SOLUSDT | LOCKED |
| 4h | FAIL | UNKNOWN | none | BTCUSDT, ETHUSDT, SOLUSDT | LOCKED |

## Actual Answers By Interval

### Interval: 15m

#### Overall

- Status: `PASS`
- Overall state: `UNKNOWN`
- Brief: UNKNOWN_CONTEXT

#### Observation candidates

- none

#### Skip candidates

- SOLUSDT
- BTCUSDT
- ETHUSDT

#### Key points

- Overall context is UNKNOWN.
- No clean observation candidates found.
- Skip candidates: SOLUSDT, BTCUSDT, ETHUSDT.
- Most symbols are skip candidates.
- Safety remains fail-closed: runtime action is not approved.

#### Per-symbol Context

| Rank | Symbol | Bucket | Quality | Score | Skip | Current regime | Stability | Last transition | Main reason |
|---:|---|---|---|---:|---|---|---|---|---|
|  | BTCUSDT | UNKNOWN | SKIP | 0.20 | true | FLAT | CHANGING | NO_CHANGE | Unknown current regime. |
|  | ETHUSDT | UNKNOWN | SKIP | 0.20 | true | FLAT | CHANGING | NO_CHANGE | Unknown current regime. |
|  | SOLUSDT | UNKNOWN | SKIP | 0.00 | true | UNKNOWN | UNSTABLE | TO_UNKNOWN | Unknown current regime. |

#### Safety

- trade_signal: `NOT_EVALUATED`
- safe_for_runtime_trading: `false`
- orders_enabled: `false`
- live_trading_connected: `false`
- safety_status: `LOCKED`

- Evidence file: `reports/book_l2/interval_answers/l1_l2_interval_answer_15m.md`

---

### Interval: 1h

#### Overall

- Status: `FAIL`
- Overall state: `UNKNOWN`
- Brief: UNKNOWN_CONTEXT
- Reason: warnings are present; L2 warnings: BTCUSDT: required 1200 candles, found 0.; ETHUSDT: required 1200 candles, found 0.; SOLUSDT: required 1200 candles, found 0.

#### Observation candidates

- none

#### Skip candidates

- BTCUSDT
- ETHUSDT
- SOLUSDT

#### Key points

- Overall context is UNKNOWN.
- No clean observation candidates found.
- Skip candidates: BTCUSDT, ETHUSDT, SOLUSDT.
- Most symbols are skip candidates.
- Safety remains fail-closed: runtime action is not approved.

#### Per-symbol Context

| Rank | Symbol | Bucket | Quality | Score | Skip | Current regime | Stability | Last transition | Main reason |
|---:|---|---|---|---:|---|---|---|---|---|
|  | BTCUSDT | INSUFFICIENT_DATA | SKIP | 0.00 | true | UNKNOWN | ERROR | ERROR | No valid context available. |
|  | ETHUSDT | INSUFFICIENT_DATA | SKIP | 0.00 | true | UNKNOWN | ERROR | ERROR | No valid context available. |
|  | SOLUSDT | INSUFFICIENT_DATA | SKIP | 0.00 | true | UNKNOWN | ERROR | ERROR | No valid context available. |

#### Safety

- trade_signal: `NOT_EVALUATED`
- safe_for_runtime_trading: `false`
- orders_enabled: `false`
- live_trading_connected: `false`
- safety_status: `LOCKED`

- Evidence file: `reports/book_l2/interval_answers/l1_l2_interval_answer_1h.md`

---

### Interval: 4h

#### Overall

- Status: `FAIL`
- Overall state: `UNKNOWN`
- Brief: UNKNOWN_CONTEXT
- Reason: warnings are present; L2 warnings: BTCUSDT: required 1200 candles, found 0.; ETHUSDT: required 1200 candles, found 0.; SOLUSDT: required 1200 candles, found 0.

#### Observation candidates

- none

#### Skip candidates

- BTCUSDT
- ETHUSDT
- SOLUSDT

#### Key points

- Overall context is UNKNOWN.
- No clean observation candidates found.
- Skip candidates: BTCUSDT, ETHUSDT, SOLUSDT.
- Most symbols are skip candidates.
- Safety remains fail-closed: runtime action is not approved.

#### Per-symbol Context

| Rank | Symbol | Bucket | Quality | Score | Skip | Current regime | Stability | Last transition | Main reason |
|---:|---|---|---|---:|---|---|---|---|---|
|  | BTCUSDT | INSUFFICIENT_DATA | SKIP | 0.00 | true | UNKNOWN | ERROR | ERROR | No valid context available. |
|  | ETHUSDT | INSUFFICIENT_DATA | SKIP | 0.00 | true | UNKNOWN | ERROR | ERROR | No valid context available. |
|  | SOLUSDT | INSUFFICIENT_DATA | SKIP | 0.00 | true | UNKNOWN | ERROR | ERROR | No valid context available. |

#### Safety

- trade_signal: `NOT_EVALUATED`
- safe_for_runtime_trading: `false`
- orders_enabled: `false`
- live_trading_connected: `false`
- safety_status: `LOCKED`

- Evidence file: `reports/book_l2/interval_answers/l1_l2_interval_answer_4h.md`

---

## Cross-Interval Observations

- Intervals checked: 3
- Intervals PASS: 1
- Intervals FAIL: 2
- Intervals PASS_WITH_WARNINGS: 0
- Intervals with observation candidates: none
- Intervals with all symbols skipped: 15m, 1h, 4h
- Most common overall state: UNKNOWN
- Symbols repeatedly skipped: BTCUSDT, ETHUSDT, SOLUSDT
- Symbols repeatedly observed: none

## Source Lineage

- L1 runtime JSON: `reports/book_l1/timeline_preview.json`
- L2 runtime JSON: `reports/book_l2/timeline_context.json`
- Each interval was processed through L1 -> L2 pipeline.
- Per-interval evidence files are stored in `reports/book_l2/interval_answers/`.

## Conclusion

The L1-L2 pipeline produced multi-interval context evidence.

This is observe-only context. It is not a trading instruction.

## Errors

- Interval 1h: warnings are present; L2 warnings: BTCUSDT: required 1200 candles, found 0.; ETHUSDT: required 1200 candles, found 0.; SOLUSDT: required 1200 candles, found 0.
- Interval 4h: warnings are present; L2 warnings: BTCUSDT: required 1200 candles, found 0.; ETHUSDT: required 1200 candles, found 0.; SOLUSDT: required 1200 candles, found 0.
