# Current Task

## BOOK-L1-25 - API Readiness Final Review / Layer 1 Freeze Candidate

Status: `DONE`

Goal:

Run the final read-only review that confirms BOOK-L1 is ready to be treated as a frozen Layer 1 market reader for terminal use and API JSON consumption.

Main command:

```powershell
python -m app.cli.commands book-l1-api-readiness-review
```

Scope completed:

- added `app.market_reader.api_readiness_review`;
- added `book-l1-api-readiness-review`;
- checks required BOOK-L1 modules;
- checks required BOOK-L1 tests;
- checks planning files;
- checks required BOOK-L1 CLI command registration;
- checks stable JSON export files when they exist;
- treats missing runtime JSON files as WARN after clean checkout/export not run;
- treats invalid JSON as FAIL;
- treats wrong `service` as FAIL;
- treats wrong `contract_version` as FAIL;
- treats missing or unsafe core safety fields as FAIL;
- prints a PASS/WARN/FAIL terminal review table;
- prints Layer 1 freeze candidate YES/NO;
- supports `--strict`, `--show-details`, and `--project-root`;
- updates `book-l1-guide` with API readiness / freeze review workflow.

Stable runtime JSON files:

```text
reports/book_l1/current_preview.json
reports/book_l1/multi_preview.json
reports/book_l1/history_preview.json
reports/book_l1/timeline_preview.json
```

JSON contract:

```text
contract_version = book_l1_json_export_v1
service = BOOK_L1_MARKET_READER
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

Layer boundary:

```text
Terminal = for humans
JSON = for API/runtime consumers
Runtime Markdown = not a working output
Trading execution = prohibited
```

Out of scope preserved:

- no market analysis logic changes;
- no JSON export semantics changes;
- no runtime Markdown API output;
- no model training;
- no Binance download;
- no traders-core execution connection;
- no live trading integration;
- no trading signal generation;
- no order placement.

Completion checks:

- compile check passed;
- `tests/test_book_l1_api_readiness_review.py` passed;
- full BOOK-L1 test pack passed;
- CLI help checks passed;
- manual JSON consumer smoke passed;
- manual API readiness review smoke passed;
- safety contract remains fail-closed.

Result:

BOOK-L1 is a `Layer 1 Freeze Candidate`.

Next possible stages:

1. `BOOK-L1-FREEZE` - officially freeze Layer 1 boundaries.
2. `BOOK-L2-00` - plan the next layer above the read-only market reader.
