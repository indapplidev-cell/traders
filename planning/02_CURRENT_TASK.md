# Current Task

## BOOK-L1-19 - Market Regime History Snapshot / Compare Current vs Previous Window

Status: `DONE`

Goal:

Add a current-vs-previous market regime comparison launch mode:

```powershell
python -m app.cli.commands book-l1-history-preview
```

Scope completed:

- added `app.market_reader.history_snapshot`;
- added `app.market_reader.history_interactive`;
- added previous/current window split with `limit * 2` candle reads;
- added transition classification such as `FLAT_TO_UP`, `DOWN_TO_FLAT`, `NO_CHANGE`, and `TO_UNKNOWN`;
- added default Enter behavior for terminal prompts;
- added non-interactive CLI mode for tests and automation;
- added compact comparison table with previous regime, current regime, transition, confidence, trend, and locked safety;
- added per-symbol `INSUFFICIENT_DATA` / `ERROR` isolation so one bad symbol does not break the run;
- added optional per-symbol previous/current reason-code details;
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

- `python -m app.cli.commands book-l1-history-preview` starts the terminal dialog;
- Enter chooses defaults;
- several symbols can be compared in one run;
- current window is compared against the immediately previous non-overlapping window;
- each symbol reads `limit * 2` candles;
- `--non-interactive` prints the table without prompts;
- `--show-details` prints reason codes for previous/current windows;
- safety remains explicit: `trade_signal = NOT_EVALUATED`, `safe_for_runtime_trading = false`, `orders_enabled = false`;
- tests cover transition classification, config defaults, window split, insufficient data, error isolation, formatter, summary, safety, non-interactive CLI, details, and prompt defaults.

Next possible stage:

Optional FastAPI integration layer or future runtime consumption planning. BOOK-L1 remains read-only.
