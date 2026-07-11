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

## Remaining BOOK-L1 work

BOOK-L1 is now a Layer 1 Freeze Candidate. Do not expand BOOK-L1 without a separate decision.

### 1. Official BOOK-L1 freeze

Possible next stage:

- formally freeze Layer 1 boundaries;
- confirm terminal output is for humans;
- confirm JSON is for API/runtime consumers;
- confirm runtime Markdown is not a working output;
- confirm fail-closed safety remains mandatory;
- confirm trading execution is prohibited.

### 2. BOOK-L2 follow-up

BOOK-L2 has started. Possible next stage:

- `BOOK-L2-02 - Context Explanation Layer / Human-Readable Market Notes`;
- add short human-readable explanations for symbol buckets and overall context;
- keep consuming only BOOK-L1 JSON output;
- keep fail-closed safety;
- keep trading signals and execution out of scope.

### 3. Optional future maintenance only

- bug fixes found by review can be logged as follow-up;
- documentation can be clarified;
- command help can be cleaned up;
- market analysis logic should not change during freeze handling.

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
