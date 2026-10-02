# Dynamic RR terminal gate to diagnostic — final audit

## Decision

```text
FINAL_STATUS = PASS_PAPER_ONLY_WITH_DISCLOSED_BASELINE_DEBT
FINAL_VERDICT = REQUIRED_DYNAMIC_RR_RETAINED_AS_OBSERVABLE_DIAGNOSTIC_ONLY; BASE_RR_AND_OTHER_GATES_UNCHANGED
STARTING_HEAD = b6b3c3322595084378fe33d90542778ba6a08c3c
IMPLEMENTATION_COMMIT = efb7d904c272758f02f725040b1937fac464607e
LIVE = false
REAL_BINANCE_ORDER_CALLS = 0
DB_SCHEMA_CHANGED = NO
PRODUCTION_HISTORY_MUTATED = NO
```

## Semantic boundary

Before this change, `net_rr < required_dynamic_rr` made the expectancy result
non-admitted and `scalping_shadow` returned a terminal
`DYNAMIC_NET_RR_CONSERVATIVE_EV_REJECT`. It could also select a farther causal
target solely to satisfy the dynamic threshold.

After this change, the required dynamic RR formula and value remain calculated,
stored and exposed. `dynamic_rr_pass` is explicitly observable, and the reason
`DYNAMIC_NET_RR_CONSERVATIVE_EV_REJECT` is retained as a diagnostic reason. It
does not make RR terminal for `trade-5m-v2` PAPER. The first actionable causal
target is retained; a farther target is no longer selected solely for dynamic RR.
Candidates that pass geometry, target, net cost and base RR continue through
Risk, Portfolio, Final Approval and PAPER-plan evaluation.

The configured base gate remains terminal and unchanged:

```text
minimum_planned_rr = 0.476674
```

Target, geometry, cost, risk, portfolio, final approval, selector, TTL, exit,
Net PnL Protection, trade-15m and universe behavior were not changed.

## Changed files/functions

* `app/engine_paper/scalping_policy_v2.py::ExpectancyDecision` and
  `evaluate_expectancy`: add `dynamic_rr_pass`; remove dynamic RR/reserve from
  terminal admission while preserving all empirical calculations and positive
  EV qualification.
* `app/engine_paper/scalping_shadow.py::ShadowGeometryDiagnostic` and
  `evaluate_scalping_shadow`: propagate `dynamic_rr_pass`, stop treating the
  dynamic threshold as terminal, and remove dynamic-only farther-target
  selection.
* `app/server_api/trading_funnel.py`: expose `dynamic_rr_pass` in downstream
  detail/telemetry.
* Regression tests were updated only where their expected dynamic-terminal
  behavior changed; the targeted suite now covers dynamic below threshold,
  base RR failure, dynamic above threshold, negative/positive EV, bootstrap,
  other gates and target selection.

## Invariants verified

```text
trade_profile = trade-5m-v2
parameter_set = scalping-v2-set-2
target_min_bps = 40
stop_max_bps = 36
min_net_edge_bps = 5
probability_confidence = 0.85
empirical_sample_requirement = 20
priors = 1/1
static_rr_fallback = false
```

Negative empirical EV remains diagnostic only. Exploration v1/v2 and empirical
requalification remain inactive. No migration or history mutation occurred.

## Test evidence

Targeted scalping/funnel/PAPER regression suite: **78 passed**.

The targeted safety/readonly/operator subset produced **1,931 passed, 2 skipped,
11 pre-existing failures, 3 environment errors**. The failures are existing
route inventory, migration predecessor, readonly-source-contract and operator
fixture debt; the three errors require the separately provisioned
`PAPER_BACKEND_TEST_PG_URL`. No failure is caused by the dynamic-RR patch.

The previously recorded project active-production gate remains the baseline
reference (**28,350 passed, 26 skipped, 20 failed, 1 error**) with disclosed
repository contract debt; this patch does not alter those unrelated contracts.

## Deployment/runtime

Affected PAPER services were rebuilt and recreated using the full immutable
implementation SHA `efb7d904c272758f02f725040b1937fac464607e`:

```text
orchestrator RestartCount = 0
readonly = healthy
operator = healthy
```

Read-only runtime verification returned health `OK`, `operational=true`,
`ready=true`; readiness is `PAPER`, `READY`, `live_allowed=false`. A bounded
Funnel smoke returned `freshness=CURRENT`, current and last-completed cycles
present, `symbols_processed=20`, `cycle_complete=true`. Production database
remains `75 commands / 73 positions / 0 open / 73 closed`, Alembic
`0036_empirical_requalification_authority`. The current observed cycle had
`RR_PASS=0`; no candidate was forced and no claim is made that a natural
below-dynamic candidate appeared during the bounded smoke.

```text
PAPER_EXPLORATION_ACTIVE = NO
EMPIRICAL_REQUALIFICATION_ACTIVE = NO
LIVE = false
REAL_BINANCE_ORDER_CALLS = 0
```

## Next stage

```text
CURRENT_BLOCKER = DOWNSTREAM_OR_DYNAMIC_RR_MATERIALITY_NOT_YET_ESTABLISHED; BASELINE_TEST_DEBT_DISCLOSED
NEXT_ACTION = PASSIVELY_OBSERVE_NATURAL_PAPER_FUNNEL_AFTER_DYNAMIC_RR_IS_DIAGNOSTIC_ONLY
```
