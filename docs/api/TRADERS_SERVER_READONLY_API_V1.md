# Traders server read-only API v1

## Contract and scope

The canonical contract snapshot is
`docs/api/contracts/client-openapi-v1.json`.

```text
API_VERSION = v1
CLIENT_SOURCE = D:\disk_E\game_projects\traders\traders-client\docs\api\openapi-v1.json
CLIENT_SOURCE_SHA256 = 683f5460131e683e89c9ce82be9f05c716f2bbae4e01e07e54db58ea381a7cd4
SNAPSHOT_MATCH = BYTE_FOR_BYTE
```

The module is a local, inert ASGI implementation. It has not been deployed,
bound to a port, connected to PostgreSQL, added to Compose, or wired to the
desktop client.

## Architecture

```text
FastAPI GET route
→ validated path/query parameters
→ ApiQueryService
→ read-only repository protocol
→ persistence-neutral record
→ ContractMapper
→ typed API v1 envelope
```

Public Pydantic models are contract models only. ORM rows, raw result JSON,
observer evidence dictionaries, SQLAlchemy sessions, filesystem paths, and
internal exceptions do not cross the HTTP boundary.

`create_app()` accepts only explicit repositories, immutable API settings, and
an optional clock. With no repositories it performs no discovery and returns
the controlled `SERVICE_NOT_CONFIGURED` error when a business endpoint is
called.

## Endpoints

| Method | Path | Projection |
|---|---|---|
| GET | `/api/v1/health` | Overall and per-service observation |
| GET | `/api/v1/dashboard` | Markets, recent persisted runs, active incident count |
| GET | `/api/v1/markets` | Deterministically ordered market summaries |
| GET | `/api/v1/markets/{symbol}` | Latest closed-only candle and market state |
| GET | `/api/v1/analysis/{symbol}` | Latest persisted analysis projection |
| GET | `/api/v1/setups` | Filtered cursor page |
| GET | `/api/v1/setups/{setup_id}` | Non-executable setup detail |
| GET | `/api/v1/incidents` | Filtered cursor page |
| GET | `/api/v1/incidents/{incident_id}` | Redacted incident detail |

There are no mutation, WebSocket, SSE, administration, pipeline-control, order,
execution, credential, Docker, database-console, or migration endpoints.
Swagger, ReDoc, and the HTTP OpenAPI route are disabled. The in-memory
`app.openapi()` method remains available for contract tests.

## Repository boundaries

`HealthReadRepository`, `MarketReadRepository`,
`AnalysisReadRepository`, `SetupReadRepository`,
`IncidentReadRepository`, and `DashboardReadRepository` expose read methods
only. `ApiRepositories` is the immutable composition object.

`SqlAlchemyReadAdapter` reads the existing `candles_*`,
`online_pipeline_runs`, and `online_pipeline_results` tables. Its session or
session factory is injected. Construction does not query, and the adapter
contains only SQLAlchemy `SELECT` statements.

`SemanticIncidentReadAdapter` accepts an injected loader of already-redacted
semantic incident snapshots. It does not discover or open observer/soak paths.
A controlled integration must select an accepted durable source and supply the
loader explicitly.

Neither adapter performs analytics, invokes an engine, changes persistence, or
falls back to Binance.

## Evidence mapping

`DIRECT` means a stable persisted value is projected. `DERIVED` means a
deterministic, documented translation of persisted fields. `OPTIONAL` means the
contract requires the key but permits JSON null. No mandatory field is marked
`NOT_OBSERVABLE`.

| API field | Server source | Mapping | Class | Safety |
|---|---|---|---|---|
| envelope `api_version` | accepted contract | constant `v1` | DIRECT | no runtime discovery |
| envelope `generated_at` | injected API clock | aware UTC → RFC 3339 `Z` | DERIVED | response assembly time only |
| health `status` | latest candle/run observations | conservative rank; unknown stays `UNKNOWN` | DERIVED | never promotes missing data to OK |
| health `observed_at` | candle `updated_at_utc`, run `updated_at` | latest source observation | DIRECT | aware UTC required |
| service `name` | fixed adapter source names | `market-data`, `online-orchestrator` | DERIVED | no host/container identifiers |
| service `status` | candle availability, run/freshness status | contract-safe health mapping | DERIVED | missing → `NOT_AVAILABLE`/`UNKNOWN` |
| service `message` | repository record | unchanged safe text or null | OPTIONAL | no exception text |
| market `symbol` | candle/run `symbol` | uppercase validated symbol | DIRECT | contract pattern |
| market `status` | persisted freshness status | known-state mapping | DERIVED | future enum → `UNKNOWN` |
| market `latest_price` | latest closed candle `close` | finite Decimal → string | OPTIONAL | no binary float |
| market `closed_until(_ms)` | latest candle `close_time_ms` | inclusive close + 1; UTC mirror | DERIVED | closed-only |
| market `regime` | result `analysis_payload_json.regime` | stable field or null | OPTIONAL | raw analysis context excluded |
| market `setup_status` | result setup status | enum-safe mapping | DIRECT | unknown → `UNKNOWN` |
| market `risk_status` | result risk status | stable string or null | OPTIONAL | not execution approval |
| market `updated_at` | run/candle update timestamp | aware UTC → `Z` | DIRECT | naive time rejected by mapper |
| market OHLCV | latest closed candle Decimal columns | finite Decimal → string | OPTIONAL | no unclosed/future row |
| market `has_gaps`, `enough_data` | persisted market payload | bool or null | OPTIONAL | absence is never false |
| market `future_bars_used` | run safety flag | exposure allowed only when false | DIRECT | true fails mapping |
| analysis identity/window/status | result analysis payload + run identity | stable projection | DIRECT | raw payload excluded |
| analysis market health | payload/run freshness | contract-safe health mapping | DERIVED | unknown → `UNKNOWN` |
| analysis regime/impulse/entry | result analysis payload | stable strings or null | OPTIONAL | no recalculation |
| analysis direction | stable direction/action | known direction or `UNKNOWN` | DERIVED | no bullish/bearish fabrication |
| analysis confidence | persisted normalized score | accept only `[0,1]`, else null | OPTIONAL | not a financial value |
| analysis reasons | `reason_codes` | immutable string list | DIRECT | no exception/context leak |
| analysis `updated_at` | run `updated_at` | aware UTC → `Z` | DIRECT | source time |
| setup identity/window/status/type | setup payload + run | stable projection | DIRECT | setup ID remains opaque |
| setup direction | `direction_hint` | known direction or `UNKNOWN` | DERIVED | unknown-safe |
| setup quality/score | setup payload | score accepted only `[0,1]` | DIRECT | no recomputation |
| setup confirmation/reasons/warnings/invalidation | setup payload | immutable lists/strings | DIRECT | context excluded |
| strategy/risk/paper status | corresponding result payload/run | stable strings or null | OPTIONAL | observational only |
| hypothetical levels/RR | paper result payload | finite Decimal string or null | OPTIONAL | always non-executable |
| setup `executable` | API safety invariant | constant false after record check | DERIVED | true record is rejected |
| run identity/window/status | `online_pipeline_runs` | known status; skipped variants collapse to `SKIPPED` | DERIVED | raw errors excluded |
| run attempt count | `freshness_attempt_count` | non-negative integer | DIRECT | diagnostic only |
| run result count | joined result cardinality | count | DERIVED | no payload exposure |
| semantic incident identity/state/severity/time | injected redacted incident record | stable projection | DIRECT | no path discovery |
| pipeline incident identity | anomalous persisted run | `pipeline:{run_id}` | DERIVED | deterministic |
| pipeline incident title/description | anomalous run classification | fixed safe text | DERIVED | raw `error_message` excluded |
| incident symbol/timeframe/boundary/reason | semantic record or anomalous run | stable fields or null | DIRECT | no evidence blob |
| page `limit` | validated query | OpenAPI range 1–100 | DIRECT | validated before repository |
| page `next_cursor` | final `(updated_at,id)` | versioned base64url JSON + checksum | DERIVED | offset is not used |

## Serialization and unknowns

- Every external timestamp is timezone-aware UTC and ends in `Z`.
- Candle `close_time_ms` is translated to the exclusive logical boundary with
  `+ 1`.
- Financial values remain `Decimal` until finite base-10 string serialization.
- Nullable keys are present with JSON null when data is absent.
- Unknown internal enum strings map only to contract `UNKNOWN`; they never map
  to `OK`, approval, bullish, or bearish states.
- Setup output is always non-executable.

## Pagination and filters

Setup and incident list operations validate `limit`, `cursor`, `symbol`,
`status`, `from`, and `to` before invoking a repository. Incidents also
validate `severity`.

Ordering is descending `(updated_at, resource_id)`. The cursor is opaque,
URL-safe, versioned, kind-scoped, and checksummed. It encodes the final stable
ordering key rather than an offset. `from` is inclusive, `to` is exclusive,
and a reversed range returns `INVALID_REQUEST`. Invalid cursors return
`INVALID_CURSOR`. Final pages return `next_cursor: null`.

## Errors

All controlled errors use the accepted v1 envelope and a generated safe request
ID. Implemented codes are:

```text
INVALID_REQUEST
INVALID_CURSOR
VALIDATION_ERROR
RESOURCE_NOT_FOUND
CONTRACT_VERSION_UNSUPPORTED
DATA_NOT_AVAILABLE
SERVICE_NOT_CONFIGURED
INTERNAL_ERROR
```

Repository failures are internal errors, never 404. Responses contain no
exception representation, traceback, SQL, path, DSN, credential, or raw
upstream body.

## Configuration and security boundary

There is no environment, `.env`, DSN, credential, service, socket, or
filesystem auto-discovery. There are no startup events or background tasks.
The future composition root must explicitly inject:

- a read-only session factory;
- the accepted semantic incident loader if used;
- immutable `ApiSettings`;
- authentication/rate-limit middleware defined by a later contract.

## Controlled integration prerequisites

Before deployment, the next task must independently prove:

1. exact merge scope and dependency lock/update policy;
2. a PostgreSQL role with transaction-level read-only enforcement;
3. accepted session and incident-source wiring;
4. localhost-only binding and explicit service/profile configuration;
5. authentication, authorization, rate limits, timeouts, and response limits;
6. production query plans/cardinality and redaction;
7. controlled canary, rollback, and client HTTP transport.

## Non-goals and deferred work

This task does not merge, push, deploy, bind a port, connect to any database,
read observer artifacts, modify Compose, run migrations, invoke Binance, add
client transport, or change the active server/client checkouts.

Production wiring, query-plan validation, authentication, deployment, and
client transport belong to
`TRADERS-SERVER-READONLY-API-CONTROLLED-INTEGRATION-01`.
