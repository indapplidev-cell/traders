# BOOK-L1-20 - Market Regime Timeline Preview / Multi-Window History Table

## Status

`PASS`

## Implemented

- Added multi-window market regime timeline preview.
- Added timeline runner.
- Added timeline table formatter.
- Added interactive mode.
- Added non-interactive mode.
- Added optional details with reason codes.
- Added timeline stability classification.
- Added adjacent-window transition tracking.
- Added per-symbol error isolation.
- Preserved BOOK-L1 safety contract.

## CLI

```powershell
python -m app.cli.commands book-l1-timeline-preview
```

```powershell
python -m app.cli.commands book-l1-timeline-preview `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --interval 15m `
  --window-size 300 `
  --window-count 4 `
  --min-candles 50 `
  --non-interactive
```

## Safety

```text
trade_signal = NOT_EVALUATED
safe_for_runtime_trading = false
orders_enabled = false
live_trading_connected = false
approved_for_live_trading = false
```

## Test status

Full BOOK-L1 test pack passed.

## Conclusion

BOOK-L1 can now display a multi-window timeline of market regimes for one or more symbols without producing trading signals or enabling runtime trading.
