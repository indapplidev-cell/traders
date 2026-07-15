# ENGINE-MARKET-DATA-01 report

## Result

The independent public market-data layer is implemented under
`app/engine_market_data`. It normalizes Binance REST and websocket klines into a
strict UTC-millisecond `Candle`, retains raw in-progress updates separately,
and exposes only exchange-confirmed closed candles.

Continuity is checked causally against the preceding stored closed candle.
Exact missing open times are recovered from public REST in minimal contiguous
intervals. A partial or failed recovery produces `DEGRADED` health and no
synthetic data.

Snapshots are closed-only, report gaps and insufficient history without
raising, and permanently set `future_bars_used=false`.

## Safety boundary

There are no private endpoints, API keys, setup candidates, trade signals,
orders, position sizing, PnL calculation, or imports from analysis/trading
engine layers. `engine_analysis` behavior and runtime trading code are not
changed by this stage.

## Verification

Unit and contract coverage is located in
`tests/test_engine_market_data_01_*.py`. Final command results are recorded in
the delivery response after both the focused and complete suites run.
