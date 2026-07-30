# Controlled PAPER lifecycle worker

## Status and boundary

`app/engine_paper/controlled_worker.py` is a caller-invoked orchestration
controller for an already approved PAPER lifecycle. It is not a daemon,
scheduler, market watcher, API, deployment unit, or global PAPER-mode switch.
It has no Binance, network-market-data, FastAPI, client, polling, sleep, or
production-binding dependency.

The implemented chain is:

```text
final approvals
-> command + OPEN ENTRY order
-> deterministic ENTRY fill + FILLED order + OPEN position + cursor
-> bounded exit window and cursor advance
or
-> exit decision + CLOSING position + OPEN EXIT/CLOSE order
-> deterministic CLOSE fill + FILLED order + CLOSED position
```

PAPER and LIVE remain disabled globally. The controller can run only when each
cycle explicitly supplies `execution_mode=PAPER` and
`explicit_paper_authorization=true`.

## Inventory and authority

| AREA | FILE | SYMBOL | CURRENT_AUTHORITY | REUSED | ADAPTED | NEW | RATIONALE |
|---|---|---|---|---|---|---|---|
| final approval ingestion | `app/engine_paper/command_ingestion_service.py` | `PaperCommandIngestionService` | validates the final strategy/quantity/risk chain and atomically creates command + OPEN ENTRY order | yes | no | no | worker must not calculate approval, risk, or quantity |
| ENTRY/CLOSE execution | `app/engine_paper/order_execution_service.py` | `PaperOrderExecutionService` | deterministic fill, order transition, position accounting, ENTRY cursor creation, replay and uncertain commit | yes | no | no | worker must not calculate fill, fee, or PnL |
| ENTRY cursor initialization | `app/engine_paper/order_execution_service.py` | `_entry_cursor` and `apply_entry_fill_and_open_position` | cursor is created from `PaperFill.source_closed_until_ms` in the ENTRY UoW | yes | no | no | post-commit cursor repair is forbidden |
| exit evaluation | `app/engine_paper/exit_evaluation_service.py` | `PaperExitEvaluationService` | bounded contiguous 1m evaluation and atomic cursor/exit/CLOSING/CLOSE-order graph | yes | no | no | worker supplies one explicit window |
| transactions | `app/engine_paper/unit_of_work.py` | `PaperUnitOfWork` | one session/transaction per application-service call | yes | no | no | no cross-stage transaction |
| graph persistence | `app/engine_paper/repositories.py` | `get_command_graph` | bounded command-rooted immutable domain graph | yes | yes | no | worker adds a read-only role-aware loader |
| lifecycle graph loader | `app/engine_paper/controlled_worker.py` | `SqlAlchemyPaperLifecycleGraphLoader` | fresh UoW, exact command identity, bounded role lookup | no | no | yes | prevents stale ORM authority |
| lifecycle classifier | `app/engine_paper/controlled_worker.py` | `classify_paper_lifecycle_state` | pure structural and audit invariant classification | no | no | yes | no I/O, time, random, repair, or mutable global |
| cycle orchestration | `app/engine_paper/controlled_worker.py` | `PaperControlledLifecycleWorker` | chooses one next stage from persisted state and delegates it | no | no | yes | resumable control without runtime enablement |
| candle input | existing immutable service requests | `candidate_candles` / `candles` | caller supplies separate ENTRY, EXIT-window, and CLOSE inputs | yes | no | no | no worker market-data fetch |
| cancellation | cycle request | `PaperLifecycleCancellationAuthority` | cooperative caller-owned check between stage boundaries | no | no | yes | child commits are never interrupted |
| configuration default | `app/engine_safety/paper_domain.py` and existing service validation | `ExecutionMode` | OFF/PAPER/LIVE fail-closed vocabulary | yes | no | no | no global default or setting is changed |
| logging/CLI/runtime | existing project conventions | none added | no worker logger, CLI, service, scheduler, or background loop | no | no | no | callable service/controller is sufficient |

Cycle identity, correlation, causation, timestamps, deterministic material IDs,
expected versions, approval identity, entry candle, exit window, close candle,
and safety directive remain explicit in the cycle or its immutable nested
application-service request. Persisted facts cannot be overridden by caller
flags.

## Cycle contract

`PaperLifecycleCycleRequest` is frozen and slotted. It carries:

- public `cycle_id`, contract version, creation time, correlation identity;
- explicit PAPER authorization and a bounded scope;
- exact known command/order/fill/position/cursor/decision identities;
- separate optional `PaperCommandIngestionRequest`,
  `PaperEntryExecutionRequest`, `PaperExitEvaluationRequest`, and
  `PaperCloseExecutionRequest`;
- an optional cooperative cancellation authority.

Material service fields are not flattened or duplicated. Before invocation the
worker verifies exact identity/correlation agreement, revalidates PAPER
authorization, and reconstructs only the existing nested request where
authorization/correlation must be pinned.

`PaperLifecycleCycleResult` is also frozen and slotted. It contains only a
bounded safe summary: initial/final state, at most four trace items, child
outcome/reason strings, persisted public identities, state/version/boundary,
and correlation ID. It contains no ORM objects, SQL, candles, approval
payloads, exceptions, tracebacks, bindings, or secrets.

## Pure lifecycle classifier

The classifier has six states:

```text
APPROVALS_ONLY
ENTRY_ORDER_OPEN
POSITION_OPEN_CURSOR_READY
POSITION_CLOSING_CLOSE_ORDER_OPEN
POSITION_CLOSED
INCONSISTENT
```

It verifies exact cardinality and causal relationships for command, ENTRY
order/fill, position, cursor, exit decision, EXIT/CLOSE order/fill, plus the
canonical order-event and journal multisets at each boundary. It treats a
missing cursor, partial material graph, duplicate material identity, role
conflict, policy/boundary mismatch, or incomplete audit graph as
`INCONSISTENT`. It never repairs.

The function performs zero DB/network/clock/random/global-state operations.

## Stage and scope model

Stages are:

```text
INGEST_COMMAND
EXECUTE_ENTRY
EVALUATE_EXIT
EXECUTE_CLOSE
COMPLETE
BLOCKED
FAILED
CANCELLED
```

`ADVANCE_ONE_LIFECYCLE_STEP` executes no more than one mutating application
stage. It returns immediately after ingestion, ENTRY, cursor advance, exit
preparation, or CLOSE. In particular, exit preparation never executes CLOSE in
the same one-step call.

`ADVANCE_UNTIL_BLOCKED_WITHIN_REQUEST` is optional caller-selected bounded
composition. `max_stages` is mandatory and cannot exceed
`MAX_STAGES_PER_CYCLE = 4`. Each iteration reloads the graph, consumes only
already supplied stage input, and stops on missing input, failure,
cancellation, completion, or the explicit bound. There is no recursion,
polling, wait, future-input fetch, or retry sleep. Child service attempts are
one.

## Source of truth and transactions

Before the first stage and after every committed child result, the worker opens
a fresh read-only UoW, loads the command-rooted graph and exact order roles,
converts it to immutable domain values, closes the UoW, and classifies it.
Mutable ORM values never survive a child boundary. No "latest entity" lookup
or unbounded scan is used.

Each child retains its existing atomic transaction:

```text
ingestion UoW
ENTRY UoW
NO_TRIGGER or trigger exit UoW
CLOSE UoW
```

The worker never calls `Session.commit` or `PaperUnitOfWork.commit` and never
wraps multiple stages in one transaction. A committed stage remains durable
when a later stage is missing, cancelled, or fails.

## Resume, replay, cancellation, and failures

Resume is derived only from the persisted graph:

- command persisted with no ENTRY candle -> wait at `EXECUTE_ENTRY`;
- ENTRY persisted with cursor and no exit window -> wait at `EVALUATE_EXIT`;
- NO_TRIGGER persisted -> wait for the next explicit contiguous window;
- exit graph persisted with no CLOSE candle -> wait at `EXECUTE_CLOSE`;
- CLOSED position -> `CYCLE_COMPLETE` with zero mutation.

Replaying a request first reloads the graph. Completed mutations are not
blindly repeated; the next eligible stage is selected or the cycle returns
complete/awaiting-input. Child outcome and reason codes are preserved in the
bounded trace.

Cancellation is checked before initial load, before each stage, after reload,
and before a next bounded stage. It never interrupts a child transaction.
Cancellation observed after a successful child and persisted reload returns
`CANCELLED_AFTER_COMMITTED_STAGE` with the final persisted summary.

Worker fault points surround graph load, child invocation, post-child reload,
result construction, and bounded-stage transitions. A simulated worker crash
does not alter child transaction semantics. A later explicit cycle reloads and
resumes from the durable graph.

## Isolated validation

The retry suite uses a task-owned loopback PostgreSQL 16 database migrated to
revision `0011_paper_close_causal_boundary_and_exit_evaluation_cursor`.
It proves:

- more than 340 collected worker retry cases;
- all six classifier states and inconsistent graph variants;
- OFF/LIVE/unknown and missing-authorization zero-mutation denial;
- exact one-step and bounded four-stage behavior;
- missing-input, child mapping, replay, cancellation, and worker faults;
- two-cycle concurrency for ingestion, ENTRY, no-trigger, trigger, and CLOSE;
- one complete lifecycle with exactly 1 command, 2 orders, 2 fills,
  1 position, 1 cursor, and 1 exit decision;
- 8 order events and 12 journal rows;
- CLOSED accounting and fees/realized PnL unchanged by replay.

No migration, ORM schema, child-service semantics, order/position state graph,
event vocabulary, production binding, Compose service, API, client, or
autonomous runtime is added or changed.

## Remaining enablement gates

The separate configuration and read-only dry-run boundary is documented in
`paper_controlled_runtime_configuration_and_dry_run.md`. It validates safe
configuration and can plan the next persisted stage without invoking this
worker. A later, separately authorized task is still required for any
single-cycle runtime canary. Production PAPER enablement, scheduler/daemon
operation, API/client visibility, exchange transport, and all LIVE behavior
remain out of scope and disabled.
