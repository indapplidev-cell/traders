# TRADERS_SCALPING_RISK_UNSUPPORTED_STRATEGY_TYPE_CONTRACT_REMEDIATION_01

## Verdict

```text
TASK_STATUS = COMPLETED
FINAL_VERDICT = PASS_TRADERS_SCALPING_RISK_UNSUPPORTED_STRATEGY_TYPE_CONTRACT_REMEDIATION_01_COMPLETED
BLOCKER_CODE = NONE
SECONDARY_BLOCKER = NONE
STOP_CONDITION = NONE
SERVER_HEAD_BEFORE = b25fce0591d6bb9b2d041311a118a813b158807f
IMPLEMENTATION_COMMIT = c30dd05ab55a102f787be3e9ec1fac6c78d71619
COLLECTOR_BINDING_COMMIT = 0c67b2f90c0d6573bcbcc645961522ce3e0f9b0c
PRODUCTION_ALEMBIC_HEAD = 0018_promote_5m_production_search
SCALPING_PROFILE_ID = trade-5m-v1
SCALPING_PARAMETER_SET_ID = trade-5m-v1-runtime-v1-87b8a882d06b3539
```

## Root cause and reproduction

The production-shaped fixture used profile `trade-5m-v1`, setup
`SCALP_BREAKOUT`, strategy `SCALP_BREAKOUT_RESEARCH`, status
`ALLOW_RESEARCH_TRADE_PLAN`, score `82`, quality `ACCEPTABLE`. Before the fix,
`RiskPolicy._evaluate` compared that code with the global
`RiskConfig.allowed_strategy_types` containing only
`BREAKOUT_CONTINUATION_RESEARCH` and `TREND_CONTINUATION_RESEARCH`; the terminal
result was `REJECT/RISK_REJECT_UNSUPPORTED_STRATEGY_TYPE`, with zero reservation.

```text
DEFECT_REPRODUCED = YES
DEFECT_ROOT_CAUSE_PROVEN = YES
ROOT_CAUSE_CLASS = B_LEGACY_15M_ONLY_ALLOWLIST
ROOT_CAUSE_SOURCE_LOCATIONS = app/engine_risk/risk_config.py:17-20;app/engine_risk/risk_policy.py:100_PRE_FIX;app/engine_strategy/strategy_type.py:6-30;app/engine_orchestrator/trade_profile.py:129-130
```

## Complete type inventory

| Layer | Scalping codes |
|---|---|
| Setup/domain | `SCALP_TREND_PULLBACK`, `SCALP_BREAKOUT`, `SCALP_BREAKOUT_RETEST`, `SCALP_RANGE_BOUNCE`, `SCALP_LIQUIDITY_SWEEP`, `SCALP_MOMENTUM_CONTINUATION`, `SCALP_COMPRESSION_BREAK` |
| Strategy/persisted machine code | the same seven codes with `_RESEARCH` suffix |
| Strategy decision status | `ALLOW_RESEARCH_TRADE_PLAN`, `REJECT`, `WAIT`, `NO_DECISION`, `ERROR` |
| Legacy 15m Strategy codes | `TREND_CONTINUATION_RESEARCH`, `BREAKOUT_CONTINUATION_RESEARCH`, `PULLBACK_CONTINUATION_RESEARCH`, `RANGE_REJECTION_RESEARCH`, `FALSE_BREAKOUT_REVERSAL_RESEARCH`, `MOMENTUM_EXHAUSTION_RESEARCH`, `NO_STRATEGY` |
| Risk-supported 15m codes | `TREND_CONTINUATION_RESEARCH`, `BREAKOUT_CONTINUATION_RESEARCH` (unchanged) |
| Public/i18n | setup machine codes remain server-catalogued RU/EN; no reason code or client-local map changed |

`SETUP_TO_STRATEGY_TYPE` remains the authoritative setup-to-strategy alias map.
The new immutable registry is keyed by `(profile_id, trade_mode)` and contains
exactly two 15m codes and seven Scalping codes. Invalid profile/mode pairs,
unknown future codes, invalid values, 15m-on-Scalping and Scalping-on-15m all
fail closed.

```text
SCALPING_STRATEGY_TYPE_INVENTORY_COMPLETE = YES
RISK_SUPPORTED_TYPE_INVENTORY_COMPLETE = YES
KNOWN_SCALPING_TYPES_COUNT = 7
KNOWN_SCALPING_TYPES_SUPPORTED_COUNT = 7
KNOWN_SCALPING_TYPES_SUPPORTED = YES
UNKNOWN_STRATEGY_TYPE_FAIL_CLOSED = YES
```

## Contract and Risk invariants

The only semantic change is bounded type compatibility in Risk and the
immediately following Scalping Paper/Geometry type gate. Numeric configuration,
quotas, account authority, preview/reservation ordering, geometry, target,
cost, RR, TTL and time-stop values were not changed. Preview remains
side-effect-free; reservation remains after a valid economic plan and is still
performed by the authoritative Risk evaluation.

```text
RISK_POLICY_NUMERIC_THRESHOLDS_CHANGED_BY_TASK = NO
RISK_ACCOUNT_AUTHORITY_CHANGED_BY_TASK = NO
RISK_HARD_LIMITS_PRESERVED = YES
RISK_REJECTION_PATHS_PRESERVED = YES
RISK_BUDGET_RESERVATION_LEAKS = 0
TRADE_15M_PRODUCTION_BEHAVIOR_CHANGED_BY_TASK = NO
15M_RISK_SEMANTIC_EQUIVALENCE = PASS
SCALPING_PARAMETER_PROMOTION_BY_TASK = NO
```

## Isolated and natural production acceptance

The deterministic matrix proved all seven known Scalping types through
Strategy -> Risk preview -> Geometry -> Net Cost -> RR -> authoritative Risk.
Unknown/invalid/wrong-profile combinations rejected. Low score and quota
rejections remained active, preview consumed zero slots, and authoritative
evaluation consumed exactly one idempotent slot.

The old collector segment continued until the exact deployment boundary, so
its authoritative final pre-change snapshot is newer than the incoming 2240
snapshot:

```text
OLD_SEGMENT = scalping-calibration-segment-a7245351ff4a18b81d644e39
OLD_SEGMENT_LAST_BOUNDARY = 1787850000000
OLD_SEGMENT_EVALUATIONS = 2320
OLD_SEGMENT_STRATEGY_ADMITTED = 261
OLD_SEGMENT_UNSUPPORTED = 261
OLD_SEGMENT_GEOMETRY_REACHED = 0
OLD_SEGMENT_APPLICABLE_MICROSTRUCTURE = 294_OF_294_100_PERCENT
```

One 5m container and one technically required collector container were replaced
once. PostgreSQL, Market Data, 15m, Readonly and Control container identities
were unchanged. The new segment did not backfill old decisions. Three
consecutive natural 5m boundaries and the concurrent natural 15m boundary at
`1787850900000` produced exact ten-symbol batches.

```text
NEW_SEGMENT = scalping-calibration-segment-d8a498357af94ae584b3b691
NEW_SEGMENT_DECISION_SEMANTICS = scalping-risk-type-contract-v2
NEW_SEGMENT_EVALUATIONS = 30
STRATEGY_ADMITTED_POST_REMEDIATION = 1
ADMITTED_TYPE = SCALP_BREAKOUT_RESEARCH
RISK_REJECT_UNSUPPORTED_STRATEGY_TYPE_AFTER = 0
KNOWN_SCALPING_UNSUPPORTED_TYPE_REJECT_COUNT = 0
GEOMETRY_REACHED_POST_REMEDIATION = 1
GEOMETRY_VALID_POST_REMEDIATION = 0
TARGET_VALID_POST_REMEDIATION = 0
NET_COST_PASS_POST_REMEDIATION = 0
RR_PASS_POST_REMEDIATION = 0
RISK_COMPATIBILITY_ADMITTED_POST_REMEDIATION = 1
TERMINAL_STAGE_FOR_ADMITTED = REJECT_REAL_GEOMETRY_PATH
```

Zero downstream positives after Geometry are valid natural outcomes for this
small sample; the stages are observable and no longer systemically unavailable
because of type mismatch.

## Collector, safety, performance and tests

```text
OLD_SEGMENT_PRESERVED = YES_2320_OBSERVATIONS_232_DIAGNOSTICS_283_OUTCOMES
NEW_SEGMENT_STARTED_AFTER_SEMANTIC_CHANGE = YES
OLD_AND_NEW_SEGMENTS_MIXED = NO
COLLECTOR_RUNNING_AFTER_TASK = YES
COLLECTOR_SINGLETON_OWNER_COUNT = 1
COLLECTOR_MISSING_RECORDS = 0
COLLECTOR_DUPLICATE_RECORDS = 0
MICROSTRUCTURE_COVERAGE_APPLICABLE_CANDIDATES = 100_PERCENT_1_OF_1
MICROSTRUCTURE_FUTURE_LEAKAGE = 0
OUTCOME_FOLLOWUP = CONTINUES_PENDING_1
5M_NATURAL_BOUNDARIES_ACCEPTED = 3
15M_NATURAL_BOUNDARIES_ACCEPTED = 1
SCALPING_SINGLETON_OWNER_COUNT = 1
SCALPING_MISSING_BOUNDARIES = 0
SCALPING_DUPLICATE_BOUNDARIES = 0
5M_LATENCY_MS = B1_110_126.5_179_B2_115_138.5_1486_B3_113_143_204_MIN_MEDIAN_MAX
15M_LATENCY_MS = 171_229_292_MIN_MEDIAN_MAX
5M_LATENCY_MATERIAL_REGRESSION = NO
15M_LATENCY_MATERIAL_REGRESSION = NO
DB_QUERY_OR_N_PLUS_ONE_CHANGE = NONE_BY_CHANGED_PATH
```

Fresh post-task safety corroboration: production Alembic `0018`, WAL/PITR
`true/true`, physical gap `false`, lineage valid, ACK PID 4912 heartbeat healthy
with backlog/pending `0/0`; Control `ARMED`, generation 6, audit PASS; LIVE
disabled. Runtime safety counters and collector trading mutations, parameter
promotions and Binance private order calls are all zero.

```text
RISK_CONTRACT_TESTS = 19_PASSED
SCALPING_FOCUSED_TESTS = PASS_ALL_7_TYPES_END_TO_END
15M_NON_REGRESSION_TESTS = PASS
COLLECTOR_SEGMENT_TESTS = PASS
PREDEPLOY_EXTENDED_REGRESSION = 140_PASSED_5_SKIPPED
POSTDEPLOY_CHANGED_PATH_REGRESSION = 97_PASSED
COMPILEALL = PASS
SECURITY_SCANNER = 49_PASSED_1_UNRELATED_STALE_TEST_REPRODUCED
SECRET_SCANNER = TRACKED0_EVIDENCE0_TASK_LOG0_ACTIVE0
SECURITY_FINDINGS = 0_ACTIVE_OR_CHANGED_PATH
LIVE_MODE_CHANGED_BY_TASK = NO
BINANCE_ORDER_API_CALLS_BY_TASK = 0
PUSHED = NO
```

The one broad security-test failure is the unchanged historical scanner result
for six lines in pre-existing credential-rotation scripts; no changed path is
involved. The authoritative current tracked/evidence/task-log/active exposure
scan reports zero in every category.

## Next action

```text
NEXT_ACTION = CONTINUE_AUTONOMOUS_SCALPING_CALIBRATION_COLLECTION_ON_NEW_HOMOGENEOUS_SEGMENT
OFFLINE_REPLAY = NOT_STARTED_WAIT_FOR_SUFFICIENT_NEW_SEGMENT_SAMPLE
```
