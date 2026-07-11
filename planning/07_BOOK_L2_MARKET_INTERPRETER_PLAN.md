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
| BOOK-L2-02 | Context Explanation Layer / Human-Readable Market Notes | PLANNED | observe-only explanations |

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

## Planned direction

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

The next stages must keep the same boundary: consume BOOK-L1 JSON, preserve fail-closed safety, and avoid trading signals.

BOOK-L2-02 can add short human-readable explanations for symbol buckets and overall context while remaining observe-only.
