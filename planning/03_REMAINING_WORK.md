# Remaining Work

## Completed before this remaining-work snapshot

The following BOOK-L1 items are already completed:

- market reader schemas;
- candle window;
- candle morphology;
- swing detector;
- trend structure analyzer;
- range structure analyzer;
- breakout / retest analyzer;
- technical context analyzer;
- market regime composer;
- market reader orchestrator;
- CLI preview command;
- real DB CLI preview smoke report;
- API/service response contract;
- repository cleanup / final review;
- interactive terminal preview / human table report;
- multi-symbol interactive preview / comparison table.
- market regime history snapshot / previous vs current window comparison.
- market regime timeline preview / multi-window history table.
- stable timeline preview JSON + Markdown export.
- unified JSON export contract / API output files for current, multi-symbol, history, and timeline previews.
- unified terminal command guide and terminal UX cleanup.
- runtime JSON consumer / API reader smoke for stable BOOK-L1 JSON export files.
- API readiness final review / Layer 1 freeze candidate.
- BOOK-L2-00 start layer 2 / consume BOOK-L1 timeline JSON.
- BOOK-L2-01 market context classification rules / symbol buckets.
- BOOK-L2-02 context quality score / deterministic symbol ranking.
- BOOK-L2-03 context summary / human market brief.
- BOOK-L2-04 L2 JSON consumer / context contract smoke.
- BOOK-L2-05 API readiness review / Layer 2 freeze candidate.
- BOOK-L2-06 L1-L2 interval answer smoke / evidence Markdown.
- BOOK-L2-07 multi-interval answer smoke / evidence Markdown.
- BOOK-DATA-01 candle data availability audit for Market Reader.
- BOOK-DATA-02 interval data preparation decision.
- BOOK-DATA-03C 15m-only Market Reader workflow stabilization.
- BOOK-L1-26 15m Market Reader quality review.
- BOOK-L1-27 L1-L2 regime alignment review.

## Remaining BOOK-L1 work

BOOK-L1 is now a Layer 1 Freeze Candidate. BOOK-L1-26 added a read-only quality review for the active `15m` workflow, and BOOK-L1-27 reviewed L1-L2 regime alignment on the same stabilized evidence. Do not expand BOOK-L1 without a separate decision.

### 1. BOOK-L1 quality/explainability on 15m

BOOK-L1-26 confirmed:

- the current 15m pipeline is stable;
- L2 overall state is `UNKNOWN`;
- observation candidates are `none`;
- all tested symbols are skip candidates;
- BTCUSDT and ETHUSDT are L1 `FLAT` with high confidence but L2 `UNKNOWN` / `SKIP`;
- SOLUSDT is L1 `UNKNOWN` with low confidence.

BOOK-L1-27 confirmed:

- L2 receives `FLAT` for BTCUSDT and ETHUSDT;
- L2 bucket still becomes `UNKNOWN`;
- L2 marks both high-confidence FLAT symbols as skip candidates;
- the next issue is FLAT context handling and L1-to-L2 contract interpretation.

Next safe stages:

- `BOOK-L1-28` - FLAT Context Alignment Diagnostic;
- `BOOK-L1-29` - 15m UNKNOWN/FLAT Reduction Diagnostic;
- `BOOK-L1-30` - Market Structure Explainability Improvement.

### 2. Official BOOK-L1 freeze

Possible next stage:

- formally freeze Layer 1 boundaries;
- confirm terminal output is for humans;
- confirm JSON is for API/runtime consumers;
- confirm runtime Markdown is not a working output;
- confirm fail-closed safety remains mandatory;
- confirm trading execution is prohibited.

### 3. BOOK-L2 status

BOOK-L2-05 completed API readiness final review.

BOOK-L2 is now Layer 2 Freeze Candidate.

BOOK-L2 remains consume-only / observe-only / fail-closed.

Do not expand BOOK-L2 without a separate decision.

BOOK-L2-06 verified the actual L1-L2 interval report answer smoke.

The system can now run L1 timeline export, consume it through L2, and produce a human-readable Markdown evidence report for a requested interval.

This evidence report is not runtime API output; API output remains JSON.

### 4. Possible BOOK-L3 discussion only

Next possible layer: BOOK-L3, but only after explicit approval.

Before any BOOK-L3 implementation, decide whether the next layer is:

- another observe-only layer;
- a risk/context gate;
- a policy layer;
- a preparation layer before trading logic;
- or whether trading logic remains prohibited.

BOOK-L3 should not start before the 15m Market Reader quality/explainability findings are addressed or explicitly accepted.

### 5. Optional future maintenance only

- bug fixes found by review can be logged as follow-up;
- documentation can be clarified;
- command help can be cleaned up;
- market analysis logic should not change during freeze handling.

### 6. Future data preparation stages

BOOK-DATA-03C stabilized the current 15m-only Market Reader workflow.

Current decision:

- `15m` is the active working interval for the current Market Reader workflow;
- `1h` and `4h` are optional/missing and should not block current BOOK-L1/BOOK-L2 work;
- no download, DB write, interval aggregation, trading logic, edge validation, or runtime integration is approved.

The next work should improve Market Reader quality on 15m before expanding intervals, unless explicitly decided otherwise.

Possible future stages:

- `BOOK-DATA-03A` - Native 1h/4h Data Loading Plan;
- `BOOK-DATA-03B` - 15m to 1h/4h Aggregation Contract;
- `BOOK-L1-27` - 15m Reason Codes Improvement;
- `BOOK-L1-28` - 15m UNKNOWN/FLAT Reduction Diagnostic.

Do not download, generate, or aggregate candles as part of BOOK-DATA-03C.

## Not remaining anymore

The following items are no longer remaining work:

- `book-l1-preview` CLI command;
- real DB smoke preview JSON;
- real DB smoke Markdown report;
- `book-l1-api-preview` command;
- API/service response contract v1;
- `book-l1-interactive-preview` human terminal report.
- `book-l1-multi-preview` multi-symbol comparison table.
- `book-l1-history-preview` current-vs-previous regime history snapshot.
- `book-l1-timeline-preview` multi-window market regime timeline preview.
- `book-l1-timeline-preview --export` stable JSON + Markdown export.
- `--export-json` unified stable JSON API output for all main BOOK-L1 preview modes.
- `book-l1-guide` unified terminal command guide.
- `book-l1-json-consumer-smoke` runtime JSON consumer / API reader smoke.
- `book-l1-api-readiness-review` API readiness final review / Layer 1 freeze candidate.
- `book-l2-timeline-context` observe-only BOOK-L2 timeline context consumer.
- BOOK-L2 explicit symbol bucket classification and skip candidate labeling.
- BOOK-L2 context quality score and deterministic symbol ranking.
- BOOK-L2 context summary / human market brief.
- BOOK-L2 JSON consumer smoke for stable `reports/book_l2/timeline_context.json`.
- BOOK-L2 API readiness review / Layer 2 freeze candidate.
- BOOK-L2 L1-L2 interval answer smoke / evidence Markdown.
- BOOK-L2 multi-interval answer smoke / evidence Markdown.
- BOOK-DATA candle availability audit / data gap evidence.
- BOOK-DATA interval data preparation decision.
- BOOK-DATA 15m-only Market Reader stabilization.
- BOOK-L1 15m Market Reader quality review.
- BOOK-L1 L1-L2 regime alignment review.

## BOOK-L1-22 export rule

BOOK-L1-22 added stable runtime API JSON output files:

```text
reports/book_l1/current_preview.json
reports/book_l1/multi_preview.json
reports/book_l1/history_preview.json
reports/book_l1/timeline_preview.json
```

The files are overwritten on each `--export-json` run. The names do not contain date, time, version, symbol, interval, stage number, UUID, or hash suffix.

## BOOK-L1-23 terminal UX rule

BOOK-L1-23 added:

```powershell
python -m app.cli.commands book-l1-guide
```

Working UX:

```text
Terminal output: for humans
JSON export: for API
Runtime Markdown export: not used as working output
```

The module remains read-only and the safety contract is preserved.

## BOOK-L1-24 runtime JSON consumer rule

BOOK-L1-24 added:

```powershell
python -m app.cli.commands book-l1-json-consumer-smoke --strict
```

The command reads stable JSON export files, validates the envelope and fail-closed safety contract, and prints an API-reader smoke table. It does not run market analysis, does not change JSON export semantics, does not use runtime Markdown as API output, and does not connect live trading.

## BOOK-L1-25 API readiness final review rule

BOOK-L1-25 added:

```powershell
python -m app.cli.commands book-l1-api-readiness-review
```

The command checks modules, tests, planning files, command registration, stable JSON files, JSON contract, and fail-closed safety. Missing runtime JSON files are WARN after a clean checkout because exports may not have run yet. Invalid JSON, wrong contract, missing safety, or unsafe safety are FAIL.

Layer boundary:

```text
Terminal output: for humans
JSON export: for API
Runtime Markdown export: not used as working output
Trading execution: prohibited
```

## BOOK-L2-00 rule

BOOK-L2-00 added:

```powershell
python -m app.cli.commands book-l2-timeline-context
```

The command reads:

```text
reports/book_l1/timeline_preview.json
```

It validates the BOOK-L1 JSON envelope and fail-closed safety, extracts timeline rows, classifies observe-only symbol contexts, builds overall market context, and can export:

```text
reports/book_l2/timeline_context.json
```

BOOK-L2 does not read candles, does not import `CandleRepository`, does not import `MarketReaderOrchestrator`, does not recalculate BOOK-L1 indicators, does not change BOOK-L1, and does not generate trading signals.

## BOOK-L2-01 rule

BOOK-L2-01 added explicit context classification rules:

```text
app/market_interpreter/context_rules.py
```

The L2 command still reads only:

```text
reports/book_l1/timeline_preview.json
```

The L2 stable output remains:

```text
reports/book_l2/timeline_context.json
```

The output includes symbol buckets, skip candidate labels, context reason codes, overall state, and bucket counts. These fields are observe-only context labels and are not trading signals.

## BOOK-L2-02 rule

BOOK-L2-02 added:

```text
app/market_interpreter/context_quality.py
```

The L2 command still reads only:

```text
reports/book_l1/timeline_preview.json
```

The L2 stable output remains:

```text
reports/book_l2/timeline_context.json
```

The output includes `context_quality_score`, `context_quality_grade`, `context_rank`, `context_quality_reason_codes`, `quality_summary`, and `top_ranked_symbols`.

Ranks are deterministic and assigned only to OK non-skip symbols. Skip and error rows are not ranked.

These fields rank context readability for observation only. BOOK-L2 still does not read candles, does not connect to the database, does not download Binance data, and does not produce trading decisions.

## BOOK-L2-03 rule

BOOK-L2-03 added:

```text
app/market_interpreter/context_summary.py
```

The L2 command still reads only:

```text
reports/book_l1/timeline_preview.json
```

The L2 stable output remains:

```text
reports/book_l2/timeline_context.json
```

The output includes `market_brief`, `brief_state`, `observation_candidates`, `skip_candidates`, `key_points`, and `safety_note`.

The summary is observe-only. It gives observation candidates, not trade candidates. BOOK-L2 still does not read candles, does not connect to DB or Binance, does not use `CandleRepository` or `MarketReaderOrchestrator`, and does not produce trading decisions.

## BOOK-L2-04 rule

BOOK-L2-04 added:

```text
app/market_interpreter/json_consumer.py
```

The command reads:

```text
reports/book_l2/timeline_context.json
```

Command:

```powershell
python -m app.cli.commands book-l2-json-consumer-smoke --strict
```

The consumer validates L2 service identity, contract version, L1 timeline source metadata, `overall_state`, symbols, buckets, quality score/grade/rank, deterministic ranking consistency, `market_brief`, forbidden human brief terms, fail-closed safety, and warnings/errors behavior.

BOOK-L2 output can now be validated for external/API consumption.

BOOK-L2 remains consume-only, observe-only, and fail-closed.

## BOOK-L2-05 rule

BOOK-L2-05 added:

```text
app/market_interpreter/api_readiness_review.py
```

Command:

```powershell
python -m app.cli.commands book-l2-api-readiness-review --strict
```

The command checks L2 module/test coverage, CLI registration, stable L1 input, stable L2 output, strict L2 JSON consumer validation, contract/version/service/source fields, fail-closed safety, observe-only runtime human fields, forbidden L2 source references, stable output filename policy, terminal guide coverage, planning markers, and stage reports.

BOOK-L2 is now Layer 2 Freeze Candidate.

BOOK-L2 remains consume-only / observe-only / fail-closed.

## BOOK-L2-06 rule

BOOK-L2-06 added:

```text
app/integration/l1_l2_interval_answer_smoke.py
```

Command:

```powershell
python -m app.cli.commands book-l1-l2-interval-answer-smoke --strict --show-details
```

The command coordinates the existing L1 and L2 pipeline:

```text
L1 timeline export -> L1 JSON consumer strict -> L2 context export -> L2 JSON consumer strict -> L2 API readiness strict -> evidence Markdown
```

It writes:

```text
reports/book_l2/l1_l2_interval_answer.md
```

The Markdown file is human evidence for smoke review. It is not runtime API output. API output remains JSON:

```text
reports/book_l2/timeline_context.json
```

## BOOK-L2-07 rule

BOOK-L2-07 added:

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

The command reuses the single-interval L1-L2 answer smoke for each requested interval, writes per-interval evidence files under:

```text
reports/book_l2/interval_answers/
```

and writes the aggregate human evidence report:

```text
reports/book_l2/l1_l2_multi_interval_answer.md
```

BOOK-L2-07 added multi-interval L1-L2 answer smoke.

The system can now produce a human-readable evidence report for multiple intervals, showing per-interval L2 state, observation candidates, skip candidates, safety, and cross-interval observations.

The report is evidence Markdown, not runtime API output. Runtime API output remains JSON.
