# Current Task

## BOOK-DATA-01 - Candle Data Availability Audit for Market Reader

Status: `DONE`

Goal:

Audit local candle availability for BOOK-L1 Market Reader and explain which `symbol/interval` combinations can support L1-L2 reports.

Command:

```powershell
python -m app.cli.commands book-data-candle-availability-audit `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --intervals 15m,1h,4h `
  --window-size 300 `
  --window-count 4 `
  --show-details
```

Strict command:

```powershell
python -m app.cli.commands book-data-candle-availability-audit `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --intervals 15m,1h,4h `
  --window-size 300 `
  --window-count 4 `
  --strict `
  --show-details
```

Evidence outputs:

```text
reports/book_data/candle_availability_audit.json
reports/book_data/candle_availability_audit.md
reports/book_data/book_data_01_candle_availability_audit_report.md
```

Implemented:

- added `app/data_audit/candle_availability.py`;
- added CLI command `book-data-candle-availability-audit`;
- added `--symbols`, `--symbol`, `--intervals`, `--window-size`, `--window-count`;
- added `--required-candles`, `--output-json`, `--output-md`, `--strict`, `--show-details`;
- added read-only candle repository count and open-time bounds methods;
- added focused unit tests with fake repository;
- added stable JSON and Markdown evidence files;
- updated terminal guide and planning.

Current finding:

```text
15m: READY for BTCUSDT, ETHUSDT, SOLUSDT
1h: MISSING for BTCUSDT, ETHUSDT, SOLUSDT
4h: MISSING for BTCUSDT, ETHUSDT, SOLUSDT
```

The current blocker for multi-interval L1-L2 reports is data availability, not the L1-L2 pipeline.

Out of scope preserved:

- no Binance download;
- no DB writes;
- no candle creation;
- no 15m to 1h/4h aggregation;
- no BOOK-L1 analysis changes;
- no BOOK-L2 context changes;
- no JSON export semantic changes for BOOK-L1/BOOK-L2;
- no training;
- no label changes;
- no trading signals.
