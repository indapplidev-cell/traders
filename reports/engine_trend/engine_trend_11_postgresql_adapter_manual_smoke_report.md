# ENGINE-TREND-11 — PostgreSQL Adapter Manual Smoke With Real `market_candles`

## Stage goal

Verify the read-only operational path from PostgreSQL `market_candles`, through
`PostgresMarketCandlesProvider` and `CandleDataRequest`, to the engine facade and
its preview/result JSON artifacts.

## Current baseline

- ENGINE-TREND-09: commit `54800af`.
- ENGINE-TREND-10: commit `fb63c22`.
- The existing PostgreSQL adapter was not changed.
- The known unrelated diagnostics collection issue was not changed or used as a
  gate.

## Files created/changed

- `scripts/engine_trend_11_postgres_adapter_manual_smoke.py`
- `reports/engine_trend/manual_smoke/.gitkeep`
- `reports/engine_trend/engine_trend_11_postgresql_adapter_manual_smoke_report.md`

No engine core file was changed.

## DB configuration source

The runner checks, in order, `TRADERS_ML_DATABASE_URL`,
`TRADERS_ML_POSTGRES_URL`, `DATABASE_URL`, and `POSTGRES_URL`. No configured
value was present. No DSN or credential was printed or stored.

## Smoke status

`SKIPPED_DB_CONFIG_MISSING`

## Availability query result

Not executed because no explicit DB configuration was available. The runner
contains the prescribed grouped, read-only availability query for the three
confirmed symbols at 15m.

## Smoke window selection

When DB access is available, the runner uses each symbol's `MAX(open_time)` as
the inclusive period end and subtracts 95 15-minute intervals for a maximum of
96 candles. The provider applies the explicit period bounds and ascending order.

## Symbols tested

Operational reads for BTCUSDT 15m, ETHUSDT 15m, and SOLUSDT 15m were not
executed because DB configuration was missing. The runner rejects other symbols,
intervals, and limits above 96.

## Results

No market results were fabricated. There are therefore no symbol-level regime,
confidence, warning, error, or reason-code results for this run.

## Saved artifacts

The output directory `reports/engine_trend/manual_smoke/` was created and kept
empty. Preview/result JSON files are written only after rows pass through the
real provider boundary; no fallback source is used.

## Safety contract verification

The runner requires every successful boundary result to retain:

- `trade_signal = NOT_EVALUATED`
- `safe_for_runtime_trading = false`
- `live_trading_connected = false`

No operational result was available to verify in this skipped run. The existing
relevant suite covering the safety contract passed. No runtime or live execution
connection was added.

## Tests executed

- Adapter test: `5 passed in 1.17s`.
- Relevant ENGINE-TREND suite: `198 passed in 5.86s`.
- Runner `py_compile`: passed.
- Manual command: exited successfully with `SKIPPED_DB_CONFIG_MISSING`.
- Full pytest was intentionally not run because it is not an ENGINE-TREND-11
  gate and has the documented unrelated diagnostics collection issue.

## Scans executed

- Old L1/L2 import scan: no legacy import is present; textual report references
  are descriptive only.
- Write SQL scan: no write statement is present.
- Trading/runtime scan: no trading action or execution logic is present; safety
  field names and report prose are descriptive only.
- Secret/diff review: no DB URL, `.env` content, or credentials stored.

## Known limitations

Real schema compatibility and operational connectivity remain unverified until
an allowed DB env variable is supplied. Availability metadata and per-symbol
artifacts do not exist for this skipped run. Expected absence of 1h and 4h data
was not tested as a failure.

## Next recommended stage

`ENGINE-TREND-11B — PostgreSQL Operational Availability Fix`: make the local
PostgreSQL/env configuration available, then rerun this read-only smoke without
changing engine_trend logic.
