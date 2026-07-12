# Current Task

## BOOK-DATA-02 - Interval Data Preparation Decision

Status: `DONE`

Goal:

Fix the technical decision for missing `1h` and `4h` candle intervals after BOOK-DATA-01 showed that `15m` is ready while `1h` and `4h` are missing from the local database.

Command:

```powershell
python -m app.cli.commands book-data-interval-preparation-decision --show-details
```

Strict command:

```powershell
python -m app.cli.commands book-data-interval-preparation-decision --strict --show-details
```

Evidence outputs:

```text
reports/book_data/interval_data_preparation_decision.json
reports/book_data/interval_data_preparation_decision.md
reports/book_data/book_data_02_interval_data_preparation_decision_report.md
```

Implemented:

- added `app/data_audit/interval_preparation_decision.py`;
- added CLI command `book-data-interval-preparation-decision`;
- added `--audit-json`, `--output-json`, `--output-md`, `--strict`, `--show-details`;
- added focused unit tests with fake audit JSON;
- added stable JSON and Markdown decision files;
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
- BOOK-L1/L2 multi-interval smoke may continue to include `1h`/`4h` only as documented missing intervals.

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

Next data work requires a separate explicit BOOK-DATA stage.
