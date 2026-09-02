# TRADERS_SCALPING_POLICY_INDEPENDENT_PROFILE_REDESIGN_01

Reconciled at `2026-09-02T17:18:10Z`.

## Verdict

```text
TASK_STATUS = COMPLETED_WITH_NO_PROMOTION_AFTER_REAL_POLICY_REDESIGN
FINAL_VERDICT = NO_PROMOTION_NEW_INDEPENDENT_POLICY_NEGATIVE_ON_CALIBRATION_VALIDATION_AND_HOLDOUT

SCALPING_PROFILE_ID_BEFORE = trade-5m-v1
SCALPING_PROFILE_ID_AFTER = trade-5m-v2_RESEARCH_CANDIDATE_NOT_DEPLOYED
SCALPING_PROFILE_INDEPENDENT = PASS_SOURCE_PERSISTENCE_READONLY_AND_POSTGRES_E2E

TRADE_15M_VERSION_BEFORE = trade-15m-v1-runtime-v1-44aa91202a60146c
TRADE_15M_VERSION_AFTER = trade-15m-v1-runtime-v1-44aa91202a60146c
TRADE_15M_CONFIG_CHANGED = NO
TRADE_15M_CODE_PATH_CHANGED = NO_SEMANTIC_BRANCH_CHANGE
TRADE_15M_BEHAVIOR_CHANGED = NO
TRADE_15M_REGRESSION = PASS

OLD_POLICY_FAMILY_RESULT = REJECTED_648_CONFIGURATIONS_ZERO_PROMOTABLE
SCALPING_POLICY_REDESIGNED = PASS_IMPLEMENTED_AND_REPLAYED_NOT_PROMOTED
```

The 15m profile/runtime serialization is frozen by a regression digest:
`e48878b06f3ea1bf26a5b3dad67bdf41bb7ea50470cd5789b935f568fa94425b`.
The implementation adds a new registry identity and Scalping-only branches;
it does not change the serialized `trade-15m-v1` profile or runtime parameter
identity.

## Policy change

```text
SETUP_POLICY_BEFORE = scalping-setup-families-v1_LEGACY_STRUCTURAL_CLASSIFIER
SETUP_POLICY_AFTER = scalping-micro-setup-v2_MICRO_MOMENTUM_BREAKOUT_AND_LOCAL_EXTREME_RESEARCH_FAMILY

ENTRY_POLICY_BEFORE = confirmation_or_reference_closed_5m_candle
ENTRY_POLICY_AFTER = scalping-next-closed-1m-entry-v2_ONE_COMPLETE_POST_DECISION_1M_CANDLE

STOP_POLICY_BEFORE = LOCAL_INVALIDATION_STRUCTURE_WITH_VOLATILITY_BUFFER_ENVELOPE80BPS
STOP_POLICY_AFTER = scalping-causal-volatility-stop-v2_MICRO_INVALIDATION_PLUS_ATR_BUFFER_ENVELOPE50BPS

TARGET_POLICY_BEFORE = CAUSAL_HIERARCHY_COST_AWARE_NET_RR_V3
TARGET_POLICY_AFTER = scalping-nearest-viable-target-v3_LOCAL_RANGE_OR_ATR_RELATIVE_COST_AWARE_TARGET

RR_POLICY_BEFORE = scalping-required-net-rr-v2_STATIC1.5
RR_POLICY_AFTER = scalping-empirical-ev-v1_DYNAMIC_COHORTS0.2_0.4_WITH0.4_STATIC_FALLBACK

EV_POLICY_BEFORE = NONE
EV_POLICY_AFTER = LAPLACE_SMOOTHED_EMPIRICAL_SETUP_DIRECTION_BUCKET_MIN20_SAMPLES_NET_OF_COSTS

TTL_POLICY_BEFORE = ENTRY60_SECONDS_TIME_STOP30_MINUTES
TTL_POLICY_AFTER = ENTRY30_SECONDS_TIME_STOP15_MINUTES
```

Every v2 PAPER candidate persists the profile, setup, entry, stop, target,
RR/EV, cost, TTL, and risk policy versions. When a setup/direction bucket has
fewer than 20 historical samples, the policy does not invent a probability and
uses its stricter static net-RR fallback.

Costs were not reduced: both replays include 20 bps round-trip fees, 4 bps
round-trip slippage, the existing 3 bps safety margin, and observed median
spread/depth impact by symbol. Risk per trade remains 10 bps, total open risk
remains capped at 50 bps, v2 concurrent positions are reduced from 3 to 2, and
v2 research pre-approvals are capped at 3/symbol, 6/direction, and 10/day.

## Replay evidence

The first new-policy replay reinterpreted 543 fully replayable outcomes from
636 outcomes / 8,140 observations over 3,456 semantic configurations. It found
zero calibration and validation survivors. Because those outcomes were
collected under v1 setup admission, a second independent candle-level replay
rebuilt setup admission directly from closed 5m candles and used the next
closed 1m candle for entry.

The candle replay covered ten symbols and six dates across calibration,
validation, and holdout. It searched 576 configurations across breakout,
momentum and local-extreme reversion setups, ATR stop choices, cost-aware target
hierarchies through 2 ATR, static/empirical EV gates, dynamic RR, and 5/10/15
minute holding horizons. Holdout was never used for selection.

No configuration passed the calibration promotion gate. The best rejected
calibration configuration was evaluated unchanged on validation and holdout for
diagnostic evidence only:

| Split | Plan PAPER/h | Expectancy/trade | Expectancy/h | PF | Win rate | Max DD | Max loss streak |
|---|---:|---:|---:|---:|---:|---:|---:|
| Calibration | 43.7917 | -21.8358 bps | -956.2255 bps | 0.2431 | 20.46% | 22,949.4123 bps | 34 |
| Validation | 26.9583 | -29.7013 bps | -800.6973 bps | 0.0237 | 7.88% | 19,216.7351 bps | 76 |
| Holdout | 39.4722 | -25.9001 bps | -1,022.3355 bps | 0.1210 | 18.37% | 73,608.1567 bps | 51 |

```text
BASELINE_OPPORTUNITIES_PER_HOUR = CALIBRATION1.4022_VALIDATION0.2917_HOLDOUT0.1319
AFTER_OPPORTUNITIES_PER_HOUR = CALIBRATION43.7917_VALIDATION26.9583_HOLDOUT39.4722_DIAGNOSTIC_REJECTED

BASELINE_PLAN_PAPER_PER_HOUR = NATURAL_WINDOW0.25
AFTER_PLAN_PAPER_PER_HOUR = CALIBRATION43.7917_VALIDATION26.9583_HOLDOUT39.4722_DIAGNOSTIC_REJECTED

BASELINE_EXPECTANCY_PER_TRADE = CALIBRATION-21.2349_VALIDATION-33.6032_HOLDOUT-42.0828_BPS
AFTER_EXPECTANCY_PER_TRADE = CALIBRATION-21.8358_VALIDATION-29.7013_HOLDOUT-25.9001_BPS

BASELINE_EXPECTANCY_PER_HOUR = CALIBRATION-29.7751_VALIDATION-9.8009_HOLDOUT-5.5494_BPS
AFTER_EXPECTANCY_PER_HOUR = CALIBRATION-956.2255_VALIDATION-800.6973_HOLDOUT-1022.3355_BPS

BASELINE_PROFIT_FACTOR = CALIBRATION0.3440_VALIDATION0_HOLDOUT0
AFTER_PROFIT_FACTOR = CALIBRATION0.2431_VALIDATION0.0237_HOLDOUT0.1210

BASELINE_MAX_DRAWDOWN = CALIBRATION931.4258_VALIDATION235.2221_HOLDOUT462.9110_BPS
AFTER_MAX_DRAWDOWN = CALIBRATION22949.4123_VALIDATION19216.7351_HOLDOUT73608.1567_BPS

BASELINE_WIN_RATE = CALIBRATION20.93PCT_VALIDATION0PCT_HOLDOUT0PCT
AFTER_WIN_RATE = CALIBRATION20.46PCT_VALIDATION7.88PCT_HOLDOUT18.37PCT

CALIBRATION_RESULT = FAIL_ZERO_OF576_PROMOTABLE
VALIDATION_RESULT = COMPLETED_DIAGNOSTIC_FAIL_NEGATIVE_EXPECTANCY_PF_BELOW1
HOLDOUT_RESULT = COMPLETED_DIAGNOSTIC_FAIL_NEGATIVE_EXPECTANCY_PF_BELOW1_NOT_USED_FOR_SELECTION
```

The new family solves frequency but not net economics. It therefore cannot be
promoted or deployed, and the old profile is not reinstated as the new model.

## Verification and runtime state

```text
SCOPED_REGRESSION = 1687_PASSED_12_SKIPPED
PROFILE_15M_ISOLATION_REGRESSION = 15_PASSED
POSTGRES_E2E = PASS_8_TESTS_POSTGRES16_SCHEMA0021_POSITIVE_V1_POSITIVE_V2_AND_V2_REJECT
COMPILE = PASS
DIFF_CHECK = PASS

FULL_LEGACY_SUITE = NOT_GREEN_PREEXISTING_HISTORICAL_SCHEMA_HEAD_ASSERTIONS
FULL_LEGACY_SUITE_FIRST_RUN = 467_PASSED_23_SKIPPED_THEN_EXPECTED0014_VS_ACTUAL0019_FAILURE
FULL_LEGACY_SUITE_SECOND_RUN = 2680_PASSED_24_SKIPPED_THEN_EXPECTED0014_VS_ACTUAL0015_FAILURE

PROJECT_STATE_COMMIT = c93693d815d3951ce40676aa21dc35435e1d34ce
SERVER_HEAD = c93693d815d3951ce40676aa21dc35435e1d34ce_LOCAL_NOT_PUSHED
DEPLOYED_COMMIT = daa8312eabeb632937b7d7d09b8c33b73b6cb0a7_LAST_EVIDENCED_SCALPING_RUNTIME
DEPLOYED_IMAGE = sha256:b0c8da13af68dcbdffc557362bf8568194ab15dac4f967101ec2d50dbf2be4d6
SCHEMA_HEAD = SOURCE0021_PRODUCTION0020
ACTIVE_5M_PROFILE = trade-5m-v1
DEPLOYMENT = NOT_PERFORMED_NEGATIVE_OUT_OF_SAMPLE_ECONOMICS

LIVE_STATE_AFTER = DISABLED_LIVE_ALLOWED_FALSE_CONTROL_ARMED_PAPER_ONLY
BINANCE_ORDER_API_CALLS_BY_TASK = 0
SECRET_OUTPUT = 0
```

Fresh runtime evidence at reconciliation: production schema is
`0020_paper_plan_execution_outcomes`; the 5m container command still selects
`trade-5m-v1`; readiness is `READY`, mode is `PAPER`, `live_allowed=false`, and
the bounded control remains `ARMED` waiting for an eligible PAPER approval with
zero commands and zero positions. The task did not mutate that control state.
The task-owned PostgreSQL 16 E2E container and its ephemeral database were
removed after verification.

```text
NATURAL_PAPER_VALIDATION = NOT_STARTED_V2_NOT_DEPLOYED
REMAINING_BLOCKERS = NEGATIVE_CALIBRATION_VALIDATION_HOLDOUT_ECONOMICS; EMPIRICAL_BUCKET_RUNTIME_FEED_NOT_PROMOTABLE; DAILY_REALIZED_LOSS_STREAK_COOLDOWN_NOT_INTEGRATED
NEXT_ACTION = KEEP_trade-5m-v2_UNDEPLOYED; DESIGN_A_NEW_CAUSAL_EDGE_SOURCE_OR_SETUP_FAMILY; REPLAY_WITH_THE_SAME_LOCKED_COST_AND_HOLDOUT_PROTOCOL; DEPLOY_PAPER_ONLY_AFTER_POSITIVE_OOS
```

Evidence:

- `TRADERS_SCALPING_POLICY_INDEPENDENT_PROFILE_REDESIGN_01_REPLAY.json`
- `TRADERS_SCALPING_POLICY_INDEPENDENT_PROFILE_REDESIGN_01_CANDLE_REPLAY.json`

