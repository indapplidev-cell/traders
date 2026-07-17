# ENGINE-ORCHESTRATOR-01 with Docker Compose

The `online-orchestrator` service is separate from `market-data-sync` and is disabled by default through the `orchestrator` profile. Apply migrations and pass smoke tests before enabling it:

```bash
docker compose run --rm traders-ml alembic upgrade head
docker compose --profile orchestrator run --rm online-orchestrator python scripts/engine_orchestrator_online_pipeline.py --symbols BTCUSDT,ETHUSDT,SOLUSDT --once --max-catchup-windows 1
docker compose --profile orchestrator up -d online-orchestrator
```

It waits for PostgreSQL health and service startup of `market-data-sync`, while the runtime freshness gate remains the authoritative readiness check. Reports are persisted through the existing `./reports` bind mount.
