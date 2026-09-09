# Scalping v2 full 15m residual dependency audit — Task C

```text
TASK_STATUS = PASS_CLASSIFICATION_COMPLETE_CLEANUP_REQUIRED
FINAL_VERDICT = ALL_5M_REACHABLE_DEPENDENCIES_CLASSIFIED_3_RUNTIME_2_RESEARCH_2_UI_PROBLEM_GROUPS
TOTAL_HITS_REVIEWED = 718_LEXICAL_HITS
RELEVANT_DEPENDENCIES = 20_SEMANTIC_GROUPS
ACTIVE_5M_RUNTIME_DEPENDENCIES = 3
ACTIVE_5M_RESEARCH_DEPENDENCIES = 2
ACTIVE_5M_UI_DEPENDENCIES = 2_GROUPS
SHARED_PROFILE_SAFE = 5
TEST_ONLY = 1
HISTORICAL_ONLY = 4
DEAD_CODE = 1
UNKNOWN_REQUIRES_TRACE = 0
DIRECT_TRADE15M_CONFIG_READ_FOUND = FALSE
15M_RUNTIME_STATE_READ_FOUND = FALSE
15M_DEFAULT_FALLBACK_FOUND = TRUE_IMPULSE_THRESHOLDS_QUANTITY_RISK_AND_GENERIC_RESEARCH_FALLBACK
15M_RESEARCH_CONTAMINATION_FOUND = TRUE
15M_UI_CONTAMINATION_FOUND = TRUE
TIMEFRAME_SCALE_MISMATCHES = 3PCT_IMPULSE_FLOOR_2.5ATR_IMPULSE_MULTIPLIER_96BAR_CONFIG_ABSENT_RESEARCH_FALLBACK
BAR_COUNT_TIMEFRAME_MISMATCHES = 96BAR_CONFIG_ABSENT_RESEARCH_FALLBACK_ONLY; PRODUCTION_5M_USES_EXPLICIT_8
HIGH_PRIORITY_ITEMS = IMPULSE_3PCT_AND_2.5ATR_RUNTIME_ORIGIN; QUANTITY_1PCT_GENERIC_RISK
MEDIUM_PRIORITY_ITEMS = RESEARCH_CONFIG_ABSENT_96BAR_FALLBACK; IMPULSE_FORENSIC_LITERALS; READONLY_GENERIC_POLICY_PROJECTION
BENIGN_ITEMS = EXPLICIT_15M_CONTEXT; 15MIN_DURATION_TIME_STOP; SET2_INHERITS_5M_SET1; HISTORICAL_EXPORT
CLEANUP_REQUIRED = TRUE
FUTURE_RESEARCH_GATE = CLOSED_UNTIL_TASK_D_AND_COLLECTOR_CATCHUP_PASS
```

## Reachability result

The full lexical search covered server source, configuration, schemas, shared
policies, research scripts, tests/fixtures, readonly projection code, and the
desktop-facing API contract. Magic numbers were excluded unless the surrounding
symbol established matching semantics. The normalized inventory is
`artifacts/scalping_v2_15m_residual_audit_01/DEPENDENCY_INVENTORY.csv`.

No `trade-5m-v2 -> trade-15m-v1` configuration lookup or runtime-state lookup
exists. `trade-15m-v1` has a distinct disabled configuration domain. Fifteen-
minute candles in the 5m profile are explicit higher-timeframe context and are
not a 15m trigger dependency. Set #2 inherits Set #1, which is a 5m parameter
set, not the legacy profile.

Three active production influences require cleanup without changing their
values: the generic impulse detector owns `3.0%` and `2.5x ATR` literals whose
provenance begins at recovered baseline commit `cca167e8`, and controlled
quantity sizing falls back to the general one-percent risk fraction even for a
5m final approval. The correct action is explicit frozen 5m/Set2 provenance,
not invented tuning.

The readonly criteria projection constructs generic `OrchestratorConfig`,
`StrategyConfig`, `RiskConfig`, and `PaperConfig` defaults and can therefore
present 15m/general RR, risk, setup and timeframe values as if current. The
production 5m pipeline itself is more isolated: `PipelineRunner` resolves the
5m profile, freezes Set #2 per cycle, and passes its bar windows and policies to
analysis, strategy, risk and the Scalping paper runner.

Research contamination is bounded to the config-absent 96-bar fallback and the
forensic script's literals mirroring the current detector. Both must become
explicit 5m inputs/provenance before further strategy research.

No component was deployed or restarted for Task C. Historical 15m readability
was not changed; LIVE and order mutation paths were not touched.
