# TRADERS_FUNNEL_TO_TRADE_SCALPING_FULL_DIAGNOSTIC_AND_CORRECTION_01

## Final decision

```text
TASK = TRADERS_FUNNEL_TO_TRADE_SCALPING_FULL_DIAGNOSTIC_AND_CORRECTION_01
FINAL_STATUS = FAIL_CLOSED
FINAL_VERDICT = FAIL_CLOSED_EMPIRICAL_DATASET_INVALID
WORKDIR = D:\disk_E\game_projects\traders\traders-ml
BRANCH = feature/engine-platform
HEAD_BEFORE = fd1aef1685472634b0126a705f369f0ba9fbfe24
HEAD_AFTER = 2ad548b1e1b2f01a09200195855a28704c4f4764
REMOTE_HEAD = 2ad548b1e1b2f01a09200195855a28704c4f4764
PUSH = PASS; ahead=0; behind=0

RUNTIME_REVISION = 2ad548b1e1b2f01a09200195855a28704c4f4764
CONFIG_HASH = 9d3f604ee4a3b0793bb40ba3cef9826a36e00d945c44e60811cdeede6b1ee7ce
CONFIG_REGISTRY_HASH = 4553895fdd0f4beb0244d9a5ccca990fee6c7b672640cf5050c39761e8da82d1
CONFIG_EPOCH = d66efd4422e1c772b2f58e7789e3717f465e9fe86bd65a916dd918cef9569eb3
CONFIG_GENERATION = 1789752918012667500
PARAMETER_SET = scalping-v2-set-2; version=scalping-v2-set-2-v1

LIVE_STATE = DISABLED; PAPER=CONTINUOUS_ARMED; live_allowed=false
REAL_BINANCE_ORDER_CALLS = 0
15M_CHANGED = false
```

The prompt is not PASS because phases 15, 22, 29, 30, 31, 32 and 40 are not
PASS. The two implementation defects were corrected and deployed, but the
active set has zero compatible, naturally closed PAPER observations after the
invalid prospective/counterfactual records are removed from runtime authority.
No threshold was relaxed to manufacture a plan.

## Block gate

| Block | Result | Proven outcome |
|---|---|---|
| 0. Scalping rules | PASS | Net expectancy after fees, spread, slippage, depth/adverse fill is the primary gate; trade count and win rate are not objectives by themselves. |
| 1. Runtime truth | PASS | Git, containers, profile, PAPER control and LIVE prohibition verified. |
| 2. Canonical funnel | PASS | Code and persisted projection agree on the ordered stages below. |
| 3. Parameter map | PASS | YAML base, set-2 overrides, effective values and consumers traced. |
| 4. Hot reload/effective config | PASS | Active snapshot, generation, content hash, epoch and set binding are present in fresh rows. |
| 5. Analysis | PASS | Closed-candle multi-timeframe inputs and causal boundary use verified. |
| 6. Setup generation | PASS after correction | Indicator-only UNKNOWN/NO_IMPULSE promotion removed; explicit causal momentum state is now required. |
| 7. Strategy score | PASS | Score admission is upstream of economics and does not override downstream rejection. |
| 8. Geometry | PASS | Directional ordering, normalized levels and causal stop envelope audited. |
| 9. Stop logic | PASS | Stops are causal/ATR-buffered; over-wide stops fail closed. |
| 10. Target selection | PASS | Targets must be causal, directionally valid and above the economic floor. |
| 11. Costs | PASS | Real account commission snapshot plus spread, slippage, depth/adverse reserve; fail closed on missing authority. |
| 12. Net edge | PASS | `target_bps - all modeled costs` is evaluated before empirical expectancy. |
| 13. Gross/net RR | PASS | Gross RR is descriptive; net RR is cost adjusted and cannot alone approve a trade. |
| 14. Empirical expectancy | PASS after correction | EV now uses observed average net wins/losses, not the candidate's planned payoff as a substitute for history. |
| 15. Empirical integrity | **FAIL** | Runtime previously mixed prospective counterfactual outcomes with 53 natural closed PAPER positions. Clean active-set authority is 0 observations. |
| 16. Positive expectancy rule | PASS | Missing/zero/negative empirical EV rejects; no static fallback. |
| 17. Risk | PASS | Risk is downstream of RR; authoritative control retains max one open/new position. |
| 18. Selector | PASS | Selector cannot promote an ineligible candidate. |
| 19. Approval/plan/command bridge | PASS by code, NOT_REACHED naturally | No bypass around checklist, portfolio and idempotent command path found. |
| 20. Entry | PASS by audit | Next closed 1m/fill policy remains PAPER-only; no natural command in the acceptance boundary. |
| 21. Exit lifecycle | PASS by audit | Stop/target/time exit and stale shadow policy use real net PnL; no PnL rewriting. |
| 22. Frequency objective | **FAIL** | Historical 53-position cohort is net negative and active set has no clean authority; desired positive frequency is unproven. |
| 23. Bottleneck analysis | PASS | Dominant bottlenecks quantified. |
| 24. Counterfactual diagnostics | PASS | Counterfactual data retained for research diagnostics but removed from production probability authority. |
| 25. Allowed changes | PASS | Only scalping funnel/statistics/setup/export observability paths changed. |
| 26. Forbidden tuning | PASS | No YAML weakening, forced trade, label rewriting or quota was introduced. |
| 27. Parameter recommendations | PASS | Recommendation is evidence accumulation first; no unsupported parameter change. |
| 28. Math examples | PASS | Five real pre-fix candidates and one fresh post-fix candidate recomputed. |
| 29. Natural PAPER trade | **FAIL** | No clean eligible candidate reached RR, plan, command or position. |
| 30. Positive trade economics | **FAIL** | No natural approved trade exists to prove positive empirical EV. |
| 31. Natural close | **FAIL** | No new position; therefore no natural close. |
| 32. Small profit/frequency | **FAIL** | Historical cohort: win rate 28.30%, PF 0.3488, expectancy -0.209485 quote units/trade. |
| 33. No 100% promise | PASS | No claim that every realized trade wins. |
| 34. Corrections | PASS | Three causal defects corrected without widening scope. |
| 35. Git | PASS | Two project-state commits pushed; user changes preserved. |
| 36. Build/deploy | PASS | Orchestrator and Readonly API images rebuilt and containers recreated. |
| 37. Runtime revision | PASS | Both deployed images/containers report `2ad548b...`, never `UNSET`. |
| 38. Fresh funnel | PASS | Boundary 1789817400000 completed 10/10 using new revision and unchanged set hash. |
| 39. Regression protection | PASS for task scope | Core focused tests pass; six known stale `trade-5m-v1` export fixtures fail outside this profile. |
| 40. Combined success | **FAIL** | No natural trade with clean positive empirical EV exists, so the all-conditions success predicate is false. |

## Canonical funnel and ownership

```text
FUNNEL_STAGE_ORDER =
ANALYSIS_QUALIFIED
→ STRUCTURAL_SETUP
→ STRATEGY_ADMITTED
→ RISK_COMPATIBILITY_ADMITTED
→ GEOMETRY_VALID
→ TARGET_VALID
→ NET_COST_PASS
→ RR_PASS
→ RISK_ADMITTED
→ PORTFOLIO_ADMITTED
→ FINAL_APPROVAL
→ PAPER_PLAN
→ PAPER_COMMAND
→ POSITION
```

Primary owners:

- analysis/setup: `app/engine_setup/setup_detector.py::SetupDetector.detect`;
- strategy: `app/engine_strategy/strategy_filter.py::StrategyFilter.evaluate`;
- geometry/target/cost/RR projection: `app/engine_paper/scalping_shadow.py::evaluate_scalping_shadow`;
- empirical hierarchy: `app/engine_paper/scalping_statistics.py::PostgresPaperOutcomeStatisticsSource.resolve`;
- EV decision: `app/engine_paper/scalping_policy_v2.py::evaluate_expectancy`;
- plan: `app/engine_paper/scalping_paper_runner.py::ScalpingPaperRunner`;
- portfolio: `app/engine_paper/portfolio_gate.py::evaluate_paper_portfolio_gate`;
- selector: `app/engine_paper/eligible_approval_ranking.py::select`;
- command persistence/position bridge: `app/engine_paper/repositories.py` and controlled runtime;
- read projection/export: `app/server_api/trading_funnel.py` and `app/server_api/funnel_export.py`.

Each stage persists or projects PASS/REJECT/NOT_REACHED independently. A later
stage cannot retroactively turn an earlier rejection into eligibility.

## Funnel counts

### Fresh post-deploy natural boundary

```text
BOUNDARY_CLOSE_MS = 1789817400000
CYCLE_COMPLETE = true; symbols=10/10
ANALYSIS_COUNT = 10
SETUP_COUNT = 5
STRATEGY_COUNT = 5
RISK_COMPATIBILITY_COUNT = 5
GEOMETRY_COUNT = 2
TARGET_COUNT = 1
COST_COUNT = 1
RR_COUNT = 0
RISK_COUNT = 0
PORTFOLIO_COUNT = 0
APPROVAL_COUNT = 0
PLAN_COUNT = 0
COMMAND_COUNT = 0
POSITION_COUNT = 0
SETUP_TYPE_DISTRIBUTION = NO_SETUP 5; SCALP_MOMENTUM_CONTINUATION 5
```

The single post-deploy cost-valid candidate was DOGEUSDT bullish momentum:

```text
ENTRY = 0.08812
STOP = 0.08794437
TARGET = 0.088645
GROSS_RR = 2.98923874
NET_RR = 0.84620774
NET_EDGE = target 59.57784839 bps - modeled cost 23.13513820 bps = 36.44271019 bps
EXPECTED_EV = null; fail closed because empirical sample=0 and parent sample=0
BREAK_EVEN = unavailable without observed payoff distribution
MODELED_COSTS = entry fee 7.5 + exit fee 7.5 + spread 1.13513820 + entry slippage 2 + exit slippage 2 + adverse reserve 3 + depth impact 0 = 23.13513820 bps
REJECT = SCALPING_EMPIRICAL_EXPECTANCY_REJECTED
FEE_SOURCE = BINANCE_ACCOUNT_COMMISSION_SNAPSHOT
```

`NET_EDGE` is positive geometry, but it is not the required statistical
expectancy proof. With no compatible closed outcomes, `P(win)`, empirical
`AvgWin_net`, empirical `AvgLoss_net` and therefore EV are unknown.

### Audited historical windows before the authority correction

| Window | Analyses | Setups/strategy | Geometry | Cost-valid | RR/plan |
|---|---:|---:|---:|---:|---:|
| 1h capture | 120 | 45 | 9 | 5 | 0 / 0 |
| 4h exact | 480 | 254 | 92 | 29 | 0 / 0 |
| 12h | 1440 | 765 | 273 | 130 | 0 / 0 |
| 24h | 2880 | 1490 | 489 | 222 | 0 / 0 |

The exact 4h canonical stage projection was 480 analysis, 254 setup/strategy/
risk-compatibility, 92 geometry, 29 target/cost, zero RR and zero downstream.
The 24h rejection attribution was:

```text
NO_SETUP / no terminal diagnostic = 1392
SCALP_REJECT_CAUSAL_STOP_TOO_WIDE = 999
ECONOMIC_GEOMETRY_NOT_FEASIBLE = 232
PAPER_REJECT_INVALID_LEVEL_GEOMETRY at net-cost boundary = 35
SCALPING_EMPIRICAL_EXPECTANCY_REJECTED = 222
```

## Parameter map

All behavioral parameters resolve from
`config/trading/trade_parameters.yaml`; runtime consumers receive the immutable
active snapshot. The table shows base → set-2 override → effective runtime.

| Parameter/group | Base | Override | Effective | Consumer/stage |
|---|---|---|---|---|
| timeframe / required | 5m / 1m,5m,15m,1h | none | same | analysis/setup |
| windows | 1m=60, 5m=120, 15m=64, 1h=50 | none | same | market-data readiness |
| allowed setups | seven scalping types | none | same | setup detector |
| history / ATR / impulse | 120 / 12 / 8 | none | same | analysis/setup |
| impulse threshold / ATR multiple | 3.0% / 2.5 | none | same | causal momentum state |
| structure / confirmation / volume / regime | 12 / 1 / 12 / 24 | none | same | setup context |
| strategy minimum score | 87.75 | none | 87.75 | strategy admission |
| ATR stop buffer | 0.25 | none | 0.25 | geometry |
| stop min/max bps | 0 / base profile value | max=36 | 0 / 36 | stop envelope |
| target min bps | base profile value | 40 | 40 | target/economic geometry |
| minimum planned RR | 0.4 | 0.476674 | 0.476674 | net geometry requirement |
| min net edge bps | 8 | 5 | 5 | net cost gate |
| minimum expected EV | 0 | none | 0 | empirical EV gate |
| bucket minimum sample | 20 | none | 20 | probability authority |
| probability confidence | 0.95 | 0.85 | 0.85 | conservative probability |
| Beta priors | 1 / 1 | none | 1 / 1 | empirical posterior |
| static RR fallback | false | none | false | fail-closed EV |
| hierarchy | exact→setup/direction/regime→setup/direction→setup→global | none | same | empirical source |
| commission | Binance account, real=true, fail_closed=true | none | same | costs |
| configured fee fallback | 10/10 bps, stub disabled | none | same | costs only when authoritative policy permits; currently fail closed |
| spread/slippage/adverse | book ticker / 2+2 / 3 bps | none | same | costs |
| depth max/reference notional | 20 bps / 100 | none | same | costs |
| plan/fill/validity/drift | 30s / 30s / 1 boundary / 10 bps | none | same | lifecycle |
| exit time stop | 15m | none | 15m | exit |
| stale soft/hard/extension | base / base / base | 600s / 1200s / 300s, max 1 | override | stale shadow |
| net break-even protection | base | true | true | exit shadow |

```text
HARDCODED_BEHAVIORAL_VALUES = none found in the corrected decision path; numeric formulas/constants are versioned policy mechanics, while tunable thresholds are YAML-resolved
UNUSED_PARAMETERS = none proven among the requested active-set fields
STALE_CONFIG_PATHS = prospective calibration directory was a stale production statistics input and was removed from runtime composition
PARAMETERS_CHANGED = none
PARAMETER_CHANGE_PROOFS = no YAML diff in either project-state commit; active content hash remained 9d3f604e...
```

The reported profile maximum of two positions is not allowed to weaken the
authoritative operator control scope (`max_new=1`, `max_open=1`).

## Technical findings

### Setup generation

The pre-fix 24h distribution was 1490 candidates, 1477 of them momentum
continuations, heavily concentrated in UNKNOWN regime. Indicator votes could
promote a momentum setup even when the causal momentum state was UNKNOWN or
NO_IMPULSE. The correction retains indicator votes for direction selection but
requires explicit EXPANSION or impulse/pullback state before momentum
promotion. Fresh boundary distribution is 5 no-setup / 5 momentum rather than
10 unconditional momentum candidates.

### Geometry, targets and costs

Pre-fix stop distances over the 4h setup cohort (`N=254`) were min 4.4557,
p25 23.7445, median 50.1260, p75 88.6878 and max 321.2638 bps; 105 were at
least 60 bps. Thus `stop_max_bps=36` is a material causal gate, not an arbitrary
source of zero plans. Targets are selected only from causal/relevant levels and
must cover the transaction-cost floor. The cost model includes both fees,
spread, both slippage legs, depth impact and adverse-fill reserve with a fresh
real-account commission snapshot. No double counting was found in the current
round-trip formula.

### RR and empirical expectancy

The corrected acceptance equation is:

```text
EV_net_bps = p_conservative * AvgWin_net_bps
           - (1 - p_conservative) * AvgLoss_net_bps
accept only when sample authority is sufficient and EV_net_bps > minimum EV
```

The earlier implementation computed an R-form expectation from the candidate's
planned net RR and treated a loss as one R. That is a geometry model, not the
observed payoff distribution requested by the task. The corrected runtime
stores/exports the selected bucket's observed average positive and negative
net returns and normalizes EV by observed average loss only for reporting.

The larger defect was dataset provenance: the production source appended
causal prospective/counterfactual opportunity outcomes to natural closed PAPER
positions. Those observations can be useful for research but are not executed
trade outcomes. Production authority is now
`postgres-natural-paper-closed-only-v3`, restricted to closed `trade-5m-v2`
PAPER positions and realized net return bps.

Clean database facts:

```text
closed natural PAPER positions = 53
open positions = 0
first/last closes = 2026-09-03 / 2026-09-06
compatible observations for active set-2 buckets = 0
prospective source in runtime probability authority = 0 after correction
```

### Risk, selector, bridge and exit

Risk sizing is reached only after cost and empirical RR/EV gates. Portfolio and
selector code cannot turn a rejected candidate into a plan. Plan/command
identities remain deterministic and command creation is idempotent. Entry uses
the PAPER causal fill boundary; exit uses stop, target, time stop and stale
shadow evidence with real net-PnL accounting. Because no post-fix candidate
passed empirical authority, risk/portfolio/approval/bridge/exit were naturally
NOT_REACHED rather than synthetically exercised.

```text
RISK_FINDINGS = no bypass; authoritative max_open/max_new remains 1
SELECTOR_FINDINGS = no ineligible promotion path found
BRIDGE_FINDINGS = no natural plan, command or position; persistence path unchanged
EXIT_FINDINGS = no new position/close; historical outcomes are not rewritten
```

## Mathematical evidence

Five representative pre-fix cost-valid candidates all had negative modeled EV
under the contaminated historical estimator:

| Symbol/time | Gross RR | Net RR | Cost bps | Sample W/L | conservative p | EV (R) |
|---|---:|---:|---:|---:|---:|---:|
| AVAX 10:25 | 4.1065 | 1.2748 | 23.8724 | 17/34 | 0.27598 | -0.37219 |
| ADA 10:55 | 2.6667 | 0.4973 | 26.5015 | 27/44 | 0.32667 | -0.51088 |
| AVAX 10:55 | 2.5041 | 1.1296 | 23.1678 | 17/31 | 0.29327 | -0.37544 |
| ADA 11:00 | 2.6667 | 0.5518 | 26.5218 | 27/44 | 0.32667 | -0.49307 |
| DOGE 11:05 | 2.1681 | 0.4902 | 23.1527 | 17/49 | 0.21323 | -0.68225 |

These examples prove that zero RR PASS was not evidence that the YAML RR floor
was too strict. The fresh DOGE example further proves that even positive net
geometry cannot be approved when the empirical payoff distribution is absent.

## Historical business metrics

For the only 53 naturally closed PAPER positions available:

```text
TRADE_FREQUENCY = 13.879 trades/day over the observed period
WIN_RATE = 15/53 = 28.3019%
PROFIT_FACTOR = 0.348847
EXPECTANCY = -0.209485 quote units/trade
MEDIAN_NET_PNL = -0.36467214
TOTAL_NET_PNL = -11.102696
TOTAL_FEES = 10.050033
MEDIAN_HOLDING_TIME = 11 minutes
```

This cohort is not evidence for active set-2 admission, but it independently
shows that past PAPER economics were negative. It must not be hidden by tuning
for more trades or a higher apparent win rate.

## Defects and corrections

```text
MATH_DEFECTS_FOUND = planned candidate net RR substituted for empirical AvgWin/AvgLoss in EV
IMPLEMENTATION_DEFECTS_FOUND = production statistics mixed prospective outcomes; indicator-only UNKNOWN/NO_IMPULSE momentum promotion
CONFIG_DEFECTS_FOUND = none proven; no threshold change justified
RUNTIME_DEFECTS_FOUND = pre-fix images did not contain corrections; rebuilt/recreated and verified
```

Corrections:

1. Natural, closed, realized PAPER outcomes are the sole production statistical
   authority; research prospective loader remains isolated.
2. Each empirical bucket carries observed average net win/loss bps; EV uses
   those values and fails closed if the payoff distribution is unavailable.
3. Momentum setup creation requires causal momentum state rather than indicator
   direction alone.
4. Export observability includes empirical average payoff fields.

No customer-facing text was added. New fields are technical report schema
keys; existing client-visible labels/reasons continue to resolve through i18n.

## Natural trade result

```text
NATURAL_ELIGIBLE_CANDIDATE = none
NATURAL_APPROVAL_ID = null
NATURAL_PLAN_ID = null
NATURAL_COMMAND_ID = null
NATURAL_POSITION_ID = null

POSITION_STATUS = NOT_OPENED
NATURAL_CLOSE = NOT_APPLICABLE
GROSS_PNL = null
NET_PNL = null
FEES = null
HOLDING_TIME = null
```

## Validation and deployment

```text
TESTS = task-focused core 38 passed, 1 skipped; setup isolation 2 passed
KNOWN_TEST_FAILURES = 6 stale server export fixtures still request removed trade-5m-v1 profile; unrelated to trade-5m-v2 corrections
COMPILE = PASS for every changed Python module
BUILD = PASS; orchestrator image sha256:232403ebe246787491c5f98a02386381e758cf8ba9857e24426b5d71b6fbbfb3; readonly image sha256:3ef699f8d2ba84e4f40f784c2cc9fcb1ec7288d20f2feee3766ceb0afb579df8
DEPLOY = PASS; both containers revision=2ad548b1e1b2f01a09200195855a28704c4f4764; readonly healthy; orchestrator running; restart_count=0
FRESH_ACCEPTANCE = PASS boundary completion and provenance; FAIL trade eligibility because clean empirical authority=0
```

Commits:

```text
cdaf1983177319817275b22b93a7e941c3590b2d fix(scalping): isolate empirical expectancy authority
2ad548b1e1b2f01a09200195855a28704c4f4764 fix(scalping): require causal momentum state
```

Project-state files changed by those commits:

```text
app/engine_paper/scalping_policy_v2.py
app/engine_paper/scalping_shadow.py
app/engine_paper/scalping_statistics.py
app/engine_setup/setup_detector.py
app/server_api/funnel_export.py
scripts/engine_orchestrator_online_pipeline.py
tests/engine_paper/test_scalping_statistics.py
tests/integration/paper_natural_execution_e2e/test_probability_authority_accumulation_postgres.py
tests/server_api/test_funnel_export.py
tests/test_probability_authority_accumulation.py
tests/test_scalping_conservative_probability.py
tests/test_scalping_dynamic_ev_gate.py
tests/test_scalping_independent_profile_v2.py
tests/test_scalping_probability_fallback_hierarchy.py
tests/test_scalping_rr_dynamic_anchor_forensic.py
tests/test_strategy_edge_geometry_forensic.py
```

Unrelated pre-existing worktree edits and deleted research artifacts were not
staged, rewritten or removed.

## Required next stage

`CURRENT_STAGE` is clean natural PAPER evidence accumulation for the active
parameter set. Keep LIVE disabled and parameters unchanged. Only naturally
closed, realized `trade-5m-v2` PAPER positions with compatible setup/direction/
regime/volatility buckets may build authority. Re-run acceptance once at least
the configured 20 compatible observations exist; then require conservative
positive EV using observed net payoff sizes before any plan is allowed.

