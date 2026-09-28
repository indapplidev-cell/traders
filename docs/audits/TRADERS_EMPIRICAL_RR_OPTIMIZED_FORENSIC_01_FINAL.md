# Traders empirical RR optimized forensic 01 — final

## Decision

```text
FINAL_STATUS = PARTIAL
FINAL_VERDICT = EMPIRICAL_AUTHORITY_ATTRIBUTION_FALLBACK_QUERY_AND_MATH_ARE_CORRECT; INTENTIONAL_NEGATIVE_EV_VETO_CREATES_A_SELF_LOCK_FOR_THE_ESTABLISHED_MOMENTUM_CONTINUATION_AUTHORITY
CURRENT_BLOCKER = POLICY_DESIGN_DECISION_REQUIRED
IMPLEMENTATION_DEFECT_FOUND = NO
IMPLEMENTATION_FIX_APPLIED = NO
DEPLOYMENT_REQUIRED = NO
```

This was a read-only forensic task. No trade was forced, no history was
modified, no policy was tuned, and no service was rebuilt or restarted.

## A. Scope and data reduction

The immutable input was
`C:\Users\ZENOL\Documents\funnel_2809_163003_172.jsonl` (the exact evidence
file was found in Documents rather than Downloads). It was streamed once for
predicate extraction and grouping; there was no 24-hour replay and no manual
per-row inspection.

```text
TOTAL_24H_ROWS = 5740
RR_ROWS_EXTRACTED = 67
RR_PASS = 9
RR_EMPIRICAL_REJECTS = 58
REJECT_REASON = SCALPING_EMPIRICAL_EXPECTANCY_REJECTED (58/58)
SETUP = SCALP_MOMENTUM_CONTINUATION (58/58)
DIRECTION = BEARISH 35; BULLISH 23
NORMALIZED_VOLATILITY_REGIME = EXPANSION 58
FALLBACK_LEVEL = setup 58
DISTINCT_EXPORTED_BUCKETS = 22
DISTINCT_SELECTED_AUTHORITY_BUCKETS = 1
DISTINCT_OBSERVATION_SET_FINGERPRINTS = 1
OBSERVATION_SET_FINGERPRINT_SHA256 = 904aaebba0a98530c61ef254ae373956d771430e1a1f37e8ea5c71fd8991dca4
DEEP_CASES_ANALYZED = 5
```

The fingerprint is SHA-256 over the sorted authoritative position IDs. It
deliberately excludes candidate inputs such as candidate break-even rate.
All 58 rows have the same 20/7/13 authority and payoff aggregates. The first
reject is later than the twentieth authority close at `2026-09-27T21:32:00Z`,
so this cohort does not contain future leakage.

Rejects by symbol: ETH 8, BNB 8, LTC 6, BTC 6, SOL 6, XLM 4, ZEC 4,
DOGE 4, ADA 3, FIL 2, UNI 2, XRP 2, FET 1, ENA 1, AVAX 1.

## B. Representative cases

The mandatory FET case plus four automatically selected cases cover both
directions, the low/high RR range, and different requested keys. There was no
additional semantic diversity in setup, normalized regime, liquidity/cost
bucket, fallback path, or observation set.

| Candidate boundary UTC | Direction | Net RR | Requested/selected exported key suffix | Selected semantics |
|---|---:|---:|---|---|
| FETUSDT 2026-09-28T03:45:00Z | BEARISH | 2.93842896 | `setup|FETUSDT|SCALP_MOMENTUM_CONTINUATION|BEARISH|EXPANSION|MEDIUM` | setup population, 20/7/13 |
| ETHUSDT 2026-09-28T09:15:00Z | BULLISH | 0.52058734 | `setup|ETHUSDT|SCALP_MOMENTUM_CONTINUATION|BULLISH|EXPANSION|MEDIUM` | setup population, 20/7/13 |
| XRPUSDT 2026-09-28T12:40:00Z | BULLISH | 1.72831841 | `setup|XRPUSDT|SCALP_MOMENTUM_CONTINUATION|BULLISH|EXPANSION|MEDIUM` | setup population, 20/7/13 |
| BNBUSDT 2026-09-28T03:45:00Z | BEARISH | 1.07910045 | `setup|BNBUSDT|SCALP_MOMENTUM_CONTINUATION|BEARISH|EXPANSION|MEDIUM` | setup population, 20/7/13 |
| DOGEUSDT 2026-09-28T05:45:00Z | BEARISH | 1.39831173 | `setup|DOGEUSDT|SCALP_MOMENTUM_CONTINUATION|BEARISH|EXPANSION|MEDIUM` | setup population, 20/7/13 |

All keys have prefix `empirical-regime-v1`. The rejected cohort's complete net
RR range is 0.48303559–2.93842896.

## C. Exact 20 observations

Read-only production SQL reproduced the source join and filtered
`parameter_set_id=scalping-v2-set-2`, resolved configuration hash
`9d3f604ee4a3b0793bb40ba3cef9826a36e00d945c44e60811cdeede6b1ee7ce`,
and setup `SCALP_MOMENTUM_CONTINUATION`. Every row is authority-eligible as a
unique CLOSED `trade-5m-v2` PAPER position. `S/D/S/G` below means membership in
the applicable setup-direction, setup, and global parents; the selected
authority is `S` (setup). Exact and setup-direction-regime have zero members
for the five candidates. Liquidity/cost bucket is MEDIUM at evaluation; the
stored source regimes shown below are intentionally ignored by setup fallback.

| # | Observation ID | Position ID | Symbol/side | Source regime | Open → close UTC | Exit | Net PnL | Net bps | Membership / eligibility |
|---:|---|---|---|---|---|---|---:|---:|---|
| 1 | `setup:SOLUSDT:5m:1789834800000:SCALP_MOMENTUM_CONTINUATION:SETUP_CANDIDATE:8f4dc7dc094ca7df` | `paper:continuous:position:48968843e65aa640cd0523a5f3562904019eacae86eec7a199afc0c6484d8ba6` | SOLUSDT SHORT | UNKNOWN | 2026-09-19 16:21 → 16:36 | STOP_LOSS | -0.092710848 | -36.7461089523 | D(BEARISH)/S/G; eligible |
| 2 | `setup:DOGEUSDT:5m:1789839300000:SCALP_MOMENTUM_CONTINUATION:SETUP_CANDIDATE:7380859b42b77029` | `paper:continuous:position:81bf5b92675716204fe3aed3a3090faec1ea2358cffc79fbd062cad54db1c153` | DOGEUSDT LONG | UNKNOWN | 2026-09-19 17:36 → 17:38 | STOP_LOSS | -0.086612250 | -43.6523562830 | D(BULLISH)/S/G; eligible |
| 3 | `setup:ETHUSDT:5m:1789839900000:SCALP_MOMENTUM_CONTINUATION:SETUP_CANDIDATE:6bd86318bdb6350c` | `paper:continuous:position:cf1b8d810747680bae1ab0efb710c10449df42531871ace37d689f068de5f1b0` | ETHUSDT SHORT | UNKNOWN | 2026-09-19 17:46 → 18:17 | TAKE_PROFIT | 0.041843844 | 17.3730284339 | D(BEARISH)/S/G; eligible |
| 4 | `setup:SOLUSDT:5m:1789842600000:SCALP_MOMENTUM_CONTINUATION:SETUP_CANDIDATE:f94d616f48430e2f` | `paper:continuous:position:94caf8fa52d7c28dc10adcb3b8a0bed0edbe97788c347cea5b0a272e10d27bfc` | SOLUSDT SHORT | UNKNOWN | 2026-09-19 18:31 → 18:38 | STOP_LOSS | -0.098061906 | -46.7648782070 | D(BEARISH)/S/G; eligible |
| 5 | `setup:ADAUSDT:5m:1789849800000:SCALP_MOMENTUM_CONTINUATION:SETUP_CANDIDATE:c05e0dfb32f00184` | `paper:continuous:position:f70d650525bc075a70c19dec8550537b272deba81f9c96b8249f0f2cff725008` | ADAUSDT SHORT | UNKNOWN | 2026-09-19 20:31 → 20:58 | SYSTEM_SAFETY_EXIT | 0.042611494 | 22.0434040771 | D(BEARISH)/S/G; eligible |
| 6 | `setup:ADAUSDT:5m:1789864200000:SCALP_MOMENTUM_CONTINUATION:SETUP_CANDIDATE:e9c359214992b718` | `paper:continuous:position:50fb19774454512fe97a78346501682525a7b97fa8821f7c2265251819a7a541` | ADAUSDT LONG | UNKNOWN | 2026-09-20 00:31 → 00:42 | SYSTEM_SAFETY_EXIT | 0.027661390 | 22.1980293516 | D(BULLISH)/S/G; eligible |
| 7 | `setup:ADAUSDT:5m:1789865400000:SCALP_MOMENTUM_CONTINUATION:SETUP_CANDIDATE:c231ecf12ce98b6e` | `paper:continuous:position:cd11d3fc17a422203b09647c6614e8537ccc66bf1a7e7291e21e5269f17fec2b` | ADAUSDT LONG | UNKNOWN | 2026-09-20 00:51 → 00:57 | STOP_LOSS | -0.114030930 | -30.2388776273 | D(BULLISH)/S/G; eligible |
| 8 | `setup:ADAUSDT:5m:1789871100000:SCALP_MOMENTUM_CONTINUATION:SETUP_CANDIDATE:170d5af69555b8d4` | `paper:continuous:position:849f6890af5acc0f1d18beab6d03198d2e94a519f70debeb054a944250d39c87` | ADAUSDT SHORT | UNKNOWN | 2026-09-20 02:26 → 02:36 | TAKE_PROFIT | 0.082293724 | 62.3298530146 | D(BEARISH)/S/G; eligible |
| 9 | `setup:SOLUSDT:5m:1789874400000:SCALP_MOMENTUM_CONTINUATION:SETUP_CANDIDATE:bf207907425be367` | `paper:continuous:position:fe4519edb01f980d53c930cded2087383c623afffbbc53e759e3b49dfca94ec0` | SOLUSDT SHORT | UNKNOWN | 2026-09-20 03:21 → 03:23 | STOP_LOSS | -0.135734820 | -45.4878742851 | D(BEARISH)/S/G; eligible |
| 10 | `setup:BNBUSDT:5m:1789874700000:SCALP_MOMENTUM_CONTINUATION:SETUP_CANDIDATE:c8f8845f3a0e3fa7` | `paper:continuous:position:f1fcdb3e1e58a4682389fa328f7262f2df02c0bdce4c237457b06ec254378345` | BNBUSDT SHORT | UNKNOWN | 2026-09-20 03:26 → 03:37 | SYSTEM_SAFETY_EXIT | 0.014104872 | 10.4100300462 | D(BEARISH)/S/G; eligible |
| 11 | `setup:DOGEUSDT:5m:1789895100000:SCALP_MOMENTUM_CONTINUATION:SETUP_CANDIDATE:a66c899700c5c6a6` | `paper:continuous:position:3b42a5853da5cc3f7cbea2ac336e6a7cfc66d05549d2a5188197aeb289f9040e` | DOGEUSDT SHORT | UNKNOWN | 2026-09-20 09:06 → 09:17 | SYSTEM_SAFETY_EXIT | -0.013039080 | -9.7177222975 | D(BEARISH)/S/G; eligible |
| 12 | `setup:LINKUSDT:5m:1789895700000:SCALP_MOMENTUM_CONTINUATION:SETUP_CANDIDATE:de19fdf418f103d8` | `paper:continuous:position:16c1f8bbcab1424c0b84e6f71b4765eb0e4e7591f1b1bb348a848d1a698b5fd2` | LINKUSDT SHORT | UNKNOWN | 2026-09-20 09:16 → 09:21 | STOP_LOSS | -0.080127042 | -37.3884468873 | D(BEARISH)/S/G; eligible |
| 13 | `setup:LTCUSDT:5m:1790501100000:SCALP_MOMENTUM_CONTINUATION:SETUP_CANDIDATE:f8dbbd554f902a08` | `paper:continuous:position:326dc5417fc4a4951a20abe1b646e44c0f8715cd659b327802470b7edec3e663` | LTCUSDT SHORT | UNKNOWN | 2026-09-27 09:26 → 09:37 | SYSTEM_SAFETY_EXIT | -0.015566578 | -11.7622867625 | D(BEARISH)/S/G; eligible |
| 14 | `setup:ENAUSDT:5m:1790502000000:SCALP_MOMENTUM_CONTINUATION:SETUP_CANDIDATE:f8fe8c37e8080998` | `paper:continuous:position:d0edf3f7aeb0eedb04c3bba76f4f80b3842781edec38a4f31faa54a31a3d2b51` | ENAUSDT LONG | UNKNOWN | 2026-09-27 09:41 → 09:54 | SYSTEM_SAFETY_EXIT | -0.0582210292 | -47.3540261373 | D(BULLISH)/S/G; eligible |
| 15 | `setup:ADAUSDT:5m:1790509200000:SCALP_MOMENTUM_CONTINUATION:SETUP_CANDIDATE:39993dba61c148c2` | `paper:continuous:position:0cdc93c7bfec099cbe885a2a10d2c780f3fd2b8eba53740a8d7b3c8668075731` | ADAUSDT SHORT | UNKNOWN | 2026-09-27 11:41 → 11:43 | STOP_LOSS | -0.112282370 | -25.4114948616 | D(BEARISH)/S/G; eligible |
| 16 | `setup:AVAXUSDT:5m:1790516100000:SCALP_MOMENTUM_CONTINUATION:SETUP_CANDIDATE:e0f48b5b38539589` | `paper:continuous:position:e6e8571c05e55296707c3301a3da56f0a4a022edb5dc548e828dc7ec137c40ec` | AVAXUSDT SHORT | UNKNOWN | 2026-09-27 13:36 → 13:38 | SYSTEM_SAFETY_EXIT | -0.019124506 | -13.2593653155 | D(BEARISH)/S/G; eligible |
| 17 | `setup:ETHUSDT:5m:1790520300000:SCALP_MOMENTUM_CONTINUATION:SETUP_CANDIDATE:b7f820cec0cf4a8d` | `paper:continuous:position:fe4ca0eaecdf9f2e86e7afafec2d63afc24c91ce62ddf1219583c83048159d3b` | ETHUSDT SHORT | UNKNOWN | 2026-09-27 14:46 → 14:59 | SYSTEM_SAFETY_EXIT | -0.048658432 | -16.4434699810 | D(BEARISH)/S/G; eligible |
| 18 | `setup:LTCUSDT:5m:1790522400000:SCALP_MOMENTUM_CONTINUATION:SETUP_CANDIDATE:3166f9c2894ecfb8` | `paper:continuous:position:c69d7ed1967ab6730e2d13631d756046a40cd18862444233e43cc61f4ad37244` | LTCUSDT LONG | UNKNOWN | 2026-09-27 15:21 → 15:32 | SYSTEM_SAFETY_EXIT | 0.006463122 | 5.2298200141 | D(BULLISH)/S/G; eligible |
| 19 | `setup:AVAXUSDT:5m:1790540400000:SCALP_MOMENTUM_CONTINUATION:SETUP_CANDIDATE:f37067791813184f` | `paper:continuous:position:3a64755a4993793d4d0a9ebc61bfac9cca7247a1a82eaf9994e73e5370f6727f` | AVAXUSDT LONG | FLAT | 2026-09-27 20:21 → 20:23 | STOP_LOSS | -0.085719396 | -53.1511907221 | D(BULLISH)/S/G; eligible |
| 20 | `setup:XRPUSDT:5m:1790544000000:SCALP_MOMENTUM_CONTINUATION:SETUP_CANDIDATE:928620414f7f9289` | `paper:continuous:position:3571e936c5c14e90ebe6f12f56c37b7e68657df38e26672fae5fb483507843eb` | XRPUSDT SHORT | UNKNOWN | 2026-09-27 21:21 → 21:32 | SYSTEM_SAFETY_EXIT | 0.007363390 | 4.7300713362 | D(BEARISH)/S/G; eligible |

Count is exactly 20: 7 positive and 13 negative observations. Production had
73 CLOSED positions total, zero OPEN/CLOSING positions, and zero commands
created after the final authority close at the fresh read.

## D. Bucket/fallback contract

Exact executed implementation:

- `app/engine_paper/scalping_paper_runner.py::_statistics_config` derives the
  candidate cost bucket and normalized regime and supplies candidate identity,
  `parameter_set_id`, and resolved config hash.
- `app/engine_paper/scalping_statistics.py::PostgresPaperOutcomeStatisticsSource._load`
  joins CLOSED position → entry order → command → `trade-5m-v2` run → same-symbol
  result, orders by close time, and deduplicates `position_id`.
- `resolve` reloads PostgreSQL on every call and invokes
  `hierarchy_from_outcomes`; there is no cache or mutable last-bucket state.
- Compatibility filtering first requires the candidate parameter set and
  resolved configuration hash. The hierarchy then evaluates: exact
  `(symbol, setup, direction, normalized regime, cost)` →
  `setup_direction_regime` → `setup_direction` → `setup` → `global`.
- `app/engine_paper/scalping_policy_v2.py::evaluate_expectancy` selects the
  first bucket with at least 20 samples.

The five exact traces collapse into two count patterns:

```text
FET/BNB/DOGE BEARISH: exact 0/0 -> setup_direction_regime 0/0 ->
  setup_direction 14/5 -> setup 20/7 SELECTED -> global 20/7
ETH/XRP BULLISH: exact 0/0 -> setup_direction_regime 0/0 ->
  setup_direction 6/2 -> setup 20/7 SELECTED -> global 20/7
fallback reason = first compatible hierarchy bucket meeting minimum sample 20
```

`bucket_key` always embeds the current candidate symbol/direction/regime/cost,
even at a parent level whose predicate ignores those dimensions. Consequently,
22 exported setup keys name one predicate-selected population. This is a
display/lineage characteristic, not attribution: selection does not compare,
query, cache, or join on that string.

## E. Cross-symbol sharing

```text
CROSS_SYMBOL_SHARING = YES
CROSS_SYMBOL_SHARING_CONTRACT = INTENTIONAL_BY_CONTRACT
```

The selected `setup` predicate is exactly `row.setup_type == setup_type`; it
intentionally ignores symbol, direction, normalized regime, and cost. The
FET/BNB/DOGE/ETH/XRP candidates therefore share observations from SOL, ADA,
LINK, LTC, AVAX, and other symbols. Exact, regime, and direction parents remain
isolated and simply do not reach the minimum sample. No incorrect query scope,
fallback key, cache key, or shared mutable state was found.

## F. FET 03:45 trace

```text
boundary = 2026-09-28T03:45:00Z
effective parameter set = scalping-v2-set-2
resolved config hash = 9d3f604ee4a3b0793bb40ba3cef9826a36e00d945c44e60811cdeede6b1ee7ce
minimum planned RR = 0.476674
minimum net edge bps = 5
gross RR = 6.1113799
net reward = 172.12867503
net risk = 58.57847078
candidate net RR = 2.93842896
candidate break-even win rate = 0.25390835
authority state = ESTABLISHED
sample/wins/losses = 20/7/13
posterior mean with priors 1/1 = 0.36363636363636365
one-sided Wilson lower, confidence 0.85 = 0.2659985292849185
average win/loss net bps = 20.616319467665843 / 32.106007563036805
empirical EV net bps = -18.081946112391396
expected EV R = -0.5631950991380469
required dynamic RR = 2.759419282085097
candidate RR gate = PASS
historical expected_value >= 0 gate = FAIL
expected_ev_r >= min_ev_reserve_r(0) gate = FAIL
bootstrap = DISABLED because authority is established
final result = SCALPING_EMPIRICAL_EXPECTANCY_REJECTED
classification = A. INTENDED_INDEPENDENT_NEGATIVE_EV_VETO
```

The candidate exceeds dynamic required RR, but admission is a conjunction.
Candidate geometry passes its RR comparison; it cannot override the separate
historical-payoff EV and EV-reserve gates. This is the implemented policy, not
a formula or stale-authority defect.

## G. Independent math

The exact 20 raw returns were independently recomputed once:

| Metric | Stored/exported | Recomputed | Absolute difference |
|---|---:|---:|---:|
| Win rate | 0.35 | 0.35 | 0 |
| Posterior mean `(7+1)/(20+2)` | 0.36363636363636365 | 0.36363636363636365 | 0 |
| Wilson lower, 0.85 (`z=1.0364333894937894`) | 0.2659985292849185 | 0.2659985292849185 | 0 |
| Average win net bps | 20.616319467665843 | 20.616319467665843 | <= 7.11e-15 |
| Average loss net bps | 32.106007563036805 | 32.106007563036805 | <= 7.11e-15 |
| EV net bps | -18.08194611239140 | -18.081946112391396 | <= 7.11e-15 |
| Expected EV R | -0.5631950991380469 | -0.5631950991380469 | 0 |
| Dynamic required RR `(1-p)/p` | 2.759419282085097 | 2.759419282085097 | 0 |

`MATH_RECOMPUTE=PASS`; maximum numeric difference is
`7.105427357601002e-15` (floating-point round-off).

## H. Learning deadlock

Authority ingestion paths were traced as follows:

| Path | Classification | Effect |
|---|---|---|
| Unique CLOSED natural PAPER position linked to `trade-5m-v2` | AUTHORITATIVE | Loaded on the next `resolve` if parameter set/config are compatible |
| Shadow/prospective observation | NON_AUTHORITATIVE | Research loader only; explicitly excluded from runtime authority |
| Rejected-candidate hypothetical outcome | NON_AUTHORITATIVE | Never persisted as a PAPER lifecycle outcome |
| Offline replay | NON_AUTHORITATIVE | Research evidence only |
| Bootstrap | DISABLED for this established authority | Bootstrap is admission behavior, not an observation; a later CLOSED bootstrap trade is authoritative only while authority is not established |
| Manual seed | TEST_ONLY | Isolated fixture only |

For the established `SCALP_MOMENTUM_CONTINUATION` setup population, historical
EV remains negative independently of candidate RR. Every candidate fails at
least those independent gates, and established negative authority disables
bootstrap. There are no in-flight positions that could close and update it.
An unrelated setup family could bootstrap but cannot change this setup bucket.

```text
CAN_NEW_AUTHORITATIVE_OBSERVATION_ENTER_WITHOUT_NEW_PAPER_TRADE = NO
CAN_A_NEW_PAPER_TRADE_PASS_CURRENT_EMPIRICAL_GATE = NO
CAN_CURRENT_AUTHORITY_CHANGE_WITHOUT_PASSING_CURRENT_GATE = NO
LEARNING_DEADLOCK = PROVEN
POLICY_DESIGN_CHANGE_REQUIRED = YES
```

The second answer is scoped to candidates governed by this established setup
authority. The third reflects the fresh production state with no open/closing
position. Resolving the lock requires an explicit policy-design decision; this
task was prohibited from inventing that design.

## I. Fix

No permitted implementation defect was proven. The query scope, hierarchy
predicates, selected population, freshness behavior, and calculations match
the code contract. No application file changed and no deployment occurred.

## J. Tests

```text
Focused empirical unit tests:
  26 passed in 8.93s
  tests/engine_paper/test_scalping_statistics.py
  tests/test_scalping_probability_fallback_hierarchy.py
  tests/test_scalping_conservative_probability.py
  tests/test_scalping_dynamic_ev_gate.py
  tests/test_probability_authority_accumulation.py

Isolated PostgreSQL 16 fixture:
  1 passed in 10.45s
  test_production_statistics_exclude_prospective_evidence
  temporary task-owned container and database removed after test

BUCKET_ISOLATION_TEST = PASS
EMPIRICAL_20_OBSERVATION_TEST = PASS
CACHE_IDENTITY_TEST = NOT_APPLICABLE_NO_CACHE
FET_HIGH_RR_NEGATIVE_EV_TEST = PASS
DEADLOCK_MODEL_TEST = POLICY_SELF_LOCK_CONFIRMED
```

The focused model exercised ratios `0.5`, `2.93842896`, `10`, and `100`; all
remain rejected under established negative EV without bootstrap. A repository-
wide suite was intentionally not run because no shared implementation changed.

## K. Invariants and fresh runtime snapshot

```text
PRODUCTION_HISTORY_MUTATED = NO
EMPIRICAL_REQUIRED_SAMPLE_CHANGED = NO
PRIORS_CHANGED = NO
CONFIDENCE_CHANGED = NO
MINIMUM_PLANNED_RR_CHANGED = NO
NEGATIVE_EV_POLICY_CHANGED = NO
BOOTSTRAP_POLICY_CHANGED = NO
STRATEGY_CHANGED = NO
TARGET_CHANGED = NO
STOP_CHANGED = NO
COST_MODEL_CHANGED = NO
COMMISSION_POLICY_CHANGED = NO
RISK_CHANGED = NO
SELECTOR_RANKING_CHANGED = NO
PORTFOLIO_LIMITS_CHANGED = NO
UNIVERSE_CHANGED = NO
ENTRY_WINDOW_CHANGED = NO
TTL_CHANGED = NO
EXIT_POLICY_CHANGED = NO
TRADE_15M_CHANGED = NO
LIVE_CHANGED = NO
LIVE_STATE = DISABLED
REAL_BINANCE_ORDER_CALLS = 0
ALEMBIC = 0035_scalping_v2_ingestion_policy_contract
APPLICATION_DEPLOYMENT = NONE
```

At `2026-09-28T19:24Z`, the read-only health endpoint was operational and
reported market-data and online-orchestrator OK. Paper readiness reported
`mode=PAPER`, `live_allowed=false`, and `LIVE_DISABLED`; it also exposed stale
durability/runtime readiness blockers outside this forensic scope. No mutation
was attempted to alter that state.

