# Current Task

## BOOK-L1-18 - Multi-Symbol Interactive Preview / Compare Market Regimes

Status: `DONE`

Goal:

Add a multi-symbol terminal launch mode:

```powershell
python -m app.cli.commands book-l1-multi-preview
```

Scope completed:

- added `app.market_reader.multi_symbol_preview`;
- added `app.market_reader.multi_symbol_interactive`;
- added symbol set selection and manual symbol entry;
- added default Enter behavior for terminal prompts;
- added non-interactive CLI mode for tests and automation;
- added compact comparison table with per-symbol status, regime, bias, confidence, trend, volatility, trade signal, and runtime trading safety;
- added per-symbol warnings so one missing symbol does not break the whole run;
- added optional per-symbol reason-code details;
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

- `python -m app.cli.commands book-l1-multi-preview` starts the terminal dialog;
- Enter chooses defaults;
- several symbols can be compared in one run;
- `--non-interactive` prints the table without prompts;
- safety remains explicit: `trade_signal = NOT_EVALUATED`, `safe_for_runtime_trading = false`, `orders_enabled = false`;
- tests cover normalization, prompt defaults, retry on invalid input, formatter, summary, error isolation, safety, and non-interactive CLI.

Next possible stage:

BOOK-L1-19 - Market Regime History Snapshot / Compare Current vs Previous Window.
