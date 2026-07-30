# Controlled PAPER runtime configuration and dry-run

## Safety boundary

`app/engine_paper/controlled_runtime.py` defines a non-secret configuration
contract and a strictly read-only one-shot planner around the controlled
lifecycle worker. It does not execute the worker, expose an API, enable PAPER,
start a daemon or scheduler, read market data, contact an exchange, or make
LIVE possible.

The only implemented actions are:

```text
VALIDATE_CONFIGURATION
DRY_RUN_PLAN
```

Executable spellings such as `EXECUTE`, `START`, `RUN_CONTINUOUS`, `DAEMON`,
`SCHEDULE`, and `LIVE` are represented only so that the startup gate can deny
them deterministically with `RUNTIME_EXECUTION_NOT_IMPLEMENTED`. There is no
fallback from planning to execution.

## Immutable configuration and safe defaults

`PaperControlledRuntimeConfiguration` is frozen and slotted. Its defaults are
configuration-only, `OFF`, runtime-disabled, dry-run-capable, unauthorized,
one-step, no symbols, supplied-input-only, no database access, and no network,
polling, scheduler, or daemon permission. Missing fields cannot enable PAPER.

PAPER planning requires all of the following to be explicit:

- `runtime_action=DRY_RUN_PLAN`;
- `target=ISOLATED_POSTGRESQL`;
- `execution_mode=PAPER`;
- `runtime_enabled=true` for this bounded planning boundary;
- `dry_run_enabled=true`;
- `explicit_paper_authorization=true`;
- `database_access_mode=ISOLATED_READ_ONLY`;
- a bounded normalized symbol allowlist.

This does not enable executable runtime behavior: no executable action exists.
LIVE and `PRODUCTION_MUTATING` are always denied. One-step scope requires a
bound of one; bounded conditional scope permits at most four plan entries.
Network, polling, scheduling, daemon operation, and any market-data mode other
than `SUPPLIED_ONLY` are forbidden.

Symbols use the existing uppercase Binance-style shape, reject empty values,
wildcards, normalized duplicates, and more than 32 entries. There is no
dynamic discovery.

## Explicit configuration loading

`PaperControlledRuntimeConfigurationLoader` accepts either an explicit Python
mapping or an explicit JSON path. It does not inspect environment variables,
`.env`, the registry, user directories, protected bindings, or recursive file
locations.

The JSON boundary:

- reads at most 64 KiB;
- requires strict UTF-8 and exactly one JSON object;
- rejects duplicate keys, unknown fields, missing/unsupported contract
  versions, invalid typed values, and trailing object ambiguity;
- rejects secret-looking field names at any bounded nested location;
- returns a typed outcome without retaining or logging raw configuration.

Rejected secret field values are neither printed, hashed, fingerprinted, nor
included in results. No active local configuration file is tracked.

## Pure startup gate and target policy

`evaluate_controlled_runtime_startup_gate` is a pure deterministic function.
It performs no database, network, clock, random, logging, filesystem, or
mutable-global operation.

Targets are:

```text
CONFIGURATION_ONLY
ISOLATED_POSTGRESQL
PRODUCTION_READONLY_METADATA
```

`CONFIGURATION_ONLY` never contacts a database or network.
`PRODUCTION_READONLY_METADATA` is also configuration/readiness-only in this
task: it never opens a PAPER graph, direct production DB connection, or
protected binding. Production remains on Alembic `0008`, which does not contain
the repository PAPER graph at `0011`. `PRODUCTION_MUTATING` is denied before
any access.

## Dry-run request, result, and read-only graph load

`PaperControlledRuntimeDryRunRequest` carries explicit request/cycle/
correlation identities, configuration, normalized symbol, exact graph
selectors, optional expected versions, and a presence-only input summary. It
does not contain full candle or approval payloads.

For an isolated target,
`SqlAlchemyPaperControlledRuntimeReadOnlyGraphLoader` opens a fresh session,
starts a PostgreSQL read-only transaction, performs exact command-rooted and
order-role lookups with existing hard row limits, maps to immutable domain
objects, rolls back, and closes the session. It has no latest-row query,
write lock, advisory lock, flush, write, or commit.

`PaperControlledRuntimeDryRunResult` contains only bounded safe metadata:
configuration/gate outcomes, initial state, next stage, at most four plan
items, missing inputs, blockers, graph consistency, correlation, and explicit
read-only proof counters. It contains no ORM values, SQL, DB URI, raw
configuration, candles, approvals, tracebacks, or secrets.

## Existing classifier and stage planning

The planner imports and reuses
`classify_paper_lifecycle_state`; it does not implement a second state machine.
The six authoritative states remain:

```text
APPROVALS_ONLY
ENTRY_ORDER_OPEN
POSITION_OPEN_CURSOR_READY
POSITION_CLOSING_CLOSE_ORDER_OPEN
POSITION_CLOSED
INCONSISTENT
```

Their next stages are respectively `INGEST_COMMAND`, `EXECUTE_ENTRY`,
`EVALUATE_EXIT`, `EXECUTE_CLOSE`, no stage/complete, and fail-closed
inconsistent.

One-step planning emits at most one ready or blocked item. A bounded
multi-stage request may show later lifecycle stages, but every later item is
`CONDITIONAL` with an explicit requirement for a future persisted
precondition. The planner never simulates a durable future graph or claims
that a later stage is currently executable.

Each item names the hypothetical child service and real-cycle pre/post
conditions. This description does not invoke that service. The dry-run service
constructor accepts only a read-only loader; it cannot be wired to ingestion,
ENTRY, exit evaluation, CLOSE execution, or a mutation-oriented UoW.

## Read-only acceptance

The focused suite covers more than 500 cases. PostgreSQL acceptance migrates a
task-owned loopback PostgreSQL 16 database to revision `0011`, visits all five
consistent persisted boundaries plus an inconsistent graph, and compares all
eight PAPER business/audit tables immediately before and after each dry-run.
Independent SQL statement spies and application counters prove:

```text
business mutations = 0
child mutation calls = 0
commits = 0
INSERT / UPDATE / DELETE during dry-run = 0
cursor advances = 0
events or journal additions = 0
```

The database also rejects an attempted mutation inside the read-only
transaction. Cancellation is cooperative before and after graph read.
Planning is deterministic for identical explicit inputs.

## CLI and remaining gates

No CLI is added because the service-level acceptance is complete. Therefore
there is no accidental non-dry-run invocation surface, daemon/scheduler option,
or default production target.

The next separately authorized task may design a single-cycle canary. It must
retain explicit configuration and authorization, provide its own acceptance
and rollback evidence, and must not infer production PAPER enablement from
this dry-run PASS. Production PAPER, continuous runtime, scheduler/daemon,
write API/client work, Binance transport, and LIVE remain unimplemented and
disabled.
