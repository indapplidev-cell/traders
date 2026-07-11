# BOOK-L2 Market Interpreter Plan

## Layer definition

BOOK-L2 is the market interpretation layer above BOOK-L1:

```text
BOOK-L1 timeline JSON -> observe-only market context
```

BOOK-L2 consumes stable BOOK-L1 JSON output. It does not read candles and does not recalculate BOOK-L1 technical analysis.

## Safety boundary

BOOK-L2 must remain fail-closed:

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

BOOK-L2 does not generate trading signals, does not create orders, does not connect to live trading, and does not connect to traders-core.

## Stage checklist

| Stage | Name | Status | Main artifact |
| --- | --- | --- | --- |
| BOOK-L2-00 | Start Layer 2 / Consume BOOK-L1 Timeline JSON | DONE | `app/market_interpreter/l1_timeline_consumer.py` |
| BOOK-L2-01 | Market Context Rules / Symbol Buckets | DONE | `app/market_interpreter/context_rules.py` |
| BOOK-L2-02 | Context Quality Score / Symbol Ranking | DONE | `app/market_interpreter/context_quality.py` |
| BOOK-L2-03 | Context Summary / Human Market Brief | DONE | `app/market_interpreter/context_summary.py` |
| BOOK-L2-04 | Market Context API Export Contract / L2 JSON Consumer | PLANNED | L2 JSON consumer contract |

## BOOK-L2-00

BOOK-L2-00 reads:

```text
reports/book_l1/timeline_preview.json
```

It validates:

- BOOK-L1 service name;
- BOOK-L1 report type;
- BOOK-L1 contract version;
- required envelope keys;
- fail-closed safety;
- presence of timeline rows.

It produces:

- symbol context labels;
- overall market context;
- terminal observe-only table;
- optional stable JSON export.

Stable export:

```text
reports/book_l2/timeline_context.json
```

Command:

```powershell
python -m app.cli.commands book-l2-timeline-context
```

## BOOK-L2-01

BOOK-L2-01 deepened observe-only classification:

- clean trend symbols;
- stable flat symbols;
- transitioning symbols;
- unstable symbols;
- unknown symbols;
- insufficient data symbols;
- error symbols;
- skip candidate labels;
- overall market context state.

BOOK-L2-01 keeps the same input and output:

```text
reports/book_l1/timeline_preview.json -> reports/book_l2/timeline_context.json
```

BOOK-L2-01 does not read candles and does not create trading signals.

## BOOK-L2-02

BOOK-L2-02 added context quality scoring and deterministic symbol ranking.

Per-symbol output includes:

```text
context_quality_score
context_quality_grade
context_rank
context_quality_reason_codes
```

Summary output includes:

```text
quality_summary
top_ranked_symbols
```

BOOK-L2-02 still consumes only:

```text
reports/book_l1/timeline_preview.json
```

BOOK-L2-02 still writes:

```text
reports/book_l2/timeline_context.json
```

BOOK-L2-02 does not read candles, does not connect to DB or Binance, does not use `CandleRepository` or `MarketReaderOrchestrator`, and does not produce trading decisions.

## BOOK-L2-03

BOOK-L2-03 added a short human-readable market context brief.

The stable export now includes:

```text
market_brief
brief_state
observation_candidates
skip_candidates
key_points
safety_note
```

The terminal command prints the brief after the context table, and details mode includes each symbol's `main_reason` and membership in observation or skip lists.

BOOK-L2-03 still consumes only:

```text
reports/book_l1/timeline_preview.json
```

BOOK-L2-03 still writes:

```text
reports/book_l2/timeline_context.json
```

The summary uses observation candidates, not trade candidates. It does not add trading signals or trading decisions.

## Planned direction

The next stages must keep the same boundary: consume BOOK-L1 JSON, preserve fail-closed safety, and avoid trading signals.

BOOK-L2-04 can add a stable L2 JSON consumer/API contract check for `reports/book_l2/timeline_context.json`.
