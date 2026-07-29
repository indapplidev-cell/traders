# PAPER close causal boundary and exit-evaluation cursor

This note records the prerequisite contracts supplied by
`TRADERS_ML_PAPER_CLOSE_ORDER_CAUSAL_CONTRACT_REMEDIATION_01`. It does not
implement an exit evaluator, stop/target application service, worker,
scheduler, runtime, API, deployment, or PAPER/LIVE enablement.

## Fill causal authority

`PaperFillCausalBoundary` is the immutable
`PAPER_FILL_CAUSAL_BOUNDARY_V1` input to the deterministic fill simulator.
The pure `resolve_paper_fill_causal_boundary` authority validates the complete
available graph before constructing it. The resolver performs no database,
network, wall-clock, or random access.

| Fill role | Source entity | Authoritative source boundary |
|---|---|---|
| ENTRY | `PAPER_EXECUTION_COMMAND` | `PaperExecutionCommand.closed_until_ms` |
| CLOSE | `PAPER_EXIT_DECISION` | `PaperExitDecision.source_closed_until_ms` |

Both boundaries use the existing exclusive convention. With one exact 1m
latency candle, the expected candle open is the source `closed_until_ms`, and
its close boundary is `close_boundary_ms(source_closed_until_ms, "1m")`.
Previous-candle and later-candle fallback remain forbidden.

The simulator no longer chooses command versus exit-decision authority. It
accepts only an explicit role-matched causal boundary. ENTRY retains the exact
v1 fill identity tuple and unchanged price, slippage, fee, and boundary
behavior. CLOSE uses fill identity v2:

```text
PAPER_FILL_CAUSAL_BOUNDARY_V1
close order ID
CLOSE
exit decision ID
exit decision source_closed_until_ms
selected candle open
selected candle close boundary
simulation policy ID
slippage policy ID
fee policy ID
latency policy ID
```

Thus identical CLOSE causal graphs replay to the same ID, while a different
exit decision or exit boundary cannot collide with the old command-derived
meaning. Existing ENTRY v1 records and replay lookups remain compatible.

The close execution service loads the command, close order, position, exit
decision, entry order, and entry fill; resolves the boundary from the exit
decision; and passes that immutable boundary to the simulator. Existing close
PnL, fee accounting, `CLOSING -> CLOSED` behavior, transaction ownership, and
fresh-session uncertain-commit recovery are unchanged.

## Dedicated exit-evaluation cursor

`PaperExitEvaluationCursor` is operational checkpoint state, not position
business state. Revision
`0011_paper_close_causal_boundary_and_exit_evaluation_cursor` adds one
`paper_exit_evaluation_cursors` row per position. The existing
`last_mark_closed_until_ms` field is not reused because it already has
mark/accounting semantics.

The cursor initializes from the authoritative entry fill:

```text
position.entry_fill_id
  -> PaperFill.source_closed_until_ms
  -> position_opened_closed_until_ms
  -> initial last_evaluated_closed_until_ms
```

The entry fill field is the close boundary of the entry-fill candle. Therefore
all earlier candles are causally ineligible and the first unevaluated candle
opens exactly at the initial cursor boundary. Wall clock, latest market candle,
the earlier command boundary, and caller-selected boundaries are not valid
initialization sources.

Each advance carries an immutable bounded tuple of at most 64 contiguous 1m
close boundaries. The repository locks the cursor row, requires the exact
expected version and starting boundary, advances monotonically, and increments
the version exactly once. Exact replay returns the existing checkpoint without
another increment. Stale, regressing, gapped, policy-conflicting, and
idempotency-conflicting attempts fail closed.

For `NO_EXIT_TRIGGER`, the future transaction is:

```text
lock cursor
validate version, start, policy, and contiguous bounded window
advance cursor once
commit
```

The position remains `OPEN`; no exit decision or close order is created. This
is zero business-graph mutation plus one operational checkpoint mutation, not
zero database mutation.

For a trigger, the repository compatibility primitive can atomically:

```text
lock cursor
lock OPEN position
advance cursor to the earliest trigger boundary
create exit decision
transition position OPEN -> CLOSING
create and open the CLOSE order with its canonical events/journal
commit one Unit of Work
```

Cursor advancement is deliberately not represented as a PAPER order event,
position transition event, or exit decision. No new journal vocabulary is
needed. Trigger graph events remain the existing exit and order vocabulary.

Cursor commit uncertainty is resolved with at most three fresh sessions.
Matching state means committed, absence means not committed, conflicting state
means idempotency conflict, and repeated lookup failure remains unresolved.
The failed session is never reused and the mutation is never blindly replayed.

## Remaining work

The separately authorized
`TRADERS_ML_PAPER_TRADING_EXIT_EVALUATION_SERVICE_01_RETRY_01` must still
perform bounded candle acquisition, apply the approved stop/target policy,
select the earliest trigger, and compose the supplied repository primitives.
No autonomous PAPER lifecycle is present in this remediation.
