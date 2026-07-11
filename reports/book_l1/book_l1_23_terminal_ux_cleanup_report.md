# BOOK-L1-23 - Terminal UX Cleanup / Unified Command Guide

## Status

`PASS`

## Implemented

- Added BOOK-L1 terminal command guide.
- Added `book-l1-guide` CLI command.
- Documented current, multi, history, timeline workflows.
- Documented JSON export workflow for API.
- Documented stable JSON output files.
- Documented that runtime Markdown export is not used for working output.
- Preserved fail-closed safety contract.
- Did not change market analysis logic.

## Main command

```powershell
python -m app.cli.commands book-l1-guide
```

## Runtime output policy

```text
Terminal output: for humans
JSON export: for API
Runtime Markdown export: not used
```

## Stable API JSON files

```text
reports/book_l1/current_preview.json
reports/book_l1/multi_preview.json
reports/book_l1/history_preview.json
reports/book_l1/timeline_preview.json
```

## Safety

```text
trade_signal = NOT_EVALUATED
safe_for_runtime_trading = false
orders_enabled = false
live_trading_connected = false
approved_for_live_trading = false
```

## Test status

BOOK-L1 tests passed.

## Conclusion

BOOK-L1 terminal usage is now documented through a unified CLI guide without changing the market reader logic or enabling trading behavior.
