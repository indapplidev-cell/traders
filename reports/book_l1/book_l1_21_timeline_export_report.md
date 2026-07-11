# BOOK-L1-21 - Market Regime Timeline Export / JSON + Markdown Report

## Status

`PASS`

## Implemented

- Added timeline preview export.
- Added fixed JSON export path.
- Added fixed Markdown export path.
- Added overwrite behavior.
- Added CLI `--export`.
- Added CLI `--export-format`.
- Added CLI `--output-dir`.
- Added interactive export choice.
- Preserved BOOK-L1 safety contract.

## Fixed runtime export files

```text
reports/book_l1/timeline_preview.json
reports/book_l1/timeline_preview.md
```

## Overwrite rule

Runtime export files are overwritten on each export run. Export filenames do not include date, time, version, symbol, interval, or hash suffix.

## Safety

```text
trade_signal = NOT_EVALUATED
safe_for_runtime_trading = false
orders_enabled = false
live_trading_connected = false
approved_for_live_trading = false
```

## Test status

Full BOOK-L1 test pack passed.

## Conclusion

BOOK-L1 can now export the latest timeline preview to stable JSON and Markdown files without creating timestamped report copies and without producing trading signals.
