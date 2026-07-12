# ENGINE-TREND-08 - Data Source Adapter Plan / DB Boundary

## Status

`PASS`

## Purpose

This stage defines a clean boundary between external candle providers and the new `engine_trend` module.

It does not connect to a real data source, old L1/L2, runtime trading, or live data.

## Created files

- `app/market_reader/engine_trend/data_source_boundary.py`
- `tests/test_engine_trend_08_data_source_boundary.py`

## Updated files

- `app/market_reader/engine_trend/__init__.py`

## Implemented

- candle data request contract
- candle data batch contract
- provider protocol
- request validation
- batch validation
- normalization through the clean engine facade
- boundary runner from provider
- boundary runner from batch
- quality flags
- safe fallback behavior
- dictionary export

## Boundary decision

This stage intentionally does not implement a real adapter to the project storage.

The actual storage-specific adapter must be implemented in a later stage and must remain outside old L1/L2.

## What this stage does not do

- no real data-source connection
- no query implementation
- no old L1 integration
- no old L2 integration
- no runtime trading integration
- no live data fetching
- no runtime JSON contract integration
- no model training

## Safety

No trading logic was added.

`EngineTrendResult` remains fail-closed:

- `trade_signal = NOT_EVALUATED`
- `safe_for_runtime_trading = false`
- `live_trading_connected = false`

## Checks

- py_compile: PASS
- targeted tests: PASS
- forbidden trading scan: PASS
- old L1/L2 import scan: PASS
- data access implementation scan: PASS
- git diff --cached --check: PASS

## Next stage

`ENGINE-TREND-09 — Storage Adapter Discovery Without Old L1/L2`

The next stage may inspect only storage-neutral project infrastructure to identify how candles are stored, but must not touch or import old L1/L2.
