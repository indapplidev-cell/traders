# Current Task

## BOOK-DATA-03C - 15m-Only Market Reader Stabilization

Status: `DONE`

Goal:

Stabilize the current 15m-only Market Reader workflow after BOOK-DATA-02 fixed `15m` as the active interval.

Command:

```powershell
python -m app.cli.commands book-data-15m-stabilization `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --interval 15m `
  --window-size 300 `
  --window-count 4 `
  --min-candles 50 `
  --strict `
  --show-details
```

Evidence outputs:

```text
reports/book_data/market_reader_15m_stabilization.json
reports/book_data/market_reader_15m_stabilization.md
reports/book_data/book_data_03c_15m_only_market_reader_stabilization_report.md
```

Implemented:

- added `app/data_audit/market_reader_15m_stabilization.py`;
- added CLI command `book-data-15m-stabilization`;
- added `--symbols`, `--symbol`, `--interval`, `--window-size`, `--window-count`, `--min-candles`, `--output-json`, `--output-md`, `--strict`, `--show-details`;
- added focused unit tests with fake services and fake JSON;
- added stable JSON and Markdown stabilization files;
- updated terminal guide and planning.

Current decision:

```text
ACTIVE_INTERVAL_15M_ONLY_WITH_1H_4H_MISSING
```

Recommended option:

```text
OPTION_D_HYBRID_LATER
```

Current finding:

```text
15m: READY for BTCUSDT, ETHUSDT, SOLUSDT
1h: MISSING for BTCUSDT, ETHUSDT, SOLUSDT
4h: MISSING for BTCUSDT, ETHUSDT, SOLUSDT
```

Current workflow decision:

- `15m` is the active working interval for the current Market Reader workflow;
- `1h` and `4h` are optional/missing and should not block current BOOK-L1/BOOK-L2 work;
- BOOK-DATA-03C stabilized the current DATA -> BOOK-L1 -> BOOK-L2 path on `15m`.

Stabilized checks:

- interval policy 15m only;
- candle availability on 15m;
- interval preparation decision;
- L1 timeline export on 15m;
- L1 JSON consumer strict;
- L2 context export on 15m;
- L2 JSON consumer strict;
- L2 API readiness strict;
- L1-L2 interval answer smoke on 15m;
- safety fail-closed;
- evidence writing.

Out of scope preserved:

- no Binance download;
- no DB writes;
- no candle creation;
- no `15m` to `1h`/`4h` aggregation;
- no BOOK-L1 analysis changes;
- no BOOK-L2 context changes;
- no JSON export semantic changes for BOOK-L1/BOOK-L2;
- no training;
- no label changes;
- no trading signals;
- no edge validation;
- no runtime trading integration.

The next work should improve Market Reader quality on 15m before expanding intervals, unless explicitly decided otherwise.
