# Data Availability Plan

## Current status

BOOK-DATA-01 and BOOK-DATA-02 are complete.

BOOK-DATA-01 added a read-only candle availability audit for Market Reader:

```powershell
python -m app.cli.commands book-data-candle-availability-audit `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --intervals 15m,1h,4h `
  --window-size 300 `
  --window-count 4 `
  --show-details
```

Stable audit outputs:

```text
reports/book_data/candle_availability_audit.json
reports/book_data/candle_availability_audit.md
```

BOOK-DATA-02 fixed the interval preparation decision:

```powershell
python -m app.cli.commands book-data-interval-preparation-decision --show-details
```

Stable decision outputs:

```text
reports/book_data/interval_data_preparation_decision.json
reports/book_data/interval_data_preparation_decision.md
reports/book_data/book_data_02_interval_data_preparation_decision_report.md
```

## Finding

The current blocker for multi-interval L1-L2 reports is data availability, not the L1-L2 pipeline.

Current audited condition:

- `15m` is ready for BTCUSDT, ETHUSDT, and SOLUSDT;
- `1h` is missing in the local database for the tested symbols;
- `4h` is missing in the local database for the tested symbols.

## Decision

BOOK-DATA-02 decision:

```text
ACTIVE_INTERVAL_15M_ONLY_WITH_1H_4H_MISSING
```

Recommended option:

```text
OPTION_D_HYBRID_LATER
```

Immediate action:

- use `15m` as the active working interval for the current Market Reader workflow;
- treat `1h` and `4h` as optional/missing;
- do not block current BOOK-L1/BOOK-L2 work on missing `1h`/`4h`.

## Boundary

BOOK-DATA-02 is decision-only.

It does not approve:

- download data;
- write DB rows;
- create candles;
- aggregate `15m` into `1h` or `4h`;
- change BOOK-L1 analysis logic;
- change BOOK-L2 context logic;
- introduce trading signals;
- validate edge;
- integrate runtime trading.

## Future decisions

Next data work requires a separate explicit BOOK-DATA stage.

Possible future stages:

- `BOOK-DATA-03A` - Native 1h/4h Data Loading Plan;
- `BOOK-DATA-03B` - 15m to 1h/4h Aggregation Contract;
- `BOOK-DATA-03C` - 15m-Only Market Reader Stabilization.
