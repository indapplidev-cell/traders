# Parameter Sweep MemoryError root cause

```text
INCIDENT = MANUAL_ZERO_SETUP_RUN_AFTER_SUCCESSFUL_PREFLIGHT
DATASET_ROWS = 53
RAW_SEARCH_SPACE_SIZE = 764411904
SEARCH_SPACE_DIMENSIONS = 22
WAS_FULL_CARTESIAN_MATERIALIZED = NO
CONFIG_GENERATOR_BEFORE = itertools.product_LAZY_BUT_UNBOUNDED
PEAK_CONFIG_OBJECT_COUNT = UNBOUNDED_RESULT_RETENTION_UP_TO_RAW_SEARCH_SPACE_SIZE; EXACT_FAILURE_COUNT_NOT_RECORDED_BY_INCIDENT_RUN
PEAK_REPLAY_OBJECT_COUNT = UP_TO_31_ROW_COPIES_PLUS_PARALLEL_OUTCOME_REPLAY_AND_STATE_LIST_REFERENCES_PER_SPLIT_FOR_THE_53_ROW_DATASET
PEAK_RESULT_BUFFER_SIZE = UNBOUNDED_RESULTS_PLUS_REJECTED; EXACT_FAILURE_COUNT_NOT_RECORDED_BY_INCIDENT_RUN
DATAFRAME_GROWTH = NONE_NO_DATAFRAME_USED
PARETO_TOP_BEFORE = REQUIRED_ALL_ACCEPTED_RESULTS_IN_MEMORY
ARTIFACT_BUFFERING_BEFORE = RESULTS_PLUS_REJECTED_CONCATENATED_THEN_FULL_JSON_DUMPS_AND_REPORT_LIST
MEMORY_ERROR_ROOT_CAUSE = UNBOUNDED_EXHAUSTIVE_CONSUMPTION_OF_A_LAZY_764411904_CARTESIAN_ITERATOR_COMBINED_WITH_UNBOUNDED_RETENTION_OF_LARGE_PER_CONFIG_SPLIT_METRICS; PER_CONFIG_REPLAY_COPIES_AND_FINAL_WHOLE_RESULT_BUFFERING_AMPLIFIED_THE_HEAP_UNTIL_MEMORYERROR_IN_TIME_STOP_METRICS_TO_METRICS_REPLAYED
```

The parser calculated the Cartesian dimensions correctly. The generator did
not call `list(product(...))`, so the raw grid itself was not allocated at
once. The defect was the absence of a search planner and evaluation budget:
the lazy iterator still represented an exhaustive 764,411,904-item run.

For every consumed configuration, the old pipeline retained the complete
calibration, validation, and holdout metric trees in either `results` or
`rejected`. `_time_stop_metrics` also created an `outcomes` list, a `replayed`
list containing copied row dictionaries, and a parallel `states` list for each
split. The final path then created `all_results = results + rejected`, flattened
another list for CSV, serialized the complete JSON document, sorted all
accepted results, computed Pareto against the full collection, and accumulated
the complete report text. The incident did not persist heap telemetry, so an
exact numeric object count at the failure boundary cannot be truthfully
reconstructed; the structural upper bounds and retention path are proven from
the incident source.

The remediation uses a first-class bounded planner, an O(1)-state deterministic
mixed-radix index permutation, structural pruning before evaluation, one-result
durable JSONL/CSV writes, atomic checkpoints, disk-backed TOP/Pareto aggregation,
and streaming final JSON assembly. Replay changes use `ChainMap` overlays over
shared immutable base rows instead of copying the dataset row per configuration.
