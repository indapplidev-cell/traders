# Paper trading foundation preparation

Task: `TRADERS_ML_PAPER_TRADING_FOUNDATION_PREPARATION_01`

Status: design contract only. This document does not implement or enable paper
or live trading.

## 1. Executive summary

The current online pipeline is a closed-market-data research pipeline:

```text
engine_market_data
-> engine_analysis
-> engine_setup
-> engine_strategy
-> engine_risk
-> engine_paper
```

`engine_paper` produces an explicitly non-executable `PaperTradePlan`.
`engine_execution` and `engine_position` contain tested, process-local domain
contracts, but neither is integrated into the online orchestrator or backed by
durable paper-order/fill/position tables. `engine_exit`, `engine_journal`, and
`engine_safety` are package skeletons.

The safe future chain is:

```text
committed closed market data
-> valid committed analysis result
-> accepted setup
-> allowed strategy decision
-> risk approval
-> immutable PaperExecutionCommand
-> durable paper order
-> deterministic simulated fill
-> durable paper position
-> closed-candle exit decision
-> deterministic close fill
-> append-only audit journal
```

The future executor must be a separate idempotent worker. The orchestrator may
publish an immutable approved command only after its result is durably
committed; it must not execute or fill an order inline.

Foundation safety is fixed:

```text
EXECUTION_MODES = OFF, PAPER, LIVE
DEFAULT_MODE = OFF
MISSING_MODE = OFF
UNKNOWN_MODE = FAIL_CLOSED
PAPER_REQUIRES_EXPLICIT_ENABLE = YES
LIVE_ENABLED = NO
LIVE_IMPLEMENTED = NO
PAPER_USES_BINANCE_TRADE_CREDENTIALS = NO
PAPER_CALLS_BINANCE_ORDER_API = NO
PAPER_CANNOT_ESCALATE_TO_LIVE = BY_CONSTRUCTION
```

The selected v1 simulation is an all-or-none, market-like fill at the next
eligible closed 1m candle open, with deterministic adverse directional
slippage. There is no random input or wall-clock-dependent price selection.
The selected intrabar exit ambiguity rule is `STOP_FIRST_CONSERVATIVE`.

## 2. Verified inventory

Statuses in this document mean:

- `EXISTS_AND_TESTED`: code and focused tests exist for the stated current
  responsibility only.
- `EXISTS_PARTIALLY`: useful code exists, but the required paper-trading
  responsibility is incomplete or not durably integrated.
- `SKELETON_ONLY`: an importable package marker exists without the required
  domain implementation.
- `PLANNED`: this document proposes the capability.
- `NOT_FOUND`: no current repository symbol or artifact was found.

The inventory used tracked source, tests, Alembic revisions, API contracts,
operations documentation, and the read-only client repository. No large source
body is reproduced here.

| AREA | FILE | SYMBOL | CURRENT_STATUS | CURRENT_RESPONSIBILITY | TEST_COVERAGE | GAP | PROPOSED_FUTURE_OWNER |
|---|---|---|---|---|---|---|---|
| Paper planning | `app/engine_paper/paper_trade_plan.py` | `PaperTradePlan` | EXISTS_AND_TESTED | Immutable-looking research plan with hypothetical float levels and all execution flags fixed false | `tests/test_engine_paper_01_*` | No quantity, run/result/config identity, Decimal-only economics, order, or fill | `engine_trade_plan` or command assembler; do not reinterpret it as an order |
| Paper planning policy | `app/engine_paper/paper_plan_policy.py` | `PaperPlanPolicy` | EXISTS_AND_TESTED | Gates `RiskDecision` into plan/no-plan/wait/reject | paper policy/safety tests | Research pre-approval is not final execution approval | future trade-plan policy |
| Paper plan store | `app/engine_paper/paper_store.py` | `PaperStore` | EXISTS_AND_TESTED | In-memory dedupe by symbol/timeframe/boundary/risk ID | store tests | Process-local, mutable replacement semantics, not a journal | replaced by durable command repository |
| Strategy decision | `app/engine_strategy/strategy_decision.py` | `StrategyDecision` | EXISTS_AND_TESTED | Non-executable research decision; forbids execution values in context | strategy contract tests | No production `APPROVED` status in current enum; no quantity or policy bundle | `engine_strategy` remains owner |
| Risk decision | `app/engine_risk/risk_decision.py` | `RiskDecision` | EXISTS_AND_TESTED | Non-executable `RISK_PRE_APPROVED_RESEARCH`; requires later execution review | risk tests | Current enum has no `RISK_APPROVED/RISK_REJECTED/RISK_DEFERRED`; no sizing | `engine_risk` remains owner; future approval contract required |
| Setup | `app/engine_setup/setup_candidate.py` | `SetupCandidate` | EXISTS_AND_TESTED | Causal non-trade setup candidate | setup tests | Not executable and must never bypass strategy/risk | `engine_setup` |
| Execution intent | `app/engine_execution/models.py` | `ExecutionIntent` | EXISTS_AND_TESTED | Decimal, UTC, frozen local intent for `PAPER/DRY_RUN/LIVE` | `tests/engine_execution/*` | No `OFF`, no pipeline run/result/config IDs, no durable command/order/fill | future `engine_paper_execution` boundary |
| Execution builder | `app/engine_execution/builder.py` | `ExecutionIntentBuilder` | EXISTS_AND_TESTED | Exact approval-pair validation, deterministic in-memory key, hard-disabled LIVE | execution tests | Defaults invalid side to BUY; uses process-local registry and local clock; not suitable as durable admission unchanged | future command assembler with strict no-default validation |
| Approval policy | `app/engine_execution/approval_policy.py` | `evaluate_approval_pair` | EXISTS_AND_TESTED | Accepts exact production or research status pairs and rejects mixed pairs | approval tests | Current upstream emits only the research pair; research approval cannot authorize paper execution by itself | `engine_risk` + command admission |
| Execution gateway | `app/engine_execution/gateway.py` | `PaperExecutionGateway` | EXISTS_AND_TESTED | Local acknowledgement and delegation back to `PaperRunner`; no exchange call | gateway/static safety tests | Does not create orders or fills; uses in-memory acknowledgements | replace with durable paper worker port |
| LIVE gateway | `app/engine_execution/gateway.py` | `DisabledLiveExecutionGateway` | EXISTS_AND_TESTED | Always returns `LIVE_EXECUTION_DISABLED` | execution tests | Must remain unreachable and disabled | `engine_safety` + composition root |
| Position core | `app/engine_position/models.py` | `Position` | EXISTS_AND_TESTED | Frozen Decimal position projection | `tests/engine_position/*` | Process-local; lacks durable version, source fill/order IDs and close average | `engine_position` |
| Position lifecycle | `app/engine_position/lifecycle.py` | `PositionLifecycleService`, `reduce_event` | EXISTS_AND_TESTED | Local event reducer, duplicate event rejection, long/short PnL | lifecycle/idempotency/PnL tests | No DB transaction/lock, durable handoff, exit integration, or journal | `engine_position` |
| Position store | `app/engine_position/store.py` | `InMemoryPositionStore` | EXISTS_AND_TESTED | Thread-safe process-local store | store concurrency tests | No restart recovery or cross-process protection | durable position repository |
| Exit | `app/engine_exit/__init__.py` | package marker | SKELETON_ONLY | Namespace only | NOT_FOUND | No exit decision, candle evaluator, state, or tests | `engine_exit` |
| Journal | `app/engine_journal/__init__.py` | package marker | SKELETON_ONLY | Namespace only | NOT_FOUND | No append-only audit model or persistence | `engine_journal` |
| Safety | `app/engine_safety/__init__.py` | package marker | SKELETON_ONLY | Namespace only | NOT_FOUND | No independent mode/admission gate | `engine_safety` |
| Orchestrator chain | `app/engine_orchestrator/pipeline_runner.py` | `PipelineRunner.run` | EXISTS_AND_TESTED | Runs analysis -> setup -> strategy -> risk -> paper plan | orchestrator unit/integration tests | Does not call execution/position/exit/journal | orchestrator publishes command; worker consumes |
| Orchestrator result | `app/engine_orchestrator/pipeline_result.py` | `SafetyCounters`, `PipelineResult` | EXISTS_AND_TESTED | Fails if any execution-like counter is nonzero | orchestrator safety tests | Flags are safety evidence, not authorization | retain as safety counters |
| Online persistence | `app/engine_orchestrator/orchestrator_models.py` | `OnlinePipelineRun`, `OnlinePipelineResultRow` | EXISTS_AND_TESTED | Durable run/result and JSON projections, one result per run | store/dedupe/API tests | No paper command/order/fill/position tables | upstream FK source only |
| Migration history | `alembic/versions/0007_engine_orchestrator_online_pipeline.py`, `0008_engine_orchestrator_freshness_retry.py` | online run/result schema | EXISTS_AND_TESTED | Current schema through revision 0008 | migration/regression tests | No paper trading schema | future dedicated migration task |
| Read-only API | `app/server_api/routes/v1.py` | nine `GET` routes | EXISTS_AND_TESTED | Bounded read-only analytics API | `tests/server_api/*` | No paper order/fill/position projections | future read-only API task |
| Client provider | `src/traders_client/api_contract/protocol.py` | `TradingDataProvider` | EXISTS_AND_TESTED | Read-only health/dashboard/market/analysis/setup/incident contract | client provider/contract tests | No paper DTO/provider methods | future client task |
| Client pages | `src/traders_client/application/client_state.py` | `PAGES` | EXISTS_AND_TESTED | Six read-only pages | GUI/state tests | No paper dashboard/orders/positions/journal | future client task |
| Client server boundary | `src/traders_client/providers/factory.py`, `server_provider.py` | `create_provider`, `ServerProvider` | EXISTS_AND_TESTED | Explicit Mock or production read-only HTTP provider | no-fallback tests | Paper APIs not present | extend without server-to-Mock fallback |

### Symbol findings

- Current authoritative research statuses are
  `ALLOW_RESEARCH_TRADE_PLAN` and `RISK_PRE_APPROVED_RESEARCH`, not
  `APPROVED` and `RISK_APPROVED`.
- `is_trade_signal`, `is_executable`, `order_approved`,
  `execution_approved`, `position_opened`, and `position_size_approved` are
  fail-closed safety counters and persisted observations. They are not
  authority to execute.
- `PaperTradePlan.paper_only` is true and its execution-related flags are
  fixed false.
- Current paper levels and several upstream scores are binary floats. They must
  be converted through `Decimal(str(value))` and revalidated at a new boundary;
  they must never become persisted economic values directly.
- Current `ExecutionIntent` and `Position` prove useful contract patterns
  (frozen dataclasses, Decimal, UTC, deterministic IDs), but their in-memory
  registries/stores do not provide production idempotency.
- No `client_order_id`, durable paper order, durable fill, paper journal, or
  standalone safety gate was found.

## 3. Existing vs missing capability matrix

| CAPABILITY | STATUS | VERIFIED CURRENT LIMIT | FOUNDATION REQUIREMENT |
|---|---|---|---|
| Closed-candle market data | EXISTS_AND_TESTED | Orchestrator snapshots reject gaps/future bars | Re-check at command admission and fill/exit evaluation |
| Analysis/setup/strategy/risk chain | EXISTS_AND_TESTED | Research-only, non-executable | Preserve exact source identities |
| Paper plan | EXISTS_AND_TESTED | Hypothetical float levels, no size | Do not execute directly |
| Immutable Decimal execution intent | EXISTS_AND_TESTED | Local only; modes omit OFF | New durable command with OFF-first configuration |
| Paper order state | PLANNED | NOT_FOUND | Durable state machine and events |
| Deterministic fill simulator | PLANNED | NOT_FOUND | Closed 1m input and versioned policy |
| Durable position | PLANNED | In-memory position exists | Numeric DB projection with optimistic version |
| Exit evaluation | SKELETON_ONLY | Package marker | Closed-candle conservative evaluator |
| Journal | SKELETON_ONLY | Package marker | Append-only audit projection |
| Global execution safety | SKELETON_ONLY | Distributed static gates exist | Independent mode/admission gate |
| Orchestrator handoff | PLANNED | No execution call today | Atomic immutable command publication |
| Paper read API | PLANNED | Current API remains 9 GET/0 write | Bounded GET-only expansion |
| Paper client | PLANNED | Current client read-only | Read-only DTOs/pages after API |

## 4. Authority chain

### 4.1 Exact chain

```text
OnlinePipelineRun(run_id, symbol, primary_timeframe, closed_until_ms)
  + OnlinePipelineResultRow(run_id, committed result payloads)
  -> AnalysisSnapshot(snapshot_id, closed_until_ms, future_bars_used=false)
  -> SetupCandidate(setup_id, source_analysis_snapshot_id)
  -> StrategyDecision(decision_id, source_setup_id, source_analysis_snapshot_id)
  -> RiskDecision(risk_decision_id, source_strategy_decision_id, source_setup_id,
                  source_analysis_snapshot_id)
  -> future immutable risk-sized trade plan
  -> PaperExecutionCommand
  -> PaperOrder -> PaperFill -> PaperPosition
  -> PaperExitDecision -> close PaperOrder -> close PaperFill
  -> PaperJournalEntry
```

The current code has no single complete upstream object. `PaperTradePlan` is
the closest plan object, but it lacks quantity, `pipeline_run_id`, committed
result identity, symbol constraints, and complete configuration identity, and
stores economic levels as float. Therefore it is not the authoritative
execution input.

### 4.2 Authoritative execution input

`PaperExecutionCommand` is the sole authoritative input to the future paper
worker. It is assembled server-side only after:

1. the `OnlinePipelineRun` is `COMPLETED`;
2. its one `OnlinePipelineResultRow` exists;
3. source symbol/timeframe/boundary and all causal IDs match;
4. strategy decision has an implementation-approved paper status;
5. risk decision has an implementation-approved paper status;
6. a future risk-sizing contract supplies quantity and symbol constraints;
7. health is non-degraded, the source is not stale, and no future bar exists;
8. mode is explicitly `PAPER`.

Missing upstream fields that must be added before command creation:

```text
requested_quantity or immutable notional-to-quantity derivation
committed pipeline_run_id
committed online_pipeline_result identity
complete configuration/bundle fingerprint
symbol price_tick, quantity_step, minimum_notional, quote_quantum
simulation, fee, slippage, and latency policy IDs
command validity/expiry boundary
final paper execution approval distinct from research pre-approval
```

### 4.3 Mandatory invariants

```text
NO_DIRECT_ANALYSIS_TO_EXECUTION = YES
NO_DIRECT_SETUP_TO_EXECUTION = YES
NO_EXECUTION_WITHOUT_STRATEGY_DECISION = YES
NO_EXECUTION_WITHOUT_RISK_APPROVAL = YES
NO_EXECUTION_FROM_DEGRADED_OR_STALE_INPUT = YES
```

No boolean safety counter is an approval. Authority comes from the immutable
typed source graph plus exact status and policy validation.

## 5. Mode and safety model

### 5.1 Mode ownership

| LAYER | OWNERSHIP |
|---|---|
| Configuration | Parse `OFF/PAPER/LIVE`; missing -> `OFF`; unknown -> startup/admission failure. No compatibility alias silently enables PAPER. |
| Execution orchestration boundary | Inject exactly one mode-specific port. `OFF` injects rejecting port, `PAPER` injects only simulator ports, `LIVE` has no constructible transport in foundation. |
| `engine_safety` gate | Revalidate mode, source graph, health, freshness, future-data, policy identities, supported order type, and symbol constraints before any command/order state change. |

### 5.2 Construction isolation

The future composition root must use distinct types:

```text
OffExecutionPort
PaperExecutionPort(PaperMarketDataPort, PaperRepositoryPorts)
DisabledLiveExecutionPort
```

`PaperExecutionPort` has no Binance private client parameter, no credential
parameter, and no exchange order transport dependency. Static import tests
must reject private Binance/order symbols in all paper modules. The LIVE port
is a terminal rejector and no factory may construct a live transport.

PAPER enablement requires both:

```text
TRADERS_EXECUTION_MODE=PAPER
PAPER_WORKER_ENABLED=true
```

Either missing value resolves to disabled. Configuration is recorded as safe
mode/policy IDs, never raw environment values. Switching mode is outside this
task and must not be exposed through an API control route.

## 6. Domain contracts

### 6.1 Proposed immutable `PaperExecutionCommand`

All monetary values are finite `Decimal`, serialized losslessly as canonical
decimal strings. All timestamps are timezone-aware UTC. IDs are bounded ASCII
strings. No secret or mutable runtime object is allowed.

| FIELD | CLASS | RULE |
|---|---|---|
| `command_id` | derived, never user-supplied | Deterministic UUID/hash from versioned canonical identity |
| `idempotency_key` | derived, never user-supplied | Stable across retries; see section 12 |
| `mode` | mandatory, configuration-owned | Exactly `PAPER`; `OFF/LIVE/unknown` reject |
| `symbol` | mandatory | Uppercase validated symbol |
| `side` | mandatory | `BUY` for LONG entry, `SELL` for SHORT entry; no default |
| `order_type` | mandatory policy value | Foundation only `MARKET_LIKE_NEXT_CLOSED_1M_OPEN` |
| `requested_quantity` | mandatory, server-derived | Positive, quantized down to `quantity_step` |
| `requested_notional` | derived | `requested_quantity * entry_reference_price`; never an independent authority |
| `entry_reference_price` | mandatory | Positive source-plan reference, Decimal-revalidated |
| `stop_price` | mandatory | Positive and on loss side of entry |
| `target_price` | mandatory | Positive and on favorable side of entry |
| `strategy_decision_id` | mandatory | Exact committed source |
| `risk_decision_id` | mandatory | Exact committed source |
| `setup_id` | mandatory | Exact committed source |
| `pipeline_run_id` | mandatory | FK to completed run |
| `analysis_result_id` | mandatory | Stable committed analysis snapshot/result identity |
| `online_pipeline_result_id` | mandatory | Stable row identity or versioned logical result ID |
| `closed_until_ms` | mandatory | Source causal boundary |
| `source_timeframe` | mandatory | Current primary timeframe, not assumed |
| `created_at` | derived, never user-supplied | DB transaction timestamp |
| `valid_until` | mandatory, policy-derived | Deterministic from source boundary and policy |
| `configuration_id` | mandatory | Full policy/config bundle fingerprint |
| `symbol_constraints_id` | mandatory | Immutable precision/notional snapshot identity |
| `simulation_policy_id` | mandatory | Immutable selected fill policy |
| `fee_policy_id` | mandatory | Immutable fee policy |
| `slippage_policy_id` | mandatory | Immutable slippage policy |
| `latency_policy_id` | mandatory | Immutable latency policy |
| `correlation_id` | derived | Root causal ID; normally command ID |
| `causation_id` | derived | Upstream result/trade-plan identity |

Optional foundation fields are limited to bounded, non-authoritative safe
diagnostics and a nullable `limit_price`, which must be null for the selected
market-like order type. No field may be supplied by the client.

### 6.2 Direction mapping

```text
BULLISH/LONG -> entry side BUY; close side SELL
BEARISH/SHORT -> entry side SELL; close side BUY
NEUTRAL/NONE/unknown -> PAPER_INPUT_INVALID_SIDE
```

### 6.3 Compatibility

Current `ExecutionIntent` can inform naming and serialization, but
`PaperExecutionCommand` is a new strict contract. It must not preserve the
current builder behavior that substitutes BUY when side is missing.

## 7. Order state machine

### 7.1 Foundation subset

Selected states:

```text
CREATED
VALIDATED
OPEN
FILLED
REJECTED
FAILED
```

`QUEUED`, `PARTIALLY_FILLED`, `CANCELLED`, and `EXPIRED` are deferred.
Foundation v1 is all-or-none, has no cancel/replace, and supports one
market-like deterministic order type.

Terminal states are `FILLED`, `REJECTED`, and `FAILED`.

### 7.2 Transitions

| FROM | EVENT | PRECONDITIONS | TO | PERSISTED_EVENT | IDEMPOTENCY_RULE | FAILURE_BEHAVIOR |
|---|---|---|---|---|---|---|
| none | `COMMAND_ACCEPTED` | New command key; mode PAPER | CREATED | `PAPER_ORDER_CREATED` | Unique `command_id` and `idempotency_key` return same order | DB failure creates nothing; retry |
| CREATED | `VALIDATION_PASSED` | Safety/source/policy/precision checks all pass | VALIDATED | `PAPER_ORDER_VALIDATED` | Unique order/event key | Validation conflict rolls back |
| CREATED | `VALIDATION_REJECTED` | Any terminal input/safety rejection | REJECTED | `PAPER_COMMAND_REJECTED` | Same retry returns same rejection | No fill/position |
| VALIDATED | `ORDER_ACTIVATED` | Validity window open; worker owns claim | OPEN | `PAPER_ORDER_OPENED` | Compare expected version | Conflict reloads; no duplicate event |
| OPEN | `ELIGIBLE_CANDLE_CLOSED` | Exact next eligible closed 1m candle, healthy and non-stale | FILLED | `PAPER_ORDER_FILLED` | Unique fill identity and one entry fill/order | Transaction failure rolls back fill and dependent mutation |
| CREATED/VALIDATED/OPEN | `TERMINAL_INTERNAL_FAILURE` | Bounded non-retriable invariant failure | FAILED | `PAPER_EXECUTION_FAILED` | Unique failure event | No fill or position; retain audit |

DB unavailable, lock timeout, serialization conflict, and missing eligible
market data are retriable and do not force a terminal state. They leave the
last committed state unchanged.

### 7.3 Invariants

```text
terminal state cannot reopen
FILLED cannot fill twice
REJECTED cannot become FILLED
same command retry cannot create a second order
same fill event cannot apply twice
one foundation entry order has exactly zero or one fill
one foundation close order has exactly zero or one fill
```

## 8. Fill simulation decision

### 8.1 Selected policy

```text
SELECTED_FOUNDATION_FILL_POLICY =
NEXT_ELIGIBLE_CLOSED_1M_OPEN_DIRECTIONAL_SLIPPAGE_V1

PRICE_SOURCE = candles_1m
ELIGIBLE_CANDLE =
  first healthy closed 1m candle with open_time_ms >= command.created boundary
  and open_time_ms > source decision closed_until_ms
ENTRY_BASE_PRICE = eligible candle open
FUTURE_BARS_USED = false
PARTIAL_FILLS = unsupported
LATENCY = one eligible closed 1m candle, deterministic
RANDOMNESS = none
```

The worker may observe the candle only after its `close_time_ms` is behind the
authoritative closed boundary. The fill economically references that candle's
open, but is not committed until the candle is closed. This sacrifices
real-time realism to eliminate look-ahead and hidden wall-clock races.

### 8.2 Slippage and rounding

Foundation policy:

```text
PAPER_SLIPPAGE_POLICY = PAPER_DIRECTIONAL_SLIPPAGE_V1
SLIPPAGE_BPS = 2
BUY_FILL = base_price * (1 + 0.0002)
SELL_FILL = base_price * (1 - 0.0002)
PRICE_ROUNDING = adverse to price_tick
QUANTITY_ROUNDING = floor to quantity_step
MINIMUM_NOTIONAL = immutable symbol constraint
```

The 2 bps value aligns with the current analytical
`AuditCostAssumptions.slippage_bps_per_side` default, but the simulation policy
must be a separate Decimal implementation and identity. The float-based label
helper is not reusable execution code.

### 8.3 Insufficient, stale, gap, and future data

- No eligible candle: keep OPEN and return retriable
  `PAPER_FILL_NO_ELIGIBLE_CLOSED_CANDLE`.
- Gap in the required exact next 1m candle: do not skip forward; return
  `PAPER_FILL_REQUIRED_CANDLE_GAP`.
- Stale/degraded health: do not fill; return a retriable safety block.
- Any candle beyond the allowed closed boundary: reject the evaluation with
  `PAPER_SAFETY_FUTURE_DATA_DETECTED`.
- Missing constraints or rounding to zero/minimum-notional failure: terminal
  rejection before OPEN.

### 8.4 Alternatives

| ALTERNATIVE | DECISION | REASON |
|---|---|---|
| Same source candle close | Rejected | Reuses a price already known to the decision and understates execution latency |
| Next candle close | Rejected | Adds a full-bar price drift and does not model a market-like entry as directly |
| Mid-price | Deferred | No authoritative bid/ask/mid series exists |
| Random slippage | Rejected | Breaks repeatability and hides an uncontrolled input |

### 8.5 Limitations

This policy does not model order-book depth, spread dynamics, partial fill,
queue priority, intra-candle path, or live latency. Results must be labeled
simulation, not execution-quality evidence.

## 9. Position model

### 9.1 Server-authoritative fields

```text
position_id
mode
symbol
side
status
opened_at
closed_at
entry_quantity
remaining_quantity
average_entry_price
average_exit_price
gross_realized_pnl
realized_pnl
unrealized_pnl
fees_paid
stop_price
target_price
source_order_id
source_fill_id
source_strategy_decision_id
source_risk_decision_id
last_mark_price
last_mark_closed_until_ms
version
created_at
updated_at
```

`realized_pnl` means net realized PnL. The explicit gross column prevents
ambiguous accounting.

### 9.2 States and ownership

Selected states:

```text
OPEN -> CLOSING -> CLOSED
OPEN/CLOSING -> FAILED only for retained irreconcilable state
```

The position is created only when the entry fill is durably accepted, so a
position-level `PENDING_OPEN` state is unnecessary. Order state owns pre-fill
waiting.

Ownership:

```text
engine_paper_execution owns commands, orders, order events, and fills
engine_position owns position state and position mutation
engine_exit owns exit decisions
engine_journal owns append-only audit projection
```

### 9.3 Multiplicity

Foundation rule:

```text
PAPER_POSITION_MULTIPLICITY = ONE_ACTIVE_POSITION_PER_MODE_AND_SYMBOL
ACTIVE = OPEN or CLOSING
SCALE_IN = NO
HEDGING = NO
PYRAMIDING = NO
```

A partial unique index enforces the active scope. A duplicate command for the
same causal decision returns its existing graph; a different decision while
the symbol is active is rejected with `PAPER_POSITION_SYMBOL_ALREADY_ACTIVE`.

### 9.4 Concurrency and invariants

- `remaining_quantity >= 0` and `remaining_quantity <= entry_quantity`.
- `CLOSED` cannot reopen.
- Final realized values are immutable except a separately designed,
  append-only audited correction workflow.
- Every mutation uses `WHERE position_id=? AND version=?`; success increments
  version exactly once.
- One fill ID may affect at most one position mutation.
- All monetary arithmetic is finite Decimal/SQL `numeric`, never float.

## 10. Exit model

Foundation causes:

```text
STOP_LOSS
TAKE_PROFIT
SYSTEM_SAFETY_EXIT
```

Deferred causes:

```text
STRATEGY_EXIT
RISK_EXIT
MANUAL_PAPER_EXIT
EXPIRY
```

Exit evaluation uses exact eligible closed 1m candles after the position's
last evaluated boundary. No current/open candle is read.

```text
PAPER_INTRABAR_AMBIGUITY_POLICY = STOP_FIRST_CONSERVATIVE
```

If both stop and target are crossed in one candle, select STOP_LOSS. There is
no favorable path assumption.

Gap rules:

- LONG stop base price: `min(candle.open, stop_price)`.
- SHORT stop base price: `max(candle.open, stop_price)`.
- Target base price: target price; a favorable gap does not improve it.
- Apply adverse close-side directional slippage and adverse tick rounding.

The exit decision has a deterministic identity from position ID/version,
eligible candle identity, cause, and exit-policy ID. The position changes to
`CLOSING` and a close order is created atomically. A repeated decision returns
the same close order.

## 11. PnL/accounting

For quantity `q`, entry `e`, exit/mark `x`:

```text
LONG gross realized = (x - e) * q
SHORT gross realized = (e - x) * q
entry fee = abs(entry fill price * entry quantity) * entry fee rate
exit fee = abs(exit fill price * exit quantity) * exit fee rate
total fees = entry fee + exit fee
net realized PnL = gross realized PnL - total fees
LONG unrealized = (mark - e) * remaining quantity
SHORT unrealized = (e - mark) * remaining quantity
return percentage = net realized PnL / abs(e * q) * 100
initial risk = abs(e - stop) * q
risk multiple R = net realized PnL / initial risk
```

Zero initial risk makes R unavailable and is rejected at command admission.

Foundation accounting:

```text
QUOTE_ASSET_BASIS = symbol quote asset
FEE_CURRENCY = quote asset
FEE_RATE = 10 bps per fill
FEE_DEDUCTION = at each durable fill
FEE_ROUNDING = ROUND_CEILING to immutable quote_quantum
PRICE_PRECISION = symbol_constraints.price_tick
QUANTITY_PRECISION = symbol_constraints.quantity_step
ZERO_OR_NEGATIVE_PRICE = reject
ZERO_OR_NEGATIVE_QUANTITY = reject
```

The fee policy is versioned and Decimal-based. Current analytical float cost
helpers are evidence for a default rate only, not authoritative accounting.

Scope:

```text
SPOT_LIKE_UNLEVERAGED = SUPPORTED_IN_FOUNDATION
LEVERAGE = OUT_OF_SCOPE
FUNDING = OUT_OF_SCOPE
LIQUIDATION = OUT_OF_SCOPE
BORROWING_COST = OUT_OF_SCOPE
```

SHORT is a synthetic unleveraged paper direction; it does not imply borrowing
or exchange margin.

## 12. Idempotency/concurrency

### 12.1 Identities

```text
command idempotency key =
  hash(contract_version, PAPER, pipeline_run_id, online_pipeline_result_id,
       analysis_result_id, setup_id, strategy_decision_id, risk_decision_id,
       symbol, side, closed_until_ms, configuration_id)

order_id = deterministic(command_id, order_role ENTRY|CLOSE, ordinal 1)
order_event_id = deterministic(order_id, expected_version, event_type, cause_id)
fill_id = deterministic(order_id, eligible_candle_id, fill_policy_id)
position_id = deterministic(entry_fill_id)
exit_decision_id =
  deterministic(position_id, position_version, candle_id, cause, exit_policy_id)
journal event_id = deterministic(aggregate_type, aggregate_id, causation_id, event_type)
```

### 12.2 Unique constraint plan

- command: unique `idempotency_key`; unique source decision identity in PAPER.
- order: unique `(command_id, order_role, ordinal)`.
- order event: unique `event_id`; unique `(order_id, resulting_version)`.
- fill: unique `fill_id`; unique `(order_id, fill_role)` in foundation.
- position: unique `source_fill_id`; partial unique active `(mode, symbol)`.
- exit: unique `exit_decision_id`; unique `(position_id, source_candle_id,
  expected_position_version)`.
- journal: unique `event_id`; unique causation tuple.

### 12.3 Transaction boundaries

1. **Command publication:** lock/read committed upstream source graph; recheck
   all identities; insert command or return existing. If command publication is
   coupled to orchestrator completion, result and command use one DB
   transaction.
2. **Order admission:** claim command with `FOR UPDATE SKIP LOCKED` or a
   compare-and-set lease; insert order and event atomically.
3. **Entry fill/open:** lock order; insert fill; transition order; insert
   position and journal events in one transaction. A unique fill prevents
   replay.
4. **Mark:** optimistic position version update plus audit event in one
   transaction.
5. **Exit decision:** lock/optimistically update position to CLOSING; insert
   exit decision and close order atomically.
6. **Close fill:** lock close order and position; insert fill; close position;
   append journal events in one transaction.

After an uncertain commit, lookup the deterministic identity graph before
retrying. Never generate a new ID or timestamp until lookup proves absence.

An outbox framework is not required in v1 because command rows themselves are
the durable queue. It becomes necessary only if delivery crosses a database
boundary.

## 13. Persistence proposal

No table is created by this task. Proposed SQL monetary type is
`numeric(38, 18)` unless symbol-policy analysis in the migration task proves a
larger scale is required. Timestamps are `timestamptz`; epoch boundaries are
`bigint`.

### 13.1 Selected tables

| TABLE | PURPOSE | PK/FK | UNIQUENESS/INDEXES | IMPORTANT COLUMNS AND RULES |
|---|---|---|---|---|
| `paper_simulation_policies` | Immutable policy bundle | `policy_id` | unique fingerprint/version | fee/slippage/latency/rounding/order/exit policy IDs; bounded typed columns; immutable; no secrets |
| `paper_execution_commands` | Authoritative durable intent/queue | `command_id`; FKs to run/result/policy where feasible | unique idempotency and causal tuple; index `(status, next_attempt_at)` | exact contract fields, status, bounded reason, lease/version; economic values numeric; only worker metadata mutable |
| `paper_orders` | Current order projection | `order_id`; FK command; nullable FK exit decision | unique role/ordinal; index status/created | side/type/quantity/prices/status/version/timestamps; checked foundation enum |
| `paper_order_events` | Immutable order transition history | `event_id`; FK order | unique order/resulting_version; order/time index | from/to/event/cause/version/reason/occurred_at; insert-only |
| `paper_fills` | Immutable entry/close fills | `fill_id`; FK order/policy/source candle identity | unique order/role; candle index | quantity/price/notional/fee/slippage/closed candle identity; insert-only |
| `paper_positions` | Current position projection | `position_id`; FKs entry order/fill/source decisions | unique entry fill; partial active symbol uniqueness; status/update indexes | section 9 fields, numeric checks, optimistic version |
| `paper_exit_decisions` | Immutable exit cause and source candle | `exit_decision_id`; FK position/policy | unique position/version/candle; status index | cause, stop/target observations, ambiguity policy, expected version; insert-only |
| `paper_journal_entries` | Append-only safe audit projection | `event_id`; logical aggregate IDs | unique causation tuple; `(aggregate_type, aggregate_id, occurred_at)` | event type, correlation/causation, upstream IDs, safe reason, before/after version; insert-only |

`paper_position_events` is not selected for foundation because
`paper_journal_entries` stores immutable before/after version evidence while
`paper_positions` remains authoritative current state. Add a dedicated
position event store later only if replay becomes an explicit requirement.

No JSON is sole authoritative state. A bounded `diagnostics_json` may contain
allowlisted non-authoritative scalar diagnostics, capped by schema and byte
size. Retention:

- commands, orders, fills, positions, exits, and journal: retained as financial
  audit records; deletion requires a separate retention policy and audit task;
- worker leases/transient attempt metadata: bounded and updateable;
- policies referenced by any row: never deleted.

### 13.2 Proposed migration sequence

```text
0009a paper_simulation_policies
0009b paper_execution_commands
0009c paper_orders + paper_order_events + paper_fills
0009d paper_positions + active-position constraint
0009e paper_exit_decisions + paper_journal_entries
0009f indexes/checks/FKs and readonly API grants in a separately accepted step
```

The implementation migration task may combine these into one Alembic revision,
but must preserve the dependency order and have upgrade/downgrade tests. It
must not be applied to production as part of implementation.

## 14. Journal model

Selected model:

```text
JOURNAL_MODEL = APPEND_ONLY_AUDIT_PROJECTION
```

Orders, fills, positions, and exit decisions are normalized authoritative
state. The journal is not an authoritative event store and is not used to
rebuild balances. This avoids introducing event-sourcing complexity while
preserving a tamper-evident causal audit.

Foundation events:

```text
PAPER_COMMAND_CREATED
PAPER_COMMAND_REJECTED
PAPER_ORDER_CREATED
PAPER_ORDER_FILLED
PAPER_POSITION_OPENED
PAPER_EXIT_TRIGGERED
PAPER_POSITION_CLOSED
PAPER_EXECUTION_FAILED
PAPER_SAFETY_BLOCKED
```

Every event contains:

```text
event_id, event_type, occurred_at, aggregate_type, aggregate_id,
correlation_id, causation_id, pipeline_run_id, analysis_result_id, setup_id,
strategy_decision_id, risk_decision_id, safe_reason_code,
before_version, after_version
```

Journal rows are inserted in the same transaction as their authoritative
mutation. They contain no exception text contract, secret, environment,
credential, raw payload, or unbounded metadata. Corrections append a new event;
history is never updated or deleted.

## 15. Orchestrator integration

### 15.1 Current fields

| FIELD | CURRENT MEANING | AUTHORITY |
|---|---|---|
| `is_trade_signal` | forbidden safety observation/counter | Not authority |
| `is_executable` | forbidden safety observation/counter | Not authority |
| `order_approved` | forbidden safety observation/counter | Not authority |
| `execution_approved` | forbidden safety observation/counter | Not authority |
| `position_opened` | forbidden safety observation/counter | Not authority |
| `position_size_approved` | forbidden safety observation/counter | Not authority |

The fields default false, are copied from module outputs into
`SafetyCounters`, and any nonzero counter makes the pipeline `ERROR`. They are
placeholders/safety assertions, not future workflow state.

### 15.2 Selected integration

```text
ORCHESTRATOR_INTEGRATION_MODEL =
ORCHESTRATOR_WRITES_IMMUTABLE_APPROVED_COMMAND;
SEPARATE_PAPER_WORKER_CONSUMES_IDEMPOTENTLY
```

Rejected alternative: inline paper execution. It couples analytics completion
to fill latency and DB contention, complicates restart recovery, and risks
rerunning execution when the orchestrator retries a boundary.

The command publisher runs only after `PipelineResultStore.finish()` has a
durable completed result, or is incorporated into the same final transaction.
It never reads an uncommitted result. A worker claims command rows with bounded
leases and resumes from durable state after restart.

Freshness, health, closed-only, and future-bar gates are checked twice:

1. at source pipeline completion/command publication;
2. at order validation and every fill/exit candle evaluation.

Paper outcomes are stored only in paper tables and exposed as `PAPER_*`
statuses. They must not set existing live-like safety counters true or imply
exchange execution. Global mode remains OFF unless explicit PAPER worker
configuration passes both enable gates.

## 16. Future API

No route is added by this task. Initial future API scope is GET-only. All list
routes use stable cursor pagination, default 50, maximum 100, allowlisted
filters, indexed order, bounded statement timeout, and no count/full-table JSON
materialization. DB failure maps to generic safe `503`; malformed filters to
`422`; missing detail to `404`.

Initial authorization boundary is the existing loopback-only deployment and
least-privilege read-only database role. Any non-loopback exposure requires a
separate authentication/authorization design before implementation.

| ROUTE | PURPOSE/FILTERS | SORT/LIMIT | RESPONSE | MISSING/DB ERROR |
|---|---|---|---|---|
| `GET /api/v1/paper/orders` | orders; symbol/status/side/from/to | created desc + ID; 50/100 | cursor page `PaperOrderSummary` | empty page / safe 503 |
| `GET /api/v1/paper/orders/{order_id}` | one order with bounded transition summary | n/a | `PaperOrderDetail` | 404 / safe 503 |
| `GET /api/v1/paper/positions` | positions; symbol/status/side/from/to | updated desc + ID; 50/100 | cursor page `PaperPositionSummary` | empty page / safe 503 |
| `GET /api/v1/paper/positions/{position_id}` | one position and bounded source IDs | n/a | `PaperPositionDetail` | 404 / safe 503 |
| `GET /api/v1/paper/fills` | fills; symbol/order/role/from/to | occurred desc + ID; 50/100 | cursor page `PaperFillSummary` | empty page / safe 503 |
| `GET /api/v1/paper/journal` | safe audit; event/aggregate/symbol/from/to | occurred desc + ID; 50/100 | cursor page `PaperJournalEntry` | empty page / safe 503 |
| `GET /api/v1/paper/summary` | bounded aggregate snapshot from indexed queries | fixed one-row projections | `PaperSummary` | n/a / safe 503 |
| `GET /api/v1/paper/health` | mode/worker/backlog/last success/latest safe reason | n/a | `PaperHealth` | n/a / safe 503 |

Response decimals are strings; timestamps are UTC; unknown enum values remain
forward-compatible but never executable. Diagnostics are bounded and
allowlisted.

```text
FUTURE_WRITE_ROUTES_APPROVED = NO
CURRENT_ROUTE_INVENTORY = 9 GET / 0 write
```

`POST enable/disable`, manual close, and reset-account routes are explicitly
not approved.

## 17. Future client impact

```text
CLIENT_CHANGE_REQUIRED = YES_FOR_FUTURE_READ_ONLY_VISIBILITY
CLIENT_CHANGE_DEFERRED_TO_TASK =
TRADERS_CLIENT_PAPER_READONLY_VIEWS_01
CLIENT_API_DEPENDENCIES =
paper summary, health, orders, positions, fills, journal GET contracts
```

Future additions:

- paper dashboard summary and explicit PAPER/OFF indicator;
- orders and positions pages;
- fills/journal view;
- persistent `LIVE disabled` safety banner.

Client rules:

```text
CLIENT_INITIAL_SCOPE = READ_ONLY
CLIENT_SERVER_SOURCE_OF_TRUTH = YES
CLIENT_DIRECT_BINANCE_ACCESS = NO
CLIENT_AUTHORITATIVE_POSITION_STATE = NO
CLIENT_SILENT_SERVER_TO_MOCK_FALLBACK = NO
```

The current provider protocol, server provider, async loader, state, DTOs,
parsers, navigation, and i18n catalogs all require additive changes. A server
failure must remain visible; it must not switch the active production provider
to Mock. The existing safe handling of an invalid configuration mode does not
authorize fallback after production mode is selected.

## 18. Failure taxonomy

Reason codes are stable uppercase identifiers; messages are non-authoritative,
bounded, sanitized, and may change. Every code is classified terminal or
retriable. Raw exception text is never a public contract.

| FAMILY | EXAMPLES | DEFAULT CLASS |
|---|---|---|
| `PAPER_CONFIG_*` | `MODE_MISSING_OFF`, `MODE_UNKNOWN`, `PAPER_NOT_ENABLED`, `LIVE_DISABLED`, `POLICY_MISSING` | terminal config/safety |
| `PAPER_INPUT_*` | `SYMBOL_INVALID`, `SIDE_INVALID`, `PRICE_INVALID`, `QUANTITY_INVALID`, `STOP_TARGET_INVALID`, `SOURCE_ID_MISMATCH` | terminal |
| `PAPER_SAFETY_*` | `HEALTH_DEGRADED`, `SOURCE_STALE`, `FUTURE_DATA_DETECTED`, `CLOSED_CANDLE_REQUIRED` | retriable except future/contract violation |
| `PAPER_RISK_*` | `APPROVAL_MISSING`, `REJECTED`, `DEFERRED`, `SIZING_MISSING` | terminal or deferred |
| `PAPER_ORDER_*` | `TYPE_UNSUPPORTED`, `INVALID_TRANSITION`, `TERMINAL`, `CONFLICT` | terminal contract or retriable conflict |
| `PAPER_FILL_*` | `NO_ELIGIBLE_CLOSED_CANDLE`, `REQUIRED_CANDLE_GAP`, `DUPLICATE`, `PARTIAL_UNSUPPORTED` | retriable gap/no candle; terminal unsupported |
| `PAPER_POSITION_*` | `SYMBOL_ALREADY_ACTIVE`, `VERSION_CONFLICT`, `ALREADY_CLOSED`, `NEGATIVE_REMAINDER` | terminal admission or retriable conflict |
| `PAPER_EXIT_*` | `NO_TRIGGER`, `DUPLICATE`, `AMBIGUOUS_STOP_SELECTED`, `CAUSE_UNSUPPORTED` | no-action/idempotent/terminal |
| `PAPER_DB_*` | `UNAVAILABLE`, `TIMEOUT`, `SERIALIZATION_CONFLICT`, `CONSTRAINT_VIOLATION` | retriable except invariant constraint |
| `PAPER_IDEMPOTENCY_*` | `COMMAND_REPLAY`, `FILL_REPLAY`, `JOURNAL_REPLAY`, `IDENTITY_COLLISION` | idempotent success; collision terminal |
| `PAPER_INTERNAL_*` | `INVARIANT_BREACH`, `UNEXPECTED` | terminal safe failure, operator review |

### 18.1 Safety acceptance matrix

| CONDITION | EXPECTED_DECISION | REASON_CODE | ORDER_CREATED | POSITION_MUTATED | JOURNAL_EVENT |
|---|---|---|---|---|---|
| mode missing | OFF/no action | `PAPER_CONFIG_MODE_MISSING_OFF` | NO | NO | safety event only if a command attempt exists |
| mode OFF | reject/no action | `PAPER_CONFIG_MODE_OFF` | NO | NO | optional bounded safety event |
| mode PAPER, all gates pass | accept | `PAPER_ORDER_VALIDATED` | YES | only after fill | command/order events |
| mode unknown | reject | `PAPER_CONFIG_MODE_UNKNOWN` | NO | NO | safety event |
| LIVE requested | hard reject | `PAPER_CONFIG_LIVE_DISABLED` | NO | NO | safety event |
| risk rejected | reject | `PAPER_RISK_REJECTED` | NO | NO | command rejected |
| risk deferred | defer | `PAPER_RISK_DEFERRED` | NO | NO | safety/defer event |
| risk approval missing | reject | `PAPER_RISK_APPROVAL_MISSING` | NO | NO | command rejected |
| strategy decision missing | reject | `PAPER_INPUT_STRATEGY_MISSING` | NO | NO | command rejected |
| stale market data | defer | `PAPER_SAFETY_SOURCE_STALE` | NO new order/fill | NO | safety blocked |
| degraded health | defer | `PAPER_SAFETY_HEALTH_DEGRADED` | NO new order/fill | NO | safety blocked |
| future data detected | reject/hard stop item | `PAPER_SAFETY_FUTURE_DATA_DETECTED` | NO | NO | safety blocked |
| invalid symbol | reject | `PAPER_INPUT_SYMBOL_INVALID` | NO | NO | command rejected |
| invalid side | reject; never default | `PAPER_INPUT_SIDE_INVALID` | NO | NO | command rejected |
| invalid price | reject | `PAPER_INPUT_PRICE_INVALID` | NO | NO | command rejected |
| invalid quantity | reject | `PAPER_INPUT_QUANTITY_INVALID` | NO | NO | command rejected |
| duplicate command | return existing graph | `PAPER_IDEMPOTENCY_COMMAND_REPLAY` | NO second order | NO duplicate | deduped replay event/metric |
| duplicate fill | return existing fill | `PAPER_IDEMPOTENCY_FILL_REPLAY` | NO | NO duplicate | deduped replay event/metric |
| position already open | reject new command | `PAPER_POSITION_SYMBOL_ALREADY_ACTIVE` | NO | NO | command rejected |
| invalid stop/target | reject | `PAPER_INPUT_STOP_TARGET_INVALID` | NO | NO | command rejected |
| DB unavailable | retry | `PAPER_DB_UNAVAILABLE` | NO uncommitted claim | NO | none until DB returns |
| transaction conflict | reload/retry bounded | `PAPER_DB_SERIALIZATION_CONFLICT` | NO duplicate | NO duplicate | none or one committed event |
| unsupported order type | reject | `PAPER_ORDER_TYPE_UNSUPPORTED` | NO | NO | command rejected |
| partial fill proposed | reject | `PAPER_FILL_PARTIAL_UNSUPPORTED` | existing order may fail safely | NO partial position | execution failed |

Unknown, missing, and ambiguous input never silently executes.

## 19. Observability

Future low-cardinality metrics:

```text
paper_commands_total{decision}
paper_commands_rejected_total{reason_family}
paper_orders_total{status,role}
paper_fills_total{role}
paper_positions_open
paper_positions_closed_total{cause}
paper_execution_failures_total{reason_family}
paper_duplicate_commands_total
paper_idempotent_replays_total{layer}
paper_realized_pnl
paper_fees_total
paper_processing_latency_seconds{stage}
paper_last_success_timestamp
```

No command/order/fill/position/run ID and no unbounded symbol label is allowed
in metrics. If symbol metrics are later required, the symbol set must be a
small explicit configuration allowlist.

Health projection:

```text
worker_enabled
mode
last_processed_intent_at
oldest_pending_intent_age_seconds
bounded backlog count
DB connectivity
latest safe error reason
last_success_at
source/fill staleness
```

Health never exposes a credential, URI, environment, SQL, raw exception, or
unbounded payload.

## 20. Testing strategy

Coverage is behavioral, not a percentage target.

| LAYER | REQUIRED BEHAVIOR |
|---|---|
| Domain unit | immutable command/order/fill/position/exit/journal construction; invalid values |
| State machine | every allowed and forbidden order/position transition; terminal closure |
| Decimal/accounting | LONG/SHORT gross/net/unrealized/R; fee and adverse rounding; extreme precision |
| Idempotency | command/order/fill/position/exit/journal replay and identity collision |
| Transaction/concurrency | two workers, lock timeout, serialization retry, uncertain commit lookup |
| Persistence | checks, FKs, unique/partial indexes, bounded diagnostics, immutable rows |
| Migration | clean upgrade/downgrade, existing-data compatibility, no production invocation |
| Simulator | exact next closed 1m candle, gap/stale/future rejection, repeatability |
| Orchestrator integration | completed result only, no inline fill, retry yields one command |
| API read-only | bounded query plans, pagination, 404/422/503, Decimal strings, zero write routes |
| Security boundary | OFF default, unknown fail closed, LIVE hard block, no private Binance import/credential |
| Restart/recovery | after command/order/fill/position/exit transaction boundaries |
| Client contract | DTO/parser/provider/pages, read-only, visible server errors, no Mock fallback |
| End-to-end paper | approved lifecycle through immutable journal without production exchange access |

Mandatory scenarios:

```text
approved LONG lifecycle
approved SHORT lifecycle
risk rejection
duplicate command replay
duplicate fill replay
restart after order before fill
restart after fill before position update
stop-loss close
take-profit close
stop and target crossed in same candle -> stop first
stale/degraded market data
future bar rejection
DB transient failure
unknown execution mode
LIVE hard block
zero secret exposure
```

The “after fill before position update” case is simulated as an uncertain
transaction outcome: because fill and position open share one transaction,
recovery observes either neither or both, never a durable orphan fill.

## 21. Implementation sequence

Every task is separately authorized. No task below inherits production
deployment authority.

| TASK ID | GOAL | ALLOWED FILES/MODULES | FORBIDDEN MUTATIONS | INPUTS -> OUTPUTS | TESTS / ACCEPTANCE | DEPENDENCY / ROLLBACK / PRODUCTION IMPACT |
|---|---|---|---|---|---|---|
| 01 `TRADERS_ML_PAPER_TRADING_DOMAIN_AND_STATE_MACHINE_01` | Strict immutable domain contracts and pure reducers | new paper-domain package; focused tests/docs | DB/Alembic/orchestrator/API/client/runtime | this contract -> command/order/fill/position/exit/journal types and reason enums | exhaustive transition/Decimal/serialization/static safety; OFF/LIVE gates | none; revert commit; none |
| 02 `...PERSISTENCE_SCHEMA_01` | SQLAlchemy tables and unapplied migration | paper models, Alembic revision, migration tests | production DB/migration execution | task 01 -> normalized schema | upgrade/downgrade/check/FK/unique tests | 01; downgrade in disposable DB; none |
| 03 `...REPOSITORY_IDEMPOTENCY_01` | Transactional repositories/claims/replay | paper repositories/tests | worker/orchestrator/API/deploy | 01+02 -> durable ports | concurrency/uncertain commit/unique conflict tests | 02; revert code/migration in test env; none |
| 04 `...DETERMINISTIC_FILL_SIMULATOR_01` | Closed-1m deterministic fill and policies | simulator/policy ports/tests | exchange/private API/runtime | 01+03, candle read port -> deterministic fill result | same input same output; gap/stale/future/rounding cases | 03; revert; none |
| 05 `...PAPER_ORDER_EXECUTION_SERVICE_01` | Command-to-order-to-entry-fill service | paper execution service/tests | position exit API/deploy/LIVE | 03+04 -> durable order/fill | state/idempotency/restart/security tests | 04; disable service; none |
| 06 `...POSITION_LIFECYCLE_SERVICE_01` | Atomic fill-to-position and mark lifecycle | `engine_position` integration/repositories/tests | exits/API/client/deploy | 05 -> durable position | long/short/version/active-symbol/restart tests | 05; disable consumer; none |
| 07 `...EXIT_EVALUATION_SERVICE_01` | Stop/target/safety exit and close orders | `engine_exit`, integration tests | manual controls/LIVE/deploy | 06 + closed 1m -> exit decision/close order | stop/target/both/gap/replay tests | 06; disable evaluator; none |
| 08 `...JOURNAL_AUDIT_SERVICE_01` | Transactional append-only audit projection | `engine_journal`, repository hooks/tests | event-sourced rewrite/log secrets | 03-07 -> journal entries | dedupe/immutability/redaction/causality tests | 07; stop projection and reconcile before acceptance; none |
| 09 `...ORCHESTRATOR_INTEGRATION_OFF_DEFAULT_01` | Publish immutable commands behind OFF default | orchestrator publisher/config/safety/tests | inline execution, deployment, LIVE | completed result -> command row | OFF/unknown/stale/retry/one-command integration | 08; flag OFF/revert; none until separately deployed |
| 10 `...READONLY_PAPER_API_01` | Bounded GET-only paper projections | server API routes/schemas/repos/contracts/tests | POST/write/client/deploy | accepted schema -> eight GET routes | bounded SQL/contract/9-current-route regression/write=0 | 09; remove additive routes; none |
| 11 `TRADERS_CLIENT_PAPER_READONLY_VIEWS_01` | Read-only paper UI/provider/DTOs | client provider/models/pages/i18n/tests | server mutation/Binance/controls | task 10 contract -> views | provider/parser/async/GUI/no-fallback tests | 10; revert client commit; none |
| 12 `...CONTROLLED_PAPER_ACCEPTANCE_01` | Non-production disposable acceptance | explicit disposable test stack/evidence | production DB/data, LIVE, Binance orders | 01-11 -> lifecycle evidence | full scenarios, zero secret exposure, exact identities | 11; destroy disposable resources; none |
| 13 `...BOUNDED_PAPER_RUNTIME_OBSERVATION_01` | Observe separately authorized PAPER runtime | observer/evidence only | remediation during observation/LIVE | accepted deployment -> bounded stability evidence | restart/backlog/duplicates/PnL invariants | 12 + separate deployment task; stop worker/return OFF; only if separately authorized |

## 22. Decision register

| DECISION_ID | QUESTION | SELECTED_DECISION | RATIONALE | ALTERNATIVES REJECTED | EVIDENCE/SYMBOLS | REVERSIBILITY | REQUIRED_BEFORE_IMPLEMENTATION |
|---|---|---|---|---|---|---|---|
| D01 | Mode model | OFF/PAPER/LIVE; default/missing OFF; unknown reject | Explicit fail-closed composition | Current PAPER/DRY_RUN/LIVE unchanged | `ExecutionMode`, disabled LIVE tests | medium | YES; task 01 |
| D02 | Authoritative command | New immutable `PaperExecutionCommand` | No current object is complete | Execute `PaperTradePlan` or `ExecutionIntent` directly | both current models and gaps in sections 2/6 | medium | YES; task 01 |
| D03 | Paper/live separation | Distinct typed ports; no private transport in paper graph | Escalation impossible by construction | Shared live transport with mode flag | `DisabledLiveExecutionGateway`, static safety tests | low | YES |
| D04 | Fill price | Next eligible closed 1m candle open | Closed-only, causal, deterministic market-like latency | same close, next close, mid | candle tables/orchestrator closed boundary | policy-version reversible | YES |
| D05 | Slippage | Fixed 2 bps adverse directional | Reproducible and aligns analytical default | random/zero/5 bps | `AuditCostAssumptions` (analytical only) | policy-version reversible | YES |
| D06 | Fee | 10 bps/fill, quote asset, ceiling to quote quantum | Explicit conservative Decimal accounting | zero fee, hidden exchange default | analytical 10 bps default; current position fee fields | policy-version reversible | YES |
| D07 | Latency | One exact eligible closed 1m candle | No hidden wall-clock dependency | immediate source-close fill, random delay | source boundaries/candle tables | policy-version reversible | YES |
| D08 | Partial fills | Unsupported in v1 | Small safe state machine; current position already rejects partial open | partial fill/order book model | `PARTIAL_OPEN_FILL_UNSUPPORTED` | medium | YES |
| D09 | Position multiplicity | One active PAPER position per mode+symbol | Prevents scale/hedge ambiguity | per strategy+symbol; multiple | current deterministic position key; no portfolio owner | schema change | YES |
| D10 | Intrabar ambiguity | STOP_FIRST_CONSERVATIVE | No favorable look-ahead assumption | target-first, unresolved, lower timeframe | closed 1m availability | policy-version reversible | YES |
| D11 | Journal authority | Append-only audit projection | Normalized state is simpler and sufficient | authoritative event store | current projection-style models | high to change | YES |
| D12 | Orchestrator integration | Immutable command + separate worker | Restart/idempotency isolation | inline execution | `PipelineResultStore.finish`, no current execution call | medium | task 09 |
| D13 | API initial scope | Eight future GET routes, zero writes | Observability first; preserves control boundary | enable/disable/manual close/reset | current 9 GET/0 write API | low | task 10 |
| D14 | Client initial scope | Read-only views and safety indicator | Server remains authority | client controls/Binance access | `TradingDataProvider`, six current pages | low | task 11 |

## 23. Open questions

These are not hidden decisions. They do not block task 01 domain/state-machine
implementation, but must be closed before the named dependent task:

| OPEN ID | QUESTION | DEADLINE |
|---|---|---|
| O01 | Exact future risk status vocabulary that distinguishes research pre-approval from final PAPER approval | before task 09 |
| O02 | Owner and schema of risk-sized trade plan and symbol-constraints snapshot | before task 05 |
| O03 | Exact command validity TTL | before task 05 |
| O04 | Source of symbol tick/step/minimum notional/quote quantum without private credentials | before task 04 |
| O05 | PostgreSQL numeric precision confirmed against all supported symbol constraints | before task 02 |
| O06 | Separate paper account/cash/reservation model and initial virtual balance | before controlled acceptance |
| O07 | Authentication model if paper API is ever exposed beyond loopback | before such exposure |

Until closed, the relevant boundary fails closed with a bounded
`PAPER_CONFIG_*` or `PAPER_INPUT_*` code.

## 24. Recommended next task

```text
RECOMMENDED_NEXT_TASK =
TRADERS_ML_PAPER_TRADING_DOMAIN_AND_STATE_MACHINE_01
```

This task should implement only pure immutable contracts, enums, validation,
canonical identities, and state reducers described in sections 5-12. It must
not create a migration, repository, worker, orchestrator hook, API route,
client change, deployment, or production record.

Acceptance:

- OFF/missing/unknown/LIVE behavior is exhaustive and fail closed;
- command input has no permissive side/price/quantity defaults;
- Decimal and UTC serialization is lossless;
- order and position transitions are exhaustive;
- duplicate command/fill/exit/journal identities are deterministic;
- partial fills/cancel/replace are explicitly unsupported;
- paper packages have no private Binance/order transport or credential import;
- all focused and safe regression tests pass;
- no production or client mutation occurs.

## 25. Explicit non-goals

This preparation does not:

- implement or enable paper trading;
- create an order, fill, position, exit, or journal runtime;
- create or apply an Alembic migration;
- change production database schema/data/roles;
- add an execution daemon or paper worker;
- add an API route or client code;
- access Binance private/order APIs or credentials;
- send a test, paper, or live exchange order;
- implement or enable LIVE;
- restart/recreate/build/deploy a service or image;
- trigger the online pipeline;
- approve any future write route;
- claim production acceptance, canary, soak, or trading readiness.

Final distinction:

```text
PAPER_FOUNDATION_PREPARATION = design PASS candidate after validation
PAPER_TRADING_IMPLEMENTED = NO
PAPER_MODE_ENABLED = NO
LIVE_TRADING_IMPLEMENTED_OR_ENABLED = NO
```
