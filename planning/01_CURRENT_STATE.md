# Current State

## BOOK-L1 Market Reader status

Status: `LAYER_1_FREEZE_CANDIDATE`

BOOK-L1 Market Reader is implemented as a read-only market-reading layer.

It currently supports:

- candle window normalization and validation;
- candle morphology analysis;
- swing high / swing low detection;
- trend structure analysis;
- range structure analysis;
- breakout / retest context;
- EMA / ATR technical context;
- market regime composition;
- full orchestration through `MarketReaderOrchestrator`;
- CLI preview from stored candles through `book-l1-preview`;
- real DB smoke report for BTCUSDT 15m;
- API/service response contract through `book-l1-api-preview`;
- human-readable terminal table report through `book-l1-interactive-preview`.
- multi-symbol terminal comparison table through `book-l1-multi-preview`.
- current-vs-previous window regime history snapshot through `book-l1-history-preview`.
- multi-window market regime timeline preview through `book-l1-timeline-preview`.
- stable JSON and Markdown timeline export through `book-l1-timeline-preview --export`.
- unified API-oriented JSON export through `--export-json` for current, multi-symbol, history, and timeline preview modes.
- unified terminal command guide through `book-l1-guide`.
- read-only runtime JSON consumer smoke through `book-l1-json-consumer-smoke`.
- API readiness final review through `book-l1-api-readiness-review`.

Current safety contract:

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

BOOK-L1 does not train models, does not download candles during preview, does not connect to runtime trading, and does not approve entries.

Latest completed implementation stages:

| Stage | Status | Result |
| --- | --- | --- |
| BOOK-L1-12 | DONE | CLI preview command added. |
| BOOK-L1-13 | DONE | Manual real DB smoke report added. |
| BOOK-L1-14 | DONE | API/service response contract added. |
| BOOK-L1-15 | DONE | Planning status synchronized. |
| BOOK-L1-16 | DONE | Final repository review completed. |
| BOOK-L1-17 | DONE | Interactive terminal preview / human table report added. |
| BOOK-L1-18 | DONE | Multi-symbol interactive preview / comparison table added. |
| BOOK-L1-19 | DONE | Market regime history snapshot / previous vs current window added. |
| BOOK-L1-20 | DONE | Market regime timeline preview / multi-window history table added. |
| BOOK-L1-21 | DONE | Stable timeline preview export / JSON + Markdown report added. |
| BOOK-L1-22 | DONE | Unified JSON export contract / API output files added. |
| BOOK-L1-23 | DONE | Terminal UX cleanup / unified command guide added. |
| BOOK-L1-24 | DONE | Runtime JSON consumer / API reader smoke added. |
| BOOK-L1-25 | DONE | API readiness final review / Layer 1 freeze candidate added. |

Latest relevant artifacts:

- `reports/book_l1/book_l1_13_BTCUSDT_15m_preview.json`
- `reports/book_l1/book_l1_13_cli_preview_smoke_report.md`
- `reports/book_l1/book_l1_14_BTCUSDT_15m_api_preview.json`
- `reports/book_l1/book_l1_16_final_review.md`
- `reports/book_l1/book_l1_17_interactive_preview_report.md`
- `reports/book_l1/book_l1_18_multi_symbol_preview_report.md`
- `reports/book_l1/book_l1_19_history_snapshot_report.md`
- `reports/book_l1/book_l1_20_timeline_preview_report.md`
- `reports/book_l1/book_l1_21_timeline_export_report.md`
- `reports/book_l1/book_l1_22_unified_json_export_report.md`
- `reports/book_l1/book_l1_23_terminal_ux_cleanup_report.md`
- `reports/book_l1/book_l1_24_runtime_json_consumer_report.md`
- `reports/book_l1/book_l1_25_api_readiness_final_review.md`
- `reports/book_l1/current_preview.json`
- `reports/book_l1/multi_preview.json`
- `reports/book_l1/history_preview.json`
- `reports/book_l1/timeline_preview.json`
- `reports/book_l1/timeline_preview.md`

BOOK-L1-22 added the unified API-oriented JSON export contract:

```text
contract_version = book_l1_json_export_v1
service = BOOK_L1_MARKET_READER
```

The stable runtime API output files are:

```text
reports/book_l1/current_preview.json
reports/book_l1/multi_preview.json
reports/book_l1/history_preview.json
reports/book_l1/timeline_preview.json
```

These files are overwritten on each `--export-json` run. Their names do not include date, time, version, symbol, interval, stage number, or hash suffix.

BOOK-L1-23 added the unified terminal command guide:

```powershell
python -m app.cli.commands book-l1-guide
```

Working UX:

```text
Terminal output: for humans
JSON export: for API
Runtime Markdown export: not used as working output
```

BOOK-L1 remains read-only and the safety contract is preserved.

BOOK-L1-24 added the read-only runtime JSON consumer smoke:

```powershell
python -m app.cli.commands book-l1-json-consumer-smoke --strict
```

The consumer validates stable JSON export files before an external API layer reads them:

- `service = BOOK_L1_MARKET_READER`;
- `contract_version = book_l1_json_export_v1`;
- expected `report_type` per fixed filename;
- required top-level envelope keys;
- `request`, `summary`, and `safety` object shape;
- `warnings` and `errors` list shape;
- fail-closed safety fields.

BOOK-L1-24 did not change market analysis logic, did not change JSON export semantics, did not use runtime Markdown as API output, did not connect live trading, and preserved fail-closed safety.

BOOK-L1-25 added the final API readiness review:

```powershell
python -m app.cli.commands book-l1-api-readiness-review
```

The review checks required modules, tests, planning files, CLI command registration, stable JSON files when present, JSON contract shape, and fail-closed safety. Missing runtime JSON files are WARN after a clean checkout because export may not have run yet; invalid JSON, wrong `service`, wrong `contract_version`, missing safety, or unsafe safety values are FAIL.

Current Layer 1 boundary:

```text
Terminal = for humans
JSON = for API/runtime consumers
Runtime Markdown = not a working output
Trading execution = prohibited
```

BOOK-L1 is now a Layer 1 Freeze Candidate. It remains a read-only market reader and must not be expanded without a separate decision.

## BOOK-L2 Market Interpreter status

Status: `LAYER_2_FREEZE_CANDIDATE`

BOOK-L2 has started as an observe-only layer above BOOK-L1.

BOOK-L2-00 consumes the existing BOOK-L1 runtime JSON file:

```text
reports/book_l1/timeline_preview.json
```

BOOK-L2 reads the BOOK-L1 timeline export, validates the envelope and fail-closed safety contract, extracts symbol timeline rows, classifies symbol context labels, classifies explicit symbol buckets, and builds an overall market context.

Current BOOK-L2 boundary:

```text
BOOK-L1 timeline JSON -> observe-only market context interpretation
```

BOOK-L2 does not read candles, does not import `CandleRepository`, does not use `MarketReaderOrchestrator`, does not recalculate indicators, and does not change BOOK-L1 market analysis logic or JSON export semantics.

BOOK-L2 safety remains fail-closed:

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

Current BOOK-L2 command:

```powershell
python -m app.cli.commands book-l2-timeline-context
```

Current BOOK-L2 stable JSON export:

```text
reports/book_l2/timeline_context.json
```

BOOK-L2-01 added explicit market context classification rules and symbol buckets:

```text
CLEAN_TREND
STABLE_FLAT
TRANSITIONING
UNSTABLE
UNKNOWN
INSUFFICIENT_DATA
ERROR
```

The export now includes `bucket`, `skip_candidate`, `context_reason_codes`, `overall_state`, bucket counts, and fail-closed safety. `skip_candidate` is an observe-only context quality label for UNKNOWN / UNSTABLE / INSUFFICIENT_DATA / ERROR buckets.

BOOK-L2-02 added context quality score and deterministic symbol ranking:

```text
context_quality_score = 0.0..1.0
context_quality_grade = HIGH / MEDIUM / LOW / SKIP / ERROR
context_rank = deterministic observation rank for OK non-skip rows
```

The stable export now includes per-symbol quality fields, `quality_summary`, and `top_ranked_symbols` for observation.

BOOK-L2-03 added Context Summary / Human Market Brief:

```text
market_brief
observation_candidates
skip_candidates
key_points
safety_note
```

The summary is observe-only. It explains which symbols look cleaner for observation, which symbols are skip candidates, and why the overall context looks the way it does. It uses `observation_candidates`, not trade candidates, and it does not create trading signals.

BOOK-L2 still consumes only:

```text
reports/book_l1/timeline_preview.json
```

BOOK-L2 still writes the stable API-oriented output:

```text
reports/book_l2/timeline_context.json
```

BOOK-L2 does not read candles and does not produce trading signals.

BOOK-L2-04 added the L2 JSON consumer smoke:

```powershell
python -m app.cli.commands book-l2-json-consumer-smoke --strict
```

The consumer validates:

- stable input file `reports/book_l2/timeline_context.json`;
- L2 `service` and `contract_version`;
- source metadata pointing to `reports/book_l1/timeline_preview.json`;
- `overall_state`, symbols, buckets, quality fields, and deterministic ranks;
- `market_brief` shape and forbidden human brief terms;
- fail-closed safety fields;
- warnings/errors behavior in default and strict modes.

BOOK-L2 output can now be validated for external/API consumption.

BOOK-L2 still consumes only `reports/book_l1/timeline_preview.json`, does not connect to DB or Binance, does not use `CandleRepository` or `MarketReaderOrchestrator`, and does not make trading decisions.

BOOK-L2-05 completed API readiness final review.

BOOK-L2 is now Layer 2 Freeze Candidate.

BOOK-L2 remains consume-only / observe-only / fail-closed.

BOOK-L2-06 verified the actual L1-L2 interval report answer smoke.

The system can now run L1 timeline export, consume it through L2, and produce a human-readable Markdown evidence report for a requested interval:

```text
reports/book_l2/l1_l2_interval_answer.md
```

BOOK-L2-07 added multi-interval L1-L2 answer smoke.

The system can now produce a human-readable evidence report for multiple intervals, showing per-interval L2 state, observation candidates, skip candidates, safety, and cross-interval observations:

```text
reports/book_l2/l1_l2_multi_interval_answer.md
```

This evidence report is not runtime API output; API output remains JSON.

## BOOK-DATA Market Reader data availability status

Status: `DATA_GAPS_DOCUMENTED`

BOOK-DATA-01 adds a read-only local candle availability audit for Market Reader:

```powershell
python -m app.cli.commands book-data-candle-availability-audit `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --intervals 15m,1h,4h `
  --window-size 300 `
  --window-count 4 `
  --show-details
```

The audit answers which `symbol/interval` combinations have enough local candles for the current L1 timeline requirement:

```text
required_candles = window_size * window_count = 1200
```

Stable evidence outputs:

```text
reports/book_data/candle_availability_audit.json
reports/book_data/candle_availability_audit.md
reports/book_data/book_data_01_candle_availability_audit_report.md
```

Current data finding:

```text
15m is ready for BTCUSDT, ETHUSDT, and SOLUSDT.
1h and 4h are missing in the local database for the tested symbols.
```

The current blocker for multi-interval L1-L2 reports is data availability, not the L1-L2 pipeline.

BOOK-DATA-01 does not download candles, does not write DB rows, does not aggregate intervals, does not change BOOK-L1 analysis logic, and does not produce trading signals.

BOOK-DATA-02 fixed the interval preparation decision after the BOOK-DATA-01 audit:

```powershell
python -m app.cli.commands book-data-interval-preparation-decision --show-details
```

Stable decision outputs:

```text
reports/book_data/interval_data_preparation_decision.json
reports/book_data/interval_data_preparation_decision.md
reports/book_data/book_data_02_interval_data_preparation_decision_report.md
```

Decision:

```text
ACTIVE_INTERVAL_15M_ONLY_WITH_1H_4H_MISSING
```

`15m` is the active working interval for the current Market Reader workflow. `1h` and `4h` are optional/missing and should not block current BOOK-L1/BOOK-L2 work.

No download, DB write, interval aggregation, trading logic, edge validation, or runtime integration is approved by BOOK-DATA-02. Next data work requires a separate explicit BOOK-DATA stage.

BOOK-L2-05 added the final API readiness review:

```powershell
python -m app.cli.commands book-l2-api-readiness-review
```

The review checks required L2 modules, required L2 tests, CLI command registration, L1 timeline input, stable L2 context export, strict L2 JSON consumer validation, contract/version/service/source fields, fail-closed safety, observe-only runtime human fields, forbidden L2 source references, stable output filename policy, terminal guide coverage, planning markers, and BOOK-L2 stage reports.

Current Layer 2 boundary:

```text
Input: reports/book_l1/timeline_preview.json
Output: reports/book_l2/timeline_context.json
Evidence: reports/book_l2/l1_l2_interval_answer.md
Multi-interval evidence: reports/book_l2/l1_l2_multi_interval_answer.md
Mode: consume-only / observe-only / fail-closed
Trading execution: prohibited
```

Next possible layer is BOOK-L3, but only after explicit approval and a separate responsibility decision.
