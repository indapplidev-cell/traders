# PAPER exit-evaluation application service

`PaperExitEvaluationService` evaluates exactly one caller-supplied PAPER
position and one bounded tuple of closed 1m candles. It is not a worker,
scheduler, market-data reader, API, deployment, or PAPER runtime.

## Authority and transaction boundary

The service loads the exact position, persisted evaluation cursor, source
command, filled ENTRY order, ENTRY fill, and active simulation policy inside
one `PaperUnitOfWork`. The caller supplies expected position/cursor versions
and IDs, but cannot supply or override symbol, side, quantity, stop, target, or
the evaluation start. Those values come only from the persisted causal graph.

`execution_mode=PAPER` and `explicit_paper_authorization=true` are mandatory.
OFF, LIVE, unknown mode, and missing authorization return before a Unit of
Work is opened.

## Pure evaluator

`evaluate_paper_exit_window` has no database, repository, network, wall-clock,
random, or mutable-global dependency. Its maximum input is 64
`PaperFillCandle` values. The tuple must:

- start exactly at `cursor.last_evaluated_closed_until_ms`;
- be canonical chronological, duplicate-free, and contiguous;
- contain closed 1m candles for the authoritative symbol;
- end no later than the explicit market snapshot.

LONG stop uses `low <= stop`; LONG target uses `high >= target`. SHORT stop
uses `high >= stop`; SHORT target uses `low <= target`. The earliest candle
wins, equality triggers, and a same-candle stop/target conflict resolves to
`STOP_LOSS` under `STOP_FIRST_CONSERVATIVE`.

An immutable `PaperSafetyExitDirective` is PAPER-only and final-authorized.
It wins at the same boundary as a market trigger, loses to an earlier market
trigger, and cannot advance evaluation past unprocessed history.

## No-trigger flow

The no-trigger transaction delegates to the existing row-locked cursor
primitive:

```text
validate exact graph and bounded window
lock cursor
advance from expected boundary to final evaluated boundary
increment cursor version once
commit
```

The position remains OPEN and its version is unchanged. No exit decision,
CLOSE order, business event, or journal row is created. Exact replay returns
`CURSOR_ALREADY_ADVANCED` without a second cursor increment.

## Trigger flow

The trigger transaction delegates to the existing atomic compatibility
primitive:

```text
lock cursor
lock OPEN position
finalize cursor at the earliest trigger boundary
create PaperExitDecision
transition position OPEN -> CLOSING
create CLOSE MARKET_SIMULATED order
transition order CREATED -> VALIDATED -> OPEN
persist the exit event, three order events, and four journal rows
commit
```

`PaperExitDecision.source_closed_until_ms` equals the trigger candle close
boundary. The cursor never advances beyond it. The result includes a valid
`PaperCloseExecutionRequest` with no candidate fill candle; the execution
service is not invoked. Therefore this service creates no CLOSE fill, performs
no `CLOSING -> CLOSED` transition, and calculates no realized PnL.

The CLOSE fill causal resolver remains authoritative:

```text
source entity = PAPER_EXIT_DECISION
source boundary = PaperExitDecision.source_closed_until_ms
fill identity = CLOSE v2
command-boundary fallback = forbidden
```

## Replay and commit uncertainty

Exact trigger replay requires the complete cursor, decision, CLOSING position,
OPEN CLOSE order, three canonical order events, and four journal rows.
Conflicting semantic graphs return `IDEMPOTENCY_CONFLICT`; partial graphs
return `EXISTING_EXIT_GRAPH_INCONSISTENT` and are never repaired.

Uncertain commits use at most three fresh sessions and never replay a
mutation. No-trigger recovery proves the expected cursor plus the absence of
an exit graph. Trigger recovery proves the complete trigger graph, including
events and journal. Committed, absent, partial/conflicting, and unavailable
states remain distinct.
