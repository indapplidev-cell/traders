# ENGINE-TREND-12 — Engine Trend CLI DB Preview for Confirmed market_candles

## Stage goal

Provide a read-only command-line entrypoint that loads confirmed `15m` candles from PostgreSQL `public.market_candles`, invokes the existing provider boundary and engine facade, prints a compact preview, and optionally saves full and compact JSON.

## Baseline

- ENGINE-TREND-09 storage discovery: commit `54800af`.
- ENGINE-TREND-10 PostgreSQL adapter: commit `fb63c22`.
- ENGINE-TREND-11B operational smoke: commit `1e244da`, status `SUCCESSFUL_SMOKE`.
- Confirmed source: PostgreSQL 16.10, `public.market_candles`, BTCUSDT/ETHUSDT/SOLUSDT at `15m`.
- The known unrelated `solusdt_sidecar_calibration_replay.py` full-suite failure was not changed or used as a gate.

## Files created/changed

- Added `app/market_reader/engine_trend/db_cli_preview.py`.
- Added `tests/test_engine_trend_12_db_cli_preview.py`.
- Added this report.
- Added `reports/engine_trend/db_cli_preview/.gitkeep` so the artifact destination remains present when DB configuration is unavailable.
- No engine core, schema, composer, book-evidence, OHLC-integrity, or PostgreSQL adapter module was changed.

## CLI entrypoint

```powershell
python -m app.market_reader.engine_trend.db_cli_preview --symbol BTCUSDT --interval 15m --max-candles 96
```

The module performs no connection attempt at import time. Connection creation occurs only inside `main` execution.

## CLI arguments

Supported arguments are `--symbol`, `--interval`, `--period-start`, `--period-end`, `--max-candles`, `--output`, `--preview-output`, `--print-json`, `--db-env`, and `--availability`.

- Symbols are restricted to BTCUSDT, ETHUSDT, and SOLUSDT.
- Interval is restricted to `15m`.
- `--max-candles` defaults to 96, must be positive, and is capped at 500.
- Explicit period bounds must be supplied as a pair of ISO datetimes.
- `period_end` is inclusive, matching the adapter's `open_time <= :period_end` condition.
- Without explicit bounds, the CLI reads `MAX(open_time)` for the requested symbol/interval and derives the inclusive window start as `period_end - (max_candles - 1) * 15 minutes`.

## DB configuration behavior

The URL is read only from environment variables. Default lookup order is `TRADERS_ML_DATABASE_URL`, `TRADERS_ML_POSTGRES_URL`, `DATABASE_URL`, then `POSTGRES_URL`. `--db-env` restricts lookup to exactly the named variable.

Public error codes are `DB_CONFIG_MISSING`, `DB_CONNECTION_FAILED`, `DB_TABLE_MISSING`, and `DB_DATA_MISSING`; expected operational failures return a non-zero exit code without a default stack trace. The CLI performs a read-only `to_regclass` table check. It never prints or saves the real DSN. Metadata contains only the selected environment variable name and a masked URL with user, password, and database placeholders.

## Availability mode

`--availability` executes one aggregate read restricted to confirmed symbols and `15m`, returning symbol, interval, count, minimum open time, and maximum open time. It does not dump candles.

## Preview run behavior

The CLI creates a SQLAlchemy connection, injects it into `PostgresMarketCandlesProvider`, builds `CandleDataRequest`, calls `run_engine_trend_from_provider`, and formats the existing facade output. Compact stdout includes stage/service, request period, loaded count, regime, confidence, top reason codes, warning/error counts, boundary status, safety fields, and output paths.

An explicit range with no rows follows the existing boundary: it yields `EMPTY` with an allowed `UNKNOWN` engine result rather than turning `UNKNOWN` into a CLI failure. Automatic range resolution with no maximum row returns `DB_DATA_MISSING`.

## JSON output behavior

`--output` saves a wrapper containing sanitized CLI metadata and the unchanged existing `json_export` payload under `payload`. `--preview-output` saves the compact preview. Parent directories are created automatically. `--print-json` prints the full sanitized wrapper; otherwise output is human-readable.

## Manual DB CLI smoke result

Status: `SUCCESSFUL_DB_CLI_SMOKE`.

`TRADERS_ML_DATABASE_URL` was set only in the smoke command's current PowerShell process from the running `traders-ml-postgres-1` configuration. Its value was neither printed nor persisted. Availability returned:

| Symbol | Interval | Candle count | Minimum `open_time` | Maximum `open_time` |
|---|---:|---:|---|---|
| BTCUSDT | 15m | 50,961 | 2025-01-01 00:00:00+00:00 | 2026-06-15 20:00:00+00:00 |
| ETHUSDT | 15m | 50,962 | 2025-01-01 00:00:00+00:00 | 2026-06-15 20:15:00+00:00 |
| SOLUSDT | 15m | 50,962 | 2025-01-01 00:00:00+00:00 | 2026-06-15 20:15:00+00:00 |

All three per-symbol runs completed with boundary status `READY`, 96 loaded candles, `market_regime=UNKNOWN`, confidence `0.3`, zero boundary warnings, and zero boundary errors. For each run, `trade_signal=NOT_EVALUATED`, `safe_for_runtime_trading=false`, and `live_trading_connected=false`.

## Saved artifacts

- `reports/engine_trend/db_cli_preview/btcusdt_15m_result.json`
- `reports/engine_trend/db_cli_preview/btcusdt_15m_preview.json`
- `reports/engine_trend/db_cli_preview/ethusdt_15m_result.json`
- `reports/engine_trend/db_cli_preview/ethusdt_15m_preview.json`
- `reports/engine_trend/db_cli_preview/solusdt_15m_result.json`
- `reports/engine_trend/db_cli_preview/solusdt_15m_preview.json`

Artifact validation confirmed the expected wrapper/preview structures, 96 candles per symbol, `READY` status, safety fields, and masked DB URLs. No real DSN is stored.

## Safety contract verification

The CLI validates before output that `trade_signal` is `NOT_EVALUATED`, `safe_for_runtime_trading` is `false`, and `live_trading_connected` is `false`. A mismatch fails closed with `SAFETY_CONTRACT_VIOLATION`. Unit tests verify compact safety output. No trading execution is connected.

## Tests executed

- `python -m pytest tests\test_engine_trend_12_db_cli_preview.py -q`: 12 passed.
- `python -m pytest tests\test_engine_trend_10_postgres_candle_adapter.py`: 5 passed.
- Relevant ENGINE-TREND 01–12 suite requested for this stage: 210 passed.
- `python -m py_compile app\market_reader\engine_trend\db_cli_preview.py`: passed.
- Full pytest was intentionally not used as a gate.

## Scans executed

- Executable write-SQL scan of the CLI and tests: no matches.
- Old L1/L2 reference scan of the CLI and tests: no matches.
- Trading/runtime action scan: the only textual match was SQL `ORDER BY`, caused by the requested broad `ORDER` pattern; review confirmed it is query sorting and not order execution. No BUY, SELL, trade-execution, runtime-trading, or live-trading action was found.
- Secret assignment scan and manual diff review: no real URL, password, env value, or credential was present.

## Known limitations

- Only the confirmed `15m` interval and three confirmed symbols are accepted.
- The CLI is an analytical preview and makes no trading claim.
- PostgreSQL freshness and ingestion are outside this stage.

## Next recommended stage

`ENGINE-TREND-13 — Engine Trend DB Preview Acceptance Pack`, after a configured environment is available for repeatable BTCUSDT/ETHUSDT/SOLUSDT `15m` artifacts. ENGINE-TREND-13 is not part of this stage.
