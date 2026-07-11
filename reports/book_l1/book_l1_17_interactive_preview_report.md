# BOOK-L1-17 - Interactive Terminal Preview / Human Table Report

## Status

`PASS`

## Goal

Add a human-oriented terminal mode:

```powershell
python -m app.cli.commands book-l1-interactive-preview
```

## Implemented

- Added `app/market_reader/interactive_preview.py`.
- Added `book-l1-interactive-preview` CLI command.
- Reused the existing fail-closed BOOK-L1 API preview payload.
- Rendered deterministic ASCII tables for:
  - response metadata;
  - request parameters;
  - candle window;
  - market analysis;
  - safety block;
  - reason codes;
  - warnings and errors.

## Verified Command

```powershell
python -m app.cli.commands book-l1-interactive-preview
```

Local BTCUSDT 15m result:

```text
status = ok
symbol = BTCUSDT
interval = 15m
candle_count = 300
market_regime = FLAT
directional_bias = NEUTRAL
trade_signal = NOT_EVALUATED
safe_for_runtime_trading = false
orders_enabled = false
```

## Safety Contract

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

## Tests

```powershell
python -m pytest tests\test_book_l1_interactive_preview.py tests\test_book_l1_cli_preview.py tests\test_book_l1_api_response_contract.py tests\test_cli.py
```

Result: `36 passed`.

## Out Of Scope

- No trading signal.
- No order placement.
- No live trading connection.
- No runtime trading approval.
- No model training.
- No Binance download.
