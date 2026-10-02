# Negative empirical EV hard-veto removal — final audit

## Decision

```text
FINAL_STATUS = PASS_PAPER_ONLY_WITH_DISCLOSED_BASELINE_DEBT
IMPLEMENTATION_COMMIT = fbe71e7
DEPLOYED_SOURCE_LABEL = fbe71e7
LIVE_ALLOWED = false
REAL_BINANCE_ORDER_CALLS = 0
DATABASE_MIGRATION = none
DATABASE_HISTORY_MUTATION = none
```

The independent terminal negative empirical-EV veto has been removed. Empirical
EV, payoff statistics, sample authority, dynamic RR and diagnostic fields remain
observable. A sufficiently sampled negative-EV candidate now continues when its
net RR meets the existing dynamic requirement; it is not terminally rejected by
`SCALPING_EMPIRICAL_EXPECTANCY_REJECTED`.

## Semantics and implementation

| Case | Result after this task |
|---|---|
| Negative empirical EV, sample authority established, net RR >= dynamic required RR | admitted; diagnostic reason `EMPIRICAL_SUFFICIENT_NEGATIVE_EV`; no empirical terminal rejection |
| Negative empirical EV, net RR < dynamic required RR | rejected by `DYNAMIC_NET_RR_CONSERVATIVE_EV_REJECT` |
| Positive empirical EV with sufficient sample | unchanged positive-EV admission and thresholds |
| Insufficient sample | unchanged bootstrap/static-RR fallback |
| Target, cost, base-RR, geometry and downstream blockers | unchanged |

Changed code:

* `app/engine_paper/scalping_policy_v2.py::evaluate_expectancy` keeps the
  empirical calculation and positive-EV thresholds, but makes the independent
  negative-EV result diagnostic rather than an admission veto when dynamic RR
  passes.
* `app/engine_paper/scalping_shadow.py` reports
  `NEGATIVE_DIAGNOSTIC`; only dynamic RR failure becomes a dynamic terminal
  reason, while incomplete/other expectancy failures preserve their prior
  generic behavior.
* `app/server_api/trading_funnel.py` no longer classifies the negative diagnostic
  reason as an expectancy rejection.

Exploration and requalification lanes remain inactive. No migration, seed,
position, command, or history mutation was performed.

## Regression evidence

Task-owned regression suite: **77 passed**. It covers the ENA-like authority
(20 observations, 7 wins, 13 losses, negative EV about `-18.0819` bps, net RR
`2.80469675`, dynamic required RR about `2.7594`), dynamic-RR rejection below
the threshold, positive-EV parity, insufficient-sample parity, and target/cost/
base-RR blockers. The funnel and exploration/requalification assertions also
remain green.

Safety suite: **641 passed, 1 skipped, 1 pre-existing baseline failure**
(migration-head expectation `0014` versus current `0015`).

The official active no-DB gate completed with **28,350 passed, 26 skipped,
20 failed, 1 error**. Failures are pre-existing repository baseline debt
(runtime-config epoch, strict enum/readiness/OpenAPI and route-count drift,
missing evidence inbox fixtures, security/environment contracts, service
resource and stale timing expectations); no task-owned test failed. An isolated
Postgres-16 natural-execution run produced **17 passed, 4 baseline fixture
failures** (`CYCLE_CANDIDATE_SET_INCOMPLETE` / no second eligible approval),
consistent with the previously disclosed fixture debt.

## Deployment and runtime evidence

Affected PAPER read-only services were rebuilt and recreated from
`fbe71e7`: `online-orchestrator-5m`, `readonly-api`, and
`operator-control-api`. Readonly and operator containers are healthy and all
three image revision labels resolve to `fbe71e7`; readonly health returned
`status=OK`, `operational=true`, `ready=true`.

The production database remains at Alembic
`0036_empirical_requalification_authority`, with unchanged counts
`paper_execution_commands=75`, `paper_positions=73`, `OPEN=0`, `CLOSED=73`.
The read-only PAPER readiness response reports `mode=PAPER`, `status=READY`,
`live_allowed=false`; mutation/runtime domains remain blocked as designed.
Commission readiness is not evaluated while the PAPER runtime is disabled.

A bounded read-only funnel smoke for `trade-5m-v2` completed successfully:
20/20 symbols were processed and the cycle was complete. The current snapshot
had `STRUCTURAL_SETUP=2`, `STRATEGY_ELIGIBLE=1`, `RR_PASS=0`; this is an
observation, not a replay or forced trade, and does not prove that dynamic RR
is yet the next material bottleneck.

## Safety and next stage

```text
EXPLORATION_ENABLED = false
REQUALIFICATION_ENABLED = false
PAPER_MUTATIONS_PERFORMED = false
LIVE_ENABLED = false
CURRENT_STAGE = PASSIVE_NATURAL_FUNNEL_OBSERVATION_AFTER_NEGATIVE_EV_VETO_REMOVAL
NEXT_ACTION = PASSIVELY_OBSERVE_NATURAL_FUNNEL_AND_MEASURE_WHETHER_DYNAMIC_RR_BECOMES_THE_NEXT_MATERIAL_BOTTLENECK
```

The remaining broad-suite and natural-execution fixture failures are disclosed
baseline debt, not grounds to weaken another gate or to enable LIVE.
