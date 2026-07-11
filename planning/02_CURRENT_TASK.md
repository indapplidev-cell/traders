# Current Task

## BOOK-L1-24 - Runtime JSON Consumer / API Reader Smoke

Status: `DONE`

Goal:

Add a small read-only consumer layer that validates whether a future external API layer can safely and stably read BOOK-L1 JSON export files.

Main command:

```powershell
python -m app.cli.commands book-l1-json-consumer-smoke --strict
```

Scope completed:

- added `app.market_reader.json_consumer`;
- added `book-l1-json-consumer-smoke`;
- validates fixed runtime JSON export filenames;
- validates top-level JSON object envelope;
- validates required top-level keys;
- validates `service = BOOK_L1_MARKET_READER`;
- validates `contract_version = book_l1_json_export_v1`;
- validates report type per filename;
- validates `request`, `summary`, and `safety` object shape;
- validates `warnings` and `errors` list shape;
- validates fail-closed safety fields;
- prints terminal API-reader smoke table;
- supports `--input-dir`, `--report-types`, `--strict`, and `--show-details`;
- updates `book-l1-guide` with JSON consumer smoke workflow.

Stable runtime JSON files:

```text
reports/book_l1/current_preview.json
reports/book_l1/multi_preview.json
reports/book_l1/history_preview.json
reports/book_l1/timeline_preview.json
```

Safety validation:

```text
trade_signal = NOT_EVALUATED
safe_for_runtime_trading = false
orders_enabled = false
live_trading_connected = false
traders_core_connected = false
approved_for_live_trading = false
approved_for_auto_activation = false
model_training_executed = false
binance_download_executed = false
```

Out of scope preserved:

- no market analysis logic changes;
- no JSON export semantics changes;
- no runtime Markdown API output;
- no model training;
- no Binance download;
- no traders-core connection;
- no live trading integration;
- no trading signal generation;
- no order placement.

Completion checks:

- compile check passed;
- `tests/test_book_l1_json_consumer.py` passed;
- full BOOK-L1 test pack passed;
- CLI help checks passed;
- manual JSON consumer smoke passed;
- safety contract remains fail-closed.

Next possible stage:

BOOK-L1-25 - Local API Facade / Read-Only JSON Endpoint Prototype.
