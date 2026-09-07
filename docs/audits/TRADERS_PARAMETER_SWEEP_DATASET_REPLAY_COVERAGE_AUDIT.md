# Parameter Sweep dataset/replay coverage audit

AUDIT_STATUS = COMPLETE
DATASET_SOURCE = PRODUCTION_PAPER_READONLY
DATASET_PROFILE = trade-5m-v2
DATASET_FINGERPRINT = a940ce77f1d24d33b5f32614bd69ed73367f15bb8deba8f02df06e16d5c5590d
DATASET_ROWS = 53
DATASET_MIN_OPENED_AT_MS = 1788404160000
DATASET_MAX_CLOSED_AT_MS = 1788734100000

## Coverage matrix

| FIELD | ROWS_PRESENT | ROWS_MISSING | COVERAGE_PERCENT | REPLAY_REQUIRED |
|---|---:|---:|---:|---|
| position_id | 53 | 0 | 100.000 | YES |
| command_id | 53 | 0 | 100.000 | YES |
| profile_id | 53 | 0 | 100.000 | YES |
| symbol | 53 | 0 | 100.000 | YES |
| direction | 53 | 0 | 100.000 | YES |
| setup type | 53 | 0 | 100.000 | CAPABILITY_DEPENDENT |
| opened_at | 53 | 0 | 100.000 | YES |
| closed_at | 53 | 0 | 100.000 | YES |
| entry_price | 53 | 0 | 100.000 | YES |
| exit_price | 53 | 0 | 100.000 | YES |
| stop_price | 53 | 0 | 100.000 | YES |
| target_price | 53 | 0 | 100.000 | YES |
| gross_pnl | 53 | 0 | 100.000 | YES |
| net_pnl | 53 | 0 | 100.000 | YES |
| entry_fee | 53 | 0 | 100.000 | YES |
| exit_fee | 53 | 0 | 100.000 | YES |
| commission provenance | 0 | 53 | 0.000 | CAPABILITY_DEPENDENT |
| cost provenance | 53 | 0 | 100.000 | CAPABILITY_DEPENDENT |
| spread/slippage provenance | 53 | 0 | 100.000 | CAPABILITY_DEPENDENT |
| causal_opportunity_id | 0 | 53 | 0.000 | CAPABILITY_DEPENDENT |
| MAE | 1 | 52 | 1.887 | CAPABILITY_DEPENDENT |
| MFE | 1 | 52 | 1.887 | CAPABILITY_DEPENDENT |
| market-data watermark | 53 | 0 | 100.000 | CAPABILITY_DEPENDENT |
| historical observation timestamps | 0 | 53 | 0.000 | CAPABILITY_DEPENDENT |
| historical price/time-stop observations | 0 | 53 | 0.000 | CAPABILITY_DEPENDENT |

## Replay eligibility

BASELINE_REPLAY_ELIGIBLE_ROWS = 53
OUTCOME_ONLY_REPLAY_ROWS = 53
ENTRY_ADMISSION_REPLAY_ELIGIBLE_ROWS = 0
TIME_STOP_REPLAY_ELIGIBLE_ROWS = 0
COST_REPLAY_ELIGIBLE_ROWS = 0
MAE_MFE_REPLAY_ELIGIBLE_ROWS = 1
FULL_REPLAY_ELIGIBLE_ROWS = 0
UNREPLAYABLE_MISSING_MARKET_TIMELINE = 53
PRE_TIME_STOP_INSTRUMENTATION_ROWS = 53
POST_TIME_STOP_INSTRUMENTATION_ROWS = 0

## Contract conclusion

A closed PAPER position is not automatically a causal replay row. All 53 rows
are valid for outcome/accounting replay, but none has a persisted timestamped
market/cost path for hypothetical earlier-exit replay. The prior loader made
this impossible to distinguish because it hard-coded an empty observation list
and then collapsed admission failures into `ALL_TRADES_FILTERED`.

The corrected loader directly consumes
`scalping_stale_position_shadow_diagnostics`, preserving its causal evaluation
boundary and historical cost provenance. No current price or commission is
substituted. For this exact production sample that authoritative join returns
zero observations, so the correct result is
`NO_REPLAYABLE_ROWS_FOR_REQUIRED_DIMENSIONS`, with search aborted before any
sampled configuration is evaluated.

SMOKE_RUN = codex-replay-correctness-smoke-20260907-181004
SMOKE_STATUS = INSUFFICIENT_REPLAY_DATA_EXPECTED_FAIL_CLOSED
SMOKE_CONFIGS_EVALUATED = 0
SEARCH_ABORTED_BEFORE_5000_CONFIGS = YES
PRODUCTION_MUTATIONS = 0
PRODUCTION_CONFIG_WRITES = 0
BINANCE_ORDER_CALLS = 0
LIVE = DISABLED_UNCHANGED
