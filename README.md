# traders-ml

Modular trading pipeline built around the `app/engine_*` packages. The active
runtime uses public Binance market data and PostgreSQL; it does not require the
removed experimental ML project.

## Active modules

```text
engine_market_data -> engine_analysis -> engine_setup -> engine_strategy
                   -> engine_risk -> engine_paper -> engine_orchestrator
```

Supporting engine packages cover execution, position, exit, journal, safety,
and online observation boundaries. Shared runtime dependencies are limited to
`app.config` and `app.db`.

## PostgreSQL and migrations

Start the application database and services:

```bash
docker compose up -d postgres market-data-sync
```

The persistent PostgreSQL volume is `traders_ml_postgres_data`. Apply or inspect
migrations with:

```bash
alembic upgrade head
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

Operational Docker and systemd notes are in `docs/operations/`.

## Development checks

```bash
pytest -q
python -m compileall app scripts
```
