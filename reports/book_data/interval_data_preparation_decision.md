# BOOK-DATA-02 - Interval Data Preparation Decision

## Status

`PASS_WITH_DATA_GAPS`

## Source

`reports/book_data/candle_availability_audit.json`

## Audit Finding

| Interval | Availability | Meaning |
|---|---|---|
| 15m | READY | Can be used now for BOOK-L1 Market Reader |
| 1h | MISSING | Not available in local DB |
| 4h | MISSING | Not available in local DB |

## Decision

`ACTIVE_INTERVAL_15M_ONLY_WITH_1H_4H_MISSING`

## Recommended Option

`OPTION_D_HYBRID_LATER`

## Immediate Action

Use 15m as active working interval for BOOK-L1 Market Reader.

## Required Intervals For Current Market Reader

| Interval | Required Now | Status |
|---|---|---|
| 15m | yes | READY |
| 1h | no | MISSING |
| 4h | no | MISSING |

## Options Considered

### Option A - 15m only for now

- Status: `AVAILABLE_NOW`
- Recommendation: `safe immediate path`

Pros:

- already has data
- L1-L2 pipeline already works
- can continue improving market reading
- no DB corruption risk
- no incorrect aggregation risk

Cons:

- no multi-timeframe picture
- cannot compare 15m/1h/4h
- L2 multi-interval evidence will show gaps

### Option B - Native 1h/4h loading later

- Status: `FUTURE_STAGE_REQUIRED`
- Recommendation: `not approved in BOOK-DATA-02`

Pros:

- clean native intervals
- simpler coverage checks
- does not depend on resampling quality

Cons:

- requires separate data loading stage
- may require Binance/source integration
- cannot be done in BOOK-DATA-02

### Option C - Build 1h/4h from 15m later

- Status: `FUTURE_STAGE_REQUIRED`
- Recommendation: `requires separate resampling contract`

Pros:

- does not require downloading additional intervals
- can derive multi-interval data from existing 15m

Cons:

- requires strict resampling contract
- must verify open/high/low/close/volume
- must verify time boundaries
- needs tests for incomplete candles
- cannot be done in BOOK-DATA-02

### Option D - Hybrid later

- Status: `RECOMMENDED`
- Recommendation: `recommended for current project state`

Pros:

- does not block current progress
- preserves safe architecture
- defers technical risk

Cons:

- decision for 1h/4h is deferred
- requires next data preparation plan

## Not Approved In This Stage

- Binance download
- DB writes
- 15m to 1h/4h aggregation
- Trading logic
- LONG/SHORT recommendations
- Edge validation

## Next Stage

`BOOK-DATA-03`

Possible scope:

- native 1h/4h loading plan;
- or 15m to 1h/4h aggregation contract;
- or explicitly keep 15m-only until Market Reader quality improves.

## Safety

- read_only: `true`
- download_approved: `false`
- db_write_approved: `false`
- aggregation_approved: `false`
- trading_signal: `NOT_EVALUATED`
- safe_for_runtime_trading: `false`

## Conclusion

The current Market Reader workflow should continue on `15m`.
Missing `1h` and `4h` data should not block BOOK-L1/BOOK-L2 progress.
Preparation of `1h` and `4h` requires a separate explicit stage.
