# traders-ml

Modular trading pipeline built around the `app/engine_*` packages. The active
runtime uses public Binance market data and PostgreSQL; it does not require the
removed experimental ML project.

## Mobile Control security source foundation

The deployed operator Control runtime remains unchanged: HTTP on exact
`127.0.0.1:8766` with the existing protected bearer. Source now also defines a
separate fail-closed `mobile_device_signed_tls` profile using registered P-256
device public keys, versioned signatures, bounded freshness and durable
device-scoped mutation nonces. Bearer fallback is impossible in that profile,
and production startup requires certificate/key paths plus an exact private
bind and persistent device/replay stores.

Alembic 0016 contains the additive public-device registry and replay tables but
has not been applied to production. No production TLS key/certificate, mobile
Control listener, firewall rule, device enrollment or Control mutation is part
of this source change. See
[the mobile Control security contract](docs/architecture/control_mobile_device_security.md).

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
# Mobile Control security boundary

MOBILE-08 is blocked at its mandatory Phase A security gate. The production
Control API remains healthy and loopback-only on `127.0.0.1:8766`, with 3 GET
and 5 POST routes protected by a static bearer capability loaded from a
server-side protected file. That local capability is not accepted for mobile
LAN use: HTTP would expose a reusable bearer, it does not identify an
individual device, requests have no signed method/path/body/time/nonce/action
envelope, and there is no per-device revocation lifecycle.

No Control LAN listener, firewall rule, Android Control URL/provider, runtime
restart, database change, or production Control action was created. The
accepted Readonly phone-scoped path remains unchanged. The next task is a
dedicated device-bound Android Keystore authentication, server-authenticated
TLS, persistent replay-protection, audit, rotation, and revocation design and
deployment review; MOBILE-08 may resume only after that security contract is
proven.
