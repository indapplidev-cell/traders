# Parameter Sweep v2 — Block B artifact compaction

TASK_STATUS = PASS
SCHEMA_V2 = PASS_EXPLICIT_ARTIFACT_SCHEMA_VERSION_2
INLINE_MARKET_PATH_COUNT = 0
V1_COMPATIBILITY = PASS_TRANSPARENT_READER
V1_TO_V2_MIGRATION = PASS_DRY_RUN_ATOMIC_NON_DESTRUCTIVE
RESOLVER_PARITY = PASS_SEMANTIC_HASH_VERIFIED

REPRESENTATIVE_SIZE_BEFORE = 1157485547_BYTES
REPRESENTATIVE_SIZE_AFTER = 77739047_BYTES
SIZE_REDUCTION_PERCENT = 93.2838

RESULTS_JSONL_SIZE = 2645850_BYTES_FOR_1277_CONFIGS
TOTAL_RUN_SIZE = 77739047_BYTES_INCLUDING_70895354_BYTE_SHARED_FROZEN_DATASET
SOFT_BUDGET_PASS = YES
HARD_BUDGET_PASS = YES

The measured non-destructive migration source is
`artifacts/scalping_v2_parameter_sweep/20260907_235854_595`; the v2 evidence is
`artifacts/scalping_v2_parameter_sweep/v2-migration-acceptance-v2-20260910`.
The original directory and bytes were not modified. At the measured v2 result
row rate, 5,000 rows plus the fixed dataset project to 81,254,986 bytes
(77.49 MiB), below both the 120 MiB soft target and 200 MiB hard cap.

Schema v2 stores one compact row per configuration. Detailed finalist rows are
bounded by YAML and replace `market_path_1m` with a hash-checked
`market_path_ref`. Accepted/rejected evaluation status is independent of the
performance class. The finalizer records total/results/finalist/dataset bytes
and fails closed with `ARTIFACT_SIZE_BUDGET_EXCEEDED` above a YAML-owned hard
budget.

Validation:

- `python -m pytest tests/research/test_parameter_sweep_artifact_v2.py -q`
  => `4 passed`;
- full representative migration => `1277 source rows = 1277 target rows`;
- compact `RESULTS.jsonl` scan => zero inline market paths.

