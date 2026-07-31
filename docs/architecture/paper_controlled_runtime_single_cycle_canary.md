# Controlled PAPER runtime single-cycle canary

## Purpose and boundary

`app/engine_paper/controlled_runtime_canary.py` is the explicit one-shot
mutation boundary between the existing read-only runtime planner and the
existing controlled lifecycle worker. One invocation performs one fresh
preflight, one existing read-only dry-run, at most one
`ADVANCE_ONE_LIFECYCLE_STEP` worker call, one fresh postflight verification,
and returns. It has no continuation, retry, polling, sleep, daemon, scheduler,
API, client, exchange transport, or market-data fetch.

This boundary authorizes only `SINGLE_CYCLE_CANARY` with:

```text
target = ISOLATED_POSTGRESQL
execution mode = PAPER
runtime enabled = true
dry-run enabled = true
explicit PAPER authorization = true
scope = ADVANCE_ONE_LIFECYCLE_STEP
max stages = 1
database access = ISOLATED_CANARY_READ_WRITE
market data = SUPPLIED_ONLY
network/polling/scheduler/daemon = false
```

`CONFIGURATION_ONLY`, production, shared, unknown, LIVE, generic execution,
continuous execution, and every production database role or name are rejected.
The default controlled-runtime configuration remains OFF and non-executable.

## Isolated identity and arming

`PaperControlledRuntimeCanaryTargetIdentity` is frozen, slotted, non-secret,
and expiring. It binds the task and run IDs to bounded task-owned database and
role names, revision `0011`, a deterministic ownership marker, and explicit
creation/expiry times. The PostgreSQL validator opens a read-only transaction
and reads only `current_database()`, `current_user`, and `alembic_version`.
It never reads a URI, password, protected binding, production PAPER graph, or
environment array.

`PaperControlledRuntimeCanaryArming` is a single-invocation deterministic
safety acknowledgement, not authentication. It binds the exact task/run,
configuration, target identity, expected stage, preflight graph fingerprint,
expiry, `single_use=true`, and the literal one-stage acknowledgement. It cannot
authorize production or more than one stage.

The graph fingerprint is SHA-256 over canonical, sorted, non-secret material
identity only: public entity IDs, role/state/version, symbol/mode, and expected
stage. Credentials, database locators, approvals, candles, and secret-derived
values are excluded. A fresh graph is loaded before the dry-run and again
after it. Any intervening change stops before worker invocation with
`CANARY_GRAPH_CHANGED_AFTER_DRY_RUN`.

## Preflight, dry-run, and invocation

Preflight validates the exact configuration/action/target, target ownership
and migration head, PAPER-only authorization, one-step scope, stage bound,
symbol allowlist, supplied-only/no-network restrictions, graph consistency,
arming, expiry, cancellation, and the stage-specific exact mutation budget.

The existing `PaperControlledRuntimeDryRunService` is reused with a derived
read-only view of the same configuration. It uses the existing lifecycle
classifier and must return `DRY_RUN_NEXT_STAGE_READY` for the exact expected
worker stage. Dry-run commits and business mutations remain zero.

The service has one `run_cycle` call site. An instance-local lock serializes
identical concurrent invocations without a persisted canary lock table.
Persisted graph state and existing child-service locking/idempotency remain
the cross-process authority. Replay reloads the advanced graph and stops before
a second worker call. There is no canary-layer retry; child uncertain-commit
handling is unchanged.

## Stage-specific mutation budgets

Budgets are exact:

| Canary stage | Exact material/audit delta |
|---|---|
| `INGEST_COMMAND` | command +1, order +1, order events +3, journal +4 |
| `EXECUTE_ENTRY` | order update +1, fill +1, position +1, cursor +1, order event +1, journal +2 |
| `EVALUATE_EXIT_NO_TRIGGER` | cursor update +1 and no material inserts |
| `EVALUATE_EXIT_TRIGGER` | exit decision +1, order +1, position update +1, cursor update +1, order events +3, journal +4 |
| `EXECUTE_CLOSE` | fill +1, order update +1, position update +1, order event +1, journal +2 |

Postflight uses a third fresh persisted-graph load. It verifies classifier
consistency, one attempted/completed stage maximum, expected no-trigger versus
trigger child outcome, exact row/version/event/journal deltas, and a bounded
ID/state/version summary. A committed child transaction is never rolled back
or automatically repeated after a postflight mismatch.

## Cancellation and faults

Cooperative cancellation is checked before target validation, before dry-run,
after dry-run, before arming verification, immediately before the worker call,
and after the child commit. Pre-commit cancellation returns zero worker calls.
Post-commit cancellation still performs postflight and returns the durable
committed graph as `CANARY_CANCELLED_AFTER_COMMITTED_STAGE`.

Injected faults cover configuration, target, dry-run, fingerprint, invocation,
and postflight boundaries. Pre-worker faults produce zero business mutation.
Post-worker faults report a durable single invocation and never retry. A later
explicit invocation observes the committed graph through normal replay logic.

## Isolated acceptance

Five independently reset task-owned PostgreSQL 16 cases cover ingestion,
ENTRY, exit/no-trigger, exit/trigger, and CLOSE. A separate controlled
sequence uses five distinct requests, arming objects, fingerprints, dry-runs,
worker calls, and postflights. Its final graph is:

```text
1 command
2 orders
2 fills
1 position
1 cursor
1 exit decision
8 order events
12 journal rows
position CLOSED
entry/exit fees and realized PnL applied once
```

This is isolated service-level acceptance only. No production migration,
PAPER runtime enablement, background runtime, API/client integration, Binance
call, or LIVE behavior is implemented. A separately authorized bounded
sequence canary remains the next runtime-enablement engineering gate.
