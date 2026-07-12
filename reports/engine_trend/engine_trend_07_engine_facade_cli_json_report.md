# ENGINE-TREND-07 - Engine Facade, CLI Preview and JSON Export

## Status

`PASS`

## Purpose

This stage exposes the clean `engine_trend` composer through a safe engine facade, preview builder and JSON export path.

It does not connect to a data source, old L1/L2, runtime trading, or live data.

## Created files

- `app/market_reader/engine_trend/engine.py`
- `app/market_reader/engine_trend/json_export.py`
- `app/market_reader/engine_trend/cli_preview.py`
- `tests/test_engine_trend_07_engine_facade_cli_json.py`

## Updated files

- `app/market_reader/engine_trend/__init__.py`

## Implemented

- candle row normalization
- alias key support
- safe conversion to `EngineTrendCandle`
- engine facade and facade output contract
- compact preview builder
- JSON payload builder and file export
- CLI preview from a JSON candle file
- CLI stdout JSON mode and output file mode

## What this stage does not do

- no data adapter or query
- no old L1 integration
- no old L2 integration
- no runtime trading integration
- no live data fetching
- no runtime JSON contract integration
- no model training

## Safety

No trading logic was added. `EngineTrendResult` remains fail-closed:

- `trade_signal = NOT_EVALUATED`
- `safe_for_runtime_trading = false`
- `live_trading_connected = false`

## Checks

- py_compile: PASS
- targeted tests: PASS
- CLI smoke test: PASS
- forbidden trading scan: PASS
- old L1/L2 import scan: PASS
- data access scan: PASS
- git diff --cached --check: PASS

## Next stage

`ENGINE-TREND-08 — Data Source Adapter Plan / DB Boundary`

The next stage should define a separate boundary for loading candles from the existing source without mixing the new engine with old L1/L2.
