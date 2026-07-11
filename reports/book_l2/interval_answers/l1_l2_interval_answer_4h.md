# L1-L2 Interval Answer Smoke

## Status

`FAIL`

## Request

| Field | Value |
|---|---|
| Symbols | BTCUSDT, ETHUSDT, SOLUSDT |
| Interval | `4h` |
| Window size | `300` |
| Window count | `4` |
| Min candles | `50` |

## Pipeline Result

| Step | Status |
|---|---|
| L1 timeline export | PASS |
| L1 JSON consumer strict | PASS |
| L2 context export | PASS |
| L2 JSON consumer strict | FAIL |
| L2 API readiness strict | FAIL |
| Symbol propagation | PASS |
| Source lineage | PASS |
| Fail-closed safety | PASS |
| Forbidden terms | PASS |
| Evidence markdown written | PASS |

## Failure

- warnings are present
- warnings are present

## Actual BOOK-L2 Answer

### Overall

- Overall state: `UNKNOWN`
- Brief: UNKNOWN_CONTEXT

### Observation candidates

- none

### Skip candidates

- BTCUSDT
- ETHUSDT
- SOLUSDT

### Key points

- Overall context is UNKNOWN.
- No clean observation candidates found.
- Skip candidates: BTCUSDT, ETHUSDT, SOLUSDT.
- Most symbols are skip candidates.
- Safety remains fail-closed: runtime action is not approved.

## Per-symbol Context

| Rank | Symbol | Bucket | Quality | Score | Skip | Current regime | Stability | Last transition | Main reason |
|---:|---|---|---|---:|---|---|---|---|---|
|  | BTCUSDT | INSUFFICIENT_DATA | SKIP | 0.00 | true | UNKNOWN | ERROR | ERROR | No valid context available. |
|  | ETHUSDT | INSUFFICIENT_DATA | SKIP | 0.00 | true | UNKNOWN | ERROR | ERROR | No valid context available. |
|  | SOLUSDT | INSUFFICIENT_DATA | SKIP | 0.00 | true | UNKNOWN | ERROR | ERROR | No valid context available. |

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

FAIL: The L1-L2 smoke checks did not all pass.

This is observe-only context. It is not a trading instruction.
