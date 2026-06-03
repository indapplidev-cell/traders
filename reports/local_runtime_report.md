# Local Runtime Report

## Scope

- Stage 3 was not started.
- This report covers Stage 2.5: local PostgreSQL runtime validation.
- VPS deploy is still pending due server-side SSH/banner timeout during maintenance.

## PostgreSQL Runtime Fixes

- Fixed Alembic revision id:
  - from: `0003_add_runner_state_and_open_position_index`
  - to: `0003_runner_state`
- Migration file renamed:
  - from: `alembic/versions/0003_add_runner_state_and_open_position_index.py`
  - to: `alembic/versions/0003_runner_state.py`
- Added test coverage to enforce `len(revision) <= 32` for all Alembic revisions.
- Updated runtime dependency:
  - `asyncpg>=0.29.0`
- Hardened CLI output for Windows narrow encodings:
  - ASCII-safe error text fallback
  - ASCII-safe progress fallback without Unicode-only widgets

## Dependency Validation

- `.venv\Scripts\python -m pip install -e ".[dev]"`: success
- `.venv\Scripts\python -m pip show asyncpg`: success
  - package: `asyncpg`
  - version: `0.31.0`

## Local PostgreSQL Reset

- `docker compose -f docker-compose.server.yml --env-file .env down -v`: success
- `docker compose -f docker-compose.server.yml --env-file .env up -d`: success
- `docker ps`: `traders_postgres` running with `127.0.0.1:5432->5432/tcp`
- `docker exec traders_postgres pg_isready -U traders -d traders`: `/var/run/postgresql:5432 - accepting connections`

## Alembic

- `.venv\Scripts\alembic upgrade head`: success
  - applied revisions:
    - `0001_init`
    - `0002_expand_trade_decisions`
    - `0003_runner_state`
- `.venv\Scripts\alembic current`: `0003_runner_state (head)`

## Direct Table Checks

Verified in PostgreSQL:

- `alembic_version`: exists
- `candles`: exists
- `paper_accounts`: exists

Additional tables present:

- `paper_positions`
- `paper_runner_state`
- `trade_decisions`

## Local Runtime Results

- `.venv\Scripts\python -m pytest`: `51 passed in 4.86s`
- `.venv\Scripts\python -m ruff check .`: `All checks passed!`
- `.venv\Scripts\python -m app.cli.commands health`: success
  - `OK: app loaded`
  - `OK: database connected`
- `.venv\Scripts\python -m app.cli.commands async-health`: success
  - `OK: async database connected`
- `.venv\Scripts\python -m app.cli.commands load-history --symbol BTCUSDT --interval 15m --days 30`: success
  - chunks loaded: `3`
  - candles saved: `2880`
  - first open time: `2026-05-04T17:00:00+00:00`
  - last open time: `2026-06-03T16:45:00+00:00`
- `.venv\Scripts\python -m app.cli.commands backtest --symbol BTCUSDT --interval 15m --days 30`: success
  - candles used: `2880`
  - final balance: `1000.01983672`
  - total pnl: `0.01983672`
  - total trades: `39`
- `.venv\Scripts\python -m app.cli.commands paper-step --symbol BTCUSDT --interval 15m`: success
  - strategy decision: `SELL`
  - final decision: `HOLD`
  - execution action: `SKIPPED`
  - execution message: `Нельзя выполнить SELL: открытая позиция отсутствует.`
- `.venv\Scripts\python -m app.cli.commands portfolio`: success
  - USDT balance: `1000.0000000000`
  - open positions: `0`
  - realized pnl: `0`

## Pending

- VPS deploy remains pending because the server still does not complete SSH banner exchange in this environment.
