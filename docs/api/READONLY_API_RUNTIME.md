# Read-only API runtime

The production composition chain is:

```text
TRADERS_READONLY_API_* configuration
-> SQLAlchemy engine/session factory
-> one SELECT-only SqlAlchemyReadAdapter
-> ApiRepositories
-> create_app()
-> app.server_api.runtime:create_runtime_app
-> uvicorn factory mode
```

Canonical host entrypoints:

```powershell
traders-readonly-api
python -m app.server_api.runtime
```

Both invoke `app.server_api.runtime.main`. The server runs one worker, reload is
disabled, access logging is enabled, and the default host/port are
`127.0.0.1:8080`. The `readonly-api` Docker target explicitly binds
`0.0.0.0:8080` inside the container and uses `CMD ["traders-readonly-api"]`.

## Configuration

`TRADERS_READONLY_API_DATABASE_URL` is required and must use the
`postgresql+psycopg` SQLAlchemy scheme. There is no default connection URL and
no `.env` discovery. The remaining variables are:

- `TRADERS_READONLY_API_HOST` (default `127.0.0.1`)
- `TRADERS_READONLY_API_PORT` (default `8080`)
- `TRADERS_READONLY_API_LOG_LEVEL` (default `info`)
- `TRADERS_READONLY_API_STATEMENT_TIMEOUT_MS` (default `30000`, max `300000`)
- `TRADERS_READONLY_API_POOL_SIZE` (default `5`, max `32`)
- `TRADERS_READONLY_API_POOL_TIMEOUT_SECONDS` (default `30`, max `120`)

Connection passwords are redacted from configuration representations. Startup
opens one validation connection and fails closed unless PostgreSQL reports
`transaction_read_only=on`. Each connection receives
`default_transaction_read_only=on`, the configured bounded statement timeout,
and `application_name=traders-readonly-api`. The application never creates
schemas, migrations, grants, or roles. Engine resources are disposed during
lifespan shutdown, including failed startup.
