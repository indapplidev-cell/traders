# Parameter Sweep v2 — Task B: real search registry

```text
TASK_STATUS = PASS
DECLARED_FAMILIES = SIGNAL,REGIME,ENTRY,GEOMETRY
ACTIVE_FAMILIES = SIGNAL,REGIME,ENTRY,GEOMETRY
ACTIVE_DIMENSIONS = strategy_minimum_score,regime_lookback_candles,entry_refinement_1m_confirmation_count,stop_max_bps,target_min_bps
NO_OP_DIMENSIONS = causal_reset_min_conditions:GENUINELY_INERT_ON_CONTROLLED_DATASET
RAW_CONFIG_COUNT = 64_CONTROLLED_FIXTURE
UNIQUE_EFFECTIVE_CONFIG_COUNT = 32_CONTROLLED_FIXTURE
BEHAVIORALLY_DISTINCT_COUNT = 32_CONTROLLED_FIXTURE
SIGNAL_DIMENSIONS = strategy_minimum_score
REGIME_DIMENSIONS = regime_lookback_candles
ENTRY_DIMENSIONS = entry_refinement_1m_confirmation_count
GEOMETRY_DIMENSIONS = stop_max_bps,target_min_bps
```

Registry provenance is resolved from the authoritative trading YAML and each
dimension names its research consumer. A one-factor sensitivity pass runs
before combinatorial generation. Dimensions whose meaningful funnel signature
does not change are recorded as `BEHAVIORAL_NO_OP` and excluded. Declared
families without an active dimension fail closed with
`DECLARED_FAMILY_WITHOUT_ACTIVE_DIMENSION`.

Behaviorally equivalent candidate signatures retain one deterministic
representative plus aliases, so reported evaluated work is not inflated by
silent no-op multiplication.
