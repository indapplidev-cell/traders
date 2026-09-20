# TRADERS_SCALPING_NET_PNL_PROTECTION_01 — final evidence

```text
FINAL_STATUS = PASS
FINAL_VERDICT = PASS_IMPLEMENTED_TESTED_BUILT_DEPLOYED_AND_RUNTIME_VERIFIED

IMPLEMENTATION_COMMIT = 90ef24192255d817b484ad475292017f64e34f43
ACTIVE_PROFILE = trade-5m-v2
MODE = PAPER
LIVE = DISABLED
REAL_BINANCE_ORDER_CALLS = 0

NET_PNL_PROTECTION_IMPLEMENTED = PASS
ACTIVE_WINDOW = holding_seconds > 600 AND holding_seconds < 1200
USES_CLOSED_1M_ONLY = PASS
USES_MODELED_EXECUTABLE_NET_PNL = PASS
USES_BINANCE_ACCOUNT_FEES = PASS; 10_OF_10_RUNTIME_SYMBOLS_READY
USES_DECIMAL_QUANTIZATION = PASS; NUMERIC_38_18; QUANTUM_0.000000000000000001
STRICTLY_POSITIVE_REQUIRED = PASS
ZERO_DOES_NOT_TRIGGER = PASS
NEGATIVE_DOES_NOT_TRIGGER = PASS

TRIGGER_IS_AUTHORITATIVE = PASS
TRIGGER_IS_IRREVERSIBLE = PASS; OPEN_TO_CLOSING_CANONICAL_EXIT_GRAPH
CANONICAL_1M_EXIT_FILL_USED = PASS
STOP_PRIORITY_PRESERVED = PASS
TARGET_PRIORITY_PRESERVED = PASS
CAUSAL_EXIT_PRIORITY_PRESERVED = PASS
HARD_TIMEOUT_1200_FORCE_EXIT = PASS
NO_POSITION_SURVIVES_HARD_TIMEOUT = PASS_BY_DETERMINISTIC_TEST_AND_EXISTING_DEFENSE_IN_DEPTH

EMPIRICAL_INGESTION_REGRESSION = PASS
BOOTSTRAP_REGRESSION = PASS
FIFTEEN_MINUTE_REGRESSION = PASS
NO_NEW_1M_STRATEGY = PASS
NO_LOOKAHEAD = PASS
NO_PARAMETER_TUNING = PASS
YAML_CHANGED = NO

ALEMBIC = PASS; SINGLE_HEAD_0033_net_pnl_protection; ISOLATED_FULL_UPGRADE_PASS; PRODUCTION_CURRENT_0033
BUILD = PASS
DEPLOY = PASS; OPERATOR_CONTROL_AND_READONLY_REBUILT_AND_RECREATED
RUNTIME_REVISION_MATCH = PASS; BOTH_90ef24192255d817b484ad475292017f64e34f43
READONLY_HEALTH = PASS; OK_CURRENT_OPERATIONAL_READY
PAPER_READINESS = PASS; READY_CONTINUOUS_ARMED_SCHEMA_READY_MUTATION_READY
NATURAL_MARKET_MONITORING_PERFORMED = NO
WAITED_FOR_TRADE_OR_CLOSE = NO
```

## Authoritative computation and trigger

`app/engine_paper/scalping_hold_lifecycle.py::modeled_executable_net_exit_pnl`
calculates the decision-boundary value using `Decimal` under precision 80. The
persisted average entry price already includes entry slippage and the persisted
entry fee is deducted. Current authoritative exit commission, spread, exit
slippage, depth impact and adverse-fill/safety reserve are also deducted. A
missing/non-authoritative Binance account commission snapshot, stale/non-causal
book, or missing depth returns `NET_PNL_UNAVAILABLE` and grants no protection
trigger authority.

The value is quantized with `ROUND_HALF_EVEN` to the existing PostgreSQL
`NUMERIC(38,18)` money quantum. Only
`quantized_net_exit_pnl > Decimal("0")` triggers; raw sub-quantum positivity is
proved not to trigger.

`app/engine_paper/scalping_hold_lifecycle.py::evaluate_hold_lifecycle` owns the
decision. Its deterministic order is:

1. absolute hard timeout at 1200 seconds;
2. canonical reversal/structure and setup/momentum invalidation;
3. already-expired `STALE_SCALP` lifecycle;
4. `NET_PNL_PROTECTION` only inside 601..1199 seconds;
5. otherwise the pre-existing bounded extension lifecycle.

STOP/TARGET priority is enforced afterward by the canonical
`evaluate_paper_exit_window`: a causally touched STOP or TARGET on an earlier or
the same closed candle wins over the safety directive, with STOP_FIRST for an
intrabar conflict. The typed `NET_PNL_PROTECTION` cause and
`PAPER_EXIT_NET_PNL_PROTECTION_TRIGGERED` reason are persisted without masking
them as target, stale, or max-hold exits.

## Idempotency, fill and no-lookahead proof

The persisted hold key is `(position_id, evaluation_closed_until_ms)`. The
directive id is deterministic from canary, boundary and reason. Existing exit
decision/order/fill idempotency then creates one OPEN→CLOSING decision graph,
one close order, one next-eligible-closed-1m fill and one accounting result.
Once CLOSING exists the worker follows only the close path; a later negative
candle cannot cancel or reopen it. `mark_exit_filled` annotates evidence only
after the canonical CLOSED position exists and never changes position state.

Candidate candles are validated closed 1m inputs and bounded by the persisted
cursor. Evidence includes `future_bars_used=false`; neither in-progress candles,
future high/low nor retrospective extrema participate in the decision.

## Test evidence

- focused hold/net/exit matrix: `304 passed` from the clean implementation
  worktree;
- expanded focused regression: `383 passed`; one unrelated legacy test still
  expects removed `trade-5m-v1` runtime authority and is excluded from this
  task's PASS;
- PostgreSQL exit service: `22 passed`;
- PostgreSQL typed NET_PNL protection graph: `1 passed`;
- compileall: PASS;
- bootstrap/empirical tests cover insufficient-sample bootstrap, sufficient
  negative-EV no-fallback, closed-outcome statistics and outcome ingestion;
- explicit 15m domain/runtime-disabled/identity tests pass; no 15m source or
  configuration file changed.

The historical persistence suite's downgrade harness cannot run from an empty
database because legacy revision `0019` has no downgrade function. Independent
fresh PostgreSQL `upgrade head` ran every revision through `0033` successfully.
`alembic check` continues to report pre-existing metadata/index drift unrelated
to this change; it reports no missing `0033` columns or constraints.

## Deployment evidence

```text
PRODUCTION_ALEMBIC = 0033_net_pnl_protection
OPERATOR_IMAGE = sha256:833ae4f729644734643132a357427a23d86cf2478dac203564ceb50cbce9dc9c
READONLY_IMAGE = sha256:b7c4f909b30e43dfd1b8a4f54fb64f331e836450f4e5c0747a31fedeb26dbec3
OPERATOR_REVISION = 90ef24192255d817b484ad475292017f64e34f43
READONLY_REVISION = 90ef24192255d817b484ad475292017f64e34f43
OPERATOR_HEALTH = HEALTHY; RESTARTS_0
READONLY_HEALTH = HEALTHY; RESTARTS_0
READONLY_API = OK; CURRENT; OPERATIONAL; READY
PAPER_READINESS = READY; PAPER; CONTINUOUS_ARMED; SCHEMA_READY; MUTATION_READY
LIVE_ALLOWED = false
BINANCE_ACCOUNT_COMMISSION_SNAPSHOT = 10_OF_10_READY
READONLY_NET_PNL_FIELDS = PRESENT_IN_AVAILABLE_HOLD_REVALIDATION_PROJECTION
```

No natural candidate, OPEN, 600-second timeout, positive PnL, or close was
awaited. Runtime acceptance used deterministic tests, schema inspection,
container revision/health, one read-only funnel projection and one readiness
snapshot only.
