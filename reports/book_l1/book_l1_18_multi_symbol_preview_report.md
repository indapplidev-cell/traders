# BOOK-L1-18 - Multi-Symbol Interactive Preview / Compare Market Regimes

## Status

PASS

## Implemented

- Added multi-symbol terminal preview.
- Added symbol set selection.
- Added default Enter behavior.
- Added non-interactive mode.
- Added compact comparison table.
- Added per-symbol warnings.
- Preserved BOOK-L1 safety contract.

## CLI

```powershell
python -m app.cli.commands book-l1-multi-preview
```

## Safety

```text
trade_signal = NOT_EVALUATED
safe_for_runtime_trading = false
orders_enabled = false
live_trading_connected = false
```

## Test status

Full BOOK-L1 test pack passed.

## Conclusion

BOOK-L1 can now compare several local symbols in one terminal run and display market regimes in a compact human-readable table without producing trading signals.
