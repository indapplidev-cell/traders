# Current Task

## BOOK-L2-02 - Context Quality Score / Symbol Ranking

Status: `DONE`

Goal:

Add observe-only context quality scoring and deterministic symbol ranking to BOOK-L2 using only the BOOK-L1 timeline JSON export.

Primary input:

```text
reports/book_l1/timeline_preview.json
```

Primary output:

```text
reports/book_l2/timeline_context.json
```

Implemented:

- added `app/market_interpreter/context_quality.py`;
- added `ContextQualityGrade`, `ContextQualityConfig`, `ContextQualityScore`, and `ContextQualityScorer`;
- added deterministic `rank_symbol_contexts`;
- added `summarize_quality_distribution`;
- added per-symbol `context_quality_score`, `context_quality_grade`, `context_rank`, and `context_quality_reason_codes`;
- added `quality_summary` and `top_ranked_symbols`;
- updated terminal output with Quality, Score, and Rank;
- updated details output with quality reason codes;
- updated strict validation for score, grade, rank, and fail-closed safety;
- updated stable BOOK-L2 export at `reports/book_l2/timeline_context.json`;
- preserved observe-only / fail-closed safety.

BOOK-L2 boundary:

```text
BOOK-L1 timeline JSON -> observe-only market context interpretation and context quality ranking
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
```

Completion checks:

- compile check passed;
- BOOK-L2 context quality tests passed;
- BOOK-L2 context rules tests passed;
- BOOK-L2 timeline context tests passed;
- fresh BOOK-L1 timeline JSON export passed;
- L1 runtime JSON consumer strict smoke passed;
- L2 default / strict / details / export smoke passed;
- full BOOK-L1 + BOOK-L2 pack passed;
- forbidden import check passed.

Next possible stage:

```text
BOOK-L2-03 - Observation Notes / Human Market Context Summary
```
