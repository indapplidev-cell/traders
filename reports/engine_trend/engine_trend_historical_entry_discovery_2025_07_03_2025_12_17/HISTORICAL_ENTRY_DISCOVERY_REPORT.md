# ENGINE-TREND Historical Entry Discovery Audit

## Executive result

A full causal scan of all three Binance Spot 15m series produced **449** deduplicated candidates, all **449** satisfying RR ≥ 1.5. The database was complete; no Binance download ran. The selected entry is `ET-HED-0001`: **BTCUSDT SHORT**, entry `2025-12-01T13:30:00Z` at **85994.0**, stop **86215.63920478**, target **84756.0**, RR **5.586**, setup **SHORT_DOWN_CONTINUATION_RETEST**. Outcome: **SL_BEFORE_TP**.

## Method and hindsight controls

Each decision point used at least 96 closed context candles and a 24-candle decision window. Pivots required two right-hand candles to be confirmed. Entry was fixed at the next 15-minute boundary at the confirmation close price; invalidation, stop, target, RR, and score were generated from that prefix only. Candidates were sorted and `main_selected_candidate_id=ET-HED-0001` was frozen before either current-engine enrichment or the outcome function. The unchanged current engine then confirmed the pre-entry context for top-10 candidates. The 96-candle future horizon was finally evaluated with same-candle TP+SL labeled `AMBIGUOUS_INTRACANDLE`.

## Data quality

Each symbol had `16128` requested candles. All coverage, cadence, duplicate, OHLC, finite-value, positive-value, and closed-candle checks passed. See `HISTORICAL_ENTRY_DISCOVERY_DATA_COVERAGE.md`.

## MAIN_SELECTED_ENTRY

See `MAIN_SELECTED_ENTRY_EXPLANATION.md` for the complete Altunina, Schwager, Nison, technical, invalidation, risk, and outcome analysis. Summary: the setup followed a pre-existing causal structure and level; the confirmation candle authorized entry only after the correction/retest. This is **trend-following**, not a hindsight-selected reversal.

## Alternatives

- `ET-HED-0002` BTCUSDT SHORT at `2025-10-30T07:00:00Z`, SHORT_DOWN_CONTINUATION_RETEST, RR `8.558`, pre-entry score `83.912`. Rejected as MAIN because its pre-entry score was lower; outcome was not considered.
- `ET-HED-0003` SOLUSDT LONG at `2025-11-15T18:45:00Z`, LONG_UP_CONTINUATION_RETEST, RR `4.096`, pre-entry score `83.597`. Rejected as MAIN because its pre-entry score was lower; outcome was not considered.
- `ET-HED-0004` SOLUSDT SHORT at `2025-07-12T00:15:00Z`, SHORT_DOWN_CONTINUATION_RETEST, RR `4.037`, pre-entry score `83.336`. Rejected as MAIN because its pre-entry score was lower; outcome was not considered.
- `ET-HED-0005` BTCUSDT SHORT at `2025-07-30T21:15:00Z`, SHORT_DOWN_CONTINUATION_RETEST, RR `4.738`, pre-entry score `83.310`. Rejected as MAIN because its pre-entry score was lower; outcome was not considered.
- `ET-HED-0006` BTCUSDT SHORT at `2025-10-10T23:15:00Z`, SHORT_DOWN_CONTINUATION_RETEST, RR `8.196`, pre-entry score `83.194`. Rejected as MAIN because its pre-entry score was lower; outcome was not considered.
- `ET-HED-0007` SOLUSDT SHORT at `2025-10-16T11:00:00Z`, SHORT_DOWN_CONTINUATION_RETEST, RR `8.029`, pre-entry score `83.159`. Rejected as MAIN because its pre-entry score was lower; outcome was not considered.
- `ET-HED-0008` SOLUSDT SHORT at `2025-10-22T02:30:00Z`, SHORT_DOWN_CONTINUATION_RETEST, RR `4.383`, pre-entry score `83.132`. Rejected as MAIN because its pre-entry score was lower; outcome was not considered.
- `ET-HED-0009` BTCUSDT SHORT at `2025-10-14T11:45:00Z`, SHORT_DOWN_CONTINUATION_RETEST, RR `3.624`, pre-entry score `83.053`. Rejected as MAIN because its pre-entry score was lower; outcome was not considered.
- `ET-HED-0010` BTCUSDT LONG at `2025-08-31T05:00:00Z`, LONG_UP_CONTINUATION_RETEST, RR `3.279`, pre-entry score `83.042`. Rejected as MAIN because its pre-entry score was lower; outcome was not considered.

## Safety boundary

- Runtime code changed: no.
- Trading runtime changed: no.
- Thresholds changed: no.
- Composer changed: no.
- Market hypothesis changed: no.
- Setup contracts changed: no.
- This script is offline/audit-only and creates reports; it does not place or simulate orders in runtime.

## Verification

- `python -m pytest tests/test_engine_trend_*.py` (PowerShell-expanded file list): **305 passed in 29.75s**.
- Audit script `py_compile`: **PASS**.
- JSON/CSV/manifest readback: **PASS**; 449 candidate rows and all recorded SHA-256 hashes verified.
- `git diff --check`: **PASS** (exit 0).
- Commit created: **no**.
