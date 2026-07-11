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
- interactive terminal preview / human table report.

## Remaining BOOK-L1 work

### 1. Optional FastAPI integration layer

Only if needed later:

- expose the BOOK-L1 response contract through an actual HTTP route;
- keep route read-only;
- keep `trade_signal = NOT_EVALUATED`;
- keep `safe_for_runtime_trading = false`.

### 2. Runtime integration planning

Only as a future planning step:

- decide how traders-core may consume BOOK-L1 market state;
- define fail-closed behavior;
- do not allow BOOK-L1 to create entries or orders.

### 3. Calibration / rule tuning

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
