# Current Task

## BOOK-L1-20 - Market Regime Timeline Preview / Multi-Window History Table

Status: `DONE`

Goal:

Add a multi-window market regime timeline launch mode:

```powershell
python -m app.cli.commands book-l1-timeline-preview
```

Scope completed:

- added `app.market_reader.timeline_preview`;
- added `app.market_reader.timeline_interactive`;
- added multi-window candle reads where `required_candles = window_size * window_count`;
- added non-overlapping chronological windows labeled `W-N ... Current`;
- reused `classify_regime_transition()` for adjacent-window transitions;
- added `last_transition` for `W-1 -> Current`;
- added timeline stability classification: `STABLE`, `CHANGING`, `UNSTABLE`, `ERROR`;
- added compact timeline table with current confidence, trend, last change, stability, and locked safety;
- added per-symbol `INSUFFICIENT_DATA` / `ERROR` isolation so one bad symbol does not break the run;
- added optional per-window reason-code details;
- added interactive mode with Enter defaults;
- added non-interactive CLI mode for tests and automation;
- preserved the BOOK-L1 read-only safety contract.

Out of scope:

- no model training;
- no Binance download;
- no traders-core connection;
- no live trading integration;
- no trading signal generation;
- no LONG / SHORT / BUY / SELL;
- no order placement;
- no label, class-weight, or training-objective changes;
- no claim that a trading edge was found.

Completion criteria:

- `python -m app.cli.commands book-l1-timeline-preview` starts the terminal dialog;
- Enter chooses defaults;
- one or more symbols can be analyzed in one run;
- `window_count` is constrained to 2 through 6;
- each symbol reads `window_size * window_count` candles;
- candles are split into non-overlapping chronological windows;
- each window is analyzed through `MarketReaderOrchestrator`;
- `--non-interactive` prints the table without prompts;
- `--show-details` prints reason codes for each timeline window;
- safety remains explicit: `trade_signal = NOT_EVALUATED`, `safe_for_runtime_trading = false`, `orders_enabled = false`;
- tests cover config defaults, validation, labels, stability, window split, insufficient data, error isolation, formatter, summary, safety, non-interactive CLI, details, and prompt defaults.

Next possible stage:

Optional FastAPI integration layer or future runtime consumption planning. BOOK-L1 remains read-only.
