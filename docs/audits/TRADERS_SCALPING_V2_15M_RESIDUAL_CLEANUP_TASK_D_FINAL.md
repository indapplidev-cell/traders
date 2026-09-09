# Scalping v2 15m residual cleanup — Task D

```text
TASK_STATUS = PARTIAL_CLEANUP_PASS_RUNTIME_BASELINE_CONFLICT
FINAL_VERDICT = 5M_CODE_AND_PROJECTION_ISOLATED_BUT_PREEXISTING_15M_CONTAINER_IS_OPERATIONALLY_ACTIVE
RUNTIME_DEPENDENCIES_BEFORE = 3
RUNTIME_DEPENDENCIES_AFTER = 0
RESEARCH_DEPENDENCIES_BEFORE = 2
RESEARCH_DEPENDENCIES_AFTER = 0
UI_DEPENDENCIES_BEFORE = 2_GROUPS
UI_DEPENDENCIES_AFTER = 0_ACTIVE_GROUPS; LEGACY_GROUPS_EXPLICITLY_LABELED
FIXES_APPLIED = EXPLICIT_5M_IMPULSE_INPUTS; FROZEN_SET2_QUANTITY_RISK; RECORDED_CYCLE_PROVENANCE_PROJECTION; EXPLICIT_RESEARCH_CONFIG
UNRESOLVED_ITEMS = PREEXISTING_TRADE15M_CONTAINER_ACTIVE_WITH_RECENT_ROWS_CONFLICTS_WITH_REQUESTED_DISABLED_BASELINE
5M_PROFILE_ISOLATION = PASS_NO_TRADE15M_CONFIG_OR_RUNTIME_STATE_READ
15M_BEHAVIOR_CHANGED = FALSE
15M_RUNTIME_STATE = CONFIG_DISABLED_COMPOSE_PROFILE_DISABLED_BUT_EXISTING_CONTAINER_RUNNING_AND_WRITING_RECENT_15M_ROWS
SERVER_TESTS = 52_FOCUSED_PASS_PLUS_18_COLLECTOR_PASS; KNOWN_MIXED_ERA_FAILURES_RECONFIRMED
POSTGRES_E2E = PASS_FRESH_EXACT10_5M_CYCLE_AND_PERSISTED_PROVENANCE; ISOLATED_TEST_DB_CASE_SKIPPED_NO_CONFIGURED_PRINCIPAL
DESKTOP_TESTS = NOT_APPLICABLE_NO_DESKTOP_CODE_CHANGE_READONLY_API_CONTRACT_VERIFIED
COMPILE = PASS
PRODUCTION_DEPLOY = 5M_ORCHESTRATOR_AND_READONLY_API_ONLY
FRESH_5M_VERIFICATION = BOUNDARY1788991500000_EXACT10_HASH5adfbe67_FROZEN_SNAPSHOT_PRESENT
LIVE_STATE_AFTER = DISABLED
BINANCE_ORDER_CALLS = 0
SERVER_COMMIT = be05d37f0b82b1bb189c16ae07c15469525733d8
CLIENT_COMMIT = NONE
DOCUMENTATION_COMMIT = SELF_RESOLVE_WITH_GIT_LOG
PUSH = PASS
```

The deployed 5m image is
`sha256:679823363304bb23c9f87a22cda2286ccd492e0e6a7eb05a37a5cf09abb87b6d`;
the readonly image is
`sha256:108c0c899f708110821ced8db07a47a046f1f82bc7e126099f2b19298b3a7ce0`.
Both report source revision `5ac096001945d0119de477b94d2583e42f6531ef`
and restart count zero.

The fresh persisted cycle exposes `signal.timeframe=5m`, Set #2 overrides,
inherited 5m Set #1 values, explicit impulse floor `3.0 percent` and multiplier
`2.5 ATR`, and the actual evaluator inputs. The values were not calibrated or
loosened. Missing frozen risk for a 5m quantity approval now fails closed;
legacy sizing remains unchanged for its own domain.

The readonly endpoint now separates generic values into `legacy_*` groups and
projects the latest recorded cycle snapshot instead of fabricating current Set
#2 values. No Desktop/client code was changed.

Fresh inspection disproved the prompt's runtime premise: although configuration
and Compose keep `trade-15m-v1` disabled, the pre-existing legacy container is
running and produced 40 rows in the last hour. The block did not stop or restart
it because the prompt also forbids changing 15m behavior and limits deployment
to affected 5m/readonly/Desktop components. This discrepancy keeps the overall
gate closed pending explicit operational authority.
