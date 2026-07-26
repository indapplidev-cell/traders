# Readonly API controlled canary runbook

## 1. Purpose and scope

This runbook prepares a separately authorized, single-container Readonly Server
API canary. It does not change the production Compose project, database schema,
market-data service, orchestrator, soak, or LIVE controls.

## 2. Preconditions

- Obtain separate operator authorization for the controlled canary.
- Reconfirm root commit, image identity, production service health, free
  localhost port, and Docker/Compose availability.
- Create a canary-specific Docker network; never attach the canary to unrelated
  networks.
- Prepare an external evidence directory and an environment file outside Git.
- Confirm the selected database is the intended target before any connection.

## 3. Exact root commit and immutable image reference

Build target `readonly-api` from root commit
`880264b1d0a881c01f8fe67dc151c0b69dd4c649`. The prepared immutable task tag is
`traders-readonly-api:880264b1-canary-preparation`; resolve and record its image
ID/digest before start. Never substitute `latest`, `stable`, or `production`.

## 4. Required PostgreSQL read-only role

Use a dedicated, non-owner, non-admin role. It may CONNECT to the selected
database, use the required schema, and SELECT required tables/sequences only.
Set `default_transaction_read_only=on`; do not grant CREATE, TEMP, DML, DDL,
role administration, replication, or bypass-RLS capabilities.

## 5. Pre-deployment privilege probes

In an explicitly read-only transaction, record `current_user`,
`transaction_read_only`, database/schema identity, Alembic version, table row
counts, deterministic content hashes, and schema object inventory. Confirm
SELECT succeeds. Against disposable probe objects owned by the canary audit,
confirm INSERT, UPDATE, DELETE, CREATE TABLE, ALTER TABLE, and DROP are denied.
Any unexpectedly successful write or DDL probe is an immediate stop.

## 6. Configuration preparation

Copy `readonly-api.env.example` to a task-owned path outside Git. Replace every
angle-bracket placeholder with the dedicated read-only role connection fields.
Do not use owner/admin credentials or production secrets in shell history,
tracked files, evidence, or logs. Set a unique
`TRADERS_READONLY_API_CANARY_NETWORK` and keep the default host bind on
`127.0.0.1:18080`.

## 7. Explicit start command with profile

From the repository root, after all prechecks pass:

```powershell
docker compose --project-name <AUTHORIZED_PROJECT_NAME> `
  --env-file <TASK_OWNED_ENV_FILE> `
  -f ops/canary/readonly-api/compose.yaml `
  --profile readonly-api-canary up -d --no-build readonly-api-canary
```

Omitting `--profile readonly-api-canary` must select no service. Do not use
plain `docker compose up`.

## 8. Localhost-only verification

Inspect the published port before probing. It must be exactly
`127.0.0.1:<AUTHORIZED_PORT> -> 8080/tcp`; `0.0.0.0`, `::`, and any public
interface are forbidden. Confirm the container is attached only to the
authorized canary network and has no Docker socket or production volume.

## 9. Healthcheck

Wait for Docker health `healthy`, then request
`GET http://127.0.0.1:<AUTHORIZED_PORT>/api/v1/health`. Record status, latency,
container restart count, CPU, memory, PIDs, and redacted logs.

## 10. All 9 endpoint probes

Probe exactly these GET routes, using deterministic identifiers obtained from
the list responses where required:

1. `/api/v1/health`
2. `/api/v1/dashboard`
3. `/api/v1/markets`
4. `/api/v1/markets/{symbol}`
5. `/api/v1/analysis/{symbol}`
6. `/api/v1/setups`
7. `/api/v1/setups/{setup_id}`
8. `/api/v1/incidents`
9. `/api/v1/incidents/{incident_id}`

All nine must return successful 2xx responses, no unexpected 5xx, and the
OpenAPI/application inventory must remain 9 GET and 0 write routes.

## 11. DB immutability comparison

After probes and again after stop, repeat the same row counts, ordered content
hashes, Alembic version, and schema object inventory. Compare exact canonical
outputs with the pre-start snapshot. Any difference rejects the canary.

## 12. Monitoring interval and observation window

For a future authorized canary, sample health, HTTP 5xx, restart count,
CPU/memory/PIDs, pool/timeout symptoms, redacted logs, and existing
market-data/orchestrator health every 60 seconds for a separately approved
observation window. The preparation dry-run is not production acceptance.

## 13. Stop criteria

One condition is sufficient for immediate controlled stop and rejection:

- healthcheck failure
- any unexpected HTTP 5xx
- route count differs from 9
- any write route appears
- DB row count changes
- DB content hash changes
- Alembic version changes
- schema object changes
- readonly privilege probe unexpectedly succeeds
- container restart
- memory limit breach/OOM
- CPU saturation beyond 90% of the 0.50 CPU limit for three consecutive samples
- connection pool exhaustion
- statement timeout violation
- credential/config leakage in logs
- market-data/orchestrator degradation after future real start

## 14. Controlled stop command

```powershell
docker compose --project-name <AUTHORIZED_PROJECT_NAME> `
  --env-file <TASK_OWNED_ENV_FILE> `
  -f ops/canary/readonly-api/compose.yaml `
  --profile readonly-api-canary down --remove-orphans
```

## 15. Post-stop cleanup

Confirm the canary container is removed, then remove only the authorized
task-owned network and temporary environment file. Preserve or remove the
immutable image only by an explicit operator decision. Do not restart unrelated
services or remove unrelated volumes, images, evidence, worktrees, or venvs.

## 16. Temporary evidence handling

Store only redacted config, commands, timestamps, image IDs/digests, probes,
metrics, comparisons, and logs outside the repository. Credential scan the
evidence before review. Temporary evidence is deleted only after user
acceptance.

## Authorization boundary

This runbook does not authorize deployment by itself.
