# ENGINE-TREND-11B — PostgreSQL Operational Availability Fix

## Stage goal

Restore operational access to the local PostgreSQL candle source and rerun the existing ENGINE-TREND-11 manual smoke against real rows from `market_candles`, without changing engine logic or connecting runtime trading.

## Baseline

- ENGINE-TREND-09: storage adapter discovery, commit `54800af`.
- ENGINE-TREND-10: PostgreSQL candle adapter, commit `fb63c22`.
- ENGINE-TREND-11 initial result: `SKIPPED_DB_CONFIG_MISSING`.
- Known unrelated full-suite failure in `app/diagnostics/solusdt_sidecar_calibration_replay.py` was outside this stage and was not changed.

## Initial status

- Working tree before ENGINE-TREND-11B work: clean.
- Existing runner: `scripts/engine_trend_11_postgres_adapter_manual_smoke.py`.
- Existing DB URL lookup order was retained.
- No engine, adapter, schema, market logic, or diagnostic code was changed.

## Docker discovery

- Compose file: `docker-compose.yml` found at repository root.
- PostgreSQL compose service: `postgres`.
- Container: `traders-ml-postgres-1`.
- Image: `postgres:16-alpine`.
- Host port mapping: `localhost:5433` to container port `5432`.
- Compose volume: `traders_ml_postgres_data`.
- Docker volume instance: `traders-ml_traders_ml_postgres_data`.
- A separate PostgreSQL container on host port 5432 was observed but was not used by this stage.

## PostgreSQL container status

- Container status during verification: running.
- PostgreSQL version query: PostgreSQL 16.10.
- Logs confirmed that the existing database directory was reused and that the server was ready to accept connections.
- The container did not require recreation or a new volume.

## Docker volume status

- `traders-ml_traders_ml_postgres_data` exists.
- Driver: `local`.
- Scope: `local`.
- No volume removal, pruning, replacement, export, or content modification was performed.

## DB configuration source

- Configuration sources: repository `docker-compose.yml` and the existing safe `.env.example`.
- DB env var used for the runner child process: `TRADERS_ML_DATABASE_URL`.
- DB URL masked: `postgresql+psycopg://<user>:<password>@localhost:<port>/<db>`.
- The environment value was temporary and was not written to a tracked env file.

## DB URL masking policy

- No real DSN or password is recorded in this report.
- User, password, port, and database components are represented by placeholders in the reported URL.
- No container environment dump, database dump, or Docker volume content was added to git.

## Read-only availability checks

- Connection/version query: passed.
- `market_candles` exists: yes, in schema `public`.
- Availability query was restricted to the requested symbols and `15m` interval.

| Symbol | Interval | Candle count | Minimum `open_time` | Maximum `open_time` |
|---|---:|---:|---|---|
| BTCUSDT | 15m | 50,961 | 2025-01-01 00:00:00+00 | 2026-06-15 20:00:00+00 |
| ETHUSDT | 15m | 50,962 | 2025-01-01 00:00:00+00 | 2026-06-15 20:15:00+00 |
| SOLUSDT | 15m | 50,962 | 2025-01-01 00:00:00+00 | 2026-06-15 20:15:00+00 |

All database checks performed for this stage were read-only.

## ENGINE-TREND-11 runner rerun result

Status: `SUCCESSFUL_SMOKE`.

The existing runner reported `smoke_status: CONNECTED`, loaded 96 latest `15m` candles for each of BTCUSDT, ETHUSDT, and SOLUSDT, and reported `successful_symbols: 3`. The candle source was the local PostgreSQL `market_candles` table. No `reports/*.json` input or mock candle source was used.

Observed result for every symbol:

- `market_regime`: `UNKNOWN`.
- `trade_signal`: `NOT_EVALUATED`.
- `safe_for_runtime_trading`: `false`.
- `live_trading_connected`: `false`.

`UNKNOWN` is an allowed analytical result and does not invalidate the operational smoke.

## Smoke artifacts

Created by the existing runner:

- `reports/engine_trend/manual_smoke/engine_trend_11_btcusdt_15m_preview.json`
- `reports/engine_trend/manual_smoke/engine_trend_11_btcusdt_15m_result.json`
- `reports/engine_trend/manual_smoke/engine_trend_11_ethusdt_15m_preview.json`
- `reports/engine_trend/manual_smoke/engine_trend_11_ethusdt_15m_result.json`
- `reports/engine_trend/manual_smoke/engine_trend_11_solusdt_15m_preview.json`
- `reports/engine_trend/manual_smoke/engine_trend_11_solusdt_15m_result.json`

Artifact validation confirmed 96 candles per preview and retained safety fields in all preview/result pairs.

## Tests executed

- `python -m pytest tests\test_engine_trend_10_postgres_candle_adapter.py`: 5 passed.
- Relevant ENGINE-TREND test set from stages 01 through 10: 198 passed.
- `python -m py_compile scripts\engine_trend_11_postgres_adapter_manual_smoke.py`: passed.
- Full pytest was not used as a gate because of the documented unrelated diagnostics failure.

## Scans executed

- Executable write-SQL scan of the runner and this report: no executable write SQL present.
- Old L1/L2 import scan of the runner: no old L1/L2 import or logic found.
- Trading/runtime logic scan of the runner: no order execution or live/runtime trading connection found.
- Secret review of the git diff: no real DB URL, password, env file, database dump, or volume contents present.

## Files changed

- Added this ENGINE-TREND-11B report.
- Added six runner-generated smoke JSON artifacts listed above.
- No file under `app/market_reader/engine_trend/` was changed.
- `.env.example` and `.gitignore` were not changed.

## Known limitations

- This was a local operational smoke, not a runtime trading integration.
- The newest available requested candles ended on 2026-06-15; ingestion freshness was not modified or investigated because all requested symbol/interval datasets were present and the runner completed successfully.
- Credentials remain local operational configuration and are intentionally absent from tracked stage artifacts.

## Next recommended stage

`ENGINE-TREND-12 — Engine Trend CLI DB Preview for Confirmed market_candles`.

That stage may add a convenient CLI preview for the confirmed PostgreSQL source, without changing engine core and without runtime trading. It was not started as part of ENGINE-TREND-11B.
