# ENGINE-MARKET-DATA-04 with Docker Compose

The repository `docker-compose.yml` defines `postgres` and the independent
`market-data-sync` service. Both use `restart: always`; the daemon waits for the
PostgreSQL healthcheck and mounts `./reports` at `/service/reports`.

Before first start, apply migrations, then operate the service without an IDE:

```bash
docker compose run --rm traders-ml alembic upgrade head
docker compose up -d market-data-sync
docker compose logs -f market-data-sync
docker compose restart market-data-sync
docker compose down
docker compose up -d
```

On a host/container restart, PostgreSQL becomes healthy first. The daemon then
runs startup warmup, computes the latest fully closed UTC candle for every pair,
downloads exact missing ranges through Binance public REST, verifies coverage,
and resumes its boundary loop. A manual backfill command is not required.

To test downtime catch-up, confirm health, stop `market-data-sync` for 10–30
minutes, start it again, inspect
`reports/engine_market_data/continuous_sync/latest_health.json`, and query
`market_data_sync_state`. Missing candles must be recovered automatically.

Codex, VSCode, notebooks, an interactive terminal, API keys, and private Binance
endpoints are not runtime dependencies.
