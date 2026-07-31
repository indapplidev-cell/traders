# Controlled bounded-sequence PAPER canary

`app/engine_paper/controlled_runtime_sequence_canary.py` composes the proven
single-cycle canary boundary into one explicitly authorized invocation of one
to five ordered PAPER lifecycle steps.

## Boundary

The sequence target is `ISOLATED_POSTGRESQL` at Alembic revision `0011`.
`PAPER`, runtime enablement, read-only dry-run, PAPER authorization, and
sequence authorization must all be explicit. Network access, polling,
scheduling, daemon mode, LIVE, production mutation, dynamic stage discovery,
and implicit continuation are rejected.

The hard limits are:

```text
MIN_SEQUENCE_STEPS = 1
MAX_SEQUENCE_STEPS = 5
MAX_WORKER_INVOCATIONS_PER_STEP = 1
MAX_MUTATING_STAGES_PER_STEP = 1
MAX_TOTAL_WORKER_INVOCATIONS = 5
MAX_TOTAL_MUTATING_STAGES = 5
```

The implementation iterates over an immutable tuple with a bounded `for`.
There is no unbounded loop, recursive continuation, background process,
automatic retry, waiting, or market-data fetch.

## Composition and transactions

Each explicit step performs a fresh persisted-graph load and derives a fresh
non-secret fingerprint. It then creates a fresh step-specific single-cycle
target identity and arming contract and calls
`PaperControlledRuntimeSingleCycleCanaryService.run` once at most.

The sequence service has no command-ingestion, order-execution,
exit-evaluation, mutation-UoW, session commit, or direct child-service
dependency. The existing single-cycle canary retains dry-run, arming,
fingerprint, one-worker, one-mutating-stage, postflight, and mutation-budget
authority. Each child application service therefore retains its own
transaction. There is no sequence-spanning business transaction and no
compensating mutation.

## Durable prefix and resume

After each successful step, its child transaction is already durable. A later
failure, cancellation, or injected fault stops the sequence without rolling
back or replaying the committed prefix.

Resume infers the longest completed prefix from the persisted material graph:
entity identities, lifecycle state, entity versions, cursor advancement, exit
decision, and close fill. No sequence history or lock table is added. A graph
that cannot prove one contiguous prefix returns
`SEQUENCE_RESUME_STATE_AMBIGUOUS` before a worker call.

Completed replay returns `SEQUENCE_ALREADY_COMPLETED` with zero worker calls
and zero new material mutations. Partial resume skips every proven completed
step and begins at the first compatible uncompleted step.

## Mutation budgets and results

Each step carries an exact mutation budget for commands, orders, fills,
positions, cursors, exit decisions, order events, journal rows, entity
updates/versions, fees, and PnL. The plan budget must equal the deterministic
sum of its step budgets. The service verifies every returned single-cycle
delta and the aggregate executed budget. Any mismatch stops immediately as
`SEQUENCE_MUTATION_BUDGET_MISMATCH`.

Results contain only bounded safe summaries: states, stages, outcome codes,
counts, non-secret row/version deltas, durable prefix, next resumable index,
and cancellation/fault classification. They contain no credentials, URI, raw
SQL, ORM objects, full candle/approval payloads, or tracebacks.

## Proven isolated behavior

The task-owned PostgreSQL 16 proof covered prefixes of lengths one through
five, compatible targeted subsequences, the full five-step lifecycle,
completed replay, partial resume after prefixes one through four, ambiguous
resume denial, concurrent identical invocation, cooperative cancellation, and
fault-after-step recovery for every durable prefix.

The full invocation produced exactly:

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
fees once
realized PnL once
```

This is isolated operator-authorized canary execution only. It does not enable
production PAPER, continuous runtime, daemon/scheduler/polling, API/client,
exchange transport, or LIVE trading.
