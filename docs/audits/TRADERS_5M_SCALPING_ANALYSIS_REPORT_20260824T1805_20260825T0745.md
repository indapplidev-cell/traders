# TRADERS 5m scalping production analysis report

## Executive summary

- Stable readonly snapshot: 2026-08-24T18:05:00Z through 2026-08-25T07:45:00Z; 165 homogeneous 5m boundaries and 1650 symbol evaluations.
- Sample completeness: 1650/1650 (100.00%); missing boundaries 0, non-exact10 boundaries 0.
- Funnel: 170 setups, 4 strategy admits, 4 geometry passes, 0 final approvals.
- PAPER: opened 0, closed 0, net PnL 0 USDT; no LIVE authority was enabled.
- Main bottleneck: STRUCTURAL_SETUP (1480 losses at that transition).
- Causal candidates: 4; positive measured net edge: 0/4.
- Safety: WAL/PITR True/True, Control ARMED generation 6, LIVE allowed False.
- Expert status: NOT_READY. PASS below means report completeness, not profitability.

## Sample identity

```text
REPORT_FROM = 2026-08-24T18:05:00Z
REPORT_TO = 2026-08-25T07:45:00Z
DURATION = 49500 seconds (165 x 5m boundaries)
TRADE_PROFILE = trade-5m-v1
PARAMETER_SET_ID = trade-5m-v1-runtime-v1-c141aece87c7f6a0
RUNTIME_SOURCE_COMMIT = 6650f5f13e03342613518584633c90b020e945ed
RUNTIME_ARTIFACT_ID = sha256:b3928a801238a21032fa53e1d34fde02a6036e902b41d23182a05aea5e00bee8
PRODUCTION_ALEMBIC_HEAD = 0018_promote_5m_production_search
BOUNDARIES_EXPECTED = 165
BOUNDARIES_ACTUAL = 165
SYMBOL_EVALUATIONS_EXPECTED = 1650
SYMBOL_EVALUATIONS_ACTUAL = 1650
SAMPLE_COMPLETENESS = 100.0000%
HOMOGENEOUS_SAMPLE = YES
STABLE_SNAPSHOT_CLOSED_UNTIL_MS = 1787643900000
KEYSET_PAGES = 9
```

## Data quality

```text
5M_BOUNDARIES = 165
MISSING_BOUNDARIES = 0
DUPLICATE_BOUNDARIES = 0
BOUNDARIES_WITH_NOT_EXACT10 = 0
TOTAL_SYMBOL_EVALUATIONS = 1650
DUPLICATE_RUNS = 0
DUPLICATE_RESULTS = 0
MISSING_RESULTS = 0
CURSOR_OR_DEDUPE_COLLISIONS = 0
5M_SINGLETON_OWNER_COUNT = 1
CLOSED_ONLY_SEMANTICS_VIOLATIONS = 0
FUTURE_LEAKAGE_VIOLATIONS = 0
PROFILE_IDENTITY_VIOLATIONS = 0
15M_5M_MIXING_VIOLATIONS = 0
```

The export remained profile-specific and snapshot-stable across all pages. Higher-timeframe context was accepted only when its closed boundary was at or before the 5m decision boundary.

## Full Funnel

| stage | input_count | pass_count | reject_count | pass_rate_pct | loss_rate_pct |
| --- | --- | --- | --- | --- | --- |
| ANALYSIS | 1650 | 1650 | 0 | 100.0000 | 0.0000 |
| STRUCTURAL_SETUP | 1650 | 170 | 1480 | 10.3030 | 89.6970 |
| STRATEGY_ADMITTED | 170 | 4 | 166 | 2.3529 | 97.6471 |
| GEOMETRY_VALID | 4 | 4 | 0 | 100.0000 | 0.0000 |
| COST_GATE_PASS | 4 | 0 | 4 | 0.0000 | 100.0000 |
| RISK_ADMITTED | 0 | 0 | 0 | null | null |
| PAPER_PLAN_CREATED | 0 | 0 | 0 | null | null |
| VALIDITY_PASS | 0 | 0 | 0 | null | null |
| FINAL_APPROVAL | 0 | 0 | 0 | null | null |
| PAPER_COMMAND | 0 | 0 | 0 | null | null |
| POSITION_OPENED | 0 | 0 | 0 | null | null |
| POSITION_CLOSED | 0 | 0 | 0 | null | null |

### Key conversions

| conversion | rate_pct |
| --- | --- |
| ANALYSIS -> STRUCTURAL_SETUP | 10.3030 |
| STRUCTURAL_SETUP -> STRATEGY_ADMITTED | 2.3529 |
| STRATEGY_ADMITTED -> GEOMETRY_VALID | 100.0000 |
| GEOMETRY_VALID -> COST_GATE_PASS | 0.0000 |
| COST_GATE_PASS -> RISK_ADMITTED | null |
| RISK_ADMITTED -> PAPER_PLAN_CREATED | null |
| PAPER_PLAN_CREATED -> VALIDITY_PASS | null |
| VALIDITY_PASS -> FINAL_APPROVAL | null |
| FINAL_APPROVAL -> PAPER_COMMAND | null |
| PAPER_COMMAND -> POSITION_OPENED | null |
| POSITION_OPENED -> POSITION_CLOSED | null |

Validity is fail-closed: the export has no standalone validity trace node, so only a persisted final approval proves `VALIDITY_PASS`.

## Raw rejection matrix

| reason_code | stage | count | share_of_stage_pct | share_of_all_analyses_pct | symbol_distribution | long_count | short_count |
| --- | --- | --- | --- | --- | --- | --- | --- |
| NO_STRUCTURAL_SETUP | STRUCTURAL_SETUP | 1477 | 89.5152 | 89.5152 | {"ADAUSDT": 164, "AVAXUSDT": 139, "BNBUSDT": 137, "BTCUSDT": 158, "DOGEUSDT": 165, "ETHUSDT": 151, "LINKUSDT": 132, "SOLUSDT": 135, "SUIUSDT": 151, "XRPUSDT": 145} | 0 | 0 |
| STRATEGY_REJECT_WEAK_QUALITY | STRATEGY_ADMITTED | 138 | 81.1765 | 8.3636 | {"ADAUSDT": 1, "AVAXUSDT": 26, "BNBUSDT": 26, "BTCUSDT": 5, "ETHUSDT": 5, "LINKUSDT": 33, "SOLUSDT": 23, "SUIUSDT": 8, "XRPUSDT": 11} | 134 | 4 |
| STRATEGY_REJECT_CONFLICTING_CONTEXT | STRATEGY_ADMITTED | 28 | 16.4706 | 1.6970 | {"BNBUSDT": 2, "BTCUSDT": 2, "ETHUSDT": 9, "SUIUSDT": 6, "XRPUSDT": 9} | 20 | 8 |
| PAPER_REJECT_NEGATIVE_NET_EDGE | COST_GATE_PASS | 4 | 100.0000 | 0.2424 | {"SOLUSDT": 4} | 4 | 0 |
| INVALIDATED_EXISTING_SETUP_IDEA | STRUCTURAL_SETUP | 3 | 0.1818 | 0.1818 | {"SOLUSDT": 3} | 3 | 0 |

Raw stage rejection codes are not merged into synthetic categories. `raw_reason_codes` remain preserved in the stable export but are not all counted as rejections because many are positive/context diagnostics.

```text
RISK_BUDGET_RESERVATION_LEAKS = 0
NO_PLAN_CONSUMED_EXECUTION_QUOTA = 0
PROFILE_QUOTA_CROSS_CONTAMINATION = 0
```

## Slices

### By symbol

| key | analyses | setups | strategy | geometry | cost | risk | approval | positions | conversion % | top rejection |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ADAUSDT | 165 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 | NO_STRUCTURAL_SETUP |
| AVAXUSDT | 165 | 26 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 | NO_STRUCTURAL_SETUP |
| BNBUSDT | 165 | 28 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 | NO_STRUCTURAL_SETUP |
| BTCUSDT | 165 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 | NO_STRUCTURAL_SETUP |
| DOGEUSDT | 165 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 | NO_STRUCTURAL_SETUP |
| ETHUSDT | 165 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 | NO_STRUCTURAL_SETUP |
| LINKUSDT | 165 | 33 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 | NO_STRUCTURAL_SETUP |
| SOLUSDT | 165 | 27 | 4 | 4 | 0 | 0 | 0 | 0 | 0.0000 | NO_STRUCTURAL_SETUP |
| SUIUSDT | 165 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 | NO_STRUCTURAL_SETUP |
| XRPUSDT | 165 | 20 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 | NO_STRUCTURAL_SETUP |

### By LONG / SHORT / NONE

| key | analyses | setups | strategy | geometry | cost | risk | approval | positions | conversion % | top rejection |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LONG | 161 | 158 | 4 | 4 | 0 | 0 | 0 | 0 | 0.0000 | STRATEGY_REJECT_WEAK_QUALITY |
| NONE | 1477 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 | NO_STRUCTURAL_SETUP |
| SHORT | 12 | 12 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 | STRATEGY_REJECT_CONFLICTING_CONTEXT |

### By market regime

| key | analyses | setups | strategy | geometry | cost | risk | approval | positions | conversion % | top rejection |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DOWN | 226 | 12 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 | NO_STRUCTURAL_SETUP |
| FLAT | 453 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 | NO_STRUCTURAL_SETUP |
| UNKNOWN | 425 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 | NO_STRUCTURAL_SETUP |
| UP | 546 | 158 | 4 | 4 | 0 | 0 | 0 | 0 | 0.0000 | NO_STRUCTURAL_SETUP |

### By setup type

| key | analyses | setups | strategy | geometry | cost | risk | approval | positions | conversion % | top rejection |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BREAKOUT_CONTINUATION | 170 | 170 | 4 | 4 | 0 | 0 | 0 | 0 | 0.0000 | STRATEGY_REJECT_WEAK_QUALITY |
| NO_SETUP | 1477 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 | NO_STRUCTURAL_SETUP |
| PULLBACK_CONTINUATION | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 | INVALIDATED_EXISTING_SETUP_IDEA |

### By UTC hour

| key | analyses | setups | strategy | geometry | cost | risk | approval | positions | conversion % | top rejection |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00 | 120 | 12 | 3 | 3 | 0 | 0 | 0 | 0 | 0.0000 | NO_STRUCTURAL_SETUP |
| 01 | 120 | 46 | 1 | 1 | 0 | 0 | 0 | 0 | 0.0000 | NO_STRUCTURAL_SETUP |
| 02 | 120 | 19 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 | NO_STRUCTURAL_SETUP |
| 03 | 120 | 24 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 | NO_STRUCTURAL_SETUP |
| 04 | 120 | 13 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 | NO_STRUCTURAL_SETUP |
| 05 | 120 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 | NO_STRUCTURAL_SETUP |
| 06 | 120 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 | NO_STRUCTURAL_SETUP |
| 07 | 100 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 | NO_STRUCTURAL_SETUP |
| 18 | 110 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 | NO_STRUCTURAL_SETUP |
| 19 | 120 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 | NO_STRUCTURAL_SETUP |
| 20 | 120 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 | NO_STRUCTURAL_SETUP |
| 21 | 120 | 22 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 | NO_STRUCTURAL_SETUP |
| 22 | 120 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 | NO_STRUCTURAL_SETUP |
| 23 | 120 | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 | NO_STRUCTURAL_SETUP |

## Causal stop/target geometry

| symbol | direction | boundary | entry | causal_invalidation | raw_stop | final_stop | target | stop_source | target_source | ATR | ATR_buffer_multiplier | stop_distance_pct | target_distance_pct | gross_rr | geometry_rejection_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SOLUSDT | LONG | 1787618700000 | 98.74 | 98.23 | 98.0554 | 98.0554 | 98.77 | CAUSAL_INVALIDATION_PLUS_ATR | LOCAL_5M | 0.6983 | 0.25 | 0.6933 | 0.0304 | 0.0438 | NONE |
| SOLUSDT | LONG | 1787619000000 | 98.74 | 98.23 | 98.0483 | 98.0483 | 98.77 | CAUSAL_INVALIDATION_PLUS_ATR | LOCAL_5M | 0.7267 | 0.25 | 0.7005 | 0.0304 | 0.0434 | NONE |
| SOLUSDT | LONG | 1787619300000 | 98.74 | 98.23 | 98.0454 | 98.0454 | 98.77 | CAUSAL_INVALIDATION_PLUS_ATR | LOCAL_5M | 0.7383 | 0.25 | 0.7034 | 0.0304 | 0.0432 | NONE |
| SOLUSDT | LONG | 1787619600000 | 98.74 | 98.23 | 98.0434 | 98.0434 | 98.77 | CAUSAL_INVALIDATION_PLUS_ATR | LOCAL_5M | 0.7462 | 0.25 | 0.7055 | 0.0304 | 0.0431 | NONE |

| metric | P10 | P25 | P50 | P75 | P90 |
| --- | --- | --- | --- | --- | --- |
| STOP_DISTANCE_BPS | 69.5471 | 69.8699 | 70.197 | 70.3948 | 70.485 |
| TARGET_DISTANCE_BPS | 3.0383 | 3.0383 | 3.0383 | 3.0383 | 3.0383 |
| GROSS_RR | 0.0431 | 0.0432 | 0.0433 | 0.0435 | 0.0437 |

```text
CAUSAL_STOP_TOO_WIDE_COUNT = 0
MISSING_CAUSAL_STOP_COUNT = 0
MISSING_TARGET_COUNT = 0
LOCAL_5M_TARGET_COUNT = 4
STRUCTURAL_TARGET_COUNT = 0
HIGHER_TF_TARGET_COUNT = 0
STOP_CLIPPED_INSIDE_CAUSAL_INVALIDATION = 0
```

## Geometry cohorts (same causal opportunities)

### ATR buffer

| ATR | candidates | causal_valid | stop_P50_bps | stop_P90_bps | target_P50_bps | target_P90_bps | gross_RR_P50 | net_RR_P50 | net_cost_pass | final_eligible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.25 | 4 | 4 | 70.197 | 70.485 | 3.0383 | 3.0383 | 0.0433 | null | 0 | 0 |
| 0.5 | 4 | 4 | 88.7432 | 89.3192 | null | null | null | null | 0 | 0 |
| 0.75 | 4 | 4 | 107.2893 | 108.1534 | null | null | null | null | 0 | 0 |
| 1.0 | 4 | 4 | 125.8355 | 126.9875 | null | null | null | null | 0 | 0 |

### Stop envelope

| envelope_bps | candidates | causal_valid | stop_P50_bps | stop_P90_bps | target_P50_bps | target_P90_bps | gross_RR_P50 | net_RR_P50 | net_cost_pass | final_eligible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 50.0 | 4 | 4 | 70.197 | 70.485 | null | null | null | null | 0 | 0 |
| 65.0 | 4 | 4 | 70.197 | 70.485 | null | null | null | null | 0 | 0 |
| 80.0 | 4 | 4 | 70.197 | 70.485 | 3.0383 | 3.0383 | 0.0433 | null | 0 | 0 |

### Minimum target diagnostic

| minimum_target_bps | candidates | causal_valid | stop_P50_bps | stop_P90_bps | target_P50_bps | target_P90_bps | gross_RR_P50 | net_RR_P50 | net_cost_pass | final_eligible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 45.0 | 4 | 4 | 70.197 | 70.485 | 3.0383 | 3.0383 | 0.0433 | null | 0 | 0 |
| 60.0 | 4 | 4 | 70.197 | 70.485 | 3.0383 | 3.0383 | 0.0433 | null | 0 | 0 |
| 80.0 | 4 | 4 | 70.197 | 70.485 | 3.0383 | 3.0383 | 0.0433 | null | 0 | 0 |

Cohorts preserve causal geometry, target validity, costs, risk/validity ordering, and the unchanged production RR floor of 1.5; no configuration is selected by signal count.

## Costs

| symbol | boundary | entry_fee_bps | exit_fee_bps | spread_bps | entry_slippage_bps | exit_slippage_bps | depth_impact_bps | safety_margin_bps | total_cost_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SOLUSDT | 1787618700000 | 10 | 10 | 0.9785 | 2 | 2 | 0.4211 | 3 | 28.3997 |
| SOLUSDT | 1787619000000 | 10 | 10 | 0.985 | 2 | 2 | 0 | 3 | 27.985 |
| SOLUSDT | 1787619300000 | 10 | 10 | 0.9798 | 2 | 2 | 0 | 3 | 27.9798 |
| SOLUSDT | 1787619600000 | 10 | 10 | 0.9812 | 2 | 2 | 0 | 3 | 27.9812 |

```text
SPREAD_BPS_P50 = 0.9805
SPREAD_BPS_P90 = 0.9838
DEPTH_IMPACT_BPS_P50 = 0
DEPTH_IMPACT_BPS_P90 = 0.2948
TOTAL_COST_BPS_P50 = 27.9831
TOTAL_COST_BPS_P90 = 28.2753
TOTAL_COST_BPS_MAX = 28.3997
MISSING_MANDATORY_COST_DATA = 0
```

Missing mandatory costs remain null and fail closed; they are never replaced by zero.

## Gross RR / Net RR

| symbol | boundary | gross_target_pct | stop_distance_pct | gross_rr | total_cost_pct | net_reward_pct | net_risk_pct | net_rr | expected_net_edge_bps | break_even_win_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SOLUSDT | 1787618700000 | 0.0304 | 0.6933 | 0.0438 | 0.284 | -0.2536 | 0.9773 | null | -25.3614 | null |
| SOLUSDT | 1787619000000 | 0.0304 | 0.7005 | 0.0434 | 0.2798 | -0.2495 | 0.9803 | null | -24.9467 | null |
| SOLUSDT | 1787619300000 | 0.0304 | 0.7034 | 0.0432 | 0.2798 | -0.2494 | 0.9832 | null | -24.9415 | null |
| SOLUSDT | 1787619600000 | 0.0304 | 0.7055 | 0.0431 | 0.2798 | -0.2494 | 0.9853 | null | -24.9429 | null |

```text
GROSS_RR_P50 = 0.0433
NET_RR_P50 = null
EXPECTED_NET_EDGE_BPS_P50 = -24.9448
BREAK_EVEN_WIN_RATE_P50 = null
```

## RR cohorts

| RR | gross_pass_count | net_cost_pass_count | final_eligible_count | paper_trade_count | win_count | loss_count | win_rate | profit_factor | net_expectancy | net_pnl |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1.0 | 0 | 0 | 0 | 0 | 0 | 0 | null | null | null | 0 |
| 1.2 | 0 | 0 | 0 | 0 | 0 | 0 | null | null | null | 0 |
| 1.5 | 0 | 0 | 0 | 0 | 0 | 0 | null | null | null | 0 |

## PAPER performance

```text
PAPER_OPENED = 0
PAPER_CLOSED = 0
PAPER_WIN_COUNT = 0
PAPER_LOSS_COUNT = 0
PAPER_BREAKEVEN_COUNT = 0
PAPER_WIN_RATE = 0
PAPER_GROSS_PNL = 0
PAPER_TOTAL_FEES = 0
PAPER_ESTIMATED_SPREAD_COST = null
PAPER_SLIPPAGE_COST = null
PAPER_NET_PNL = 0
PAPER_PROFIT_FACTOR = null
PAPER_AVG_WIN = null
PAPER_AVG_LOSS = null
PAPER_PAYOFF_RATIO = null
PAPER_NET_EXPECTANCY_PER_TRADE = null
HOLDING_TIME_P50 = null
HOLDING_TIME_P90 = null
MFE_P50 = null
MFE_P90 = null
MAE_P50 = null
MAE_P90 = null
```

No strong PAPER-economics inference is made when the closed-trade sample is small or zero.

## Opportunity churn

```text
RAW_CANDIDATES = 4
UNIQUE_CAUSAL_OPPORTUNITIES = 1
REPEAT_OBSERVATIONS = 3
REPEAT_RATE = 75.0000
```

Opportunity identity uses symbol + direction + setup identity + causal invalidation + target identity with consecutive-5m continuity.

## 15m non-regression

```text
15M_SEARCH_CONTINUITY = PASS
15M_MISSING_BOUNDARIES = 0
15M_DUPLICATE_BOUNDARIES = 0
15M_BATCH_SIZE_ANOMALIES = 0
15M_PARAMETERIZATION_CHANGED = NO
15M_PRODUCTION_BEHAVIOR_CHANGED = NO
15M_BOUNDARIES_OBSERVED = 55
15M_SYMBOL_EVALUATIONS = 550
15M_STABLE_SNAPSHOT = 1787643900000
```

## Safety snapshot

```text
WAL_READY = true
PITR_READY = true
ACTIVE_UNRESOLVED_FAILURES = 0
EXPORT_BACKLOG = 0
PENDING_ARCHIVE_STATUS = 0
PHYSICAL_WAL_GAP = false
CONTROL_STATE = ARMED
CONTROL_GENERATION = 6
LIVE_STATE = DISABLED
5M_SINGLETON_OWNER_COUNT = 1
```

## EXPERT ASSESSMENT

1. Главный Funnel bottleneck — `STRUCTURAL_SETUP`: потеряно 1480 из 1650 входов.
2. Stop geometry наблюдалась на 4 causal candidates; median/P90 = 70.197/70.485 bps, clip-inside violations = 0. При нулевой/малой выборке адекватность не доказана.
3. Target median/P90 = 3.0383/3.0383 bps; достижимость без достаточной PAPER outcome sample не доказана.
4. Target hierarchy: LOCAL_5M=4, STRUCTURAL=0, HIGHER_TF=0.
5. ATR cohorts показывают geometry pass/final eligible от 4/0 при 0.25 до 4/0 при 1.00; economics нельзя выбирать по объёму сигналов.
6. Положительный measured net edge: 0/4 causal candidates (0.0000%).
7. Median break-even win rate = null; если null, обязательная economic sample отсутствует.
8. RR gross/net passes: 1.0=0/0, 1.2=0/0, 1.5=0/0.
9. Преждевременное расходование quota: reservation leaks=0, no-plan consumed quota=0; ожидаемое 0 подтверждено=True.
10. LONG/SHORT, symbol, regime и UTC-hour bias приведены в slices; при малом causal/PAPER sample статистический bias не заявляется.
11. Opportunity churn: repeats=3/4, rate=75.0000%.
12. Положительная PAPER economics не доказана: closed trades=0, net PnL=0 USDT.

SCALPING_SUITABILITY = NOT_READY

## Recommendations

### KEEP

- Сохранять closed-only, exact10, profile isolation и fail-closed costs: violations/missing/duplicates = 0/0/0.
- Сохранять post-plan quota semantics: reservation leaks=0, consumed-on-no-plan=0.

### SHADOW_TEST_NEXT

- Продолжить SHADOW observation до появления достаточной causal sample; сейчас causal candidates=4, closed PAPER trades=0.
- Сравнивать ATR/RR cohorts на тех же opportunities; текущие RR 1.0/1.2/1.5 net passes=0/0/0.

### REJECT

- Отклонить production tuning по этому отчёту: closed trades=0, profitability confidence insufficient.
- Отклонить замену unknown mandatory costs нулями: missing mandatory cost candidate rows=0.

### INSUFFICIENT_EVIDENCE

- Недостаточно данных для profitability, stop/target outcome и bias conclusions: causal=4, closed=0.
- Недостаточно данных для выбора ATR buffer или RR threshold: same-opportunity cohort size=4.

## Machine-readable footer

```text
TASK_STATUS = PASS
FINAL_VERDICT = PASS_COMPLETE_REPRODUCIBLE_HOMOGENEOUS_READONLY_REPORT
REPORT_FROM = 2026-08-24T18:05:00Z
REPORT_TO = 2026-08-25T07:45:00Z
REPORT_DURATION = 49500 seconds (165 x 5m boundaries)
TRADE_PROFILE = trade-5m-v1
PARAMETER_SET_ID = trade-5m-v1-runtime-v1-c141aece87c7f6a0
HOMOGENEOUS_SAMPLE = YES
5M_BOUNDARIES = 165
5M_MISSING_BOUNDARIES = 0
5M_DUPLICATE_BOUNDARIES = 0
5M_SYMBOL_EVALUATIONS = 1650
5M_ANALYSES = 1650
5M_STRUCTURAL_SETUPS = 170
5M_STRATEGY_ADMITTED = 4
5M_GEOMETRY_VALID = 4
5M_COST_GATE_PASS = 0
5M_RISK_ADMITTED = 0
5M_PAPER_PLANS = 0
5M_FINAL_APPROVALS = 0
5M_PAPER_COMMANDS = 0
5M_POSITIONS_OPENED = 0
5M_POSITIONS_CLOSED = 0
TOP_REJECTION_REASON_1 = NO_STRUCTURAL_SETUP
TOP_REJECTION_REASON_2 = STRATEGY_REJECT_WEAK_QUALITY
TOP_REJECTION_REASON_3 = STRATEGY_REJECT_CONFLICTING_CONTEXT
STOP_DISTANCE_P50 = 70.197
STOP_DISTANCE_P90 = 70.485
TARGET_DISTANCE_P50 = 3.0383
TARGET_DISTANCE_P90 = 3.0383
SPREAD_BPS_P50 = 0.9805
SPREAD_BPS_P90 = 0.9838
TOTAL_COST_BPS_P50 = 27.9831
TOTAL_COST_BPS_P90 = 28.2753
GROSS_RR_P50 = 0.0433
NET_RR_P50 = null
EXPECTED_NET_EDGE_BPS_P50 = -24.9448
BREAK_EVEN_WIN_RATE_P50 = null
RR_1_0_GROSS_PASS = 0
RR_1_0_NET_PASS = 0
RR_1_2_GROSS_PASS = 0
RR_1_2_NET_PASS = 0
RR_1_5_GROSS_PASS = 0
RR_1_5_NET_PASS = 0
PAPER_WIN_COUNT = 0
PAPER_LOSS_COUNT = 0
PAPER_WIN_RATE = 0
PAPER_PROFIT_FACTOR = null
PAPER_NET_EXPECTANCY = null
PAPER_NET_PNL = 0
RAW_CANDIDATES = 4
UNIQUE_CAUSAL_OPPORTUNITIES = 1
REPEAT_OBSERVATIONS = 3
RISK_BUDGET_RESERVATION_LEAKS = 0
WAL_READY = true
PITR_READY = true
CONTROL_STATE = ARMED
LIVE_STATE = DISABLED
SCALPING_SUITABILITY = NOT_READY
PROFITABILITY_CONFIDENCE = INSUFFICIENT_SAMPLE
KEEP_RECOMMENDATIONS = 2
SHADOW_TEST_NEXT_RECOMMENDATIONS = 2
REJECT_RECOMMENDATIONS = 2
INSUFFICIENT_EVIDENCE = 2
PRODUCTION_5M_PARAMETER_CHANGES_BY_TASK = 0
PRODUCTION_15M_PARAMETER_CHANGES_BY_TASK = 0
PRODUCTION_TRADING_MUTATIONS_BY_TASK = 0
BINANCE_ORDER_API_CALLS_BY_TASK = 0
REPORT_FILE = D:\disk_E\game_projects\traders\evidence_inbox\TRADERS_5M_SCALPING_ANALYSIS_REPORT_20260824T1805_20260825T0745.md
REPORT_SHA256 = 57854de94be5255882bd7e60e2bd508d2166afd89295af8851de1249efccaba5
REPORT_SHA256_SCOPE = UTF8_BYTES_BEFORE_MACHINE_READABLE_FOOTER
PUSHED = NO
```
