# TRADERS 5m scalping decision-chain report

Task: `TRADERS_5M_SCALPING_STRATEGY_QUALITY_AND_TARGET_ACTIONABILITY_SHADOW_CALIBRATION_01`

## Decision

The source-level calibration work passes. Production deployment was intentionally
withheld because the previously disclosed production DB credential has no proved
rotation/invalidation/rebind closure. No credential value is stored here.

The trading verdict is `5M_READY_FOR_MORE_SHADOW`, not PAPER-ready. The causal
target hierarchy now traverses beyond a non-actionable micro-local level, but the
offline completed sample is one unique opportunity and cannot support parameter
promotion or an expectancy conclusion.

## Fresh homogeneous baseline

Only the current parameter set is used for the fresh funnel and Strategy cohorts.
The older 165-boundary sample is used separately as a historical causal replay;
the two datasets are not merged.

```text
PRODUCTION_ALEMBIC_HEAD = 0018_promote_5m_production_search
5M_PARAMETER_SET_ID = trade-5m-v1-runtime-v1-4e257e4cff2a5b9a
5M_RUNTIME_SOURCE_COMMIT = 8a2413f00dc0ba6ba398faa8d08ac98e1cacf58a
5M_RUNTIME_ARTIFACT_ID = sha256:41f836ed3ecc41b8f5e323b49c39ce06d17059c2b0152a0751100e5e1b9efc9b
5M_SINGLETON_OWNER_COUNT = 1
WAL_READY = true
PITR_READY = true
CONTROL_STATE = ARMED
CONTROL_GENERATION = 6
LIVE_STATE = DISABLED
OBSERVATION_BOUNDARIES = 22
SYMBOL_EVALUATIONS = 220
EXPECTED_SYMBOL_EVALUATIONS = 220
PARAMETER_HOMOGENEOUS = YES
```

| stage | input | pass | reject | principal reason/policy |
|---|---:|---:|---:|---|
| analysis | 220 | 220 | 0 | closed-boundary analysis |
| setup | 220 | 37 | 183 | `NO_SETUP` |
| Strategy current 65 | 37 | 0 | 37 | weak quality 36; conflicting context 1 |
| geometry | 0 | 0 | 0 | not reached by current production admission |
| actionable target | 0 | 0 | 0 | not reached |
| cost | 0 | 0 | 0 | not reached |
| risk | 0 | 0 | 0 | not reached |
| PAPER plan | 0 | 0 | 0 | not reached |
| approval / position | 0 | 0 | 0 | no authority mutation |

The 37 raw setup observations collapse to 11 opportunity episodes; 26 are
adjacent-boundary repeats. Opportunity identity is based on symbol, direction,
setup family and a contiguous episode, while score, stop and target evolution
remain diagnostics rather than identity inputs.

## Strategy quality decomposition

The implementation persists the actual project components: raw values,
normalized values, positive contributions, negative penalties, final score,
threshold, margin, status and reason. Conflict diagnostics include component,
severity, source/timeframe and whether the conflict remained valid at the
decision boundary. No synthetic scoring factor was added.

For `STRATEGY_REJECT_WEAK_QUALITY` (36 observations):

| statistic | score | margin to 65 |
|---|---:|---:|
| P10 | 64.999 | -0.001 |
| P25 | 64.999 | -0.001 |
| P50 | 64.999 | -0.001 |
| P75 | 64.999 | -0.001 |
| P90 | 64.999 | -0.001 |
| P95 | 64.999 | -0.001 |

```text
SCORE_MIN_MAX = 64.666 / 64.999
MARGIN_MIN_MAX = -0.334 / -0.001
[-0.10, 0) = 34
[-0.25, -0.10) = 1
[-0.50, -0.25) = 1
[-1.00, -0.50) = 0
< -1.00 = 0
```

The single conflicting-context rejection is `LOW_CONFIDENCE`. The new trace
records contemporaneous conflict evidence rather than inferring it later. This
proves a dense boundary cluster caused by the existing tier cap, but it does not
prove that the gate is economically too strict.

## Same-dataset Strategy SHADOW cohorts

| threshold | setups | admits | unique | stops | targets | geometry | costs missing | actionable | cost/risk/PAPER |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 65.00 control | 37 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 64.90 shadow | 37 | 34 | 9 | 34 | 20 | 20 | 20 | 0 | 0 |
| 64.75 shadow | 37 | 35 | 9 | 35 | 21 | 21 | 21 | 0 | 0 |
| 64.50 shadow | 37 | 36 | 10 | 36 | 21 | 21 | 21 | 0 | 0 |
| 64.00 diagnostic | 37 | 36 | 10 | 36 | 21 | 21 | 21 | 0 | 0 |

Historical boundary records did not persist authoritative spread/depth costs
for candidates rejected at Strategy. These cohorts therefore fail closed at
economics. Lowering the production threshold is not justified. If further
diagnostic observation is run, 64.90 is the narrowest evidence-bounded cohort;
it is not a promotion recommendation.

## Setup coverage and symmetry

The 183 `NO_SETUP` records are not a mass one-predicate near miss:

```text
missing structural trigger = 183
missing liquidity/level context = 183
missing directional context = 105
distance 2 missing predicates = 78
distance 3 missing predicates = 105
```

No setup-threshold cohort is justified. Setup observations contain 36 SHORT and
1 LONG candidates; this is market evidence, not a fabricated symmetry fix. The
tested LONG and SHORT traversal paths are direction-aware.

## Causal target hierarchy

The 5m path now exports and traverses distinct causal candidates in this order:

```text
nearest LOCAL_5M
next validated LOCAL_5M
STRUCTURAL
15M
reachable 1H
```

The nearest causal level is retained in the trace even when non-actionable.
Traversal never constructs a fixed-percent, ATR-derived or stop/RR-derived
target and never uses candles after the decision boundary. Each trace records
source/timeframe/price/distance, causal/future/direction/relevance flags, cost
floor, gross RR, expected edge, net RR, actionability and reject reason.

The historical 165-boundary dataset is a separate read-only causal replay of
the four previously admitted SOLUSDT observations (one contiguous unique
opportunity). Only candles closed before each decision construct targets;
later candles are read only by the offline outcome evaluator.

| replay metric | value |
|---|---:|
| candidates considered | 74 |
| first micro-local non-actionable | 4 |
| next LOCAL_5M selected/actionable | 2 |
| STRUCTURAL selected/actionable | 2 |
| 15m selected/actionable | 0 |
| 1h selected/actionable | 0 |
| no actionable causal target | 0 |
| actionable / cost pass / positive edge | 4 raw, 1 unique |

The 74 includes rejected wrong-direction and unreachable candidates so the trace
is auditable. Direction-valid causal candidates by source were LOCAL_5M 6,
STRUCTURAL 8 and 15M 4.

## Economics, stops and RR

Cost actionability is evaluated before RR:

```text
minimum_actionable_target_bps = fees + spread + slippage + depth impact
                              + safety margin + minimum_positive_edge_bps
```

Minimum-edge diagnostics are 0, 5 and 10 bps; production minimum edge is not
changed. Spread and depth remain mandatory. The fee is explicitly a conservative
configured assumption until an account-authoritative integration exists.

| distribution | P50 | P90 |
|---|---:|---:|
| stop distance, bps | 70.1970 | 70.4850 |
| target distance, bps | 329.1473 | 384.4440 |
| total costs, bps | 27.9831 | 28.2753 |
| net edge, bps | 301.1649 | 356.4632 |

All four replay rows pass net RR 1.0, 1.2 and 1.5. They are repeated boundaries
of one opportunity, so no RR cohort can be declared superior by expectancy.
The selected stop is causal and near the 80 bps envelope; it is not clipped.
The earlier full admitted sample's P90 around 257 bps remains evidence that wide
causal stops must be rejected, not reshaped to manufacture RR.

## Offline outcome and holding horizon

The sole unique opportunity hit its target before its stop in 5 minutes. The
result is identical for diagnostic 15, 30 and 60 minute horizons:

```text
completed unique opportunities = 1
win rate = 1.0
loss rate = 0.0
profit factor = undefined (no loss observations)
MFE = 408.1426 bps
MAE = 0 bps
estimated net outcome / expectancy = +300.7476 bps
sample classification = INSUFFICIENT_SAMPLE
```

Future candles do not feed the decision path. This result is not a production
entry, execution, or credible profitability estimate.

## Invariants and operational state

```text
RISK_BUDGET_RESERVATION_LEAKS = 0
NO_PLAN_CONSUMED_EXECUTION_QUOTA = 0
PROFILE_RESEARCH_COUNTERS_SEPARATE = YES
GLOBAL_ACCOUNT_RISK_AUTHORITY_SHARED = YES
TRADE_15M_PARAMETERIZATION_CHANGED_BY_TASK = NO
TRADE_15M_PRODUCTION_BEHAVIOR_CHANGED_BY_TASK = NO
TRADE_15M_SEARCH_CONTINUITY = PASS (3 boundaries, exact10, no incomplete rows)
PRODUCTION_5M_STRATEGY_THRESHOLD_CHANGED_BY_TASK = NO
PRODUCTION_5M_MIN_RR_CHANGED_BY_TASK = NO
PRODUCTION_5M_STOP_OR_VALIDITY_CHANGED_BY_TASK = NO
PRODUCTION_TRADING_MUTATIONS_BY_TASK = 0
BINANCE_ORDER_API_CALLS_BY_TASK = 0
CONTROL_POSTS_BY_TASK = 0
LIVE = DISABLED
```

WAL and PITR remained ready, no physical gap was reported, Control remained
`ARMED` generation 6, and no command or position was created. Production source
deployment and natural-boundary acceptance were not attempted because the
credential incident gate is open.

## Validation

```text
focused post-final-change = 81 passed
affected server/security = 854 passed, 5 skipped
invariant/i18n = 50 passed, 5 skipped
desktop = 1465 passed, 2 skipped, 3029 subtests
compileall = PASS
git diff --check = PASS (line-ending warnings only)
CHANGED_PATH_REGRESSION_FAILURES = 0
```

## Scalping readiness scorecard

| criterion | status | evidence |
|---|---|---|
| 5m profile isolation | PASS | explicit 5m enrichment; 15m equivalence tests and continuity |
| Strategy explainability | PASS | components, penalties, score, margin and conflict trace |
| unique opportunity semantics | PASS | 37 observations collapse to 11 episodes |
| causal stop | PASS | causal authority preserved; no clipping |
| actionable causal target | EARLY_SIGNAL | traversal passes; 1 unique historical opportunity |
| positive net edge | EARLY_SIGNAL | 1 unique historical opportunity |
| bounded transaction cost | PASS | mandatory spread/depth and fail-closed missing costs |
| RR viability | EARLY_SIGNAL | all cohorts pass same single opportunity |
| risk quota integrity | PASS | zero leaks; no-plan consumes no quota |
| short validity | EARLY_SIGNAL | 5-minute outcome, but one sample |
| PAPER expectancy | INSUFFICIENT_SAMPLE | 1 completed unique versus desired >=30 |

## Expert answers

1. Do not weaken the production Strategy threshold now.
2. 64.90 is suitable only as the next narrow SHADOW cohort because it captures
   the boundary cluster; downstream costs must be captured prospectively.
3. It adds 9 unique opportunities versus the current cohort in this snapshot.
4. Zero additional opportunities have proved actionable targets because their
   authoritative boundary costs are absent; fail-closed is intentional.
5. Zero additional opportunities have proved positive net edge. Separately, the
   historical traversal replay has one positive-edge unique opportunity.
6. At row level, next LOCAL_5M and STRUCTURAL split 2/2; the first unique episode
   selected next LOCAL_5M.
7. Selected P50/P90 near 70 bps is near the envelope, while the earlier 257 bps
   P90 confirms that many causal stops are unsuitable for a scalp.
8. No RR cohort is superior: 1.0/1.2/1.5 see the same single winning opportunity.
9. The sample is insufficient for production parameter promotion.
10. The profile is not ready for PAPER validation; it is ready for more SHADOW.

```text
FINAL_VERDICT = PASS_SOURCE_AND_SHADOW_CALIBRATION_DEPLOYMENT_WITHHELD
BLOCKER_CODE = PRODUCTION_DB_CREDENTIAL_ROTATION_PENDING_FOR_DEPLOYMENT
TRADING_VERDICT = 5M_READY_FOR_MORE_SHADOW
PROFITABILITY_CONFIDENCE = INSUFFICIENT_SAMPLE
NEXT_ACTION = PRODUCTION_DB_CREDENTIAL_ROTATION_INVALIDATION_AND_SAFE_SHARED_CLIENT_REBIND
AFTER_SECURITY_GATE = TRADERS_5M_SCALPING_EXTENDED_UNIQUE_OPPORTUNITY_SHADOW_OBSERVATION_01
```
