# ENGINE-TREND-09 - Storage Adapter Discovery Without Old L1/L2

## Status

`PASS`

## Purpose

This stage performs read-only discovery of possible candle storage locations for the new `engine_trend` module.

It does not implement a real storage adapter.

## Current baseline

- Last commit before stage: `e1c460c feat: add engine_trend data source boundary`
- Previous tests: `146 passed`
- Branch: `book-l1-market-reader`
- Initial working tree: clean
- Old L1/L2 rule: old L1/L2 were intentionally excluded

## Discovery scope

Discovery covered repository-root filenames, `artifacts/`, `reports/`, root configuration and documentation, storage-neutral `app/data*` and `app/*dataset*` paths, database schema artifacts under `alembic/`, and repository paths identified by a storage-neutral metadata search.

The discovery excluded old L1/L2 source paths, `planning/`, runtime integrations, live data access, `.venv/`, `.git/`, `__pycache__/`, and all content below `app/market_reader/`. Old L1/L2 reports returned by the initial filename inventory were not opened or used as evidence.

## Commands used

The following read-only PowerShell commands, or equivalent commands with the same exclusions, were used:

```powershell
git status --short
git branch --show-current
git log -1 --oneline

Get-ChildItem -Force | Select-Object Name,Mode,Length,LastWriteTime

Get-ChildItem -Recurse -File `
  -Include *.csv,*.json,*.jsonl,*.parquet,*.sqlite,*.sqlite3,*.db,*.duckdb `
  -ErrorAction SilentlyContinue |
  Where-Object {
    $_.FullName -notmatch "\\.venv\\" -and
    $_.FullName -notmatch "\\__pycache__\\" -and
    $_.FullName -notmatch "\\.git\\" -and
    $_.FullName -notmatch "\\app\\market_reader\\"
  } |
  Select-Object FullName,Length,LastWriteTime

Get-ChildItem -Recurse -File -ErrorAction SilentlyContinue |
  Where-Object {
    $_.Length -gt 10MB -and
    $_.FullName -notmatch "\\.venv\\" -and
    $_.FullName -notmatch "\\.git\\" -and
    $_.FullName -notmatch "\\__pycache__\\" -and
    $_.FullName -notmatch "\\app\\market_reader\\"
  } |
  Sort-Object Length -Descending |
  Select-Object FullName,Length,LastWriteTime -First 50

rg --files app/data app/dataset app/data_audit app/config

rg -n `
  --glob '!app/market_reader/**' `
  --glob '!reports/book_l1/**' `
  --glob '!reports/book_l2/**' `
  --glob '!planning/**' `
  --glob 'alembic/**' `
  --glob 'app/db/**' `
  "open_time|timestamp|volume|__tablename__|candles"

Get-Content .env.example -Encoding UTF8
Get-Content docker-compose.yml -Encoding UTF8
Get-Content pyproject.toml -Encoding UTF8
Get-Content alembic/versions/0001_ml_foundation.py -Encoding UTF8 | Select-Object -First 42
Get-Content reports/book_data/candle_availability_audit.json -Encoding UTF8
Get-Content reports/book_data/interval_data_preparation_decision.json -Encoding UTF8
```

No database process was contacted and no query was executed.

## Found candidates

### 1. PostgreSQL `market_candles` table in an external Docker volume

- Physical location: Docker named volume `traders_ml_postgres_data`, mapped to `/var/lib/postgresql/data`
- Repository evidence: `docker-compose.yml`
- Connection configuration evidence: `.env.example`
- Schema evidence: `alembic/versions/0001_ml_foundation.py`
- Storage type: PostgreSQL 16
- Repository file size / modified time: `docker-compose.yml`, 564 bytes, 2026-06-08 17:42:47 +03:00; migration, 9,873 bytes, 2026-06-08 18:15:06 +03:00
- Why it may contain candles: the migration defines `market_candles`, while the read-only availability artifact reports populated local database rows
- Symbols inferred: `BTCUSDT`, `ETHUSDT`, `SOLUSDT`
- Intervals inferred: `15m` populated; `1h` and `4h` absent in the recorded audit
- Recorded coverage: 50,961 BTCUSDT rows and 50,962 rows each for ETHUSDT and SOLUSDT, from 2025-01-01 through 2026-06-15
- Risk / uncertainty: the named volume is external to the Git worktree; this stage did not verify that the container or database is currently running, and did not inspect live schema or rows

### 2. `reports/book_data/candle_availability_audit.json`

- File type: JSON
- Size / modified time: 3,316 bytes, 2026-07-12 11:55:21 +03:00
- Why it is relevant: it is read-only metadata evidence for local database coverage, symbols, intervals, row counts, and time bounds
- Symbol / interval inference: explicit
- Candle fields: not present; only availability metadata is present
- Risk / uncertainty: this is not a candle dataset and must not be used as a candle source

### 3. `reports/book_data/interval_data_preparation_decision.json`

- File type: JSON
- Size / modified time: 4,040 bytes, 2026-07-12 10:44:36 +03:00
- Why it is relevant: it independently records that `15m` exists in the local database and `1h` / `4h` do not
- Symbol / interval inference: explicit for BTCUSDT, ETHUSDT, SOLUSDT and 15m / 1h / 4h
- Candle fields: only an OHLCV validation requirement is named; no candle rows are present
- Risk / uncertainty: this is a decision artifact, not a candle dataset

No repository-local CSV, Parquet, SQLite, DuckDB, or other database file containing candles was found. JSON and JSONL files elsewhere under `reports/` are generated reports or experiment artifacts; none was established as the authoritative historical candle store. Large files found under `reports/` are diagnostic outputs, not confirmed candle storage.

## Candidate formats

| Format | Discovery result |
|---|---|
| CSV | No candle candidate found |
| JSON / JSONL | Metadata and generated reports found; no authoritative candle-row dataset confirmed |
| Parquet | No candidate found |
| SQLite | No candidate found |
| DuckDB | No candidate found |
| PostgreSQL | Strong schema, configuration, volume, and availability evidence |
| Unknown / raw dump | No candidate found |

## OHLCV field mapping

The storage schema is explicit:

| Adapter field | Storage field | Notes |
|---|---|---|
| timestamp | `open_time` | Timezone-aware candle opening time; unique with symbol and interval |
| open | `open` | Numeric(20, 8) |
| high | `high` | Numeric(20, 8) |
| low | `low` | Numeric(20, 8) |
| close | `close` | Numeric(20, 8) |
| volume | `volume` | Numeric(20, 8) |

Additional available fields are `close_time`, `quote_asset_volume`, `number_of_trades`, `taker_buy_base_volume`, `taker_buy_quote_volume`, `source`, and `created_at`. No alias mapping is needed for the price and volume fields; only `open_time` must map to the engine timestamp field.

## Storage adapter recommendation

The stage-level recommendation is **manual review first**, because the prescribed file-adapter choices do not include PostgreSQL and the external volume was not contacted during this read-only stage.

After confirming that the configured PostgreSQL source is the approved source, the implementation recommendation for ENGINE-TREND-10 is a new, independent **PostgreSQL candle adapter** over `market_candles`. It must use only the new `engine_trend` data-source boundary and must not reuse or import old L1/L2 storage access.

A CSV, JSON, Parquet, SQLite, or DuckDB adapter is not supported by the discovered evidence.

## Boundary decision

This stage does not connect `engine_trend` to storage.

The future adapter must return rows compatible with:

`CandleDataProvider.load_rows(request)`

or directly:

`CandleDataBatch`

Storage access appears to exist outside the new engine boundary and must not be reused through old L1/L2. The future adapter should be a fresh storage-specific implementation with explicit symbol, interval, time ordering, row limit, and numeric conversion behavior.

## What this stage does not do

- no real adapter
- no query implementation
- no old L1 integration
- no old L2 integration
- no runtime trading integration
- no live data fetching
- no model training

## Safety

No trading logic was added.

`engine_trend` remains fail-closed.

Discovery was read-only. No source data, schema, configuration, runtime contract, or old L1/L2 file was changed.

## Checks

- py_compile: N/A, no code created
- targeted tests: PASS (`193 passed in 4.77s`)
- forbidden trading scan: PASS
- old L1/L2 import scan: PASS
- data access implementation scan: PASS
- git diff --cached --check: PASS

## Next stage

`ENGINE-TREND-10 — Storage Adapter Implementation for Confirmed Source`

Only after the PostgreSQL source and its operational availability are confirmed.
