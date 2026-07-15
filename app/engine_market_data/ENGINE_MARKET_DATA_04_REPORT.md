# ENGINE-MARKET-DATA-04 implementation report

The operational service synchronizes only real, fully closed Binance public REST
klines into the six canonical PostgreSQL candle tables. Startup and every restart
derive the expected closed boundary from exchange time, query PostgreSQL for exact
missing opens, recover only those opens, and verify coverage after idempotent upsert.

Freshness and recovery state is persisted in `market_data_sync_state`. The service
has no imports from downstream engines and produces no signals, setups, decisions,
orders, positions, outcomes, or PnL. Docker Compose and systemd operation are
documented under `docs/operations`.
