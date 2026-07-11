# Current Task

## BOOK-L1-21 - Market Regime Timeline Export / JSON + Markdown Report

Status: `DONE`

Goal:

Add stable file export to the existing timeline preview command:

```powershell
python -m app.cli.commands book-l1-timeline-preview --export
```

Scope completed:

- added `app.market_reader.timeline_export`;
- added fixed JSON export path: `reports/book_l1/timeline_preview.json`;
- added fixed Markdown export path: `reports/book_l1/timeline_preview.md`;
- added overwrite-only write behavior for runtime export files;
- added CLI `--export`;
- added CLI `--export-format` with `all`, `json`, and `md`;
- added CLI `--output-dir` while keeping filenames fixed;
- added interactive export choice: none, all, json, or markdown;
- added JSON contract fields: `service`, `export_type`, `contract_version`, `config`, `summary`, `rows`, `warnings`, `safety`;
- added compact Markdown report with config, timeline table, summary, warnings, safety, and conclusion;
- preserved the BOOK-L1 read-only safety contract.

Stable runtime export files:

```text
reports/book_l1/timeline_preview.json
reports/book_l1/timeline_preview.md
```

Overwrite rule:

Runtime export files are overwritten on each export run. Export filenames do not include date, time, version, symbol, interval, stage number, or hash suffix.

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

Completion criteria:

- `book-l1-timeline-preview --export` writes JSON and Markdown;
- `--export-format json` writes only `timeline_preview.json`;
- `--export-format md` writes only `timeline_preview.md`;
- `--output-dir` changes only the directory, not filenames;
- repeated exports overwrite the same files;
- JSON is valid UTF-8 and machine-readable;
- Markdown is compact and human-readable;
- safety is explicit in both files;
- interactive mode can choose export or no export;
- unit tests pass;
- full BOOK-L1 test pack passes;
- CLI help shows the new options;
- smoke and overwrite checks pass.

Next possible stage:

BOOK-L1-22 - Market Regime Decision Notes / Human Explanation Layer. This should remain explanatory and must not produce trading decisions or live-trading approval.
