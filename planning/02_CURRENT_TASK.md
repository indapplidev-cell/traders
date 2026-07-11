# Current Task

## BOOK-L1-17 - Interactive Terminal Preview / Human Table Report

Status: `DONE`

Goal:

Add a human-oriented terminal launch mode:

```powershell
python -m app.cli.commands book-l1-interactive-preview
```

Scope completed:

- added `app.market_reader.interactive_preview`;
- added deterministic ASCII terminal tables for response, request, candle window, market analysis, safety, reason codes, warnings, and errors;
- added `book-l1-interactive-preview` CLI command;
- reused the existing BOOK-L1 API preview payload and safety contract;
- added tests for formatter and CLI wiring;
- verified the command against local BTCUSDT 15m stored candles.

Out of scope:

- no new analyzer logic;
- no model training;
- no Binance download;
- no runtime trading integration;
- no strategy / risk / executor changes.

Completion criteria:

- `python -m app.cli.commands book-l1-interactive-preview` prints a human-readable table report;
- safety remains explicit: `trade_signal = NOT_EVALUATED`, `safe_for_runtime_trading = false`, `orders_enabled = false`;
- tests cover the formatter and CLI command.
