# Parameter Sweep v2 — Task D: counterfactual funnel

```text
TASK_STATUS = PASS
ROOT_CAUSE = FUNNEL_WRITER_REREAD_COMPACT_RESULTS_JSONL_USING_REMOVED_V1_NESTED_FIELDS
CONFIG_RESULTS_COUNT = 2_BOUNDED_FIXTURE
RESULTS_JSONL_COUNT = 2_BOUNDED_FIXTURE
CONFIG_COUNT_PARITY = PASS
NULL_CONFIG_METADATA_AFTER = 0
AGGREGATE_FUNNEL_POPULATED = YES_PASS_SUM_OF_PER_CONFIG_VALIDATION_FUNNELS
COUNTERFACTUAL_COUNT = 1_BOUNDED_FIXTURE
REPORT_COUNTERFACTUAL_COUNT = 1_BOUNDED_FIXTURE
COUNTERFACTUAL_COUNT_PARITY = PASS
REJECTION_DISTRIBUTION_PARITY = PASS
TRADE_COUNT_PARITY = PASS
```

The artifact now consumes the same canonical compact result rows as
`RESULTS.jsonl`. It does not attempt to read removed v1 nested fields.
Per-config status, trade count and rejection distribution are copied from that
canonical row; aggregate semantics are explicitly labeled as a sum across
per-config validation funnels.

Counterfactual counts are captured from evaluated result objects before trade
detail compaction. Examples are bounded by research YAML and contain references
and disposition changes only—never inline market paths. Missing required
metadata aborts finalization with `FUNNEL_ARTIFACT_INCOMPLETE`.
