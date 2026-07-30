# PAPER order execution application service

## Scope

`app.engine_paper.order_execution_service` executes exactly one immutable,
caller-supplied PAPER entry or close request. It is an application service, not
a worker: it has no polling, scheduler, queue, market-data query, network
client, wall clock, random identity generation, FastAPI route, production
binding, or exchange transport.

The service owns orchestration only:

```text
caller request
-> one PaperUnitOfWork
-> authoritative repository graph
-> existing deterministic fill simulator exactly once
-> existing atomic repository operation
-> UoW commit
-> bounded typed result
```

## Inventory and authority reuse

| AREA | FILE | SYMBOL | CURRENT_AUTHORITY | REUSED | ADAPTED | NEW | RATIONALE |
|---|---|---|---|---|---|---|---|
| Command/order/fill | `app/engine_execution/paper_models.py` | `PaperExecutionCommand`, `PaperOrder`, `PaperFill` | Immutable approved execution graph | yes | no | no | Request cannot override symbol, side, quantity, or policy identities |
| Order transitions | `app/engine_execution/paper_state_machine.py` | `fill_order` | OPEN to FILLED, exact version, one fill | yes | no | no | Service does not duplicate transition rules |
| Position transitions | `app/engine_position/paper_state_machine.py` | `apply_entry_fill`, `apply_close_fill` | OPEN/CLOSING/CLOSED and PnL state | yes | no | no | Service does not calculate PnL or fees |
| Exit decision | `app/engine_exit/paper_exit.py` | `PaperExitDecision` | Immutable caller-prepared exit cause/quantity | yes | no | no | Service never selects an exit cause |
| Events | `app/engine_journal/paper_events.py` | `PaperDomainEvent` | Immutable bounded audit event | yes | identity/time injection | no | Caller IDs and UTC operation time are explicit |
| Policy | `app/engine_paper/fill_policy.py` | `PaperFillSimulationPolicy` | Exact 1m/1-candle/2-bps/10-bps v1 policy | yes | no | no | Policy object is matched against command identities |
| Exit cursor | `app/engine_paper/exit_evaluation_cursor.py` | `PaperExitEvaluationCursor`, `paper_exit_evaluation_cursor_id` | One deterministic v1 checkpoint per position | yes | ENTRY composition | no | Successful ENTRY cannot commit an OPEN position without its exit checkpoint |
| Exit policy identity | `app/engine_paper/exit_evaluator.py` | `PAPER_EXIT_EVALUATION_POLICY_ID` | Existing `STOP_FIRST_CONSERVATIVE` exit-evaluation authority | yes | no | no | Cursor policy is not a caller-selected fill policy |
| Simulator | `app/engine_paper/fill_simulator.py` | `simulate_paper_fill` | Deterministic candle eligibility, price, fee, fill identity | yes | no | no | One pure call per execution attempt |
| Repositories | `app/engine_paper/repositories.py` | `apply_entry_fill_and_open_position`, `apply_close_fill_and_close_position` | Locks, CAS, atomic ENTRY fill/order/position/cursor/audit and CLOSE graph | yes | ENTRY cursor composition | no | No graph fragments are persisted by the service |
| Unit of Work | `app/engine_paper/unit_of_work.py` | `PaperUnitOfWork` | Sole Session/transaction/commit owner | yes | factory injection | no | Exactly one UoW per attempt |
| Recovery | `app/engine_paper/commit_recovery.py` | `recover_uncertain_commit` | Three fresh-session lookups, no mutation replay | yes | graph lookup callback | no | Failed Session is never reused |
| Bounded graph | `app/engine_paper/repositories.py` | `get_command_graph` | Stable bounded graph read, maximum 100 | yes | exit/replay selection | no | Existing repository has no separate exit getter |
| Application contract | `app/engine_paper/order_execution_service.py` | entry/close requests, result, service | N/A | no | no | yes | Callable boundary required by this task |

## Immutable requests and result

`PaperEntryExecutionRequest` and `PaperCloseExecutionRequest` are frozen,
slotted dataclasses. Candidate candles must be an immutable tuple of at most
64 values. IDs are bounded public identities. Expected versions, policy,
price/fee quantums, quote asset, event/journal IDs, correlation/causation IDs,
and an explicit UTC operation timestamp are mandatory. No aggregate, ORM row,
Session, credential, or database location is accepted.

`PaperOrderExecutionResult` contains only bounded structural metadata:
operation, typed outcome/reason, public causal IDs, states, versions,
simulation/repository outcomes, source close boundary, and the safe cursor
summary (`cursor_id`, version, last-evaluated boundary, policy ID) for ENTRY.
It never contains SQL, ORM objects, exceptions, traceback, candle payloads,
environment data, or credentials.

## Entry sequence

1. Validate immutable request shape.
2. Open one UoW and load command/order from repositories.
3. Validate PAPER approval, role identity, command/order relation,
   symbol/side/type/quantity, policy IDs, state, and expected version.
4. Build `FillSimulationRequest` from authoritative command/order plus explicit
   candles/policy/precision context.
5. Run the existing simulator exactly once.
6. Return every simulator non-success outcome without repository mutation or
   commit.
7. Validate the caller fill ID against deterministic fill identity.
8. Build order/position projections with the existing state machines and inject
   event/journal IDs and UTC operation timestamp.
9. Derive the initial cursor from the newly simulated ENTRY fill and position:
   both cursor boundaries equal `PaperFill.source_closed_until_ms`, the
   evaluation policy is the existing `PAPER_EXIT_EVALUATION_POLICY_ID`, the
   cursor ID uses the existing v1 constructor, version is zero, and causation
   is the ENTRY fill ID. The caller cannot override position, symbol, mode,
   boundary, policy, or cursor identity.
10. Reject a different active PAPER position; allow the same deterministic
   in-flight graph to reach repository replay resolution.
11. Call only the extended `apply_entry_fill_and_open_position`.
12. Commit only through the UoW and return the committed graph summary.

The atomic repository owns fill insertion, order transition, position open,
cursor creation through the existing cursor repository, event/journal
persistence, locking, CAS, and active-position normalization. All writes are
inside the existing ENTRY `PaperUnitOfWork`; cursor creation has no secondary
commit, post-commit repair, or worker ownership.

The initial boundary is deliberately the ENTRY fill candle close boundary, not
the earlier command boundary. All earlier candles are therefore causally
covered and the first unevaluated exit candle opens exactly at the cursor
boundary.

## Close sequence

1. Validate the immutable close request.
2. Open one UoW and load command, close order, position, and the exit decision
   from the existing bounded command graph.
3. Validate close role, OPEN/CLOSING states, exact order/position versions,
   decision ownership/version, symbol/side, and full remaining quantity.
4. Run the simulator once with `PaperFillRole.CLOSE`; LONG maps to SELL and
   SHORT maps to BUY through `resolve_trade_action`.
5. Return non-success simulation outcomes without mutation or commit.
6. Build transition events through existing state machines and call only
   `apply_close_fill_and_close_position`.
7. Commit through the UoW. The repository/domain own close accounting, fees,
   realized PnL, unrealized reset, versions, and atomic audit persistence.

The service never creates or evaluates an exit decision.

## Replay, concurrency, and recovery

For a terminal order, the service reconstructs only the immutable pre-fill
order input needed to rerun the deterministic simulator, then compares the
resulting fill semantic tuple and complete initial ENTRY graph with the current
bounded repository graph. Replay is exact only while that graph still denotes
the initial OPEN position and unadvanced cursor. Later lifecycle progression is
not rewritten or mistaken for an initial ENTRY replay.

Exact replay requires the complete fill, FILLED order, OPEN position, initial
cursor, canonical order event, and two journal rows. It performs no insert or
version increment. A missing cursor or audit fragment is
`EXISTING_ENTRY_GRAPH_INCONSISTENT` and is never repaired; conflicting cursor
material is an idempotency conflict.

Concurrent attempts converge at the existing order lock and deterministic
fill/cursor identities. One transaction creates the complete graph; another
returns the same idempotent graph. The position row and its not-yet-visible
cursor are created in the same transaction, so exit evaluation cannot observe
an OPEN position before its cursor. No service path blindly retries a mutation.

If UoW commit becomes uncertain, the service calls
`recover_uncertain_commit` with:

```text
attempts = 3
session source = injected fresh-session factory
lookup = bounded command graph
comparison = order equality + fill semantic tuple + position equality
             + cursor equality + canonical order event + journal equality
mutation replay = forbidden
```

Matching, absent, conflicting, partial, and unavailable lookup states remain
distinct. Partial cursor/audit graphs never resolve as committed and never
trigger a blind mutation replay.

## Bounds and dependency direction

```text
MAX_CANDIDATE_CANDLES = 64
COMMAND_GRAPH_LIMIT = 100
ACTIVE_POSITION_LIMIT = existing repository limit 1
UNBOUNDED_INPUT_COLLECTIONS = 0
SERVICE_DATABASE_CANDLE_QUERY = NO
SERVICE_MARKET_DATA_NETWORK_CALL = NO
SERVICE_WALL_CLOCK_READS = 0
SERVICE_RANDOM_ID_GENERATION = 0
SERVICE_GLOBAL_MUTABLE_STATE = 0
```

Dependency direction remains:

```text
order execution application service
-> immutable domain and deterministic simulator
-> repository / Unit of Work
-> persistence
```

There is no reverse dependency from domain, simulator, or repository to the
service.

## Non-goals

This module does not create a worker, daemon, scheduler, queue consumer,
command, strategy order, exit decision, candle fetch/query, stop/target
evaluation, API route, client change, Docker image, deployment, production
migration, PAPER runtime, LIVE runtime, or Binance order call.
