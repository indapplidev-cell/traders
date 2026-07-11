# Current Task

## BOOK-L2-00 - Start Layer 2 / Consume BOOK-L1 Timeline JSON

Status: `DONE`

Goal:

Start BOOK-L2 as a safe read-only market context interpreter above the frozen BOOK-L1 Market Reader.

Primary input:

```text
reports/book_l1/timeline_preview.json
```

Implemented:

- added `app/market_interpreter/`;
- added `app/market_interpreter/l1_timeline_consumer.py`;
- added BOOK-L2 fail-closed safety state;
- added BOOK-L1 timeline JSON contract validation;
- added fail-closed input safety validation;
- added symbol-level context labels;
- added overall market context classification;
- added terminal table formatter;
- added optional stable JSON export to `reports/book_l2/timeline_context.json`;
- added CLI command `book-l2-timeline-context`;
- added focused BOOK-L2 tests;
- added BOOK-L2 stage report.

BOOK-L2 boundary:

```text
BOOK-L1 timeline JSON -> market context interpretation
```

Out of scope preserved:

- no candle reads;
- no `CandleRepository` import in BOOK-L2;
- no `MarketReaderOrchestrator` import in BOOK-L2;
- no EMA / ATR / swing / range recalculation;
- no BOOK-L1 JSON semantics changes;
- no BOOK-L1 market analysis changes;
- no model training;
- no Binance download;
- no traders-core connection;
- no live trading connection;
- no order creation;
- no trading signal generation.

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

Command:

```powershell
python -m app.cli.commands book-l2-timeline-context
```

Useful modes:

```powershell
python -m app.cli.commands book-l2-timeline-context --strict
python -m app.cli.commands book-l2-timeline-context --show-details
python -m app.cli.commands book-l2-timeline-context --export-json
```

Completion checks:

- compile check passed;
- BOOK-L2 tests passed;
- L1 runtime JSON consumer smoke passed;
- L2 CLI smoke passed;
- L2 strict/details/export smoke passed;
- full BOOK-L1 pack still passed.

Next possible stage:

```text
BOOK-L2-01 - Market Context Rules / Symbol Buckets
```
