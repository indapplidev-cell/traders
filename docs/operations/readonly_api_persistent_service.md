# Persistent localhost Readonly API service

The production Readonly API is an independently managed Compose service in
`ops/production/readonly-api/compose.yaml`. It joins the existing production
network but does not own, replace, or restart PostgreSQL, market-data, or the
online orchestrator.

The host boundary is exactly `127.0.0.1:8765`. The process listens on
`0.0.0.0:8765` only inside its isolated container so Docker can forward the
loopback-only host socket. The service exposes the existing nine GET routes and
no write route.

Runtime configuration is read only from the protected, untracked
`.env.production.local` through Compose `env_file`. That file is excluded from
the Docker build context. Never render or capture the resolved Compose
configuration because it contains the credential-bearing database URL.

The service is non-root, has a read-only root filesystem, drops all Linux
capabilities, enables `no-new-privileges`, and uses bounded CPU, memory, PIDs,
and `/tmp`. Its healthcheck calls `/api/v1/health`, which proves the process,
HTTP readiness, and database connectivity. `restart: unless-stopped` provides
managed host-restart recovery without controlling any other service.

Controlled deployment:

```powershell
python scripts/verify_persistent_secret_binding.py --require-provisioned-secret
docker compose -f ops/production/readonly-api/compose.yaml build readonly-api
docker compose -f ops/production/readonly-api/compose.yaml up -d --no-deps readonly-api
```

Do not run `docker compose down`. A rollback stops and removes only this
service:

```powershell
docker compose -f ops/production/readonly-api/compose.yaml stop readonly-api
docker compose -f ops/production/readonly-api/compose.yaml rm -f readonly-api
```

After deployment, verify the loopback listener, health, 9 GET/0 write route
contract, least-privilege positive and negative database probes, redacted logs,
and unchanged IDs/restart counts for PostgreSQL, market-data, and orchestrator.
