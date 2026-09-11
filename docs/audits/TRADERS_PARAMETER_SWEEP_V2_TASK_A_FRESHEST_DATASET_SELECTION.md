# Parameter Sweep v2 — Task A: freshest frozen dataset selection

```text
TASK_STATUS = PASS
ROOT_CAUSE = ASCENDING_SOURCE_STREAM_WAS_TRUNCATED_AFTER_FIRST_MAX_ROWS_AND_THEREFORE_RETAINED_OLDEST_PREFIX
SELECTION_MODE = ALL_UNTIL_CUTOFF
TOTAL_ELIGIBLE_ROWS = 11037_FIXTURE
LOADED_ROWS = 11037_FIXTURE
FIRST_BOUNDARY = 0_FIXTURE
LAST_BOUNDARY = 11036_FIXTURE
CUTOFF = 11036_FIXTURE
OMITTED_OLDER_ROWS = 0
OMITTED_NEWER_ROWS = 0
PAGINATION = DETERMINISTIC_STREAMING_FETCHMANY_WITH_STABLE_CLOSED_UNTIL_SYMBOL_RUN_ID_ORDER
DETERMINISM = PASS
```

The production read-only query is consumed page by page. `ALL_UNTIL_CUTOFF`
retains the complete eligible universe. When a caller explicitly selects
`LATEST_N_UNTIL_CUTOFF`, a bounded deque retains the latest N stable-ordered
rows, after which replay storage is normalized to chronological ascending
order. The manifest records selection policy, eligible and loaded counts,
boundaries, omission direction, pagination, and composition diagnostics.

Focused acceptance also exercises 11,037 eligible rows with N=10,000: the
oldest 1,037 are omitted and the newest eligible boundary remains present.
