# Data Availability Plan

## Current status

BOOK-DATA-01 is complete.

It adds a read-only candle availability audit for Market Reader:

```powershell
python -m app.cli.commands book-data-candle-availability-audit `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --intervals 15m,1h,4h `
  --window-size 300 `
  --window-count 4 `
  --show-details
```

Stable evidence outputs:

```text
reports/book_data/candle_availability_audit.json
reports/book_data/candle_availability_audit.md
```

## Finding

The current blocker for multi-interval L1-L2 reports is data availability, not the L1-L2 pipeline.

Current audited condition:

- `15m` is ready for BTCUSDT, ETHUSDT, and SOLUSDT;
- `1h` is missing in the local database for the tested symbols;
- `4h` is missing in the local database for the tested symbols.

## Boundary

BOOK-DATA-01 is audit-only.

It does not:

- download data;
- write DB rows;
- create candles;
- aggregate `15m` into `1h` or `4h`;
- change BOOK-L1 analysis logic;
- change BOOK-L2 context logic;
- introduce trading signals.

## Future decisions

After BOOK-DATA-01, decide separately whether:

- Market Reader should operate only on `15m`;
- `1h` and `4h` should be loaded as source data;
- `1h` and `4h` should be built from `15m` in a separate data preparation stage;
- specific intervals should be required for Market Reader reports.
