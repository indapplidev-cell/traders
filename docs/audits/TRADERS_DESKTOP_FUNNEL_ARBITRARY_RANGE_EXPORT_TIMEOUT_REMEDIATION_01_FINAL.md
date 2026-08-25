# TRADERS desktop Funnel arbitrary-range export timeout remediation 01

## Final decision

```text
TASK_STATUS = COMPLETED
FINAL_VERDICT = PASS_TRADERS_DESKTOP_FUNNEL_ARBITRARY_RANGE_EXPORT_TIMEOUT_REMEDIATION_01_COMPLETED
BLOCKER_CODE = NONE
SECONDARY_BLOCKER = NONE
STOP_CONDITION = NONE
```

## Reproduction and root cause

The production desktop provider was exercised with its unchanged 10-second
aggregate read timeout. A `trade-5m-v1` JSONL export for one hour returned
877855 bytes in 814.546 ms. The exact 24-hour request returned no first byte
and raised `ProviderTimeoutError`/`READ_TIMEOUT` after 10.027 seconds; curl
corroboration timed out at 10.005519 seconds with HTTP 000 and zero bytes.

The old repository used one joined rows query and one bulk outcomes query, so
N+1 was not the cause. The defect was a synchronous one-shot path that loaded
up to 2880 wide JSON rows, built all canonical records, built aggregates and
serialized the full response before sending its first byte. During the
reproduction the 512 MiB Readonly container reached 511.9 MiB. The client also
held the returned body before writing it. A 24-hour hard cap prevented longer
ranges instead of bounding work.

## Remediation contract

```text
ROUTE = GET_/api/v1/trading/funnel/export
PAGED_FORMATS = jsonl-records,csv-records
LEGACY_FORMAT_COMPATIBILITY = jsonl,csv,summary-json,summary-md
ARBITRARY_PAGED_TOTAL_RANGE_CAP = NONE
DEFAULT_PAGE_SIZE = 200
MAX_PAGE_SIZE = 2000
ORDER = boundary_closed_at_ASC,symbol_ASC,run_id_ASC
OFFSET = NOT_USED
SNAPSHOT = min(requested_to,latest_authoritative_available_boundary_at_start)
CURSOR = OPAQUE_CHECKSUM_VALIDATED_PROFILE_RANGE_SYMBOL_SNAPSHOT_KEYSET
FIRST_PAGE_SQL = bounds_PLUS_joined_records_PLUS_bulk_outcomes
FOLLOWING_PAGE_SQL = joined_records_PLUS_bulk_outcomes
N_PLUS_ONE = NO
DB_WRITES = 0
```

The first response reports requested and available bounds and fixes
`snapshot_closed_until`. Every following request must repeat that snapshot and
present a cursor whose profile, requested range, symbol and snapshot match.
New boundaries cannot enter the in-progress export. Keyset filtering uses the
last `(closed_until_ms, symbol, run_id)`; no OFFSET or full-history sort/window
is used. Existing indexes `ix_online_pipeline_profile_boundary`,
`ix_online_pipeline_runs_closed_until`, the unique run-id indexes and the
unique profile window support the bounded lookups.

Representative production EXPLAIN ANALYZE loaded 201 complete joined rows in
57.709 ms on the first range page and 22.809 ms on a later keyset page.
Incremental-sort peak memory was 185 KiB. Application query count is bounded;
the indexed join remains one SQL statement, not per-row SQL.

## Desktop and resumability

The desktop requests pages asynchronously and writes each page incrementally.
JSONL writes one authoritative record per line. CSV emits UTF-8 BOM/header
once and quotes through `csv.DictWriter`. Summary JSON/Markdown spools the
authoritative JSONL records and performs a second streaming presentation-only
aggregation; it does not recalculate decisions, geometry, RR, cost or risk.

The destination remains `filename.part` until success. Each page is flushed
and fsynced before an atomically replaced resume record commits the cursor,
snapshot, row count and byte offset. Restart truncates any uncommitted tail to
the committed byte offset, preventing duplicates across the crash window.
Only idempotent GET pages are retried, at most three attempts with bounded
backoff. Final success uses atomic replacement; cancel stops only the client
loop and leaves a safe resumable `.part` plus metadata. Unit acceptance proves
timeout after page N, retry, restart resume, exact ordering, five unique rows,
zero duplicates and zero missing rows. Resume metadata and cursors contain no
credentials or secret fields.

The dialog retains current/last/1h/4h/12h/24h and adds 7d, 30d, arbitrary
UTC-aware from/to and all-available-history. Progress reports rows, current
boundary and elapsed time without an expensive COUNT. RU/EN messages
distinguish connect failure, page timeout, retry, cancellation, partial
availability, server failure and file-write failure.

## Performance and production acceptance

Both profiles completed real seven-day desktop page loops against production:

```text
trade-5m-v1 = 13040_rows_66_pages_131.489_seconds_0_timeouts_ordered_unique
trade-15m-v1 = 6520_rows_33_pages_66.243_seconds_0_timeouts_ordered_unique
TOTAL = 19560_rows_99_pages_197.732_seconds
7D_PAGE_P50 = 1520.605ms_5m;1610.850ms_15m
7D_PAGE_P95 = 2304.189ms_5m;2365.062ms_15m
7D_PAGE_MAX = 5675.614ms_5m;2497.476ms_15m
MEASURED_ACCEPTANCE_BOUND = P95_LE_3000ms_AND_MAX_LE_6000ms
```

The measured 3s/6s bound is justified for the wide canonical production rows
under `tracemalloc`; every page remains below the unchanged 10-second desktop
read timeout. A separate 24-hour run with no instrumentation page retention
measured 7.63 MiB peak Python allocation, 1.58-1.74s P95 and 2.16s max. Total
range size therefore no longer determines a single server read timeout.

Available authoritative ranges at acceptance were:

```text
trade-5m-v1 = 1787242200000..1787633400000
trade-15m-v1 = 1784143800000..1787633100000
```

A production spot check for run
`orchestrator:935410b1c50b4e849c00068574f66ae3` matched direct PostgreSQL facts:
profile `trade-5m-v1`, boundary `1787594100000`, symbol `SUIUSDT`, entry
`0.8211`, invalidation `0.8337`, final stop `0.8350677083333333`, stop distance
`170.10971055`, stop-envelope false, economics enabled/failed, PAPER `NO_PLAN`
and the persisted paper reason sequence. Export record equivalence is PASS.

## Runtime isolation and recovery

Only the Readonly container was replaced once. Final identity is container
`7c9c376af2650eaa3332ebe237a739cd3dbe0ac6b9a8d1e08b2f8bd2732202be`,
image `sha256:4426ad3c4dd8cddbcfeec5eeca3fa6e99e42cf8645226a28fb0ac94fab721947`,
source `4d32db3c9c3f4b2b2de225468615e2903159a26a`, healthy with restart count 0.
The route inventory remains 28 GET and zero write methods.

Observer PID 23308, creation time, command and counting window remained
unchanged. Its homogeneous 5m window advanced naturally from 130/1300 to
132/1320, exact ten symbols per boundary and zero duplicate keys. The 15m
window advanced from 12/120 to 13/130, also exact ten and zero duplicates.
Under-export 5m P95 was 199.85 ms. The 15m boundary completed with P95 2280.45
ms, within the observed 24-hour boundary envelope (P95 max 2593.7 ms), far
inside its 900-second schedule and without loss; material regression is NO.
Trading semantics, profiles, 5m minimum RR 1.5, Control generation 6, canary,
PAPER tables and LIVE state were unchanged. Command/order/fill/position counts
remain 0/0/0/0.

Canonical post-load recovery diagnosis is PASS: WAL archive mode ON, PITR
lineage contiguous, 1210/1210 required segments, missing/source-recoverable 0,
active unresolved/backlog/pending 0/0/0, physical gap false. ACK daemon PID
4912 and heartbeat owner identity remained unchanged.

## Validation and Git

```text
SERVER_EXPORT_FOCUSED = 8_passed
SERVER_READONLY_SECURITY_REGRESSION = 737_passed_7_skipped
DESKTOP_EXPORT_FOCUSED = 9_passed
DESKTOP_FULL_REGRESSION = 1464_passed_2_skipped_3029_subtests;_isolated_Tcl_rerun_1_passed
SECRET_FIELDS_IN_EXPORT = 0
SECRET_FIELDS_IN_CURSOR = 0
SECRET_FIELDS_IN_RESUME_STATE = 0
SERVER_SOURCE_COMMIT = 4d32db3c9c3f4b2b2de225468615e2903159a26a
DESKTOP_SOURCE_COMMIT = 9983d8f039e5bb3bdd0db1d252dd9837fb4fa20c
MOBILE_COMMITS = NONE
PUSHED = NO
EVIDENCE_SHA256 = RESOLVED_EXTERNALLY_AFTER_COPY
```

The one full-client GUI failure was an environmental Tcl `init.tcl` lookup;
the exact isolated rerun passed without source changes. No migration was
required; production remains on Alembic `0018_promote_5m_production_search`.

## Required report

```text
TASK_STATUS = COMPLETED
FINAL_VERDICT = PASS_TRADERS_DESKTOP_FUNNEL_ARBITRARY_RANGE_EXPORT_TIMEOUT_REMEDIATION_01_COMPLETED
BLOCKER_CODE = NONE
SECONDARY_BLOCKER = NONE
STOP_CONDITION = NONE
ORIGINAL_TIMEOUT_REPRODUCED = YES
ORIGINAL_TIMEOUT_TYPE = READ_TIMEOUT
ORIGINAL_TIMEOUT_RANGE = trade-5m-v1_24h_JSONL
EXPORT_TIMEOUT_ROOT_CAUSE_PROVEN = YES
ARBITRARY_TOTAL_RANGE_SUPPORTED = YES_PAGED_MODE
TOTAL_RANGE_HARD_CAP = NONE_PAGED_MODE
EXPORT_PAGINATION_METHOD = STABLE_KEYSET_CURSOR
OFFSET_PAGINATION_USED = NO
STABLE_SNAPSHOT_IMPLEMENTED = YES
EXPORT_PAGE_QUERY_COUNT_BOUNDED = YES
EXPORT_QUERY_N_PLUS_ONE = NO
EXPORT_PAGE_MEMORY_BOUNDED = YES
DESKTOP_EXPORT_STREAMING_WRITE = YES
DESKTOP_EXPORT_FULL_DATASET_HELD_IN_MEMORY = NO
ATOMIC_PART_FILE_RENAME = YES
EXPORT_RETRY_SUPPORTED = YES
EXPORT_RESUME_SUPPORTED = YES
DUPLICATE_ROWS_AFTER_RESUME = 0
MISSING_ROWS_AFTER_RESUME = 0
JSONL_EXPORT = PASS
CSV_EXPORT = PASS
SUMMARY_EXPORT = PASS_JSON_AND_MARKDOWN
REAL_LARGE_RANGE_TEST = PASS_BOTH_PROFILES_7D_REQUEST
REAL_LARGE_RANGE_SERVER_TIMEOUTS = 0
EXPORT_RECORD_EQUIVALENCE = PASS
ACTIVE_CALIBRATION_OBSERVER_PRESERVED = YES
CALIBRATION_SAMPLE_SEMANTICS_CHANGED_BY_TASK = NO
5M_EXPORT_CAUSED_BOUNDARY_LOSS = 0
15M_EXPORT_CAUSED_BOUNDARY_LOSS = 0
15M_LATENCY_MATERIAL_REGRESSION = NO
TRADE_15M_PRODUCTION_BEHAVIOR_CHANGED_BY_TASK = NO
TRADE_5M_PRODUCTION_BEHAVIOR_CHANGED_BY_TASK = NO
PRODUCTION_5M_MIN_RR_CHANGED_BY_TASK = NO
READONLY_GET_ROUTE_COUNT_AFTER = 28
READONLY_WRITE_ROUTE_COUNT_AFTER = 0
READONLY_REPLACEMENTS_BY_TASK = 1
WAL_READY_AFTER = true
PITR_READY_AFTER = true
ACTIVE_UNRESOLVED_FAILURES_AFTER = 0
EXPORT_BACKLOG_AFTER = 0
PENDING_ARCHIVE_STATUS_AFTER = 0
LINEAGE_VALID_AFTER = true
PHYSICAL_WAL_GAP_AFTER = false
ACK_OWNER_HEARTBEAT_HEALTH_AFTER = PASS
PUSHED = NO
NEXT_ACTION = CONTINUE_TRADERS_5M_SCALPING_PRODUCTION_OBSERVATION_AND_CALIBRATION_BASELINE_01_UNTIL_144_HOMOGENEOUS_BOUNDARIES
```
