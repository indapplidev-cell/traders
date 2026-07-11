# Current Task

## BOOK-L1-22 - Unified JSON Export Contract / API Output Files

Status: `DONE`

Goal:

Make stable API-oriented JSON output available for all main BOOK-L1 preview modes:

```text
current preview
multi-symbol preview
history snapshot
timeline preview
```

Scope completed:

- added `app.market_reader.json_export`;
- added unified envelope with `status`, `service`, `report_type`, `contract_version`, `request`, `result`, `summary`, `safety`, `warnings`, and `errors`;
- added `contract_version = book_l1_json_export_v1`;
- added `service = BOOK_L1_MARKET_READER`;
- added fail-closed `BookL1JsonExportSafety`;
- added stable JSON writer with overwrite behavior;
- added `--export-json` and `--output-dir` to `book-l1-preview`;
- added `--export-json` and `--output-dir` to `book-l1-multi-preview`;
- added `--export-json` and `--output-dir` to `book-l1-history-preview`;
- added `--export-json` to `book-l1-timeline-preview`;
- kept legacy timeline `--export` / `--export-format` compatibility;
- kept runtime Markdown export out of the new API output path.

Stable runtime JSON files:

```text
reports/book_l1/current_preview.json
reports/book_l1/multi_preview.json
reports/book_l1/history_preview.json
reports/book_l1/timeline_preview.json
```

Overwrite rule:

Runtime JSON export files are overwritten on each `--export-json` run. Export filenames do not include date, time, version, symbol, interval, stage number, UUID, or hash suffix.

Out of scope:

- no model training;
- no Binance download;
- no traders-core connection;
- no live trading integration;
- no trading signal generation;
- no LONG / SHORT / BUY / SELL;
- no order placement;
- no label, class-weight, or training-objective changes;
- no claim that a trading edge was found.

Completion checks:

- compile check passed;
- `tests/test_book_l1_json_export.py` passed;
- full BOOK-L1 test pack passed;
- CLI help checks passed;
- manual smoke JSON exports passed;
- repeated export overwrote the same runtime JSON file;
- JSON contract validation passed;
- JSON safety validation passed.

Next possible stage:

BOOK-L1-23 - API Reader Contract / Load JSON Exports for External Service.
