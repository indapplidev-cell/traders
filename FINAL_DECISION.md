# TRADERS_SCALPING_RISK_UNSUPPORTED_STRATEGY_TYPE_CONTRACT_REMEDIATION_01

Authoritative final audit:
`docs/audits/TRADERS_SCALPING_RISK_UNSUPPORTED_STRATEGY_TYPE_CONTRACT_REMEDIATION_01_FINAL.md`.

```text
TASK_STATUS = COMPLETED
FINAL_VERDICT = PASS_TRADERS_SCALPING_RISK_UNSUPPORTED_STRATEGY_TYPE_CONTRACT_REMEDIATION_01_COMPLETED
BLOCKER_CODE = NONE
SECONDARY_BLOCKER = NONE
STOP_CONDITION = NONE
IMPLEMENTATION_COMMIT = c30dd05ab55a102f787be3e9ec1fac6c78d71619
COLLECTOR_BINDING_COMMIT = 0c67b2f90c0d6573bcbcc645961522ce3e0f9b0c
RISK_REJECT_UNSUPPORTED_STRATEGY_TYPE_BEFORE = 261_OF_261_CURRENT_FINAL_OLD_SEGMENT
RISK_REJECT_UNSUPPORTED_STRATEGY_TYPE_AFTER = 0_OF_1_STRATEGY_ADMITTED
OLD_SEGMENT = scalping-calibration-segment-a7245351ff4a18b81d644e39
NEW_SEGMENT = scalping-calibration-segment-d8a498357af94ae584b3b691
NATURAL_ACCEPTANCE = 3_CONSECUTIVE_5M_PLUS_1_15M_EXACT10_ERRORS0_MISSING0_DUPLICATES0
CONTROL_LIVE = ARMED_GENERATION6_LIVE_DISABLED
WAL_PITR_ACK = TRUE_TRUE_NO_PHYSICAL_GAP_HEALTHY
NEXT_ACTION = CONTINUE_AUTONOMOUS_SCALPING_CALIBRATION_COLLECTION_ON_NEW_HOMOGENEOUS_SEGMENT
```

---

## Prior snapshot retained below

Snapshot cutoff: `2026-08-27T16:20:00Z`. Generated: `2026-08-27T16:24:05.729475Z`.

> PASS here means the read-only report completed. It is not a profitability, parameter-promotion, deployment, or LIVE verdict.

## Verdict

```text
TASK_STATUS = COMPLETED
FINAL_VERDICT = PASS_TRADERS_SCALPING_INTERIM_DIAGNOSTIC_SNAPSHOT_REPORT_01_COMPLETED
BLOCKER_CODE = NONE
SECONDARY_BLOCKER = NONE
STOP_CONDITION = NONE
READ_ONLY_ANALYSIS = YES
```

## Collector baseline and observation progress

```text
COLLECTOR_INSTANCE_ID = scalping-calibration-collector-fe96410c-87a9-4576-b970-00ee0ddf94d2
OBSERVATION_SEGMENT_ID = scalping-calibration-segment-a7245351ff4a18b81d644e39
STARTED_AT = 2026-08-26T21:49:16.336708Z
LAST_BOUNDARY = 2026-08-27T16:20:00Z
RECORDS_WRITTEN_AT_CUTOFF = 2240
SCALPING_PARAMETER_SET_ID = trade-5m-v1-runtime-v1-87b8a882d06b3539
RUNTIME_SOURCE_IDENTITY = 3aad38787a0ccb0af760a0ac7796913d965f2368
RUNTIME_ARTIFACT_IDENTITY = sha256:728e369dfe3b7983d44eea2e4cac6304fc29ed04f25122237baca0b3e5883ea8
OBSERVATION_START = 2026-08-26T21:45:00Z
OBSERVATION_END = 2026-08-27T16:20:00Z
OBSERVATION_DURATION_SECONDS = 67200
5M_BOUNDARIES_COLLECTED = 224
5M_EXPECTED_EVALUATIONS = 2240
5M_ACTUAL_EVALUATIONS = 2240
SAMPLE_COMPLETENESS = 100_PERCENT
GATE_24H_PROGRESS = 224_OF_288
GATE_72H_PROGRESS = 224_OF_864
MISSING_BOUNDARIES = 0
DUPLICATE_BOUNDARIES = 0
MISSING_RECORDS = 0
DUPLICATE_RECORDS = 0
COLLECTOR_ERRORS = 0
```

## Full funnel

| Stage | Count | Conversion % | Loss |
| --- | --- | --- | --- |
| Market evaluations | 2240 | 100 | null |
| Analysis qualified | 2240 | 100 | 0 |
| Structural setup | 287 | 12.8125 | 1953 |
| Strategy admitted | 254 | 88.501742 | 33 |
| Geometry valid | 0 | 0 | 254 |
| Target valid | 0 | null | 0 |
| Net-cost pass | 0 | null | 0 |
| RR pass | 0 | null | 0 |
| Risk admitted | 0 | null | 0 |
| Portfolio admitted | 0 | null | 0 |
| Final approval | 0 | null | 0 |
| PAPER order | 0 | null | 0 |
| PAPER fill | 0 | null | 0 |
| PAPER position | 0 | null | 0 |
| Closed PAPER trade | 0 | null | 0 |

Dominant viable-opportunity bottleneck: **Risk policy before geometry** — all `254` Strategy-admitted records were rejected as `RISK_REJECT_UNSUPPORTED_STRATEGY_TYPE`. The `1953` non-setup/invalid rows are not counted as lost viable opportunities.

## Rejection reasons

### Analysis

No terminal rejections at this stage.

### Setup

| Reason | Count | Share % |
| --- | --- | --- |
| NO_STRUCTURAL_SETUP | 1952 | 99.948797 |
| ENTRY_QUALITY_POOR | 1 | 0.051203 |

### Strategy

| Reason | Count | Share % |
| --- | --- | --- |
| STRATEGY_REJECT_CONFLICTING_CONTEXT | 33 | 100 |

### Geometry

No terminal rejections at this stage.

### Target

No terminal rejections at this stage.

### Net Cost

No terminal rejections at this stage.

### RR

No terminal rejections at this stage.

### Risk

| Reason | Count | Share % |
| --- | --- | --- |
| RISK_REJECT_UNSUPPORTED_STRATEGY_TYPE | 254 | 100 |

### Portfolio

No terminal rejections at this stage.

### Final Approval

No terminal rejections at this stage.

### PAPER

No terminal rejections at this stage.

`PAPER NOT_REACHED -> paper_no_plan_reason = null` passes for all snapshot rows; generic raw PAPER plan reasons were not promoted into a false terminal PAPER rejection.

## Unique opportunities and churn

```text
RAW_CANDIDATE_OBSERVATIONS = 287
UNIQUE_CAUSAL_OPPORTUNITIES = 66
REPEAT_OBSERVATIONS = 221
REPEAT_RATE = 77.003484_PERCENT
CHURN_RATE = 77.003484_PERCENT
```

| Partition | Raw | Unique | Repeats |
| --- | --- | --- | --- |
| AVAXUSDT | 17 | 5 | 12 |
| BNBUSDT | 31 | 9 | 22 |
| BTCUSDT | 14 | 2 | 12 |
| ETHUSDT | 33 | 8 | 25 |
| LINKUSDT | 48 | 11 | 37 |
| SOLUSDT | 53 | 11 | 42 |
| SUIUSDT | 47 | 12 | 35 |
| XRPUSDT | 44 | 8 | 36 |

## Symbol distribution

| Symbol | Eval | Setups | Strategy | Geometry | Cost | Risk | PAPER | Closed | Unique opp | Opp/hour |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BTCUSDT | 224 | 14 | 14 | 0 | 0 | 0 | 0 | 0 | 2 | 0.107143 |
| ETHUSDT | 224 | 33 | 33 | 0 | 0 | 0 | 0 | 0 | 8 | 0.428571 |
| SOLUSDT | 224 | 53 | 47 | 0 | 0 | 0 | 0 | 0 | 11 | 0.589286 |
| BNBUSDT | 224 | 31 | 31 | 0 | 0 | 0 | 0 | 0 | 9 | 0.482143 |
| XRPUSDT | 224 | 44 | 38 | 0 | 0 | 0 | 0 | 0 | 8 | 0.428571 |
| LINKUSDT | 224 | 48 | 36 | 0 | 0 | 0 | 0 | 0 | 11 | 0.589286 |
| DOGEUSDT | 224 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ADAUSDT | 224 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| AVAXUSDT | 224 | 17 | 15 | 0 | 0 | 0 | 0 | 0 | 5 | 0.267857 |
| SUIUSDT | 224 | 47 | 40 | 0 | 0 | 0 | 0 | 0 | 12 | 0.642857 |

Symbols with zero or very small samples are descriptive only; no symbol exclusion verdict is made.

## LONG / SHORT

| Direction | Setups | Strategy | Geometry | Cost | PAPER | Outcomes | Unique |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LONG | 261 | 237 | 0 | 0 | 0 | 0 | 55 |
| SHORT | 26 | 17 | 0 | 0 | 0 | 0 | 11 |

Directional skew: `LONG_HEAVY`.

## Strategy forensics

| Metric | P10 | P25 | P50 | P75 | P90 | P95 | N |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Raw score | 81.5 | 86.25 | 90.75 | 95 | 95 | 95 | 287 |
| Final score | 74.75 | 85.917 | 91.617 | 97 | 97 | 97 | 287 |
| Threshold | 65 | 65 | 65 | 65 | 65 | 65 | 287 |
| Margin | 9.75 | 20.917 | 26.617 | 32 | 32 | 32 | 287 |

Cap types: `{"ANALYSIS_ENTRY_QUALITY_TIER_CAP": 24, "NONE": 263}`
Gate types: `{"ADMISSION:ALLOW_RESEARCH_TRADE_PLAN:STRATEGY_ALLOW_ACCEPTABLE_SETUP": 24, "ADMISSION:ALLOW_RESEARCH_TRADE_PLAN:STRATEGY_ALLOW_GOOD_SETUP": 230, "CONFLICT_CONTEXT_GATE:FAIL:STRATEGY_REJECT_CONFLICTING_CONTEXT": 33}`
Terminal reasons: `{"NONE": 254, "STRATEGY_REJECT_CONFLICTING_CONTEXT": 33}`
Entry-quality categories: `{"CONFLICTING": 0, "INVALID": 0, "NOT_EVALUATED": 2207, "UNKNOWN": 0, "WEAK": 0}`
ENTRY_QUALITY_NOT_EVALUATED_DISTINCT_FROM_WEAK = YES

## Geometry

No production candidate reached geometry. Required stop/target/RR percentiles are therefore `null`; the report does not replay a counterfactual cohort. Stored causal input distance is included only as descriptive instrumentation in JSON.

Geometry histogram: `{"CAUSAL_STOP_TOO_WIDE": 0, "INVALID_TARGET": 0, "MISSING_TARGET": 0, "NOT_REACHED_RISK_POLICY": 254, "OTHER": 0}`.

## Microstructure coverage

```text
TOTAL_EVALUATIONS = 2240
MICROSTRUCTURE_AVAILABLE = 287
MICROSTRUCTURE_UNAVAILABLE = 1953
MICROSTRUCTURE_STALE = 0
MICROSTRUCTURE_COVERAGE_ALL_EVALUATIONS = 12.8125_PERCENT
MICROSTRUCTURE_COVERAGE_APPLICABLE_CANDIDATES = 100_PERCENT
MICROSTRUCTURE_COVERAGE_STATUS = GOOD
MICROSTRUCTURE_FUTURE_LEAKAGE = 0
```

| Component | Count | All % | Applicable % |
| --- | --- | --- | --- |
| bid | 287 | 12.8125 | 100 |
| ask | 287 | 12.8125 | 100 |
| spread | 287 | 12.8125 | 100 |
| depth | 287 | 12.8125 | 100 |
| vwap_impact | 287 | 12.8125 | 100 |

The low all-evaluation percentage is caused by no-applicable-candidate rows where runtime correctly did not request a book capture. Applicable-candidate coverage is 100%, so this is not a collector instrumentation concern.

## Cost economics and RR

| Metric | P50 | P90 | N |
| --- | --- | --- | --- |
| Spread bps | 0.850593 | 1.327053 | 287 |
| Total known cost bps | 27.857743 | 28.340716 | 287 |
| Net RR | null | null | 0 |
| Expected net edge bps | null | null | 0 |
| Break-even win rate | null | null | 0 |

Known cost input records: `287`. Net-cost pass/fail: `0/0`; not reached: `287`. Gross/net RR cohorts are all zero/not evaluated because upstream Risk policy prevented geometry.

## Risk

```text
RISK_ADMITTED = 0
RISK_REJECTED = 288
RISK_REJECT_UNSUPPORTED_STRATEGY_TYPE = 254
QUOTA_CONSUMPTION = 0
SAME_SYMBOL_EXPOSURE_REJECT = 0
PORTFOLIO_EXPOSURE_REJECT = 0
GLOBAL_BUDGET_REJECT = 0
DIRECTIONAL_LIMIT_REJECT = 0
RISK_BUDGET_RESERVATION_LEAKS = 0
```

## PAPER, outcomes, MFE/MAE

```text
PAPER_ORDERS = 0
PAPER_FILLS = 0
PAPER_POSITIONS = 0
PAPER_CLOSED_TRADES = 0
PENDING_OUTCOME_FOLLOWUPS = 23
COLLECTOR_OUTCOME_PATH_RECORDS = 264
TP_FIRST = 0
SL_FIRST = 0
SAME_CANDLE_AMBIGUOUS = 0
ENTRY_EXPIRED = 31
PATH_CAPTURED_NO_BASELINE_GEOMETRY = 233
PAPER_WIN_COUNT = 0
PAPER_LOSS_COUNT = 0
PAPER_WIN_RATE = null
PAPER_PROFIT_FACTOR = null
PAPER_NET_EXPECTANCY = null
PAPER_NET_PNL = 0
PROFITABILITY_CONFIDENCE = INSUFFICIENT_SAMPLE
```

| Metric | P50 | P90 | N |
| --- | --- | --- | --- |
| Holding seconds | 1800 | 1800 | 233 |
| MFE bps | 60.144346 | 156.556488 | 233 |
| MAE bps | 26.624068 | 73.276032 | 233 |
| Time to MFE seconds | 960 | 1728 | 233 |
| Time to MAE seconds | 360 | 1560 | 233 |

These are 30-minute path-followup diagnostics without baseline geometry, not closed PAPER trades.

## Preliminary frequency

```text
PRELIMINARY_FREQUENCY_ESTIMATE = YES
UNIQUE_OPPORTUNITIES_PER_HOUR = 3.535714
PAPER_ELIGIBLE_PER_HOUR = 0
COMPLETED_PAPER_TRADES_PER_HOUR = 0
PROJECTED_UNIQUE_OPPORTUNITIES_ROLLING_24H = 84.857143
PRELIMINARY_TRADES_PER_24H = 0
PRELIMINARY_FREQUENCY_CLASSIFICATION = FREQUENCY_TOO_LOW
```

## Regime / time distribution

Detailed regime, volatility-bucket and UTC-hour tables are in the JSON companion. They are descriptive only at this interim sample.

## Collector health and performance

```text
COLLECTOR_STATUS = RUNNING
COLLECTOR_SINGLETON_OWNER_COUNT = 1
CHECKPOINT_AGE_SECONDS_AT_BASELINE = 196.442285
RECORDS_WRITTEN_AT_CUTOFF = 2240
PENDING_FOLLOWUPS = 23
COLLECTOR_ERRORS = 0
STORAGE_SIZE_BYTES = 407792618
OBSERVATION_PARTS = 7
ROTATION_STATUS = PASS_DATE_PLUS_64_MIB_PARTS
COLLECTOR_CPU = 0.00%
COLLECTOR_MEMORY = 57.35 MiB
CHECKPOINT_HEALTH = PASS
5M_LATENCY_P50 = 184_MS
5M_LATENCY_P95 = 1552_MS
15M_LATENCY_P50 = 198_MS
15M_LATENCY_P95 = 1794_MS
5M_LATENCY_MATERIAL_REGRESSION = NO
15M_LATENCY_MATERIAL_REGRESSION = NO
```

## WAL / PITR / Control / security

```text
WAL_READY = true
PITR_READY = true
PHYSICAL_WAL_GAP = false
ACK_OWNER_HEALTH = PASS_PID4912_IDENTITY_HEARTBEAT_BACKLOG0_PENDING0
BACKLOG = 0
PENDING = 0
UNRESOLVED = 0
CONTROL_STATE = ARMED
CONTROL_GENERATION = 6
LIVE_STATE = DISABLED
```

The Readonly readiness projection still says WAL/PITR false, but the hardened canonical archive diagnostic proves PASS, contiguous lineage, 1449/1449 coverage and no physical gap. This is a known projection drift, not a new archive failure.

## Interim expert conclusions

1. RISK_REJECT_UNSUPPORTED_STRATEGY_TYPE before geometry for all 250 Strategy-admitted records.
2. 250 admissions from 283 valid setups (88.34%); throughput is sufficient for downstream calibration if the policy-path blocker is separately remediated.
3. Not assessable: geometry was never reached; do not label geometry itself as the bottleneck.
4. Microstructure and known-cost distribution are assessable, but net edge/net RR are not because geometry/reward was never produced.
5. Good on applicable candidates (100%); low all-evaluation coverage is expected because no-setup rows do not request a book capture.
6. No quota leak. Repeat/churn is high (same causal opportunities observed across boundaries) and is correctly deduplicated.
7. 64 unique opportunities over the interim window, but zero PAPER-eligible or completed trades; projected actual trades/24h is 0.
8. Known execution-cost sample exists; profitability/net-edge statistics do not.
9. At minimum the 24h/288 homogeneous-boundary gate and enough geometry-bearing/completed outcomes; current 72h and min-trade gates are not reached.
10. No collector instrumentation repair. The observed gap is production decision-path policy ordering/support, requiring a separate targeted remediation if the operator wants downstream calibration before continued accumulation.

## Recommended action

`NEXT_ACTION = CONTINUE_AUTONOMOUS_SCALPING_CALIBRATION_COLLECTION`

Collector instrumentation is healthy and the 24h gate is not reached, so continue autonomous collection. Separately diagnose the upstream RISK_REJECT_UNSUPPORTED_STRATEGY_TYPE production path before interpreting downstream calibration; any future semantic repair must start a new segment and must not be mixed with this one.

Collector should continue autonomously while the separate path remediation is evaluated. Do not mix pre- and post-remediation decision semantics in one segment.

## Required final report

```text
TASK_STATUS = COMPLETED
FINAL_VERDICT = PASS_TRADERS_SCALPING_INTERIM_DIAGNOSTIC_SNAPSHOT_REPORT_01_COMPLETED
BLOCKER_CODE = NONE
SECONDARY_BLOCKER = NONE
STOP_CONDITION = NONE
REPORT_SNAPSHOT_TIME = 2026-08-27T16:24:05.729475Z
OBSERVATION_START = 2026-08-26T21:45:00Z
OBSERVATION_DURATION_SECONDS = 67200
COLLECTOR_INSTANCE_ID = scalping-calibration-collector-fe96410c-87a9-4576-b970-00ee0ddf94d2
OBSERVATION_SEGMENT_ID = scalping-calibration-segment-a7245351ff4a18b81d644e39
SCALPING_PARAMETER_SET_ID = trade-5m-v1-runtime-v1-87b8a882d06b3539
5M_BOUNDARIES_COLLECTED = 224
5M_EXPECTED_EVALUATIONS = 2240
5M_ACTUAL_EVALUATIONS = 2240
SAMPLE_COMPLETENESS = 100_PERCENT
MARKET_EVALUATIONS = 2240
ANALYSIS_QUALIFIED = 2240
STRUCTURAL_SETUPS = 287
STRATEGY_ADMITTED = 254
GEOMETRY_VALID = 0
TARGET_VALID = 0
NET_COST_PASS = 0
RR_PASS = 0
RISK_ADMITTED = 0
PORTFOLIO_ADMITTED = 0
FINAL_APPROVALS = 0
PAPER_ORDERS = 0
PAPER_FILLS = 0
PAPER_POSITIONS = 0
PAPER_CLOSED_TRADES = 0
DOMINANT_FUNNEL_BOTTLENECK = RISK_REJECT_UNSUPPORTED_STRATEGY_TYPE_BEFORE_GEOMETRY
TOP_REJECTION_REASONS = {"Risk":[{"reason":"RISK_REJECT_UNSUPPORTED_STRATEGY_TYPE","count":254,"share_percent":100.0}],"Setup":[{"reason":"NO_STRUCTURAL_SETUP","count":1952,"share_percent":99.948797},{"reason":"ENTRY_QUALITY_POOR","count":1,"share_percent":0.051203}],"Strategy":[{"reason":"STRATEGY_REJECT_CONFLICTING_CONTEXT","count":33,"share_percent":100.0}]}
RAW_CANDIDATE_OBSERVATIONS = 287
UNIQUE_CAUSAL_OPPORTUNITIES = 66
REPEAT_OBSERVATIONS = 221
CHURN_RATE = 77.003484_PERCENT
LONG_SAMPLE_SIZE = 261
SHORT_SAMPLE_SIZE = 26
STRATEGY_RAW_SCORE_P50 = 90.75
STRATEGY_RAW_SCORE_P90 = 95
STRATEGY_FINAL_SCORE_P50 = 91.617
STRATEGY_FINAL_SCORE_P90 = 97
STOP_DISTANCE_P50 = null
STOP_DISTANCE_P90 = null
TARGET_DISTANCE_P50 = null
TARGET_DISTANCE_P90 = null
GROSS_RR_P50 = null
GROSS_RR_P90 = null
MICROSTRUCTURE_COVERAGE_ALL_EVALUATIONS = 12.8125_PERCENT
MICROSTRUCTURE_COVERAGE_APPLICABLE_CANDIDATES = 100_PERCENT
MICROSTRUCTURE_COVERAGE_STATUS = GOOD
MICROSTRUCTURE_UNAVAILABLE_REASON_HISTOGRAM = [{"reason":"NO_APPLICABLE_CANDIDATE_RUNTIME_CAPTURE_NOT_REQUESTED","count":1953,"share_percent":100.0}]
SPREAD_BPS_P50 = 0.850593
SPREAD_BPS_P90 = 1.327053
TOTAL_COST_BPS_P50 = 27.857743
TOTAL_COST_BPS_P90 = 28.340716
NET_RR_P50 = null
NET_RR_P90 = null
EXPECTED_NET_EDGE_BPS_P50 = null
EXPECTED_NET_EDGE_BPS_P90 = null
RISK_BUDGET_RESERVATION_LEAKS = 0
PAPER_WIN_COUNT = 0
PAPER_LOSS_COUNT = 0
PAPER_WIN_RATE = null
PAPER_PROFIT_FACTOR = null
PAPER_NET_EXPECTANCY = null
PAPER_NET_PNL = 0
PROFITABILITY_CONFIDENCE = INSUFFICIENT_SAMPLE
HOLDING_TIME_P50 = 1800
HOLDING_TIME_P90 = 1800
MFE_P50 = 60.144346
MFE_P90 = 156.556488
MAE_P50 = 26.624068
MAE_P90 = 73.276032
PRELIMINARY_TRADES_PER_24H = 0
PRELIMINARY_FREQUENCY_CLASSIFICATION = FREQUENCY_TOO_LOW
COLLECTOR_SINGLETON_OWNER_COUNT = 1
CHECKPOINT_HEALTH = PASS
COLLECTOR_ERRORS = 0
COLLECTOR_CPU = 0.00%
COLLECTOR_MEMORY = 57.35_MiB
5M_LATENCY_MATERIAL_REGRESSION = NO
15M_LATENCY_MATERIAL_REGRESSION = NO
WAL_READY = true
PITR_READY = true
PHYSICAL_WAL_GAP = false
ACK_OWNER_HEALTH = PASS
CONTROL_STATE = ARMED
CONTROL_GENERATION = 6
LIVE_STATE = DISABLED
COLLECTOR_RUNNING_AFTER_REPORT = YES
COLLECTOR_CHECKPOINT_CHANGED_BY_TASK = NO
SCALPING_PRODUCTION_BEHAVIOR_CHANGED_BY_TASK = NO
TRADE_15M_PRODUCTION_BEHAVIOR_CHANGED_BY_TASK = NO
INTERIM_EXPERT_CONCLUSION = COLLECTOR_HEALTHY_APPLICABLE_MICROSTRUCTURE_GOOD_DOWNSTREAM_BLOCKED_BY_UNSUPPORTED_STRATEGY_RISK_POLICY_NO_PROFITABILITY_SAMPLE
RECOMMENDED_ACTION = CONTINUE_AUTONOMOUS_SCALPING_CALIBRATION_COLLECTION
REPORT_MD = D:\disk_E\game_projects\traders\evidence_inbox\TRADERS_SCALPING_INTERIM_DIAGNOSTIC_SNAPSHOT_REPORT_01.md
REPORT_JSON = D:\disk_E\game_projects\traders\evidence_inbox\TRADERS_SCALPING_INTERIM_DIAGNOSTIC_SNAPSHOT_REPORT_01.json
PUSHED = NO
```
