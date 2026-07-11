# Current Task

## BOOK-L2-03 - Context Summary / Human Market Brief

Status: `DONE`

Goal:

Add a short human-readable market context summary to BOOK-L2 using only the BOOK-L1 timeline JSON export.

Primary input:

```text
reports/book_l1/timeline_preview.json
```

Primary output:

```text
reports/book_l2/timeline_context.json
```

Implemented:

- added `app/market_interpreter/context_summary.py`;
- added `MarketBriefConfig`, `SymbolBrief`, `MarketBrief`, and `ContextSummaryBuilder`;
- added deterministic `observation_candidates`;
- added deterministic `skip_candidates`;
- added `brief_state`, `key_points`, `warnings`, and `safety_note`;
- added `market_brief` to stable BOOK-L2 export;
- updated terminal output with a human market brief;
- updated details output with `main_reason` and market brief membership;
- updated strict validation for `market_brief`;
- preserved observe-only / fail-closed safety.

BOOK-L2 boundary:

```text
BOOK-L1 timeline JSON -> observe-only market context interpretation and human market brief
```

Out of scope preserved:

- no candle reads;
- no `CandleRepository` import in BOOK-L2;
- no `MarketReaderOrchestrator` import in BOOK-L2;
- no DB access;
- no Binance download;
- no BOOK-L1 market analysis changes;
- no BOOK-L1 JSON semantics changes;
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
python -m app.cli.commands book-l2-timeline-context --export
python -m app.cli.commands book-l2-timeline-context --show-details --export
```

Completion checks:

- compile check passed;
- BOOK-L2 context summary tests passed;
- BOOK-L2 context rules tests passed;
- BOOK-L2 timeline context tests passed;
- fresh BOOK-L1 timeline JSON export passed;
- L1 runtime JSON consumer strict smoke passed;
- L2 default / strict / details / export smoke passed;
- full BOOK-L1 + BOOK-L2 pack passed;
- forbidden import check passed.

Next possible stage:

```text
BOOK-L2-04 - Market Context API Export Contract / L2 JSON Consumer
```
