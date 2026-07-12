# BOOK-DATA-01 - Candle Data Availability Audit for Market Reader

## Status

`PASS_WITH_DATA_GAPS`

## Purpose

This stage audits local candle availability for BOOK-L1 Market Reader and explains which symbol/interval combinations can support L1-L2 reports.

## Request

- Symbols: BTCUSDT, ETHUSDT, SOLUSDT
- Intervals: 15m, 1h, 4h
- Window size: 300
- Window count: 4
- Required candles: 1200

## Outputs

- `reports/book_data/candle_availability_audit.json`
- `reports/book_data/candle_availability_audit.md`

## Result summary

- READY: 3
- INSUFFICIENT_DATA: 0
- MISSING: 6
- ERROR: 0

## Main finding

`15m` has enough candles for the tested symbols.

`1h` and `4h` currently have no candles in the local database for the tested symbols.

The current blocker for multi-interval L1-L2 reports is data availability, not the L1-L2 pipeline.

## Safety

Read-only audit.
No download was executed.
No DB writes were executed.
No market analysis logic was changed.
No trading signals were generated.

## Checks

- py_compile: PASS
- targeted tests: PASS
- full relevant pack: PASS
- full repository pytest: BLOCKED by existing ML38 collection error in `tests/test_ml38_10_67_solusdt_sidecar_calibration_replay.py`
- real audit smoke: PASS_WITH_DATA_GAPS
- strict smoke: documented FAIL because data gaps exist
- git diff --cached --check: PASS

## Conclusion

The system now has a dedicated data availability audit explaining why some intervals cannot produce L1-L2 reports yet.
