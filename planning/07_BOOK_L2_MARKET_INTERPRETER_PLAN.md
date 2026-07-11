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
| BOOK-L2-04 | L2 JSON Consumer / Context Contract Smoke | DONE | `app/market_interpreter/json_consumer.py` |
| BOOK-L2-05 | API Readiness Review / Layer 2 Freeze Candidate | DONE | `app/market_interpreter/api_readiness_review.py` |
| BOOK-L2-06 | L1-L2 Interval Answer Smoke / Evidence Markdown | DONE | `app/integration/l1_l2_interval_answer_smoke.py` |
| BOOK-L2-07 | Multi-Interval Answer Smoke | DONE | `app/integration/l1_l2_multi_interval_answer_smoke.py` |

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

## BOOK-L2-04

BOOK-L2-04 added a consumer-smoke for the stable BOOK-L2 JSON output:

```text
reports/book_l2/timeline_context.json
```

Command:

```powershell
python -m app.cli.commands book-l2-json-consumer-smoke --strict
```

The consumer validates:

- L2 service and contract version;
- source metadata pointing to BOOK-L1 timeline JSON;
- `overall_state`;
- symbols, buckets, skip flags, quality score/grade/rank, and reason codes;
- deterministic ranking consistency for rankable symbols;
- `market_brief`;
- forbidden human brief terms;
- fail-closed safety;
- warnings/errors handling in default and strict modes.

BOOK-L2 output can now be validated for external/API consumption.

BOOK-L2-04 remains consume-only. It does not read candles, does not connect to DB or live services, does not recalculate BOOK-L1 analysis, and does not create trading decisions.

## Planned direction

BOOK-L2-07 added multi-interval L1-L2 answer smoke.

BOOK-L2 is now Layer 2 Freeze Candidate.

BOOK-L2 remains consume-only / observe-only / fail-closed.

The system can now produce a human-readable evidence report for multiple intervals, showing per-interval L2 state, observation candidates, skip candidates, safety, and cross-interval observations.

The report is evidence Markdown, not runtime API output. Runtime API output remains JSON.

The next stages must keep the same boundary unless an explicit separate decision changes it: consume BOOK-L1 JSON, preserve fail-closed safety, and avoid trading signals.

Next possible layer: BOOK-L3, but only after explicit approval.

## BOOK-L2-05

BOOK-L2-05 added the final readiness reviewer:

```text
app/market_interpreter/api_readiness_review.py
```

Command:

```powershell
python -m app.cli.commands book-l2-api-readiness-review --strict
```

The reviewer validates:

- required BOOK-L2 modules;
- required BOOK-L2 tests;
- CLI commands;
- L1 timeline input `reports/book_l1/timeline_preview.json`;
- L2 stable output `reports/book_l2/timeline_context.json`;
- strict L2 JSON consumer result;
- contract/version/service/source fields;
- fail-closed safety;
- observe-only runtime human fields;
- forbidden L2 source references;
- stable output filename policy;
- terminal guide workflow;
- planning markers;
- BOOK-L2 stage reports.

It does not change bucket rules, scoring rules, ranking rules, market brief rules, L1 JSON semantics, or L2 JSON export semantics.

## BOOK-L2-06

BOOK-L2-06 added an integration smoke:

```text
app/integration/l1_l2_interval_answer_smoke.py
```

Command:

```powershell
python -m app.cli.commands book-l1-l2-interval-answer-smoke `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --interval 15m `
  --window-size 300 `
  --window-count 4 `
  --min-candles 50 `
  --strict `
  --show-details
```

The command verifies:

- fresh L1 timeline export;
- strict L1 JSON consumer;
- fresh L2 context export;
- strict L2 JSON consumer;
- strict L2 API readiness review;
- symbol propagation from L1 to L2;
- L2 source lineage back to `reports/book_l1/timeline_preview.json`;
- fail-closed safety;
- actual human-readable evidence Markdown.

Evidence output:

```text
reports/book_l2/l1_l2_interval_answer.md
```

This Markdown file is evidence for human smoke review, not runtime API output. The stable runtime/API output remains:

```text
reports/book_l2/timeline_context.json
```

## BOOK-L2-07

BOOK-L2-07 added a multi-interval integration smoke:

```text
app/integration/l1_l2_multi_interval_answer_smoke.py
```

Command:

```powershell
python -m app.cli.commands book-l1-l2-multi-interval-answer-smoke `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --intervals 15m,1h,4h `
  --window-size 300 `
  --window-count 4 `
  --min-candles 50 `
  --strict `
  --show-details
```

The command verifies multiple intervals through the existing single-interval smoke runner:

- fresh L1 timeline export per interval;
- strict L1 JSON consumer per interval;
- fresh L2 context export per interval;
- strict L2 JSON consumer per interval;
- strict L2 API readiness review per interval;
- actual L2 answer extraction per interval;
- cross-interval observation summary;
- fail-closed safety per interval.

Aggregate evidence output:

```text
reports/book_l2/l1_l2_multi_interval_answer.md
```

Per-interval evidence output:

```text
reports/book_l2/interval_answers/
```

BOOK-L2-07 does not change BOOK-L1 logic, BOOK-L1 JSON semantics, BOOK-L2 bucket rules, BOOK-L2 quality score rules, BOOK-L2 market brief rules, BOOK-L2 JSON semantics, or API readiness logic.

The report is evidence Markdown, not runtime API output. Runtime API output remains JSON.
