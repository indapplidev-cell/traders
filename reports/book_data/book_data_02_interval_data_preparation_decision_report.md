# BOOK-DATA-02 - Interval Data Preparation Decision

## Status

`PASS_WITH_DATA_GAPS`

## Purpose

This stage fixes the data preparation decision after BOOK-DATA-01 showed that 15m is ready while 1h and 4h are missing from the local database.

## Source

`reports/book_data/candle_availability_audit.json`

## Decision

`ACTIVE_INTERVAL_15M_ONLY_WITH_1H_4H_MISSING`

## Recommended option

`OPTION_D_HYBRID_LATER`

## Immediate action

Use `15m` as the active working interval for BOOK-L1 Market Reader.

## Intervals

- `15m`: active / ready
- `1h`: optional / missing
- `4h`: optional / missing

## Not approved in this stage

- Binance download
- DB writes
- 15m to 1h/4h aggregation
- Trading logic
- LONG/SHORT recommendations
- Edge validation

## Outputs

- `reports/book_data/interval_data_preparation_decision.json`
- `reports/book_data/interval_data_preparation_decision.md`

## Checks

- py_compile: PASS
- targeted decision tests: PASS
- DATA targeted pack: PASS
- relevant BOOK-L1/L2/DATA pack: PASS
- real decision smoke: PASS_WITH_DATA_GAPS
- strict smoke: documented FAIL because `1h`/`4h` are missing
- forbidden operation check: PASS
- git diff --cached --check: PASS

## Conclusion

The current Market Reader workflow continues on `15m`.
Missing `1h` and `4h` should not block BOOK-L1/BOOK-L2 progress.
Preparation of `1h` and `4h` requires a separate explicit BOOK-DATA stage.
