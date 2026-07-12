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
| BOOK-L2-08 | FLAT Context Handling Proposal | DONE | `app/market_interpreter/flat_context_proposal.py` |
| BOOK-L2-09 | Implement FLAT Context Handling | DONE | `app/market_interpreter/flat_context_handling.py` |
| BOOK-DATA-01 | Candle Data Availability Audit for Market Reader | DONE | `app/data_audit/candle_availability.py` |
| BOOK-DATA-02 | Interval Data Preparation Decision | DONE | `app/data_audit/interval_preparation_decision.py` |
| BOOK-DATA-03C | 15m-Only Market Reader Stabilization | DONE | `app/data_audit/market_reader_15m_stabilization.py` |
| BOOK-L1-26 | 15m Market Reader Quality Review | DONE | `app/market_reader/quality_review.py` |
| BOOK-L1-27 | L1-L2 Regime Alignment Review | DONE | `app/market_reader/regime_alignment_review.py` |
| BOOK-L1-28 | FLAT Context Alignment Diagnostic | DONE | `app/market_reader/flat_context_alignment.py` |

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

BOOK-L2-08 added a proposal-only FLAT context handling stage.

Current problem:

```text
High-confidence L1 FLAT is received by L2 but mapped to UNKNOWN/SKIP.
```

Proposal:

```text
High-confidence L1 FLAT should be preserved as L2 FLAT_CONTEXT.
It should remain non-observation / skip by default and must not become a trading signal.
```

The next safe L2 stage is `BOOK-L2-09 — Implement FLAT Context Handling`.

Do not start BOOK-L3 before the high-confidence FLAT handling boundary is implemented and reviewed.

BOOK-DATA-01 documented the data condition behind multi-interval failures:

```text
15m is ready for BTCUSDT, ETHUSDT, and SOLUSDT.
1h and 4h are missing in the local database for the tested symbols.
```

This means the current blocker for multi-interval L1-L2 reports is candle availability, not BOOK-L1 or BOOK-L2 pipeline logic.

BOOK-DATA-01 is read-only and does not change BOOK-L2 consume-only behavior.

BOOK-DATA-02 fixed the current interval preparation decision:

```text
ACTIVE_INTERVAL_15M_ONLY_WITH_1H_4H_MISSING
```

`15m` is the active working interval for the current Market Reader workflow. `1h` and `4h` are optional/missing and should not block current BOOK-L1/BOOK-L2 work.

BOOK-DATA-02 does not approve download, DB write, interval aggregation, trading logic, edge validation, or runtime integration. Next data work requires a separate explicit BOOK-DATA stage.

BOOK-DATA-03C stabilized the current BOOK-DATA -> BOOK-L1 -> BOOK-L2 path on `15m`:

```powershell
python -m app.cli.commands book-data-15m-stabilization --strict --show-details
```

The command confirms `15m` availability, the active interval decision, L1 timeline export, strict L1 JSON consumption, L2 context export, strict L2 JSON consumption, strict L2 API readiness, the L1-L2 interval answer, and fail-closed safety.

`15m` is the active interval for current BOOK-L1/BOOK-L2 development. `1h` and `4h` remain optional/missing and are not blockers.

BOOK-DATA-03C does not approve download, DB write, interval aggregation, trading logic, edge validation, or runtime integration.

BOOK-L1-26 reviewed the quality of the stabilized `15m` L1/L2 workflow.

Current review result:

```text
status = PASS_WITH_QUALITY_WARNINGS
overall_state = UNKNOWN
observation_candidates = none
skip_candidates = SOLUSDT, BTCUSDT, ETHUSDT
```

The L2 consume path is stable, but the current context is weak: every tested symbol is in the L2 `UNKNOWN` bucket and marked `SKIP`. This points the next work back to BOOK-L1 quality/explainability, not to L2 rule changes or a new layer.

BOOK-L1-27 reviewed the interpretation boundary between L1 regimes and L2 buckets.

Current finding:

```text
BTCUSDT and ETHUSDT are L1 FLAT with high confidence, but L2 reports UNKNOWN/SKIP.
```

This does not change BOOK-L2 rules. It identifies FLAT context handling and L1-to-L2 contract mapping as the next diagnostic focus before any new layer or runtime integration.

BOOK-L1-28 diagnosed the FLAT context semantic gap from the L1/L2 boundary.

Current finding:

```text
High-confidence L1 FLAT is received by L2 but mapped to UNKNOWN/SKIP.
```

Recommended interpretation:

```text
High-confidence FLAT should not become UNKNOWN.
It may remain non-observation / skip, but L2 should preserve and explain it as FLAT context.
```

Completed follow-up stage:

```text
BOOK-L2-08 - FLAT Context Handling Proposal
```

BOOK-L1-28 does not change BOOK-L2 rules. It provides evidence for a later L2 handling proposal.

## BOOK-L2-08

BOOK-L2-08 added:

```text
app/market_interpreter/flat_context_proposal.py
```

Command:

```powershell
python -m app.cli.commands book-l2-flat-context-handling-proposal `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --interval 15m `
  --high-confidence-threshold 0.80 `
  --strict `
  --show-details
```

Stable proposal outputs:

```text
reports/book_l2/flat_context_handling_proposal.json
reports/book_l2/flat_context_handling_proposal.md
reports/book_l2/book_l2_08_flat_context_handling_proposal_report.md
```

Recommended option:

```text
OPTION_C_FLAT_CONTEXT_NOT_OBSERVATION_CANDIDATE
```

BOOK-L2-08 reads the FLAT diagnostic, L1-L2 alignment review, L1 timeline JSON, and L2 context JSON. It proposes preserving high-confidence L1 `FLAT` as `FLAT_CONTEXT`, keeping observation_candidate false and skip_candidate true by default.

BOOK-L2-08 does not change context rules, quality scoring, market brief behavior, JSON export semantics, or runtime bucket decisions.

## BOOK-L2-09

BOOK-L2-09 implements safe FLAT context handling.

High-confidence L1 `FLAT` now maps to L2 `FLAT_CONTEXT` instead of `UNKNOWN`.

Runtime behavior:

- `market_regime = FLAT` and confidence `>= 0.80` maps to `FLAT_CONTEXT`;
- `FLAT_CONTEXT` remains non-observation / skip by default;
- `safe_for_runtime_trading` remains `false`;
- `trade_signal` remains `NOT_EVALUATED`;
- `UNKNOWN` remains distinct from `FLAT`.

Current 15m evidence:

- BTCUSDT: L1 `FLAT` 0.94 -> L2 `FLAT_CONTEXT`;
- ETHUSDT: L1 `FLAT` 0.87 -> L2 `FLAT_CONTEXT`;
- SOLUSDT: L1 `UNKNOWN` 0.00 -> L2 `UNKNOWN`.

BOOK-L2-09 does not change BOOK-L1 logic, candle analysis, data availability, training, labels, edge validation, runtime execution, or BOOK-L3 scope.

Next safe stage is `BOOK-L2-10 - Post-FLAT Context Integration Review`.

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
