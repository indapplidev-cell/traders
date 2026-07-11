# L1-L2 Interval Answer Smoke

## Status

`PASS`

## Request

| Field | Value |
|---|---|
| Symbols | BTCUSDT, ETHUSDT, SOLUSDT |
| Interval | `15m` |
| Window size | `300` |
| Window count | `4` |
| Min candles | `50` |

## Pipeline Result

| Step | Status |
|---|---|
| L1 timeline export | PASS |
| L1 JSON consumer strict | PASS |
| L2 context export | PASS |
| L2 JSON consumer strict | PASS |
| L2 API readiness strict | PASS |
| Symbol propagation | PASS |
| Source lineage | PASS |
| Fail-closed safety | PASS |
| Forbidden terms | PASS |
| Evidence markdown written | PASS |

## Actual BOOK-L2 Answer

### Overall

- Overall state: `UNKNOWN`
- Brief: UNKNOWN_CONTEXT

### Observation candidates

- none

### Skip candidates

- SOLUSDT
- BTCUSDT
- ETHUSDT

### Key points

- Overall context is UNKNOWN.
- No clean observation candidates found.
- Skip candidates: SOLUSDT, BTCUSDT, ETHUSDT.
- Most symbols are skip candidates.
- Safety remains fail-closed: runtime action is not approved.

## Per-symbol Context

| Rank | Symbol | Bucket | Quality | Score | Skip | Current regime | Stability | Last transition | Main reason |
|---:|---|---|---|---:|---|---|---|---|---|
|  | BTCUSDT | UNKNOWN | SKIP | 0.20 | true | FLAT | CHANGING | NO_CHANGE | Unknown current regime. |
|  | ETHUSDT | UNKNOWN | SKIP | 0.20 | true | FLAT | CHANGING | NO_CHANGE | Unknown current regime. |
|  | SOLUSDT | UNKNOWN | SKIP | 0.00 | true | UNKNOWN | UNSTABLE | TO_UNKNOWN | Unknown current regime. |

## Source Lineage

- L1 input JSON: `reports/book_l1/timeline_preview.json`
- L2 output JSON: `reports/book_l2/timeline_context.json`
- L2 source confirms L1 timeline: `PASS`

## Safety

- trade_signal: `NOT_EVALUATED`
- safe_for_runtime_trading: `false`
- orders_enabled: `false`
- live_trading_connected: `false`
- traders_core_connected: `false`
- approved_for_live_trading: `false`
- approved_for_auto_activation: `false`
- observe_only: `N/A`

## Conclusion

The L1-L2 pipeline produced a readable market context report for the requested interval.

This is observe-only context. It is not a trading instruction.
