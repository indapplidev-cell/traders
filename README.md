# traders-ml

Modular trading pipeline built around the `app/engine_*` packages. The active
runtime uses public Binance market data and PostgreSQL; it does not require the
removed experimental ML project.

## Current architecture

```text
engine_market_data -> engine_analysis -> engine_setup -> engine_strategy
                   -> engine_risk -> engine_execution -> engine_position
                   -> engine_exit -> engine_journal -> engine_safety
                   -> engine_paper -> engine_orchestrator -> engine_observation
```

All packages above are current contract boundaries. `engine_market_data` reads
public Binance market data; the remaining engines consume repository-local
contracts and PostgreSQL-backed state. Shared runtime dependencies are limited
to `app.config` and `app.db`. No private Binance credentials are required.

## PostgreSQL and migrations

Copy `.env.example` to `.env` and replace placeholders locally when needed.
The Compose database is published on host port `5433`; containers connect to
`postgres:5432`.

Start the application database and market-data service:

```bash
docker compose up -d postgres market-data-sync
```

The persistent PostgreSQL volume is `traders_ml_postgres_data`. The Alembic
history is a single compatibility chain from `0001` through `0008`. Inspect it
with:

```bash
alembic heads
alembic history
```

## Market data operations

```bash
python scripts/engine_market_data_03_backfill.py --help
python scripts/engine_market_data_continuous_sync.py --help
python scripts/engine_market_data_04_prod_smoke.py --help
```

The market-data engine includes Binance REST and WebSocket ingestion, exchange
time sync, closed-candle persistence, warmup, historical backfill, gap recovery,
multi-timeframe synchronization, freshness monitoring, and health reporting.

## Online pipeline

```bash
python scripts/engine_orchestrator_online_pipeline.py --help
python scripts/engine_online_pipeline_observation.py --help
```

The orchestrator is profile-gated in Compose and can be selected explicitly
with `--profile orchestrator`. Runtime health output under `reports/` is
generated and intentionally untracked.

Operational Docker and systemd notes are in `docs/operations/`.

## Development checks

```bash
python -m pytest -q
python -m compileall app scripts tests
```
