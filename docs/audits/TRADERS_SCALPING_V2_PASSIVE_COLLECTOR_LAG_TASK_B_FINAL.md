# Scalping v2 passive collector lag fix — Task B

```text
TASK_STATUS = PASS_FIXED_AND_VERIFIED
FINAL_VERDICT = CURSOR_ADVANCE_AFTER_SUCCESS_RESTORES_BACKLOG_AND_FRESH_FAIRNESS
ROOT_CAUSE = LAST_SEEN_BOUNDARY_ADVANCED_BEFORE_PARTIAL_MULTI_SYMBOL_BOUNDARY_COMPLETED
FIX = REMOVE_PREEMPTIVE_CURSOR_ADVANCE; PROCESS_BOUNDARY_CHECKPOINT_IS_SOLE_SUCCESS_ADVANCE
MISSING_BEFORE = 500
MISSING_AFTER = 0
LAG_P95_BEFORE = 67039.8575_SECONDS_MIXED_HISTORICAL_CATCHUP_WINDOW
LAG_P95_AFTER = 9.52805_SECONDS_FRESH_POST_DEPLOY_BOUNDARY
BACKLOG_BEFORE = 500
BACKLOG_AFTER = 0
DUPLICATES_AFTER = 0_OBSERVATIONS_AND_OUTCOMES
PRE_DECISION_VIOLATIONS_AFTER = 0_OF_1672_V3_OUTCOMES
POSTGRES_E2E = PASS_READONLY_EXACT_SET_2682_OF_2682_CURRENT_SEGMENT
FOCUSED_TESTS = 18_PASS_COLLECTOR; 52_PASS_ISOLATION_PROVENANCE
COMPILE = PASS
DEPLOYED_COMPONENTS = SCALPING_CALIBRATION_COLLECTOR_ONLY
ORCHESTRATOR_RESTARTED = FALSE_FOR_TASK_B
COLLECTOR_RESTART_COUNT = 0_AFTER_REQUIRED_RECREATE
LIVE_STATE_AFTER = DISABLED
BINANCE_ORDER_CALLS = 0
SERVER_COMMIT = c32e366ba8946ba46864389f9b59ed945b08d47c
DOCUMENTATION_COMMIT = SELF_RESOLVE_WITH_GIT_LOG
PUSH = PASS
```

The fixed collector caught the entire bounded backlog while authoritative 5m
continued producing new cycles. At anchor `1788991500000`, the current segment
contained all 2,682 authoritative identities in the bounded window: zero
missing, orphan or duplicate IDs, zero skipped/partial persisted cycles, and
zero mature followups without outcomes. Twenty-four followups were correctly
classified `NOT_YET_MATURE` and were not counted as defects.

The historical-window p95 remains large because the new homogeneous segment
intentionally replayed old backlog. The first fresh post-deploy exact-ten cycle
was collected with p95 9.52805 seconds and max 9.569 seconds. This is below the
240-second boundary wait and processing now exceeds the 0.033333 rows/second
arrival rate during catch-up.

Only the collector was recreated in Task B. PostgreSQL, market-data, 15m and
the authoritative 5m orchestrator were not restarted by that block.
