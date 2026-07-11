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

## Remaining BOOK-L1 work

### 1. Market regime decision notes / human explanation layer

Optional next stage:

- explain why a regime is UP / DOWN / FLAT / UNKNOWN;
- list the main factors behind the regime classification;
- state clearly that the explanation is not a trading signal;
- keep `trade_signal = NOT_EVALUATED`;
- keep `safe_for_runtime_trading = false`.

### 2. Optional FastAPI integration layer

Only if needed later:

- expose the BOOK-L1 response contract through an actual HTTP route;
- keep route read-only;
- keep `trade_signal = NOT_EVALUATED`;
- keep `safe_for_runtime_trading = false`.

### 3. Runtime integration planning

Only as a future planning step:

- decide how traders-core may consume BOOK-L1 market state;
- define fail-closed behavior;
- do not allow BOOK-L1 to create entries or orders.

### 4. Calibration / rule tuning

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

## BOOK-L1-21 export rule

BOOK-L1-21 added stable runtime export files:

```text
reports/book_l1/timeline_preview.json
reports/book_l1/timeline_preview.md
```

The files are overwritten on each export run. The names do not contain date, time, version, symbol, interval, stage number, or hash suffix. The module remains read-only and the safety contract is preserved.
