# ENGINE-ORCHESTRATOR-01 with Docker Compose

The `online-orchestrator` service is separate from `market-data-sync` and is disabled by default through the `orchestrator` profile. Apply migrations and pass smoke tests before enabling it:

```bash
docker compose run --rm traders-ml alembic upgrade head
docker compose --profile orchestrator run --rm online-orchestrator python scripts/engine_orchestrator_online_pipeline.py --symbols BTCUSDT,ETHUSDT,SOLUSDT --once --max-catchup-windows 1
docker compose --profile orchestrator up -d online-orchestrator
```

It waits for PostgreSQL health and service startup of `market-data-sync`, while the runtime freshness gate remains the authoritative readiness check. Reports are persisted through the existing `./reports` bind mount.

The production 5m shadow owner is a separate opt-in service and must be
started independently of the unchanged 15m orchestrator:

```bash
docker compose --profile orchestrator-5m up -d --build --no-deps online-orchestrator-5m
```

`online-orchestrator-5m` resolves `trade-5m-v1` before startup, validates the
exact `0017_parallel_trade_profiles` capability, and acquires its dedicated
PostgreSQL session advisory lock before boundary evaluation. Its health is
written to `reports/engine_orchestrator/latest_health_trade_5m.json`. A second
owner exits with `OWNER_ALREADY_ACTIVE` and does not create or advance a run.

For compatibility with a running legacy 15m image, retryable 5m freshness is
checked before an authoritative run is reserved. Until the required context is
ready there is no 5m `WAITING_FOR_REQUIRED_BOUNDARY` row for a legacy retry
scanner to claim. Once ready, the 5m owner reserves and completes the boundary
on its fenced session. This behavior is confined to non-default profiles and
does not change or restart the 15m runtime.

Apply migration `0008_engine_orchestrator_freshness_retry` before starting the
new binary. The migration is additive and adds a `(status, next_retry_at)` due
queue index; rollback requires stopping every orchestrator instance before
downgrading to `0007`.

`BOUNDARY_NOT_READY` is transient until the immutable boundary-close plus grace
deadline. The logical run remains `WAITING_FOR_REQUIRED_BOUNDARY`, keeps its
original `run_id` and dedupe key, and has no result or snapshot. Due rows are
read from PostgreSQL after restart and claimed atomically by one daemon. A retry
re-runs freshness, then creates a new causal snapshot and executes the pipeline
once. Persistent gaps/corruption remain terminal; expiry is the distinct
`SKIPPED_FRESHNESS_TIMEOUT` status. Completed and terminal rows are never
automatically reconsidered.

Defaults are controlled by `ORCHESTRATOR_FRESHNESS_RETRY_INTERVAL_SECONDS=5`,
`ORCHESTRATOR_FRESHNESS_GRACE_SECONDS=180`,
`ORCHESTRATOR_FRESHNESS_MAX_ATTEMPTS=60`, and
`ORCHESTRATOR_WAITING_BATCH_SIZE=100`. Health JSON includes waiting counts by
timeframe/symbol, oldest age, next retry, retry/recovery/timeout totals and last
recovery/timeout timestamps. Structured transition events are
`FRESHNESS_WAIT_STARTED`, `FRESHNESS_RETRY_SCHEDULED`,
`FRESHNESS_RETRY_CLAIMED`, `FRESHNESS_RECOVERED`, `FRESHNESS_TIMEOUT`, and
`FRESHNESS_TERMINAL_SKIP`.

Example lifecycle:

```text
20:00:21 — 15m available
20:00:28 — 1h missing
20:00:28 — WAITING_FOR_REQUIRED_BOUNDARY
20:01:01 — 1h available
20:01:03 — retry claim
20:01:03 — READY
20:01:03 — pipeline executes once
```
