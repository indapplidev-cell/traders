# PAPER transactional repository foundation

## Scope

This implementation adds synchronous SQLAlchemy repositories and a single-owner
Unit of Work for the already-approved immutable PAPER domain and migration
`0009_paper_trading_persistence_foundation`. It does not add a worker, polling,
simulation, API, client, deployment, exchange transport, or mode enablement.

## Inventory and reuse

| AREA | FILE | SYMBOL | REUSED | ADAPTED | NEW | RATIONALE |
|---|---|---|---|---|---|---|
| ORM base | `app/db/base.py` | `Base` | yes | no | no | existing model registry |
| Session factory | `app/db/session.py` | `get_session_factory` | yes | no | no | one existing sync SQLAlchemy stack |
| PAPER ORM | `app/db/paper_models.py` | eight PAPER records | yes | no | no | migration-aligned persistence records |
| Mapping | `app/db/paper_mappings.py` | domain/ORM value mappers | yes | no | no | pure DB-independent conversion |
| State machines | `app/engine_execution/paper_state_machine.py`, `app/engine_position/paper_state_machine.py` | order/position transitions | yes | no | no | repository never reimplements workflow rules |
| PostgreSQL normalization | `app/db/connection_failure.py` | structured SQLSTATE traversal convention | yes | adapted | no | safe structured classification |
| Unit of Work | `app/engine_paper/unit_of_work.py` | `PaperUnitOfWork` | no | no | yes | sole outer transaction owner |
| Results | `app/engine_paper/repository_results.py` | typed outcomes | no | no | yes | stable safe repository boundary |
| Repositories | `app/engine_paper/repositories.py` | command/order/position/exit/journal and atomic workflows | no | no | yes | durable aggregate graph |
| Recovery | `app/engine_paper/commit_recovery.py` | `recover_uncertain_commit` | no | no | yes | bounded fresh-session lookup |

The stack is synchronous. `Session` uses the existing factory defaults:
`autoflush=False`, `autocommit=False`, default PostgreSQL `READ COMMITTED`, and
default expiration on commit. Repository methods may flush and use a savepoint
to normalize a concurrent unique-insert race, but they never commit.

## Transaction and lock contract

`PaperUnitOfWork` creates one Session, begins one explicit outer transaction,
commits only on an explicit `uow.commit()`, rolls back on exceptions or an
uncommitted exit, and closes deterministically. Re-entry and double commit fail
closed.

The deterministic lock order is:

```text
command -> order -> position -> exit decision -> fill/event/journal inserts
```

The actual entry flow locks command/order before position insertion. The close
flow locks close order before position and reads the immutable exit decision
after both locks. No code acquires these locks in reverse order. Aggregate
mutations use `SELECT FOR UPDATE`, verify expected versions, invoke the pure
state machine, require exact `old + 1`, and flush aggregate plus audit rows in
one outer transaction.

## Semantic idempotency

Explicit tuples live in `semantic_idempotency.py`:

- command: all 27 immutable public command fields;
- order creation: identity, command, symbol, side, type, requested quantity,
  and creation time (mutable state and `updated_at` are excluded);
- fill: all 16 immutable fill fields;
- exit decision: all 10 immutable decision fields;
- journal: all nine immutable event fields.

A deterministic-key hit is compared using the appropriate tuple. Equal data
returns `EXISTING_IDEMPOTENT`; different material data returns
`IDEMPOTENCY_CONFLICT`; existing rows are never overwritten.

## Failure and uncertain-COMMIT behavior

Public results contain a stable reason code and bounded static message. Raw
SQL, URI values, driver messages, and `IntegrityError.orig` never cross the
repository boundary. SQLSTATE drives unique, foreign-key, check,
serialization, deadlock, timeout, and connection classification. The named
active-position index maps to `ACTIVE_POSITION_CONFLICT`.

Uncertain COMMIT recovery never retries mutation. It opens a fresh Session for
each of at most three lookups, compares the deterministic record semantically,
and returns committed, not-committed, conflict, or unresolved. Backoff is
bounded and the failed/uncertain Session is never reused.

## Bounded reads

Command graphs are capped at 100 rows per component and journal lists at 200
rows. Every multi-row query has a stable indexed ordering and explicit limit.
No polling or destructive journal API exists.
