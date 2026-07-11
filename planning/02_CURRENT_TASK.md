# Current Task

## BOOK-L2-01 - Market Context Classification Rules / Symbol Buckets

Status: `DONE`

Goal:

Add explicit, testable, and extensible BOOK-L2 classification rules for symbol context buckets using the BOOK-L1 timeline JSON export.

Primary input:

```text
reports/book_l1/timeline_preview.json
```

Primary output:

```text
reports/book_l2/timeline_context.json
```

Implemented:

- added `app/market_interpreter/context_rules.py`;
- added `SymbolBucket`, `MarketContextState`, and `SymbolBucketDecision`;
- added `classify_symbol_bucket`;
- added `classify_overall_market_context` for bucket decisions;
- added skip candidate labeling;
- updated the L2 timeline consumer with bucket fields;
- updated terminal output with Bucket and Skip columns;
- updated details output with `context_reason_codes`;
- updated stable JSON export with `bucket`, `skip_candidate`, `context_reason_codes`, `overall_state`, and bucket summary fields;
- preserved fail-closed observe-only safety;
- added focused BOOK-L2 context rules tests;
- updated existing BOOK-L2 timeline context tests;
- added BOOK-L2-01 stage report.

BOOK-L2 boundary:

```text
BOOK-L1 timeline JSON -> observe-only market context interpretation
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
- no LONG / SHORT / BUY / SELL decision generation.

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
- BOOK-L2 context rules tests passed;
- existing BOOK-L2 tests passed;
- fresh BOOK-L1 timeline JSON export passed;
- L1 runtime JSON consumer strict smoke passed;
- L2 default / strict / details / export smoke passed;
- full BOOK-L1 + BOOK-L2 pack passed.

Next possible stage:

```text
BOOK-L2-02 - Context Explanation Layer / Human-Readable Market Notes
```
