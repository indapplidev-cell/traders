# Current Task

## BOOK-L1-23 - Terminal UX Cleanup / Unified Command Guide

Status: `DONE`

Goal:

Make terminal work with BOOK-L1 clear and unified without changing market-reader analysis logic.

Main command:

```powershell
python -m app.cli.commands book-l1-guide
```

Scope completed:

- added `app.market_reader.terminal_guide`;
- added `book-l1-guide`;
- documented current, API preview, multi-symbol, history, and timeline workflows;
- documented `--export-json` as the recommended API export path;
- documented stable JSON output filenames;
- documented overwrite behavior for runtime JSON export;
- documented that runtime Markdown export is not used as working output;
- kept legacy timeline export compatibility untouched;
- kept fail-closed safety contract unchanged.

Working UX:

```text
Terminal output: for humans
JSON export: for API
Runtime Markdown export: not used
```

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
- no order placement;
- no label, class-weight, or training-objective changes;
- no claim that a trading edge was found.

Completion checks:

- compile check passed;
- `tests/test_book_l1_terminal_guide.py` passed;
- full BOOK-L1 test pack passed;
- CLI help checks passed;
- guide smoke passed;
- no runtime JSON export smoke required for this stage;
- safety validation passed.

Next possible stage:

BOOK-L1-24 - Terminal Output Normalization / Consistent Tables.
