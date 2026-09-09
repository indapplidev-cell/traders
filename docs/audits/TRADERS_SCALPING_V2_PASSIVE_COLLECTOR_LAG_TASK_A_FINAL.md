# Scalping v2 passive collector lag — Task A

```text
TASK_STATUS = PASS_DEFECT_PROVEN
FINAL_VERDICT = WATERMARK_CURSOR_DEFECT_AND_PARTIAL_CYCLE_ADVANCE_DEFECT
ANCHOR = 1788990000000_20260909T214000Z_EXACT10_TRADE5MV2_SET2_SCHEMA0031
AUTHORITATIVE_IDS = 2682_IN_BOUNDED_24H_RESULT_WINDOW
COLLECTOR_IDS = 2182_CURRENT_V3_SEGMENT
MISSING_IDS = 500
LATE_IDS = 2182_HISTORICAL_CATCHUP_OBSERVATIONS_OVER_EXPECTED_240S_BOUND
DUPLICATE_IDS = 0
ORPHAN_IDS = 0
LAG_P50_SECONDS = 37619.9405
LAG_P95_SECONDS = 67039.8575
LAG_P99_SECONDS = 69439.80702
LAG_MAX_SECONDS = 70029.025
SKIPPED_CYCLES = 50
PARTIAL_CYCLES = 0_PERSISTED_BUT_PARTIAL_ARRIVAL_WAS_SKIPPED_BY_CURSOR
BACKLOG_COUNT = 500
OLDEST_BACKLOG_AGE = 12900_SECONDS_AT_ANCHOR
ARRIVAL_RATE = 0.033333_ROWS_PER_SECOND_10_ROWS_PER_300S
PROCESSING_RATE = 0_ROWS_PER_SECOND_AFTER_1788977100000
MATURE_BUT_NOT_COLLECTED = 0_FOR_ALREADY_COLLECTED_FOLLOWUPS; 500_SOURCE_ROWS_NOT_INGESTED
WATERMARK_DEFECT_FOUND = TRUE
RESTART_RESUME_DEFECT_FOUND = FALSE_CHECKPOINT_RESUME_IS_IDEMPOTENT
RESEARCH_DATA_COMPLETE = FALSE
RESEARCH_DATA_DELAYED = TRUE
RESEARCH_DATA_BIASED = TRUE_TEMPORAL_AND_CYCLE_COVERAGE
ROOT_CAUSE = RUN_LOOP_ADVANCED_LAST_SEEN_BEFORE_PROCESS_BOUNDARY_CONFIRMED_FULL
FIX_REQUIRED = TRUE_MINIMAL_CURSOR_ADVANCE_AFTER_SUCCESS
```

## Evidence

The authoritative source was the latest completed `trade-5m-v2` cycle in
PostgreSQL. The exact expected identities are frozen in
`artifacts/scalping_v2_collector_lag_01/AUTHORITATIVE_5M_EXPECTED_IDS.jsonl`;
the machine-readable comparison is `TASK_A_REPORT.json` in the same directory.
The universe was derived from the anchor cycle, not hardcoded by the forensic.

The collector's durable checkpoint stopped at `1788977100000`, while the
authoritative runtime reached `1788990000000`. PostgreSQL contained ten complete
results for each recent boundary. Source inspection found that `run()` assigned
`last_seen_boundary` before `process_boundary()` returned success. If a boundary
was observed while only part of its ten-symbol set existed, `process_boundary`
returned `False`, but the next poll selected a later boundary. This precisely
explains zero persisted partial cycles, skipped whole cycles, a growing backlog,
and a healthy-looking polling loop with a stale checkpoint.

Normal outcome maturity is separate: among observations already ingested in the
current v3 segment, mature followups missing outcomes were zero and outcome
identity duplicates were zero. The defect is opportunity/candidate ingestion,
not the expected 15-minute time-stop maturity wait.

Read-only PostgreSQL inspection showed two idle collector connections, no lock
wait, no transaction stall, and the advisory singleton lock held by one owner.
The container restart count was zero. Poll cadence was two seconds; throughput
after the stuck boundary was zero, below the authoritative arrival rate.

No component was deployed or restarted in Task A. LIVE and real order mutation
paths were not touched.
