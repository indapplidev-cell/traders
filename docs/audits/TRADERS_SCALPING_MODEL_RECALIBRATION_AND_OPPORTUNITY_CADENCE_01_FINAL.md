# TRADERS_SCALPING_MODEL_RECALIBRATION_AND_OPPORTUNITY_CADENCE_01

## Verdict

```text
TASK_STATUS = TERMINAL_NO_PROMOTION
FINAL_VERDICT = REJECTED_NO_OUT_OF_SAMPLE_POSITIVE_EXPECTANCY
SCALPING_ONLY_CHANGE = YES_READONLY_CALIBRATION_TOOLING_ONLY
CONFIG_ONLY_SOLUTION_ASSESSED = YES
CAN_SCALPING_BE_RECALIBRATED_BY_CONFIG_ONLY = NO
RUNTIME_OR_STRATEGY_CHANGE = NONE
LIVE_STATE_AFTER = DISABLED
BINANCE_ORDER_API_CALLS_BY_TASK = 0
SECRET_OUTPUT = 0
```

No Scalping parameter was promoted.  This is the required fail-closed outcome:
the bounded search found no configuration with positive calibration expectancy,
so validation/holdout promotion was forbidden.  `trade-15m-v1` source,
configuration, versions and runtime were not changed.

## Config-only assessment

The Scalping runtime has one immutable, profile-indexed parameter object in
`app/engine_orchestrator/runtime_parameters.py`, constructed from
`app/engine_orchestrator/trade_profile.py`.  It is loaded at process start;
there is no hot reload.  A changed object receives a content-derived parameter
set identifier and requires the normal image/profile deployment path.

Most tuning is already profile-scoped.  A lower Scalping RR cannot currently be
promoted by data-only configuration because these three guards encode 1.5 as a
global invariant:

1. `TradeSearchProfile.__post_init__` rejects `minimum_planned_rr < 1.5`;
2. `RuntimeProfileParameters.__post_init__` rejects the same value;
3. `ShadowGeometryConfig.__post_init__` accepts only `production_rr_floor == 1.5`.

If a future replay proves a lower RR, the only justified runtime code change is
a profile-aware validation floor in those bounded contracts while retaining an
exact 1.5 invariant for `trade-15m-v1`.  No strategy-engine rewrite is needed.

## Authoritative Scalping parameter map

All values below are current and unchanged.  Runtime parameter identity is
`trade-5m-v1-runtime-v1-af11b65b74275bf3`.

| Domain / knob | Current value | Source | Scope / reload | Version |
|---|---|---|---|---|
| Setup families | 7 explicit `SCALP_*` families | `runtime_parameters.py` | Scalping-only, process restart | `scalping-setup-families-v1` |
| Analysis compression / expansion | 0.75 / 1.35 | `runtime_parameters.py` | profile object, process restart | parameter-set ID |
| History / ATR / impulse / structure | 120 / 24 / 12 / 48 candles | `trade_profile.py`, `runtime_parameters.py` | Scalping-only, process restart | parameter-set ID |
| Confirmation / volume / regime | 3 / 36 / 72 candles | same | Scalping-only, process restart | parameter-set ID |
| Strategy score cohorts | 55 / 60 / 65; production risk minimum 65 | `runtime_parameters.py` | Scalping parameter object; strategy policy ID is shared | `engine-strategy-01-shadow-v1` |
| ATR stop buffer | 0.25; cohorts 0.25 / 0.5 / 0.75 | `runtime_parameters.py` | profile object, process restart | `LOCAL_INVALIDATION_STRUCTURE_WITH_VOLATILITY_BUFFER` |
| Maximum stop | 80 bps; cohorts 50 / 65 / 80 | `runtime_parameters.py` | profile object, process restart | parameter-set ID |
| Minimum target diagnostic | 45 bps; cohorts 45 / 60 / 80 | `runtime_parameters.py` | profile object, process restart | target policy |
| Target selection | causal hierarchy, cost-aware traversal | `runtime_parameters.py`, `scalping_shadow.py` | Scalping-only | `CAUSAL_HIERARCHY_COST_AWARE_NET_RR_V3` / `scalping-causal-cost-aware-target-v2` |
| Fees | 10 bps entry + 10 bps exit | `runtime_parameters.py` | current values shared, separately materialized | `scalping-round-trip-net-pnl-v2` |
| Slippage | 2 bps entry + 2 bps exit | same | current values shared, separately materialized | same cost model |
| Spread | authoritative public book ticker | `scalping_paper_runner.py` | runtime input, fail closed | same cost model |
| Depth / impact | authoritative bounded depth, max 20 bps, depth limit 100 | `runtime_parameters.py`, `scalping_paper_runner.py` | profile object + runtime input | same cost model |
| Cost safety margin | 3 bps | `trade_profile.py` | Scalping-only | parameter-set ID |
| Minimum net edge | 1 bps; research cohorts 10 / 15 / 20 | `runtime_parameters.py` | profile object, process restart | parameter-set ID |
| Minimum net RR | 1.5; cohorts 1.0 / 1.2 / 1.5 | `trade_profile.py`, `runtime_parameters.py` | value is profile-held but global guards block lower values | `scalping-required-net-rr-v2` |
| Risk per trade | 10 bps (0.10%); cohorts 10 / 15 / 20 / 25 | `runtime_parameters.py`, `scalping_sizing.py` | Scalping-only sizing input | `ENGINE_RISK_01_RESEARCH_POLICY_V1` |
| Concurrent positions | 3 | `runtime_parameters.py`, `portfolio_gate.py` | profile input, shared account authority | parameter-set ID |
| Total open risk | 50 bps (0.50%) | same | profile input, shared account authority | parameter-set ID |
| TTL / price drift | 60 seconds / 10 bps | `runtime_parameters.py` | Scalping-only | parameter-set ID |
| Duplicate/opposing exposure | same-symbol exposure forbidden | `portfolio_gate.py` | shared portfolio authority, not loosened | existing portfolio contract |
| Re-entry / cooldown | re-entry disabled; no independent time cooldown knob | `runtime_parameters.py` | Scalping-only flag | parameter-set ID |
| Exit time stop | 30 minutes; cohorts 15 / 30 / 45 | `runtime_parameters.py` | Scalping-only | parameter-set ID |

The selector, approval, execution, readonly, portfolio-account authority and all
15m semantics remain shared/frozen exactly as required.

## Historical data and split

The replay consumed append-only collector segments `84b3b691` and `59b30160`.
It scanned 8,130 observations and 624 completed outcome records; 531 had all
causal geometry, authoritative spread/depth and closed-1m path inputs required
for replay.  The remaining 93 were explicitly not imputed.

| Window | UTC days | Replayable outcomes | Symbols | Span |
|---|---|---:|---:|---:|
| Calibration | 2026-08-27, 2026-08-28 | 400 | 9 | 30.667 h |
| Validation | 2026-08-29 | 38 | 6 | 24.000 h |
| Holdout | 2026-08-30, 2026-09-01, 2026-09-02 | 93 | 7 | 83.417 h |

Holdout was not used for selection.  Replay retains long/short observations,
multiple hours, symbols and regimes from the prospective collector.  Same-candle
stop/target ambiguity is scored conservatively as stop-first.  Opportunity IDs
are deduplicated before cadence and PnL metrics.

## Bounded search and results

The search evaluated exactly 648 configurations:

```text
minimum net RR       = 0.4, 0.6, 0.8, 1.0, 1.2, 1.5
minimum net edge bps = 1, 10, 15, 20
minimum score        = 55, 60, 65
ATR buffer           = 0.25, 0.5, 0.75
maximum stop bps     = 50, 65, 80
```

Every configuration retained 20 bps round-trip fees, 4 bps round-trip
slippage, 3 bps safety margin, and the observed authoritative spread and depth
impact.  Risk per trade and portfolio limits were not searched or increased.

Baseline outcome metrics (RR 1.5, edge 1 bps, score 65, ATR 0.25, stop 80):

| Window | Opportunities/h | Expectancy/trade | Expectancy/h | Profit factor | Win rate | Max DD | Loss streak |
|---|---:|---:|---:|---:|---:|---:|---:|
| Calibration | 1.4022 | -21.2349 bps | -29.7751 bps | 0.3440 | 20.93% | 931.4258 bps | 12 |
| Validation | 0.2917 | -33.6032 bps | -9.8009 bps | 0.0000 | 0.00% | 235.2221 bps | 7 |
| Holdout | 0.1319 | -42.0828 bps | -5.5494 bps | 0.0000 | 0.00% | 462.9110 bps | 11 |

The best calibration row was still rejected: RR 1.5, edge 1 bps, score 55,
ATR 0.75, stop 80; 0.9783 opportunities/h, expectancy -10.7754 bps/trade,
profit factor 0.5768, win rate 26.67%, max drawdown 406.3359 bps, loss streak 7,
and both calibration days negative.  Therefore:

```text
VIABLE_CALIBRATION_CONFIGURATIONS = 0_OF_648
VALIDATION_SURVIVORS = 0
HOLDOUT_PROMOTION_EVALUATIONS = 0
SCALPING_PARAMETER_SEARCH = PASS_NO_PROMOTABLE_CONFIGURATION
SCALPING_HOLDOUT_VALIDATION = NOT_RUN_FOR_PROMOTION_NO_CALIBRATION_SURVIVOR
```

The supplied operational 4h funnel remains the natural baseline:
480 analyses -> 64 setup -> 32 geometry -> 5 target -> 1 cost/RR/final/plan,
or 0.25 Plan PAPER/h and 15.625% geometry-to-target conversion.  Because no
configuration was promoted, there is no honest AFTER production metric.

## Tests, isolation and operations

The read-only replay tests prove a lower-RR positive-net candidate can pass,
a cost-heavy candidate rejects, a wide-stop candidate rejects, and ambiguous
same-candle paths use the conservative loss ordering.  Runtime regression and
PostgreSQL evidence are recorded in the task handoff after execution.

No migration, deployment, config/profile promotion, Control mutation, PAPER
command, position, LIVE action, private exchange request, or Binance order API
call was made.  The machine-readable search artifact is
`TRADERS_SCALPING_MODEL_RECALIBRATION_AND_OPPORTUNITY_CADENCE_01_SEARCH.json`.

## Operational output

```text
TASK_STATUS = TERMINAL_NO_PROMOTION
FINAL_VERDICT = REJECTED_NO_OUT_OF_SAMPLE_POSITIVE_EXPECTANCY

SCALPING_PROFILE_ID = trade-5m-v1
SCALPING_VERSION_BEFORE = trade-5m-v1-runtime-v1-af11b65b74275bf3
SCALPING_VERSION_AFTER = trade-5m-v1-runtime-v1-af11b65b74275bf3

TRADE_15M_VERSION_BEFORE = trade-15m-v1-runtime-v1-44aa91202a60146c
TRADE_15M_VERSION_AFTER = trade-15m-v1-runtime-v1-44aa91202a60146c
TRADE_15M_BEHAVIOR_CHANGED = NO

CAN_SCALPING_BE_RECALIBRATED_BY_CONFIG_ONLY = NO
CODE_CHANGES_REQUIRED = NO_FOR_RUNTIME_PROMOTION_YES_READONLY_REPLAY_TOOL_ADDED
CODE_CHANGES_SCOPE = OFFLINE_CAUSAL_OUTCOME_SEARCH_AND_TESTS_ONLY

BASELINE_OPPORTUNITIES_PER_HOUR = 0.25_NATURAL_4H_PLAN_PROXY; REPLAY_CALIBRATION_1.4022
AFTER_OPPORTUNITIES_PER_HOUR = NOT_AVAILABLE_NO_PROMOTION
BASELINE_PLAN_PAPER_PER_HOUR = 0.25_NATURAL_4H
AFTER_PLAN_PAPER_PER_HOUR = NOT_AVAILABLE_NO_PROMOTION

BASELINE_NET_EXPECTANCY_PER_TRADE = CALIBRATION_-21.2349_BPS; VALIDATION_-33.6032_BPS; HOLDOUT_-42.0828_BPS
AFTER_NET_EXPECTANCY_PER_TRADE = NOT_AVAILABLE_NO_PROMOTION
BASELINE_NET_EXPECTANCY_PER_HOUR = CALIBRATION_-29.7751_BPS; VALIDATION_-9.8009_BPS; HOLDOUT_-5.5494_BPS
AFTER_NET_EXPECTANCY_PER_HOUR = NOT_AVAILABLE_NO_PROMOTION
BASELINE_PROFIT_FACTOR = CALIBRATION_0.3440; VALIDATION_0; HOLDOUT_0
AFTER_PROFIT_FACTOR = NOT_AVAILABLE_NO_PROMOTION
BASELINE_MAX_DRAWDOWN = CALIBRATION_931.4258_BPS; VALIDATION_235.2221_BPS; HOLDOUT_462.9110_BPS
AFTER_MAX_DRAWDOWN = NOT_AVAILABLE_NO_PROMOTION
BASELINE_WIN_RATE = CALIBRATION_20.93%; VALIDATION_0%; HOLDOUT_0%
AFTER_WIN_RATE = NOT_AVAILABLE_NO_PROMOTION
BASELINE_TARGET_CONVERSION = 5_OF_32_15.625_PERCENT_SUPPLIED_NATURAL_4H
AFTER_TARGET_CONVERSION = NOT_AVAILABLE_NO_PROMOTION

RR_POLICY_BEFORE = scalping-required-net-rr-v2_MIN_1.5
RR_POLICY_AFTER = UNCHANGED
NET_EDGE_POLICY_BEFORE = MIN_1_BPS_WITH_AUTHORITATIVE_FULL_COSTS
NET_EDGE_POLICY_AFTER = UNCHANGED
TARGET_POLICY_BEFORE = CAUSAL_HIERARCHY_COST_AWARE_NET_RR_V3
TARGET_POLICY_AFTER = UNCHANGED
COST_MODEL_CHANGED = NO
RISK_POLICY_CHANGED = NO

CALIBRATION_RESULT = FAIL_ZERO_OF_648_PROMOTABLE
VALIDATION_RESULT = NOT_ELIGIBLE_NO_CALIBRATION_SURVIVOR
HOLDOUT_RESULT = BASELINE_NEGATIVE_NOT_USED_FOR_SELECTION_NO_CANDIDATE_UNBLINDED

POSTGRES_E2E = NOT_APPLICABLE_NO_NEW_POLICY_SELECTED
TRADE_15M_REGRESSION = PASS_64_PASSED_5_POSTGRES_OPT_IN_SKIPPED

SERVER_HEAD = 884b5cd9811102b92099f673e5f78c8cb20d9965
DEPLOYED_COMMIT = daa8312eabeb632937b7d7d09b8c33b73b6cb0a7_SCALPING_RUNTIME
SCHEMA_HEAD = 0020_paper_plan_execution_outcomes

LIVE_STATE_AFTER = DISABLED
BINANCE_ORDER_API_CALLS_BY_TASK = 0
SECRET_OUTPUT = 0

REMAINING_BLOCKERS = NO_CONFIGURATION_WITH_POSITIVE_CALIBRATION_EXPECTANCY; CURRENT_HOMOGENEOUS_AF11B_SAMPLE_BELOW_24H_AND_30_OUTCOME_GATES_AT_INITIAL_SNAPSHOT
NEXT_ACTION = CONTINUE_NATURAL_COLLECTION_AND_REPEAT_THE_SAME_PRESPECIFIED_SEARCH_AFTER_SAMPLE_GATES_WITHOUT_PARAMETER_PROMOTION
```
