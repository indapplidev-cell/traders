# Current Task

## BOOK-L2-04 - L2 JSON Consumer / Context Contract Smoke

Status: `DONE`

Goal:

Add a consumer-smoke command for the stable BOOK-L2 context JSON export.

Primary input:

```text
reports/book_l2/timeline_context.json
```

Implemented:

- added `app/market_interpreter/json_consumer.py`;
- added `L2ContextConsumerConfig`;
- added `L2ContextConsumerCheck`;
- added `L2ContextConsumerResult`;
- added `L2ContextJsonConsumer`;
- added `L2ContextConsumerFormatter`;
- added CLI command `book-l2-json-consumer-smoke`;
- added default input path `reports/book_l2/timeline_context.json`;
- added `--input-path`;
- added `--strict`;
- added `--show-details`;
- added `--json` stdout mode;
- validated L2 contract version and service/layer identity;
- validated L1 timeline source metadata;
- validated `overall_state`, symbols, buckets, quality score/grade/rank, and ranking consistency;
- validated `market_brief`;
- validated forbidden market brief terms;
- validated fail-closed safety;
- added focused unit tests for the consumer and CLI parser.

BOOK-L2 boundary:

```text
BOOK-L1 JSON -> BOOK-L2 context interpretation -> BOOK-L2 JSON -> consumer validation
```

Out of scope preserved:

- no candle reads;
- no `CandleRepository` import in BOOK-L2;
- no `MarketReaderOrchestrator` import in BOOK-L2;
- no DB access;
- no external exchange access;
- no BOOK-L1 market analysis changes;
- no BOOK-L1 JSON semantics changes;
- no scoring/ranking rule changes;
- no model training;
- no traders-core connection;
- no live trading connection;
- no order creation;
- no trading decisions.

Safety validation:

```text
trade_signal = NOT_EVALUATED
safe_for_runtime_trading = false
orders_enabled = false
live_trading_connected = false
traders_core_connected = false
approved_for_live_trading = false
approved_for_auto_activation = false
```

Command:

```powershell
python -m app.cli.commands book-l2-json-consumer-smoke
```

Useful modes:

```powershell
python -m app.cli.commands book-l2-json-consumer-smoke --strict
python -m app.cli.commands book-l2-json-consumer-smoke --show-details
python -m app.cli.commands book-l2-json-consumer-smoke --json
python -m app.cli.commands book-l2-json-consumer-smoke --input-path reports/book_l2/timeline_context.json
```

Completion checks:

- compile check passed;
- BOOK-L2 JSON consumer tests passed;
- BOOK-L2 targeted pack passed;
- fresh BOOK-L1 timeline JSON export passed;
- L1 runtime JSON consumer strict smoke passed;
- L2 context export passed;
- L2 JSON consumer default / strict / details / JSON stdout smoke passed;
- full BOOK-L1 + BOOK-L2 pack passed;
- forbidden import check passed.

Next possible stage:

```text
BOOK-L2-05 - API Readiness Review / Layer 2 Freeze Candidate
```
