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

## Remaining BOOK-L1 work

### 1. Terminal output normalization / consistent tables

Logical next stage:

- normalize current, multi, history, and timeline terminal table style;
- align column names and safety display;
- keep terminal output human-readable;
- keep JSON export as the API output path;
- avoid changing market analysis logic.

### 2. API reader contract / load JSON exports for external service

Optional future stage:

- add a read-only module that loads the stable JSON output files;
- validate `contract_version = book_l1_json_export_v1`;
- validate `service = BOOK_L1_MARKET_READER`;
- keep fail-closed behavior when a file is missing or invalid;
- avoid re-running analysis when the future API/service layer only needs the latest export snapshot.

### 3. Market regime decision notes / human explanation layer

Optional next stage:

- explain why a regime is UP / DOWN / FLAT / UNKNOWN;
- list the main factors behind the regime classification;
- state clearly that the explanation is not a trading signal;
- keep `trade_signal = NOT_EVALUATED`;
- keep `safe_for_runtime_trading = false`.

### 4. Optional FastAPI integration layer

Only if needed later:

- expose the BOOK-L1 response contract through an actual HTTP route;
- keep route read-only;
- keep `trade_signal = NOT_EVALUATED`;
- keep `safe_for_runtime_trading = false`.

### 5. Runtime integration planning

Only as a future planning step:

- decide how traders-core may consume BOOK-L1 market state;
- define fail-closed behavior;
- do not allow BOOK-L1 to create entries or orders.

### 6. Calibration / rule tuning

Optional future work:

- compare BOOK-L1 market regimes against historical chart samples;
- tune thresholds for range/trend/breakout classification;
- keep this separate from model training and live trading.

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
